import re
import json
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import defaultdict

from sqlalchemy.orm import Session
from ..models import (
    CouponShare, CouponShareStatus, VerificationStatus,
    CouponVerification, CouponVote, UserReward,
    CouponMinedRule, CouponUsageLog
)


@dataclass
class CouponShareResult:
    share_id: str
    status: str
    message: str
    reward_points: int
    verification_url: Optional[str]


@dataclass
class MinedRuleResult:
    pattern: str
    support: float
    confidence: float
    lift: float
    frequency: int
    suggested_discount: Optional[float]
    suggested_min_amount: Optional[float]


class CouponShareService:
    def __init__(self, db: Session):
        self.db = db
        self._init_reward_rules()

    def _init_reward_rules(self):
        self.reward_rules = {
            "share_submitted": 10,
            "share_approved": 50,
            "share_verified": 30,
            "verification_performed": 5,
            "verification_accurate": 10,
            "high_quality_share": 100,
        }

    def share_coupon(self, user_id: str, user_nickname: str,
                     platform: str, code: str, discount: float,
                     discount_type: str, min_amount: float = 0,
                     max_discount: Optional[float] = None,
                     valid_from: Optional[datetime] = None,
                     valid_to: Optional[datetime] = None,
                     applicable_products: Optional[str] = None,
                     applicable_categories: Optional[str] = None,
                     description: Optional[str] = None,
                     source_url: Optional[str] = None) -> CouponShareResult:
        
        valid_from = valid_from or datetime.now().date()
        valid_to = valid_to or (datetime.now() + timedelta(days=30)).date()
        
        existing = self.db.query(CouponShare).filter(
            CouponShare.platform == platform,
            CouponShare.code == code,
            CouponShare.status != CouponShareStatus.EXPIRED
        ).first()
        
        if existing:
            return CouponShareResult(
                share_id=existing.id,
                status="duplicate",
                message="该优惠券已存在",
                reward_points=0,
                verification_url=None
            )
        
        coupon_share = CouponShare(
            user_id=user_id,
            user_nickname=user_nickname,
            platform=platform,
            code=code,
            discount=discount,
            discount_type=discount_type,
            min_amount=min_amount,
            max_discount=max_discount,
            applicable_products=applicable_products,
            applicable_categories=applicable_categories,
            valid_from=valid_from,
            valid_to=valid_to,
            description=description,
            source_url=source_url,
            status=CouponShareStatus.PENDING,
            verification_status=VerificationStatus.UNVERIFIED,
            reward_points=self.reward_rules["share_submitted"]
        )
        
        self.db.add(coupon_share)
        self.db.commit()
        self.db.refresh(coupon_share)
        
        self._add_reward(
            user_id=user_id,
            points=self.reward_rules["share_submitted"],
            reward_type="coupon_share_submitted",
            related_coupon_id=coupon_share.id,
            description=f"分享优惠券获得 {self.reward_rules['share_submitted']} 积分"
        )
        
        auto_approve = self._auto_approve_check(coupon_share)
        if auto_approve:
            self._approve_coupon(coupon_share, "system_auto_approve")
        
        return CouponShareResult(
            share_id=coupon_share.id,
            status=coupon_share.status.value,
            message="优惠券分享成功，等待审核验证",
            reward_points=coupon_share.reward_points,
            verification_url=f"/coupons/share/{coupon_share.id}/verify"
        )

    def _auto_approve_check(self, coupon: CouponShare) -> bool:
        user_shares = self.db.query(CouponShare).filter(
            CouponShare.user_id == coupon.user_id
        ).count()
        
        user_approved = self.db.query(CouponShare).filter(
            CouponShare.user_id == coupon.user_id,
            CouponShare.status == CouponShareStatus.APPROVED
        ).count()
        
        if user_shares > 0:
            approval_rate = user_approved / user_shares
            if approval_rate >= 0.8 and user_approved >= 5:
                return True
        
        if coupon.min_amount >= 100 and coupon.discount <= 20:
            return True
        
        return False

    def verify_coupon(self, coupon_share_id: str, verifier_id: str,
                      is_valid: bool, verification_method: str = "manual",
                      actual_discount: Optional[float] = None,
                      verification_result: Optional[str] = None) -> Dict[str, Any]:
        
        coupon_share = self.db.query(CouponShare).filter(
            CouponShare.id == coupon_share_id
        ).first()
        
        if not coupon_share:
            return {"success": False, "message": "优惠券分享不存在"}
        
        verification = CouponVerification(
            coupon_share_id=coupon_share_id,
            verifier_id=verifier_id,
            is_valid=is_valid,
            verification_method=verification_method,
            verification_result=verification_result,
            actual_discount=actual_discount
        )
        
        self.db.add(verification)
        
        coupon_share.verification_count += 1
        if is_valid:
            coupon_share.success_count += 1
        else:
            coupon_share.fail_count += 1
        
        success_rate = coupon_share.success_count / max(coupon_share.verification_count, 1)
        
        if coupon_share.verification_count >= 3:
            if success_rate >= 0.8:
                coupon_share.verification_status = VerificationStatus.VERIFIED
                if coupon_share.status == CouponShareStatus.PENDING:
                    self._approve_coupon(coupon_share, verifier_id)
            elif success_rate <= 0.2:
                coupon_share.verification_status = VerificationStatus.FAILED
                if coupon_share.status == CouponShareStatus.PENDING:
                    coupon_share.status = CouponShareStatus.REJECTED
        
        self.db.commit()
        
        self._add_reward(
            user_id=verifier_id,
            points=self.reward_rules["verification_performed"],
            reward_type="coupon_verification",
            related_coupon_id=coupon_share_id,
            related_verification_id=verification.id,
            description=f"验证优惠券获得 {self.reward_rules['verification_performed']} 积分"
        )
        
        return {
            "success": True,
            "coupon_status": coupon_share.status.value,
            "verification_status": coupon_share.verification_status.value,
            "success_rate": success_rate,
            "reward_points": self.reward_rules["verification_performed"]
        }

    def _approve_coupon(self, coupon: CouponShare, reviewer_id: str):
        coupon.status = CouponShareStatus.APPROVED
        coupon.reviewed_by = reviewer_id
        coupon.reviewed_at = datetime.now()
        
        additional_reward = self.reward_rules["share_approved"]
        if coupon.verification_status == VerificationStatus.VERIFIED:
            additional_reward += self.reward_rules["share_verified"]
        
        if coupon.discount >= 30 or coupon.success_count >= 10:
            additional_reward += self.reward_rules["high_quality_share"]
        
        coupon.reward_points += additional_reward
        
        self._add_reward(
            user_id=coupon.user_id,
            points=additional_reward,
            reward_type="coupon_approved",
            related_coupon_id=coupon.id,
            description=f"优惠券通过审核获得 {additional_reward} 积分"
        )

    def vote_coupon(self, coupon_share_id: str, user_id: str,
                    vote_type: str) -> Dict[str, Any]:
        
        coupon_share = self.db.query(CouponShare).filter(
            CouponShare.id == coupon_share_id
        ).first()
        
        if not coupon_share:
            return {"success": False, "message": "优惠券分享不存在"}
        
        existing_vote = self.db.query(CouponVote).filter(
            CouponVote.coupon_share_id == coupon_share_id,
            CouponVote.user_id == user_id
        ).first()
        
        if existing_vote:
            if existing_vote.vote_type == vote_type:
                return {"success": False, "message": "已经投过票了"}
            
            if existing_vote.vote_type == "up":
                coupon_share.upvotes -= 1
            else:
                coupon_share.downvotes -= 1
            
            existing_vote.vote_type = vote_type
        else:
            existing_vote = CouponVote(
                coupon_share_id=coupon_share_id,
                user_id=user_id,
                vote_type=vote_type
            )
            self.db.add(existing_vote)
        
        if vote_type == "up":
            coupon_share.upvotes += 1
        else:
            coupon_share.downvotes += 1
        
        self.db.commit()
        
        return {
            "success": True,
            "upvotes": coupon_share.upvotes,
            "downvotes": coupon_share.downvotes,
            "score": coupon_share.upvotes - coupon_share.downvotes
        }

    def get_user_rewards(self, user_id: str) -> Dict[str, Any]:
        rewards = self.db.query(UserReward).filter(
            UserReward.user_id == user_id
        ).order_by(UserReward.created_at.desc()).all()
        
        total_points = sum(r.points for r in rewards)
        
        return {
            "total_points": total_points,
            "reward_count": len(rewards),
            "recent_rewards": [
                {
                    "points": r.points,
                    "type": r.reward_type,
                    "description": r.description,
                    "created_at": r.created_at.isoformat()
                }
                for r in rewards[:10]
            ]
        }

    def _add_reward(self, user_id: str, points: int, reward_type: str,
                    related_coupon_id: Optional[str] = None,
                    related_verification_id: Optional[str] = None,
                    description: Optional[str] = None):
        
        reward = UserReward(
            user_id=user_id,
            points=points,
            reward_type=reward_type,
            related_coupon_id=related_coupon_id,
            related_verification_id=related_verification_id,
            description=description
        )
        
        self.db.add(reward)
        self.db.commit()

    def get_pending_verifications(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        verified_ids = self.db.query(CouponVerification.coupon_share_id).filter(
            CouponVerification.verifier_id == user_id
        ).subquery()
        
        pending = self.db.query(CouponShare).filter(
            CouponShare.status == CouponShareStatus.PENDING,
            CouponShare.verification_status != VerificationStatus.VERIFIED,
            CouponShare.user_id != user_id,
            CouponShare.id.notin_(verified_ids)
        ).order_by(CouponShare.created_at.desc()).limit(limit).all()
        
        return [
            {
                "id": c.id,
                "platform": c.platform,
                "code": c.code,
                "discount": float(c.discount),
                "discount_type": c.discount_type,
                "min_amount": float(c.min_amount),
                "description": c.description,
                "user_nickname": c.user_nickname,
                "verification_count": c.verification_count,
                "success_count": c.success_count,
                "created_at": c.created_at.isoformat()
            }
            for c in pending
        ]

    def get_approved_coupons(self, platform: Optional[str] = None,
                            category: Optional[str] = None,
                            min_discount: Optional[float] = None,
                            limit: int = 50) -> List[Dict[str, Any]]:
        
        query = self.db.query(CouponShare).filter(
            CouponShare.status == CouponShareStatus.APPROVED,
            CouponShare.verification_status == VerificationStatus.VERIFIED,
            CouponShare.valid_from <= datetime.now().date(),
            CouponShare.valid_to >= datetime.now().date()
        )
        
        if platform:
            query = query.filter(CouponShare.platform == platform)
        
        if min_discount:
            query = query.filter(CouponShare.discount >= min_discount)
        
        coupons = query.order_by(
            (CouponShare.upvotes - CouponShare.downvotes).desc()
        ).limit(limit).all()
        
        return [
            {
                "id": c.id,
                "platform": c.platform,
                "code": c.code,
                "discount": float(c.discount),
                "discount_type": c.discount_type,
                "min_amount": float(c.min_amount),
                "max_discount": float(c.max_discount) if c.max_discount else None,
                "valid_from": c.valid_from.isoformat(),
                "valid_to": c.valid_to.isoformat(),
                "description": c.description,
                "applicable_categories": c.applicable_categories,
                "upvotes": c.upvotes,
                "downvotes": c.downvotes,
                "success_rate": c.success_count / max(c.verification_count, 1),
                "shared_by": c.user_nickname
            }
            for c in coupons
        ]

    def record_usage(self, coupon_id: str, user_id: str,
                     product_id: Optional[str], original_price: float,
                     discount_amount: float, final_price: float,
                     is_successful: bool = True,
                     error_message: Optional[str] = None,
                     coupon_source: str = "crowdsource"):
        
        usage_log = CouponUsageLog(
            coupon_id=coupon_id,
            coupon_source=coupon_source,
            user_id=user_id,
            product_id=product_id,
            original_price=original_price,
            discount_amount=discount_amount,
            final_price=final_price,
            is_successful=is_successful,
            error_message=error_message
        )
        
        self.db.add(usage_log)
        self.db.commit()


class CouponRuleMiner:
    def __init__(self, db: Session):
        self.db = db
        self._init_pattern_templates()

    def _init_pattern_templates(self):
        self.pattern_templates = {
            "percent_discount": [
                r"满(\d+)减(\d+)",
                r"(\d+)元优惠券",
                r"立减(\d+)元",
                r"优惠(\d+)元",
                r"省(\d+)元",
            ],
            "fixed_discount": [
                r"(\d+)折",
                r"(\d+)%[oO][fF][fF]",
                r"优惠(\d+)%",
                r"打(\d+)折",
            ],
            "platform_specific": {
                "taobao": [r"淘宝(\d+)元券", r"天猫(\d+)元券"],
                "jd": [r"京东(\d+)元券", r"东券(\d+)元"],
                "pdd": [r"拼多多(\d+)元券", r"多多券(\d+)"],
                "suning": [r"苏宁(\d+)元券"],
            }
        }

    def mine_rules_from_text(self, text: str, platform: Optional[str] = None) -> List[Dict[str, Any]]:
        if not text:
            return []
        
        found_rules = []
        
        for rule_name, patterns in self.pattern_templates.items():
            if isinstance(patterns, dict):
                if platform and platform in patterns:
                    patterns = patterns[platform]
                else:
                    continue
            
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    if isinstance(match, tuple):
                        if len(match) >= 2 and rule_name == "percent_discount":
                            min_amount, discount = match
                            found_rules.append({
                                "pattern": pattern,
                                "rule_type": rule_name,
                                "min_amount": float(min_amount),
                                "discount": float(discount),
                                "matched_text": text[max(0, text.find(match[0])-10):text.find(match[0])+50]
                            })
                        elif len(match) >= 1:
                            discount = match[0]
                            found_rules.append({
                                "pattern": pattern,
                                "rule_type": rule_name,
                                "discount": float(discount),
                                "matched_text": text[max(0, text.find(match[0])-10):text.find(match[0])+50]
                            })
                    else:
                        found_rules.append({
                            "pattern": pattern,
                            "rule_type": rule_name,
                            "discount": float(match),
                            "matched_text": text[max(0, text.find(match)-10):text.find(match)+50]
                        })
        
        return found_rules

    def mine_association_rules(self, transactions: List[List[str]],
                               min_support: float = 0.1,
                               min_confidence: float = 0.5) -> List[MinedRuleResult]:
        if not transactions:
            return []
        
        item_counts = defaultdict(int)
        item_pair_counts = defaultdict(int)
        total_transactions = len(transactions)
        
        for transaction in transactions:
            unique_items = set(transaction)
            for item in unique_items:
                item_counts[item] += 1
            
            items_list = list(unique_items)
            for i in range(len(items_list)):
                for j in range(i + 1, len(items_list)):
                    pair = tuple(sorted([items_list[i], items_list[j]]))
                    item_pair_counts[pair] += 1
        
        rules = []
        for pair, count in item_pair_counts.items():
            support = count / total_transactions
            if support < min_support:
                continue
            
            for i in range(2):
                antecedent = pair[i]
                consequent = pair[1 - i]
                
                antecedent_count = item_counts[antecedent]
                if antecedent_count == 0:
                    continue
                
                confidence = count / antecedent_count
                if confidence < min_confidence:
                    continue
                
                consequent_count = item_counts[consequent]
                if consequent_count == 0:
                    continue
                
                lift = confidence / (consequent_count / total_transactions)
                
                discount_info = self._extract_discount_from_rule(consequent)
                
                rules.append(MinedRuleResult(
                    pattern=f"{antecedent} -> {consequent}",
                    support=support,
                    confidence=confidence,
                    lift=lift,
                    frequency=count,
                    suggested_discount=discount_info.get("discount"),
                    suggested_min_amount=discount_info.get("min_amount")
                ))
        
        rules.sort(key=lambda r: (r.confidence, r.support, r.lift), reverse=True)
        return rules

    def _extract_discount_from_rule(self, rule_text: str) -> Dict[str, Any]:
        result = {}
        
        discount_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:元|块|%)', rule_text)
        if discount_match:
            result["discount"] = float(discount_match.group(1))
        
        min_amount_match = re.search(r'满(\d+(?:\.\d+)?)', rule_text)
        if min_amount_match:
            result["min_amount"] = float(min_amount_match.group(1))
        
        return result

    def mine_from_shares(self, platform: Optional[str] = None,
                         days: int = 30,
                         min_frequency: int = 5) -> List[Dict[str, Any]]:
        
        query = self.db.query(CouponShare).filter(
            CouponShare.created_at >= datetime.now() - timedelta(days=days)
        )
        
        if platform:
            query = query.filter(CouponShare.platform == platform)
        
        shares = query.all()
        
        pattern_frequency = defaultdict(lambda: {
            "count": 0,
            "success": 0,
            "total": 0,
            "discounts": [],
            "min_amounts": []
        })
        
        for share in shares:
            text = f"{share.description or ''} {share.code} {share.applicable_categories or ''}"
            rules = self.mine_rules_from_text(text, share.platform)
            
            for rule in rules:
                key = (rule["pattern"], share.platform)
                data = pattern_frequency[key]
                data["count"] += 1
                data["total"] += 1
                if "discount" in rule:
                    data["discounts"].append(rule["discount"])
                if "min_amount" in rule:
                    data["min_amounts"].append(rule["min_amount"])
                
                if share.verification_status == VerificationStatus.VERIFIED:
                    data["success"] += 1
        
        results = []
        for (pattern, plat), data in pattern_frequency.items():
            if data["count"] >= min_frequency:
                avg_discount = sum(data["discounts"]) / len(data["discounts"]) if data["discounts"] else None
                avg_min_amount = sum(data["min_amounts"]) / len(data["min_amounts"]) if data["min_amounts"] else None
                success_rate = data["success"] / max(data["total"], 1)
                
                results.append({
                    "pattern": pattern,
                    "platform": plat,
                    "frequency": data["count"],
                    "success_rate": success_rate,
                    "avg_discount": avg_discount,
                    "avg_min_amount": avg_min_amount,
                    "support": data["count"] / max(len(shares), 1)
                })
        
        results.sort(key=lambda x: (x["success_rate"], x["frequency"]), reverse=True)
        return results

    def save_mined_rule(self, pattern: str, platform: str,
                        rule_type: str, support: float, confidence: float,
                        lift: float, frequency: int,
                        min_amount: Optional[float] = None,
                        max_discount: Optional[float] = None,
                        auto_apply: bool = False) -> CouponMinedRule:
        
        existing = self.db.query(CouponMinedRule).filter(
            CouponMinedRule.pattern == pattern,
            CouponMinedRule.platform == platform
        ).first()
        
        if existing:
            existing.frequency += 1
            existing.last_verified = datetime.now()
            existing.support = max(existing.support or 0, support)
            existing.confidence = max(existing.confidence or 0, confidence)
            rule = existing
        else:
            rule = CouponMinedRule(
                platform=platform,
                rule_type=rule_type,
                pattern=pattern,
                regex_pattern=self._pattern_to_regex(pattern),
                support=support,
                confidence=confidence,
                lift=lift,
                min_amount=min_amount,
                max_discount=max_discount,
                frequency=frequency,
                auto_apply=auto_apply
            )
            self.db.add(rule)
        
        self.db.commit()
        self.db.refresh(rule)
        
        return rule

    def _pattern_to_regex(self, pattern: str) -> str:
        regex = pattern
        regex = regex.replace("满", r"满")
        regex = regex.replace("减", r"减")
        regex = regex.replace("(\d+)", r"(\d+(?:\.\d+)?)")
        regex = regex.replace("%", r"%")
        regex = regex.replace("折", r"折")
        return regex

    def get_active_rules(self, platform: Optional[str] = None) -> List[Dict[str, Any]]:
        query = self.db.query(CouponMinedRule).filter(
            CouponMinedRule.is_active == True
        )
        
        if platform:
            query = query.filter(CouponMinedRule.platform == platform)
        
        rules = query.order_by(CouponMinedRule.confidence.desc()).all()
        
        return [
            {
                "id": r.id,
                "platform": r.platform,
                "pattern": r.pattern,
                "regex_pattern": r.regex_pattern,
                "rule_type": r.rule_type,
                "support": r.support,
                "confidence": r.confidence,
                "lift": r.lift,
                "min_amount": float(r.min_amount) if r.min_amount else None,
                "max_discount": float(r.max_discount) if r.max_discount else None,
                "frequency": r.frequency,
                "success_rate": r.success_rate,
                "auto_apply": r.auto_apply,
                "discovered_at": r.discovered_at.isoformat() if r.discovered_at else None
            }
            for r in rules
        ]

    def apply_mined_rules(self, text: str, platform: str,
                          price: float) -> List[Dict[str, Any]]:
        
        active_rules = self.db.query(CouponMinedRule).filter(
            CouponMinedRule.is_active == True,
            (CouponMinedRule.platform == platform) | (CouponMinedRule.platform == "all")
        ).all()
        
        matched = []
        
        for rule in active_rules:
            if not rule.regex_pattern:
                continue
            
            try:
                regex = re.compile(rule.regex_pattern, re.IGNORECASE)
                matches = regex.findall(text)
                
                if matches:
                    applicable = True
                    if rule.min_amount and price < float(rule.min_amount):
                        applicable = False
                    
                    discount_value = None
                    if rule.max_discount:
                        discount_value = float(rule.max_discount)
                    
                    for match in matches:
                        if isinstance(match, tuple):
                            for m in match:
                                if m.replace('.', '').isdigit():
                                    value = float(m)
                                    if rule.rule_type == "fixed_discount":
                                        if value <= 10:
                                            discount_value = price * (1 - value / 10)
                                        else:
                                            discount_value = value
                                    else:
                                        discount_value = value
                                    break
                        elif match.replace('.', '').isdigit():
                            value = float(match)
                            if rule.rule_type == "fixed_discount":
                                if value <= 10:
                                    discount_value = price * (1 - value / 10)
                                else:
                                    discount_value = value
                            else:
                                discount_value = value
                    
                    if discount_value and rule.max_discount:
                        discount_value = min(discount_value, float(rule.max_discount))
                    
                    matched.append({
                        "rule_id": rule.id,
                        "pattern": rule.pattern,
                        "confidence": rule.confidence,
                        "applicable": applicable,
                        "discount_value": discount_value,
                        "final_price": price - discount_value if discount_value and applicable else price,
                        "savings_percent": (discount_value / price * 100) if discount_value and price > 0 else 0
                    })
            except re.error:
                continue
        
        matched.sort(key=lambda x: (x["applicable"], x["discount_value"] or 0), reverse=True)
        return matched
