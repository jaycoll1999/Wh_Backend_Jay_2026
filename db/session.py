import logging
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from .base import engine

logger = logging.getLogger("DB_SESSION")

# 1. Plain sessionmaker - NO scoped_session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=engine)

def get_db():
    """
    FastAPI dependency that provides a fresh session per request with a retry mechanism.
    """
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        db = SessionLocal()
        try:
            # 🔥 Test the connection before yielding (ensures pool pre-ping works)
            db.execute(text("SELECT 1"))
            yield db
            return # Success, break the loop
        except OperationalError as e:
            retry_count += 1
            logger.warning(f"⚠️ [RETRY {retry_count}/{max_retries}] Database connection failed: {e}")
            if db.in_transaction():
                db.rollback()
            db.close()
            
            if retry_count >= max_retries:
                logger.error("❌ Max retries reached. Database is unreachable.")
                raise e
            import time
            time.sleep(1) # Wait before retry
        except Exception as e:
            if db.in_transaction():
                db.rollback()
            db.close()
            raise e
        finally:
            if 'db' in locals():
                db.close()
