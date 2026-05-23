import pandas as pd
import numpy as np
import os
from typing import Dict, Tuple, Optional
from config import DATA_DIR, HANDLE_SUSPEND, HANDLE_DELIST, MAX_MISSING_RATIO


class DataLoader:
    def __init__(self, data_dir: str = DATA_DIR):
        self.data_dir = data_dir
        self.price_data = None
        self.factor_data = None
        self.suspend_data = None
        self.delist_data = None
        self.industry_data = None
        self.industries = ['金融', '地产', '消费', '医药', '科技', '制造', '能源', '材料']

    def generate_sample_data(self, n_stocks: int = 50, 
                            start_date: str = '2018-01-01',
                            end_date: str = '2023-12-31') -> None:
        dates = pd.date_range(start=start_date, end=end_date, freq='B')
        stocks = [f'STOCK_{i:03d}' for i in range(n_stocks)]
        
        np.random.seed(42)
        price_data = {}
        for stock in stocks:
            base_price = np.random.uniform(10, 100)
            returns = np.random.normal(0.0005, 0.02, len(dates))
            prices = base_price * np.cumprod(1 + returns)
            price_data[stock] = prices
        
        self.price_data = pd.DataFrame(price_data, index=dates)
        
        self.factor_data = {}
        self.factor_data['PE'] = pd.DataFrame(
            np.random.uniform(5, 50, (len(dates), n_stocks)),
            index=dates, columns=stocks
        )
        self.factor_data['PB'] = pd.DataFrame(
            np.random.uniform(0.5, 5, (len(dates), n_stocks)),
            index=dates, columns=stocks
        )
        self.factor_data['ROE'] = pd.DataFrame(
            np.random.uniform(-0.1, 0.3, (len(dates), n_stocks)),
            index=dates, columns=stocks
        )
        self.factor_data['MKT_CAP'] = pd.DataFrame(
            np.random.uniform(1e9, 1e12, (len(dates), n_stocks)),
            index=dates, columns=stocks
        )
        
        suspend_mask = np.random.choice([True, False], size=(len(dates), n_stocks), 
                                       p=[0.02, 0.98])
        self.suspend_data = pd.DataFrame(suspend_mask, index=dates, columns=stocks)
        
        delist_stocks = np.random.choice(stocks, size=int(n_stocks * 0.1), replace=False)
        delist_dates = np.random.choice(dates[int(len(dates)*0.5):], size=len(delist_stocks))
        self.delist_data = pd.Series(delist_dates, index=delist_stocks)
        
        self.industry_data = pd.Series(
            np.random.choice(self.industries, size=n_stocks),
            index=stocks,
            name='industry'
        )
        
        self._save_data()
        print(f"Sample data generated: {n_stocks} stocks from {start_date} to {end_date}")

    def _save_data(self) -> None:
        if self.price_data is not None:
            self.price_data.to_csv(os.path.join(self.data_dir, 'price_data.csv'))
        
        if self.factor_data is not None:
            for name, df in self.factor_data.items():
                df.to_csv(
                    os.path.join(self.data_dir, f'factor_{name}.csv')
                )
        
        if self.suspend_data is not None:
            self.suspend_data.to_csv(os.path.join(self.data_dir, 'suspend_data.csv'))
        
        if self.delist_data is not None:
            self.delist_data.to_csv(os.path.join(self.data_dir, 'delist_data.csv'))
        
        if self.industry_data is not None:
            self.industry_data.to_csv(os.path.join(self.data_dir, 'industry_data.csv'))

    def load_data(self) -> Tuple[pd.DataFrame, dict, pd.DataFrame, pd.Series, pd.Series]:
        price_path = os.path.join(self.data_dir, 'price_data.csv')
        
        if not os.path.exists(price_path):
            print("No data found, generating sample data...")
            self.generate_sample_data()
        
        self.price_data = pd.read_csv(price_path, index_col=0, parse_dates=True)
        
        factor_files = [f for f in os.listdir(self.data_dir) 
                       if f.startswith('factor_') and f.endswith('.csv')]
        self.factor_data = {}
        for f in factor_files:
            factor_name = f.replace('factor_', '').replace('.csv', '')
            self.factor_data[factor_name] = pd.read_csv(
                os.path.join(self.data_dir, f), 
                index_col=0, parse_dates=True
            )
        
        suspend_path = os.path.join(self.data_dir, 'suspend_data.csv')
        if os.path.exists(suspend_path):
            self.suspend_data = pd.read_csv(suspend_path, index_col=0, parse_dates=True)
            self.suspend_data = self.suspend_data.astype(bool)
        
        delist_path = os.path.join(self.data_dir, 'delist_data.csv')
        if os.path.exists(delist_path):
            self.delist_data = pd.read_csv(delist_path, index_col=0, 
                                          header=None, parse_dates=True,
                                          squeeze=True)
        
        industry_path = os.path.join(self.data_dir, 'industry_data.csv')
        if os.path.exists(industry_path):
            self.industry_data = pd.read_csv(industry_path, index_col=0, 
                                            header=None, squeeze=True)
            self.industry_data.name = 'industry'
        
        return self.price_data, self.factor_data, self.suspend_data, self.delist_data, self.industry_data

    def get_valid_stocks(self, date: pd.Timestamp) -> list:
        valid_stocks = self.price_data.columns.tolist()
        
        if HANDLE_SUSPEND and self.suspend_data is not None:
            if date in self.suspend_data.index:
                suspended = self.suspend_data.loc[date][self.suspend_data.loc[date]].index
                valid_stocks = [s for s in valid_stocks if s not in suspended]
        
        if HANDLE_DELIST and self.delist_data is not None:
            delisted = self.delist_data[self.delist_data <= date].index
            valid_stocks = [s for s in valid_stocks if s not in delisted]
        
        return valid_stocks

    def calculate_daily_returns(self) -> pd.DataFrame:
        if self.price_data is None:
            self.load_data()
        
        returns = self.price_data.pct_change()
        
        if HANDLE_SUSPEND and self.suspend_data is not None:
            returns = returns.mask(self.suspend_data, 0)
        
        if HANDLE_DELIST and self.delist_data is not None:
            for stock, delist_date in self.delist_data.items():
                if stock in returns.columns:
                    returns.loc[delist_date:, stock] = np.nan
        
        returns = returns.replace([np.inf, -np.inf], np.nan)
        
        return returns

    def filter_stocks_by_missing_ratio(self, df: pd.DataFrame, 
                                       max_ratio: float = MAX_MISSING_RATIO) -> pd.DataFrame:
        missing_ratio = df.isnull().mean()
        valid_stocks = missing_ratio[missing_ratio <= max_ratio].index
        return df[valid_stocks]

    def get_trading_dates(self) -> pd.DatetimeIndex:
        if self.price_data is None:
            self.load_data()
        return self.price_data.index

    def forward_fill_factor_for_suspend(self, factor_df: pd.DataFrame) -> pd.DataFrame:
        if self.suspend_data is None:
            return factor_df
        
        ffill_factor = factor_df.copy()
        
        for stock in factor_df.columns:
            if stock in self.suspend_data.columns:
                suspend_mask = self.suspend_data[stock].reindex(factor_df.index).fillna(False)
                ffill_factor.loc[suspend_mask, stock] = np.nan
                ffill_factor[stock] = ffill_factor[stock].ffill()
        
        return ffill_factor

    def calculate_forward_returns(self, periods: int = 1) -> pd.DataFrame:
        if self.price_data is None:
            self.load_data()
        
        returns = self.price_data.pct_change(periods).shift(-periods)
        
        returns = returns.replace([np.inf, -np.inf], np.nan)
        
        return returns


if __name__ == '__main__':
    loader = DataLoader()
    loader.generate_sample_data()
    price, factors, suspend, delist, industry = loader.load_data()
    print(f"Price data shape: {price.shape}")
    print(f"Available factors: {list(factors.keys())}")
    print(f"Suspend data shape: {suspend.shape}")
    print(f"Number of delisted stocks: {len(delist)}")
    print(f"Industry distribution:\n{industry.value_counts()}")
