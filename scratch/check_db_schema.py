import sys
import os

# Add the project root to sys.path
sys.path.append(os.getcwd())

from db.session import SessionLocal
from sqlalchemy import text

def check_schema():
    db = SessionLocal()
    try:
        # Check columns of devices table
        result = db.execute(text("SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name = 'devices'"))
        columns = result.fetchall()
        print("Columns in 'devices' table:")
        for col in columns:
            print(f" - {col[0]} ({col[1]}), Nullable: {col[2]}")
        
        # Check if any unique constraints
        result = db.execute(text("SELECT conname FROM pg_constraint WHERE conrelid = 'devices'::regclass AND contype = 'u'"))
        constraints = result.fetchall()
        print("\nUnique constraints on 'devices' table:")
        for con in constraints:
            print(f" - {con[0]}")
            
    except Exception as e:
        print(f"Error checking schema: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_schema()
