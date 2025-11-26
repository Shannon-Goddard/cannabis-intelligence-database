#!/usr/bin/env python3
import requests
import json
import boto3

# Get credentials
secrets_client = boto3.client('secretsmanager', region_name='us-east-1')
response = secrets_client.get_secret_value(SecretId='cannabis-brightdata-api')
credentials = json.loads(response['SecretString'])

# Test with longer timeout and wait
test_url = "https://www.cannabis-seeds-bank.co.uk/feminized-seeds/cat_106"
api_url = "https://api.brightdata.com/request"
headers = {"Authorization": f"Bearer {credentials['api_key']}"}
payload = {
    "zone": "cannabis_unlocker",
    "url": test_url,
    "format": "raw"
}

print(f"Testing: {test_url}")
print("Making request...")

try:
    response = requests.post(api_url, headers=headers, json=payload, timeout=300)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        html = response.text
        print(f"Response length: {len(html)} characters")
        
        # Check for product links
        if '/prod_' in html:
            prod_count = html.count('/prod_')
            print(f"Found {prod_count} product references")
        else:
            print("No product links found")
            
        # Show first 500 chars
        print("\nFirst 500 characters:")
        print(html[:500])
        
    else:
        print(f"Error: {response.text}")
        
except Exception as e:
    print(f"Request failed: {e}")