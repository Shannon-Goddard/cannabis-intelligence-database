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
    """Extract product URLs from Great Lakes Genetics breeder pages"""
    soup = BeautifulSoup(html_content, 'html.parser')
    product_urls = []
    
    # Look for product links - Great Lakes uses /product/ URLs
    for link in soup.find_all('a', href=True):
        href = link.get('href')
        if href and '/product/' in href and 'greatlakesgenetics.com' in href:
            # Skip non-seed products
            skip_terms = ['merch', 'cart', 'account', 'checkout']
            if not any(term in href.lower() for term in skip_terms):
                product_urls.append(href)
    
    return list(set(product_urls))

def extract_strain_data(html_content, url):
    """Extract strain data from Great Lakes Genetics product page"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Extract strain name from title or h1
    strain_name = None
    title_tag = soup.find('h1', class_='product_title') or soup.find('h1') or soup.find('title')
    if title_tag:
        strain_name = title_tag.get_text().strip()
        # Clean up strain name
        strain_name = re.sub(r'\s+', ' ', strain_name)
        strain_name = strain_name.replace(' - Great Lakes Genetics', '').strip()
    
    # Initialize strain data
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
        'seed_type': None,
        'price': None,
        'description': None
    }
    
    # Extract breeder from product title or description
    if strain_name:
        # Great Lakes often has "Breeder - Strain Name" format
        if ' - ' in strain_name:
            parts = strain_name.split(' - ', 1)
            if len(parts) == 2:
                strain_data['breeder_name'] = parts[0].strip()
                strain_data['strain_name'] = parts[1].strip()
    
    # Extract from product description/details
    description_div = soup.find('div', class_='woocommerce-product-details__short-description') or \
                     soup.find('div', class_='product-description') or \
                     soup.find('div', id='tab-description')
    
    if description_div:
        desc_text = description_div.get_text()
        strain_data['description'] = desc_text[:500]  # First 500 chars
        
        # Look for flowering time patterns
        flowering_match = re.search(r'(\d+)[-\s]*(\d+)?\s*days?|(\d+)[-\s]*(\d+)?\s*weeks?', desc_text, re.IGNORECASE)
        if flowering_match:
            strain_data['flowering_time'] = flowering_match.group(0)
        
        # Look for THC/CBD content
        thc_match = re.search(r'THC[:\s]*(\d+(?:\.\d+)?)\s*%', desc_text, re.IGNORECASE)
        if thc_match:
            strain_data['thc_content'] = thc_match.group(1) + '%'
        
        cbd_match = re.search(r'CBD[:\s]*(\d+(?:\.\d+)?)\s*%', desc_text, re.IGNORECASE)
        if cbd_match:
            strain_data['cbd_content'] = cbd_match.group(1) + '%'
    
    # Extract price
    price_elem = soup.find('span', class_='woocommerce-Price-amount') or \
                soup.find('span', class_='price')
    if price_elem:
        strain_data['price'] = price_elem.get_text().strip()
    
    # Extract pack size from title or description
    if strain_name:
        pack_match = re.search(r'(\d+)\s*(pack|seeds?|reg|fem)', strain_name, re.IGNORECASE)
        if pack_match:
            strain_data['pack_size'] = pack_match.group(0)
        
        # Determine seed type
        if 'fem' in strain_name.lower() or 'feminized' in strain_name.lower():
            strain_data['seed_type'] = 'Feminized'
        elif 'reg' in strain_name.lower() or 'regular' in strain_name.lower():
            strain_data['seed_type'] = 'Regular'
        elif 'auto' in strain_name.lower():
            strain_data['seed_type'] = 'Autoflower'
    
    return strain_data

def save_to_dynamodb(strain_data):
    """Save strain data to DynamoDB"""
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    table = dynamodb.Table('cannabis-strains')
    
    # Create item for DynamoDB
    item = {
        'strain_name': strain_data['strain_name'] or 'Unknown',
        'breeder_name': strain_data['breeder_name'] or 'Great Lakes Genetics',
        'source': 'Great Lakes Genetics',
        'source_url': strain_data['source_url'],
        'flowering_time': strain_data['flowering_time'],
        'thc_content': strain_data['thc_content'],
        'cbd_content': strain_data['cbd_content'],
        'seed_type': strain_data['seed_type'],
        'pack_size': strain_data['pack_size'],
        'price': strain_data['price'],
        'description': strain_data['description'],
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
    """Main scraping function for Great Lakes Genetics"""
    credentials = get_brightdata_credentials()
    
    # Step 1: Extract product URLs from all 25 breeder pages
    print("Extracting product URLs from Great Lakes Genetics breeder pages...")
    all_product_urls = []
    
    for page in range(1, 26):  # 25 pages total
        breeder_url = f"https://www.greatlakesgenetics.com/breeders/page/{page}/"
        print(f"Scraping breeder page {page}/25")
        
        html_content = brightdata_request(breeder_url, credentials)
        if html_content:
            product_urls = extract_product_urls(html_content)
            if product_urls:
                all_product_urls.extend(product_urls)
                print(f"  Found {len(product_urls)} products")
            else:
                print(f"  No products found - checking if end of pages")
        else:
            print(f"  Failed to fetch page {page}")
        
        time.sleep(1)  # Rate limiting
    
    # Remove duplicates
    all_product_urls = list(set(all_product_urls))
    print(f"\nTotal unique products found: {len(all_product_urls)}")
    
    # Save URLs to file for resume capability
    with open('great_lakes_urls.txt', 'w') as f:
        for url in all_product_urls:
            f.write(url + '\n')
    
    # Step 2: Scrape individual product pages
    successful_scrapes = 0
    failed_scrapes = 0
    
    for i, product_url in enumerate(all_product_urls):
        print(f"Scraping product {i+1}/{len(all_product_urls)}: {product_url}")
        
        html_content = brightdata_request(product_url, credentials)
        if html_content:
            strain_data = extract_strain_data(html_content, product_url)
            
            if strain_data['strain_name']:
                if save_to_dynamodb(strain_data):
                    successful_scrapes += 1
                    breeder = strain_data.get('breeder_name') or 'Unknown'
                    strain_name = strain_data['strain_name'][:50].encode('ascii', 'ignore').decode('ascii')
                    breeder_name = breeder[:30].encode('ascii', 'ignore').decode('ascii')
                    print(f"  SUCCESS: {strain_name} ({breeder_name})")
                else:
                    failed_scrapes += 1
                    strain_name = (strain_data.get('strain_name') or 'Unknown')[:50]
                    clean_name = strain_name.encode('ascii', 'ignore').decode('ascii')
                    print(f"  FAILED to save: {clean_name}")
            else:
                failed_scrapes += 1
                print("  FAILED: No strain name found")
        else:
            failed_scrapes += 1
            print("  FAILED: Could not fetch page")
        
        # Progress checkpoint every 100 strains
        if (i + 1) % 100 == 0:
            print(f"\n--- CHECKPOINT {i+1} ---")
            print(f"Successful: {successful_scrapes}")
            print(f"Failed: {failed_scrapes}")
            print(f"Success Rate: {successful_scrapes/(successful_scrapes+failed_scrapes)*100:.1f}%")
            print("--- CONTINUING ---\n")
        
        time.sleep(1)  # Rate limiting
    
    print(f"\n🎉 GREAT LAKES GENETICS SCRAPING COMPLETE!")
    print(f"Successful: {successful_scrapes}")
    print(f"Failed: {failed_scrapes}")
    print(f"Success Rate: {successful_scrapes/(successful_scrapes+failed_scrapes)*100:.1f}%")
    print(f"Total Database: {4978 + successful_scrapes} strains")

if __name__ == "__main__":
    main()