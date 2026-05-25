import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import io
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.data_cleaning import DataCleaner
from src.feature_engineering import TimeSeriesFeatureEngineer
from src.automl import TimeSeriesAutoML
from src.competition import TimeSeriesCompetition

st.set_page_config(
    page_title="时间序列预测 AutoML 平台",
    page_icon="📈",
    layout="wide"
)

st.title("📈 时间序列预测 AutoML 平台")
st.markdown("---")

if 'data' not in st.session_state:
    st.session_state.data = None
if 'cleaned_data' not in st.session_state:
    st.session_state.cleaned_data = None
if 'engineered_data' not in st.session_state:
    st.session_state.engineered_data = None
if 'automl' not in st.session_state:
    st.session_state.automl = None
if 'predictions' not in st.session_state:
    st.session_state.predictions = None
if 'forecast_dates' not in st.session_state:
    st.session_state.forecast_dates = None
if 'feedback_data' not in st.session_state:
    st.session_state.feedback_data = []
if 'ensemble_predictions' not in st.session_state:
    st.session_state.ensemble_predictions = None
if 'feature_importance' not in st.session_state:
    st.session_state.feature_importance = None
if 'competition' not in st.session_state:
    st.session_state.competition = TimeSeriesCompetition("TimeSeries_AutoML_Challenge")

st.sidebar.header("📁 数据上传")
uploaded_file = st.sidebar.file_uploader("上传 CSV 文件", type=['csv'])

sample_data = st.sidebar.checkbox("使用示例数据")

if sample_data and st.session_state.data is None:
    date_rng = pd.date_range(start='2023-01-01', end='2024-01-01', freq='D')
    np.random.seed(42)
    trend = np.linspace(100, 200, len(date_rng))
    seasonality = 20 * np.sin(np.arange(len(date_rng)) * 2 * np.pi / 365)
    noise = np.random.normal(0, 5, len(date_rng))
    values = trend + seasonality + noise
    
    sample_df = pd.DataFrame({
        'date': date_rng,
        'value': values
    })
    st.session_state.data = sample_df
    st.sidebar.success("✅ 已加载示例数据")

if uploaded_file is not None:
    st.session_state.data = pd.read_csv(uploaded_file)
    st.sidebar.success("✅ 文件上传成功")

if st.session_state.data is not None:
    data = st.session_state.data
    
    with st.expander("📊 原始数据预览", expanded=True):
        st.dataframe(data.head(20), use_container_width=True)
        st.write(f"数据形状: {data.shape[0]} 行 × {data.shape[1]} 列")
        
        st.subheader("数据统计")
        st.write(data.describe())
    
    st.markdown("---")
    st.subheader("🔧 第一步：数据预处理")
    
    col1, col2 = st.columns(2)
    with col1:
        datetime_col = st.selectbox(
            "选择日期时间列",
            options=[col for col in data.columns if 'date' in col.lower() or 'time' in col.lower()] + [data.columns[0]],
            index=0
        )
    
    with col2:
        target_col = st.selectbox(
            "选择目标列（预测值）",
            options=[col for col in data.columns if col != datetime_col],
            index=0
        )
    
    st.markdown("#### 数据清洗配置")
    col1, col2, col3 = st.columns(3)
    with col1:
        fill_method = st.selectbox(
            "缺失值填充方法",
            options=['interpolate', 'ffill', 'mean', 'median'],
            index=0
        )
    with col2:
        anomaly_method = st.selectbox(
            "异常检测方法",
            options=['adaptive_iqr', 'iqr', 'zscore', 'isolation_forest'],
            index=0,
            help="自适应IQR: 根据数据偏度自动调整阈值"
        )
    with col3:
        anomaly_strategy = st.selectbox(
            "异常值处理策略",
            options=['interpolate', 'remove', 'cap'],
            index=0
        )
    
    if st.button("🚀 执行数据清洗", type="primary"):
        with st.spinner("正在进行数据清洗..."):
            try:
                data[datetime_col] = pd.to_datetime(data[datetime_col])
                data = data.set_index(datetime_col).sort_index()
                
                cleaner = DataCleaner()
                cleaned_data, clean_report = cleaner.clean_data(
                    data,
                    fill_method=fill_method,
                    anomaly_method=anomaly_method,
                    anomaly_strategy=anomaly_strategy
                )
                
                st.session_state.cleaned_data = cleaned_data
                st.session_state.target_col = target_col
                st.session_state.datetime_col = datetime_col
                
                st.success("✅ 数据清洗完成！")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**清洗报告**")
                    st.write(f"原始行数: {clean_report['original_rows']}")
                    st.write(f"原始缺失值: {clean_report['original_missing']}")
                    st.write(f"检测到异常值: {clean_report['anomalies_detected']}")
                    st.write(f"最终行数: {clean_report['final_rows']}")
                
                with col2:
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=data.index, y=data[target_col],
                        mode='lines', name='原始数据', opacity=0.5
                    ))
                    fig.add_trace(go.Scatter(
                        x=cleaned_data.index, y=cleaned_data[target_col],
                        mode='lines', name='清洗后数据', line=dict(color='red')
                    ))
                    fig.update_layout(title='原始数据 vs 清洗后数据')
                    st.plotly_chart(fig, use_container_width=True)
                    
            except Exception as e:
                st.error(f"❌ 数据清洗失败: {str(e)}")
    
    if st.session_state.cleaned_data is not None:
        st.markdown("---")
        st.subheader("⚙️ 第二步：特征工程")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            create_time_features = st.checkbox("创建时间特征", value=True)
        with col2:
            create_lag_features = st.checkbox("创建滞后特征", value=True)
        with col3:
            auto_detect_seasonality = st.checkbox("自动季节性检测", value=True,
                                                   help="根据ACF自动检测季节性并确定滞后步长")
        with col4:
            scale_features = st.checkbox("标准化特征", value=False)
        
        if create_lag_features and not auto_detect_seasonality:
            col1, col2 = st.columns(2)
            with col1:
                lags_input = st.text_input("滞后值 (逗号分隔)", value="1,2,3,7,14")
                lags = [int(x.strip()) for x in lags_input.split(',')]
            with col2:
                windows_input = st.text_input("窗口大小 (逗号分隔)", value="7,14,28")
                window_sizes = [int(x.strip()) for x in windows_input.split(',')]
        else:
            lags = None
            window_sizes = None
        
        if st.button("🔨 执行特征工程"):
            with st.spinner("正在进行特征工程..."):
                try:
                    engineer = TimeSeriesFeatureEngineer()
                    engineered_data, feat_report = engineer.engineer_features(
                        st.session_state.cleaned_data,
                        target_col=st.session_state.target_col,
                        create_time=create_time_features,
                        create_lag=create_lag_features,
                        lags=lags,
                        window_sizes=window_sizes,
                        auto_detect_seasonality=auto_detect_seasonality,
                        scale=scale_features
                    )
                    
                    st.session_state.engineered_data = engineered_data
                    st.session_state.engineer = engineer
                    
                    st.success("✅ 特征工程完成！")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"新增特征数: {feat_report['new_features']}")
                        st.write(f"最终特征数: {feat_report['final_columns']}")
                        
                        if engineer.detected_seasonality:
                            st.info(f"📊 检测到季节性周期: {engineer.detected_seasonality['seasonal_period']}")
                            st.write(f"ACF峰值: {engineer.detected_seasonality['acf_peaks']}")
                    
                    with col2:
                        if 'detected_seasonality' in feat_report:
                            st.write("**自动检测结果**")
                            st.json(feat_report['detected_seasonality'])
                    
                    with st.expander("查看所有特征"):
                        st.write(engineered_data.columns.tolist())
                    
                    fig = px.imshow(
                        engineered_data.corr(),
                        title='特征相关性热力图',
                        aspect='auto'
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    
                except Exception as e:
                    st.error(f"❌ 特征工程失败: {str(e)}")
                    import traceback
                    st.error(traceback.format_exc())
    
    if st.session_state.engineered_data is not None:
        st.markdown("---")
        st.subheader("🤖 第三步：AutoML 模型训练")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            selected_models = st.multiselect(
                "选择模型类型",
                options=['arima', 'prophet', 'xgboost', 'lstm'],
                default=['arima', 'prophet', 'xgboost', 'lstm']
            )
        with col2:
            n_trials = st.slider("总试验次数", min_value=5, max_value=50, value=10)
        with col3:
            forecast_horizon = st.slider("预测步长", min_value=1, max_value=90, value=7)
        with col4:
            two_stage_opt = st.checkbox("分阶段搜索", value=True,
                                        help="先粗略搜索，后精细搜索，加速收敛")
        
        col1, col2 = st.columns(2)
        with col1:
            metric = st.selectbox(
                "优化指标",
                options=['rmse', 'mae', 'mape'],
                index=0
            )
        with col2:
            if two_stage_opt:
                coarse_ratio = st.slider("粗略搜索比例", min_value=0.3, max_value=0.6, value=0.4,
                                         help="分配给粗略搜索的试验比例")
            else:
                coarse_ratio = 0.4
        
        if st.button("🎯 开始 AutoML 训练", type="primary"):
            with st.spinner("正在进行 AutoML 模型优化... (此过程可能需要几分钟)"):
                try:
                    engineered_data = st.session_state.engineered_data
                    target_col = st.session_state.target_col
                    
                    y = engineered_data[target_col]
                    X = engineered_data.drop(columns=[target_col])
                    
                    automl = TimeSeriesAutoML(
                        model_types=selected_models,
                        n_trials=n_trials,
                        metric=metric,
                        direction='minimize',
                        two_stage_optimization=two_stage_opt,
                        coarse_trials_ratio=coarse_ratio
                    )
                    
                    automl.fit(y, X, forecast_horizon=forecast_horizon)
                    st.session_state.automl = automl
                    st.session_state.forecast_horizon = forecast_horizon
                    
                    st.success("✅ AutoML 训练完成！")
                    
                    st.markdown("### 🏆 模型对比结果")
                    comparison = automl.get_model_comparison()
                    st.dataframe(comparison, use_container_width=True)
                    
                    st.markdown(f"### 🥇 最佳模型: {automl.best_model_name.upper()}")
                    st.write(f"最佳参数: {automl.best_params}")
                    st.write(f"最佳 {metric.upper()}: {automl.best_score:.4f}")
                    
                    last_date = engineered_data.index[-1]
                    if isinstance(last_date, pd.Timestamp):
                        freq = pd.infer_freq(engineered_data.index) or 'D'
                        forecast_dates = pd.date_range(
                            start=last_date + pd.Timedelta(days=1),
                            periods=forecast_horizon,
                            freq=freq
                        )
                    else:
                        forecast_dates = pd.RangeIndex(
                            start=len(engineered_data),
                            stop=len(engineered_data) + forecast_horizon
                        )
                    
                    X_test = X.tail(forecast_horizon).copy()
                    predictions = automl.predict(forecast_horizon, X_test)
                    
                    st.session_state.predictions = predictions
                    st.session_state.forecast_dates = forecast_dates
                    
                    st.markdown("### 📊 预测结果")
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=y.index[-30:], y=y.values[-30:],
                        mode='lines', name='历史数据', line=dict(color='blue')
                    ))
                    fig.add_trace(go.Scatter(
                        x=forecast_dates, y=predictions,
                        mode='lines+markers', name='预测值',
                        line=dict(color='red', dash='dash')
                    ))
                    fig.update_layout(title='历史数据与预测结果')
                    st.plotly_chart(fig, use_container_width=True)
                    
                    pred_df = pd.DataFrame({
                        '日期': forecast_dates,
                        '预测值': predictions
                    })
                    st.dataframe(pred_df, use_container_width=True)
                    
                    st.markdown("---")
                    st.subheader("🔍 模型解释：特征重要性")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        model_for_interpret = st.selectbox(
                            "选择模型进行解释",
                            options=list(automl.best_models.keys()),
                            index=0,
                            format_func=lambda x: x.upper()
                        )
                    with col2:
                        show_top_n = st.slider("显示Top N特征", min_value=5, max_value=30, value=15)
                    
                    if st.button("📊 计算特征重要性"):
                        with st.spinner("正在计算特征重要性..."):
                            try:
                                X_all = engineered_data.drop(columns=[target_col])
                                y_all = engineered_data[target_col]
                                
                                importance_df = automl.get_feature_importance(
                                    model_name=model_for_interpret,
                                    X=X_all,
                                    y=y_all
                                )
                                
                                st.session_state.feature_importance = importance_df
                                
                                if not importance_df.empty:
                                    st.success("✅ 特征重要性计算完成！")
                                    
                                    col1, col2 = st.columns(2)
                                    with col1:
                                        st.dataframe(importance_df.head(show_top_n), use_container_width=True)
                                    
                                    with col2:
                                        fig = px.bar(
                                            importance_df.head(show_top_n),
                                            x='feature',
                                            y=importance_df.columns[1],
                                            title=f'Top {show_top_n} 特征重要性',
                                            orientation='v'
                                        )
                                        fig.update_layout(xaxis_tickangle=-45)
                                        st.plotly_chart(fig, use_container_width=True)
                                else:
                                    st.warning("该模型暂不支持特征重要性分析")
                                    
                            except Exception as e:
                                st.error(f"特征重要性计算失败: {str(e)}")
                    
                    st.markdown("---")
                    st.subheader("🤝 集成预测：多模型加权平均")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        ensemble_method = st.selectbox(
                            "集成权重计算方法",
                            options=['rank', 'equal', 'inverse_score', 'optimized'],
                            index=0,
                            format_func=lambda x: {
                                'rank': '排名加权',
                                'equal': '等权重',
                                'inverse_score': '得分倒数加权',
                                'optimized': '优化权重'
                            }[x]
                        )
                    with col2:
                        st.info("集成预测可以提升预测稳定性和精度")
                    
                    if st.button("🚀 生成集成预测"):
                        with st.spinner("正在生成集成预测..."):
                            try:
                                y_val = engineered_data[target_col].tail(forecast_horizon)
                                X_val = engineered_data.drop(columns=[target_col]).tail(forecast_horizon)
                                
                                automl.create_ensemble(
                                    y_val=y_val,
                                    X_val=X_val,
                                    horizon=forecast_horizon,
                                    weight_method=ensemble_method
                                )
                                
                                ensemble_preds = automl.predict_ensemble(forecast_horizon, X_test)
                                st.session_state.ensemble_predictions = ensemble_preds
                                
                                st.success("✅ 集成预测生成完成！")
                                
                                weights_df = automl.get_ensemble_weights()
                                st.write("**模型权重分配**")
                                st.dataframe(weights_df, use_container_width=True)
                                
                                all_preds_df = automl.get_all_model_predictions(forecast_horizon, X_test)
                                all_preds_df['ENSEMBLE'] = ensemble_preds
                                all_preds_df.index = forecast_dates
                                
                                st.markdown("**各模型预测对比**")
                                fig = go.Figure()
                                for col in all_preds_df.columns:
                                    fig.add_trace(go.Scatter(
                                        x=all_preds_df.index,
                                        y=all_preds_df[col],
                                        mode='lines+markers',
                                        name=col.upper(),
                                        line=dict(dash='dash' if col == 'ENSEMBLE' else 'solid',
                                                  width=3 if col == 'ENSEMBLE' else 1)
                                    ))
                                fig.update_layout(title='各模型预测结果对比')
                                st.plotly_chart(fig, use_container_width=True)
                                
                            except Exception as e:
                                st.error(f"集成预测生成失败: {str(e)}")
                                import traceback
                                st.error(traceback.format_exc())
                    
                except Exception as e:
                    st.error(f"❌ AutoML 训练失败: {str(e)}")
                    import traceback
                    st.error(traceback.format_exc())
    
    if st.session_state.automl is not None and st.session_state.predictions is not None:
        st.markdown("---")
        st.subheader("💬 第四步：用户反馈与模型更新")
        
        st.info("如果您有实际观测值，可以在此输入以帮助模型改进！")
        
        col1, col2 = st.columns(2)
        with col1:
            feedback_date = st.date_input(
                "实际数据日期",
                min_value=st.session_state.forecast_dates[0].date() if hasattr(st.session_state.forecast_dates[0], 'date') else datetime.now().date()
            )
        with col2:
            feedback_value = st.number_input("实际观测值", value=0.0)
        
        if st.button("📝 添加反馈"):
            st.session_state.feedback_data.append({
                'date': feedback_date,
                'value': feedback_value
            })
            st.success("✅ 反馈已添加！")
        
        if st.session_state.feedback_data:
            st.write("已收集的反馈数据:")
            feedback_df = pd.DataFrame(st.session_state.feedback_data)
            st.dataframe(feedback_df, use_container_width=True)
            
            if st.button("🔄 使用反馈数据更新模型"):
                with st.spinner("正在更新模型..."):
                    try:
                        engineered_data = st.session_state.engineered_data
                        target_col = st.session_state.target_col
                        
                        feedback_series = pd.Series(
                            [f['value'] for f in st.session_state.feedback_data],
                            index=pd.to_datetime([f['date'] for f in st.session_state.feedback_data])
                        )
                        feedback_series.name = target_col
                        
                        combined_y = pd.concat([engineered_data[target_col], feedback_series])
                        combined_y = combined_y[~combined_y.index.duplicated(keep='last')]
                        combined_y = combined_y.sort_index()
                        
                        st.session_state.automl.update_with_feedback(combined_y)
                        
                        st.success("✅ 模型更新完成！")
                        st.write(f"新的最佳模型: {st.session_state.automl.best_model_name.upper()}")
                        
                    except Exception as e:
                        st.error(f"❌ 模型更新失败: {str(e)}")
        
        st.markdown("---")
        st.subheader("🏆 第五步：时序预测竞赛")
        
        st.info("🎯 提交您的模型预测结果参与竞赛，与其他模型一较高下！")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            team_name = st.text_input("团队名称", value="MyTeam")
        with col2:
            submit_model_name = st.text_input("模型名称", value="MyModel")
        with col3:
            submission_desc = st.text_input("模型描述", value="")
        
        col1, col2 = st.columns(2)
        with col1:
            use_ensemble = st.checkbox("使用集成预测提交", value=False)
        with col2:
            st.write("")
        
        if st.button("📤 提交到竞赛"):
            with st.spinner("正在提交..."):
                try:
                    engineered_data = st.session_state.engineered_data
                    target_col = st.session_state.target_col
                    
                    y_true = engineered_data[target_col].tail(st.session_state.forecast_horizon)
                    
                    if use_ensemble and st.session_state.ensemble_predictions is not None:
                        predictions = st.session_state.ensemble_predictions
                        submit_model_name = submit_model_name + "_Ensemble"
                    else:
                        predictions = st.session_state.predictions
                    
                    result = st.session_state.competition.submit_model(
                        team_name=team_name,
                        model_name=submit_model_name,
                        y_pred=predictions,
                        y_true=y_true,
                        description=submission_desc
                    )
                    
                    st.success(f"✅ 提交成功！当前排名: #{result['current_rank']}")
                    st.write(f"RMSE: {result['metrics']['rmse']:.4f}")
                    st.write(f"MAE: {result['metrics']['mae']:.4f}")
                    
                except Exception as e:
                    st.error(f"提交失败: {str(e)}")
        
        st.markdown("---")
        st.subheader("📊 竞赛排行榜")
        
        leaderboard = st.session_state.competition.get_leaderboard()
        
        if not leaderboard.empty:
            col1, col2 = st.columns(2)
            with col1:
                st.dataframe(leaderboard, use_container_width=True)
            with col2:
                stats = st.session_state.competition.get_competition_stats()
                st.write("**竞赛统计**")
                st.write(f"参赛团队数: {stats.get('total_teams', 0)}")
                st.write(f"总提交次数: {stats.get('total_submissions', 0)}")
                st.write(f"最佳RMSE: {stats.get('best_rmse', 0):.4f}")
                st.write(f"平均RMSE: {stats.get('mean_rmse', 0):.4f}")
            
            fig = px.bar(
                leaderboard,
                x='team_name',
                y='rmse',
                color='rank',
                title='竞赛RMSE对比',
                text='rmse'
            )
            fig.update_traces(texttemplate='%{text:.4f}', textposition='outside')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("暂无提交记录，成为第一个提交者吧！")
        
        st.markdown("---")
        st.subheader("📥 导出结果")
        
        if st.button("导出预测结果 (CSV)"):
            pred_df = pd.DataFrame({
                'date': st.session_state.forecast_dates,
                'prediction': st.session_state.predictions
            })
            
            csv = pred_df.to_csv(index=False)
            st.download_button(
                label="⬇️ 下载预测结果",
                data=csv,
                file_name=f'predictions_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
                mime='text/csv'
            )

else:
    st.info("👈 请在左侧上传数据文件，或勾选'使用示例数据'开始体验！")
    
    st.markdown("""
    ## 🚀 平台功能介绍
    
    欢迎使用时间序列预测 AutoML 平台！本平台提供端到端的时间序列预测解决方案：
    
    ### 🔧 数据清洗
    - **缺失值填充**：支持插值、前向填充、均值、中位数等方法
    - **异常检测**：支持 Isolation Forest、Z-score、IQR 方法
    - **异常处理**：支持插值、删除、盖帽处理
    
    ### ⚙️ 特征工程
    - **时间特征**：年、月、日、星期、节假日等
    - **滞后特征**：自定义滞后阶数
    - **滚动统计**：均值、标准差、最大最小值等
    - **特征标准化**：StandardScaler / MinMaxScaler
    
    ### 🤖 模型库
    - **ARIMA**：经典统计模型
    - **Prophet**：Facebook 开源模型，适合强季节性数据
    - **XGBoost**：梯度提升树，适合复杂非线性关系
    - **LSTM**：深度学习模型，适合长序列依赖
    
    ### 🎯 AutoML 优化
    - **Optuna 超参数优化**
    - **时间序列交叉验证**
    - **多模型自动对比**
    - **最佳模型自动选择**
    
    ### 💬 用户反馈
    - 支持输入实际观测值
    - 基于反馈数据在线更新模型
    - 持续学习优化
    
    ---
    
    ### 📊 支持的文件格式
    - CSV 格式
    - 包含日期列和数值列
    """)

st.markdown("---")
st.caption("🚀 时间序列预测 AutoML 平台 | Powered by Streamlit + Optuna + sktime")
