import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./price_comparison.db")
SQLITE_URL = os.getenv("SQLITE_URL", "sqlite:///./price_history.db")

engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=3600)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

history_engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})
HistorySessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=history_engine)

Base = declarative_base()
HistoryBase = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_history_db():
    db = HistorySessionLocal()
    try:
        yield db
    finally:
        db.close()
