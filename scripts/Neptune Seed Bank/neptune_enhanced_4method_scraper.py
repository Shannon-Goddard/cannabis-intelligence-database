#!/usr/bin/env python3
"""
Neptune Seed Bank - Enhanced 4-Method Scraper
Based on North Atlantic's 100% success rate methodology
Target: 2,500+ strains with 95%+ success rate
"""

import json
import boto3
import requests
import time
import re
from bs4 import BeautifulSoup
from decimal import Decimal
from datetime import datetime

class NeptuneEnhanced4MethodScraper:
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
        """Method 1: Extract from WooCommerce attributes table"""
        data = {}
        
        # Neptune's WooCommerce product attributes table
        table = soup.find('table', class_='woocommerce-product-attributes')
        if table:
            for row in table.find_all('tr', class_='woocommerce-product-attributes-item'):
                label = row.find('th', class_='woocommerce-product-attributes-item__label')
                value = row.find('td', class_='woocommerce-product-attributes-item__value')
                
                if label and value:
                    label_text = label.get_text().strip()
                    
                    # Extract value, skip #REF! errors
                    value_p = value.find('p')
                    if value_p and value_p.get_text().strip() != '#REF!':
                        value_text = value_p.get_text().strip()
                        
                        # Neptune-specific field mapping
                        field_map = {
                            'Yield': 'yield',
                            'Harvest Time': 'flowering_time',
                            'Cannabis Type': 'strain_type',
                            'Dominant Terpene': 'dominant_terpene',
                            'Feelings': 'feelings',  # UNIQUE TO NEPTUNE
                            'Flowering Type': 'seed_type',
                            'Grow Difficulty': 'grow_difficulty',  # UNIQUE TO NEPTUNE
                            'Height': 'plant_height',
                            'Terpene Profile': 'terpenes'
                        }
                        
                        if label_text in field_map:
                            data[field_map[label_text]] = value_text
        
        # Extract breeder from breeder link
        breeder_link = soup.find('a', class_='breeder-link')
        if breeder_link:
            data['breeder_name'] = breeder_link.get_text().strip()
            
        return data

    def method2_description_mining(self, soup, url):
        """Method 2: Mine product descriptions with regex patterns"""
        data = {}
        
        # Find description content
        description = soup.find('div', id='description')
        if description:
            desc_text = description.get_text()
            data['about_info'] = desc_text.strip()
            
            # Neptune-specific patterns
            patterns = {
                'thc_content': r'THC[:\s]*([0-9.-]+%?(?:\s*-\s*[0-9.-]+%?)?)',
                'cbd_content': r'CBD[:\s]*([0-9.-]+%?(?:\s*-\s*[0-9.-]+%?)?)',
                'flowering_time': r'(?:flowering|flower|harvest)[:\s]*([0-9-]+\s*(?:days?|weeks?))',
                'genetics': r'(?:genetics|cross|lineage)[:\s]*([^.]+?)(?:\.|$)',
                'effects': r'effects?[:\s]*([^.]+?)(?:\.|$)',
                'breeder_name': r'by\s+([A-Za-z\s&]+?)(?:\s|$|\.)'
            }
            
            for key, pattern in patterns.items():
                match = re.search(pattern, desc_text, re.IGNORECASE)
                if match:
                    data[key] = match.group(1).strip()
        
        return data

    def method3_advanced_patterns(self, soup, url):
        """Method 3: Advanced Neptune-specific patterns"""
        data = {}
        
        # Extract strain name from H1
        h1_tag = soup.find('h1')
        if h1_tag:
            strain_name = h1_tag.get_text().strip()
            # Clean Neptune naming patterns
            strain_name = re.sub(r'\s+', ' ', strain_name)
            strain_name = strain_name.replace(' Strain Feminized Seeds by ', ' - ')
            strain_name = strain_name.replace(' Strain ', ' ')
            data['strain_name'] = strain_name
        
        # Extract from attribute items (alternative structure)
        for item in soup.find_all('div', class_='attribute-item'):
            label_elem = item.find('span', class_='attribute-label')
            value_elem = item.find('span', class_='attribute-value')
            
            if label_elem and value_elem:
                label = label_elem.get_text().strip().lower().replace(':', '')
                value = value_elem.get_text().strip()
                
                if 'harvest time' in label or 'flowering time' in label:
                    data['flowering_time'] = value
                elif 'grow difficulty' in label:
                    data['grow_difficulty'] = value
                elif 'height' in label:
                    data['plant_height'] = value
                elif 'pack size' in label:
                    data['pack_size'] = value
                elif 'flowering type' in label:
                    data['seed_type'] = value
                elif 'feelings' in label:
                    data['feelings'] = value  # Neptune unique
                elif 'terpene profile' in label:
                    data['terpenes'] = value
                elif 'cannabis type' in label:
                    data['strain_type'] = value
        
        return data

    def method4_fallback_extraction(self, soup, url):
        """Method 4: Universal fallback extraction"""
        data = {}
        
        # Extract strain name from URL if not found
        if 'strain_name' not in data:
            path_parts = url.split('/')
            for part in reversed(path_parts):
                if part and 'product' not in part and len(part) > 3:
                    data['strain_name'] = part.replace('-', ' ').title()
                    break
        
        # Meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and not data.get('about_info'):
            data['about_info'] = meta_desc.get('content', '')
        
        # Page title parsing for breeder
        title = soup.find('title')
        if title and not data.get('breeder_name'):
            title_text = title.get_text().strip()
            breeder_match = re.search(r'by\s+([A-Za-z\s&]+)', title_text, re.IGNORECASE)
            if breeder_match:
                data['breeder_name'] = breeder_match.group(1).strip()
        
        return data

    def apply_4_methods(self, html_content, url):
        """Apply all 4 extraction methods"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        strain_data = {
            'seed_bank': 'Neptune Seed Bank',
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
        breeder_name = strain_data.get('breeder_name', 'Neptune Seed Bank')
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
            'genetics': 8, 'flowering_time': 8, 'strain_type': 8,
            'feelings': 7, 'grow_difficulty': 7,  # Neptune unique fields
            'yield': 6, 'plant_height': 6, 'terpenes': 6,
            'effects': 5, 'seed_type': 4, 'about_info': 4
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
        combined = f"{strain_name}-{breeder_name}-neptune".lower()
        combined = re.sub(r'[^a-z0-9-]', '', combined.replace(' ', '-'))
        return combined[:50]

    def collect_strain_urls(self):
        """Phase 1: Collect all strain URLs from Neptune"""
        print("PHASE 1: Collecting Neptune strain URLs...")
        
        tag_urls = [
            'https://neptuneseedbank.com/product_tag/feminized/',
            'https://neptuneseedbank.com/product_tag/regular-seeds/',
            'https://neptuneseedbank.com/product_tag/auto-flowering/'
        ]
        
        all_urls = []
        
        for tag_url in tag_urls:
            print(f"\nScraping tag: {tag_url}")
            
            for page in range(1, 51):  # Check up to 50 pages per tag
                page_url = f"{tag_url}page/{page}/"
                print(f"  Page {page}")
                
                html = self._brightdata_request(page_url)
                if html:
                    soup = BeautifulSoup(html, 'html.parser')
                    urls = []
                    
                    # Extract product URLs
                    for link in soup.find_all('a', class_='product-title-link'):
                        href = link.get('href')
                        if href:
                            urls.append(href)
                    
                    if urls:
                        all_urls.extend(urls)
                        print(f"    Found {len(urls)} strains")
                    else:
                        print(f"    No strains - end of tag")
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
        
        print(f"\nNEPTUNE ENHANCED SCRAPING COMPLETE!")
        print(f"FINAL STATISTICS:")
        print(f"   Total Processed: {self.total_processed}")
        print(f"   Successful: {self.successful_extractions}")
        print(f"   Success Rate: {success_rate:.1f}%")
        print(f"\nMETHOD USAGE:")
        for method, count in self.method_stats.items():
            print(f"   {method.title()}: {count} strains")
        print(f"\nCost: ~${self.total_processed * 0.0015:.2f} (BrightData)")

def main():
    scraper = NeptuneEnhanced4MethodScraper()
    
    # Phase 1: Collect URLs
    strain_urls = scraper.collect_strain_urls()
    
    # Phase 2: Scrape details
    scraper.scrape_strain_details(strain_urls)
    
    # Final statistics
    scraper.print_final_stats()

if __name__ == "__main__":
    print("NEPTUNE SEED BANK - ENHANCED 4-METHOD SCRAPER")
    print("Target: 2,500+ strains with 95%+ success rate")
    print("Methods: Structured + Description + Patterns + Fallback")
    print("Preserving Neptune's unique 'feelings' and 'grow_difficulty' fields")
    print("\n" + "="*60)
    
    main()