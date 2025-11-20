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

def extract_product_urls(html_content):
    """Extract product URLs from shop page"""
    soup = BeautifulSoup(html_content, 'html.parser')
    product_urls = []
    
    # Look for actual product pages only
    for link in soup.find_all('a', href=True):
        href = link.get('href')
        if href and '/product/' in href and 'neptuneseedbank.com' in href:
            # Skip non-seed products
            skip_terms = ['flower', 'sugar', 'extract', 'vape', 'merch', 'cart', 'account']
            if not any(term in href.lower() for term in skip_terms):
                product_urls.append(href)
    
    return list(set(product_urls))

def extract_strain_data(html_content, url):
    """Extract strain data from product page"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Extract strain name from title or h1
    strain_name = None
    title_tag = soup.find('h1') or soup.find('title')
    if title_tag:
        strain_name = title_tag.get_text().strip()
        # Clean up strain name
        strain_name = re.sub(r'\s+', ' ', strain_name)
        strain_name = strain_name.replace(' - Neptune Seed Bank', '').strip()
    
    # Extract attributes from the structured data
    strain_data = {
        'strain_name': strain_name,
        'source_url': url,
        'breeder_name': None,
        'genetics': None,
        'flowering_time': None,
        'thc_content': None,
        'cbd_content': None,
        'effects': None,
        'flavors': None,
        'difficulty': None,
        'height': None,
        'pack_size': None,
        'seed_type': None
    }
    
    # Extract from attribute items
    attribute_items = soup.find_all('div', class_='attribute-item')
    for item in attribute_items:
        label_elem = item.find('span', class_='attribute-label')
        value_elem = item.find('span', class_='attribute-value')
        
        if label_elem and value_elem:
            label = label_elem.get_text().strip().lower().replace(':', '')
            value = value_elem.get_text().strip()
            
            if 'harvest time' in label or 'flowering time' in label:
                strain_data['flowering_time'] = value
            elif 'grow difficulty' in label:
                strain_data['difficulty'] = value
            elif 'height' in label:
                strain_data['height'] = value
            elif 'pack size' in label:
                strain_data['pack_size'] = value
            elif 'flowering type' in label:
                strain_data['seed_type'] = value
            elif 'feelings' in label:
                strain_data['effects'] = value
            elif 'terpene profile' in label:
                strain_data['flavors'] = value
    
    # Extract breeder from description or title
    description = soup.find('div', id='description')
    if description:
        desc_text = description.get_text()
        # Look for "by [Breeder Name]" pattern
        breeder_match = re.search(r'by\s+([A-Za-z\s&]+?)(?:\s|$)', desc_text)
        if breeder_match:
            strain_data['breeder_name'] = breeder_match.group(1).strip()
    
    return strain_data

def save_to_dynamodb(strain_data):
    """Save strain data to DynamoDB"""
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    table = dynamodb.Table('cannabis-strains')
    
    # Create item for DynamoDB
    item = {
        'strain_name': strain_data['strain_name'] or 'Unknown',
        'breeder_name': strain_data['breeder_name'] or 'Neptune Seed Bank',
        'source': 'Neptune Seed Bank',
        'source_url': strain_data['source_url'],
        'flowering_time': strain_data['flowering_time'],
        'difficulty': strain_data['difficulty'],
        'height': strain_data['height'],
        'pack_size': strain_data['pack_size'],
        'seed_type': strain_data['seed_type'],
        'effects': strain_data['effects'],
        'flavors': strain_data['flavors'],
        'created_at': str(int(time.time()))
    }
    
    # Remove None values
    item = {k: v for k, v in item.items() if v is not None}
    
    try:
        table.put_item(Item=item)
        return True
    except Exception as e:
        print(f"Error saving to DynamoDB: {e}")
        return False

def main():
    """Main scraping function"""
    credentials = get_brightdata_credentials()
    
    # Categories to scrape with pagination
    categories = ['feminized-seeds', 'regular-seeds', 'autoflower-seeds']
    all_product_urls = []
    
    # Step 1: Extract product URLs from all pages
    print("Extracting product URLs from all category pages...")
    for category in categories:
        print(f"\nScraping category: {category}")
        
        for page in range(1, 21):  # Check up to 20 pages per category
            shop_url = f"https://neptuneseedbank.com/product-category/{category}/page/{page}/"
            print(f"  Page {page}")
            
            html_content = brightdata_request(shop_url, credentials)
            if html_content:
                product_urls = extract_product_urls(html_content)
                if product_urls:
                    all_product_urls.extend(product_urls)
                    print(f"    Found {len(product_urls)} products")
                else:
                    print(f"    No products - end of category")
                    break
            else:
                print(f"    Failed to fetch page")
                break
            
            time.sleep(1)  # Rate limiting
    
    # Remove duplicates
    all_product_urls = list(set(all_product_urls))
    print(f"Total unique products found: {len(all_product_urls)}")
    
    # Step 2: Scrape individual product pages (seeds only)
    successful_scrapes = 0
    for i, product_url in enumerate(all_product_urls[:20]):  # Limit to 20 for testing
        print(f"Scraping product {i+1}/{min(50, len(all_product_urls))}: {product_url}")
        
        html_content = brightdata_request(product_url, credentials)
        if html_content:
            strain_data = extract_strain_data(html_content, product_url)
            
            if strain_data['strain_name']:
                if save_to_dynamodb(strain_data):
                    successful_scrapes += 1
                    print(f"SUCCESS: {strain_data['strain_name']}")
                else:
                    print(f"FAILED to save: {strain_data['strain_name']}")
            else:
                print("FAILED: No strain name found")
        else:
            print("FAILED: Could not fetch page")
        
        time.sleep(1)  # Rate limiting
    
    print(f"\nScraping complete: {successful_scrapes}/{min(50, len(all_product_urls))} strains saved")

if __name__ == "__main__":
    main()