import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import talib
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import time
import hashlib

st.set_page_config(
    page_title="股票量价因子可视化分析平台",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main {
        background-color: #0e1117;
    }
    .stMetric {
        background-color: #1e2130;
        padding: 10px;
        border-radius: 5px;
    }
    .signal-buy {
        background-color: rgba(0, 255, 0, 0.2) !important;
    }
    .signal-sell {
        background-color: rgba(255, 0, 0, 0.2) !important;
    }
    .stButton button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)


def params_hash(params):
    return hashlib.md5(str(sorted(params.items())).encode()).hexdigest()


@st.cache_data(show_spinner=False, ttl=3600)
def get_stock_data(ticker, start_date, end_date):
    try:
        data = yf.download(ticker, start=start_date, end=end_date, progress=False)
        if data.empty:
            return None
        data.columns = ['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']
        return data
    except Exception as e:
        st.error(f"获取股票数据失败: {e}")
        return None


@st.cache_data(show_spinner=False)
def calculate_factors_cached(data_hash, params_json, data):
    df = data.copy()
    
    df['RSI'] = talib.RSI(df['Close'], timeperiod=params_json['rsi_period'])
    df['RSI2'] = talib.RSI(df['Close'], timeperiod=params_json['rsi_period2'])
    df['RSI3'] = talib.RSI(df['Close'], timeperiod=params_json['rsi_period3'])
    
    df['MACD'], df['MACD_Signal'], df['MACD_Hist'] = talib.MACD(
        df['Close'],
        fastperiod=params_json['macd_fast'],
        slowperiod=params_json['macd_slow'],
        signalperiod=params_json['macd_signal']
    )
    
    low_min = df['Low'].rolling(window=params_json['kdj_n']).min()
    high_max = df['High'].rolling(window=params_json['kdj_n']).max()
    rsv = (df['Close'] - low_min) / (high_max - low_min) * 100
    rsv = rsv.fillna(50)
    
    df['K'] = rsv.ewm(alpha=1/params_json['kdj_m1'], adjust=False).mean()
    df['D'] = df['K'].ewm(alpha=1/params_json['kdj_m2'], adjust=False).mean()
    df['J'] = 3 * df['K'] - 2 * df['D']
    
    df['BB_Upper'], df['BB_Middle'], df['BB_Lower'] = talib.BBANDS(
        df['Close'],
        timeperiod=params_json['bb_period'],
        nbdevup=params_json['bb_std'],
        nbdevdn=params_json['bb_std'],
        matype=0
    )
    df['BB_Width'] = (df['BB_Upper'] - df['BB_Lower']) / df['BB_Middle']
    
    df['Volume_MA'] = df['Volume'].rolling(window=params_json['volume_ma_period']).mean()
    df['Volume_Std'] = df['Volume'].rolling(window=params_json['volume_ma_period']).std()
    df['Volume_CV'] = df['Volume_Std'] / df['Volume_MA']
    df['Volume_Ratio'] = df['Volume'] / df['Volume_MA']
    
    return df


@st.cache_data(show_spinner=False)
def generate_signals_cached(factors_hash, params_json, df_factors):
    df = df_factors.copy()
    signals = pd.DataFrame(index=df.index)
    signals['Price'] = df['Close']
    
    signal_details = {}
    
    signals['RSI_Signal'] = 0
    rsi_buy = (df['RSI'] < params_json['rsi_oversold'])
    rsi_sell = (df['RSI'] > params_json['rsi_overbought'])
    signals.loc[rsi_buy, 'RSI_Signal'] = 1
    signals.loc[rsi_sell, 'RSI_Signal'] = -1
    signal_details['RSI'] = {'buy': rsi_buy, 'sell': rsi_sell}
    
    signals['MACD_Signal'] = 0
    macd_buy = (df['MACD'] > df['MACD_Signal']) & (df['MACD'].shift(1) <= df['MACD_Signal'].shift(1))
    macd_sell = (df['MACD'] < df['MACD_Signal']) & (df['MACD'].shift(1) >= df['MACD_Signal'].shift(1))
    signals.loc[macd_buy, 'MACD_Signal'] = 1
    signals.loc[macd_sell, 'MACD_Signal'] = -1
    signal_details['MACD'] = {'buy': macd_buy, 'sell': macd_sell}
    
    signals['KDJ_Signal'] = 0
    kdj_buy = (df['K'] > df['D']) & (df['K'].shift(1) <= df['D'].shift(1)) & (df['K'] < params_json['kdj_oversold'])
    kdj_sell = (df['K'] < df['D']) & (df['K'].shift(1) >= df['D'].shift(1)) & (df['K'] > params_json['kdj_overbought'])
    signals.loc[kdj_buy, 'KDJ_Signal'] = 1
    signals.loc[kdj_sell, 'KDJ_Signal'] = -1
    signal_details['KDJ'] = {'buy': kdj_buy, 'sell': kdj_sell}
    
    signals['BB_Signal'] = 0
    bb_buy = (df['Close'] <= df['BB_Lower']) & (df['Close'].shift(1) > df['BB_Lower'].shift(1))
    bb_sell = (df['Close'] >= df['BB_Upper']) & (df['Close'].shift(1) < df['BB_Upper'].shift(1))
    signals.loc[bb_buy, 'BB_Signal'] = 1
    signals.loc[bb_sell, 'BB_Signal'] = -1
    signal_details['BB'] = {'buy': bb_buy, 'sell': bb_sell}
    
    signals['Volume_Signal'] = 0
    volume_buy = (df['Volume_Ratio'] > params_json['volume_threshold']) & (df['Close'] > df['Close'].shift(1))
    volume_sell = (df['Volume_Ratio'] > params_json['volume_threshold']) & (df['Close'] < df['Close'].shift(1))
    signals.loc[volume_buy, 'Volume_Signal'] = 1
    signals.loc[volume_sell, 'Volume_Signal'] = -1
    signal_details['Volume'] = {'buy': volume_buy, 'sell': volume_sell}
    
    signal_cols = ['RSI_Signal', 'MACD_Signal', 'KDJ_Signal', 'BB_Signal', 'Volume_Signal']
    signals['Buy_Count'] = (signals[signal_cols] == 1).sum(axis=1)
    signals['Sell_Count'] = (signals[signal_cols] == -1).sum(axis=1)
    signals['Combined_Score'] = signals[signal_cols].sum(axis=1)
    
    signals['Final_Signal'] = 0
    signals.loc[signals['Combined_Score'] >= params_json['buy_threshold'], 'Final_Signal'] = 1
    signals.loc[signals['Combined_Score'] <= -params_json['sell_threshold'], 'Final_Signal'] = -1
    
    return signals, signal_details


@st.cache_data(show_spinner=False)
def backtest_cached(signals_hash, signals, initial_capital):
    df = signals.copy()
    df['Position'] = 0
    df['Holdings'] = 0.0
    df['Cash'] = float(initial_capital)
    df['Total'] = float(initial_capital)
    
    position = 0
    cash = float(initial_capital)
    holdings = 0.0
    
    for i in range(len(df)):
        if df['Final_Signal'].iloc[i] == 1 and position == 0:
            shares = int(cash / df['Price'].iloc[i] / 100) * 100
            if shares > 0:
                holdings = shares
                cash -= shares * df['Price'].iloc[i]
                position = 1
        elif df['Final_Signal'].iloc[i] == -1 and position == 1:
            cash += holdings * df['Price'].iloc[i]
            holdings = 0.0
            position = 0
        
        df.loc[df.index[i], 'Position'] = position
        df.loc[df.index[i], 'Holdings'] = holdings
        df.loc[df.index[i], 'Cash'] = cash
        df.loc[df.index[i], 'Total'] = cash + holdings * df['Price'].iloc[i]
    
    df['Returns'] = df['Total'].pct_change()
    df['Cumulative_Returns'] = (1 + df['Returns']).cumprod()
    
    return df


def calculate_metrics(backtest_df, initial_capital=100000):
    total_return = (backtest_df['Total'].iloc[-1] - initial_capital) / initial_capital
    
    trading_days = len(backtest_df)
    annual_return = (1 + total_return) ** (252 / trading_days) - 1 if trading_days > 0 else 0
    
    daily_returns = backtest_df['Returns'].dropna()
    if len(daily_returns) > 0:
        sharpe_ratio = np.sqrt(252) * daily_returns.mean() / daily_returns.std() if daily_returns.std() != 0 else 0
        max_drawdown = (backtest_df['Total'] / backtest_df['Total'].cummax() - 1).min()
        volatility = daily_returns.std() * np.sqrt(252)
    else:
        sharpe_ratio = 0
        max_drawdown = 0
        volatility = 0
    
    win_trades = 0
    total_trades = 0
    position = 0
    entry_price = 0
    
    for i in range(len(backtest_df)):
        if backtest_df['Final_Signal'].iloc[i] == 1 and position == 0:
            position = 1
            entry_price = backtest_df['Price'].iloc[i]
            total_trades += 1
        elif backtest_df['Final_Signal'].iloc[i] == -1 and position == 1:
            position = 0
            exit_price = backtest_df['Price'].iloc[i]
            if exit_price > entry_price:
                win_trades += 1
    
    win_rate = win_trades / total_trades if total_trades > 0 else 0
    
    return {
        'Total Return': f"{total_return*100:.2f}%",
        'Annual Return': f"{annual_return*100:.2f}%",
        'Sharpe Ratio': f"{sharpe_ratio:.2f}",
        'Max Drawdown': f"{max_drawdown*100:.2f}%",
        'Volatility': f"{volatility*100:.2f}%",
        'Win Rate': f"{win_rate*100:.2f}%",
        'Total Trades': total_trades,
        'Final Value': f"¥{backtest_df['Total'].iloc[-1]:,.2f}"
    }


def plot_price_with_aggregated_signals(df, signals, signal_details):
    fig = go.Figure()
    
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close'],
        name='K线',
        increasing_line_color='#ff6b6b',
        decreasing_line_color='#4ecdc4'
    ))
    
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df['BB_Upper'],
        name='布林上轨',
        line=dict(color='rgba(255, 165, 0, 0.5)', width=1),
        showlegend=True
    ))
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df['BB_Lower'],
        name='布林下轨',
        line=dict(color='rgba(255, 165, 0, 0.5)', width=1),
        fill='tonexty',
        fillcolor='rgba(255, 165, 0, 0.1)',
        showlegend=True
    ))
    
    buy_signals = signals[signals['Buy_Count'] > 0]
    for idx, row in buy_signals.iterrows():
        count = int(row['Buy_Count'])
        price = df.loc[idx, 'Low'] * 0.995
        
        active_factors = []
        if signal_details['RSI']['buy'].loc[idx]:
            active_factors.append('RSI')
        if signal_details['MACD']['buy'].loc[idx]:
            active_factors.append('MACD')
        if signal_details['KDJ']['buy'].loc[idx]:
            active_factors.append('KDJ')
        if signal_details['BB']['buy'].loc[idx]:
            active_factors.append('BB')
        if signal_details['Volume']['buy'].loc[idx]:
            active_factors.append('VOL')
        
        hover_text = f"买入信号 ({count}个)<br>日期: {idx.strftime('%Y-%m-%d')}<br>价格: {df.loc[idx, 'Close']:.2f}<br>因子: {', '.join(active_factors)}"
        
        fig.add_annotation(
            x=idx,
            y=price,
            text=f"▲{count}",
            showarrow=False,
            font=dict(size=14, color='white', family='Arial Black'),
            bgcolor='rgba(0, 180, 0, 0.9)',
            bordercolor='lime',
            borderwidth=2,
            borderpad=3,
            hovertext=hover_text,
            hoverlabel=dict(bgcolor='green', font=dict(color='white')),
            xanchor='center',
            yanchor='top'
        )
    
    sell_signals = signals[signals['Sell_Count'] > 0]
    for idx, row in sell_signals.iterrows():
        count = int(row['Sell_Count'])
        price = df.loc[idx, 'High'] * 1.005
        
        active_factors = []
        if signal_details['RSI']['sell'].loc[idx]:
            active_factors.append('RSI')
        if signal_details['MACD']['sell'].loc[idx]:
            active_factors.append('MACD')
        if signal_details['KDJ']['sell'].loc[idx]:
            active_factors.append('KDJ')
        if signal_details['BB']['sell'].loc[idx]:
            active_factors.append('BB')
        if signal_details['Volume']['sell'].loc[idx]:
            active_factors.append('VOL')
        
        hover_text = f"卖出信号 ({count}个)<br>日期: {idx.strftime('%Y-%m-%d')}<br>价格: {df.loc[idx, 'Close']:.2f}<br>因子: {', '.join(active_factors)}"
        
        fig.add_annotation(
            x=idx,
            y=price,
            text=f"▼{count}",
            showarrow=False,
            font=dict(size=14, color='white', family='Arial Black'),
            bgcolor='rgba(180, 0, 0, 0.9)',
            bordercolor='red',
            borderwidth=2,
            borderpad=3,
            hovertext=hover_text,
            hoverlabel=dict(bgcolor='red', font=dict(color='white')),
            xanchor='center',
            yanchor='bottom'
        )
    
    fig.update_layout(
        title='股价走势与聚合买卖信号 (数字为信号数量)',
        xaxis_title='日期',
        yaxis_title='价格',
        height=550,
        xaxis_rangeslider_visible=False,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white'),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    return fig


def plot_rsi(df, params):
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df['RSI'],
        name=f'RSI{params["rsi_period"]}',
        line=dict(color='#9c27b0', width=2)
    ))
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df['RSI2'],
        name=f'RSI{params["rsi_period2"]}',
        line=dict(color='#e91e63', width=1.5, dash='dash')
    ))
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df['RSI3'],
        name=f'RSI{params["rsi_period3"]}',
        line=dict(color='#f44336', width=1.5, dash='dot')
    ))
    
    fig.add_hline(y=params['rsi_overbought'], line_dash="dash", line_color="red", 
                  annotation_text=f"超买 ({params['rsi_overbought']})", 
                  annotation_position="top right")
    fig.add_hline(y=params['rsi_oversold'], line_dash="dash", line_color="green", 
                  annotation_text=f"超卖 ({params['rsi_oversold']})", 
                  annotation_position="bottom right")
    fig.add_hline(y=50, line_dash="dash", line_color="gray", 
                  annotation_text="多空线 (50)", 
                  annotation_position="middle right")
    
    fig.update_layout(
        title='RSI 指标 (通达信风格: 6/12/24)',
        xaxis_title='日期',
        yaxis_title='RSI 值',
        height=300,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white'),
        yaxis=dict(range=[0, 100])
    )
    
    return fig


def plot_macd(df):
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df['MACD'],
        name='DIF',
        line=dict(color='#2196f3', width=2)
    ))
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df['MACD_Signal'],
        name='DEA',
        line=dict(color='#ff9800', width=2)
    ))
    
    colors = ['#4caf50' if val >= 0 else '#f44336' for val in df['MACD_Hist']]
    fig.add_trace(go.Bar(
        x=df.index,
        y=df['MACD_Hist'],
        name='MACD柱',
        marker_color=colors,
        opacity=0.7
    ))
    
    fig.update_layout(
        title='MACD 指标 (通达信风格: 12/26/9)',
        xaxis_title='日期',
        yaxis_title='MACD 值',
        height=300,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white'),
        barmode='relative'
    )
    
    return fig


def plot_kdj(df):
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df['K'],
        name='K',
        line=dict(color='#2196f3', width=2)
    ))
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df['D'],
        name='D',
        line=dict(color='#ff9800', width=2)
    ))
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df['J'],
        name='J',
        line=dict(color='#9c27b0', width=2)
    ))
    
    fig.add_hline(y=80, line_dash="dash", line_color="red", annotation_text="超买 (80)")
    fig.add_hline(y=20, line_dash="dash", line_color="green", annotation_text="超卖 (20)")
    fig.add_hline(y=50, line_dash="dash", line_color="gray", annotation_text="多空线 (50)")
    
    fig.update_layout(
        title='KDJ 指标 (通达信风格: 9/3/3)',
        xaxis_title='日期',
        yaxis_title='KDJ 值',
        height=300,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white'),
        yaxis=dict(range=[-10, 110])
    )
    
    return fig


def plot_volume(df):
    fig = go.Figure()
    
    colors = ['#ff6b6b' if df['Close'].iloc[i] < df['Open'].iloc[i] else '#4ecdc4' for i in range(len(df))]
    
    fig.add_trace(go.Bar(
        x=df.index,
        y=df['Volume'],
        name='成交量',
        marker_color=colors,
        opacity=0.7
    ))
    
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df['Volume_MA'],
        name='均量线',
        line=dict(color='#ff9800', width=2)
    ))
    
    fig.update_layout(
        title='成交量',
        xaxis_title='日期',
        yaxis_title='成交量',
        height=300,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white')
    )
    
    return fig


def plot_backtest(backtest_df):
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    fig.add_trace(
        go.Scatter(x=backtest_df.index, y=backtest_df['Total'], name='策略净值', 
                   line=dict(color='#4ecdc4', width=2)),
        secondary_y=False,
    )
    
    fig.add_trace(
        go.Scatter(x=backtest_df.index, y=backtest_df['Price'] / backtest_df['Price'].iloc[0] * 100000, 
                   name='持有收益 (基准)', line=dict(color='#ff6b6b', width=2, dash='dash')),
        secondary_y=False,
    )
    
    buy_points = backtest_df[backtest_df['Final_Signal'] == 1]
    sell_points = backtest_df[backtest_df['Final_Signal'] == -1]
    
    fig.add_trace(
        go.Scatter(x=buy_points.index, y=backtest_df.loc[buy_points.index, 'Total'],
                   mode='markers', marker=dict(symbol='triangle-up', size=10, color='lime'),
                   name='买入'),
        secondary_y=False,
    )
    
    fig.add_trace(
        go.Scatter(x=sell_points.index, y=backtest_df.loc[sell_points.index, 'Total'],
                   mode='markers', marker=dict(symbol='triangle-down', size=10, color='red'),
                   name='卖出'),
        secondary_y=False,
    )
    
    fig.update_layout(
        title='策略回测净值曲线',
        xaxis_title='日期',
        yaxis_title='净值',
        height=400,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white'),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    return fig


def main():
    st.title("📈 股票量价因子可视化分析平台")
    st.caption("参数默认适配通达信 | 信号聚合显示 | 智能缓存优化")
    st.markdown("---")
    
    if 'last_params_hash' not in st.session_state:
        st.session_state['last_params_hash'] = None
    if 'needs_update' not in st.session_state:
        st.session_state['needs_update'] = False
    
    with st.sidebar:
        st.header("📊 股票选择")
        
        ticker = st.text_input("股票代码 (如: 600519.SS, AAPL)", value="600519.SS")
        
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("开始日期", value=datetime.now() - timedelta(days=365*2))
        with col2:
            end_date = st.date_input("结束日期", value=datetime.now())
        
        st.markdown("---")
        st.header("⚙️ 因子参数设置 (通达信默认)")
        
        with st.expander("RSI 参数 (6/12/24)", expanded=False):
            rsi_period = st.slider("RSI1 周期", 3, 20, 6, key='rsi1')
            rsi_period2 = st.slider("RSI2 周期", 5, 30, 12, key='rsi2')
            rsi_period3 = st.slider("RSI3 周期", 10, 40, 24, key='rsi3')
            rsi_oversold = st.slider("超卖阈值", 10, 40, 20)
            rsi_overbought = st.slider("超买阈值", 60, 90, 80)
        
        with st.expander("MACD 参数 (12/26/9)", expanded=False):
            macd_fast = st.slider("DIF快周期", 5, 20, 12)
            macd_slow = st.slider("DIF慢周期", 20, 40, 26)
            macd_signal = st.slider("DEA周期", 5, 15, 9)
        
        with st.expander("KDJ 参数 (9/3/3)", expanded=False):
            kdj_n = st.slider("KDJ N周期", 5, 20, 9)
            kdj_m1 = st.slider("K值平滑周期", 2, 10, 3)
            kdj_m2 = st.slider("D值平滑周期", 2, 10, 3)
            kdj_oversold = st.slider("KDJ超卖阈值", 10, 40, 20)
            kdj_overbought = st.slider("KDJ超买阈值", 60, 90, 80)
        
        with st.expander("布林带参数 (20/2)", expanded=False):
            bb_period = st.slider("布林带周期", 10, 30, 20)
            bb_std = st.slider("标准差倍数", 1.0, 3.0, 2.0, step=0.1)
        
        with st.expander("成交量参数 (5/10)", expanded=False):
            volume_ma_period = st.slider("均量线周期", 5, 30, 5)
            volume_threshold = st.slider("量比阈值", 1.0, 3.0, 1.5, step=0.1)
        
        st.markdown("---")
        st.header("🎯 交易信号设置")
        
        buy_threshold = st.slider("买入信号阈值 (因子数量)", 1, 5, 2)
        sell_threshold = st.slider("卖出信号阈值 (因子数量)", 1, 5, 2)
        
        initial_capital = st.number_input("初始资金 (元)", min_value=10000, value=100000, step=10000)
        
        st.markdown("---")
        col_a, col_b = st.columns(2)
        with col_a:
            fetch_button = st.button("📥 获取数据", type="secondary", use_container_width=True)
        with col_b:
            analyze_button = st.button("🚀 分析/回测", type="primary", use_container_width=True)
        
        auto_update = st.checkbox("自动更新参数变化", value=False, help="启用后参数变化自动重新计算（建议关闭以提升性能）")
    
    params = {
        'rsi_period': rsi_period,
        'rsi_period2': rsi_period2,
        'rsi_period3': rsi_period3,
        'rsi_oversold': rsi_oversold,
        'rsi_overbought': rsi_overbought,
        'macd_fast': macd_fast,
        'macd_slow': macd_slow,
        'macd_signal': macd_signal,
        'kdj_n': kdj_n,
        'kdj_m1': kdj_m1,
        'kdj_m2': kdj_m2,
        'kdj_oversold': kdj_oversold,
        'kdj_overbought': kdj_overbought,
        'bb_period': bb_period,
        'bb_std': bb_std,
        'volume_ma_period': volume_ma_period,
        'volume_threshold': volume_threshold,
        'buy_threshold': buy_threshold,
        'sell_threshold': sell_threshold
    }
    
    current_params_hash = params_hash(params)
    data_key = f"{ticker}_{start_date}_{end_date}"
    
    if fetch_button:
        st.session_state['data_loaded'] = False
        with st.spinner('正在获取股票数据...'):
            data = get_stock_data(ticker, start_date, end_date)
            if data is not None:
                st.session_state['data'] = data
                st.session_state['ticker'] = ticker
                st.session_state['data_key'] = data_key
                st.session_state['data_loaded'] = True
                st.session_state['needs_update'] = True
                st.success(f"✅ 成功获取 {ticker} 数据，共 {len(data)} 个交易日")
            else:
                st.error("无法获取股票数据，请检查代码是否正确。")
    
    if 'data' in st.session_state and st.session_state.get('data_loaded', False):
        data = st.session_state['data']
        ticker = st.session_state['ticker']
        
        params_changed = current_params_hash != st.session_state.get('last_params_hash')
        
        if auto_update and params_changed:
            st.session_state['needs_update'] = True
        
        if analyze_button or (auto_update and st.session_state.get('needs_update', False)):
            st.session_state['last_params_hash'] = current_params_hash
            st.session_state['needs_update'] = False
            
            data_hash = hashlib.md5(data.to_csv().encode()).hexdigest()
            
            with st.spinner('正在计算因子...'):
                df_factors = calculate_factors_cached(data_hash, params, data)
            
            with st.spinner('正在生成交易信号...'):
                factors_hash = hashlib.md5(df_factors.to_csv().encode()).hexdigest()
                signals, signal_details = generate_signals_cached(factors_hash, params, df_factors)
            
            with st.spinner('正在执行策略回测...'):
                signals_hash = hashlib.md5(signals.to_csv().encode()).hexdigest()
                backtest_df = backtest_cached(signals_hash, signals, initial_capital)
            
            metrics = calculate_metrics(backtest_df, initial_capital)
            
            st.session_state['df_factors'] = df_factors
            st.session_state['signals'] = signals
            st.session_state['signal_details'] = signal_details
            st.session_state['backtest_df'] = backtest_df
            st.session_state['metrics'] = metrics
            st.session_state['params'] = params
        
        if 'df_factors' in st.session_state:
            df_factors = st.session_state['df_factors']
            signals = st.session_state['signals']
            signal_details = st.session_state['signal_details']
            backtest_df = st.session_state['backtest_df']
            metrics = st.session_state['metrics']
            params = st.session_state['params']
            
            st.header("📊 回测绩效指标")
            metric_cols = st.columns(4)
            metric_cols[0].metric("总收益率", metrics['Total Return'], help="策略总收益率")
            metric_cols[1].metric("年化收益率", metrics['Annual Return'], help="年化收益率")
            metric_cols[2].metric("夏普比率", metrics['Sharpe Ratio'], help="夏普比率越高越好")
            metric_cols[3].metric("最大回撤", metrics['Max Drawdown'], help="最大回撤越小越好")
            
            metric_cols2 = st.columns(4)
            metric_cols2[0].metric("波动率", metrics['Volatility'], help="年化波动率")
            metric_cols2[1].metric("胜率", metrics['Win Rate'], help="盈利交易占比")
            metric_cols2[2].metric("交易次数", metrics['Total Trades'], help="总交易次数")
            metric_cols2[3].metric("最终资产", metrics['Final Value'], help="策略最终资产")
            
            st.markdown("---")
            
            st.header("📈 价格走势与聚合买卖信号")
            st.caption("📌 绿色▲=买入信号 红色▼=卖出信号 数字=当日触发的因子数量")
            fig_price = plot_price_with_aggregated_signals(df_factors, signals, signal_details)
            st.plotly_chart(fig_price, use_container_width=True)
            
            st.header("🔬 因子可视化")
            
            tab1, tab2, tab3, tab4, tab5 = st.tabs(["RSI", "MACD", "KDJ", "布林带", "成交量"])
            
            with tab1:
                fig_rsi = plot_rsi(df_factors, params)
                st.plotly_chart(fig_rsi, use_container_width=True)
                st.info(f"""
                **RSI 说明 (通达信风格):**
                - 三条线: {params['rsi_period']}/{params['rsi_period2']}/{params['rsi_period3']} 天
                - 超卖阈值: {params['rsi_oversold']} (低于此值视为买入信号)
                - 超买阈值: {params['rsi_overbought']} (高于此值视为卖出信号)
                - RSI > 50 表示强势，< 50 表示弱势
                - 三条线多头排列（短>中>长）为强势信号
                """)
            
            with tab2:
                fig_macd = plot_macd(df_factors)
                st.plotly_chart(fig_macd, use_container_width=True)
                st.info(f"""
                **MACD 说明 (通达信风格):**
                - DIF: {params['macd_fast']}日EMA - {params['macd_slow']}日EMA
                - DEA: DIF的{params['macd_signal']}日EMA
                - MACD柱: 2×(DIF-DEA)
                - DIF上穿DEA为金叉（买入信号）
                - DIF下穿DEA为死叉（卖出信号）
                - 柱状由绿翻红为买入信号，由红翻绿为卖出信号
                """)
            
            with tab3:
                fig_kdj = plot_kdj(df_factors)
                st.plotly_chart(fig_kdj, use_container_width=True)
                st.info(f"""
                **KDJ 说明 (通达信风格):**
                - N周期: {params['kdj_n']} 天
                - K值平滑: {params['kdj_m1']} 天
                - D值平滑: {params['kdj_m2']} 天
                - J = 3K - 2D
                - K线上穿D线为金叉（配合超卖区使用）
                - K线下穿D线为死叉（配合超买区使用）
                - J值 > 100 超买，< 0 超卖
                """)
            
            with tab4:
                fig_bb = plot_price_with_aggregated_signals(df_factors, signals, signal_details)
                st.plotly_chart(fig_bb, use_container_width=True)
                st.info(f"""
                **布林带说明 (通达信风格):**
                - 中轨: {params['bb_period']}日移动平均线
                - 上下轨: 中轨 ± {params['bb_std']}倍标准差
                - 价格触及下轨可能反弹（买入信号）
                - 价格触及上轨可能回落（卖出信号）
                - 布林带收窄预示即将有大行情
                - 价格沿上轨运行为强势，沿下轨运行为弱势
                """)
            
            with tab5:
                fig_volume = plot_volume(df_factors)
                st.plotly_chart(fig_volume, use_container_width=True)
                st.info(f"""
                **成交量说明:**
                - 均量线周期: {params['volume_ma_period']} 天
                - 量比阈值: {params['volume_threshold']}
                - 放量上涨：资金进场信号
                - 放量下跌：资金出逃信号
                - 缩量整理：等待方向选择
                - 量价背离是趋势反转的重要信号
                """)
            
            st.markdown("---")
            
            st.header("💹 策略回测")
            fig_backtest = plot_backtest(backtest_df)
            st.plotly_chart(fig_backtest, use_container_width=True)
            
            st.markdown("---")
            
            st.header("📋 交易信号明细")
            
            def get_active_factors(idx, signal_details, signal_type):
                factors = []
                for name, detail in signal_details.items():
                    if detail[signal_type].loc[idx]:
                        factors.append(name)
                return ','.join(factors) if factors else '-'
            
            signal_details_df = pd.DataFrame({
                '日期': signals.index,
                '收盘价': signals['Price'].round(2),
                'RSI': df_factors['RSI'].round(1),
                'MACD': df_factors['MACD'].round(4),
                'K': df_factors['K'].round(1),
                'D': df_factors['D'].round(1),
                '布林位置%': ((df_factors['Close'] - df_factors['BB_Lower']) / (df_factors['BB_Upper'] - df_factors['BB_Lower']) * 100).round(1),
                '量比': df_factors['Volume_Ratio'].round(2),
                '买入因子数': signals['Buy_Count'],
                '卖出因子数': signals['Sell_Count'],
                '综合得分': signals['Combined_Score'],
                '交易信号': signals['Final_Signal'].map({1: '🔵 买入', -1: '🔴 卖出', 0: '⚪ 持有'})
            })
            
            signal_details_df = signal_details_df.sort_index(ascending=False)
            
            def highlight_signals(s):
                if s['交易信号'] == '🔵 买入':
                    return ['background-color: rgba(0, 255, 0, 0.15)'] * len(s)
                elif s['交易信号'] == '🔴 卖出':
                    return ['background-color: rgba(255, 0, 0, 0.15)'] * len(s)
                else:
                    return [''] * len(s)
            
            st.dataframe(
                signal_details_df.style.apply(highlight_signals, axis=1),
                use_container_width=True,
                height=400
            )
            
            st.markdown("---")
            
            st.header("💡 使用说明")
            st.markdown("""
            ### 平台功能
            1. **数据获取**: 支持A股（后缀.SS/.SZ）、美股等全球市场股票数据
            2. **因子计算**: 集成RSI(6/12/24)、MACD(12/26/9)、KDJ(9/3/3)、布林带(20/2)、成交量变异系数等通达信风格因子
            3. **聚合信号**: 多因子信号聚合显示，图标数字表示当日触发的因子数量
            4. **回测分析**: 基于历史数据回测策略表现，计算各项绩效指标
            5. **智能缓存**: 因子计算和回测结果自动缓存，重复参数无需重新计算
            
            ### 操作步骤
            1. 在左侧输入股票代码（如：600519.SS 代表贵州茅台）
            2. 选择分析时间区间
            3. 点击"📥 获取数据"按钮下载股票数据
            4. 调整各因子参数（可选，使用通达信默认值即可）
            5. 设置买卖信号阈值（需要多少个因子同时发出信号）
            6. 点击"🚀 分析/回测"按钮查看结果
            
            ### 信号说明
            - 🟢 **绿色▲数字**: 买入信号，数字表示触发的因子数量
            - 🔴 **红色▼数字**: 卖出信号，数字表示触发的因子数量
            - 数字越大表示信号强度越高，可靠性越强
            
            ### 性能优化
            - 已启用智能缓存，相同参数无需重复计算
            - 建议关闭"自动更新参数变化"，调整好参数后手动点击"分析/回测"
            - 数据获取后可多次调整参数快速回测
            
            ### 注意事项
            - 本平台仅供学习研究使用，不构成投资建议
            - 历史回测不代表未来收益，投资有风险，入市需谨慎
            - 建议结合基本面分析和市场环境综合判断
            """)


if __name__ == "__main__":
    main()
