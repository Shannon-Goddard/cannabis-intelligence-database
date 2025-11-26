#!/usr/bin/env python3

import requests
import json
import boto3
from bs4 import BeautifulSoup
import re

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

def test_product_extraction():
    """Test product data extraction"""
    api_key = get_brightdata_credentials()
    if not api_key:
        return
    
    test_url = "https://multiversebeans.com/product/blue-dream-full-term-atlas-seeds-photoperiod-cannabis-seeds-female/"
    print(f"Testing product: {test_url}")
    
    html = scrape_with_brightdata(test_url, api_key)
    if not html:
        print("Failed to get content")
        return
    
    print(f"Got {len(html)} characters")
    
    soup = BeautifulSoup(html, 'html.parser')
    
    # Extract title
    title_selectors = ['h1.product_title', 'h1', '.product-title']
    for selector in title_selectors:
        title_elem = soup.select_one(selector)
        if title_elem:
            print(f"Title: {title_elem.get_text(strip=True)}")
            break
    
    # Look for product details/specifications
    print("\nLooking for product details...")
    
    # Check for tabs or sections
    tabs = soup.select('.woocommerce-tabs, .product-tabs, .tab-content')
    if tabs:
        print("Found tabs/sections")
        for tab in tabs:
            print(f"Tab content preview: {tab.get_text()[:200]}...")
    
    # Check for description
    desc = soup.select_one('.woocommerce-product-details__short-description, .product-description, .entry-summary')
    if desc:
        print(f"\nDescription: {desc.get_text()[:300]}...")
    
    # Look for specifications table
    tables = soup.select('table')
    for i, table in enumerate(tables):
        print(f"\nTable {i+1}:")
        rows = table.select('tr')
        for row in rows[:5]:  # First 5 rows
            cells = [cell.get_text(strip=True) for cell in row.select('td, th')]
            if cells:
                print(f"  {' | '.join(cells)}")
    
    # Search for key terms in full text
    text_content = soup.get_text()
    
    print(f"\nSearching for key terms in {len(text_content)} characters...")
    
    # Genetics
    genetics_match = re.search(r'(\d+)%?\s*(sativa|indica)', text_content, re.IGNORECASE)
    if genetics_match:
        print(f"Genetics found: {genetics_match.group()}")
    
    # Flowering
    flowering_match = re.search(r'flowering[^\d]*(\d+)', text_content, re.IGNORECASE)
    if flowering_match:
        print(f"Flowering found: {flowering_match.group()}")
    
    # THC
    thc_match = re.search(r'thc[^\d]*(\d+)', text_content, re.IGNORECASE)
    if thc_match:
        print(f"THC found: {thc_match.group()}")

if __name__ == "__main__":
    test_product_extraction()