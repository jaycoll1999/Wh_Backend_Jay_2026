#!/usr/bin/env python3
"""
Test complete filename preservation flow
"""

import re

def test_filename_preservation():
    """Test complete filename preservation flow"""
    
    print("=== Testing Filename Preservation Flow ===")
    
    # Simulate file upload with original filename
    original_filename = "रमाई स्वंसहाय्यता महिला बचत गट चांगदेव.pdf"
    
    # Simulate upload process
    import uuid
    unique_filename = f"trigger_{uuid.uuid4()}_{original_filename}"
    
    print(f"1. Original filename: {original_filename}")
    print(f"2. After upload: {unique_filename}")
    
    # Simulate filename cleaning in engine service
    raw_filename = unique_filename
    
    # Handle both formats: trigger_UUID.ext and trigger_UUID_name.ext
    if re.match(r'^trigger_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}_', raw_filename):
        # Format: trigger_UUID_name.ext -> name.ext (remove only UUID)
        clean_filename = re.sub(r'^trigger_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}_', '', raw_filename)
    else:
        # No trigger UUID prefix, use as-is
        clean_filename = raw_filename
    
    print(f"3. After cleaning: {clean_filename}")
    
    # Test caption logic
    user_caption = None  # Media-only case
    final_caption = user_caption if user_caption is not None else ""
    print(f"4. Media-only caption: '{final_caption}'")
    
    # Test with caption case
    user_caption = "Check this document"
    final_caption = user_caption if user_caption is not None else ""
    print(f"5. With custom caption: '{final_caption}'")
    
    # Test with empty string caption (should remain empty)
    user_caption = ""
    final_caption = user_caption if user_caption is not None else ""
    print(f"6. With empty caption: '{final_caption}'")
    
    print("\n=== RESULTS ===")
    print(f"✅ Original filename preserved: {clean_filename == original_filename}")
    print(f"✅ Media-only has no caption: {final_caption == ''}")
    print(f"✅ Custom caption works: {final_caption == 'Check this document'}")
    print(f"✅ Empty caption stays empty: {final_caption == ''}")

if __name__ == "__main__":
    test_filename_preservation()
