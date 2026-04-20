import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Add project root to sys.path
sys.path.append(os.getcwd())

load_dotenv()

def check_user():
    db_url = os.getenv("DATABASE_URL")
    if "?sslmode=require" not in db_url:
        db_url += "?sslmode=require"
    
    engine = create_engine(db_url)
    email = "sushil.bodade@gmail.com"
    
    print(f"--- Investigating User: {email} ---")
    
    try:
        with engine.connect() as connection:
            # 1. Check Businesses
            res = connection.execute(text("SELECT name, status, role, password_hash, parent_role FROM businesses WHERE email = :email"), {"email": email})
            row = res.fetchone()
            if row:
                print(f"FOUND in 'businesses' table:")
                print(f"  Name: {row[0]}")
                print(f"  Status: {row[1]}")
                print(f"  Role: {row[2]}")
                print(f"  Parent Role: {row[4]}")
                print(f"  Has Password Hash: {bool(row[3])}")
                
            # 2. Check Resellers
            res = connection.execute(text("SELECT name, status, role, password_hash FROM resellers WHERE email = :email"), {"email": email})
            row = res.fetchone()
            if row:
                print(f"FOUND in 'resellers' table:")
                print(f"  Name: {row[0]}")
                print(f"  Status: {row[1]}")
                print(f"  Role: {row[2]}")
                print(f"  Has Password Hash: {bool(row[3])}")

            # 3. Try a Test Auth Logic Simulation
            from core.security import verify_password
            password_to_check = "user123" # Common default if testing? Or maybe they set one.
            # I can't check the password without knowing it, but I can check if it STARTS with $2b$ (bcrypt)
            # or if it's plain text (which would fail login).

    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    check_user()
