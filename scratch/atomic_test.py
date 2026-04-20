
from db.session import get_db
from sqlalchemy import text
import uuid

db = next(get_db())
try:
    print("--- ATOMIC ALTER AND QUERY ---")
    
    # 1. Alter type
    print("Altering type...")
    db.execute(text("ALTER TABLE master_admins ALTER COLUMN admin_id TYPE UUID USING admin_id::UUID"))
    
    # 2. Query immediately
    print("Querying type...")
    result = db.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'master_admins' AND column_name = 'admin_id'"))
    for row in result:
        print(f"Type in DB: {row[1]}")
        
    # 3. Query with SQLAlchemy (using the already loaded models)
    from models.admin import MasterAdmin
    print("Querying with models...")
    user_id = "db7bc700-2c51-4aa8-820d-bf9150f9339a"
    admin = db.query(MasterAdmin).filter(MasterAdmin.admin_id == uuid.UUID(user_id)).first()
    if admin:
        print(f"Success! Found: {admin.username}")
    else:
        print("Not found, but query worked.")
        
    db.commit()
    print("Committed.")
    
except Exception as e:
    print(f"Error: {e}")
    db.rollback()
finally:
    db.close()
