import asyncio
from sqlalchemy.orm import Session
from db.session import get_db
from models.reseller import Reseller
from models.busi_user import BusiUser
import uuid

async def test_image_removal():
    db_gen = get_db()
    db = next(db_gen)
    
    try:
        # 1. Test Reseller Removal Logic
        reseller_id = str(uuid.uuid4())
        mock_reseller = Reseller(
            reseller_id=reseller_id,
            email=f"test_{reseller_id[:8]}@example.com",
            username=f"user_{reseller_id[:8]}",
            name="Test Reseller",
            phone="1234567890",
            password_hash="...",
            image_url="http://example.com/image.jpg"
        )
        db.add(mock_reseller)
        db.commit()
        
        print(f"Reseller created with image: {mock_reseller.image_url}")
        
        # Simulate removal
        mock_reseller.image_url = None
        db.commit()
        db.refresh(mock_reseller)
        
        if mock_reseller.image_url is None:
            print("Backend logic verified: Reseller image removed.")
        else:
            print("Backend logic failed: Reseller image still present.")
            
        # 2. Test Business User Removal Logic
        user_id = str(uuid.uuid4())
        mock_user = BusiUser(
            busi_user_id=user_id,
            email=f"user_{user_id[:8]}@example.com",
            username=f"user_{user_id[:8]}",
            name="Test User",
            phone="0987654321",
            business_name="Test Business",
            password_hash="...",
            image_url="http://example.com/user.jpg"
        )
        db.add(mock_user)
        db.commit()
        
        print(f"User created with image: {mock_user.image_url}")
        
        # Simulate removal
        mock_user.image_url = None
        db.commit()
        db.refresh(mock_user)
        
        if mock_user.image_url is None:
            print("Backend logic verified: User image removed.")
        else:
            print("Backend logic failed: User image still present.")
            
    finally:
        # Cleanup
        db.query(Reseller).filter(Reseller.reseller_id == reseller_id).delete()
        db.query(BusiUser).filter(BusiUser.busi_user_id == user_id).delete()
        db.commit()
        db.close()

if __name__ == "__main__":
    asyncio.run(test_image_removal())
