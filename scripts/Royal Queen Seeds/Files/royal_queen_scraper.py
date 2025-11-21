#!/usr/bin/env python3
"""
Royal Queen Seeds Comprehensive Scraper
Using 4-method extraction approach from COMPREHENSIVE_SCRAPING_STRATEGY.md
Target: 1000+ strains from autoflowering, feminized, and CBD collections
"""

import json
import boto3
import requests
import time
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from decimal import Decimal

class RoyalQueenStrainScraper:
    def __init__(self):
        self.base_url = "https://www.royalqueenseeds.com"
        self.collection_urls = [
            "https://www.royalqueenseeds.com/34-autoflowering-cannabis-seeds",
            "https://www.royalqueenseeds.com/33-feminized-cannabis-seeds",
            "https://www.royalqueenseeds.com/36-cbd-seeds"
        ]
        
        # AWS clients
        self.secrets_client = boto3.client('secretsmanager', region_name='us-east-1')
        self.dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        self.table = self.dynamodb.Table('cannabis-strains')
        
        # BrightData credentials
        self.api_key = self._get_brightdata_credentials()
        self.api_url = "https://api.brightdata.com/request"
        
        # Tracking
        self.total_strains = 0
        self.successful_extractions = 0
        self.total_cost = 0.0

    def _get_brightdata_credentials(self):
        """Retrieve BrightData API key from AWS Secrets Manager"""
        try:
            response = self.secrets_client.get_secret_value(SecretId='cannabis-brightdata-api')
            credentials = json.loads(response['SecretString'])
            return credentials['api_key']
        except Exception as e:
            print(f"Error retrieving credentials: {e}")
            return None

    def _make_brightdata_request(self, url):
        """Make request through BrightData Web Unlocker API"""
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {
            "zone": "cannabis_strain_scraper",
            "url": url,
            "format": "raw"
        }
        
        try:
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=30)
            if response.status_code == 200:
                self.total_cost += 0.0015  # $0.0015 per request
                return response.text
            else:
                print(f"BrightData error {response.status_code}: {response.text}")
                return None
        except Exception as e:
            print(f"Request error: {e}")
            return None

    def extract_strain_urls(self, collection_url):
        """Extract strain URLs from collection pages"""
        print(f"Extracting strain URLs from: {collection_url}")
        
        html = self._make_brightdata_request(collection_url)
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        strain_urls = []
        
        # Look for product links in various formats
        selectors = [
            'a[href*=".html"]',
            '.product-item a',
            '.product-link',
            'a.product-name',
            '.product-title a'
        ]
        
        for selector in selectors:
            links = soup.select(selector)
            for link in links:
                href = link.get('href')
                if href and '.html' in href:
                    full_url = urljoin(self.base_url, href)
                    if full_url not in strain_urls:
                        strain_urls.append(full_url)
        
        print(f"Found {len(strain_urls)} strain URLs")
        return strain_urls

    def extract_strain_data_comprehensive(self, url):
        """4-method comprehensive strain data extraction"""
        html = self._make_brightdata_request(url)
        if not html:
            return None
        
        soup = BeautifulSoup(html, 'html.parser')
        strain_data = {'source_url': url}
        
        # Method 1: Table/List parsing
        self._extract_from_tables(soup, strain_data)
        
        # Method 2: Description mining
        self._extract_from_descriptions(soup, strain_data)
        
        # Method 3: Pattern matching
        self._extract_from_patterns(soup, strain_data)
        
        # Method 4: Fallback extraction
        self._extract_fallback_data(soup, strain_data)
        
        # Extract strain name and breeder
        self._extract_basic_info(soup, strain_data, url)
        
        return strain_data if strain_data.get('strain_name') else None

    def _extract_from_tables(self, soup, strain_data):
        """Method 1: Extract from structured tables/lists"""
        # Look for specification tables
        tables = soup.find_all(['table', 'dl', 'ul', 'div'])
        
        for table in tables:
            if table.find_all(['dt', 'th', 'li', 'span']):
                rows = table.find_all(['tr', 'dt', 'li', 'div', 'span'])
                for row in rows:
                    text = row.get_text(strip=True).lower()
                    
                    if 'flowering' in text or 'flower' in text:
                        numbers = re.findall(r'\d+', text)
                        if numbers:
                            strain_data['flowering_days'] = int(numbers[0])
                    
                    elif 'thc' in text:
                        numbers = re.findall(r'\d+(?:\.\d+)?', text)
                        if numbers:
                            strain_data['thc_max'] = float(numbers[0])
                    
                    elif 'cbd' in text:
                        numbers = re.findall(r'\d+(?:\.\d+)?', text)
                        if numbers:
                            strain_data['cbd_max'] = float(numbers[0])
                    
                    elif any(word in text for word in ['indica', 'sativa']):
                        if 'indica' in text and 'sativa' in text:
                            numbers = re.findall(r'\d+', text)
                            if len(numbers) >= 2:
                                strain_data['genetics_indica'] = int(numbers[0])
                                strain_data['genetics_sativa'] = int(numbers[1])

    def _extract_from_descriptions(self, soup, strain_data):
        """Method 2: Mine descriptions for cultivation data"""
        descriptions = soup.find_all(['div', 'p'], class_=re.compile(r'description|content|details|product'))
        
        for desc in descriptions:
            text = desc.get_text().lower()
            
            # Flowering time patterns
            flowering_patterns = [
                r'flowering[:\s]+(\d+)[-\s]*(\d+)?\s*(?:days?|weeks?)',
                r'flower[:\s]+(\d+)[-\s]*(\d+)?\s*(?:days?|weeks?)',
                r'(\d+)[-\s]*(\d+)?\s*(?:days?|weeks?)[:\s]*flowering'
            ]
            
            for pattern in flowering_patterns:
                match = re.search(pattern, text)
                if match:
                    days = int(match.group(1))
                    if 'week' in text:
                        days *= 7
                    strain_data['flowering_days'] = days
                    break
            
            # THC/CBD patterns
            thc_match = re.search(r'thc[:\s]*(\d+(?:\.\d+)?)%?', text)
            if thc_match:
                strain_data['thc_max'] = float(thc_match.group(1))
            
            cbd_match = re.search(r'cbd[:\s]*(\d+(?:\.\d+)?)%?', text)
            if cbd_match:
                strain_data['cbd_max'] = float(cbd_match.group(1))
            
            # Genetics patterns
            genetics_match = re.search(r'(\d+)%?\s*indica[,\s/]*(\d+)%?\s*sativa', text)
            if genetics_match:
                strain_data['genetics_indica'] = int(genetics_match.group(1))
                strain_data['genetics_sativa'] = int(genetics_match.group(2))

    def _extract_from_patterns(self, soup, strain_data):
        """Method 3: Pattern matching across entire page"""
        full_text = soup.get_text().lower()
        
        # Yield patterns
        yield_patterns = [
            r'yield[:\s]*(\d+)[-\s]*(\d+)?\s*(?:g|grams?|oz)',
            r'(\d+)[-\s]*(\d+)?\s*(?:g|grams?|oz)[:\s]*yield'
        ]
        
        for pattern in yield_patterns:
            match = re.search(pattern, full_text)
            if match:
                yield_val = int(match.group(1))
                strain_data['yield_indoor_grams'] = yield_val
                break
        
        # Height patterns
        height_patterns = [
            r'height[:\s]*(\d+)[-\s]*(\d+)?\s*(?:cm|m)',
            r'(\d+)[-\s]*(\d+)?\s*(?:cm|m)[:\s]*height'
        ]
        
        for pattern in height_patterns:
            match = re.search(pattern, full_text)
            if match:
                height = int(match.group(1))
                strain_data['height_cm'] = height
                break
        
        # Difficulty patterns
        if any(word in full_text for word in ['easy', 'beginner', 'simple']):
            strain_data['difficulty_rating'] = 2
        elif any(word in full_text for word in ['intermediate', 'moderate']):
            strain_data['difficulty_rating'] = 5
        elif any(word in full_text for word in ['advanced', 'expert', 'difficult']):
            strain_data['difficulty_rating'] = 8

    def _extract_fallback_data(self, soup, strain_data):
        """Method 4: Fallback extraction from any available data"""
        # Extract any numbers that might be relevant
        all_text = soup.get_text()
        
        # Look for percentage values that might be THC/CBD
        percentages = re.findall(r'(\d+(?:\.\d+)?)%', all_text)
        for pct in percentages:
            val = float(pct)
            if 15 <= val <= 35 and 'thc_max' not in strain_data:
                strain_data['thc_max'] = val
            elif 0.1 <= val <= 20 and 'cbd_max' not in strain_data:
                strain_data['cbd_max'] = val
        
        # Look for day ranges that might be flowering
        day_ranges = re.findall(r'(\d+)[-\s]*(\d+)?\s*days?', all_text.lower())
        for day_range in day_ranges:
            days = int(day_range[0])
            if 35 <= days <= 90 and 'flowering_days' not in strain_data:
                strain_data['flowering_days'] = days

    def _extract_basic_info(self, soup, strain_data, url):
        """Extract strain name and breeder information"""
        # Strain name from title or h1
        title_selectors = ['h1', '.product-title', '.product-name', 'title']
        for selector in title_selectors:
            element = soup.select_one(selector)
            if element:
                title = element.get_text(strip=True)
                # Clean up title
                strain_name = re.sub(r'\s*-\s*Royal Queen Seeds.*', '', title, flags=re.IGNORECASE)
                strain_name = re.sub(r'\s*\(.*?\)', '', strain_name)
                strain_data['strain_name'] = strain_name.strip()
                break
        
        # Extract from URL if no title found
        if not strain_data.get('strain_name'):
            url_parts = url.split('/')
            if len(url_parts) > 0:
                strain_slug = url_parts[-1].replace('.html', '')
                strain_name = strain_slug.replace('-', ' ').title()
                strain_name = re.sub(r'\s*Royal Queen Seeds.*', '', strain_name, flags=re.IGNORECASE)
                strain_data['strain_name'] = strain_name.strip()
        
        # Breeder extraction
        breeder_patterns = [
            r'by\s+([^,\n]+)',
            r'breeder[:\s]*([^,\n]+)',
            r'from\s+([^,\n]+)'
        ]
        
        page_text = soup.get_text()
        for pattern in breeder_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                breeder = match.group(1).strip()
                if len(breeder) < 50 and not any(word in breeder.lower() for word in ['seeds', 'shop', 'store']):
                    strain_data['breeder_name'] = breeder
                    break
        
        # Default breeder if none found
        if not strain_data.get('breeder_name'):
            strain_data['breeder_name'] = "Royal Queen Seeds"

    def save_to_dynamodb(self, strain_data):
        """Save strain data to DynamoDB"""
        try:
            # Convert floats to Decimal for DynamoDB
            for key, value in strain_data.items():
                if isinstance(value, float):
                    strain_data[key] = Decimal(str(value))
            
            # Add metadata
            strain_data['source'] = 'royal_queen_seeds'
            strain_data['scraped_at'] = int(time.time())
            
            self.table.put_item(Item=strain_data)
            return True
        except Exception as e:
            print(f"DynamoDB error: {e}")
            return False

    def scrape_all_strains(self):
        """Main scraping function"""
        print("Starting Royal Queen Seeds comprehensive scraping...")
        
        all_strain_urls = []
        
        # Collect URLs from all collections
        for collection_url in self.collection_urls:
            urls = self.extract_strain_urls(collection_url)
            all_strain_urls.extend(urls)
        
        # Remove duplicates
        all_strain_urls = list(set(all_strain_urls))
        self.total_strains = len(all_strain_urls)
        
        print(f"Found {self.total_strains} unique strain URLs")
        print(f"Estimated cost: ${self.total_strains * 0.0015:.2f}")
        
        # Process each strain
        for i, url in enumerate(all_strain_urls, 1):
            print(f"\n[{i}/{self.total_strains}] Processing: {url}")
            
            strain_data = self.extract_strain_data_comprehensive(url)
            
            if strain_data and strain_data.get('strain_name'):
                if self.save_to_dynamodb(strain_data):
                    self.successful_extractions += 1
                    print(f"SAVED: {strain_data['strain_name']} - {strain_data.get('breeder_name', 'Unknown')}")
                else:
                    print(f"FAILED to save: {strain_data.get('strain_name', 'Unknown')}")
            else:
                print(f"FAILED to extract data")
            
            # Rate limiting
            time.sleep(1)
        
        # Final statistics
        success_rate = (self.successful_extractions / self.total_strains) * 100 if self.total_strains > 0 else 0
        cost_per_strain = self.total_cost / self.successful_extractions if self.successful_extractions > 0 else 0
        
        print(f"\nROYAL QUEEN SEEDS SCRAPING COMPLETE!")
        print(f"Total strains processed: {self.total_strains}")
        print(f"Successful extractions: {self.successful_extractions}")
        print(f"Success rate: {success_rate:.1f}%")
        print(f"Total cost: ${self.total_cost:.2f}")
        print(f"Cost per strain: ${cost_per_strain:.4f}")

if __name__ == "__main__":
    scraper = RoyalQueenStrainScraper()
    scraper.scrape_all_strains()