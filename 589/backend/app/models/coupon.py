import uuid
from datetime import datetime
from sqlalchemy import Column, String, DECIMAL, Boolean, Date, Enum
from ..database import Base


class Coupon(Base):
    __tablename__ = "coupons"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    platform = Column(String(50), nullable=False, index=True)
    code = Column(String(100))
    discount = Column(DECIMAL(10, 2), nullable=False)
    discount_type = Column(Enum("percentage", "fixed", name="discount_type"), nullable=False)
    min_amount = Column(DECIMAL(10, 2), default=0)
    max_discount = Column(DECIMAL(10, 2))
    valid_from = Column(Date, nullable=False)
    valid_to = Column(Date, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(Date, default=datetime.utcnow)
