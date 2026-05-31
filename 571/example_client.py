import requests
import json


BASE_URL = "http://localhost:8000"


def example_train_model():
    print("1. Training the model...")
    response = requests.post(f"{BASE_URL}/train")
    result = response.json()
    print(f"   Status: {result['status']}")
    print(f"   Training samples: {result['training_samples']}")
    print(f"   Test RMSE: {result['metrics']['test']['rmse']:.2f} ms")
    print()


def example_predict_with_early_warning():
    print("2. Making a prediction with early warning...")
    payload = {
        "endpoint": "/api/orders",
        "http_method": "POST",
        "user_segment": "vip",
        "user_id": "user_12345",
        "param_complexity": "medium",
        "param_count": 6,
        "payload_size_kb": 25.5,
        "is_cached": False,
        "server_load": 0.65,
        "enable_early_warning": True
    }
    
    response = requests.post(f"{BASE_URL}/predict", json=payload)
    result = response.json()
    
    print(f"   Request ID: {result['request_id']}")
    print(f"   Predicted: {result['predicted_response_time_ms']:.2f} ms")
    print(f"   Dynamic P99 Threshold: {result['dynamic_threshold_p99_ms']:.2f} ms")
    print(f"   Timeout Probability: {result['timeout_probability']:.2%}")
    print(f"   Warning Level: {result['warning_level']}")
    
    if result.get('early_warning') and result['early_warning']['warning_types']:
        print(f"   Warning Types: {', '.join(result['early_warning']['warning_types'])}")
        print(f"   Recommended Actions:")
        for action in result['early_warning']['recommended_actions'][:2]:
            print(f"     - {action}")
    
    if result.get('future_risk_prediction'):
        print(f"   Will Timeout Soon: {result['future_risk_prediction']['will_timeout_soon']}")
        if result['future_risk_prediction'].get('steps_to_warning'):
            print(f"   Steps to Warning: {result['future_risk_prediction']['steps_to_warning']}")
    print()
    return result['request_id']


def example_record_actual(request_id):
    print("3. Recording actual response time...")
    params = {
        "request_id": request_id,
        "endpoint": "/api/orders",
        "response_time_ms": 245.5
    }
    response = requests.post(f"{BASE_URL}/record", params=params)
    result = response.json()
    print(f"   Status: {result['status']}")
    print()


def example_update_downstream_status():
    print("4. Updating downstream service status...")
    statuses = [
        {"service_name": "db_users", "status": "healthy", "latency_ms": 25, "health_score": 1.0},
        {"service_name": "db_orders", "status": "degraded", "latency_ms": 150, "health_score": 0.7},
        {"service_name": "queue_kafka", "status": "healthy", "latency_ms": 15, "health_score": 0.95},
    ]
    
    for status in statuses:
        response = requests.post(f"{BASE_URL}/downstream/status", json=status)
        print(f"   {status['service_name']}: {status['status']} ({status['latency_ms']}ms)")
    print()


def example_get_downstream_status():
    print("5. Getting downstream service statuses...")
    response = requests.get(f"{BASE_URL}/downstream/status")
    result = response.json()
    
    for service, status in result['downstream_services'].items():
        print(f"   {service}: {status['status']} - {status['latency_ms']}ms (health: {status['health_score']:.2f})")
    print()


def example_get_dynamic_thresholds():
    print("6. Getting dynamic P99 thresholds...")
    response = requests.get(f"{BASE_URL}/thresholds")
    result = response.json()
    
    print(f"   Percentile: P{result['percentile']}")
    for endpoint, threshold in result['thresholds'].items():
        if endpoint != 'global':
            print(f"   {endpoint}: P99={threshold['p99_ms']:.0f}ms, Threshold={threshold['dynamic_threshold_ms']:.0f}ms")
    print()


def example_get_warnings():
    print("7. Getting recent warnings...")
    response = requests.get(f"{BASE_URL}/warnings")
    result = response.json()
    
    print(f"   Total warnings: {result['count']}")
    for warning in result['warnings'][:3]:
        print(f"   [{warning['warning_level']}] {warning['endpoint']}: {', '.join(warning['warning_types'])}")
    print()


def example_health_check():
    print("8. Health check...")
    response = requests.get(f"{BASE_URL}/health")
    result = response.json()
    print(f"   Status: {result['status']}")
    print(f"   Model Loaded: {result['model_loaded']}")
    print(f"   Redis Connected: {result['redis_connected']}")
    print()


def example_batch_predict():
    print("9. Batch prediction...")
    params = {
        "endpoints": ["/api/users", "/api/products", "/api/payments"]
    }
    response = requests.get(f"{BASE_URL}/batch-predict", params=params)
    result = response.json()
    
    for pred in result['predictions']:
        print(f"   {pred['endpoint']}: {pred['predicted_response_time_ms']:.2f} ms")
    print()


def example_get_metrics():
    print("10. Getting model metrics...")
    response = requests.get(f"{BASE_URL}/metrics")
    result = response.json()
    
    print(f"   Train RMSE: {result['metrics']['test']['rmse']:.2f} ms")
    print(f"   Test R2: {result['metrics']['test']['r2']:.4f}")
    print("   Top 5 Features:")
    for feat, imp in list(result['feature_importance'].items())[:5]:
        print(f"     {feat}: {imp:.2f}")
    print()


if __name__ == "__main__":
    print("="*60)
    print("API Response Time Predictor - API Usage Examples")
    print("with Downstream Services, Dynamic P99 Thresholds, and Early Warnings")
    print("="*60)
    print()
    
    try:
        example_health_check()
        example_train_model()
        example_update_downstream_status()
        example_get_downstream_status()
        request_id = example_predict_with_early_warning()
        example_record_actual(request_id)
        example_get_dynamic_thresholds()
        example_get_warnings()
        example_batch_predict()
        example_get_metrics()
        
        print("="*60)
        print("All examples completed successfully!")
        print("="*60)
        
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to the API server.")
        print("Please start the server first with: python api.py")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error: {e}")