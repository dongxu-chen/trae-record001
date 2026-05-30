import pandas as pd
import numpy as np
from typing import List, Tuple, Dict, Optional


def detect_user_cycle(user_df: pd.DataFrame) -> int:
    login_series = user_df.sort_values('date')['login_count'].values
    n = len(login_series)

    if n < 7:
        return max(1, n)

    autocorr_full = np.correlate(login_series - login_series.mean(), login_series - login_series.mean(), mode='full')
    autocorr_full = autocorr_full[n - 1:]
    autocorr_full = autocorr_full / autocorr_full[0] if autocorr_full[0] > 0 else autocorr_full

    search_range = min(n // 2, 15)
    if search_range < 2:
        return 3

    for lag in range(2, search_range + 1):
        if lag < len(autocorr_full) and autocorr_full[lag] > 0.3:
            return lag

    active_days = (login_series > 0).sum()
    if active_days > 0:
        return max(1, round(n / active_days))
    return 7


def calculate_window_features(
    df: pd.DataFrame,
    window_days: int,
    feature_cols: List[str]
) -> pd.DataFrame:
    df_sorted = df.sort_values(['user_id', 'date'])
    window_features = []

    for user_id, user_df in df_sorted.groupby('user_id'):
        user_df = user_df.set_index('date').sort_index()

        for col in feature_cols:
            user_df[f'{col}_rolling_mean_{window_days}d'] = (
                user_df[col].rolling(window=window_days, min_periods=1).mean()
            )
            user_df[f'{col}_rolling_std_{window_days}d'] = (
                user_df[col].rolling(window=window_days, min_periods=2).std()
            )
            user_df[f'{col}_rolling_max_{window_days}d'] = (
                user_df[col].rolling(window=window_days, min_periods=1).max()
            )
            user_df[f'{col}_rolling_min_{window_days}d'] = (
                user_df[col].rolling(window=window_days, min_periods=1).min()
            )
            user_df[f'{col}_rolling_sum_{window_days}d'] = (
                user_df[col].rolling(window=window_days, min_periods=1).sum()
            )

        user_df = user_df.reset_index()
        window_features.append(user_df)

    return pd.concat(window_features, ignore_index=True)


def calculate_adaptive_window_features(
    df: pd.DataFrame,
    user_cycles: pd.DataFrame,
    feature_cols: List[str]
) -> pd.DataFrame:
    df_sorted = df.sort_values(['user_id', 'date'])
    cycle_map = dict(zip(user_cycles['user_id'], user_cycles['activity_cycle_days']))
    adaptive_features = []

    for user_id, user_df in df_sorted.groupby('user_id'):
        user_df = user_df.set_index('date').sort_index()
        base_cycle = cycle_map.get(user_id, 7)

        windows = []
        windows.append(('1c', max(1, base_cycle)))
        windows.append(('2c', max(2, base_cycle * 2)))
        windows.append(('4c', max(3, min(base_cycle * 4, len(user_df)))))

        for win_label, win_days in windows:
            for col in feature_cols:
                user_df[f'{col}_rolling_mean_{win_label}'] = (
                    user_df[col].rolling(window=win_days, min_periods=1).mean()
                )
                user_df[f'{col}_rolling_std_{win_label}'] = (
                    user_df[col].rolling(window=win_days, min_periods=2).std()
                )
                user_df[f'{col}_rolling_max_{win_label}'] = (
                    user_df[col].rolling(window=win_days, min_periods=1).max()
                )
                user_df[f'{col}_rolling_min_{win_label}'] = (
                    user_df[col].rolling(window=win_days, min_periods=1).min()
                )
                user_df[f'{col}_rolling_sum_{win_label}'] = (
                    user_df[col].rolling(window=win_days, min_periods=1).sum()
                )

        user_df['detected_cycle_days'] = base_cycle
        user_df = user_df.reset_index()
        adaptive_features.append(user_df)

    return pd.concat(adaptive_features, ignore_index=True)


def calculate_time_series_features(
    df: pd.DataFrame,
    user_cycles: Optional[pd.DataFrame] = None
) -> pd.DataFrame:
    feature_cols = [
        'login_count',
        'session_duration_minutes',
        'feature_usage_count',
        'n_features_used'
    ]

    if user_cycles is not None and len(user_cycles) > 0:
        df = calculate_adaptive_window_features(df, user_cycles, feature_cols)
    else:
        df = calculate_window_features(df, 3, feature_cols)
        df = calculate_window_features(df, 7, feature_cols)
        df = calculate_window_features(df, 14, feature_cols)

    return df


def calculate_trend_features(df: pd.DataFrame) -> pd.DataFrame:
    df_sorted = df.sort_values(['user_id', 'date'])
    trend_features = []

    for user_id, user_df in df_sorted.groupby('user_id'):
        user_df = user_df.sort_values('date').reset_index(drop=True)

        for col in ['login_count', 'session_duration_minutes', 'feature_usage_count']:
            values = user_df[col].values
            days = np.arange(len(values))

            if len(values) >= 3:
                mask = values > 0
                if mask.sum() >= 2:
                    slope, _ = np.polyfit(days[mask], values[mask], 1)
                else:
                    slope = 0
            else:
                slope = 0

            user_df[f'{col}_trend_slope'] = slope

            recent_7d_mean = values[-7:].mean() if len(values) >= 7 else values.mean()
            prev_7d_mean = values[-14:-7].mean() if len(values) >= 14 else values.mean()
            user_df[f'{col}_mom_change'] = (
                recent_7d_mean - prev_7d_mean if prev_7d_mean > 0 else 0
            )
            user_df[f'{col}_mom_pct_change'] = (
                (recent_7d_mean - prev_7d_mean) / prev_7d_mean
                if prev_7d_mean > 0 else 0
            )

        trend_features.append(user_df)

    return pd.concat(trend_features, ignore_index=True)


def calculate_engagement_features(df: pd.DataFrame) -> pd.DataFrame:
    df_sorted = df.sort_values(['user_id', 'date'])
    engagement_features = []

    for user_id, user_df in df_sorted.groupby('user_id'):
        user_df = user_df.sort_values('date').reset_index(drop=True)

        login_days = (user_df['login_count'] > 0).sum()
        total_days = len(user_df)
        user_df['login_frequency'] = login_days / total_days if total_days > 0 else 0

        active_days = user_df[user_df['login_count'] > 0]
        if len(active_days) > 0:
            user_df['avg_session_duration'] = active_days['session_duration_minutes'].mean()
            user_df['avg_feature_usage'] = active_days['feature_usage_count'].mean()
            user_df['avg_features_used'] = active_days['n_features_used'].mean()
        else:
            user_df['avg_session_duration'] = 0
            user_df['avg_feature_usage'] = 0
            user_df['avg_features_used'] = 0

        last_login_idx = user_df[user_df['login_count'] > 0].index.max()
        if pd.notna(last_login_idx):
            user_df['days_since_last_login'] = len(user_df) - 1 - last_login_idx
        else:
            user_df['days_since_last_login'] = total_days

        login_streak = 0
        max_streak = 0
        streaks = []
        for _, row in user_df.iterrows():
            if row['login_count'] > 0:
                login_streak += 1
                max_streak = max(max_streak, login_streak)
            else:
                max_streak = max(max_streak, login_streak)
                login_streak = 0
            streaks.append(login_streak)

        user_df['current_login_streak'] = streaks
        user_df['max_login_streak'] = max_streak

        feature_cols = [
            'dashboard', 'analytics', 'reports', 'settings', 'search',
            'export', 'share', 'notifications', 'profile', 'help',
            'upload', 'download', 'edit', 'delete', 'create'
        ]

        feature_usage_counts = {f: 0 for f in feature_cols}
        for features_str in user_df['features_used'].dropna():
            if isinstance(features_str, str) and features_str:
                for f in features_str.split(','):
                    if f in feature_usage_counts:
                        feature_usage_counts[f] += 1

        for f in feature_cols:
            user_df[f'feature_{f}_used_count'] = feature_usage_counts[f]

        user_df['unique_features_used_total'] = sum(
            1 for v in feature_usage_counts.values() if v > 0
        )

        user_df['feature_diversity_score'] = (
            user_df['unique_features_used_total'] / len(feature_cols)
        )

        engagement_features.append(user_df)

    return pd.concat(engagement_features, ignore_index=True)


def calculate_recency_features(df: pd.DataFrame) -> pd.DataFrame:
    df_sorted = df.sort_values(['user_id', 'date'])
    recency_features = []

    for user_id, user_df in df_sorted.groupby('user_id'):
        user_df = user_df.sort_values('date', ascending=False).reset_index(drop=True)

        for col in ['login_count', 'session_duration_minutes', 'feature_usage_count']:
            user_df[f'{col}_last_1d'] = user_df[col].iloc[0] if len(user_df) > 0 else 0
            user_df[f'{col}_last_3d_avg'] = user_df[col].iloc[:3].mean() if len(user_df) >= 3 else user_df[col].mean()
            user_df[f'{col}_last_7d_avg'] = user_df[col].iloc[:7].mean() if len(user_df) >= 7 else user_df[col].mean()

        active_last_7d = (user_df['login_count'].iloc[:7] > 0).sum() if len(user_df) >= 7 else (user_df['login_count'] > 0).sum()
        user_df['active_days_last_7d'] = active_last_7d

        active_last_14d = (user_df['login_count'].iloc[:14] > 0).sum() if len(user_df) >= 14 else (user_df['login_count'] > 0).sum()
        user_df['active_days_last_14d'] = active_last_14d

        user_df['is_active_weekend'] = (
            user_df[user_df['login_count'] > 0]['date'].dt.dayofweek >= 5
        ).mean() if (user_df['login_count'] > 0).sum() > 0 else 0

        recency_features.append(user_df)

    return pd.concat(recency_features, ignore_index=True)


def calculate_channel_features(df: pd.DataFrame, channel_df: pd.DataFrame) -> pd.DataFrame:
    all_channels = ['email', 'push', 'sms', 'in_app', 'wechat', 'community']

    interaction_weights = {'open': 1.0, 'click': 2.0, 'reply': 3.0}
    channel_df['weight'] = channel_df['interaction_type'].map(interaction_weights)

    channel_scores = channel_df.groupby(['user_id', 'channel'])['weight'].sum().reset_index()
    channel_scores.columns = ['user_id', 'channel', 'channel_score']

    channel_pivot = channel_scores.pivot_table(
        index='user_id', columns='channel', values='channel_score', fill_value=0
    ).reset_index()

    for ch in all_channels:
        if ch not in channel_pivot.columns:
            channel_pivot[ch] = 0

    channel_pivot['total_channel_score'] = channel_pivot[all_channels].sum(axis=1)

    for ch in all_channels:
        channel_pivot[f'channel_{ch}_ratio'] = np.where(
            channel_pivot['total_channel_score'] > 0,
            channel_pivot[ch] / channel_pivot['total_channel_score'],
            0
        )

    sorted_channels = channel_pivot[all_channels].values
    best_idx = np.argsort(sorted_channels, axis=1)[:, ::-1]
    channel_names = np.array(all_channels)

    channel_pivot['preferred_channel'] = channel_names[best_idx[:, 0]]
    channel_pivot['second_channel'] = channel_names[best_idx[:, 1]]

    channel_pivot['channel_diversity'] = np.where(
        channel_pivot['total_channel_score'] > 0,
        (channel_pivot[all_channels] > 0).sum(axis=1) / len(all_channels),
        0
    )

    channel_agg = channel_df.groupby('user_id').agg(
        total_channel_interactions=('weight', 'sum'),
        unique_channels=('channel', 'nunique'),
    ).reset_index()

    channel_features = channel_pivot.merge(channel_agg, on='user_id', how='outer').fillna(0)

    rename_map = {ch: f'channel_{ch}_score' for ch in all_channels}
    channel_features = channel_features.rename(columns=rename_map)

    df = df.merge(channel_features, on='user_id', how='left')
    fill_cols = [c for c in df.columns if c.startswith('channel_')]
    df[fill_cols] = df[fill_cols].fillna(0)

    return df


def build_feature_matrix(
    behavior_df: pd.DataFrame,
    labels_df: pd.DataFrame = None,
    user_cycles: pd.DataFrame = None,
    channel_df: pd.DataFrame = None
) -> Tuple[pd.DataFrame, List[str]]:
    print("开始特征工程...")

    df = behavior_df.copy()
    df = calculate_time_series_features(df, user_cycles=user_cycles)
    print("时序特征计算完成 (自适应窗口)")

    df = calculate_trend_features(df)
    print("趋势特征计算完成")

    df = calculate_engagement_features(df)
    print("参与度特征计算完成")

    df = calculate_recency_features(df)
    print("新近度特征计算完成")

    if channel_df is not None and len(channel_df) > 0:
        df = calculate_channel_features(df, channel_df)
        print("渠道偏好特征计算完成")

    feature_cols = [col for col in df.columns if col not in [
        'user_id', 'date', 'features_used', 'user_segment',
        'preferred_channel', 'second_channel'
    ]]

    last_date_df = df.sort_values('date').groupby('user_id').last().reset_index()

    if labels_df is not None:
        user_labels = labels_df.groupby('user_id').agg({
            'active_level': lambda x: x.mode().iloc[0] if len(x.mode()) > 0 else x.iloc[0],
            'activity_score': 'mean'
        }).reset_index()

        feature_matrix = last_date_df.merge(user_labels, on='user_id', how='inner')

        level_mapping = {'low': 0, 'medium': 1, 'high': 2}
        feature_matrix['active_level_encoded'] = feature_matrix['active_level'].map(level_mapping)
    else:
        feature_matrix = last_date_df

    print(f"特征矩阵形状: {feature_matrix.shape}")
    print(f"特征数量: {len(feature_cols)}")

    return feature_matrix, feature_cols


def select_features_by_importance(
    feature_matrix: pd.DataFrame,
    feature_cols: List[str],
    top_k: int = 30
) -> List[str]:
    from sklearn.ensemble import RandomForestClassifier

    X = feature_matrix[feature_cols].fillna(0)
    y = feature_matrix['active_level_encoded']

    rf = RandomForestClassifier(n_estimators=100, random_state=42)
    rf.fit(X, y)

    importances = pd.DataFrame({
        'feature': feature_cols,
        'importance': rf.feature_importances_
    }).sort_values('importance', ascending=False)

    top_features = importances.head(top_k)['feature'].tolist()
    print(f"选择的Top {top_k} 特征:\n{top_features}")

    return top_features


if __name__ == '__main__':
    from data_generator import generate_all_data

    behavior_df, labels_df, channel_df, user_cycles = generate_all_data(n_users=50, history_days=30)
    feature_matrix, feature_cols = build_feature_matrix(behavior_df, labels_df, user_cycles=user_cycles, channel_df=channel_df)

    print("\n特征矩阵示例:")
    print(feature_matrix[['user_id', 'login_frequency', 'avg_session_duration',
                          'active_level', 'activity_score']].head(10))
    print("\n可用特征列表:")
    for i, col in enumerate(feature_cols[:20], 1):
        print(f"{i}. {col}")
    print(f"... 共 {len(feature_cols)} 个特征")
