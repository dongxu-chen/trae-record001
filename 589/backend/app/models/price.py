import uuid
from datetime import datetime
from sqlalchemy import Column, String, DECIMAL, Boolean, Integer, DateTime, ForeignKey, Date
from sqlalchemy.orm import relationship
from ..database import Base, HistoryBase


class PlatformPrice(Base):
    __tablename__ = "platform_prices"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    product_id = Column(String(36), ForeignKey("products.id"), nullable=False, index=True)
    platform = Column(String(50), nullable=False, index=True)
    platform_name = Column(String(50), nullable=False)
    price = Column(DECIMAL(10, 2), nullable=False, index=True)
    original_price = Column(DECIMAL(10, 2))
    product_url = Column(String(1000), nullable=False)
    in_stock = Column(Boolean, default=True)
    rating = Column(DECIMAL(3, 1))
    sales = Column(Integer, default=0)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    product = relationship("Product", back_populates="prices")


class PriceHistory(HistoryBase):
    __tablename__ = "price_history"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    product_id = Column(String(36), nullable=False, index=True)
    platform = Column(String(50), nullable=False, index=True)
    price = Column(DECIMAL(10, 2), nullable=False)
    record_date = Column(Date, nullable=False, index=True)
