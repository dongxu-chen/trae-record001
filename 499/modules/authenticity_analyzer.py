import re
import numpy as np
from typing import Tuple, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

HAS_BERT = False
try:
    import torch
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    HAS_BERT = True
except (ImportError, OSError, Exception) as e:
    logger.warning(f"BERT dependencies not available: {e}. BERT features will be disabled, using rule-based fallback.")
    HAS_BERT = False

from config import settings
from schemas import (
    ReviewItem,
    PurchaseBehavior,
    PurchaseVerificationStatus,
    PurchaseVerificationDetail
)


class AuthenticityAnalyzer:
    def __init__(self):
        self.device = settings.DEVICE
        self.model = None
        self.tokenizer = None
        self._load_model()

    def _load_model(self):
        if not HAS_BERT:
            logger.info("BERT model not available, using rule-based fallback")
            return

        try:
            model_name = settings.BERT_MODEL_NAME
            logger.info(f"Loading BERT model: {model_name}")

            self.tokenizer = AutoTokenizer.from_pretrained(
                model_name,
                model_max_length=settings.MAX_SEQ_LENGTH
            )

            self.model = AutoModelForSequenceClassification.from_pretrained(
                model_name,
                num_labels=2
            )

            self.model.to(self.device)
            self.model.eval()

            logger.info("BERT model loaded successfully")
        except Exception as e:
            logger.warning(f"Failed to load BERT model: {e}, using rule-based fallback")
            self.model = None
            self.tokenizer = None

    def _bert_predict(self, text: str) -> float:
        if self.model is None or self.tokenizer is None:
            return 50.0

        try:
            inputs = self.tokenizer(
                text,
                padding=True,
                truncation=True,
                max_length=settings.MAX_SEQ_LENGTH,
                return_tensors="pt"
            ).to(self.device)

            with torch.no_grad():
                outputs = self.model(**inputs)
                probabilities = torch.softmax(outputs.logits, dim=1)
                authentic_prob = probabilities[0][1].item()

            return authentic_prob * 100.0
        except Exception as e:
            logger.warning(f"BERT prediction failed: {e}")
            return 50.0

    def _check_suspicious_patterns(self, text: str) -> Tuple[float, List[str]]:
        warnings = []
        score = 100.0
        text_lower = text.lower()

        for keyword in settings.SUSPICIOUS_KEYWORDS:
            if keyword in text_lower:
                penalty = 15.0
                score -= penalty
                warnings.append(f"包含可疑关键词: '{keyword}'")

        if re.search(r"[^\w\s]", text) and len(re.findall(r"[^\w\s]", text)) / max(len(text), 1) > 0.3:
            score -= 20.0
            warnings.append("特殊符号比例过高")

        if len(set(text)) < max(5, len(text) * 0.1):
            score -= 25.0
            warnings.append("字符重复度过高，可能是刷评内容")

        if len(text) < 10 and any(kw in text_lower for kw in ["好", "不错", "棒"]):
            score -= 15.0
            warnings.append("短评且全为正面词汇，真实性存疑")

        repeated_pattern = re.search(r"(.{3,}?)\1{2,}", text)
        if repeated_pattern:
            score -= 20.0
            warnings.append(f"存在重复内容模式: '{repeated_pattern.group(1)[:20]}...'")

        emotion_words = re.findall(r"[太超很最非][棒好优秀完美赞]", text_lower)
        if len(emotion_words) > 5:
            score -= min(len(emotion_words) * 3, 15)
            warnings.append(f"过度使用极端情感词汇 ({len(emotion_words)}次)")

        return max(0.0, score), warnings

    def _check_metadata_trust(self, review: ReviewItem) -> Tuple[float, List[str]]:
        score = 100.0
        warnings = []

        if not review.is_verified_purchase:
            score -= 20.0
            warnings.append("非已验证购买")

        if review.rating == 5 and len(review.content) < 20:
            score -= 15.0
            warnings.append("五星短评，可能为默认好评")

        if review.rating in [1, 5] and review.helpful_votes == 0:
            score -= 5.0

        if not review.has_images and not review.has_videos and len(review.content) < 30:
            score -= 10.0

        return max(0.0, score), warnings

    def verify_purchase_behavior(self, review: ReviewItem) -> PurchaseVerificationDetail:
        warnings = []
        score = 100.0
        penalty = 0.0
        behavior = review.purchase_behavior

        if behavior is None:
            if review.is_verified_purchase:
                status = PurchaseVerificationStatus.VERIFIED_PURCHASE
                score = 90.0
            else:
                status = PurchaseVerificationStatus.NO_PURCHASE_RECORD
                penalty = settings.NO_PURCHASE_PENALTY
                score -= penalty
                warnings.append("未提供购买行为数据且非已验证购买，评论将被大幅降权")
        else:
            if not behavior.has_purchased:
                status = PurchaseVerificationStatus.NO_PURCHASE_RECORD
                penalty = settings.NO_PURCHASE_PENALTY
                score -= penalty
                warnings.append("用户未购买该商品，评论真实性存疑，大幅降权")
            elif not behavior.purchase_verified:
                status = PurchaseVerificationStatus.UNVERIFIED_PURCHASE
                penalty = settings.UNVERIFIED_PURCHASE_PENALTY
                score -= penalty
                warnings.append("购买记录未验证，评论适度降权")
            else:
                status = PurchaseVerificationStatus.VERIFIED_PURCHASE
                score = 100.0

            if behavior.has_purchased and behavior.purchase_time and behavior.review_after_purchase:
                if behavior.days_between_purchase_and_review is not None:
                    if behavior.days_between_purchase_and_review < settings.PURCHASE_REVIEW_TOO_FAST_DAYS:
                        fast_penalty = settings.PURCHASE_REVIEW_TOO_FAST_PENALTY
                        penalty += fast_penalty
                        score -= fast_penalty
                        warnings.append(
                            f"购买后{behavior.days_between_purchase_and_review:.1f}天内即评论，"
                            f"可能未充分体验商品，适度降权"
                        )

            if behavior.return_requested and not behavior.return_completed:
                return_penalty = settings.RETURN_AFTER_REVIEW_PENALTY
                penalty += return_penalty
                score -= return_penalty
                warnings.append("评论后发起退货，评价动机可疑，降权处理")

        score = max(0.0, min(100.0, score))

        return PurchaseVerificationDetail(
            verification_status=status,
            purchase_score=score,
            penalty_applied=penalty,
            warnings=warnings
        )

    def analyze(self, review: ReviewItem) -> Tuple[float, List[str], PurchaseVerificationDetail]:
        text = review.content.strip()

        if len(text) < settings.MIN_REVIEW_LENGTH:
            purchase_detail = self.verify_purchase_behavior(review)
            return 0.0, ["评论内容过短"], purchase_detail

        bert_score = self._bert_predict(text)

        pattern_score, pattern_warnings = self._check_suspicious_patterns(text)

        metadata_score, metadata_warnings = self._check_metadata_trust(review)

        purchase_detail = self.verify_purchase_behavior(review)

        purchase_weight = 0.0
        if purchase_detail.verification_status == PurchaseVerificationStatus.NO_PURCHASE_RECORD:
            purchase_weight = 0.25
        elif purchase_detail.verification_status == PurchaseVerificationStatus.UNVERIFIED_PURCHASE:
            purchase_weight = 0.15
        elif purchase_detail.verification_status == PurchaseVerificationStatus.VERIFIED_PURCHASE:
            purchase_weight = 0.0

        remaining_weight = 1.0 - purchase_weight
        bert_weight = remaining_weight * 0.4
        pattern_weight = remaining_weight * 0.35
        metadata_weight = remaining_weight * 0.25

        if purchase_weight > 0:
            combined_score = (
                bert_score * bert_weight +
                pattern_score * pattern_weight +
                metadata_score * metadata_weight +
                purchase_detail.purchase_score * purchase_weight
            )
        else:
            combined_score = (
                bert_score * 0.4 +
                pattern_score * 0.35 +
                metadata_score * 0.25
            )

        warnings = pattern_warnings + metadata_warnings + purchase_detail.warnings

        return round(min(100.0, max(0.0, combined_score)), 2), warnings, purchase_detail
