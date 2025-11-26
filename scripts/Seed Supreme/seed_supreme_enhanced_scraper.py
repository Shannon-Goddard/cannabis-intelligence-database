#!/usr/bin/env python3
"""
Seed Supreme Enhanced 4-Method Scraper
Based on Neptune's 99.9% success rate methodology
Seed Supreme specific HTML: #product-attribute-specs-table with comprehensive THC/CBD ranges
"""

import json
import boto3
import requests
import time
import re
from bs4 import BeautifulSoup
from decimal import Decimal
from datetime import datetime

class SeedSupremeEnhancedScraper:
    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        self.table = self.dynamodb.Table('cannabis-strains-universal')
        self.secrets_client = boto3.client('secretsmanager', region_name='us-east-1')
        self.brightdata_config = self._get_brightdata_credentials()
        
    def _get_brightdata_credentials(self):
        """Get BrightData credentials from AWS Secrets Manager"""
        response = self.secrets_client.get_secret_value(SecretId='cannabis-brightdata-api')
        return json.loads(response['SecretString'])
    
    def _make_brightdata_request(self, url):
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
        
        response = requests.post(api_url, headers=headers, json=payload, timeout=30)
        return response.text if response.status_code == 200 else None

    def method1_structured_extraction(self, soup, url):
        """Method 1: Extract from Seed Supreme's comprehensive table (#product-attribute-specs-table)"""
        data = {}
        
        # Extract strain profile table - Seed Supreme's main data source
        table = soup.find('table', id='product-attribute-specs-table')
        if table:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all('td')
                # Process pairs of label/data cells (Seed Supreme format)
                for i in range(0, len(cells), 2):
                    if i + 1 < len(cells):
                        label = cells[i].get_text().strip().rstrip(':')
                        value = cells[i + 1].get_text().strip()
                        
                        # Seed Supreme specific field mapping
                        field_map = {
                            'SKU': 'sku',
                            'Seedbank': 'breeder_name',  # IMPORTANT: This is the breeder, not seed bank!
                            'Genetics': 'genetics',
                            'Variety': 'variety',
                            'Flowering Type': 'flowering_type',
                            'THC Content': 'thc_content',  # Seed Supreme's strength: precise ranges
                            'CBD Content': 'cbd_content',  # Seed Supreme's strength: precise ranges
                            'Yield': 'yield',
                            'Effects': 'effects',  # Detailed comma-separated effects
                            'Flavors': 'flavors',  # Multiple flavors
                            'Terpenes': 'terpenes',  # Specific terpene names
                            'Flowering Time': 'flowering_time',
                            'Plant Height': 'plant_height'
                        }
                        
                        if label in field_map and value:
                            data[field_map[label]] = value
        
        return data

    def method2_description_mining(self, soup, url):
        """Method 2: Mine descriptions with Seed Supreme specific patterns"""
        data = {}
        
        # Extract description content - Seed Supreme format
        description = soup.find('div', id='description')
        if description:
            value_div = description.find('div', class_='value')
            if value_div:
                desc_text = value_div.get_text()
                data['about_info'] = desc_text.strip()
                
                # Seed Supreme specific patterns for THC/CBD ranges
                patterns = {
                    'thc_range_detailed': r'THC[:\s]*([0-9.-]+%?\s*-\s*[0-9.-]+%?)',
                    'cbd_range_detailed': r'CBD[:\s]*([0-9.-]+%?\s*-\s*[0-9.-]+%?)',
                    'flowering_weeks': r'(?:flowering|flower)[:\s]*([0-9-]+\s*weeks?)',
                    'strain_effects_detailed': r'effects?[:\s]*([^.]+)',
                    'terpene_profile_detailed': r'terpenes?[:\s]*([^.]+)',
                    'flavor_notes_detailed': r'flavou?rs?[:\s]*([^.]+)',
                    'genetics_lineage': r'(?:genetics|cross|lineage)[:\s]*([^.]+)',
                    'breeder_attribution': r'(?:by|from|bred by)[:\s]*([A-Za-z\s&]+?)(?:\s|$|\.)'
                }
                
                for key, pattern in patterns.items():
                    match = re.search(pattern, desc_text, re.IGNORECASE)
                    if match:
                        data[key] = match.group(1).strip()
        
        return data

    def method3_advanced_patterns(self, soup, url):
        """Method 3: Advanced pattern matching for Seed Supreme"""
        data = {}
        
        # Extract strain name from title or H1 - Seed Supreme format
        title_selectors = ['h1', '.product-title', 'title', '.page-title']
        for selector in title_selectors:
            element = soup.select_one(selector)
            if element:
                title_text = element.get_text().strip()
                # Clean up Seed Supreme titles (remove "Seeds", "Feminized", etc.)
                clean_title = re.sub(r'\b(seeds?|feminized|auto|autoflower|photoperiod|cannabis)\b', '', title_text, flags=re.IGNORECASE)
                clean_title = re.sub(r'\s+', ' ', clean_title).strip()
                if clean_title:
                    data['strain_name'] = clean_title
                    break
        
        # Extract from breadcrumbs or navigation
        breadcrumbs = soup.select('.breadcrumb a, .nav-breadcrumb a, .breadcrumbs a')
        if breadcrumbs:
            data['category_path'] = ' > '.join([b.get_text().strip() for b in breadcrumbs])
        
        # Extract price information (Seed Supreme specific)
        price_selectors = ['.price', '.product-price', '.cost', '[class*="price"]']
        for selector in price_selectors:
            price_elem = soup.select_one(selector)
            if price_elem:
                price_text = price_elem.get_text().strip()
                if any(symbol in price_text for symbol in ['$', '€', '£']):
                    data['price'] = price_text
                    break
        
        return data

    def method4_fallback_extraction(self, soup, url):
        """Method 4: Universal fallback extraction"""
        data = {}
        
        # Meta tags
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            data['meta_description'] = meta_desc.get('content', '')
            
        # Page title fallback
        title = soup.find('title')
        if title and not data.get('strain_name'):
            title_text = title.get_text().strip()
            data['page_title'] = title_text
            
        # Extract strain name from URL if not found elsewhere
        if not data.get('strain_name'):
            url_parts = url.split('/')
            for part in reversed(url_parts):
                if part and part.endswith('.html'):
                    strain_from_url = part.replace('.html', '').replace('-', ' ').title()
                    strain_from_url = re.sub(r'\b(Feminized|Auto|Autoflower|Seeds?)\b', '', strain_from_url).strip()
                    if strain_from_url:
                        data['strain_name_from_url'] = strain_from_url
                        break
                        
        return data

    def calculate_quality_score(self, strain_data):
        """Calculate data completeness score with Seed Supreme weights"""
        # Seed Supreme specific field weights (emphasizing their strengths)
        field_weights = {
            'strain_name': 10, 'breeder_name': 10,
            'thc_content': 9,  # Seed Supreme's strength: precise ranges
            'cbd_content': 8,  # Seed Supreme's strength: precise ranges
            'terpenes': 8,     # Seed Supreme's strength: specific terpenes
            'effects': 7,      # Seed Supreme's strength: detailed effects
            'flavors': 6,      # Seed Supreme's strength: multiple flavors
            'genetics': 8, 'flowering_time': 6, 'yield': 5,
            'plant_height': 5, 'variety': 4, 'flowering_type': 4,
            'about_info': 3, 'sku': 2
        }
        
        total_possible = sum(field_weights.values())
        actual_score = 0
        
        for field, weight in field_weights.items():
            if strain_data.get(field) and len(str(strain_data[field]).strip()) > 2:
                actual_score += weight
        
        return round((actual_score / total_possible) * 100, 1)

    def determine_quality_tier(self, score):
        """Determine quality tier based on score"""
        if score >= 80: return "Premium"
        elif score >= 60: return "High"
        elif score >= 40: return "Medium"
        elif score >= 20: return "Basic"
        else: return "Minimal"

    def create_strain_id(self, strain_name, breeder_name):
        """Create unique strain ID"""
        combined = f"{strain_name}-{breeder_name}-seed-supreme".lower()
        combined = re.sub(r'[^a-z0-9-]', '', combined.replace(' ', '-'))
        return combined[:50]

    def extract_strain_data(self, html_content, url):
        """Enhanced 4-method extraction for Seed Supreme"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        strain_data = {
            'seed_bank': 'Seed Supreme',
            'source_url': url,
            'extraction_methods_used': []
        }
        
        # Apply all 4 methods in sequence
        methods = [
            ('structured', self.method1_structured_extraction),
            ('description', self.method2_description_mining),
            ('patterns', self.method3_advanced_patterns),
            ('fallback', self.method4_fallback_extraction)
        ]
        
        for method_name, method_func in methods:
            try:
                method_data = method_func(soup, url)
                if method_data:
                    strain_data.update(method_data)
                    strain_data['extraction_methods_used'].append(method_name)
            except Exception as e:
                print(f"Method {method_name} failed: {e}")
        
        # Post-processing: use fallback strain name if needed
        if not strain_data.get('strain_name') and strain_data.get('strain_name_from_url'):
            strain_data['strain_name'] = strain_data['strain_name_from_url']
        
        # Calculate quality metrics
        strain_data['data_completeness_score'] = Decimal(str(self.calculate_quality_score(strain_data)))
        strain_data['quality_tier'] = self.determine_quality_tier(float(strain_data['data_completeness_score']))
        strain_data['field_count'] = len([v for v in strain_data.values() if v])
        
        # Create strain ID
        strain_name = strain_data.get('strain_name', 'Unknown')
        breeder_name = strain_data.get('breeder_name', 'Seed Supreme')
        strain_data['strain_id'] = self.create_strain_id(strain_name, breeder_name)
        
        # Add timestamps
        now = datetime.utcnow().isoformat() + 'Z'
        strain_data['created_at'] = now
        strain_data['updated_at'] = now
        
        return strain_data

    def save_to_dynamodb(self, strain_data):
        """Save strain data to DynamoDB"""
        try:
            self.table.put_item(Item=strain_data)
            return True
        except Exception as e:
            print(f"DynamoDB save error: {e}")
            return False

    def scrape_seed_supreme_catalog(self):
        """Scrape Seed Supreme catalog pages for strain URLs"""
        print("Collecting Seed Supreme strain URLs...")
        
        # Use path.txt URLs as starting points
        catalog_urls = [
            "https://seedsupreme.com/feminized-seeds.html",
            "https://seedsupreme.com/autoflowering-seeds.html", 
            "https://seedsupreme.com/regular-seeds.html"
        ]
        
        all_strain_urls = set()
        
        for catalog_url in catalog_urls:
            print(f"Scraping catalog: {catalog_url}")
            
            # Try multiple pages per catalog
            for page in range(1, 11):  # Up to 10 pages per catalog
                if page == 1:
                    page_url = catalog_url
                else:
                    page_url = f"{catalog_url}?p={page}"
                
                html = self._make_brightdata_request(page_url)
                if html:
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Find product links - Seed Supreme specific
                    page_urls = set()
                    
                    # Look for strain page links
                    links = soup.find_all('a', href=True)
                    for link in links:
                        href = link.get('href', '')
                        
                        # Filter for Seed Supreme strain pages
                        if (href.endswith('.html') and 
                            any(keyword in href for keyword in ['feminized', 'autoflower', 'regular']) and
                            not any(exclude in href for exclude in ['category', 'seed-banks', 'cannabis-seeds/', 'sitemap', 'bogos', 'free-cannabis', 'best-sellers'])):
                            
                            if href.startswith('/'):
                                full_url = f"https://seedsupreme.com{href}"
                            elif href.startswith('http'):
                                full_url = href
                            else:
                                continue
                            
                            if 'seedsupreme.com' in full_url:
                                page_urls.add(full_url)
                    
                    print(f"  Page {page}: Found {len(page_urls)} strain URLs")
                    all_strain_urls.update(page_urls)
                    
                    # If no new URLs found, likely reached end
                    if not page_urls:
                        break
                        
                else:
                    print(f"  Failed to fetch page {page}")
                    break
                
                time.sleep(2)  # Rate limiting
        
        strain_urls = sorted(list(all_strain_urls))
        print(f"Total strain URLs collected: {len(strain_urls)}")
        
        # Save URLs for reference
        with open('seed_supreme_collected_urls.txt', 'w') as f:
            for url in strain_urls:
                f.write(f"{url}\n")
        
        return strain_urls

    def run_enhanced_scraping(self):
        """Run enhanced 4-method scraping on Seed Supreme"""
        print("Starting Seed Supreme Enhanced 4-Method Scraping")
        print("Target: Comprehensive THC/CBD ranges and detailed terpene profiles")
        
        # Get strain URLs
        strain_urls = self.scrape_seed_supreme_catalog()
        
        if len(strain_urls) == 0:
            print("No URLs found, exiting")
            return
        
        successful_extractions = 0
        failed_extractions = 0
        method_stats = {'structured': 0, 'description': 0, 'patterns': 0, 'fallback': 0}
        quality_distribution = {'Premium': 0, 'High': 0, 'Medium': 0, 'Basic': 0, 'Minimal': 0}
        
        for i, url in enumerate(strain_urls, 1):
            print(f"Processing {i}/{len(strain_urls)}: {url.split('/')[-1]}")
            
            html = self._make_brightdata_request(url)
            if html:
                strain_data = self.extract_strain_data(html, url)
                
                # Update statistics
                for method in strain_data.get('extraction_methods_used', []):
                    method_stats[method] += 1
                
                quality_tier = strain_data.get('quality_tier', 'Minimal')
                quality_distribution[quality_tier] += 1
                
                # Save to database
                if self.save_to_dynamodb(strain_data):
                    successful_extractions += 1
                    strain_name = strain_data.get('strain_name', 'Unknown')[:30]
                    breeder = strain_data.get('breeder_name', 'Unknown')[:20]
                    score = strain_data.get('data_completeness_score', 0)
                    print(f"  Saved: {strain_name} ({breeder}) - {quality_tier} ({score}%)")
                else:
                    failed_extractions += 1
                    print(f"  Failed to save: {url}")
            else:
                failed_extractions += 1
                print(f"  Failed to fetch: {url}")
            
            time.sleep(1)  # Rate limiting
        
        # Final statistics
        success_rate = (successful_extractions / len(strain_urls)) * 100 if len(strain_urls) > 0 else 0
        print(f"\nSEED SUPREME ENHANCED SCRAPING COMPLETE!")
        print(f"Success Rate: {success_rate:.1f}% ({successful_extractions}/{len(strain_urls)})")
        print(f"Method Performance:")
        for method, count in method_stats.items():
            coverage = (count / successful_extractions) * 100 if successful_extractions > 0 else 0
            print(f"   {method.title()}: {count} strains ({coverage:.1f}% coverage)")
        
        print(f"Quality Distribution:")
        for tier, count in quality_distribution.items():
            percentage = (count / successful_extractions) * 100 if successful_extractions > 0 else 0
            print(f"   {tier}: {count} strains ({percentage:.1f}%)")
        
        # Cost calculation
        total_requests = len(strain_urls) + 30  # URLs + catalog pages
        total_cost = total_requests * 0.0015
        print(f"Cost: ${total_cost:.2f} (${total_cost/successful_extractions:.4f} per strain)")

if __name__ == "__main__":
    scraper = SeedSupremeEnhancedScraper()
    scraper.run_enhanced_scraping()