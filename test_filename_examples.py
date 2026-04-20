#!/usr/bin/env python3
"""
Test filename cleaning with real examples
"""

import re

def test_filename_cleaning():
    """Test filename cleaning with real examples"""
    
    print("=== Testing Filename Cleaning ===")
    
    test_cases = [
        "trigger_33496d04-29aa-4770-a9f3-4c7294ed5746.pdf",
        "trigger_33496d04-29aa-4770-a9f3-4c7294ed5746_रमाई स्वंसहाय्यता महिला बचत गट चांगदेव.pdf",
        "trigger_33496d04-29aa-4770-a9f3-4c7294ed5746.jpg",
        "trigger_33496d04-29aa-4770-a9f3-4c7294ed5746_image.png",
        "normal_file.pdf",
    ]
    
    for filename in test_cases:
        print(f"\nOriginal: {filename}")
        
        # New logic: Handle both formats
        if re.match(r'^trigger_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}_', filename):
            # Format: trigger_UUID_name.ext -> name.ext (remove only UUID)
            clean_name = re.sub(r'^trigger_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}_', '', filename)
        else:
            # No trigger UUID prefix, use as-is
            clean_name = filename
            
        print(f"Cleaned:  {clean_name}")

if __name__ == "__main__":
    test_filename_cleaning()
