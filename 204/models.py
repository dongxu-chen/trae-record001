from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Index, Boolean, Text
from database import Base
from datetime import datetime

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(String(50), unique=True, index=True)
    order_date = Column(Date, index=True)
    category = Column(String(50), index=True)
    region = Column(String(50), index=True)
    product_name = Column(String(200))
    quantity = Column(Integer)
    unit_price = Column(Float)
    total_amount = Column(Float)
    customer_id = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_date_category', 'order_date', 'category'),
        Index('idx_date_region', 'order_date', 'region'),
        Index('idx_date_category_region', 'order_date', 'category', 'region'),
    )

class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(200), index=True)
    frequency = Column(String(20))
    start_date = Column(Date, default=datetime.now().date())
    is_active = Column(Boolean, default=True)
    filters = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_sent = Column(DateTime, nullable=True)

