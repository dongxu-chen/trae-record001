import numpy as np
import pandas as pd
import os
import joblib
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.preprocessing import StandardScaler, LabelEncoder, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score, precision_recall_curve, auc
from sklearn.impute import SimpleImputer
from sklearn.base import BaseEstimator, ClassifierMixin
from imblearn.over_sampling import SMOTE
from imblearn.pipeline import Pipeline as ImbPipeline
import xgboost as xgb
import warnings
warnings.filterwarnings('ignore')


def load_data(train_path='data/train.csv', test_path='data/test.csv'):
    print("Loading data...")
    train_df = pd.read_csv(train_path, encoding='utf-8-sig')
    test_df = pd.read_csv(test_path, encoding='utf-8-sig')
    
    print(f"Training set: {len(train_df)} samples")
    print(f"Test set: {len(test_df)} samples")
    
    return train_df, test_df


def preprocess_data(df, is_train=True, preprocessor=None):
    exclude_cols = ['claim_id', 'is_fraud', 'accident_date']
    
    numeric_features = ['age', 'driving_years', 'annual_income', 'vehicle_age', 'vehicle_value',
                       'policy_premium', 'policy_duration', 'past_claims_count', 'past_claims_total',
                       'past_fraud_count', 'medical_expense', 'vehicle_repair_cost', 'third_party_medical',
                       'third_party_property_damage', 'total_claim_amount', 'deductible', 'claim_amount',
                       'hospital_days', 'disability_level', 'claim_processing_days', 'claim_ratio',
                       'expense_to_value_ratio', 'fraud_indicators']
    
    binary_features = ['third_party_injury', 'police_report', 'witness_present', 'photos_provided',
                      'repair_invoice', 'medical_invoice', 'same_day_claim', 'high_value_ratio',
                      'suspicious_time']
    
    categorical_features = ['gender', 'occupation', 'region', 'marital_status', 'accident_type',
                           'accident_season', 'accident_time', 'accident_weather', 'vehicle_type',
                           'coverage_type']
    
    feature_cols = numeric_features + binary_features + categorical_features
    
    for col in feature_cols:
        if col in df.columns and df[col].isnull().sum() > 0:
            if col in numeric_features:
                df[col] = df[col].fillna(df[col].median())
            else:
                df[col] = df[col].fillna(df[col].mode()[0])
    
    X = df[feature_cols].copy()
    
    if 'is_fraud' in df.columns:
        y = df['is_fraud']
    else:
        y = None
    
    if is_train or preprocessor is None:
        numeric_transformer = Pipeline(steps=[
            ('imputer', SimpleImputer(strategy='median')),
            ('scaler', StandardScaler())
        ])
        
        binary_transformer = Pipeline(steps=[
            ('imputer', SimpleImputer(strategy='most_frequent'))
        ])
        
        categorical_transformer = Pipeline(steps=[
            ('imputer', SimpleImputer(strategy='most_frequent')),
            ('onehot', OneHotEncoder(handle_unknown='ignore', sparse_output=False))
        ])
        
        preprocessor = ColumnTransformer(
            transformers=[
                ('num', numeric_transformer, numeric_features),
                ('bin', binary_transformer, binary_features),
                ('cat', categorical_transformer, categorical_features)
            ])
        
        X_processed = preprocessor.fit_transform(X)
        
        if hasattr(preprocessor.named_transformers_['cat'].named_steps['onehot'], 'get_feature_names_out'):
            cat_features = preprocessor.named_transformers_['cat'].named_steps['onehot'].get_feature_names_out(categorical_features)
        else:
            cat_features = preprocessor.named_transformers_['cat'].named_steps['onehot'].get_feature_names(categorical_features)
        
        all_features = numeric_features + binary_features + list(cat_features)
        
        return X_processed, y, preprocessor, all_features
    else:
        X_processed = preprocessor.transform(X)
        return X_processed, y, preprocessor, None


def train_xgboost_with_cv_smote(X_train, y_train, X_test, y_test, feature_names, n_splits=5):
    print("\nTraining XGBoost model with CV-SMOTE (no data leakage)...")
    print("="*60)
    print("SMOTE will be applied WITHIN each cross-validation fold to avoid data leakage")
    print("="*60)
    
    print(f"\nOriginal training data: {X_train.shape[0]} samples, Fraud ratio: {y_train.mean():.4f}")
    
    smote = SMOTE(random_state=42, k_neighbors=5)
    
    scale_pos_weight = (len(y_train) - y_train.sum()) / y_train.sum()
    
    xgb_model = xgb.XGBClassifier(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        gamma=0.1,
        min_child_weight=3,
        scale_pos_weight=scale_pos_weight,
        objective='binary:logistic',
        eval_metric='auc',
        random_state=42,
        n_jobs=-1,
        tree_method='hist'
    )
    
    cv_pipeline = ImbPipeline([
        ('smote', smote),
        ('classifier', xgb_model)
    ])
    
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
    
    print(f"\nPerforming {n_splits}-fold stratified cross-validation with SMOTE inside each fold...")
    cv_scores_roc = cross_val_score(cv_pipeline, X_train, y_train, cv=skf, scoring='roc_auc', n_jobs=-1)
    cv_scores_pr = cross_val_score(cv_pipeline, X_train, y_train, cv=skf, scoring='average_precision', n_jobs=-1)
    
    print(f"\nCross-Validation Results:")
    print(f"  ROC-AUC: {cv_scores_roc.mean():.4f} (±{cv_scores_roc.std():.4f})")
    print(f"  PR-AUC:  {cv_scores_pr.mean():.4f} (±{cv_scores_pr.std():.4f})")
    print(f"  Fold scores: {[f'{s:.4f}' for s in cv_scores_roc]}")
    
    print(f"\nTraining final model on full training set with SMOTE...")
    X_train_resampled, y_train_resampled = smote.fit_resample(X_train, y_train)
    print(f"After SMOTE: {X_train_resampled.shape[0]} samples, Fraud ratio: {y_train_resampled.mean():.4f}")
    
    final_model = xgb.XGBClassifier(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        gamma=0.1,
        min_child_weight=3,
        scale_pos_weight=scale_pos_weight,
        objective='binary:logistic',
        eval_metric='auc',
        random_state=42,
        n_jobs=-1,
        tree_method='hist'
    )
    
    final_model.fit(
        X_train_resampled, y_train_resampled,
        eval_set=[(X_test, y_test)],
        verbose=False
    )
    
    return final_model, cv_scores_roc, cv_scores_pr


def evaluate_model(model, X_test, y_test, feature_names, cv_scores_roc=None, cv_scores_pr=None):
    print("\n" + "="*60)
    print("MODEL EVALUATION ON TEST SET")
    print("="*60)
    
    y_pred = model.predict(X_test)
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    
    print("\nConfusion Matrix:")
    cm = confusion_matrix(y_test, y_pred)
    print(cm)
    
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred))
    
    roc_auc = roc_auc_score(y_test, y_pred_proba)
    print(f"\nTest ROC-AUC Score: {roc_auc:.4f}")
    
    precision, recall, _ = precision_recall_curve(y_test, y_pred_proba)
    pr_auc = auc(recall, precision)
    print(f"Test PR-AUC Score: {pr_auc:.4f}")
    
    if cv_scores_roc is not None and cv_scores_pr is not None:
        print(f"\nCross-Validation vs Test Set Comparison:")
        print(f"  CV ROC-AUC:   {cv_scores_roc.mean():.4f} (±{cv_scores_roc.std():.4f})")
        print(f"  Test ROC-AUC: {roc_auc:.4f}")
        print(f"  CV PR-AUC:    {cv_scores_pr.mean():.4f} (±{cv_scores_pr.std():.4f})")
        print(f"  Test PR-AUC:  {pr_auc:.4f}")
        if abs(cv_scores_roc.mean() - roc_auc) > 0.05:
            print(f"  ⚠️ Note: Significant difference between CV and test performance may indicate overfitting")
    
    importances = model.feature_importances_
    feature_importance = pd.DataFrame({
        'feature': feature_names[:len(importances)],
        'importance': importances
    }).sort_values('importance', ascending=False)
    
    print("\nTop 15 Most Important Features:")
    print(feature_importance.head(15).to_string(index=False))
    
    return {
        'roc_auc': roc_auc,
        'pr_auc': pr_auc,
        'confusion_matrix': cm,
        'feature_importance': feature_importance,
        'cv_scores_roc': cv_scores_roc,
        'cv_scores_pr': cv_scores_pr
    }


def save_model(model, preprocessor, feature_names, model_path='models/xgboost_model.pkl', 
               preprocessor_path='models/preprocessor.pkl', features_path='models/features.pkl'):
    os.makedirs('models', exist_ok=True)
    
    joblib.dump(model, model_path)
    joblib.dump(preprocessor, preprocessor_path)
    joblib.dump(feature_names, features_path)
    
    print(f"\nModel saved to {model_path}")
    print(f"Preprocessor saved to {preprocessor_path}")
    print(f"Feature names saved to {features_path}")


def load_model(model_path='models/xgboost_model.pkl', preprocessor_path='models/preprocessor.pkl',
               features_path='models/features.pkl'):
    model = joblib.load(model_path)
    preprocessor = joblib.load(preprocessor_path)
    feature_names = joblib.load(features_path)
    
    return model, preprocessor, feature_names


def main():
    if not os.path.exists('data/train.csv') or not os.path.exists('data/test.csv'):
        print("Data files not found. Generating data first...")
        from generate_data import generate_insurance_claims, save_data
        df = generate_insurance_claims(n_samples=10000, fraud_ratio=0.08)
        save_data(df)
    
    train_df, test_df = load_data()
    
    X_train, y_train, preprocessor, feature_names = preprocess_data(train_df, is_train=True)
    X_test, y_test, _, _ = preprocess_data(test_df, is_train=False, preprocessor=preprocessor)
    
    print(f"\nTraining features shape: {X_train.shape}")
    print(f"Test features shape: {X_test.shape}")
    print(f"Number of features: {len(feature_names)}")
    
    model, cv_scores_roc, cv_scores_pr = train_xgboost_with_cv_smote(X_train, y_train, X_test, y_test, feature_names)
    
    metrics = evaluate_model(model, X_test, y_test, feature_names, cv_scores_roc, cv_scores_pr)
    
    save_model(model, preprocessor, feature_names)
    
    return model, preprocessor, feature_names, metrics


if __name__ == '__main__':
    main()
