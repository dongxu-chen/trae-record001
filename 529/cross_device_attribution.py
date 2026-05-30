import pandas as pd
import numpy as np
from collections import defaultdict
import networkx as nx
from itertools import combinations


def analyze_device_coverage(touchpoints_df, users_df):
    device_stats = touchpoints_df.groupby('device').agg({
        'user_id': 'nunique',
        'channel': 'count',
        'converted': 'sum',
        'cost': 'sum'
    }).reset_index()
    
    device_stats.columns = [
        'device', 'unique_users', 'touchpoints', 
        'conversions_on_device', 'total_cost'
    ]
    
    device_stats['conversion_rate'] = (
        device_stats['conversions_on_device'] / device_stats['unique_users'] * 100
    ).round(2)
    
    device_stats['avg_cost_per_user'] = (
        device_stats['total_cost'] / device_stats['unique_users']
    ).round(2)
    
    device_users = touchpoints_df.groupby('user_id')['device'].nunique().reset_index()
    device_users.columns = ['user_id', 'n_devices_used']
    
    device_dist = device_users['n_devices_used'].value_counts().sort_index()
    
    login_stats = users_df.groupby('is_logged_in').agg({
        'user_id': 'count',
        'converted': 'sum',
        'conversion_value': 'sum',
        'n_devices': 'mean'
    }).reset_index()
    
    login_stats.columns = [
        'is_logged_in', 'total_users', 'conversions',
        'total_value', 'avg_devices'
    ]
    
    login_stats['conversion_rate'] = (
        login_stats['conversions'] / login_stats['total_users'] * 100
    ).round(2)
    
    return {
        'device_stats': device_stats,
        'device_distribution': device_dist,
        'login_stats': login_stats
    }


def build_device_graph(touchpoints_df, users_df):
    logged_in_users = users_df[users_df['is_logged_in'] == 1]['user_id'].tolist()
    logged_in_tp = touchpoints_df[touchpoints_df['user_id'].isin(logged_in_users)].copy()
    
    G = nx.Graph()
    
    for user_id, group in logged_in_tp.groupby('user_id'):
        devices = group['device_id'].unique()
        if len(devices) > 1:
            for d1, d2 in combinations(devices, 2):
                if G.has_edge(d1, d2):
                    G[d1][d2]['weight'] += 1
                else:
                    G.add_edge(d1, d2, weight=1, user_ids=[user_id])
                if user_id not in G[d1][d2]['user_ids']:
                    G[d1][d2]['user_ids'].append(user_id)
    
    for node in G.nodes():
        device_info = logged_in_tp[logged_in_tp['device_id'] == node].iloc[0]
        G.nodes[node]['device_type'] = device_info['device']
        G.nodes[node]['user_id'] = device_info['user_id']
    
    return G


def resolve_cross_device_identities(touchpoints_df, users_df):
    logged_in_users = users_df[users_df['is_logged_in'] == 1]['user_id'].tolist()
    
    device_to_user = {}
    for user_id, group in touchpoints_df.groupby('user_id'):
        for device_id in group['device_id'].unique():
            if user_id in logged_in_users:
                device_to_user[device_id] = user_id
    
    cross_device_summary = defaultdict(list)
    for device_id, user_id in device_to_user.items():
        cross_device_summary[user_id].append(device_id)
    
    cross_device_users = {
        user_id: device_ids 
        for user_id, device_ids in cross_device_summary.items()
        if len(device_ids) > 1
    }
    
    return device_to_user, cross_device_users


def unify_user_journeys_cross_device(touchpoints_df, users_df):
    device_to_user, cross_device_users = resolve_cross_device_identities(
        touchpoints_df, users_df
    )
    
    unified_tp = touchpoints_df.copy()
    unified_tp['original_user_id'] = unified_tp['user_id']
    
    for idx, row in unified_tp.iterrows():
        if row['is_logged_in'] == 0:
            continue
        device_id = row['device_id']
        if device_id in device_to_user:
            unified_tp.at[idx, 'user_id'] = device_to_user[device_id]
    
    unified_tp = unified_tp.sort_values(['user_id', 'timestamp']).reset_index(drop=True)
    
    unified_tp['touchpoint_position'] = unified_tp.groupby('user_id').cumcount() + 1
    unified_tp['total_touchpoints'] = unified_tp.groupby('user_id')['touchpoint_position'].transform('max')
    
    user_metrics = unified_tp.groupby('user_id').agg({
        'device_id': 'nunique',
        'device': lambda x: ' > '.join(x),
        'channel': lambda x: ' > '.join(x)
    }).reset_index()
    
    user_metrics.columns = [
        'user_id', 'n_devices_used', 'device_journey', 'channel_journey'
    ]
    
    return unified_tp, user_metrics, cross_device_users


def cross_device_last_touch_attribution(touchpoints_df, unified_tp, users_df):
    converted_users = users_df[users_df['converted'] == 1]['user_id'].tolist()
    
    converted_tp = unified_tp[unified_tp['user_id'].isin(converted_users)].copy()
    
    last_touches = converted_tp.sort_values('timestamp').groupby('user_id').last().reset_index()
    
    device_channel_attribution = last_touches.groupby(['device', 'channel']).agg({
        'user_id': 'count',
        'conversion_value': 'sum'
    }).reset_index()
    
    device_channel_attribution.columns = [
        'device', 'channel', 'conversions', 'total_value'
    ]
    
    device_attribution = last_touches.groupby('device').agg({
        'user_id': 'count',
        'conversion_value': 'sum'
    }).reset_index()
    
    device_attribution.columns = ['device', 'device_conversions', 'device_value']
    device_attribution['device_weight'] = (
        device_attribution['device_conversions'] / device_attribution['device_conversions'].sum()
    ).round(4)
    
    cross_device_stats = last_touches.groupby('user_id').agg({
        'device_id': 'nunique'
    }).reset_index()
    
    n_cross_device = (cross_device_stats['device_id'] > 1).sum()
    
    return {
        'device_channel_attribution': device_channel_attribution,
        'device_attribution': device_attribution,
        'cross_device_conversion_count': n_cross_device,
        'cross_device_conversion_rate': round(n_cross_device / len(converted_users) * 100, 2)
    }


def cross_device_attribution_analysis(touchpoints_df, users_df):
    if 'device' not in touchpoints_df.columns:
        raise ValueError("touchpoints_df must contain 'device' column for cross-device attribution")
    
    device_analysis = analyze_device_coverage(touchpoints_df, users_df)
    device_graph = build_device_graph(touchpoints_df, users_df)
    unified_tp, user_metrics, cross_device_users = unify_user_journeys_cross_device(
        touchpoints_df, users_df
    )
    attribution_results = cross_device_last_touch_attribution(
        touchpoints_df, unified_tp, users_df
    )
    
    cross_device_count = len(cross_device_users)
    cross_device_rate = round(cross_device_count / len(users_df) * 100, 2)
    
    conversion_value_by_devices = user_metrics.merge(
        users_df[['user_id', 'conversion_value', 'converted']], on='user_id'
    )
    
    multi_device_conv = conversion_value_by_devices[
        conversion_value_by_devices['n_devices_used'] > 1
    ]['conversion_value'].mean()
    
    single_device_conv = conversion_value_by_devices[
        conversion_value_by_devices['n_devices_used'] == 1
    ]['conversion_value'].mean()
    
    cross_device_lift = round((multi_device_conv - single_device_conv) / single_device_conv * 100, 2) if single_device_conv > 0 else 0
    
    summary = {
        'total_users': len(users_df),
        'logged_in_users': (users_df['is_logged_in'] == 1).sum(),
        'cross_device_users': cross_device_count,
        'cross_device_rate': cross_device_rate,
        'cross_device_conversion_rate': attribution_results['cross_device_conversion_rate'],
        'multi_device_avg_value': round(multi_device_conv, 2),
        'single_device_avg_value': round(single_device_conv, 2),
        'cross_device_value_lift': cross_device_lift,
        'device_graph_nodes': len(device_graph.nodes()),
        'device_graph_edges': len(device_graph.edges())
    }
    
    return {
        'summary': summary,
        'device_analysis': device_analysis,
        'unified_touchpoints': unified_tp,
        'user_metrics': user_metrics,
        'cross_device_users': cross_device_users,
        'attribution_results': attribution_results,
        'device_graph': device_graph
    }


if __name__ == '__main__':
    from data_generator import generate_attribution_data
    
    users_df, touchpoints_df = generate_attribution_data(n_users=1000)
    
    print("运行跨设备归因分析...")
    results = cross_device_attribution_analysis(touchpoints_df, users_df)
    
    print("\n=== 跨设备归因摘要 ===")
    for k, v in results['summary'].items():
        print(f"  {k}: {v}")
    
    print("\n=== 设备归因 ===")
    print(results['attribution_results']['device_attribution'])
