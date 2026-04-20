import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()
url = os.getenv("DATABASE_URL")

print(f"Testing direct psycopg2 connection to: {url.split('@')[1]}")

try:
    conn = psycopg2.connect(url)
    print("✅ Connection successful!")
    cur = conn.cursor()
    cur.execute("SELECT version();")
    print(f"PostgreSQL version: {cur.fetchone()}")
    cur.close()
    conn.close()
except Exception as e:
    print(f"❌ Connection failed: {e}")
    import traceback
    traceback.print_exc()
