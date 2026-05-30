import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from scipy import stats
from sklearn.linear_model import LinearRegression


class TrendAnalyzer:
    def __init__(self, price_history_df):
        self.df = price_history_df.copy()
        if not self.df.empty and 'date' in self.df.columns:
            self.df['date'] = pd.to_datetime(self.df['date'])
            self.df = self.df.sort_values('date')

    def compute_moving_averages(self, windows=None):
        if self.df.empty:
            return self.df
        if windows is None:
            windows = [7, 14, 30]
        for w in windows:
            if len(self.df) >= w:
                self.df[f'ma_{w}'] = self.df['price'].rolling(window=w, min_periods=1).mean()
        return self.df

    def compute_trend_direction(self):
        if self.df.empty or len(self.df) < 3:
            return {'direction': '数据不足', 'slope': 0, 'r_squared': 0}
        x = np.arange(len(self.df)).reshape(-1, 1)
        y = self.df['price'].values
        model = LinearRegression()
        model.fit(x, y)
        slope = model.coef_[0]
        r_squared = model.score(x, y)
        daily_change_pct = (slope / np.mean(y)) * 100

        if abs(daily_change_pct) < 0.05:
            direction = '横盘'
        elif daily_change_pct > 0:
            direction = '上涨'
        else:
            direction = '下降'

        return {
            'direction': direction,
            'slope': round(slope, 4),
            'daily_change_pct': round(daily_change_pct, 4),
            'r_squared': round(r_squared, 4),
            'trend_strength': '强' if r_squared > 0.7 else '中' if r_squared > 0.4 else '弱',
        }

    def compute_volatility(self):
        if self.df.empty or len(self.df) < 2:
            return {'volatility': 0, 'cv': 0, 'max_drawdown': 0}
        prices = self.df['price']
        returns = prices.pct_change().dropna()
        volatility = returns.std() if len(returns) > 0 else 0
        cv = (prices.std() / prices.mean()) * 100 if prices.mean() > 0 else 0
        cummax = prices.cummax()
        drawdown = (prices - cummax) / cummax
        max_drawdown = drawdown.min() * 100
        return {
            'volatility': round(volatility, 4),
            'cv': round(cv, 2),
            'max_drawdown': round(abs(max_drawdown), 2),
        }

    def detect_price_anomalies(self, threshold=2.0):
        if self.df.empty or len(self.df) < 5:
            return pd.DataFrame()
        prices = self.df['price']
        z_scores = np.abs(stats.zscore(prices))
        anomalies = self.df[z_scores > threshold].copy()
        anomalies['z_score'] = z_scores[z_scores > threshold]
        return anomalies

    def forecast_simple(self, days=7):
        if self.df.empty or len(self.df) < 5:
            return pd.DataFrame()
        x = np.arange(len(self.df)).reshape(-1, 1)
        y = self.df['price'].values
        model = LinearRegression()
        model.fit(x, y)
        last_date = self.df['date'].max()
        future_dates = [last_date + timedelta(days=i + 1) for i in range(days)]
        future_x = np.arange(len(self.df), len(self.df) + days).reshape(-1, 1)
        future_prices = model.predict(future_x)
        residuals = y - model.predict(x)
        std_err = residuals.std()
        forecast_df = pd.DataFrame({
            'date': future_dates,
            'predicted_price': np.round(future_prices, 2),
            'lower_bound': np.round(future_prices - 1.96 * std_err, 2),
            'upper_bound': np.round(future_prices + 1.96 * std_err, 2),
        })
        return forecast_df

    def compute_price_change_points(self):
        if self.df.empty or len(self.df) < 3:
            return pd.DataFrame()
        prices = self.df['price'].values
        changes = []
        for i in range(1, len(prices)):
            pct = ((prices[i] - prices[i - 1]) / prices[i - 1]) * 100
            if abs(pct) > 1.0:
                changes.append({
                    'date': self.df['date'].iloc[i],
                    'price': prices[i],
                    'change_pct': round(pct, 2),
                    'type': '涨价' if pct > 0 else '降价',
                })
        return pd.DataFrame(changes) if changes else pd.DataFrame()
