import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import warnings
warnings.filterwarnings('ignore')


class BacktestVisualizer:
    COLORS = {
        'strategy': '#1f77b4',
        'benchmark': '#ff7f0e',
        'buy': '#2ecc71',
        'sell': '#e74c3c',
        'fast_ma': '#9b59b6',
        'slow_ma': '#34495e',
        'rsi': '#e67e22',
        'macd': '#1abc9c',
        'signal': '#e74c3c',
        'bb_top': '#34495e',
        'bb_mid': '#3498db',
        'bb_bot': '#34495e',
    }
    
    @staticmethod
    def _align_trades_with_data(data: pd.DataFrame, trades: List[Dict]) -> List[Dict]:
        aligned_trades = []
        data_dates = set(data.index.date)
        
        for trade in trades:
            trade_date = trade.get('timestamp') or trade.get('date')
            if trade_date is None:
                continue
            
            if hasattr(trade_date, 'date'):
                trade_date = trade_date.date()
            
            if trade_date in data_dates:
                idx = data.index.get_indexer([pd.Timestamp(trade_date)], method='nearest')[0]
                if idx >= 0 and idx < len(data):
                    aligned_trade = trade.copy()
                    aligned_trade['idx'] = idx
                    aligned_trade['price'] = data.iloc[idx]['close']
                    aligned_trades.append(aligned_trade)
        
        return aligned_trades
    
    @staticmethod
    def create_equity_curve(metrics: Dict, data: pd.DataFrame, 
                            benchmark_data: pd.Series = None, 
                            initial_cash: float = 100000.0) -> go.Figure:
        fig = go.Figure()
        
        equity_curve = metrics.get('equity_curve', [])
        
        if len(equity_curve) == len(data):
            strategy_dates = data.index
            strategy_values = equity_curve
        else:
            min_len = min(len(equity_curve), len(data))
            strategy_dates = data.index[:min_len]
            strategy_values = equity_curve[:min_len]
        
        strategy_returns = pd.Series(strategy_values, index=strategy_dates)
        strategy_norm = strategy_returns / initial_cash * 100
        
        fig.add_trace(go.Scatter(
            x=strategy_dates,
            y=strategy_norm.values,
            name='策略收益',
            line=dict(color=BacktestVisualizer.COLORS['strategy'], width=2),
            hovertemplate='日期: %{x}<br>归一化收益: %{y:.2f}%<br>资产净值: ¥%{customdata:.2f}',
            customdata=strategy_values
        ))
        
        if benchmark_data is not None:
            benchmark_norm = benchmark_data / benchmark_data.iloc[0] * 100
            fig.add_trace(go.Scatter(
                x=benchmark_data.index,
                y=benchmark_norm.values,
                name='基准收益',
                line=dict(color=BacktestVisualizer.COLORS['benchmark'], width=2, dash='dash'),
                hovertemplate='日期: %{x}<br>归一化收益: %{y:.2f}%'
            ))
        
        fig.update_layout(
            title='资产净值曲线',
            xaxis_title='日期',
            yaxis_title='归一化收益 (%)',
            hovermode='x unified',
            showlegend=True,
            template='plotly_white',
            height=500
        )
        
        return fig
    
    @staticmethod
    def create_drawdown_chart(metrics: Dict, data: pd.DataFrame) -> go.Figure:
        equity_curve = metrics.get('equity_curve', [])
        
        if len(equity_curve) == len(data):
            dates = data.index
            equity = np.array(equity_curve)
        else:
            min_len = min(len(equity_curve), len(data))
            dates = data.index[:min_len]
            equity = np.array(equity_curve[:min_len])
        
        running_max = np.maximum.accumulate(equity)
        drawdown = (equity - running_max) / running_max * 100
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=dates,
            y=drawdown,
            name='回撤',
            fill='tozeroy',
            fillcolor='rgba(231, 76, 60, 0.3)',
            line=dict(color=BacktestVisualizer.COLORS['sell'], width=1),
            hovertemplate='日期: %{x}<br>回撤: %{y:.2f}%'
        ))
        
        fig.update_layout(
            title='回撤曲线',
            xaxis_title='日期',
            yaxis_title='回撤 (%)',
            hovermode='x unified',
            template='plotly_white',
            height=300
        )
        
        return fig
    
    @staticmethod
    def create_price_with_signals(data: pd.DataFrame, trades: List[Dict],
                                   strategy_name: str, params: Dict = None) -> go.Figure:
        aligned_trades = BacktestVisualizer._align_trades_with_data(data, trades)
        
        if strategy_name == '双均线策略':
            return BacktestVisualizer._create_ma_chart(data, aligned_trades, params)
        elif strategy_name == 'RSI策略':
            return BacktestVisualizer._create_rsi_chart(data, aligned_trades, params)
        elif strategy_name == 'MACD策略':
            return BacktestVisualizer._create_macd_chart(data, aligned_trades, params)
        elif strategy_name == '布林带策略':
            return BacktestVisualizer._create_bb_chart(data, aligned_trades, params)
        else:
            return BacktestVisualizer._create_basic_price_chart(data, aligned_trades)
    
    @staticmethod
    def _create_basic_price_chart(data: pd.DataFrame, aligned_trades: List[Dict]) -> go.Figure:
        fig = make_subplots(rows=1, cols=1, shared_xaxes=True, vertical_spacing=0.02)
        
        fig.add_trace(go.Candlestick(
            x=data.index,
            open=data['open'],
            high=data['high'],
            low=data['low'],
            close=data['close'],
            name='K线',
            increasing_line_color='#2ecc71',
            decreasing_line_color='#e74c3c'
        ), row=1, col=1)
        
        BacktestVisualizer._add_aligned_trade_signals(fig, data, aligned_trades)
        
        fig.update_layout(
            title='价格走势与交易信号',
            xaxis_title='日期',
            yaxis_title='价格',
            hovermode='x unified',
            template='plotly_white',
            height=500,
            xaxis_rangeslider_visible=False
        )
        
        return fig
    
    @staticmethod
    def _create_ma_chart(data: pd.DataFrame, aligned_trades: List[Dict], params: Dict) -> go.Figure:
        fast_period = params.get('fast_period', 5)
        slow_period = params.get('slow_period', 20)
        
        data = data.copy()
        data['fast_ma'] = data['close'].rolling(fast_period).mean()
        data['slow_ma'] = data['close'].rolling(slow_period).mean()
        
        fig = make_subplots(rows=1, cols=1, shared_xaxes=True, vertical_spacing=0.02)
        
        fig.add_trace(go.Candlestick(
            x=data.index,
            open=data['open'],
            high=data['high'],
            low=data['low'],
            close=data['close'],
            name='K线',
            increasing_line_color='#2ecc71',
            decreasing_line_color='#e74c3c'
        ), row=1, col=1)
        
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data['fast_ma'],
            name=f'MA{fast_period}',
            line=dict(color=BacktestVisualizer.COLORS['fast_ma'], width=1.5)
        ), row=1, col=1)
        
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data['slow_ma'],
            name=f'MA{slow_period}',
            line=dict(color=BacktestVisualizer.COLORS['slow_ma'], width=1.5)
        ), row=1, col=1)
        
        BacktestVisualizer._add_aligned_trade_signals(fig, data, aligned_trades)
        
        fig.update_layout(
            title='双均线策略 - 价格走势与交易信号',
            xaxis_title='日期',
            yaxis_title='价格',
            hovermode='x unified',
            template='plotly_white',
            height=500,
            xaxis_rangeslider_visible=False
        )
        
        return fig
    
    @staticmethod
    def _create_rsi_chart(data: pd.DataFrame, aligned_trades: List[Dict], params: Dict) -> go.Figure:
        rsi_period = params.get('rsi_period', 14)
        rsi_overbought = params.get('rsi_overbought', 70)
        rsi_oversold = params.get('rsi_oversold', 30)
        
        data = data.copy()
        delta = data['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(rsi_period).mean()
        rs = gain / loss
        data['rsi'] = 100 - (100 / (1 + rs))
        
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                           vertical_spacing=0.05,
                           row_heights=[0.6, 0.4])
        
        fig.add_trace(go.Candlestick(
            x=data.index,
            open=data['open'],
            high=data['high'],
            low=data['low'],
            close=data['close'],
            name='K线',
            increasing_line_color='#2ecc71',
            decreasing_line_color='#e74c3c'
        ), row=1, col=1)
        
        BacktestVisualizer._add_aligned_trade_signals(fig, data, aligned_trades, row=1)
        
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data['rsi'],
            name=f'RSI{rsi_period}',
            line=dict(color=BacktestVisualizer.COLORS['rsi'], width=1.5)
        ), row=2, col=1)
        
        fig.add_hline(
            y=rsi_overbought,
            line_dash="dash",
            line_color="#e74c3c",
            line_width=1,
            row=2,
            col=1
        )
        
        fig.add_hline(
            y=rsi_oversold,
            line_dash="dash",
            line_color="#2ecc71",
            line_width=1,
            row=2,
            col=1
        )
        
        fig.update_layout(
            title='RSI策略 - 价格走势与交易信号',
            hovermode='x unified',
            template='plotly_white',
            height=600,
            xaxis_rangeslider_visible=False,
            showlegend=True
        )
        
        fig.update_yaxes(title_text='价格', row=1, col=1)
        fig.update_yaxes(title_text='RSI', row=2, col=1, range=[0, 100])
        
        return fig
    
    @staticmethod
    def _create_macd_chart(data: pd.DataFrame, aligned_trades: List[Dict], params: Dict) -> go.Figure:
        macd_fast = params.get('macd_fast', 12)
        macd_slow = params.get('macd_slow', 26)
        macd_signal = params.get('macd_signal', 9)
        
        data = data.copy()
        ema_fast = data['close'].ewm(span=macd_fast, adjust=False).mean()
        ema_slow = data['close'].ewm(span=macd_slow, adjust=False).mean()
        data['macd'] = ema_fast - ema_slow
        data['macd_signal'] = data['macd'].ewm(span=macd_signal, adjust=False).mean()
        data['macd_histogram'] = data['macd'] - data['macd_signal']
        
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                           vertical_spacing=0.05,
                           row_heights=[0.6, 0.4])
        
        fig.add_trace(go.Candlestick(
            x=data.index,
            open=data['open'],
            high=data['high'],
            low=data['low'],
            close=data['close'],
            name='K线',
            increasing_line_color='#2ecc71',
            decreasing_line_color='#e74c3c'
        ), row=1, col=1)
        
        BacktestVisualizer._add_aligned_trade_signals(fig, data, aligned_trades, row=1)
        
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data['macd'],
            name='MACD',
            line=dict(color=BacktestVisualizer.COLORS['macd'], width=1.5)
        ), row=2, col=1)
        
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data['macd_signal'],
            name='信号线',
            line=dict(color=BacktestVisualizer.COLORS['signal'], width=1.5)
        ), row=2, col=1)
        
        colors = ['#2ecc71' if val >= 0 else '#e74c3c' for val in data['macd_histogram']]
        fig.add_trace(go.Bar(
            x=data.index,
            y=data['macd_histogram'],
            name='MACD柱',
            marker_color=colors,
            opacity=0.5
        ), row=2, col=1)
        
        fig.update_layout(
            title='MACD策略 - 价格走势与交易信号',
            hovermode='x unified',
            template='plotly_white',
            height=600,
            xaxis_rangeslider_visible=False,
            showlegend=True
        )
        
        fig.update_yaxes(title_text='价格', row=1, col=1)
        fig.update_yaxes(title_text='MACD', row=2, col=1)
        
        return fig
    
    @staticmethod
    def _create_bb_chart(data: pd.DataFrame, aligned_trades: List[Dict], params: Dict) -> go.Figure:
        bb_period = params.get('bb_period', 20)
        bb_dev = params.get('bb_dev', 2.0)
        
        data = data.copy()
        data['bb_mid'] = data['close'].rolling(bb_period).mean()
        data['bb_std'] = data['close'].rolling(bb_period).std()
        data['bb_top'] = data['bb_mid'] + bb_dev * data['bb_std']
        data['bb_bot'] = data['bb_mid'] - bb_dev * data['bb_std']
        
        fig = make_subplots(rows=1, cols=1, shared_xaxes=True, vertical_spacing=0.02)
        
        fig.add_trace(go.Candlestick(
            x=data.index,
            open=data['open'],
            high=data['high'],
            low=data['low'],
            close=data['close'],
            name='K线',
            increasing_line_color='#2ecc71',
            decreasing_line_color='#e74c3c'
        ), row=1, col=1)
        
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data['bb_top'],
            name='上轨',
            line=dict(color=BacktestVisualizer.COLORS['bb_top'], width=1),
            fill=None
        ), row=1, col=1)
        
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data['bb_mid'],
            name='中轨',
            line=dict(color=BacktestVisualizer.COLORS['bb_mid'], width=1.5)
        ), row=1, col=1)
        
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data['bb_bot'],
            name='下轨',
            line=dict(color=BacktestVisualizer.COLORS['bb_bot'], width=1),
            fill='tonexty',
            fillcolor='rgba(52, 152, 219, 0.1)'
        ), row=1, col=1)
        
        BacktestVisualizer._add_aligned_trade_signals(fig, data, aligned_trades)
        
        fig.update_layout(
            title='布林带策略 - 价格走势与交易信号',
            xaxis_title='日期',
            yaxis_title='价格',
            hovermode='x unified',
            template='plotly_white',
            height=500,
            xaxis_rangeslider_visible=False
        )
        
        return fig
    
    @staticmethod
    def _add_aligned_trade_signals(fig: go.Figure, data: pd.DataFrame, 
                                    aligned_trades: List[Dict], row: int = 1):
        buy_dates = []
        buy_prices = []
        sell_dates = []
        sell_prices = []
        
        for trade in aligned_trades:
            idx = trade.get('idx')
            if idx is None or idx >= len(data):
                continue
                
            trade_date = data.index[idx]
            trade_price = trade.get('price', data.iloc[idx]['close'])
            
            if trade['type'] == 'buy':
                buy_dates.append(trade_date)
                buy_prices.append(trade_price)
            else:
                sell_dates.append(trade_date)
                sell_prices.append(trade_price)
        
        fig.add_trace(go.Scatter(
            x=buy_dates,
            y=buy_prices,
            mode='markers',
            name='买入',
            marker=dict(
                symbol='triangle-up',
                size=15,
                color=BacktestVisualizer.COLORS['buy'],
                line=dict(width=2, color='white')
            ),
            hovertemplate='买入<br>日期: %{x}<br>价格: ¥%{y:.2f}'
        ), row=row, col=1)
        
        fig.add_trace(go.Scatter(
            x=sell_dates,
            y=sell_prices,
            mode='markers',
            name='卖出',
            marker=dict(
                symbol='triangle-down',
                size=15,
                color=BacktestVisualizer.COLORS['sell'],
                line=dict(width=2, color='white')
            ),
            hovertemplate='卖出<br>日期: %{x}<br>价格: ¥%{y:.2f}'
        ), row=row, col=1)
    
    @staticmethod
    def create_monthly_returns_heatmap(metrics: Dict, data: pd.DataFrame) -> go.Figure:
        equity_curve = metrics.get('equity_curve', [])
        
        if len(equity_curve) == len(data):
            dates = data.index
            equity = pd.Series(equity_curve, index=dates)
        else:
            min_len = min(len(equity_curve), len(data))
            dates = data.index[:min_len]
            equity = pd.Series(equity_curve[:min_len], index=dates)
        
        monthly_returns = equity.resample('ME').last().pct_change() * 100
        monthly_returns = monthly_returns.dropna()
        
        heatmap_data = pd.DataFrame({
            'year': monthly_returns.index.year,
            'month': monthly_returns.index.month,
            'return': monthly_returns.values
        })
        
        pivot = heatmap_data.pivot(index='year', columns='month', values='return')
        
        month_names = ['1月', '2月', '3月', '4月', '5月', '6月', 
                      '7月', '8月', '9月', '10月', '11月', '12月']
        
        pivot.columns = pivot.columns.astype(int)
        cols_to_use = [c for c in pivot.columns if c >= 1 and c <= 12]
        pivot = pivot[cols_to_use]
        
        display_month_names = [month_names[i-1] for i in cols_to_use]
        
        fig = go.Figure(data=go.Heatmap(
            z=pivot.values,
            x=display_month_names,
            y=pivot.index,
            colorscale='RdYlGn',
            zmid=0,
            text=[[f'{val:.2f}%' if not pd.isna(val) else '' for val in row] for row in pivot.values],
            texttemplate='%{text}',
            textfont={"size": 10},
            hoverongaps=False,
            hovertemplate='%{y}年%{x}<br>收益: %{z:.2f}%'
        ))
        
        fig.update_layout(
            title='月度收益热力图',
            xaxis_title='月份',
            yaxis_title='年份',
            template='plotly_white',
            height=400
        )
        
        return fig
    
    @staticmethod
    def create_param_heatmap(heatmap_data: pd.DataFrame, optimize_by: str) -> go.Figure:
        fig = go.Figure(data=go.Heatmap(
            z=heatmap_data.values,
            x=heatmap_data.columns,
            y=heatmap_data.index,
            colorscale='Viridis',
            text=[[f'{val:.3f}' if not pd.isna(val) else '' for val in row] for row in heatmap_data.values],
            texttemplate='%{text}',
            textfont={"size": 10},
            hoverongaps=False,
            hovertemplate=f'{optimize_by}: %{{z:.3f}}<br>参数: %{{x}}, %{{y}}'
        ))
        
        fig.update_layout(
            title=f'参数优化热力图 ({optimize_by})',
            xaxis_title=heatmap_data.columns.name or '参数1',
            yaxis_title=heatmap_data.index.name or '参数2',
            template='plotly_white',
            height=500
        )
        
        return fig
    
    @staticmethod
    def create_trade_analysis_chart(trades: List[Dict]) -> go.Figure:
        if len(trades) < 2:
            fig = go.Figure()
            fig.add_annotation(
                text="交易次数不足，无法生成分析图表",
                xref="paper", yref="paper",
                x=0.5, y=0.5,
                showarrow=False,
                font=dict(size=16)
            )
            fig.update_layout(height=400, template='plotly_white')
            return fig
        
        completed_trades = []
        for i in range(1, len(trades)):
            if trades[i]['type'] == 'sell' and trades[i-1]['type'] == 'buy':
                pnl = trades[i].get('pnl', 0)
                completed_trades.append({
                    'date': trades[i].get('timestamp', trades[i].get('date')),
                    'pnl': pnl,
                    'winning': pnl > 0
                })
        
        if not completed_trades:
            fig = go.Figure()
            fig.add_annotation(
                text="没有完成的交易",
                xref="paper", yref="paper",
                x=0.5, y=0.5,
                showarrow=False,
                font=dict(size=16)
            )
            fig.update_layout(height=400, template='plotly_white')
            return fig
        
        df = pd.DataFrame(completed_trades)
        
        fig = make_subplots(rows=2, cols=2, subplot_titles=(
            '盈亏分布', '累计盈亏', '交易统计', '平均盈亏'
        ))
        
        pnl_values = df['pnl'].values
        fig.add_trace(go.Histogram(
            x=pnl_values,
            nbinsx=20,
            name='盈亏分布',
            marker_color='#1f77b4'
        ), row=1, col=1)
        
        cumulative_pnl = np.cumsum(df['pnl'].values)
        fig.add_trace(go.Scatter(
            x=df['date'],
            y=cumulative_pnl,
            name='累计盈亏',
            line=dict(color='#1f77b4', width=2),
            fill='tozeroy',
            fillcolor='rgba(31, 119, 180, 0.3)'
        ), row=1, col=2)
        
        win_trades = df[df['winning']]
        lose_trades = df[~df['winning']]
        
        fig.add_trace(go.Bar(
            x=['盈利交易', '亏损交易'],
            y=[len(win_trades), len(lose_trades)],
            name='交易数量',
            marker_color=['#2ecc71', '#e74c3c'],
            text=[len(win_trades), len(lose_trades)],
            textposition='auto'
        ), row=2, col=1)
        
        avg_win = win_trades['pnl'].mean() if len(win_trades) > 0 else 0
        avg_loss = lose_trades['pnl'].mean() if len(lose_trades) > 0 else 0
        
        fig.add_trace(go.Bar(
            x=['平均盈利', '平均亏损'],
            y=[avg_win, abs(avg_loss)],
            name='平均盈亏',
            marker_color=['#2ecc71', '#e74c3c'],
            text=[f'¥{avg_win:.2f}', f'¥{abs(avg_loss):.2f}'],
            textposition='auto'
        ), row=2, col=2)
        
        fig.update_layout(
            title='交易分析',
            template='plotly_white',
            height=600,
            showlegend=False
        )
        
        return fig
