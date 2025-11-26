#!/usr/bin/env python3
"""
North Atlantic Seed Company Comprehensive Scraper
Using 4-method extraction approach for maximum success rate
Target: Beat original 77.9% success rate with new methodology
"""

import json
import boto3
import requests
import time
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class NorthAtlanticScraper:
    def __init__(self):
        self.base_url = "https://www.northatlanticseed.com"
        self.session = requests.Session()
        self.scraped_strains = []
        self.failed_urls = []
        self.success_count = 0
        self.total_count = 0
        
        # Initialize AWS clients
        self.secrets_client = boto3.client('secretsmanager', region_name='us-east-1')
        self.dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        self.table = self.dynamodb.Table('cannabis-strains')
        
        # Get BrightData credentials
        self.brightdata_config = self._get_brightdata_credentials()
        
    def _get_brightdata_credentials(self):
        """Retrieve BrightData credentials from AWS Secrets Manager"""
        try:
            response = self.secrets_client.get_secret_value(SecretId='cannabis-brightdata-api')
            credentials = json.loads(response['SecretString'])
            return {
                'api_key': credentials['api_key'],
                'zone': credentials['zone']
            }
        except Exception as e:
            logger.error(f"Failed to retrieve BrightData credentials: {e}")
            raise

    def _make_brightdata_request(self, url, max_retries=3):
        """Make request through BrightData Web Unlocker API"""
        api_url = "https://api.brightdata.com/request"
        headers = {
            "Authorization": f"Bearer {self.brightdata_config['api_key']}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "zone": self.brightdata_config['zone'],
            "url": url,
            "format": "raw"
        }
        
        for attempt in range(max_retries):
            try:
                response = requests.post(api_url, headers=headers, json=payload, timeout=30)
                if response.status_code == 200:
                    return response.text
                else:
                    logger.warning(f"BrightData API returned {response.status_code} for {url}")
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)
            except Exception as e:
                logger.warning(f"Request failed (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
        
        return None

    def _extract_strain_data_method1_table_parsing(self, soup, url):
        """Method 1: Extract from structured tables/lists"""
        strain_data = {}
        
        # Look for product information tables
        tables = soup.find_all(['table', 'dl', 'div'], class_=re.compile(r'(product|strain|info|detail|spec)', re.I))
        
        for table in tables:
            rows = table.find_all(['tr', 'dt', 'div'])
            for row in rows:
                text = row.get_text(strip=True)
                if ':' in text:
                    key, value = text.split(':', 1)
                    key = key.strip().lower()
                    value = value.strip()
                    
                    if 'thc' in key and '%' in value:
                        strain_data['thc_content'] = value
                    elif 'cbd' in key and '%' in value:
                        strain_data['cbd_content'] = value
                    elif 'flowering' in key or 'flower' in key:
                        strain_data['flowering_time'] = value
                    elif 'yield' in key:
                        strain_data['yield_info'] = value
                    elif 'genetics' in key or 'lineage' in key:
                        strain_data['genetics'] = value
                    elif 'type' in key:
                        strain_data['strain_type'] = value
        
        return strain_data

    def _extract_strain_data_method2_description_mining(self, soup, url):
        """Method 2: Mine product descriptions for strain data"""
        strain_data = {}
        
        # Find description areas
        desc_selectors = [
            '.product-description', '.description', '.product-details',
            '.strain-info', '.product-info', '[class*="desc"]'
        ]
        
        description_text = ""
        for selector in desc_selectors:
            elements = soup.select(selector)
            for element in elements:
                description_text += " " + element.get_text()
        
        if not description_text:
            # Fallback to common paragraph areas
            paragraphs = soup.find_all('p')
            description_text = " ".join([p.get_text() for p in paragraphs])
        
        # Extract data using regex patterns
        patterns = {
            'thc_content': r'THC[:\s]*(\d+(?:\.\d+)?(?:\s*-\s*\d+(?:\.\d+)?)?%?)',
            'cbd_content': r'CBD[:\s]*(\d+(?:\.\d+)?(?:\s*-\s*\d+(?:\.\d+)?)?%?)',
            'flowering_time': r'(?:flowering|flower)[:\s]*(\d+(?:\s*-\s*\d+)?\s*(?:days?|weeks?))',
            'genetics': r'(?:genetics|lineage|cross)[:\s]*([^.]+)',
            'yield_info': r'yield[:\s]*([^.]+)',
            'strain_type': r'(?:type|variety)[:\s]*(indica|sativa|hybrid|auto)',
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, description_text, re.IGNORECASE)
            if match:
                strain_data[key] = match.group(1).strip()
        
        return strain_data

    def _extract_strain_data_method3_pattern_matching(self, soup, url):
        """Method 3: Advanced pattern matching across entire page"""
        strain_data = {}
        
        # Get all text content
        page_text = soup.get_text()
        
        # Advanced patterns for North Atlantic specific format
        advanced_patterns = {
            'breeder': r'(?:by|from|breeder)[:\s]*([A-Za-z\s&]+?)(?:\n|$|[,.])',
            'seed_type': r'(feminized|regular|auto|autoflower)',
            'indoor_yield': r'indoor[:\s]*(\d+[^.\n]*)',
            'outdoor_yield': r'outdoor[:\s]*(\d+[^.\n]*)',
            'height': r'height[:\s]*(\d+[^.\n]*)',
            'effects': r'effects?[:\s]*([^.\n]+)',
            'flavors': r'(?:flavor|taste|aroma)[:\s]*([^.\n]+)',
        }
        
        for key, pattern in advanced_patterns.items():
            matches = re.findall(pattern, page_text, re.IGNORECASE | re.MULTILINE)
            if matches:
                strain_data[key] = matches[0].strip()
        
        return strain_data

    def _extract_strain_data_method4_fallback(self, soup, url):
        """Method 4: Fallback extraction from any available data"""
        strain_data = {}
        
        # Extract from meta tags
        meta_tags = soup.find_all('meta')
        for meta in meta_tags:
            if meta.get('name') == 'description' or meta.get('property') == 'og:description':
                content = meta.get('content', '')
                if content:
                    strain_data['meta_description'] = content
        
        # Extract from title
        title = soup.find('title')
        if title:
            strain_data['page_title'] = title.get_text().strip()
        
        # Extract from any span/div with numbers (likely specs)
        spec_elements = soup.find_all(['span', 'div'], string=re.compile(r'\d+%|\d+\s*days?|\d+\s*weeks?'))
        for element in spec_elements:
            text = element.get_text().strip()
            if '%' in text and 'thc' in element.get('class', []):
                strain_data['thc_content'] = text
            elif 'day' in text or 'week' in text:
                strain_data['flowering_time'] = text
        
        return strain_data

    def extract_strain_data(self, html_content, url):
        """Comprehensive strain data extraction using all 4 methods"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Initialize combined data
        strain_data = {
            'source_url': url,
            'seed_bank': 'North Atlantic Seed Company',
            'extraction_methods_used': []
        }
        
        # Method 1: Table parsing
        method1_data = self._extract_strain_data_method1_table_parsing(soup, url)
        if method1_data:
            strain_data.update(method1_data)
            strain_data['extraction_methods_used'].append('table_parsing')
        
        # Method 2: Description mining
        method2_data = self._extract_strain_data_method2_description_mining(soup, url)
        if method2_data:
            strain_data.update(method2_data)
            strain_data['extraction_methods_used'].append('description_mining')
        
        # Method 3: Pattern matching
        method3_data = self._extract_strain_data_method3_pattern_matching(soup, url)
        if method3_data:
            strain_data.update(method3_data)
            strain_data['extraction_methods_used'].append('pattern_matching')
        
        # Method 4: Fallback
        method4_data = self._extract_strain_data_method4_fallback(soup, url)
        if method4_data:
            strain_data.update(method4_data)
            strain_data['extraction_methods_used'].append('fallback')
        
        # Extract strain name from URL or title
        strain_name = self._extract_strain_name(soup, url)
        if strain_name:
            strain_data['strain_name'] = strain_name
        
        return strain_data

    def _extract_strain_name(self, soup, url):
        """Extract strain name from URL or page content"""
        # Try URL path
        path_parts = urlparse(url).path.split('/')
        for part in reversed(path_parts):
            if part and part != 'product':
                return part.replace('-', ' ').title()
        
        # Try page title
        title = soup.find('title')
        if title:
            title_text = title.get_text()
            # Remove common suffixes
            for suffix in [' - North Atlantic Seed Company', ' | NASC', ' Seeds']:
                title_text = title_text.replace(suffix, '')
            return title_text.strip()
        
        # Try h1
        h1 = soup.find('h1')
        if h1:
            return h1.get_text().strip()
        
        return None

    def get_all_product_urls(self):
        """Get all product URLs from North Atlantic Seed Company"""
        print("Collecting all product URLs from North Atlantic Seed Company...")
        
        product_urls = []
        base_catalog_url = "https://www.northatlanticseed.com/seeds/"
        
        # Scrape all 191 pages like original method for comparison
        for page in range(1, 192):  # Pages 1-191
            catalog_url = f"{base_catalog_url}page/{page}/" if page > 1 else base_catalog_url
            
            print(f"Scraping catalog page {page}/191...")
            
            html_content = self._make_brightdata_request(catalog_url)
            if not html_content:
                print(f"Failed to fetch catalog page {page}")
                continue
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Find product links
            product_links = soup.find_all('a', href=re.compile(r'/product/'))
            page_urls = []
            
            for link in product_links:
                href = link.get('href')
                if href:
                    full_url = urljoin(self.base_url, href)
                    if full_url not in product_urls:
                        product_urls.append(full_url)
                        page_urls.append(full_url)
            
            print(f"Found {len(page_urls)} products on page {page}")
            
            # Small delay between catalog pages
            time.sleep(0.5)
        
        print(f"Total product URLs collected: {len(product_urls)}")
        return product_urls

    def scrape_strain(self, url):
        """Scrape individual strain data"""
        self.total_count += 1
        
        print(f"Scraping strain {self.total_count}: {url}")
        
        html_content = self._make_brightdata_request(url)
        if not html_content:
            print(f"Failed to fetch {url}")
            self.failed_urls.append(url)
            return None
        
        try:
            strain_data = self.extract_strain_data(html_content, url)
            
            # Validate we got meaningful data
            data_fields = len([k for k, v in strain_data.items() 
                             if k not in ['source_url', 'seed_bank', 'extraction_methods_used'] and v])
            
            if data_fields >= 2:  # At least 2 meaningful fields
                self.scraped_strains.append(strain_data)
                self.success_count += 1
                
                # Store in DynamoDB
                self._store_in_dynamodb(strain_data)
                
                print(f"SUCCESS: Extracted {data_fields} fields using methods: {strain_data.get('extraction_methods_used', [])}")
                return strain_data
            else:
                print(f"Insufficient data extracted from {url}")
                self.failed_urls.append(url)
                return None
                
        except Exception as e:
            print(f"Error processing {url}: {e}")
            self.failed_urls.append(url)
            return None

    def _store_in_dynamodb(self, strain_data):
        """Store strain data in DynamoDB"""
        try:
            # Create item for DynamoDB
            item = {
                'strain_name': strain_data.get('strain_name', 'Unknown'),
                'breeder_name': strain_data.get('breeder', 'North Atlantic Seed Company'),
                'seed_bank': 'North Atlantic Seed Company',
                'source_url': strain_data['source_url'],
                'extraction_methods': strain_data.get('extraction_methods_used', []),
                'data_fields': len([k for k, v in strain_data.items() if v and k not in ['source_url', 'seed_bank', 'extraction_methods_used']])
            }
            
            # Add all extracted data
            for key, value in strain_data.items():
                if value and key not in ['source_url', 'seed_bank', 'extraction_methods_used']:
                    item[key] = str(value)
            
            self.table.put_item(Item=item)
            
        except Exception as e:
            print(f"Failed to store in DynamoDB: {e}")

    def run_comprehensive_scrape(self):
        """Run the complete scraping operation"""
        print("Starting North Atlantic Seed Company comprehensive scrape...")
        print("Target: Beat original 77.9% success rate with 4-method extraction")
        
        start_time = time.time()
        
        # Get all product URLs
        product_urls = self.get_all_product_urls()
        
        if not product_urls:
            print("No product URLs found!")
            return
        
        print(f"Starting to scrape {len(product_urls)} products...")
        
        # Scrape each product
        for i, url in enumerate(product_urls, 1):
            print(f"Progress: {i}/{len(product_urls)} ({(i/len(product_urls)*100):.1f}%)")
            
            self.scrape_strain(url)
            
            # Progress update every 50 strains
            if i % 50 == 0:
                success_rate = (self.success_count / self.total_count) * 100
                print(f"Current success rate: {success_rate:.1f}% ({self.success_count}/{self.total_count})")
            
            # Small delay between requests
            time.sleep(0.2)
        
        # Final results
        end_time = time.time()
        duration = end_time - start_time
        success_rate = (self.success_count / self.total_count) * 100
        
        print("=" * 60)
        print("NORTH ATLANTIC SEED COMPANY - COMPREHENSIVE SCRAPE COMPLETE")
        print("=" * 60)
        print(f"Total Products Processed: {self.total_count}")
        print(f"Successful Extractions: {self.success_count}")
        print(f"Failed Extractions: {len(self.failed_urls)}")
        print(f"Success Rate: {success_rate:.1f}%")
        print(f"Duration: {duration/3600:.1f} hours")
        print(f"Original Success Rate: 77.9%")
        print(f"Improvement: {success_rate - 77.9:+.1f} percentage points")
        
        # Save results
        self._save_results()
        
        return {
            'total_processed': self.total_count,
            'successful': self.success_count,
            'failed': len(self.failed_urls),
            'success_rate': success_rate,
            'duration_hours': duration / 3600,
            'improvement_over_original': success_rate - 77.9
        }

    def _save_results(self):
        """Save scraping results to files"""
        # Save successful strains
        with open('north_atlantic_strains_comprehensive.json', 'w') as f:
            json.dump(self.scraped_strains, f, indent=2)
        
        # Save failed URLs
        with open('north_atlantic_failed_urls.txt', 'w') as f:
            for url in self.failed_urls:
                f.write(f"{url}\n")
        
        print(f"Results saved: {len(self.scraped_strains)} strains, {len(self.failed_urls)} failed URLs")

if __name__ == "__main__":
    scraper = NorthAtlanticScraper()
    results = scraper.run_comprehensive_scrape()
    
    print("\n" + "="*60)
    print("FINAL RESULTS SUMMARY")
    print("="*60)
    print(f"Success Rate: {results['success_rate']:.1f}%")
    print(f"Strains Collected: {results['successful']}")
    print(f"Improvement over Original: {results['improvement_over_original']:+.1f} percentage points")
    print(f"Duration: {results['duration_hours']:.1f} hours")
    print("="*60)