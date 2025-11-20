import requests
import json
import boto3
from bs4 import BeautifulSoup
import time
import re

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

def extract_product_urls(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    urls = []
    
    # Look for product-title-link class
    for link in soup.find_all('a', class_='product-title-link'):
        href = link.get('href')
        if href:
            urls.append(href)
    
    return urls

def extract_strain_data(html_content, url):
    soup = BeautifulSoup(html_content, 'html.parser')
    
    strain_name = None
    # Try h1 first, then h2
    h1_tag = soup.find('h1')
    if h1_tag:
        strain_name = h1_tag.get_text().strip()
    else:
        h2_tag = soup.find('h2', string=lambda text: text and 'strain' in text.lower())
        if h2_tag:
            strain_name = h2_tag.get_text().strip()
    
    if strain_name:
        strain_name = re.sub(r'\s+', ' ', strain_name)
        strain_name = strain_name.replace(' Strain Feminized Seeds by ', ' - ')
        strain_name = strain_name.replace(' Strain ', ' ')
    
    strain_data = {
        'strain_name': strain_name,
        'source_url': url,
        'breeder_name': None,
        'flowering_time': None,
        'difficulty': None,
        'height': None,
        'pack_size': None,
        'seed_type': None,
        'effects': None,
        'flavors': None,
        'genetics': None
    }
    
    for item in soup.find_all('div', class_='attribute-item'):
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
            elif 'cannabis type' in label:
                strain_data['genetics'] = value
    
    description = soup.find('div', id='description')
    if description:
        desc_text = description.get_text()
        breeder_match = re.search(r'by\s+([A-Za-z\s&]+?)(?:\s|$)', desc_text)
        if breeder_match:
            strain_data['breeder_name'] = breeder_match.group(1).strip()
    
    return strain_data

def save_to_dynamodb(strain_data):
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    table = dynamodb.Table('cannabis-strains')
    
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
        'genetics': strain_data['genetics'],
        'created_at': str(int(time.time()))
    }
    
    item = {k: v for k, v in item.items() if v is not None}
    
    try:
        table.put_item(Item=item)
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

credentials = get_brightdata_credentials()

# Product tag URLs to paginate through
tag_urls = [
    'https://neptuneseedbank.com/product_tag/feminized/',
    'https://neptuneseedbank.com/product_tag/regular-seeds/',
    'https://neptuneseedbank.com/product_tag/auto-flowering/'
]

all_urls = []
print("Finding all strain URLs...")

for tag_url in tag_urls:
    print(f"\nScraping tag: {tag_url}")
    
    for page in range(1, 51):  # Check up to 50 pages per tag
        page_url = f"{tag_url}page/{page}/"
        print(f"  Page {page}")
        
        html = brightdata_request(page_url, credentials)
        if html:
            urls = extract_product_urls(html)
            if urls:
                all_urls.extend(urls)
                print(f"    Found {len(urls)} strains")
            else:
                print(f"    No strains - end of tag")
                break
        else:
            print(f"    Failed to fetch")
            break
        
        time.sleep(1)

all_urls = list(set(all_urls))
print(f"\nTotal unique strains found: {len(all_urls)}")

# Scrape each strain
successful = 0
for i, url in enumerate(all_urls, 1):  # Scrape all strains
    print(f"[{i}/{len(all_urls)}] {url}")
    html = brightdata_request(url, credentials)
    
    if html:
        data = extract_strain_data(html, url)
        if data['strain_name'] and save_to_dynamodb(data):
            successful += 1
            print(f"  SUCCESS: {data['strain_name']} - {data['breeder_name']}")
        else:
            print(f"  FAILED")
    else:
        print(f"  FAILED to fetch")
    
    time.sleep(1)

print(f"\nComplete: {successful}/{len(all_urls)} strains saved")