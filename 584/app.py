import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import warnings
import time
warnings.filterwarnings('ignore')

st.set_page_config(
    page_title="股票因子挖掘平台",
    page_icon="📈",
    layout="wide"
)

from config import Config
from data_loader import DataLoader
from gp_factor_miner import GPFactorMiner
from factor_evaluator import FactorEvaluator, TransactionCostModel
from factor_combiner import FactorCombiner
from factor_interpreter import FactorInterpreter
from factor_decay_tracker import FactorDecayTracker, FactorStatus
from gpu_accelerator import is_gpu_available, get_device_info, AcceleratedFactorOps

st.title("📈 股票因子挖掘平台")
st.markdown("基于遗传编程的Alpha因子自动挖掘与分析系统 | GPU加速 · 因子解释 · 衰减预警")

@st.cache_data
def load_sample_data(n_assets, n_days):
    loader = DataLoader()
    return loader.load_sample_data(n_assets, n_days)

def main():
    st.sidebar.header("导航")
    page = st.sidebar.radio(
        "选择功能模块",
        ["数据加载", "因子挖掘", "因子评估", "相关性分析", "因子组合", "因子解释与预警"]
    )
    
    gpu_info = get_device_info()
    st.sidebar.markdown("---")
    st.sidebar.markdown("**硬件状态**")
    if gpu_info['gpu_available']:
        st.sidebar.success(f"GPU: {gpu_info.get('gpu_name', 'Available')}")
    else:
        st.sidebar.info("CPU模式 (Numba JIT加速)")
    
    if 'data' not in st.session_state:
        st.session_state.data = None
    if 'factors' not in st.session_state:
        st.session_state.factors = []
    if 'factor_values' not in st.session_state:
        st.session_state.factor_values = []
    if 'factor_evaluations' not in st.session_state:
        st.session_state.factor_evaluations = []
    if 'gp_miner' not in st.session_state:
        st.session_state.gp_miner = None
    
    if page == "数据加载":
        st.header("📊 数据加载")
        
        data_source = st.radio("数据来源", ["生成示例数据", "上传CSV文件"])
        
        if data_source == "生成示例数据":
            col1, col2 = st.columns(2)
            with col1:
                n_assets = st.slider("股票数量", 10, 200, 50)
            with col2:
                n_days = st.slider("交易日数", 100, 1000, 252)
            
            if st.button("生成数据"):
                with st.spinner("正在生成示例数据..."):
                    st.session_state.data = load_sample_data(n_assets, n_days)
                    st.success(f"成功生成 {n_assets} 只股票，{n_days} 个交易日的数据")
        
        else:
            uploaded_file = st.file_uploader("上传CSV文件", type="csv")
            if uploaded_file is not None:
                with st.spinner("正在加载数据..."):
                    loader = DataLoader()
                    st.session_state.data = loader.load_from_csv(uploaded_file)
                    st.success("数据加载成功！")
        
        if st.session_state.data is not None:
            st.subheader("数据预览")
            st.dataframe(st.session_state.data.head(100))
            
            st.subheader("数据统计")
            st.write(f"股票数量: {st.session_state.data['asset'].nunique()}")
            st.write(f"日期范围: {st.session_state.data['date'].min()} 至 {st.session_state.data['date'].max()}")
            
            st.subheader("价格走势")
            sample_assets = st.session_state.data['asset'].unique()[:5]
            plot_data = st.session_state.data[st.session_state.data['asset'].isin(sample_assets)]
            
            fig = px.line(
                plot_data,
                x='date',
                y='close',
                color='asset',
                title='样本股票收盘价走势'
            )
            st.plotly_chart(fig, use_container_width=True)
    
    elif page == "因子挖掘":
        st.header("🧬 遗传编程因子挖掘")
        
        if st.session_state.data is None:
            st.warning("请先加载数据！")
            return
        
        st.subheader("GP算法参数设置")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            pop_size = st.slider("种群大小", 50, 500, 100)
        with col2:
            n_gen = st.slider("进化代数", 5, 50, 10)
        with col3:
            max_depth = st.slider("最大深度", 2, 10, 5)
        
        st.subheader("多样性保护设置")
        col1, col2, col3 = st.columns(3)
        with col1:
            use_niching = st.checkbox("启用小生境选择", value=True)
        with col2:
            preserve_bad = st.checkbox("保留劣评因子", value=True)
        with col3:
            niche_radius = st.slider("小生境半径", 0.1, 0.5, 0.3)
        
        if st.button("开始挖掘因子"):
            with st.spinner("正在进行遗传编程因子挖掘..."):
                loader = DataLoader()
                prices, forward_returns = loader.prepare_factor_data(st.session_state.data)
                
                miner = GPFactorMiner()
                st.session_state.gp_miner = miner
                factors = miner.mine_factors(
                    st.session_state.data, forward_returns,
                    population_size=pop_size,
                    generations=n_gen,
                    use_niching=use_niching,
                    preserve_bad=preserve_bad
                )
                
                st.session_state.factors = factors
                st.session_state.factor_values = []
                factor_names = []
                
                for factor in factors:
                    factor_vals = miner.calculate_factor_values(
                        factor['individual'],
                        st.session_state.data
                    )
                    st.session_state.factor_values.append(factor_vals)
                    factor_names.append(factor['id'])
                
                st.session_state.factor_names = factor_names
                st.success(f"成功挖掘 {len(factors)} 个因子！")
        
        if st.session_state.factors:
            st.subheader("挖掘到的因子")
            
            factor_df = pd.DataFrame([
                {
                    '因子ID': f['id'],
                    '适应度(IC)': f['fitness'],
                    '表达式': f['expression']
                } for f in st.session_state.factors
            ])
            st.dataframe(factor_df)
            
            if st.session_state.gp_miner and hasattr(st.session_state.gp_miner, 'diversity_history'):
                st.subheader("种群多样性变化")
                diversity_history = st.session_state.gp_miner.diversity_history
                if diversity_history:
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=list(range(len(diversity_history))),
                        y=diversity_history,
                        mode='lines+markers',
                        name='多样性'
                    ))
                    fig.update_layout(
                        title='种群多样性随进化代数变化',
                        xaxis_title='代数',
                        yaxis_title='多样性'
                    )
                    st.plotly_chart(fig, use_container_width=True)
            
            st.subheader("因子表达式详情")
            selected_factor = st.selectbox(
                "选择因子查看详情",
                [f['id'] for f in st.session_state.factors],
                format_func=lambda x: x
            )
            
            for f in st.session_state.factors:
                if f['id'] == selected_factor:
                    st.code(f['expression'])
                    
                    interpreter = FactorInterpreter()
                    interp = interpreter.interpret(f['expression'])
                    st.markdown(f"**💡 因子含义**: {interp['readable_description']}")
                    if interp['factor_types']:
                        st.markdown(f"**🏷️ 因子类型**: {', '.join(interp['factor_types'])}")
                    if interp['pattern_meanings']:
                        st.markdown(f"**📝 识别模式**: {', '.join(interp['pattern_meanings'])}")
                    s = interp['structure']
                    st.markdown(f"**🔧 复杂度**: 嵌套{s['nesting_depth']}层 | {s['n_operators']}个算子 | {s['n_features']}个特征")
                    if interp['warnings']:
                        for w in interp['warnings']:
                            st.warning(f"⚠️ {w}")
                    break
    
    elif page == "因子评估":
        st.header("📐 因子评估")
        
        if not st.session_state.factor_values:
            st.warning("请先进行因子挖掘！")
            return
        
        loader = DataLoader()
        prices, forward_returns = loader.prepare_factor_data(st.session_state.data)
        
        st.subheader("交易费用模型设置")
        col1, col2, col3 = st.columns(3)
        with col1:
            base_fee = st.slider("基础手续费(‰)", 0.0, 5.0, 0.3) / 1000
        with col2:
            slippage = st.slider("滑点因子(‰)", 0.0, 2.0, 0.1) / 1000
        with col3:
            market_impact = st.slider("市场冲击(‰)", 0.0, 1.0, 0.01) / 1000
        
        portfolio_value = st.number_input("组合规模(元)", 1e6, 1e10, 1e8)
        
        evaluator = FactorEvaluator()
        evaluator.cost_model = TransactionCostModel(
            base_fee=base_fee,
            slippage_factor=slippage,
            market_impact_factor=market_impact
        )
        
        if st.button("开始评估所有因子"):
            t0 = time.time()
            with st.spinner("正在评估因子..."):
                evaluations = evaluator.evaluate_factors_parallel(
                    st.session_state.factor_values,
                    forward_returns,
                    st.session_state.factor_names,
                    include_transaction_costs=True
                )
                st.session_state.factor_evaluations = evaluations
                elapsed = time.time() - t0
                st.success(f"评估完成！耗时 {elapsed:.2f} 秒")
        
        if st.session_state.factor_evaluations:
            summary_df = evaluator.get_summary_table(
                st.session_state.factor_evaluations
            )
            st.dataframe(summary_df)
            
            st.subheader("因子表现可视化")
            
            selected_factor = st.selectbox(
                "选择因子查看详细分析",
                [evl['name'] for evl in st.session_state.factor_evaluations]
            )
            
            for evl in st.session_state.factor_evaluations:
                if evl['name'] == selected_factor:
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("IC均值", f"{evl['ic_mean']:.4f}")
                        st.metric("IR", f"{evl['ir']:.4f}")
                    with col2:
                        st.metric("日换手率", f"{evl['turnover']:.4f}")
                        st.metric("年化换手率", f"{evl['turnover'] * 252:.2f}")
                    with col3:
                        cost_analysis = evl['returns_analysis'].get('cost_analysis', {})
                        annual_cost = cost_analysis.get('annualized_cost', 0)
                        st.metric("年化交易成本", f"{annual_cost:.4%}")
                    with col4:
                        st.metric("年化收益(毛)", f"{evl['returns_analysis']['annual_return']:.2%}")
                        st.metric("年化收益(净)", f"{evl['returns_analysis']['annual_return_net']:.2%}")
                    
                    st.subheader("IC时间序列")
                    ic_series = evl['ic_series']
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=ic_series.index,
                        y=ic_series.values,
                        mode='lines',
                        name='IC'
                    ))
                    fig.add_hline(y=ic_series.mean(),
                        line_dash="dash",
                        annotation_text="均值")
                    fig.update_layout(title="IC时间序列")
                    st.plotly_chart(fig, use_container_width=True)
                    
                    st.subheader("换手率与交易成本")
                    turnover_series = evl['turnover_series']
                    cost_analysis = evl['returns_analysis'].get('cost_analysis', {})
                    
                    if cost_analysis:
                        daily_costs = cost_analysis.get('daily_costs', pd.Series())
                        
                        fig = go.Figure()
                        fig.add_trace(go.Scatter(
                            x=turnover_series.index,
                            y=turnover_series.values,
                            mode='lines',
                            name='换手率',
                            yaxis='y'
                        ))
                        if not daily_costs.empty:
                            fig.add_trace(go.Scatter(
                                x=daily_costs.index,
                                y=daily_costs.values,
                                mode='lines',
                                name='交易成本',
                                yaxis='y2'
                            ))
                        fig.update_layout(
                            title='日换手率与交易成本',
                            yaxis=dict(title='换手率'),
                            yaxis2=dict(title='交易成本', overlaying='y', side='right')
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    
                    st.subheader("分位数收益")
                    q_returns = evl['returns_analysis']['quantile_returns']
                    fig = go.Figure()
                    for i in range(q_returns.shape[1]):
                        fig.add_trace(go.Bar(
                            x=[f'Q{i+1}'],
                            y=[q_returns.iloc[:, i].mean()],
                            name=f'Q{i+1}'
                        ))
                    fig.update_layout(title="各分位数平均收益")
                    st.plotly_chart(fig, use_container_width=True)
                    
                    st.subheader("多空累计收益")
                    ls_cum = evl['returns_analysis']['long_short_cumulative']
                    ls_cum_net = evl['returns_analysis']['long_short_cumulative_net']
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=ls_cum.index,
                        y=ls_cum.values,
                        mode='lines',
                        name='毛收益'
                    ))
                    fig.add_trace(go.Scatter(
                        x=ls_cum_net.index,
                        y=ls_cum_net.values,
                        mode='lines',
                        name='净收益(扣除费用)'
                    ))
                    fig.update_layout(title="多空组合累计收益")
                    st.plotly_chart(fig, use_container_width=True)
    
    elif page == "相关性分析":
        st.header("🔗 因子相关性分析")
        
        if not st.session_state.factor_values:
            st.warning("请先进行因子挖掘！")
            return
        
        combiner = FactorCombiner()
        
        corr_matrix = combiner.calculate_correlation_matrix(
            st.session_state.factor_values
        )
        
        st.subheader("因子相关性热力图")
        fig, ax = plt.subplots(figsize=(10, 8))
        sns.heatmap(
            corr_matrix,
            annot=True,
            cmap='coolwarm',
            center=0,
            ax=ax
        )
        st.pyplot(fig)
        
        st.subheader("低相关性因子筛选")
        max_corr = st.slider("最大相关系数阈值", 0.3, 0.9, 0.7)
        
        selected_indices, selected_names = combiner.select_low_correlation_factors(
            st.session_state.factor_values,
            st.session_state.factor_names,
            max_corr
        )
        
        st.write(f"筛选后保留的因子:")
        st.write(selected_names)
        
        st.session_state.selected_factor_indices = selected_indices
        st.session_state.selected_factor_names = selected_names
        
        if len(selected_indices) < len(st.session_state.factor_values):
            st.info(f"已筛选掉 {len(st.session_state.factor_values) - len(selected_indices)} 个高相关性因子")
    
    elif page == "因子组合":
        st.header("⚖️ 因子组合优化")
        
        if not st.session_state.factor_evaluations:
            st.warning("请先进行因子评估！")
            return
        
        combiner = FactorCombiner()
        
        st.subheader("组合优化设置")
        col1, col2 = st.columns(2)
        with col1:
            method = st.selectbox(
                "组合方法",
                ["equal_weight", "ic_weight", "ir_weight", "max_ir", "risk_parity"]
            )
        with col2:
            l2_reg = st.slider("L2正则化系数", 0.0, 0.1, 0.01, 0.001)
        
        col1, col2 = st.columns(2)
        with col1:
            turnover_penalty = st.slider("换手率惩罚系数", 0.0, 1.0, 0.0)
        with col2:
            use_selected_factors = st.checkbox("使用筛选后的低相关因子", value=True)
        
        if st.button("构建因子组合"):
            with st.spinner("正在构建因子组合..."):
                loader = DataLoader()
                prices, forward_returns = loader.prepare_factor_data(st.session_state.data)
                
                if use_selected_factors and hasattr(st.session_state, 'selected_factor_indices'):
                    indices = st.session_state.selected_factor_indices
                    selected_factors = [st.session_state.factor_values[i] for i in indices]
                    selected_evaluations = [st.session_state.factor_evaluations[i] for i in indices]
                    selected_names = st.session_state.selected_factor_names
                else:
                    selected_factors = st.session_state.factor_values
                    selected_evaluations = st.session_state.factor_evaluations
                    selected_names = st.session_state.factor_names
                
                combined_factor, weights = combiner.combine_factors(
                    selected_factors,
                    selected_evaluations,
                    forward_returns,
                    method=method,
                    l2_reg=l2_reg,
                    turnover_penalty=turnover_penalty
                )
                
                evaluator = FactorEvaluator()
                combined_eval = evaluator.evaluate_factor(
                    combined_factor,
                    forward_returns,
                    '组合因子'
                )
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("组合IC", f"{combined_eval['ic_mean']:.4f}")
                with col2:
                    st.metric("组合IR", f"{combined_eval['ir']:.4f}")
                with col3:
                    st.metric("换手率", f"{combined_eval['turnover']:.4f}")
                with col4:
                    st.metric("夏普比率(净)", f"{combined_eval['returns_analysis']['sharpe_net']:.4f}")
                
                st.subheader("因子权重")
                weight_df = combiner.get_weight_summary(selected_names)
                st.dataframe(weight_df)
                
                fig = px.pie(
                    weight_df,
                    values='权重',
                    names='因子',
                    title='因子权重分布'
                )
                st.plotly_chart(fig, use_container_width=True)
                
                st.subheader("组合因子累计收益")
                ls_cum = combined_eval['returns_analysis']['long_short_cumulative']
                ls_cum_net = combined_eval['returns_analysis']['long_short_cumulative_net']
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=ls_cum.index,
                    y=ls_cum.values,
                    mode='lines',
                    name='毛收益'
                ))
                fig.add_trace(go.Scatter(
                    x=ls_cum_net.index,
                    y=ls_cum_net.values,
                    mode='lines',
                    name='净收益(扣除费用)'
                ))
                fig.update_layout(title="组合因子多空累计收益")
                st.plotly_chart(fig, use_container_width=True)
    
    elif page == "因子解释与预警":
        st.header("🔍 因子解释与衰减预警")
        
        if not st.session_state.factors:
            st.warning("请先进行因子挖掘！")
            return
        
        tab1, tab2, tab3 = st.tabs(["💡 因子可解释性", "📉 衰减跟踪预警", "⚡ GPU加速状态"])
        
        with tab1:
            st.subheader("因子表达式解释")
            interpreter = FactorInterpreter()
            
            for f in st.session_state.factors:
                with st.expander(f"📌 {f['id']} (IC={f['fitness']:.4f})"):
                    interp = interpreter.interpret(f['expression'])
                    
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        st.markdown(f"**原始表达式**")
                        st.code(f['expression'])
                        
                        st.markdown(f"**中文描述**")
                        st.info(interp['readable_description'])
                        
                        if interp['pattern_meanings']:
                            st.markdown(f"**识别的因子模式**")
                            for m in interp['pattern_meanings']:
                                st.markdown(f"- {m}")
                        
                        if interp['factor_types']:
                            st.markdown(f"**因子类型**: {', '.join(interp['factor_types'])}")
                        
                        if interp['warnings']:
                            st.markdown(f"**⚠️ 风险提示**")
                            for w in interp['warnings']:
                                st.warning(w)
                    
                    with col2:
                        s = interp['structure']
                        st.markdown("**结构分析**")
                        st.metric("嵌套深度", s['nesting_depth'])
                        st.metric("算子数量", s['n_operators'])
                        st.metric("特征数量", s['n_features'])
                        st.metric("总复杂度", s['complexity'])
                        
                        if interp['features_used']:
                            st.markdown("**使用特征**")
                            for feat in interp['features_used']:
                                st.markdown(f"- {feat}")
        
        with tab2:
            st.subheader("因子衰减跟踪与失效预警")
            
            if not st.session_state.factor_values:
                st.warning("请先进行因子挖掘！")
            else:
                loader = DataLoader()
                prices, forward_returns = loader.prepare_factor_data(st.session_state.data)
                
                col1, col2 = st.columns(2)
                with col1:
                    ic_warning = st.slider("IC预警阈值", 0.01, 0.10, 0.03, 0.01)
                with col2:
                    ic_critical = st.slider("IC失效阈值", 0.005, 0.05, 0.01, 0.005)
                
                tracker = FactorDecayTracker(
                    ic_warning_threshold=ic_warning,
                    ic_critical_threshold=ic_critical,
                    decay_window=20
                )
                
                if st.button("开始衰减分析"):
                    with st.spinner("正在分析因子衰减..."):
                        reports = tracker.track_factors_batch(
                            st.session_state.factor_names,
                            st.session_state.factor_values,
                            forward_returns
                        )
                        st.session_state.decay_reports = reports
                
                if 'decay_reports' in st.session_state:
                    reports = st.session_state.decay_reports
                    
                    n_invalid = len([r for r in reports if r.status == FactorStatus.INVALID])
                    n_degraded = len([r for r in reports if r.status == FactorStatus.DEGRADED])
                    n_weakening = len([r for r in reports if r.status == FactorStatus.WEAKENING])
                    n_active = len([r for r in reports if r.status == FactorStatus.ACTIVE])
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("✅ 正常因子", n_active)
                    with col2:
                        st.metric("🟡 衰减中", n_weakening)
                    with col3:
                        st.metric("🟠 退化", n_degraded)
                    with col4:
                        st.metric("🔴 失效", n_invalid)
                    
                    if n_invalid > 0 or n_degraded > 0:
                        st.error(f"⚠️ 发现 {n_invalid} 个失效因子和 {n_degraded} 个退化因子，建议替换！")
                    
                    summary = tracker.get_summary(reports)
                    st.dataframe(summary)
                    
                    st.subheader("IC衰减趋势")
                    selected = st.selectbox(
                        "选择因子查看衰减趋势",
                        [r.factor_name for r in reports]
                    )
                    
                    for r in reports:
                        if r.factor_name == selected:
                            rolling_ic = r.rolling_ic
                            if len(rolling_ic) > 0:
                                fig = go.Figure()
                                fig.add_trace(go.Scatter(
                                    x=rolling_ic.index,
                                    y=rolling_ic.values,
                                    mode='lines',
                                    name='滚动IC',
                                    line=dict(color='blue')
                                ))
                                fig.add_hline(y=ic_warning, 
                                    line_dash="dash", line_color="orange",
                                    annotation_text="预警线")
                                fig.add_hline(y=ic_critical,
                                    line_dash="dash", line_color="red",
                                    annotation_text="失效线")
                                fig.add_hline(y=-ic_warning,
                                    line_dash="dash", line_color="orange")
                                fig.add_hline(y=-ic_critical,
                                    line_dash="dash", line_color="red")
                                fig.update_layout(title=f"{selected} IC衰减趋势")
                                st.plotly_chart(fig, use_container_width=True)
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                st.metric("当前IC", f"{r.current_ic:.4f}" if not np.isnan(r.current_ic) else "N/A")
                                st.metric("历史IC", f"{r.historical_ic:.4f}" if not np.isnan(r.historical_ic) else "N/A")
                            with col2:
                                st.metric("IC衰减率", f"{r.ic_decay_rate:.6f}/期")
                                half_life_str = f"{r.ic_half_life:.1f}期" if r.ic_half_life != np.inf else "∞"
                                st.metric("IC半衰期", half_life_str)
                            
                            if r.status != FactorStatus.ACTIVE:
                                st.warning(f"🚨 {r.warning_message}")
                            else:
                                st.success("✅ 因子表现正常")
                            
                            if r.decay_details:
                                st.markdown("**详细指标**")
                                for k, v in r.decay_details.items():
                                    if isinstance(v, float):
                                        st.markdown(f"- {k}: {v:.4f}")
                                    else:
                                        st.markdown(f"- {k}: {v}")
                            break
        
        with tab3:
            st.subheader("⚡ GPU加速状态")
            
            info = get_device_info()
            st.json(info)
            
            if info['gpu_available']:
                st.success(f"GPU已启用: {info.get('gpu_name', 'Unknown')}")
                st.info(f"显存: {info.get('gpu_free_memory_gb', 0):.1f}GB 可用 / {info.get('gpu_memory_gb', 0):.1f}GB 总量")
            else:
                st.info("GPU不可用，当前使用Numba JIT CPU加速模式")
                st.markdown("**安装GPU加速支持**:")
                st.code("pip install cupy-cuda11x  # 根据CUDA版本选择")
                st.code("pip install numba")
            
            if st.session_state.data is not None:
                st.subheader("GPU加速性能对比")
                
                loader = DataLoader()
                prices, forward_returns = loader.prepare_factor_data(st.session_state.data)
                
                if st.button("运行性能基准测试"):
                    test_factor = st.session_state.factor_values[0] if st.session_state.factor_values else None
                    
                    if test_factor is not None:
                        accelerator = AcceleratedFactorOps(use_gpu=True)
                        
                        factor_unstacked = test_factor.unstack(level='asset')
                        data_arr = factor_unstacked.values.astype(np.float32)
                        
                        import time as _time
                        
                        t0 = _time.time()
                        for _ in range(10):
                            for col in range(data_arr.shape[1]):
                                pd.Series(data_arr[:, col]).rolling(5).mean().values
                        cpu_time = _time.time() - t0
                        
                        t0 = _time.time()
                        for _ in range(10):
                            for col in range(data_arr.shape[1]):
                                accelerator.rolling_mean(data_arr[:, col], 5)
                        accel_time = _time.time() - t0
                        
                        speedup = cpu_time / accel_time if accel_time > 0 else 0
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("CPU耗时", f"{cpu_time:.4f}s")
                        with col2:
                            st.metric("加速耗时", f"{accel_time:.4f}s")
                        with col3:
                            st.metric("加速倍数", f"{speedup:.1f}x")
                        
                        fig = go.Figure(go.Bar(
                            x=['CPU (Pandas)', '加速模式'],
                            y=[cpu_time, accel_time],
                            marker_color=['#636EFA', '#EF553B']
                        ))
                        fig.update_layout(title="性能对比: 10轮滚动平均计算")
                        st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    main()
