import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import matplotlib.pyplot as plt
import seaborn as sns
from config import RESULT_DIR
import os


@dataclass
class AttributionResult:
    total_return: float
    industry_return: float
    style_return: float
    specific_return: float
    industry_contributions: Dict[str, float]
    style_contributions: Dict[str, float]


class FactorAttribution:
    def __init__(self, returns: pd.DataFrame,
                 industry_data: pd.Series,
                 factor_data: Dict[str, pd.DataFrame],
                 style_factors: List[str] = None):
        
        self.returns = returns
        self.industry_data = industry_data
        self.factor_data = factor_data
        self.style_factors = style_factors or ['MKT_CAP', 'PB', 'ROE']
        
        self.industries = industry_data.unique().tolist()
        self.industry_returns = None
        self.style_returns = None
        
    def calculate_industry_returns(self) -> pd.DataFrame:
        industry_returns = pd.DataFrame(index=self.returns.index,
                                       columns=self.industries,
                                       dtype=float)
        
        for date in self.returns.index:
            date_returns = self.returns.loc[date]
            
            for industry in self.industries:
                industry_stocks = self.industry_data[self.industry_data == industry].index
                common_stocks = industry_stocks.intersection(date_returns.dropna().index)
                
                if len(common_stocks) > 0:
                    industry_returns.loc[date, industry] = date_returns.loc[common_stocks].mean()
                else:
                    industry_returns.loc[date, industry] = 0
        
        self.industry_returns = industry_returns
        return industry_returns
    
    def calculate_style_returns(self) -> pd.DataFrame:
        style_returns = pd.DataFrame(index=self.returns.index,
                                    columns=self.style_factors,
                                    dtype=float)
        
        for date in self.returns.index:
            for style_factor in self.style_factors:
                if style_factor in self.factor_data:
                    factor_values = self.factor_data[style_factor].loc[date].dropna()
                    date_rets = self.returns.loc[date].dropna()
                    
                    common = factor_values.index.intersection(date_rets.index)
                    if len(common) > 10:
                        f = factor_values.loc[common]
                        r = date_rets.loc[common]
                        
                        long_stocks = f.nlargest(len(common) // 5).index
                        short_stocks = f.nsmallest(len(common) // 5).index
                        
                        long_ret = r.loc[long_stocks].mean()
                        short_ret = r.loc[short_stocks].mean()
                        
                        style_returns.loc[date, style_factor] = long_ret - short_ret
                    else:
                        style_returns.loc[date, style_factor] = 0
                else:
                    style_returns.loc[date, style_factor] = 0
        
        self.style_returns = style_returns
        return style_returns
    
    def calculate_exposures(self, weights: pd.Series, 
                           date: pd.Timestamp) -> Tuple[Dict, Dict]:
        valid_stocks = weights[weights.abs() > 0].index
        
        industry_exposure = {}
        for industry in self.industries:
            industry_stocks = self.industry_data[self.industry_data == industry].index
            industry_exposure[industry] = weights.loc[valid_stocks.intersection(industry_stocks)].sum()
        
        style_exposure = {}
        for style_factor in self.style_factors:
            if style_factor in self.factor_data:
                factor_values = self.factor_data[style_factor].loc[date].reindex(valid_stocks)
                style_exposure[style_factor] = (weights.loc[valid_stocks] * factor_values).sum()
        
        return industry_exposure, style_exposure
    
    def decompose_returns(self, portfolio_weights: pd.DataFrame,
                         start_date: str = None,
                         end_date: str = None) -> pd.DataFrame:
        if self.industry_returns is None:
            self.calculate_industry_returns()
        if self.style_returns is None:
            self.calculate_style_returns()
        
        dates = portfolio_weights.loc[start_date:end_date].index
        
        attribution = pd.DataFrame(
            index=dates,
            columns=['Total', 'Industry', 'Style', 'Specific'],
            dtype=float
        )
        
        for i, date in enumerate(dates[:-1]):
            next_date = dates[i + 1]
            
            weights = portfolio_weights.loc[date]
            period_returns = self.returns.loc[date:next_date].add(1).prod() - 1
            
            portfolio_ret = (weights * period_returns).sum()
            
            industry_exposure, style_exposure = self.calculate_exposures(weights, date)
            
            industry_period_rets = self.industry_returns.loc[date:next_date].add(1).prod() - 1
            industry_contrib = sum(
                industry_exposure.get(ind, 0) * industry_period_rets.get(ind, 0)
                for ind in self.industries
            )
            
            style_period_rets = self.style_returns.loc[date:next_date].add(1).prod() - 1
            style_contrib = sum(
                style_exposure.get(sf, 0) * style_period_rets.get(sf, 0)
                for sf in self.style_factors
            )
            
            specific_contrib = portfolio_ret - industry_contrib - style_contrib
            
            attribution.loc[date, 'Total'] = portfolio_ret
            attribution.loc[date, 'Industry'] = industry_contrib
            attribution.loc[date, 'Style'] = style_contrib
            attribution.loc[date, 'Specific'] = specific_contrib
        
        return attribution
    
    def decompose_group_returns(self, groups: pd.DataFrame,
                                group: int = 1) -> AttributionResult:
        valid_mask = groups == group
        
        portfolio_weights = valid_mask.astype(float).div(
            valid_mask.sum(axis=1), axis=0
        ).fillna(0)
        
        attribution = self.decompose_returns(portfolio_weights)
        
        total_return = (1 + attribution['Total']).prod() - 1
        industry_return = (1 + attribution['Industry']).prod() - 1
        style_return = (1 + attribution['Style']).prod() - 1
        specific_return = (1 + attribution['Specific']).prod() - 1
        
        industry_contribs = self._get_industry_contributions(portfolio_weights)
        style_contribs = self._get_style_contributions(portfolio_weights)
        
        return AttributionResult(
            total_return=total_return,
            industry_return=industry_return,
            style_return=style_return,
            specific_return=specific_return,
            industry_contributions=industry_contribs,
            style_contributions=style_contribs
        )
    
    def _get_industry_contributions(self, weights: pd.DataFrame) -> Dict[str, float]:
        contributions = {}
        
        for industry in self.industries:
            industry_stocks = self.industry_data[self.industry_data == industry].index
            industry_weights = weights[industry_stocks.intersection(weights.columns)].sum(axis=1)
            
            if self.industry_returns is not None:
                industry_rets = self.industry_returns[industry].reindex(weights.index).fillna(0)
                contrib = (industry_weights * industry_rets).sum()
                contributions[industry] = contrib
        
        return contributions
    
    def _get_style_contributions(self, weights: pd.DataFrame) -> Dict[str, float]:
        contributions = {}
        
        for style_factor in self.style_factors:
            if style_factor in self.factor_data:
                exposure = pd.Series(index=weights.index, dtype=float)
                for date in weights.index:
                    _, style_exp = self.calculate_exposures(weights.loc[date], date)
                    exposure.loc[date] = style_exp.get(style_factor, 0)
                
                if self.style_returns is not None:
                    style_rets = self.style_returns[style_factor].reindex(weights.index).fillna(0)
                    contrib = (exposure * style_rets).sum()
                    contributions[style_factor] = contrib
        
        return contributions


class AttributionVisualizer:
    def __init__(self, save_dir: str = RESULT_DIR):
        self.save_dir = save_dir
        os.makedirs(save_dir, exist_ok=True)
        
    def plot_attribution_breakdown(self, attribution_df: pd.DataFrame,
                                   factor_name: str = '',
                                   save: bool = True,
                                   show: bool = False):
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 12))
        
        cum_attribution = (1 + attribution_df.fillna(0)).cumprod() - 1
        
        ax1.stackplot(cum_attribution.index,
                     cum_attribution['Industry'],
                     cum_attribution['Style'],
                     cum_attribution['Specific'],
                     labels=['行业收益', '风格收益', '特异性收益'],
                     colors=['#FF6B6B', '#4ECDC4', '#45B7D1'],
                     alpha=0.8)
        ax1.plot(cum_attribution.index, cum_attribution['Total'], 
                color='black', linewidth=2, label='总收益')
        ax1.set_ylabel('累积收益', fontsize=12)
        ax1.set_title('收益来源分解 - 累积收益', fontsize=14, fontweight='bold')
        ax1.legend(loc='best')
        ax1.grid(True, alpha=0.3)
        
        total_period = (1 + attribution_df['Total']).prod() - 1
        industry_period = (1 + attribution_df['Industry']).prod() - 1
        style_period = (1 + attribution_df['Style']).prod() - 1
        specific_period = (1 + attribution_df['Specific']).prod() - 1
        
        components = ['行业收益', '风格收益', '特异性收益']
        values = [industry_period, style_period, specific_period]
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1']
        
        bars = ax2.bar(components, [v * 100 for v in values], color=colors, alpha=0.8)
        ax2.axhline(y=0, color='black', linewidth=0.5)
        ax2.set_ylabel('贡献收益 (%)', fontsize=12)
        ax2.set_title('各来源总收益贡献', fontsize=14, fontweight='bold')
        
        for bar, value in zip(bars, values):
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height,
                    f'{value*100:.2f}%',
                    ha='center', va='bottom' if height >= 0 else 'top')
        
        plt.suptitle(f'归因分析 - {factor_name}', fontsize=16, fontweight='bold')
        plt.tight_layout()
        
        if save:
            plt.savefig(os.path.join(self.save_dir, f'attribution_breakdown_{factor_name}.png'),
                       dpi=300, bbox_inches='tight')
        if show:
            plt.show()
        else:
            plt.close()
    
    def plot_group_attribution_comparison(self, results: Dict[int, AttributionResult],
                                         factor_name: str = '',
                                         save: bool = True,
                                         show: bool = False):
        groups = sorted(results.keys())
        
        industry_rets = [results[g].industry_return * 100 for g in groups]
        style_rets = [results[g].style_return * 100 for g in groups]
        specific_rets = [results[g].specific_return * 100 for g in groups]
        total_rets = [results[g].total_return * 100 for g in groups]
        
        fig, ax = plt.subplots(figsize=(14, 8))
        
        x = np.arange(len(groups))
        width = 0.2
        
        ax.bar(x - width, industry_rets, width, label='行业收益', color='#FF6B6B', alpha=0.8)
        ax.bar(x, style_rets, width, label='风格收益', color='#4ECDC4', alpha=0.8)
        ax.bar(x + width, specific_rets, width, label='特异性收益', color='#45B7D1', alpha=0.8)
        ax.plot(x, total_rets, color='black', linewidth=2, marker='o', label='总收益')
        
        ax.set_xlabel('分组', fontsize=12)
        ax.set_ylabel('收益 (%)', fontsize=12)
        ax.set_title(f'各组收益来源对比 - {factor_name}', fontsize=14, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels([f'Group {g}' for g in groups])
        ax.legend()
        ax.grid(True, alpha=0.3, axis='y')
        
        plt.tight_layout()
        
        if save:
            plt.savefig(os.path.join(self.save_dir, f'group_attribution_comparison_{factor_name}.png'),
                       dpi=300, bbox_inches='tight')
        if show:
            plt.show()
        else:
            plt.close()
    
    def plot_industry_contributions(self, result: AttributionResult,
                                    factor_name: str = '',
                                    group: int = 1,
                                    save: bool = True,
                                    show: bool = False):
        industries = list(result.industry_contributions.keys())
        contributions = [v * 100 for v in result.industry_contributions.values()]
        
        sorted_idx = np.argsort(contributions)
        industries = [industries[i] for i in sorted_idx]
        contributions = [contributions[i] for i in sorted_idx]
        
        fig, ax = plt.subplots(figsize=(12, 8))
        
        colors = ['#FF6B6B' if c < 0 else '#4ECDC4' for c in contributions]
        bars = ax.barh(industries, contributions, color=colors, alpha=0.8)
        
        ax.set_xlabel('收益贡献 (%)', fontsize=12)
        ax.set_title(f'行业收益贡献 - Group {group} - {factor_name}', fontsize=14, fontweight='bold')
        ax.axvline(x=0, color='black', linewidth=0.5)
        ax.grid(True, alpha=0.3, axis='x')
        
        plt.tight_layout()
        
        if save:
            plt.savefig(os.path.join(self.save_dir, f'industry_contributions_{factor_name}_group{group}.png'),
                       dpi=300, bbox_inches='tight')
        if show:
            plt.show()
        else:
            plt.close()


def run_attribution_analysis(groups: pd.DataFrame,
                            returns: pd.DataFrame,
                            industry_data: pd.Series,
                            factor_data: Dict[str, pd.DataFrame],
                            factor_name: str = '',
                            n_groups: int = 10) -> Dict:
    print("\n" + "=" * 70)
    print("归因分析开始")
    print("=" * 70)
    
    attribution = FactorAttribution(returns, industry_data, factor_data)
    
    print("计算行业收益...")
    attribution.calculate_industry_returns()
    print("计算风格收益...")
    attribution.calculate_style_returns()
    
    group_results = {}
    print("分解各组收益来源...")
    for group in range(1, n_groups + 1):
        result = attribution.decompose_group_returns(groups, group)
        group_results[group] = result
        print(f"  Group {group}: 总收益={result.total_return*100:.2f}%, "
              f"行业={result.industry_return*100:.2f}%, "
              f"风格={result.style_return*100:.2f}%, "
              f"特异性={result.specific_return*100:.2f}%")
    
    print("生成可视化图表...")
    visualizer = AttributionVisualizer()
    
    group1_weights = (groups == 1).astype(float).div(
        (groups == 1).sum(axis=1), axis=0
    ).fillna(0)
    attribution_df = attribution.decompose_returns(group1_weights)
    
    visualizer.plot_attribution_breakdown(attribution_df, factor_name)
    visualizer.plot_group_attribution_comparison(group_results, factor_name)
    visualizer.plot_industry_contributions(group_results[1], factor_name, 1)
    
    print("归因分析完成!")
    print("=" * 70)
    
    return {
        'attribution': attribution,
        'group_results': group_results,
        'attribution_df': attribution_df
    }


if __name__ == '__main__':
    from data_loader import DataLoader
    from factor_engine import FactorEngine
    from backtest import BacktestEngine
    
    loader = DataLoader()
    loader.generate_sample_data(n_stocks=60, start_date='2022-01-01', end_date='2023-12-31')
    price, factors, suspend, delist, industry = loader.load_data()
    returns = loader.calculate_daily_returns()
    mkt_cap = factors.get('MKT_CAP')
    
    engine = FactorEngine(factors)
    factor = engine.calculate_factor('1 / PE')
    factor_ffill = loader.forward_fill_factor_for_suspend(factor)
    
    backtest = BacktestEngine(returns, suspend, delist, industry, mkt_cap)
    rebalance_dates = backtest.get_rebalance_dates(freq='M')
    groups = backtest.assign_groups(factor_ffill, rebalance_dates)
    
    results = run_attribution_analysis(groups, returns, industry, factors, 'EP_Factor')
