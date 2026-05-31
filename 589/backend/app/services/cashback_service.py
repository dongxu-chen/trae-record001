from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import random
import uuid

from ..models.procurement import (
    CashbackTransaction, CashbackStatus, CashbackRule,
    UserCashbackAccount, PriceComparisonV2
)
from ..models import Product, ProductPrice, Coupon


class CashbackService:
    def __init__(self, db: Session):
        self.db = db
        self.platforms = ["taobao", "jd", "pdd", "suning"]
        self.default_cashback_rates = {
            "taobao": 0.03,
            "jd": 0.02,
            "pdd": 0.05,
            "suning": 0.015
        }

    def calculate_cashback(self, product_id: str, price: float,
                          platform: str, category: Optional[str] = None,
                          brand: Optional[str] = None) -> Dict[str, Any]:
        rules = self._get_applicable_rules(platform, category, brand, product_id, price)
        
        best_rule = None
        max_cashback = 0
        
        for rule in rules:
            cashback = self._calculate_rule_cashback(rule, price)
            if cashback > max_cashback:
                max_cashback = cashback
                best_rule = rule
        
        if not best_rule:
            default_rate = self.default_cashback_rates.get(platform, 0.02)
            max_cashback = price * default_rate
            best_rule = {
                "rule_type": "default",
                "cashback_rate": default_rate,
                "platform": platform
            }
        
        effective_price = price - max_cashback
        
        return {
            "product_id": product_id,
            "platform": platform,
            "original_price": price,
            "cashback_amount": round(max_cashback, 2),
            "cashback_rate": best_rule.get("cashback_rate", best_rule.cashback_rate if hasattr(best_rule, "cashback_rate") else 0),
            "effective_price": round(effective_price, 2),
            "rule_type": best_rule.get("rule_type", best_rule.rule_type if hasattr(best_rule, "rule_type") else "custom"),
            "rule_id": best_rule.id if hasattr(best_rule, "id") else None,
            "is_promo": best_rule.get("is_promo", best_rule.is_promo if hasattr(best_rule, "is_promo") else False)
        }

    def _get_applicable_rules(self, platform: str, category: Optional[str],
                               brand: Optional[str], product_id: Optional[str],
                               price: float) -> List[CashbackRule]:
        query = self.db.query(CashbackRule).filter(
            CashbackRule.platform == platform,
            CashbackRule.is_active == True,
            (CashbackRule.valid_from == None) | (CashbackRule.valid_from <= datetime.utcnow()),
            (CashbackRule.valid_to == None) | (CashbackRule.valid_to >= datetime.utcnow()),
            CashbackRule.min_order_amount <= price
        )
        
        all_rules = query.all()
        
        applicable = []
        for rule in all_rules:
            if rule.product_id and rule.product_id != product_id:
                continue
            if rule.category and category and rule.category != category:
                continue
            if rule.brand and brand and rule.brand != brand:
                continue
            applicable.append(rule)
        
        applicable.sort(key=lambda x: (-x.priority, -x.cashback_rate))
        return applicable

    def _calculate_rule_cashback(self, rule: CashbackRule, price: float) -> float:
        if rule.rule_type == "percentage":
            cashback = price * rule.cashback_rate
        elif rule.rule_type == "fixed":
            cashback = rule.fixed_amount
        elif rule.rule_type == "tiered" and rule.tiered_rates:
            cashback = self._calculate_tiered_cashback(rule.tiered_rates, price)
        else:
            cashback = price * rule.cashback_rate
        
        if rule.max_cashback_amount:
            cashback = min(cashback, rule.max_cashback_amount)
        
        return cashback

    def _calculate_tiered_cashback(self, tiered_rates: List[Dict], price: float) -> float:
        max_rate = 0
        for tier in tiered_rates:
            if price >= tier.get("min_amount", 0):
                max_rate = max(max_rate, tier.get("rate", 0))
        return price * max_rate

    def compare_prices_with_cashback(self, product_id: str) -> Dict[str, Any]:
        product = self.db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise ValueError("商品不存在")
        
        prices = self.db.query(ProductPrice).filter(
            ProductPrice.product_id == product_id
        ).all()
        
        if not prices:
            raise ValueError("未找到价格信息")
        
        platform_data = {}
        all_final_prices = []
        original_prices = []
        cashback_amounts = []
        
        for price in prices:
            original_price = price.price if price and price.price else 0
            original_prices.append(original_price)
            
            cashback_result = self.calculate_cashback(
                product_id, original_price, price.platform,
                product.category, product.brand
            )
            
            coupon_discount = self._get_coupon_discount(price.platform, product.category, original_price)
            
            price_after_coupon = original_price - coupon_discount
            final_price = price_after_coupon - cashback_result["cashback_amount"]
            total_savings = original_price - final_price
            savings_percent = total_savings / original_price if original_price else 0
            
            cashback_amounts.append(cashback_result["cashback_amount"])
            
            platform_data[price.platform] = {
                "platform": price.platform,
                "original_price": original_price,
                "coupon_discount": round(coupon_discount, 2),
                "cashback_amount": cashback_result["cashback_amount"],
                "cashback_rate": cashback_result["cashback_rate"],
                "price_after_coupon": round(price_after_coupon, 2),
                "final_price": round(final_price, 2),
                "total_savings": round(total_savings, 2),
                "savings_percent": round(savings_percent * 100, 2),
                "cashback_rule_type": cashback_result["rule_type"],
                "is_promo_cashback": cashback_result["is_promo"]
            }
            all_final_prices.append(final_price)
        
        if all_final_prices:
            best_idx = all_final_prices.index(min(all_final_prices))
            best_platform = list(platform_data.keys())[best_idx]
            best_data = platform_data[best_platform]
        else:
            best_platform = None
            best_data = None
        
        comparison = {
            "product_id": product_id,
            "product_name": product.name,
            "platform_prices": platform_data,
            "summary": {
                "original_price_min": min(original_prices) if original_prices else 0,
                "original_price_max": max(original_prices) if original_prices else 0,
                "original_price_avg": sum(original_prices) / len(original_prices) if original_prices else 0,
                "cashback_min": min(cashback_amounts) if cashback_amounts else 0,
                "cashback_max": max(cashback_amounts) if cashback_amounts else 0,
                "final_price_min": min(all_final_prices) if all_final_prices else 0,
                "final_price_max": max(all_final_prices) if all_final_prices else 0,
                "final_price_avg": sum(all_final_prices) / len(all_final_prices) if all_final_prices else 0,
            },
            "best_deal": {
                "platform": best_platform,
                "original_price": best_data["original_price"] if best_data else 0,
                "final_price": best_data["final_price"] if best_data else 0,
                "total_savings": best_data["total_savings"] if best_data else 0,
                "savings_percent": best_data["savings_percent"] if best_data else 0,
                "coupon_discount": best_data["coupon_discount"] if best_data else 0,
                "cashback_amount": best_data["cashback_amount"] if best_data else 0,
            } if best_data else None
        }
        
        self._save_comparison_result(product_id, comparison)
        
        return comparison

    def _get_coupon_discount(self, platform: str, category: Optional[str],
                              price: float) -> float:
        coupons = self.db.query(Coupon).filter(
            Coupon.platform == platform,
            Coupon.is_active == True,
            Coupon.min_amount <= price
        ).all()
        
        max_discount = 0
        for coupon in coupons:
            if coupon.category and category and coupon.category != category:
                continue
            if coupon.discount_type == "percentage":
                discount = price * coupon.discount_value
            else:
                discount = coupon.discount_value
            
            if coupon.max_discount:
                discount = min(discount, coupon.max_discount)
            
            max_discount = max(max_discount, discount)
        
        return max_discount

    def _save_comparison_result(self, product_id: str, comparison: Dict[str, Any]):
        summary = comparison["summary"]
        best = comparison["best_deal"] or {}
        
        record = PriceComparisonV2(
            product_id=product_id,
            platform_prices=comparison["platform_prices"],
            original_price_min=summary["original_price_min"],
            original_price_max=summary["original_price_max"],
            original_price_avg=summary["original_price_avg"],
            cashback_min=summary["cashback_min"],
            cashback_max=summary["cashback_max"],
            final_price_min=summary["final_price_min"],
            final_price_max=summary["final_price_max"],
            final_price_avg=summary["final_price_avg"],
            best_platform=best.get("platform"),
            best_price=best.get("original_price", 0),
            best_final_price=best.get("final_price", 0),
            best_total_savings=best.get("total_savings", 0),
            best_savings_percent=best.get("savings_percent", 0),
            breakdown=comparison
        )
        
        self.db.add(record)
        self.db.commit()

    def create_transaction(self, user_id: str, platform: str,
                           product_id: str, product_name: str,
                           original_price: float, final_price: float,
                           cashback_rate: float, cashback_amount: float,
                           coupon_amount: float = 0,
                           discount_amount: float = 0,
                           platform_transaction_id: Optional[str] = None,
                           affiliate_id: Optional[str] = None,
                           click_id: Optional[str] = None,
                           source_type: str = "direct") -> CashbackTransaction:
        effective_price = final_price - cashback_amount
        
        transaction = CashbackTransaction(
            id=str(uuid.uuid4()),
            user_id=user_id,
            platform=platform,
            product_id=product_id,
            product_name=product_name,
            original_price=original_price,
            final_price=final_price,
            cashback_rate=cashback_rate,
            cashback_amount=cashback_amount,
            coupon_amount=coupon_amount,
            discount_amount=discount_amount,
            effective_price=effective_price,
            status=CashbackStatus.PENDING.value,
            platform_transaction_id=platform_transaction_id,
            affiliate_id=affiliate_id,
            click_id=click_id,
            purchase_date=datetime.utcnow(),
            expected_payout_date=datetime.utcnow() + timedelta(days=60),
            source_type=source_type
        )
        
        self.db.add(transaction)
        
        account = self.get_or_create_account(user_id)
        account.pending_amount += cashback_amount
        
        self.db.commit()
        self.db.refresh(transaction)
        
        return transaction

    def confirm_transaction(self, transaction_id: str) -> CashbackTransaction:
        transaction = self.db.query(CashbackTransaction).filter(
            CashbackTransaction.id == transaction_id
        ).first()
        
        if not transaction:
            raise ValueError("交易不存在")
        
        if transaction.status != CashbackStatus.PENDING.value:
            raise ValueError("交易状态不允许确认")
        
        transaction.status = CashbackStatus.CONFIRMED.value
        
        account = self.get_or_create_account(transaction.user_id)
        account.pending_amount -= transaction.cashback_amount
        account.available_balance += transaction.cashback_amount
        
        self.db.commit()
        self.db.refresh(transaction)
        
        return transaction

    def process_payout(self, transaction_id: str) -> CashbackTransaction:
        transaction = self.db.query(CashbackTransaction).filter(
            CashbackTransaction.id == transaction_id
        ).first()
        
        if not transaction:
            raise ValueError("交易不存在")
        
        if transaction.status != CashbackStatus.CONFIRMED.value:
            raise ValueError("交易状态不允许打款")
        
        transaction.status = CashbackStatus.PAID.value
        transaction.actual_payout_date = datetime.utcnow()
        
        account = self.get_or_create_account(transaction.user_id)
        account.available_balance -= transaction.cashback_amount
        account.total_paid += transaction.cashback_amount
        account.last_payout_date = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(transaction)
        
        return transaction

    def get_user_transactions(self, user_id: str, status: Optional[str] = None,
                               limit: int = 50, offset: int = 0) -> List[CashbackTransaction]:
        query = self.db.query(CashbackTransaction).filter(
            CashbackTransaction.user_id == user_id
        )
        
        if status:
            query = query.filter(CashbackTransaction.status == status)
        
        return query.order_by(CashbackTransaction.created_at.desc()).offset(offset).limit(limit).all()

    def get_or_create_account(self, user_id: str) -> UserCashbackAccount:
        account = self.db.query(UserCashbackAccount).filter(
            UserCashbackAccount.user_id == user_id
        ).first()
        
        if not account:
            account = UserCashbackAccount(
                user_id=user_id
            )
            self.db.add(account)
            self.db.commit()
            self.db.refresh(account)
        
        return account

    def update_account(self, user_id: str, **kwargs) -> UserCashbackAccount:
        account = self.get_or_create_account(user_id)
        
        for key, value in kwargs.items():
            if hasattr(account, key):
                setattr(account, key, value)
        
        account.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(account)
        
        return account

    def get_account_summary(self, user_id: str) -> Dict[str, Any]:
        account = self.get_or_create_account(user_id)
        
        pending_transactions = self.db.query(CashbackTransaction).filter(
            CashbackTransaction.user_id == user_id,
            CashbackTransaction.status == CashbackStatus.PENDING.value
        ).count()
        
        confirmed_transactions = self.db.query(CashbackTransaction).filter(
            CashbackTransaction.user_id == user_id,
            CashbackTransaction.status == CashbackStatus.CONFIRMED.value
        ).count()
        
        total_transactions = self.db.query(CashbackTransaction).filter(
            CashbackTransaction.user_id == user_id
        ).count()
        
        return {
            "user_id": user_id,
            "total_earned": round(account.total_earned, 2),
            "total_paid": round(account.total_paid, 2),
            "pending_amount": round(account.pending_amount, 2),
            "available_balance": round(account.available_balance, 2),
            "minimum_payout": account.minimum_payout,
            "payout_method": account.payout_method,
            "can_withdraw": account.available_balance >= account.minimum_payout,
            "transactions_summary": {
                "total": total_transactions,
                "pending": pending_transactions,
                "confirmed": confirmed_transactions
            },
            "last_payout_date": account.last_payout_date.isoformat() if account.last_payout_date else None,
            "next_payout_date": account.next_payout_date.isoformat() if account.next_payout_date else None
        }

    def create_cashback_rule(self, platform: str, rule_type: str,
                              cashback_rate: float = 0, fixed_amount: float = 0,
                              category: Optional[str] = None,
                              brand: Optional[str] = None,
                              product_id: Optional[str] = None,
                              min_order_amount: float = 0,
                              max_cashback_amount: Optional[float] = None,
                              valid_from: Optional[datetime] = None,
                              valid_to: Optional[datetime] = None,
                              is_promo: bool = False,
                              priority: int = 0) -> CashbackRule:
        rule = CashbackRule(
            id=str(uuid.uuid4()),
            platform=platform,
            category=category,
            brand=brand,
            product_id=product_id,
            rule_type=rule_type,
            cashback_rate=cashback_rate,
            fixed_amount=fixed_amount,
            min_order_amount=min_order_amount,
            max_cashback_amount=max_cashback_amount,
            valid_from=valid_from,
            valid_to=valid_to,
            is_promo=is_promo,
            priority=priority
        )
        
        self.db.add(rule)
        self.db.commit()
        self.db.refresh(rule)
        
        return rule

    def get_active_rules(self, platform: Optional[str] = None,
                          category: Optional[str] = None) -> List[CashbackRule]:
        query = self.db.query(CashbackRule).filter(
            CashbackRule.is_active == True,
            (CashbackRule.valid_from == None) | (CashbackRule.valid_from <= datetime.utcnow()),
            (CashbackRule.valid_to == None) | (CashbackRule.valid_to >= datetime.utcnow())
        )
        
        if platform:
            query = query.filter(CashbackRule.platform == platform)
        if category:
            query = query.filter(CashbackRule.category == category)
        
        return query.order_by(CashbackRule.priority.desc()).all()

    def get_best_cashback_deals(self, category: Optional[str] = None,
                                 limit: int = 20) -> List[Dict[str, Any]]:
        deals = []
        
        products_query = self.db.query(Product)
        if category:
            products_query = products_query.filter(Product.category == category)
        
        products = products_query.limit(100).all()
        
        for product in products:
            try:
                comparison = self.compare_prices_with_cashback(product.id)
                best = comparison.get("best_deal")
                if best and best.get("savings_percent", 0) >= 5:
                    deals.append({
                        "product_id": product.id,
                        "product_name": product.name,
                        "product_image": product.image_url,
                        "category": product.category,
                        "best_platform": best.get("platform"),
                        "original_price": best.get("original_price"),
                        "final_price": best.get("final_price"),
                        "total_savings": best.get("total_savings"),
                        "savings_percent": best.get("savings_percent"),
                        "cashback_amount": best.get("cashback_amount"),
                        "coupon_discount": best.get("coupon_discount"),
                    })
            except:
                continue
        
        deals.sort(key=lambda x: -x["savings_percent"])
        return deals[:limit]

    def request_withdrawal(self, user_id: str, amount: float) -> Dict[str, Any]:
        account = self.get_or_create_account(user_id)
        
        if amount > account.available_balance:
            return {
                "success": False,
                "message": "余额不足"
            }
        
        if amount < account.minimum_payout:
            return {
                "success": False,
                "message": f"最低提现金额为 {account.minimum_payout} 元"
            }
        
        account.available_balance -= amount
        account.total_paid += amount
        account.last_payout_date = datetime.utcnow()
        
        self.db.commit()
        
        return {
            "success": True,
            "message": "提现申请已提交",
            "withdrawal_amount": amount,
            "remaining_balance": round(account.available_balance, 2),
            "payout_method": account.payout_method,
            "expected_processing_days": 3
        }

    def generate_affiliate_link(self, product_id: str, platform: str,
                                 user_id: str) -> Dict[str, Any]:
        affiliate_id = f"aff_{user_id}_{int(datetime.utcnow().timestamp())}"
        click_id = f"clk_{uuid.uuid4().hex[:12]}"
        
        product = self.db.query(Product).filter(Product.id == product_id).first()
        
        base_urls = {
            "taobao": "https://s.click.taobao.com/t",
            "jd": "https://union.jd.com/proManager/index",
            "pdd": "https://jinbao.pinduoduo.com/",
            "suning": "https://union.suning.com/"
        }
        
        base_url = base_urls.get(platform, "#")
        
        tracking_params = f"af={affiliate_id}&ck={click_id}&uid={user_id}"
        
        return {
            "product_id": product_id,
            "platform": platform,
            "affiliate_id": affiliate_id,
            "click_id": click_id,
            "tracking_params": tracking_params,
            "affiliate_link": f"{base_url}?productId={product_id}&{tracking_params}",
            "product_name": product.name if product else None,
            "estimated_cashback_rate": self.default_cashback_rates.get(platform, 0.02)
        }
