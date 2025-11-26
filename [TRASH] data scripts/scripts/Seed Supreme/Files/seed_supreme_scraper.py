#!/usr/bin/env python3
"""
Seed Supreme Comprehensive Scraper
Using COMPREHENSIVE_SCRAPING_STRATEGY.md approach
Target: 3000+ strains with maximum data extraction
"""

import requests
import json
import boto3
import time
import re
from bs4 import BeautifulSoup
from decimal import Decimal
from urllib.parse import urljoin, urlparse

class SeedSupremeScraper:
    def __init__(self):
        self.base_url = "https://seedsupreme.com"
        self.session = requests.Session()
        self.dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        self.table = self.dynamodb.Table('cannabis-strains')
        self.brightdata_api = self.get_brightdata_credentials()
        self.scraped_urls = set()
        self.success_count = 0
        self.fail_count = 0
        self.total_cost = 0.0

    def get_brightdata_credentials(self):
        """Get BrightData credentials from AWS Secrets Manager"""
        secrets_client = boto3.client('secretsmanager', region_name='us-east-1')
        try:
            response = secrets_client.get_secret_value(SecretId='cannabis-brightdata-api')
            credentials = json.loads(response['SecretString'])
            return {
                'api_key': credentials['api_key'],
                'zone': credentials['zone']
            }
        except Exception as e:
            print(f"Error getting credentials: {e}")
            return None

    def make_brightdata_request(self, url):
        """Make request through BrightData Web Unlocker API"""
        if not self.brightdata_api:
            return None
        
        api_url = "https://api.brightdata.com/request"
        headers = {"Authorization": f"Bearer {self.brightdata_api['api_key']}"}
        payload = {
            "zone": self.brightdata_api['zone'],
            "url": url,
            "format": "raw"
        }
        
        try:
            response = requests.post(api_url, headers=headers, json=payload, timeout=30)
            if response.status_code == 200:
                self.total_cost += 0.0015  # $1.50 per 1000 requests
                return response.text
            return None
        except Exception as e:
            print(f"BrightData request failed: {e}")
            return None

    def extract_from_tables(self, soup):
        """Method 1: Table parsing (Seeds Here Now approach)"""
        data = {}
        
        # Look for specification tables
        for table in soup.find_all('table'):
            for row in table.find_all('tr'):
                th = row.find('th')
                td = row.find('td')
                if th and td:
                    key = th.get_text().strip().lower()
                    value = td.get_text().strip()
                    
                    if 'breeder' in key:
                        data['breeder_name'] = value
                    elif 'genetics' in key or 'lineage' in key:
                        data['genetics_description'] = value
                    elif 'thc' in key:
                        data['thc_description'] = value
                    elif 'cbd' in key:
                        data['cbd_description'] = value
                    elif 'flowering' in key:
                        data['flowering_description'] = value
                    elif 'yield' in key:
                        data['yield_description'] = value
                    elif 'height' in key:
                        data['height_description'] = value
                    elif 'difficulty' in key:
                        data['difficulty_rating'] = value
                    elif 'effect' in key:
                        data['effects_description'] = value
                    elif 'flavor' in key or 'taste' in key:
                        data['flavor_primary'] = value
                    elif 'aroma' in key:
                        data['aroma_profile'] = value
        
        return data

    def extract_from_descriptions(self, soup):
        """Method 2: Description mining (North Atlantic approach)"""
        data = {}
        
        # Get all text content
        text_content = soup.get_text()
        
        # Specification patterns
        spec_patterns = {
            'pack_size': r'Pack Size[:\s]*([^\\n\\r]+)',
            'genetics': r'Genetics[:\s]*([^\\n\\r]+)',
            'flowering_time': r'Flowering Time[:\s]*([^\\n\\r]+)',
            'thc_content': r'THC[:\s]*([^\\n\\r]+)',
            'cbd_content': r'CBD[:\s]*([^\\n\\r]+)',
            'yield_info': r'Yield[:\s]*([^\\n\\r]+)',
            'height_info': r'Height[:\s]*([^\\n\\r]+)'
        }
        
        for key, pattern in spec_patterns.items():
            match = re.search(pattern, text_content, re.IGNORECASE)
            if match:
                data[key] = match.group(1).strip()
        
        return data

    def extract_with_patterns(self, soup):
        """Method 3: Pattern matching (Multiverse approach)"""
        data = {}
        text = soup.get_text()
        
        # Genetics percentage patterns
        genetics_patterns = [
            r'(\\d+)%?\\s*sativa[^\\d]*(\\d+)%?\\s*indica',
            r'(\\d+)%?\\s*indica[^\\d]*(\\d+)%?\\s*sativa',
            r'sativa\\s*(\\d+)%[^\\d]*indica\\s*(\\d+)%',
            r'indica\\s*(\\d+)%[^\\d]*sativa\\s*(\\d+)%'
        ]
        
        for pattern in genetics_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if 'sativa' in pattern.lower():
                    data['genetics_sativa'] = int(match.group(1))
                    data['genetics_indica'] = int(match.group(2))
                else:
                    data['genetics_indica'] = int(match.group(1))
                    data['genetics_sativa'] = int(match.group(2))
                break
        
        # THC patterns with decimal precision
        thc_patterns = [
            r'THC[:\\s]*(\\d+(?:\\.\\d+)?)\\s*-\\s*(\\d+(?:\\.\\d+)?)%',
            r'THC[:\\s]*(\\d+(?:\\.\\d+)?)%',
            r'(\\d+(?:\\.\\d+)?)\\s*-\\s*(\\d+(?:\\.\\d+)?)%\\s*THC'
        ]
        
        for pattern in thc_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if len(match.groups()) == 2:
                    data['thc_min'] = float(match.group(1))
                    data['thc_max'] = float(match.group(2))
                else:
                    data['thc_min'] = data['thc_max'] = float(match.group(1))
                break
        
        # Flowering time patterns
        flowering_patterns = [
            r'(\\d+)\\s*-\\s*(\\d+)\\s*weeks',
            r'(\\d+)\\s*weeks',
            r'(\\d+)\\s*-\\s*(\\d+)\\s*days'
        ]
        
        for pattern in flowering_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if len(match.groups()) == 2:
                    if 'weeks' in pattern:
                        data['flowering_days_indoor'] = int(match.group(1)) * 7
                    else:
                        data['flowering_days_indoor'] = int(match.group(1))
                break
        
        return data

    def extract_fallback_data(self, soup):
        """Method 4: Fallback extraction"""
        data = {}
        
        # Extract from title
        title = soup.find('title')
        if title:
            title_text = title.get_text()
            # Try to extract strain name from title
            if 'seeds' in title_text.lower():
                parts = title_text.split('-')
                if parts:
                    data['strain_name_fallback'] = parts[0].strip()
        
        # Extract from meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            data['meta_description'] = meta_desc.get('content', '')
        
        # Extract price information
        price_selectors = ['.price', '.cost', '[class*="price"]', '[id*="price"]']
        for selector in price_selectors:
            price_elem = soup.select_one(selector)
            if price_elem:
                price_text = price_elem.get_text().strip()
                if '$' in price_text or '€' in price_text or '£' in price_text:
                    data['price'] = price_text
                    break
        
        return data

    def extract_comprehensive_data(self, soup, url):
        """Comprehensive data extraction using all methods"""
        # Method 1: Table parsing (highest priority)
        data = self.extract_from_tables(soup)
        
        # Method 2: Description mining (fill gaps)
        desc_data = self.extract_from_descriptions(soup)
        for key, value in desc_data.items():
            if key not in data or not data[key]:
                data[key] = value
        
        # Method 3: Pattern matching (precision data)
        pattern_data = self.extract_with_patterns(soup)
        data.update(pattern_data)
        
        # Method 4: Fallback extraction
        fallback_data = self.extract_fallback_data(soup)
        for key, value in fallback_data.items():
            if key not in data or not data[key]:
                data[key] = value
        
        # Add metadata
        data['source_url'] = url
        data['source_site'] = 'Seed Supreme'
        data['created_at'] = int(time.time())
        
        return self.validate_and_clean(data)

    def validate_and_clean(self, data):
        """Validate and clean extracted data"""
        cleaned = {}
        
        # Required fields
        if 'strain_name' not in data and 'strain_name_fallback' in data:
            data['strain_name'] = data['strain_name_fallback']
        
        # Clean and validate each field
        for key, value in data.items():
            if value and str(value).strip():
                cleaned_value = str(value).strip()
                
                # Convert numeric fields
                if key in ['genetics_sativa', 'genetics_indica', 'flowering_days_indoor']:
                    try:
                        cleaned[key] = int(cleaned_value)
                    except:
                        pass
                elif key in ['thc_min', 'thc_max', 'cbd_min', 'cbd_max']:
                    try:
                        cleaned[key] = float(cleaned_value)
                    except:
                        pass
                else:
                    cleaned[key] = cleaned_value
        
        return cleaned

    def scrape_strain_page(self, url):
        """Scrape individual strain page"""
        html = self.make_brightdata_request(url)
        if not html:
            return None
        
        soup = BeautifulSoup(html, 'html.parser')
        return self.extract_comprehensive_data(soup, url)

    def save_to_dynamodb(self, strain_data):
        """Save strain data to DynamoDB"""
        try:
            # Use strain_name and breeder_name as composite key
            item = {
                'strain_name': strain_data.get('strain_name', 'Unknown'),
                'breeder_name': strain_data.get('breeder_name', 'Unknown'),
                **strain_data
            }
            
            self.table.put_item(Item=item)
            return True
        except Exception as e:
            print(f"DynamoDB save error: {e}")
            return False

    def get_strain_urls(self):
        """Get strain URLs from Seed Supreme catalog pages"""
        strain_urls = []
        
        # Seed Supreme category pages (from chat.txt)
        category_urls = [
            "https://seedsupreme.com/feminized-seeds.html",
            "https://seedsupreme.com/autoflower-seeds.html",
            "https://seedsupreme.com/seed-banks/seed-supreme.html"  # Shop all
        ]
        
        for category_url in category_urls:
            print(f"Scraping category: {category_url}")
            
            # Get multiple pages per category
            for page in range(1, 51):  # Up to 50 pages per category
                if page == 1:
                    page_url = category_url
                else:
                    page_url = f"{category_url}?p={page}"
                
                html = self.make_brightdata_request(page_url)
                
                if html:
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Find product links - look for .html strain pages
                    product_links = soup.find_all('a', href=True)
                    page_urls = []
                    
                    for link in product_links:
                        href = link['href']
                        # Look for strain pages ending in .html
                        if href.endswith('.html') and any(word in href for word in ['seeds', 'strain', 'auto', 'fem']):
                            if href.startswith('http'):
                                full_url = href
                            else:
                                full_url = urljoin(self.base_url, href)
                            
                            if full_url not in strain_urls and 'category' not in full_url:
                                strain_urls.append(full_url)
                                page_urls.append(full_url)
                    
                    print(f"  Page {page}: Found {len(page_urls)} products")
                    
                    # If no products found, likely reached end
                    if not page_urls:
                        break
                    
                    time.sleep(1)  # Rate limiting
                else:
                    print(f"  Failed to fetch page {page}")
        
        return list(set(strain_urls))  # Remove duplicates

    def scrape_all_strains(self):
        """Main scraping function"""
        print("Starting Seed Supreme comprehensive scraping...")
        
        # Get all strain URLs
        strain_urls = self.get_strain_urls()
        print(f"Found {len(strain_urls)} strain URLs")
        
        if not strain_urls:
            print("No strain URLs found. Exiting.")
            return
        
        # Save URLs to file for resume capability
        with open('seed_supreme_urls.txt', 'w') as f:
            for url in strain_urls:
                f.write(f"{url}\n")
        
        # Scrape each strain
        for i, url in enumerate(strain_urls, 1):
            print(f"[{i}/{len(strain_urls)}] {url.split('/')[-1]}")
            
            strain_data = self.scrape_strain_page(url)
            
            if strain_data and strain_data.get('strain_name'):
                if self.save_to_dynamodb(strain_data):
                    self.success_count += 1
                    strain_name = strain_data.get('strain_name', 'Unknown')[:50]
                    breeder = strain_data.get('breeder_name', 'Unknown')[:30]
                    print(f"  SUCCESS: {strain_name} ({breeder})")
                else:
                    self.fail_count += 1
                    print("  SAVE FAILED")
            else:
                self.fail_count += 1
                print("  NO DATA")
            
            # Progress checkpoint every 100 strains
            if i % 100 == 0:
                print(f"\n--- CHECKPOINT {i} ---")
                print(f"Successful: {self.success_count}")
                print(f"Failed: {self.fail_count}")
                print(f"Success Rate: {(self.success_count/(self.success_count+self.fail_count)*100):.1f}%")
                print("--- CONTINUING ---\n")
            
            time.sleep(1)  # Rate limiting
        
        # Final results
        print(f"\nSEED SUPREME COMPLETE!")
        print(f"Success: {self.success_count}/{len(strain_urls)}")
        print(f"Cost: ${self.total_cost:.2f}")

if __name__ == "__main__":
    scraper = SeedSupremeScraper()
    scraper.scrape_all_strains()