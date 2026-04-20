import sys
import os
from sqlalchemy import text

# Add the current directory to sys.path
sys.path.append(os.getcwd())

from db.session import SessionLocal
from models.admin import MasterAdmin
from core.security import verify_password, get_password_hash

def test_admin_login_logic():
    db = SessionLocal()
    try:
        email = "admin@example.com"
        password = "admin123"
        
        print(f"Testing login for: {email}")
        admin = db.query(MasterAdmin).filter(MasterAdmin.email == email).first()
        
        if not admin:
            print("❌ Admin NOT FOUND by email.")
            return

        print(f"Admin found: {admin.username}")
        print(f"Stored Hash: {admin.password_hash}")
        
        # Test verification
        is_correct = verify_password(password, admin.password_hash)
        print(f"Verification result for '{password}': {is_correct}")
        
        # Check what a fresh hash looks like
        fresh_hash = get_password_hash(password)
        print(f"Fresh hash for '{password}': {fresh_hash}")
        
    except Exception as e:
        print(f"Error during test: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    test_admin_login_logic()
