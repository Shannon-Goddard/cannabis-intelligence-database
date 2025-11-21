import requests
import json
import boto3
from bs4 import BeautifulSoup
import time
import re
from datetime import datetime

class NorthAtlanticResumeScraper:
    def __init__(self):
        # Get BrightData credentials from AWS Secrets Manager
        secrets_client = boto3.client('secretsmanager', region_name='us-east-1')
        response = secrets_client.get_secret_value(SecretId='cannabis-brightdata-api')
        credentials = json.loads(response['SecretString'])
        self.api_key = credentials['api_key']
        self.zone = credentials['zone']
        
        # DynamoDB setup
        self.dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        self.table = self.dynamodb.Table('cannabis-strains')
    
    def brightdata_request(self, url):
        """Make request through BrightData Web Unlocker API"""
        api_url = "https://api.brightdata.com/request"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {"zone": self.zone, "url": url, "format": "raw"}
        
        try:
            response = requests.post(api_url, headers=headers, json=payload, timeout=60)
            return response.text if response.status_code == 200 else None
        except Exception as e:
            print(f"Request error: {e}")
            return None
    
    def extract_product_urls(self, html_content):
        """Extract product URLs from catalog page"""
        soup = BeautifulSoup(html_content, 'html.parser')
        urls = []
        
        # Look for product-card-image div with anchor tags
        for div in soup.find_all('div', class_='product-card-image'):
            link = div.find('a')
            if link and link.get('href'):
                href = link.get('href')
                # Ensure full URL
                if href.startswith('/'):
                    href = 'https://www.northatlanticseed.com' + href
                urls.append(href)
        
        return urls
    
    def extract_strain_data(self, html_content, url):
        """Extract strain data from individual product page"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Initialize strain data
        strain_data = {
            'strain_name': None,
            'breeder_name': None,
            'source_url': url,
            'source': 'North Atlantic Seed Company',
            'flowering_time': None,
            'difficulty': None,
            'height': None,
            'pack_size': None,
            'seed_type': None,
            'effects': None,
            'flavors': None,
            'genetics': None,
            'thc_min': None,
            'thc_max': None,
            'cbd_level': None,
            'yield_level': None,
            'created_at': str(int(time.time()))
        }
        
        # Extract strain name from title
        title_tag = soup.find('h1') or soup.find('title')
        if title_tag:
            title = title_tag.get_text().strip()
            # Clean up title to get strain name
            strain_name = re.sub(r'\s*-\s*North Atlantic Seed.*', '', title)
            strain_name = re.sub(r'\s*\|\s*.*', '', strain_name)
            strain_data['strain_name'] = strain_name.strip()
        
        # Extract specifications from product-specifications div (text format)
        specs_div = soup.find('div', class_='product-specifications')
        if specs_div:
            specs_text = specs_div.get_text()
            
            # Parse specifications using regex patterns
            spec_patterns = {
                'pack_size': r'Pack Size\s*([^\n\r]+)',
                'seed_type': r'Seed Type\s*([^\n\r]+)',
                'growth_type': r'Growth Type\s*([^\n\r]+)',
                'genetics': r'Genetics\s*([^\n\r]+)',
                'cannabis_type': r'Cannabis Type\s*([^\n\r]+)',
                'indica_sativa': r'Indica / Sativa / CBD\s*([^\n\r]+)',
                'flowering_time': r'Flowering Time\s*([^\n\r]+)',
                'flavor_profile': r'Flavor Profile\s*([^\n\r]+)'
            }
            
            for key, pattern in spec_patterns.items():
                match = re.search(pattern, specs_text, re.IGNORECASE)
                if match:
                    value = match.group(1).strip()
                    
                    if key == 'pack_size':
                        strain_data['pack_size'] = value
                    elif key in ['seed_type', 'growth_type']:
                        strain_data['seed_type'] = value
                    elif key in ['genetics', 'cannabis_type', 'indica_sativa']:
                        strain_data['genetics'] = value
                    elif key == 'flowering_time':
                        strain_data['flowering_time'] = value
                    elif key == 'flavor_profile':
                        strain_data['flavors'] = value
        
        # Extract description for additional data
        desc_div = soup.find('div', class_='product-description')
        if desc_div:
            desc_text = desc_div.get_text()
            
            # Extract breeder name from description
            breeder_patterns = [
                r'([A-Z\s&]+)\s*>\s*[A-Z]',  # "PURPLE CAPER SEEDS > ALIEN JACK"
                r'by\s+([A-Za-z\s&]+?)(?:\s|$|\.|\,)',
                r'from\s+([A-Za-z\s&]+?)(?:\s|$|\.|\,)',
                r'breeder:\s*([A-Za-z\s&]+?)(?:\s|$|\.|\,)'
            ]
            for pattern in breeder_patterns:
                match = re.search(pattern, desc_text, re.IGNORECASE)
                if match:
                    breeder = match.group(1).strip()
                    if len(breeder) > 2 and breeder != 'ABOUT THIS STRAIN':
                        strain_data['breeder_name'] = breeder
                        break
            
            # Extract genetics from parentheses in description
            genetics_match = re.search(r'\(([^)]+[Xx][^)]+)\)', desc_text)
            if genetics_match and not strain_data['genetics']:
                strain_data['genetics'] = genetics_match.group(1).strip()
            
            # Extract THC/CBD percentages
            thc_match = re.search(r'THC[:\s]*(\d+)(?:%)?(?:\s*-\s*(\d+)(?:%)?)?', desc_text, re.IGNORECASE)
            if thc_match:
                strain_data['thc_min'] = int(thc_match.group(1))
                if thc_match.group(2):
                    strain_data['thc_max'] = int(thc_match.group(2))
            
            cbd_match = re.search(r'CBD[:\s]*(\d+)(?:%)?', desc_text, re.IGNORECASE)
            if cbd_match:
                strain_data['cbd_level'] = int(cbd_match.group(1))
        
        return strain_data
    
    def save_to_dynamodb(self, strain_data):
        """Save strain data to DynamoDB"""
        # Remove None values
        item = {k: v for k, v in strain_data.items() if v is not None}
        
        # Ensure required fields
        if not item.get('strain_name'):
            return False
        if not item.get('breeder_name'):
            item['breeder_name'] = 'North Atlantic Seed Company'
        
        try:
            self.table.put_item(Item=item)
            return True
        except Exception as e:
            print(f"DynamoDB error: {e}")
            return False
    
    def resume_scraping(self, start_page=16, end_page=191):
        """Resume scraping from specified page"""
        print(f"RESUMING NORTH ATLANTIC SCRAPING FROM PAGE {start_page}")
        print("=" * 60)
        print(f"Current status: 165 strains already collected")
        print(f"Target: Pages {start_page}-{end_page} ({end_page-start_page+1} pages)")
        print(f"Expected: ~{(end_page-start_page+1)*16} additional strains")
        
        start_time = time.time()
        total_successful = 0
        total_failed = 0
        
        for page in range(start_page, end_page + 1):
            print(f"\n--- PAGE {page}/{end_page} ---")
            catalog_url = f"https://www.northatlanticseed.com/seeds/page/{page}/"
            
            # Get catalog page
            html = self.brightdata_request(catalog_url)
            if not html:
                print(f"FAILED: Could not fetch catalog page {page}")
                total_failed += 16  # Estimate 16 products per page
                continue
            
            # Extract product URLs
            urls = self.extract_product_urls(html)
            if not urls:
                print(f"No products found on page {page} - may be end of catalog")
                break
            
            print(f"Found {len(urls)} products on page {page}")
            
            # Scrape each product
            page_successful = 0
            page_failed = 0
            
            for i, url in enumerate(urls, 1):
                print(f"  [{i}/{len(urls)}] Scraping product...")
                
                product_html = self.brightdata_request(url)
                if product_html:
                    strain_data = self.extract_strain_data(product_html, url)
                    
                    if strain_data['strain_name'] and self.save_to_dynamodb(strain_data):
                        page_successful += 1
                        total_successful += 1
                        print(f"    SUCCESS: {strain_data['strain_name']} - {strain_data.get('breeder_name', 'Unknown')}")
                    else:
                        page_failed += 1
                        total_failed += 1
                        print(f"    FAILED: Could not extract or save data")
                else:
                    page_failed += 1
                    total_failed += 1
                    print(f"    FAILED: Could not fetch product page")
                
                time.sleep(1)  # Rate limiting
            
            print(f"Page {page} complete: {page_successful} success, {page_failed} failed")
            
            # Progress update every 5 pages
            if page % 5 == 0:
                elapsed = time.time() - start_time
                pages_done = page - start_page + 1
                pages_remaining = end_page - page
                estimated_total_time = elapsed * (pages_done + pages_remaining) / pages_done
                estimated_remaining = estimated_total_time - elapsed
                
                print(f"\n*** PROGRESS UPDATE ***")
                print(f"Pages completed: {pages_done}/{end_page-start_page+1}")
                print(f"Total strains collected this session: {total_successful}")
                print(f"Estimated time remaining: {estimated_remaining/60:.1f} minutes")
                print(f"Current success rate: {total_successful/(total_successful+total_failed)*100:.1f}%")
            
            time.sleep(2)  # Longer pause between pages
        
        # Final summary
        total_time = time.time() - start_time
        print(f"\n" + "=" * 60)
        print(f"RESUME SESSION COMPLETE")
        print(f"Pages scraped: {start_page}-{end_page}")
        print(f"New strains collected: {total_successful}")
        print(f"Failed attempts: {total_failed}")
        print(f"Success rate: {total_successful/(total_successful+total_failed)*100:.1f}%")
        print(f"Total time: {total_time/60:.1f} minutes")
        print(f"Cost estimate: ${(total_successful+total_failed) * 0.0015:.2f}")
        print(f"Total database size: ~{165 + total_successful} North Atlantic strains")

if __name__ == "__main__":
    scraper = NorthAtlanticResumeScraper()
    scraper.resume_scraping(start_page=16, end_page=191)