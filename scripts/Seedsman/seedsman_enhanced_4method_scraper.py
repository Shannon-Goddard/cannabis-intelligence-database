#!/usr/bin/env python3
"""
Seedsman - Enhanced 4-Method Scraper (THE BEAR)
Target: 1000+ strains with 95%+ success rate
Strategy: Breeder page crawling + 4-method extraction
"""

import json
import boto3
import requests
import time
import re
from bs4 import BeautifulSoup
from decimal import Decimal
from datetime import datetime

class SeedsmanEnhanced4MethodScraper:
    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        self.table = self.dynamodb.Table('cannabis-strains-universal')
        self.secrets_client = boto3.client('secretsmanager', region_name='us-east-1')
        self.brightdata_config = self._get_brightdata_credentials()
        
        # Success tracking
        self.total_processed = 0
        self.successful_extractions = 0
        self.method_stats = {'structured': 0, 'description': 0, 'patterns': 0, 'fallback': 0}
        
    def _get_brightdata_credentials(self):
        response = self.secrets_client.get_secret_value(SecretId='cannabis-brightdata-api')
        return json.loads(response['SecretString'])
    
    def _brightdata_request(self, url):
        api_url = "https://api.brightdata.com/request"
        headers = {"Authorization": f"Bearer {self.brightdata_config['api_key']}"}
        payload = {"zone": self.brightdata_config['zone'], "url": url, "format": "raw"}
        
        response = requests.post(api_url, headers=headers, json=payload, timeout=30)
        return response.text if response.status_code == 200 else None

    def method1_structured_extraction(self, soup, url):
        """Method 1: Seedsman specifications table extraction"""
        data = {}
        
        # Target the main specifications table
        table = soup.find('table', id='product-attribute-specs-table')
        if table:
            rows = table.find_all('tr')
            for row in rows:
                label_th = row.find('th', class_='col label')
                data_td = row.find('td', class_='col data')
                
                if label_th and data_td:
                    label_h4 = label_th.find('h4')
                    if label_h4:
                        label = label_h4.get_text().strip()
                        
                        # Extract value from nested spans or h3
                        spans = data_td.find_all('span')
                        if spans:
                            # Handle multi-value fields (pipe-separated)
                            values = [span.get_text().strip() for span in spans if span.get_text().strip()]
                            value = ' | '.join(values) if len(values) > 1 else values[0] if values else ''
                        else:
                            # Fallback to h3 text
                            h3 = data_td.find('h3')
                            value = h3.get_text().strip() if h3 else data_td.get_text().strip()
                        
                        # Map Seedsman fields to our schema
                        field_map = {
                            'SKU': 'sku',
                            'Brand/breeder': 'brand_breeder',
                            'Parental lines': 'parental_lines',
                            'Variety': 'variety',
                            'Color': 'color',
                            'Flowering type': 'flowering_type',
                            'Sex': 'sex',
                            'THC content': 'thc_content',
                            'CBD content': 'cbd_content',
                            'Yield outdoor': 'yield_outdoor',
                            'Yield indoor': 'yield_indoor',
                            'Plant size': 'plant_size',
                            'Photoperiod flowering time': 'photoperiod_flowering_time',
                            'Northern hemisphere harvest': 'northern_hemisphere_harvest',
                            'Southern hemisphere harvest': 'southern_hemisphere_harvest',
                            'Suitable climates': 'suitable_climates',
                            'Aroma': 'aroma'
                        }
                        
                        if label in field_map and value:
                            data[field_map[label]] = value
        
        return data

    def method2_description_mining(self, soup, url):
        """Method 2: Mine Seedsman product descriptions"""
        data = {}
        
        # Look for product description sections
        desc_selectors = [
            'div.ProductActions-ShortDescription',
            'div.ProductPageDescription',
            'div.product-description',
            'div.description'
        ]
        
        about_parts = []
        for selector in desc_selectors:
            elements = soup.select(selector)
            for element in elements:
                text = element.get_text().strip()
                if text and len(text) > 100:
                    about_parts.append(text)
        
        if about_parts:
            full_text = ' '.join(about_parts)
            data['about_info'] = full_text
            
            # Extract specific patterns from descriptions
            patterns = {
                'genetics_pattern': r'(?:genetics|lineage|cross|bred from)[:\s]*([^.]+?)(?:\.|$)',
                'effects_pattern': r'(?:effect|high|buzz)[s]?[:\s]*([^.]+?)(?:\.|$)',
                'flavor_pattern': r'(?:flavor|taste|aroma)[s]?[:\s]*([^.]+?)(?:\.|$)',
                'cultivation_pattern': r'(?:grow|cultivat|flower)[^.]*?(?:indoor|outdoor|climate)[^.]*'
            }
            
            for key, pattern in patterns.items():
                matches = re.findall(pattern, full_text, re.IGNORECASE)
                if matches:
                    data[key] = '; '.join(matches[:2])
        
        return data

    def method3_advanced_patterns(self, soup, url):
        """Method 3: Seedsman specific patterns"""
        data = {}
        
        # Seedsman is always the seed bank
        data['seed_bank'] = 'Seedsman'
        
        # Extract strain name from product title or H1
        title_selectors = ['h1.page-title', 'h1', '.product-name h1', '.page-title']
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                strain_name = title_elem.get_text().strip()
                # Clean Seedsman naming patterns
                strain_name = re.sub(r'\s+', ' ', strain_name)
                strain_name = re.sub(r'\s*(Feminized|Auto|Autoflower|Seeds?|Regular)\s*', ' ', strain_name, re.IGNORECASE)
                strain_name = re.sub(r'\s*-\s*Seedsman\s*', '', strain_name, re.IGNORECASE)
                data['strain_name'] = strain_name.strip()
                break
        
        # Extract strain name from URL if not found
        if 'strain_name' not in data:
            path_parts = url.split('/')
            for part in reversed(path_parts):
                if part and len(part) > 5 and 'seedsman' not in part.lower():
                    strain_name = part.replace('-', ' ').title()
                    # Clean common suffixes
                    strain_name = re.sub(r'\s+(Auto|Feminized|Regular|Seeds?)$', '', strain_name, re.IGNORECASE)
                    strain_name = re.sub(r'^Sman\s+', '', strain_name)
                    data['strain_name'] = strain_name.strip()
                    break
        
        # Detect seed type from URL or content
        url_lower = url.lower()
        page_text = soup.get_text().lower()
        
        if 'autoflower' in url_lower or 'auto' in url_lower or 'autoflower' in page_text:
            data['growth_type'] = 'Autoflower'
            data['seed_type'] = 'Feminized'
        elif 'feminized' in url_lower or 'fem' in url_lower or 'feminized' in page_text:
            data['seed_type'] = 'Feminized'
            data['growth_type'] = 'Photoperiod'
        elif 'regular' in url_lower or 'reg' in url_lower or 'regular' in page_text:
            data['seed_type'] = 'Regular'
            data['growth_type'] = 'Photoperiod'
        
        return data

    def method4_fallback_extraction(self, soup, url):
        """Method 4: Universal fallback for Seedsman"""
        data = {}
        
        # Meta description fallback
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and not data.get('about_info'):
            data['about_info'] = meta_desc.get('content', '')
        
        # Page title fallback
        title = soup.find('title')
        if title and not data.get('strain_name'):
            title_text = title.get_text().strip()
            title_parts = title_text.split(' - ')
            if title_parts:
                potential_strain = title_parts[0].strip()
                potential_strain = re.sub(r'\s+(Auto|Feminized|Regular|Seeds?)$', '', potential_strain, re.IGNORECASE)
                data['strain_name'] = potential_strain
        
        return data

    def apply_4_methods(self, html_content, url):
        """Apply all 4 extraction methods with Seedsman hardcoded values"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        strain_data = {
            'seed_bank': 'Seedsman',
            'source_url': url,
            'extraction_methods_used': []
        }
        
        # Method 1: Structured extraction
        method1_data = self.method1_structured_extraction(soup, url)
        if method1_data:
            strain_data.update(method1_data)
            strain_data['extraction_methods_used'].append('structured')
            self.method_stats['structured'] += 1
        
        # Method 2: Description mining
        method2_data = self.method2_description_mining(soup, url)
        if method2_data:
            strain_data.update(method2_data)
            strain_data['extraction_methods_used'].append('description')
            self.method_stats['description'] += 1
        
        # Method 3: Advanced patterns
        method3_data = self.method3_advanced_patterns(soup, url)
        if method3_data:
            strain_data.update(method3_data)
            strain_data['extraction_methods_used'].append('patterns')
            self.method_stats['patterns'] += 1
        
        # Method 4: Fallback extraction
        method4_data = self.method4_fallback_extraction(soup, url)
        if method4_data:
            strain_data.update(method4_data)
            strain_data['extraction_methods_used'].append('fallback')
            self.method_stats['fallback'] += 1
        
        # Set breeder name from brand_breeder or default to Seedsman
        if strain_data.get('brand_breeder') and strain_data['brand_breeder'] != 'Seedsman':
            strain_data['breeder_name'] = strain_data['brand_breeder']
        else:
            strain_data['breeder_name'] = 'Seedsman'
        
        # Calculate quality score
        strain_data['data_completeness_score'] = self.calculate_quality_score(strain_data)
        strain_data['quality_tier'] = self.determine_quality_tier(strain_data['data_completeness_score'])
        strain_data['field_count'] = len([v for v in strain_data.values() if v])
        
        # Create strain ID
        strain_name = strain_data.get('strain_name', 'Unknown')
        breeder_name = strain_data.get('breeder_name', 'Seedsman')
        strain_data['strain_id'] = self.create_strain_id(strain_name, breeder_name)
        
        # Add timestamps
        now = datetime.utcnow().isoformat() + 'Z'
        strain_data['created_at'] = now
        strain_data['updated_at'] = now
        
        return strain_data

    def calculate_quality_score(self, strain_data):
        """Calculate weighted quality score optimized for Seedsman"""
        field_weights = {
            # Core fields (required)
            'strain_name': 10,
            'seed_bank': 10,
            
            # Seedsman strengths (98% completeness potential)
            'brand_breeder': 10,             # Excellent breeder attribution
            'thc_content': 9,                # Precise THC ranges
            'yield_indoor': 9,               # Indoor yield specifications
            'yield_outdoor': 9,              # Outdoor yield specifications
            'photoperiod_flowering_time': 8, # Flowering time
            'suitable_climates': 8,          # Multi-climate support
            'parental_lines': 7,             # Genetics lineage
            'aroma': 7,                      # Multi-value aromas
            'variety': 6,                    # Sativa/Indica classification
            'flowering_type': 6,             # Photoperiod/Auto
            'sex': 6,                        # Feminized/Regular
            'plant_size': 5,                 # Size classification
            'sku': 5,                        # Product identifier
            
            # Enhanced fields from description mining
            'about_info': 6,                 # Rich descriptions
            'genetics_pattern': 5,           # Extracted genetics
            'effects_pattern': 5,            # Effect descriptions
            'flavor_pattern': 4,             # Flavor profiles
            'cultivation_pattern': 4,        # Growing info
            
            # Additional classification
            'growth_type': 4,                # Auto/Photo classification
            'seed_type': 4,                  # Feminized/Regular
            'breeder_name': 8                # Breeder attribution
        }
        
        total_possible = sum(field_weights.values())
        actual_score = 0
        
        for field, weight in field_weights.items():
            if strain_data.get(field) and len(str(strain_data[field]).strip()) > 2:
                actual_score += weight
        
        return round((actual_score / total_possible) * 100, 1)

    def determine_quality_tier(self, score):
        if score >= 80: return "Premium"
        elif score >= 60: return "High"
        elif score >= 40: return "Medium"
        elif score >= 20: return "Basic"
        else: return "Minimal"

    def create_strain_id(self, strain_name, breeder_name):
        combined = f"{strain_name}-{breeder_name}-seedsman".lower()
        combined = re.sub(r'[^a-z0-9-]', '', combined.replace(' ', '-'))
        return combined[:50]

    def collect_strain_urls(self):
        """Phase 1: Collect all strain URLs from Seedsman breeder pages (path.txt)"""
        print("PHASE 1: Collecting Seedsman strain URLs from breeder pages...")
        
        # Use exact URLs from path.txt
        base_url = "https://www.seedsman.com/us-en/cannabis-seed-breeders/seedsman"
        strain_urls = []
        
        # Crawl pages 1-11 as specified in path.txt
        for page in range(1, 12):
            if page == 1:
                url = base_url
            else:
                url = f"{base_url}?page={page}"
            
            print(f"Scraping page {page}: {url}")
            
            html = self._brightdata_request(url)
            if not html:
                print(f"Failed to fetch page {page}: {url}")
                continue
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract product URLs from the page
            page_urls = []
            all_links = soup.find_all('a', href=True)
            print(f"    Total links found: {len(all_links)}")
            
            for link in all_links:
                href = link.get('href')
                if href:
                    # More flexible product URL detection
                    if (href.startswith('/us-en/') and 
                        'cannabis-seed-breeders' not in href and
                        'category' not in href and
                        'search' not in href and
                        'page=' not in href and
                        len(href.split('/')) >= 4):
                        
                        full_url = f"https://www.seedsman.com{href}"
                        
                        # Clean URL parameters but keep essential ones
                        if '?' in full_url and 'store=' not in full_url:
                            full_url = full_url.split('?')[0]
                        
                        page_urls.append(full_url)
            
            # Debug: show some example URLs found
            if page_urls:
                print(f"    Example URLs: {page_urls[:3]}")
            
            unique_page_urls = list(set(page_urls))
            strain_urls.extend(unique_page_urls)
            print(f"  Found {len(unique_page_urls)} product URLs on page {page}")
            
            # If no URLs found, try alternative extraction
            if len(unique_page_urls) == 0:
                print(f"    No URLs with standard pattern, trying alternative extraction...")
                alt_urls = []
                for link in all_links:
                    href = link.get('href')
                    if href and ('seeds' in href.lower() or 'strain' in href.lower()):
                        if href.startswith('/') and len(href) > 10:
                            alt_urls.append(f"https://www.seedsman.com{href}")
                
                if alt_urls:
                    print(f"    Alternative extraction found {len(alt_urls)} URLs")
                    strain_urls.extend(alt_urls[:10])  # Limit to 10 for testing
            
            time.sleep(2)  # Increased delay for Seedsman
        
        unique_urls = list(set(strain_urls))
        print(f"Total unique strain URLs found: {len(unique_urls)}")
        return unique_urls

    def scrape_strain_details(self, strain_urls):
        """Phase 2: Extract detailed strain data using 4-method approach"""
        print(f"\nPHASE 2: Scraping {len(strain_urls)} strains with 4-method extraction...")
        
        for i, url in enumerate(strain_urls, 1):
            self.total_processed += 1
            print(f"\n[{i}/{len(strain_urls)}] {url}")
            
            html = self._brightdata_request(url)
            if html:
                strain_data = self.apply_4_methods(html, url)
                
                # Quality validation (minimum 20% score)
                if strain_data['data_completeness_score'] >= 20:
                    try:
                        # Convert Decimal for DynamoDB
                        strain_data['data_completeness_score'] = Decimal(str(strain_data['data_completeness_score']))
                        
                        self.table.put_item(Item=strain_data)
                        self.successful_extractions += 1
                        
                        print(f"  SUCCESS: {strain_data.get('strain_name', 'Unknown')} - {strain_data.get('breeder_name', 'Unknown Breeder')}")
                        print(f"     Quality: {strain_data['quality_tier']} ({float(strain_data['data_completeness_score']):.1f}%)")
                        print(f"     Methods: {', '.join(strain_data['extraction_methods_used'])}")
                        
                        # Show key Seedsman fields if present
                        if strain_data.get('thc_content'):
                            print(f"     THC: {strain_data['thc_content']}")
                        if strain_data.get('yield_indoor'):
                            print(f"     Yield Indoor: {strain_data['yield_indoor']}")
                        
                    except Exception as e:
                        print(f"  STORAGE FAILED: {e}")
                else:
                    print(f"  LOW QUALITY: {strain_data['data_completeness_score']:.1f}% - skipped")
            else:
                print(f"  FETCH FAILED")
            
            time.sleep(1)

    def print_final_stats(self):
        """Print comprehensive scraping statistics"""
        success_rate = (self.successful_extractions / self.total_processed * 100) if self.total_processed > 0 else 0
        
        print(f"\nSEEDSMAN ENHANCED SCRAPING COMPLETE!")
        print(f"THE BEAR HAS BEEN CONQUERED!")
        print(f"FINAL STATISTICS:")
        print(f"   Total Processed: {self.total_processed}")
        print(f"   Successful: {self.successful_extractions}")
        print(f"   Success Rate: {success_rate:.1f}%")
        print(f"\nMETHOD USAGE:")
        for method, count in self.method_stats.items():
            print(f"   {method.title()}: {count} strains")
        print(f"\nCost: ~${self.total_processed * 0.0015:.2f} (BrightData)")
        print(f"Unique Features: Comprehensive specifications, breeder attribution, multi-climate data")

def main():
    scraper = SeedsmanEnhanced4MethodScraper()
    
    # Phase 1: Collect URLs from breeder pages
    strain_urls = scraper.collect_strain_urls()
    
    if not strain_urls:
        print("No strain URLs found. Exiting.")
        return
    
    # Phase 2: Scrape details
    scraper.scrape_strain_details(strain_urls)
    
    # Final statistics
    scraper.print_final_stats()

if __name__ == "__main__":
    print("SEEDSMAN - ENHANCED 4-METHOD SCRAPER")
    print("CONQUERING THE BEAR")
    print("Target: 1000+ strains with 95%+ success rate")
    print("Methods: Structured + Description + Patterns + Fallback")
    print("Strategy: Breeder page crawling + 4-method extraction")
    print("Expected: 98% data completeness (highest of all seed banks)")
    print("\n" + "="*60)
    
    main()