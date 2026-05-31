from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from datetime import datetime

from ..database import get_db
from ..models import MonitorSchedule, MonitorFrequencyLevel, MonitorScheduleType
from ..models import PromotionPeriod, PriceMonitorLog, FrequencyAdjustmentLog
from ..services.dynamic_monitor import DynamicFrequencyAdjuster

router = APIRouter(prefix="/monitor", tags=["动态价格监测"])


class CreateMonitorRequest(BaseModel):
    product_id: str
    user_id: str
    target_price: Optional[float] = None
    price_drop_threshold: float = 0.05
    schedule_type: str = "auto"
    frequency_minutes: Optional[int] = 60
    alert_enabled: bool = True
    webhook_url: Optional[str] = None
    notify_email: Optional[str] = None
    notify_wechat: Optional[str] = None


class UpdateMonitorRequest(BaseModel):
    target_price: Optional[float] = None
    price_drop_threshold: Optional[float] = None
    frequency_minutes: Optional[int] = None
    schedule_type: Optional[str] = None
    alert_enabled: Optional[bool] = None
    webhook_url: Optional[str] = None
    notify_email: Optional[str] = None
    notify_wechat: Optional[str] = None


class RecordPriceCheckRequest(BaseModel):
    old_price: Optional[float] = None
    new_price: float
    is_alert: bool = False


class AdjustFrequencyRequest(BaseModel):
    force_reason: Optional[str] = None


class CreatePromotionRequest(BaseModel):
    name: str
    platform: Optional[str] = None
    start_date: datetime
    end_date: datetime
    preheat_days: int = 3
    cooldown_days: int = 2
    monitor_frequency_level: str = "very_high"
    description: Optional[str] = None


@router.post("/schedules", summary="创建监测任务")
async def create_monitor_schedule(request: CreateMonitorRequest, db: Session = Depends(get_db)):
    try:
        schedule_type_enum = MonitorScheduleType(request.schedule_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的调度类型")
    
    freq_level = None
    if schedule_type_enum == MonitorScheduleType.AUTO:
        freq_level = MonitorFrequencyLevel.NORMAL
    elif request.frequency_minutes:
        freq_level = MonitorFrequencyLevel.from_minutes(request.frequency_minutes)
    
    monitor = MonitorSchedule(
        product_id=request.product_id,
        user_id=request.user_id,
        target_price=request.target_price,
        price_drop_threshold=request.price_drop_threshold,
        schedule_type=schedule_type_enum,
        frequency_level=freq_level,
        frequency_minutes=freq_level.minutes if freq_level else request.frequency_minutes,
        alert_enabled=request.alert_enabled,
        webhook_url=request.webhook_url,
        notify_email=request.notify_email,
        notify_wechat=request.notify_wechat,
    )
    
    db.add(monitor)
    db.commit()
    db.refresh(monitor)
    
    return {
        "success": True,
        "data": {
            "id": monitor.id,
            "product_id": monitor.product_id,
            "schedule_type": monitor.schedule_type.value,
            "frequency_level": monitor.frequency_level.value if monitor.frequency_level else None,
            "frequency_minutes": monitor.frequency_minutes,
            "next_check_at": monitor.next_check_at.isoformat(),
            "is_active": monitor.is_active,
        }
    }


@router.get("/schedules", summary="获取监测任务列表")
async def get_monitor_schedules(
    user_id: Optional[str] = None,
    product_id: Optional[str] = None,
    is_active: Optional[bool] = None,
    schedule_type: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    query = db.query(MonitorSchedule)
    
    if user_id:
        query = query.filter(MonitorSchedule.user_id == user_id)
    if product_id:
        query = query.filter(MonitorSchedule.product_id == product_id)
    if is_active is not None:
        query = query.filter(MonitorSchedule.is_active == is_active)
    if schedule_type:
        try:
            type_enum = MonitorScheduleType(schedule_type)
            query = query.filter(MonitorSchedule.schedule_type == type_enum)
        except ValueError:
            pass
    
    total = query.count()
    monitors = query.order_by(MonitorSchedule.created_at.desc()).offset(offset).limit(limit).all()
    
    return {
        "success": True,
        "data": [
            {
                "id": m.id,
                "product_id": m.product_id,
                "target_price": float(m.target_price) if m.target_price else None,
                "price_drop_threshold": float(m.price_drop_threshold),
                "schedule_type": m.schedule_type.value,
                "frequency_level": m.frequency_level.value if m.frequency_level else None,
                "frequency_minutes": m.frequency_minutes,
                "consecutive_changes": m.consecutive_changes,
                "alerts_24h": m.alerts_24h,
                "last_price": float(m.last_price) if m.last_price else None,
                "lowest_price": float(m.lowest_price) if m.lowest_price else None,
                "next_check_at": m.next_check_at.isoformat(),
                "last_check_at": m.last_check_at.isoformat() if m.last_check_at else None,
                "is_active": m.is_active,
                "alert_enabled": m.alert_enabled,
                "created_at": m.created_at.isoformat(),
            }
            for m in monitors
        ],
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.get("/schedules/{schedule_id}", summary="获取监测任务详情")
async def get_monitor_detail(schedule_id: str, db: Session = Depends(get_db)):
    monitor = db.query(MonitorSchedule).filter(MonitorSchedule.id == schedule_id).first()
    
    if not monitor:
        raise HTTPException(status_code=404, detail="监测任务不存在")
    
    return {
        "success": True,
        "data": {
            "id": monitor.id,
            "product_id": monitor.product_id,
            "user_id": monitor.user_id,
            "target_price": float(monitor.target_price) if monitor.target_price else None,
            "price_drop_threshold": float(monitor.price_drop_threshold),
            "schedule_type": monitor.schedule_type.value,
            "frequency_level": monitor.frequency_level.value if monitor.frequency_level else None,
            "frequency_minutes": monitor.frequency_minutes,
            "consecutive_changes": monitor.consecutive_changes,
            "alerts_24h": monitor.alerts_24h,
            "last_price": float(monitor.last_price) if monitor.last_price else None,
            "lowest_price": float(monitor.lowest_price) if monitor.lowest_price else None,
            "highest_price": float(monitor.highest_price) if monitor.highest_price else None,
            "avg_price": float(monitor.avg_price) if monitor.avg_price else None,
            "next_check_at": monitor.next_check_at.isoformat(),
            "last_check_at": monitor.last_check_at.isoformat() if monitor.last_check_at else None,
            "last_price_change": monitor.last_price_change.isoformat() if monitor.last_price_change else None,
            "is_active": monitor.is_active,
            "alert_enabled": monitor.alert_enabled,
            "webhook_url": monitor.webhook_url,
            "notify_email": monitor.notify_email,
            "notify_wechat": monitor.notify_wechat,
            "created_at": monitor.created_at.isoformat(),
            "updated_at": monitor.updated_at.isoformat(),
        }
    }


@router.put("/schedules/{schedule_id}", summary="更新监测任务")
async def update_monitor_schedule(schedule_id: str, request: UpdateMonitorRequest,
                                   db: Session = Depends(get_db)):
    monitor = db.query(MonitorSchedule).filter(MonitorSchedule.id == schedule_id).first()
    
    if not monitor:
        raise HTTPException(status_code=404, detail="监测任务不存在")
    
    if request.target_price is not None:
        monitor.target_price = request.target_price
    if request.price_drop_threshold is not None:
        monitor.price_drop_threshold = request.price_drop_threshold
    if request.frequency_minutes is not None:
        monitor.frequency_minutes = request.frequency_minutes
        monitor.frequency_level = MonitorFrequencyLevel.from_minutes(request.frequency_minutes)
    if request.schedule_type is not None:
        try:
            monitor.schedule_type = MonitorScheduleType(request.schedule_type)
        except ValueError:
            raise HTTPException(status_code=400, detail="无效的调度类型")
    if request.alert_enabled is not None:
        monitor.alert_enabled = request.alert_enabled
    if request.webhook_url is not None:
        monitor.webhook_url = request.webhook_url
    if request.notify_email is not None:
        monitor.notify_email = request.notify_email
    if request.notify_wechat is not None:
        monitor.notify_wechat = request.notify_wechat
    
    monitor.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(monitor)
    
    return {
        "success": True,
        "message": "监测任务已更新",
        "data": {
            "id": monitor.id,
            "frequency_minutes": monitor.frequency_minutes,
            "frequency_level": monitor.frequency_level.value if monitor.frequency_level else None,
        }
    }


@router.post("/schedules/{schedule_id}/adjust-frequency", summary="调整监测频率")
async def adjust_monitor_frequency(schedule_id: str, request: AdjustFrequencyRequest,
                                    db: Session = Depends(get_db)):
    monitor = db.query(MonitorSchedule).filter(MonitorSchedule.id == schedule_id).first()
    
    if not monitor:
        raise HTTPException(status_code=404, detail="监测任务不存在")
    
    if monitor.schedule_type != MonitorScheduleType.AUTO:
        raise HTTPException(status_code=400, detail="仅自动调度任务可调整频率")
    
    adjuster = DynamicFrequencyAdjuster(db=db)
    result = adjuster.adjust_frequency(monitor, force_reason=request.force_reason)
    
    if not result:
        return {
            "success": True,
            "message": "频率无需调整",
            "data": {
                "current_frequency": monitor.frequency_minutes,
                "current_level": monitor.frequency_level.value if monitor.frequency_level else None,
            }
        }
    
    return {
        "success": True,
        "data": {
            "old_level": result.old_level.value if result.old_level else None,
            "new_level": result.new_level.value,
            "old_frequency_minutes": result.old_frequency_minutes,
            "new_frequency_minutes": result.new_frequency_minutes,
            "reason": result.reason,
            "adjustment_type": result.adjustment_type,
            "volatility": result.volatility,
        }
    }


@router.post("/schedules/{schedule_id}/price-check", summary="记录价格检查")
async def record_price_check(schedule_id: str, request: RecordPriceCheckRequest,
                              db: Session = Depends(get_db)):
    monitor = db.query(MonitorSchedule).filter(MonitorSchedule.id == schedule_id).first()
    
    if not monitor:
        raise HTTPException(status_code=404, detail="监测任务不存在")
    
    adjuster = DynamicFrequencyAdjuster(db=db)
    log = adjuster.record_price_check(
        monitor=monitor,
        old_price=request.old_price,
        new_price=request.new_price,
        is_alert=request.is_alert
    )
    
    return {
        "success": True,
        "data": {
            "log_id": log.id,
            "product_id": log.product_id,
            "old_price": float(log.old_price) if log.old_price else None,
            "new_price": float(log.new_price),
            "price_change_percent": float(log.price_change_percent) if log.price_change_percent else None,
            "is_alert": log.is_alert,
            "current_frequency_minutes": monitor.frequency_minutes,
            "next_check_at": monitor.next_check_at.isoformat(),
        }
    }


@router.post("/adjust-all", summary="批量调整所有监测频率")
async def adjust_all_monitors(db: Session = Depends(get_db)):
    adjuster = DynamicFrequencyAdjuster(db=db)
    results = adjuster.adjust_all_monitors()
    
    summary = {
        "total": len(results),
        "upgraded": sum(1 for r in results if r.adjustment_type == "upgrade"),
        "downgraded": sum(1 for r in results if r.adjustment_type == "downgrade"),
        "promotion": sum(1 for r in results if r.adjustment_type == "promotion"),
        "no_change": sum(1 for r in results if r.adjustment_type == "no_change"),
    }
    
    return {
        "success": True,
        "summary": summary,
        "data": [
            {
                "monitor_id": r.monitor_id,
                "old_level": r.old_level.value if r.old_level else None,
                "new_level": r.new_level.value,
                "reason": r.reason,
                "adjustment_type": r.adjustment_type,
            }
            for r in results
        ]
    }


@router.delete("/schedules/{schedule_id}", summary="删除监测任务")
async def delete_monitor_schedule(schedule_id: str, db: Session = Depends(get_db)):
    monitor = db.query(MonitorSchedule).filter(MonitorSchedule.id == schedule_id).first()
    
    if not monitor:
        raise HTTPException(status_code=404, detail="监测任务不存在")
    
    monitor.is_active = False
    db.commit()
    
    return {
        "success": True,
        "message": "监测任务已停用"
    }


@router.post("/schedules/{schedule_id}/activate", summary="激活监测任务")
async def activate_monitor_schedule(schedule_id: str, db: Session = Depends(get_db)):
    monitor = db.query(MonitorSchedule).filter(MonitorSchedule.id == schedule_id).first()
    
    if not monitor:
        raise HTTPException(status_code=404, detail="监测任务不存在")
    
    monitor.is_active = True
    db.commit()
    
    return {
        "success": True,
        "message": "监测任务已激活"
    }


@router.post("/promotions", summary="创建促销周期")
async def create_promotion_period(request: CreatePromotionRequest, db: Session = Depends(get_db)):
    try:
        freq_level = MonitorFrequencyLevel(request.monitor_frequency_level)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的频率等级")
    
    promotion = PromotionPeriod(
        name=request.name,
        platform=request.platform,
        start_date=request.start_date,
        end_date=request.end_date,
        preheat_days=request.preheat_days,
        cooldown_days=request.cooldown_days,
        monitor_frequency_level=freq_level,
        description=request.description,
    )
    
    db.add(promotion)
    db.commit()
    db.refresh(promotion)
    
    return {
        "success": True,
        "data": {
            "id": promotion.id,
            "name": promotion.name,
            "start_date": promotion.start_date.isoformat(),
            "end_date": promotion.end_date.isoformat(),
            "monitor_frequency": promotion.monitor_frequency_level.value,
            "is_active": promotion.is_active,
        }
    }


@router.get("/promotions", summary="获取促销周期列表")
async def get_promotion_periods(
    is_active: Optional[bool] = None,
    include_expired: bool = False,
    db: Session = Depends(get_db)
):
    query = db.query(PromotionPeriod)
    
    if is_active is not None:
        query = query.filter(PromotionPeriod.is_active == is_active)
    
    if not include_expired:
        now = datetime.utcnow()
        query = query.filter(PromotionPeriod.end_date >= now)
    
    promotions = query.order_by(PromotionPeriod.start_date).all()
    
    return {
        "success": True,
        "data": [
            {
                "id": p.id,
                "name": p.name,
                "platform": p.platform,
                "start_date": p.start_date.isoformat(),
                "end_date": p.end_date.isoformat(),
                "preheat_days": p.preheat_days,
                "cooldown_days": p.cooldown_days,
                "monitor_frequency_level": p.monitor_frequency_level.value,
                "description": p.description,
                "is_active": p.is_active,
            }
            for p in promotions
        ]
    }


@router.delete("/promotions/{promotion_id}", summary="删除促销周期")
async def delete_promotion_period(promotion_id: str, db: Session = Depends(get_db)):
    promotion = db.query(PromotionPeriod).filter(PromotionPeriod.id == promotion_id).first()
    
    if not promotion:
        raise HTTPException(status_code=404, detail="促销周期不存在")
    
    promotion.is_active = False
    db.commit()
    
    return {
        "success": True,
        "message": "促销周期已停用"
    }


@router.get("/promotions/current", summary="获取当前促销周期")
async def get_current_promotion(db: Session = Depends(get_db)):
    adjuster = DynamicFrequencyAdjuster(db=db)
    in_promo, active_promo = adjuster.is_in_promotion_period()
    
    if not active_promo:
        return {
            "success": True,
            "data": {
                "in_promotion": False,
                "promotion": None,
                "stage": None,
            }
        }
    
    now = datetime.utcnow()
    preheat_start = active_promo.start_date - __import__('datetime').timedelta(days=active_promo.preheat_days)
    cooldown_start = active_promo.end_date + __import__('datetime').timedelta(days=1)
    cooldown_end = cooldown_start + __import__('datetime').timedelta(days=active_promo.cooldown_days)
    
    if now < active_promo.start_date:
        stage = "preheat"
    elif now > active_promo.end_date:
        stage = "cooldown"
    else:
        stage = "active"
    
    return {
        "success": True,
        "data": {
            "in_promotion": in_promo,
            "stage": stage,
            "promotion": {
                "id": active_promo.id,
                "name": active_promo.name,
                "start_date": active_promo.start_date.isoformat(),
                "end_date": active_promo.end_date.isoformat(),
                "monitor_frequency_level": active_promo.monitor_frequency_level.value,
            }
        }
    }


@router.post("/promotions/detect", summary="自动检测促销")
async def auto_detect_promotion(
    product_id: Optional[str] = None,
    text: Optional[str] = None,
    db: Session = Depends(get_db)
):
    adjuster = DynamicFrequencyAdjuster(db=db)
    detected = adjuster.auto_detect_promotion(product_id, text)
    
    return {
        "success": True,
        "data": [
            {
                "id": p.id,
                "name": p.name,
                "start_date": p.start_date.isoformat(),
                "end_date": p.end_date.isoformat(),
                "monitor_frequency_level": p.monitor_frequency_level.value,
                "is_active": p.is_active,
            }
            for p in detected
        ],
        "count": len(detected)
    }


@router.get("/logs/{schedule_id}", summary="获取监测日志")
async def get_monitor_logs(
    schedule_id: str,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    monitor = db.query(MonitorSchedule).filter(MonitorSchedule.id == schedule_id).first()
    
    if not monitor:
        raise HTTPException(status_code=404, detail="监测任务不存在")
    
    query = db.query(PriceMonitorLog).filter(
        PriceMonitorLog.monitor_schedule_id == schedule_id
    )
    
    total = query.count()
    logs = query.order_by(PriceMonitorLog.timestamp.desc()).offset(offset).limit(limit).all()
    
    return {
        "success": True,
        "data": [
            {
                "id": log.id,
                "old_price": float(log.old_price) if log.old_price else None,
                "new_price": float(log.new_price),
                "price_change_percent": float(log.price_change_percent) if log.price_change_percent else None,
                "is_alert": log.is_alert,
                "frequency_minutes": log.frequency_minutes,
                "timestamp": log.timestamp.isoformat(),
            }
            for log in logs
        ],
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.get("/adjustments/{schedule_id}", summary="获取频率调整日志")
async def get_frequency_adjustments(
    schedule_id: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    query = db.query(FrequencyAdjustmentLog).filter(
        FrequencyAdjustmentLog.monitor_schedule_id == schedule_id
    )
    
    total = query.count()
    logs = query.order_by(FrequencyAdjustmentLog.adjusted_at.desc()).offset(offset).limit(limit).all()
    
    return {
        "success": True,
        "data": [
            {
                "id": log.id,
                "old_level": log.old_level.value if log.old_level else None,
                "new_level": log.new_level.value,
                "old_frequency_minutes": log.old_frequency_minutes,
                "new_frequency_minutes": log.new_frequency_minutes,
                "reason": log.reason,
                "adjustment_type": log.adjustment_type,
                "volatility": float(log.volatility) if log.volatility else None,
                "adjusted_at": log.adjusted_at.isoformat(),
            }
            for log in logs
        ],
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.get("/stats", summary="获取监测统计")
async def get_monitor_stats(
    hours: int = Query(24, ge=1, le=720),
    db: Session = Depends(get_db)
):
    from ..models import MonitorStats
    from sqlalchemy import func
    
    start_time = datetime.utcnow() - __import__('datetime').timedelta(hours=hours)
    
    total_monitors = db.query(MonitorSchedule).count()
    active_monitors = db.query(MonitorSchedule).filter(MonitorSchedule.is_active == True).count()
    auto_monitors = db.query(MonitorSchedule).filter(
        MonitorSchedule.schedule_type == MonitorScheduleType.AUTO,
        MonitorSchedule.is_active == True
    ).count()
    
    level_stats = db.query(
        MonitorSchedule.frequency_level,
        func.count(MonitorSchedule.id)
    ).filter(
        MonitorSchedule.is_active == True,
        MonitorSchedule.frequency_level.isnot(None)
    ).group_by(MonitorSchedule.frequency_level).all()
    
    recent_logs = db.query(PriceMonitorLog).filter(
        PriceMonitorLog.timestamp >= start_time
    )
    total_checks = recent_logs.count()
    total_alerts = recent_logs.filter(PriceMonitorLog.is_alert == True).count()
    
    recent_adjustments = db.query(FrequencyAdjustmentLog).filter(
        FrequencyAdjustmentLog.adjusted_at >= start_time
    )
    total_adjustments = recent_adjustments.count()
    
    type_stats = recent_adjustments.with_entities(
        FrequencyAdjustmentLog.adjustment_type,
        func.count(FrequencyAdjustmentLog.id)
    ).group_by(FrequencyAdjustmentLog.adjustment_type).all()
    
    adjuster = DynamicFrequencyAdjuster(db=db)
    in_promo, active_promo = adjuster.is_in_promotion_period()
    
    return {
        "success": True,
        "data": {
            "period_hours": hours,
            "total_monitors": total_monitors,
            "active_monitors": active_monitors,
            "auto_monitors": auto_monitors,
            "total_price_checks": total_checks,
            "total_alerts": total_alerts,
            "total_adjustments": total_adjustments,
            "in_promotion": in_promo,
            "current_promotion": active_promo.name if active_promo else None,
            "frequency_distribution": [
                {"level": l.value if l else "manual", "count": c} for l, c in level_stats
            ],
            "adjustment_distribution": [
                {"type": t, "count": c} for t, c in type_stats
            ],
        }
    }
