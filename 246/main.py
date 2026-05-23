import io
import base64
from typing import Optional, List, Dict
from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from services.audit_service import audit_service
from review.review_manager import review_manager, ReviewStatus
from mq.rabbitmq_client import mq_client
from config import config
from cache.redis_cache import CacheHitSource
from video.video_auditor import video_auditor
from config.rules_config import rules_config
from reports.audit_reports import report_manager, ReportPeriod

app = FastAPI(
    title="多媒体内容审核服务 API v3.0",
    description="基于深度学习的图片/视频内容审核服务，支持色情、暴力、广告、泳装场景检测，动态规则配置，统计报表",
    version="3.0.0"
)

class AuditResponse(BaseModel):
    image_id: str
    risk_level: str
    main_content: str
    secondary_content: str
    confidence: float
    predictions: dict
    cached: bool
    from_similar: bool
    cache_hit_source: str
    is_swimwear_context: bool
    risk_details: dict

class BatchAuditRequest(BaseModel):
    images: List[str]
    callback_url: Optional[str] = None
    enable_cache: bool = True
    use_multi_hash: bool = True

class ReviewUpdateRequest(BaseModel):
    review_id: str
    status: str
    reviewer: str
    notes: Optional[str] = None
    final_decision: Optional[str] = None

class CacheClearRequest(BaseModel):
    image_md5: Optional[str] = None
    clear_all: bool = False

class ThresholdUpdateRequest(BaseModel):
    content_type: str
    high_threshold: Optional[float] = None
    low_threshold: Optional[float] = None

class SensitiveWordsRequest(BaseModel):
    words: List[str]
    category: str = "all"

class VideoAuditResponse(BaseModel):
    video_id: str
    duration: float
    sampled_frames: int
    overall_risk: str
    violation_count: int
    violation_frames: List[Dict]

@app.post("/api/audit/sync")
async def audit_sync(
    file: UploadFile = File(...),
    enable_cache: bool = Form(True),
    enable_review: bool = Form(True),
    use_multi_hash: bool = Form(True)
):
    try:
        image_data = await file.read()
        result = audit_service.audit_image_sync(
            image_data,
            enable_cache=enable_cache,
            enable_review=enable_review,
            use_multi_hash=use_multi_hash
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/audit/sync/base64")
async def audit_sync_base64(
    image: str = Form(...),
    enable_cache: bool = Form(True),
    enable_review: bool = Form(True),
    use_multi_hash: bool = Form(True)
):
    try:
        result = audit_service.audit_base64_sync(
            image,
            enable_cache=enable_cache,
            enable_review=enable_review,
            use_multi_hash=use_multi_hash
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/audit/async")
async def audit_async(
    file: UploadFile = File(...),
    callback_url: Optional[str] = Form(None),
    enable_cache: bool = Form(True),
    use_multi_hash: bool = Form(True)
):
    try:
        image_data = await file.read()
        result = audit_service.audit_image_async(
            image_data,
            callback_url=callback_url,
            enable_cache=enable_cache,
            use_multi_hash=use_multi_hash
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/audit/batch/sync")
async def audit_batch_sync(
    files: List[UploadFile] = File(...),
    enable_cache: bool = Form(True),
    enable_review: bool = Form(True),
    use_multi_hash: bool = Form(True)
):
    try:
        if len(files) > config.MAX_BATCH_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"Batch size exceeds maximum of {config.MAX_BATCH_SIZE}"
            )
        
        images_data = []
        for file in files:
            image_data = await file.read()
            images_data.append(image_data)
        
        results = audit_service.audit_batch_sync(
            images_data,
            enable_cache=enable_cache,
            enable_review=enable_review,
            use_multi_hash=use_multi_hash
        )
        return {"results": results}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/audit/batch/async")
async def audit_batch_async(
    files: List[UploadFile] = File(...),
    callback_url: Optional[str] = Form(None),
    enable_cache: bool = Form(True),
    use_multi_hash: bool = Form(True)
):
    try:
        if len(files) > config.MAX_BATCH_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"Batch size exceeds maximum of {config.MAX_BATCH_SIZE}"
            )
        
        images_data = []
        for file in files:
            image_data = await file.read()
            images_data.append(image_data)
        
        result = audit_service.audit_batch_async(
            images_data,
            callback_url=callback_url,
            enable_cache=enable_cache,
            use_multi_hash=use_multi_hash
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/review/pending")
async def get_pending_reviews(limit: int = 100):
    reviews = review_manager.get_pending_reviews(limit)
    return {"reviews": reviews, "count": len(reviews)}

@app.post("/api/review/update")
async def update_review(request: ReviewUpdateRequest):
    result = review_manager.update_review_status(
        review_id=request.review_id,
        status=request.status,
        reviewer=request.reviewer,
        notes=request.notes,
        final_decision=request.final_decision
    )
    if not result:
        raise HTTPException(status_code=404, detail="Review not found")
    return result

@app.get("/api/review/stats")
async def get_review_stats():
    return review_manager.get_review_stats()

@app.get("/api/stats")
async def get_system_stats():
    return audit_service.get_stats()

@app.get("/api/cache/stats")
async def get_cache_stats():
    return audit_service.cache.get_cache_stats()

@app.post("/api/cache/clear")
async def clear_cache(clear_all: bool = Form(False)):
    try:
        if clear_all:
            deleted_count = audit_service.clear_all_cache()
            return {"status": "success", "deleted_count": deleted_count}
        return {"status": "success", "message": "Specify clear_all=true to clear all cache"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check():
    try:
        cache_ok = True
        try:
            audit_service.cache.client.ping()
        except Exception:
            cache_ok = False
        
        mq_ok = True
        try:
            mq_size = mq_client.get_async_queue_size()
        except Exception:
            mq_ok = False
        
        return {
            "status": "healthy" if cache_ok and mq_ok else "degraded",
            "services": {
                "cache": "ok" if cache_ok else "error",
                "mq": "ok" if mq_ok else "error"
            },
            "queue_sizes": {
                "async_audit": mq_client.get_async_queue_size() if mq_ok else -1,
                "review": mq_client.get_review_queue_size() if mq_ok else -1
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ========== Video Audit APIs ==========
@app.post("/api/video/audit")
async def video_audit(
    file: UploadFile = File(...),
    sample_interval: Optional[float] = Form(1.0),
    min_risk_level: Optional[str] = Form("low_risk"),
    enable_cache: bool = Form(True)
):
    try:
        video_data = await file.read()
        result = video_auditor.audit_video(
            video_data,
            sample_interval=sample_interval,
            min_risk_level=min_risk_level,
            enable_cache=enable_cache
        )
        
        report_manager.record_video_audit(
            result.video_id,
            video_auditor.result_to_dict(result),
            result.process_time
        )
        
        return video_auditor.result_to_dict(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ========== Dynamic Rules Config APIs ==========
@app.get("/api/config/all")
async def get_all_config():
    return rules_config.get_all_config()

@app.get("/api/config/thresholds")
async def get_content_thresholds():
    return {"thresholds": rules_config.get_content_thresholds()}

@app.post("/api/config/thresholds")
async def update_content_threshold(
    content_type: str = Form(...),
    high_threshold: Optional[float] = Form(None),
    low_threshold: Optional[float] = Form(None)
):
    success = rules_config.update_content_threshold(
        content_type=content_type,
        high=high_threshold,
        low=low_threshold
    )
    if success:
        return {"status": "success", "thresholds": rules_config.get_content_thresholds()}
    raise HTTPException(status_code=500, detail="Failed to update thresholds")

@app.get("/api/config/sensitive-words")
async def get_sensitive_words(category: str = "all"):
    words = rules_config.get_sensitive_words(category)
    return {"category": category, "words": words, "count": len(words)}

@app.post("/api/config/sensitive-words")
async def set_sensitive_words(request: SensitiveWordsRequest):
    success = rules_config.set_sensitive_words(request.words, request.category)
    if success:
        return {"status": "success", "count": len(request.words)}
    raise HTTPException(status_code=500, detail="Failed to set sensitive words")

@app.post("/api/config/sensitive-words/add")
async def add_sensitive_word(word: str = Form(...), category: str = Form("all")):
    success = rules_config.add_sensitive_word(word, category)
    if success:
        return {"status": "success", "word": word}
    raise HTTPException(status_code=500, detail="Failed to add sensitive word")

@app.post("/api/config/sensitive-words/remove")
async def remove_sensitive_word(word: str = Form(...), category: str = Form("all")):
    success = rules_config.remove_sensitive_word(word, category)
    if success:
        return {"status": "success", "word": word}
    raise HTTPException(status_code=500, detail="Failed to remove sensitive word")

@app.post("/api/config/sensitive-words/check")
async def check_sensitive_content(text: str = Form(...)):
    return rules_config.check_sensitive_content(text)

@app.get("/api/config/review-rules")
async def get_review_rules():
    return {"rules": rules_config.get_review_rules()}

@app.post("/api/config/review-rules")
async def set_review_rules(rules: Dict = Body(...)):
    success = rules_config.set_review_rules(rules)
    if success:
        return {"status": "success", "rules": rules_config.get_review_rules()}
    raise HTTPException(status_code=500, detail="Failed to set review rules")

@app.get("/api/config/video-settings")
async def get_video_settings():
    return {"settings": rules_config.get_video_settings()}

@app.post("/api/config/video-settings")
async def set_video_settings(settings: Dict = Body(...)):
    success = rules_config.set_video_settings(settings)
    if success:
        return {"status": "success", "settings": rules_config.get_video_settings()}
    raise HTTPException(status_code=500, detail="Failed to set video settings")

@app.post("/api/config/reset")
async def reset_config():
    success = rules_config.reset_to_default()
    if success:
        return {"status": "success", "message": "Config reset to default"}
    raise HTTPException(status_code=500, detail="Failed to reset config")

# ========== Report APIs ==========
@app.get("/api/reports/content-distribution")
async def get_content_distribution(
    period: str = ReportPeriod.DAILY,
    date: Optional[str] = None
):
    from datetime import datetime
    dt = datetime.strptime(date, "%Y-%m-%d") if date else None
    return report_manager.get_content_distribution(period, dt)

@app.get("/api/reports/risk-distribution")
async def get_risk_distribution(
    period: str = ReportPeriod.DAILY,
    date: Optional[str] = None
):
    from datetime import datetime
    dt = datetime.strptime(date, "%Y-%m-%d") if date else None
    return report_manager.get_risk_distribution(period, dt)

@app.get("/api/reports/performance")
async def get_audit_performance(
    period: str = ReportPeriod.DAILY,
    date: Optional[str] = None
):
    from datetime import datetime
    dt = datetime.strptime(date, "%Y-%m-%d") if date else None
    return report_manager.get_audit_performance(period, dt)

@app.get("/api/reports/review-consistency")
async def get_review_consistency(
    period: str = ReportPeriod.DAILY,
    date: Optional[str] = None
):
    from datetime import datetime
    dt = datetime.strptime(date, "%Y-%m-%d") if date else None
    return report_manager.get_review_consistency(period, dt)

@app.get("/api/reports/comprehensive")
async def get_comprehensive_report(
    period: str = ReportPeriod.DAILY,
    date: Optional[str] = None
):
    from datetime import datetime
    dt = datetime.strptime(date, "%Y-%m-%d") if date else None
    return report_manager.get_comprehensive_report(period, dt)

@app.get("/api/reports/trend")
async def get_trend_data(days: int = 7):
    return report_manager.get_trend_data(days)

@app.get("/api/reports/top-violations")
async def get_top_violations(
    limit: int = 10,
    period: str = ReportPeriod.DAILY
):
    return {"violations": report_manager.get_top_violations(limit, period)}

@app.post("/api/reports/record-review")
async def record_review(
    review_id: str = Form(...),
    image_id: str = Form(...),
    original_risk: str = Form(...),
    final_risk: str = Form(...),
    reviewer: str = Form(...)
):
    report_manager.record_review(
        review_id=review_id,
        image_id=image_id,
        original_result={"risk_level": original_risk},
        final_result={"risk_level": final_risk},
        reviewer=reviewer
    )
    return {"status": "success"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
