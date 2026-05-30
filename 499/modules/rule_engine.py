import re
import math
from typing import Tuple, List
import logging

logger = logging.getLogger(__name__)

try:
    import jieba
    HAS_JIEBA = True
except ImportError:
    HAS_JIEBA = False
    logger.warning("Jieba not installed, using simple tokenization")

from config import settings
from schemas import ReviewItem


class RuleEngine:
    def __init__(self):
        self._init_patterns()

    def _init_patterns(self):
        self.incomplete_regexes = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in settings.INCOMPLETE_PATTERNS
        ]

    def _tokenize(self, text: str) -> List[str]:
        if HAS_JIEBA:
            return list(jieba.cut(text))
        else:
            return list(text)

    def analyze_usefulness(self, review: ReviewItem) -> Tuple[float, List[str]]:
        text = review.content.strip()
        warnings = []
        score = 0.0

        length = len(text)
        if length >= 200:
            length_score = 100.0
        elif length >= 100:
            length_score = 80.0
        elif length >= 50:
            length_score = 60.0
        elif length >= 20:
            length_score = 40.0
        else:
            length_score = 20.0
            warnings.append("评论内容较短")

        tokens = self._tokenize(text)
        useful_word_count = 0
        for kw in settings.USEFUL_KEYWORDS:
            if kw in text:
                useful_word_count += text.count(kw)

        keyword_score = min(useful_word_count * 15, 100.0)
        if useful_word_count == 0:
            warnings.append("缺少具体描述维度")
        elif useful_word_count >= 3:
            pass

        detail_score = 0.0
        if review.has_images:
            detail_score += 30.0
        if review.has_videos:
            detail_score += 20.0

        has_numbers = bool(re.search(r"\d+", text))
        if has_numbers:
            detail_score += 15.0

        has_comparison = any(kw in text for kw in ["比", "对比", "相比", "之前", "以前", "原来"])
        if has_comparison:
            detail_score += 15.0

        has_negative = any(kw in text for kw in ["缺点", "不足", "问题", "不好", "差"])
        has_positive = any(kw in text for kw in ["优点", "不错", "好", "满意"])
        if has_negative and has_positive:
            detail_score += 20.0
            warnings.append("评论包含正反两面评价")

        detail_score = min(detail_score, 100.0)

        helpful_vote_score = min(review.helpful_votes * settings.HELPFUL_VOTE_BOOST * 100, 50.0)

        usefulness_score = (
            length_score * 0.25 +
            keyword_score * 0.30 +
            detail_score * 0.30 +
            helpful_vote_score * 0.15
        )

        return round(min(100.0, max(0.0, usefulness_score)), 2), warnings

    def analyze_completeness(self, review: ReviewItem) -> Tuple[float, List[str]]:
        text = review.content.strip()
        warnings = []

        for pattern in self.incomplete_regexes:
            if pattern.match(text):
                warnings.append("评论内容过于简单，缺乏实质信息")
                return 10.0, warnings

        sentences = re.split(r"[。！？.!?]", text)
        sentences = [s.strip() for s in sentences if s.strip()]
        sentence_count = len(sentences)

        if sentence_count == 0:
            warnings.append("评论无有效内容")
            return 0.0, warnings

        if sentence_count == 1:
            sentence_score = 30.0
            warnings.append("评论仅包含单句")
        elif sentence_count == 2:
            sentence_score = 60.0
        elif sentence_count >= 3:
            sentence_score = 100.0

        tokens = self._tokenize(text)
        unique_tokens = len(set(tokens))
        total_tokens = len(tokens)

        if total_tokens == 0:
            lexical_score = 0.0
        else:
            lexical_diversity = unique_tokens / total_tokens
            lexical_score = min(lexical_diversity * 150, 100.0)

        aspect_count = 0
        aspects = {
            "product": ["质量", "做工", "材质", "尺寸", "大小", "颜色", "外观"],
            "service": ["物流", "快递", "包装", "服务", "售后", "客服"],
            "experience": ["使用", "体验", "效果", "味道", "手感"]
        }

        for aspect, keywords in aspects.items():
            if any(kw in text for kw in keywords):
                aspect_count += 1

        aspect_score = (aspect_count / len(aspects)) * 100.0

        if aspect_count == 0:
            warnings.append("评论未涉及产品、服务或使用体验的具体描述")
        elif aspect_count == 1:
            warnings.append("评论仅涉及单一维度")

        rating_consistency = self._check_rating_consistency(review)

        completeness_score = (
            sentence_score * 0.30 +
            lexical_score * 0.25 +
            aspect_score * 0.30 +
            rating_consistency * 0.15
        )

        return round(min(100.0, max(0.0, completeness_score)), 2), warnings

    def _check_rating_consistency(self, review: ReviewItem) -> float:
        text = review.content
        rating = review.rating

        positive_words = ["好", "不错", "满意", "喜欢", "棒", "优秀", "完美", "赞"]
        negative_words = ["差", "不好", "糟糕", "失望", "问题", "退货", "退款"]

        pos_count = sum(text.count(w) for w in positive_words)
        neg_count = sum(text.count(w) for w in negative_words)

        if pos_count == 0 and neg_count == 0:
            return 70.0

        sentiment_ratio = pos_count / max(pos_count + neg_count, 1)

        expected_sentiment = (rating - 1) / 4.0

        consistency = 1.0 - abs(sentiment_ratio - expected_sentiment)

        if consistency < 0.3:
            return 20.0
        elif consistency < 0.5:
            return 50.0
        elif consistency < 0.7:
            return 75.0
        else:
            return 100.0
