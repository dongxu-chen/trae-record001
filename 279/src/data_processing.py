import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf


class DataProcessor:
    def __init__(self):
        pass

    @staticmethod
    def load_from_csv(file_path, date_col='date', value_col='value'):
        df = pd.read_csv(file_path)
        df[date_col] = pd.to_datetime(df[date_col])
        df = df.sort_values(date_col)
        return df.rename(columns={date_col: 'ds', value_col: 'y'})

    @staticmethod
    def load_from_yfinance(ticker, start_date, end_date):
        data = yf.download(ticker, start=start_date, end=end_date)
        df = data['Close'].reset_index()
        df.columns = ['ds', 'y']
        return df

    @staticmethod
    def generate_mock_data(n_days=365,
                            start_date=None,
                            inject_anomalies=True):
        if start_date is None:
            start_date = datetime.now() - timedelta(days=n_days)

        dates = [start_date + timedelta(days=i) for i in range(n_days)]

        base_price = 100.0
        trend = np.linspace(0, 20, n_days)
        seasonality = 5 * np.sin(np.linspace(0, 4 * np.pi, n_days))
        noise = np.random.normal(0, 1, n_days)

        prices = base_price + trend + seasonality + noise

        df = pd.DataFrame({'ds': dates, 'y': prices})

        if inject_anomalies:
            df = DataProcessor._inject_anomalies(df)

        return df

    @staticmethod
    def _inject_anomalies(df):
        n = len(df)

        crash_idx = np.random.randint(n // 4, 3 * n // 4)
        df.loc[crash_idx:crash_idx + 3, 'y'] *= 0.7

        vol_idx = np.random.randint(n // 4, 3 * n // 4)
        while abs(vol_idx - crash_idx) < 20:
            vol_idx = np.random.randint(n // 4, 3 * n // 4)
        df.loc[vol_idx:vol_idx + 5, 'y'] += np.random.normal(0, 8, 6)

        missing_idx = np.random.randint(n // 4, 3 * n // 4)
        while abs(missing_idx - crash_idx) < 20 and abs(missing_idx - vol_idx) < 20:
            missing_idx = np.random.randint(n // 4, 3 * n // 4)
        df.loc[missing_idx:missing_idx + 2, 'y'] = np.nan

        return df

    @staticmethod
    def preprocess_data(df):
        df = df.copy()

        df['y'] = df['y'].interpolate(method='linear')

        df['missing'] = df['y'].isna().astype(int)

        df['y'] = df['y'].ffill().bfill()

        return df

    @staticmethod
    def create_sequences(data, seq_length=30):
        sequences = []
        for i in range(len(data) - seq_length + 1):
            sequences.append(data[i:i + seq_length])
        return np.array(sequences)

    @staticmethod
    def normalize_data(data):
        mean = np.mean(data)
        std = np.std(data)
        return (data - mean) / std, mean, std

    @staticmethod
    def denormalize_data(data, mean, std):
        return data * std + mean
