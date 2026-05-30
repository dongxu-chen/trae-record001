import logging
from datetime import datetime
from typing import List, Optional, Dict
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

from config import settings
from schemas import (
    ReviewItem,
    BatchReviewRequest,
    ReviewQualityResult,
    BatchReviewResponse,
    ReputationEventRequest,
    UserProfile,
    ReputationEventType,
    VoteRecord,
    GangDetectionRequest,
    GangDetectionResult,
    AdoptionAnalysisResult,
    MerchantReplyImpact
)
from modules import (
    AuthenticityAnalyzer,
    UserReputationModel,
    RuleEngine,
    ScoringEngine,
    GangDetector,
    AdoptionAnalyzer,
    MerchantReplyAnalyzer
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

scoring_engine: Optional[ScoringEngine] = None
user_profiles_store: Dict[str, UserProfile] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    global scoring_engine

    logger.info("Initializing review quality scoring system v3.0...")

    try:
        authenticity_analyzer = AuthenticityAnalyzer()
        user_reputation_model = UserReputationModel()
        rule_engine = RuleEngine()
        gang_detector = GangDetector()
        adoption_analyzer = AdoptionAnalyzer()
        merchant_reply_analyzer = MerchantReplyAnalyzer()

        scoring_engine = ScoringEngine(
            authenticity_analyzer=authenticity_analyzer,
            user_reputation_model=user_reputation_model,
            rule_engine=rule_engine,
            gang_detector=gang_detector,
            adoption_analyzer=adoption_analyzer,
            merchant_reply_analyzer=merchant_reply_analyzer
        )

        logger.info("All components initialized successfully (v3.0)")
    except Exception as e:
        logger.error(f"Failed to initialize components: {e}")
        raise

    yield

    logger.info("Shutting down review quality scoring system...")
    scoring_engine = None


app = FastAPI(
    title="电商评论质量评分系统",
    description="基于BERT、用户信誉模型、规则引擎的电商评论质量分析系统 - 含团伙检测、采纳度分析、商家回复评估",
    version="3.0.0",
    lifespan=lifespan
)


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "3.0.0",
        "timestamp": datetime.now().isoformat(),
        "bert_enabled": scoring_engine.authenticity_analyzer.model is not None if scoring_engine else False,
        "features": [
            "authenticity_analysis",
            "purchase_verification",
            "user_reputation",
            "gang_detection",
            "adoption_analysis",
            "merchant_reply_impact"
        ]
    }


@app.get("/config")
async def get_config():
    return {
        "weights": {
            "authenticity": settings.AUTHENTICITY_WEIGHT,
            "usefulness": settings.USEFULNESS_WEIGHT,
            "completeness": settings.COMPLETENESS_WEIGHT,
            "user_reputation": settings.REPUTATION_WEIGHT
        },
        "thresholds": {
            "low_quality": settings.LOW_QUALITY_THRESHOLD,
            "collapse": settings.COLLAPSE_THRESHOLD
        },
        "purchase_verification": {
            "no_purchase_penalty": settings.NO_PURCHASE_PENALTY,
            "unverified_penalty": settings.UNVERIFIED_PURCHASE_PENALTY,
            "too_fast_penalty": settings.PURCHASE_REVIEW_TOO_FAST_PENALTY,
            "return_penalty": settings.RETURN_AFTER_REVIEW_PENALTY
        },
        "time_sorting": {
            "recency_boost_window_days": settings.RECENCY_BOOST_WINDOW_DAYS,
            "recency_boost_factor": settings.RECENCY_BOOST_FACTOR,
            "decay_half_life_days": settings.TIME_DECAY_HALF_LIFE_DAYS
        },
        "gang_detection": {
            "min_members": settings.GANG_MIN_MEMBERS,
            "mutual_vote_threshold": settings.GANG_MUTUAL_VOTE_THRESHOLD,
            "suspicious_threshold": settings.GANG_SUSPICIOUS_SCORE_THRESHOLD
        },
        "adoption": {
            "purchase_influence_weight": settings.ADOPTION_PURCHASE_INFLUENCE_WEIGHT,
            "engagement_weight": settings.ADOPTION_ENGAGEMENT_WEIGHT,
            "decision_weight": settings.ADOPTION_DECISION_WEIGHT,
            "top_k": settings.ADOPTION_TOP_K
        },
        "merchant_reply": {
            "trust_boost": settings.MERCHANT_REPLY_TRUST_BOOST,
            "solution_bonus": settings.MERCHANT_REPLY_SOLUTION_BONUS,
            "quality_delta_max": settings.MERCHANT_REPLY_QUALITY_DELTA_MAX
        }
    }


@app.post("/score", response_model=ReviewQualityResult)
async def score_single_review(review: ReviewItem):
    if scoring_engine is None:
        raise HTTPException(status_code=503, detail="Service not initialized")

    try:
        result = scoring_engine.score_review(review)
        return result
    except Exception as e:
        logger.error(f"Error scoring review: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/batch/score", response_model=BatchReviewResponse)
async def score_batch_reviews(request: BatchReviewRequest):
    if scoring_engine is None:
        raise HTTPException(status_code=503, detail="Service not initialized")

    if not request.reviews:
        raise HTTPException(status_code=400, detail="No reviews provided")

    if len(request.reviews) > 1000:
        raise HTTPException(
            status_code=400,
            detail=f"Batch size exceeds limit of 1000, got {len(request.reviews)}"
        )

    try:
        vote_records = request.vote_records or []
        results, total_processed, low_quality_count, collapsed_count, gang_detections, top_adopted = (
            scoring_engine.score_batch(request.reviews, vote_records)
        )

        return BatchReviewResponse(
            results=results,
            total_processed=total_processed,
            low_quality_count=low_quality_count,
            collapsed_count=collapsed_count,
            gang_detections=gang_detections,
            top_adopted_reviews=top_adopted
        )
    except Exception as e:
        logger.error(f"Error scoring batch reviews: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/batch/sort", response_model=List[ReviewQualityResult])
async def sort_reviews(
    request: BatchReviewRequest,
    collapse_low_quality: bool = Query(True, description="是否折叠低质量评论")
):
    if scoring_engine is None:
        raise HTTPException(status_code=503, detail="Service not initialized")

    try:
        vote_records = request.vote_records or []
        results, _, _, _, _, _ = scoring_engine.score_batch(request.reviews, vote_records)
        sorted_results = scoring_engine.sort_reviews(
            results,
            collapse_low_quality=collapse_low_quality
        )
        return sorted_results
    except Exception as e:
        logger.error(f"Error sorting reviews: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/gang/detect", response_model=List[GangDetectionResult])
async def detect_gangs(request: GangDetectionRequest):
    if scoring_engine is None:
        raise HTTPException(status_code=503, detail="Service not initialized")

    try:
        results = scoring_engine.gang_detector.detect_gangs(
            request.reviews, request.vote_records
        )
        return results
    except Exception as e:
        logger.error(f"Error detecting gangs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/adoption/analyze", response_model=List[AdoptionAnalysisResult])
async def analyze_adoption(request: BatchReviewRequest):
    if scoring_engine is None:
        raise HTTPException(status_code=503, detail="Service not initialized")

    try:
        results = scoring_engine.adoption_analyzer.rank_by_adoption(
            request.reviews, request.interactions
        )
        return results
    except Exception as e:
        logger.error(f"Error analyzing adoption: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/merchant-reply/analyze", response_model=MerchantReplyImpact)
async def analyze_merchant_reply(review: ReviewItem):
    if scoring_engine is None:
        raise HTTPException(status_code=503, detail="Service not initialized")

    try:
        impact = scoring_engine.merchant_reply_analyzer.analyze_reply_impact(review)
        return impact
    except Exception as e:
        logger.error(f"Error analyzing merchant reply: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/reputation/event")
async def submit_reputation_event(request: ReputationEventRequest):
    if scoring_engine is None:
        raise HTTPException(status_code=503, detail="Service not initialized")

    try:
        profile = user_profiles_store.get(request.user_id)

        if profile is None:
            raise HTTPException(
                status_code=404,
                detail=f"User profile not found for user_id: {request.user_id}"
            )

        new_score, warnings, updated_profile = scoring_engine.user_reputation_model.process_event(
            user_id=request.user_id,
            event=request.event,
            current_profile=profile
        )

        user_profiles_store[request.user_id] = updated_profile

        event_type_str = request.event.event_type.value if isinstance(request.event.event_type, ReputationEventType) else request.event.event_type

        return {
            "user_id": request.user_id,
            "event_type": event_type_str,
            "event_time": request.event.event_time.isoformat(),
            "previous_score": profile.current_reputation_score,
            "new_score": new_score,
            "score_change": round(new_score - (profile.current_reputation_score or 50.0), 2),
            "warnings": warnings,
            "is_malicious": event_type_str in [
                "fake_review_detected",
                "brush_order_reported",
                "malicious_review_reported",
                "gang_member_detected"
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing reputation event: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/reputation/register")
async def register_user_profile(profile: UserProfile):
    user_profiles_store[profile.user_id] = profile

    if scoring_engine is not None:
        score, warnings = scoring_engine.user_reputation_model.calculate_reputation(profile)
        profile.current_reputation_score = score

    return {
        "user_id": profile.user_id,
        "reputation_score": profile.current_reputation_score,
        "registered": True
    }


@app.get("/reputation/{user_id}")
async def get_user_reputation(user_id: str):
    if scoring_engine is None:
        raise HTTPException(status_code=503, detail="Service not initialized")

    profile = user_profiles_store.get(user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail=f"User not found: {user_id}")

    score, warnings = scoring_engine.user_reputation_model.calculate_reputation(profile)
    history = scoring_engine.user_reputation_model.get_reputation_history(profile)

    return {
        "user_id": user_id,
        "current_reputation_score": score,
        "warnings": warnings,
        "event_count": len(profile.reputation_events),
        "recent_events": [
            {
                "event_type": e.event_type.value if isinstance(e.event_type, ReputationEventType) else e.event_type,
                "event_time": e.event_time.isoformat(),
                "severity": e.severity
            }
            for e in sorted(profile.reputation_events, key=lambda x: x.event_time, reverse=True)[:5]
        ],
        "reputation_history": history
    }


@app.get("/stats")
async def get_stats():
    return {
        "version": "3.0.0",
        "model_name": settings.BERT_MODEL_NAME,
        "max_seq_length": settings.MAX_SEQ_LENGTH,
        "device": settings.DEVICE,
        "suspicious_keywords_count": len(settings.SUSPICIOUS_KEYWORDS),
        "useful_keywords_count": len(settings.USEFUL_KEYWORDS),
        "incomplete_patterns_count": len(settings.INCOMPLETE_PATTERNS),
        "registered_users": len(user_profiles_store),
        "reputation_event_types": list(settings.REPUTATION_EVENT_WEIGHTS.keys()),
        "gang_config": {
            "min_members": settings.GANG_MIN_MEMBERS,
            "mutual_vote_threshold": settings.GANG_MUTUAL_VOTE_THRESHOLD,
            "suspicious_threshold": settings.GANG_SUSPICIOUS_SCORE_THRESHOLD
        },
        "adoption_config": {
            "top_k": settings.ADOPTION_TOP_K,
            "weights": {
                "purchase_influence": settings.ADOPTION_PURCHASE_INFLUENCE_WEIGHT,
                "engagement": settings.ADOPTION_ENGAGEMENT_WEIGHT,
                "decision": settings.ADOPTION_DECISION_WEIGHT
            }
        }
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "message": str(exc)
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
