import numpy as np
import pandas as pd
from collections import OrderedDict


class AnomalyAttributor:
    def __init__(self, lookback_window=20):
        self.lookback_window = lookback_window
        self.factor_names = [
            'price_volatility',
            'trend_deviation',
            'volume_spike',
            'price_jump',
            'prophet_residual',
            'seasonal_anomaly'
        ]

    def analyze(self, df, anomaly_idx, prophet_features=None):
        factors = OrderedDict()

        current_idx = anomaly_idx
        start_idx = max(0, current_idx - self.lookback_window)

        window = df.iloc[start_idx:current_idx + 1]
        current_price = df['y'].iloc[current_idx]

        factors['price_volatility'] = self._calculate_volatility_factor(window, current_idx)
        factors['trend_deviation'] = self._calculate_trend_deviation(window, current_price)
        factors['price_jump'] = self._calculate_price_jump(df, current_idx)
        factors['prophet_residual'] = self._calculate_prophet_factor(prophet_features, current_idx)
        factors['seasonal_anomaly'] = self._calculate_seasonal_factor(df, current_idx)

        if 'volume' in df.columns:
            factors['volume_spike'] = self._calculate_volume_factor(df, current_idx)
        else:
            factors['volume_spike'] = 0.0

        total = sum(v for v in factors.values() if not np.isnan(v))
        if total > 0:
            normalized_factors = {k: (v / total if not np.isnan(v) else 0) for k, v in factors.items()}
        else:
            normalized_factors = {k: 0 for k in factors.keys()}

        sorted_factors = OrderedDict(sorted(
            normalized_factors.items(),
            key=lambda x: -abs(x[1])
        ))

        dominant_factor = list(sorted_factors.keys())[0]
        dominant_contribution = sorted_factors[dominant_factor]

        explanation = self._generate_explanation(
            sorted_factors,
            df['y'].iloc[current_idx],
            df['ds'].iloc[current_idx]
        )

        return {
            'factors': sorted_factors,
            'dominant_factor': dominant_factor,
            'dominant_contribution': dominant_contribution,
            'explanation': explanation,
            'raw_values': factors
        }

    def _calculate_volatility_factor(self, window, current_idx):
        if len(window) < 5:
            return 0.0

        recent_returns = window['y'].pct_change().dropna()
        if len(recent_returns) < 3:
            return 0.0

        current_vol = np.std(recent_returns[-3:]) if len(recent_returns) >= 3 else 0
        historical_vol = np.std(recent_returns[:-3]) if len(recent_returns) > 3 else current_vol

        if historical_vol > 0:
            vol_ratio = current_vol / historical_vol
            return min(vol_ratio - 1, 2.0) / 2.0
        return 0.0

    def _calculate_trend_deviation(self, window, current_price):
        if len(window) < 10:
            return 0.0

        trend_line = np.polyfit(range(len(window)), window['y'].values, 1)
        predicted_price = np.polyval(trend_line, len(window) - 1)

        deviation = abs(current_price - predicted_price) / (abs(predicted_price) + 1e-8)
        return min(deviation, 1.0)

    def _calculate_price_jump(self, df, current_idx):
        if current_idx < 1:
            return 0.0

        price_change = abs(df['y'].iloc[current_idx] - df['y'].iloc[current_idx - 1])
        historical_changes = []
        for i in range(max(1, current_idx - 20), current_idx):
            historical_changes.append(abs(df['y'].iloc[i] - df['y'].iloc[i - 1]))

        if historical_changes:
            avg_change = np.mean(historical_changes)
            if avg_change > 0:
                jump_ratio = price_change / avg_change
                return min(jump_ratio / 5.0, 1.0)
        return 0.0

    def _calculate_prophet_factor(self, prophet_features, current_idx):
        if prophet_features is None or current_idx >= len(prophet_features):
            return 0.0

        residual = prophet_features['residual'].iloc[current_idx]
        residual_std = prophet_features['residual'].std()

        if residual_std > 0:
            z_score = abs(residual) / residual_std
            return min(z_score / 3.0, 1.0)
        return 0.0

    def _calculate_seasonal_factor(self, df, current_idx):
        if len(df) < 30:
            return 0.0

        day_of_week = df['ds'].iloc[current_idx].dayofweek
        same_dow = df[df['ds'].dt.dayofweek == day_of_week]

        if len(same_dow) > 5:
            dow_mean = same_dow['y'].mean()
            dow_std = same_dow['y'].std()
            if dow_std > 0:
                deviation = abs(df['y'].iloc[current_idx] - dow_mean) / dow_std
                return min(deviation / 2.0, 1.0)
        return 0.0

    def _calculate_volume_factor(self, df, current_idx):
        if current_idx < 5:
            return 0.0

        current_vol = df['volume'].iloc[current_idx]
        historical_vol = df['volume'].iloc[max(0, current_idx - 20):current_idx].mean()

        if historical_vol > 0:
            vol_ratio = current_vol / historical_vol
            return min(vol_ratio / 3.0, 1.0)
        return 0.0

    def _generate_explanation(self, factors, price, date):
        factor_names_cn = {
            'price_volatility': '价格波动率异常',
            'trend_deviation': '趋势偏离',
            'volume_spike': '成交量异常放大',
            'price_jump': '价格跳变',
            'prophet_residual': '模型预测残差',
            'seasonal_anomaly': '季节性异常'
        }

        top_factors = [(k, v) for k, v in factors.items() if v > 0.1][:3]

        if not top_factors:
            return "该异常由多种因素共同影响导致，无显著主导因素。"

        explanation_parts = []
        for factor, contrib in top_factors:
            explanation_parts.append(
                f"{factor_names_cn.get(factor, factor)}（贡献度{contrib*100:.1f}%）"
            )

        if len(explanation_parts) == 1:
            explanation = f"该异常主要由{explanation_parts[0]}导致。"
        else:
            explanation = f"该异常主要由{', '.join(explanation_parts[:-1])}和{explanation_parts[-1]}共同导致。"

        return explanation

    def batch_analyze(self, result_df, prophet_features=None):
        anomaly_indices = result_df[result_df['is_anomaly']].index.tolist()

        attribution_results = []
        for idx in anomaly_indices:
            result = self.analyze(result_df, idx, prophet_features)
            attribution_results.append({
                'date': result_df['ds'].iloc[idx],
                'index': idx,
                'price': result_df['y'].iloc[idx],
                'anomaly_score': result_df['anomaly_score'].iloc[idx],
                'anomaly_type': result_df['anomaly_type'].iloc[idx],
                **result
            })

        return pd.DataFrame(attribution_results)


class EventDetector:
    def __init__(self):
        self.event_database = pd.DataFrame(columns=[
            'date', 'event_type', 'event_name', 'impact_level', 'source'
        ])

    def add_event(self, date, event_type, event_name, impact_level='medium', source='manual'):
        new_event = pd.DataFrame({
            'date': [pd.to_datetime(date)],
            'event_type': [event_type],
            'event_name': [event_name],
            'impact_level': [impact_level],
            'source': [source]
        })
        self.event_database = pd.concat(
            [self.event_database, new_event], ignore_index=True
        )

    def find_related_events(self, anomaly_date, window_days=3):
        if self.event_database.empty:
            return pd.DataFrame()

        anomaly_date = pd.to_datetime(anomaly_date)
        window_start = anomaly_date - pd.Timedelta(days=window_days)
        window_end = anomaly_date + pd.Timedelta(days=window_days)

        related = self.event_database[
            (self.event_database['date'] >= window_start) &
            (self.event_database['date'] <= window_end)
        ].copy()

        related['days_from_anomaly'] = (related['date'] - anomaly_date).dt.days.abs()
        return related.sort_values('days_from_anomaly')

    def match_anomalies_with_events(self, result_df, window_days=3):
        matched = []
        for idx, row in result_df[result_df['is_anomaly']].iterrows():
            events = self.find_related_events(row['ds'], window_days)
            if not events.empty:
                matched.append({
                    'anomaly_date': row['ds'],
                    'anomaly_type': row['anomaly_type'],
                    'anomaly_score': row['anomaly_score'],
                    'matched_events': events.to_dict('records')
                })

        return matched
