import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from streamlit_echarts import st_pyecharts
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import APP_TITLE, APP_ICON
from database.clickhouse_client import ClickHouseClient
from analytics.path_analyzer import PathAnalyzer
from analytics.funnel_analyzer import FunnelAnalyzer
from analytics.churn_analyzer import ChurnAnalyzer
from analytics.path_predictor import MarkovChainPredictor
from analytics.anomaly_detector import AnomalyDetector, AnomalyType
from analytics.attribution_analyzer import AttributionAnalyzer
from analytics.advanced_sankey import AdvancedSankeyAnalyzer
from analytics.dynamic_segmentation import DynamicSegmentation, Segment, SegmentCondition, DimensionType, Operator
from visualization.sankey_chart import SankeyChart
from visualization.funnel_chart import FunnelChart
from visualization.charts import PathCharts
from data_generator import SampleDataGenerator

st.set_page_config(
    page_title=APP_TITLE,
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main > div {
        padding-top: 2rem;
    }
    .stMetric {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
    }
    .segment-card {
        background-color: #ffffff;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #5470c6;
        margin-bottom: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def get_db_client():
    try:
        return ClickHouseClient()
    except Exception as e:
        return None

@st.cache_data
def get_sample_data(_generator, num_users, start_date, end_date):
    return _generator.generate_sample_data(num_users=num_users, start_date=start_date, end_date=end_date)

def get_session_paths(sample_df):
    session_paths = sample_df.groupby(['user_id', 'session_id'])['event_name'].apply(
        lambda x: ' -> '.join(x)
    ).reset_index(name='path')
    path_counts = session_paths['path'].value_counts().reset_index()
    path_counts.columns = ['path', 'count']
    path_counts['percentage'] = (path_counts['count'] / path_counts['count'].sum() * 100).round(2)
    return path_counts

def advanced_sankey_view(sample_df=None):
    st.header("🌊 高级桑基图 - 可折叠分组")
    
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("开始日期", datetime.now() - timedelta(days=7), key="adv_sankey_start")
    with col2:
        end_date = st.date_input("结束日期", datetime.now(), key="adv_sankey_end")
    
    user_group = st.selectbox("选择用户分组", ["全部"] + SampleDataGenerator().user_groups, key="adv_sankey_group")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        max_depth = st.slider("最大路径深度", 2, 10, 5, key="adv_sankey_depth")
    with col2:
        low_freq_threshold = st.slider("低频路径阈值(%)", 0.1, 5.0, 1.0, 0.1, key="adv_sankey_threshold")
    with col3:
        enable_grouping = st.checkbox("启用事件分组", value=True)
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("分组控制")
        sankey_analyzer = AdvancedSankeyAnalyzer()
        group_options = list(sankey_analyzer.EVENT_GROUPS.keys())
        collapse_groups = st.multiselect(
            "选择要折叠的分组",
            group_options,
            default=[],
            format_func=lambda x: f"📁 {x}"
        )
    with col2:
        st.subheader("分组说明")
        for group, events in sankey_analyzer.EVENT_GROUPS.items():
            with st.expander(f"📁 {group} ({len(events)}个事件)"):
                st.write(", ".join(events))
    
    if st.button("生成高级桑基图", type="primary"):
        with st.spinner("正在生成桑基图..."):
            group_df = sample_df if user_group == "全部" else sample_df[sample_df['user_group'] == user_group]
            group_df = group_df[(group_df['event_time'] >= pd.Timestamp(start_date)) & 
                                (group_df['event_time'] <= pd.Timestamp(end_date))]
            
            path_counts = get_session_paths(group_df)
            
            sankey_data = sankey_analyzer.create_grouped_sankey_data(
                path_counts,
                max_depth=max_depth,
                low_freq_threshold=low_freq_threshold,
                collapse_groups=collapse_groups,
                group_by_category=enable_grouping
            )
            
            st.subheader("桑基图")
            sankey_chart = SankeyChart.create_advanced_sankey(
                sankey_data,
                title=f"用户行为路径 - 低频阈值 {low_freq_threshold}%"
            )
            st_pyecharts(sankey_chart, height="600px")
            
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("分组统计")
                group_stats = sankey_data.get('group_stats', {})
                for group, stats in group_stats.items():
                    st.markdown(f"""
                    <div style="padding: 0.5rem; margin: 0.25rem 0; border-radius: 0.25rem; background-color: {stats['color']}20; border-left: 4px solid {stats['color']}">
                        <strong>{group}</strong>: {stats['node_count']}个节点, {stats['total_value']:,}次流转
                    </div>
                    """, unsafe_allow_html=True)
            with col2:
                st.subheader("聚合信息")
                agg_info = sankey_data.get('aggregation_info', {})
                st.info(f"""
                - 低频路径阈值: {agg_info.get('threshold_pct', 0)}%
                - 聚合的低频路径数: {agg_info.get('low_frequency_count', 0)}
                - 总节点数: {len(sankey_data.get('nodes', []))}
                - 总连接数: {len(sankey_data.get('links', []))}
                """)

def multi_group_comparison_view(sample_df=None):
    st.header("⚖️ 多群组并排对比")
    
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("开始日期", datetime.now() - timedelta(days=14), key="multi_comp_start")
    with col2:
        end_date = st.date_input("结束日期", datetime.now(), key="multi_comp_end")
    
    analysis_type = st.radio("分析类型", ["路径对比", "桑基图对比", "漏斗对比"], horizontal=True)
    
    user_groups = SampleDataGenerator().user_groups
    selected_groups = st.multiselect(
        "选择要对比的用户分组 (最多4个)",
        user_groups,
        default=user_groups[:2],
        max_selections=4
    )
    
    if len(selected_groups) < 2:
        st.warning("请至少选择2个分组进行对比")
        return
    
    col1, col2 = st.columns(2)
    with col1:
        max_depth = st.slider("路径深度", 2, 8, 4, key="multi_comp_depth")
    with col2:
        cols = st.selectbox("布局列数", [1, 2, 3, 4], index=1)
    
    if st.button("开始对比分析", type="primary"):
        with st.spinner("正在进行多组对比分析..."):
            filtered_df = sample_df[
                (sample_df['event_time'] >= pd.Timestamp(start_date)) & 
                (sample_df['event_time'] <= pd.Timestamp(end_date))
            ]
            
            if analysis_type == "路径对比":
                st.subheader("Top 路径对比")
                
                all_paths = []
                for group in selected_groups:
                    group_df = filtered_df[filtered_df['user_group'] == group]
                    path_counts = get_session_paths(group_df).head(10)
                    path_counts['group'] = group
                    all_paths.append(path_counts)
                
                combined = pd.concat(all_paths, ignore_index=True)
                
                chart_data = []
                for group in selected_groups:
                    group_paths = combined[combined['group'] == group].head(5)
                    for _, row in group_paths.iterrows():
                        chart_data.append({
                            'path': row['path'][:30] + '...' if len(row['path']) > 30 else row['path'],
                            'count': row['count'],
                            'group': group
                        })
                
                comparison_df = pd.DataFrame(chart_data)
                
                from pyecharts import options as opts
                from pyecharts.charts import Bar
                from pyecharts.commons.utils import JsCode
                
                colors = ["#5470c6", "#ee6666", "#91cc75", "#73c0de"]
                
                bar = Bar(init_opts=opts.InitOpts(width="100%", height="500px"))
                bar.add_xaxis(comparison_df['path'].unique().tolist())
                
                for idx, group in enumerate(selected_groups):
                    group_data = comparison_df[comparison_df['group'] == group]
                    bar.add_yaxis(
                        group,
                        group_data['count'].tolist(),
                        color=colors[idx % len(colors)]
                    )
                
                bar.set_global_opts(
                    title_opts=opts.TitleOpts(title="各分组Top路径对比", pos_left="center"),
                    xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=45, font_size=10)),
                    yaxis_opts=opts.AxisOpts(name="会话数"),
                    legend_opts=opts.LegendOpts(pos_top="bottom")
                )
                
                st_pyecharts(bar, height="550px")
                
                st.subheader("详细路径数据")
                for group in selected_groups:
                    with st.expander(f"📊 {group} - Top路径"):
                        group_paths = combined[combined['group'] == group][['path', 'count', 'percentage']]
                        st.dataframe(group_paths, use_container_width=True)
            
            elif analysis_type == "桑基图对比":
                st.subheader("多分组桑基图并排对比")
                
                sankey_data_list = []
                sankey_analyzer = AdvancedSankeyAnalyzer()
                
                for group in selected_groups:
                    group_df = filtered_df[filtered_df['user_group'] == group]
                    path_counts = get_session_paths(group_df)
                    sankey_data = sankey_analyzer.create_grouped_sankey_data(
                        path_counts,
                        max_depth=max_depth,
                        low_freq_threshold=1.0
                    )
                    
                    nodes = sankey_data.get('nodes', [])
                    links = sankey_data.get('links', [])
                    
                    node_list = [n['name'] for n in nodes]
                    node_index = {name: i for i, name in enumerate(node_list)}
                    
                    simple_nodes = [{'name': n['name']} for n in nodes]
                    simple_links = [
                        {
                            'source': node_index.get(link['source'], 0),
                            'target': node_index.get(link['target'], 0),
                            'value': link['value']
                        }
                        for link in links
                    ]
                    
                    sankey_data_list.append({
                        'nodes': simple_nodes,
                        'links': simple_links
                    })
                
                colors = ["#5470c6", "#ee6666", "#91cc75", "#73c0de"]
                
                display_cols = st.columns(min(cols, len(selected_groups)))
                
                for idx, (group, sankey_data, display_col) in enumerate(zip(selected_groups, sankey_data_list, display_cols)):
                    with display_col:
                        st.markdown(f"### {group}")
                        
                        for node in sankey_data['nodes']:
                            node['itemStyle'] = {'color': colors[idx % len(colors)]}
                        
                        for link in sankey_data['links']:
                            link['lineStyle'] = {'color': colors[idx % len(colors)], 'opacity': 0.4}
                        
                        sankey_chart = SankeyChart.create_sankey(
                            sankey_data,
                            title=group,
                            height="400px"
                        )
                        st_pyecharts(sankey_chart, height="400px")
            
            elif analysis_type == "漏斗对比":
                st.subheader("漏斗对比分析")
                
                funnel_steps = st.multiselect(
                    "选择漏斗步骤",
                    ['page_view_home', 'login', 'page_view_product', 'add_to_cart', 'view_cart', 'checkout_start', 'checkout_complete', 'purchase', 'search'],
                    default=['page_view_home', 'add_to_cart', 'purchase']
                )
                
                if len(funnel_steps) < 2:
                    st.warning("请至少选择2个步骤")
                    return
                
                from pyecharts import options as opts
                from pyecharts.charts import Bar
                
                funnel_results = []
                colors = ["#5470c6", "#ee6666", "#91cc75", "#73c0de"]
                
                for group in selected_groups:
                    group_df = filtered_df[filtered_df['user_group'] == group]
                    user_events = group_df.groupby('user_id')['event_name'].unique().reset_index()
                    total_users = len(user_events)
                    
                    group_funnel = []
                    for step in funnel_steps:
                        step_users = user_events[user_events['event_name'].apply(lambda x: step in x)]['user_id'].nunique()
                        conversion_rate = (step_users / total_users * 100) if total_users > 0 else 0
                        group_funnel.append({
                            'step': step,
                            'group': group,
                            'users': step_users,
                            'conversion': round(conversion_rate, 2)
                        })
                    
                    funnel_results.extend(group_funnel)
                
                funnel_df = pd.DataFrame(funnel_results)
                
                bar = Bar(init_opts=opts.InitOpts(width="100%", height="500px"))
                bar.add_xaxis(funnel_steps)
                
                for idx, group in enumerate(selected_groups):
                    group_data = funnel_df[funnel_df['group'] == group]['conversion'].tolist()
                    bar.add_yaxis(
                        group,
                        group_data,
                        color=colors[idx % len(colors)],
                        label_opts=opts.LabelOpts(formatter="{c}%")
                    )
                
                bar.set_global_opts(
                    title_opts=opts.TitleOpts(title="各分组漏斗转化率对比(%)", pos_left="center"),
                    yaxis_opts=opts.AxisOpts(name="转化率(%)"),
                    legend_opts=opts.LegendOpts(pos_top="bottom")
                )
                
                st_pyecharts(bar, height="500px")
                
                st.dataframe(funnel_df.pivot(index='step', columns='group', values='users'), use_container_width=True)

def dynamic_segmentation_view(sample_df=None):
    st.header("🎯 动态分群分析")
    
    segmentor = DynamicSegmentation()
    
    if 'segments' not in st.session_state:
        st.session_state.segments = []
        st.session_state.segment_colors = ["#5470c6", "#ee6666", "#91cc75", "#73c0de", "#9a60b4", "#fac858"]
    
    st.subheader("📐 创建分群规则")
    
    with st.form("create_segment"):
        col1, col2 = st.columns(2)
        with col1:
            segment_name = st.text_input("分群名称", placeholder="例如：高价值购买用户")
        with col2:
            segment_color = st.color_picker("分群颜色", st.session_state.segment_colors[len(st.session_state.segments) % len(st.session_state.segment_colors)])
        
        st.markdown("#### 分群条件")
        
        if 'condition_count' not in st.session_state:
            st.session_state.condition_count = 1
        
        conditions = []
        logic = st.radio("条件逻辑", ["AND", "OR"], horizontal=True)
        
        for i in range(st.session_state.condition_count):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                dimension = st.selectbox(
                    f"维度 {i+1}",
                    list(segmentor.available_dimensions.keys()),
                    format_func=lambda x: segmentor.available_dimensions[x]['label'],
                    key=f"dim_{i}"
                )
            
            dim_type = segmentor.available_dimensions[dimension]['type']
            operators = segmentor.get_operators_for_type(dim_type)
            
            with col2:
                operator = st.selectbox(
                    f"运算符 {i+1}",
                    operators,
                    format_func=lambda x: x.value,
                    key=f"op_{i}"
                )
            
            with col3:
                if dim_type == DimensionType.CATEGORICAL:
                    values = sample_df[segmentor.available_dimensions[dimension]['column']].unique().tolist()
                    if operator in [Operator.IN, Operator.NOT_IN]:
                        value = st.multiselect(f"值 {i+1}", values, key=f"val_{i}")
                    else:
                        value = st.selectbox(f"值 {i+1}", values, key=f"val_{i}")
                elif dim_type == DimensionType.NUMERICAL:
                    value = st.number_input(f"值 {i+1}", value=0, key=f"val_{i}")
                elif dim_type == DimensionType.BOOLEAN:
                    value = st.selectbox(f"值 {i+1}", [True, False], key=f"val_{i}")
                else:
                    value = st.text_input(f"值 {i+1}", key=f"val_{i}")
            
            conditions.append(SegmentCondition(
                dimension=dimension,
                operator=operator,
                value=value,
                dimension_type=dim_type
            ))
        
        col1, col2 = st.columns(2)
        with col1:
            if st.form_submit_button("➕ 添加条件"):
                st.session_state.condition_count += 1
                st.rerun()
        with col2:
            if st.form_submit_button("✅ 创建分群"):
                if segment_name:
                    new_segment = Segment(
                        name=segment_name,
                        conditions=conditions,
                        logic=logic,
                        color=segment_color
                    )
                    st.session_state.segments.append(new_segment)
                    st.success(f"成功创建分群: {segment_name}")
                    st.session_state.condition_count = 1
                    st.rerun()
    
    if st.session_state.segments:
        st.subheader("📋 已创建的分群")
        
        for idx, segment in enumerate(st.session_state.segments):
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.markdown(f"""
                <div class="segment-card" style="border-left-color: {segment.color}">
                    <strong style="color: {segment.color}">{segment.name}</strong>
                    <br/>
                    <small>{segment.logic.join([f"{c.dimension} {c.operator.value} {c.value}" for c in segment.conditions])}
                    </small>
                </div>
                """, unsafe_allow_html=True)
            with col2:
                st.write(f"{len(segment.conditions)} 个条件")
            with col3:
                if st.button("🗑️", key=f"del_{idx}"):
                    del st.session_state.segments[idx]
                    st.rerun()
        
        if st.button("🚀 执行分群分析", type="primary"):
            with st.spinner("正在执行分群分析..."):
                segment_results = segmentor.create_segments_from_df(
                    sample_df,
                    st.session_state.segments
                )
                
                summary = segmentor.get_segment_summary(segment_results)
                
                st.subheader("📊 分群概览")
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("总分群数", len(segment_results))
                with col2:
                    total_users = sum(len(df) for df in segment_results.values())
                    st.metric("总用户数", total_users)
                with col3:
                    max_segment = summary.iloc[0] if not summary.empty else None
                    st.metric("最大分群", max_segment['segment'] if max_segment else "-")
                with col4:
                    avg_size = int(total_users / len(segment_results)) if segment_results else 0
                    st.metric("平均分群大小", avg_size)
                
                st.subheader("📈 分群统计")
                st.dataframe(summary, use_container_width=True)
                
                from pyecharts import options as opts
                from pyecharts.charts import Pie
                
                pie_data = [
                    {"value": row['user_count'], "name": row['segment']}
                    for _, row in summary.iterrows()
                ]
                
                colors = [seg.color for seg in st.session_state.segments]
                if '未分群' in summary['segment'].values:
                    colors.append("#999999")
                
                pie = Pie(init_opts=opts.InitOpts(width="100%", height="500px"))
                pie.add(
                    "",
                    [(item['name'], item['value']) for item in pie_data],
                    radius=["40%", "70%"],
                    label_opts=opts.LabelOpts(formatter="{b}: {c}人 ({d}%)")
                )
                pie.set_colors(colors)
                pie.set_global_opts(
                    title_opts=opts.TitleOpts(title="用户分群分布", pos_left="center"),
                    legend_opts=opts.LegendOpts(orient="vertical", pos_left="left", pos_top="middle")
                )
                
                st_pyecharts(pie, height="500px")
                
                st.subheader("🔍 分群路径对比")
                
                selected_segments = st.multiselect(
                    "选择分群查看路径",
                    list(segment_results.keys()),
                    default=list(segment_results.keys())[:2]
                )
                
                for seg_name in selected_segments:
                    with st.expander(f"🛤️ {seg_name} - Top路径"):
                        seg_users = segment_results[seg_name]['user_id'].tolist()
                        seg_paths = segmentor.get_segment_paths(
                            sample_df,
                            seg_users,
                            top_n=10
                        )
                        st.dataframe(seg_paths, use_container_width=True)
                
                if len(selected_segments) >= 2:
                    st.subheader("🌊 分群桑基图对比")
                    
                    sankey_data_list = []
                    for seg_name in selected_segments[:4]:
                        seg_users = segment_results[seg_name]['user_id'].tolist()
                        seg_df = sample_df[sample_df['user_id'].isin(seg_users)]
                        path_counts = get_session_paths(seg_df)
                        
                        sankey_analyzer = AdvancedSankeyAnalyzer()
                        sankey_data = sankey_analyzer.create_grouped_sankey_data(
                            path_counts,
                            max_depth=4,
                            low_freq_threshold=2.0
                        )
                        
                        sankey_data_list.append(sankey_data)
                    
                    display_cols = st.columns(min(2, len(selected_segments)))
                    
                    colors = ["#5470c6", "#ee6666", "#91cc75", "#73c0de"]
                    
                    for idx, (seg_name, sankey_data, col) in enumerate(zip(selected_segments, sankey_data_list, display_cols)):
                        with col:
                            st.markdown(f"### {seg_name}")
                            
                            nodes = sankey_data.get('nodes', [])
                            links = sankey_data.get('links', [])
                            
                            node_list = [n['name'] for n in nodes]
                            node_index = {name: i for i, name in enumerate(node_list)}
                            
                            simple_nodes = [{'name': n['name']} for n in nodes]
                            for node in simple_nodes:
                                node['itemStyle'] = {'color': colors[idx % len(colors)]}
                            
                            simple_links = [
                                {
                                    'source': node_index.get(link['source'], 0),
                                    'target': node_index.get(link['target'], 0),
                                    'value': link['value'],
                                    'lineStyle': {'color': colors[idx % len(colors)], 'opacity': 0.4}
                                }
                                for link in links
                            ]
                            
                            simple_sankey = {
                                'nodes': simple_nodes,
                                'links': simple_links
                            }
                            
                            sankey_chart = SankeyChart.create_sankey(
                                simple_sankey,
                                title=seg_name,
                                height="400px"
                            )
                            st_pyecharts(sankey_chart, height="400px")
    else:
        st.info("💡 请先创建至少一个分群规则")
        
        with st.expander("📚 分群示例模板"):
            st.markdown("""
            **高价值用户分群:**
            - 维度: 会话数, 运算符: 大于等于, 值: 5
            - 维度: 是否购买, 运算符: 等于, 值: True
            
            **流失风险用户:**
            - 维度: 最近访问天数, 运算符: 大于, 值: 14
            - 维度: 会话数, 运算符: 小于, 值: 2
            
            **移动设备用户:**
            - 维度: 设备类型, 运算符: 等于, 值: mobile
            """)

def path_prediction_view(sample_df=None):
    st.header("🔮 路径预测 - 马尔可夫链模型")
    
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("开始日期", datetime.now() - timedelta(days=14), key="pred_start")
    with col2:
        end_date = st.date_input("结束日期", datetime.now(), key="pred_end")
    
    user_group = st.selectbox("选择用户分组", ["全部"] + sample_df['user_group'].unique().tolist(), key="pred_group")
    
    col1, col2 = st.columns(2)
    with col1:
        model_order = st.selectbox("马尔可夫链阶数", [1, 2, 3], index=0, format_func=lambda x: f"{x}阶")
    with col2:
        predict_steps = st.slider("预测步数", 1, 5, 3)
    
    available_events = sorted(sample_df['event_name'].unique().tolist())
    current_event = st.selectbox("选择当前事件（预测起点）", available_events, key="pred_event")
    
    if st.button("训练模型并预测", type="primary", key="pred_btn"):
        with st.spinner("正在训练马尔可夫链模型..."):
            group_df = sample_df if user_group == "全部" else sample_df[sample_df['user_group'] == user_group]
            group_df = group_df[(group_df['event_time'] >= pd.Timestamp(start_date)) & 
                                (group_df['event_time'] <= pd.Timestamp(end_date))]
            
            path_counts = get_session_paths(group_df)
            
            predictor = MarkovChainPredictor(order=model_order)
            predictor.fit(path_counts)
            
            st.subheader("🔮 下一步行为预测")
            predictions = predictor.predict_next(current_event, top_k=5)
            
            if predictions:
                pred_df = pd.DataFrame(predictions)
                st.dataframe(pred_df, use_container_width=True)
                
                from pyecharts import options as opts
                from pyecharts.charts import Bar
                
                bar = Bar(init_opts=opts.InitOpts(width="100%", height="400px"))
                bar.add_xaxis([p['next_event'] for p in predictions])
                bar.add_yaxis(
                    "概率(%)",
                    [p['probability'] for p in predictions],
                    itemstyle_opts=opts.ItemStyleOpts(
                        color=opts.JsCode(
                            "function(params) {"
                            "var colors = ['#5470c6','#91cc75','#fac858','#ee6666','#73c0de'];"
                            "return colors[params.dataIndex % colors.length];"
                            "}"
                        )
                    )
                )
                bar.set_global_opts(
                    title_opts=opts.TitleOpts(title=f"从「{current_event}」出发的下一步行为概率", pos_left="center"),
                    yaxis_opts=opts.AxisOpts(name="概率(%)", max_=100),
                    xaxis_opts=opts.AxisOpts(name="预测事件"),
                    tooltip_opts=opts.TooltipOpts(trigger="axis")
                )
                bar.set_series_opts(label_opts=opts.LabelOpts(formatter="{c}%"))
                st_pyecharts(bar, height="450px")
            else:
                st.warning("当前事件无足够转移数据")
            
            st.subheader("🔮 多步路径预测")
            sequence_preds = predictor.predict_sequence(current_event, steps=predict_steps, top_k=3)
            
            for step_result in sequence_preds:
                st.markdown(f"**第 {step_result['step']} 步** (从 `{step_result['from_state']}` 出发)")
                for pred in step_result['predictions']:
                    st.markdown(f"  → `{pred['next_event']}` (概率: {pred['probability']}%, 置信度: {pred['confidence']})")
            
            st.subheader("📊 各状态可预测性分析")
            entropy_df = predictor.get_all_entropies()
            st.dataframe(entropy_df, use_container_width=True)
            
            st.info("💡 熵值越低表示可预测性越高；可预测性指标接近1表示该节点的下一步行为高度确定")

def anomaly_detection_view(sample_df=None):
    st.header("🔍 异常路径检测")
    
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("开始日期", datetime.now() - timedelta(days=14), key="anomaly_start")
    with col2:
        end_date = st.date_input("结束日期", datetime.now(), key="anomaly_end")
    
    user_group = st.selectbox("选择用户分组", ["全部"] + sample_df['user_group'].unique().tolist(), key="anomaly_group")
    
    available_events = sorted(sample_df['event_name'].unique().tolist())
    
    col1, col2 = st.columns(2)
    with col1:
        expected_flow = st.multiselect(
            "定义预期流程（可选，用于检测跳步/回退）",
            available_events,
            default=['page_view_home', 'search', 'page_view_product', 'add_to_cart', 'view_cart', 'checkout_start', 'purchase'] if all(e in available_events for e in ['page_view_home', 'search', 'page_view_product', 'add_to_cart', 'view_cart', 'checkout_start', 'purchase']) else []
        )
    with col2:
        top_n = st.slider("显示异常数量", 10, 100, 30)
    
    if st.button("检测异常路径", type="primary", key="anomaly_btn"):
        with st.spinner("正在检测异常路径..."):
            group_df = sample_df if user_group == "全部" else sample_df[sample_df['user_group'] == user_group]
            group_df = group_df[(group_df['event_time'] >= pd.Timestamp(start_date)) & 
                                (group_df['event_time'] <= pd.Timestamp(end_date))]
            
            path_counts = get_session_paths(group_df)
            
            detector = AnomalyDetector()
            detector.fit(path_counts, expected_flow=expected_flow if expected_flow else None)
            
            anomaly_df = detector.batch_detect(path_counts, top_n=top_n)
            
            summary = detector.get_anomaly_summary_stats(path_counts)
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("总异常数", summary.get('total_anomalies', 0))
            with col2:
                st.metric("异常类型数", summary.get('unique_anomaly_types', 0))
            with col3:
                high_severity = summary.get('by_severity', {}).get('high', 0)
                st.metric("高危异常", high_severity)
            with col4:
                medium_severity = summary.get('by_severity', {}).get('medium', 0)
                st.metric("中危异常", medium_severity)
            
            if not anomaly_df.empty:
                st.subheader("📋 异常详情列表")
                
                severity_filter = st.multiselect(
                    "筛选严重级别",
                    ['high', 'medium', 'low'],
                    default=['high', 'medium']
                )
                
                filtered_df = anomaly_df[anomaly_df['severity'].isin(severity_filter)]
                st.dataframe(filtered_df, use_container_width=True)
                
                st.subheader("📊 异常类型分布")
                by_type = summary.get('by_type', {})
                if by_type:
                    from pyecharts import options as opts
                    from pyecharts.charts import Pie
                    
                    pie = Pie(init_opts=opts.InitOpts(width="100%", height="400px"))
                    pie.add(
                        "",
                        list(by_type.items()),
                        radius=["40%", "70%"],
                        label_opts=opts.LabelOpts(formatter="{b}: {c} ({d}%)")
                    )
                    pie.set_global_opts(
                        title_opts=opts.TitleOpts(title="异常类型分布", pos_left="center"),
                        legend_opts=opts.LegendOpts(orient="vertical", pos_left="left", pos_top="middle")
                    )
                    st_pyecharts(pie, height="450px")
                
                st.subheader("📊 严重级别分布")
                by_severity = summary.get('by_severity', {})
                if by_severity:
                    severity_colors = {'high': '#ee6666', 'medium': '#fac858', 'low': '#91cc75'}
                    from pyecharts import options as opts
                    from pyecharts.charts import Pie
                    
                    pie = Pie(init_opts=opts.InitOpts(width="100%", height="400px"))
                    pie.add(
                        "",
                        list(by_severity.items()),
                        radius=["40%", "70%"],
                        label_opts=opts.LabelOpts(formatter="{b}: {c} ({d}%)")
                    )
                    pie.set_colors([severity_colors.get(k, '#999') for k in by_severity.keys()])
                    pie.set_global_opts(
                        title_opts=opts.TitleOpts(title="严重级别分布", pos_left="center")
                    )
                    st_pyecharts(pie, height="400px")
            else:
                st.success("✅ 未检测到显著异常路径")
            
            with st.expander("📚 异常类型说明"):
                from analytics.anomaly_detector import ANOMALY_DESCRIPTION
                for atype, desc in ANOMALY_DESCRIPTION.items():
                    st.markdown(f"- **{atype.value}**: {desc}")

def attribution_analysis_view(sample_df=None):
    st.header("🏆 归因分析 - 转化路径权重")
    
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("开始日期", datetime.now() - timedelta(days=14), key="attr_start")
    with col2:
        end_date = st.date_input("结束日期", datetime.now(), key="attr_end")
    
    available_events = sorted(sample_df['event_name'].unique().tolist())
    conversion_candidates = [e for e in available_events if any(kw in e for kw in ['purchase', 'checkout_complete', 'order'])]
    default_conv = conversion_candidates[0] if conversion_candidates else (available_events[-1] if available_events else 'purchase')
    
    conversion_event = st.selectbox(
        "选择转化事件",
        available_events,
        index=available_events.index(default_conv) if default_conv in available_events else 0,
        key="attr_conv"
    )
    
    if st.button("执行归因分析", type="primary", key="attr_btn"):
        with st.spinner("正在计算归因权重..."):
            group_df = sample_df[
                (sample_df['event_time'] >= pd.Timestamp(start_date)) & 
                (sample_df['event_time'] <= pd.Timestamp(end_date))
            ]
            
            path_counts = get_session_paths(group_df)
            
            analyzer = AttributionAnalyzer()
            analyzer.fit(path_counts, conversion_event=conversion_event)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("转化路径数", len(analyzer.conversion_paths))
            with col2:
                st.metric("非转化路径数", len(analyzer.non_conversion_paths))
            with col3:
                total = len(analyzer.conversion_paths) + len(analyzer.non_conversion_paths)
                conv_rate = len(analyzer.conversion_paths) / total * 100 if total > 0 else 0
                st.metric("转化率", f"{conv_rate:.1f}%")
            
            st.subheader("🏆 多模型归因对比")
            comparison = analyzer.compare_models()
            
            if not comparison.empty:
                from pyecharts import options as opts
                from pyecharts.charts import Bar
                
                models = comparison['model'].unique().tolist()
                events = comparison[comparison['model'] == models[0]]['event'].tolist() if models else []
                
                colors = ["#5470c6", "#ee6666", "#91cc75", "#73c0de", "#9a60b4", "#fac858"]
                
                bar = Bar(init_opts=opts.InitOpts(width="100%", height="500px"))
                bar.add_xaxis(events)
                
                for idx, model in enumerate(models):
                    model_data = comparison[comparison['model'] == model]
                    event_weights = []
                    for event in events:
                        ew = model_data[model_data['event'] == event]['attribution_weight'].tolist()
                        event_weights.append(ew[0] if ew else 0)
                    bar.add_yaxis(model, event_weights, color=colors[idx % len(colors)])
                
                bar.set_global_opts(
                    title_opts=opts.TitleOpts(title="多模型归因权重对比(%)", pos_left="center"),
                    yaxis_opts=opts.AxisOpts(name="归因权重(%)"),
                    xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=30, font_size=10)),
                    legend_opts=opts.LegendOpts(pos_top="bottom")
                )
                
                st_pyecharts(bar, height="550px")
                
                st.subheader("📊 详细归因数据")
                pivot_df = comparison.pivot_table(
                    index='event', columns='model', values='attribution_weight', fill_value=0
                ).round(2)
                st.dataframe(pivot_df, use_container_width=True)
            
            st.subheader("📈 各事件转化提升度 (Lift)")
            lift_df = analyzer.get_conversion_funnel_attribution()
            if not lift_df.empty:
                st.dataframe(lift_df, use_container_width=True)
                
                from pyecharts import options as opts
                from pyecharts.charts import Bar
                
                lift_bar = Bar(init_opts=opts.InitOpts(width="100%", height="400px"))
                lift_bar.add_xaxis(lift_df['event'].tolist())
                lift_bar.add_yaxis(
                    "Lift值",
                    lift_df['lift'].tolist(),
                    itemstyle_opts=opts.ItemStyleOpts(
                        color=opts.JsCode(
                            "function(params) {"
                            "return params.value >= 1 ? '#91cc75' : '#ee6666';"
                            "}"
                        )
                    )
                )
                lift_bar.set_global_opts(
                    title_opts=opts.TitleOpts(title="各事件对转化的提升度 (Lift>1为正向贡献)", pos_left="center"),
                    yaxis_opts=opts.AxisOpts(name="Lift值"),
                    xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=30, font_size=10))
                )
                st_pyecharts(lift_bar, height="450px")
                
                st.info("💡 Lift > 1 表示该事件出现时转化率高于整体平均水平，对转化有正向贡献；Lift < 1 则相反")
            
            st.subheader("🔗 转化贡献路径")
            path_contrib = analyzer.get_path_contribution(conversion_event)
            if not path_contrib.empty:
                st.dataframe(path_contrib, use_container_width=True)

def main():
    st.title(f"{APP_ICON} {APP_TITLE}")
    
    with st.sidebar:
        st.header("导航")
        
        page = st.radio(
            "选择功能模块",
            ["数据概览", "路径预测", "异常路径检测", "归因分析", "高级桑基图", "多群组对比", "动态分群分析", "路径分析", "转化漏斗", "流失分析"]
        )
        
        st.divider()
        
        use_sample_data = st.checkbox("使用本地示例数据", value=True)
    
    sample_df = None
    
    if use_sample_data:
        generator = SampleDataGenerator()
        
        col1, col2 = st.sidebar.columns(2)
        with col1:
            sample_users = st.number_input("示例用户数", 100, 5000, 1000, step=100)
        with col2:
            sample_days = st.number_input("数据天数", 7, 90, 30, step=7)
        
        if st.sidebar.button("生成示例数据", type="primary"):
            with st.spinner("正在生成示例数据..."):
                end_date = datetime.now()
                start_date = end_date - timedelta(days=sample_days)
                sample_df = get_sample_data(
                    generator,
                    num_users=sample_users,
                    start_date=start_date.strftime('%Y-%m-%d'),
                    end_date=end_date.strftime('%Y-%m-%d')
                )
                st.sidebar.success(f"已生成 {len(sample_df)} 条记录")
    else:
        st.sidebar.error("本演示版本仅支持本地示例数据")
        return
    
    if sample_df is None:
        st.info("👈 请在左侧边栏点击'生成示例数据'开始使用")
        return
    
    st.sidebar.success(f"✅ 数据已加载: {len(sample_df)} 条记录")
    
    if page == "数据概览":
        st.header("📊 数据概览")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("总用户数", f"{sample_df['user_id'].nunique():,}")
        with col2:
            st.metric("总会话数", f"{sample_df['session_id'].nunique():,}")
        with col3:
            st.metric("事件数", f"{len(sample_df):,}")
        with col4:
            st.metric("事件类型", f"{sample_df['event_name'].nunique()}")
        
        st.subheader("用户分组统计")
        group_stats = sample_df.groupby('user_group').agg({
            'user_id': 'nunique',
            'session_id': 'nunique',
            'event_name': 'count'
        }).reset_index()
        group_stats.columns = ['用户分组', '用户数', '会话数', '事件数']
        st.dataframe(group_stats, use_container_width=True)
        
        st.subheader("设备分布")
        col1, col2 = st.columns(2)
        with col1:
            st.write("设备类型")
            st.dataframe(sample_df['device_type'].value_counts().reset_index(), use_container_width=True)
        with col2:
            st.write("操作系统")
            st.dataframe(sample_df['os'].value_counts().reset_index(), use_container_width=True)
    
    elif page == "高级桑基图":
        advanced_sankey_view(sample_df)
    
    elif page == "路径预测":
        path_prediction_view(sample_df)
    
    elif page == "异常路径检测":
        anomaly_detection_view(sample_df)
    
    elif page == "归因分析":
        attribution_analysis_view(sample_df)
    
    elif page == "多群组对比":
        multi_group_comparison_view(sample_df)
    
    elif page == "动态分群分析":
        dynamic_segmentation_view(sample_df)
    
    elif page == "路径分析":
        st.header("🛤️ 路径分析")
        
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("开始日期", datetime.now() - timedelta(days=7))
        with col2:
            end_date = st.date_input("结束日期", datetime.now())
        
        user_group = st.selectbox("选择用户分组", ["全部"] + sample_df['user_group'].unique().tolist())
        
        col1, col2 = st.columns(2)
        with col1:
            min_length = st.slider("最小路径长度", 2, 10, 2)
        with col2:
            max_length = st.slider("最大路径长度", 2, 15, 8)
        
        top_n = st.slider("显示Top N路径", 5, 50, 20)
        
        if st.button("分析路径", type="primary"):
            with st.spinner("正在分析路径..."):
                group_df = sample_df if user_group == "全部" else sample_df[sample_df['user_group'] == user_group]
                group_df = group_df[(group_df['event_time'] >= pd.Timestamp(start_date)) & 
                                    (group_df['event_time'] <= pd.Timestamp(end_date))]
                
                session_paths = group_df.groupby(['user_id', 'session_id'])['event_name'].apply(
                    lambda x: ' -> '.join(x)
                ).reset_index(name='path')
                session_paths['path_length'] = session_paths['path'].apply(lambda x: len(x.split(' -> ')))
                
                paths_df = session_paths[
                    (session_paths['path_length'] >= min_length) & 
                    (session_paths['path_length'] <= max_length)
                ]['path'].value_counts().reset_index()
                paths_df.columns = ['path', 'count']
                paths_df['percentage'] = (paths_df['count'] / paths_df['count'].sum() * 100).round(2)
                paths_df = paths_df.head(top_n)
                
                st.subheader(f"Top {len(paths_df)} 常见路径")
                st.dataframe(paths_df, use_container_width=True)
                
                st.subheader("路径分布图表")
                chart = PathCharts.create_top_paths_bar(paths_df, top_n=top_n)
                st_pyecharts(chart, height="500px")
    
    elif page == "转化漏斗":
        st.header("📈 转化漏斗分析")
        
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("开始日期", datetime.now() - timedelta(days=14))
        with col2:
            end_date = st.date_input("结束日期", datetime.now())
        
        user_group = st.selectbox("选择用户分组", ["全部"] + sample_df['user_group'].unique().tolist())
        
        available_events = sample_df['event_name'].unique().tolist()
        
        st.subheader("选择漏斗步骤")
        selected_steps = st.multiselect(
            "按顺序选择漏斗步骤（至少2个）",
            available_events,
            default=['page_view_home', 'add_to_cart', 'purchase'] if all(e in available_events for e in ['page_view_home', 'add_to_cart', 'purchase']) else available_events[:3]
        )
        
        if len(selected_steps) < 2:
            st.warning("请至少选择2个步骤")
            return
        
        if st.button("分析漏斗", type="primary"):
            with st.spinner("正在分析漏斗..."):
                group_df = sample_df if user_group == "全部" else sample_df[sample_df['user_group'] == user_group]
                group_df = group_df[(group_df['event_time'] >= pd.Timestamp(start_date)) & 
                                    (group_df['event_time'] <= pd.Timestamp(end_date))]
                
                user_events = group_df.groupby('user_id')['event_name'].unique().reset_index()
                total_users = len(user_events)
                
                funnel_data = []
                for i, step in enumerate(selected_steps):
                    step_users = user_events[user_events['event_name'].apply(lambda x: step in x)]['user_id'].nunique()
                    conversion_rate = (step_users / total_users * 100) if total_users > 0 else 0
                    
                    if i == 0:
                        step_conversion = 100.0
                    else:
                        prev_users = funnel_data[i-1]['users']
                        step_conversion = (step_users / prev_users * 100) if prev_users > 0 else 0
                    
                    funnel_data.append({
                        'step': step,
                        'step_number': i + 1,
                        'users': step_users,
                        'conversion_from_start': round(conversion_rate, 2),
                        'conversion_from_previous': round(step_conversion, 2),
                        'dropoff': round(100 - step_conversion, 2)
                    })
                
                funnel_df = pd.DataFrame(funnel_data)
                final_users = funnel_df['users'].iloc[-1] if not funnel_df.empty else 0
                overall_conversion = (final_users / total_users * 100) if total_users > 0 else 0
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("总用户数", f"{total_users:,}")
                with col2:
                    st.metric("转化用户数", f"{final_users:,}")
                with col3:
                    st.metric("整体转化率", f"{round(overall_conversion, 2)}%")
                with col4:
                    st.metric("平均步骤转化率", f"{round(funnel_df['conversion_from_previous'].mean(), 2)}%")
                
                st.info(f"💡 最大流失节点: {funnel_df.loc[funnel_df['dropoff'].idxmax(), 'step']} ({funnel_df['dropoff'].max()}%)")
                
                st.subheader("漏斗详情")
                st.dataframe(funnel_df, use_container_width=True)
                
                st.subheader("漏斗图表")
                funnel_chart = FunnelChart.create_funnel_with_conversion(funnel_df)
                st_pyecharts(funnel_chart, height="500px")
    
    elif page == "流失分析":
        st.header("📉 流失分析")
        
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("开始日期", datetime.now() - timedelta(days=30))
        with col2:
            end_date = st.date_input("结束日期", datetime.now())
        
        churn_days = st.slider("流失判定天数（N天未活跃视为流失）", 1, 30, 7)
        user_group = st.selectbox("选择用户分组", ["全部"] + sample_df['user_group'].unique().tolist())
        
        if st.button("分析流失", type="primary"):
            with st.spinner("正在分析流失..."):
                group_df = sample_df if user_group == "全部" else sample_df[sample_df['user_group'] == user_group]
                group_df = group_df[(group_df['event_time'] >= pd.Timestamp(start_date)) & 
                                    (group_df['event_time'] <= pd.Timestamp(end_date))]
                
                user_activity = group_df.groupby('user_id')['event_time'].agg(['min', 'max']).reset_index()
                churn_threshold = pd.Timestamp(end_date) - pd.Timedelta(days=churn_days)
                
                user_activity['is_churned'] = user_activity['max'] < churn_threshold
                total_users = len(user_activity)
                churned_users = user_activity['is_churned'].sum()
                
                churn_data = {
                    'total_users': total_users,
                    'churned_users': churned_users,
                    'churn_rate': round(churned_users / total_users * 100, 2),
                    'churn_days': churn_days
                }
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("总用户数", f"{churn_data.get('total_users', 0):,}")
                with col2:
                    st.metric("流失用户数", f"{churn_data.get('churned_users', 0):,}")
                with col3:
                    st.metric(f"{churn_days}天流失率", f"{churn_data.get('churn_rate', 0)}%")
                
                st.subheader("用户流失分布")
                pie_chart = PathCharts.create_churn_pie(churn_data, title=f"{churn_days}天用户流失分布")
                st_pyecharts(pie_chart, height="400px")
                
                st.subheader("各用户分组流失率对比")
                
                churn_by_group = []
                for group in sample_df['user_group'].unique():
                    group_df = sample_df[sample_df['user_group'] == group]
                    user_activity = group_df.groupby('user_id')['event_time'].agg(['max']).reset_index()
                    user_activity['is_churned'] = user_activity['max'] < churn_threshold
                    group_total = len(user_activity)
                    group_churned = user_activity['is_churned'].sum()
                    churn_rate = (group_churned / group_total * 100) if group_total > 0 else 0
                    
                    churn_by_group.append({
                        'group': group,
                        'total_users': group_total,
                        'churned_users': group_churned,
                        'churn_rate': round(churn_rate, 2)
                    })
                
                churn_df = pd.DataFrame(churn_by_group)
                st.dataframe(churn_df, use_container_width=True)

if __name__ == "__main__":
    main()
