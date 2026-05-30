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
from analytics.comparison_analyzer import ComparisonAnalyzer
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
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def get_db_client():
    try:
        return ClickHouseClient()
    except Exception as e:
        st.error(f"数据库连接失败: {e}")
        return None

@st.cache_data
def get_sample_data(_generator, num_users, start_date, end_date):
    return _generator.generate_sample_data(num_users=num_users, start_date=start_date, end_date=end_date)

def init_database():
    st.subheader("📊 数据库初始化")
    
    db = get_db_client()
    
    if not db or not db.is_connected():
        st.warning("ClickHouse未连接，将使用本地示例数据模式")
        return None
    
    try:
        db.create_database()
        db.create_events_table()
        st.success("数据库和表创建成功！")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            num_users = st.number_input("用户数量", min_value=100, max_value=10000, value=1000, step=100)
        with col2:
            start_date = st.date_input("开始日期", datetime.now() - timedelta(days=30))
        with col3:
            end_date = st.date_input("结束日期", datetime.now())
        
        if st.button("生成并导入示例数据", type="primary"):
            with st.spinner("正在生成数据..."):
                generator = SampleDataGenerator()
                df = generator.generate_sample_data(
                    num_users=num_users,
                    start_date=str(start_date),
                    end_date=str(end_date)
                )
                db.insert_events(df)
                st.success(f"成功导入 {len(df)} 条事件记录！")
        
        return db
    except Exception as e:
        st.error(f"初始化失败: {e}")
        return None

def dashboard_view(db, sample_df=None):
    st.header("📊 数据概览")
    
    if db and db.is_connected():
        date_range = db.get_date_range()
        total_users = db.get_distinct_users(str(date_range.get('min', '')), str(date_range.get('max', '')))
        events = db.get_distinct_events(str(date_range.get('min', '')), str(date_range.get('max', '')))
        user_groups = db.get_user_groups()
    elif sample_df is not None:
        total_users = sample_df['user_id'].nunique()
        events = sample_df['event_name'].unique().tolist()
        user_groups = sample_df['user_group'].unique().tolist()
        date_range = {
            'min': sample_df['event_time'].min(),
            'max': sample_df['event_time'].max()
        }
    else:
        st.warning("没有可用数据，请先初始化数据库或使用示例数据")
        return
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("总用户数", f"{total_users:,}")
    with col2:
        st.metric("事件类型数", len(events))
    with col3:
        st.metric("用户分组数", len(user_groups))
    with col4:
        st.metric("数据日期范围", f"{str(date_range.get('min', ''))[:10]} ~ {str(date_range.get('max', ''))[:10]}")
    
    st.subheader("用户分组统计")
    if db and db.is_connected():
        comparison = ComparisonAnalyzer(db)
        group_metrics = comparison.get_group_metrics(str(date_range.get('min', '')), str(date_range.get('max', '')))
        st.dataframe(group_metrics, use_container_width=True)
    elif sample_df is not None:
        group_stats = sample_df.groupby('user_group').agg({
            'user_id': 'nunique',
            'session_id': 'nunique',
            'event_name': 'count'
        }).reset_index()
        group_stats.columns = ['user_group', 'user_count', 'session_count', 'event_count']
        group_stats['avg_events_per_session'] = (group_stats['event_count'] / group_stats['session_count']).round(2)
        st.dataframe(group_stats, use_container_width=True)

def path_analysis_view(db, sample_df=None):
    st.header("🛤️ 路径分析")
    
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("开始日期", datetime.now() - timedelta(days=7))
    with col2:
        end_date = st.date_input("结束日期", datetime.now())
    
    user_group = st.selectbox("选择用户分组", ["全部"] + (db.get_user_groups() if db and db.is_connected() else SampleDataGenerator().user_groups))
    
    col1, col2 = st.columns(2)
    with col1:
        min_length = st.slider("最小路径长度", 2, 10, 2)
    with col2:
        max_length = st.slider("最大路径长度", 2, 15, 8)
    
    top_n = st.slider("显示Top N路径", 5, 50, 20)
    
    if st.button("分析路径", type="primary"):
        with st.spinner("正在分析路径..."):
            if db and db.is_connected():
                path_analyzer = PathAnalyzer(db)
                group_param = None if user_group == "全部" else user_group
                paths_df = path_analyzer.get_frequent_paths(
                    str(start_date), str(end_date),
                    min_length=min_length,
                    max_length=max_length,
                    user_group=group_param,
                    top_n=top_n
                )
            elif sample_df is not None:
                from collections import defaultdict
                
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
            else:
                st.warning("没有可用数据")
                return
            
            if paths_df.empty:
                st.info("未找到符合条件的路径")
                return
            
            st.subheader(f"Top {len(paths_df)} 常见路径")
            st.dataframe(paths_df, use_container_width=True)
            
            st.subheader("路径分布图表")
            chart = PathCharts.create_top_paths_bar(paths_df, top_n=top_n)
            st_pyecharts(chart, height="500px")

def sankey_view(db, sample_df=None):
    st.header("🌊 桑基图可视化")
    
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("开始日期", datetime.now() - timedelta(days=7), key="sankey_start")
    with col2:
        end_date = st.date_input("结束日期", datetime.now(), key="sankey_end")
    
    user_group = st.selectbox("选择用户分组", ["全部"] + (db.get_user_groups() if db and db.is_connected() else SampleDataGenerator().user_groups), key="sankey_group")
    
    max_depth = st.slider("最大路径深度", 2, 10, 5)
    
    if st.button("生成桑基图", type="primary"):
        with st.spinner("正在生成桑基图..."):
            if db and db.is_connected():
                path_analyzer = PathAnalyzer(db)
                group_param = None if user_group == "全部" else user_group
                sankey_data = path_analyzer.get_sankey_data(
                    str(start_date), str(end_date),
                    max_depth=max_depth,
                    user_group=group_param
                )
            elif sample_df is not None:
                from collections import defaultdict
                
                group_df = sample_df if user_group == "全部" else sample_df[sample_df['user_group'] == user_group]
                group_df = group_df[(group_df['event_time'] >= pd.Timestamp(start_date)) & 
                                    (group_df['event_time'] <= pd.Timestamp(end_date))]
                
                session_paths = group_df.groupby(['user_id', 'session_id'])['event_name'].apply(
                    lambda x: ' -> '.join(x)
                ).reset_index(name='path')
                session_paths['path_length'] = session_paths['path'].apply(lambda x: len(x.split(' -> ')))
                session_paths = session_paths[session_paths['path_length'] >= 2]
                
                transitions = defaultdict(int)
                nodes = set()
                
                for path in session_paths['path']:
                    events = path.split(' -> ')
                    for i in range(min(len(events) - 1, max_depth - 1)):
                        source = events[i]
                        target = events[i + 1]
                        transitions[(source, target)] += 1
                        nodes.add(source)
                        nodes.add(target)
                
                node_list = list(nodes)
                node_index = {node: i for i, node in enumerate(node_list)}
                
                sankey_data = {
                    'nodes': [{'name': node} for node in node_list],
                    'links': [
                        {
                            'source': node_index[source],
                            'target': node_index[target],
                            'value': count
                        }
                        for (source, target), count in transitions.items()
                    ]
                }
            else:
                st.warning("没有可用数据")
                return
            
            if not sankey_data['nodes']:
                st.info("未找到足够的路径数据")
                return
            
            sankey_chart = SankeyChart.create_sankey(sankey_data, title=f"用户行为路径桑基图 - {user_group}")
            st_pyecharts(sankey_chart, height="600px")

def funnel_view(db, sample_df=None):
    st.header("📈 转化漏斗分析")
    
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("开始日期", datetime.now() - timedelta(days=14), key="funnel_start")
    with col2:
        end_date = st.date_input("结束日期", datetime.now(), key="funnel_end")
    
    user_group = st.selectbox("选择用户分组", ["全部"] + (db.get_user_groups() if db and db.is_connected() else SampleDataGenerator().user_groups), key="funnel_group")
    
    available_events = ['page_view_home', 'login', 'page_view_product', 'add_to_cart', 'view_cart', 'checkout_start', 'checkout_complete', 'purchase', 'search']
    
    st.subheader("选择漏斗步骤")
    selected_steps = st.multiselect(
        "按顺序选择漏斗步骤（至少2个）",
        available_events,
        default=['page_view_home', 'add_to_cart', 'purchase']
    )
    
    if len(selected_steps) < 2:
        st.warning("请至少选择2个步骤")
        return
    
    if st.button("分析漏斗", type="primary"):
        with st.spinner("正在分析漏斗..."):
            if db and db.is_connected():
                funnel_analyzer = FunnelAnalyzer(db)
                group_param = None if user_group == "全部" else user_group
                funnel_details = funnel_analyzer.get_funnel_details(
                    str(start_date), str(end_date),
                    funnel_steps=selected_steps,
                    user_group=group_param
                )
                funnel_df = funnel_details.get('funnel_data', pd.DataFrame())
            elif sample_df is not None:
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
                
                funnel_details = {
                    'funnel_data': funnel_df,
                    'total_users': total_users,
                    'converted_users': final_users,
                    'overall_conversion_rate': round(overall_conversion, 2),
                    'avg_step_conversion': round(funnel_df['conversion_from_previous'].mean(), 2),
                    'biggest_dropoff_step': funnel_df.loc[funnel_df['dropoff'].idxmax(), 'step'] if not funnel_df.empty else '',
                    'biggest_dropoff_rate': round(funnel_df['dropoff'].max(), 2)
                }
            else:
                st.warning("没有可用数据")
                return
            
            if funnel_df.empty:
                st.info("未找到漏斗数据")
                return
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("总用户数", f"{funnel_details.get('total_users', 0):,}")
            with col2:
                st.metric("转化用户数", f"{funnel_details.get('converted_users', 0):,}")
            with col3:
                st.metric("整体转化率", f"{funnel_details.get('overall_conversion_rate', 0)}%")
            with col4:
                st.metric("平均步骤转化率", f"{funnel_details.get('avg_step_conversion', 0)}%")
            
            st.info(f"💡 最大流失节点: {funnel_details.get('biggest_dropoff_step', '')} ({funnel_details.get('biggest_dropoff_rate', 0)}%)")
            
            st.subheader("漏斗详情")
            st.dataframe(funnel_df, use_container_width=True)
            
            st.subheader("漏斗图表")
            funnel_chart = FunnelChart.create_funnel_with_conversion(funnel_df)
            st_pyecharts(funnel_chart, height="500px")

def churn_view(db, sample_df=None):
    st.header("📉 流失分析")
    
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("开始日期", datetime.now() - timedelta(days=30), key="churn_start")
    with col2:
        end_date = st.date_input("结束日期", datetime.now(), key="churn_end")
    
    churn_days = st.slider("流失判定天数（N天未活跃视为流失）", 1, 30, 7)
    user_group = st.selectbox("选择用户分组", ["全部"] + (db.get_user_groups() if db and db.is_connected() else SampleDataGenerator().user_groups), key="churn_group")
    
    if st.button("分析流失", type="primary"):
        with st.spinner("正在分析流失..."):
            if db and db.is_connected():
                churn_analyzer = ChurnAnalyzer(db)
                group_param = None if user_group == "全部" else user_group
                churn_data = churn_analyzer.get_churn_rate(
                    str(start_date), str(end_date),
                    churn_days=churn_days,
                    user_group=group_param
                )
                churn_by_event = churn_analyzer.get_churn_by_event(
                    str(start_date), str(end_date),
                    churn_days=churn_days,
                    user_group=group_param
                )
            elif sample_df is not None:
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
                
                churn_by_event = pd.DataFrame()
            else:
                st.warning("没有可用数据")
                return
            
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
            
            if not churn_by_event.empty:
                st.subheader("各事件流失率")
                st.dataframe(churn_by_event, use_container_width=True)

def comparison_view(db, sample_df=None):
    st.header("⚖️ 路径对比分析")
    
    comparison_type = st.radio("对比类型", ["用户分组对比", "时间段对比"])
    
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("开始日期", datetime.now() - timedelta(days=14), key="comp_start")
    with col2:
        end_date = st.date_input("结束日期", datetime.now(), key="comp_end")
    
    if comparison_type == "用户分组对比":
        user_groups = db.get_user_groups() if db and db.is_connected() else SampleDataGenerator().user_groups
        
        col1, col2 = st.columns(2)
        with col1:
            group_a = st.selectbox("选择A组", user_groups, key="group_a")
        with col2:
            group_b = st.selectbox("选择B组", user_groups, key="group_b", index=1 if len(user_groups) > 1 else 0)
        
        if st.button("对比分组", type="primary"):
            with st.spinner("正在对比分析..."):
                if db and db.is_connected():
                    comparison = ComparisonAnalyzer(db)
                    result = comparison.compare_groups(
                        str(start_date), str(end_date),
                        group_a=group_a,
                        group_b=group_b
                    )
                    similarity = comparison.get_group_path_similarity(
                        str(start_date), str(end_date),
                        group_a=group_a,
                        group_b=group_b
                    )
                elif sample_df is not None:
                    from collections import defaultdict
                    
                    def get_paths(df, group):
                        group_df = df[(df['user_group'] == group) & 
                                      (df['event_time'] >= pd.Timestamp(start_date)) & 
                                      (df['event_time'] <= pd.Timestamp(end_date))]
                        session_paths = group_df.groupby(['user_id', 'session_id'])['event_name'].apply(
                            lambda x: ' -> '.join(x)
                        ).reset_index(name='path')
                        
                        paths = session_paths['path'].value_counts().reset_index()
                        paths.columns = ['path', 'count']
                        paths['percentage'] = (paths['count'] / paths['count'].sum() * 100).round(2)
                        return paths.head(20)
                    
                    paths_a = get_paths(sample_df, group_a)
                    paths_b = get_paths(sample_df, group_b)
                    
                    merged = pd.merge(
                        paths_a[['path', 'count', 'percentage']],
                        paths_b[['path', 'count', 'percentage']],
                        on='path',
                        how='outer',
                        suffixes=('_a', '_b')
                    ).fillna(0)
                    
                    merged['count_diff'] = merged['count_b'] - merged['count_a']
                    merged['count_change_pct'] = ((merged['count_b'] - merged['count_a']) / 
                                                   merged['count_a'].replace(0, 1) * 100).round(2)
                    
                    result = {
                        'group_a': group_a,
                        'group_b': group_b,
                        'comparison_data': merged.sort_values('count_a', ascending=False)
                    }
                    
                    paths_a_set = set(paths_a['path'].tolist())
                    paths_b_set = set(paths_b['path'].tolist())
                    common_paths = paths_a_set & paths_b_set
                    jaccard = len(common_paths) / len(paths_a_set | paths_b_set) if (paths_a_set | paths_b_set) else 0
                    
                    similarity = {
                        'group_a': group_a,
                        'group_b': group_b,
                        'common_paths_count': len(common_paths),
                        'unique_to_a_count': len(paths_a_set - paths_b_set),
                        'unique_to_b_count': len(paths_b_set - paths_a_set),
                        'jaccard_similarity': round(jaccard * 100, 2),
                        'common_paths': list(common_paths)[:10],
                        'unique_to_a': list(paths_a_set - paths_b_set)[:10],
                        'unique_to_b': list(paths_b_set - paths_a_set)[:10]
                    }
                else:
                    st.warning("没有可用数据")
                    return
                
                st.subheader("路径相似度")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("共同路径数", similarity.get('common_paths_count', 0))
                with col2:
                    st.metric("Jaccard相似度", f"{similarity.get('jaccard_similarity', 0)}%")
                with col3:
                    st.metric("A组独有路径数", similarity.get('unique_to_a_count', 0))
                
                st.subheader("路径对比详情")
                comparison_df = result.get('comparison_data', pd.DataFrame())
                st.dataframe(comparison_df, use_container_width=True)
    
    else:
        st.info("时间段对比功能实现类似，请参考用户分组对比")

def main():
    st.title(f"{APP_ICON} {APP_TITLE}")
    
    with st.sidebar:
        st.header("导航")
        
        page = st.radio(
            "选择功能模块",
            ["数据库初始化", "数据概览", "路径分析", "桑基图可视化", "转化漏斗", "流失分析", "路径对比"]
        )
        
        st.divider()
        
        use_sample_data = st.checkbox("使用本地示例数据（无需ClickHouse）", value=True)
    
    sample_df = None
    db = None
    
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
        db = get_db_client()
        if not db or not db.is_connected():
            st.sidebar.error("ClickHouse连接失败，请检查配置")
            st.sidebar.info("可以勾选'使用本地示例数据'来体验功能")
            return
    
    if page == "数据库初始化":
        if use_sample_data:
            st.info("已启用本地示例数据模式，无需初始化数据库")
            st.write("当前示例数据统计:")
            if sample_df is not None:
                col1, col2, col3 = st.columns(3)
                col1.metric("用户数", sample_df['user_id'].nunique())
                col2.metric("会话数", sample_df['session_id'].nunique())
                col3.metric("事件数", len(sample_df))
        else:
            init_database()
    
    elif page == "数据概览":
        dashboard_view(db, sample_df)
    
    elif page == "路径分析":
        path_analysis_view(db, sample_df)
    
    elif page == "桑基图可视化":
        sankey_view(db, sample_df)
    
    elif page == "转化漏斗":
        funnel_view(db, sample_df)
    
    elif page == "流失分析":
        churn_view(db, sample_df)
    
    elif page == "路径对比":
        comparison_view(db, sample_df)

if __name__ == "__main__":
    main()
