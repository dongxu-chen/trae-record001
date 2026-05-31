import re
import json
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import defaultdict, deque
from statistics import mean, stdev

from sqlalchemy.orm import Session
from ..models import (
    MonitorSchedule, MonitorFrequencyLevel, FREQUENCY_MINUTES,
    PromotionPeriod, PromotionType,
    PriceMonitorLog, FrequencyAdjustmentLog, MonitorStats,
    PriceHistory, PlatformPrice
)


@dataclass
class FrequencyAdjustmentResult:
    monitor_id: str
    old_level: str
    new_level: str
    old_interval: int
    new_interval: int
    reason: str
    adjustment_type: str
    volatility_score: float
    in_promotion: bool


@dataclass
class PromotionDetectionResult:
    detected: bool
    promotion_type: Optional[str]
    name: Optional[str]
    confidence: float
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    evidence: List[str]


class VolatilityAnalyzer:
    def __init__(self, window_size: int = 20):
        self.window_size = window_size
        self.price_history = defaultdict(lambda: deque(maxlen=window_size))

    def calculate_volatility(self, product_id: str, prices: List[float]) -> float:
        if len(prices) < 2:
            return 0.0
        
        for price in prices[-self.window_size:]:
            self.price_history[product_id].append(price)
        
        recent_prices = list(self.price_history[product_id])
        
        if len(recent_prices) < 2:
            return 0.0
        
        price_changes = []
        for i in range(1, len(recent_prices)):
            if recent_prices[i-1] > 0:
                change_pct = abs((recent_prices[i] - recent_prices[i-1]) / recent_prices[i-1])
                price_changes.append(change_pct)
        
        if not price_changes:
            return 0.0
        
        avg_change = mean(price_changes)
        
        if len(price_changes) >= 2:
            try:
                volatility = stdev(price_changes) + avg_change
            except:
                volatility = avg_change * 1.5
        else:
            volatility = avg_change * 1.5
        
        return min(volatility, 1.0)

    def calculate_price_change_frequency(self, product_id: str, 
                                         price_timestamps: List[Tuple[datetime, float]]) -> float:
        if len(price_timestamps) < 2:
            return 0.0
        
        changes = 0
        for i in range(1, len(price_timestamps)):
            if abs(price_timestamps[i][1] - price_timestamps[i-1][1]) > 0.01:
                changes += 1
        
        time_span = (price_timestamps[-1][0] - price_timestamps[0][0]).total_seconds() / 3600
        if time_span > 0:
            return changes / time_span
        return 0.0


class PromotionDetector:
    def __init__(self):
        self._init_promotion_patterns()
        self._init_promotion_calendar()

    def _init_promotion_patterns(self):
        self.promotion_keywords = {
            PromotionType.DOUBLE_ELEVEN: ["双11", "双十一", "11.11", "双11狂欢", "天猫双11"],
            PromotionType.DOUBLE_TWELVE: ["双12", "双十二", "12.12", "双12狂欢"],
            PromotionType.SIX_EIGHTEEN: ["618", "6.18", "京东618", "天猫618", "年中大促"],
            PromotionType.NEW_YEAR: ["元旦", "新年", "跨年", "new year"],
            PromotionType.SPRING_FESTIVAL: ["春节", "过年", "年货节", "新春", "除夕"],
            PromotionType.MID_YEAR: ["年中", "半年", "mid year"],
            PromotionType.PLATFORM_PROMO: ["平台券", "跨店满减", "品类券", "超级补贴"],
            PromotionType.BRAND_PROMO: ["品牌日", "品牌盛典", "超级品牌日", "周年庆"],
        }

        self.price_drop_keywords = [
            "直降", "降价", "立减", "特惠", "特价", "秒杀",
            "限时特惠", "今日特价", "历史最低", "新低",
            "满减", "多买多减", "买一送一", "折扣",
        ]

    def _init_promotion_calendar(self):
        now = datetime.now()
        current_year = now.year
        
        self.fixed_promotions = [
            {
                "type": PromotionType.DOUBLE_ELEVEN,
                "name": "双十一狂欢节",
                "start": datetime(current_year, 11, 1),
                "end": datetime(current_year, 11, 15),
                "pre_warm_days": 7,
                "cool_down_days": 3,
            },
            {
                "type": PromotionType.DOUBLE_TWELVE,
                "name": "双十二狂欢节",
                "start": datetime(current_year, 12, 10),
                "end": datetime(current_year, 12, 14),
                "pre_warm_days": 3,
                "cool_down_days": 3,
            },
            {
                "type": PromotionType.SIX_EIGHTEEN,
                "name": "618年中大促",
                "start": datetime(current_year, 6, 1),
                "end": datetime(current_year, 6, 20),
                "pre_warm_days": 7,
                "cool_down_days": 3,
            },
            {
                "type": PromotionType.NEW_YEAR,
                "name": "元旦跨年",
                "start": datetime(current_year, 12, 30),
                "end": datetime(current_year + 1, 1, 2),
                "pre_warm_days": 3,
                "cool_down_days": 1,
            },
            {
                "type": PromotionType.SPRING_FESTIVAL,
                "name": "春节年货节",
                "start": datetime(current_year, 1, 15),
                "end": datetime(current_year, 2, 5),
                "pre_warm_days": 5,
                "cool_down_days": 3,
            },
        ]

    def detect_from_calendar(self, check_date: Optional[datetime] = None) -> List[PromotionPeriod]:
        check_date = check_date or datetime.now()
        active_promotions = []
        
        for promo in self.fixed_promotions:
            pre_warm_start = promo["start"] - timedelta(days=promo["pre_warm_days"])
            cool_down_end = promo["end"] + timedelta(days=promo["cool_down_days"])
            
            if pre_warm_start <= check_date <= cool_down_end:
                active_promotions.append(PromotionPeriod(
                    name=promo["name"],
                    promotion_type=promo["type"],
                    is_all_platforms=True,
                    start_date=promo["start"],
                    end_date=promo["end"],
                    pre_warm_start=pre_warm_start,
                    cool_down_end=cool_down_end,
                    monitor_frequency_level=MonitorFrequencyLevel.CRITICAL,
                    expected_volatility=0.4,
                    priority=10 if promo["type"] in [PromotionType.DOUBLE_ELEVEN, PromotionType.SIX_EIGHTEEN] else 5,
                    is_auto_detected=False,
                    detection_source="calendar",
                    description=f"{promo['name']}官方大促期间",
                ))
        
        return active_promotions

    def detect_from_price_patterns(self, product_id: str, price_history: List[PriceHistory],
                                   recent_changes: List[PriceMonitorLog],
                                   days_back: int = 7) -> PromotionDetectionResult:
        evidence = []
        confidence = 0.0
        
        recent_prices = [float(p.price) for p in price_history[-30:]]
        if len(recent_prices) >= 7:
            avg_price = mean(recent_prices[:-3])
            current_price = recent_prices[-1]
            price_drop_pct = (avg_price - current_price) / avg_price if avg_price > 0 else 0
            
            if price_drop_pct >= 0.15:
                evidence.append(f"价格大幅下降 {price_drop_pct:.1%}")
                confidence += 0.3
            
            if len(recent_changes) >= 3:
                change_frequency = len(recent_changes) / days_back
                if change_frequency >= 0.5:
                    evidence.append(f"近期价格变动频繁 ({len(recent_changes)}次/{days_back}天)")
                    confidence += 0.2
        
        recent_changes_7d = [c for c in recent_changes 
                             if c.detected_at >= datetime.now() - timedelta(days=7)]
        
        price_drops = [c for c in recent_changes_7d 
                       if c.price_change_percent is not None and c.price_change_percent < -5]
        
        if len(price_drops) >= 2:
            evidence.append(f"多次显著降价 ({len(price_drops)}次)")
            confidence += 0.2
        
        avg_drop = mean([abs(c.price_change_percent) for c in price_drops]) if price_drops else 0
        if avg_drop >= 15:
            evidence.append(f"平均降幅 {avg_drop:.1f}%")
            confidence += 0.15
        
        if len(recent_prices) >= 10:
            min_price = min(recent_prices)
            if current_price <= min_price * 1.05:
                evidence.append("价格接近历史最低")
                confidence += 0.1
        
        if confidence > 0:
            confidence = min(confidence + 0.2, 1.0)
        
        promo_type = None
        name = None
        
        if confidence >= 0.5:
            current_date = datetime.now()
            for promo in self.fixed_promotions:
                if promo["start"] - timedelta(days=10) <= current_date <= promo["end"] + timedelta(days=5):
                    promo_type = promo["type"]
                    name = promo["name"]
                    confidence += 0.1
                    break
            
            if not promo_type:
                promo_type = PromotionType.OTHER
                name = "疑似促销活动"
        
        return PromotionDetectionResult(
            detected=confidence >= 0.5,
            promotion_type=promo_type.value if promo_type else None,
            name=name,
            confidence=min(confidence, 1.0),
            start_date=None,
            end_date=None,
            evidence=evidence
        )

    def detect_from_text(self, text: str) -> PromotionDetectionResult:
        if not text:
            return PromotionDetectionResult(
                detected=False,
                promotion_type=None,
                name=None,
                confidence=0.0,
                start_date=None,
                end_date=None,
                evidence=[]
            )
        
        text_lower = text.lower()
        evidence = []
        confidence = 0.0
        promo_type = None
        
        for ptype, keywords in self.promotion_keywords.items():
            matches = [kw for kw in keywords if kw.lower() in text_lower]
            if matches:
                evidence.extend(matches)
                confidence += len(matches) * 0.1
                if not promo_type:
                    promo_type = ptype
        
        price_drop_matches = [kw for kw in self.price_drop_keywords if kw in text_lower]
        if price_drop_matches:
            evidence.extend(price_drop_matches)
            confidence += len(price_drop_matches) * 0.05
        
        date_patterns = [
            r'(\d{1,2})月(\d{1,2})日',
            r'(\d{4})[.-](\d{1,2})[.-](\d{1,2})',
            r'(\d{1,2})[./](\d{1,2})',
        ]
        
        for pattern in date_patterns:
            matches = re.findall(pattern, text)
            if matches:
                evidence.append(f"包含日期信息: {matches[0]}")
                confidence += 0.1
        
        if confidence >= 0.3:
            confidence = min(confidence, 1.0)
            
            if not promo_type:
                promo_type = PromotionType.OTHER
            
            return PromotionDetectionResult(
                detected=True,
                promotion_type=promo_type.value,
                name=f"检测到{promo_type.value}活动",
                confidence=confidence,
                start_date=None,
                end_date=None,
                evidence=evidence
            )
        
        return PromotionDetectionResult(
            detected=False,
            promotion_type=None,
            name=None,
            confidence=confidence,
            start_date=None,
            end_date=None,
            evidence=evidence
        )


class DynamicFrequencyAdjuster:
    def __init__(self, db: Session):
        self.db = db
        self.volatility_analyzer = VolatilityAnalyzer()
        self.promotion_detector = PromotionDetector()
        
        self._init_frequency_levels()
        self._init_adjustment_rules()

    def _init_frequency_levels(self):
        self.level_order = [
            MonitorFrequencyLevel.LOW,
            MonitorFrequencyLevel.NORMAL,
            MonitorFrequencyLevel.HIGH,
            MonitorFrequencyLevel.VERY_HIGH,
            MonitorFrequencyLevel.CRITICAL,
        ]

    def _init_adjustment_rules(self):
        self.adjustment_rules = {
            "volatility": [
                (0.4, MonitorFrequencyLevel.HIGH),
                (0.25, MonitorFrequencyLevel.HIGH),
                (0.1, MonitorFrequencyLevel.NORMAL),
                (0.0, MonitorFrequencyLevel.LOW),
            ],
            "consecutive_changes": [
                (5, MonitorFrequencyLevel.CRITICAL),
                (3, MonitorFrequencyLevel.VERY_HIGH),
                (2, MonitorFrequencyLevel.HIGH),
            ],
            "alert_count": [
                (10, MonitorFrequencyLevel.CRITICAL),
                (5, MonitorFrequencyLevel.VERY_HIGH),
                (3, MonitorFrequencyLevel.HIGH),
            ],
        }

    def get_current_promotions(self) -> List[PromotionPeriod]:
        now = datetime.now()
        
        calendar_promotions = self.promotion_detector.detect_from_calendar(now)
        
        db_promotions = self.db.query(PromotionPeriod).filter(
            PromotionPeriod.is_active == True,
            PromotionPeriod.pre_warm_start <= now,
            PromotionPeriod.cool_down_end >= now
        ).all()
        
        all_promotions = []
        seen_types = set()
        
        for promo in db_promotions + calendar_promotions:
            key = (promo.promotion_type, promo.start_date, promo.end_date)
            if key not in seen_types:
                seen_types.add(key)
                all_promotions.append(promo)
        
        return sorted(all_promotions, key=lambda p: p.priority or 0, reverse=True)

    def is_in_promotion_period(self) -> Tuple[bool, Optional[PromotionPeriod]]:
        active_promotions = self.get_current_promotions()
        if active_promotions:
            return True, active_promotions[0]
        return False, None

    def adjust_frequency(self, monitor: MonitorSchedule,
                         force_reason: Optional[str] = None) -> Optional[FrequencyAdjustmentResult]:
        if not monitor.auto_adjust and not force_reason:
            return None
        
        if monitor.is_manual:
            return None
        
        old_level = monitor.frequency_level
        old_interval = monitor.check_interval_minutes
        
        new_level = old_level
        adjustment_reason = force_reason or ""
        adjustment_type = "auto"
        
        in_promo, active_promo = self.is_in_promotion_period()
        
        if in_promo and active_promo:
            promo_freq = active_promo.monitor_frequency_level or MonitorFrequencyLevel.VERY_HIGH
            if self._level_index(promo_freq) > self._level_index(new_level):
                new_level = promo_freq
                adjustment_reason = f"大促期间: {active_promo.name}"
                adjustment_type = "promotion"
        
        if not in_promo and not force_reason:
            price_history = self.db.query(PriceHistory).filter(
                PriceHistory.product_id == monitor.product_id
            ).order_by(PriceHistory.record_date.desc()).limit(30).all()
            
            prices = [float(p.price) for p in price_history]
            volatility = self.volatility_analyzer.calculate_volatility(
                monitor.product_id, prices
            )
            
            monitor.volatility_score = volatility
            
            recent_logs = self.db.query(PriceMonitorLog).filter(
                PriceMonitorLog.product_id == monitor.product_id,
                PriceMonitorLog.detected_at >= datetime.now() - timedelta(days=7)
            ).all()
            
            if recent_logs:
                price_changes = [
                    l for l in recent_logs 
                    if l.price_change_percent is not None and abs(l.price_change_percent) > 0.5
                ]
                monitor.consecutive_changes = len(price_changes)
                
                if len(price_changes) >= 3:
                    avg_change = mean([abs(l.price_change_percent) for l in price_changes])
                    volatility = max(volatility, min(avg_change / 20, 1.0))
            
            alert_count_24h = self.db.query(PriceMonitorLog).filter(
                PriceMonitorLog.product_id == monitor.product_id,
                PriceMonitorLog.is_alert_sent == True,
                PriceMonitorLog.detected_at >= datetime.now() - timedelta(hours=24)
            ).count()
            
            rule_based_level = self._get_level_by_rules(
                volatility, monitor.consecutive_changes, alert_count_24h
            )
            
            if self._level_index(rule_based_level) > self._level_index(new_level):
                new_level = rule_based_level
                adjustment_reason = self._generate_reason(
                    volatility, monitor.consecutive_changes, alert_count_24h
                )
                adjustment_type = "volatility"
            
            if self._should_downgrade(volatility, monitor.consecutive_changes, recent_logs):
                current_idx = self._level_index(new_level)
                if current_idx > self._level_index(MonitorFrequencyLevel.NORMAL):
                    new_level = self.level_order[current_idx - 1]
                    adjustment_reason = "价格趋于稳定，降低监测频率"
                    adjustment_type = "downgrade"
        
        if new_level == old_level and not force_reason:
            return None
        
        new_interval = FREQUENCY_MINUTES.get(new_level, 60)
        
        if force_reason and new_level == old_level:
            return None
        
        adjustment_log = FrequencyAdjustmentLog(
            monitor_schedule_id=monitor.id,
            old_frequency_level=old_level,
            new_frequency_level=new_level,
            old_interval_minutes=old_interval,
            new_interval_minutes=new_interval,
            adjustment_reason=adjustment_reason or force_reason,
            adjustment_type=adjustment_type,
            volatility_score=monitor.volatility_score,
            consecutive_changes=monitor.consecutive_changes,
            in_promotion=in_promo,
        )
        
        self.db.add(adjustment_log)
        
        monitor.frequency_level = new_level
        monitor.check_interval_minutes = new_interval
        monitor.adjust_reason = adjustment_reason or force_reason
        
        if monitor.last_checked_at:
            monitor.next_check_at = monitor.last_checked_at + timedelta(minutes=new_interval)
        
        self.db.commit()
        
        return FrequencyAdjustmentResult(
            monitor_id=monitor.id,
            old_level=old_level.value if hasattr(old_level, 'value') else str(old_level),
            new_level=new_level.value if hasattr(new_level, 'value') else str(new_level),
            old_interval=old_interval,
            new_interval=new_interval,
            reason=adjustment_reason or force_reason or "",
            adjustment_type=adjustment_type,
            volatility_score=monitor.volatility_score,
            in_promotion=in_promo
        )

    def _level_index(self, level: MonitorFrequencyLevel) -> int:
        try:
            return self.level_order.index(level)
        except ValueError:
            return 1

    def _get_level_by_rules(self, volatility: float, consecutive_changes: int,
                           alert_count: int) -> MonitorFrequencyLevel:
        for threshold, level in self.adjustment_rules["volatility"]:
            if volatility >= threshold:
                return level
        
        for threshold, level in self.adjustment_rules["consecutive_changes"]:
            if consecutive_changes >= threshold:
                return level
        
        for threshold, level in self.adjustment_rules["alert_count"]:
            if alert_count >= threshold:
                return level
        
        return MonitorFrequencyLevel.NORMAL

    def _generate_reason(self, volatility: float, consecutive_changes: int,
                        alert_count: int) -> str:
        reasons = []
        
        if volatility >= 0.4:
            reasons.append(f"价格波动剧烈 (波动率:{volatility:.2f})")
        elif volatility >= 0.25:
            reasons.append(f"价格波动较大 (波动率:{volatility:.2f})")
        elif volatility >= 0.1:
            reasons.append(f"价格有一定波动 (波动率:{volatility:.2f})")
        
        if consecutive_changes >= 5:
            reasons.append(f"连续价格变动 {consecutive_changes} 次")
        elif consecutive_changes >= 3:
            reasons.append(f"价格变动频繁 ({consecutive_changes} 次)")
        
        if alert_count >= 5:
            reasons.append(f"24小时内 {alert_count} 次提醒")
        
        return "; ".join(reasons) if reasons else "自动调整监测频率"

    def _should_downgrade(self, volatility: float, consecutive_changes: int,
                         recent_logs: List[PriceMonitorLog]) -> bool:
        if volatility >= 0.1:
            return False
        
        if consecutive_changes >= 1:
            return False
        
        recent_changes = [
            l for l in recent_logs
            if l.detected_at >= datetime.now() - timedelta(days=2)
            and l.price_change_percent is not None
            and abs(l.price_change_percent) > 1
        ]
        
        if len(recent_changes) > 0:
            return False
        
        return True

    def adjust_all_monitors(self) -> List[FrequencyAdjustmentResult]:
        monitors = self.db.query(MonitorSchedule).filter(
            MonitorSchedule.is_active == True,
            MonitorSchedule.auto_adjust == True
        ).all()
        
        results = []
        in_promo, _ = self.is_in_promotion_period()
        
        for monitor in monitors:
            result = self.adjust_frequency(
                monitor,
                force_reason="大促期间高频监测" if in_promo else None
            )
            if result:
                results.append(result)
        
        return results

    def create_monitor(self, product_id: str, platform: Optional[str] = None,
                       is_manual: bool = False,
                       manual_interval: Optional[int] = None) -> MonitorSchedule:
        
        existing = self.db.query(MonitorSchedule).filter(
            MonitorSchedule.product_id == product_id,
            MonitorSchedule.platform == platform
        ).first()
        
        if existing:
            if is_manual and manual_interval:
                existing.is_manual = True
                existing.check_interval_minutes = manual_interval
                existing.auto_adjust = False
                self.db.commit()
            return existing
        
        frequency_level = MonitorFrequencyLevel.NORMAL
        interval = 60
        
        if is_manual and manual_interval:
            for level, minutes in FREQUENCY_MINUTES.items():
                if minutes == manual_interval:
                    frequency_level = level
                    break
            interval = manual_interval or 60
        
        in_promo, active_promo = self.is_in_promotion_period()
        if in_promo and active_promo and not is_manual:
            frequency_level = active_promo.monitor_frequency_level or MonitorFrequencyLevel.VERY_HIGH
            interval = FREQUENCY_MINUTES.get(frequency_level, 15)
        
        monitor = MonitorSchedule(
            product_id=product_id,
            platform=platform,
            frequency_level=frequency_level,
            check_interval_minutes=interval,
            next_check_at=datetime.now() + timedelta(minutes=interval),
            is_active=True,
            is_manual=is_manual,
            auto_adjust=not is_manual,
        )
        
        self.db.add(monitor)
        self.db.commit()
        self.db.refresh(monitor)
        
        return monitor

    def get_due_monitors(self) -> List[MonitorSchedule]:
        now = datetime.now()
        return self.db.query(MonitorSchedule).filter(
            MonitorSchedule.is_active == True,
            MonitorSchedule.next_check_at <= now
        ).order_by(MonitorSchedule.next_check_at).all()

    def record_price_check(self, monitor: MonitorSchedule,
                           old_price: Optional[float],
                           new_price: float,
                           is_alert: bool = False) -> PriceMonitorLog:
        
        price_change = new_price - old_price if old_price else 0
        price_change_percent = (price_change / old_price * 100) if old_price and old_price > 0 else None
        
        in_promo, active_promo = self.is_in_promotion_period()
        
        log = PriceMonitorLog(
            product_id=monitor.product_id,
            platform=monitor.platform,
            old_price=old_price,
            new_price=new_price,
            price_change=price_change,
            price_change_percent=price_change_percent,
            monitor_schedule_id=monitor.id,
            is_alert_sent=is_alert,
            alert_sent_at=datetime.now() if is_alert else None,
            in_promotion_period=in_promo,
            promotion_type=active_promo.promotion_type.value if active_promo else None,
        )
        
        self.db.add(log)
        
        monitor.last_checked_at = datetime.now()
        monitor.next_check_at = datetime.now() + timedelta(minutes=monitor.check_interval_minutes)
        
        if price_change_percent is not None and abs(price_change_percent) > 0.5:
            self.adjust_frequency(monitor)
        else:
            self.db.commit()
        
        return log

    def get_monitor_stats(self, days: int = 7) -> Dict[str, Any]:
        start_date = datetime.now() - timedelta(days=days)
        
        total_monitors = self.db.query(MonitorSchedule).count()
        active_monitors = self.db.query(MonitorSchedule).filter(
            MonitorSchedule.is_active == True
        ).count()
        
        logs = self.db.query(PriceMonitorLog).filter(
            PriceMonitorLog.detected_at >= start_date
        ).all()
        
        price_changes = [l for l in logs if l.price_change_percent is not None]
        price_increases = [l for l in price_changes if l.price_change_percent > 0]
        price_decreases = [l for l in price_changes if l.price_change_percent < 0]
        
        alerts = [l for l in logs if l.is_alert_sent]
        
        promotions = [l for l in logs if l.in_promotion_period]
        
        changes_pct = [abs(l.price_change_percent) for l in price_changes if l.price_change_percent]
        
        stats = MonitorStats(
            stat_date=datetime.now(),
            total_monitored=total_monitors,
            active_monitors=active_monitors,
            price_changes_detected=len(price_changes),
            price_increases=len(price_increases),
            price_decreases=len(price_decreases),
            avg_change_percent=mean(changes_pct) if changes_pct else None,
            max_change_percent=max(changes_pct) if changes_pct else None,
            alerts_sent=len(alerts),
            frequency_adjustments=self.db.query(FrequencyAdjustmentLog).filter(
                FrequencyAdjustmentLog.adjusted_at >= start_date
            ).count(),
            in_promotion_count=len(promotions),
            total_checks=len(logs),
            checks_success=len(logs),
        )
        
        self.db.add(stats)
        self.db.commit()
        
        return {
            "period_days": days,
            "total_monitors": total_monitors,
            "active_monitors": active_monitors,
            "price_changes": len(price_changes),
            "price_increases": len(price_increases),
            "price_decreases": len(price_decreases),
            "avg_change_percent": stats.avg_change_percent,
            "max_change_percent": stats.max_change_percent,
            "alerts_sent": len(alerts),
            "frequency_adjustments": stats.frequency_adjustments,
            "promotion_checks": len(promotions),
            "frequency_distribution": self._get_frequency_distribution(),
            "current_promotions": [
                {
                    "name": p.name,
                    "type": p.promotion_type.value,
                    "start": p.start_date.isoformat(),
                    "end": p.end_date.isoformat(),
                    "frequency_level": p.monitor_frequency_level.value,
                }
                for p in self.get_current_promotions()
            ]
        }

    def _get_frequency_distribution(self) -> Dict[str, int]:
        distribution = defaultdict(int)
        
        monitors = self.db.query(MonitorSchedule).filter(
            MonitorSchedule.is_active == True
        ).all()
        
        for monitor in monitors:
            level_value = monitor.frequency_level.value if hasattr(monitor.frequency_level, 'value') else str(monitor.frequency_level)
            distribution[level_value] += 1
        
        return dict(distribution)

    def auto_detect_promotion(self, product_id: Optional[str] = None,
                             text: Optional[str] = None) -> List[PromotionPeriod]:
        detected_periods = []
        
        if text:
            text_result = self.promotion_detector.detect_from_text(text)
            if text_result.detected and text_result.confidence >= 0.6:
                start = datetime.now()
                end = datetime.now() + timedelta(days=7)
                
                period = PromotionPeriod(
                    name=text_result.name or "检测到促销活动",
                    promotion_type=text_result.promotion_type or PromotionType.OTHER,
                    is_all_platforms=product_id is None,
                    start_date=start,
                    end_date=end,
                    monitor_frequency_level=MonitorFrequencyLevel.VERY_HIGH,
                    expected_volatility=0.3,
                    is_auto_detected=True,
                    detection_confidence=text_result.confidence,
                    detection_source="text_analysis",
                    description=f"自动检测到的促销活动，证据: {', '.join(text_result.evidence)}",
                )
                
                self.db.add(period)
                detected_periods.append(period)
        
        if product_id:
            price_history = self.db.query(PriceHistory).filter(
                PriceHistory.product_id == product_id
            ).order_by(PriceHistory.record_date.desc()).limit(30).all()
            
            recent_logs = self.db.query(PriceMonitorLog).filter(
                PriceMonitorLog.product_id == product_id,
                PriceMonitorLog.detected_at >= datetime.now() - timedelta(days=14)
            ).all()
            
            pattern_result = self.promotion_detector.detect_from_price_patterns(
                product_id, price_history, recent_logs
            )
            
            if pattern_result.detected and pattern_result.confidence >= 0.5:
                start = datetime.now()
                end = datetime.now() + timedelta(days=7)
                
                period = PromotionPeriod(
                    name=pattern_result.name or "疑似促销活动",
                    promotion_type=pattern_result.promotion_type or PromotionType.OTHER,
                    is_all_platforms=False,
                    start_date=start,
                    end_date=end,
                    monitor_frequency_level=MonitorFrequencyLevel.HIGH,
                    expected_volatility=0.25,
                    is_auto_detected=True,
                    detection_confidence=pattern_result.confidence,
                    detection_source="price_pattern",
                    description=f"基于价格模式检测的促销，证据: {', '.join(pattern_result.evidence)}",
                )
                
                self.db.add(period)
                detected_periods.append(period)
        
        if detected_periods:
            self.db.commit()
            
            for period in detected_periods:
                self.adjust_all_monitors()
        
        return detected_periods
