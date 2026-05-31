import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Integer, DECIMAL, Boolean, Date, Enum, Float
from sqlalchemy.orm import relationship
from ..database import Base
import enum


class CouponShareStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class VerificationStatus(str, enum.Enum):
    UNVERIFIED = "unverified"
    VERIFIED = "verified"
    FAILED = "failed"


class CouponShare(Base):
    __tablename__ = "coupon_shares"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    user_id = Column(String(36), index=True)
    user_nickname = Column(String(100))
    
    platform = Column(String(50), nullable=False, index=True)
    code = Column(String(100), nullable=False)
    discount = Column(DECIMAL(10, 2), nullable=False)
    discount_type = Column(Enum("percentage", "fixed", name="discount_type"), nullable=False)
    min_amount = Column(DECIMAL(10, 2), default=0)
    max_discount = Column(DECIMAL(10, 2))
    
    applicable_products = Column(Text)
    applicable_categories = Column(String(500))
    
    valid_from = Column(Date, nullable=False)
    valid_to = Column(Date, nullable=False)
    
    description = Column(Text)
    source_url = Column(String(1000))
    
    status = Column(Enum(CouponShareStatus), default=CouponShareStatus.PENDING, index=True)
    verification_status = Column(Enum(VerificationStatus), default=VerificationStatus.UNVERIFIED)
    
    verification_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    fail_count = Column(Integer, default=0)
    
    upvotes = Column(Integer, default=0)
    downvotes = Column(Integer, default=0)
    
    reviewed_by = Column(String(36))
    reviewed_at = Column(DateTime)
    review_comment = Column(Text)
    
    reward_points = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CouponVerification(Base):
    __tablename__ = "coupon_verifications"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    coupon_share_id = Column(String(36), ForeignKey("coupon_shares.id"), nullable=False, index=True)
    verifier_id = Column(String(36), nullable=False, index=True)
    
    is_valid = Column(Boolean, nullable=False)
    verification_method = Column(String(50))
    verification_result = Column(Text)
    
    actual_discount = Column(DECIMAL(10, 2))
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    coupon_share = relationship("CouponShare", backref="verifications")


class CouponVote(Base):
    __tablename__ = "coupon_votes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    coupon_share_id = Column(String(36), ForeignKey("coupon_shares.id"), nullable=False, index=True)
    user_id = Column(String(36), nullable=False, index=True)
    
    vote_type = Column(Enum("up", "down", name="vote_type"), nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    coupon_share = relationship("CouponShare", backref="votes")


class UserReward(Base):
    __tablename__ = "user_rewards"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    user_id = Column(String(36), nullable=False, index=True)
    
    points = Column(Integer, nullable=False)
    reward_type = Column(String(50), nullable=False)
    
    related_coupon_id = Column(String(36))
    related_verification_id = Column(String(36))
    
    description = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class CouponMinedRule(Base):
    __tablename__ = "coupon_mined_rules"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    platform = Column(String(50), nullable=False, index=True)
    rule_type = Column(String(50), nullable=False)
    
    pattern = Column(String(500), nullable=False)
    regex_pattern = Column(String(500))
    
    support = Column(Float)
    confidence = Column(Float)
    lift = Column(Float)
    
    min_amount = Column(DECIMAL(10, 2))
    max_discount = Column(DECIMAL(10, 2))
    
    frequency = Column(Integer, default=0)
    success_rate = Column(Float, default=0.0)
    
    is_active = Column(Boolean, default=True)
    auto_apply = Column(Boolean, default=False)
    
    discovered_at = Column(DateTime, default=datetime.utcnow)
    last_verified = Column(DateTime)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class CouponUsageLog(Base):
    __tablename__ = "coupon_usage_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    coupon_id = Column(String(36), nullable=False, index=True)
    coupon_source = Column(String(50), default="official")
    
    user_id = Column(String(36), index=True)
    product_id = Column(String(36), index=True)
    
    original_price = Column(DECIMAL(10, 2))
    discount_amount = Column(DECIMAL(10, 2))
    final_price = Column(DECIMAL(10, 2))
    
    is_successful = Column(Boolean, default=True)
    error_message = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
