#!/usr/bin/env python3
"""
Test the new filename cleaning pattern
"""

import re

def test_new_pattern():
    """Test the updated regex pattern"""
    
    print("=== Testing New Filename Pattern ===")
    
    test_files = [
        "trigger_33496d04-29aa-4770-a9f3-4c7294ed5746.jpg",
        "trigger_33496d04-29aa-4770-a9f3-4c7294ed5746_image.png",
        "trigger_33496d04-29aa-4770-a9f3-4c7294ed5746_video.mp4",
        "trigger_33496d04-29aa-4770-a9f3-4c7294ed5746_document.pdf",
        "normal_filename.jpg",
    ]
    
    # New pattern
    pattern = r'^trigger_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.'
    
    print(f"New pattern: {pattern}")
    print()
    
    for filename in test_files:
        result = re.sub(pattern, '.', filename)
        print(f"Original: {filename}")
        print(f"Result:   {result}")
        print()

if __name__ == "__main__":
    test_new_pattern()
