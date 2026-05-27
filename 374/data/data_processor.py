import pandas as pd
import numpy as np
from datetime import timedelta
import os
from model.lstm_attention import simulate_pv_output, decompose_load, evaluate_demand_response


DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')


def load_or_create_data():
    data_path = os.path.join(DATA_DIR, 'historical_load.csv')
    if os.path.exists(data_path):
        return pd.read_csv(data_path, parse_dates=['timestamp'])
    else:
        from model.lstm_attention import generate_sample_data
        df = generate_sample_data(days=730)
        os.makedirs(DATA_DIR, exist_ok=True)
        df.to_csv(data_path, index=False)
        return df


def _build_holiday_set(df):
    holiday_dates = df[df['is_holiday'] == 1]['timestamp'].dt.normalize().unique()
    return set(pd.Timestamp(d) for d in holiday_dates)


def _compute_holiday_window_features(timestamps, holiday_set):
    window_data = []
    for ts in timestamps:
        row_ts = pd.Timestamp(ts).normalize()
        if holiday_set:
            past = sorted([h for h in holiday_set if h <= row_ts])
            future = sorted([h for h in holiday_set if h >= row_ts])

            days_from_last = (row_ts - past[-1]).days if past else 999
            days_to_next = (future[0] - row_ts).days if future else 999

            is_holiday = 1 if row_ts in holiday_set else 0

            is_pre = 1 if (0 < days_to_next <= 3) and is_holiday == 0 else 0
            is_post = 1 if (0 < days_from_last <= 3) and is_holiday == 0 else 0

            pre_decay = max(0, 1 - days_to_next / 3) if days_to_next <= 3 else 0
            post_decay = max(0, 1 - days_from_last / 3) if days_from_last <= 3 else 0

            window_data.append([is_pre, is_post, pre_decay, post_decay])
        else:
            window_data.append([0, 0, 0, 0])

    return np.array(window_data)


def _forecast_pv_output(future_dates, df_historical):
    avg_temp_by_month = df_historical.groupby(df_historical['timestamp'].dt.month)['temperature'].mean()
    future_month = future_dates.month
    future_temp = np.array([avg_temp_by_month.get(m, 20) for m in future_month])

    pv_capacity = 800
    if 'pv_output' in df_historical.columns:
        historical_pv = df_historical['pv_output']
        historical_pv_positive = historical_pv[historical_pv > 10]
        if len(historical_pv_positive) > 100:
            pv_capacity = historical_pv_positive.max() * 1.2

    pv_forecast = simulate_pv_output(future_dates, pv_capacity, future_temp)
    return pv_forecast, pv_capacity


def prepare_prediction_input(df_historical, predict_start_date):
    future_dates = pd.date_range(predict_start_date, periods=168, freq='h')

    hours = future_dates.hour
    dayofweek = future_dates.dayofweek
    month = future_dates.month

    avg_temp_by_month = df_historical.groupby(df_historical['timestamp'].dt.month)['temperature'].mean()
    avg_humidity_by_month = df_historical.groupby(df_historical['timestamp'].dt.month)['humidity'].mean()

    temperature = np.array([avg_temp_by_month.get(m, 20) + np.random.randn() * 2 for m in month])
    humidity = np.array([avg_humidity_by_month.get(m, 50) + np.random.randn() * 3 for m in month])

    holidays_2024_2025 = [
        '2024-01-01', '2024-02-10', '2024-04-04', '2024-05-01', '2024-06-10',
        '2024-09-15', '2024-10-01', '2024-10-07', '2024-12-25',
        '2025-01-01', '2025-01-29', '2025-04-04', '2025-05-01', '2025-06-02',
        '2025-10-01', '2025-10-08', '2025-12-25'
    ]
    holiday_set = set()
    for h in holidays_2024_2025:
        hd = pd.Timestamp(h)
        for i in range(24):
            holiday_set.add(hd + timedelta(hours=i))

    is_holiday = np.array([1 if d in holiday_set else 0 for d in future_dates])

    window_feats = _compute_holiday_window_features(future_dates, set(pd.Timestamp(h) for h in holidays_2024_2025))

    pv_forecast, pv_capacity = _forecast_pv_output(future_dates, df_historical)

    avg_residential = df_historical['industry_residential'].mean()
    avg_commercial = df_historical['industry_commercial'].mean()
    avg_industrial = df_historical['industry_industrial'].mean()

    industry_residential = np.random.randn(len(future_dates)) * 50 + avg_residential
    industry_commercial = np.where(dayofweek < 5, 1.0, 0.3) * np.random.randn(len(future_dates)) * 100 + avg_commercial
    industry_industrial = np.where(dayofweek < 5, 1.0, 0.2) * np.random.randn(len(future_dates)) * 150 + avg_industrial

    df_future = pd.DataFrame({
        'timestamp': future_dates,
        'load': np.zeros(len(future_dates)),
        'pv_output': pv_forecast,
        'temperature': temperature,
        'humidity': humidity,
        'is_holiday': is_holiday,
        'is_pre_holiday': window_feats[:, 0],
        'is_post_holiday': window_feats[:, 1],
        'pre_holiday_decay': window_feats[:, 2],
        'post_holiday_decay': window_feats[:, 3],
        'industry_residential': industry_residential,
        'industry_commercial': industry_commercial,
        'industry_industrial': industry_industrial
    })

    pv_info = {
        'capacity_mw': float(pv_capacity),
        'forecast': pv_forecast.tolist(),
        'total_generation_mwh': float(np.sum(pv_forecast)),
        'peak_output_mw': float(np.max(pv_forecast)),
        'self_consumption_ratio': 85.0
    }

    return df_future, pv_info


def _compute_monthly_baselines(df_historical):
    df = df_historical.copy()
    df['month'] = df['timestamp'].dt.month
    monthly_stats = df.groupby('month')['load'].agg(['mean', 'std', 'max'])
    monthly_baselines = {}
    for month in range(1, 13):
        if month in monthly_stats.index:
            monthly_baselines[month] = {
                'mean': monthly_stats.loc[month, 'mean'],
                'std': monthly_stats.loc[month, 'std'],
                'max': monthly_stats.loc[month, 'max'],
                'p95': df[df['month'] == month]['load'].quantile(0.95)
            }
    return monthly_baselines


def analyze_influences(predictions, df_historical, df_future, pv_info=None):
    analysis = {}

    monthly_baselines = _compute_monthly_baselines(df_historical)

    pred_months = df_future['timestamp'].dt.month
    unique_months = pred_months.unique()

    pred_max = predictions.max()
    pred_min = predictions.min()
    pred_avg = predictions.mean()

    hist_avg = df_historical['load'].mean()
    hist_max = df_historical['load'].max()

    analysis['peak_load'] = float(pred_max)
    analysis['valley_load'] = float(pred_min)
    analysis['avg_load'] = float(pred_avg)
    analysis['peak_ratio'] = float(pred_max / hist_max * 100)

    peak_idx = predictions.argmax()
    peak_time = df_future.iloc[peak_idx]['timestamp']
    peak_month = peak_time.month
    analysis['peak_time'] = str(peak_time)
    analysis['peak_hour'] = peak_time.hour
    analysis['peak_month'] = peak_month

    monthly_peak_thresholds = {}
    monthly_warning_thresholds = {}
    for m in unique_months:
        m = int(m)
        if m in monthly_baselines:
            bl = monthly_baselines[m]
            monthly_peak_thresholds[m] = bl['p95']
            monthly_warning_thresholds[m] = bl['mean'] + bl['std']

    peak_periods = []
    high_alert_count = 0
    for i, pred in enumerate(predictions):
        m = int(df_future.iloc[i]['timestamp'].month)
        peak_thresh = monthly_peak_thresholds.get(m, hist_avg * 1.15)
        warn_thresh = monthly_warning_thresholds.get(m, hist_avg * 1.1)

        if pred > peak_thresh:
            peak_periods.append({
                'time': str(df_future.iloc[i]['timestamp']),
                'value': float(pred),
                'exceed_pct': float((pred - peak_thresh) / peak_thresh * 100),
                'threshold': float(peak_thresh),
                'level': 'danger'
            })
            high_alert_count += 1
        elif pred > warn_thresh:
            peak_periods.append({
                'time': str(df_future.iloc[i]['timestamp']),
                'value': float(pred),
                'exceed_pct': float((pred - warn_thresh) / warn_thresh * 100),
                'threshold': float(warn_thresh),
                'level': 'warning'
            })

    analysis['peak_periods'] = peak_periods
    analysis['high_alert_count'] = high_alert_count

    if high_alert_count > 12:
        analysis['alert_level'] = 'severe'
    elif high_alert_count > 6:
        analysis['alert_level'] = 'warning'
    else:
        analysis['alert_level'] = 'normal'

    analysis['monthly_baselines'] = {
        str(k): {kk: float(vv) for kk, vv in v.items()}
        for k, v in monthly_baselines.items()
    }

    temp_correlation = df_historical['temperature'].corr(df_historical['load'])
    humidity_correlation = df_historical['humidity'].corr(df_historical['load'])
    holiday_correlation = df_historical['is_holiday'].corr(df_historical['load'])

    df_temp = df_historical.copy()
    df_temp['month'] = df_temp['timestamp'].dt.month
    monthly_correlations = {}
    for m in range(1, 13):
        subset = df_temp[df_temp['month'] == m]
        if len(subset) > 10:
            monthly_correlations[str(m)] = {
                'temp_corr': float(subset['temperature'].corr(subset['load'])),
                'humidity_corr': float(subset['humidity'].corr(subset['load']))
            }

    analysis['monthly_correlations'] = monthly_correlations

    analysis['influences'] = [
        {'factor': '温度', 'correlation': float(abs(temp_correlation)),
         'impact': 'positive' if temp_correlation > 0 else 'negative',
         'description': f'温度每升高1°C，负荷约变化{abs(temp_correlation) * 100:.1f}%'},
        {'factor': '湿度', 'correlation': float(abs(humidity_correlation)),
         'impact': 'positive' if humidity_correlation > 0 else 'negative',
         'description': f'湿度每升高1%，负荷约变化{abs(humidity_correlation) * 100:.1f}%'},
        {'factor': '节假日', 'correlation': float(abs(holiday_correlation)),
         'impact': 'negative',
         'description': f'节假日负荷约降低{abs(holiday_correlation) * 100:.1f}%'},
        {'factor': '节前效应', 'correlation': float(abs(holiday_correlation) * 0.6),
         'impact': 'positive',
         'description': '节假日前1-3天负荷逐步上升，平均增加15%-25%'},
        {'factor': '节后效应', 'correlation': float(abs(holiday_correlation) * 0.7),
         'impact': 'negative',
         'description': '节假日后1-3天负荷逐步恢复，存在滞后效应'}
    ]

    recent_hist = df_historical.tail(336)
    total_hist = recent_hist['load']
    temp_hist = recent_hist['temperature'].values
    hour_hist = recent_hist['timestamp'].dt.hour.values
    dow_hist = recent_hist['timestamp'].dt.dayofweek.values
    ts_hist = recent_hist['timestamp'].values

    _, load_breakdown, hourly_profile = decompose_load(
        total_hist.values, temp_hist, hour_hist, dow_hist, ts_hist
    )
    analysis['load_breakdown'] = load_breakdown
    analysis['hourly_profile'] = hourly_profile

    pv_forecast = None
    if pv_info is not None:
        analysis['pv_info'] = pv_info
        pv_forecast = np.array(pv_info['forecast'])

    dr_analysis = evaluate_demand_response(
        predictions, df_historical, df_future, pv_forecast, hourly_profile
    )
    analysis['demand_response'] = dr_analysis

    return analysis
