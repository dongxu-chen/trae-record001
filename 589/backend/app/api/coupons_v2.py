from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from datetime import datetime, date

from ..database import get_db
from ..models import CouponShare, CouponShareStatus, VerificationStatus
from ..services.coupon_crowdsource import CouponShareService, CouponRuleMiner

router = APIRouter(prefix="/coupons-v2", tags=["优惠券众包系统"])


class ShareCouponRequest(BaseModel):
    user_id: str
    user_nickname: str
    platform: str
    code: str
    discount: float
    discount_type: str = Field(..., description="percentage or fixed")
    min_amount: float = 0.0
    max_discount: Optional[float] = None
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None
    applicable_products: Optional[str] = None
    applicable_categories: Optional[str] = None
    description: Optional[str] = None
    source_url: Optional[str] = None


class VerifyCouponRequest(BaseModel):
    verifier_id: str
    is_valid: bool
    verification_method: str = "manual"
    actual_discount: Optional[float] = None
    verification_result: Optional[str] = None


class VoteCouponRequest(BaseModel):
    user_id: str
    vote_type: str = Field(..., description="up or down")


class RecordUsageRequest(BaseModel):
    user_id: str
    product_id: Optional[str] = None
    original_price: float
    discount_amount: float
    final_price: float
    is_successful: bool = True
    error_message: Optional[str] = None
    coupon_source: str = "crowdsource"


class MineRulesRequest(BaseModel):
    platform: Optional[str] = None
    days: int = 30
    min_frequency: int = 5


class ApplyRulesRequest(BaseModel):
    text: str
    platform: str
    price: float


@router.post("/share", summary="分享优惠券")
async def share_coupon(request: ShareCouponRequest, db: Session = Depends(get_db)):
    service = CouponShareService(db)
    result = service.share_coupon(
        user_id=request.user_id,
        user_nickname=request.user_nickname,
        platform=request.platform,
        code=request.code,
        discount=request.discount,
        discount_type=request.discount_type,
        min_amount=request.min_amount,
        max_discount=request.max_discount,
        valid_from=request.valid_from,
        valid_to=request.valid_to,
        applicable_products=request.applicable_products,
        applicable_categories=request.applicable_categories,
        description=request.description,
        source_url=request.source_url
    )
    
    return {
        "success": True,
        "data": {
            "share_id": result.share_id,
            "status": result.status,
            "message": result.message,
            "reward_points": result.reward_points,
            "verification_url": result.verification_url,
        }
    }


@router.post("/{coupon_id}/verify", summary="验证优惠券")
async def verify_coupon(coupon_id: str, request: VerifyCouponRequest,
                         db: Session = Depends(get_db)):
    service = CouponShareService(db)
    result = service.verify_coupon(
        coupon_share_id=coupon_id,
        verifier_id=request.verifier_id,
        is_valid=request.is_valid,
        verification_method=request.verification_method,
        actual_discount=request.actual_discount,
        verification_result=request.verification_result
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message"))
    
    return {
        "success": True,
        "data": result
    }


@router.post("/{coupon_id}/vote", summary="投票优惠券")
async def vote_coupon(coupon_id: str, request: VoteCouponRequest,
                       db: Session = Depends(get_db)):
    service = CouponShareService(db)
    result = service.vote_coupon(
        coupon_share_id=coupon_id,
        user_id=request.user_id,
        vote_type=request.vote_type
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message"))
    
    return {
        "success": True,
        "data": result
    }


@router.get("/pending-verifications", summary="获取待验证优惠券列表")
async def get_pending_verifications(
    user_id: str,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    service = CouponShareService(db)
    coupons = service.get_pending_verifications(user_id, limit)
    
    return {
        "success": True,
        "data": coupons,
        "count": len(coupons)
    }


@router.get("/approved", summary="获取已通过优惠券列表")
async def get_approved_coupons(
    platform: Optional[str] = None,
    category: Optional[str] = None,
    min_discount: Optional[float] = None,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    service = CouponShareService(db)
    coupons = service.get_approved_coupons(platform, category, min_discount, limit)
    
    return {
        "success": True,
        "data": coupons,
        "count": len(coupons)
    }


@router.get("/user/{user_id}/shares", summary="获取用户分享的优惠券")
async def get_user_shares(
    user_id: str,
    status: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    query = db.query(CouponShare).filter(CouponShare.user_id == user_id)
    
    if status:
        try:
            status_enum = CouponShareStatus(status)
            query = query.filter(CouponShare.status == status_enum)
        except ValueError:
            pass
    
    total = query.count()
    shares = query.order_by(CouponShare.created_at.desc()).offset(offset).limit(limit).all()
    
    return {
        "success": True,
        "data": [
            {
                "id": s.id,
                "platform": s.platform,
                "code": s.code,
                "discount": float(s.discount),
                "discount_type": s.discount_type,
                "min_amount": float(s.min_amount),
                "status": s.status.value,
                "verification_status": s.verification_status.value,
                "upvotes": s.upvotes,
                "downvotes": s.downvotes,
                "reward_points": s.reward_points,
                "verification_count": s.verification_count,
                "success_count": s.success_count,
                "created_at": s.created_at.isoformat(),
                "valid_to": s.valid_to.isoformat() if s.valid_to else None,
            }
            for s in shares
        ],
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.get("/user/{user_id}/rewards", summary="获取用户奖励积分")
async def get_user_rewards(user_id: str, db: Session = Depends(get_db)):
    service = CouponShareService(db)
    rewards = service.get_user_rewards(user_id)
    
    return {
        "success": True,
        "data": rewards
    }


@router.post("/{coupon_id}/usage", summary="记录优惠券使用")
async def record_coupon_usage(coupon_id: str, request: RecordUsageRequest,
                                db: Session = Depends(get_db)):
    service = CouponShareService(db)
    service.record_usage(
        coupon_id=coupon_id,
        user_id=request.user_id,
        product_id=request.product_id,
        original_price=request.original_price,
        discount_amount=request.discount_amount,
        final_price=request.final_price,
        is_successful=request.is_successful,
        error_message=request.error_message,
        coupon_source=request.coupon_source
    )
    
    return {
        "success": True,
        "message": "使用记录已保存"
    }


@router.get("/{coupon_id}", summary="获取优惠券详情")
async def get_coupon_detail(coupon_id: str, db: Session = Depends(get_db)):
    coupon = db.query(CouponShare).filter(CouponShare.id == coupon_id).first()
    
    if not coupon:
        raise HTTPException(status_code=404, detail="优惠券不存在")
    
    return {
        "success": True,
        "data": {
            "id": coupon.id,
            "platform": coupon.platform,
            "code": coupon.code,
            "discount": float(coupon.discount),
            "discount_type": coupon.discount_type,
            "min_amount": float(coupon.min_amount),
            "max_discount": float(coupon.max_discount) if coupon.max_discount else None,
            "valid_from": coupon.valid_from.isoformat() if coupon.valid_from else None,
            "valid_to": coupon.valid_to.isoformat() if coupon.valid_to else None,
            "applicable_products": coupon.applicable_products,
            "applicable_categories": coupon.applicable_categories,
            "description": coupon.description,
            "source_url": coupon.source_url,
            "status": coupon.status.value,
            "verification_status": coupon.verification_status.value,
            "upvotes": coupon.upvotes,
            "downvotes": coupon.downvotes,
            "shared_by": coupon.user_nickname,
            "verification_count": coupon.verification_count,
            "success_count": coupon.success_count,
            "fail_count": coupon.fail_count,
            "success_rate": coupon.success_count / max(coupon.verification_count, 1),
            "reward_points": coupon.reward_points,
            "review_comment": coupon.review_comment,
            "created_at": coupon.created_at.isoformat(),
            "updated_at": coupon.updated_at.isoformat(),
        }
    }


@router.post("/mine", summary="挖掘优惠券规则")
async def mine_coupon_rules(request: MineRulesRequest, db: Session = Depends(get_db)):
    miner = CouponRuleMiner(db)
    rules = miner.mine_from_shares(request.platform, request.days, request.min_frequency)
    
    for rule in rules:
        miner.save_mined_rule(
            pattern=rule["pattern"],
            platform=rule["platform"],
            rule_type="mined_pattern",
            support=rule["support"],
            confidence=rule["success_rate"],
            lift=1.0,
            frequency=rule["frequency"],
            min_amount=rule["avg_min_amount"],
            max_discount=rule["avg_discount"],
            auto_apply=rule["success_rate"] >= 0.8
        )
    
    return {
        "success": True,
        "data": rules,
        "count": len(rules)
    }


@router.post("/mine/association", summary="挖掘关联规则")
async def mine_association_rules(
    transactions: List[List[str]],
    min_support: float = Query(0.1, ge=0.01, le=1.0),
    min_confidence: float = Query(0.5, ge=0.01, le=1.0),
    db: Session = Depends(get_db)
):
    miner = CouponRuleMiner(db)
    rules = miner.mine_association_rules(transactions, min_support, min_confidence)
    
    return {
        "success": True,
        "data": [
            {
                "pattern": r.pattern,
                "support": r.support,
                "confidence": r.confidence,
                "lift": r.lift,
                "frequency": r.frequency,
                "suggested_discount": r.suggested_discount,
                "suggested_min_amount": r.suggested_min_amount,
            }
            for r in rules
        ],
        "count": len(rules)
    }


@router.get("/mined-rules", summary="获取已挖掘的规则")
async def get_mined_rules(platform: Optional[str] = None, db: Session = Depends(get_db)):
    miner = CouponRuleMiner(db)
    rules = miner.get_active_rules(platform)
    
    return {
        "success": True,
        "data": rules,
        "count": len(rules)
    }


@router.post("/apply-rules", summary="应用规则到商品")
async def apply_mined_rules(request: ApplyRulesRequest, db: Session = Depends(get_db)):
    miner = CouponRuleMiner(db)
    matched = miner.apply_mined_rules(request.text, request.platform, request.price)
    
    best_offer = matched[0] if matched else None
    
    return {
        "success": True,
        "data": {
            "matched_rules": matched,
            "best_offer": best_offer,
            "original_price": request.price,
            "best_final_price": best_offer["final_price"] if best_offer else request.price,
            "max_savings": best_offer["savings_percent"] if best_offer else 0,
        }
    }


@router.post("/mine-from-text", summary="从文本中挖掘优惠券")
async def mine_from_text(
    text: str,
    platform: Optional[str] = None,
    db: Session = Depends(get_db)
):
    miner = CouponRuleMiner(db)
    found = miner.mine_rules_from_text(text, platform)
    
    return {
        "success": True,
        "data": found,
        "count": len(found)
    }


@router.post("/mined-rules/{rule_id}/toggle", summary="切换规则状态")
async def toggle_mined_rule(rule_id: str, db: Session = Depends(get_db)):
    from ..models import CouponMinedRule
    
    rule = db.query(CouponMinedRule).filter(CouponMinedRule.id == rule_id).first()
    
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    
    rule.is_active = not rule.is_active
    db.commit()
    
    return {
        "success": True,
        "data": {
            "id": rule.id,
            "is_active": rule.is_active,
            "message": f"规则已{'启用' if rule.is_active else '禁用'}"
        }
    }


@router.get("/stats", summary="获取优惠券众包统计")
async def get_crowdsource_stats(
    days: int = Query(7, ge=1, le=365),
    db: Session = Depends(get_db)
):
    start_date = datetime.now().date() - __import__('datetime').timedelta(days=days)
    
    total_shares = db.query(CouponShare).count()
    approved_shares = db.query(CouponShare).filter(
        CouponShare.status == CouponShareStatus.APPROVED
    ).count()
    pending_shares = db.query(CouponShare).filter(
        CouponShare.status == CouponShareStatus.PENDING
    ).count()
    
    recent_shares = db.query(CouponShare).filter(
        CouponShare.created_at >= start_date
    ).count()
    
    from ..models import UserReward, CouponUsageLog
    total_rewards = db.query(UserReward).count()
    total_reward_points = db.query(UserReward).all()
    total_points = sum(r.points for r in total_reward_points)
    
    total_usages = db.query(CouponUsageLog).count()
    successful_usages = db.query(CouponUsageLog).filter(
        CouponUsageLog.is_successful == True
    ).count()
    
    from ..models import CouponMinedRule
    total_rules = db.query(CouponMinedRule).count()
    active_rules = db.query(CouponMinedRule).filter(
        CouponMinedRule.is_active == True
    ).count()
    
    platform_stats = db.query(
        CouponShare.platform,
        __import__('sqlalchemy').func.count(CouponShare.id)
    ).group_by(CouponShare.platform).all()
    
    return {
        "success": True,
        "data": {
            "period_days": days,
            "total_shares": total_shares,
            "approved_shares": approved_shares,
            "pending_shares": pending_shares,
            "approval_rate": approved_shares / max(total_shares, 1),
            "recent_shares": recent_shares,
            "total_rewards": total_rewards,
            "total_reward_points": total_points,
            "total_usages": total_usages,
            "successful_usages": successful_usages,
            "usage_success_rate": successful_usages / max(total_usages, 1),
            "total_mined_rules": total_rules,
            "active_mined_rules": active_rules,
            "platform_distribution": [
                {"platform": p, "count": c} for p, c in platform_stats
            ],
        }
    }
