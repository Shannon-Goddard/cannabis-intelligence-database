import requests
import json
import boto3
from bs4 import BeautifulSoup

def get_brightdata_credentials():
    secrets_client = boto3.client('secretsmanager', region_name='us-east-1')
    response = secrets_client.get_secret_value(SecretId='cannabis-brightdata-api')
    return json.loads(response['SecretString'])

def brightdata_request(url, credentials):
    api_url = "https://api.brightdata.com/request"
    headers = {"Authorization": f"Bearer {credentials['api_key']}"}
    payload = {"zone": credentials['zone'], "url": url, "format": "raw"}
    
    response = requests.post(api_url, headers=headers, json=payload)
    if response.status_code == 200:
        return response.text
    return None

# Test one page to see structure
credentials = get_brightdata_credentials()
test_url = "https://neptuneseedbank.com/product-category/feminized-seeds/"
html = brightdata_request(test_url, credentials)

if html:
    soup = BeautifulSoup(html, 'html.parser')
    
    # Look for all links
    print("All product-related links found:")
    for link in soup.find_all('a', href=True):
        href = link.get('href')
        if href and ('product' in href or 'strain' in href):
            print(f"  {href}")
    
    # Look for WooCommerce product containers
    print("\nProduct containers:")
    products = soup.find_all(['div', 'li'], class_=lambda x: x and any(term in x for term in ['product', 'woocommerce']))
    for product in products[:5]:
        print(f"  Class: {product.get('class')}")
        link = product.find('a', href=True)
        if link:
            print(f"    Link: {link.get('href')}")
else:
    print("Failed to fetch page")