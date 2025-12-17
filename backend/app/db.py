import os
import time
from sqlalchemy import create_engine
from sqlalchemy import sessionmaker, DeclaritiveBase

DATABASE_URL = os.environ["DATABASE_URL"]

engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        
    
def wait_for_db(retries: int = 30, delay_s: float = 1.0) -> None:
    last_err = None
    for _ in range(retries):
        try:
            with engine.connect():
                return
        except Exception as e:
            last_err = e
            time.sleep(delay_s)
    raise RuntimeError("Database not ready") from last_err
            