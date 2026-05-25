import numpy as np
import pandas as pd
from scipy import stats
from collections import defaultdict
from datetime import timedelta


class MultiAssetAnalyzer:
    def __init__(self, co_anomaly_window=3, min_assets_for_systemic=2):
        self.co_anomaly_window = co_anomaly_window
        self.min_assets_for_systemic = min_assets_for_systemic
        self.asset_results = {}
        self.asset_names = []

    def add_asset_result(self, asset_name, result_df):
        self.asset_results[asset_name] = result_df.copy()
        if asset_name not in self.asset_names:
            self.asset_names.append(asset_name)

    def detect_co_anomalies(self):
        if len(self.asset_names) < 2:
            return [], pd.DataFrame()

        all_anomalies = []
        for asset_name in self.asset_names:
            df = self.asset_results[asset_name]
            anomaly_dates = df[df['is_anomaly']]['ds'].tolist()
            for date in anomaly_dates:
                all_anomalies.append({
                    'asset': asset_name,
                    'date': date,
                    'score': df[df['ds'] == date]['anomaly_score'].iloc[0],
                    'type': df[df['ds'] == date]['anomaly_type'].iloc[0]
                })

        if not all_anomalies:
            return [], pd.DataFrame()

        anomalies_df = pd.DataFrame(all_anomalies)
        anomalies_df = anomalies_df.sort_values('date')

        systemic_events = []
        used_indices = set()

        for i, row in anomalies_df.iterrows():
            if i in used_indices:
                continue

            window_start = row['date'] - timedelta(days=self.co_anomaly_window)
            window_end = row['date'] + timedelta(days=self.co_anomaly_window)

            window_anomalies = anomalies_df[
                (anomalies_df['date'] >= window_start) &
                (anomalies_df['date'] <= window_end)
            ]

            unique_assets = window_anomalies['asset'].nunique()

            if unique_assets >= self.min_assets_for_systemic:
                systemic_events.append({
                    'event_date': row['date'],
                    'window_start': window_start,
                    'window_end': window_end,
                    'assets_involved': unique_assets,
                    'asset_names': list(window_anomalies['asset'].unique()),
                    'total_anomalies': len(window_anomalies),
                    'avg_score': window_anomalies['score'].mean(),
                    'max_score': window_anomalies['score'].max(),
                    'severity': self._calculate_severity(unique_assets, window_anomalies['score'].mean()),
                    'anomaly_types': list(window_anomalies['type'].unique())
                })

                for idx in window_anomalies.index:
                    used_indices.add(idx)

        systemic_events_df = pd.DataFrame(systemic_events)
        if not systemic_events_df.empty:
            systemic_events_df = systemic_events_df.sort_values('event_date')

        return systemic_events, systemic_events_df

    def _calculate_severity(self, asset_count, avg_score):
        base = min(asset_count / len(self.asset_names), 1.0)
        score_factor = min(avg_score / 3.0, 1.0)
        severity = 0.6 * base + 0.4 * score_factor

        if severity > 0.7:
            return 'high'
        elif severity > 0.4:
            return 'medium'
        else:
            return 'low'

    def calculate_correlations(self):
        if len(self.asset_names) < 2:
            return pd.DataFrame()

        price_data = pd.DataFrame()
        for asset_name in self.asset_names:
            df = self.asset_results[asset_name]
            price_data[asset_name] = df.set_index('ds')['y']

        return price_data.corr()

    def calculate_anomaly_correlation(self):
        if len(self.asset_names) < 2:
            return pd.DataFrame()

        anomaly_data = pd.DataFrame()
        for asset_name in self.asset_names:
            df = self.asset_results[asset_name]
            anomaly_data[asset_name] = df.set_index('ds')['is_anomaly'].astype(int)

        return anomaly_data.corr()

    def get_summary(self):
        summary = {
            'total_assets': len(self.asset_names),
            'asset_names': self.asset_names,
            'total_anomalies_per_asset': {}
        }

        for asset_name in self.asset_names:
            df = self.asset_results[asset_name]
            summary['total_anomalies_per_asset'][asset_name] = {
                'total': int(df['is_anomaly'].sum()),
                'flash_crash': int((df['anomaly_type'] == 'flash_crash').sum()),
                'volatility_spike': int((df['anomaly_type'] == 'volatility_spike').sum()),
                'missing_data': int((df['anomaly_type'] == 'missing_data').sum()),
                'timestamp_gap': int((df['anomaly_type'] == 'timestamp_gap').sum())
            }

        return summary

    def get_systemic_risk_summary(self, systemic_events_df):
        if systemic_events_df.empty:
            return {}

        high_risk = len(systemic_events_df[systemic_events_df['severity'] == 'high'])
        medium_risk = len(systemic_events_df[systemic_events_df['severity'] == 'medium'])
        low_risk = len(systemic_events_df[systemic_events_df['severity'] == 'low'])

        most_affected = defaultdict(int)
        for assets in systemic_events_df['asset_names']:
            for asset in assets:
                most_affected[asset] += 1

        return {
            'total_systemic_events': len(systemic_events_df),
            'high_risk_events': high_risk,
            'medium_risk_events': medium_risk,
            'low_risk_events': low_risk,
            'most_affected_assets': dict(sorted(most_affected.items(), key=lambda x: -x[1])[:5]),
            'avg_assets_per_event': systemic_events_df['assets_involved'].mean()
        }
