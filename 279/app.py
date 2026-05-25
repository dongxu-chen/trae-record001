import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.data_processing import DataProcessor
from src.anomaly_detector import AnomalyDetector
from src.multi_asset_analyzer import MultiAssetAnalyzer
from src.anomaly_attribution import AnomalyAttributor, EventDetector
from src.alert_notifier import AlertNotifier

st.set_page_config(
    page_title="金融时序数据异常检测平台",
    page_icon="📊",
    layout="wide"
)

st.title("📊 金融时序数据异常检测平台")
st.markdown("基于自编码器 + Prophet 的异常检测系统，支持多资产联动分析、异常归因、预警推送")

if 'detector' not in st.session_state:
    st.session_state.detector = None
if 'data' not in st.session_state:
    st.session_state.data = None
if 'result_df' not in st.session_state:
    st.session_state.result_df = None
if 'anomaly_intervals' not in st.session_state:
    st.session_state.anomaly_intervals = []
if 'user_feedback' not in st.session_state:
    st.session_state.user_feedback = []
if 'multi_asset_data' not in st.session_state:
    st.session_state.multi_asset_data = {}
if 'multi_asset_results' not in st.session_state:
    st.session_state.multi_asset_results = {}
if 'multi_asset_analyzer' not in st.session_state:
    st.session_state.multi_asset_analyzer = MultiAssetAnalyzer()
if 'systemic_events_df' not in st.session_state:
    st.session_state.systemic_events_df = pd.DataFrame()
if 'attributor' not in st.session_state:
    st.session_state.attributor = AnomalyAttributor()
if 'attribution_results' not in st.session_state:
    st.session_state.attribution_results = None
if 'event_detector' not in st.session_state:
    st.session_state.event_detector = EventDetector()
if 'alert_notifier' not in st.session_state:
    st.session_state.alert_notifier = AlertNotifier()

with st.sidebar:
    st.header("📁 数据输入")

    data_source = st.radio(
        "选择数据源",
        ["模拟数据", "CSV上传", "Yahoo Finance"],
        horizontal=True
    )

    if data_source == "模拟数据":
        n_days = st.slider("数据天数", 100, 730, 365)
        inject_anomalies = st.checkbox("注入异常数据", value=True)
        inject_timestamp_gaps = st.checkbox("注入时间戳跳点", value=False)
        n_assets = st.slider("资产数量（多资产分析）", 1, 5, 1)

        if st.button("生成模拟数据"):
            with st.spinner("正在生成模拟数据..."):
                if n_assets == 1:
                    df = DataProcessor.generate_mock_data(
                        n_days=n_days,
                        inject_anomalies=inject_anomalies
                    )
                    if inject_timestamp_gaps:
                        gap_idx = np.random.randint(n_days // 3, 2 * n_days // 3)
                        df = df.drop(df.index[gap_idx:gap_idx + 5]).reset_index(drop=True)
                    st.session_state.data = df
                    st.success(f"已生成 {len(df)} 条模拟数据")
                else:
                    st.session_state.multi_asset_data = {}
                    for i in range(n_assets):
                        df = DataProcessor.generate_mock_data(
                            n_days=n_days,
                            inject_anomalies=inject_anomalies
                        )
                        if i == 0 and inject_timestamp_gaps:
                            gap_idx = np.random.randint(n_days // 3, 2 * n_days // 3)
                            df = df.drop(df.index[gap_idx:gap_idx + 5]).reset_index(drop=True)
                        st.session_state.multi_asset_data[f'资产_{i+1}'] = df
                    st.success(f"已生成 {n_assets} 个资产的模拟数据")

    elif data_source == "CSV上传":
        uploaded_file = st.file_uploader("上传CSV文件", type=["csv"])
        asset_name = st.text_input("资产名称", "资产1")
        if uploaded_file is not None:
            date_col = st.text_input("日期列名", "date")
            value_col = st.text_input("数值列名", "value")
            if st.button("加载CSV数据"):
                try:
                    df = DataProcessor.load_from_csv(
                        uploaded_file,
                        date_col=date_col,
                        value_col=value_col
                    )
                    if asset_name:
                        st.session_state.multi_asset_data[asset_name] = df
                    else:
                        st.session_state.data = df
                    st.success(f"已加载 {len(df)} 条数据")
                except Exception as e:
                    st.error(f"加载失败: {e}")

    elif data_source == "Yahoo Finance":
        tickers = st.text_input("股票代码（多个用逗号分隔）", "AAPL,MSFT,GOOGL")
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("开始日期", datetime.now() - timedelta(days=365))
        with col2:
            end_date = st.date_input("结束日期", datetime.now())
        if st.button("下载数据"):
            ticker_list = [t.strip() for t in tickers.split(',')]
            for ticker in ticker_list:
                try:
                    df = DataProcessor.load_from_yfinance(
                        ticker,
                        start_date.strftime("%Y-%m-%d"),
                        end_date.strftime("%Y-%m-%d")
                    )
                    st.session_state.multi_asset_data[ticker] = df
                    st.success(f"已下载 {ticker}: {len(df)} 条数据")
                except Exception as e:
                    st.error(f"{ticker} 下载失败: {e}")

    if st.session_state.multi_asset_data:
        st.markdown("---")
        st.markdown("#### 📦 已加载资产")
        for name, df in st.session_state.multi_asset_data.items():
            st.markdown(f"- **{name}**: {len(df)} 条数据")

    st.markdown("---")
    st.header("⚙️ 模型参数")

    seq_length = st.slider("序列长度", 7, 60, 30)
    hidden_dims = st.selectbox("隐藏层维度", ["[64, 32]", "[128, 64]", "[32, 16]"])
    epochs = st.slider("训练轮数", 10, 200, 100)
    base_percentile = st.slider("基础阈值百分位", 80, 99, 95)

    st.markdown("#### 🎯 动态阈值配置")
    use_dynamic_threshold = st.checkbox("启用动态阈值", value=True)
    if use_dynamic_threshold:
        threshold_window = st.slider("阈值窗口大小", 7, 60, 30)
        volatility_scale = st.slider("波动率影响系数", 0.5, 3.0, 1.5, 0.1)

    st.markdown("#### 🔗 多资产联动分析")
    co_anomaly_window = st.slider("协同异常窗口", 1, 7, 3)
    min_assets_systemic = st.slider("最小资产数（系统性风险）", 2, 5, 2)

    st.markdown("#### ⏰ 时间序列检查")
    expected_freq = st.selectbox("预期数据频率", ["D", "H", "W", "M"],
                                 format_func=lambda x: {"D": "日频", "H": "小时", "W": "周", "M": "月"}[x])

    if len(st.session_state.multi_asset_data) > 0:
        if st.button("🚀 批量训练并检测异常", type="primary"):
            with st.spinner("正在训练多资产模型..."):
                st.session_state.multi_asset_results = {}
                st.session_state.multi_asset_analyzer = MultiAssetAnalyzer(
                    co_anomaly_window=co_anomaly_window,
                    min_assets_for_systemic=min_assets_systemic
                )

                for asset_name, df in st.session_state.multi_asset_data.items():
                    detector = AnomalyDetector(
                        seq_length=seq_length,
                        hidden_dims=eval(hidden_dims),
                        use_dynamic_threshold=use_dynamic_threshold,
                        threshold_window=threshold_window if use_dynamic_threshold else 30,
                        base_percentile=base_percentile,
                        volatility_scale=volatility_scale if use_dynamic_threshold else 1.0
                    )
                    detector.fit(df, epochs=epochs, verbose=False)
                    result_df = detector.detect_anomalies(df, expected_freq=expected_freq)

                    st.session_state.multi_asset_results[asset_name] = {
                        'detector': detector,
                        'result_df': result_df
                    }
                    st.session_state.multi_asset_analyzer.add_asset_result(asset_name, result_df)

                _, systemic_events_df = st.session_state.multi_asset_analyzer.detect_co_anomalies()
                st.session_state.systemic_events_df = systemic_events_df

                st.session_state.detector = list(st.session_state.multi_asset_results.values())[0]['detector']
                first_asset = list(st.session_state.multi_asset_data.keys())[0]
                st.session_state.result_df = st.session_state.multi_asset_results[first_asset]['result_df']
                st.session_state.data = st.session_state.multi_asset_data[first_asset]

                st.success(f"已完成 {len(st.session_state.multi_asset_results)} 个资产的异常检测！")
    elif st.session_state.data is not None:
        if st.button("🚀 训练模型并检测异常", type="primary"):
            with st.spinner("正在训练模型..."):
                detector = AnomalyDetector(
                    seq_length=seq_length,
                    hidden_dims=eval(hidden_dims),
                    use_dynamic_threshold=use_dynamic_threshold,
                    threshold_window=threshold_window if use_dynamic_threshold else 30,
                    base_percentile=base_percentile,
                    volatility_scale=volatility_scale if use_dynamic_threshold else 1.0
                )
                losses = detector.fit(
                    st.session_state.data,
                    epochs=epochs,
                    verbose=False
                )

                st.session_state.detector = detector

                result_df = detector.detect_anomalies(st.session_state.data, expected_freq=expected_freq)
                st.session_state.result_df = result_df

                intervals = detector.get_anomaly_intervals(st.session_state.data)
                st.session_state.anomaly_intervals = intervals

                st.success("模型训练完成！")

    st.markdown("---")
    st.header("💡 人工反馈与增量训练")
    if st.session_state.result_df is not None:
        feedback_dates = st.multiselect(
            "选择误报/漏报日期",
            options=st.session_state.result_df['ds'].dt.strftime('%Y-%m-%d').tolist()
        )
        feedback_type = st.radio("反馈类型", ["是异常（漏报）", "不是异常（误报）"])
        feedback_confidence = st.slider("反馈置信度", 0.5, 2.0, 1.0, 0.1)

        if st.button("提交反馈"):
            for date_str in feedback_dates:
                date = pd.to_datetime(date_str)
                is_anomaly = (feedback_type == "是异常（漏报）")
                st.session_state.user_feedback.append({
                    'date': date,
                    'is_anomaly': is_anomaly,
                    'confidence': feedback_confidence
                })
                if st.session_state.detector:
                    st.session_state.detector.add_user_feedback(date, is_anomaly, feedback_confidence)
            st.success(f"已提交 {len(feedback_dates)} 条反馈")

        if len(st.session_state.user_feedback) > 0:
            st.markdown(f"**已收集反馈: {len(st.session_state.user_feedback)} 条**")
            incremental_epochs = st.slider("增量训练轮数", 10, 100, 30)
            feedback_weight = st.slider("反馈样本权重", 1.0, 5.0, 2.0, 0.5)

            if st.button("🔄 基于反馈增量训练", type="secondary"):
                with st.spinner("正在增量训练..."):
                    new_losses = st.session_state.detector.retrain_with_feedback(
                        st.session_state.data,
                        epochs=incremental_epochs,
                        feedback_weight=feedback_weight
                    )
                    result_df = st.session_state.detector.detect_anomalies(
                        st.session_state.data, expected_freq=expected_freq
                    )
                    st.session_state.result_df = result_df
                    st.session_state.anomaly_intervals = st.session_state.detector.get_anomaly_intervals(
                        st.session_state.data
                    )
                    st.success("增量训练完成！模型已更新")

    st.markdown("---")
    st.header("🔔 预警推送配置")
    wecom_webhook = st.text_input("企业微信Webhook", type="password")
    dingtalk_webhook = st.text_input("钉钉Webhook", type="password")

    if wecom_webhook:
        st.session_state.alert_notifier.set_wecom_webhook(wecom_webhook)
    if dingtalk_webhook:
        st.session_state.alert_notifier.set_dingtalk_webhook(dingtalk_webhook)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("测试企业微信"):
            success, msg = st.session_state.alert_notifier.test_webhook('wecom')
            if success:
                st.success("企业微信测试成功！")
            else:
                st.error(f"测试失败: {msg}")
    with col2:
        if st.button("测试钉钉"):
            success, msg = st.session_state.alert_notifier.test_webhook('dingtalk')
            if success:
                st.success("钉钉测试成功！")
            else:
                st.error(f"测试失败: {msg}")

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "📈 数据概览", "🔍 异常检测结果", "🔗 多资产联动", "📊 异常归因",
    "📋 异常列表", "🔔 预警推送", "🤖 模型状态"
])

with tab1:
    if len(st.session_state.multi_asset_data) > 0:
        st.subheader("多资产数据概览")

        selected_asset = st.selectbox(
            "选择查看资产",
            options=list(st.session_state.multi_asset_data.keys())
        )

        if selected_asset:
            df = st.session_state.multi_asset_data[selected_asset]

            gap_info = []
            if selected_asset in st.session_state.multi_asset_results:
                detector = st.session_state.multi_asset_results[selected_asset]['detector']
                gap_info = detector.check_timestamp_continuity(df, expected_freq=expected_freq)

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df['ds'],
                y=df['y'],
                mode='lines+markers',
                name=f'{selected_asset} 价格',
                line=dict(color='#1f77b4'),
                marker=dict(size=4)
            ))

            if gap_info:
                for gap in gap_info:
                    fig.add_vrect(
                        x0=gap['gap_start'],
                        x1=gap['gap_end'],
                        fillcolor='rgba(255, 0, 0, 0.1)',
                        opacity=0.5,
                        layer="below",
                        line_width=1,
                        line_color='red',
                        annotation_text=f"跳点: {gap['gap_days']:.1f}天"
                    )

            fig.update_layout(
                title=f"{selected_asset} - 时序数据图",
                xaxis_title="日期",
                yaxis_title="价格/净值",
                hovermode='x unified',
                height=500
            )
            st.plotly_chart(fig, use_container_width=True)

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("数据点数量", len(df))
            with col2:
                st.metric("时间范围", f"{df['ds'].min().strftime('%Y-%m-%d')} ~ {df['ds'].max().strftime('%Y-%m-%d')}")
            with col3:
                st.metric("均值", f"{df['y'].mean():.2f}")
            with col4:
                st.metric("时间戳跳点", f"{len(gap_info)} 处")

            if gap_info:
                st.warning(f"⚠️ 检测到 {len(gap_info)} 处时间戳不连续")
                gap_df = pd.DataFrame(gap_info)
                gap_df['gap_start'] = pd.to_datetime(gap_df['gap_start']).dt.strftime('%Y-%m-%d')
                gap_df['gap_end'] = pd.to_datetime(gap_df['gap_end']).dt.strftime('%Y-%m-%d')
                gap_df['gap_duration'] = gap_df['gap_duration'].astype(str)
                st.dataframe(gap_df[['gap_start', 'gap_end', 'gap_days']], use_container_width=True)

    elif st.session_state.data is not None:
        st.subheader("原始数据")

        gap_info = []
        if st.session_state.detector:
            gap_info = st.session_state.detector.check_timestamp_continuity(
                st.session_state.data, expected_freq=expected_freq
            )

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=st.session_state.data['ds'],
            y=st.session_state.data['y'],
            mode='lines+markers',
            name='价格/净值',
            line=dict(color='#1f77b4'),
            marker=dict(size=4)
        ))

        if gap_info:
            for gap in gap_info:
                fig.add_vrect(
                    x0=gap['gap_start'],
                    x1=gap['gap_end'],
                    fillcolor='rgba(255, 0, 0, 0.1)',
                    opacity=0.5,
                    layer="below",
                    line_width=1,
                    line_color='red',
                    annotation_text=f"跳点: {gap['gap_days']:.1f}天"
                )

        fig.update_layout(
            title="时序数据图",
            xaxis_title="日期",
            yaxis_title="价格/净值",
            hovermode='x unified',
            height=500
        )
        st.plotly_chart(fig, use_container_width=True)

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("数据点数量", len(st.session_state.data))
        with col2:
            st.metric("时间范围", f"{st.session_state.data['ds'].min().strftime('%Y-%m-%d')} ~ {st.session_state.data['ds'].max().strftime('%Y-%m-%d')}")
        with col3:
            st.metric("均值", f"{st.session_state.data['y'].mean():.2f}")
        with col4:
            st.metric("时间戳跳点", f"{len(gap_info)} 处")

        if gap_info:
            st.warning(f"⚠️ 检测到 {len(gap_info)} 处时间戳不连续")
            gap_df = pd.DataFrame(gap_info)
            gap_df['gap_start'] = pd.to_datetime(gap_df['gap_start']).dt.strftime('%Y-%m-%d')
            gap_df['gap_end'] = pd.to_datetime(gap_df['gap_end']).dt.strftime('%Y-%m-%d')
            gap_df['gap_duration'] = gap_df['gap_duration'].astype(str)
            st.dataframe(gap_df[['gap_start', 'gap_end', 'gap_days']], use_container_width=True)

        with st.expander("查看原始数据"):
            st.dataframe(st.session_state.data, use_container_width=True)
    else:
        st.info("请在左侧选择数据源并加载数据")

with tab2:
    if len(st.session_state.multi_asset_results) > 0:
        st.subheader("多资产异常检测结果")

        selected_asset = st.selectbox(
            "选择查看资产",
            options=list(st.session_state.multi_asset_results.keys()),
            key="result_asset_select"
        )

        if selected_asset:
            result_df = st.session_state.multi_asset_results[selected_asset]['result_df']

            fig = make_subplots(
                rows=2, cols=1,
                shared_xaxes=True,
                vertical_spacing=0.05,
                subplot_titles=(f"{selected_asset} - 价格走势与异常标注", "异常评分与动态阈值")
            )

            fig.add_trace(go.Scatter(
                x=result_df['ds'],
                y=result_df['y'],
                mode='lines',
                name='价格',
                line=dict(color='#1f77b4')
            ), row=1, col=1)

            anomaly_df = result_df[result_df['is_anomaly']]
            if len(anomaly_df) > 0:
                color_map = {
                    'flash_crash': 'red',
                    'volatility_spike': 'orange',
                    'missing_data': 'purple',
                    'timestamp_gap': 'brown',
                    'anomaly': 'yellow'
                }
                name_map = {
                    'flash_crash': '闪崩',
                    'volatility_spike': '异常波动',
                    'missing_data': '数据缺失',
                    'timestamp_gap': '时间戳跳点',
                    'anomaly': '一般异常'
                }

                for atype in anomaly_df['anomaly_type'].unique():
                    type_df = anomaly_df[anomaly_df['anomaly_type'] == atype]
                    fig.add_trace(go.Scatter(
                        x=type_df['ds'],
                        y=type_df['y'],
                        mode='markers',
                        name=name_map.get(atype, '异常'),
                        marker=dict(
                            color=color_map.get(atype, 'red'),
                            size=10,
                            line=dict(width=2, color='black')
                        )
                    ), row=1, col=1)

            fig.add_trace(go.Scatter(
                x=result_df['ds'],
                y=result_df['anomaly_score'],
                mode='lines',
                name='异常评分',
                line=dict(color='#ff7f0e')
            ), row=2, col=1)

            if use_dynamic_threshold and 'dynamic_threshold' in result_df.columns:
                fig.add_trace(go.Scatter(
                    x=result_df['ds'],
                    y=result_df['dynamic_threshold'],
                    mode='lines',
                    name='动态阈值',
                    line=dict(color='red', dash='dash'),
                    opacity=0.7
                ), row=2, col=1)

            fig.update_layout(
                height=700,
                hovermode='x unified',
                showlegend=True
            )
            st.plotly_chart(fig, use_container_width=True)

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("异常点数量", len(anomaly_df))
            with col2:
                st.metric("闪崩", len(anomaly_df[anomaly_df['anomaly_type'] == 'flash_crash']))
            with col3:
                st.metric("异常波动", len(anomaly_df[anomaly_df['anomaly_type'] == 'volatility_spike']))
            with col4:
                ts_gaps = len(anomaly_df[anomaly_df['anomaly_type'] == 'timestamp_gap'])
                st.metric("时间戳跳点", ts_gaps)

    elif st.session_state.result_df is not None:
        st.subheader("异常检测结果")

        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.05,
            subplot_titles=("价格走势与异常标注", "异常评分与动态阈值")
        )

        fig.add_trace(go.Scatter(
            x=st.session_state.result_df['ds'],
            y=st.session_state.result_df['y'],
            mode='lines',
            name='价格',
            line=dict(color='#1f77b4')
        ), row=1, col=1)

        anomaly_df = st.session_state.result_df[st.session_state.result_df['is_anomaly']]
        if len(anomaly_df) > 0:
            color_map = {
                'flash_crash': 'red',
                'volatility_spike': 'orange',
                'missing_data': 'purple',
                'timestamp_gap': 'brown',
                'anomaly': 'yellow'
            }
            name_map = {
                'flash_crash': '闪崩',
                'volatility_spike': '异常波动',
                'missing_data': '数据缺失',
                'timestamp_gap': '时间戳跳点',
                'anomaly': '一般异常'
            }

            for atype in anomaly_df['anomaly_type'].unique():
                type_df = anomaly_df[anomaly_df['anomaly_type'] == atype]
                fig.add_trace(go.Scatter(
                    x=type_df['ds'],
                    y=type_df['y'],
                    mode='markers',
                    name=name_map.get(atype, '异常'),
                    marker=dict(
                        color=color_map.get(atype, 'red'),
                        size=10,
                        line=dict(width=2, color='black')
                    )
                ), row=1, col=1)

        for interval in st.session_state.anomaly_intervals:
            color_map = {
                'flash_crash': 'rgba(255, 0, 0, 0.2)',
                'volatility_spike': 'rgba(255, 165, 0, 0.2)',
                'missing_data': 'rgba(128, 0, 128, 0.2)',
                'timestamp_gap': 'rgba(139, 69, 19, 0.2)',
                'anomaly': 'rgba(255, 255, 0, 0.2)'
            }
            fig.add_vrect(
                x0=interval['start'],
                x1=interval['end'],
                fillcolor=color_map.get(interval['type'], 'rgba(255, 0, 0, 0.2)'),
                opacity=0.3,
                layer="below",
                line_width=0,
                row=1, col=1
            )

        fig.add_trace(go.Scatter(
            x=st.session_state.result_df['ds'],
            y=st.session_state.result_df['anomaly_score'],
            mode='lines',
            name='异常评分',
            line=dict(color='#ff7f0e')
        ), row=2, col=1)

        if use_dynamic_threshold and 'dynamic_threshold' in st.session_state.result_df.columns:
            fig.add_trace(go.Scatter(
                x=st.session_state.result_df['ds'],
                y=st.session_state.result_df['dynamic_threshold'],
                mode='lines',
                name='动态阈值',
                line=dict(color='red', dash='dash'),
                opacity=0.7
            ), row=2, col=1)
        else:
            fig.add_hline(
                y=st.session_state.detector.threshold,
                line_dash="dash",
                line_color="red",
                annotation_text="阈值",
                row=2, col=1
            )

        fig.update_layout(
            height=700,
            hovermode='x unified',
            showlegend=True
        )
        st.plotly_chart(fig, use_container_width=True)

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("异常点数量", len(anomaly_df))
        with col2:
            st.metric("异常区间数量", len(st.session_state.anomaly_intervals))
        with col3:
            if use_dynamic_threshold:
                st.metric("动态阈值范围",
                         f"{st.session_state.result_df['dynamic_threshold'].min():.2f} ~ {st.session_state.result_df['dynamic_threshold'].max():.2f}")
            else:
                st.metric("固定阈值", f"{st.session_state.detector.threshold:.4f}")
        with col4:
            ts_gaps = len(anomaly_df[anomaly_df['anomaly_type'] == 'timestamp_gap']) if 'timestamp_gap' in anomaly_df['anomaly_type'].values else 0
            st.metric("时间戳跳点异常", ts_gaps)
    else:
        st.info("请先训练模型并检测异常")

with tab3:
    st.subheader("🔗 多资产联动分析")

    if len(st.session_state.multi_asset_results) >= 2:
        summary = st.session_state.multi_asset_analyzer.get_summary()

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("监控资产数", summary['total_assets'])
        with col2:
            total_anomalies = sum(v['total'] for v in summary['total_anomalies_per_asset'].values())
            st.metric("总异常点", total_anomalies)
        with col3:
            st.metric("系统性风险事件", len(st.session_state.systemic_events_df))

        st.markdown("#### 🚨 系统性风险事件")
        if not st.session_state.systemic_events_df.empty:
            display_df = st.session_state.systemic_events_df.copy()
            display_df['event_date'] = pd.to_datetime(display_df['event_date']).dt.strftime('%Y-%m-%d')
            display_df['window_start'] = pd.to_datetime(display_df['window_start']).dt.strftime('%Y-%m-%d')
            display_df['window_end'] = pd.to_datetime(display_df['window_end']).dt.strftime('%Y-%m-%d')
            display_df['asset_names'] = display_df['asset_names'].apply(lambda x: ', '.join(x))
            display_df['anomaly_types'] = display_df['anomaly_types'].apply(lambda x: ', '.join(x))

            severity_map = {'high': '🔴 高', 'medium': '🟠 中', 'low': '🟢 低'}
            display_df['severity'] = display_df['severity'].map(severity_map)

            display_df.columns = [
                '事件日期', '窗口开始', '窗口结束', '涉及资产数', '涉及资产名称',
                '异常总数', '平均评分', '最高评分', '风险等级', '异常类型'
            ]
            st.dataframe(display_df, use_container_width=True)

            st.markdown("#### 📊 系统性风险统计")
            risk_summary = st.session_state.multi_asset_analyzer.get_systemic_risk_summary(
                st.session_state.systemic_events_df
            )
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("高风险事件", risk_summary.get('high_risk_events', 0))
            with col2:
                st.metric("中风险事件", risk_summary.get('medium_risk_events', 0))
            with col3:
                st.metric("平均涉及资产", f"{risk_summary.get('avg_assets_per_event', 0):.1f}")

            if 'most_affected_assets' in risk_summary:
                st.markdown("#### 🏆 受影响最多的资产")
                affected_df = pd.DataFrame(
                    list(risk_summary['most_affected_assets'].items()),
                    columns=['资产', '风险事件数']
                )
                st.dataframe(affected_df, use_container_width=True)
        else:
            st.info("未检测到系统性风险事件")

        st.markdown("#### 📈 价格相关性矩阵")
        corr_matrix = st.session_state.multi_asset_analyzer.calculate_correlations()
        if not corr_matrix.empty:
            fig = go.Figure(data=go.Heatmap(
                z=corr_matrix.values,
                x=corr_matrix.columns,
                y=corr_matrix.index,
                colorscale='RdBu',
                zmid=0,
                text=corr_matrix.values.round(2),
                texttemplate='%{text}',
                textfont={"size": 10}
            ))
            fig.update_layout(title="资产价格相关性", height=500)
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("#### 🎯 异常相关性矩阵")
        anomaly_corr = st.session_state.multi_asset_analyzer.calculate_anomaly_correlation()
        if not anomaly_corr.empty:
            fig = go.Figure(data=go.Heatmap(
                z=anomaly_corr.values,
                x=anomaly_corr.columns,
                y=anomaly_corr.index,
                colorscale='RdBu',
                zmid=0,
                text=anomaly_corr.values.round(2),
                texttemplate='%{text}',
                textfont={"size": 10}
            ))
            fig.update_layout(title="异常事件相关性", height=500)
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("请加载至少2个资产的数据进行联动分析")

with tab4:
    st.subheader("📊 异常归因分析")

    if st.session_state.result_df is not None:
        prophet_features = None
        if st.session_state.detector and st.session_state.detector.prophet_extractor.forecast is not None:
            prophet_features = st.session_state.detector.prophet_extractor.extract_features(
                st.session_state.result_df
            )

        attribution_results = st.session_state.attributor.batch_analyze(
            st.session_state.result_df, prophet_features
        )
        st.session_state.attribution_results = attribution_results

        if not attribution_results.empty:
            st.markdown("#### 异常归因概览")

            factor_names_cn = {
                'price_volatility': '价格波动率异常',
                'trend_deviation': '趋势偏离',
                'volume_spike': '成交量异常放大',
                'price_jump': '价格跳变',
                'prophet_residual': '模型预测残差',
                'seasonal_anomaly': '季节性异常'
            }

            dominant_dist = attribution_results['dominant_factor'].value_counts()
            dominant_dist.index = [factor_names_cn.get(x, x) for x in dominant_dist.index]

            col1, col2 = st.columns(2)
            with col1:
                fig_pie = go.Figure(data=[go.Pie(
                    labels=dominant_dist.index,
                    values=dominant_dist.values,
                    hole=.3
                )])
                fig_pie.update_layout(title="主导因子分布")
                st.plotly_chart(fig_pie, use_container_width=True)

            with col2:
                avg_contrib = attribution_results['dominant_contribution'].mean()
                st.metric("平均主导因子贡献度", f"{avg_contrib*100:.1f}%")

                high_score = attribution_results[attribution_results['anomaly_score'] > 2.0]
                st.metric("高评分异常数（>2.0）", len(high_score))

            st.markdown("#### 详细归因列表")
            display_attr = attribution_results.copy()
            display_attr['date'] = pd.to_datetime(display_attr['date']).dt.strftime('%Y-%m-%d')
            display_attr['dominant_factor_cn'] = display_attr['dominant_factor'].map(factor_names_cn)
            display_attr['dominant_contribution_pct'] = (display_attr['dominant_contribution'] * 100).round(1)

            type_map = {
                'flash_crash': '闪崩',
                'volatility_spike': '异常波动',
                'missing_data': '数据缺失',
                'timestamp_gap': '时间戳跳点',
                'anomaly': '一般异常'
            }
            display_attr['anomaly_type_cn'] = display_attr['anomaly_type'].map(type_map)

            display_df = display_attr[[
                'date', 'price', 'anomaly_score', 'anomaly_type_cn',
                'dominant_factor_cn', 'dominant_contribution_pct', 'explanation'
            ]]
            display_df.columns = [
                '日期', '价格', '异常评分', '异常类型',
                '主导因子', '贡献度(%)', '解释'
            ]
            st.dataframe(display_df, use_container_width=True)

            st.markdown("#### 🔍 单条异常详细分析")
            selected_idx = st.selectbox(
                "选择异常序号",
                options=range(len(attribution_results)),
                format_func=lambda x: f"{x+1}. {display_attr.iloc[x]['date']} - {display_attr.iloc[x]['anomaly_type_cn']}"
            )

            if selected_idx is not None:
                selected = attribution_results.iloc[selected_idx]
                st.info(f"**解释**: {selected['explanation']}")

                factors = selected['factors']
                factor_df = pd.DataFrame({
                    '因子': [factor_names_cn.get(k, k) for k in factors.keys()],
                    '贡献度': [v * 100 for v in factors.values()]
                })

                fig_bar = go.Figure(data=[go.Bar(
                    x=factor_df['贡献度'],
                    y=factor_df['因子'],
                    orientation='h',
                    marker_color='#1f77b4'
                )])
                fig_bar.update_layout(
                    title="各因子贡献度 (%)",
                    xaxis_title="贡献度 (%)",
                    height=400
                )
                st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("当前数据中未检测到异常")

        st.markdown("#### 📅 外部事件匹配")
        st.markdown("添加外部事件（如财报、政策变化等），系统将自动匹配异常时间点")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            event_date = st.date_input("事件日期")
        with col2:
            event_type = st.selectbox("事件类型", ["财报发布", "政策变化", "宏观数据", "公司事件", "其他"])
        with col3:
            event_name = st.text_input("事件名称")
        with col4:
            impact_level = st.select_slider("影响等级", ["low", "medium", "high"], value="medium")

        if st.button("添加事件"):
            st.session_state.event_detector.add_event(
                event_date, event_type, event_name, impact_level
            )
            st.success("事件已添加！")

        if not st.session_state.event_detector.event_database.empty:
            st.markdown("**已添加事件:**")
            events_df = st.session_state.event_detector.event_database.copy()
            events_df['date'] = pd.to_datetime(events_df['date']).dt.strftime('%Y-%m-%d')
            st.dataframe(events_df, use_container_width=True)

            if not attribution_results.empty:
                matched = st.session_state.event_detector.match_anomalies_with_events(
                    st.session_state.result_df
                )
                if matched:
                    st.markdown("**异常-事件匹配:**")
                    for m in matched:
                        st.markdown(f"- **{m['anomaly_date'].strftime('%Y-%m-%d')}** {m['anomaly_type']}: "
                                  f"匹配到 {len(m['matched_events'])} 个相关事件")
    else:
        st.info("请先进行异常检测")

with tab5:
    if len(st.session_state.multi_asset_results) > 0:
        st.subheader("📋 多资产异常列表")

        all_anomalies = []
        for asset_name, result in st.session_state.multi_asset_results.items():
            df = result['result_df']
            anomalies = df[df['is_anomaly']].copy()
            anomalies['asset'] = asset_name
            all_anomalies.append(anomalies)

        if all_anomalies:
            combined_df = pd.concat(all_anomalies, ignore_index=True)
            type_map = {
                'flash_crash': '闪崩',
                'volatility_spike': '异常波动',
                'missing_data': '数据缺失',
                'timestamp_gap': '时间戳跳点',
                'anomaly': '一般异常'
            }
            combined_df['anomaly_type_cn'] = combined_df['anomaly_type'].map(type_map)
            combined_df['ds'] = pd.to_datetime(combined_df['ds']).dt.strftime('%Y-%m-%d')

            display_df = combined_df[[
                'asset', 'ds', 'y', 'anomaly_score', 'anomaly_type_cn'
            ]]
            display_df.columns = [
                '资产名称', '日期', '价格', '异常评分', '异常类型'
            ]
            st.dataframe(display_df.sort_values('异常评分', ascending=False),
                        use_container_width=True)

            st.download_button(
                "导出异常列表CSV",
                display_df.to_csv(index=False).encode('utf-8-sig'),
                "异常列表.csv",
                "text/csv"
            )
    elif st.session_state.anomaly_intervals:
        st.subheader("检测到的异常区间")

        intervals_df = pd.DataFrame(st.session_state.anomaly_intervals)
        name_map = {
            'flash_crash': '闪崩',
            'volatility_spike': '异常波动',
            'missing_data': '数据缺失',
            'timestamp_gap': '时间戳跳点',
            'anomaly': '一般异常'
        }
        intervals_df['type'] = intervals_df['type'].map(name_map)
        intervals_df['start'] = pd.to_datetime(intervals_df['start']).dt.strftime('%Y-%m-%d')
        intervals_df['end'] = pd.to_datetime(intervals_df['end']).dt.strftime('%Y-%m-%d')
        intervals_df.columns = ['开始日期', '结束日期', '持续天数', '最高异常评分', '异常类型']

        st.dataframe(
            intervals_df[['异常类型', '开始日期', '结束日期', '持续天数', '最高异常评分']],
            use_container_width=True
        )

        if len(st.session_state.user_feedback) > 0:
            st.markdown("#### 人工反馈记录")
            feedback_df = pd.DataFrame(st.session_state.user_feedback)
            feedback_df['date'] = pd.to_datetime(feedback_df['date']).dt.strftime('%Y-%m-%d')
            feedback_df['is_anomaly'] = feedback_df['is_anomaly'].map({True: '是异常', False: '不是异常'})
            feedback_df.columns = ['日期', '是否异常', '置信度']
            st.dataframe(feedback_df, use_container_width=True)
    else:
        st.info("暂无检测到的异常区间")

with tab6:
    st.subheader("🔔 预警推送")

    if not st.session_state.alert_notifier.wecom_webhook and not st.session_state.alert_notifier.dingtalk_webhook:
        st.warning("⚠️ 请在左侧配置企业微信或钉钉的Webhook地址")
    else:
        col1, col2 = st.columns(2)
        with col1:
            st.success("✅ 企业微信已配置" if st.session_state.alert_notifier.wecom_webhook else "❌ 企业微信未配置")
        with col2:
            st.success("✅ 钉钉已配置" if st.session_state.alert_notifier.dingtalk_webhook else "❌ 钉钉未配置")

    if st.session_state.result_df is not None:
        st.markdown("#### 📨 手动推送预警")

        anomaly_df = st.session_state.result_df[st.session_state.result_df['is_anomaly']]
        if not anomaly_df.empty:
            selected_anomaly = st.selectbox(
                "选择要推送的异常",
                options=range(len(anomaly_df)),
                format_func=lambda x: f"{x+1}. {anomaly_df.iloc[x]['ds'].strftime('%Y-%m-%d')} - {anomaly_df.iloc[x]['anomaly_type']}"
            )

            push_platforms = st.multiselect(
                "推送平台",
                ["企业微信", "钉钉"],
                default=["企业微信"] if st.session_state.alert_notifier.wecom_webhook else []
            )

            include_attribution = st.checkbox("包含异常归因分析", value=True)

            if st.button("发送预警", type="primary"):
                if selected_anomaly is not None:
                    anomaly_row = anomaly_df.iloc[selected_anomaly]

                    attribution_result = None
                    if include_attribution and st.session_state.attribution_results is not None:
                        attr_matches = st.session_state.attribution_results[
                            st.session_state.attribution_results['date'] == anomaly_row['ds']
                        ]
                        if not attr_matches.empty:
                            attribution_result = attr_matches.iloc[0].to_dict()

                    platform_map = {"企业微信": "wecom", "钉钉": "dingtalk"}
                    platforms = [platform_map[p] for p in push_platforms]

                    alert_level, results = st.session_state.alert_notifier.send_anomaly_alert(
                        asset_name="当前资产",
                        anomaly_date=anomaly_row['ds'],
                        anomaly_type=anomaly_row['anomaly_type'],
                        anomaly_score=anomaly_row['anomaly_score'],
                        attribution_result=attribution_result,
                        platforms=platforms
                    )

                    for platform, result in results.items():
                        if result['success']:
                            st.success(f"✅ {platform} 推送成功")
                        else:
                            st.error(f"❌ {platform} 推送失败: {result['message']}")

        if not st.session_state.systemic_events_df.empty:
            st.markdown("#### ⚠️ 推送系统性风险预警")
            selected_event = st.selectbox(
                "选择系统性风险事件",
                options=range(len(st.session_state.systemic_events_df)),
                format_func=lambda x: (f"{x+1}. {st.session_state.systemic_events_df.iloc[x]['event_date'].strftime('%Y-%m-%d')} "
                                     f"- {st.session_state.systemic_events_df.iloc[x]['assets_involved']}个资产")
            )

            if st.button("推送系统性风险预警", type="secondary"):
                if selected_event is not None:
                    event_row = st.session_state.systemic_events_df.iloc[selected_event]
                    results = st.session_state.alert_notifier.send_systemic_risk_alert(
                        event_date=event_row['event_date'],
                        assets_involved=event_row['assets_involved'],
                        avg_score=event_row['avg_score'],
                        severity=event_row['severity'],
                        anomaly_types=event_row['anomaly_types'],
                        platforms=platforms if 'platforms' in locals() else ['wecom', 'dingtalk']
                    )
                    for platform, result in results.items():
                        if result['success']:
                            st.success(f"✅ {platform} 推送成功")
                        else:
                            st.error(f"❌ {platform} 推送失败: {result['message']}")

    st.markdown("#### 📜 推送历史记录")
    history_df = st.session_state.alert_notifier.get_alert_history()
    if not history_df.empty:
        history_df['time'] = pd.to_datetime(history_df['time']).dt.strftime('%Y-%m-%d %H:%M:%S')
        status_map = {'success': '✅ 成功', 'failed': '❌ 失败', 'error': '⚠️ 错误'}
        history_df['status_cn'] = history_df['status'].map(status_map)
        st.dataframe(history_df[['time', 'platform', 'title', 'status_cn', 'error']],
                    use_container_width=True)
    else:
        st.info("暂无推送历史")

    st.markdown("#### 🔧 Webhook配置说明")
    st.markdown("""
    **企业微信机器人配置:**
    1. 在企业微信群聊中添加群机器人
    2. 复制Webhook地址粘贴到左侧配置栏
    3. 选择"markdown"消息类型

    **钉钉机器人配置:**
    1. 在钉钉群聊中添加自定义机器人
    2. 选择"安全设置"为"自定义关键词"，添加关键词如"告警"、"预警"
    3. 复制Webhook地址粘贴到左侧配置栏
    """)

with tab7:
    if st.session_state.detector:
        st.subheader("🤖 模型状态")
        status = st.session_state.detector.get_model_status()

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("模型状态", "✅ 已训练" if status['is_trained'] else "❌ 未训练")
        with col2:
            st.metric("训练次数", status['training_count'])
        with col3:
            st.metric("反馈样本数", status['feedback_count'])

        col4, col5, col6 = st.columns(3)
        with col4:
            st.metric("基础阈值", f"{status['base_threshold']:.4f}" if status['base_threshold'] else "N/A")
        with col5:
            st.metric("动态阈值", "✅ 启用" if status['use_dynamic_threshold'] else "❌ 禁用")
        with col6:
            st.metric("历史误差样本", status['historical_errors_count'])

        if status['last_training_time']:
            st.info(f"⏰ 上次训练时间: {status['last_training_time'].strftime('%Y-%m-%d %H:%M:%S')}")

        if st.session_state.detector.training_history:
            st.markdown("#### 📚 训练历史")
            hist_df = pd.DataFrame(st.session_state.detector.training_history)
            hist_df['time'] = pd.to_datetime(hist_df['time']).dt.strftime('%Y-%m-%d %H:%M:%S')
            if 'type' not in hist_df.columns:
                hist_df['type'] = 'full'
            hist_df['type'] = hist_df['type'].map({'full': '完整训练', 'incremental': '增量训练'})
            st.dataframe(hist_df, use_container_width=True)

        if len(st.session_state.multi_asset_results) > 0:
            st.markdown("#### 📦 多资产模型状态")
            model_status = []
            for asset_name, result in st.session_state.multi_asset_results.items():
                ms = result['detector'].get_model_status()
                model_status.append({
                    '资产': asset_name,
                    '已训练': ms['is_trained'],
                    '训练次数': ms['training_count'],
                    '反馈样本数': ms['feedback_count']
                })
            st.dataframe(pd.DataFrame(model_status), use_container_width=True)

        st.markdown("---")
        st.markdown("#### 📤 模型导出")
        col_export1, col_export2 = st.columns(2)
        with col_export1:
            if st.button("保存模型状态"):
                st.info("模型保存功能开发中...")
        with col_export2:
            if st.button("导出训练日志"):
                st.info("日志导出功能开发中...")
    else:
        st.info("请先训练模型以查看状态")

st.markdown("---")
st.markdown("### 📌 使用说明")
st.markdown("""
1. **数据输入**: 支持模拟数据、CSV上传或Yahoo Finance下载，支持多资产批量加载
2. **多资产联动分析**: 加载2个以上资产后，自动检测协同异常识别系统性风险
3. **动态阈值**: 启用后阈值将根据历史重构误差和波动率自适应调整
4. **异常归因**: 自动分析每个异常的贡献因子（波动率、趋势偏离、价格跳变等）
5. **事件匹配**: 添加外部事件（财报、政策等），自动匹配异常时间点
6. **预警推送**: 配置企业微信/钉钉Webhook，支持手动和自动推送预警
7. **异常类型**:
   - 🔴 闪崩 (flash_crash): 价格单日跌幅超过5%
   - 🟠 异常波动 (volatility_spike): 单日涨跌幅超过3%
   - 🟣 数据缺失 (missing_data): 数据存在缺失
   - 🟤 时间戳跳点 (timestamp_gap): 时间戳不连续
   - 🟡 一般异常 (anomaly): 其他异常模式
""")
