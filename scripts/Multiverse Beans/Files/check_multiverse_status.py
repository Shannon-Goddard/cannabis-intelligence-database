#!/usr/bin/env python3

import requests
import json
import boto3

def get_brightdata_credentials():
    """Get BrightData credentials from AWS Secrets Manager"""
    try:
        secrets_client = boto3.client('secretsmanager', region_name='us-east-1')
        response = secrets_client.get_secret_value(SecretId='cannabis-brightdata-api')
        credentials = json.loads(response['SecretString'])
        return credentials['api_key']
    except Exception as e:
        print(f"Error getting credentials: {e}")
        return None

def test_brightdata_status():
    """Test BrightData connectivity and Multiverse Beans accessibility"""
    api_key = get_brightdata_credentials()
    if not api_key:
        return
    
    api_url = "https://api.brightdata.com/request"
    headers = {"Authorization": f"Bearer {api_key}"}
    
    # Test with a simple site first
    test_payload = {
        "zone": "cannabis_strain_scraper",
        "url": "https://httpbin.org/get",
        "format": "raw"
    }
    
    print("Testing BrightData connectivity...")
    try:
        response = requests.post(api_url, headers=headers, json=test_payload, timeout=30)
        print(f"BrightData status: {response.status_code}")
        if response.status_code == 200:
            print("BrightData is working!")
        else:
            print(f"BrightData error: {response.text}")
            return
    except Exception as e:
        print(f"BrightData connection error: {e}")
        return
    
    # Now test Multiverse Beans
    multiverse_payload = {
        "zone": "cannabis_strain_scraper", 
        "url": "https://multiversebeans.com",
        "format": "raw"
    }
    
    print("\nTesting Multiverse Beans...")
    try:
        response = requests.post(api_url, headers=headers, json=multiverse_payload, timeout=30)
        print(f"Multiverse status: {response.status_code}")
        print(f"Response length: {len(response.text)} characters")
        
        if response.status_code == 200:
            content = response.text
            if len(content) > 1000:
                print("Got substantial content - site is accessible")
                print(f"Content preview: {content[:200]}...")
            else:
                print("Got minimal content - possible blocking")
                print(f"Full response: {content}")
        else:
            print(f"Error response: {response.text}")
            
    except Exception as e:
        print(f"Multiverse request error: {e}")

if __name__ == "__main__":
    test_brightdata_status()