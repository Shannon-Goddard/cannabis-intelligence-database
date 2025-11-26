#!/usr/bin/env python3
"""
Multiverse Beans - Enhanced 4-Method Scraper
Based on proven North Atlantic (97.8%) methodology
Target: 1,200+ strains (857 photoperiods + 400+ autoflowers) with 95%+ success rate
"""

import json
import boto3
import requests
import time
import re
from bs4 import BeautifulSoup
from decimal import Decimal
from datetime import datetime

class MultiverseEnhanced4MethodScraper:
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
        """Method 1: Extract from Multiverse's attribute structure"""
        data = {}
        
        # Multiverse product attributes (.attribute-row structure)
        attributes = soup.find_all('div', class_='attribute-row')
        for attr in attributes:
            label = attr.find('span', class_='attribute-label')
            value = attr.find('span', class_='attribute-value')
            if label and value:
                field_map = {
                    'Flowering Time': 'flowering_time',
                    'Plant Size': 'plant_height',
                    'Yield': 'yield',
                    'THC Content': 'thc_content',
                    'Effects': 'effects',
                    'Flavors': 'flavors',
                    'Genetics': 'genetics',
                    'Breeder': 'breeder_name',
                    'Seed Type': 'seed_type',
                    'Growth Type': 'growth_type'
                }
                label_text = label.get_text().strip().rstrip(':')
                if label_text in field_map:
                    data[field_map[label_text]] = value.get_text().strip()
        
        return data

    def method2_description_mining(self, soup, url):
        """Method 2: Mine product description with autoflower-specific patterns"""
        data = {}
        
        # Find product description
        description = soup.find('div', class_='product-description')
        if not description:
            description = soup.find('div', class_='woocommerce-product-details__short-description')
        if not description:
            description = soup.find('div', id='tab-description')
            
        if description:
            desc_text = description.get_text()
            data['about_info'] = desc_text.strip()
            
            # Autoflower-specific patterns
            patterns = {
                'thc_content': r'THC[:\s]*([0-9.-]+%?(?:\s*-\s*[0-9.-]+%?)?)',
                'cbd_content': r'CBD[:\s]*([0-9.-]+%?(?:\s*-\s*[0-9.-]+%?)?)',
                'flowering_time': r'(?:flowering|flower|harvest|ready)[:\s]*([0-9-]+\s*(?:days?|weeks?))',
                'genetics': r'(?:genetics|cross|lineage)[:\s]*([^.]+?)(?:\.|$)',
                'effects': r'effects?[:\s]*([^.]+?)(?:\.|$)',
                'yield': r'yield[:\s]*([^.]+?)(?:\.|$)',
                'height': r'(?:height|size)[:\s]*([^.]+?)(?:\.|$)',
                'autoflower': r'(auto|autoflower|automatic)',
                'mephisto': r'(mephisto|night owl|illuminauto)',
                'limited': r'(limited|exclusive|drop|artisanal)'
            }
            
            for key, pattern in patterns.items():
                match = re.search(pattern, desc_text, re.IGNORECASE)
                if match:
                    if key in ['autoflower', 'mephisto', 'limited']:
                        data[f'{key}_indicator'] = True
                    else:
                        data[key] = match.group(1).strip()
        
        return data

    def method3_advanced_patterns(self, soup, url):
        """Method 3: Advanced Multiverse-specific patterns"""
        data = {}
        
        # Extract strain name from product title
        h1_tag = soup.find('h1', class_='product_title')
        if not h1_tag:
            h1_tag = soup.find('h1')
        if h1_tag:
            strain_name = h1_tag.get_text().strip()
            # Clean Multiverse naming patterns (remove pack sizes, F2, Auto, etc.)
            strain_name = re.sub(r'\s+', ' ', strain_name)
            strain_name = re.sub(r'\s*-\s*(Auto|Fem|Photo|F[0-9]+)\s*', ' ', strain_name, re.IGNORECASE)
            strain_name = re.sub(r'\s*[0-9]+\s*pack.*$', '', strain_name, re.IGNORECASE)
            strain_name = re.sub(r'\s*(Seeds?|Strain)$', '', strain_name, re.IGNORECASE)
            data['strain_name'] = strain_name.strip()
        
        # Extract breeder from product title or breadcrumbs
        if 'strain_name' in data:
            title_parts = data['strain_name'].split(' - ')
            if len(title_parts) >= 2:
                potential_breeder = title_parts[0].strip()
                # Known Multiverse breeders
                known_breeders = [
                    'Mephisto Genetics', 'Night Owl', 'Cali Connection', 
                    'Ethos Genetics', 'In House Genetics', 'Compound Genetics',
                    'Cannarado Genetics', 'Thug Pug', 'Exotic Genetix'
                ]
                for breeder in known_breeders:
                    if breeder.lower() in potential_breeder.lower():
                        data['breeder_name'] = breeder
                        # Clean strain name
                        data['strain_name'] = ' - '.join(title_parts[1:]).strip()
                        break
        
        # Detect autoflower vs photoperiod from URL or categories
        if '/autoflower/' in url or 'auto' in url.lower():
            data['growth_type'] = 'Autoflower'
        elif '/photoperiod/' in url or 'photo' in url.lower():
            data['growth_type'] = 'Photoperiod'
        
        # Extract from WooCommerce product attributes
        woo_attributes = soup.find('table', class_='woocommerce-product-attributes')
        if woo_attributes:
            rows = woo_attributes.find_all('tr')
            for row in rows:
                label_cell = row.find('th')
                value_cell = row.find('td')
                if label_cell and value_cell:
                    label = label_cell.get_text().strip()
                    value = value_cell.get_text().strip()
                    
                    if 'breeder' in label.lower() and not data.get('breeder_name'):
                        data['breeder_name'] = value
                    elif 'genetics' in label.lower():
                        data['genetics'] = value
                    elif 'flowering' in label.lower():
                        data['flowering_time'] = value
        
        return data

    def method4_fallback_extraction(self, soup, url):
        """Method 4: Universal fallback extraction"""
        data = {}
        
        # Extract strain name from URL if not found
        if 'strain_name' not in data:
            path_parts = url.split('/')
            for part in reversed(path_parts):
                if part and 'product' not in part and len(part) > 3:
                    strain_name = part.replace('-', ' ').title()
                    # Clean common suffixes
                    strain_name = re.sub(r'\s+(Seeds?|Feminized|Auto|F[0-9]+|Pack)$', '', strain_name, re.IGNORECASE)
                    data['strain_name'] = strain_name.strip()
                    break
        
        # Meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and not data.get('about_info'):
            data['about_info'] = meta_desc.get('content', '')
        
        # Page title parsing
        title = soup.find('title')
        if title:
            title_text = title.get_text().strip()
            if not data.get('strain_name'):
                # Extract strain name from title
                title_parts = title_text.split(' - ')
                if title_parts:
                    potential_strain = title_parts[0].strip()
                    potential_strain = re.sub(r'\s+(Seeds?|Feminized|Auto)$', '', potential_strain, re.IGNORECASE)
                    data['strain_name'] = potential_strain
        
        # Default values for Multiverse
        if not data.get('seed_type'):
            data['seed_type'] = 'Feminized'  # Most Multiverse strains are feminized
        
        return data

    def apply_4_methods(self, html_content, url):
        """Apply all 4 extraction methods"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        strain_data = {
            'seed_bank': 'Multiverse Beans',
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
        breeder_name = strain_data.get('breeder_name', 'Multiverse Beans')
        strain_data['strain_id'] = self.create_strain_id(strain_name, breeder_name)
        
        # Add timestamps
        now = datetime.utcnow().isoformat() + 'Z'
        strain_data['created_at'] = now
        strain_data['updated_at'] = now
        
        return strain_data

    def calculate_quality_score(self, strain_data):
        """Calculate weighted quality score"""
        field_weights = {
            'strain_name': 10, 'breeder_name': 10,
            'genetics': 8, 'flowering_time': 8, 'growth_type': 8,
            'yield': 6, 'plant_height': 6, 'thc_content': 6,
            'effects': 5, 'seed_type': 4, 'about_info': 4,
            'flavors': 4, 'autoflower_indicator': 3
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
        combined = f"{strain_name}-{breeder_name}-multiverse".lower()
        combined = re.sub(r'[^a-z0-9-]', '', combined.replace(' ', '-'))
        return combined[:50]

    def collect_strain_urls(self):
        """Phase 1: Collect all strain URLs from Multiverse catalogs"""
        print("PHASE 1: Collecting Multiverse strain URLs from autoflower and photoperiod catalogs...")
        
        catalog_urls = [
            "https://multiversebeans.com/flowering-type/autoflower/",
            "https://multiversebeans.com/flowering-type/photoperiod/"
        ]
        
        all_urls = []
        
        for catalog_url in catalog_urls:
            print(f"\nScraping catalog: {catalog_url}")
            page = 1
            
            while True:
                page_url = f"{catalog_url}page/{page}/" if page > 1 else catalog_url
                print(f"  Page {page}: {page_url}")
                
                html = self._brightdata_request(page_url)
                if html:
                    soup = BeautifulSoup(html, 'html.parser')
                    urls = []
                    
                    # Extract product URLs (WooCommerce structure)
                    for link in soup.find_all('a', href=True):
                        href = link.get('href')
                        if href and '/product/' in href and href not in all_urls:
                            urls.append(href)
                    
                    if urls:
                        all_urls.extend(urls)
                        print(f"    Found {len(urls)} strains")
                        page += 1
                    else:
                        print(f"    No strains - end of catalog")
                        break
                else:
                    print(f"    Failed to fetch")
                    break
                
                time.sleep(1)
        
        unique_urls = list(set(all_urls))
        print(f"\nTotal unique strains found: {len(unique_urls)}")
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
                        
                        print(f"  SUCCESS: {strain_data.get('strain_name', 'Unknown')} - {strain_data.get('breeder_name', 'Unknown')}")
                        print(f"     Quality: {strain_data['quality_tier']} ({float(strain_data['data_completeness_score']):.1f}%)")
                        print(f"     Methods: {', '.join(strain_data['extraction_methods_used'])}")
                        
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
        
        print(f"\nMULTIVERSE BEANS ENHANCED SCRAPING COMPLETE!")
        print(f"FINAL STATISTICS:")
        print(f"   Total Processed: {self.total_processed}")
        print(f"   Successful: {self.successful_extractions}")
        print(f"   Success Rate: {success_rate:.1f}%")
        print(f"\nMETHOD USAGE:")
        for method, count in self.method_stats.items():
            print(f"   {method.title()}: {count} strains")
        print(f"\nCost: ~${self.total_processed * 0.0015:.2f} (BrightData)")

def main():
    scraper = MultiverseEnhanced4MethodScraper()
    
    # Phase 1: Collect URLs
    strain_urls = scraper.collect_strain_urls()
    
    # Phase 2: Scrape details
    scraper.scrape_strain_details(strain_urls)
    
    # Final statistics
    scraper.print_final_stats()

if __name__ == "__main__":
    print("MULTIVERSE BEANS - ENHANCED 4-METHOD SCRAPER")
    print("Target: 1,200+ strains (857 photoperiods + 400+ autoflowers) with 95%+ success rate")
    print("Methods: Structured + Description + Patterns + Fallback")
    print("Based on proven North Atlantic (97.8%) methodology")
    print("\n" + "="*60)
    
    main()