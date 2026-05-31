import uuid
import enum
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Integer, DECIMAL, Boolean, JSON, Float, Enum
from sqlalchemy.orm import relationship
from ..database import Base


class MonitorFrequencyLevel(str, enum.Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    VERY_HIGH = "very_high"
    CRITICAL = "critical"


FREQUENCY_MINUTES = {
    MonitorFrequencyLevel.LOW: 120,
    MonitorFrequencyLevel.NORMAL: 60,
    MonitorFrequencyLevel.HIGH: 30,
    MonitorFrequencyLevel.VERY_HIGH: 15,
    MonitorFrequencyLevel.CRITICAL: 5,
}


class PromotionType(str, enum.Enum):
    DOUBLE_ELEVEN = "double_eleven"
    DOUBLE_TWELVE = "double_twelve"
    SIX_EIGHTEEN = "six_eighteen"
    NEW_YEAR = "new_year"
    SPRING_FESTIVAL = "spring_festival"
    MID_YEAR = "mid_year"
    PLATFORM_PROMO = "platform_promo"
    BRAND_PROMO = "brand_promo"
    OTHER = "other"


class MonitorSchedule(Base):
    __tablename__ = "monitor_schedules"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    product_id = Column(String(36), ForeignKey("products.id"), nullable=False, index=True)
    platform = Column(String(50), index=True)
    
    frequency_level = Column(Enum(MonitorFrequencyLevel), default=MonitorFrequencyLevel.NORMAL)
    check_interval_minutes = Column(Integer, default=60)
    
    last_checked_at = Column(DateTime)
    next_check_at = Column(DateTime, index=True)
    
    is_active = Column(Boolean, default=True, index=True)
    is_manual = Column(Boolean, default=False)
    
    auto_adjust = Column(Boolean, default=True)
    adjust_reason = Column(String(200))
    
    consecutive_changes = Column(Integer, default=0)
    volatility_score = Column(Float, default=0.0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    product = relationship("Product", backref="monitor_schedules")


class PriceMonitorLog(Base):
    __tablename__ = "price_monitor_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    product_id = Column(String(36), nullable=False, index=True)
    platform = Column(String(50), nullable=False, index=True)
    
    old_price = Column(DECIMAL(10, 2))
    new_price = Column(DECIMAL(10, 2))
    price_change = Column(DECIMAL(10, 2))
    price_change_percent = Column(Float)
    
    detected_at = Column(DateTime, default=datetime.utcnow, index=True)
    monitor_schedule_id = Column(String(36), ForeignKey("monitor_schedules.id"))
    
    is_alert_sent = Column(Boolean, default=False)
    alert_sent_at = Column(DateTime)
    
    in_promotion_period = Column(Boolean, default=False)
    promotion_type = Column(String(50))
    
    created_at = Column(DateTime, default=datetime.utcnow)


class PromotionPeriod(Base):
    __tablename__ = "promotion_periods"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    name = Column(String(200), nullable=False)
    promotion_type = Column(Enum(PromotionType), nullable=False)
    
    platform = Column(String(50))
    is_all_platforms = Column(Boolean, default=True)
    
    start_date = Column(DateTime, nullable=False, index=True)
    end_date = Column(DateTime, nullable=False, index=True)
    
    pre_warm_start = Column(DateTime)
    cool_down_end = Column(DateTime)
    
    monitor_frequency_level = Column(Enum(MonitorFrequencyLevel), default=MonitorFrequencyLevel.VERY_HIGH)
    
    expected_volatility = Column(Float, default=0.3)
    priority = Column(Integer, default=5)
    
    description = Column(Text)
    
    is_active = Column(Boolean, default=True)
    is_auto_detected = Column(Boolean, default=False)
    
    detection_confidence = Column(Float)
    detection_source = Column(String(200))
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class FrequencyAdjustmentLog(Base):
    __tablename__ = "frequency_adjustment_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    monitor_schedule_id = Column(String(36), ForeignKey("monitor_schedules.id"), nullable=False, index=True)
    
    old_frequency_level = Column(Enum(MonitorFrequencyLevel))
    new_frequency_level = Column(Enum(MonitorFrequencyLevel))
    old_interval_minutes = Column(Integer)
    new_interval_minutes = Column(Integer)
    
    adjustment_reason = Column(String(200))
    adjustment_type = Column(String(50))
    
    volatility_score = Column(Float)
    consecutive_changes = Column(Integer)
    in_promotion = Column(Boolean)
    
    price_change_percent = Column(Float)
    alert_count_24h = Column(Integer)
    
    adjusted_at = Column(DateTime, default=datetime.utcnow)
    adjusted_by = Column(String(100), default="auto")


class MonitorStats(Base):
    __tablename__ = "monitor_stats"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    stat_date = Column(DateTime, nullable=False, index=True)
    
    total_monitored = Column(Integer, default=0)
    active_monitors = Column(Integer, default=0)
    
    price_changes_detected = Column(Integer, default=0)
    price_increases = Column(Integer, default=0)
    price_decreases = Column(Integer, default=0)
    
    avg_change_percent = Column(Float)
    max_change_percent = Column(Float)
    
    alerts_sent = Column(Integer, default=0)
    frequency_adjustments = Column(Integer, default=0)
    
    in_promotion_count = Column(Integer, default=0)
    
    total_checks = Column(Integer, default=0)
    checks_success = Column(Integer, default=0)
    checks_failed = Column(Integer, default=0)
    
    avg_response_time_ms = Column(Float)
    
    created_at = Column(DateTime, default=datetime.utcnow)
