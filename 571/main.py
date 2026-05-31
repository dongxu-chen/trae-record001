import sys
import pandas as pd
import numpy as np
from datetime import datetime

from config import config
from data_generator import DataGenerator
from feature_engineer import FeatureEngineer
from predictor import ResponseTimePredictor
from redis_cache import RedisCache
from timeout_advisor import TimeoutAdvisor
from root_cause_analyzer import RootCauseAnalyzer
from model_updater import ModelUpdater


def generate_sample_data(num_samples: int = 20000):
    print(f"Generating {num_samples} sample API requests...")
    generator = DataGenerator()
    df = generator.generate_data(num_samples=num_samples)
    generator.save_data(df, "./data/api_requests.csv")
    print(f"Generated data shape: {df.shape}")
    print("\nResponse time statistics:")
    print(df["response_time_ms"].describe())
    return df


def train_model(df: pd.DataFrame):
    print("\n" + "="*60)
    print("Training XGBoost model...")
    print("="*60)
    
    feature_engineer = FeatureEngineer(config=config.FEATURE_ENGINEERING)
    df_features = feature_engineer.fit_transform(df, fit_encoders=True)
    
    X, y = feature_engineer.prepare_for_training(df_features)
    
    print(f"Number of features: {X.shape[1]}")
    print(f"Feature columns: {list(X.columns[:10])}...")
    
    predictor = ResponseTimePredictor(
        params=config.XGB_PARAMS,
        warning_config=config.EARLY_WARNING
    )
    metrics = predictor.train(X, y)
    
    print("\nTraining Metrics:")
    print(f"  Train RMSE: {metrics['train']['rmse']:.2f} ms")
    print(f"  Train R2:   {metrics['train']['r2']:.4f}")
    print(f"  Test RMSE:  {metrics['test']['rmse']:.2f} ms")
    print(f"  Test R2:    {metrics['test']['r2']:.4f}")
    
    print("\nTop 10 Feature Importance:")
    importance = predictor.get_feature_importance()
    for feat, imp in list(importance.items())[:10]:
        print(f"  {feat}: {imp:.2f}")
    
    feature_engineer.save("./models/feature_engineer.joblib")
    predictor.save("./models/response_time_model.joblib")
    print("\nModels saved to ./models/")
    
    historical_stats = feature_engineer.get_historical_stats(df)
    historical_stats["endpoint_std"] = df.groupby("endpoint")["response_time_ms"].std().fillna(0).to_dict()
    
    return feature_engineer, predictor, historical_stats


def demonstrate_prediction(feature_engineer, predictor, historical_stats, timeout_advisor):
    print("\n" + "="*60)
    print("Prediction + Auto Timeout Recommendation")
    print("="*60)
    
    test_requests = [
        {
            "endpoint": "/api/users",
            "http_method": "GET",
            "user_segment": "regular",
            "user_id": "user_123",
            "param_complexity": "simple",
            "param_count": 2,
            "payload_size_kb": 5,
            "is_cached": False,
            "server_load": 0.3,
            "downstream_count": 2,
            "downstream_degraded_count": 0,
            "downstream_max_latency_ms": 25,
            "downstream_total_latency_ms": 35,
            "has_downstream_degradation": False,
            "has_downstream_outage": False,
            "rolling_mean": historical_stats["endpoint_avg"].get("/api/users", 200),
            "rolling_std": 30,
            "ema": historical_stats["endpoint_avg"].get("/api/users", 200),
            "user_request_count": 5,
        },
        {
            "endpoint": "/api/payments",
            "http_method": "POST",
            "user_segment": "new",
            "user_id": "user_789",
            "param_complexity": "medium",
            "param_count": 6,
            "payload_size_kb": 30,
            "is_cached": False,
            "server_load": 0.95,
            "downstream_count": 3,
            "downstream_degraded_count": 2,
            "downstream_max_latency_ms": 300,
            "downstream_total_latency_ms": 450,
            "has_downstream_degradation": True,
            "has_downstream_outage": False,
            "rolling_mean": historical_stats["endpoint_avg"].get("/api/payments", 400),
            "rolling_std": 100,
            "ema": historical_stats["endpoint_avg"].get("/api/payments", 400),
            "user_request_count": 1,
        },
    ]
    
    for i, request in enumerate(test_requests, 1):
        print(f"\n--- Request {i}: {request['endpoint']} ---")
        
        features = feature_engineer.transform_single(request, historical_stats)
        X = features.select_dtypes(include=["number"]).fillna(0)
        
        result = predictor.predict_single(X, historical_stats, request["endpoint"])
        
        print(f"  Predicted: {result['predicted_response_time_ms']:.2f} ms")
        print(f"  P99 Threshold: {result['dynamic_threshold_p99_ms']:.2f} ms")
        print(f"  Timeout Prob:  {result['timeout_probability']:.2%}")
        print(f"  Warning:       {result['warning_level']}")
        
        timeout_rec = timeout_advisor.recommend_timeout(
            predicted_ms=result["predicted_response_time_ms"],
            predicted_std_ms=result["prediction_std_ms"],
            historical_stats=historical_stats,
            endpoint=request["endpoint"],
            current_timeout_ms=3000
        )
        
        print(f"\n  === Timeout Recommendation ===")
        print(f"  Recommended:  {timeout_rec['recommended_timeout_ms']:.0f} ms")
        print(f"  Conservative: {timeout_rec['tier_timeouts']['conservative']:.0f} ms")
        print(f"  Balanced:     {timeout_rec['tier_timeouts']['balanced']:.0f} ms")
        print(f"  Aggressive:   {timeout_rec['tier_timeouts']['aggressive']:.0f} ms")
        print(f"  Confidence:   {timeout_rec['confidence']}")
        if timeout_rec.get("change_analysis"):
            ca = timeout_rec["change_analysis"]
            print(f"  Direction:    {ca['direction']} ({ca['change_percent']:+.1f}%)")


def demonstrate_root_cause(historical_stats):
    print("\n" + "="*60)
    print("Root Cause Analysis Demonstration")
    print("="*60)
    
    analyzer = RootCauseAnalyzer(config=config.ROOT_CAUSE_ANALYZER)
    
    test_cases = [
        {
            "name": "Downstream outage causing severe underprediction",
            "predicted_ms": 250,
            "actual_ms": 1800,
            "endpoint": "/api/orders",
            "request_data": {
                "endpoint": "/api/orders",
                "downstream_count": 3,
                "downstream_degraded_count": 2,
                "downstream_max_latency_ms": 800,
                "downstream_total_latency_ms": 1200,
                "has_downstream_degradation": True,
                "has_downstream_outage": True,
                "server_load": 0.85,
                "param_count": 6,
                "payload_size_kb": 30,
                "is_peak_hour": True,
                "hour": 10,
            }
        },
        {
            "name": "High server load causing moderate underprediction",
            "predicted_ms": 150,
            "actual_ms": 400,
            "endpoint": "/api/users",
            "request_data": {
                "endpoint": "/api/users",
                "downstream_count": 2,
                "downstream_degraded_count": 0,
                "downstream_max_latency_ms": 25,
                "downstream_total_latency_ms": 35,
                "has_downstream_degradation": False,
                "has_downstream_outage": False,
                "server_load": 0.92,
                "param_count": 2,
                "payload_size_kb": 5,
                "is_peak_hour": True,
                "hour": 9,
            }
        },
        {
            "name": "Normal deviation (not significant)",
            "predicted_ms": 200,
            "actual_ms": 230,
            "endpoint": "/api/products",
            "request_data": {
                "endpoint": "/api/products",
                "downstream_count": 2,
                "downstream_degraded_count": 0,
                "downstream_max_latency_ms": 20,
                "downstream_total_latency_ms": 30,
                "has_downstream_degradation": False,
                "has_downstream_outage": False,
                "server_load": 0.4,
                "param_count": 3,
                "payload_size_kb": 8,
            }
        },
    ]
    
    for tc in test_cases:
        print(f"\n--- {tc['name']} ---")
        
        result = analyzer.analyze_deviation(
            predicted_ms=tc["predicted_ms"],
            actual_ms=tc["actual_ms"],
            features=tc["request_data"],
            historical_stats=historical_stats,
            endpoint=tc["endpoint"],
            request_data=tc["request_data"]
        )
        
        print(f"  Predicted: {tc['predicted_ms']}ms | Actual: {tc['actual_ms']}ms")
        print(f"  Deviation: {result['deviation_percent']:+.1f}%")
        print(f"  Significant: {result['is_significant_deviation']}")
        print(f"  Severity: {result.get('severity', 'N/A')}")
        
        if result["is_significant_deviation"]:
            print(f"  Summary: {result.get('summary', 'N/A')}")
            print(f"  Root Causes:")
            for rc in result.get("root_causes", []):
                print(f"    [{rc['category']}] {rc['description']} (contribution: {rc.get('contribution_percent', 0):.1f}%)")
            print(f"  Investigations:")
            for step in result.get("recommended_investigations", [])[:3]:
                print(f"    - {step}")


def demonstrate_model_updater(feature_engineer, predictor, redis_cache):
    print("\n" + "="*60)
    print("Model Auto-Update Demonstration")
    print("="*60)
    
    updater = ModelUpdater(
        predictor=predictor,
        feature_engineer=feature_engineer,
        redis_cache=redis_cache,
        config={**config.MODEL_UPDATER, "min_new_samples": 10}
    )
    
    print(f"  Initial status: {updater.get_status()}")
    
    print("\n  Adding simulated data points...")
    for i in range(15):
        updater.add_data_point(
            request_data={
                "endpoint": "/api/users",
                "http_method": "GET",
                "user_segment": "regular",
                "param_complexity": "simple",
                "param_count": 2,
                "payload_size_kb": 5,
                "is_cached": False,
                "server_load": 0.5,
                "downstream_count": 2,
                "downstream_degraded_count": 0,
                "downstream_max_latency_ms": 25,
                "downstream_total_latency_ms": 35,
                "has_downstream_degradation": False,
                "has_downstream_outage": False,
            },
            actual_response_time_ms=np.random.normal(150, 30)
        )
    
    print(f"  Buffer size: {len(updater.new_data_buffer)}")
    
    should, reason = updater.should_update()
    print(f"  Should update: {should} ({reason})")
    
    if should:
        print("\n  Running forced model update...")
        result = updater.update_model(force=True)
        print(f"  Update result: {result['status']}")
        if result['status'] == 'success':
            print(f"  New version: {result.get('version')}")
            print(f"  Samples used: {result.get('total_samples')}")
            print(f"  New Test R2: {result['metrics']['test']['r2']:.4f}")
            print(f"  New Test RMSE: {result['metrics']['test']['rmse']:.2f}")
            if result.get('validation'):
                v = result['validation']
                print(f"  Validation: {v['reason']} (RMSE change: {v.get('rmse_change_percent', 0):+.1f}%)")
    
    print(f"\n  Final status: {updater.get_status()}")


def redis_cache_demo():
    print("\n" + "="*60)
    print("Redis Cache Demonstration")
    print("="*60)
    
    cache = RedisCache(
        host=config.REDIS_HOST,
        port=config.REDIS_PORT,
        db=config.REDIS_DB,
        password=config.REDIS_PASSWORD,
        history_window=100,
        downstream_services=config.DOWNSTREAM_SERVICE_TYPES
    )
    
    print(f"Redis Connected: {cache.is_connected()}")
    
    downstream_statuses = [
        ("db_users", "healthy", 25, 1.0),
        ("cache_redis", "healthy", 5, 1.0),
        ("db_orders", "degraded", 120, 0.6),
    ]
    
    for service, status, latency, health in downstream_statuses:
        cache.update_downstream_service_status(service, status, latency, health)
    
    return cache


def main():
    print("="*60)
    print("API Response Time Prediction Tool v2.0")
    print("with Auto Timeout, Root Cause Analysis & Model Auto-Update")
    print("="*60)
    
    df = generate_sample_data(20000)
    
    feature_engineer, predictor, historical_stats = train_model(df)
    
    timeout_advisor = TimeoutAdvisor(config=config.TIMEOUT_ADVISOR)
    
    demonstrate_prediction(feature_engineer, predictor, historical_stats, timeout_advisor)
    
    demonstrate_root_cause(historical_stats)
    
    cache = redis_cache_demo()
    
    demonstrate_model_updater(feature_engineer, predictor, cache)
    
    print("\n" + "="*60)
    print("All demonstrations completed!")
    print("="*60)
    print("\nNext steps:")
    print("1. Start Redis server (optional)")
    print("2. Run: python api.py")
    print("3. Open http://localhost:8000/docs for API documentation")
    print("\nKey new endpoints:")
    print("  POST /timeout/recommend     - Get timeout recommendation")
    print("  GET  /timeout/recommend/{ep} - Get cached recommendation")
    print("  POST /root-cause            - Analyze prediction deviation")
    print("  GET  /root-cause/history    - View past analyses")
    print("  POST /model/update          - Trigger model update")
    print("  GET  /model/status          - Check updater status")
    print("  POST /model/auto-update/start - Start auto-update loop")
    print("  POST /model/auto-update/stop  - Stop auto-update loop")


if __name__ == "__main__":
    main()