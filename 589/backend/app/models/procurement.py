from sqlalchemy import Column, String, Float, Integer, DateTime, Text, Boolean, ForeignKey, Enum, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from ..database import Base


class ProcurementOrderStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    ORDERED = "ordered"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"
    REFUNDED = "refunded"


class ProcurementPlatform(str, enum.Enum):
    TAOBAO = "taobao"
    JD = "jd"
    PDD = "pdd"
    SUNING = "suning"
    MANUAL = "manual"


class ProcurementServiceFeeType(str, enum.Enum):
    PERCENTAGE = "percentage"
    FIXED = "fixed"


class ProcurementOrder(Base):
    __tablename__ = "procurement_orders"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, index=True, nullable=False)
    user_nickname = Column(String(100))
    
    product_id = Column(String, index=True, nullable=False)
    product_name = Column(String(500), nullable=False)
    product_image = Column(String(500))
    product_url = Column(String(500))
    
    target_platform = Column(String(50))
    selected_platform = Column(String(50))
    selected_shop = Column(String(200))
    selected_price = Column(Float, default=0.0)
    
    quantity = Column(Integer, default=1)
    unit_price = Column(Float, default=0.0)
    total_price = Column(Float, default=0.0)
    
    service_fee_type = Column(String(20), default=ProcurementServiceFeeType.PERCENTAGE.value)
    service_fee_rate = Column(Float, default=0.05)
    service_fee = Column(Float, default=0.0)
    
    shipping_fee = Column(Float, default=0.0)
    discount_amount = Column(Float, default=0.0)
    coupon_code = Column(String(100))
    cashback_amount = Column(Float, default=0.0)
    
    final_total = Column(Float, default=0.0)
    amount_paid = Column(Float, default=0.0)
    
    recipient_name = Column(String(100))
    recipient_phone = Column(String(20))
    recipient_address = Column(String(500))
    recipient_province = Column(String(50))
    recipient_city = Column(String(50))
    recipient_district = Column(String(50))
    
    status = Column(String(20), default=ProcurementOrderStatus.PENDING.value, index=True)
    status_history = Column(JSON, default=list)
    
    platform_order_id = Column(String(100))
    tracking_number = Column(String(100))
    tracking_company = Column(String(100))
    
    auto_order = Column(Boolean, default=True)
    auto_track = Column(Boolean, default=True)
    
    user_notes = Column(Text)
    admin_notes = Column(Text)
    
    price_protection_days = Column(Integer, default=7)
    price_protection_claimed = Column(Boolean, default=False)
    price_protection_amount = Column(Float, default=0.0)
    
    estimated_delivery_date = Column(DateTime)
    actual_delivery_date = Column(DateTime)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    ordered_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    alternatives = relationship("ProcurementAlternative", back_populates="order", cascade="all, delete-orphan")


class ProcurementAlternative(Base):
    __tablename__ = "procurement_alternatives"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    order_id = Column(String, ForeignKey("procurement_orders.id"), nullable=False)
    
    platform = Column(String(50), nullable=False)
    shop_name = Column(String(200))
    price = Column(Float, default=0.0)
    shipping_fee = Column(Float, default=0.0)
    total_price = Column(Float, default=0.0)
    
    estimated_delivery_days = Column(Integer)
    seller_rating = Column(Float)
    in_stock = Column(Boolean, default=True)
    
    product_url = Column(String(500))
    product_image = Column(String(500))
    
    discount_info = Column(JSON)
    coupon_info = Column(JSON)
    cashback_info = Column(JSON)
    
    final_price_with_benefits = Column(Float, default=0.0)
    savings_percent = Column(Float, default=0.0)
    
    is_recommended = Column(Boolean, default=False)
    recommendation_reason = Column(String(200))
    
    rank_score = Column(Float, default=0.0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    order = relationship("ProcurementOrder", back_populates="alternatives")


class ProcurementSetting(Base):
    __tablename__ = "procurement_settings"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, unique=True, index=True, nullable=False)
    
    enabled = Column(Boolean, default=True)
    auto_select_best = Column(Boolean, default=True)
    auto_order = Column(Boolean, default=False)
    
    preferred_platforms = Column(JSON, default=list)
    excluded_platforms = Column(JSON, default=list)
    
    max_service_fee_rate = Column(Float, default=0.1)
    min_seller_rating = Column(Float, default=4.5)
    
    price_difference_threshold = Column(Float, default=0.05)
    allow_cross_region = Column(Boolean, default=True)
    
    notify_on_price_drop = Column(Boolean, default=True)
    notify_on_order_status = Column(Boolean, default=True)
    notify_on_delivery = Column(Boolean, default=True)
    
    default_shipping_address = Column(JSON)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class GroupBuyStatus(str, enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class GroupBuyType(str, enum.Enum):
    PLATFORM_PROMO = "platform_promo"
    COMMUNITY = "community"
    QUANTITY_DISCOUNT = "quantity_discount"
    FLASH_SALE = "flash_sale"
    PRE_SALE = "pre_sale"


class GroupBuyDeal(Base):
    __tablename__ = "groupbuy_deals"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    title = Column(String(500), nullable=False)
    description = Column(Text)
    platform = Column(String(50), index=True)
    
    product_id = Column(String, index=True)
    product_name = Column(String(500))
    product_image = Column(String(500))
    product_url = Column(String(500))
    
    category = Column(String(100), index=True)
    brand = Column(String(100), index=True)
    
    original_price = Column(Float, default=0.0)
    group_price = Column(Float, default=0.0)
    unit_price = Column(Float, default=0.0)
    
    discount_percent = Column(Float, default=0.0)
    savings_amount = Column(Float, default=0.0)
    
    deal_type = Column(String(30), default=GroupBuyType.PLATFORM_PROMO.value, index=True)
    
    min_quantity = Column(Integer, default=2)
    max_quantity_per_person = Column(Integer)
    current_participants = Column(Integer, default=0)
    target_participants = Column(Integer, default=10)
    
    total_quantity_available = Column(Integer)
    total_quantity_sold = Column(Integer, default=0)
    
    start_time = Column(DateTime, index=True)
    end_time = Column(DateTime, index=True)
    duration_hours = Column(Integer)
    
    is_limited = Column(Boolean, default=False)
    is_flash_sale = Column(Boolean, default=False)
    is_top_deal = Column(Boolean, default=False)
    
    status = Column(String(20), default=GroupBuyStatus.ACTIVE.value, index=True)
    
    seller_name = Column(String(200))
    seller_rating = Column(Float)
    
    shipping_info = Column(JSON)
    payment_methods = Column(JSON)
    
    requirements = Column(JSON)
    benefits = Column(JSON)
    
    volume_price_tiers = Column(JSON)
    
    discovered_at = Column(DateTime, default=datetime.utcnow)
    source_url = Column(String(500))
    source_type = Column(String(50))
    
    popularity_score = Column(Float, default=0.0)
    value_score = Column(Float, default=0.0)
    overall_score = Column(Float, default=0.0)
    
    view_count = Column(Integer, default=0)
    join_count = Column(Integer, default=0)
    share_count = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class GroupBuyParticipation(Base):
    __tablename__ = "groupbuy_participations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    deal_id = Column(String, ForeignKey("groupbuy_deals.id"), nullable=False)
    
    user_id = Column(String, index=True, nullable=False)
    user_nickname = Column(String(100))
    
    quantity = Column(Integer, default=1)
    unit_price_at_join = Column(Float, default=0.0)
    total_amount = Column(Float, default=0.0)
    
    status = Column(String(20), default="joined")
    is_organizer = Column(Boolean, default=False)
    
    joined_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    
    notes = Column(Text)


class CashbackStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    PAID = "paid"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class CashbackTransaction(Base):
    __tablename__ = "cashback_transactions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, index=True, nullable=False)
    
    order_id = Column(String, index=True)
    platform = Column(String(50), index=True)
    
    product_id = Column(String)
    product_name = Column(String(500))
    product_image = Column(String(500))
    
    original_price = Column(Float, default=0.0)
    final_price = Column(Float, default=0.0)
    
    cashback_rate = Column(Float, default=0.0)
    cashback_amount = Column(Float, default=0.0)
    
    coupon_amount = Column(Float, default=0.0)
    discount_amount = Column(Float, default=0.0)
    
    effective_price = Column(Float, default=0.0)
    
    status = Column(String(20), default=CashbackStatus.PENDING.value, index=True)
    
    platform_transaction_id = Column(String(100))
    affiliate_id = Column(String(100))
    click_id = Column(String(100))
    
    purchase_date = Column(DateTime)
    expected_payout_date = Column(DateTime)
    actual_payout_date = Column(DateTime)
    
    source_type = Column(String(50))
    source_url = Column(String(500))
    
    notes = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CashbackRule(Base):
    __tablename__ = "cashback_rules"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    platform = Column(String(50), index=True, nullable=False)
    category = Column(String(100), index=True)
    brand = Column(String(100), index=True)
    
    product_id = Column(String, index=True)
    product_sku = Column(String(100))
    
    rule_type = Column(String(30), default="percentage")
    cashback_rate = Column(Float, default=0.0)
    fixed_amount = Column(Float, default=0.0)
    
    min_order_amount = Column(Float, default=0.0)
    max_cashback_amount = Column(Float)
    
    tiered_rates = Column(JSON)
    
    valid_from = Column(DateTime)
    valid_to = Column(DateTime)
    
    is_active = Column(Boolean, default=True, index=True)
    is_promo = Column(Boolean, default=False)
    
    conditions = Column(JSON)
    exclusions = Column(JSON)
    
    priority = Column(Integer, default=0)
    
    total_used = Column(Integer, default=0)
    total_cashback = Column(Float, default=0.0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class UserCashbackAccount(Base):
    __tablename__ = "user_cashback_accounts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, unique=True, index=True, nullable=False)
    
    total_earned = Column(Float, default=0.0)
    total_paid = Column(Float, default=0.0)
    pending_amount = Column(Float, default=0.0)
    available_balance = Column(Float, default=0.0)
    
    minimum_payout = Column(Float, default=10.0)
    payout_method = Column(String(50), default="alipay")
    payout_account = Column(String(100))
    
    affiliate_ids = Column(JSON)
    
    last_payout_date = Column(DateTime)
    next_payout_date = Column(DateTime)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PriceComparisonV2(Base):
    __tablename__ = "price_comparison_v2"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    product_id = Column(String, index=True, nullable=False)
    
    platform_prices = Column(JSON)
    
    original_price_min = Column(Float, default=0.0)
    original_price_max = Column(Float, default=0.0)
    original_price_avg = Column(Float, default=0.0)
    
    coupon_discount_min = Column(Float, default=0.0)
    coupon_discount_max = Column(Float, default=0.0)
    
    cashback_min = Column(Float, default=0.0)
    cashback_max = Column(Float, default=0.0)
    
    final_price_min = Column(Float, default=0.0)
    final_price_max = Column(Float, default=0.0)
    final_price_avg = Column(Float, default=0.0)
    
    best_platform = Column(String(50))
    best_price = Column(Float, default=0.0)
    best_final_price = Column(Float, default=0.0)
    best_total_savings = Column(Float, default=0.0)
    best_savings_percent = Column(Float, default=0.0)
    
    breakdown = Column(JSON)
    
    calculated_at = Column(DateTime, default=datetime.utcnow, index=True)
