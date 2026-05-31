import pandas as pd
import numpy as np
from typing import Optional, Tuple
from config import Config

class DataLoader:
    def __init__(self):
        pass
    
    def load_from_csv(self, file_path: str) -> pd.DataFrame:
        df = pd.read_csv(file_path, parse_dates=['date'])
        df = df.sort_values(['date', 'asset']).reset_index(drop=True)
        return self._preprocess(df)
    
    def load_sample_data(self, n_assets: int = 50, n_days: int = 252) -> pd.DataFrame:
        np.random.seed(Config.RANDOM_SEED)
        dates = pd.date_range(start='2023-01-01', periods=n_days, freq='B')
        assets = [f'STOCK_{i:03d}' for i in range(n_assets)]
        
        data = []
        for asset in assets:
            prices = np.cumprod(1 + np.random.randn(n_days) * 0.02) * 100
            for i, date in enumerate(dates):
                data.append({
                    'date': date,
                    'asset': asset,
                    'open': prices[i] * (1 + np.random.randn() * 0.005),
                    'high': prices[i] * (1 + abs(np.random.randn()) * 0.01),
                    'low': prices[i] * (1 - abs(np.random.randn()) * 0.01),
                    'close': prices[i],
                    'volume': np.random.randint(100000, 1000000)
                })
        
        df = pd.DataFrame(data)
        return self._preprocess(df)
    
    def _preprocess(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.sort_values(['date', 'asset']).reset_index(drop=True)
        
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col not in df.columns:
                raise ValueError(f"Missing required column: {col}")
        
        df['returns'] = df.groupby('asset')['close'].pct_change()
        df['log_returns'] = df.groupby('asset')['close'].transform(lambda x: np.log(x / x.shift(1)))
        
        for window in [5, 10, 20, 60]:
            df[f'close_mean_{window}'] = df.groupby('asset')['close'].transform(
                lambda x: x.rolling(window).mean()
            )
            df[f'close_std_{window}'] = df.groupby('asset')['close'].transform(
                lambda x: x.rolling(window).std()
            )
            df[f'volume_mean_{window}'] = df.groupby('asset')['volume'].transform(
                lambda x: x.rolling(window).mean()
            )
        
        df['hl_range'] = (df['high'] - df['low']) / df['close']
        df['co_range'] = (df['close'] - df['open']) / df['open']
        
        df = df.dropna()
        return df
    
    def prepare_factor_data(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
        prices = df.pivot(index='date', columns='asset', values='close')
        returns = df.pivot(index='date', columns='asset', values='returns')
        
        forward_returns = returns.shift(-1)
        forward_returns = forward_returns.stack()
        
        return prices, forward_returns
