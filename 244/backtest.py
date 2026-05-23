import pandas as pd
import numpy as np
from typing import Tuple, Dict, Optional
from config import N_GROUPS, REBALANCE_FREQ, HANDLE_SUSPEND, HANDLE_DELIST


class BacktestEngine:
    def __init__(self, returns: pd.DataFrame, 
                 suspend_data: pd.DataFrame = None,
                 delist_data: pd.Series = None,
                 industry_data: pd.Series = None,
                 mkt_cap_data: pd.DataFrame = None):
        self.returns = returns
        self.suspend_data = suspend_data
        self.delist_data = delist_data
        self.industry_data = industry_data
        self.mkt_cap_data = mkt_cap_data
        self.groups = None
        self.group_returns = None
        self.n_groups = N_GROUPS

    def get_rebalance_dates(self, start_date: str = None, 
                           end_date: str = None,
                           freq: str = REBALANCE_FREQ) -> pd.DatetimeIndex:
        if start_date is None:
            start_date = self.returns.index[0]
        if end_date is None:
            end_date = self.returns.index[-1]
        
        dates = self.returns.loc[start_date:end_date].index
        rebalance_dates = dates.to_series().resample(freq).last().dropna().index
        
        return rebalance_dates

    def _handle_suspend_delist(self, factor_df: pd.DataFrame, 
                               date: pd.Timestamp) -> pd.Series:
        factor_values = factor_df.loc[date].copy()
        
        if HANDLE_SUSPEND and self.suspend_data is not None:
            if date in self.suspend_data.index:
                suspended = self.suspend_data.loc[date][self.suspend_data.loc[date]].index
                factor_values.loc[suspended] = np.nan
        
        if HANDLE_DELIST and self.delist_data is not None:
            delisted = self.delist_data[self.delist_data <= date].index
            factor_values.loc[delisted] = np.nan
        
        return factor_values

    def _neutralize_industry_size(self, factor_values: pd.Series, 
                                  date: pd.Timestamp) -> pd.Series:
        if self.industry_data is None or self.mkt_cap_data is None:
            return factor_values
        
        valid_stocks = factor_values.dropna().index
        
        if len(valid_stocks) < 10:
            return factor_values
        
        industries = self.industry_data.reindex(valid_stocks).dropna()
        mkt_cap = self.mkt_cap_data.loc[date].reindex(valid_stocks).dropna()
        
        common_stocks = industries.index.intersection(mkt_cap.index).intersection(factor_values.index)
        
        if len(common_stocks) < 10:
            return factor_values
        
        y = factor_values.loc[common_stocks].values
        industry_dummies = pd.get_dummies(industries.loc[common_stocks]).values
        log_mkt_cap = np.log(mkt_cap.loc[common_stocks].values)
        
        X = np.column_stack([
            np.ones(len(common_stocks)),
            industry_dummies[:, 1:],
            log_mkt_cap
        ])
        
        try:
            beta = np.linalg.lstsq(X, y, rcond=None)[0]
            y_pred = X @ beta
            residual = y - y_pred
            
            result = factor_values.copy()
            result.loc[common_stocks] = residual
            return result
        except:
            return factor_values

    def _assign_groups_with_industry_neutral(self, factor_values: pd.Series,
                                             date: pd.Timestamp,
                                             ascending: bool = False) -> pd.Series:
        if self.industry_data is None:
            valid_values = factor_values.dropna()
            if len(valid_values) < self.n_groups:
                return pd.Series(dtype=float)
            
            if ascending:
                group_labels = pd.qcut(valid_values, self.n_groups, 
                                      labels=range(1, self.n_groups + 1))
            else:
                group_labels = pd.qcut(valid_values.rank(ascending=False), 
                                      self.n_groups, 
                                      labels=range(1, self.n_groups + 1))
            return group_labels
        
        valid_stocks = factor_values.dropna().index
        industries = self.industry_data.reindex(valid_stocks).dropna()
        
        common_stocks = industries.index.intersection(factor_values.dropna().index)
        
        if len(common_stocks) < self.n_groups * 2:
            return pd.Series(dtype=float)
        
        industry_groups = {}
        for industry in industries.unique():
            industry_stocks = industries[industries == industry].index
            industry_factor = factor_values.loc[industry_stocks].dropna()
            
            if len(industry_factor) >= self.n_groups:
                if ascending:
                    ig = pd.qcut(industry_factor, self.n_groups, 
                                labels=range(1, self.n_groups + 1))
                else:
                    ig = pd.qcut(industry_factor.rank(ascending=False), 
                                self.n_groups, 
                                labels=range(1, self.n_groups + 1))
                industry_groups[industry] = ig
        
        if not industry_groups:
            return pd.Series(dtype=float)
        
        all_group_labels = pd.concat(industry_groups.values())
        return all_group_labels

    def assign_groups(self, factor_df: pd.DataFrame,
                     rebalance_dates: pd.DatetimeIndex,
                     ascending: bool = False,
                     neutralize: bool = True,
                     industry_neutral: bool = True) -> pd.DataFrame:
        groups = pd.DataFrame(index=self.returns.index, 
                             columns=self.returns.columns,
                             dtype=float)
        
        for i, rebalance_date in enumerate(rebalance_dates):
            if i < len(rebalance_dates) - 1:
                start_idx = self.returns.index.get_loc(rebalance_date) + 1
                end_idx = self.returns.index.get_loc(rebalance_dates[i + 1]) + 1
            else:
                start_idx = self.returns.index.get_loc(rebalance_date) + 1
                end_idx = len(self.returns.index)
            
            if start_idx >= len(self.returns.index):
                continue
            
            factor_values = self._handle_suspend_delist(factor_df, rebalance_date)
            
            if neutralize:
                factor_values = self._neutralize_industry_size(factor_values, rebalance_date)
            
            if industry_neutral:
                group_labels = self._assign_groups_with_industry_neutral(
                    factor_values, rebalance_date, ascending
                )
            else:
                valid_values = factor_values.dropna()
                if len(valid_values) < self.n_groups:
                    continue
                if ascending:
                    group_labels = pd.qcut(valid_values, self.n_groups, 
                                          labels=range(1, self.n_groups + 1))
                else:
                    group_labels = pd.qcut(valid_values.rank(ascending=False), 
                                          self.n_groups, 
                                          labels=range(1, self.n_groups + 1))
            
            if len(group_labels) == 0:
                continue
            
            period_dates = self.returns.index[start_idx:end_idx]
            for date in period_dates:
                groups.loc[date, group_labels.index] = group_labels.values
        
        self.groups = groups
        return groups

    def calculate_group_returns(self, groups: pd.DataFrame = None,
                               weighting: str = 'equal') -> pd.DataFrame:
        if groups is None:
            groups = self.groups
        
        if groups is None:
            raise ValueError("Groups not assigned. Call assign_groups first.")
        
        group_returns = pd.DataFrame(index=self.returns.index,
                                    columns=range(1, self.n_groups + 1),
                                    dtype=float)
        
        for date in self.returns.index:
            date_groups = groups.loc[date]
            date_returns = self.returns.loc[date]
            
            for g in range(1, self.n_groups + 1):
                group_stocks = date_groups[date_groups == g].index
                
                if len(group_stocks) == 0:
                    group_returns.loc[date, g] = np.nan
                    continue
                
                stock_returns = date_returns.loc[group_stocks]
                valid_returns = stock_returns.dropna()
                
                if len(valid_returns) == 0:
                    group_returns.loc[date, g] = 0
                    continue
                
                if weighting == 'equal':
                    group_returns.loc[date, g] = valid_returns.mean()
                elif weighting == 'vw' and self.mkt_cap_data is not None:
                    if date in self.mkt_cap_data.index:
                        weights = self.mkt_cap_data.loc[date].loc[valid_returns.index]
                        weights = weights / weights.sum()
                        group_returns.loc[date, g] = (valid_returns * weights).sum()
                    else:
                        group_returns.loc[date, g] = valid_returns.mean()
                else:
                    group_returns.loc[date, g] = valid_returns.mean()
        
        self.group_returns = group_returns
        return group_returns

    def calculate_cumulative_returns(self, group_returns: pd.DataFrame = None) -> pd.DataFrame:
        if group_returns is None:
            group_returns = self.group_returns
        
        if group_returns is None:
            raise ValueError("Group returns not calculated. Call calculate_group_returns first.")
        
        cum_returns = (1 + group_returns.fillna(0)).cumprod()
        return cum_returns

    def calculate_spread_return(self, group_returns: pd.DataFrame = None,
                                long_group: int = 1, short_group: int = None) -> pd.Series:
        if group_returns is None:
            group_returns = self.group_returns
        
        if short_group is None:
            short_group = self.n_groups
        
        spread = group_returns[long_group] - group_returns[short_group]
        return spread

    def run_backtest(self, factor_df: pd.DataFrame,
                    start_date: str = None,
                    end_date: str = None,
                    rebalance_freq: str = REBALANCE_FREQ,
                    ascending: bool = False,
                    weighting: str = 'equal',
                    neutralize: bool = True,
                    industry_neutral: bool = True) -> Dict:
        rebalance_dates = self.get_rebalance_dates(start_date, end_date, rebalance_freq)
        
        print(f"Rebalance dates: {len(rebalance_dates)} periods")
        print(f"First rebalance: {rebalance_dates[0].date()}")
        print(f"Last rebalance: {rebalance_dates[-1].date()}")
        print(f"Industry neutralization: {'Enabled' if industry_neutral else 'Disabled'}")
        print(f"Size neutralization: {'Enabled' if neutralize else 'Disabled'}")
        
        groups = self.assign_groups(factor_df, rebalance_dates, ascending, neutralize, industry_neutral)
        group_returns = self.calculate_group_returns(groups, weighting)
        cum_returns = self.calculate_cumulative_returns(group_returns)
        spread = self.calculate_spread_return(group_returns)
        
        return {
            'groups': groups,
            'group_returns': group_returns,
            'cumulative_returns': cum_returns,
            'spread_return': spread,
            'rebalance_dates': rebalance_dates
        }


if __name__ == '__main__':
    from data_loader import DataLoader
    from factor_engine import FactorEngine
    
    loader = DataLoader()
    loader.generate_sample_data(n_stocks=100)
    price, factors, suspend, delist, industry = loader.load_data()
    returns = loader.calculate_daily_returns()
    mkt_cap = factors.get('MKT_CAP')
    
    engine = FactorEngine(factors)
    factor = engine.calculate_factor('1 / PE')
    
    factor_ffill = loader.forward_fill_factor_for_suspend(factor)
    
    backtest = BacktestEngine(returns, suspend, delist, industry, mkt_cap)
    results = backtest.run_backtest(factor_ffill, rebalance_freq='M', neutralize=True, industry_neutral=True)
    
    print(f"\nBacktest Results:")
    print(f"Group returns shape: {results['group_returns'].shape}")
    print(f"Final cumulative returns by group:")
    final_cum = results['cumulative_returns'].iloc[-1]
    for g in range(1, N_GROUPS + 1):
        print(f"  Group {g}: {final_cum[g]:.4f}")
