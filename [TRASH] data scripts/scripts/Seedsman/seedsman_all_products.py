#!/usr/bin/env python3
"""
Seedsman All Products - Get everything with search filter
"""
import requests
import json
import boto3
import time
from datetime import datetime

def get_brightdata_credentials():
    secrets_client = boto3.client('secretsmanager', region_name='us-east-1')
    response = secrets_client.get_secret_value(SecretId='cannabis-brightdata-api')
    return json.loads(response['SecretString'])

def query_graphql(query, variables=None):
    credentials = get_brightdata_credentials()
    
    payload = {
        "zone": "cannabis_strain_scraper",
        "url": "https://www.seedsman.com/graphql",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"query": query, "variables": variables or {}}),
        "format": "raw"
    }
    
    response = requests.post("https://api.brightdata.com/request", 
                           headers={"Authorization": f"Bearer {credentials['api_key']}"}, 
                           json=payload)
    
    if response.status_code == 200:
        try:
            result = json.loads(response.text)
            if 'errors' in result:
                print(f"GraphQL errors: {result['errors']}")
            return result
        except:
            print(f"JSON parse error: {response.text[:200]}")
            return None
    else:
        print(f"HTTP error {response.status_code}: {response.text[:200]}")
    return None

def get_products_with_search():
    # Use search instead of category filter
    query = """
    query GetProducts($search: String!, $pageSize: Int!, $currentPage: Int!) {
        products(
            search: $search
            pageSize: $pageSize
            currentPage: $currentPage
        ) {
            total_count
            page_info {
                current_page
                total_pages
            }
            items {
                id
                name
                sku
                url_key
            }
        }
    }
    """
    
    # Search for common cannabis terms
    search_terms = ["seeds", "cannabis", "auto", "fem"]
    all_products = []
    
    for search_term in search_terms:
        print(f"\nSearching for: {search_term}")
        page = 1
        
        while page <= 5:  # Limit to 5 pages per search
            print(f"  Page {page}...")
            result = query_graphql(query, {
                "search": search_term, 
                "pageSize": 50, 
                "currentPage": page
            })
            
            if not result or 'data' not in result or not result['data']['products']:
                break
                
            products_data = result['data']['products']
            products = products_data['items']
            
            if not products:
                break
                
            # Filter duplicates
            new_products = []
            existing_ids = {p['id'] for p in all_products}
            for product in products:
                if product['id'] not in existing_ids:
                    new_products.append(product)
            
            all_products.extend(new_products)
            print(f"    Found {len(new_products)} new products (total: {len(all_products)})")
            
            if page >= products_data['page_info']['total_pages']:
                break
                
            page += 1
            time.sleep(0.5)
    
    return all_products

def save_strain(product):
    strain_data = {
        'strain_name': product['name'],
        'breeder_name': 'Seedsman',
        'source_url': f"https://www.seedsman.com/{product['url_key']}",
        'source': 'Seedsman GraphQL Search',
        'sku': product['sku'],
        'created_at': datetime.now().isoformat() + 'Z'
    }
    
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    table = dynamodb.Table('cannabis-strains')
    
    try:
        table.put_item(Item=strain_data)
        return True
    except:
        return False

def main():
    print("SEEDSMAN ALL PRODUCTS COLLECTION")
    print("Using search queries to get maximum data\n")
    
    products = get_products_with_search()
    print(f"\nCollected {len(products)} unique products from Seedsman")
    
    if not products:
        print("No products collected")
        return 0
    
    saved = 0
    for i, product in enumerate(products):
        if save_strain(product):
            saved += 1
            
        if (i + 1) % 25 == 0:
            print(f"Processed {i + 1}/{len(products)} ({saved} saved)")
    
    print(f"\nSUCCESS: {saved} Seedsman strains added!")
    
    # Check new total
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    table = dynamodb.Table('cannabis-strains')
    response = table.scan()
    items = response['Items']
    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        items.extend(response['Items'])
    
    total = len(items)
    print(f"New database total: {total} strains")
    
    if total >= 10000:
        print("\n🎉 10,000+ STRAIN MILESTONE ACHIEVED! 🎉")
    
    return saved

if __name__ == "__main__":
    main()