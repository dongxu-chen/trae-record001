import backtrader as bt
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

from backtest_engine import BacktestEngine


class OverfitDetector:
    
    def __init__(self, initial_cash: float = 100000.0, commission: float = 0.001,
                 slippage: float = 0.001):
        self.initial_cash = initial_cash
        self.commission = commission
        self.slippage = slippage
    
    def rolling_window_backtest(self, strategy_name: str, data: pd.DataFrame,
                                 strategy_params: Dict = None,
                                 window_ratio: float = 0.7,
                                 step_ratio: float = 0.1,
                                 optimize_by: str = 'sharpe_ratio') -> Dict:
        strategy_params = strategy_params or {}
        total_len = len(data)
        window_size = int(total_len * window_ratio)
        step_size = int(total_len * step_ratio)
        
        if window_size < 50:
            raise ValueError("数据量不足以进行滚动窗口回测")
        
        windows = []
        start = 0
        while start + window_size <= total_len:
            end = start + window_size
            windows.append((start, end))
            start += step_size
            if start + window_size > total_len:
                if end < total_len:
                    windows.append((total_len - window_size, total_len))
                break
        
        results = []
        for i, (start_idx, end_idx) in enumerate(windows):
            window_data = data.iloc[start_idx:end_idx].copy()
            if len(window_data) < 50:
                continue
            
            try:
                engine = BacktestEngine(self.initial_cash, self.commission, self.slippage)
                metrics = engine.run_backtest(strategy_name, window_data, strategy_params)
                metrics['window_start'] = data.index[start_idx]
                metrics['window_end'] = data.index[end_idx - 1]
                metrics['window_idx'] = i
                results.append(metrics)
            except Exception as e:
                print(f"窗口 {i} 回测失败: {e}")
        
        if not results:
            raise ValueError("所有窗口回测均失败")
        
        returns = [r['total_return'] for r in results]
        sharpe_ratios = [r['sharpe_ratio'] for r in results]
        max_drawdowns = [r['max_drawdown'] for r in results]
        win_rates = [r['win_rate'] for r in results]
        
        stability_score = self._calculate_stability_score(returns, sharpe_ratios, max_drawdowns)
        
        return {
            'window_results': results,
            'stability_score': stability_score,
            'return_mean': np.mean(returns),
            'return_std': np.std(returns),
            'return_cv': np.std(returns) / abs(np.mean(returns)) if np.mean(returns) != 0 else float('inf'),
            'sharpe_mean': np.mean(sharpe_ratios),
            'sharpe_std': np.std(sharpe_ratios),
            'drawdown_mean': np.mean(max_drawdowns),
            'drawdown_std': np.std(max_drawdowns),
            'win_rate_mean': np.mean(win_rates),
            'win_rate_std': np.std(win_rates),
            'positive_ratio': sum(1 for r in returns if r > 0) / len(returns),
            'num_windows': len(results),
            'window_ratio': window_ratio,
            'step_ratio': step_ratio
        }
    
    def _calculate_stability_score(self, returns: List[float], sharpes: List[float],
                                    drawdowns: List[float]) -> float:
        if not returns:
            return 0.0
        
        positive_ratio = sum(1 for r in returns if r > 0) / len(returns)
        
        mean_ret = np.mean(returns)
        std_ret = np.std(returns)
        cv = std_ret / abs(mean_ret) if mean_ret != 0 else float('inf')
        consistency = max(0, 1 - cv)
        
        mean_sharpe = np.mean(sharpes)
        sharpe_score = min(1, max(0, mean_sharpe / 2))
        
        mean_dd = np.mean(drawdowns)
        dd_score = max(0, 1 - mean_dd / 50)
        
        stability = (
            positive_ratio * 0.3 +
            consistency * 0.3 +
            sharpe_score * 0.2 +
            dd_score * 0.2
        )
        
        return round(stability * 100, 2)
    
    def in_sample_out_sample_test(self, strategy_name: str, data: pd.DataFrame,
                                   strategy_params: Dict = None,
                                   train_ratio: float = 0.7) -> Dict:
        strategy_params = strategy_params or {}
        split_idx = int(len(data) * train_ratio)
        
        in_sample_data = data.iloc[:split_idx].copy()
        out_sample_data = data.iloc[split_idx:].copy()
        
        if len(out_sample_data) < 20:
            raise ValueError("样本外数据不足")
        
        engine = BacktestEngine(self.initial_cash, self.commission, self.slippage)
        
        in_sample_metrics = engine.run_backtest(strategy_name, in_sample_data, strategy_params)
        out_sample_metrics = engine.run_backtest(strategy_name, out_sample_data, strategy_params)
        
        in_ret = in_sample_metrics['total_return']
        out_ret = out_sample_metrics['total_return']
        
        return_degradation = (in_ret - out_ret) / abs(in_ret) * 100 if in_ret != 0 else 0
        
        is_overfit = False
        overfit_severity = 'none'
        
        if return_degradation > 50:
            is_overfit = True
            overfit_severity = 'severe'
        elif return_degradation > 30:
            is_overfit = True
            overfit_severity = 'moderate'
        elif return_degradation > 15:
            overfit_severity = 'mild'
        
        if in_sample_metrics['sharpe_ratio'] > 0 and out_sample_metrics['sharpe_ratio'] < 0:
            is_overfit = True
            overfit_severity = 'severe'
        
        return {
            'in_sample': in_sample_metrics,
            'out_sample': out_sample_metrics,
            'return_degradation': return_degradation,
            'is_overfit': is_overfit,
            'overfit_severity': overfit_severity,
            'train_ratio': train_ratio,
            'in_sample_period': (data.index[0], data.index[split_idx - 1]),
            'out_sample_period': (data.index[split_idx], data.index[-1]),
            'sharpe_degradation': in_sample_metrics['sharpe_ratio'] - out_sample_metrics['sharpe_ratio'],
            'win_rate_change': out_sample_metrics['win_rate'] - in_sample_metrics['win_rate'],
            'drawdown_change': out_sample_metrics['max_drawdown'] - in_sample_metrics['max_drawdown']
        }
    
    def walk_forward_analysis(self, strategy_name: str, data: pd.DataFrame,
                               strategy_params: Dict = None,
                               train_ratio: float = 0.7,
                               n_splits: int = 5,
                               optimize_by: str = 'sharpe_ratio') -> Dict:
        strategy_params = strategy_params or {}
        total_len = len(data)
        test_size = total_len // (n_splits + 1)
        train_size = int(test_size * train_ratio / (1 - train_ratio))
        
        fold_results = []
        
        for i in range(n_splits):
            test_start = i * test_size + train_size
            test_end = test_start + test_size
            train_start = i * test_size
            train_end = test_start
            
            if test_end > total_len:
                test_end = total_len
            
            train_data = data.iloc[train_start:train_end].copy()
            test_data = data.iloc[test_start:test_end].copy()
            
            if len(train_data) < 50 or len(test_data) < 20:
                continue
            
            try:
                engine = BacktestEngine(self.initial_cash, self.commission, self.slippage)
                train_metrics = engine.run_backtest(strategy_name, train_data, strategy_params)
                
                engine = BacktestEngine(self.initial_cash, self.commission, self.slippage)
                test_metrics = engine.run_backtest(strategy_name, test_data, strategy_params)
                
                fold_results.append({
                    'fold': i + 1,
                    'train_period': (data.index[train_start], data.index[train_end - 1]),
                    'test_period': (data.index[test_start], data.index[min(test_end - 1, total_len - 1)]),
                    'train_return': train_metrics['total_return'],
                    'test_return': test_metrics['total_return'],
                    'train_sharpe': train_metrics['sharpe_ratio'],
                    'test_sharpe': test_metrics['sharpe_ratio'],
                    'train_drawdown': train_metrics['max_drawdown'],
                    'test_drawdown': test_metrics['max_drawdown'],
                    'train_win_rate': train_metrics['win_rate'],
                    'test_win_rate': test_metrics['win_rate'],
                    'degradation': train_metrics['total_return'] - test_metrics['total_return']
                })
            except Exception as e:
                print(f"Fold {i+1} 失败: {e}")
        
        if not fold_results:
            raise ValueError("所有折回测均失败")
        
        test_returns = [f['test_return'] for f in fold_results]
        test_sharpes = [f['test_sharpe'] for f in fold_results]
        degradations = [f['degradation'] for f in fold_results]
        
        avg_test_return = np.mean(test_returns)
        avg_test_sharpe = np.mean(test_sharpes)
        avg_degradation = np.mean(degradations)
        consistency = sum(1 for r in test_returns if r > 0) / len(test_returns)
        
        wfa_score = self._calculate_stability_score(test_returns, test_sharpes,
                                                     [f['test_drawdown'] for f in fold_results])
        
        return {
            'fold_results': fold_results,
            'avg_test_return': avg_test_return,
            'avg_test_sharpe': avg_test_sharpe,
            'avg_degradation': avg_degradation,
            'consistency': consistency,
            'wfa_score': wfa_score,
            'n_splits': n_splits,
            'train_ratio': train_ratio
        }
