import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import engine, history_engine, Base, HistoryBase
from app.models import *


def init_database():
    print("Creating main database tables...")
    Base.metadata.create_all(bind=engine)
    print("Main database tables created successfully!")

    print("Creating history database tables...")
    HistoryBase.metadata.create_all(bind=history_engine)
    print("History database tables created successfully!")

    print("\nDatabase initialization complete!")


if __name__ == "__main__":
    init_database()
