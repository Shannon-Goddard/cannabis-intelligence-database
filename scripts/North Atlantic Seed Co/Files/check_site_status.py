import requests
import json
import boto3
from bs4 import BeautifulSoup
import time

def check_site_status():
    """Check if North Atlantic site is accessible and what's happening"""
    
    # Get BrightData credentials
    secrets_client = boto3.client('secretsmanager', region_name='us-east-1')
    response = secrets_client.get_secret_value(SecretId='cannabis-brightdata-api')
    credentials = json.loads(response['SecretString'])
    
    def brightdata_request(url):
        api_url = "https://api.brightdata.com/request"
        headers = {"Authorization": f"Bearer {credentials['api_key']}"}
        payload = {"zone": credentials['zone'], "url": url, "format": "raw"}
        
        try:
            response = requests.post(api_url, headers=headers, json=payload, timeout=60)
            print(f"BrightData Response Status: {response.status_code}")
            if response.status_code != 200:
                print(f"BrightData Error: {response.text}")
            return response.text if response.status_code == 200 else None
        except Exception as e:
            print(f"BrightData Exception: {e}")
            return None
    
    print("CHECKING NORTH ATLANTIC SITE STATUS")
    print("=" * 40)
    
    # Test main page first
    main_url = "https://www.northatlanticseed.com/"
    print(f"Testing main page: {main_url}")
    
    html = brightdata_request(main_url)
    if html:
        print("SUCCESS: Main page accessible")
        soup = BeautifulSoup(html, 'html.parser')
        title = soup.find('title')
        print(f"Page title: {title.get_text() if title else 'No title'}")
    else:
        print("FAILED: Main page failed")
    
    time.sleep(2)
    
    # Test seeds category page
    seeds_url = "https://www.northatlanticseed.com/seeds/"
    print(f"\nTesting seeds page: {seeds_url}")
    
    html = brightdata_request(seeds_url)
    if html:
        print("SUCCESS: Seeds page accessible")
        soup = BeautifulSoup(html, 'html.parser')
        
        # Look for products
        products = soup.find_all('div', class_='product-card-image')
        print(f"Products found: {len(products)}")
        
        # Check pagination
        pagination = soup.find_all('a', href=lambda x: x and 'page' in x)
        print(f"Pagination links: {len(pagination)}")
        
        if pagination:
            print("Sample pagination links:")
            for link in pagination[:3]:
                print(f"  {link.get('href')}")
    else:
        print("FAILED: Seeds page failed")
    
    time.sleep(2)
    
    # Test a specific product URL that worked before
    test_product = "https://www.northatlanticseed.com/product/alien-jack-f/"
    print(f"\nTesting known product: {test_product}")
    
    html = brightdata_request(test_product)
    if html:
        print("SUCCESS: Product page accessible")
        soup = BeautifulSoup(html, 'html.parser')
        title = soup.find('h1')
        print(f"Product title: {title.get_text() if title else 'No title'}")
    else:
        print("FAILED: Product page failed")
    
    # Check BrightData usage/limits
    print(f"\nBrightData Zone: {credentials['zone']}")
    print("If all requests are failing, possible causes:")
    print("1. Rate limiting by North Atlantic")
    print("2. IP blocking")
    print("3. BrightData zone issues")
    print("4. Site maintenance/changes")

if __name__ == "__main__":
    check_site_status()