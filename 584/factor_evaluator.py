import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
from joblib import Parallel, delayed
import warnings
warnings.filterwarnings('ignore')
from config import Config

class TransactionCostModel:
    def __init__(self, 
                 base_fee: float = 0.0003,
                 slippage_factor: float = 0.0001,
                 market_impact_factor: float = 0.000001):
        self.base_fee = base_fee
        self.slippage_factor = slippage_factor
        self.market_impact_factor = market_impact_factor
    
    def calculate_cost(self, 
                       turnover: float,
                       position_size: float = 1.0,
                       volatility: float = 0.02) -> float:
        base_cost = turnover * self.base_fee
        slippage_cost = turnover * self.slippage_factor
        market_impact_cost = turnover * self.market_impact_factor * np.sqrt(abs(position_size) / 1e6) * volatility
        
        total_cost = base_cost + slippage_cost + market_impact_cost
        return total_cost

class FactorEvaluator:
    def __init__(self, n_jobs: int = None):
        self.n_jobs = n_jobs or Config.N_JOBS
        self.cost_model = TransactionCostModel()
    
    def calculate_ic(self, factor: pd.Series, forward_returns: pd.Series, 
                    periods: List[int] = None) -> Dict:
        periods = periods or Config.FACTOR_FORWARD_PERIODS
        results = {}
        
        aligned = pd.concat([factor, forward_returns], axis=1).dropna()
        if len(aligned) == 0:
            return {p: {'ic': np.nan, 'ir': np.nan} for p in periods}
        
        ic_series = aligned.groupby(level='date').apply(
            lambda x: x.iloc[:, 0].corr(x.iloc[:, 1])
        )
        
        results[1] = {
            'ic': ic_series.mean(),
            'ic_std': ic_series.std(),
            'ir': ic_series.mean() / ic_series.std() if ic_series.std() > 0 else np.nan,
            'ic_series': ic_series
        }
        
        return results
    
    def calculate_turnover(self, factor: pd.Series, window: int = 1) -> pd.Series:
        factor_unstacked = factor.unstack(level='asset')
        ranks = factor_unstacked.rank(axis=1, pct=True)
        
        turnover = ranks.diff().abs().mean(axis=1)
        
        return turnover
    
    def calculate_transaction_costs(self, 
                                     factor: pd.Series,
                                     portfolio_value: float = 1e8,
                                     volatility: float = None) -> Dict:
        turnover_series = self.calculate_turnover(factor)
        
        if volatility is None:
            volatility = 0.02
        
        daily_costs = turnover_series.apply(
            lambda x: self.cost_model.calculate_cost(
                x, position_size=portfolio_value, volatility=volatility
            )
        )
        
        annualized_turnover = turnover_series.mean() * 252
        annualized_cost = daily_costs.mean() * 252
        
        return {
            'turnover_series': turnover_series,
            'daily_costs': daily_costs,
            'daily_turnover': turnover_series.mean(),
            'annualized_turnover': annualized_turnover,
            'annualized_cost': annualized_cost,
            'cost_turnover_ratio': annualized_cost / (annualized_turnover + 1e-8)
        }
    
    def calculate_factor_returns(self, factor: pd.Series, 
                               forward_returns: pd.Series,
                               quantiles: int = 5,
                               include_transaction_costs: bool = True,
                               portfolio_value: float = 1e8) -> Dict:
        factor_df = factor.to_frame('factor')
        returns_df = forward_returns.to_frame('returns')
        
        merged = pd.concat([factor_df, returns_df], axis=1).dropna()
        
        merged['quantile'] = merged.groupby(level='date')['factor'].transform(
            lambda x: pd.qcut(x, q=quantiles, labels=False, duplicates='drop')
        )
        
        quantile_returns = merged.groupby(['date', 'quantile'])['returns'].mean().unstack()
        long_short = quantile_returns.iloc[:, -1] - quantile_returns.iloc[:, 0]
        
        cost_analysis = {}
        long_short_net = long_short
        
        if include_transaction_costs:
            cost_analysis = self.calculate_transaction_costs(
                factor, portfolio_value=portfolio_value
            )
            daily_costs = cost_analysis['daily_costs']
            long_short_net = long_short - daily_costs.reindex(long_short.index).fillna(0)
        
        return {
            'quantile_returns': quantile_returns,
            'long_short_returns': long_short,
            'long_short_returns_net': long_short_net,
            'long_short_cumulative': (1 + long_short).cumprod(),
            'long_short_cumulative_net': (1 + long_short_net).cumprod(),
            'annual_return': long_short.mean() * 252,
            'annual_return_net': long_short_net.mean() * 252,
            'annual_volatility': long_short.std() * np.sqrt(252),
            'sharpe': (long_short.mean() * 252) / (long_short.std() * np.sqrt(252)) if long_short.std() > 0 else np.nan,
            'sharpe_net': (long_short_net.mean() * 252) / (long_short_net.std() * np.sqrt(252)) if long_short_net.std() > 0 else np.nan,
            'cost_analysis': cost_analysis
        }
    
    def evaluate_factor(self, factor: pd.Series, forward_returns: pd.Series,
                        factor_name: str = 'factor',
                        include_transaction_costs: bool = True,
                        portfolio_value: float = 1e8) -> Dict:
        factor = factor.copy()
        factor.name = factor_name
        
        ic_results = self.calculate_ic(factor, forward_returns)
        turnover_series = self.calculate_turnover(factor)
        turnover = turnover_series.mean()
        returns_analysis = self.calculate_factor_returns(
            factor, forward_returns, 
            include_transaction_costs=include_transaction_costs,
            portfolio_value=portfolio_value
        )
        
        return {
            'name': factor_name,
            'ic_mean': ic_results[1]['ic'],
            'ir': ic_results[1]['ir'],
            'ic_series': ic_results[1]['ic_series'],
            'turnover': turnover,
            'turnover_series': turnover_series,
            'returns_analysis': returns_analysis
        }
    
    def evaluate_factors_parallel(self, factors: List[pd.Series], 
                                  forward_returns: pd.Series,
                                  factor_names: List[str] = None,
                                  include_transaction_costs: bool = True) -> List[Dict]:
        if factor_names is None:
            factor_names = [f'factor_{i}' for i in range(len(factors))]
        
        results = Parallel(n_jobs=self.n_jobs)(
            delayed(self.evaluate_factor)(
                factor, forward_returns, name, 
                include_transaction_costs=include_transaction_costs
            )
            for factor, name in zip(factors, factor_names)
        )
        
        return results
    
    def get_summary_table(self, evaluation_results: List[Dict]) -> pd.DataFrame:
        summary = []
        for res in evaluation_results:
            row = {
                '因子名称': res['name'],
                'IC均值': res['ic_mean'],
                'IR': res['ir'],
                '日换手率': res['turnover'],
                '年化换手率': res['turnover'] * 252,
            }
            
            cost_analysis = res['returns_analysis'].get('cost_analysis', {})
            if cost_analysis:
                row['年化交易成本'] = cost_analysis.get('annualized_cost', np.nan)
            
            row['年化收益(毛)'] = res['returns_analysis']['annual_return']
            row['年化收益(净)'] = res['returns_analysis']['annual_return_net']
            row['夏普(毛)'] = res['returns_analysis']['sharpe']
            row['夏普(净)'] = res['returns_analysis']['sharpe_net']
            
            summary.append(row)
        
        return pd.DataFrame(summary).round(4)
