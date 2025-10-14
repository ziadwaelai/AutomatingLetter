"""
Test script for WhatsApp API endpoints
This script demonstrates how to use the WhatsApp integration endpoints.
"""

import requests
import json

# Base URL for your API
BASE_URL = "http://localhost:5000/api/v1/whatsapp"

def test_send_whatsapp_letter():
    """Test the WhatsApp send endpoint"""
    
    # Test data
    data = {
        "phone_number": "1234567890",
        "letter_id": "LTR_20241014_001"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/send",
            json=data,
            headers={'Content-Type': 'application/json'}
        )
        
        print(f"Send WhatsApp Letter - Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
        return response.status_code == 200
        
    except Exception as e:
        print(f"Error testing send endpoint: {e}")
        return False

def test_update_whatsapp_status():
    """Test the WhatsApp status update endpoint"""
    
    # Test data
    data = {
        "phone_number": "201123808495",
        "status": "delivered"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/update-status",
            json=data,
            headers={'Content-Type': 'application/json'},
            verify=False  # Uncomment if using self-signed certificates
        )
        
        print(f"Update WhatsApp Status - Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
        return response.status_code == 200
        
    except Exception as e:
        print(f"Error testing status update endpoint: {e}")
        return False

def test_get_letter_by_id():
    """Test the get letter by ID endpoint"""
    
    # Test data
    letter_id = "LTR_20241014_001"
    
    try:
        response = requests.get(
            f"{BASE_URL}/letter/{letter_id}",
            headers={'Accept': 'application/json'}
        )
        
        print(f"Get Letter by ID - Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
        return response.status_code == 200
        
    except Exception as e:
        print(f"Error testing get letter endpoint: {e}")
        return False

def test_get_assigned_letter():
    """Test the get assigned letter ID endpoint"""
    
    # Test phone number
    phone_number = "201123808495"
    
    try:
        response = requests.get(
            f"{BASE_URL}/assigned-letter/{phone_number}",
            headers={'Accept': 'application/json'},
            verify=False,
            timeout=30
        )
        
        print(f"Get Assigned Letter - Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
        return response.status_code == 200
        
    except Exception as e:
        print(f"Error testing get assigned letter endpoint: {e}")
        return False

if __name__ == "__main__":
    print("Testing WhatsApp API Endpoints")
    print("=" * 50)
    
    # print("\n1. Testing get letter by ID endpoint:")
    # test_get_letter_by_id()
    
    # print("\n2. Testing send WhatsApp letter endpoint:")
    # test_send_whatsapp_letter()
    
    print("\n3. Testing get assigned letter endpoint:")
    test_get_assigned_letter()
    
    print("\n4. Testing update WhatsApp status endpoint:")
    test_update_whatsapp_status()
    
    print("\n" + "=" * 50)
    print("Testing complete!")