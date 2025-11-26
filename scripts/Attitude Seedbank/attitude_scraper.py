#!/usr/bin/env python3
"""
The Attitude Seed Bank Scraper
Target: 3,000-5,000+ strains across 167 pages for 10,000+ milestone
"""

import requests
import json
import boto3
import re
import time
from bs4 import BeautifulSoup
from datetime import datetime
from botocore.exceptions import ClientError

class AttitudeScraper:
    def __init__(self):
        self.session = requests.Session()
        self.dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        self.table = self.dynamodb.Table('cannabis-strains-universal')
        self.secrets_client = boto3.client('secretsmanager', region_name='us-east-1')
        self.api_credentials = self.get_brightdata_credentials()
        
        # Category URLs with page counts
        self.categories = {
            'feminized': {
                'url': 'https://www.cannabis-seeds-bank.co.uk/feminized-seeds/cat_106',
                'pages': 97
            },
            'regular': {
                'url': 'https://www.cannabis-seeds-bank.co.uk/regular-seeds/cat_107', 
                'pages': 46
            },
            'autoflower': {
                'url': 'https://www.cannabis-seeds-bank.co.uk/autoflowering-seeds/cat_108',
                'pages': 24
            }
        }
        
        self.stats = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'urls_collected': 0,
            'cost_estimate': 0.0
        }

    def get_brightdata_credentials(self):
        try:
            response = self.secrets_client.get_secret_value(SecretId='cannabis-brightdata-api')
            return json.loads(response['SecretString'])
        except ClientError as e:
            print(f"Error retrieving credentials: {e}")
            return None

    def scrape_with_brightdata(self, url):
        if not self.api_credentials:
            return None
            
        api_url = "https://api.brightdata.com/request"
        headers = {"Authorization": f"Bearer {self.api_credentials['api_key']}"}
        payload = {
            "zone": "cannabis_unlocker",
            "url": url,
            "format": "raw"
        }
        
        try:
            response = requests.post(api_url, headers=headers, json=payload, timeout=300)
            self.stats['cost_estimate'] += 0.0015  # $1.50 per 1000 requests
            
            if response.status_code == 200:
                return response.text
            else:
                print(f"BrightData error {response.status_code}: {response.text}")
                return None
        except Exception as e:
            print(f"Request failed for {url}: {e}")
            return None

    def collect_product_urls(self):
        """Collect all product URLs from category pages"""
        all_urls = []
        
        for category_name, category_info in self.categories.items():
            print(f"\nCollecting URLs from {category_name} category ({category_info['pages']} pages)...")
            
            for page in range(1, category_info['pages'] + 1):
                if page == 1:
                    page_url = category_info['url']
                else:
                    page_url = f"{category_info['url']}?page={page}"
                
                print(f"  Page {page}/{category_info['pages']}: {page_url}")
                
                html = self.scrape_with_brightdata(page_url)
                if html:
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Extract product URLs from category page
                    product_links = soup.find_all('a', href=True)
                    page_urls = []
                    
                    for link in product_links:
                        href = link.get('href', '')
                        if '/prod_' in href:
                            # Convert relative URL to absolute URL
                            if href.startswith('/'):
                                full_url = f"https://www.cannabis-seeds-bank.co.uk{href}"
                            else:
                                full_url = href
                            
                            if full_url not in all_urls:
                                all_urls.append(full_url)
                                page_urls.append(full_url)
                    
                    print(f"    Found {len(page_urls)} product URLs")
                    time.sleep(3)  # Longer delay for slow pages
                else:
                    print(f"    Failed to scrape page {page}")
        
        self.stats['urls_collected'] = len(all_urls)
        print(f"\nTotal URLs collected: {len(all_urls)}")
        
        # Save URLs to file
        with open('attitude_product_urls.txt', 'w') as f:
            for url in all_urls:
                f.write(f"{url}\n")
        
        return all_urls

    def extract_strain_data(self, soup, url):
        """Extract strain data from product page"""
        data = {
            'bank_name': 'The Attitude Seed Bank',
            'url': url,
            'scraped_at': datetime.utcnow().isoformat()
        }
        
        # Extract strain name from product title
        title_elem = soup.find('h2', class_='productHeading')
        if title_elem:
            data['strain_name'] = title_elem.get_text().strip()
        
        # Extract characteristics from structured list
        char_tab = soup.find('div', id='tabChar')
        if char_tab:
            char_items = char_tab.find_all('li')
            for item in char_items:
                text = item.get_text().strip()
                if ':' in text:
                    label, value = text.split(':', 1)
                    label = label.strip()
                    
                    # Extract value from span if available
                    span = item.find('span')
                    if span:
                        value = span.get_text().strip()
                    else:
                        value = value.strip()
                    
                    field_map = {
                        'Genetics': 'genetics',
                        'Sex': 'sex',
                        'Flowering': 'flowering',
                        'Type': 'type',
                        'Flowering Time': 'flowering_time',
                        'Height': 'height',
                        'Area': 'area'
                    }
                    
                    if label in field_map and value:
                        data[field_map[label]] = value
        
        # Extract detailed information from description tab
        desc_tab = soup.find('div', id='tabDesc')
        if desc_tab:
            desc_text = desc_tab.get_text()
            data['about_info'] = desc_text.strip()
            
            # Extract breeder using pattern matching
            breeder_match = re.search(r'Cannabis Seeds by ([^\n]+?)(?:\s|$)', desc_text)
            if breeder_match:
                data['breeder_name'] = breeder_match.group(1).strip()
            
            # Extract specific cultivation data using regex
            # THC content
            thc_match = re.search(r'THC:\s*(\d+%)', desc_text)
            if thc_match:
                data['thc_content'] = thc_match.group(1)
            
            # Indoor specifications
            indoor_yield_match = re.search(r'Yield:\s*([\d\s-]+gr/m2)', desc_text)
            if indoor_yield_match:
                data['yield_indoor'] = indoor_yield_match.group(1).strip()
            
            indoor_height_match = re.search(r'Height:\s*([\d\s-]+cm)', desc_text)
            if indoor_height_match:
                data['height_indoor'] = indoor_height_match.group(1).strip()
            
            # Cultivation time
            cultivation_match = re.search(r'Total Cultivation:\s*([\d\s-]+days)', desc_text)
            if cultivation_match:
                data['cultivation_time'] = cultivation_match.group(1).strip()
            
            # Outdoor harvest period
            harvest_match = re.search(r'Harvest:\s*(From [^\n]+)', desc_text)
            if harvest_match:
                data['harvest_period'] = harvest_match.group(1).strip()
            
            # Outdoor height - simple extraction, will be refined later
            height_matches = re.findall(r'Height:\s*(\d+\s*-\s*\d+\s*cm)', desc_text)
            if len(height_matches) > 1:
                data['height_outdoor'] = height_matches[1].strip()  # Second height match is usually outdoor
        
        return data

    def save_to_dynamodb(self, strain_data):
        """Save strain data to DynamoDB"""
        try:
            # Create unique ID
            strain_id = f"{strain_data.get('strain_name', 'unknown')}_{strain_data.get('breeder_name', 'attitude')}".lower()
            strain_id = re.sub(r'[^a-z0-9_-]', '_', strain_id)
            
            strain_data['strain_id'] = strain_id
            
            self.table.put_item(Item=strain_data)
            return True
        except Exception as e:
            print(f"Error saving to DynamoDB: {e}")
            return False

    def scrape_product_page(self, url):
        """Scrape individual product page"""
        html = self.scrape_with_brightdata(url)
        if not html:
            return False
        
        soup = BeautifulSoup(html, 'html.parser')
        strain_data = self.extract_strain_data(soup, url)
        
        # Validate required fields
        if not strain_data.get('strain_name'):
            print(f"  ERROR: No strain name found")
            return False
        
        # Save to database
        if self.save_to_dynamodb(strain_data):
            print(f"  SUCCESS: {strain_data.get('strain_name')} - {strain_data.get('breeder_name', 'Unknown Breeder')}")
            return True
        else:
            print(f"  ERROR: Failed to save {strain_data.get('strain_name')}")
            return False

    def run_full_scrape(self):
        """Run complete scraping process"""
        print("THE ATTITUDE SEED BANK SCRAPER")
        print("Target: 3,000-5,000+ strains for 10,000+ milestone")
        print("=" * 60)
        
        # Phase 1: Collect URLs
        print("\nPHASE 1: COLLECTING PRODUCT URLS")
        urls = self.collect_product_urls()
        
        if not urls:
            print("❌ No URLs collected. Exiting.")
            return
        
        # Phase 2: Scrape products
        print("\nPHASE 2: SCRAPING PRODUCT PAGES")
        
        for i, url in enumerate(urls, 1):
            print(f"\n[{i}/{len(urls)}] {url}")
            
            if self.scrape_product_page(url):
                self.stats['successful'] += 1
            else:
                self.stats['failed'] += 1
            
            self.stats['total_processed'] += 1
            
            # Progress update every 50 strains
            if i % 50 == 0:
                success_rate = (self.stats['successful'] / self.stats['total_processed']) * 100
                print(f"\nProgress: {i}/{len(urls)} ({success_rate:.1f}% success rate)")
                print(f"Estimated cost: ${self.stats['cost_estimate']:.2f}")
            
            time.sleep(2)  # Longer delay for slow pages
        
        # Final statistics
        self.print_final_stats()

    def print_final_stats(self):
        """Print final scraping statistics"""
        success_rate = (self.stats['successful'] / self.stats['total_processed']) * 100 if self.stats['total_processed'] > 0 else 0
        
        print("\n" + "=" * 60)
        print("THE ATTITUDE SEED BANK SCRAPING COMPLETE!")
        print("=" * 60)
        print(f"FINAL STATISTICS:")
        print(f"   URLs Collected: {self.stats['urls_collected']}")
        print(f"   Total Processed: {self.stats['total_processed']}")
        print(f"   Successful: {self.stats['successful']}")
        print(f"   Failed: {self.stats['failed']}")
        print(f"   Success Rate: {success_rate:.1f}%")
        print(f"Total Cost: ${self.stats['cost_estimate']:.2f}")
        print(f"Cost per Strain: ${self.stats['cost_estimate']/max(self.stats['successful'], 1):.4f}")
        
        if self.stats['successful'] >= 3000:
            print("\nMILESTONE ACHIEVED: 3,000+ strains collected!")
            print("Ready for 10,000+ strain milestone!")
        
        print("\nCannabis genetics revolution continues!")

if __name__ == "__main__":
    scraper = AttitudeScraper()
    scraper.run_full_scrape()