#!/usr/bin/env python3
"""
Test media-only sending (no caption) for both local and URL paths
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db.session import get_db
from services.unified_service import UnifiedWhatsAppService
from schemas.unified import UnifiedMessageRequest, MessageType

def test_media_only():
    """Test media-only sending with empty caption"""
    
    print("=== Testing Media-Only (No Caption) ===")
    
    # Get database session
    db = next(get_db())
    
    try:
        unified_service = UnifiedWhatsAppService(db)
        
        # Test 1: Local file path
        print("\n1. Testing LOCAL file path...")
        local_request = UnifiedMessageRequest(
            to="+919876543210",
            type=MessageType.IMAGE,
            message="",  # Empty message for media-only
            media_url="uploads/trigger_media/trigger_33496d04-29aa-4770-a9f3-4c7294ed5746.jpg",
            device_id="e0266dcb-d968-4180-988f-9542c77bfc1a",
            user_id="e74e56ab-4d68-4fcd-bef7-2f7ea64ab6d2"
        )
        
        result1 = unified_service.send_unified_message(local_request)
        print(f"   Local result: {result1.success}")
        
        # Test 2: HTTP URL
        print("\n2. Testing HTTP URL...")
        url_request = UnifiedMessageRequest(
            to="+919876543210",
            type=MessageType.IMAGE,
            message="",  # Empty message for media-only
            media_url="http://localhost:8000/uploads/trigger_media/trigger_33496d04-29aa-4770-a9f3-4c7294ed5746.jpg",
            device_id="e0266dcb-d968-4180-988f-9542c77bfc1a",
            user_id="e74e56ab-4d68-4fcd-bef7-2f7ea64ab6d2"
        )
        
        result2 = unified_service.send_unified_message(url_request)
        print(f"   URL result: {result2.success}")
        
        # Summary
        print(f"\n=== RESULTS ===")
        print(f"✅ Local file media-only: {'SUCCESS' if result1.success else 'FAILED'}")
        print(f"✅ HTTP URL media-only: {'SUCCESS' if result2.success else 'FAILED'}")
        
        if result1.success and result2.success:
            print(f"\n🎉 Media-only (no caption) sending is working perfectly!")
        else:
            print(f"\n❌ Some tests failed - check logs")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_media_only()
