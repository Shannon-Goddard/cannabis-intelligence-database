#!/usr/bin/env python3
"""Analyze Seedsman page structure"""

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

# Test one strain page
url = "https://www.seedsman.com/us-en/special-queen-1-auto-feminised-seeds-rqs-specq1-auto-fem"
print(f"Analyzing: {url}")

html = brightdata_request(url)
if html:
    soup = BeautifulSoup(html, 'html.parser')
    
    print(f"Page title: {soup.title.string if soup.title else 'No title'}")
    
    # Look for h1 tags
    h1_tags = soup.find_all('h1')
    print(f"H1 tags found: {len(h1_tags)}")
    for i, h1 in enumerate(h1_tags):
        print(f"  H1 {i+1}: {h1.get_text().strip()}")
    
    # Look for any text containing strain info
    text_content = soup.get_text()
    if 'special queen' in text_content.lower():
        print("Found 'Special Queen' in page text")
    if 'royal queen' in text_content.lower():
        print("Found 'Royal Queen' in page text")
    if 'auto' in text_content.lower():
        print("Found 'auto' in page text")
    
    # Look for JSON data
    scripts = soup.find_all('script')
    print(f"Script tags found: {len(scripts)}")
    
    for i, script in enumerate(scripts):
        if script.string and 'special' in script.string.lower():
            print(f"Script {i} contains strain data:")
            print(script.string[:200] + "...")
            break
    
    # Save full HTML for inspection
    with open('seedsman_analysis.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("Saved full HTML to seedsman_analysis.html")
    
else:
    print("Failed to get page")