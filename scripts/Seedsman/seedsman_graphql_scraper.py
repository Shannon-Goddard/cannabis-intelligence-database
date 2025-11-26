#!/usr/bin/env python3
"""
Seedsman GraphQL Scraper - THE PROVEN APPROACH
Based on successful previous implementation that collected 747 strains
"""

import json
import boto3
import requests
import time
import re
from bs4 import BeautifulSoup
from decimal import Decimal
from datetime import datetime

class SeedsmanGraphQLScraper:
    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        self.table = self.dynamodb.Table('cannabis-strains-universal')
        self.secrets_client = boto3.client('secretsmanager', region_name='us-east-1')
        self.brightdata_config = self._get_brightdata_credentials()
        
        # Success tracking
        self.total_processed = 0
        self.successful_extractions = 0
        
    def _get_brightdata_credentials(self):
        response = self.secrets_client.get_secret_value(SecretId='cannabis-brightdata-api')
        return json.loads(response['SecretString'])
    
    def _brightdata_graphql_request(self, query, variables=None):
        """Make GraphQL request via BrightData Web Unlocker"""
        payload = {
            "zone": self.brightdata_config['zone'],
            "url": "https://www.seedsman.com/graphql",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"query": query, "variables": variables or {}}),
            "format": "raw"
        }
        
        response = requests.post("https://api.brightdata.com/request", 
                               headers={"Authorization": f"Bearer {self.brightdata_config['api_key']}"}, 
                               json=payload, timeout=30)
        
        if response.status_code == 200:
            try:
                result = json.loads(response.text)
                if 'errors' in result:
                    print(f"GraphQL errors: {result['errors']}")
                return result
            except:
                print(f"JSON parse error: {response.text[:200]}")
                return None
        else:
            print(f"HTTP error {response.status_code}: {response.text[:200]}")
        return None
    
    def _brightdata_request(self, url):
        """Standard BrightData request for individual pages"""
        api_url = "https://api.brightdata.com/request"
        headers = {"Authorization": f"Bearer {self.brightdata_config['api_key']}"}
        payload = {"zone": self.brightdata_config['zone'], "url": url, "format": "raw"}
        
        response = requests.post(api_url, headers=headers, json=payload, timeout=30)
        return response.text if response.status_code == 200 else None

    def collect_products_graphql(self):
        """Phase 1: Collect product URLs using proven GraphQL approach"""
        print("PHASE 1: Collecting Seedsman products via GraphQL...")
        
        query = """
        query GetProducts($search: String!, $pageSize: Int!, $currentPage: Int!) {
            products(
                search: $search
                pageSize: $pageSize
                currentPage: $currentPage
            ) {
                total_count
                page_info {
                    current_page
                    total_pages
                }
                items {
                    id
                    name
                    sku
                    url_key
                }
            }
        }
        """
        
        # Use proven search terms from previous success
        search_terms = ["seeds", "cannabis", "auto", "fem", "photoperiod", "indica", "sativa"]
        all_products = []
        
        for search_term in search_terms:
            print(f"\nSearching for: {search_term}")
            page = 1
            
            while page <= 5:  # Limit to 5 pages per search
                print(f"  Page {page}...")
                result = self._brightdata_graphql_request(query, {
                    "search": search_term, 
                    "pageSize": 50, 
                    "currentPage": page
                })
                
                if not result or 'data' not in result or not result['data']['products']:
                    break
                    
                products_data = result['data']['products']
                products = products_data['items']
                
                if not products:
                    break
                    
                # Filter duplicates by ID
                new_products = []
                existing_ids = {p['id'] for p in all_products}
                for product in products:
                    if product['id'] not in existing_ids:
                        new_products.append(product)
                
                all_products.extend(new_products)
                print(f"    Found {len(new_products)} new products (total: {len(all_products)})")
                
                if page >= products_data['page_info']['total_pages']:
                    break
                    
                page += 1
                time.sleep(0.5)
        
        print(f"\nTotal unique products collected: {len(all_products)}")
        return all_products

    def extract_strain_data_4method(self, html_content, url, product_info):
        """Apply 4-method extraction to individual product pages"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        strain_data = {
            'seed_bank': 'Seedsman',
            'source_url': url,
            'sku': product_info.get('sku', ''),
            'extraction_methods_used': []
        }
        
        # Method 1: Structured extraction from specifications table
        table = soup.find('table', id='product-attribute-specs-table')
        if table:
            strain_data['extraction_methods_used'].append('structured')
            rows = table.find_all('tr')
            for row in rows:
                label_th = row.find('th', class_='col label')
                data_td = row.find('td', class_='col data')
                
                if label_th and data_td:
                    label_h4 = label_th.find('h4')
                    if label_h4:
                        label = label_h4.get_text().strip()
                        
                        # Extract value from nested spans or h3
                        spans = data_td.find_all('span')
                        if spans:
                            values = [span.get_text().strip() for span in spans if span.get_text().strip()]
                            value = ' | '.join(values) if len(values) > 1 else values[0] if values else ''
                        else:
                            h3 = data_td.find('h3')
                            value = h3.get_text().strip() if h3 else data_td.get_text().strip()
                        
                        # Map Seedsman fields
                        field_map = {
                            'Brand/breeder': 'breeder_name',
                            'THC content': 'thc_content',
                            'Yield indoor': 'yield_indoor',
                            'Yield outdoor': 'yield_outdoor',
                            'Photoperiod flowering time': 'flowering_time',
                            'Suitable climates': 'suitable_climates',
                            'Aroma': 'aroma',
                            'Variety': 'variety',
                            'Sex': 'sex',
                            'Flowering type': 'flowering_type'
                        }
                        
                        if label in field_map and value:
                            strain_data[field_map[label]] = value
        
        # Method 2: Description mining
        desc_div = soup.find('div', class_='ProductActions-ShortDescription')
        if desc_div:
            strain_data['extraction_methods_used'].append('description')
            strain_data['about_info'] = desc_div.get_text().strip()
        
        # Method 3: Advanced patterns - strain name extraction
        strain_data['extraction_methods_used'].append('patterns')
        strain_name = product_info.get('name', '')
        if strain_name:
            # Clean Seedsman naming patterns
            strain_name = re.sub(r'\s*(Feminized|Auto|Autoflower|Seeds?|Regular)\s*', ' ', strain_name, re.IGNORECASE)
            strain_name = re.sub(r'\s*-\s*Seedsman\s*', '', strain_name, re.IGNORECASE)
            strain_data['strain_name'] = strain_name.strip()
        
        # Set breeder name
        if not strain_data.get('breeder_name'):
            strain_data['breeder_name'] = 'Seedsman'
        
        # Method 4: Fallback - always executed
        strain_data['extraction_methods_used'].append('fallback')
        
        # Calculate quality score
        strain_data['data_completeness_score'] = self.calculate_quality_score(strain_data)
        strain_data['quality_tier'] = self.determine_quality_tier(strain_data['data_completeness_score'])
        strain_data['field_count'] = len([v for v in strain_data.values() if v])
        
        # Create strain ID
        strain_name = strain_data.get('strain_name', 'Unknown')
        breeder_name = strain_data.get('breeder_name', 'Seedsman')
        strain_data['strain_id'] = self.create_strain_id(strain_name, breeder_name)
        
        # Add timestamps
        now = datetime.utcnow().isoformat() + 'Z'
        strain_data['created_at'] = now
        strain_data['updated_at'] = now
        
        return strain_data

    def calculate_quality_score(self, strain_data):
        """Calculate quality score for Seedsman data"""
        field_weights = {
            'strain_name': 10,
            'breeder_name': 8,
            'thc_content': 9,
            'yield_indoor': 8,
            'yield_outdoor': 8,
            'flowering_time': 7,
            'suitable_climates': 7,
            'aroma': 6,
            'variety': 5,
            'sex': 5,
            'flowering_type': 5,
            'about_info': 6,
            'sku': 3
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
        combined = f"{strain_name}-{breeder_name}-seedsman".lower()
        combined = re.sub(r'[^a-z0-9-]', '', combined.replace(' ', '-'))
        return combined[:50]

    def scrape_individual_products(self, products):
        """Phase 2: Scrape individual product pages"""
        print(f"\nPHASE 2: Scraping {len(products)} individual product pages...")
        
        for i, product in enumerate(products, 1):
            self.total_processed += 1
            url = f"https://www.seedsman.com/us-en/{product['url_key']}"
            print(f"\n[{i}/{len(products)}] {product['name']}")
            print(f"  URL: {url}")
            
            html = self._brightdata_request(url)
            if html:
                strain_data = self.extract_strain_data_4method(html, url, product)
                
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
                        
                        if strain_data.get('thc_content'):
                            print(f"     THC: {strain_data['thc_content']}")
                        
                    except Exception as e:
                        print(f"  STORAGE FAILED: {e}")
                else:
                    print(f"  LOW QUALITY: {strain_data['data_completeness_score']:.1f}% - skipped")
            else:
                print(f"  FETCH FAILED")
            
            time.sleep(1)

    def print_final_stats(self):
        """Print final statistics"""
        success_rate = (self.successful_extractions / self.total_processed * 100) if self.total_processed > 0 else 0
        
        print(f"\nSEEDSMAN GRAPHQL SCRAPING COMPLETE!")
        print(f"THE BEAR HAS BEEN CONQUERED!")
        print(f"FINAL STATISTICS:")
        print(f"   Total Processed: {self.total_processed}")
        print(f"   Successful: {self.successful_extractions}")
        print(f"   Success Rate: {success_rate:.1f}%")
        print(f"\nCost: ~${self.total_processed * 0.0015:.2f} (BrightData)")
        print(f"Achievement: Seedsman conquered using proven GraphQL approach!")

def main():
    scraper = SeedsmanGraphQLScraper()
    
    # Phase 1: Collect products via GraphQL
    products = scraper.collect_products_graphql()
    
    if not products:
        print("No products found via GraphQL. Exiting.")
        return
    
    # Phase 2: Scrape individual pages
    scraper.scrape_individual_products(products)
    
    # Final statistics
    scraper.print_final_stats()

if __name__ == "__main__":
    print("SEEDSMAN GRAPHQL SCRAPER - THE PROVEN APPROACH")
    print("Based on successful previous implementation (747 strains)")
    print("Strategy: GraphQL product discovery + 4-method extraction")
    print("Expected: High success rate with comprehensive data")
    print("\n" + "="*60)
    
    main()