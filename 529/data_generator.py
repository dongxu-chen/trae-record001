import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import uuid


def generate_attribution_data(n_users=5000, seed=42):
    np.random.seed(seed)
    random.seed(seed)
    
    channels = [
        'Google Search', 'Facebook Ads', 'Instagram Ads', 
        'Email Marketing', 'Direct', 'Referral', 
        'YouTube Ads', 'TikTok Ads', 'LinkedIn Ads', 'Twitter Ads'
    ]
    
    devices = ['Mobile', 'Desktop', 'Tablet']
    device_prob = [0.55, 0.35, 0.10]
    
    channel_device_preference = {
        'Google Search': {'Mobile': 0.6, 'Desktop': 0.35, 'Tablet': 0.05},
        'Facebook Ads': {'Mobile': 0.7, 'Desktop': 0.25, 'Tablet': 0.05},
        'Instagram Ads': {'Mobile': 0.85, 'Desktop': 0.1, 'Tablet': 0.05},
        'Email Marketing': {'Mobile': 0.5, 'Desktop': 0.45, 'Tablet': 0.05},
        'Direct': {'Mobile': 0.5, 'Desktop': 0.4, 'Tablet': 0.1},
        'Referral': {'Mobile': 0.55, 'Desktop': 0.35, 'Tablet': 0.1},
        'YouTube Ads': {'Mobile': 0.65, 'Desktop': 0.3, 'Tablet': 0.05},
        'TikTok Ads': {'Mobile': 0.9, 'Desktop': 0.08, 'Tablet': 0.02},
        'LinkedIn Ads': {'Mobile': 0.4, 'Desktop': 0.55, 'Tablet': 0.05},
        'Twitter Ads': {'Mobile': 0.75, 'Desktop': 0.2, 'Tablet': 0.05}
    }
    
    channel_effectiveness = {
        'Google Search': 0.25,
        'Facebook Ads': 0.18,
        'Instagram Ads': 0.15,
        'Email Marketing': 0.20,
        'Direct': 0.30,
        'Referral': 0.22,
        'YouTube Ads': 0.12,
        'TikTok Ads': 0.10,
        'LinkedIn Ads': 0.08,
        'Twitter Ads': 0.07
    }
    
    channel_costs = {
        'Google Search': 2.5,
        'Facebook Ads': 1.8,
        'Instagram Ads': 2.0,
        'Email Marketing': 0.5,
        'Direct': 0.0,
        'Referral': 0.3,
        'YouTube Ads': 3.0,
        'TikTok Ads': 2.2,
        'LinkedIn Ads': 2.8,
        'Twitter Ads': 1.5
    }
    
    users_data = []
    touchpoints_data = []
    
    for user_id in range(1, n_users + 1):
        is_logged_in = 1 if random.random() < 0.6 else 0
        n_devices = np.random.choice([1, 2, 3], p=[0.5, 0.35, 0.15]) if is_logged_in else 1
        user_devices = random.sample(devices, n_devices) if is_logged_in else [random.choices(devices, device_prob)[0]]
        
        n_touchpoints = np.random.poisson(3) + 1
        user_channels = random.sample(channels, min(n_touchpoints, len(channels)))
        
        base_date = datetime(2024, 1, 1)
        time_deltas = sorted([np.random.uniform(0, 60) for _ in range(n_touchpoints)])
        
        conversion_prob = 0
        touchpoints_for_user = []
        
        for i, (channel, time_delta) in enumerate(zip(user_channels, time_deltas)):
            decay_factor = 1 - (i / max(n_touchpoints, 1)) * 0.3
            conversion_prob += channel_effectiveness[channel] * decay_factor * 0.3
            
            timestamp = base_date + timedelta(days=time_delta)
            cost = channel_costs[channel] * np.random.uniform(0.8, 1.2)
            
            device_prefs = channel_device_preference[channel]
            available_devices = list(device_prefs.keys())
            device_probs = [device_prefs[d] for d in available_devices]
            device = random.choices(available_devices, device_probs)[0]
            
            if is_logged_in and n_devices > 1 and random.random() < 0.4:
                device = random.choice(user_devices)
            
            device_id = str(uuid.uuid4())[:8]
            
            touchpoint = {
                'user_id': user_id,
                'timestamp': timestamp,
                'channel': channel,
                'cost': cost,
                'touchpoint_position': i + 1,
                'total_touchpoints': n_touchpoints,
                'device': device,
                'device_id': device_id,
                'is_logged_in': is_logged_in
            }
            touchpoints_for_user.append(touchpoint)
        
        converted = 1 if (conversion_prob > 0.25 or (conversion_prob > 0.1 and random.random() < 0.5)) else 0
        conversion_value = converted * np.random.uniform(50, 500)
        
        if converted:
            conversion_delay = np.random.exponential(2) + 1
            conversion_ts = base_date + timedelta(days=time_deltas[-1] + conversion_delay)
            conversion_device = random.choices(devices, device_prob)[0]
        else:
            conversion_ts = None
            conversion_device = None
        
        user_data = {
            'user_id': user_id,
            'converted': converted,
            'conversion_value': conversion_value,
            'total_touchpoints': n_touchpoints,
            'first_channel': user_channels[0],
            'last_channel': user_channels[-1],
            'conversion_timestamp': conversion_ts,
            'is_logged_in': is_logged_in,
            'n_devices': n_devices,
            'devices': ','.join(user_devices),
            'conversion_device': conversion_device
        }
        users_data.append(user_data)
        
        for tp in touchpoints_for_user:
            tp['converted'] = converted
            tp['conversion_value'] = conversion_value
            touchpoints_data.append(tp)
    
    users_df = pd.DataFrame(users_data)
    touchpoints_df = pd.DataFrame(touchpoints_data)
    touchpoints_df = touchpoints_df.sort_values(['user_id', 'timestamp']).reset_index(drop=True)
    
    return users_df, touchpoints_df


def get_user_journeys(touchpoints_df):
    journeys = touchpoints_df.groupby('user_id').agg({
        'channel': lambda x: ' > '.join(x),
        'timestamp': ['min', 'max'],
        'converted': 'first',
        'conversion_value': 'first',
        'cost': 'sum'
    }).reset_index()
    
    journeys.columns = [
        'user_id', 'journey', 'first_touch', 'last_touch',
        'converted', 'conversion_value', 'total_cost'
    ]
    return journeys


def calculate_conversion_cycle(touchpoints_df, users_df):
    converted_users = users_df[users_df['converted'] == 1].copy()
    
    first_touches = touchpoints_df.groupby('user_id')['timestamp'].min().reset_index()
    first_touches.columns = ['user_id', 'first_touch_time']
    
    converted_users = converted_users.merge(first_touches, on='user_id', how='left')
    converted_users = converted_users[converted_users['conversion_timestamp'].notna()]
    
    converted_users['conversion_cycle_days'] = (
        converted_users['conversion_timestamp'] - converted_users['first_touch_time']
    ).dt.total_seconds() / 86400
    
    converted_users['conversion_cycle_days'] = converted_users['conversion_cycle_days'].clip(lower=0)
    
    median_cycle = converted_users['conversion_cycle_days'].median()
    mean_cycle = converted_users['conversion_cycle_days'].mean()
    p75_cycle = converted_users['conversion_cycle_days'].quantile(0.75)
    p90_cycle = converted_users['conversion_cycle_days'].quantile(0.90)
    
    cycle_stats = {
        'median_days': round(median_cycle, 2),
        'mean_days': round(mean_cycle, 2),
        'p75_days': round(p75_cycle, 2),
        'p90_days': round(p90_cycle, 2),
        'recommended_window_days': round(median_cycle * 1.5, 2)
    }
    
    return cycle_stats, converted_users


def apply_attribution_window(touchpoints_df, users_df, window_days=None):
    if window_days is None:
        cycle_stats, _ = calculate_conversion_cycle(touchpoints_df, users_df)
        window_days = cycle_stats['recommended_window_days']
    
    converted_users = users_df[users_df['converted'] == 1].copy()
    converted_users = converted_users[converted_users['conversion_timestamp'].notna()]
    
    conversion_ts_map = converted_users.set_index('user_id')['conversion_timestamp'].to_dict()
    
    first_touch_map = touchpoints_df.groupby('user_id')['timestamp'].min().to_dict()
    
    filtered_touchpoints = []
    for user_id, group in touchpoints_df.groupby('user_id'):
        conv_ts = conversion_ts_map.get(user_id)
        first_ts = first_touch_map.get(user_id)
        
        if conv_ts is not None and group['converted'].iloc[0] == 1:
            cutoff = conv_ts - pd.Timedelta(days=window_days)
            window_group = group[group['timestamp'] >= cutoff].copy()
        else:
            window_group = group.copy()
        
        if len(window_group) > 0:
            window_group['total_touchpoints'] = len(window_group)
            window_group['touchpoint_position'] = range(1, len(window_group) + 1)
            filtered_touchpoints.append(window_group)
    
    if filtered_touchpoints:
        result = pd.concat(filtered_touchpoints, ignore_index=True)
    else:
        result = touchpoints_df.copy()
    
    return result, window_days


def calculate_channel_metrics(touchpoints_df):
    channel_summary = touchpoints_df.groupby('channel').agg({
        'user_id': 'nunique',
        'converted': 'sum',
        'conversion_value': 'sum',
        'cost': 'sum'
    }).reset_index()
    
    total_conversions = touchpoints_df[touchpoints_df['converted'] == 1]['user_id'].nunique()
    
    channel_summary.columns = [
        'channel', 'users_reached', 'touchpoint_conversions', 
        'total_conversion_value', 'total_cost'
    ]
    
    converted_users = touchpoints_df[touchpoints_df['converted'] == 1].groupby('channel')['user_id'].nunique()
    channel_summary['users_converted'] = channel_summary['channel'].map(converted_users).fillna(0)
    
    channel_summary['conversion_rate'] = (
        channel_summary['users_converted'] / channel_summary['users_reached'] * 100
    ).round(2)
    
    channel_summary['roi'] = (
        (channel_summary['total_conversion_value'] - channel_summary['total_cost']) / 
        channel_summary['total_cost'].replace(0, 1) * 100
    ).round(2)
    
    channel_summary['avg_value_per_user'] = (
        channel_summary['total_conversion_value'] / channel_summary['users_converted'].replace(0, 1)
    ).round(2)
    
    return channel_summary


if __name__ == '__main__':
    users_df, touchpoints_df = generate_attribution_data(n_users=1000)
    print("用户数据形状:", users_df.shape)
    print("接触点数据形状:", touchpoints_df.shape)
    print("\n转化率:", users_df['converted'].mean() * 100, "%")
    print("\n渠道统计:")
    print(calculate_channel_metrics(touchpoints_df))
