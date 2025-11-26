#!/usr/bin/env python3
"""
Great Lakes Genetics - Enhanced 4-Method Scraper
Target: 200+ US boutique breeder strains with 95%+ success rate
Hardcoded: seed_bank as 'Great Lakes Genetics'
"""

import json
import boto3
import requests
import time
import re
from bs4 import BeautifulSoup
from decimal import Decimal
from datetime import datetime

class GreatLakesGeneticsEnhanced4MethodScraper:
    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        self.table = self.dynamodb.Table('cannabis-strains-universal')
        self.secrets_client = boto3.client('secretsmanager', region_name='us-east-1')
        self.brightdata_config = self._get_brightdata_credentials()
        
        # Success tracking
        self.total_processed = 0
        self.successful_extractions = 0
        self.method_stats = {'structured': 0, 'description': 0, 'patterns': 0, 'fallback': 0}
        
    def _get_brightdata_credentials(self):
        response = self.secrets_client.get_secret_value(SecretId='cannabis-brightdata-api')
        return json.loads(response['SecretString'])
    
    def _brightdata_request(self, url):
        api_url = "https://api.brightdata.com/request"
        headers = {"Authorization": f"Bearer {self.brightdata_config['api_key']}"}
        payload = {"zone": self.brightdata_config['zone'], "url": url, "format": "raw"}
        
        response = requests.post(api_url, headers=headers, json=payload, timeout=30)
        return response.text if response.status_code == 200 else None

    def method1_structured_extraction(self, soup, url):
        """Method 1: Great Lakes Genetics .et_pb_module_inner container extraction"""
        data = {}
        
        # Target the main container
        container = soup.find('div', class_='et_pb_module_inner')
        if container:
            # Extract strain name and breeder from H3
            h3_tag = container.find('h3')
            if h3_tag:
                h3_text = h3_tag.get_text().strip()
                # Parse format: "Breeder - Strain Name (pack info)"
                if ' - ' in h3_text:
                    breeder_part, strain_part = h3_text.split(' - ', 1)
                    data['breeder_name'] = breeder_part.strip()
                    # Remove pack info from strain name
                    strain_name = strain_part.split(' (')[0].strip()
                    data['strain_name'] = strain_name
            
            # Extract structured fields from paragraphs
            paragraphs = container.find_all('p')
            for p in paragraphs:
                # Find all strong tags (field labels)
                strong_tags = p.find_all('strong')
                for strong in strong_tags:
                    label = strong.get_text().strip().rstrip(':')
                    
                    # Get the value after the strong tag
                    next_sibling = strong.next_sibling
                    value = ""
                    
                    # Handle different sibling types
                    if next_sibling:
                        if hasattr(next_sibling, 'get_text'):
                            value = next_sibling.get_text().strip()
                        else:
                            value = str(next_sibling).strip()
                        
                        # Clean up the value
                        value = value.lstrip(': ').strip()
                        
                        # If value is empty, look for span after strong
                        if not value:
                            next_span = strong.find_next_sibling('span')
                            if next_span:
                                value = next_span.get_text().strip()
                    
                    # Map Great Lakes Genetics fields
                    field_map = {
                        'Genetics': 'genetics',
                        'Seeds in pack': 'seeds_in_pack',
                        'Sex': 'sex',
                        'Type': 'strain_type',
                        'Yield': 'yield',
                        'Flowering Time': 'flowering_time',
                        'Area (Indoor, Outdoor, Both)': 'growing_area',
                        'Notes': 'cultivation_notes'
                    }
                    
                    if label in field_map and value:
                        data[field_map[label]] = value
        
        return data

    def method2_description_mining(self, soup, url):
        """Method 2: Mine Great Lakes Genetics Notes section for detailed information"""
        data = {}
        
        # Look for Notes section and other descriptive content
        desc_selectors = [
            'div.et_pb_module_inner',
            'div.product-description',
            'div.strain-info'
        ]
        
        about_parts = []
        for selector in desc_selectors:
            elements = soup.select(selector)
            for element in elements:
                text = element.get_text().strip()
                if text and len(text) > 100:  # Substantial content
                    about_parts.append(text)
        
        if about_parts:
            full_text = ' '.join(about_parts)
            data['about_info'] = full_text
            
            # Extract specific patterns from Notes section
            patterns = {
                'effects_pattern': r'(?:euphoric|creative|stoned|relaxing|uplifting|energetic|calming)[^.]*',
                'aroma_pattern': r'(?:nose|aroma|smell)[^.]*?(?:spicy|hash|lemon|fuel|sweet|earthy|pine)[^.]*',
                'structure_pattern': r'(?:structure|tree|bush|plant)[^.]*?(?:christmas|uniform|branching)[^.]*',
                'resin_pattern': r'(?:resin|sticky|trichome)[^.]*?(?:production|impressive|coverage)[^.]*'
            }
            
            for key, pattern in patterns.items():
                matches = re.findall(pattern, full_text, re.IGNORECASE)
                if matches:
                    data[key] = '; '.join(matches[:3])  # Limit to 3 matches
        
        return data

    def method3_advanced_patterns(self, soup, url):
        """Method 3: Great Lakes Genetics specific patterns"""
        data = {}
        
        # Great Lakes Genetics is always the seed bank
        data['seed_bank'] = 'Great Lakes Genetics'
        
        # Extract strain name from URL if not found
        if 'strain_name' not in data:
            path_parts = url.split('/')
            for part in reversed(path_parts):
                if part and 'product' in url and len(part) > 5:
                    strain_name = part.replace('-', ' ').title()
                    # Clean common suffixes
                    strain_name = re.sub(r'\s+(Auto|Autoflower|Fem|Feminized|Regular|Seeds?)$', '', strain_name, re.IGNORECASE)
                    data['strain_name'] = strain_name.strip()
                    break
        
        # Detect seed type from content
        page_text = soup.get_text().lower()
        if 'autoflower' in page_text or 'auto' in page_text:
            data['growth_type'] = 'Autoflower'
            data['seed_type'] = 'Feminized'  # Most autos are feminized
        elif 'feminized' in page_text or 'fem' in page_text:
            data['seed_type'] = 'Feminized'
            data['growth_type'] = 'Photoperiod'
        elif 'regular' in page_text or 'reg' in page_text:
            data['seed_type'] = 'Regular'
            data['growth_type'] = 'Photoperiod'
        
        # Extract US breeder indicators
        us_breeders = [
            'forest', 'jaws', 'cannarado', 'ethos', 'in house', 'compound',
            'thug pug', 'exotic genetix', 'oni seed', 'clearwater', 'bloom'
        ]
        
        page_text_lower = soup.get_text().lower()
        for breeder in us_breeders:
            if breeder in page_text_lower:
                data['us_genetics'] = True
                break
        
        return data

    def method4_fallback_extraction(self, soup, url):
        """Method 4: Universal fallback for Great Lakes Genetics"""
        data = {}
        
        # Extract strain name from page title if not found
        if 'strain_name' not in data:
            title = soup.find('title')
            if title:
                title_text = title.get_text().strip()
                title_parts = title_text.split(' - ')
                if title_parts:
                    potential_strain = title_parts[0].strip()
                    potential_strain = re.sub(r'\s+(Auto|Feminized|Regular|Seeds?)$', '', potential_strain, re.IGNORECASE)
                    data['strain_name'] = potential_strain
        
        # Meta description fallback
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and not data.get('about_info'):
            data['about_info'] = meta_desc.get('content', '')
        
        # Extract any H1-H6 headings for additional context
        headings = []
        for i in range(1, 7):
            h_tags = soup.find_all(f'h{i}')
            for h in h_tags:
                heading_text = h.get_text().strip()
                if heading_text and len(heading_text) > 5:
                    headings.append(heading_text)
        
        if headings and not data.get('strain_name'):
            # Use first substantial heading as strain name
            data['strain_name'] = headings[0]
        
        return data

    def apply_4_methods(self, html_content, url):
        """Apply all 4 extraction methods with Great Lakes Genetics hardcoded values"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        strain_data = {
            'seed_bank': 'Great Lakes Genetics',
            'source_url': url,
            'extraction_methods_used': []
        }
        
        # Method 1: Structured extraction
        method1_data = self.method1_structured_extraction(soup, url)
        if method1_data:
            strain_data.update(method1_data)
            strain_data['extraction_methods_used'].append('structured')
            self.method_stats['structured'] += 1
        
        # Method 2: Description mining
        method2_data = self.method2_description_mining(soup, url)
        if method2_data:
            strain_data.update(method2_data)
            strain_data['extraction_methods_used'].append('description')
            self.method_stats['description'] += 1
        
        # Method 3: Advanced patterns
        method3_data = self.method3_advanced_patterns(soup, url)
        if method3_data:
            strain_data.update(method3_data)
            strain_data['extraction_methods_used'].append('patterns')
            self.method_stats['patterns'] += 1
        
        # Method 4: Fallback extraction
        method4_data = self.method4_fallback_extraction(soup, url)
        if method4_data:
            strain_data.update(method4_data)
            strain_data['extraction_methods_used'].append('fallback')
            self.method_stats['fallback'] += 1
        
        # Calculate quality score
        strain_data['data_completeness_score'] = self.calculate_quality_score(strain_data)
        strain_data['quality_tier'] = self.determine_quality_tier(strain_data['data_completeness_score'])
        strain_data['field_count'] = len([v for v in strain_data.values() if v])
        
        # Create strain ID
        strain_name = strain_data.get('strain_name', 'Unknown')
        breeder_name = strain_data.get('breeder_name', 'Unknown')
        strain_data['strain_id'] = self.create_strain_id(strain_name, breeder_name)
        
        # Add timestamps
        now = datetime.utcnow().isoformat() + 'Z'
        strain_data['created_at'] = now
        strain_data['updated_at'] = now
        
        return strain_data

    def calculate_quality_score(self, strain_data):
        """Calculate weighted quality score optimized for Great Lakes Genetics"""
        field_weights = {
            # Core fields (required)
            'strain_name': 10,
            'seed_bank': 10,
            
            # Great Lakes Genetics strengths
            'breeder_name': 10,              # Clear breeder attribution
            'genetics': 9,                   # Parent strain lineage
            'cultivation_notes': 9,          # Comprehensive growing info
            'flowering_time': 8,             # Cultivation timing
            'yield': 8,                      # Production data
            'strain_type': 7,                # Cannabis classification
            'sex': 7,                        # Seed type
            'growing_area': 6,               # Indoor/Outdoor suitability
            'seeds_in_pack': 5,              # Pack information
            
            # Enhanced fields from Notes mining
            'effects_pattern': 7,            # Experience profiles
            'aroma_pattern': 6,              # Scent profiles
            'structure_pattern': 5,          # Growth patterns
            'resin_pattern': 5,              # Quality indicators
            
            # Additional info
            'about_info': 6,                 # Detailed descriptions
            'growth_type': 5,                # Auto/Photo classification
            'seed_type': 5,                  # Feminized/Regular
            'us_genetics': 3                 # US breeder indicator
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
        combined = f"{strain_name}-{breeder_name}-glg".lower()
        combined = re.sub(r'[^a-z0-9-]', '', combined.replace(' ', '-'))
        return combined[:50]

    def collect_strain_urls(self):
        """Phase 1: Collect all strain URLs from Great Lakes Genetics breeders page"""
        print("PHASE 1: Collecting Great Lakes Genetics strain URLs...")
        
        breeders_url = "https://www.greatlakesgenetics.com/breeders/"
        
        print(f"Scraping breeders page: {breeders_url}")
        
        html = self._brightdata_request(breeders_url)
        if not html:
            print(f"Failed to fetch breeders page: {breeders_url}")
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        strain_urls = []
        
        # Extract product URLs
        for link in soup.find_all('a', href=True):
            href = link.get('href')
            if href and '/product/' in href:
                if href.startswith('/'):
                    full_url = f"https://www.greatlakesgenetics.com{href}"
                else:
                    full_url = href
                strain_urls.append(full_url)
        
        unique_urls = list(set(strain_urls))  # Remove duplicates
        print(f"Total unique strains found: {len(unique_urls)}")
        return unique_urls

    def scrape_strain_details(self, strain_urls):
        """Phase 2: Extract detailed strain data using 4-method approach"""
        print(f"\nPHASE 2: Scraping {len(strain_urls)} strains with 4-method extraction...")
        
        for i, url in enumerate(strain_urls, 1):
            self.total_processed += 1
            print(f"\n[{i}/{len(strain_urls)}] {url}")
            
            html = self._brightdata_request(url)
            if html:
                strain_data = self.apply_4_methods(html, url)
                
                # Quality validation (minimum 20% score)
                if strain_data['data_completeness_score'] >= 20:
                    try:
                        # Convert Decimal for DynamoDB
                        strain_data['data_completeness_score'] = Decimal(str(strain_data['data_completeness_score']))
                        
                        self.table.put_item(Item=strain_data)
                        self.successful_extractions += 1
                        
                        print(f"  SUCCESS: {strain_data.get('strain_name', 'Unknown')} - {strain_data.get('breeder_name', 'Unknown Breeder')}")
                        print(f"     Quality: {strain_data['quality_tier']} ({float(strain_data['data_completeness_score']):.1f}%)")
                        print(f"     Methods: {', '.join(strain_data['extraction_methods_used'])}")
                        
                        # Show key Great Lakes Genetics fields if present
                        if strain_data.get('genetics'):
                            print(f"     Genetics: {strain_data['genetics']}")
                        if strain_data.get('flowering_time'):
                            print(f"     Flowering: {strain_data['flowering_time']}")
                        
                    except Exception as e:
                        print(f"  STORAGE FAILED: {e}")
                else:
                    print(f"  LOW QUALITY: {strain_data['data_completeness_score']:.1f}% - skipped")
            else:
                print(f"  FETCH FAILED")
            
            time.sleep(1)

    def print_final_stats(self):
        """Print comprehensive scraping statistics"""
        success_rate = (self.successful_extractions / self.total_processed * 100) if self.total_processed > 0 else 0
        
        print(f"\nGREAT LAKES GENETICS ENHANCED SCRAPING COMPLETE!")
        print(f"FINAL STATISTICS:")
        print(f"   Total Processed: {self.total_processed}")
        print(f"   Successful: {self.successful_extractions}")
        print(f"   Success Rate: {success_rate:.1f}%")
        print(f"\nMETHOD USAGE:")
        for method, count in self.method_stats.items():
            print(f"   {method.title()}: {count} strains")
        print(f"\nCost: ~${self.total_processed * 0.0015:.2f} (BrightData)")
        print(f"Unique Features: US boutique breeders, detailed cultivation notes, breeder attribution")

def main():
    scraper = GreatLakesGeneticsEnhanced4MethodScraper()
    
    # Phase 1: Collect URLs
    strain_urls = scraper.collect_strain_urls()
    
    if not strain_urls:
        print("No strain URLs found. Exiting.")
        return
    
    # Phase 2: Scrape details
    scraper.scrape_strain_details(strain_urls)
    
    # Final statistics
    scraper.print_final_stats()

if __name__ == "__main__":
    print("GREAT LAKES GENETICS - ENHANCED 4-METHOD SCRAPER")
    print("Target: 200+ US boutique breeder strains with 95%+ success rate")
    print("Methods: Structured + Description + Patterns + Fallback")
    print("Hardcoded: seed_bank as 'Great Lakes Genetics'")
    print("Specializing in US genetics and detailed cultivation data extraction")
    print("\n" + "="*60)
    
    main()