import logging
import asyncio
import time
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from .base import engine

logger = logging.getLogger("DB_SESSION")

# 🔥 CONCURRENCY CONTROL: Semaphore to limit parallel DB calls
db_semaphore = asyncio.Semaphore(10)  # Max 10 concurrent DB operations

# 1. Plain sessionmaker - NO scoped_session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=engine)

def get_db():
    """
    FastAPI dependency that provides a fresh session per request with proper cleanup.
    Includes automatic retry once with 1s delay on connection failures.
    Returns 503 Service Unavailable if database is unreachable.
    """
    db = None
    attempts = 2
    
    while attempts > 0:
        try:
            db = SessionLocal()
            # 🔥 ROBUST: Pre-check connection health
            db.execute(text("SELECT 1"))
            
            logger.debug(f"🔓 DB session opened: {id(db)}")
            yield db
            return # Success
            
        except (OperationalError, SQLAlchemyError) as e:
            attempts -= 1
            if db:
                db.close()
            
            if attempts > 0:
                logger.warning(f"🔄 DB Connection failed: {e}. Retrying in 1s... ({attempts} attempt left)")
                time.sleep(1)
                continue
            
            # If we reach here, both attempts failed
            logger.error(f"❌ Database unreachable after retries: {e}")
            raise HTTPException(
                status_code=503, 
                detail={"error": "Database temporarily unavailable", "message": "Could not establish connection to the database server."}
            )
        except Exception as e:
            logger.error(f"❌ Unexpected DB session error: {e}")
            if db and db.in_transaction():
                db.rollback()
            raise e
        finally:
            if db:
                db.close()
                logger.debug(f"🔒 DB session closed: {id(db)}")
