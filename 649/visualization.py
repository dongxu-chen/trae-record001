import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import List, Dict, Optional


class ChartVisualizer:
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy().sort_index()
    
    def create_candlestick_chart(self, 
                                  patterns: List[Dict],
                                  title: str = "K线图与形态识别",
                                  show_volume: bool = True) -> go.Figure:
        if show_volume:
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                               vertical_spacing=0.03, 
                               row_heights=[0.7, 0.3])
        else:
            fig = make_subplots(rows=1, cols=1)
        
        candlestick = go.Candlestick(
            x=self.df.index,
            open=self.df['Open'],
            high=self.df['High'],
            low=self.df['Low'],
            close=self.df['Close'],
            name='K线',
            increasing_line_color='#26a69a',
            decreasing_line_color='#ef5350'
        )
        
        if show_volume:
            fig.add_trace(candlestick, row=1, col=1)
            
            colors = ['#26a69a' if self.df['Close'].iloc[i] >= self.df['Open'].iloc[i] 
                      else '#ef5350' for i in range(len(self.df))]
            
            volume = go.Bar(
                x=self.df.index,
                y=self.df.get('Volume', [0] * len(self.df)),
                name='成交量',
                marker_color=colors,
                opacity=0.7
            )
            fig.add_trace(volume, row=2, col=1)
            fig.update_yaxes(title_text="成交量", row=2, col=1)
        else:
            fig.add_trace(candlestick, row=1, col=1)
        
        fig = self._add_pattern_markers(fig, patterns, show_volume)
        
        fig.update_layout(
            title=title,
            xaxis_rangeslider_visible=False,
            template='plotly_white',
            hovermode='x unified',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        fig.update_yaxes(title_text="价格", row=1, col=1)
        
        return fig
    
    def _add_pattern_markers(self, fig: go.Figure, patterns: List[Dict], show_volume: bool) -> go.Figure:
        row = 1
        
        pattern_colors = {
            'Hammer': '#ff9800',
            'Hanging Man': '#ff5722',
            'Bullish Engulfing': '#4caf50',
            'Bearish Engulfing': '#f44336',
            'Head & Shoulders': '#9c27b0',
            'Inverse H&S': '#673ab7',
            'Double Top': '#e91e63',
            'Double Bottom': '#00bcd4'
        }
        
        pattern_markers = {
            'bullish': 'triangle-up',
            'bearish': 'triangle-down'
        }
        
        for pattern in patterns:
            pattern_name = pattern['pattern']
            pattern_type = pattern['type']
            date = pattern['date']
            price = pattern['price']
            confidence = pattern['confidence']
            is_combo = pattern.get('is_combo', False)
            
            if is_combo:
                color = '#ffd700'
                symbol = 'star'
                size = 18 + int(confidence * 12)
                border_color = '#ff6f00'
                border_width = 3
                
                details = pattern.get('details', {})
                boost = details.get('boost_factor', 1.0)
                desc = details.get('description', '')
                hover_text = (
                    f"⚡ 组合形态: {pattern_name}<br>"
                    f"日期: {date}<br>"
                    f"价格: {price:.2f}<br>"
                    f"置信度: {confidence:.0%}<br>"
                    f"信号增强: {boost:.1f}x<br>"
                    f"预测: {'上涨' if pattern_type == 'bullish' else '下跌'}<br>"
                    f"{desc}"
                )
            else:
                color = pattern_colors.get(pattern_name, '#2196f3')
                symbol = pattern_markers.get(pattern_type, 'circle')
                size = 12 + int(confidence * 8)
                border_color = 'white'
                border_width = 2
                hover_text = (
                    f"{pattern_name}<br>"
                    f"日期: {date}<br>"
                    f"价格: {price:.2f}<br>"
                    f"置信度: {confidence:.0%}<br>"
                    f"预测: {'上涨' if pattern_type == 'bullish' else '下跌'}"
                )
            
            marker = go.Scatter(
                x=[date],
                y=[price * 0.98 if pattern_type == 'bullish' else price * 1.02],
                mode='markers',
                marker=dict(
                    symbol=symbol,
                    size=size,
                    color=color,
                    line=dict(width=border_width, color=border_color)
                ),
                name=f"{'⚡' if is_combo else ''}{pattern_name} ({confidence:.0%})",
                text=[hover_text],
                hoverinfo='text',
                showlegend=True
            )
            
            fig.add_trace(marker, row=row, col=1)
        
        return fig
    
    def create_equity_curve(self, 
                            equity_curve: pd.Series,
                            benchmark_curve: Optional[pd.Series] = None,
                            title: str = "资金曲线") -> go.Figure:
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=equity_curve.index,
            y=equity_curve.values,
            mode='lines',
            name='策略收益',
            line=dict(color='#2196f3', width=2)
        ))
        
        if benchmark_curve is not None:
            fig.add_trace(go.Scatter(
                x=benchmark_curve.index,
                y=benchmark_curve.values,
                mode='lines',
                name='基准收益',
                line=dict(color='#ff9800', width=2, dash='dash')
            ))
        
        fig.update_layout(
            title=title,
            xaxis_title='日期',
            yaxis_title='资金',
            template='plotly_white',
            hovermode='x unified'
        )
        
        return fig
    
    def create_drawdown_chart(self, equity_curve: pd.Series, title: str = "回撤曲线") -> go.Figure:
        running_max = equity_curve.expanding().max()
        drawdown = (equity_curve - running_max) / running_max * 100
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=drawdown.index,
            y=drawdown.values,
            mode='lines',
            name='回撤',
            fill='tozeroy',
            fillcolor='rgba(244, 67, 54, 0.3)',
            line=dict(color='#f44336', width=2)
        ))
        
        fig.update_layout(
            title=title,
            xaxis_title='日期',
            yaxis_title='回撤 (%)',
            template='plotly_white',
            hovermode='x unified'
        )
        
        return fig
    
    def create_monthly_returns_heatmap(self, equity_curve: pd.Series, title: str = "月度收益率热力图") -> go.Figure:
        monthly_returns = equity_curve.resample('M').last().pct_change() * 100
        
        returns_df = pd.DataFrame({
            'year': monthly_returns.index.year,
            'month': monthly_returns.index.month,
            'return': monthly_returns.values
        })
        
        pivot_df = returns_df.pivot(index='year', columns='month', values='return')
        
        month_names = ['1月', '2月', '3月', '4月', '5月', '6月', 
                      '7月', '8月', '9月', '10月', '11月', '12月']
        
        fig = go.Figure(data=go.Heatmap(
            z=pivot_df.values,
            x=month_names[:pivot_df.shape[1]],
            y=pivot_df.index,
            colorscale='RdYlGn',
            zmid=0,
            text=[[f"{v:.1f}%" if not pd.isna(v) else "" for v in row] for row in pivot_df.values],
            texttemplate="%{text}",
            textfont={"size": 10},
            hoverongaps=False
        ))
        
        fig.update_layout(
            title=title,
            template='plotly_white'
        )
        
        return fig
    
    def create_pattern_performance_chart(self, 
                                         pattern_stats: pd.DataFrame,
                                         title: str = "各形态表现统计") -> go.Figure:
        if pattern_stats.empty:
            return go.Figure().update_layout(title=title + " (无数据)")
        
        fig = make_subplots(rows=1, cols=2, subplot_titles=('胜率', '平均盈亏'))
        
        fig.add_trace(go.Bar(
            x=pattern_stats.index,
            y=pattern_stats['win_rate'] * 100,
            name='胜率 (%)',
            marker_color='#4caf50'
        ), row=1, col=1)
        
        fig.add_trace(go.Bar(
            x=pattern_stats.index,
            y=pattern_stats['avg_pnl'],
            name='平均盈亏',
            marker_color='#2196f3'
        ), row=1, col=2)
        
        fig.update_layout(
            title=title,
            template='plotly_white',
            showlegend=False
        )
        
        fig.update_yaxes(title_text="胜率 (%)", row=1, col=1)
        fig.update_yaxes(title_text="平均盈亏", row=1, col=2)
        
        return fig
    
    def create_success_rate_chart(self, 
                                   success_df: pd.DataFrame,
                                   title: str = "各形态历史成功率") -> go.Figure:
        if success_df.empty:
            return go.Figure().update_layout(title=title + " (无数据)")
        
        valid_df = success_df.dropna(subset=['success_rate'])
        if valid_df.empty:
            return go.Figure().update_layout(title=title + " (数据不足)")
        
        fig = make_subplots(
            rows=1, cols=3,
            subplot_titles=('历史胜率', '平均收益率', '样本数'),
            horizontal_spacing=0.12
        )
        
        colors = ['#4caf50' if r >= 0.5 else '#f44336' for r in valid_df['success_rate']]
        
        fig.add_trace(go.Bar(
            x=valid_df['pattern'],
            y=valid_df['success_rate'] * 100,
            name='胜率',
            marker_color=colors,
            text=[f"{r:.1f}%" for r in valid_df['success_rate'] * 100],
            textposition='outside'
        ), row=1, col=1)
        
        fig.add_hline(y=50, line_dash="dash", line_color="gray", row=1, col=1)
        
        return_colors = ['#26a69a' if r >= 0 else '#ef5350' for r in valid_df['avg_return']]
        fig.add_trace(go.Bar(
            x=valid_df['pattern'],
            y=valid_df['avg_return'] * 100,
            name='平均收益率',
            marker_color=return_colors,
            text=[f"{r:.2f}%" for r in valid_df['avg_return'] * 100],
            textposition='outside'
        ), row=1, col=2)
        
        fig.add_trace(go.Bar(
            x=valid_df['pattern'],
            y=valid_df['total'],
            name='样本数',
            marker_color='#2196f3',
            text=[str(int(t)) for t in valid_df['total']],
            textposition='outside'
        ), row=1, col=3)
        
        fig.update_layout(
            title=title,
            template='plotly_white',
            showlegend=False
        )
        
        fig.update_yaxes(title_text="胜率 (%)", row=1, col=1)
        fig.update_yaxes(title_text="收益率 (%)", row=1, col=2)
        fig.update_yaxes(title_text="次数", row=1, col=3)
        
        return fig
    
    def create_rolling_success_chart(self,
                                      rolling_df: pd.DataFrame,
                                      title: str = "滚动成功率趋势") -> go.Figure:
        if rolling_df.empty:
            return go.Figure().update_layout(title=title + " (无数据)")
        
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                           vertical_spacing=0.08,
                           subplot_titles=('滚动胜率', '滚动平均收益率'))
        
        fig.add_trace(go.Scatter(
            x=rolling_df['date'],
            y=rolling_df['rolling_success_rate'] * 100,
            mode='lines+markers',
            name='滚动胜率',
            line=dict(color='#2196f3', width=2),
            marker=dict(size=4)
        ), row=1, col=1)
        
        fig.add_hline(y=50, line_dash="dash", line_color="gray", row=1, col=1)
        
        colors = ['#26a69a' if r >= 0 else '#ef5350' for r in rolling_df['rolling_avg_return']]
        fig.add_trace(go.Bar(
            x=rolling_df['date'],
            y=rolling_df['rolling_avg_return'] * 100,
            name='滚动收益率',
            marker_color=colors
        ), row=2, col=1)
        
        fig.update_layout(
            title=title,
            template='plotly_white',
            hovermode='x unified'
        )
        
        fig.update_yaxes(title_text="胜率 (%)", row=1, col=1)
        fig.update_yaxes(title_text="收益率 (%)", row=2, col=1)
        
        return fig
    
    def create_alert_panel(self, 
                            alerts: list,
                            title: str = "形态预警面板") -> go.Figure:
        fig = go.Figure()
        
        fig.add_annotation(
            text=f"<b>{title}</b><br>共 {len(alerts)} 条预警",
            xref="paper", yref="paper",
            x=0.5, y=0.98,
            showarrow=False,
            font=dict(size=16)
        )
        
        y_pos = 0.90
        for i, alert in enumerate(alerts[:15]):
            direction_icon = "🟢" if alert.direction.value == "bullish" else "🔴"
            combo_icon = "⚡" if alert.is_combo else "📌"
            
            text = (
                f"{direction_icon} {combo_icon} <b>{alert.pattern_name}</b><br>"
                f"&nbsp;&nbsp;&nbsp;{alert.date.strftime('%Y-%m-%d')} | "
                f"价格: {alert.price:.2f} | "
                f"置信度: {alert.confidence:.0%}<br>"
                f"&nbsp;&nbsp;&nbsp;预测: {'上涨' if alert.prediction == 'up' else '下跌'}"
            )
            
            fig.add_annotation(
                text=text,
                xref="paper", yref="paper",
                x=0.05, y=y_pos,
                showarrow=False,
                align="left",
                font=dict(size=12)
            )
            y_pos -= 0.12
        
        fig.update_layout(
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            template='plotly_white',
            height=max(300, 100 + len(alerts[:15]) * 80)
        )
        
        return fig
