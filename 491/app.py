import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.data_collector import CloudResourceDataCollector
from src.cost_analyzer import CostAnalyzer
from src.optimizer import CloudOptimizer
from src.forecasting import CostForecaster

st.set_page_config(
    page_title="云资源成本优化推荐引擎",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

def format_currency(value):
    if value >= 1000:
        return f"${value:,.2f}"
    return f"${value:.2f}"

def get_impact_color(impact_score):
    if impact_score < 0.3:
        return "🟢"
    elif impact_score < 0.7:
        return "🟡"
    else:
        return "🔴"

def get_flexibility_badge(score):
    if score >= 0.75:
        return "🟢 高"
    elif score >= 0.5:
        return "🟡 中"
    else:
        return "🔴 低 (按需推荐)"

def main():
    st.title("💰 云资源成本优化推荐引擎")
    st.markdown("---")

    with st.sidebar:
        st.header("⚙️ 设置")
        cloud_provider = st.selectbox("云厂商", ["AWS", "Azure", "GCP"])
        num_instances = st.slider("实例数量", 10, 200, 50)
        forecast_days = st.slider("预测天数", 30, 180, 90)
        
        st.markdown("---")
        st.subheader("📊 高级选项")
        show_multi_granular = st.checkbox("启用多粒度采样分析", True)
        sort_by_impact = st.checkbox("按业务影响度排序", True)
        show_flexibility = st.checkbox("显示灵活性评分", True)
        
        st.markdown("---")
        st.subheader("📊 数据源")
        data_source = st.radio("数据源", ["模拟数据", "上传CSV"])
        
        if data_source == "上传CSV":
            uploaded_file = st.file_uploader("上传成本数据CSV", type="csv")
        else:
            uploaded_file = None
        
        st.markdown("---")
        if st.button("🔄 重新生成数据", type="primary"):
            st.rerun()

    with st.spinner("正在分析云资源数据..."):
        collector = CloudResourceDataCollector(cloud_provider.lower())
        data = collector.get_all_data()
        
        analyzer = CostAnalyzer(data)
        optimizer = CloudOptimizer(data)
        forecaster = CostForecaster(data['historical_costs'])
        all_recs = optimizer.generate_all_recommendations()

    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
        "📊 成本概览", 
        "💡 优化推荐", 
        "🔮 成本预测", 
        "🖥️ 资源分析", 
        "📋 执行计划",
        "📈 高级分析",
        "💰 多云比价",
        "⚠️ 异常检测",
        "📅 预算预测"
    ])

    with tab1:
        st.header("成本概览 Dashboard")
        
        cost_summary = analyzer.get_cost_summary()
        util_analysis = analyzer.analyze_instance_utilization()
        storage_analysis = analyzer.analyze_storage_optimization()
        mg_analysis = optimizer.get_multi_granular_analysis()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="近30天总成本",
                value=format_currency(cost_summary.get('last_30d_cost', 0)),
                delta=f"{cost_summary.get('daily_avg_30d', 0):.2f}/天"
            )
        
        with col2:
            st.metric(
                label="预计月度节省",
                value=format_currency(all_recs['total_monthly_savings']),
                delta="潜在节省"
            )
        
        with col3:
            st.metric(
                label="运行中实例",
                value=util_analysis.get('total_running', 0),
                delta=f"利用率: {util_analysis.get('avg_utilization', 0):.1f}%"
            )
        
        with col4:
            st.metric(
                label="存储总量 (GB)",
                value=f"{storage_analysis.get('total_storage_gb', 0):,.0f}",
                delta=f"未使用: {storage_analysis.get('unused_storage_gb', 0):.0f} GB"
            )
        
        st.markdown("---")
        
        col_chart1, col_chart2 = st.columns([2, 1])
        
        with col_chart1:
            st.subheader("📈 每日成本趋势")
            
            daily_costs = cost_summary.get('daily_costs', pd.Series())
            if not daily_costs.empty:
                fig_daily = px.line(
                    x=daily_costs.index,
                    y=daily_costs.values,
                    title="每日成本",
                    labels={'x': '日期', 'y': '成本 ($)'}
                )
                fig_daily.update_layout(height=350)
                st.plotly_chart(fig_daily, use_container_width=True)
        
        with col_chart2:
            st.subheader("📊 按服务分类")
            
            by_service = cost_summary.get('by_service', {})
            if by_service:
                fig_service = px.pie(
                    names=list(by_service.keys()),
                    values=list(by_service.values()),
                    title="服务成本分布",
                    hole=0.3
                )
                fig_service.update_layout(height=350)
                st.plotly_chart(fig_service, use_container_width=True)

        if show_multi_granular and mg_analysis:
            st.markdown("---")
            st.subheader("🔬 多粒度采样分析")
            
            col_mg1, col_mg2, col_mg3, col_mg4 = st.columns(4)
            
            peak_features = mg_analysis.get('peak_features', {})
            
            with col_mg1:
                st.metric("总采样点", mg_analysis.get('total_samples', 0))
            
            with col_mg2:
                st.metric("峰值点数量", mg_analysis.get('peak_count', 0))
            
            with col_mg3:
                st.metric("峰值/均值比", f"{peak_features.get('peak_mean_ratio', 0):.2f}x")
            
            with col_mg4:
                burst_score = peak_features.get('burst_score', 0)
                st.metric("突增评分", f"{burst_score:.2f}")
            
            if burst_score > 0.5:
                st.warning("⚠️ 检测到高突增模式，使用按需计费可能更优")

        st.markdown("---")
        st.subheader("🔍 关键洞察")
        
        insights = analyzer.generate_cost_insights()
        
        for insight in insights:
            severity_colors = {
                'high': '🔴',
                'medium': '🟡',
                'low': '🟢'
            }
            type_emoji = {
                'danger': '🔴',
                'warning': '🟡',
                'success': '🟢',
                'info': '🔵'
            }
            
            with st.expander(
                f"{type_emoji.get(insight['type'], 'ℹ️')} {insight['title']} | 影响: {insight['impact']}"
            ):
                st.write(insight['description'])
                st.caption(f"类别: {insight['category']} | 严重程度: {severity_colors.get(insight['severity'], '')} {insight['severity']}")

    with tab2:
        st.header("优化推荐")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="月度潜在节省",
                value=format_currency(all_recs['total_monthly_savings']),
                delta=f"年度: {format_currency(all_recs['total_annual_savings'])}"
            )
        
        with col2:
            st.metric(
                label="推荐数量",
                value=len(all_recs['all_recommendations']),
                delta=f"{len(all_recs['quick_wins'])} 快速胜利"
            )
        
        with col3:
            roi = optimizer.calculate_roi(all_recs['all_recommendations'])
            st.metric(
                label="投资回收期",
                value=roi['payback_period'],
                delta=f"ROI: {roi['first_year_net_savings']:,.0f} 净节省"
            )
        
        with col4:
            avg_flex = roi.get('avg_flexibility_score', 0)
            st.metric(
                label="平均灵活性评分",
                value=f"{avg_flex:.2f}",
                delta="高=适合RI/SP"
            )
        
        st.markdown("---")
        
        col_filter1, col_filter2 = st.columns(2)
        
        with col_filter1:
            rec_type = st.selectbox(
                "筛选推荐类型",
                ["全部", "终止资源", "实例降配", "存储优化", "预留实例", "节省计划"]
            )
        
        with col_filter2:
            impact_filter = st.selectbox(
                "按业务影响筛选",
                ["全部", "低影响优先", "中影响", "高影响"]
            )
        
        if rec_type == "终止资源":
            display_recs = all_recs['by_type']['terminate']
        elif rec_type == "实例降配":
            display_recs = all_recs['by_type']['downsize']
        elif rec_type == "存储优化":
            display_recs = all_recs['by_type']['storage']
        elif rec_type == "预留实例":
            display_recs = all_recs['by_type']['reserve']
        elif rec_type == "节省计划":
            display_recs = all_recs['by_type'].get('savings_plan', [])
        else:
            display_recs = all_recs['all_recommendations']
        
        if impact_filter == "低影响优先":
            display_recs = [r for r in display_recs if r.business_impact_score < 0.3]
        elif impact_filter == "中影响":
            display_recs = [r for r in display_recs if 0.3 <= r.business_impact_score < 0.7]
        elif impact_filter == "高影响":
            display_recs = [r for r in display_recs if r.business_impact_score >= 0.7]
        
        st.subheader(f"📋 推荐列表 ({len(display_recs)} 条)")
        
        for i, rec in enumerate(display_recs[:20]):
            impact_badge = get_impact_color(rec.business_impact_score)
            flex_badge = get_flexibility_badge(rec.flexibility_score)
            
            with st.expander(
                f"#{i+1} | {rec.resource_name} | 节省: {format_currency(rec.monthly_savings)} | 优先级: {rec.priority_score:.3f}"
            ):
                col_a, col_b, col_c = st.columns(3)
                
                with col_a:
                    st.write("**资源信息**")
                    st.write(f"- 资源ID: {rec.resource_id}")
                    st.write(f"- 资源类型: {rec.resource_type}")
                    st.write(f"- 风险等级: {rec.risk_level}")
                    st.write(f"- 实施难度: {rec.effort_level}")
                
                with col_b:
                    st.write("**评分指标**")
                    st.write(f"- 业务影响: {impact_badge} {rec.business_impact} ({rec.business_impact_score:.2f})")
                    st.write(f"- 灵活性评分: {flex_badge} ({rec.flexibility_score:.2f})")
                    st.write(f"- 置信度: {rec.confidence_score:.0%}")
                    st.write(f"- 优先级分: {rec.priority_score:.3f}")
                
                with col_c:
                    st.write("**当前配置**")
                    for k, v in rec.current_config.items():
                        st.write(f"- {k}: {v}")
                    if rec.recommended_config:
                        st.write("**推荐配置**")
                        for k, v in rec.recommended_config.items():
                            st.write(f"- {k}: {v}")
                
                st.write("**描述:**")
                st.info(rec.description)
                
                st.write("**实施步骤:**")
                for step in rec.action_steps:
                    st.text(step)
                
                if rec.peak_metrics:
                    st.write("**峰值指标:**")
                    st.json(rec.peak_metrics)

    with tab3:
        st.header("成本预测")
        
        forecast_summary = forecaster.generate_forecast_summary(periods=forecast_days)
        forecast_result = forecast_summary['forecast']
        run_rate = forecast_summary['run_rate']
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                label="月度运行率",
                value=format_currency(run_rate.get('monthly_run_rate', 0)),
                delta=f"环比: {run_rate.get('mom_change_pct', 0):+.1f}%"
            )
        
        with col2:
            st.metric(
                label="年度运行率",
                value=format_currency(run_rate.get('annual_run_rate', 0)),
                delta=f"基于近30天"
            )
        
        with col3:
            st.metric(
                label="预测方法",
                value=forecast_result.get('method', 'N/A'),
                delta=f"准确率: {forecast_result.get('accuracy', 0):.1f}%"
            )
        
        st.markdown("---")
        
        st.subheader("📉 成本预测图表")
        
        if 'forecast_dates' in forecast_result and len(forecast_result['forecast_dates']) > 0:
            fig_forecast = go.Figure()
            
            fig_forecast.add_trace(go.Scatter(
                x=forecast_result['historical_dates'],
                y=forecast_result['historical_values'],
                mode='lines',
                name='历史数据',
                line=dict(color='blue')
            ))
            
            fig_forecast.add_trace(go.Scatter(
                x=forecast_result['forecast_dates'],
                y=forecast_result['forecast_values'],
                mode='lines',
                name='预测值',
                line=dict(color='red', dash='dash')
            ))
            
            if 'forecast_lower' in forecast_result and 'forecast_upper' in forecast_result:
                fig_forecast.add_trace(go.Scatter(
                    x=list(forecast_result['forecast_dates']) + list(reversed(forecast_result['forecast_dates'])),
                    y=list(forecast_result['forecast_upper']) + list(reversed(forecast_result['forecast_lower'])),
                    fill='toself',
                    fillcolor='rgba(255,0,0,0.1)',
                    line=dict(color='rgba(255,255,255,0)'),
                    name='置信区间'
                ))
            
            fig_forecast.update_layout(
                title='成本趋势预测',
                xaxis_title='日期',
                yaxis_title='成本 ($)',
                height=500,
                hovermode='x unified'
            )
            
            st.plotly_chart(fig_forecast, use_container_width=True)
        
        st.markdown("---")
        
        col_a, col_b = st.columns(2)
        
        with col_a:
            st.subheader("🔔 异常检测")
            anomalies = forecast_summary['anomalies']
            st.write(f"检测到 **{anomalies['total_anomalies']}** 个异常点")
            st.write(f"- 成本突增: {anomalies['spikes']} 次")
            st.write(f"- 成本突降: {anomalies['drops']} 次")
            
            if 'anomalies' in anomalies and not anomalies['anomalies'].empty and len(anomalies['anomalies']) > 0:
                st.dataframe(anomalies['anomalies'][['ds', 'y', 'type', 'z_score']])
        
        with col_b:
            st.subheader("📊 按服务预测")
            service_forecasts = forecaster.forecast_by_service()
            
            for service, data in service_forecasts.items():
                st.write(f"**{service}**")
                st.write(f"- 预测月度: {format_currency(data['total_forecast'])}")
                st.write(f"- 历史平均: {format_currency(data['historical_avg'])}/天")

    with tab4:
        st.header("资源分析")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🖥️ 实例利用率分析")
            
            util_df = util_analysis.get('instances', pd.DataFrame())
            if not util_df.empty:
                fig_util = px.scatter(
                    util_df,
                    x='avg_cpu_7d',
                    y='avg_memory_7d',
                    size='ondemand_cost_30d',
                    color='utilization_category',
                    hover_data=['name', 'instance_type', 'environment'],
                    title='CPU vs 内存利用率'
                )
                fig_util.update_layout(height=400)
                st.plotly_chart(fig_util, use_container_width=True)
        
        with col2:
            st.subheader("💾 存储分析")
            
            storage_by_type = storage_analysis.get('by_type', {})
            if storage_by_type:
                storage_df = pd.DataFrame([
                    {'类型': k, '大小(GB)': v['size_gb'], '成本': v['monthly_cost'], '数量': v['count']}
                    for k, v in storage_by_type.items()
                ])
                
                fig_storage = px.bar(
                    storage_df,
                    x='类型',
                    y='大小(GB)',
                    color='类型',
                    title='EBS卷类型分布',
                    text_auto=True
                )
                st.plotly_chart(fig_storage, use_container_width=True)
        
        st.markdown("---")
        
        st.subheader("📋 未充分利用的实例")
        
        underutilized = util_analysis.get('underutilized_instances', pd.DataFrame())
        if not underutilized.empty:
            display_cols = ['instance_id', 'name', 'instance_type', 'environment', 
                          'avg_cpu_7d', 'avg_memory_7d', 'ondemand_cost_30d']
            st.dataframe(
                underutilized[display_cols].style.format({
                    'avg_cpu_7d': '{:.1f}%',
                    'avg_memory_7d': '{:.1f}%',
                    'ondemand_cost_30d': '${:.2f}'
                }),
                use_container_width=True
            )
        else:
            st.success("✅ 没有发现未充分利用的实例！")
        
        st.markdown("---")
        
        st.subheader("📊 按环境分类")
        env_util = util_analysis.get('utilization_by_env', {})
        if env_util:
            env_df = pd.DataFrame({
                '环境': list(env_util.keys()),
                '平均利用率': list(env_util.values())
            })
            fig_env = px.bar(
                env_df,
                x='环境',
                y='平均利用率',
                color='环境',
                title='各环境平均利用率'
            )
            st.plotly_chart(fig_env, use_container_width=True)

    with tab5:
        st.header("执行计划")
        
        all_recommendations = all_recs['all_recommendations']
        execution_plan = optimizer.generate_execution_plan(all_recommendations)
        
        st.subheader("🎯 分阶段实施计划 (按业务影响排序)")
        
        phases = [
            ('立即执行 (0-7天)', execution_plan['immediate'], '#4CAF50'),
            ('短期计划 (1-4周)', execution_plan['short_term'], '#FF9800'),
            ('长期规划 (1-3月)', execution_plan['long_term'], '#f44336'),
        ]
        
        for phase_name, phase_data, color in phases:
            with st.expander(f"{phase_name} | 节省: {format_currency(phase_data['monthly_savings'])}/月 | 平均影响: {phase_data['avg_impact_score']:.2f}"):
                st.info(phase_data['description'])
                st.write(f"**推荐数量:** {len(phase_data['items'])}")
                st.write(f"**月度节省:** {format_currency(phase_data['monthly_savings'])}")
                
                for item in phase_data['items'][:10]:
                    st.write(f"- {item.resource_name}: {format_currency(item.monthly_savings)}/月 | 影响分: {item.business_impact_score:.2f}")
        
        st.markdown("---")
        
        st.subheader("🚀 快速胜利 (低投入高回报)")
        
        quick_wins = all_recs.get('quick_wins', [])
        if quick_wins:
            for win in quick_wins[:5]:
                col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                with col1:
                    st.write(f"**{win.resource_name}**")
                    st.caption(win.description)
                with col2:
                    st.metric("月度节省", format_currency(win.monthly_savings))
                with col3:
                    st.metric("影响分", f"{win.business_impact_score:.2f}")
                with col4:
                    st.button("执行", key=f"exec_{win.resource_id}")
        
        st.markdown("---")
        
        st.subheader("📈 优化路线图")
        
        roadmap_data = pd.DataFrame({
            '阶段': ['第1周', '第2周', '第3周', '第4周', '第2月', '第3月'],
            '累计节省': [
                execution_plan['immediate']['monthly_savings'],
                execution_plan['immediate']['monthly_savings'] * 2,
                execution_plan['immediate']['monthly_savings'] * 3,
                execution_plan['immediate']['monthly_savings'] * 4,
                execution_plan['immediate']['monthly_savings'] * 4 + execution_plan['short_term']['monthly_savings'],
                all_recs['total_monthly_savings'],
            ]
        })
        
        fig_roadmap = px.line(
            roadmap_data,
            x='阶段',
            y='累计节省',
            markers=True,
            title='优化实施路线图 - 累计月度节省',
            text='累计节省'
        )
        fig_roadmap.update_traces(textposition='top center', texttemplate='%{text:$,.0f}')
        st.plotly_chart(fig_roadmap, use_container_width=True)

    with tab6:
        st.header("📈 高级分析")
        
        st.subheader("📊 多粒度采样与峰值分析")
        
        if mg_analysis:
            col_p1, col_p2, col_p3 = st.columns(3)
            
            peak_features = mg_analysis.get('peak_features', {})
            
            with col_p1:
                st.metric("P99 峰值", format_currency(peak_features.get('peak_99th', 0)))
            
            with col_p2:
                st.metric("P95 峰值", format_currency(peak_features.get('peak_95th', 0)))
            
            with col_p3:
                volatility = peak_features.get('volatility', 0)
                st.metric("波动性", f"{volatility:.2%}")
            
            st.markdown("**按粒度分布**")
            sample_dist = mg_analysis.get('samples_by_granularity', {})
            dist_df = pd.DataFrame({
                '粒度': list(sample_dist.keys()),
                '样本数': list(sample_dist.values())
            })
            st.bar_chart(dist_df.set_index('粒度'))
            
            if peak_features.get('burst_score', 0) > 0.5:
                st.warning("⚠️ **高突增模式检测**")
                st.write("检测到显著的负载突增模式，这表明：")
                st.write("- 工作负载具有高度可变性")
                st.write("- 建议使用按需实例或无服务器架构")
                st.write("- 预留实例可能不划算")
                st.write("- 考虑使用 Savings Plans 获得更大的灵活性")

        st.markdown("---")
        
        st.subheader("💡 购买建议分析")
        
        col_f1, col_f2 = st.columns(2)
        
        with col_f1:
            st.write("**按业务影响分布**")
            impact_dist = {
                '低影响': len(all_recs['by_business_impact']['low']),
                '中影响': len(all_recs['by_business_impact']['medium']),
                '高影响': len(all_recs['by_business_impact']['high']),
            }
            fig_impact = px.pie(
                names=list(impact_dist.keys()),
                values=list(impact_dist.values()),
                title='推荐按业务影响分布'
            )
            st.plotly_chart(fig_impact, use_container_width=True)
        
        with col_f2:
            st.write("**灵活性评分分析**")
            flex_scores = [r.flexibility_score for r in all_recs['all_recommendations']]
            flex_df = pd.DataFrame({
                '灵活性评分': flex_scores
            })
            fig_flex = px.histogram(
                flex_df,
                x='灵活性评分',
                nbins=10,
                title='灵活性评分分布'
            )
            st.plotly_chart(fig_flex, use_container_width=True)
        
        low_flex = all_recs.get('low_flexibility_recommendations', [])
        if low_flex:
            st.markdown("---")
            st.subheader("⚠️ 低灵活性资源 (建议按需计费)")
            
            for rec in low_flex:
                st.warning(f"{rec.resource_name}: 灵活性评分 {rec.flexibility_score:.2f} - {rec.description}")

        st.markdown("---")
        
        st.download_button(
            label="📥 下载完整报告",
            data="优化报告内容...",
            file_name="cloud_cost_optimization_report.csv",
            mime="text/csv"
        )

    with tab7:
        st.header("💰 多云比价推荐")
        st.markdown("实时对比AWS、Azure、GCP三大云厂商的实例价格")
        
        col_compare1, col_compare2 = st.columns(2)
        
        with col_compare1:
            compare_mode = st.radio("比价模式", ["批量比价", "实例规格比价", "自定义配置"])
        
        with col_compare2:
            if compare_mode == "实例规格比价":
                instance_type = st.selectbox(
                    "选择实例类型",
                    ["t2.medium", "t2.large", "m5.large", "m5.xlarge", "c5.xlarge", "r5.large"]
                )
                price_result = optimizer.get_cloud_price_comparison(instance_type=instance_type)
            elif compare_mode == "自定义配置":
                vcpu = st.slider("vCPU数量", 1, 64, 4)
                memory = st.slider("内存(GB)", 1, 256, 16)
                price_result = optimizer.get_cloud_price_comparison(vcpu=vcpu, memory=memory)
            else:
                price_result = optimizer.get_cloud_price_comparison()
        
        if compare_mode == "批量比价":
            st.subheader("📊 批量比价结果")
            
            batch_data = price_result.get('batch_comparisons', [])
            total_savings = price_result.get('total_potential_annual_savings', 0)
            current_cloud = price_result.get('current_cloud', 'aws').upper()
            
            col_m1, col_m2, col_m3 = st.columns(3)
            
            with col_m1:
                st.metric("当前云厂商", current_cloud)
            
            with col_m2:
                st.metric("分析实例数", len(batch_data))
            
            with col_m3:
                st.metric(
                    "潜在年度节省",
                    format_currency(total_savings),
                    delta=f"{total_savings / (all_recs['total_monthly_savings'] * 12) * 100:.1f}% vs 优化节省"
                )
            
            st.markdown("---")
            
            if batch_data:
                compare_df = pd.DataFrame([
                    {
                        '实例类型': c.instance_type,
                        '当前价格($/月)': round(c.current_price, 2),
                        '最优厂商': c.best_cloud.upper(),
                        '最优价格($/月)': round(c.best_price, 2),
                        '月节省($)': round(c.monthly_savings, 2),
                        '差价(%)': f"{c.price_difference_pct:.1f}%",
                        '迁移复杂度': c.migration_complexity
                    }
                    for c in batch_data
                ])
                
                st.dataframe(
                    compare_df.style.format({
                        '当前价格($/月)': '${:,.2f}',
                        '最优价格($/月)': '${:,.2f}',
                        '月节省($)': '${:,.2f}'
                    }).background_gradient(subset=['月节省($)'], cmap='Greens'),
                    use_container_width=True
                )
            
            st.markdown("---")
            st.subheader("💡 迁移建议")
            
            high_savings = [c for c in batch_data if c.price_difference_pct > 15]
            medium_savings = [c for c in batch_data if 5 < c.price_difference_pct <= 15]
            
            if high_savings:
                st.success(f"✅ 发现 {len(high_savings)} 个实例有超过15%的节省空间，建议优先考虑迁移")
            if medium_savings:
                st.info(f"ℹ️ 发现 {len(medium_savings)} 个实例有5-15%的节省空间，可作为备选迁移对象")
        
        elif compare_mode == "实例规格比价" and 'comparison' in price_result:
            comparison = price_result['comparison']
            price_matrix = price_result['price_matrix']
            
            col_detail1, col_detail2, col_detail3, col_detail4 = st.columns(4)
            
            with col_detail1:
                st.metric(
                    "当前价格",
                    format_currency(comparison.current_price) + "/月",
                    delta=comparison.current_cloud.upper()
                )
            
            with col_detail2:
                st.metric(
                    "最优价格",
                    format_currency(comparison.best_price) + "/月",
                    delta=comparison.best_cloud.upper(),
                    delta_color="normal"
                )
            
            with col_detail3:
                st.metric(
                    "月节省",
                    format_currency(comparison.monthly_savings),
                    delta=f"{comparison.price_difference_pct:.1f}%"
                )
            
            with col_detail4:
                st.metric(
                    "迁移复杂度",
                    comparison.migration_complexity,
                    delta=f"{comparison.migration_effort_months:.1f}月"
                )
            
            st.markdown("---")
            st.subheader("📋 各厂商价格对比")
            st.dataframe(price_matrix, use_container_width=True)
            
            st.markdown("---")
            st.subheader("🔄 对等实例映射")
            eq_df = pd.DataFrame([
                {'厂商': k.upper(), '对等实例': v}
                for k, v in comparison.equivalent_instances.items()
            ])
            st.table(eq_df)
        
        elif compare_mode == "自定义配置":
            st.subheader("📊 规格价格矩阵")
            st.dataframe(price_result['price_matrix'], use_container_width=True)
            
            st.info(f"💡 提示：以上为 {vcpu} vCPU / {memory} GB 内存规格在各云厂商的近似价格对比")

    with tab8:
        st.header("⚠️ 成本异常检测")
        st.markdown("自动检测成本突增/突降并归因分析")
        
        col_anomaly1, col_anomaly2 = st.columns(2)
        
        with col_anomaly1:
            anomaly_threshold = st.slider("异常阈值(%)", 10, 100, 20, 5) / 100
        
        with col_anomaly2:
            show_spikes_only = st.checkbox("仅显示突增异常", True)
        
        anomaly_result = optimizer.detect_cost_anomalies(threshold=anomaly_threshold)
        anomalies = anomaly_result.get('anomalies', [])
        anomaly_summary = anomaly_result.get('summary', {})
        
        if show_spikes_only:
            anomalies = [a for a in anomalies if a.anomaly_type == 'spike']
        
        col_sum1, col_sum2, col_sum3, col_sum4 = st.columns(4)
        
        with col_sum1:
            st.metric("检测到异常", anomaly_summary.get('total', 0))
        
        with col_sum2:
            st.metric("严重/高危", f"{anomaly_summary.get('critical_count', 0)}/{anomaly_summary.get('high_count', 0)}")
        
        with col_sum3:
            st.metric("突增异常", anomaly_summary.get('by_type', {}).get('spike', 0))
        
        with col_sum4:
            st.metric("预估影响金额", format_currency(anomaly_summary.get('estimated_impact', 0)))
        
        st.markdown("---")
        
        if anomalies:
            st.subheader("🔍 异常详情")
            
            for i, anomaly in enumerate(anomalies[:10]):
                severity_color = {
                    'Critical': '🔴',
                    'High': '🟠',
                    'Medium': '🟡',
                    'Low': '🟢'
                }.get(anomaly.severity, '⚪')
                
                with st.expander(
                    f"{severity_color} #{i+1} | {anomaly.timestamp.strftime('%Y-%m-%d')} | {anomaly.service} | {anomaly.deviation_pct:+.1%}"
                ):
                    col_a1, col_a2, col_a3 = st.columns(3)
                    
                    with col_a1:
                        st.write("**异常信息**")
                        st.write(f"- 时间: {anomaly.timestamp.strftime('%Y-%m-%d')}")
                        st.write(f"- 服务: {anomaly.service}")
                        st.write(f"- 区域: {anomaly.region}")
                        st.write(f"- 类型: {'📈 成本突增' if anomaly.anomaly_type == 'spike' else '📉 成本突降'}")
                        st.write(f"- 严重程度: {severity_color} {anomaly.severity}")
                    
                    with col_a2:
                        st.write("**成本分析**")
                        st.write(f"- 实际成本: {format_currency(anomaly.actual_cost)}")
                        st.write(f"- 预期成本: {format_currency(anomaly.expected_cost)}")
                        st.write(f"- 偏差金额: {format_currency(anomaly.actual_cost - anomaly.expected_cost)}")
                        st.write(f"- 偏差比例: {anomaly.deviation_pct:+.1%}")
                    
                    with col_a3:
                        st.write("**归因分析**")
                        st.write(f"- 置信度: {anomaly.root_cause_confidence:.0%}")
                        st.write(f"- 根因: {anomaly.root_cause}")
                    
                    if anomaly.contributing_factors:
                        st.write("**影响因素:**")
                        for factor in anomaly.contributing_factors:
                            st.info(f"- {factor['factor']}: {factor['impact']}")
                    
                    st.write("**建议行动:**")
                    st.success(f"💡 {anomaly.recommended_action}")
        else:
            st.success("✅ 未检测到显著的成本异常")
        
        st.markdown("---")
        st.subheader("📈 异常趋势图")
        
        if 'historical_costs' in data and not data['historical_costs'].empty:
            daily_costs = data['historical_costs'].groupby('date')['cost'].sum()
            
            fig_anomaly = go.Figure()
            fig_anomaly.add_trace(go.Scatter(
                x=daily_costs.index,
                y=daily_costs.values,
                mode='lines+markers',
                name='每日成本',
                line=dict(color='blue')
            ))
            
            for anomaly in anomalies[:5]:
                fig_anomaly.add_annotation(
                    x=anomaly.timestamp,
                    y=anomaly.actual_cost,
                    text=f"{anomaly.deviation_pct:+.0%}",
                    showarrow=True,
                    arrowhead=1,
                    ax=0,
                    ay=-40,
                    bgcolor="red" if anomaly.anomaly_type == 'spike' else "green",
                    font=dict(color="white")
                )
            
            fig_anomaly.update_layout(
                title='每日成本趋势与异常标记',
                xaxis_title='日期',
                yaxis_title='成本 ($)',
                height=400
            )
            st.plotly_chart(fig_anomaly, use_container_width=True)

    with tab9:
        st.header("📅 预算预测与风险评估")
        st.markdown("预估年度成本趋势和超预算风险")
        
        col_budget1, col_budget2 = st.columns(2)
        
        with col_budget1:
            annual_budget = st.number_input(
                "年度预算 ($)",
                min_value=0,
                value=120000,
                step=10000
            )
        
        with col_budget2:
            forecast_months = st.slider("预测月数", 3, 24, 12)
        
        forecast_scenario = st.selectbox(
            "增长情景",
            ["保守 (5%)", "中等 (10%)", "激进 (20%)"],
            index=1
        )
        
        scenario_map = {
            "保守 (5%)": "conservative",
            "中等 (10%)": "moderate",
            "激进 (20%)": "aggressive"
        }
        
        budget_result = optimizer.forecast_budget(
            annual_budget=annual_budget,
            forecast_months=forecast_months
        )
        
        if 'error' in budget_result:
            st.error(budget_result['error'])
        else:
            forecast = budget_result['forecast']
            scenarios = budget_result['scenarios']
            alert_thresholds = budget_result['alert_thresholds']
            
            risk_color = {
                'Critical': '🔴',
                'High': '🟠',
                'Medium': '🟡',
                'Low': '🟢'
            }.get(forecast.risk_level, '⚪')
            
            col_f1, col_f2, col_f3, col_f4 = st.columns(4)
            
            with col_f1:
                st.metric(
                    "年度预算",
                    format_currency(forecast.budget_amount),
                    delta="设定值"
                )
            
            with col_f2:
                st.metric(
                    "预测成本",
                    format_currency(forecast.projected_cost),
                    delta=f"{forecast.budget_variance_pct:+.1%}",
                    delta_color="inverse"
                )
            
            with col_f3:
                st.metric(
                    "预算差额",
                    format_currency(forecast.budget_variance),
                    delta="超支" if forecast.budget_variance > 0 else "节省"
                )
            
            with col_f4:
                st.metric(
                    "超预算风险",
                    f"{risk_color} {forecast.risk_level}",
                    delta=f"{forecast.over_budget_risk:.0%}"
                )
            
            st.markdown("---")
            
            col_chart_b1, col_chart_b2 = st.columns([2, 1])
            
            with col_chart_b1:
                st.subheader("📈 月度成本预测")
                
                forecast_df = forecast.monthly_forecast.copy()
                
                fig_forecast = go.Figure()
                
                fig_forecast.add_trace(go.Scatter(
                    x=forecast_df['date'],
                    y=forecast_df['projected_cost'],
                    mode='lines+markers',
                    name='预测成本',
                    line=dict(color='blue', width=2)
                ))
                
                fig_forecast.add_trace(go.Scatter(
                    x=list(forecast_df['date']) + list(reversed(forecast_df['date'])),
                    y=list(forecast_df['upper_bound']) + list(reversed(forecast_df['lower_bound'])),
                    fill='toself',
                    fillcolor='rgba(0,100,255,0.2)',
                    line=dict(color='rgba(255,255,255,0)'),
                    name='预测区间'
                ))
                
                fig_forecast.add_hline(
                    y=annual_budget / 12,
                    line_dash="dash",
                    line_color="red",
                    annotation_text="月度预算线"
                )
                
                fig_forecast.update_layout(
                    title='月度成本预测趋势',
                    xaxis_title='月份',
                    yaxis_title='成本 ($)',
                    height=400,
                    hovermode='x unified'
                )
                st.plotly_chart(fig_forecast, use_container_width=True)
            
            with col_chart_b2:
                st.subheader("📊 多情景对比")
                
                scenario_data = []
                for name, sc in scenarios.items():
                    scenario_data.append({
                        '情景': name.capitalize(),
                        '预测成本': sc.projected_cost,
                        '预算差额': sc.budget_variance,
                        '风险等级': sc.risk_level
                    })
                
                scenario_df = pd.DataFrame(scenario_data)
                st.dataframe(
                    scenario_df.style.format({
                        '预测成本': '${:,.2f}',
                        '预算差额': '${:,.2f}'
                    }),
                    use_container_width=True
                )
            
            st.markdown("---")
            
            col_driver1, col_driver2 = st.columns(2)
            
            with col_driver1:
                st.subheader("🔑 关键成本驱动因素")
                
                if forecast.key_drivers:
                    for driver in forecast.key_drivers:
                        impact_emoji = '🔴' if driver['impact'] == 'high' else '🟡'
                        with st.expander(
                            f"{impact_emoji} {driver['service']} | {driver['change_pct']:+.1%} | 占比 {driver['contribution_pct']:.0%}"
                        ):
                            st.write(f"- 当前成本: {format_currency(driver['current_cost'])}")
                            st.write(f"- 前期成本: {format_currency(driver['previous_cost'])}")
                            st.write(f"- 变化幅度: {driver['change_pct']:+.1%}")
                            st.write(f"- 成本占比: {driver['contribution_pct']:.0%}")
                            st.write(f"- 影响程度: {driver['impact'].upper()}")
                else:
                    st.info("ℹ️ 暂无足够数据识别关键驱动因素")
            
            with col_driver2:
                st.subheader("💡 风险缓解建议")
                
                for i, rec in enumerate(forecast.mitigation_recommendations, 1):
                    st.info(f"{i}. {rec}")
                
                st.markdown("---")
                st.subheader("🚨 预算预警阈值")
                
                threshold_df = pd.DataFrame([
                    {'预警级别': '75% 警告', '金额($)': alert_thresholds['warning_75']},
                    {'预警级别': '90% 提醒', '金额($)': alert_thresholds['alert_90']},
                    {'预警级别': '100% 临界', '金额($)': alert_thresholds['critical_100']},
                    {'预警级别': '110% 超支', '金额($)': alert_thresholds['overage_110']},
                ])
                
                st.dataframe(
                    threshold_df.style.format({'金额($)': '${:,.2f}'}),
                    use_container_width=True
                )

if __name__ == "__main__":
    main()
