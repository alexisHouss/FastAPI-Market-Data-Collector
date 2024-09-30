from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool, NullPool
from sqlalchemy.ext.declarative import declarative_base
import os
from contextlib import contextmanager

DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "postgres")
DB_HOST = os.getenv("DB_HOST", "db")
DB_NAME = os.getenv("DB_NAME", "streamer")

SQLALCHEMY_DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}"


engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    poolclass=QueuePool,  # Manage pool size and overflow
    pool_size=10,  # Connection pool size
    max_overflow=5,  # Number of connections to allow in overflow state
    pool_timeout=30,  # Timeout for getting connection from the pool
    pool_recycle=1800,  # Recycle connections after 30 minutes
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


# Dependency
def get_db():
    with get_celery_db() as db:
        yield db


@contextmanager
def get_celery_db():
    db = SessionLocal()
    try:
        yield db
    except:
        db.rollback()
        raise
    finally:
        db.close()
