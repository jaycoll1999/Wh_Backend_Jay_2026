import os
from sqlalchemy import create_engine, inspect, text
from dotenv import load_dotenv

load_dotenv()

def test_render_db():
    db_url = os.getenv("DATABASE_URL")
    print(f"Testing Connection to: {db_url.split('@')[1] if '@' in db_url else 'Unknown'}")
    
    try:
        # Note: Render requires SSL
        if "?sslmode=require" not in db_url:
            db_url += "?sslmode=require"
            
        engine = create_engine(db_url)
        with engine.connect() as connection:
            print("SUCCESS: Successfully connected to Render Database!")
            
            # Inspect tables
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            print(f"Tables found ({len(tables)}): {', '.join(tables)}")
            
            if 'master_admins' in tables:
                # Check for admins
                result = connection.execute(text("SELECT email, username FROM master_admins"))
                admins = result.fetchall()
                print(f"Found {len(admins)} Admin(s):")
                for admin in admins:
                    print(f"  - {admin[0]} ({admin[1]})")
            else:
                print("FAILURE: 'master_admins' table NOT FOUND!")

    except Exception as e:
        print(f"FAILURE: Connection failed: {e}")

if __name__ == "__main__":
    test_render_db()
