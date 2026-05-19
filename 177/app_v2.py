import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import talib
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import hashlib
from scipy import stats

st.set_page_config(
    page_title="股票量价因子分析平台 Pro",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #1e2130; padding: 10px; border-radius: 5px; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; border-radius: 4px 4px 0 0; padding: 10px; }
    .stTabs [aria-selected="true"] { background-color: rgba(78, 205, 196, 0.2); }
    div[data-testid="stExpander"] { border-color: #333; }
</style>
""", unsafe_allow_html=True)

DEFAULT_TICKERS = ["600519.SS", "000858.SZ", "000001.SS", "601318.SS", "000333.SZ"]
TICKER_EXAMPLES = {
    "贵州茅台": "600519.SS",
    "五粮液": "000858.SZ",
    "平安银行": "000001.SS",
    "中国平安": "601318.SS",
    "美的集团": "000333.SZ",
    "苹果": "AAPL",
    "微软": "MSFT",
    "腾讯": "0700.HK"
}


def params_hash(params):
    return hashlib.md5(str(sorted(params.items())).encode()).hexdigest()


@st.cache_data(show_spinner=False, ttl=3600)
def get_single_stock_data(ticker, start_date, end_date):
    try:
        data = yf.download(ticker, start=start_date, end=end_date, progress=False)
        if data.empty:
            return None
        data.columns = ['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']
        return data
    except Exception as e:
        return None


@st.cache_data(show_spinner=False, ttl=3600)
def get_multi_stock_data(tickers, start_date, end_date):
    results = {}
    for ticker in tickers:
        data = get_single_stock_data(ticker, start_date, end_date)
        if data is not None:
            results[ticker] = data
    return results


def calculate_factors_single(data, params):
    df = data.copy()
    
    df['RSI'] = talib.RSI(df['Close'], timeperiod=params['rsi_period'])
    df['RSI2'] = talib.RSI(df['Close'], timeperiod=params['rsi_period2'])
    df['RSI3'] = talib.RSI(df['Close'], timeperiod=params['rsi_period3'])
    
    df['MACD'], df['MACD_Signal'], df['MACD_Hist'] = talib.MACD(
        df['Close'],
        fastperiod=params['macd_fast'],
        slowperiod=params['macd_slow'],
        signalperiod=params['macd_signal']
    )
    
    low_min = df['Low'].rolling(window=params['kdj_n']).min()
    high_max = df['High'].rolling(window=params['kdj_n']).max()
    rsv = (df['Close'] - low_min) / (high_max - low_min) * 100
    rsv = rsv.fillna(50)
    df['K'] = rsv.ewm(alpha=1/params['kdj_m1'], adjust=False).mean()
    df['D'] = df['K'].ewm(alpha=1/params['kdj_m2'], adjust=False).mean()
    df['J'] = 3 * df['K'] - 2 * df['D']
    
    df['BB_Upper'], df['BB_Middle'], df['BB_Lower'] = talib.BBANDS(
        df['Close'], timeperiod=params['bb_period'],
        nbdevup=params['bb_std'], nbdevdn=params['bb_std'], matype=0
    )
    df['BB_Position'] = (df['Close'] - df['BB_Lower']) / (df['BB_Upper'] - df['BB_Lower'])
    
    df['Volume_MA'] = df['Volume'].rolling(window=params['volume_ma_period']).mean()
    df['Volume_Ratio'] = df['Volume'] / df['Volume_MA']
    
    df['Returns'] = df['Close'].pct_change()
    df['Returns_1d'] = df['Returns'].shift(-1)
    df['Returns_5d'] = df['Close'].pct_change(5).shift(-5)
    df['Returns_10d'] = df['Close'].pct_change(10).shift(-10)
    
    df['MOM'] = talib.MOM(df['Close'], timeperiod=10)
    df['ATR'] = talib.ATR(df['High'], df['Low'], df['Close'], timeperiod=14)
    
    return df


def calculate_factors_multi(stock_data, params):
    results = {}
    for ticker, data in stock_data.items():
        results[ticker] = calculate_factors_single(data, params)
    return results


def calculate_ic_analysis(all_factors, factor_names, forward_returns=['Returns_1d', 'Returns_5d', 'Returns_10d']):
    ic_results = []
    
    for ticker, df in all_factors.items():
        for factor in factor_names:
            for ret_col in forward_returns:
                valid_data = df[[factor, ret_col]].dropna()
                if len(valid_data) > 30:
                    ic, p_value = stats.spearmanr(valid_data[factor], valid_data[ret_col])
                    ic_results.append({
                        'Ticker': ticker,
                        'Factor': factor,
                        'Forward_Return': ret_col,
                        'IC': ic,
                        'IC_Abs': abs(ic),
                        'P_Value': p_value,
                        'Samples': len(valid_data)
                    })
    
    ic_df = pd.DataFrame(ic_results)
    
    factor_ic_summary = ic_df.groupby(['Factor', 'Forward_Return']).agg({
        'IC': ['mean', 'std', 'min', 'max'],
        'IC_Abs': ['mean', 'std'],
        'P_Value': 'mean',
        'Samples': 'sum'
    }).reset_index()
    factor_ic_summary.columns = ['_'.join(col).strip() if col[1] else col[0] for col in factor_ic_summary.columns.values]
    
    return ic_df, factor_ic_summary


def calculate_quantile_returns(all_factors, factor_name, n_quantiles=5, forward_return='Returns_5d'):
    all_data = []
    
    for ticker, df in all_factors.items():
        valid_data = df[[factor_name, forward_return]].dropna().copy()
        valid_data['Ticker'] = ticker
        all_data.append(valid_data)
    
    if not all_data:
        return None
    
    combined = pd.concat(all_data, axis=0)
    combined['Quantile'] = pd.qcut(combined[factor_name], q=n_quantiles, labels=False, duplicates='drop')
    
    quantile_stats = combined.groupby('Quantile').agg({
        forward_return: ['mean', 'std', 'count', 'min', 'max']
    }).reset_index()
    quantile_stats.columns = ['Quantile', 'Mean_Return', 'Std', 'Count', 'Min', 'Max']
    quantile_stats['Annualized_Return'] = quantile_stats['Mean_Return'] * 252 / 5
    quantile_stats['Sharpe'] = quantile_stats['Mean_Return'] / quantile_stats['Std'] * np.sqrt(252 / 5) if quantile_stats['Std'].min() > 0 else 0
    
    return combined, quantile_stats


def run_factor_strategy(df, factor_name, direction='long_high', holding_period=5, initial_capital=100000, n_quantiles=5):
    df = df.copy()
    df = df.dropna(subset=[factor_name, 'Returns'])
    
    df['Quantile'] = pd.qcut(df[factor_name], q=n_quantiles, labels=False, duplicates='drop')
    
    df['Signal'] = 0
    if direction == 'long_high':
        df.loc[df['Quantile'] == n_quantiles - 1, 'Signal'] = 1
    elif direction == 'long_low':
        df.loc[df['Quantile'] == 0, 'Signal'] = 1
    elif direction == 'long_short':
        df.loc[df['Quantile'] == n_quantiles - 1, 'Signal'] = 1
        df.loc[df['Quantile'] == 0, 'Signal'] = -1
    
    df['Position'] = 0
    df['Holdings'] = 0.0
    df['Cash'] = float(initial_capital)
    df['Total'] = float(initial_capital)
    
    position = 0
    cash = float(initial_capital)
    holdings = 0.0
    hold_counter = 0
    
    trades = []
    entry_date = None
    entry_price = 0
    
    for i in range(len(df)):
        signal = df['Signal'].iloc[i]
        current_price = df['Close'].iloc[i]
        
        if position == 0 and signal != 0:
            shares = int(cash / current_price / 100) * 100 * signal
            if abs(shares) > 0:
                holdings = shares
                cash -= shares * current_price
                position = 1 if shares > 0 else -1
                hold_counter = holding_period
                entry_date = df.index[i]
                entry_price = current_price
        
        elif position != 0:
            hold_counter -= 1
            if hold_counter <= 0 or (signal == -position):
                cash += holdings * current_price
                exit_price = current_price
                exit_date = df.index[i]
                pnl = (exit_price - entry_price) * position * abs(holdings)
                return_pct = (exit_price / entry_price - 1) * position * 100
                
                trades.append({
                    'Entry_Date': entry_date,
                    'Exit_Date': exit_date,
                    'Entry_Price': entry_price,
                    'Exit_Price': exit_price,
                    'Side': 'Long' if position > 0 else 'Short',
                    'Shares': abs(holdings),
                    'PnL': pnl,
                    'Return_%': return_pct,
                    'Holding_Days': holding_period
                })
                
                holdings = 0.0
                position = 0
                cash = float(initial_capital) if cash < 0 else cash
        
        df.loc[df.index[i], 'Position'] = position
        df.loc[df.index[i], 'Holdings'] = holdings
        df.loc[df.index[i], 'Cash'] = cash
        df.loc[df.index[i], 'Total'] = cash + holdings * current_price
    
    if position != 0:
        cash += holdings * df['Close'].iloc[-1]
        df.loc[df.index[-1], 'Total'] = cash
        if trades:
            trades[-1]['Exit_Date'] = df.index[-1]
            trades[-1]['Exit_Price'] = df['Close'].iloc[-1]
    
    df['Returns'] = df['Total'].pct_change()
    df['Cumulative_Returns'] = (1 + df['Returns']).cumprod()
    
    trades_df = pd.DataFrame(trades) if trades else pd.DataFrame()
    
    return df, trades_df


def calculate_backtest_metrics(df, initial_capital=100000):
    if len(df) < 2:
        return {}
    
    total_return = (df['Total'].iloc[-1] - initial_capital) / initial_capital
    trading_days = len(df)
    annual_return = (1 + total_return) ** (252 / trading_days) - 1 if trading_days > 0 else 0
    
    daily_returns = df['Returns'].dropna()
    if len(daily_returns) > 0:
        sharpe_ratio = np.sqrt(252) * daily_returns.mean() / daily_returns.std() if daily_returns.std() != 0 else 0
        max_drawdown = (df['Total'] / df['Total'].cummax() - 1).min()
        volatility = daily_returns.std() * np.sqrt(252)
    else:
        sharpe_ratio = 0
        max_drawdown = 0
        volatility = 0
    
    return {
        'Total Return': f"{total_return*100:.2f}%",
        'Annual Return': f"{annual_return*100:.2f}%",
        'Sharpe Ratio': f"{sharpe_ratio:.2f}",
        'Max Drawdown': f"{max_drawdown*100:.2f}%",
        'Volatility': f"{volatility*100:.2f}%"
    }


def plot_ic_heatmap(ic_df, title="因子IC值热力图"):
    pivot = ic_df.pivot_table(values='IC', index='Factor', columns='Forward_Return', aggfunc='mean')
    
    fig = go.Figure(data=go.Heatmap(
        z=pivot.values,
        x=pivot.columns,
        y=pivot.index,
        text=pivot.values.round(4),
        texttemplate='%{text:.4f}',
        textfont={"size": 12},
        colorscale='RdYlGn',
        zmid=0,
        colorbar=dict(title='IC值')
    ))
    
    fig.update_layout(
        title=title,
        height=400,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white')
    )
    
    return fig


def plot_quantile_bars(quantile_stats, title="分位数收益率"):
    fig = go.Figure()
    
    colors = ['#ff6b6b' if r < 0 else '#4ecdc4' for r in quantile_stats['Mean_Return']]
    
    fig.add_trace(go.Bar(
        x=[f'Q{int(q)+1}' for q in quantile_stats['Quantile']],
        y=quantile_stats['Mean_Return'] * 100,
        marker_color=colors,
        text=quantile_stats['Mean_Return'].apply(lambda x: f'{x*100:.2f}%'),
        textposition='auto',
        name='平均收益率'
    ))
    
    fig.update_layout(
        title=title,
        xaxis_title='分位数 (Q1最低, Q5最高)',
        yaxis_title='平均收益率 (%)',
        height=400,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white')
    )
    
    return fig


def plot_multistock_returns(backtest_results, initial_capital=100000):
    fig = go.Figure()
    
    colors = ['#4ecdc4', '#ff6b6b', '#45b7d1', '#f9ca24', '#6c5ce7', '#a29bfe', '#fd79a8', '#00b894']
    
    for i, (ticker, (df, trades_df)) in enumerate(backtest_results.items()):
        color = colors[i % len(colors)]
        fig.add_trace(go.Scatter(
            x=df.index,
            y=df['Total'],
            name=ticker,
            line=dict(color=color, width=2)
        ))
    
    fig.update_layout(
        title='多股票策略净值曲线对比',
        xaxis_title='日期',
        yaxis_title='净值',
        height=500,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white'),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    return fig


def plot_factor_comparison(all_factors, factor_name, title="因子值对比"):
    fig = go.Figure()
    
    colors = ['#4ecdc4', '#ff6b6b', '#45b7d1', '#f9ca24', '#6c5ce7']
    
    for i, (ticker, df) in enumerate(all_factors.items()):
        color = colors[i % len(colors)]
        fig.add_trace(go.Scatter(
            x=df.index,
            y=df[factor_name],
            name=ticker,
            line=dict(color=color, width=1.5)
        ))
    
    fig.update_layout(
        title=title,
        xaxis_title='日期',
        yaxis_title=factor_name,
        height=400,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white')
    )
    
    return fig


def main():
    st.title("📊 股票量价因子分析平台 Pro")
    st.caption("多股票对比 | 因子有效性分析 | 策略回测引擎")
    st.markdown("---")
    
    mode = st.sidebar.radio("工作模式", ["单股票深度分析", "多股票对比", "因子有效性分析", "策略回测"])
    
    with st.sidebar:
        st.header("📊 股票选择")
        
        if mode in ["多股票对比", "因子有效性分析", "策略回测"]:
            st.subheader("多股票选择")
            preset = st.multiselect("快速选择", list(TICKER_EXAMPLES.keys()), default=["贵州茅台", "五粮液"])
            custom_tickers = st.text_area("或输入股票代码（每行一个）", 
                                        value="\n".join([TICKER_EXAMPLES[p] for p in preset]))
            tickers = [t.strip() for t in custom_tickers.split('\n') if t.strip()]
            if st.checkbox("仅使用预设股票", value=True):
                tickers = [TICKER_EXAMPLES[p] for p in preset]
        else:
            ticker = st.text_input("股票代码", value="600519.SS")
            tickers = [ticker]
        
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("开始日期", value=datetime.now() - timedelta(days=365*3))
        with col2:
            end_date = st.date_input("结束日期", value=datetime.now())
        
        st.markdown("---")
        st.header("⚙️ 因子参数 (通达信默认)")
        
        with st.expander("RSI 参数 (6/12/24)", expanded=False):
            rsi_period = st.slider("RSI1", 3, 20, 6, key='rsi1')
            rsi_period2 = st.slider("RSI2", 5, 30, 12, key='rsi2')
            rsi_period3 = st.slider("RSI3", 10, 40, 24, key='rsi3')
            rsi_oversold = st.slider("超卖阈值", 10, 40, 20)
            rsi_overbought = st.slider("超买阈值", 60, 90, 80)
        
        with st.expander("MACD 参数 (12/26/9)", expanded=False):
            macd_fast = st.slider("DIF快周期", 5, 20, 12)
            macd_slow = st.slider("DIF慢周期", 20, 40, 26)
            macd_signal = st.slider("DEA周期", 5, 15, 9)
        
        with st.expander("KDJ 参数 (9/3/3)", expanded=False):
            kdj_n = st.slider("N周期", 5, 20, 9)
            kdj_m1 = st.slider("K平滑", 2, 10, 3)
            kdj_m2 = st.slider("D平滑", 2, 10, 3)
        
        with st.expander("布林带参数 (20/2)", expanded=False):
            bb_period = st.slider("周期", 10, 30, 20)
            bb_std = st.slider("标准差", 1.0, 3.0, 2.0, step=0.1)
        
        volume_ma_period = st.slider("均量线周期", 5, 30, 5)
        volume_threshold = st.slider("量比阈值", 1.0, 3.0, 1.5, step=0.1)
        
        st.markdown("---")
        st.header("🎯 回测设置")
        initial_capital = st.number_input("初始资金", min_value=10000, value=100000, step=10000)
        
        if mode in ["策略回测", "因子有效性分析"]:
            holding_period = st.slider("持仓周期（天）", 1, 20, 5)
            n_quantiles = st.slider("分位数数量", 3, 10, 5)
            direction = st.selectbox("策略方向", ["long_high", "long_low", "long_short"], 
                                   format_func=lambda x: {"long_high": "做多高分位", "long_low": "做多低分位", "long_short": "多空对冲"}[x])
        
        analyze_button = st.button("🚀 开始分析", type="primary", use_container_width=True)
    
    params = {
        'rsi_period': rsi_period, 'rsi_period2': rsi_period2, 'rsi_period3': rsi_period3,
        'rsi_oversold': rsi_oversold, 'rsi_overbought': rsi_overbought,
        'macd_fast': macd_fast, 'macd_slow': macd_slow, 'macd_signal': macd_signal,
        'kdj_n': kdj_n, 'kdj_m1': kdj_m1, 'kdj_m2': kdj_m2,
        'bb_period': bb_period, 'bb_std': bb_std,
        'volume_ma_period': volume_ma_period, 'volume_threshold': volume_threshold
    }
    
    if analyze_button:
        if not tickers:
            st.error("请至少选择一只股票！")
            return
        
        with st.spinner(f'正在获取 {len(tickers)} 只股票数据...'):
            stock_data = get_multi_stock_data(tickers, start_date, end_date)
        
        if not stock_data:
            st.error("未能获取任何股票数据，请检查代码是否正确。")
            return
        
        st.success(f"✅ 成功获取 {len(stock_data)} 只股票数据")
        
        with st.spinner('正在计算因子...'):
            all_factors = calculate_factors_multi(stock_data, params)
        
        st.session_state['stock_data'] = stock_data
        st.session_state['all_factors'] = all_factors
        st.session_state['params'] = params
        st.session_state['tickers'] = list(stock_data.keys())
    
    if 'all_factors' in st.session_state:
        all_factors = st.session_state['all_factors']
        stock_data = st.session_state['stock_data']
        params = st.session_state['params']
        tickers = st.session_state['tickers']
        
        if mode == "单股票深度分析":
            render_single_stock_analysis(all_factors, stock_data, params, tickers)
        
        elif mode == "多股票对比":
            render_multi_stock_comparison(all_factors, tickers, initial_capital)
        
        elif mode == "因子有效性分析":
            render_factor_analysis(all_factors, tickers)
        
        elif mode == "策略回测":
            render_strategy_backtest(all_factors, tickers, initial_capital, holding_period, n_quantiles, direction)


def render_single_stock_analysis(all_factors, stock_data, params, tickers):
    ticker = st.selectbox("选择股票", tickers, index=0)
    df = all_factors[ticker]
    data = stock_data[ticker]
    
    st.header(f"📈 {ticker} 深度分析")
    
    metric_cols = st.columns(4)
    metric_cols[0].metric("当前价格", f"¥{df['Close'].iloc[-1]:.2f}")
    metric_cols[1].metric("累计涨幅", f"{(df['Close'].iloc[-1] / df['Close'].iloc[0] - 1) * 100:.2f}%")
    metric_cols[2].metric("RSI(6)", f"{df['RSI'].iloc[-1]:.1f}")
    metric_cols[3].metric("量比", f"{df['Volume_Ratio'].iloc[-1]:.2f}")
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["价格走势", "RSI", "MACD", "KDJ", "成交量"])
    
    with tab1:
        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
            name='K线', increasing_line_color='#ff6b6b', decreasing_line_color='#4ecdc4'
        ))
        fig.add_trace(go.Scatter(x=df.index, y=df['BB_Upper'], name='上轨',
                                line=dict(color='rgba(255,165,0,0.5)', width=1)))
        fig.add_trace(go.Scatter(x=df.index, y=df['BB_Lower'], name='下轨',
                                line=dict(color='rgba(255,165,0,0.5)', width=1),
                                fill='tonexty', fillcolor='rgba(255,165,0,0.1)'))
        fig.update_layout(title='股价走势与布林带', height=500, xaxis_rangeslider_visible=False,
                         plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='white'))
        st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], name='RSI6', line=dict(color='#9c27b0', width=2)))
        fig.add_trace(go.Scatter(x=df.index, y=df['RSI2'], name='RSI12', line=dict(color='#e91e63', width=1.5, dash='dash')))
        fig.add_trace(go.Scatter(x=df.index, y=df['RSI3'], name='RSI24', line=dict(color='#f44336', width=1.5, dash='dot')))
        fig.add_hline(y=80, line_dash="dash", line_color="red")
        fig.add_hline(y=20, line_dash="dash", line_color="green")
        fig.add_hline(y=50, line_dash="dash", line_color="gray")
        fig.update_layout(title='RSI 指标 (6/12/24)', height=400, yaxis=dict(range=[0, 100]),
                         plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='white'))
        st.plotly_chart(fig, use_container_width=True)
    
    with tab3:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df.index, y=df['MACD'], name='DIF', line=dict(color='#2196f3', width=2)))
        fig.add_trace(go.Scatter(x=df.index, y=df['MACD_Signal'], name='DEA', line=dict(color='#ff9800', width=2)))
        colors = ['#4caf50' if v >= 0 else '#f44336' for v in df['MACD_Hist']]
        fig.add_trace(go.Bar(x=df.index, y=df['MACD_Hist'], name='MACD柱', marker_color=colors, opacity=0.7))
        fig.update_layout(title='MACD 指标', height=400,
                         plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='white'))
        st.plotly_chart(fig, use_container_width=True)
    
    with tab4:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df.index, y=df['K'], name='K', line=dict(color='#2196f3', width=2)))
        fig.add_trace(go.Scatter(x=df.index, y=df['D'], name='D', line=dict(color='#ff9800', width=2)))
        fig.add_trace(go.Scatter(x=df.index, y=df['J'], name='J', line=dict(color='#9c27b0', width=2)))
        fig.add_hline(y=80, line_dash="dash", line_color="red")
        fig.add_hline(y=20, line_dash="dash", line_color="green")
        fig.update_layout(title='KDJ 指标', height=400, yaxis=dict(range=[-10, 110]),
                         plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='white'))
        st.plotly_chart(fig, use_container_width=True)
    
    with tab5:
        fig = go.Figure()
        colors = ['#ff6b6b' if df['Close'].iloc[i] < df['Open'].iloc[i] else '#4ecdc4' for i in range(len(df))]
        fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name='成交量', marker_color=colors, opacity=0.7))
        fig.add_trace(go.Scatter(x=df.index, y=df['Volume_MA'], name='均量线', line=dict(color='#ff9800', width=2)))
        fig.update_layout(title='成交量', height=400,
                         plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='white'))
        st.plotly_chart(fig, use_container_width=True)
    
    st.header("📋 因子数据表")
    st.dataframe(df[['Close', 'RSI', 'MACD', 'K', 'D', 'J', 'BB_Position', 'Volume_Ratio', 'Returns_1d', 'Returns_5d']].tail(50),
                use_container_width=True, height=300)


def render_multi_stock_comparison(all_factors, tickers, initial_capital):
    st.header("📊 多股票对比分析")
    
    factor_options = ['RSI', 'RSI2', 'RSI3', 'MACD', 'MACD_Signal', 'K', 'D', 'J', 
                     'BB_Position', 'Volume_Ratio', 'MOM', 'ATR']
    selected_factor = st.selectbox("选择对比因子", factor_options, index=0)
    
    col1, col2 = st.columns([3, 1])
    with col1:
        fig = plot_factor_comparison(all_factors, selected_factor, f"多股票 {selected_factor} 对比")
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("最新因子值")
        latest_values = []
        for ticker in tickers:
            df = all_factors[ticker]
            latest_values.append({
                '股票': ticker,
                selected_factor: df[selected_factor].iloc[-1],
                '价格': df['Close'].iloc[-1]
            })
        lv_df = pd.DataFrame(latest_values).sort_values(selected_factor, ascending=False)
        st.dataframe(lv_df.style.background_gradient(cmap='RdYlGn', subset=[selected_factor]),
                    use_container_width=True, height=400)
    
    st.header("📈 累计收益率对比")
    fig = go.Figure()
    colors = ['#4ecdc4', '#ff6b6b', '#45b7d1', '#f9ca24', '#6c5ce7']
    for i, ticker in enumerate(tickers):
        df = all_factors[ticker]
        fig.add_trace(go.Scatter(
            x=df.index,
            y=(df['Close'] / df['Close'].iloc[0] - 1) * 100,
            name=ticker,
            line=dict(color=colors[i % len(colors)], width=2)
        ))
    fig.update_layout(title='累计收益率对比 (%)', yaxis_title='累计收益率 (%)',
                     height=450, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='white'))
    st.plotly_chart(fig, use_container_width=True)
    
    st.header("📋 股票指标汇总")
    summary = []
    for ticker in tickers:
        df = all_factors[ticker]
        total_return = (df['Close'].iloc[-1] / df['Close'].iloc[0] - 1) * 100
        annual_return = (1 + total_return/100) ** (252/len(df)) - 1
        volatility = df['Returns'].std() * np.sqrt(252) * 100
        max_dd = (df['Close'] / df['Close'].cummax() - 1).min() * 100
        
        summary.append({
            '股票': ticker,
            '最新价': f"¥{df['Close'].iloc[-1]:.2f}",
            '累计收益': f"{total_return:.2f}%",
            '年化收益': f"{annual_return*100:.2f}%",
            '波动率': f"{volatility:.2f}%",
            '最大回撤': f"{max_dd:.2f}%",
            'RSI(6)': f"{df['RSI'].iloc[-1]:.1f}",
            'MACD': f"{df['MACD'].iloc[-1]:.4f}",
            '量比': f"{df['Volume_Ratio'].iloc[-1]:.2f}"
        })
    
    summary_df = pd.DataFrame(summary)
    st.dataframe(summary_df, use_container_width=True, height=300)


def render_factor_analysis(all_factors, tickers):
    st.header("🔬 因子有效性分析")
    
    factor_names = ['RSI', 'RSI2', 'RSI3', 'MACD', 'MACD_Signal', 'K', 'D', 'J', 
                   'BB_Position', 'Volume_Ratio', 'MOM', 'ATR']
    
    with st.spinner('正在计算因子IC值...'):
        ic_df, ic_summary = calculate_ic_analysis(all_factors, factor_names)
    
    col1, col2 = st.columns([3, 2])
    
    with col1:
        st.subheader("因子IC热力图")
        fig = plot_ic_heatmap(ic_df, "各因子IC值（Spearman相关系数）")
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("IC值汇总")
        ic_display = ic_summary.sort_values('IC_Abs_mean', ascending=False).head(10)
        ic_display['Factor'] = ic_display['Factor']
        ic_display = ic_display[['Factor', 'Forward_Return', 'IC_mean', 'IC_Abs_mean', 'P_Value_mean', 'Samples_sum']]
        ic_display.columns = ['因子', '预测周期', '平均IC', '平均|IC|', 'P值', '样本数']
        st.dataframe(ic_display.style.background_gradient(cmap='RdYlGn', subset=['平均IC']),
                    use_container_width=True, height=400)
    
    st.markdown("---")
    st.subheader("分位数收益分析")
    
    col3, col4 = st.columns([1, 3])
    with col3:
        quantile_factor = st.selectbox("选择因子", factor_names, 
                                      index=factor_names.index('RSI') if 'RSI' in factor_names else 0)
        forward_return = st.selectbox("预测周期", ['Returns_1d', 'Returns_5d', 'Returns_10d'], index=1,
                                    format_func=lambda x: {'Returns_1d': '1天', 'Returns_5d': '5天', 'Returns_10d': '10天'}[x])
        n_quantiles = st.slider("分位数数量", 3, 10, 5, key='qa_nq')
    
    with col4:
        with st.spinner('正在计算分位数收益...'):
            combined, quantile_stats = calculate_quantile_returns(all_factors, quantile_factor, n_quantiles, forward_return)
        
        if quantile_stats is not None:
            fig = plot_quantile_bars(quantile_stats, f"{quantile_factor} 因子分位数{forward_return.split('_')[1]}天平均收益率")
            st.plotly_chart(fig, use_container_width=True)
            
            st.subheader("分位数详细统计")
            quantile_stats['Quantile'] = [f'Q{int(q)+1}' for q in quantile_stats['Quantile']]
            quantile_stats_display = quantile_stats[['Quantile', 'Mean_Return', 'Annualized_Return', 'Sharpe', 'Count']].copy()
            quantile_stats_display.columns = ['分位数', '平均收益率', '年化收益', '夏普比率', '样本数']
            quantile_stats_display['平均收益率'] = quantile_stats_display['平均收益率'].apply(lambda x: f"{x*100:.2f}%")
            quantile_stats_display['年化收益'] = quantile_stats_display['年化收益'].apply(lambda x: f"{x*100:.2f}%")
            quantile_stats_display['夏普比率'] = quantile_stats_display['夏普比率'].apply(lambda x: f"{x:.2f}")
            st.dataframe(quantile_stats_display, use_container_width=True)
    
    st.markdown("---")
    st.info("💡 **IC值说明**：IC（Information Coefficient）衡量因子预测未来收益的能力，范围[-1,1]。绝对值越大表示预测能力越强。通常|IC|>0.05且统计显著（P<0.05）的因子被认为是有效的。")


def render_strategy_backtest(all_factors, tickers, initial_capital, holding_period, n_quantiles, direction):
    st.header("💹 策略回测引擎")
    
    factor_names = ['RSI', 'RSI2', 'RSI3', 'MACD', 'K', 'D', 'J', 'BB_Position', 'Volume_Ratio', 'MOM']
    strategy_factor = st.selectbox("选择策略因子", factor_names, index=0)
    
    run_backtest = st.button("▶️ 运行策略回测", type="primary")
    
    if run_backtest:
        backtest_results = {}
        all_trades = []
        all_metrics = []
        
        progress_bar = st.progress(0)
        for i, ticker in enumerate(tickers):
            progress_bar.progress((i + 1) / len(tickers))
            df = all_factors[ticker].copy()
            bt_df, trades_df = run_factor_strategy(
                df, strategy_factor, direction, holding_period, initial_capital, n_quantiles
            )
            backtest_results[ticker] = (bt_df, trades_df)
            
            if not trades_df.empty:
                trades_df['Ticker'] = ticker
                all_trades.append(trades_df)
            
            metrics = calculate_backtest_metrics(bt_df, initial_capital)
            metrics['Ticker'] = ticker
            all_metrics.append(metrics)
        
        progress_bar.empty()
        
        st.session_state['backtest_results'] = backtest_results
        st.session_state['all_trades'] = pd.concat(all_trades) if all_trades else pd.DataFrame()
        st.session_state['all_metrics'] = pd.DataFrame(all_metrics)
        st.session_state['strategy_factor'] = strategy_factor
        st.session_state['holding_period'] = holding_period
        st.session_state['direction'] = direction
    
    if 'backtest_results' in st.session_state:
        backtest_results = st.session_state['backtest_results']
        all_trades = st.session_state['all_trades']
        all_metrics = st.session_state['all_metrics']
        strategy_factor = st.session_state['strategy_factor']
        holding_period = st.session_state['holding_period']
        direction = st.session_state['direction']
        
        st.subheader("策略净值曲线")
        fig = plot_multistock_returns(backtest_results, initial_capital)
        st.plotly_chart(fig, use_container_width=True)
        
        st.subheader("回测绩效汇总")
        metrics_display = all_metrics[['Ticker', 'Total Return', 'Annual Return', 'Sharpe Ratio', 'Max Drawdown', 'Volatility']]
        metrics_display.columns = ['股票', '总收益', '年化收益', '夏普比率', '最大回撤', '波动率']
        st.dataframe(metrics_display, use_container_width=True)
        
        if not all_trades.empty:
            st.subheader("交易记录汇总")
            
            col1, col2, col3, col4 = st.columns(4)
            total_trades = len(all_trades)
            win_trades = len(all_trades[all_trades['PnL'] > 0])
            total_pnl = all_trades['PnL'].sum()
            avg_return = all_trades['Return_%'].mean()
            
            col1.metric("总交易次数", total_trades)
            col2.metric("胜率", f"{win_trades/total_trades*100:.2f}%" if total_trades > 0 else "N/A")
            col3.metric("总盈亏", f"¥{total_pnl:,.2f}")
            col4.metric("平均单笔收益", f"{avg_return:.2f}%")
            
            st.subheader("所有交易记录")
            trades_display = all_trades[['Ticker', 'Entry_Date', 'Exit_Date', 'Side', 'Entry_Price', 'Exit_Price', 'Shares', 'PnL', 'Return_%', 'Holding_Days']].copy()
            trades_display.columns = ['股票', '入场日期', '出场日期', '方向', '入场价', '出场价', '股数', '盈亏', '收益%', '持仓天数']
            trades_display = trades_display.sort_values('Exit_Date', ascending=False)
            
            def highlight_pnl(row):
                color = 'background-color: rgba(0,255,0,0.1)' if row['盈亏'] > 0 else 'background-color: rgba(255,0,0,0.1)' if row['盈亏'] < 0 else ''
                return [color] * len(row)
            
            st.dataframe(
                trades_display.style.apply(highlight_pnl, axis=1),
                use_container_width=True,
                height=400
            )
            
            st.download_button(
                label="📥 下载交易记录 CSV",
                data=trades_display.to_csv(index=False).encode('utf-8-sig'),
                file_name=f"trades_{strategy_factor}_{direction}_{holding_period}d.csv",
                mime='text/csv'
            )
        
        selected_stock = st.selectbox("查看单只股票详细回测", tickers, index=0)
        if selected_stock in backtest_results:
            bt_df, trades_df = backtest_results[selected_stock]
            
            st.subheader(f"{selected_stock} 详细回测")
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=bt_df.index, y=bt_df['Total'], name='策略净值',
                                    line=dict(color='#4ecdc4', width=2)))
            fig.add_trace(go.Scatter(x=bt_df.index, 
                                    y=bt_df['Close'] / bt_df['Close'].iloc[0] * initial_capital,
                                    name='持有收益', line=dict(color='#ff6b6b', width=2, dash='dash')))
            fig.update_layout(title=f'{selected_stock} 策略 vs 持有', height=400,
                             plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='white'))
            st.plotly_chart(fig, use_container_width=True)


if __name__ == "__main__":
    main()
