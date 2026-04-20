#!/usr/bin/env python3
"""
Test script to verify trigger media functionality
"""

import requests
import json

def test_trigger_media():
    """Test trigger media sending functionality"""
    
    # Test 1: Check if media URL is accessible
    print("=== Testing Media URL Access ===")
    media_url = "http://localhost:8000/uploads/trigger_media/trigger_33496d04-29aa-4770-a9f3-4c7294ed5746.jpg"
    
    try:
        response = requests.get(media_url)
        if response.status_code == 200:
            print(f"SUCCESS: Media URL is accessible - {media_url}")
            print(f"Content-Type: {response.headers.get('content-type')}")
            print(f"Content-Length: {response.headers.get('content-length')}")
        else:
            print(f"FAILED: Media URL not accessible - Status: {response.status_code}")
    except Exception as e:
        print(f"ERROR: Failed to access media URL - {e}")
    
    # Test 2: Check unified service media handling
    print("\n=== Testing Unified Service Media Handling ===")
    
    # Create a mock media message request
    test_request = {
        "to": "+919876543210",
        "type": "image",
        "message": "Test message with media",
        "media_url": media_url,
        "device_id": "test-device-id",
        "user_id": "test-user-id"
    }
    
    try:
        response = requests.post(
            "http://localhost:8000/api/test/unified-message",
            json=test_request,
            headers={"Content-Type": "application/json"}
        )
        print(f"Unified Service Test Response: {response.status_code}")
        if response.status_code == 200:
            print(f"Response: {response.json()}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"ERROR: Failed to test unified service - {e}")
    
    # Test 3: Check trigger creation with media
    print("\n=== Testing Trigger Creation with Media ===")
    
    # This would need proper authentication, so we'll skip for now
    print("Trigger creation test skipped (requires authentication)")

if __name__ == "__main__":
    test_trigger_media()
