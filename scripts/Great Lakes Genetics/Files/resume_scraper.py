import requests
import json
import boto3
from bs4 import BeautifulSoup
import time
import re

def get_brightdata_credentials():
    """Get BrightData credentials from AWS Secrets Manager"""
    secrets_client = boto3.client('secretsmanager', region_name='us-east-1')
    response = secrets_client.get_secret_value(SecretId='cannabis-brightdata-api')
    return json.loads(response['SecretString'])

def brightdata_request(url, credentials):
    """Make request through BrightData Web Unlocker API"""
    api_url = "https://api.brightdata.com/request"
    headers = {"Authorization": f"Bearer {credentials['api_key']}"}
    payload = {"zone": credentials['zone'], "url": url, "format": "raw"}
    
    response = requests.post(api_url, headers=headers, json=payload)
    if response.status_code == 200:
        return response.text
    return None

def extract_strain_data(html_content, url):
    """Extract strain data from Great Lakes Genetics product page"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Extract strain name from title or h1
    strain_name = None
    title_tag = soup.find('h1', class_='product_title') or soup.find('h1') or soup.find('title')
    if title_tag:
        strain_name = title_tag.get_text().strip()
        strain_name = re.sub(r'\s+', ' ', strain_name)
        strain_name = strain_name.replace(' - Great Lakes Genetics', '').strip()
    
    # Initialize strain data
    strain_data = {
        'strain_name': strain_name,
        'source_url': url,
        'breeder_name': None,
        'seed_type': None,
        'pack_size': None,
        'price': None,
        'description': None
    }
    
    # Extract breeder from product title
    if strain_name and ' - ' in strain_name:
        parts = strain_name.split(' - ', 1)
        if len(parts) == 2:
            strain_data['breeder_name'] = parts[0].strip()
            strain_data['strain_name'] = parts[1].strip()
    
    # Extract seed type and pack size from title
    if strain_name:
        if 'fem' in strain_name.lower():
            strain_data['seed_type'] = 'Feminized'
        elif 'reg' in strain_name.lower():
            strain_data['seed_type'] = 'Regular'
        elif 'auto' in strain_name.lower():
            strain_data['seed_type'] = 'Autoflower'
        
        pack_match = re.search(r'(\d+)\s*(seeds?|pack)', strain_name, re.IGNORECASE)
        if pack_match:
            strain_data['pack_size'] = pack_match.group(1)
    
    return strain_data

def save_to_dynamodb(strain_data):
    """Save strain data to DynamoDB"""
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    table = dynamodb.Table('cannabis-strains')
    
    item = {
        'strain_name': strain_data['strain_name'] or 'Unknown',
        'breeder_name': strain_data['breeder_name'] or 'Great Lakes Genetics',
        'source': 'Great Lakes Genetics',
        'source_url': strain_data['source_url'],
        'seed_type': strain_data['seed_type'],
        'pack_size': strain_data['pack_size'],
        'created_at': str(int(time.time()))
    }
    
    item = {k: v for k, v in item.items() if v is not None}
    
    try:
        table.put_item(Item=item)
        return True
    except Exception as e:
        print(f"Error saving to DynamoDB: {e}")
        return False

def main():
    """Resume scraping from where we left off"""
    credentials = get_brightdata_credentials()
    
    # Load URLs from file
    try:
        with open('great_lakes_urls.txt', 'r') as f:
            all_product_urls = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print("URLs file not found. Run main scraper first.")
        return
    
    print(f"Resuming scraping from URL 75/{len(all_product_urls)}")
    
    successful_scrapes = 74  # Already completed
    failed_scrapes = 0
    
    # Continue from URL 75 (index 74)
    for i, product_url in enumerate(all_product_urls[74:], 75):
        print(f"Scraping product {i}/{len(all_product_urls)}: {product_url}")
        
        html_content = brightdata_request(product_url, credentials)
        if html_content:
            strain_data = extract_strain_data(html_content, product_url)
            
            if strain_data['strain_name']:
                if save_to_dynamodb(strain_data):
                    successful_scrapes += 1
                    # Safe ASCII output
                    strain_name = strain_data['strain_name'][:50].encode('ascii', 'ignore').decode('ascii')
                    breeder = (strain_data.get('breeder_name') or 'Unknown')[:30].encode('ascii', 'ignore').decode('ascii')
                    print(f"  SUCCESS: {strain_name} ({breeder})")
                else:
                    failed_scrapes += 1
                    print(f"  FAILED to save")
            else:
                failed_scrapes += 1
                print("  FAILED: No strain name found")
        else:
            failed_scrapes += 1
            print("  FAILED: Could not fetch page")
        
        # Progress checkpoint every 25 strains
        if i % 25 == 0:
            print(f"\n--- CHECKPOINT {i} ---")
            print(f"Successful: {successful_scrapes}")
            print(f"Failed: {failed_scrapes}")
            print(f"Success Rate: {successful_scrapes/(successful_scrapes+failed_scrapes)*100:.1f}%")
            print("--- CONTINUING ---\n")
        
        time.sleep(1)
    
    print(f"\n🎉 GREAT LAKES GENETICS COMPLETE!")
    print(f"Successful: {successful_scrapes}")
    print(f"Failed: {failed_scrapes}")
    print(f"Success Rate: {successful_scrapes/(successful_scrapes+failed_scrapes)*100:.1f}%")
    print(f"Total Database: {4978 + successful_scrapes} strains")

if __name__ == "__main__":
    main()