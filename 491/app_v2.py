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
        return "🔴 低 (按需推荐"

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

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 成本概览", 
        "💡 优化推荐", 
        "🔮 成本预测", 
        "🖥️ 资源分析", 
        "📋 执行计划",
        "📈 高级分析"
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
                st.warning("⚠️ 检测到高突增模式，建议使用按需计费可能更优")

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
                value=len(all_recs['all_recommendations'])),
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
                value=forecast_result.get('method', 'N/A')],
                delta=f"准确率: {forecast_result.get('accuracy', 0):.1f}%"
            )
        
        st.markdown("---")
        
        st.subheader("📉 成本预测图表")
        
        if 'forecast_dates' in forecast_result and len(forecast_result['forecast_dates']) > 0:
            fig_forecast = go.Figure()
            
            fig_forecast.add_trace(go.Scatter(
                x=forecast_result['historical_dates']),
                y=forecast_result['historical_values']),
                mode='lines',
                name='历史数据',
                line=dict(color='blue')
            ))
            
            fig_forecast.add_trace(go.Scatter(
                x=forecast_result['forecast_dates']),
                y=forecast_result['forecast_values']),
                mode='lines',
                name='预测值',
                line=dict(color='red', dash='dash')
            ))
            
            if 'forecast_lower' in forecast_result and 'forecast_upper' in forecast_result:
                fig_forecast.add_trace(go.Scatter(
                    x=list(forecast_result['forecast_dates']) + list(reversed(forecast_result['forecast_dates']))),
                    y=list(forecast_result['forecast_upper']) + list(reversed(forecast_result['forecast_lower']))),
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
                    x='avg_cpu_7d'),
                    y='avg_memory_7d'),
                    size='ondemand_cost_30d'),
                    color='utilization_category'),
                    hover_data=['name', 'instance_type', 'environment']),
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
                    x='类型'),
                    y='大小(GB)'),
                    color='类型'),
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
                    'avg_cpu_7d': '{:.1f}%'),
                    'avg_memory_7d': '{:.1f}%'),
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
                '环境': list(env_util.keys())),
                '平均利用率': list(env_util.values())
            })
            fig_env = px.bar(
                env_df,
                x='环境'),
                y='平均利用率'),
                color='环境'),
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
                st.write(f"**月度节省:** {format_currency(phase_data['monthly_savings'])})
                
                for item in phase_data['items'][:10]:
                    st.write(f"- {item.resource_name}: {format_currency(item.monthly_savings'])}/月 | 影响分: {item.business_impact_score:.2f}")
        
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
                    st.metric("月度节省", format_currency(win.monthly_savings]))
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
            x='阶段'),
            y='累计节省'),
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
            
            st.markdown("**按粒度分布:")
            sample_dist = mg_analysis.get('samples_by_granularity', {})
            dist_df = pd.DataFrame({
                '粒度': list(sample_dist.keys())),
                '样本数': list(sample_dist.values())
            })
            st.bar_chart(dist_df.set_index('粒度'))
            
            if peak_features.get('burst_score', 0) > 0.5:
                st.warning("⚠️ **高突增模式检测**")
                st.write("检测到显著的负载突增模式，这表明：")
                st.write("- 工作负载具有高度可变")
                st.write("- 建议使用按需实例或无服务器架构")
                st.write("- 预留实例可能不划算")
                st.write("- 考虑使用 Savings Plans 获得更大的灵活性")

        st.markdown("---")
        
        st.subheader("💡 购买建议分析")
        
        col_f1, col_f2 = st.columns(2)
        
        with col_f1:
            st.write("**按业务影响分布")
            impact_dist = {
                '低影响': len(all_recs['by_business_impact']['low']),
                '中影响': len(all_recs['by_business_impact']['medium']),
                '高影响': len(all_recs['by_business_impact']['high']),
            }
            fig_impact = px.pie(
                names=list(impact_dist.keys())),
                values=list(impact_dist.values())),
                title='推荐按业务影响分布'
            )
            st.plotly_chart(fig_impact, use_container_width=True)
        
        with col_f2:
            st.write("**灵活性评分分析**")
            flex_scores = [r.flexibility_score for r in all_recs['all_recommendations']
            flex_df = pd.DataFrame({
                '灵活性评分': flex_scores
            })
            fig_flex = px.histogram(
                flex_df,
                x='灵活性评分'),
                nbins=10,
                title='灵活性评分分布'
            )
            st.plotly_chart(fig_flex, use_container_width=True)
        
        low_flex = all_recs.get('low_flexibility_recommendations', [])
        if low_flex:
            st.markdown("---")
            st.subheader("⚠️ 低灵活性资源 (建议按需计费")
            
            for rec in low_flex:
                st.warning(f"{rec.resource_name}: 灵活性评分 {rec.flexibility_score:.2f} - {rec.description}")

        st.markdown("---")
        
        st.download_button(
            label="📥 下载完整报告",
            data="优化报告内容...",
            file_name="cloud_cost_optimization_report.csv",
            mime="text/csv"
        )

if __name__ == "__main__":
    main()
