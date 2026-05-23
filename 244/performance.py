import pandas as pd
import numpy as np
from typing import Dict, Tuple
from config import TRADING_DAYS, RISK_FREE_RATE, N_GROUPS


class PerformanceAnalyzer:
    def __init__(self, returns: pd.DataFrame = None):
        self.returns = returns

    def calculate_annualized_return(self, returns: pd.Series) -> float:
        if returns is None or len(returns) == 0:
            return np.nan
        
        cum_return = (1 + returns.fillna(0)).prod()
        n_days = len(returns)
        annualized = (cum_return ** (TRADING_DAYS / n_days)) - 1
        return annualized

    def calculate_sharpe_ratio(self, returns: pd.Series, 
                               risk_free_rate: float = RISK_FREE_RATE) -> float:
        if returns is None or len(returns) == 0:
            return np.nan
        
        excess_returns = returns - risk_free_rate / TRADING_DAYS
        sharpe = np.sqrt(TRADING_DAYS) * excess_returns.mean() / excess_returns.std()
        return sharpe

    def calculate_max_drawdown(self, returns: pd.Series) -> Tuple[float, pd.Timestamp, pd.Timestamp]:
        if returns is None or len(returns) == 0:
            return np.nan, pd.NaT, pd.NaT
        
        cum_returns = (1 + returns.fillna(0)).cumprod()
        running_max = cum_returns.cummax()
        drawdown = (cum_returns - running_max) / running_max
        
        max_dd = drawdown.min()
        
        end_idx = drawdown.argmin()
        start_idx = cum_returns.iloc[:end_idx + 1].argmax()
        
        return max_dd, drawdown.index[start_idx], drawdown.index[end_idx]

    def calculate_volatility(self, returns: pd.Series) -> float:
        if returns is None or len(returns) == 0:
            return np.nan
        
        return returns.std() * np.sqrt(TRADING_DAYS)

    def calculate_win_rate(self, returns: pd.Series) -> float:
        if returns is None or len(returns) == 0:
            return np.nan
        
        valid_returns = returns.dropna()
        return (valid_returns > 0).mean()

    def analyze_group_performance(self, group_returns: pd.DataFrame) -> pd.DataFrame:
        metrics = []
        
        for group in group_returns.columns:
            returns = group_returns[group]
            ann_return = self.calculate_annualized_return(returns)
            sharpe = self.calculate_sharpe_ratio(returns)
            max_dd, dd_start, dd_end = self.calculate_max_drawdown(returns)
            vol = self.calculate_volatility(returns)
            win_rate = self.calculate_win_rate(returns)
            
            metrics.append({
                'Group': group,
                'Annualized Return': ann_return,
                'Volatility': vol,
                'Sharpe Ratio': sharpe,
                'Max Drawdown': max_dd,
                'Win Rate': win_rate,
                'Total Return': (1 + returns.fillna(0)).prod() - 1
            })
        
        result_df = pd.DataFrame(metrics).set_index('Group')
        return result_df

    def calculate_period_returns(self, returns: pd.DataFrame, 
                                  rebalance_dates: pd.DatetimeIndex) -> pd.DataFrame:
        period_returns = pd.DataFrame(index=rebalance_dates[:-1], 
                                     columns=returns.columns,
                                     dtype=float)
        
        for i in range(len(rebalance_dates) - 1):
            start_date = rebalance_dates[i]
            end_date = rebalance_dates[i + 1]
            
            period_ret = (1 + returns.loc[start_date:end_date].fillna(0)).prod() - 1
            period_returns.loc[start_date] = period_ret
        
        return period_returns

    def calculate_ic_by_rebalance(self, factor_df: pd.DataFrame,
                                   returns: pd.DataFrame,
                                   rebalance_dates: pd.DatetimeIndex) -> pd.Series:
        ic_series = pd.Series(index=rebalance_dates[:-1], dtype=float)
        
        period_returns = self.calculate_period_returns(returns, rebalance_dates)
        
        for i, rebalance_date in enumerate(rebalance_dates[:-1]):
            factor_values = factor_df.loc[rebalance_date].dropna()
            period_ret = period_returns.loc[rebalance_date].dropna()
            
            common_stocks = factor_values.index.intersection(period_ret.index)
            
            if len(common_stocks) < 10:
                ic_series.loc[rebalance_date] = np.nan
                continue
            
            f = factor_values.loc[common_stocks]
            r = period_ret.loc[common_stocks]
            
            ic = f.corr(r, method='spearman')
            ic_series.loc[rebalance_date] = ic
        
        return ic_series

    def calculate_ic(self, factor_df: pd.DataFrame, 
                     returns: pd.DataFrame, 
                     periods: int = 1) -> pd.Series:
        shifted_factor = factor_df.shift(periods)
        
        ic_series = pd.Series(index=factor_df.index, dtype=float)
        
        for date in factor_df.index:
            factor_values = shifted_factor.loc[date].dropna()
            return_values = returns.loc[date].dropna()
            
            common_stocks = factor_values.index.intersection(return_values.index)
            
            if len(common_stocks) < 10:
                ic_series.loc[date] = np.nan
                continue
            
            f = factor_values.loc[common_stocks]
            r = return_values.loc[common_stocks]
            
            ic = f.corr(r, method='spearman')
            ic_series.loc[date] = ic
        
        return ic_series

    def calculate_ic_stats(self, ic_series: pd.Series) -> Dict:
        valid_ic = ic_series.dropna()
        
        if len(valid_ic) == 0:
            return {
                'Mean IC': np.nan,
                'Std IC': np.nan,
                'IR': np.nan,
                'IC > 0': np.nan,
                'IC < 0': np.nan,
                'T-Statistic': np.nan,
                'P-Value': np.nan,
                'N_Obs': 0
            }
        
        from scipy import stats
        t_stat, p_value = stats.ttest_1samp(valid_ic, 0)
        
        return {
            'Mean IC': valid_ic.mean(),
            'Std IC': valid_ic.std(),
            'IR': valid_ic.mean() / valid_ic.std() if valid_ic.std() != 0 else np.nan,
            'IC > 0': (valid_ic > 0).mean(),
            'IC < 0': (valid_ic < 0).mean(),
            'T-Statistic': t_stat,
            'P-Value': p_value,
            'N_Obs': len(valid_ic)
        }

    def calculate_rank_ic(self, factor_df: pd.DataFrame, 
                          returns: pd.DataFrame,
                          periods: int = 1) -> pd.Series:
        return self.calculate_ic(factor_df, returns, periods)

    def analyze_spread(self, spread_returns: pd.Series) -> Dict:
        ann_return = self.calculate_annualized_return(spread_returns)
        sharpe = self.calculate_sharpe_ratio(spread_returns)
        max_dd, dd_start, dd_end = self.calculate_max_drawdown(spread_returns)
        vol = self.calculate_volatility(spread_returns)
        win_rate = self.calculate_win_rate(spread_returns)
        
        return {
            'Annualized Return': ann_return,
            'Volatility': vol,
            'Sharpe Ratio': sharpe,
            'Max Drawdown': max_dd,
            'Max Drawdown Start': dd_start,
            'Max Drawdown End': dd_end,
            'Win Rate': win_rate,
            'Total Return': (1 + spread_returns.fillna(0)).prod() - 1
        }

    def generate_report(self, backtest_results: Dict, 
                        factor_df: pd.DataFrame,
                        returns: pd.DataFrame) -> Dict:
        group_returns = backtest_results['group_returns']
        spread_returns = backtest_results['spread_return']
        rebalance_dates = backtest_results['rebalance_dates']
        
        group_performance = self.analyze_group_performance(group_returns)
        spread_performance = self.analyze_spread(spread_returns)
        
        ic_rebalance = self.calculate_ic_by_rebalance(factor_df, returns, rebalance_dates)
        ic_stats_rebalance = self.calculate_ic_stats(ic_rebalance)
        
        ic_1d = self.calculate_ic(factor_df, returns, periods=1)
        ic_5d = self.calculate_ic(factor_df, returns, periods=5)
        ic_20d = self.calculate_ic(factor_df, returns, periods=20)
        
        ic_stats_1d = self.calculate_ic_stats(ic_1d)
        ic_stats_5d = self.calculate_ic_stats(ic_5d)
        ic_stats_20d = self.calculate_ic_stats(ic_20d)
        
        return {
            'group_performance': group_performance,
            'spread_performance': spread_performance,
            'ic_series': {
                'rebalance': ic_rebalance,
                '1d': ic_1d,
                '5d': ic_5d,
                '20d': ic_20d
            },
            'ic_stats': {
                'rebalance': ic_stats_rebalance,
                '1d': ic_stats_1d,
                '5d': ic_stats_5d,
                '20d': ic_stats_20d
            }
        }

    def print_report(self, report: Dict, factor_name: str = '') -> None:
        print("=" * 80)
        print(f"FACTOR BACKTEST REPORT: {factor_name}")
        print("=" * 80)
        
        print("\n【 GROUP PERFORMANCE 】")
        print("-" * 80)
        group_perf = report['group_performance'].copy()
        for col in ['Annualized Return', 'Volatility', 'Max Drawdown', 'Total Return']:
            group_perf[col] = group_perf[col].apply(lambda x: f"{x*100:.2f}%")
        group_perf['Sharpe Ratio'] = group_perf['Sharpe Ratio'].apply(lambda x: f"{x:.2f}")
        group_perf['Win Rate'] = group_perf['Win Rate'].apply(lambda x: f"{x*100:.2f}%")
        print(group_perf.to_string())
        
        print("\n【 LONG-SHORT SPREAD PERFORMANCE 】")
        print("-" * 80)
        spread_perf = report['spread_performance']
        print(f"Annualized Return: {spread_perf['Annualized Return']*100:.2f}%")
        print(f"Volatility: {spread_perf['Volatility']*100:.2f}%")
        print(f"Sharpe Ratio: {spread_perf['Sharpe Ratio']:.2f}")
        print(f"Max Drawdown: {spread_perf['Max Drawdown']*100:.2f}%")
        print(f"  Start: {spread_perf['Max Drawdown Start']}")
        print(f"  End: {spread_perf['Max Drawdown End']}")
        print(f"Win Rate: {spread_perf['Win Rate']*100:.2f}%")
        print(f"Total Return: {spread_perf['Total Return']*100:.2f}%")
        
        print("\n【 IC ANALYSIS (按调仓周期计算 - 消除预测错配) 】")
        print("-" * 80)
        rebalance_stats = report['ic_stats']['rebalance']
        print(f"\n  调仓周期 IC (Rebalance Period IC):")
        print(f"    样本数量 (N_Obs): {rebalance_stats['N_Obs']}")
        print(f"    Mean IC: {rebalance_stats['Mean IC']:.4f}")
        print(f"    Std IC: {rebalance_stats['Std IC']:.4f}")
        print(f"    IR (IC Mean / Std): {rebalance_stats['IR']:.4f}")
        print(f"    IC > 0: {rebalance_stats['IC > 0']*100:.2f}%")
        print(f"    T-Statistic: {rebalance_stats['T-Statistic']:.4f}")
        print(f"    P-Value: {rebalance_stats['P-Value']:.4f}")
        
        print("\n【 IC ANALYSIS (日频对比 - 参考) 】")
        print("-" * 80)
        for period in ['1d', '5d', '20d']:
            stats = report['ic_stats'][period]
            print(f"\n  {period.upper()} IC:")
            print(f"    样本数量 (N_Obs): {stats['N_Obs']}")
            print(f"    Mean IC: {stats['Mean IC']:.4f}")
            print(f"    Std IC: {stats['Std IC']:.4f}")
            print(f"    IR (IC Mean / Std): {stats['IR']:.4f}")
            print(f"    IC > 0: {stats['IC > 0']*100:.2f}%")
            print(f"    T-Statistic: {stats['T-Statistic']:.4f}")
            print(f"    P-Value: {stats['P-Value']:.4f}")
        
        print("\n" + "=" * 80)


if __name__ == '__main__':
    from data_loader import DataLoader
    from factor_engine import FactorEngine
    from backtest import BacktestEngine
    
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
    
    analyzer = PerformanceAnalyzer()
    report = analyzer.generate_report(results, factor_ffill, returns)
    analyzer.print_report(report, 'EP (1/PE)')
