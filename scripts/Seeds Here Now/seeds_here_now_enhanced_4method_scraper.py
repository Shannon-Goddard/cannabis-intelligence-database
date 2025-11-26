#!/usr/bin/env python3
"""
Seeds Here Now - Enhanced 4-Method Scraper
Target: 200+ strains with 95%+ success rate
Hardcoded: seed_bank as 'Seeds Here Now'
"""

import json
import boto3
import requests
import time
import re
from bs4 import BeautifulSoup
from decimal import Decimal
from datetime import datetime

class SeedsHereNowEnhanced4MethodScraper:
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
        """Method 1: Seeds Here Now card-based layout extraction"""
        data = {}
        
        # Extract info cards
        cards = soup.find_all('div', class_='add-info-card')
        for card in cards:
            title_elem = card.find('h3', class_='add-info-title')
            desc_elem = card.find('p', class_='add-info-description')
            
            if title_elem and desc_elem:
                title = title_elem.get_text().strip()
                description = desc_elem.get_text().strip()
                
                # Map Seeds Here Now fields to our schema
                field_map = {
                    'Indica / Sativa': 'indica_sativa',
                    'THC %': 'thc_percentage',
                    'Aroma': 'aroma',
                    'Flower Time': 'flowering_time',
                    'Yield': 'yield',
                    'Terpenes': 'terpenes',
                    'Effects': 'effects',
                    'Best Use': 'best_use'
                }
                
                if title in field_map and description:
                    data[field_map[title]] = description
        
        return data

    def method2_description_mining(self, soup, url):
        """Method 2: Mine Seeds Here Now product descriptions and grow tips"""
        data = {}
        
        # Look for grow tips and product descriptions
        desc_selectors = [
            'div.grow-tips',
            'div.product-description',
            'div.strain-info',
            'div.description'
        ]
        
        about_parts = []
        for selector in desc_selectors:
            elements = soup.select(selector)
            for element in elements:
                text = element.get_text().strip()
                if text and len(text) > 50:
                    about_parts.append(text)
        
        if about_parts:
            data['about_info'] = ' '.join(about_parts)
            
            # Extract patterns from descriptions
            desc_text = data['about_info']
            patterns = {
                'genetics_pattern': r'(?:genetics|lineage|cross|bred from)[:\s]*([^.]+?)(?:\.|$)',
                'breeder_pattern': r'(?:breeder|bred by|genetics by)[:\s]*([^.]+?)(?:\.|$)',
                'flowering_pattern': r'(?:flower|bloom)[s]?\s+(?:in|for|after)\s+([^.]+?)(?:\.|$)',
                'yield_pattern': r'(?:yield|produce)[s]?\s+(?:up to|around|about)?\s*([^.]+?)(?:\.|$)'
            }
            
            for key, pattern in patterns.items():
                match = re.search(pattern, desc_text, re.IGNORECASE)
                if match:
                    data[key] = match.group(1).strip()
        
        return data

    def method3_advanced_patterns(self, soup, url):
        """Method 3: Seeds Here Now specific patterns"""
        data = {}
        
        # Extract strain name from product title
        title_selectors = ['h1', '.product-title', '.strain-title']
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                strain_name = title_elem.get_text().strip()
                # Clean Seeds Here Now naming patterns
                strain_name = re.sub(r'\s+', ' ', strain_name)
                strain_name = re.sub(r'\s*(Feminized|Auto|Autoflower|Seeds?|Regular)\s*', ' ', strain_name, re.IGNORECASE)
                data['strain_name'] = strain_name.strip()
                break
        
        # Seeds Here Now is the seed bank
        data['seed_bank'] = 'Seeds Here Now'
        
        # Extract breeder from URL or product info
        url_parts = url.split('/')
        for part in url_parts:
            if part and len(part) > 3:
                # Look for breeder patterns in URL
                breeder_patterns = [
                    r'(.+)-seeds?$',
                    r'(.+)-genetics?$',
                    r'(.+)-(?:fem|auto|regular)',
                ]
                for pattern in breeder_patterns:
                    match = re.search(pattern, part, re.IGNORECASE)
                    if match:
                        potential_breeder = match.group(1).replace('-', ' ').title()
                        if len(potential_breeder) > 3:
                            data['breeder_name'] = potential_breeder
                            break
        
        # Detect seed type from URL or content
        url_lower = url.lower()
        if 'autoflower' in url_lower or 'auto' in url_lower:
            data['seed_type'] = 'Feminized'
            data['growth_type'] = 'Autoflower'
        elif 'feminized' in url_lower or 'fem' in url_lower:
            data['seed_type'] = 'Feminized'
            data['growth_type'] = 'Photoperiod'
        elif 'regular' in url_lower:
            data['seed_type'] = 'Regular'
            data['growth_type'] = 'Photoperiod'
        
        # Extract price information
        price_selectors = ['.price', '.product-price', '[data-price]']
        for selector in price_selectors:
            price_elem = soup.select_one(selector)
            if price_elem:
                price_text = price_elem.get_text().strip()
                price_match = re.search(r'[\$€£]?([0-9]+\.?[0-9]*)', price_text)
                if price_match:
                    data['price'] = price_match.group(1)
                break
        
        # Check availability
        if soup.find(string=re.compile(r'out of stock|sold out|unavailable', re.IGNORECASE)):
            data['availability'] = 'OutOfStock'
        else:
            data['availability'] = 'InStock'
        
        return data

    def method4_fallback_extraction(self, soup, url):
        """Method 4: Universal fallback for Seeds Here Now"""
        data = {}
        
        # Extract strain name from URL if not found
        if 'strain_name' not in data:
            path_parts = url.split('/')
            for part in reversed(path_parts):
                if part and 'shop' in url and len(part) > 5:
                    strain_name = part.replace('-', ' ').title()
                    # Clean common suffixes
                    strain_name = re.sub(r'\s+(Auto|Autoflower|Fem|Feminized|Regular|Seeds?)\s*', ' ', strain_name, re.IGNORECASE)
                    strain_name = re.sub(r'\s+\d+pk$', '', strain_name)  # Remove pack size
                    data['strain_name'] = strain_name.strip()
                    break
        
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
        """Apply all 4 extraction methods with Seeds Here Now hardcoded values"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        strain_data = {
            'seed_bank': 'Seeds Here Now',
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
        
        # Calculate quality score
        strain_data['data_completeness_score'] = self.calculate_quality_score(strain_data)
        strain_data['quality_tier'] = self.determine_quality_tier(strain_data['data_completeness_score'])
        strain_data['field_count'] = len([v for v in strain_data.values() if v])
        
        # Create strain ID
        strain_name = strain_data.get('strain_name', 'Unknown')
        breeder_name = strain_data.get('breeder_name', 'Unknown')
        strain_data['strain_id'] = self.create_strain_id(strain_name, breeder_name)
        
        # Add timestamps
        now = datetime.utcnow().isoformat() + 'Z'
        strain_data['created_at'] = now
        strain_data['updated_at'] = now
        
        return strain_data

    def calculate_quality_score(self, strain_data):
        """Calculate weighted quality score optimized for Seeds Here Now"""
        field_weights = {
            # Core fields (required)
            'strain_name': 10,
            'seed_bank': 10,
            
            # Seeds Here Now strengths
            'breeder_name': 9,               # Breeder attribution
            'thc_percentage': 9,             # THC ranges (22% to 26%)
            'terpenes': 8,                   # Specific terpenes
            'effects': 8,                    # Multiple effects
            'aroma': 7,                      # Aroma profiles
            'flowering_time': 8,             # Flower time
            'yield': 7,                      # Yield descriptions
            'best_use': 6,                   # Usage recommendations
            'indica_sativa': 7,              # Genetic ratios
            
            # Seed classification
            'seed_type': 6,                  # Feminized/Regular
            'growth_type': 6,                # Auto/Photo classification
            
            # Additional info
            'about_info': 6,                 # Grow tips and descriptions
            'availability': 3,               # Stock status
            'price': 3                       # Pricing data
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
        combined = f"{strain_name}-{breeder_name}-shn".lower()
        combined = re.sub(r'[^a-z0-9-]', '', combined.replace(' ', '-'))
        return combined[:50]

    def collect_strain_urls(self):
        """Phase 1: Collect all strain URLs from Seeds Here Now categories"""
        print("PHASE 1: Collecting Seeds Here Now strain URLs...")
        
        category_urls = [
            "https://seedsherenow.com/product-category/feminized-cannabis-seeds/",
            "https://seedsherenow.com/product-category/regular-cannabis-seeds/",
            "https://seedsherenow.com/product-category/autoflower-cannabis-seeds/"
        ]
        
        strain_urls = []
        
        for category_url in category_urls:
            print(f"Scraping category: {category_url}")
            
            html = self._brightdata_request(category_url)
            if not html:
                print(f"Failed to fetch category: {category_url}")
                continue
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract product URLs
            for link in soup.find_all('a', href=True):
                href = link.get('href')
                if href and '/shop/' in href:
                    if href.startswith('/'):
                        full_url = f"https://seedsherenow.com{href}"
                    else:
                        full_url = href
                    strain_urls.append(full_url)
        
        unique_urls = list(set(strain_urls))  # Remove duplicates
        print(f"Total unique strains found: {len(unique_urls)}")
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
                        
                        # Show key Seeds Here Now fields if present
                        if strain_data.get('thc_percentage'):
                            print(f"     THC: {strain_data['thc_percentage']}")
                        if strain_data.get('terpenes'):
                            print(f"     Terpenes: {strain_data['terpenes']}")
                        
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
        
        print(f"\nSEEDS HERE NOW ENHANCED SCRAPING COMPLETE!")
        print(f"FINAL STATISTICS:")
        print(f"   Total Processed: {self.total_processed}")
        print(f"   Successful: {self.successful_extractions}")
        print(f"   Success Rate: {success_rate:.1f}%")
        print(f"\nMETHOD USAGE:")
        for method, count in self.method_stats.items():
            print(f"   {method.title()}: {count} strains")
        print(f"\nCost: ~${self.total_processed * 0.0015:.2f} (BrightData)")
        print(f"Unique Features: Card-based layout, THC ranges, terpene profiles")

def main():
    scraper = SeedsHereNowEnhanced4MethodScraper()
    
    # Phase 1: Collect URLs
    strain_urls = scraper.collect_strain_urls()
    
    if not strain_urls:
        print("No strain URLs found. Exiting.")
        return
    
    # Phase 2: Scrape details
    scraper.scrape_strain_details(strain_urls)
    
    # Final statistics
    scraper.print_final_stats()

if __name__ == "__main__":
    print("SEEDS HERE NOW - ENHANCED 4-METHOD SCRAPER")
    print("Target: 200+ strains with 95%+ success rate")
    print("Methods: Structured + Description + Patterns + Fallback")
    print("Hardcoded: seed_bank as 'Seeds Here Now'")
    print("Specializing in card-based data extraction and breeder attribution")
    print("\n" + "="*60)
    
    main()