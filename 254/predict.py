import numpy as np
import pandas as pd
import os
from train_model import load_model, preprocess_data


def predict_single_claim(claim_data, model, preprocessor, feature_names):
    if isinstance(claim_data, dict):
        claim_data = pd.DataFrame([claim_data])
    
    X_processed, _, _, _ = preprocess_data(claim_data, is_train=False, preprocessor=preprocessor)
    
    fraud_probability = model.predict_proba(X_processed)[0, 1]
    prediction = model.predict(X_processed)[0]
    
    if fraud_probability >= 0.7:
        risk_level = "高风险"
        risk_color = "🔴"
    elif fraud_probability >= 0.4:
        risk_level = "中风险"
        risk_color = "🟡"
    else:
        risk_level = "低风险"
        risk_color = "🟢"
    
    return {
        'fraud_probability': float(fraud_probability),
        'prediction': int(prediction),
        'risk_level': risk_level,
        'risk_color': risk_color
    }


def predict_batch(claims_data, model, preprocessor, feature_names):
    if isinstance(claims_data, list):
        claims_data = pd.DataFrame(claims_data)
    
    X_processed, _, _, _ = preprocess_data(claims_data, is_train=False, preprocessor=preprocessor)
    
    fraud_probabilities = model.predict_proba(X_processed)[:, 1]
    predictions = model.predict(X_processed)
    
    results = []
    for i, (prob, pred) in enumerate(zip(fraud_probabilities, predictions)):
        if prob >= 0.7:
            risk_level = "高风险"
        elif prob >= 0.4:
            risk_level = "中风险"
        else:
            risk_level = "低风险"
        
        results.append({
            'claim_id': claims_data.iloc[i].get('claim_id', f'CLAIM_{i}'),
            'fraud_probability': float(prob),
            'prediction': int(pred),
            'risk_level': risk_level
        })
    
    return pd.DataFrame(results)


def create_sample_claim():
    return {
        'age': 35,
        'gender': '男',
        'occupation': '技术工人',
        'region': '华东',
        'marital_status': '已婚',
        'driving_years': 10,
        'annual_income': 180000,
        
        'accident_type': '追尾事故',
        'accident_season': '夏',
        'accident_time': '晚高峰',
        'accident_weather': '晴',
        
        'vehicle_age': 3,
        'vehicle_type': '轿车',
        'vehicle_value': 250000,
        
        'coverage_type': '商业险-全险',
        'policy_premium': 8000,
        'policy_duration': 1,
        
        'past_claims_count': 2,
        'past_claims_total': 15000,
        'past_fraud_count': 0,
        
        'medical_expense': 3000,
        'vehicle_repair_cost': 12000,
        'third_party_injury': 0,
        'third_party_medical': 0,
        'third_party_property_damage': 2000,
        'total_claim_amount': 17000,
        'deductible': 1000,
        'claim_amount': 16000,
        'hospital_days': 0,
        'disability_level': 0,
        
        'police_report': 1,
        'witness_present': 1,
        'photos_provided': 1,
        'repair_invoice': 1,
        'medical_invoice': 0,
        'claim_processing_days': 5,
        
        'claim_ratio': 2.0,
        'expense_to_value_ratio': 0.068,
        'same_day_claim': 0,
        'high_value_ratio': 0,
        'suspicious_time': 0,
        'fraud_indicators': 0
    }


def create_suspicious_claim():
    return {
        'age': 28,
        'gender': '男',
        'occupation': '自由职业',
        'region': '华南',
        'marital_status': '未婚',
        'driving_years': 3,
        'annual_income': 80000,
        
        'accident_type': '单 vehicle 事故',
        'accident_season': '冬',
        'accident_time': '夜间',
        'accident_weather': '晴',
        
        'vehicle_age': 8,
        'vehicle_type': '轿车',
        'vehicle_value': 80000,
        
        'coverage_type': '商业险-基本',
        'policy_premium': 3000,
        'policy_duration': 1,
        
        'past_claims_count': 5,
        'past_claims_total': 60000,
        'past_fraud_count': 2,
        
        'medical_expense': 15000,
        'vehicle_repair_cost': 45000,
        'third_party_injury': 0,
        'third_party_medical': 0,
        'third_party_property_damage': 0,
        'total_claim_amount': 60000,
        'deductible': 500,
        'claim_amount': 59500,
        'hospital_days': 2,
        'disability_level': 0,
        
        'police_report': 0,
        'witness_present': 0,
        'photos_provided': 0,
        'repair_invoice': 1,
        'medical_invoice': 1,
        'claim_processing_days': 1,
        
        'claim_ratio': 19.83,
        'expense_to_value_ratio': 0.75,
        'same_day_claim': 1,
        'high_value_ratio': 1,
        'suspicious_time': 1,
        'fraud_indicators': 5
    }


if __name__ == '__main__':
    if not os.path.exists('models/xgboost_model.pkl'):
        print("Model not found. Training model first...")
        from train_model import main as train_main
        train_main()
    
    print("Loading trained model...")
    model, preprocessor, feature_names = load_model()
    
    print("\n" + "="*60)
    print("TEST 1: Normal Claim Prediction")
    print("="*60)
    normal_claim = create_sample_claim()
    result = predict_single_claim(normal_claim, model, preprocessor, feature_names)
    print(f"Fraud Probability: {result['fraud_probability']:.4f}")
    print(f"Risk Level: {result['risk_color']} {result['risk_level']}")
    print(f"Prediction: {'Fraud' if result['prediction'] == 1 else 'Normal'}")
    
    print("\n" + "="*60)
    print("TEST 2: Suspicious Claim Prediction")
    print("="*60)
    suspicious_claim = create_suspicious_claim()
    result = predict_single_claim(suspicious_claim, model, preprocessor, feature_names)
    print(f"Fraud Probability: {result['fraud_probability']:.4f}")
    print(f"Risk Level: {result['risk_color']} {result['risk_level']}")
    print(f"Prediction: {'Fraud' if result['prediction'] == 1 else 'Normal'}")
    
    print("\n" + "="*60)
    print("TEST 3: Batch Prediction")
    print("="*60)
    test_df = pd.read_csv('data/test.csv', encoding='utf-8-sig')
    batch_results = predict_batch(test_df.head(10), model, preprocessor, feature_names)
    print(batch_results.to_string(index=False))
