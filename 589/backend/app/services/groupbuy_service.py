from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import random
import uuid

from ..models.procurement import (
    GroupBuyDeal, GroupBuyStatus, GroupBuyType,
    GroupBuyParticipation
)
from ..models import Product, ProductPrice


class GroupBuyService:
    def __init__(self, db: Session):
        self.db = db
        self.platforms = ["taobao", "jd", "pdd", "suning"]

    def discover_groupbuys(self, category: Optional[str] = None,
                           platform: Optional[str] = None,
                           min_discount: float = 0.1,
                           limit: int = 50) -> List[GroupBuyDeal]:
        existing_deals = self._get_active_deals(category, platform, limit)
        
        new_deals = self._discover_new_deals(category, platform, min_discount)
        for deal in new_deals:
            self.db.add(deal)
        
        self.db.commit()
        
        all_deals = self._get_active_deals(category, platform, limit)
        return sorted(all_deals, key=lambda x: -x.overall_score)

    def _get_active_deals(self, category: Optional[str],
                          platform: Optional[str],
                          limit: int) -> List[GroupBuyDeal]:
        query = self.db.query(GroupBuyDeal).filter(
            GroupBuyDeal.status == GroupBuyStatus.ACTIVE.value,
            GroupBuyDeal.end_time > datetime.utcnow()
        )
        
        if category:
            query = query.filter(GroupBuyDeal.category == category)
        if platform:
            query = query.filter(GroupBuyDeal.platform == platform)
        
        return query.order_by(GroupBuyDeal.overall_score.desc()).limit(limit).all()

    def _discover_new_deals(self, category: Optional[str],
                            platform: Optional[str],
                            min_discount: float) -> List[GroupBuyDeal]:
        deals = []
        
        products = self._get_products_for_discovery(category, limit=20)
        
        for product in products:
            platform_deals = self._analyze_product_for_groupbuy(
                product, platform, min_discount
            )
            deals.extend(platform_deals)
        
        return deals

    def _get_products_for_discovery(self, category: Optional[str],
                                    limit: int = 20) -> List[Product]:
        query = self.db.query(Product)
        if category:
            query = query.filter(Product.category == category)
        return query.limit(limit).all()

    def _analyze_product_for_groupbuy(self, product: Product,
                                       target_platform: Optional[str],
                                       min_discount: float) -> List[GroupBuyDeal]:
        deals = []
        prices = self.db.query(ProductPrice).filter(
            ProductPrice.product_id == product.id
        ).all()
        
        for price in prices:
            if target_platform and price.platform != target_platform:
                continue
            
            base_price = price.price if price and price.price else random.uniform(50, 5000)
            
            groupbuy_scenarios = self._generate_groupbuy_scenarios(
                product, price.platform, base_price, min_discount
            )
            
            for scenario in groupbuy_scenarios:
                if scenario["discount_percent"] >= min_discount:
                    deal = self._create_groupbuy_deal(product, scenario)
                    deals.append(deal)
        
        return deals

    def _generate_groupbuy_scenarios(self, product: Product, platform: str,
                                      base_price: float,
                                      min_discount: float) -> List[Dict[str, Any]]:
        scenarios = []
        
        quantity_tiers = [
            {"min_quantity": 2, "discount": 0.05, "type": GroupBuyType.QUANTITY_DISCOUNT.value},
            {"min_quantity": 5, "discount": 0.10, "type": GroupBuyType.QUANTITY_DISCOUNT.value},
            {"min_quantity": 10, "discount": 0.15, "type": GroupBuyType.QUANTITY_DISCOUNT.value},
            {"min_quantity": 20, "discount": 0.20, "type": GroupBuyType.QUANTITY_DISCOUNT.value},
        ]
        
        for tier in quantity_tiers:
            if tier["discount"] < min_discount:
                continue
                
            group_price = base_price * (1 - tier["discount"])
            scenarios.append({
                "platform": platform,
                "deal_type": tier["type"],
                "min_quantity": tier["min_quantity"],
                "original_price": base_price,
                "group_price": group_price,
                "unit_price": group_price,
                "discount_percent": tier["discount"],
                "savings_amount": base_price - group_price,
                "target_participants": tier["min_quantity"] * 2,
                "duration_hours": 48,
                "is_flash_sale": False,
                "is_limited": tier["min_quantity"] >= 10,
                "title": f"{tier['min_quantity']}人团 - {product.name}",
                "description": f"购买{tier['min_quantity']}件即可享受{tier['discount']*100:.0f}%折扣"
            })
        
        if random.random() > 0.7:
            flash_discount = random.uniform(0.15, 0.40)
            flash_price = base_price * (1 - flash_discount)
            scenarios.append({
                "platform": platform,
                "deal_type": GroupBuyType.FLASH_SALE.value,
                "min_quantity": 1,
                "original_price": base_price,
                "group_price": flash_price,
                "unit_price": flash_price,
                "discount_percent": flash_discount,
                "savings_amount": base_price - flash_price,
                "target_participants": 50,
                "duration_hours": 2,
                "is_flash_sale": True,
                "is_limited": True,
                "title": f"限时秒杀 - {product.name}",
                "description": f"限时{flash_discount*100:.0f}%折扣，数量有限"
            })
        
        if random.random() > 0.8:
            promo_discount = random.uniform(0.10, 0.30)
            promo_price = base_price * (1 - promo_discount)
            scenarios.append({
                "platform": platform,
                "deal_type": GroupBuyType.PLATFORM_PROMO.value,
                "min_quantity": 1,
                "original_price": base_price,
                "group_price": promo_price,
                "unit_price": promo_price,
                "discount_percent": promo_discount,
                "savings_amount": base_price - promo_price,
                "target_participants": 100,
                "duration_hours": 72,
                "is_flash_sale": False,
                "is_limited": False,
                "title": f"平台促销 - {product.name}",
                "description": f"平台大促，限时{promo_discount*100:.0f}%优惠"
            })
        
        return scenarios

    def _create_groupbuy_deal(self, product: Product,
                               scenario: Dict[str, Any]) -> GroupBuyDeal:
        now = datetime.utcnow()
        end_time = now + timedelta(hours=scenario["duration_hours"])
        
        value_score = scenario["discount_percent"] * 100
        popularity_score = random.uniform(50, 100)
        overall_score = value_score * 0.6 + popularity_score * 0.4
        
        volume_tiers = self._generate_volume_tiers(scenario["original_price"])
        
        return GroupBuyDeal(
            id=str(uuid.uuid4()),
            title=scenario["title"],
            description=scenario["description"],
            platform=scenario["platform"],
            product_id=product.id,
            product_name=product.name,
            product_image=product.image_url,
            product_url=product.url,
            category=product.category,
            brand=product.brand,
            original_price=scenario["original_price"],
            group_price=scenario["group_price"],
            unit_price=scenario["unit_price"],
            discount_percent=scenario["discount_percent"],
            savings_amount=scenario["savings_amount"],
            deal_type=scenario["deal_type"],
            min_quantity=scenario["min_quantity"],
            max_quantity_per_person=scenario["min_quantity"] * 5,
            target_participants=scenario["target_participants"],
            total_quantity_available=scenario["target_participants"] * 3 if scenario["is_limited"] else None,
            start_time=now,
            end_time=end_time,
            duration_hours=scenario["duration_hours"],
            is_limited=scenario["is_limited"],
            is_flash_sale=scenario["is_flash_sale"],
            is_top_deal=scenario["discount_percent"] >= 0.25,
            status=GroupBuyStatus.ACTIVE.value,
            seller_name=f"{scenario['platform']}官方",
            seller_rating=round(random.uniform(4.5, 5.0), 1),
            volume_price_tiers=volume_tiers,
            source_type="auto_discovered",
            popularity_score=popularity_score,
            value_score=value_score,
            overall_score=overall_score,
            current_participants=random.randint(0, scenario["target_participants"] // 2),
            total_quantity_sold=random.randint(0, scenario["target_participants"]),
        )

    def _generate_volume_tiers(self, base_price: float) -> List[Dict[str, Any]]:
        tiers = []
        for qty, discount in [(2, 0.05), (5, 0.10), (10, 0.15), (20, 0.20)]:
            tiers.append({
                "quantity": qty,
                "discount_percent": discount,
                "unit_price": round(base_price * (1 - discount), 2),
                "total_price": round(base_price * (1 - discount) * qty, 2)
            })
        return tiers

    def get_deal_detail(self, deal_id: str) -> Optional[GroupBuyDeal]:
        deal = self.db.query(GroupBuyDeal).filter(
            GroupBuyDeal.id == deal_id
        ).first()
        
        if deal:
            deal.view_count += 1
            self.db.commit()
        
        return deal

    def join_groupbuy(self, deal_id: str, user_id: str,
                      quantity: int = 1,
                      user_nickname: Optional[str] = None) -> GroupBuyParticipation:
        deal = self.db.query(GroupBuyDeal).filter(
            GroupBuyDeal.id == deal_id
        ).first()
        
        if not deal:
            raise ValueError("团购活动不存在")
        
        if deal.status != GroupBuyStatus.ACTIVE.value:
            raise ValueError("团购活动已结束")
        
        if deal.end_time < datetime.utcnow():
            deal.status = GroupBuyStatus.EXPIRED.value
            self.db.commit()
            raise ValueError("团购活动已过期")
        
        if deal.is_limited and deal.total_quantity_sold + quantity > deal.total_quantity_available:
            raise ValueError("库存不足")
        
        existing = self.db.query(GroupBuyParticipation).filter(
            GroupBuyParticipation.deal_id == deal_id,
            GroupBuyParticipation.user_id == user_id,
            GroupBuyParticipation.status == "joined"
        ).first()
        
        if existing:
            raise ValueError("已参与此团购")
        
        participation = GroupBuyParticipation(
            id=str(uuid.uuid4()),
            deal_id=deal_id,
            user_id=user_id,
            user_nickname=user_nickname,
            quantity=quantity,
            unit_price_at_join=deal.unit_price,
            total_amount=deal.unit_price * quantity,
            status="joined",
            is_organizer=deal.current_participants == 0
        )
        
        self.db.add(participation)
        
        deal.current_participants += 1
        deal.join_count += 1
        deal.total_quantity_sold += quantity
        deal.popularity_score = min(100, deal.popularity_score + 1)
        
        if deal.current_participants >= deal.target_participants:
            deal.status = GroupBuyStatus.SUCCESS.value
        
        self.db.commit()
        self.db.refresh(participation)
        
        return participation

    def get_user_participations(self, user_id: str,
                                 status: Optional[str] = None,
                                 limit: int = 20,
                                 offset: int = 0) -> List[GroupBuyParticipation]:
        query = self.db.query(GroupBuyParticipation).filter(
            GroupBuyParticipation.user_id == user_id
        )
        
        if status:
            query = query.filter(GroupBuyParticipation.status == status)
        
        return query.order_by(GroupBuyParticipation.joined_at.desc()).offset(offset).limit(limit).all()

    def get_deal_participations(self, deal_id: str,
                                 limit: int = 50,
                                 offset: int = 0) -> List[GroupBuyParticipation]:
        return self.db.query(GroupBuyParticipation).filter(
            GroupBuyParticipation.deal_id == deal_id
        ).order_by(GroupBuyParticipation.joined_at.desc()).offset(offset).limit(limit).all()

    def recommend_groupbuys(self, user_id: Optional[str] = None,
                             category: Optional[str] = None,
                             limit: int = 20) -> List[GroupBuyDeal]:
        query = self.db.query(GroupBuyDeal).filter(
            GroupBuyDeal.status == GroupBuyStatus.ACTIVE.value,
            GroupBuyDeal.end_time > datetime.utcnow()
        )
        
        if category:
            query = query.filter(GroupBuyDeal.category == category)
        
        query = query.order_by(GroupBuyDeal.overall_score.desc())
        
        return query.limit(limit).all()

    def get_hot_deals(self, platform: Optional[str] = None,
                       limit: int = 10) -> List[GroupBuyDeal]:
        query = self.db.query(GroupBuyDeal).filter(
            GroupBuyDeal.status == GroupBuyStatus.ACTIVE.value,
            GroupBuyDeal.end_time > datetime.utcnow(),
            GroupBuyDeal.is_top_deal == True
        )
        
        if platform:
            query = query.filter(GroupBuyDeal.platform == platform)
        
        return query.order_by(GroupBuyDeal.overall_score.desc()).limit(limit).all()

    def get_flash_sales(self, platform: Optional[str] = None,
                         limit: int = 20) -> List[GroupBuyDeal]:
        query = self.db.query(GroupBuyDeal).filter(
            GroupBuyDeal.status == GroupBuyStatus.ACTIVE.value,
            GroupBuyDeal.end_time > datetime.utcnow(),
            GroupBuyDeal.is_flash_sale == True
        )
        
        if platform:
            query = query.filter(GroupBuyDeal.platform == platform)
        
        return query.order_by(GroupBuyDeal.end_time).limit(limit).all()

    def analyze_quantity_discount(self, product_id: str,
                                   max_quantity: int = 50) -> Dict[str, Any]:
        prices = self.db.query(ProductPrice).filter(
            ProductPrice.product_id == product_id
        ).all()
        
        if not prices:
            return {"error": "未找到价格信息"}
        
        base_price = min(p.price for p in prices if p.price)
        
        analysis = {
            "product_id": product_id,
            "base_price": base_price,
            "quantity_tiers": [],
            "best_value": None,
            "recommendation": None
        }
        
        best_savings = 0
        best_tier = None
        
        for qty in [1, 2, 3, 5, 10, 20, 50]:
            if qty > max_quantity:
                continue
                
            discount = self._estimate_quantity_discount(qty)
            unit_price = base_price * (1 - discount)
            total_price = unit_price * qty
            savings_per_unit = base_price - unit_price
            
            tier_info = {
                "quantity": qty,
                "discount_percent": discount,
                "unit_price": round(unit_price, 2),
                "total_price": round(total_price, 2),
                "savings_per_unit": round(savings_per_unit, 2),
                "total_savings": round(savings_per_unit * qty, 2)
            }
            
            analysis["quantity_tiers"].append(tier_info)
            
            if discount > best_savings:
                best_savings = discount
                best_tier = tier_info
        
        analysis["best_value"] = best_tier
        
        if best_savings >= 0.15:
            analysis["recommendation"] = f"建议购买{best_tier['quantity']}件，可节省{best_savings*100:.0f}%"
        elif best_savings >= 0.1:
            analysis["recommendation"] = f"推荐购买{best_tier['quantity']}件，性价比最高"
        else:
            analysis["recommendation"] = "按量购买即可，批量优惠不大"
        
        return analysis

    def _estimate_quantity_discount(self, quantity: int) -> float:
        if quantity >= 50:
            return 0.25
        elif quantity >= 20:
            return 0.20
        elif quantity >= 10:
            return 0.15
        elif quantity >= 5:
            return 0.10
        elif quantity >= 3:
            return 0.07
        elif quantity >= 2:
            return 0.05
        else:
            return 0.0

    def create_custom_groupbuy(self, user_id: str, product_id: str,
                                target_price: float,
                                min_participants: int = 5,
                                duration_hours: int = 48) -> GroupBuyDeal:
        product = self.db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise ValueError("商品不存在")
        
        prices = self.db.query(ProductPrice).filter(
            ProductPrice.product_id == product_id
        ).all()
        
        if not prices:
            raise ValueError("未找到价格信息")
        
        current_price = min(p.price for p in prices if p.price)
        
        if target_price >= current_price:
            raise ValueError("目标价格必须低于当前价格")
        
        discount_percent = (current_price - target_price) / current_price
        
        deal = GroupBuyDeal(
            id=str(uuid.uuid4()),
            title=f"求组团 - {product.name}",
            description=f"目标价格{target_price:.2f}元，{min_participants}人成团",
            platform="community",
            product_id=product_id,
            product_name=product.name,
            product_image=product.image_url,
            product_url=product.url,
            category=product.category,
            brand=product.brand,
            original_price=current_price,
            group_price=target_price,
            unit_price=target_price,
            discount_percent=discount_percent,
            savings_amount=current_price - target_price,
            deal_type=GroupBuyType.COMMUNITY.value,
            min_quantity=1,
            target_participants=min_participants,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow() + timedelta(hours=duration_hours),
            duration_hours=duration_hours,
            status=GroupBuyStatus.PENDING.value,
            popularity_score=50,
            value_score=discount_percent * 100,
            overall_score=discount_percent * 100 * 0.6 + 50 * 0.4,
        )
        
        self.db.add(deal)
        self.db.commit()
        self.db.refresh(deal)
        
        self.join_groupbuy(deal.id, user_id, 1, "发起者")
        
        return deal
