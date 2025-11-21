#!/usr/bin/env python3
"""Find strain data in Seedsman page"""

import requests
import json
import boto3
import re
from bs4 import BeautifulSoup

# Get BrightData credentials
secrets_client = boto3.client('secretsmanager', region_name='us-east-1')
response = secrets_client.get_secret_value(SecretId='cannabis-brightdata-api')
brightdata_config = json.loads(response['SecretString'])

def brightdata_request(url):
    api_url = "https://api.brightdata.com/request"
    headers = {"Authorization": f"Bearer {brightdata_config['api_key']}"}
    payload = {
        "zone": brightdata_config['zone'],
        "url": url,
        "format": "raw"
    }
    
    response = requests.post(api_url, headers=headers, json=payload, timeout=30)
    if response.status_code == 200:
        return response.text
    return None

# Test strain page
url = "https://www.seedsman.com/us-en/special-queen-1-auto-feminised-seeds-rqs-specq1-auto-fem"
html = brightdata_request(url)

if html:
    # Look for JSON data in script tags
    json_pattern = re.compile(r'window\.__INITIAL_STATE__\s*=\s*({.*?});', re.DOTALL)
    state_pattern = re.compile(r'window\.preloadData\s*=\s*({.*?});', re.DOTALL)
    product_pattern = re.compile(r'"product":\s*({.*?"name".*?})', re.DOTALL)
    
    # Search for various data patterns
    patterns = [
        (r'"Special Queen"', "Special Queen found"),
        (r'"Royal Queen"', "Royal Queen found"),
        (r'"name":\s*"[^"]*Special[^"]*"', "Product name found"),
        (r'"sku":\s*"[^"]*"', "SKU found"),
        (r'"price":\s*\d+', "Price found"),
        (r'"thc":\s*\d+', "THC found"),
        (r'"flowering":\s*\d+', "Flowering found")
    ]
    
    print("Searching for data patterns...")
    for pattern, description in patterns:
        matches = re.findall(pattern, html, re.IGNORECASE)
        if matches:
            print(f"{description}: {matches[:3]}")  # Show first 3 matches
    
    # Look for React component data
    if 'window.preloadData' in html:
        print("\nFound window.preloadData")
        preload_match = state_pattern.search(html)
        if preload_match:
            try:
                preload_data = json.loads(preload_match.group(1))
                print(f"Preload data keys: {list(preload_data.keys())}")
            except:
                print("Could not parse preload data")
    
    # Check if page is fully rendered
    if '<div id="root"></div>' in html and 'React' in html:
        print("\nThis is a React SPA - content loads dynamically")
        print("Need to wait for JavaScript execution or find API endpoints")
    
    # Look for API endpoints
    api_patterns = [
        r'/api/[^"\']*',
        r'/graphql[^"\']*',
        r'\.json[^"\']*'
    ]
    
    print("\nLooking for API endpoints...")
    for pattern in api_patterns:
        matches = re.findall(pattern, html)
        if matches:
            print(f"Found endpoints: {set(matches)}")
    
else:
    print("Failed to get page")