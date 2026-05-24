import pandas as pd
import numpy as np
from datetime import datetime, timedelta

np.random.seed(42)

def generate_sample_data(n_users=1000, max_days=180):
    user_ids = [f'user_{i:05d}' for i in range(n_users)]
    
    features = {
        'avg_session_duration': np.random.exponential(15, n_users) + 2,
        'login_frequency': np.random.poisson(4, n_users) / 30,
        'pages_per_session': np.random.normal(5, 2, n_users).clip(1, 15),
        'total_purchases': np.random.poisson(2, n_users),
        'avg_order_value': np.random.lognormal(4, 0.8, n_users),
        'customer_service_calls': np.random.poisson(1, n_users),
        'discount_usage_ratio': np.random.beta(2, 3, n_users),
        'product_reviews_count': np.random.poisson(1, n_users),
        'social_shares': np.random.poisson(0.5, n_users),
        'days_since_last_activity': np.random.randint(0, 90, n_users),
        'is_mobile_user': np.random.choice([0, 1], n_users, p=[0.4, 0.6]),
        'has_subscription': np.random.choice([0, 1], n_users, p=[0.7, 0.3]),
        'account_age_days': np.random.randint(30, 365, n_users)
    }
    
    df = pd.DataFrame(features, index=user_ids)
    df.index.name = 'user_id'
    df = df.reset_index()
    
    hazard_scores = (
        -0.03 * df['avg_session_duration'] +
        -0.5 * df['login_frequency'] +
        -0.08 * df['pages_per_session'] +
        -0.15 * df['total_purchases'] +
        -0.0001 * df['avg_order_value'] +
        0.2 * df['customer_service_calls'] +
        -0.3 * df['discount_usage_ratio'] +
        -0.1 * df['product_reviews_count'] +
        -0.05 * df['social_shares'] +
        0.02 * df['days_since_last_activity'] +
        0.1 * df['is_mobile_user'] +
        -0.4 * df['has_subscription'] +
        -0.001 * df['account_age_days']
    )
    
    hazard_scores = (hazard_scores - hazard_scores.mean()) / hazard_scores.std()
    base_hazard = 0.01
    event_hazard = base_hazard * np.exp(hazard_scores)
    
    survival_times = np.random.exponential(1 / event_hazard, n_users)
    survival_times = survival_times.clip(1, max_days).astype(int)
    
    censoring_prob = 0.2
    censored = np.random.choice([0, 1], n_users, p=[1 - censoring_prob, censoring_prob])
    observed_churn = (censored == 0).astype(int)
    
    df['tenure_days'] = survival_times
    df['churned'] = observed_churn
    
    return df

def load_csv_data(uploaded_file):
    df = pd.read_csv(uploaded_file)
    return df

def validate_data(df, duration_col, event_col):
    errors = []
    
    if duration_col not in df.columns:
        errors.append(f"Duration column '{duration_col}' not found in data")
    elif not np.issubdtype(df[duration_col].dtype, np.number):
        errors.append(f"Duration column '{duration_col}' must be numeric")
    elif (df[duration_col] <= 0).any():
        errors.append(f"Duration column '{duration_col}' must contain positive values")
    
    if event_col not in df.columns:
        errors.append(f"Event column '{event_col}' not found in data")
    else:
        unique_vals = df[event_col].unique()
        if not set(unique_vals).issubset({0, 1}):
            errors.append(f"Event column '{event_col}' must contain only 0 and 1")
    
    return errors

def preprocess_data(df, duration_col, event_col, exclude_cols=None):
    if exclude_cols is None:
        exclude_cols = []
    
    df_clean = df.copy()
    
    feature_cols = [col for col in df_clean.columns 
                   if col not in exclude_cols + [duration_col, event_col]]
    
    for col in feature_cols:
        if df_clean[col].dtype == 'object':
            df_clean[col] = pd.Categorical(df_clean[col]).codes
        elif df_clean[col].isnull().any():
            df_clean[col] = df_clean[col].fillna(df_clean[col].median())
    
    return df_clean, feature_cols
