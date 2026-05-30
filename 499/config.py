from pydantic import BaseModel


class Settings(BaseModel):
    BERT_MODEL_NAME: str = "uer/roberta-base-finetuned-dianping-chinese"
    MAX_SEQ_LENGTH: int = 256
    BATCH_SIZE: int = 32
    DEVICE: str = "cpu"

    AUTHENTICITY_WEIGHT: float = 0.35
    USEFULNESS_WEIGHT: float = 0.30
    COMPLETENESS_WEIGHT: float = 0.20
    REPUTATION_WEIGHT: float = 0.15

    LOW_QUALITY_THRESHOLD: float = 40.0
    COLLAPSE_THRESHOLD: float = 30.0

    MIN_REVIEW_LENGTH: int = 5
    MAX_REVIEW_LENGTH: int = 2000

    TIME_DECAY_FACTOR: float = 0.001
    HELPFUL_VOTE_BOOST: float = 0.05

    NO_PURCHASE_PENALTY: float = 35.0
    UNVERIFIED_PURCHASE_PENALTY: float = 15.0
    PURCHASE_REVIEW_TOO_FAST_DAYS: float = 0.5
    PURCHASE_REVIEW_TOO_FAST_PENALTY: float = 10.0
    RETURN_AFTER_REVIEW_PENALTY: float = 20.0

    REPUTATION_EVENT_WEIGHTS: dict = {
        "review_removed": -15.0,
        "fake_review_detected": -25.0,
        "brush_order_reported": -30.0,
        "malicious_review_reported": -20.0,
        "purchase_verified": 5.0,
        "helpful_vote_received": 2.0,
        "review_restored": 10.0,
        "appeal_approved": 8.0,
        "gang_member_detected": -35.0
    }
    REPUTATION_EVENT_DECAY_DAYS: float = 90.0
    REPUTATION_MIN_SCORE: float = 0.0
    REPUTATION_MAX_SCORE: float = 100.0

    RECENCY_BOOST_WINDOW_DAYS: float = 3.0
    RECENCY_BOOST_FACTOR: float = 1.3
    RECENCY_TRANSITION_DAYS: float = 30.0
    RECENCY_LONG_TAIL_FACTOR: float = 0.5
    TIME_DECAY_HALF_LIFE_DAYS: float = 30.0

    GANG_MIN_MEMBERS: int = 2
    GANG_MUTUAL_VOTE_THRESHOLD: int = 3
    GANG_TIME_WINDOW_HOURS: float = 72.0
    GANG_SUSPICIOUS_SCORE_THRESHOLD: float = 60.0
    GANG_RATING_SIMILARITY_THRESHOLD: float = 0.8
    GANG_CONTENT_SIMILARITY_THRESHOLD: float = 0.6
    GANG_SAME_PRODUCT_WEIGHT: float = 1.5
    GANG_ACCOUNT_AGE_NEW_DAYS: int = 30
    GANG_NEW_ACCOUNT_PENALTY: float = 15.0
    GANG_DETECTION_AUTHENTICITY_PENALTY: float = 20.0

    ADOPTION_PURCHASE_INFLUENCE_WEIGHT: float = 0.40
    ADOPTION_ENGAGEMENT_WEIGHT: float = 0.30
    ADOPTION_DECISION_WEIGHT: float = 0.30
    ADOPTION_MIN_VIEWS_FOR_SIGNIFICANCE: int = 10
    ADOPTION_PURCHASE_RATE_EXCELLENT: float = 0.15
    ADOPTION_PURCHASE_RATE_GOOD: float = 0.08
    ADOPTION_PURCHASE_RATE_AVERAGE: float = 0.03
    ADOPTION_TOP_K: int = 10

    MERCHANT_REPLY_TRUST_BOOST: float = 8.0
    MERCHANT_REPLY_SOLUTION_BONUS: float = 12.0
    MERCHANT_REPLY_COMPENSATION_BONUS: float = 5.0
    MERCHANT_REPLY_APOLOGY_BONUS: float = 6.0
    MERCHANT_REPLY_QUALITY_DELTA_MAX: float = 15.0
    MERCHANT_REPLY_NEGATIVE_REVIEW_MULTIPLIER: float = 1.5
    MERCHANT_REPLY_LATE_DAYS_THRESHOLD: float = 7.0
    MERCHANT_REPLY_LATE_PENALTY: float = 3.0

    SUSPICIOUS_KEYWORDS: list = [
        "刷单", "好评返现", "追评有礼", "五分好评", "好评有礼",
        "返现", "优惠券", "红包", "免单", "试用品",
        "太棒了", "非常好", "超级好", "完美", "没得说",
        "copy", "复制", "同上", "和上面一样"
    ]

    USEFUL_KEYWORDS: list = [
        "质量", "做工", "材质", "尺寸", "大小", "颜色",
        "物流", "快递", "包装", "服务", "售后",
        "使用", "体验", "效果", "味道", "手感",
        "推荐", "建议", "注意", "缺点", "优点",
        "对比", "之前", "以前", "第二次", "回购"
    ]

    INCOMPLETE_PATTERNS: list = [
        r"^[好不错差一般]+$",
        r"^[1-5]星?$",
        r"^还可以$",
        r"^还行$",
        r"^不错$",
        r"^一般$",
        r"^凑活$",
        r"^挺好$",
        r"^ok$",
        r"^好的$"
    ]


settings = Settings()
