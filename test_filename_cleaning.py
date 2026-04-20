#!/usr/bin/env python3
"""
Test filename cleaning to remove trigger ID prefix
"""

import re
import os

def test_filename_cleaning():
    """Test the filename cleaning regex"""
    
    print("=== Testing Filename Cleaning ===")
    
    # Test cases
    test_cases = [
        "trigger_33496d04-29aa-4770-a9f3-4c7294ed5746.jpg",
        "trigger_33496d04-29aa-4770-a9f3-4c7294ed5746_image.png",
        "trigger_33496d04-29aa-4770-a9f3-4c7294ed5746_video.mp4",
        "trigger_33496d04-29aa-4770-a9f3-4c7294ed5746_document.pdf",
        "normal_filename.jpg",  # Should not be changed
        "33496d04-29aa-4770-a9f3-4c7294ed5746.jpg",  # Without trigger_ prefix
    ]
    
    current_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-.*?[0-9a-f]{12}_'
    new_pattern = r'^trigger_[0-9a-f]{8}-[0-9a-f]{4}-.*?[0-9a-f]{12}_'
    
    print(f"Current pattern: {current_pattern}")
    print(f"New pattern: {new_pattern}")
    print()
    
    for filename in test_cases:
        # Current pattern
        current_result = re.sub(current_pattern, '', filename)
        
        # New pattern (with "trigger_" prefix)
        new_result = re.sub(new_pattern, '', filename)
        
        print(f"Original: {filename}")
        print(f"Current:  {current_result}")
        print(f"New:      {new_result}")
        print(f"Fixed:     {'YES' if new_result != current_result else 'NO'}")
        print()

if __name__ == "__main__":
    test_filename_cleaning()
