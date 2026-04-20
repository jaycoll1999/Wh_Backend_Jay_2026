#!/usr/bin/env python3
"""
Direct test of media sending functionality
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.unified_service import UnifiedWhatsAppService
from schemas.unified import UnifiedMessageRequest, MessageType
from db.session import get_db

def test_media_direct():
    """Test media sending directly through unified service"""
    
    print("=== Direct Media Test ===")
    
    # Get database session
    db = next(get_db())
    
    try:
        # Create unified service instance
        unified_service = UnifiedWhatsAppService(db)
        
        # Create a test media message request
        media_url = "http://localhost:8000/uploads/trigger_media/trigger_33496d04-29aa-4770-a9f3-4c7294ed5746.jpg"  # Use HTTP URL to test conversion
        
        test_request = UnifiedMessageRequest(
            to="+919876543210",  # Test phone number
            type=MessageType.IMAGE,
            message="",  # Empty message for media-only test
            media_url=media_url,
            device_id="e0266dcb-d968-4180-988f-9542c77bfc1a",  # Real connected device (Arati)
            user_id="e74e56ab-4d68-4fcd-bef7-2f7ea64ab6d2"  # Real user ID
        )
        
        print(f"Test request created:")
        print(f"  - To: {test_request.to}")
        print(f"  - Type: {test_request.type}")
        print(f"  - Message: {test_request.message}")
        print(f"  - Media URL: {test_request.media_url}")
        print(f"  - Device ID: {test_request.device_id}")
        print(f"  - User ID: {test_request.user_id}")
        
        print("\nSending media message...")
        result = unified_service.send_unified_message(test_request)
        print(f"Result: {result}")
        
        if result.success:
            print("✅ Media message sent successfully!")
        else:
            print(f"❌ Failed to send media message: {result.error}")
                
    except Exception as e:
        print(f"❌ Error sending media message: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_media_direct()
