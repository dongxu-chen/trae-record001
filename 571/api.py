from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from datetime import datetime
import uuid
import os

from config import config
from feature_engineer import FeatureEngineer
from predictor import ResponseTimePredictor
from redis_cache import RedisCache
from timeout_advisor import TimeoutAdvisor
from root_cause_analyzer import RootCauseAnalyzer
from model_updater import ModelUpdater


class PredictionRequest(BaseModel):
    endpoint: str = Field(..., description="API endpoint path")
    http_method: str = Field(default="GET", description="HTTP method")
    user_segment: str = Field(default="regular", description="User segment (new, regular, vip, internal, bot)")
    user_id: str = Field(default="user_0", description="User identifier")
    param_complexity: str = Field(default="simple", description="Parameter complexity (simple, medium, complex)")
    param_count: int = Field(default=2, ge=0, description="Number of parameters")
    payload_size_kb: float = Field(default=5.0, ge=0, description="Payload size in KB")
    is_cached: bool = Field(default=False, description="Whether request is cached")
    server_load: float = Field(default=0.5, ge=0, le=1, description="Current server load")
    request_id: Optional[str] = Field(default=None, description="Optional request ID")
    enable_early_warning: bool = Field(default=True, description="Enable early warning prediction")
    downstream_count: Optional[int] = Field(default=None, description="Number of downstream services")
    downstream_degraded_count: Optional[int] = Field(default=None, description="Number of degraded downstream services")
    downstream_max_latency_ms: Optional[float] = Field(default=None, description="Max downstream latency")
    downstream_total_latency_ms: Optional[float] = Field(default=None, description="Total downstream latency")
    has_downstream_degradation: Optional[bool] = Field(default=None, description="Whether any downstream is degraded")
    has_downstream_outage: Optional[bool] = Field(default=None, description="Whether any downstream is out")
    current_timeout_ms: Optional[float] = Field(default=None, description="Current configured timeout for recommendation")


class PredictionResponse(BaseModel):
    request_id: str
    predicted_response_time_ms: float
    prediction_std_ms: float
    dynamic_threshold_p99_ms: float
    timeout_probability: float
    is_anomaly: bool
    anomaly_score: float
    warning_level: str
    confidence_interval: Dict
    trend_analysis: Optional[Dict]
    future_risk_prediction: Optional[Dict]
    early_warning: Optional[Dict]
    timeout_recommendation: Optional[Dict]
    timestamp: str


class DownstreamServiceStatus(BaseModel):
    service_name: str = Field(..., description="Downstream service name")
    status: str = Field(..., description="Service status: healthy, degraded, outage")
    latency_ms: float = Field(..., ge=0, description="Current latency in ms")
    health_score: float = Field(default=1.0, ge=0, le=1, description="Health score 0-1")


class DeviationAnalysisRequest(BaseModel):
    request_id: str = Field(..., description="Original prediction request ID")
    endpoint: str = Field(..., description="API endpoint path")
    predicted_ms: float = Field(..., ge=0, description="Predicted response time")
    actual_ms: float = Field(..., ge=0, description="Actual response time")
    request_data: Optional[Dict] = Field(default=None, description="Original request data for analysis")


class TimeoutRecommendRequest(BaseModel):
    endpoint: str = Field(..., description="API endpoint path")
    current_timeout_ms: Optional[float] = Field(default=None, description="Current timeout setting")
    target_success_rate: Optional[float] = Field(default=None, ge=0.9, le=1.0, description="Target success rate")


class ModelUpdateRequest(BaseModel):
    force: bool = Field(default=False, description="Force update even if conditions not met")


class EarlyWarningResponse(BaseModel):
    warning_id: str
    endpoint: str
    warning_level: str
    warning_types: List[str]
    urgency: str
    recommended_actions: List[str]
    predicted_response_time_ms: float
    timeout_probability: float
    steps_to_warning: Optional[int]
    timestamp: str


class HistoricalRecord(BaseModel):
    request_id: str
    endpoint: str
    response_time_ms: float
    timestamp: str


class ModelMetrics(BaseModel):
    train: Dict
    test: Dict


app = FastAPI(
    title="API Response Time Predictor",
    description="Predict API response times using XGBoost with feature engineering, Redis caching, auto timeout recommendation, root cause analysis and model auto-update",
    version="2.0.0"
)

feature_engineer = None
predictor = None
redis_cache = None
historical_stats = {}
timeout_advisor = None
root_cause_analyzer = None
model_updater = None


@app.on_event("startup")
async def startup_event():
    global feature_engineer, predictor, redis_cache, historical_stats
    global timeout_advisor, root_cause_analyzer, model_updater
    
    feature_engineer = FeatureEngineer(config=config.FEATURE_ENGINEERING)
    predictor = ResponseTimePredictor(
        params=config.XGB_PARAMS,
        warning_config=config.EARLY_WARNING
    )
    
    redis_cache = RedisCache(
        host=config.REDIS_HOST,
        port=config.REDIS_PORT,
        db=config.REDIS_DB,
        password=config.REDIS_PASSWORD,
        history_window=config.ANOMALY_HISTORY_WINDOW,
        downstream_services=config.DOWNSTREAM_SERVICE_TYPES
    )
    
    timeout_advisor = TimeoutAdvisor(config=config.TIMEOUT_ADVISOR)
    root_cause_analyzer = RootCauseAnalyzer(config=config.ROOT_CAUSE_ANALYZER)
    
    predictor.threshold_percentile = config.DYNAMIC_THRESHOLD_PERCENTILE
    predictor.threshold_safety_margin = config.THRESHOLD_SAFETY_MARGIN
    predictor.min_history_for_threshold = config.MIN_HISTORY_FOR_THRESHOLD
    
    if os.path.exists("./models/feature_engineer.joblib") and os.path.exists("./models/response_time_model.joblib"):
        try:
            feature_engineer = FeatureEngineer.load("./models/feature_engineer.joblib")
            predictor = ResponseTimePredictor.load("./models/response_time_model.joblib")
            print("Loaded pre-trained models")
        except Exception as e:
            print(f"Warning: Could not load models: {e}")
    
    model_updater = ModelUpdater(
        predictor=predictor,
        feature_engineer=feature_engineer,
        redis_cache=redis_cache,
        config=config.MODEL_UPDATER
    )
    
    historical_stats = redis_cache.get_historical_stats()
    if not historical_stats:
        historical_stats = {
            "endpoint_avg": {},
            "endpoint_p95": {},
            "endpoint_p99": {},
            "endpoint_std": {},
            "endpoint_count": {},
            "user_segment_avg": {},
            "global_avg": 200.0,
            "global_p95": 500.0,
            "global_p99": 1000.0,
            "global_std": 100.0,
        }


@app.post("/predict", response_model=PredictionResponse)
async def predict_response_time(request: PredictionRequest):
    if predictor.model is None:
        raise HTTPException(
            status_code=503,
            detail="Model not trained. Please call /train endpoint first."
        )
    
    request_id = request.request_id or str(uuid.uuid4())
    
    endpoint_stats = redis_cache.get_endpoint_stats(request.endpoint)
    rolling_stats = redis_cache.get_rolling_stats(
        request.endpoint,
        window=config.FEATURE_ENGINEERING["rolling_window_size"]
    )
    user_request_count = redis_cache.increment_user_request_count(request.user_id)
    
    downstream_status = redis_cache.get_downstream_status_for_endpoint(
        request.endpoint,
        config.DOWNSTREAM_SERVICES
    )
    
    request_data = request.dict()
    
    if request.downstream_count is None:
        request_data["downstream_count"] = downstream_status["downstream_count"]
    if request.downstream_degraded_count is None:
        request_data["downstream_degraded_count"] = downstream_status["downstream_degraded_count"]
    if request.downstream_max_latency_ms is None:
        request_data["downstream_max_latency_ms"] = downstream_status["downstream_max_latency_ms"]
    if request.downstream_total_latency_ms is None:
        request_data["downstream_total_latency_ms"] = downstream_status["downstream_total_latency_ms"]
    if request.has_downstream_degradation is None:
        request_data["has_downstream_degradation"] = downstream_status["has_downstream_degradation"]
    if request.has_downstream_outage is None:
        request_data["has_downstream_outage"] = downstream_status["has_downstream_outage"]
    
    request_data.update({
        "rolling_mean": rolling_stats["rolling_mean"],
        "rolling_std": rolling_stats["rolling_std"],
        "ema": rolling_stats["ema"],
        "user_request_count": user_request_count,
    })
    
    features = feature_engineer.transform_single(request_data, historical_stats)
    X = features.select_dtypes(include=["number"]).fillna(0)
    
    result = predictor.predict_single(
        X, 
        historical_stats, 
        request.endpoint,
        enable_early_warning=request.enable_early_warning
    )
    result["request_id"] = request_id
    
    recent_actuals = redis_cache.get_endpoint_history(request.endpoint, limit=50)
    recent_times = [h["response_time_ms"] for h in recent_actuals] if recent_actuals else []
    
    timeout_rec = timeout_advisor.recommend_timeout(
        predicted_ms=result["predicted_response_time_ms"],
        predicted_std_ms=result["prediction_std_ms"],
        historical_stats=historical_stats,
        endpoint=request.endpoint,
        current_timeout_ms=request.current_timeout_ms,
        recent_actual_times=recent_times
    )
    result["timeout_recommendation"] = timeout_rec
    redis_cache.store_timeout_recommendation(request.endpoint, timeout_rec)
    
    redis_cache.store_prediction(request_id, result)
    redis_cache.append_prediction_history(request.endpoint, result["predicted_response_time_ms"])
    
    if result.get("early_warning") and result["early_warning"]["warning_level"] != "normal":
        warning_data = {
            "warning_id": str(uuid.uuid4()),
            "endpoint": request.endpoint,
            "warning_level": result["early_warning"]["warning_level"],
            "warning_types": result["early_warning"]["warning_types"],
            "urgency": result["early_warning"]["urgency"],
            "recommended_actions": result["early_warning"]["recommended_actions"],
            "predicted_response_time_ms": result["predicted_response_time_ms"],
            "timeout_probability": result["timeout_probability"],
            "steps_to_warning": result.get("future_risk_prediction", {}).get("steps_to_warning"),
            "timestamp": result["timestamp"]
        }
        redis_cache.store_warning(warning_data)
    
    return result


@app.post("/record")
async def record_actual_response(
    request_id: str,
    endpoint: str,
    response_time_ms: float,
    request_data: Optional[Dict] = None
):
    record_data = {
        "request_id": request_id,
        "endpoint": endpoint,
        "response_time_ms": response_time_ms,
        "timestamp": datetime.now().isoformat()
    }
    
    redis_cache.store_request(request_data or {"endpoint": endpoint}, response_time_ms)
    
    if model_updater:
        model_updater.add_data_point(
            request_data or {"endpoint": endpoint},
            response_time_ms
        )
    
    return {"status": "success", "recorded": record_data}


@app.get("/stats/{endpoint}")
async def get_endpoint_statistics(endpoint: str):
    stats = redis_cache.get_endpoint_stats(endpoint)
    return {
        "endpoint": endpoint,
        "statistics": stats,
        "historical_baseline": {
            "avg": historical_stats["endpoint_avg"].get(endpoint, historical_stats["global_avg"]),
            "p95": historical_stats["endpoint_p95"].get(endpoint, historical_stats["global_p95"])
        }
    }


@app.get("/metrics")
async def get_model_metrics():
    if not predictor.training_metrics:
        raise HTTPException(
            status_code=404,
            detail="No training metrics available. Train the model first."
        )
    
    return {
        "metrics": predictor.training_metrics,
        "feature_importance": predictor.get_feature_importance()
    }


@app.post("/train")
async def train_model(data_path: str = "./data/api_requests.csv"):
    from data_generator import DataGenerator
    import pandas as pd
    
    if os.path.exists(data_path):
        df = pd.read_csv(data_path, parse_dates=["timestamp"])
    else:
        generator = DataGenerator()
        df = generator.generate_data(num_samples=20000)
        generator.save_data(df, data_path)
    
    df_features = feature_engineer.fit_transform(df, fit_encoders=True)
    X, y = feature_engineer.prepare_for_training(df_features)
    
    metrics = predictor.train(X, y)
    
    global historical_stats
    historical_stats = feature_engineer.get_historical_stats(df)
    historical_stats["endpoint_std"] = df.groupby("endpoint")["response_time_ms"].std().to_dict()
    
    redis_cache.update_historical_stats(historical_stats)
    
    feature_engineer.save("./models/feature_engineer.joblib")
    predictor.save("./models/response_time_model.joblib")
    
    return {
        "status": "success",
        "training_samples": len(df),
        "metrics": metrics,
        "message": "Model trained and saved successfully"
    }


@app.get("/health")
async def health_check():
    redis_status = redis_cache.is_connected() if redis_cache else False
    
    return {
        "status": "healthy",
        "model_loaded": predictor.model is not None,
        "redis_connected": redis_status,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/batch-predict")
async def batch_predict(
    endpoints: List[str],
    http_method: str = "GET",
    user_segment: str = "regular"
):
    if predictor.model is None:
        raise HTTPException(
            status_code=503,
            detail="Model not trained. Please call /train endpoint first."
        )
    
    results = []
    for endpoint in endpoints:
        request = PredictionRequest(
            endpoint=endpoint,
            http_method=http_method,
            user_segment=user_segment
        )
        result = await predict_response_time(request)
        results.append(result)
    
    return {"predictions": results}


@app.post("/downstream/status")
async def update_downstream_status(status: DownstreamServiceStatus):
    redis_cache.update_downstream_service_status(
        service_name=status.service_name,
        status=status.status,
        latency_ms=status.latency_ms,
        health_score=status.health_score
    )
    return {"status": "success", "message": f"Updated status for {status.service_name}"}


@app.get("/downstream/status")
async def get_all_downstream_statuses():
    statuses = redis_cache.get_all_downstream_statuses()
    return {"downstream_services": statuses}


@app.get("/downstream/status/{service_name}")
async def get_downstream_service_status(service_name: str):
    status = redis_cache.get_downstream_service_status(service_name)
    if not status:
        raise HTTPException(
            status_code=404,
            detail=f"Downstream service {service_name} not found"
        )
    return status


@app.get("/downstream/endpoint/{endpoint}")
async def get_endpoint_downstream_status(endpoint: str):
    status = redis_cache.get_downstream_status_for_endpoint(
        endpoint,
        config.DOWNSTREAM_SERVICES
    )
    return {"endpoint": endpoint, "downstream_status": status}


@app.get("/warnings")
async def get_recent_warnings(limit: int = 20):
    warnings = redis_cache.get_recent_warnings(limit=limit)
    return {"warnings": warnings, "count": len(warnings)}


@app.get("/warnings/{endpoint}")
async def get_endpoint_warnings(endpoint: str, limit: int = 10):
    warnings = redis_cache.get_endpoint_warnings(endpoint, limit=limit)
    return {"endpoint": endpoint, "warnings": warnings, "count": len(warnings)}


@app.get("/thresholds")
async def get_dynamic_thresholds():
    thresholds = {}
    for endpoint in historical_stats.get("endpoint_p99", {}).keys():
        threshold = predictor.calculate_dynamic_threshold(endpoint, historical_stats)
        thresholds[endpoint] = {
            "p99_ms": historical_stats["endpoint_p99"].get(endpoint, 0),
            "dynamic_threshold_ms": threshold,
            "safety_margin": config.THRESHOLD_SAFETY_MARGIN,
            "sample_count": historical_stats.get("endpoint_count", {}).get(endpoint, 0)
        }
    
    thresholds["global"] = {
        "p99_ms": historical_stats.get("global_p99", 0),
        "dynamic_threshold_ms": historical_stats.get("global_p99", 0) * config.THRESHOLD_SAFETY_MARGIN,
        "safety_margin": config.THRESHOLD_SAFETY_MARGIN
    }
    
    return {"thresholds": thresholds, "percentile": config.DYNAMIC_THRESHOLD_PERCENTILE}


@app.get("/prediction-history/{endpoint}")
async def get_prediction_history(endpoint: str, limit: int = 10):
    history = redis_cache.get_prediction_history(endpoint, limit=limit)
    return {"endpoint": endpoint, "prediction_history": history}


@app.post("/timeout/recommend")
async def recommend_timeout(request: TimeoutRecommendRequest):
    endpoint_stats = redis_cache.get_endpoint_stats(request.endpoint)
    recent_history = redis_cache.get_endpoint_history(request.endpoint, limit=50)
    recent_times = [h["response_time_ms"] for h in recent_history] if recent_history else []
    
    endpoint_avg = historical_stats.get("endpoint_avg", {}).get(request.endpoint, 500)
    endpoint_std = historical_stats.get("endpoint_std", {}).get(request.endpoint, 100)
    
    recommendation = timeout_advisor.recommend_timeout(
        predicted_ms=endpoint_avg,
        predicted_std_ms=endpoint_std,
        historical_stats=historical_stats,
        endpoint=request.endpoint,
        current_timeout_ms=request.current_timeout_ms,
        recent_actual_times=recent_times
    )
    
    redis_cache.store_timeout_recommendation(request.endpoint, recommendation)
    
    return recommendation


@app.get("/timeout/recommend/{endpoint}")
async def get_timeout_recommendation(endpoint: str):
    cached = redis_cache.get_timeout_recommendation(endpoint)
    if cached:
        return cached
    
    endpoint_stats = redis_cache.get_endpoint_stats(endpoint)
    recent_history = redis_cache.get_endpoint_history(endpoint, limit=50)
    recent_times = [h["response_time_ms"] for h in recent_history] if recent_history else []
    
    endpoint_avg = historical_stats.get("endpoint_avg", {}).get(endpoint, 500)
    endpoint_std = historical_stats.get("endpoint_std", {}).get(endpoint, 100)
    
    recommendation = timeout_advisor.recommend_timeout(
        predicted_ms=endpoint_avg,
        predicted_std_ms=endpoint_std,
        historical_stats=historical_stats,
        endpoint=endpoint,
        recent_actual_times=recent_times
    )
    
    redis_cache.store_timeout_recommendation(endpoint, recommendation)
    return recommendation


@app.get("/timeout/recommendations")
async def get_all_timeout_recommendations():
    recommendations = {}
    for endpoint in historical_stats.get("endpoint_avg", {}).keys():
        rec = redis_cache.get_timeout_recommendation(endpoint)
        if rec:
            recommendations[endpoint] = rec
    return {"recommendations": recommendations}


@app.post("/root-cause")
async def analyze_deviation(request: DeviationAnalysisRequest):
    request_data = request.request_data or {}
    if "endpoint" not in request_data:
        request_data["endpoint"] = request.endpoint
    
    features = {}
    if request_data:
        for key in ["downstream_count", "downstream_degraded_count", "downstream_max_latency_ms",
                     "downstream_total_latency_ms", "server_load", "param_count", "payload_size_kb"]:
            if key in request_data:
                features[key] = request_data[key]
    
    features["has_downstream_degradation"] = request_data.get("has_downstream_degradation", False)
    features["has_downstream_outage"] = request_data.get("has_downstream_outage", False)
    features["is_peak_hour"] = request_data.get("is_peak_hour", False)
    features["hour"] = request_data.get("hour", 12)
    
    analysis = root_cause_analyzer.analyze_deviation(
        predicted_ms=request.predicted_ms,
        actual_ms=request.actual_ms,
        features=features,
        historical_stats=historical_stats,
        endpoint=request.endpoint,
        request_data=request_data
    )
    
    analysis_id = str(uuid.uuid4())
    redis_cache.store_root_cause_result(analysis_id, analysis)
    
    return analysis


@app.get("/root-cause/history")
async def get_root_cause_history(limit: int = 20):
    results = redis_cache.get_recent_root_causes(limit=limit)
    return {"analyses": results, "count": len(results)}


@app.get("/root-cause/summary/{endpoint}")
async def get_root_cause_summary(endpoint: str):
    summary = root_cause_analyzer.get_endpoint_analysis_summary(endpoint)
    return summary


@app.post("/model/update")
async def trigger_model_update(request: ModelUpdateRequest = ModelUpdateRequest()):
    if not model_updater:
        raise HTTPException(status_code=503, detail="Model updater not initialized")
    
    result = model_updater.update_model(force=request.force)
    
    if result.get("status") == "success":
        global historical_stats
        from data_generator import DataGenerator
        import pandas as pd
        
        data_path = "./data/api_requests.csv"
        if os.path.exists(data_path):
            df = pd.read_csv(data_path, parse_dates=["timestamp"])
            historical_stats = feature_engineer.get_historical_stats(df)
            redis_cache.update_historical_stats(historical_stats)
        
        redis_cache.store_model_version({
            "version": result.get("version", 0),
            "timestamp": datetime.now().isoformat(),
            "metrics": result.get("metrics", {}),
            "samples": result.get("total_samples", 0),
        })
    
    return result


@app.get("/model/status")
async def get_model_update_status():
    if not model_updater:
        raise HTTPException(status_code=503, detail="Model updater not initialized")
    
    return model_updater.get_status()


@app.post("/model/auto-update/start")
async def start_auto_update():
    if not model_updater:
        raise HTTPException(status_code=503, detail="Model updater not initialized")
    
    return model_updater.start_auto_update()


@app.post("/model/auto-update/stop")
async def stop_auto_update():
    if not model_updater:
        raise HTTPException(status_code=503, detail="Model updater not initialized")
    
    return model_updater.stop_auto_update()


@app.get("/model/versions")
async def get_model_versions(limit: int = 10):
    versions = redis_cache.get_model_versions(limit=limit)
    return {"versions": versions}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.API_HOST, port=config.API_PORT)