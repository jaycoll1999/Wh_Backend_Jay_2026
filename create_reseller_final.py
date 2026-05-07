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
from models.reseller import Reseller

def create_reseller(email, password, name="Jaypal Reseller", username="jaypal_9421", phone="+919421000000"):
    """Create a reseller in the database"""
    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Check if reseller already exists
        existing = session.query(Reseller).filter(Reseller.email == email).first()
        if existing:
            print(f"Reseller with email {email} already exists.")
            return False
            
        # Create new reseller
        reseller = Reseller(
            reseller_id=str(uuid.uuid4()),
            username=username,
            email=email,
            phone=phone,
            password_hash=get_password_hash(password),
            name=name,
            total_credits=1000.0,
            available_credits=1000.0,
            status="active"
        )
        
        session.add(reseller)
        session.commit()
        print(f"Reseller created successfully!")
        print(f"   Email: {email}")
        print(f"   Username: {username}")
        print(f"   Reseller ID: {reseller.reseller_id}")
        return True
        
    except Exception as e:
        session.rollback()
        print(f"Error creating reseller: {e}")
        return False
    finally:
        session.close()

if __name__ == "__main__":
    # User provided credentials
    EMAIL = "jaypaltupare9421@gmail.com"
    PASSWORD = "call@9421"
    
    print(f"Creating reseller: {EMAIL}...")
    create_reseller(EMAIL, PASSWORD)
