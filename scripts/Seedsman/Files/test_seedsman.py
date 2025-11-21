#!/usr/bin/env python3
"""Test Seedsman page structure"""

import requests
import json
import boto3
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

# Test autoflower category page
url = "https://www.seedsman.com/us-en/cannabis-seeds/flowering-type/autoflowering-cannabis-seeds"
print(f"Testing: {url}")

html = brightdata_request(url)
if html:
    soup = BeautifulSoup(html, 'html.parser')
    
    # Look for different link patterns
    all_links = soup.find_all('a', href=True)
    strain_links = []
    
    for link in all_links:
        href = link['href']
        if 'seeds' in href and '/us-en/' in href:
            strain_links.append(href)
    
    print(f"Found {len(strain_links)} potential strain links")
    
    # Show first 10 links
    for i, link in enumerate(strain_links[:10]):
        print(f"{i+1}: {link}")
    
    # Save HTML for inspection
    with open('seedsman_page.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("Saved HTML to seedsman_page.html")
else:
    print("Failed to get page")