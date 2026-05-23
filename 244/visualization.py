import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
from typing import Dict
import os
from config import RESULT_DIR, N_GROUPS

matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False
plt.style.use('seaborn-v0_8-darkgrid')


class Visualizer:
    def __init__(self, save_dir: str = RESULT_DIR):
        self.save_dir = save_dir
        os.makedirs(save_dir, exist_ok=True)

    def plot_group_cumulative_returns(self, cum_returns: pd.DataFrame,
                                      factor_name: str = '',
                                      save: bool = True,
                                      show: bool = False) -> None:
        fig, ax = plt.subplots(figsize=(14, 8))
        
        colors = plt.cm.RdYlGn_r(np.linspace(0, 1, N_GROUPS))
        
        for i, group in enumerate(cum_returns.columns):
            ax.plot(cum_returns.index, cum_returns[group], 
                    label=f'Group {group}', 
                    color=colors[i],
                    linewidth=2,
                    alpha=0.8)
        
        ax.set_xlabel('Date', fontsize=12)
        ax.set_ylabel('Cumulative Return', fontsize=12)
        ax.set_title(f'Group Cumulative Returns - {factor_name}', fontsize=14, fontweight='bold')
        ax.legend(loc='best', fontsize=10, ncol=2)
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save:
            plt.savefig(os.path.join(self.save_dir, f'group_returns_{factor_name}.png'), 
                       dpi=300, bbox_inches='tight')
        
        if show:
            plt.show()
        else:
            plt.close()

    def plot_spread_return(self, spread_returns: pd.Series,
                           factor_name: str = '',
                           save: bool = True,
                           show: bool = False) -> None:
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), 
                                       gridspec_kw={'height_ratios': [3, 1]})
        
        cum_spread = (1 + spread_returns.fillna(0)).cumprod()
        ax1.plot(cum_spread.index, cum_spread, 
                 label='Long-Short Spread', 
                 color='darkblue',
                 linewidth=2)
        ax1.axhline(y=1, color='gray', linestyle='--', alpha=0.5)
        ax1.set_xlabel('Date', fontsize=12)
        ax1.set_ylabel('Cumulative Return', fontsize=12)
        ax1.set_title(f'Long-Short Spread Cumulative Return - {factor_name}', 
                     fontsize=14, fontweight='bold')
        ax1.legend(loc='best')
        ax1.grid(True, alpha=0.3)
        
        ax2.bar(spread_returns.index, spread_returns.fillna(0), 
                color=np.where(spread_returns.fillna(0) >= 0, 'green', 'red'),
                alpha=0.6)
        ax2.axhline(y=0, color='black', linewidth=0.5)
        ax2.set_xlabel('Date', fontsize=12)
        ax2.set_ylabel('Daily Return', fontsize=12)
        ax2.set_title('Daily Spread Returns', fontsize=12)
        
        plt.tight_layout()
        
        if save:
            plt.savefig(os.path.join(self.save_dir, f'spread_return_{factor_name}.png'), 
                       dpi=300, bbox_inches='tight')
        
        if show:
            plt.show()
        else:
            plt.close()

    def plot_ic_series(self, ic_series: Dict[str, pd.Series],
                       factor_name: str = '',
                       save: bool = True,
                       show: bool = False) -> None:
        rebalance_ic = ic_series.get('rebalance')
        
        if rebalance_ic is not None:
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), 
                                           gridspec_kw={'height_ratios': [1, 1]})
            
            ax = ax1
            ax.plot(rebalance_ic.index, rebalance_ic.values, 'o-',
                    label='Rebalance Period IC', 
                    color='darkred',
                    linewidth=2,
                    markersize=6,
                    alpha=0.8)
            ax.axhline(y=0, color='black', linewidth=1, linestyle='--')
            ax.axhline(y=rebalance_ic.mean(), color='red', linewidth=2, 
                      linestyle='--', label=f'Mean IC: {rebalance_ic.mean():.4f}')
            ax.set_ylabel('IC Value', fontsize=11)
            ax.set_title('IC by Rebalance Period (消除预测错配)', fontsize=12, fontweight='bold')
            ax.legend(loc='best')
            ax.grid(True, alpha=0.3)
            
            ax = ax2
            daily_ic = ic_series.get('1d', pd.Series())
            if len(daily_ic) > 0:
                ax.plot(daily_ic.index, daily_ic.rolling(20).mean(), 
                        label='1d IC (20d MA)', 
                        color='steelblue',
                        linewidth=2)
                ax.bar(daily_ic.index, daily_ic.fillna(0), 
                       alpha=0.2, 
                       color='steelblue')
                ax.axhline(y=0, color='black', linewidth=1, linestyle='--')
                ax.axhline(y=daily_ic.mean(), color='red', linewidth=1, 
                          linestyle='--', label=f'Mean IC: {daily_ic.mean():.4f}')
                ax.set_ylabel('IC Value', fontsize=11)
                ax.set_title('Daily IC Series (参考)', fontsize=12, fontweight='bold')
                ax.legend(loc='best')
                ax.grid(True, alpha=0.3)
            
            fig.suptitle(f'IC Analysis - {factor_name}', fontsize=14, fontweight='bold')
            axes = [ax1, ax2]
        else:
            n_plots = min(3, len(ic_series))
            fig, axes = plt.subplots(n_plots, 1, figsize=(14, 4 * n_plots), sharex=True)
            if n_plots == 1:
                axes = [axes]
            
            for i, (period, ic) in enumerate(list(ic_series.items())[:n_plots]):
                ax = axes[i]
                ax.plot(ic.index, ic.rolling(20).mean(), 
                        label=f'{period} IC (20d MA)', 
                        color='steelblue',
                        linewidth=2)
                ax.bar(ic.index, ic.fillna(0), 
                       alpha=0.3, 
                       color='steelblue',
                       label=f'{period} IC')
                ax.axhline(y=0, color='black', linewidth=1, linestyle='--')
                ax.axhline(y=ic.mean(), color='red', linewidth=1, 
                          linestyle='--', label=f'Mean IC: {ic.mean():.4f}')
                ax.set_ylabel('IC Value', fontsize=11)
                ax.set_title(f'{period.upper()} IC Series', fontsize=12, fontweight='bold')
                ax.legend(loc='best')
                ax.grid(True, alpha=0.3)
        
        axes[-1].set_xlabel('Date', fontsize=12)
        
        plt.tight_layout()
        
        if save:
            plt.savefig(os.path.join(self.save_dir, f'ic_analysis_{factor_name}.png'), 
                       dpi=300, bbox_inches='tight')
        
        if show:
            plt.show()
        else:
            plt.close()

    def plot_ic_histogram(self, ic_series: Dict[str, pd.Series],
                          factor_name: str = '',
                          save: bool = True,
                          show: bool = False) -> None:
        fig, axes = plt.subplots(1, 3, figsize=(18, 5))
        
        for i, (period, ic) in enumerate(ic_series.items()):
            ax = axes[i]
            valid_ic = ic.dropna()
            n, bins, patches = ax.hist(valid_ic, bins=50, 
                                       alpha=0.7, 
                                       color='steelblue',
                                       edgecolor='black')
            
            ax.axvline(x=valid_ic.mean(), color='red', linewidth=2, 
                      linestyle='--', label=f'Mean: {valid_ic.mean():.4f}')
            ax.axvline(x=0, color='black', linewidth=1, linestyle='-')
            ax.set_xlabel('IC Value', fontsize=11)
            ax.set_ylabel('Frequency', fontsize=11)
            ax.set_title(f'{period.upper()} IC Distribution', fontsize=12, fontweight='bold')
            ax.legend(loc='best')
            ax.grid(True, alpha=0.3)
        
        fig.suptitle(f'IC Distribution - {factor_name}', fontsize=14, fontweight='bold')
        
        plt.tight_layout()
        
        if save:
            plt.savefig(os.path.join(self.save_dir, f'ic_histogram_{factor_name}.png'), 
                       dpi=300, bbox_inches='tight')
        
        if show:
            plt.show()
        else:
            plt.close()

    def plot_performance_metrics(self, group_performance: pd.DataFrame,
                                 factor_name: str = '',
                                 save: bool = True,
                                 show: bool = False) -> None:
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        
        groups = group_performance.index
        
        colors = plt.cm.RdYlGn_r(np.linspace(0, 1, len(groups)))
        
        ax = axes[0, 0]
        bars = ax.bar(groups, group_performance['Annualized Return'] * 100, 
                      color=colors, alpha=0.8, edgecolor='black')
        ax.set_xlabel('Group', fontsize=11)
        ax.set_ylabel('Annualized Return (%)', fontsize=11)
        ax.set_title('Annualized Return by Group', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='y')
        ax.axhline(y=0, color='black', linewidth=0.5)
        
        ax = axes[0, 1]
        bars = ax.bar(groups, group_performance['Sharpe Ratio'], 
                      color=colors, alpha=0.8, edgecolor='black')
        ax.set_xlabel('Group', fontsize=11)
        ax.set_ylabel('Sharpe Ratio', fontsize=11)
        ax.set_title('Sharpe Ratio by Group', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='y')
        ax.axhline(y=0, color='black', linewidth=0.5)
        
        ax = axes[1, 0]
        bars = ax.bar(groups, group_performance['Max Drawdown'] * 100, 
                      color=colors, alpha=0.8, edgecolor='black')
        ax.set_xlabel('Group', fontsize=11)
        ax.set_ylabel('Max Drawdown (%)', fontsize=11)
        ax.set_title('Max Drawdown by Group', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='y')
        
        ax = axes[1, 1]
        bars = ax.bar(groups, group_performance['Win Rate'] * 100, 
                      color=colors, alpha=0.8, edgecolor='black')
        ax.set_xlabel('Group', fontsize=11)
        ax.set_ylabel('Win Rate (%)', fontsize=11)
        ax.set_title('Win Rate by Group', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='y')
        
        fig.suptitle(f'Performance Metrics - {factor_name}', fontsize=14, fontweight='bold')
        
        plt.tight_layout()
        
        if save:
            plt.savefig(os.path.join(self.save_dir, f'performance_metrics_{factor_name}.png'), 
                       dpi=300, bbox_inches='tight')
        
        if show:
            plt.show()
        else:
            plt.close()

    def plot_drawdown(self, returns: pd.Series,
                      factor_name: str = '',
                      save: bool = True,
                      show: bool = False) -> None:
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), 
                                       gridspec_kw={'height_ratios': [3, 1]})
        
        cum_returns = (1 + returns.fillna(0)).cumprod()
        running_max = cum_returns.cummax()
        drawdown = (cum_returns - running_max) / running_max
        
        ax1.plot(cum_returns.index, cum_returns, 
                 label='Cumulative Return', 
                 color='darkblue',
                 linewidth=2)
        ax1.plot(running_max.index, running_max, 
                 label='Running Max', 
                 color='red',
                 linestyle='--',
                 linewidth=1.5,
                 alpha=0.7)
        ax1.set_xlabel('Date', fontsize=12)
        ax1.set_ylabel('Cumulative Return', fontsize=12)
        ax1.set_title(f'Cumulative Return and Drawdown - {factor_name}', 
                     fontsize=14, fontweight='bold')
        ax1.legend(loc='best')
        ax1.grid(True, alpha=0.3)
        
        ax2.fill_between(drawdown.index, drawdown.values, 0, 
                        color='red', alpha=0.5)
        ax2.set_xlabel('Date', fontsize=12)
        ax2.set_ylabel('Drawdown', fontsize=12)
        ax2.set_title('Drawdown Series', fontsize=12)
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save:
            plt.savefig(os.path.join(self.save_dir, f'drawdown_{factor_name}.png'), 
                       dpi=300, bbox_inches='tight')
        
        if show:
            plt.show()
        else:
            plt.close()

    def generate_all_plots(self, backtest_results: Dict,
                           report: Dict,
                           factor_name: str = '',
                           save: bool = True,
                           show: bool = False) -> None:
        print(f"Generating plots for {factor_name}...")
        
        self.plot_group_cumulative_returns(
            backtest_results['cumulative_returns'], 
            factor_name, save, show
        )
        
        self.plot_spread_return(
            backtest_results['spread_return'], 
            factor_name, save, show
        )
        
        self.plot_ic_series(
            report['ic_series'], 
            factor_name, save, show
        )
        
        self.plot_ic_histogram(
            report['ic_series'], 
            factor_name, save, show
        )
        
        self.plot_performance_metrics(
            report['group_performance'], 
            factor_name, save, show
        )
        
        self.plot_drawdown(
            backtest_results['spread_return'], 
            factor_name, save, show
        )
        
        print(f"All plots saved to {self.save_dir}")


if __name__ == '__main__':
    from data_loader import DataLoader
    from factor_engine import FactorEngine
    from backtest import BacktestEngine
    from performance import PerformanceAnalyzer
    
    loader = DataLoader()
    loader.generate_sample_data(n_stocks=100)
    price, factors, suspend, delist = loader.load_data()
    returns = loader.calculate_daily_returns()
    
    engine = FactorEngine(factors)
    factor = engine.calculate_factor('1 / PE')
    
    backtest = BacktestEngine(returns, suspend, delist)
    results = backtest.run_backtest(factor, rebalance_freq='M')
    
    analyzer = PerformanceAnalyzer()
    report = analyzer.generate_report(results, factor, returns)
    
    visualizer = Visualizer()
    visualizer.generate_all_plots(results, report, 'EP_Test', save=True, show=False)
    print("Plots generated successfully!")
