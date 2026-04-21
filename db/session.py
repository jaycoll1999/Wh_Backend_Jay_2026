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
    The session is automatically closed by FastAPI after the request completes.
    """
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        db = SessionLocal()
        try:
            # 🔥 FIXED: Remove connection test to prevent hanging
            # The connection pool will handle connection errors gracefully
            yield db
            # On success path, FastAPI will close the session automatically
            return # Success, break the loop
        except OperationalError as e:
            retry_count += 1
            logger.warning(f" [RETRY {retry_count}/{max_retries}] Database connection failed: {e}")
            if db.in_transaction():
                db.rollback()
            db.close()
            
            if retry_count >= max_retries:
                logger.error("❌ Max retries reached. Database is unreachable.")
                raise e
            import time
            time.sleep(1) # Wait before retry
        except TimeoutError as e:
            logger.error(f"❌ Database connection timeout: {e}")
            if db.in_transaction():
                db.rollback()
            db.close()
            raise e
        except Exception as e:
            if db.in_transaction():
                db.rollback()
            db.close()
            raise e
