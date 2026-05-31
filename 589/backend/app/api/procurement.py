from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from datetime import datetime

from ..database import get_db
from ..services.procurement_service import ProcurementService
from ..services.groupbuy_service import GroupBuyService
from ..services.cashback_service import CashbackService

router = APIRouter(prefix="/procurement", tags=["代购/团购/返利"])


class CreateProcurementOrderRequest(BaseModel):
    product_id: str
    quantity: int = 1
    user_nickname: Optional[str] = None
    target_platform: Optional[str] = None
    recipient_name: Optional[str] = None
    recipient_phone: Optional[str] = None
    recipient_address: Optional[str] = None
    recipient_province: Optional[str] = None
    recipient_city: Optional[str] = None
    recipient_district: Optional[str] = None
    user_notes: Optional[str] = None
    auto_order: bool = True


class UpdateProcurementSettingsRequest(BaseModel):
    enabled: Optional[bool] = None
    auto_select_best: Optional[bool] = None
    auto_order: Optional[bool] = None
    preferred_platforms: Optional[List[str]] = None
    excluded_platforms: Optional[List[str]] = None
    max_service_fee_rate: Optional[float] = None
    min_seller_rating: Optional[float] = None
    price_difference_threshold: Optional[float] = None
    allow_cross_region: Optional[bool] = None
    notify_on_price_drop: Optional[bool] = None
    notify_on_order_status: Optional[bool] = None
    notify_on_delivery: Optional[bool] = None


class JoinGroupbuyRequest(BaseModel):
    user_id: str
    quantity: int = 1
    user_nickname: Optional[str] = None


class CreateCustomGroupbuyRequest(BaseModel):
    user_id: str
    product_id: str
    target_price: float
    min_participants: int = 5
    duration_hours: int = 48


class CreateCashbackTransactionRequest(BaseModel):
    user_id: str
    platform: str
    product_id: str
    product_name: str
    original_price: float
    final_price: float
    cashback_rate: float
    cashback_amount: float
    coupon_amount: float = 0
    discount_amount: float = 0
    platform_transaction_id: Optional[str] = None
    affiliate_id: Optional[str] = None
    click_id: Optional[str] = None
    source_type: str = "direct"


class WithdrawRequest(BaseModel):
    user_id: str
    amount: float


class UpdateCashbackAccountRequest(BaseModel):
    minimum_payout: Optional[float] = None
    payout_method: Optional[str] = None
    payout_account: Optional[str] = None


@router.post("/orders", summary="创建代购订单")
async def create_procurement_order(request: CreateProcurementOrderRequest,
                                    user_id: str,
                                    db: Session = Depends(get_db)):
    service = ProcurementService(db)
    try:
        order = service.create_order(
            user_id=user_id,
            product_id=request.product_id,
            quantity=request.quantity,
            user_nickname=request.user_nickname,
            target_platform=request.target_platform,
            recipient_name=request.recipient_name,
            recipient_phone=request.recipient_phone,
            recipient_address=request.recipient_address,
            recipient_province=request.recipient_province,
            recipient_city=request.recipient_city,
            recipient_district=request.recipient_district,
            user_notes=request.user_notes,
            auto_order=request.auto_order
        )
        
        return {
            "success": True,
            "data": {
                "order_id": order.id,
                "product_name": order.product_name,
                "selected_platform": order.selected_platform,
                "selected_shop": order.selected_shop,
                "unit_price": float(order.unit_price),
                "quantity": order.quantity,
                "total_price": float(order.total_price),
                "service_fee": float(order.service_fee),
                "shipping_fee": float(order.shipping_fee),
                "cashback_amount": float(order.cashback_amount),
                "final_total": float(order.final_total),
                "status": order.status,
                "created_at": order.created_at.isoformat()
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/orders/{order_id}", summary="获取代购订单详情")
async def get_procurement_order(order_id: str, db: Session = Depends(get_db)):
    service = ProcurementService(db)
    order = service.get_order_detail(order_id)
    
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    
    alternatives = service.get_order_alternatives(order_id)
    
    return {
        "success": True,
        "data": {
            "id": order.id,
            "product_id": order.product_id,
            "product_name": order.product_name,
            "product_image": order.product_image,
            "selected_platform": order.selected_platform,
            "selected_shop": order.selected_shop,
            "unit_price": float(order.unit_price),
            "quantity": order.quantity,
            "total_price": float(order.total_price),
            "service_fee_rate": float(order.service_fee_rate),
            "service_fee": float(order.service_fee),
            "shipping_fee": float(order.shipping_fee),
            "discount_amount": float(order.discount_amount),
            "cashback_amount": float(order.cashback_amount),
            "final_total": float(order.final_total),
            "amount_paid": float(order.amount_paid),
            "status": order.status,
            "status_history": order.status_history,
            "platform_order_id": order.platform_order_id,
            "tracking_number": order.tracking_number,
            "tracking_company": order.tracking_company,
            "recipient_name": order.recipient_name,
            "recipient_phone": order.recipient_phone,
            "recipient_address": order.recipient_address,
            "auto_order": order.auto_order,
            "price_protection_days": order.price_protection_days,
            "price_protection_claimed": order.price_protection_claimed,
            "price_protection_amount": float(order.price_protection_amount),
            "estimated_delivery_date": order.estimated_delivery_date.isoformat() if order.estimated_delivery_date else None,
            "actual_delivery_date": order.actual_delivery_date.isoformat() if order.actual_delivery_date else None,
            "user_notes": order.user_notes,
            "created_at": order.created_at.isoformat(),
            "updated_at": order.updated_at.isoformat(),
            "ordered_at": order.ordered_at.isoformat() if order.ordered_at else None,
            "completed_at": order.completed_at.isoformat() if order.completed_at else None,
            "alternatives": [
                {
                    "id": alt.id,
                    "platform": alt.platform,
                    "shop_name": alt.shop_name,
                    "price": float(alt.price),
                    "shipping_fee": float(alt.shipping_fee),
                    "total_price": float(alt.total_price),
                    "final_price_with_benefits": float(alt.final_price_with_benefits),
                    "savings_percent": float(alt.savings_percent),
                    "estimated_delivery_days": alt.estimated_delivery_days,
                    "seller_rating": float(alt.seller_rating) if alt.seller_rating else None,
                    "in_stock": alt.in_stock,
                    "is_recommended": alt.is_recommended,
                    "recommendation_reason": alt.recommendation_reason,
                    "rank_score": float(alt.rank_score),
                    "cashback_info": alt.cashback_info
                }
                for alt in alternatives
            ]
        }
    }


@router.get("/orders", summary="获取用户代购订单列表")
async def get_user_procurement_orders(user_id: str,
                                       status: Optional[str] = None,
                                       limit: int = Query(20, ge=1, le=100),
                                       offset: int = Query(0, ge=0),
                                       db: Session = Depends(get_db)):
    service = ProcurementService(db)
    orders = service.get_user_orders(user_id, status, limit, offset)
    
    return {
        "success": True,
        "data": [
            {
                "id": order.id,
                "product_id": order.product_id,
                "product_name": order.product_name,
                "product_image": order.product_image,
                "selected_platform": order.selected_platform,
                "final_total": float(order.final_total),
                "status": order.status,
                "tracking_number": order.tracking_number,
                "created_at": order.created_at.isoformat()
            }
            for order in orders
        ]
    }


@router.post("/orders/{order_id}/confirm", summary="确认代购订单")
async def confirm_procurement_order(order_id: str, db: Session = Depends(get_db)):
    service = ProcurementService(db)
    try:
        order = service.confirm_order(order_id)
        return {
            "success": True,
            "message": "订单已确认",
            "data": {
                "order_id": order.id,
                "status": order.status
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/orders/{order_id}/process", summary="处理代购订单（开始下单）")
async def process_procurement_order(order_id: str, db: Session = Depends(get_db)):
    service = ProcurementService(db)
    try:
        order = service.process_order(order_id)
        result = service.simulate_platform_order(order_id)
        
        return {
            "success": True,
            "message": "订单处理完成，已在平台下单",
            "data": {
                "order_id": order.id,
                "status": order.status,
                "platform_order_id": result.get("platform_order_id"),
                "estimated_delivery": result.get("estimated_delivery")
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/orders/{order_id}/complete", summary="完成代购订单")
async def complete_procurement_order(order_id: str, db: Session = Depends(get_db)):
    service = ProcurementService(db)
    try:
        order = service.complete_order(order_id)
        return {
            "success": True,
            "message": "订单已完成",
            "data": {
                "order_id": order.id,
                "status": order.status
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/orders/{order_id}/cancel", summary="取消代购订单")
async def cancel_procurement_order(order_id: str, reason: str = "", db: Session = Depends(get_db)):
    service = ProcurementService(db)
    try:
        order = service.cancel_order(order_id, reason)
        return {
            "success": True,
            "message": "订单已取消",
            "data": {
                "order_id": order.id,
                "status": order.status
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/orders/{order_id}/tracking", summary="更新物流信息")
async def update_tracking(order_id: str, tracking_number: str,
                           tracking_company: str, db: Session = Depends(get_db)):
    service = ProcurementService(db)
    try:
        order = service.update_tracking(order_id, tracking_number, tracking_company)
        return {
            "success": True,
            "message": "物流信息已更新",
            "data": {
                "order_id": order.id,
                "tracking_number": order.tracking_number,
                "tracking_company": order.tracking_company,
                "status": order.status
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/orders/{order_id}/price-protection", summary="申请价格保护")
async def claim_price_protection(order_id: str, db: Session = Depends(get_db)):
    service = ProcurementService(db)
    result = service.get_price_protection_claim(order_id)
    
    return {
        "success": result["success"],
        "message": result["message"],
        "data": result
    }


@router.get("/settings/{user_id}", summary="获取代购设置")
async def get_procurement_settings(user_id: str, db: Session = Depends(get_db)):
    service = ProcurementService(db)
    settings = service.get_or_create_settings(user_id)
    
    return {
        "success": True,
        "data": {
            "enabled": settings.enabled,
            "auto_select_best": settings.auto_select_best,
            "auto_order": settings.auto_order,
            "preferred_platforms": settings.preferred_platforms,
            "excluded_platforms": settings.excluded_platforms,
            "max_service_fee_rate": float(settings.max_service_fee_rate),
            "min_seller_rating": float(settings.min_seller_rating),
            "price_difference_threshold": float(settings.price_difference_threshold),
            "allow_cross_region": settings.allow_cross_region,
            "notify_on_price_drop": settings.notify_on_price_drop,
            "notify_on_order_status": settings.notify_on_order_status,
            "notify_on_delivery": settings.notify_on_delivery,
            "default_shipping_address": settings.default_shipping_address
        }
    }


@router.put("/settings/{user_id}", summary="更新代购设置")
async def update_procurement_settings(user_id: str,
                                       request: UpdateProcurementSettingsRequest,
                                       db: Session = Depends(get_db)):
    service = ProcurementService(db)
    settings = service.update_settings(user_id, **request.dict(exclude_unset=True))
    
    return {
        "success": True,
        "message": "设置已更新",
        "data": {
            "enabled": settings.enabled,
            "auto_select_best": settings.auto_select_best,
            "auto_order": settings.auto_order
        }
    }


@router.get("/alternatives/{product_id}", summary="获取商品的最优购买渠道")
async def get_best_alternatives(product_id: str,
                                  target_platform: Optional[str] = None,
                                  db: Session = Depends(get_db)):
    service = ProcurementService(db)
    try:
        alternatives = service.find_best_alternatives(product_id, target_platform)
        
        if not alternatives:
            return {
                "success": True,
                "data": [],
                "best": None
            }
        
        best = service.select_best_alternative(alternatives)
        
        return {
            "success": True,
            "data": alternatives,
            "best": best
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/groupbuy/discover", summary="发现团购活动")
async def discover_groupbuys(category: Optional[str] = None,
                              platform: Optional[str] = None,
                              min_discount: float = Query(0.1, ge=0, le=1),
                              limit: int = Query(50, ge=1, le=200),
                              db: Session = Depends(get_db)):
    service = GroupBuyService(db)
    deals = service.discover_groupbuys(category, platform, min_discount, limit)
    
    return {
        "success": True,
        "data": [
            {
                "id": deal.id,
                "title": deal.title,
                "description": deal.description,
                "platform": deal.platform,
                "product_id": deal.product_id,
                "product_name": deal.product_name,
                "product_image": deal.product_image,
                "category": deal.category,
                "brand": deal.brand,
                "original_price": float(deal.original_price),
                "group_price": float(deal.group_price),
                "unit_price": float(deal.unit_price),
                "discount_percent": float(deal.discount_percent),
                "savings_amount": float(deal.savings_amount),
                "deal_type": deal.deal_type,
                "min_quantity": deal.min_quantity,
                "current_participants": deal.current_participants,
                "target_participants": deal.target_participants,
                "total_quantity_available": deal.total_quantity_available,
                "total_quantity_sold": deal.total_quantity_sold,
                "start_time": deal.start_time.isoformat(),
                "end_time": deal.end_time.isoformat(),
                "is_limited": deal.is_limited,
                "is_flash_sale": deal.is_flash_sale,
                "is_top_deal": deal.is_top_deal,
                "status": deal.status,
                "seller_name": deal.seller_name,
                "seller_rating": float(deal.seller_rating) if deal.seller_rating else None,
                "volume_price_tiers": deal.volume_price_tiers,
                "overall_score": float(deal.overall_score),
                "view_count": deal.view_count,
                "join_count": deal.join_count
            }
            for deal in deals
        ],
        "count": len(deals)
    }


@router.get("/groupbuy/hot", summary="获取热门团购")
async def get_hot_groupbuys(platform: Optional[str] = None,
                             limit: int = Query(10, ge=1, le=50),
                             db: Session = Depends(get_db)):
    service = GroupBuyService(db)
    deals = service.get_hot_deals(platform, limit)
    
    return {
        "success": True,
        "data": deals,
        "count": len(deals)
    }


@router.get("/groupbuy/flash", summary="获取限时秒杀")
async def get_flash_sales(platform: Optional[str] = None,
                           limit: int = Query(20, ge=1, le=100),
                           db: Session = Depends(get_db)):
    service = GroupBuyService(db)
    deals = service.get_flash_sales(platform, limit)
    
    return {
        "success": True,
        "data": deals,
        "count": len(deals)
    }


@router.get("/groupbuy/{deal_id}", summary="获取团购详情")
async def get_groupbuy_detail(deal_id: str, db: Session = Depends(get_db)):
    service = GroupBuyService(db)
    deal = service.get_deal_detail(deal_id)
    
    if not deal:
        raise HTTPException(status_code=404, detail="团购活动不存在")
    
    return {
        "success": True,
        "data": {
            "id": deal.id,
            "title": deal.title,
            "description": deal.description,
            "platform": deal.platform,
            "product_id": deal.product_id,
            "product_name": deal.product_name,
            "product_image": deal.product_image,
            "product_url": deal.product_url,
            "category": deal.category,
            "brand": deal.brand,
            "original_price": float(deal.original_price),
            "group_price": float(deal.group_price),
            "unit_price": float(deal.unit_price),
            "discount_percent": float(deal.discount_percent),
            "savings_amount": float(deal.savings_amount),
            "deal_type": deal.deal_type,
            "min_quantity": deal.min_quantity,
            "max_quantity_per_person": deal.max_quantity_per_person,
            "current_participants": deal.current_participants,
            "target_participants": deal.target_participants,
            "progress_percent": round(deal.current_participants / deal.target_participants * 100, 1),
            "total_quantity_available": deal.total_quantity_available,
            "total_quantity_sold": deal.total_quantity_sold,
            "start_time": deal.start_time.isoformat(),
            "end_time": deal.end_time.isoformat(),
            "remaining_hours": max(0, (deal.end_time - datetime.utcnow()).total_seconds() / 3600),
            "is_limited": deal.is_limited,
            "is_flash_sale": deal.is_flash_sale,
            "is_top_deal": deal.is_top_deal,
            "status": deal.status,
            "seller_name": deal.seller_name,
            "seller_rating": float(deal.seller_rating) if deal.seller_rating else None,
            "shipping_info": deal.shipping_info,
            "payment_methods": deal.payment_methods,
            "volume_price_tiers": deal.volume_price_tiers,
            "popularity_score": float(deal.popularity_score),
            "value_score": float(deal.value_score),
            "overall_score": float(deal.overall_score),
            "view_count": deal.view_count,
            "join_count": deal.join_count,
            "share_count": deal.share_count
        }
    }


@router.post("/groupbuy/{deal_id}/join", summary="参与团购")
async def join_groupbuy(deal_id: str, request: JoinGroupbuyRequest,
                         db: Session = Depends(get_db)):
    service = GroupBuyService(db)
    try:
        participation = service.join_groupbuy(
            deal_id, request.user_id, request.quantity, request.user_nickname
        )
        
        return {
            "success": True,
            "message": "成功参与团购",
            "data": {
                "participation_id": participation.id,
                "deal_id": participation.deal_id,
                "quantity": participation.quantity,
                "unit_price": float(participation.unit_price_at_join),
                "total_amount": float(participation.total_amount),
                "is_organizer": participation.is_organizer,
                "joined_at": participation.joined_at.isoformat()
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/groupbuy/custom", summary="发起自定义团购")
async def create_custom_groupbuy(request: CreateCustomGroupbuyRequest,
                                   db: Session = Depends(get_db)):
    service = GroupBuyService(db)
    try:
        deal = service.create_custom_groupbuy(
            request.user_id, request.product_id,
            request.target_price, request.min_participants,
            request.duration_hours
        )
        
        return {
            "success": True,
            "message": "团购已发起",
            "data": {
                "deal_id": deal.id,
                "title": deal.title,
                "target_price": float(deal.group_price),
                "min_participants": deal.target_participants,
                "end_time": deal.end_time.isoformat()
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/groupbuy/user/{user_id}", summary="获取用户参与的团购")
async def get_user_groupbuys(user_id: str,
                              status: Optional[str] = None,
                              limit: int = Query(20, ge=1, le=100),
                              offset: int = Query(0, ge=0),
                              db: Session = Depends(get_db)):
    service = GroupBuyService(db)
    participations = service.get_user_participations(user_id, status, limit, offset)
    
    return {
        "success": True,
        "data": [
            {
                "id": p.id,
                "deal_id": p.deal_id,
                "quantity": p.quantity,
                "unit_price": float(p.unit_price_at_join),
                "total_amount": float(p.total_amount),
                "status": p.status,
                "is_organizer": p.is_organizer,
                "joined_at": p.joined_at.isoformat()
            }
            for p in participations
        ]
    }


@router.get("/groupbuy/analyze/{product_id}", summary="分析商品的批量折扣")
async def analyze_quantity_discount(product_id: str,
                                     max_quantity: int = Query(50, ge=1, le=100),
                                     db: Session = Depends(get_db)):
    service = GroupBuyService(db)
    analysis = service.analyze_quantity_discount(product_id, max_quantity)
    
    return {
        "success": True,
        "data": analysis
    }


@router.get("/cashback/compare/{product_id}", summary="对比多平台返利后价格")
async def compare_prices_with_cashback(product_id: str, db: Session = Depends(get_db)):
    service = CashbackService(db)
    try:
        comparison = service.compare_prices_with_cashback(product_id)
        return {
            "success": True,
            "data": comparison
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/cashback/calculate", summary="计算商品返利")
async def calculate_cashback(product_id: str, price: float, platform: str,
                               category: Optional[str] = None,
                               brand: Optional[str] = None,
                               db: Session = Depends(get_db)):
    service = CashbackService(db)
    result = service.calculate_cashback(product_id, price, platform, category, brand)
    
    return {
        "success": True,
        "data": result
    }


@router.get("/cashback/best-deals", summary="获取返利最优商品")
async def get_best_cashback_deals(category: Optional[str] = None,
                                    limit: int = Query(20, ge=1, le=100),
                                    db: Session = Depends(get_db)):
    service = CashbackService(db)
    deals = service.get_best_cashback_deals(category, limit)
    
    return {
        "success": True,
        "data": deals,
        "count": len(deals)
    }


@router.post("/cashback/transactions", summary="创建返利交易")
async def create_cashback_transaction(request: CreateCashbackTransactionRequest,
                                        db: Session = Depends(get_db)):
    service = CashbackService(db)
    transaction = service.create_transaction(**request.dict())
    
    return {
        "success": True,
        "data": {
            "transaction_id": transaction.id,
            "user_id": transaction.user_id,
            "cashback_amount": float(transaction.cashback_amount),
            "status": transaction.status,
            "expected_payout_date": transaction.expected_payout_date.isoformat()
        }
    }


@router.post("/cashback/transactions/{transaction_id}/confirm", summary="确认返利交易")
async def confirm_cashback_transaction(transaction_id: str, db: Session = Depends(get_db)):
    service = CashbackService(db)
    try:
        transaction = service.confirm_transaction(transaction_id)
        return {
            "success": True,
            "message": "交易已确认",
            "data": {
                "transaction_id": transaction.id,
                "status": transaction.status,
                "cashback_amount": float(transaction.cashback_amount)
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/cashback/transactions", summary="获取用户返利交易记录")
async def get_user_cashback_transactions(user_id: str,
                                           status: Optional[str] = None,
                                           limit: int = Query(50, ge=1, le=200),
                                           offset: int = Query(0, ge=0),
                                           db: Session = Depends(get_db)):
    service = CashbackService(db)
    transactions = service.get_user_transactions(user_id, status, limit, offset)
    
    return {
        "success": True,
        "data": [
            {
                "id": t.id,
                "platform": t.platform,
                "product_id": t.product_id,
                "product_name": t.product_name,
                "original_price": float(t.original_price),
                "final_price": float(t.final_price),
                "cashback_rate": float(t.cashback_rate),
                "cashback_amount": float(t.cashback_amount),
                "effective_price": float(t.effective_price),
                "status": t.status,
                "purchase_date": t.purchase_date.isoformat() if t.purchase_date else None,
                "expected_payout_date": t.expected_payout_date.isoformat() if t.expected_payout_date else None,
                "actual_payout_date": t.actual_payout_date.isoformat() if t.actual_payout_date else None
            }
            for t in transactions
        ]
    }


@router.get("/cashback/account/{user_id}", summary="获取用户返利账户")
async def get_cashback_account(user_id: str, db: Session = Depends(get_db)):
    service = CashbackService(db)
    summary = service.get_account_summary(user_id)
    
    return {
        "success": True,
        "data": summary
    }


@router.put("/cashback/account/{user_id}", summary="更新返利账户设置")
async def update_cashback_account(user_id: str,
                                   request: UpdateCashbackAccountRequest,
                                   db: Session = Depends(get_db)):
    service = CashbackService(db)
    account = service.update_account(user_id, **request.dict(exclude_unset=True))
    
    return {
        "success": True,
        "message": "账户设置已更新",
        "data": {
            "minimum_payout": float(account.minimum_payout),
            "payout_method": account.payout_method
        }
    }


@router.post("/cashback/withdraw", summary="申请返利提现")
async def request_cashback_withdraw(request: WithdrawRequest,
                                     db: Session = Depends(get_db)):
    service = CashbackService(db)
    result = service.request_withdrawal(request.user_id, request.amount)
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    
    return {
        "success": True,
        "data": result
    }


@router.get("/cashback/rules", summary="获取返利规则")
async def get_cashback_rules(platform: Optional[str] = None,
                              category: Optional[str] = None,
                              db: Session = Depends(get_db)):
    service = CashbackService(db)
    rules = service.get_active_rules(platform, category)
    
    return {
        "success": True,
        "data": [
            {
                "id": rule.id,
                "platform": rule.platform,
                "category": rule.category,
                "brand": rule.brand,
                "product_id": rule.product_id,
                "rule_type": rule.rule_type,
                "cashback_rate": float(rule.cashback_rate),
                "fixed_amount": float(rule.fixed_amount),
                "min_order_amount": float(rule.min_order_amount),
                "max_cashback_amount": float(rule.max_cashback_amount) if rule.max_cashback_amount else None,
                "valid_from": rule.valid_from.isoformat() if rule.valid_from else None,
                "valid_to": rule.valid_to.isoformat() if rule.valid_to else None,
                "is_promo": rule.is_promo,
                "priority": rule.priority
            }
            for rule in rules
        ]
    }


@router.get("/cashback/affiliate-link", summary="生成推广返利链接")
async def generate_affiliate_link(product_id: str, platform: str, user_id: str,
                                   db: Session = Depends(get_db)):
    service = CashbackService(db)
    link_info = service.generate_affiliate_link(product_id, platform, user_id)
    
    return {
        "success": True,
        "data": link_info
    }
