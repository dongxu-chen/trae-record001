import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sklearn.preprocessing import StandardScaler


def generate_customer_profiles(n_customers=1000, seed=42):
    np.random.seed(seed)
    customer_ids = [f'CUST_{i:05d}' for i in range(1, n_customers + 1)]
    
    age = np.random.randint(18, 70, n_customers)
    gender = np.random.choice(['M', 'F'], n_customers, p=[0.45, 0.55])
    region = np.random.choice(['华东', '华北', '华南', '西南', '西北', '东北'], n_customers, 
                              p=[0.25, 0.2, 0.2, 0.15, 0.1, 0.1])
    membership_level = np.random.choice(['普通', '银卡', '金卡', '钻石'], n_customers,
                                         p=[0.5, 0.3, 0.15, 0.05])
    registration_days = np.random.randint(30, 730, n_customers)
    
    profiles = pd.DataFrame({
        'customer_id': customer_ids,
        'age': age,
        'gender': gender,
        'region': region,
        'membership_level': membership_level,
        'registration_days': registration_days
    })
    
    return profiles


def generate_transaction_history(profiles, observation_period=365, seed=42):
    np.random.seed(seed)
    transactions = []
    end_date = datetime.now()
    start_date = end_date - timedelta(days=observation_period)
    
    level_lambda = {'普通': 0.8, '银卡': 1.5, '金卡': 2.5, '钻石': 4.0}
    level_avg_amount = {'普通': 150, '银卡': 250, '金卡': 400, '钻石': 800}
    
    for _, row in profiles.iterrows():
        customer_id = row['customer_id']
        level = row['membership_level']
        reg_days = row['registration_days']
        
        n_transactions = np.random.poisson(level_lambda[level] * (reg_days / 365))
        
        for _ in range(max(1, n_transactions)):
            days_after_reg = np.random.randint(0, min(reg_days, observation_period))
            transaction_date = end_date - timedelta(days=reg_days - days_after_reg)
            
            if transaction_date >= start_date:
                amount = np.random.gamma(shape=2, scale=level_avg_amount[level] / 2)
                amount = round(amount, 2)
                
                transactions.append({
                    'customer_id': customer_id,
                    'transaction_date': transaction_date,
                    'amount': amount,
                    'transaction_type': np.random.choice(['购买', '充值', '退款'], 
                                                          p=[0.9, 0.08, 0.02])
                })
    
    df = pd.DataFrame(transactions)
    df = df.sort_values('transaction_date').reset_index(drop=True)
    return df


def generate_behavior_logs(profiles, observation_period=365, seed=42):
    np.random.seed(seed)
    behaviors = []
    end_date = datetime.now()
    start_date = end_date - timedelta(days=observation_period)
    
    for _, row in profiles.iterrows():
        customer_id = row['customer_id']
        level = row['membership_level']
        
        base_freq = {'普通': 5, '银卡': 10, '金卡': 20, '钻石': 35}[level]
        n_activities = np.random.poisson(base_freq)
        
        for _ in range(n_activities):
            days_ago = np.random.randint(0, observation_period)
            activity_date = end_date - timedelta(days=days_ago)
            
            if activity_date >= start_date:
                behaviors.append({
                    'customer_id': customer_id,
                    'activity_date': activity_date,
                    'activity_type': np.random.choice(
                        ['浏览商品', '加入购物车', '收藏', '查看订单', '客服咨询'],
                        p=[0.5, 0.2, 0.15, 0.1, 0.05]
                    ),
                    'duration_seconds': np.random.randint(10, 600)
                })
    
    df = pd.DataFrame(behaviors)
    df = df.sort_values('activity_date').reset_index(drop=True)
    return df


def create_rfm_data(transactions_df, customer_ids, observation_end_date=None):
    if observation_end_date is None:
        observation_end_date = transactions_df['transaction_date'].max()
    
    purchases = transactions_df[transactions_df['transaction_type'] == '购买'].copy()
    
    rfm = purchases.groupby('customer_id').agg({
        'transaction_date': ['min', 'max', 'count'],
        'amount': ['sum', 'mean']
    }).reset_index()
    
    rfm.columns = ['customer_id', 'first_purchase', 'last_purchase', 
                   'frequency', 'total_amount', 'avg_amount']
    
    all_customers = pd.DataFrame({'customer_id': customer_ids})
    rfm = all_customers.merge(rfm, on='customer_id', how='left')
    
    rfm['frequency'] = rfm['frequency'].fillna(0).astype(int)
    rfm['total_amount'] = rfm['total_amount'].fillna(0)
    rfm['avg_amount'] = rfm['avg_amount'].fillna(0)
    
    rfm['recency'] = (observation_end_date - rfm['last_purchase']).dt.days
    rfm['T'] = (observation_end_date - rfm['first_purchase']).dt.days
    
    rfm['recency'] = rfm['recency'].fillna(365)
    rfm['T'] = rfm['T'].fillna(365)
    
    rfm = rfm[rfm['frequency'] > 0].copy()
    rfm = rfm.reset_index(drop=True)
    
    return rfm


def create_behavior_features(behavior_df, customer_ids):
    activity_counts = behavior_df.groupby(['customer_id', 'activity_type']).size().unstack(fill_value=0)
    activity_counts = activity_counts.reindex(customer_ids, fill_value=0).reset_index()
    
    total_activities = activity_counts.drop('customer_id', axis=1).sum(axis=1)
    activity_counts['total_activities'] = total_activities
    activity_counts['cart_conversion_rate'] = np.where(
        activity_counts['浏览商品'] > 0,
        activity_counts['加入购物车'] / activity_counts['浏览商品'],
        0
    )
    
    avg_duration = behavior_df.groupby('customer_id')['duration_seconds'].mean().reset_index()
    avg_duration.columns = ['customer_id', 'avg_duration']
    
    features = activity_counts.merge(avg_duration, on='customer_id', how='left')
    features['avg_duration'] = features['avg_duration'].fillna(0)
    
    return features


def prepare_model_data(profiles, transactions, behavior_logs):
    customer_ids = profiles['customer_id'].unique()
    
    rfm = create_rfm_data(transactions, customer_ids)
    behavior_features = create_behavior_features(behavior_logs, customer_ids)
    
    model_data = rfm.merge(profiles, on='customer_id', how='left')
    model_data = model_data.merge(behavior_features, on='customer_id', how='left')
    
    model_data = model_data.fillna(0)
    
    return model_data


if __name__ == '__main__':
    profiles = generate_customer_profiles(n_customers=500)
    transactions = generate_transaction_history(profiles)
    behavior_logs = generate_behavior_logs(profiles)
    
    model_data = prepare_model_data(profiles, transactions, behavior_logs)
    
    print("客户画像:", profiles.shape)
    print("交易历史:", transactions.shape)
    print("行为日志:", behavior_logs.shape)
    print("建模数据:", model_data.shape)
    print("\n建模数据列:", model_data.columns.tolist())
    print("\n前5行:")
    print(model_data.head())
