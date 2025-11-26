#!/usr/bin/env python3
import requests
import json
import boto3
import re
import time
from bs4 import BeautifulSoup
from datetime import datetime
from botocore.exceptions import ClientError

class AttitudeProductScraper:
    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        self.table = self.dynamodb.Table('cannabis-strains-universal')
        self.secrets_client = boto3.client('secretsmanager', region_name='us-east-1')
        self.api_credentials = self.get_brightdata_credentials()
        self.stats = {'total_processed': 0, 'successful': 0, 'failed': 0, 'cost_estimate': 0.0}

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
        payload = {"zone": "cannabis_unlocker", "url": url, "format": "raw"}
        
        try:
            response = requests.post(api_url, headers=headers, json=payload, timeout=300)
            self.stats['cost_estimate'] += 0.0015
            
            if response.status_code == 200:
                return response.text
            else:
                return None
        except Exception as e:
            return None

    def extract_strain_data(self, soup, url):
        data = {'bank_name': 'The Attitude Seed Bank', 'url': url, 'scraped_at': datetime.now().isoformat()}
        
        # Extract strain name
        title_elem = soup.find('h2', class_='productHeading')
        if title_elem:
            data['strain_name'] = title_elem.get_text().strip()
        
        # Extract characteristics
        char_tab = soup.find('div', id='tabChar')
        if char_tab:
            char_items = char_tab.find_all('li')
            for item in char_items:
                text = item.get_text().strip()
                if ':' in text:
                    label, value = text.split(':', 1)
                    span = item.find('span')
                    if span:
                        value = span.get_text().strip()
                    else:
                        value = value.strip()
                    
                    field_map = {'Genetics': 'genetics', 'Sex': 'sex', 'Flowering': 'flowering', 
                               'Type': 'type', 'Flowering Time': 'flowering_time', 'Height': 'height', 'Area': 'area'}
                    
                    if label.strip() in field_map and value:
                        data[field_map[label.strip()]] = value
        
        # Extract description data
        desc_tab = soup.find('div', id='tabDesc')
        if desc_tab:
            desc_text = desc_tab.get_text()
            data['about_info'] = desc_text.strip()
            
            # Extract breeder
            breeder_match = re.search(r'Cannabis Seeds by ([^\\n]+?)(?:\\s|$)', desc_text)
            if breeder_match:
                data['breeder_name'] = breeder_match.group(1).strip()
            
            # Extract cultivation data
            thc_match = re.search(r'THC:\\s*(\\d+%)', desc_text)
            if thc_match:
                data['thc_content'] = thc_match.group(1)
            
            yield_match = re.search(r'Yield:\\s*([\\d\\s-]+gr/m2)', desc_text)
            if yield_match:
                data['yield_indoor'] = yield_match.group(1).strip()
        
        return data

    def save_to_dynamodb(self, strain_data):
        try:
            strain_id = f"{strain_data.get('strain_name', 'unknown')}_{strain_data.get('breeder_name', 'attitude')}"
            strain_id = re.sub(r'[^a-z0-9_-]', '_', strain_id.lower())
            strain_data['strain_id'] = strain_id
            self.table.put_item(Item=strain_data)
            return True
        except Exception as e:
            return False

    def run_product_scraping(self):
        # Load URLs from file
        try:
            with open('attitude_product_urls.txt', 'r') as f:
                urls = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            print("No URLs file found. Run full scraper first.")
            return
        
        print(f"Processing {len(urls)} product URLs...")
        
        for i, url in enumerate(urls, 1):
            print(f"[{i}/{len(urls)}] Processing...")
            
            html = self.scrape_with_brightdata(url)
            if html:
                soup = BeautifulSoup(html, 'html.parser')
                strain_data = self.extract_strain_data(soup, url)
                
                if strain_data.get('strain_name') and self.save_to_dynamodb(strain_data):
                    strain_name = strain_data.get('strain_name', '').encode('ascii', 'ignore').decode('ascii')
                    breeder_name = strain_data.get('breeder_name', 'Unknown').encode('ascii', 'ignore').decode('ascii')
                    print(f"  SUCCESS: {strain_name} - {breeder_name}")
                    self.stats['successful'] += 1
                else:
                    print(f"  ERROR: Failed to process")
                    self.stats['failed'] += 1
            else:
                print(f"  ERROR: No HTML returned")
                self.stats['failed'] += 1
            
            self.stats['total_processed'] += 1
            
            if i % 100 == 0:
                success_rate = (self.stats['successful'] / self.stats['total_processed']) * 100
                print(f"\\nProgress: {i}/{len(urls)} ({success_rate:.1f}% success)")
                print(f"Cost: ${self.stats['cost_estimate']:.2f}")
            
            time.sleep(2)
        
        # Final stats
        success_rate = (self.stats['successful'] / self.stats['total_processed']) * 100
        print(f"\\nFINAL: {self.stats['successful']}/{self.stats['total_processed']} ({success_rate:.1f}% success)")
        print(f"Total Cost: ${self.stats['cost_estimate']:.2f}")

if __name__ == "__main__":
    scraper = AttitudeProductScraper()
    scraper.run_product_scraping()