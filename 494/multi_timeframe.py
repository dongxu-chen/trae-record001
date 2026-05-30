import backtrader as bt
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

from backtest_engine import BacktestEngine


class MultiTimeframeEngine:
    
    TIMEFRAMES = {
        '1m': bt.TimeFrame.Minutes,
        '5m': bt.TimeFrame.Minutes,
        '15m': bt.TimeFrame.Minutes,
        '30m': bt.TimeFrame.Minutes,
        '1h': bt.TimeFrame.Minutes,
        '1d': bt.TimeFrame.Days,
        '1w': bt.TimeFrame.Weeks,
        '1M': bt.TimeFrame.Months,
    }
    
    TIMEFRAME_COMPRESSION = {
        '1m': 1, '5m': 5, '15m': 15, '30m': 30,
        '1h': 60, '1d': 1, '1w': 1, '1M': 1,
    }
    
    def __init__(self, initial_cash: float = 100000.0, commission: float = 0.001,
                 slippage: float = 0.001):
        self.initial_cash = initial_cash
        self.commission = commission
        self.slippage = slippage
    
    def resample_data(self, data: pd.DataFrame, target_timeframe: str) -> pd.DataFrame:
        resample_map = {
            '5m': '5min', '15m': '15min', '30m': '30min', '1h': '1h',
            '1d': '1D', '1w': '1W', '1M': '1ME',
        }
        
        if target_timeframe not in resample_map:
            raise ValueError(f"不支持的时间周期: {target_timeframe}")
        
        rule = resample_map[target_timeframe]
        
        resampled = data.resample(rule).agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()
        
        return resampled
    
    def generate_signals(self, strategy_name: str, data: pd.DataFrame,
                          strategy_params: Dict = None) -> pd.DataFrame:
        strategy_params = strategy_params or {}
        
        cerebro = bt.Cerebro(stdstats=False)
        cerebro.broker.setcash(self.initial_cash)
        cerebro.broker.setcommission(commission=self.commission)
        if self.slippage > 0:
            cerebro.broker.set_slippage_perc(perc=self.slippage)
        cerebro.addsizer(bt.sizers.PercentSizer, percents=95)
        
        strategy_class = BacktestEngine.STRATEGIES.get(strategy_name)
        if not strategy_class:
            raise ValueError(f"策略不存在: {strategy_name}")
        
        cerebro.addstrategy(strategy_class, **strategy_params)
        
        bt_data = bt.feeds.PandasData(dataname=data)
        cerebro.adddata(bt_data)
        
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
        
        class SignalRecorder(bt.Analyzer):
            params = (('strategy_name', strategy_name),)
            
            def __init__(self):
                self.signals = []
                self.strategy_obj = None
            
            def start(self):
                self.strategy_obj = self.strategy
            
            def next(self):
                pass
            
            def stop(self):
                if hasattr(self.strategy, 'trades'):
                    for trade in self.strategy.trades:
                        self.signals.append(trade)
        
        results = cerebro.run()
        strat = results[0]
        
        signals_df = pd.DataFrame(strat.trades) if strat.trades else pd.DataFrame()
        
        return signals_df
    
    def multi_timeframe_backtest(self, strategy_name: str, data: pd.DataFrame,
                                  timeframes: List[str] = None,
                                  strategy_params: Dict = None) -> Dict:
        if timeframes is None:
            timeframes = ['1d', '1h']
        
        strategy_params = strategy_params or {}
        
        tf_results = {}
        for tf in timeframes:
            try:
                if tf == '1d':
                    tf_data = data.copy()
                else:
                    tf_data = self.resample_data(data, tf)
                
                if len(tf_data) < 30:
                    print(f"周期 {tf} 数据不足，跳过")
                    continue
                
                engine = BacktestEngine(self.initial_cash, self.commission, self.slippage)
                metrics = engine.run_backtest(strategy_name, tf_data, strategy_params)
                signals = self.generate_signals(strategy_name, tf_data, strategy_params)
                
                tf_results[tf] = {
                    'metrics': metrics,
                    'signals': signals,
                    'data': tf_data,
                    'num_bars': len(tf_data)
                }
            except Exception as e:
                print(f"周期 {tf} 回测失败: {e}")
        
        if len(tf_results) < 2:
            raise ValueError("至少需要2个有效周期才能进行联合分析")
        
        resonance = self._detect_resonance(tf_results, data)
        consensus = self._build_consensus_signals(tf_results, data)
        
        return {
            'timeframe_results': tf_results,
            'resonance_analysis': resonance,
            'consensus_signals': consensus,
            'timeframes_used': list(tf_results.keys())
        }
    
    def _detect_resonance(self, tf_results: Dict, original_data: pd.DataFrame) -> Dict:
        all_signals = {}
        for tf, result in tf_results.items():
            signals = result['signals']
            if signals is None or len(signals) == 0:
                all_signals[tf] = pd.DataFrame()
                continue
            
            if 'timestamp' in signals.columns:
                dates = pd.to_datetime(signals['timestamp'])
            elif 'date' in signals.columns:
                dates = pd.to_datetime(signals['date'])
            else:
                continue
            
            signal_df = pd.DataFrame({
                'date': dates,
                'type': signals['type'].values,
                'timeframe': tf
            })
            signal_df['date_only'] = signal_df['date'].dt.date
            all_signals[tf] = signal_df
        
        resonance_signals = []
        if len(all_signals) >= 2:
            tf_names = list(all_signals.keys())
            
            for tf_name in tf_names:
                if all_signals[tf_name].empty:
                    continue
                for _, row in all_signals[tf_name].iterrows():
                    trade_date = row['date_only']
                    trade_type = row['type']
                    
                    confirmed_by = [tf_name]
                    for other_tf in tf_names:
                        if other_tf == tf_name:
                            continue
                        if all_signals[other_tf].empty:
                            continue
                        
                        same_day = all_signals[other_tf][
                            (all_signals[other_tf]['date_only'] == trade_date) &
                            (all_signals[other_tf]['type'] == trade_type)
                        ]
                        
                        if not same_day.empty:
                            confirmed_by.append(other_tf)
                    
                    if len(confirmed_by) >= 2:
                        resonance_signals.append({
                            'date': trade_date,
                            'type': trade_type,
                            'confirmed_by': confirmed_by,
                            'strength': len(confirmed_by) / len(tf_names),
                            'source_timeframe': tf_name
                        })
        
        unique_resonance = {}
        for sig in resonance_signals:
            key = (sig['date'], sig['type'])
            if key not in unique_resonance or sig['strength'] > unique_resonance[key]['strength']:
                unique_resonance[key] = sig
        
        resonance_list = list(unique_resonance.values())
        
        buy_signals = [s for s in resonance_list if s['type'] == 'buy']
        sell_signals = [s for s in resonance_list if s['type'] == 'sell']
        
        total_signals = sum(len(all_signals[tf]) for tf in all_signals)
        resonance_ratio = len(resonance_list) / total_signals if total_signals > 0 else 0
        
        avg_strength = np.mean([s['strength'] for s in resonance_list]) if resonance_list else 0
        
        return {
            'signals': resonance_list,
            'buy_signals': len(buy_signals),
            'sell_signals': len(sell_signals),
            'total_signals': total_signals,
            'resonance_count': len(resonance_list),
            'resonance_ratio': resonance_ratio,
            'avg_strength': avg_strength
        }
    
    def _build_consensus_signals(self, tf_results: Dict, 
                                  original_data: pd.DataFrame) -> pd.DataFrame:
        if len(tf_results) < 2:
            return pd.DataFrame()
        
        tf_names = list(tf_results.keys())
        
        consensus_list = []
        
        for tf_name in tf_names:
            result = tf_results[tf_name]
            signals = result['signals']
            if signals is None or len(signals) == 0:
                continue
            
            if 'timestamp' in signals.columns:
                dates = pd.to_datetime(signals['timestamp'])
            elif 'date' in signals.columns:
                dates = pd.to_datetime(signals['date'])
            else:
                continue
            
            for date, sig_type in zip(dates, signals['type'].values):
                consensus_list.append({
                    'date': date,
                    'date_only': date.date() if hasattr(date, 'date') else date,
                    'type': sig_type,
                    'timeframe': tf_name
                })
        
        if not consensus_list:
            return pd.DataFrame()
        
        consensus_df = pd.DataFrame(consensus_list)
        
        grouped = consensus_df.groupby(['date_only', 'type']).agg(
            count=('timeframe', 'count'),
            timeframes=('timeframe', lambda x: ','.join(sorted(set(x))))
        ).reset_index()
        
        grouped = grouped.rename(columns={'date_only': 'date'})
        grouped['consensus_ratio'] = grouped['count'] / len(tf_names)
        grouped['is_consensus'] = grouped['count'] >= 2
        
        return grouped
    
    def get_timeframe_comparison(self, multi_tf_results: Dict) -> pd.DataFrame:
        rows = []
        for tf, result in multi_tf_results['timeframe_results'].items():
            metrics = result['metrics']
            rows.append({
                'timeframe': tf,
                'total_return': metrics['total_return'],
                'sharpe_ratio': metrics['sharpe_ratio'],
                'max_drawdown': metrics['max_drawdown'],
                'win_rate': metrics['win_rate'],
                'profit_factor': metrics['profit_factor'],
                'total_trades': metrics['total_trades'],
                'num_bars': result['num_bars']
            })
        return pd.DataFrame(rows)
