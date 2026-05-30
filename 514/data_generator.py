import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Tuple, List


def generate_user_ids(n_users: int = 200) -> List[str]:
    return [f"user_{i:04d}" for i in range(1, n_users + 1)]


def generate_user_behavior_data(
    n_users: int = 200,
    history_days: int = 30,
    random_seed: int = 42
) -> pd.DataFrame:
    np.random.seed(random_seed)
    user_ids = generate_user_ids(n_users)
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=history_days - 1)
    date_range = pd.date_range(start=start_date, end=end_date, freq='D')

    user_segments = np.random.choice(
        ['high_active', 'medium_active', 'low_active', 'churn_risk'],
        size=n_users,
        p=[0.2, 0.4, 0.25, 0.15]
    )

    segment_params = {
        'high_active': {
            'login_prob': 0.95,
            'session_duration_mean': 45,
            'session_duration_std': 15,
            'feature_usage_mean': 12,
            'feature_usage_std': 3,
            'n_features_mean': 8,
            'channel_prefs': {
                'email': 0.85, 'push': 0.90, 'sms': 0.40,
                'in_app': 0.95, 'wechat': 0.70, 'community': 0.60,
            },
            'activity_cycle_days': 2,
        },
        'medium_active': {
            'login_prob': 0.65,
            'session_duration_mean': 25,
            'session_duration_std': 10,
            'feature_usage_mean': 6,
            'feature_usage_std': 2,
            'n_features_mean': 5,
            'channel_prefs': {
                'email': 0.60, 'push': 0.70, 'sms': 0.30,
                'in_app': 0.80, 'wechat': 0.50, 'community': 0.25,
            },
            'activity_cycle_days': 4,
        },
        'low_active': {
            'login_prob': 0.3,
            'session_duration_mean': 12,
            'session_duration_std': 6,
            'feature_usage_mean': 2,
            'feature_usage_std': 1,
            'n_features_mean': 2,
            'channel_prefs': {
                'email': 0.35, 'push': 0.30, 'sms': 0.20,
                'in_app': 0.40, 'wechat': 0.25, 'community': 0.10,
            },
            'activity_cycle_days': 7,
        },
        'churn_risk': {
            'login_prob': 0.1,
            'session_duration_mean': 5,
            'session_duration_std': 3,
            'feature_usage_mean': 1,
            'feature_usage_std': 0.5,
            'n_features_mean': 1,
            'channel_prefs': {
                'email': 0.15, 'push': 0.10, 'sms': 0.25,
                'in_app': 0.05, 'wechat': 0.10, 'community': 0.02,
            },
            'activity_cycle_days': 10,
        }
    }

    records = []
    channel_interaction_records = []
    all_channels = ['email', 'push', 'sms', 'in_app', 'wechat', 'community']

    for user_idx, user_id in enumerate(user_ids):
        segment = user_segments[user_idx]
        params = segment_params[segment]
        channel_prefs = params['channel_prefs']

        user_channel_noise = {ch: np.random.uniform(-0.1, 0.1) for ch in all_channels}
        user_channel_prefs = {ch: max(0, min(1, channel_prefs[ch] + user_channel_noise[ch])) for ch in all_channels}

        trend = np.random.uniform(-0.01, 0.02)
        volatility = np.random.uniform(0.8, 1.2)

        for day_idx, date in enumerate(date_range):
            day_factor = 1 + trend * day_idx / history_days
            login_prob = min(0.99, max(0.01, params['login_prob'] * day_factor * volatility))

            if np.random.random() < login_prob:
                session_duration = max(1, np.random.normal(
                    params['session_duration_mean'] * day_factor,
                    params['session_duration_std']
                ))
                feature_usage_count = max(0, int(np.random.normal(
                    params['feature_usage_mean'] * day_factor,
                    params['feature_usage_std']
                )))
                n_features_used = max(1, min(15, int(np.random.normal(
                    params['n_features_mean'], 1
                ))))

                features_used = np.random.choice(
                    ['dashboard', 'analytics', 'reports', 'settings',
                     'search', 'export', 'share', 'notifications',
                     'profile', 'help', 'upload', 'download',
                     'edit', 'delete', 'create'],
                    size=n_features_used,
                    replace=False
                ).tolist()

                records.append({
                    'user_id': user_id,
                    'date': date,
                    'login_count': 1,
                    'session_duration_minutes': round(session_duration, 1),
                    'feature_usage_count': feature_usage_count,
                    'features_used': ','.join(features_used),
                    'n_features_used': n_features_used,
                    'user_segment': segment,
                })
            else:
                records.append({
                    'user_id': user_id,
                    'date': date,
                    'login_count': 0,
                    'session_duration_minutes': 0,
                    'feature_usage_count': 0,
                    'features_used': '',
                    'n_features_used': 0,
                    'user_segment': segment,
                })

            for ch in all_channels:
                if np.random.random() < user_channel_prefs[ch] * 0.15:
                    channel_interaction_records.append({
                        'user_id': user_id,
                        'date': date,
                        'channel': ch,
                        'interaction_type': np.random.choice(
                            ['open', 'click', 'reply'], p=[0.5, 0.35, 0.15]
                        ),
                    })

    df = pd.DataFrame(records)
    df['date'] = pd.to_datetime(df['date'])

    weekend_mask = df['date'].dt.dayofweek >= 5
    df.loc[weekend_mask, 'session_duration_minutes'] *= 0.7
    df.loc[weekend_mask, 'feature_usage_count'] = (
        df.loc[weekend_mask, 'feature_usage_count'] * 0.6
    ).astype(int)

    df['session_duration_minutes'] = df['session_duration_minutes'].round(1)

    channel_df = pd.DataFrame(channel_interaction_records)
    if len(channel_df) > 0:
        channel_df['date'] = pd.to_datetime(channel_df['date'])

    user_cycles = pd.DataFrame({
        'user_id': user_ids,
        'activity_cycle_days': [segment_params[user_segments[i]]['activity_cycle_days']
                                for i in range(n_users)]
    })

    return df, channel_df, user_cycles


def generate_future_labels(
    df: pd.DataFrame,
    future_days: int = 7
) -> pd.DataFrame:
    user_segments = df.groupby('user_id')['user_segment'].first()

    last_date = df['date'].max()
    future_start = last_date + timedelta(days=1)
    future_end = last_date + timedelta(days=future_days)
    future_dates = pd.date_range(start=future_start, end=future_end, freq='D')

    label_records = []
    for user_id in df['user_id'].unique():
        segment = user_segments[user_id]

        if segment == 'high_active':
            avg_daily_activity = np.random.uniform(70, 100)
        elif segment == 'medium_active':
            avg_daily_activity = np.random.uniform(35, 70)
        elif segment == 'low_active':
            avg_daily_activity = np.random.uniform(10, 35)
        else:
            avg_daily_activity = np.random.uniform(0, 15)

        for date in future_dates:
            day_factor = np.random.uniform(0.8, 1.2)
            daily_activity = max(0, min(100, avg_daily_activity * day_factor))

            if daily_activity >= 60:
                active_level = 'high'
            elif daily_activity >= 25:
                active_level = 'medium'
            else:
                active_level = 'low'

            label_records.append({
                'user_id': user_id,
                'date': date,
                'activity_score': round(daily_activity, 1),
                'active_level': active_level,
            })

    labels_df = pd.DataFrame(label_records)
    labels_df['date'] = pd.to_datetime(labels_df['date'])

    return labels_df


def generate_all_data(
    n_users: int = 200,
    history_days: int = 30,
    future_days: int = 7,
    random_seed: int = 42
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    behavior_df, channel_df, user_cycles = generate_user_behavior_data(n_users, history_days, random_seed)
    labels_df = generate_future_labels(behavior_df, future_days)
    return behavior_df, labels_df, channel_df, user_cycles


if __name__ == '__main__':
    behavior_df, labels_df, channel_df, user_cycles = generate_all_data()
    print("行为数据形状:", behavior_df.shape)
    print("\n行为数据示例:")
    print(behavior_df.head(10))
    print("\n渠道交互数据形状:", channel_df.shape)
    print("\n渠道交互示例:")
    print(channel_df.head(10))
    print("\n用户活跃周期示例:")
    print(user_cycles.head(10))
    print("\n活跃等级分布:")
    print(labels_df.groupby('user_id')['active_level'].first().value_counts())
