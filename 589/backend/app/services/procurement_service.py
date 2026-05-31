from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import random
import uuid

from ..models.procurement import (
    ProcurementOrder, ProcurementOrderStatus, ProcurementAlternative,
    ProcurementSetting,
)
from ..models import ProductPrice, Product


class ProcurementService:
    def __init__(self, db: Session):
        self.db = db
        self.platforms = ["taobao", "jd", "pdd", "suning"]
        self.default_service_fee_rate = 0.05
        self.max_service_fee_rate = 0.1

    def create_order(self, user_id: str, product_id: str, quantity: int = 1,
                  user_nickname: Optional[str] = None,
                  target_platform: Optional[str] = None,
                  **kwargs) -> ProcurementOrder:
        product = self.db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise ValueError("商品不存在")
        
        alternatives = self.find_best_alternatives(product_id, target_platform)
        if not alternatives:
            raise ValueError("未找到可用购买渠道")
        
        best_alt = self.select_best_alternative(alternatives)
        
        unit_price = best_alt["final_price_with_benefits"]
        total_price = unit_price * quantity
        
        service_fee = self._calculate_service_fee(total_price)
        shipping_fee = best_alt.get("shipping_fee", 0)
        cashback_amount = best_alt.get("cashback", 0) * quantity
        
        final_total = total_price + service_fee + shipping_fee - cashback_amount
        
        order = ProcurementOrder(
            id=str(uuid.uuid4()),
            user_id=user_id,
            user_nickname=user_nickname,
            product_id=product_id,
            product_name=product.name,
            product_image=product.image_url,
            product_url=product.url,
            target_platform=target_platform,
            selected_platform=best_alt["platform"],
            selected_shop=best_alt.get("shop_name"),
            selected_price=best_alt["price"],
            quantity=quantity,
            unit_price=unit_price,
            total_price=total_price,
            service_fee_rate=self.default_service_fee_rate,
            service_fee=service_fee,
            shipping_fee=shipping_fee,
            cashback_amount=cashback_amount,
            final_total=final_total,
            status=ProcurementOrderStatus.PENDING.value,
            status_history=[{
                "status": ProcurementOrderStatus.PENDING.value,
                "timestamp": datetime.utcnow().isoformat(),
                "message": "订单已创建"
            }],
            **{k: v for k, v in kwargs.items() if k in [
                'recipient_name', 'recipient_phone', 'recipient_address',
                'recipient_province', 'recipient_city', 'recipient_district',
                'user_notes', 'auto_order', 'auto_track'
            ]}
        )
        
        self.db.add(order)
        self.db.flush()
        
        for alt in alternatives:
            self._save_alternative(order.id, alt)
        
        self.db.commit()
        self.db.refresh(order)
        
        return order

    def find_best_alternatives(self, product_id: str,
                              target_platform: Optional[str] = None) -> List[Dict[str, Any]]:
        alternatives = []
        
        prices = self.db.query(ProductPrice).filter(
            ProductPrice.product_id == product_id
        ).all()
        
        for price in prices:
            if target_platform and price.platform != target_platform:
                continue
                
            platform_prices = self._get_platform_prices(price.platform, product_id)
            
            for pp in platform_prices:
                cashback_rate = self._estimate_cashback_rate(price.platform, product_id)
                cashback = pp["price"] * cashback_rate
                
                final_price = pp["price"] - cashback
                
                alternatives.append({
                    "platform": price.platform,
                    "shop_name": pp.get("shop_name", f"{price.platform}官方"),
                    "price": pp["price"],
                    "shipping_fee": pp.get("shipping_fee", 0),
                    "cashback_rate": cashback_rate,
                    "cashback": cashback,
                    "final_price_with_benefits": final_price,
                    "savings_percent": (pp["original_price"] - final_price) / pp["original_price"] if pp.get("original_price") else 0,
                    "estimated_delivery_days": random.randint(2, 7),
                    "seller_rating": round(random.uniform(4.0, 5.0),
                    "in_stock": True,
                    "product_url": pp.get("url"),
                    "product_image": pp.get("image_url"),
                    "original_price": pp.get("original_price", pp["price"]),
                })
        
        alternatives.sort(key=lambda x: x["final_price_with_benefits"])
        
        return alternatives

    def _get_platform_prices(self, platform: str, product_id: str) -> List[Dict[str, Any]]:
        prices = []
        
        base_price = random.uniform(50, 5000)
        
        prices.append({
            "price": base_price,
            "original_price": base_price * 1.1,
            "shop_name": f"{platform}官方旗舰店",
            "shipping_fee": 0 if base_price > 99 else random.randint(5, 15),
            "url": f"https://{platform}.com/item/{product_id}",
            "image_url": None
        })
        
        if random.random() > 0.5:
            prices.append({
                "price": base_price * 0.95,
                "original_price": base_price * 1.15,
                "shop_name": f"{platform}专营店",
                "shipping_fee": random.randint(0, 10),
                "url": f"https://{platform}.com/item/{product_id}_2",
                "image_url": None
            })
        
        return prices

    def _estimate_cashback_rate(self, platform: str, product_id: str) -> float:
        rates = {
            "taobao": 0.03,
            "jd": 0.02,
            "pdd": 0.05,
            "suning": 0.015
        }
        return rates.get(platform, 0.02)

    def select_best_alternative(self, alternatives: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not alternatives:
            return None
        
        scored = []
        for alt in alternatives:
            score = 0
            
            price_score = 100 - (alt["final_price_with_benefits"] / max(a["final_price_with_benefits"] for a in alternatives)) * 50
            score += price_score
            
            if alt.get("seller_rating", 0) >= 4.8:
                score += 20
            elif alt.get("seller_rating", 0) >= 4.5:
                score += 10
                
            if alt.get("in_stock"):
                score += 15
                
            if alt.get("estimated_delivery_days", 7) <= 3:
                score += 10
            elif alt.get("estimated_delivery_days", 7) <= 5:
                score += 5
            
            alt["rank_score"] = score
            scored.append(alt)
        
        scored.sort(key=lambda x: -x["rank_score"])
        
        best = scored[0]
        best["is_recommended"] = True
        
        if best["savings_percent"] >= 0.15:
            best["recommendation_reason"] = "价格最优，节省超过15%"
        elif best.get("seller_rating") >= 4.8:
            best["recommendation_reason"] = "高评分商家"
        else:
            best["recommendation_reason"] = "综合最优"
        
        return best

    def _calculate_service_fee(self, total_price: float) -> float:
        return total_price * self.default_service_fee_rate

    def _save_alternative(self, order_id: str, alt: Dict[str, Any]):
        alternative = ProcurementAlternative(
            order_id=order_id,
            platform=alt["platform"],
            shop_name=alt.get("shop_name"),
            price=alt["price"],
            shipping_fee=alt.get("shipping_fee", 0),
            total_price=alt["price"] + alt.get("shipping_fee", 0),
            estimated_delivery_days=alt.get("estimated_delivery_days"),
            seller_rating=alt.get("seller_rating"),
            in_stock=alt.get("in_stock", True),
            product_url=alt.get("product_url"),
            product_image=alt.get("product_image"),
            discount_info=alt.get("discount_info"),
            coupon_info=alt.get("coupon_info"),
            cashback_info={"rate": alt.get("cashback_rate"), "amount": alt.get("cashback")},
            final_price_with_benefits=alt.get("final_price_with_benefits"),
            savings_percent=alt.get("savings_percent"),
            is_recommended=alt.get("is_recommended", False),
            recommendation_reason=alt.get("recommendation_reason"),
            rank_score=alt.get("rank_score", 0)
        )
        self.db.add(alternative)

    def confirm_order(self, order_id: str) -> ProcurementOrder:
        order = self.db.query(ProcurementOrder).filter(
            ProcurementOrder.id == order_id
        ).first()
        
        if not order:
            raise ValueError("订单不存在")
        
        if order.status != ProcurementOrderStatus.PENDING.value:
            raise ValueError("订单状态不允许确认")
        
        order.status = ProcurementOrderStatus.CONFIRMED.value
        order.status_history.append({
            "status": ProcurementOrderStatus.CONFIRMED.value,
            "timestamp": datetime.utcnow().isoformat(),
            "message": "订单已确认"
        })
        order.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(order)
        
        return order

    def process_order(self, order_id: str) -> ProcurementOrder:
        order = self.db.query(ProcurementOrder).filter(
            ProcurementOrder.id == order_id
        ).first()
        
        if not order:
            raise ValueError("订单不存在")
        
        if order.status != ProcurementOrderStatus.CONFIRMED.value:
            raise ValueError("订单状态不允许处理")
        
        order.status = ProcurementOrderStatus.PROCESSING.value
        order.status_history.append({
            "status": ProcurementOrderStatus.PROCESSING.value,
            "timestamp": datetime.utcnow().isoformat(),
            "message": "订单处理中，正在下单"
        })
        order.updated_at = datetime.utcnow()
        
        self.db.commit()
        
        return order

    def simulate_platform_order(self, order_id: str) -> Dict[str, Any]:
        order = self.db.query(ProcurementOrder).filter(
            ProcurementOrder.id == order_id
        ).first()
        
        if not order:
            raise ValueError("订单不存在")
        
        platform_order_id = f"{order.selected_platform}_{int(datetime.utcnow().timestamp())}_{random.randint(1000, 9999)}"
        
        order.platform_order_id = platform_order_id
        order.status = ProcurementOrderStatus.ORDERED.value
        order.ordered_at = datetime.utcnow()
        order.status_history.append({
            "status": ProcurementOrderStatus.ORDERED.value,
            "timestamp": datetime.utcnow().isoformat(),
            "message": f"已在{order.selected_platform}下单，订单号：{platform_order_id}",
            "platform_order_id": platform_order_id
        })
        order.estimated_delivery_date = datetime.utcnow() + timedelta(days=random.randint(3, 7))
        
        self.db.commit()
        
        return {
            "success": True,
            "platform_order_id": platform_order_id,
            "estimated_delivery": order.estimated_delivery_date.isoformat()
        }

    def update_tracking(self, order_id: str, tracking_number: str,
                        tracking_company: str) -> ProcurementOrder:
        order = self.db.query(ProcurementOrder).filter(
            ProcurementOrder.id == order_id
        ).first()
        
        if not order:
            raise ValueError("订单不存在")
        
        order.tracking_number = tracking_number
        order.tracking_company = tracking_company
        order.status = ProcurementOrderStatus.SHIPPED.value
        order.status_history.append({
            "status": ProcurementOrderStatus.SHIPPED.value,
            "timestamp": datetime.utcnow().isoformat(),
            "message": f"商品已发货",
            "tracking_number": tracking_number,
            "tracking_company": tracking_company
        })
        order.updated_at = datetime.utcnow()
        
        self.db.commit()
        
        return order

    def complete_order(self, order_id: str) -> ProcurementOrder:
        order = self.db.query(ProcurementOrder).filter(
            ProcurementOrder.id == order_id
        ).first()
        
        if not order:
            raise ValueError("订单不存在")
        
        order.status = ProcurementOrderStatus.COMPLETED.value
        order.completed_at = datetime.utcnow()
        order.actual_delivery_date = datetime.utcnow()
        order.status_history.append({
            "status": ProcurementOrderStatus.COMPLETED.value,
            "timestamp": datetime.utcnow().isoformat(),
            "message": "订单已完成"
        })
        order.updated_at = datetime.utcnow()
        
        self.db.commit()
        
        return order

    def cancel_order(self, order_id: str, reason: str = "") -> ProcurementOrder:
        order = self.db.query(ProcurementOrder).filter(
            ProcurementOrder.id == order_id
        ).first()
        
        if not order:
            raise ValueError("订单不存在")
        
        if order.status in [ProcurementOrderStatus.ORDERED.value,
                           ProcurementOrderStatus.SHIPPED.value]:
            raise ValueError("订单已发货，无法取消")
        
        order.status = ProcurementOrderStatus.CANCELLED.value
        order.status_history.append({
            "status": ProcurementOrderStatus.CANCELLED.value,
            "timestamp": datetime.utcnow().isoformat(),
            "message": f"订单已取消：{reason}"
        })
        order.updated_at = datetime.utcnow()
        
        self.db.commit()
        
        return order

    def get_user_orders(self, user_id: str, status: Optional[str] = None,
                         limit: int = 20, offset: int = 0) -> List[ProcurementOrder]:
        query = self.db.query(ProcurementOrder).filter(
            ProcurementOrder.user_id == user_id
        )
        
        if status:
            query = query.filter(ProcurementOrder.status == status)
        
        return query.order_by(ProcurementOrder.created_at.desc()).offset(offset).limit(limit).all()

    def get_order_detail(self, order_id: str) -> Optional[ProcurementOrder]:
        return self.db.query(ProcurementOrder).filter(
            ProcurementOrder.id == order_id
        ).first()

    def get_order_alternatives(self, order_id: str) -> List[ProcurementAlternative]:
        return self.db.query(ProcurementAlternative).filter(
            ProcurementAlternative.order_id == order_id
        ).order_by(ProcurementAlternative.rank_score.desc()).all()

    def get_or_create_settings(self, user_id: str) -> ProcurementSetting:
        setting = self.db.query(ProcurementSetting).filter(
            ProcurementSetting.user_id == user_id
        ).first()
        
        if not setting:
            setting = ProcurementSetting(
                user_id=user_id
            )
            self.db.add(setting)
            self.db.commit()
            self.db.refresh(setting)
        
        return setting

    def update_settings(self, user_id: str, **kwargs) -> ProcurementSetting:
        setting = self.get_or_create_settings(user_id)
        
        for key, value in kwargs.items():
            if hasattr(setting, key):
                setattr(setting, key, value)
        
        setting.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(setting)
        
        return setting

    def get_price_protection_claim(self, order_id: str) -> Dict[str, Any]:
        order = self.db.query(ProcurementOrder).filter(
            ProcurementOrder.id == order_id
        ).first()
        
        if not order:
            raise ValueError("订单不存在")
        
        if order.price_protection_claimed:
            return {
                "success": False,
                "message": "已申请过价格保护"
            }
        
        protection_end = order.ordered_at + timedelta(days=order.price_protection_days)
        
        if datetime.utcnow() > protection_end:
            return {
                "success": False,
                "message": "价格保护期已过"
            }
        
        alternatives = self.find_best_alternatives(order.product_id)
        if not alternatives:
            return {
                "success": False,
                "message": "未找到价格信息"
            }
        
        current_lowest = min(a["final_price_with_benefits"] for a in alternatives)
        current_unit_price = order.unit_price
        
        if current_lowest < current_unit_price * 0.95:
            diff = current_unit_price - current_lowest
            refund_amount = diff * order.quantity
            
            order.price_protection_claimed = True
            order.price_protection_amount = refund_amount
            
            self.db.commit()
            
            return {
                "success": True,
                "original_price": current_unit_price,
                "current_price": current_lowest,
                "refund_amount": refund_amount,
                "message": f"价格保护申请成功，可退款 {refund_amount:.2f} 元"
            }
        
        return {
            "success": False,
            "message": "价格未明显下降"
        }
