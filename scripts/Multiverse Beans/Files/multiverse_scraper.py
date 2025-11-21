#!/usr/bin/env python3

import requests
import json
import boto3
from bs4 import BeautifulSoup
import time
import re
from urllib.parse import urljoin, urlparse
from decimal import Decimal

def get_brightdata_credentials():
    """Get BrightData credentials from AWS Secrets Manager"""
    try:
        secrets_client = boto3.client('secretsmanager', region_name='us-east-1')
        response = secrets_client.get_secret_value(SecretId='cannabis-brightdata-api')
        credentials = json.loads(response['SecretString'])
        return credentials['api_key']
    except Exception as e:
        print(f"Error getting credentials: {e}")
        return None

def get_dynamodb_table():
    """Get DynamoDB table"""
    try:
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        return dynamodb.Table('cannabis-strains')
    except Exception as e:
        print(f"Error connecting to DynamoDB: {e}")
        return None

def scrape_with_brightdata(url, api_key):
    """Scrape URL using BrightData Web Unlocker API"""
    api_url = "https://api.brightdata.com/request"
    headers = {"Authorization": f"Bearer {api_key}"}
    payload = {
        "zone": "cannabis_strain_scraper",
        "url": url,
        "format": "raw"
    }
    
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

def extract_product_urls(html, base_url):
    """Extract product URLs from category page"""
    soup = BeautifulSoup(html, 'html.parser')
    urls = []
    
    # Look for product links
    selectors = [
        'a[href*="/product/"]',
        '.product a',
        '.woocommerce-loop-product__link',
        'h2.woocommerce-loop-product__title a'
    ]
    
    for selector in selectors:
        links = soup.select(selector)
        if links:
            for link in links:
                href = link.get('href')
                if href and '/product/' in href:
                    full_url = urljoin(base_url, href)
                    if full_url not in urls:
                        urls.append(full_url)
            break
    
    return urls

def extract_strain_data(html, url):
    """Extract strain data from product page"""
    soup = BeautifulSoup(html, 'html.parser')
    
    # Extract strain name from title or h1
    strain_name = None
    title_selectors = ['h1.product_title', 'h1', '.product-title']
    for selector in title_selectors:
        title_elem = soup.select_one(selector)
        if title_elem:
            strain_name = title_elem.get_text(strip=True)
            break
    
    if not strain_name:
        return None
    
    # Clean strain name
    strain_name = re.sub(r'\s*-\s*.*?(seeds|cannabis).*$', '', strain_name, flags=re.IGNORECASE)
    strain_name = strain_name.strip()
    
    # Extract breeder from title
    breeder_name = "Unknown"
    
    # Look for breeder in title format: "BREEDER | STRAIN | TYPE"
    if '|' in strain_name:
        parts = [p.strip() for p in strain_name.split('|')]
        if len(parts) >= 2:
            # First part is usually breeder
            potential_breeder = parts[0].strip()
            if len(potential_breeder) < 50:  # Reasonable breeder name
                breeder_name = potential_breeder
                # Second part is strain name
                strain_name = parts[1].strip() if len(parts) > 1 else strain_name
    
    # Look for breeder in product details
    breeder_patterns = [
        r'breeder[:\s]+([^,\n]+)',
        r'by\s+([^,\n]+)',
        r'from\s+([^,\n]+)'
    ]
    
    text_content = soup.get_text()
    for pattern in breeder_patterns:
        match = re.search(pattern, text_content, re.IGNORECASE)
        if match:
            potential_breeder = match.group(1).strip()
            if len(potential_breeder) < 50:  # Reasonable breeder name length
                breeder_name = potential_breeder
                break
    
    # Extract specifications
    genetics_sativa = None
    genetics_indica = None
    flowering_days = None
    thc_min = None
    thc_max = None
    
    # Look for genetics info
    genetics_patterns = [
        r'(\d+)%?\s*sativa[^\d]*(\d+)%?\s*indica',
        r'(\d+)%?\s*indica[^\d]*(\d+)%?\s*sativa',
        r'sativa[^\d]*(\d+)%',
        r'indica[^\d]*(\d+)%'
    ]
    
    for pattern in genetics_patterns:
        match = re.search(pattern, text_content, re.IGNORECASE)
        if match:
            if 'sativa' in pattern and 'indica' in pattern:
                if 'sativa.*indica' in pattern:
                    genetics_sativa = int(match.group(1))
                    genetics_indica = int(match.group(2))
                else:
                    genetics_indica = int(match.group(1))
                    genetics_sativa = int(match.group(2))
            elif 'sativa' in pattern:
                genetics_sativa = int(match.group(1))
                genetics_indica = 100 - genetics_sativa
            elif 'indica' in pattern:
                genetics_indica = int(match.group(1))
                genetics_sativa = 100 - genetics_indica
            break
    
    # Look for flowering time
    flowering_patterns = [
        r'flowering[^\d]*(\d+)[^\d]*(\d+)?\s*(?:days?|weeks?)',
        r'(\d+)[^\d]*(\d+)?\s*(?:days?|weeks?).*flowering',
        r'harvest.*(\d+)\s*(?:days?|weeks?)'
    ]
    
    for pattern in flowering_patterns:
        match = re.search(pattern, text_content, re.IGNORECASE)
        if match:
            days = int(match.group(1))
            if 'week' in match.group(0).lower():
                days *= 7
            if 30 <= days <= 120:  # Reasonable flowering range
                flowering_days = days
                break
    
    # Look for THC content
    thc_patterns = [
        r'thc[^\d]*(\d+(?:\.\d+)?)%?[^\d]*(\d+(?:\.\d+)?)?%?',
        r'(\d+(?:\.\d+)?)%?[^\d]*(\d+(?:\.\d+)?)?%?.*thc'
    ]
    
    for pattern in thc_patterns:
        match = re.search(pattern, text_content, re.IGNORECASE)
        if match:
            thc_min = Decimal(str(match.group(1)))
            if match.group(2):
                thc_max = Decimal(str(match.group(2)))
            else:
                thc_max = thc_min
            break
    
    return {
        'strain_name': strain_name,
        'breeder_name': breeder_name,
        'genetics_sativa': genetics_sativa,
        'genetics_indica': genetics_indica,
        'flowering_days_indoor': flowering_days,
        'thc_min': thc_min,
        'thc_max': thc_max,
        'source_url': url,
        'source_site': 'Multiverse Beans'
    }

def save_to_dynamodb(strain_data, table):
    """Save strain data to DynamoDB"""
    try:
        # Create composite key
        strain_key = f"{strain_data['strain_name']}_{strain_data['breeder_name']}"
        
        item = {
            'strain_id': strain_key.lower().replace(' ', '_').replace('-', '_'),
            **strain_data,
            'created_at': int(time.time())
        }
        
        table.put_item(Item=item)
        return True
    except Exception as e:
        print(f"DynamoDB error: {e}")
        return False

def scrape_multiverse_beans():
    """Main scraping function"""
    api_key = get_brightdata_credentials()
    table = get_dynamodb_table()
    
    if not api_key or not table:
        return
    
    # Category URLs - start with photoperiod since autoflower was partially completed
    category_urls = [
        "https://multiversebeans.com/flowering-type/photoperiod/"
    ]
    
    all_product_urls = []
    
    # Phase 1: Collect all product URLs
    for category_url in category_urls:
        print(f"\nScraping category: {category_url}")
        
        page = 1
        while True:
            if page == 1:
                url = category_url
            else:
                url = f"{category_url}page/{page}/"
            
            print(f"  Page {page}: {url}")
            html = scrape_with_brightdata(url, api_key)
            
            if not html or len(html) < 1000:
                print(f"    No content or blocked, stopping at page {page}")
                break
            
            urls = extract_product_urls(html, "https://multiversebeans.com")
            if not urls:
                print(f"    No products found, stopping at page {page}")
                break
            
            print(f"    Found {len(urls)} products")
            all_product_urls.extend(urls)
            
            page += 1
            time.sleep(2)  # Rate limiting
            
            if page > 50:  # Safety limit
                break
    
    print(f"\nTotal product URLs collected: {len(all_product_urls)}")
    
    # Phase 2: Scrape individual products
    successful = 0
    failed = 0
    
    for i, product_url in enumerate(all_product_urls, 1):
        print(f"\n[{i}/{len(all_product_urls)}] {product_url}")
        
        html = scrape_with_brightdata(product_url, api_key)
        if not html:
            print("  Failed to get content")
            failed += 1
            continue
        
        strain_data = extract_strain_data(html, product_url)
        if not strain_data:
            print("  Failed to extract strain data")
            failed += 1
            continue
        
        print(f"  Strain: {strain_data['strain_name']} by {strain_data['breeder_name']}")
        
        if save_to_dynamodb(strain_data, table):
            print("  + Saved to database")
            successful += 1
        else:
            print("  - Failed to save")
            failed += 1
        
        time.sleep(1)  # Rate limiting
    
    print(f"\nScraping complete!")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Success rate: {successful/(successful+failed)*100:.1f}%")

if __name__ == "__main__":
    scrape_multiverse_beans()