#!/usr/bin/env python3
import sys
import os
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.config import settings
from core.security import get_password_hash
from models.admin import MasterAdmin

def create_admin_user(email, password, name="Master Admin", username="admin"):
    """Create a master admin user in the database"""
    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Check if admin already exists
        existing_admin = session.query(MasterAdmin).filter(MasterAdmin.email == email).first()
        if existing_admin:
            print(f"Admin with email {email} already exists.")
            return False
            
        # Create new admin
        admin = MasterAdmin(
            admin_id=str(uuid.uuid4()),
            username=username,
            email=email,
            password_hash=get_password_hash(password),
            name=name
        )
        
        session.add(admin)
        session.commit()
        print(f"Admin user created successfully!")
        print(f"   Email: {email}")
        print(f"   Username: {username}")
        print(f"   Admin ID: {admin.admin_id}")
        return True
        
    except Exception as e:
        session.rollback()
        print(f"Error creating admin user: {e}")
        return False
    finally:
        session.close()

if __name__ == "__main__":
    # User provided credentials
    EMAIL = "adminlogin6631@gmail.com"
    PASSWORD = "Admin@6631"
    
    print(f"Creating admin user: {EMAIL}...")
    create_admin_user(EMAIL, PASSWORD, name="Admin User", username="admin_6631")
