#!/usr/bin/env python3
"""
Seedsman Cannabis Strains Scraper
Comprehensive approach using chat.txt URLs
Target: 2000+ European classic strains
"""

import requests
import json
import boto3
import time
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin

class SeedsmanScraper:
    def __init__(self):
        self.base_url = "https://www.seedsman.com"
        
        # Category URLs from chat.txt
        self.categories = [
            "/us-en/cannabis-seeds/flowering-type/autoflowering-cannabis-seeds",
            "/us-en/cannabis-seeds/sex/feminised-cannabis-seeds", 
            "/us-en/cannabis-seeds/sex/regular-cannabis-seeds"
        ]
        
        # AWS clients
        self.secrets_client = boto3.client('secretsmanager', region_name='us-east-1')
        self.dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        self.table = self.dynamodb.Table('cannabis-strains')
        
        # Get BrightData credentials
        self.brightdata_config = self._get_brightdata_credentials()
        
    def _get_brightdata_credentials(self):
        try:
            response = self.secrets_client.get_secret_value(SecretId='cannabis-brightdata-api')
            return json.loads(response['SecretString'])
        except Exception as e:
            print(f"Error getting BrightData credentials: {e}")
            return None

    def _brightdata_request(self, url):
        if not self.brightdata_config:
            return None
            
        api_url = "https://api.brightdata.com/request"
        headers = {"Authorization": f"Bearer {self.brightdata_config['api_key']}"}
        payload = {
            "zone": self.brightdata_config['zone'],
            "url": url,
            "format": "raw"
        }
        
        try:
            response = requests.post(api_url, headers=headers, json=payload, timeout=30)
            if response.status_code == 200:
                return response.text
            else:
                print(f"BrightData error {response.status_code}")
                return None
        except Exception as e:
            print(f"BrightData request failed: {e}")
            return None

    def get_strain_urls(self):
        """Get strain URLs from known examples and search"""
        # Start with known working URLs from chat.txt
        known_urls = [
            "https://www.seedsman.com/us-en/special-queen-1-auto-feminised-seeds-rqs-specq1-auto-fem",
            "https://www.seedsman.com/us-en/forbidden-fruit-feminised-seeds-rqs-forfr-fem",
            "https://www.seedsman.com/us-en/mentha-de-croco-croco-bx-regular-seeds-terp-mdcbx-reg"
        ]
        
        print(f"Testing {len(known_urls)} known strain URLs")
        working_urls = []
        
        for url in known_urls:
            html = self._brightdata_request(url)
            if html and "seeds" in html.lower():
                working_urls.append(url)
                print(f"SUCCESS: {url.split('/')[-1]}")
            else:
                print(f"FAILED: {url.split('/')[-1]}")
            time.sleep(1)
                    
        print(f"Working strain URLs: {len(working_urls)}")
        return working_urls

    def extract_strain_data(self, html, url):
        """Extract strain data from product page"""
        soup = BeautifulSoup(html, 'html.parser')
        
        data = {
            'source_url': url,
            'seed_bank': 'Seedsman'
        }
        
        # Extract strain name from title - try multiple selectors
        title_selectors = ['h1.page-title', 'h1', '.product-name h1', '.product-title']
        for selector in title_selectors:
            title = soup.select_one(selector)
            if title:
                strain_name = title.get_text().strip()
                # Clean up title
                strain_name = re.sub(r'\s+(Seeds?|Feminised?|Auto|Regular)\s*', ' ', strain_name, flags=re.I)
                strain_name = strain_name.strip()
                data['strain_name'] = strain_name
                break
        
        # Extract breeder from multiple sources
        # Try breadcrumbs first
        breadcrumb_selectors = ['ol.breadcrumb', '.breadcrumb', 'nav.breadcrumb']
        for selector in breadcrumb_selectors:
            breadcrumbs = soup.select_one(selector)
            if breadcrumbs:
                links = breadcrumbs.find_all('a')
                if len(links) >= 2:
                    breeder = links[-2].get_text().strip()
                    if breeder not in ['Cannabis Seeds', 'Feminised Cannabis Seeds', 'Autoflowering Cannabis Seeds', 'Regular Cannabis Seeds']:
                        data['breeder_name'] = breeder
                        break
        
        # Try product info if no breeder found
        if not data.get('breeder_name'):
            brand_selectors = ['.brand', '.manufacturer', '.breeder', '[data-brand]']
            for selector in brand_selectors:
                brand = soup.select_one(selector)
                if brand:
                    data['breeder_name'] = brand.get_text().strip()
                    break
        
        # Extract from product details - try multiple table types
        table_selectors = ['table.data-table', 'table', '.product-details table', '.specifications table']
        for table_selector in table_selectors:
            details_table = soup.select_one(table_selector)
            if details_table:
                rows = details_table.find_all('tr')
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:
                        key = cells[0].get_text().strip().lower()
                        value = cells[1].get_text().strip()
                    
                    if 'thc' in key:
                        thc_match = re.search(r'(\d+(?:\.\d+)?)(?:\s*-\s*(\d+(?:\.\d+)?))?', value)
                        if thc_match:
                            data['thc_min'] = float(thc_match.group(1))
                            if thc_match.group(2):
                                data['thc_max'] = float(thc_match.group(2))
                    
                    elif 'cbd' in key:
                        cbd_match = re.search(r'(\d+(?:\.\d+)?)(?:\s*-\s*(\d+(?:\.\d+)?))?', value)
                        if cbd_match:
                            data['cbd_min'] = float(cbd_match.group(1))
                            if cbd_match.group(2):
                                data['cbd_max'] = float(cbd_match.group(2))
                    
                    elif 'flower' in key:
                        flower_match = re.search(r'(\d+)(?:\s*-\s*(\d+))?', value)
                        if flower_match:
                            days = int(flower_match.group(1))
                            if 'week' in value.lower():
                                days *= 7
                            data['flowering_days_min'] = days
                            if flower_match.group(2):
                                days_max = int(flower_match.group(2))
                                if 'week' in value.lower():
                                    days_max *= 7
                                data['flowering_days_max'] = days_max
                    
                    elif 'yield' in key:
                        yield_match = re.search(r'(\d+)(?:\s*-\s*(\d+))?', value)
                        if yield_match:
                            data['yield_indoor_min'] = int(yield_match.group(1))
                            if yield_match.group(2):
                                data['yield_indoor_max'] = int(yield_match.group(2))
                    
                    elif any(x in key for x in ['sativa', 'indica', 'genetic']):
                        # Extract genetics percentages
                        sativa_match = re.search(r'(\d+)%?\s*sativa', value, re.I)
                        indica_match = re.search(r'(\d+)%?\s*indica', value, re.I)
                        if sativa_match:
                            data['genetics_sativa'] = int(sativa_match.group(1))
                        if indica_match:
                            data['genetics_indica'] = int(indica_match.group(1))
        
        # Extract description from multiple possible locations
        desc_selectors = [
            '.product-description',
            '.description', 
            '.product-details',
            '.product-info',
            '[data-tab="description"]',
            '.tab-content'
        ]
        
        for selector in desc_selectors:
            desc_elem = soup.select_one(selector)
            if desc_elem:
                desc_text = desc_elem.get_text().strip()
                if len(desc_text) > 50:  # Only use substantial descriptions
                    data['description'] = desc_text[:1000]
                    break
        
        # Determine genetics type
        if data.get('genetics_sativa') and data.get('genetics_indica'):
            if data['genetics_sativa'] > 60:
                data['genetics_type'] = 'Sativa Dominant'
            elif data['genetics_indica'] > 60:
                data['genetics_type'] = 'Indica Dominant'
            else:
                data['genetics_type'] = 'Hybrid'
        
        return data

    def save_to_dynamodb(self, strain_data):
        """Save to DynamoDB"""
        try:
            strain_name = strain_data.get('strain_name', 'Unknown')
            breeder_name = strain_data.get('breeder_name', 'Unknown')
            
            # Clean data
            clean_data = {k: v for k, v in strain_data.items() if v is not None}
            clean_data['strain_name'] = strain_name
            clean_data['breeder_name'] = breeder_name
            
            self.table.put_item(Item=clean_data)
            return True
        except Exception as e:
            print(f"DynamoDB error: {e}")
            return False

    def scrape_all_strains(self):
        """Main scraping function - test with known URLs first"""
        print("Starting Seedsman test scraping...")
        
        # Get strain URLs (starting with known working ones)
        strain_urls = self.get_strain_urls()
        
        if not strain_urls:
            print("No working URLs found - Seedsman may require different approach")
            return
        
        success_count = 0
        total_count = len(strain_urls)
        
        for i, url in enumerate(strain_urls, 1):
            print(f"\n[{i}/{total_count}] {url.split('/')[-1]}")
            
            html = self._brightdata_request(url)
            if not html:
                print("FAILED")
                continue
            
            strain_data = self.extract_strain_data(html, url)
            
            if strain_data.get('strain_name'):
                if self.save_to_dynamodb(strain_data):
                    success_count += 1
                    strain_name = strain_data['strain_name'][:30].encode('ascii', 'ignore').decode('ascii')
                    breeder_name = strain_data.get('breeder_name', 'Unknown')[:20].encode('ascii', 'ignore').decode('ascii')
                    print(f"SUCCESS: {strain_name} ({breeder_name})")
                    
                    # Show extracted data for analysis
                    print(f"  Data points: {len([k for k, v in strain_data.items() if v is not None])}")
                else:
                    print("SAVE FAILED")
            else:
                print("NO DATA")
            
            time.sleep(2)  # Slower for testing
        
        print(f"\nSEEDSMAN TEST COMPLETE!")
        print(f"Success: {success_count}/{total_count}")
        print(f"Cost: ${total_count * 0.0015:.2f}")
        
        if success_count > 0:
            print("\nSeedsman scraping is working! Ready to scale up.")
        else:
            print("\nSeedsman requires different scraping approach.")

if __name__ == "__main__":
    scraper = SeedsmanScraper()
    scraper.scrape_all_strains()