import requests
import boto3
import json
import re
from bs4 import BeautifulSoup
from datetime import datetime

class SHNScraper:
    def __init__(self):
        # Get BrightData credentials
        secrets_client = boto3.client('secretsmanager', region_name='us-east-1')
        response = secrets_client.get_secret_value(SecretId='cannabis-brightdata-api')
        credentials = json.loads(response['SecretString'])
        self.api_key = credentials['api_key']
        self.zone = credentials['zone']
        
        # DynamoDB
        self.dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        self.table = self.dynamodb.Table('cannabis-strains')
    
    def get_page(self, url):
        api_url = "https://api.brightdata.com/request"
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"}
        payload = {"zone": self.zone, "url": url, "format": "raw"}
        
        response = requests.post(api_url, headers=headers, json=payload, timeout=60)
        return response.text if response.status_code == 200 else None
    
    def get_strain_names(self):
        """Get strain names from all seed categories"""
        categories = [
            "feminized-cannabis-seeds",
            "regular-cannabis-seeds", 
            "autoflower-cannabis-seeds"
        ]
        
        all_strains = []
        
        for category in categories:
            print(f"\nScraping {category}...")
            
            for page in range(1, 11):  # First 10 pages per category
                catalog_url = f"https://seedsherenow.com/product-category/{category}/page/{page}/"
                print(f"  Page {page}")
                
                html = self.get_page(catalog_url)
                if not html:
                    break
                
                soup = BeautifulSoup(html, 'html.parser')
                page_strains = []
                
                # Find product images with alt text
                for img in soup.find_all('img', alt=True):
                    alt = img.get('alt', '')
                    if '(' in alt and any(seed_type in alt.lower() for seed_type in ['feminized', 'regular', 'autoflower']):
                        # Extract strain name from "Strain Name (Type) - Breeder"
                        strain = alt.split('(')[0].strip()
                        if len(strain) > 2:
                            page_strains.append(strain)
                
                all_strains.extend(page_strains)
                print(f"    Found {len(page_strains)} strains")
                
                if len(page_strains) == 0:
                    break
        
        return list(set(all_strains))
    
    def scrape_strain_detail(self, strain_name):
        """Scrape individual strain page"""
        # Convert strain name to URL slug
        slug = strain_name.lower().replace(' ', '-').replace("'", "")
        url = f"https://seedsherenow.com/shop/{slug}/"
        
        html = self.get_page(url)
        if not html:
            return None
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract table data
        strain_data = {
            'strain_name': strain_name, 
            'breeder_name': 'Unknown',  # Default value
            'source_url': url, 
            'scraped_at': int(datetime.now().timestamp())
        }
        
        for row in soup.find_all('tr'):
            th = row.find('th')
            td = row.find('td')
            if th and td:
                key = th.get_text().strip().lower()
                value = td.get_text().strip()
                
                if 'breeder' in key:
                    strain_data['breeder_name'] = value
                elif 'genetics' in key:
                    strain_data['genetics'] = value
                elif 'thc' in key:
                    thc_match = re.search(r'(\d+)%?\s*to\s*(\d+)%', value)
                    if thc_match:
                        strain_data['thc_min'] = int(thc_match.group(1))
                        strain_data['thc_max'] = int(thc_match.group(2))
                elif 'cbd' in key:
                    cbd_match = re.search(r'(\d+)', value)
                    if cbd_match:
                        strain_data['cbd_level'] = int(cbd_match.group(1))
                elif 'flowering' in key:
                    strain_data['flowering_time'] = value
                elif 'yield' in key:
                    strain_data['yield_level'] = value
                elif 'difficulty' in key:
                    strain_data['difficulty'] = value
                elif 'aroma' in key or 'flavor' in key:
                    strain_data['flavor_profile'] = value
                elif 'effects' in key:
                    strain_data['effects'] = value
                elif 'seed type' in key:
                    strain_data['seed_type'] = value
        
        return strain_data
    
    def run(self):
        print("SEEDS HERE NOW SCRAPER")
        print("=" * 40)
        
        # Load strain names from file
        print("Loading strain names from file...")
        with open('strain_names.txt', 'r') as f:
            strain_names = [line.strip() for line in f if line.strip()]
        print(f"Loaded {len(strain_names)} strains")
        
        # Scrape each strain
        scraped = 0
        failed = 0
        
        for i, strain in enumerate(strain_names, 1):
            print(f"[{i}/{len(strain_names)}] {strain}")
            data = self.scrape_strain_detail(strain)
            if data:
                self.table.put_item(Item=data)
                scraped += 1
                print(f"  SUCCESS: {data.get('breeder_name', 'Unknown')}")
            else:
                failed += 1
                print(f"  FAILED")
        
        print(f"\nRESULTS: {scraped} success, {failed} failed")

if __name__ == "__main__":
    import sys
    
    scraper = SHNScraper()
    
    if len(sys.argv) > 1 and sys.argv[1] == "names-only":
        # Just collect strain names
        strain_names = scraper.get_strain_names()
        with open('strain_names.txt', 'w') as f:
            for strain in strain_names:
                f.write(strain + '\n')
        print(f"Saved {len(strain_names)} strain names to strain_names.txt")
    else:
        # Full scrape
        scraper.run()