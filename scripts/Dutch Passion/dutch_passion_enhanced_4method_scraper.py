#!/usr/bin/env python3
"""
Dutch Passion Enhanced 4-Method Scraper
Targets legacy genetics from original seed company (1987)
"""

import json
import boto3
import requests
import time
import re
from datetime import datetime
from botocore.exceptions import ClientError

# Configuration
SEED_BANK = "Dutch Passion"
BREEDER_NAME = "Dutch Passion"
DYNAMODB_TABLE = "cannabis-strains-perfect"

# Categories to scrape
CATEGORIES = [
    "https://dutch-passion.us/feminized-seeds",
    "https://dutch-passion.us/autoflower-seeds", 
    "https://dutch-passion.us/regular-seeds"
]

class DutchPassionScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # AWS clients
        self.secrets_client = boto3.client('secretsmanager', region_name='us-east-1')
        self.dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        self.table = self.dynamodb.Table(DYNAMODB_TABLE)
        
        # Get BrightData credentials
        self.api_key = self._get_brightdata_credentials()
        
        # Stats
        self.stats = {
            'total_processed': 0,
            'successful_extractions': 0,
            'method_usage': {'structured': 0, 'description': 0, 'patterns': 0, 'fallback': 0},
            'quality_distribution': {'premium': 0, 'high': 0, 'medium': 0, 'basic': 0}
        }

    def _get_brightdata_credentials(self):
        try:
            response = self.secrets_client.get_secret_value(SecretId='cannabis-brightdata-api')
            credentials = json.loads(response['SecretString'])
            return credentials['api_key']
        except Exception as e:
            print(f"Error getting credentials: {e}")
            return None

    def _brightdata_request(self, url):
        """Make request through BrightData Web Unlocker API"""
        api_url = "https://api.brightdata.com/request"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {"zone": "cannabis_strain_scraper", "url": url, "format": "raw"}
        
        try:
            response = requests.post(api_url, headers=headers, json=payload, timeout=30)
            if response.status_code == 200:
                return response.text
            else:
                print(f"BrightData error {response.status_code}: {response.text}")
                return None
        except Exception as e:
            print(f"Request error: {e}")
            return None

    def extract_strain_urls(self, category_url):
        """Extract strain URLs from category page"""
        print(f"Extracting URLs from: {category_url}")
        html = self._brightdata_request(category_url)
        if not html:
            return []
        
        # Extract strain URLs from product links
        urls = []
        patterns = [
            r'href="(/cannabis-seeds/[^"]+)"',
            r'href="(https://dutch-passion\.us/cannabis-seeds/[^"]+)"'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, html)
            for match in matches:
                if match.startswith('/'):
                    url = f"https://dutch-passion.us{match}"
                else:
                    url = match
                if url not in urls:
                    urls.append(url)
        
        print(f"Found {len(urls)} strain URLs")
        return urls

    def method_1_structured_extraction(self, html):
        """Extract from structured HTML tables"""
        data = {}
        
        # Extract from specification tables
        table_patterns = {
            'genetics': r'<td[^>]*>Genetics[^<]*</td>\s*<td[^>]*>([^<]+)</td>',
            'flowering_time': r'<td[^>]*>Flowering[^<]*</td>\s*<td[^>]*>([^<]+)</td>',
            'thc_content': r'<td[^>]*>THC[^<]*</td>\s*<td[^>]*>([^<]+)</td>',
            'cbd_content': r'<td[^>]*>CBD[^<]*</td>\s*<td[^>]*>([^<]+)</td>',
            'yield': r'<td[^>]*>Yield[^<]*</td>\s*<td[^>]*>([^<]+)</td>',
            'height': r'<td[^>]*>Height[^<]*</td>\s*<td[^>]*>([^<]+)</td>',
            'seed_type': r'<td[^>]*>Type[^<]*</td>\s*<td[^>]*>([^<]+)</td>'
        }
        
        for field, pattern in table_patterns.items():
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                data[field] = match.group(1).strip()
        
        if data:
            self.stats['method_usage']['structured'] += 1
        
        return data

    def method_2_description_mining(self, html):
        """Mine data from product descriptions"""
        data = {}
        
        # Extract description text
        desc_patterns = [
            r'<div[^>]*class="[^"]*description[^"]*"[^>]*>(.*?)</div>',
            r'<p[^>]*class="[^"]*product-description[^"]*"[^>]*>(.*?)</p>'
        ]
        
        description = ""
        for pattern in desc_patterns:
            match = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
            if match:
                description = match.group(1)
                break
        
        if description:
            # Extract flowering time
            flowering_match = re.search(r'(\d+)[-\s]*(\d+)?\s*weeks?\s*flower', description, re.IGNORECASE)
            if flowering_match:
                if flowering_match.group(2):
                    data['flowering_time'] = f"{flowering_match.group(1)}-{flowering_match.group(2)} weeks"
                else:
                    data['flowering_time'] = f"{flowering_match.group(1)} weeks"
            
            # Extract THC content
            thc_match = re.search(r'(\d+(?:\.\d+)?)[-\s]*(\d+(?:\.\d+)?)?\s*%\s*THC', description, re.IGNORECASE)
            if thc_match:
                if thc_match.group(2):
                    data['thc_content'] = f"{thc_match.group(1)}-{thc_match.group(2)}%"
                else:
                    data['thc_content'] = f"{thc_match.group(1)}%"
            
            # Extract effects
            effect_keywords = ['euphoric', 'relaxing', 'energetic', 'creative', 'uplifting', 'calming']
            effects = []
            for keyword in effect_keywords:
                if re.search(rf'\b{keyword}\b', description, re.IGNORECASE):
                    effects.append(keyword)
            if effects:
                data['effects'] = ', '.join(effects)
        
        if data:
            self.stats['method_usage']['description'] += 1
        
        return data

    def method_3_advanced_patterns(self, html):
        """Advanced pattern matching for specific data"""
        data = {}
        
        # Detect seed type from URL and content
        if '/autoflower-seeds' in html or 'auto-' in html.lower():
            data['seed_type'] = 'Autoflower'
            data['growth_type'] = 'Autoflower'
        elif '/feminized-seeds' in html or 'feminized' in html.lower():
            data['seed_type'] = 'Feminized'
            data['growth_type'] = 'Photoperiod'
        elif '/regular-seeds' in html:
            data['seed_type'] = 'Regular'
            data['growth_type'] = 'Photoperiod'
        
        # Extract terpene profiles
        terpene_pattern = r'terpene[^:]*:\s*([^<\n]+)'
        terpene_match = re.search(terpene_pattern, html, re.IGNORECASE)
        if terpene_match:
            data['terpene_profile'] = terpene_match.group(1).strip()
        
        # Extract awards
        award_pattern = r'(cup|award|winner|champion)[^<\n]*([^<\n]{10,50})'
        award_match = re.search(award_pattern, html, re.IGNORECASE)
        if award_match:
            data['awards'] = award_match.group(0).strip()
        
        if data:
            self.stats['method_usage']['patterns'] += 1
        
        return data

    def method_4_universal_fallback(self, html, url):
        """Universal fallback extraction"""
        data = {}
        
        # Extract strain name from URL
        strain_match = re.search(r'/cannabis-seeds/([^/?]+)', url)
        if strain_match:
            strain_name = strain_match.group(1).replace('-', ' ').title()
            data['strain_name'] = strain_name
        
        # Extract title
        title_match = re.search(r'<title>([^<]+)</title>', html, re.IGNORECASE)
        if title_match:
            title = title_match.group(1).strip()
            if 'Dutch Passion' in title:
                data['page_title'] = title
        
        # Set hardcoded values
        data['seed_bank'] = SEED_BANK
        data['breeder_name'] = BREEDER_NAME
        data['source_url'] = url
        data['scraped_at'] = datetime.utcnow().isoformat()
        
        self.stats['method_usage']['fallback'] += 1
        return data

    def extract_strain_data(self, url):
        """Extract comprehensive strain data using 4 methods"""
        print(f"Processing: {url}")
        
        html = self._brightdata_request(url)
        if not html:
            return None
        
        # Apply all 4 methods
        strain_data = {}
        
        # Method 1: Structured extraction
        structured_data = self.method_1_structured_extraction(html)
        strain_data.update(structured_data)
        
        # Method 2: Description mining
        description_data = self.method_2_description_mining(html)
        strain_data.update(description_data)
        
        # Method 3: Advanced patterns
        pattern_data = self.method_3_advanced_patterns(html)
        strain_data.update(pattern_data)
        
        # Method 4: Universal fallback (always runs)
        fallback_data = self.method_4_universal_fallback(html, url)
        strain_data.update(fallback_data)
        
        # Calculate quality score
        quality_score = self._calculate_quality_score(strain_data)
        strain_data['quality_score'] = quality_score
        
        # Update quality distribution
        if quality_score >= 85:
            self.stats['quality_distribution']['premium'] += 1
        elif quality_score >= 60:
            self.stats['quality_distribution']['high'] += 1
        elif quality_score >= 40:
            self.stats['quality_distribution']['medium'] += 1
        else:
            self.stats['quality_distribution']['basic'] += 1
        
        self.stats['total_processed'] += 1
        self.stats['successful_extractions'] += 1
        
        return strain_data

    def _calculate_quality_score(self, data):
        """Calculate data quality score (0-100)"""
        core_fields = ['strain_name', 'genetics', 'flowering_time', 'thc_content', 'seed_type']
        bonus_fields = ['cbd_content', 'yield', 'height', 'effects', 'terpene_profile', 'awards']
        
        score = 0
        
        # Core fields (20 points each)
        for field in core_fields:
            if field in data and data[field]:
                score += 20
        
        # Bonus fields (5 points each, max 30)
        bonus_score = 0
        for field in bonus_fields:
            if field in data and data[field]:
                bonus_score += 5
        score += min(bonus_score, 30)
        
        return min(score, 100)

    def save_to_dynamodb(self, strain_data):
        """Save strain data to DynamoDB"""
        try:
            # Create composite key
            strain_key = f"{strain_data.get('strain_name', 'unknown')}_{BREEDER_NAME}".lower().replace(' ', '_')
            
            item = {
                'strain_id': strain_key,
                **strain_data
            }
            
            self.table.put_item(Item=item)
            print(f"Saved: {strain_data.get('strain_name', 'Unknown')}")
            return True
            
        except Exception as e:
            print(f"DynamoDB error: {e}")
            return False

    def run_scraper(self):
        """Main scraper execution"""
        print(f"Starting Dutch Passion 4-Method Scraper")
        print(f"Target: {len(CATEGORIES)} categories")
        
        all_urls = []
        
        # Collect all strain URLs
        for category in CATEGORIES:
            urls = self.extract_strain_urls(category)
            all_urls.extend(urls)
            time.sleep(2)
        
        # Remove duplicates
        unique_urls = list(set(all_urls))
        print(f"Total unique strains to process: {len(unique_urls)}")
        
        # Process each strain
        for i, url in enumerate(unique_urls, 1):
            print(f"\n[{i}/{len(unique_urls)}] Processing strain...")
            
            strain_data = self.extract_strain_data(url)
            if strain_data:
                self.save_to_dynamodb(strain_data)
            
            # Rate limiting
            time.sleep(1)
        
        # Print final stats
        self._print_final_stats()

    def _print_final_stats(self):
        """Print comprehensive execution statistics"""
        print(f"\nDUTCH PASSION SCRAPING COMPLETE")
        print(f"Total Processed: {self.stats['total_processed']}")
        print(f"Successful: {self.stats['successful_extractions']}")
        print(f"Success Rate: {(self.stats['successful_extractions']/max(self.stats['total_processed'],1)*100):.1f}%")
        
        print(f"\nMethod Usage:")
        for method, count in self.stats['method_usage'].items():
            print(f"  {method.title()}: {count}")
        
        print(f"\nQuality Distribution:")
        for quality, count in self.stats['quality_distribution'].items():
            print(f"  {quality.title()}: {count}")

if __name__ == "__main__":
    scraper = DutchPassionScraper()
    scraper.run_scraper()