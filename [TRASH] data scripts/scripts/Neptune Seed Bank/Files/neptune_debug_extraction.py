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

# Test a failing URL
credentials = get_brightdata_credentials()
test_url = "https://neptuneseedbank.com/product/raw-genetics-puffo-gelato/"

html = brightdata_request(test_url, credentials)
if html:
    soup = BeautifulSoup(html, 'html.parser')
    
    print("=== TITLE TAGS ===")
    for tag in soup.find_all(['h1', 'h2', 'title']):
        print(f"{tag.name}: {tag.get_text().strip()}")
    
    print("\n=== PRODUCT TITLE ===")
    product_title = soup.find('h2', class_='product-title')
    if product_title:
        print(f"Product title: {product_title.get_text().strip()}")
    
    print("\n=== ATTRIBUTE ITEMS ===")
    for item in soup.find_all('div', class_='attribute-item'):
        label = item.find('span', class_='attribute-label')
        value = item.find('span', class_='attribute-value')
        if label and value:
            print(f"{label.get_text().strip()}: {value.get_text().strip()}")
    
    print("\n=== DESCRIPTION ===")
    description = soup.find('div', id='description')
    if description:
        print(description.get_text()[:200] + "...")
else:
    print("Failed to fetch page")