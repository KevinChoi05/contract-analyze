#!/usr/bin/env python3
"""
Test script to verify health endpoint works
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app

def test_health_endpoint():
    """Test the health endpoint"""
    print("Testing health endpoint...")
    
    app = create_app()
    
    with app.test_client() as client:
        response = client.get('/health')
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.get_json()}")
        print(f"Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            print("✅ Health endpoint working correctly!")
            return True
        else:
            print("❌ Health endpoint failed!")
            return False

if __name__ == '__main__':
    success = test_health_endpoint()
    sys.exit(0 if success else 1) 