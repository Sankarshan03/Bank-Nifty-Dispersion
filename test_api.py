#!/usr/bin/env python3
"""
Test script for BankNifty Dispersion Trade Monitor API
"""

import requests
import json
import time

def test_api_endpoints():
    """Test all API endpoints"""
    base_url = "http://localhost:5000"
    
    print("🚀 Testing BankNifty Dispersion Trade Monitor API")
    print("=" * 50)
    
    # Test 1: Main page
    print("\n1. Testing main page...")
    try:
        response = requests.get(f"{base_url}/")
        if response.status_code == 200:
            print("✅ Main page loaded successfully")
        else:
            print(f"❌ Main page failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Main page error: {str(e)}")
    
    # Test 2: Dispersion data API
    print("\n2. Testing dispersion data API...")
    try:
        response = requests.get(f"{base_url}/api/dispersion-data")
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                print("✅ Dispersion data API working")
                print(f"   Net Premium: ₹{data['data'].get('net_premium', 0):,.2f}")
                print(f"   BankNifty Premium: ₹{data['data']['banknifty_position'].get('premium', 0):,.2f}")
                print(f"   Constituents Premium: ₹{data['data']['constituents_positions'].get('total_premium', 0):,.2f}")
            else:
                print(f"❌ API returned error: {data.get('message', 'Unknown error')}")
        else:
            print(f"❌ Dispersion data API failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Dispersion data API error: {str(e)}")
    
    # Test 3: Constituents API
    print("\n3. Testing constituents API...")
    try:
        response = requests.get(f"{base_url}/api/constituents")
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                print("✅ Constituents API working")
                print(f"   Total constituents: {len(data['data'])}")
                print(f"   Top constituent: {list(data['data'].keys())[0]}")
            else:
                print(f"❌ API returned error: {data.get('message', 'Unknown error')}")
        else:
            print(f"❌ Constituents API failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Constituents API error: {str(e)}")
    
    # Test 4: OTM levels API
    print("\n4. Testing OTM levels API...")
    try:
        response = requests.get(f"{base_url}/api/otm-levels?levels=2")
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                print("✅ OTM levels API working")
                print(f"   OTM levels returned: {len(data['data'])}")
            else:
                print(f"❌ API returned error: {data.get('message', 'Unknown error')}")
        else:
            print(f"❌ OTM levels API failed: {response.status_code}")
    except Exception as e:
        print(f"❌ OTM levels API error: {str(e)}")
    
    print("\n" + "=" * 50)
    print("🎯 API Testing Complete!")
    print("\n💡 Note: The application is using mock data for development.")
    print("   Real market data will be used when markets are open and API is accessible.")

if __name__ == "__main__":
    # Wait a moment for the server to be ready
    print("⏳ Waiting for server to be ready...")
    time.sleep(2)
    
    test_api_endpoints()
