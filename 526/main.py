import os
import sys
import json
import tempfile
from datetime import datetime, timedelta
from typing import List, Dict, Any

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.cache_recommender import (
    CacheStrategyEngine,
    AdaptiveCacheStrategyEngine,
    AdaptiveStrategyResult,
    WarmupSimulationReport,
    PenetrationProtectionReport
)
from src.utils import (
    format_size,
    DATA_FRESHNESS_TAGS,
    format_size as format_bytes
)

st.set_page_config(
    page_title="API缓存预测工具",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main .block-container {
        padding-top: 2rem;
    }
    .stMetric {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
    }
    .cache-high {
        background-color: #d4edda;
        color: #155724;
        padding: 0.25rem 0.5rem;
        border-radius: 0.25rem;
    }
    .cache-medium {
        background-color: #fff3cd;
        color: #856404;
        padding: 0.25rem 0.5rem;
        border-radius: 0.25rem;
    }
    .cache-low {
        background-color: #f8d7da;
        color: #721c24;
        padding: 0.25rem 0.5rem;
        border-radius: 0.25rem;
    }
    .priority-critical {
        background-color: #dc3545;
        color: white;
        padding: 0.25rem 0.5rem;
        border-radius: 0.25rem;
        font-weight: bold;
    }
    .priority-high {
        background-color: #fd7e14;
        color: white;
        padding: 0.25rem 0.5rem;
        border-radius: 0.25rem;
        font-weight: bold;
    }
    .priority-medium {
        background-color: #ffc107;
        color: black;
        padding: 0.25rem 0.5rem;
        border-radius: 0.25rem;
    }
    .priority-low {
        background-color: #6c757d;
        color: white;
        padding: 0.25rem 0.5rem;
        border-radius: 0.25rem;
    }
    .freshness-realtime {
        background: linear-gradient(90deg, #dc3545, #ff6b6b);
        color: white;
        padding: 0.25rem 0.5rem;
        border-radius: 0.25rem;
        font-weight: bold;
        animation: pulse 2s infinite;
    }
    .freshness-near_realtime {
        background: linear-gradient(90deg, #fd7e14, #ffa94d);
        color: white;
        padding: 0.25rem 0.5rem;
        border-radius: 0.25rem;
        font-weight: bold;
    }
    .freshness-dynamic {
        background: linear-gradient(90deg, #17a2b8, #4dd0e1);
        color: white;
        padding: 0.25rem 0.5rem;
        border-radius: 0.25rem;
        font-weight: bold;
    }
    .freshness-semi_static {
        background: linear-gradient(90deg, #20c997, #63e6be);
        color: white;
        padding: 0.25rem 0.5rem;
        border-radius: 0.25rem;
        font-weight: bold;
    }
    .freshness-static {
        background: linear-gradient(90deg, #28a745, #69db7c);
        color: white;
        padding: 0.25rem 0.5rem;
        border-radius: 0.25rem;
        font-weight: bold;
    }
    .hot-field {
        background-color: #fff3cd;
        border-left: 4px solid #ffc107;
        padding: 0.25rem 0.5rem;
        margin: 0.125rem 0;
        border-radius: 0.25rem;
    }
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.7; }
    }
    .serialization-stats {
        background-color: #e3f2fd;
        border-left: 4px solid #2196f3;
        padding: 0.5rem;
        border-radius: 0.25rem;
        margin: 0.5rem 0;
    }
    .content-hash-badge {
        font-family: 'Courier New', monospace;
        background-color: #f5f5f5;
        padding: 0.125rem 0.375rem;
        border-radius: 0.25rem;
        font-size: 0.875rem;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def get_engine():
    """获取缓存策略引擎实例"""
    return CacheStrategyEngine()


def load_sample_data(engine: CacheStrategyEngine):
    """加载示例数据"""
    sample_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "data",
        "sample_access.log"
    )
    if os.path.exists(sample_path):
        count = engine.load_logs(sample_path)
        return count, sample_path
    return 0, None


def plot_endpoint_frequency(df: pd.DataFrame, top_n: int = 10):
    """绘制端点访问频率图"""
    if df.empty:
        return None
    
    fig, ax = plt.subplots(figsize=(10, 6))
    data = df.head(top_n).sort_values('request_count', ascending=True)
    
    bars = ax.barh(data['pattern'], data['request_count'], color='#4CAF50')
    ax.set_xlabel('请求次数')
    ax.set_ylabel('端点模式')
    ax.set_title(f'Top {top_n} 最常访问端点')
    
    for i, (bar, count) in enumerate(zip(bars, data['request_count'])):
        width = bar.get_width()
        ax.text(width + 0.5, bar.get_y() + bar.get_height()/2,
                f'{int(count)}', va='center')
    
    plt.tight_layout()
    return fig


def plot_time_distribution(time_data: Dict[int, int]):
    """绘制时间分布图"""
    if not time_data:
        return None
    
    fig, ax = plt.subplots(figsize=(12, 4))
    hours = sorted(time_data.keys())
    counts = [time_data[h] for h in hours]
    
    ax.plot(hours, counts, marker='o', linewidth=2, markersize=6, color='#2196F3')
    ax.fill_between(hours, counts, alpha=0.3, color='#2196F3')
    ax.set_xlabel('小时')
    ax.set_ylabel('请求次数')
    ax.set_title('24小时请求分布')
    ax.set_xticks(range(0, 24, 2))
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    return fig


def plot_cache_benefit_chart(recommendations: List[Any]):
    """绘制缓存收益图"""
    if not recommendations:
        return None
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    
    cache_levels = {'response': 0, 'field': 0, 'none': 0}
    for rec in recommendations:
        cache_levels[rec.cache_level] = cache_levels.get(rec.cache_level, 0) + 1
    
    colors = ['#4CAF50', '#FFC107', '#9E9E9E']
    labels = ['响应级缓存', '字段级缓存', '不建议缓存']
    sizes = [cache_levels.get('response', 0), cache_levels.get('field', 0), cache_levels.get('none', 0)]
    
    ax1.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
    ax1.set_title('缓存级别分布')
    
    priorities = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
    for rec in recommendations:
        priorities[rec.priority] = priorities.get(rec.priority, 0) + 1
    
    prio_colors = ['#dc3545', '#fd7e14', '#ffc107', '#6c757d']
    prio_labels = ['关键', '高', '中', '低']
    prio_sizes = [priorities.get('critical', 0), priorities.get('high', 0),
                  priorities.get('medium', 0), priorities.get('low', 0)]
    
    ax2.pie(prio_sizes, labels=prio_labels, colors=prio_colors, autopct='%1.1f%%', startangle=90)
    ax2.set_title('优先级分布')
    
    plt.tight_layout()
    return fig


def plot_field_redundancy(field_data: List[Any], top_n: int = 10):
    """绘制字段冗余度图"""
    if not field_data:
        return None
    
    fig, ax = plt.subplots(figsize=(10, 6))
    data = sorted(field_data, key=lambda x: x.redundancy_ratio, reverse=True)[:top_n]
    data = list(reversed(data))
    
    fields = [f.field_path for f in data]
    ratios = [f.redundancy_ratio for f in data]
    
    colors = ['#4CAF50' if r >= 0.7 else '#FFC107' if r >= 0.3 else '#9E9E9E' for r in ratios]
    
    bars = ax.barh(fields, ratios, color=colors)
    ax.set_xlabel('冗余比率')
    ax.set_ylabel('字段路径')
    ax.set_title(f'Top {top_n} 字段冗余度')
    ax.set_xlim(0, 1)
    
    for i, (bar, ratio) in enumerate(zip(bars, ratios)):
        width = bar.get_width()
        ax.text(width + 0.01, bar.get_y() + bar.get_height()/2,
                f'{ratio:.1%}', va='center')
    
    plt.tight_layout()
    return fig


def get_priority_class(priority: str) -> str:
    """获取优先级CSS类"""
    return {
        'critical': 'priority-critical',
        'high': 'priority-high',
        'medium': 'priority-medium',
        'low': 'priority-low'
    }.get(priority, 'priority-low')


def get_cache_level_class(level: str) -> str:
    """获取缓存级别CSS类"""
    return {
        'response': 'cache-high',
        'field': 'cache-medium',
        'none': 'cache-low'
    }.get(level, 'cache-low')


def get_freshness_class(tag: str) -> str:
    """获取时效性标签CSS类"""
    return {
        'realtime': 'freshness-realtime',
        'near_realtime': 'freshness-near_realtime',
        'dynamic': 'freshness-dynamic',
        'semi_static': 'freshness-semi_static',
        'static': 'freshness-static'
    }.get(tag, 'freshness-dynamic')


def get_freshness_display(tag: str) -> str:
    """获取时效性标签显示文本"""
    display_map = {
        'realtime': '🔴 实时数据',
        'near_realtime': '🟠 近实时数据',
        'dynamic': '🔵 动态数据',
        'semi_static': '🟢 半静态数据',
        'static': '💚 静态数据'
    }
    return display_map.get(tag, '🔵 动态数据')


def format_ttl(seconds: int) -> str:
    """格式化TTL显示"""
    if seconds < 60:
        return f"{seconds}秒"
    elif seconds < 3600:
        return f"{seconds // 60}分钟"
    elif seconds < 86400:
        return f"{seconds // 3600}小时{seconds % 3600 // 60}分钟"
    else:
        return f"{seconds // 86400}天{seconds % 86400 // 3600}小时"


def main():
    st.title("📊 API响应缓存预测工具")
    st.markdown("---")
    
    engine = get_engine()
    
    with st.sidebar:
        st.header("📁 数据加载")
        
        data_source = st.radio(
            "选择数据源",
            ["使用示例数据", "上传日志文件"]
        )
        
        if data_source == "使用示例数据":
            if st.button("加载示例数据", type="primary", use_container_width=True):
                with st.spinner("正在加载示例数据..."):
                    count, path = load_sample_data(engine)
                    if count > 0:
                        st.success(f"成功加载 {count} 条日志记录")
                        st.session_state['data_loaded'] = True
                    else:
                        st.error("加载示例数据失败")
        else:
            uploaded_file = st.file_uploader(
                "上传访问日志文件",
                type=['log', 'txt', 'json'],
                help="支持Nginx格式、JSON格式的访问日志"
            )
            
            if uploaded_file is not None:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.log') as tmp:
                    tmp.write(uploaded_file.getvalue())
                    tmp_path = tmp.name
                
                try:
                    count = engine.load_logs(tmp_path)
                    if count > 0:
                        st.success(f"成功加载 {count} 条日志记录")
                        st.session_state['data_loaded'] = True
                    else:
                        st.warning("未能解析任何有效日志记录")
                finally:
                    os.unlink(tmp_path)
        
        if st.session_state.get('data_loaded', False):
            st.divider()
            st.header("⚙️ 分析设置")
            
            st.slider(
                "Top N 端点",
                min_value=5,
                max_value=30,
                value=15,
                key='top_n'
            )
            
            st.slider(
                "最小缓存命中率阈值",
                min_value=0.1,
                max_value=0.9,
                value=0.3,
                step=0.1,
                key='hit_rate_threshold'
            )
            
            st.divider()
            
            if st.button("🔄 重新分析", use_container_width=True):
                st.cache_resource.clear()
                st.rerun()
            
            if st.button("💾 导出推荐结果", use_container_width=True):
                export_path = os.path.join(
                    os.path.dirname(os.path.abspath(__file__)),
                    "cache_recommendations.json"
                )
                engine.export_recommendations(export_path)
                st.success(f"推荐结果已导出到: {export_path}")
    
    if not st.session_state.get('data_loaded', False):
        st.info("👈 请从左侧边栏加载数据开始分析")
        
        st.markdown("### 功能介绍")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.info("📈 **访问日志分析**\n\n解析多种格式的访问日志，分析请求模式和重复率")
        
        with col2:
            st.info("🤖 **机器学习预测**\n\n使用随机森林模型预测缓存命中率，优化TTL配置")
        
        with col3:
            st.info("🔍 **布隆过滤器**\n\n高效判断缓存存在性，支持端点级和字段级缓存")
        
        with col4:
            st.info("💡 **智能推荐**\n\n提供响应级和字段级缓存策略推荐，估算存储节省")
        
        return
    
    with st.spinner("正在分析数据..."):
        basic_stats = engine.analyzer.get_basic_stats()
        endpoint_freq = engine.analyzer.get_endpoint_frequency(st.session_state['top_n'])
        duplication_stats = engine.analyzer.analyze_duplication_patterns()
        similarity_analysis = engine.analyzer.analyze_response_similarity()
        
        training_results = engine.train_models()
        benefit_analysis = engine.analyze_cache_benefit()
    
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "📊 总览",
        "📈 访问模式分析",
        "🎯 缓存预测",
        "💡 缓存推荐",
        "🔍 布隆过滤器",
        "🔄 自适应策略",
        "🔥 预热模拟",
        "🛡️ 穿透防护"
    ])
    
    with tab1:
        st.subheader("分析总览")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "总请求数",
                f"{basic_stats.get('total_requests', 0):,}",
                help="分析的总请求数量"
            )
        
        with col2:
            st.metric(
                "独立端点数",
                f"{basic_stats.get('unique_patterns', 0):,}",
                help="去重后的API端点模式数量"
            )
        
        with col3:
            duplication_ratio = duplication_stats.get('duplication_ratio', 0)
            st.metric(
                "请求重复率",
                f"{duplication_ratio:.1%}",
                delta=f"+{duplication_ratio:.1%}" if duplication_ratio > 0.5 else f"{duplication_ratio:.1%}",
                help="重复请求占总请求的比例"
            )
        
        with col4:
            hit_rate = benefit_analysis.estimated_hit_rate
            st.metric(
                "预测缓存命中率",
                f"{hit_rate:.1%}",
                help="基于历史数据预测的缓存命中率"
            )
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            savings = benefit_analysis.estimated_savings_bytes
            st.metric(
                "预估存储节省",
                format_size(savings),
                f"{benefit_analysis.estimated_savings_percent:.1%}",
                help="实施缓存后预计节省的存储空间"
            )
        
        with col2:
            latency_reduction = benefit_analysis.estimated_latency_reduction_ms
            st.metric(
                "预估延迟降低",
                f"{latency_reduction:.1f} ms",
                help="平均响应时间减少量"
            )
        
        with col3:
            st.metric(
                "可缓存请求数",
                f"{benefit_analysis.cacheable_requests:,}",
                f"{benefit_analysis.cacheable_requests / basic_stats.get('total_requests', 1):.1%}",
                help="适合缓存的请求数量"
            )
        
        st.subheader("时间范围")
        time_span = basic_stats.get('time_span', {})
        if time_span:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.info(f"🕐 开始时间: {time_span.get('start', 'N/A')}")
            with col2:
                st.info(f"🕒 结束时间: {time_span.get('end', 'N/A')}")
            with col3:
                duration = time_span.get('duration_hours', 0)
                st.info(f"⏱️ 持续时间: {duration:.1f} 小时 ({time_span.get('duration_days', 0):.2f} 天)")
        
        st.divider()
        
        st.subheader("Top 可缓存端点")
        if benefit_analysis.top_endpoints:
            top_df = pd.DataFrame(benefit_analysis.top_endpoints)
            top_df = top_df[[
                'pattern', 'request_count', 'total_response_size',
                'avg_interval_seconds', 'saving_potential_formatted'
            ]]
            top_df.columns = ['端点模式', '请求次数', '总响应大小', '平均间隔(秒)', '节省潜力']
            st.dataframe(top_df, use_container_width=True, hide_index=True)
    
    with tab2:
        st.subheader("访问模式分析")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**端点访问频率**")
            freq_fig = plot_endpoint_frequency(endpoint_freq, st.session_state['top_n'])
            if freq_fig:
                st.pyplot(freq_fig)
        
        with col2:
            st.markdown("**24小时请求分布**")
            time_based = duplication_stats.get('time_based_duplication', {})
            hourly_dist = time_based.get('hourly_distribution', {})
            time_fig = plot_time_distribution(hourly_dist)
            if time_fig:
                st.pyplot(time_fig)
        
        st.divider()
        
        st.subheader("响应时间统计")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            avg_rt = basic_stats.get('avg_response_time_ms', 0)
            st.metric("平均响应时间", f"{avg_rt:.1f} ms")
        
        with col2:
            p50_rt = basic_stats.get('p50_response_time_ms', 0)
            st.metric("P50 响应时间", f"{p50_rt:.1f} ms")
        
        with col3:
            p95_rt = basic_stats.get('p95_response_time_ms', 0)
            st.metric("P95 响应时间", f"{p95_rt:.1f} ms")
        
        st.divider()
        
        st.subheader("请求方法分布")
        method_dist = basic_stats.get('method_distribution', {})
        if method_dist:
            method_df = pd.DataFrame({
                '方法': list(method_dist.keys()),
                '数量': list(method_dist.values())
            })
            col1, col2 = st.columns([1, 1])
            with col1:
                st.dataframe(method_df, use_container_width=True, hide_index=True)
            with col2:
                fig, ax = plt.subplots(figsize=(6, 4))
                ax.bar(method_df['方法'], method_df['数量'], color='#2196F3')
                ax.set_ylabel('请求数量')
                ax.set_title('请求方法分布')
                st.pyplot(fig)
        
        st.divider()
        
        st.subheader("重复请求模式")
        dup_df = duplication_stats.get('endpoint_duplication_stats', pd.DataFrame())
        if not dup_df.empty:
            display_df = dup_df[[
                'pattern', 'request_count', 'avg_interval_seconds',
                'total_response_size', 'avg_response_time'
            ]].copy()
            display_df.columns = [
                '端点模式', '请求次数', '平均间隔(秒)', '总响应大小', '平均响应时间(ms)'
            ]
            st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    with tab3:
        st.subheader("缓存预测分析")
        
        if 'cache_predictor' in training_results and 'error' not in training_results['cache_predictor']:
            training_info = training_results['cache_predictor']
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    "模型准确率",
                    f"{training_info.get('accuracy', 0):.1%}",
                    help="预测模型在测试集上的准确率"
                )
            
            with col2:
                st.metric(
                    "交叉验证准确率",
                    f"{training_info.get('cv_accuracy_mean', 0):.1%} ± {training_info.get('cv_accuracy_std', 0):.1%}",
                    help="5折交叉验证的准确率"
                )
            
            with col3:
                st.metric(
                    "训练样本数",
                    f"{training_info.get('training_samples', 0):,}",
                    help="用于训练模型的样本数量"
                )
            
            st.divider()
            
            feature_importance = engine.cache_predictor.get_feature_importance()
            if feature_importance:
                st.subheader("特征重要性")
                fi_df = pd.DataFrame({
                    '特征': list(feature_importance.keys()),
                    '重要性': list(feature_importance.values())
                }).sort_values('重要性', ascending=False).head(10)
                
                col1, col2 = st.columns([1, 1])
                with col1:
                    st.dataframe(fi_df, use_container_width=True, hide_index=True)
                with col2:
                    fig, ax = plt.subplots(figsize=(8, 5))
                    data = fi_df.sort_values('重要性', ascending=True)
                    ax.barh(data['特征'], data['重要性'], color='#9C27B0')
                    ax.set_xlabel('重要性')
                    ax.set_title('Top 10 重要特征')
                    st.pyplot(fig)
        else:
            st.info("使用基于规则的预测模型（数据量不足时使用）")
        
        st.divider()
        
        chart_fig = plot_cache_benefit_chart(benefit_analysis.recommendations)
        if chart_fig:
            st.pyplot(chart_fig)
        
        st.divider()
        
        st.subheader("响应相似度分析")
        if not similarity_analysis.get('similarity_details', pd.DataFrame()).empty:
            sim_df = similarity_analysis['similarity_details']
            display_sim = sim_df[[
                'pattern', 'response_count', 'total_fields',
                'avg_response_size', 'overall_redundancy'
            ]].copy()
            display_sim['overall_redundancy'] = display_sim['overall_redundancy'].apply(
                lambda x: f"{x:.1%}"
            )
            display_sim.columns = [
                '端点模式', '响应次数', '字段总数', '平均响应大小', '整体冗余度'
            ]
            st.dataframe(display_sim, use_container_width=True, hide_index=True)
    
    with tab4:
        st.subheader("缓存策略推荐")
        
        if not benefit_analysis.recommendations:
            st.info("没有足够的数据生成缓存推荐")
            return
        
        filter_level = st.multiselect(
            "筛选缓存级别",
            ['response', 'field', 'none'],
            default=['response', 'field'],
            format_func=lambda x: {
                'response': '响应级缓存',
                'field': '字段级缓存',
                'none': '不建议缓存'
            }[x]
        )
        
        filter_priority = st.multiselect(
            "筛选优先级",
            ['critical', 'high', 'medium', 'low'],
            default=['critical', 'high', 'medium'],
            format_func=lambda x: {
                'critical': '🔴 关键',
                'high': '🟠 高',
                'medium': '🟡 中',
                'low': '⚪ 低'
            }[x]
        )
        
        filter_freshness = st.multiselect(
            "筛选数据时效性",
            ['realtime', 'near_realtime', 'dynamic', 'semi_static', 'static'],
            default=['realtime', 'near_realtime', 'dynamic', 'semi_static', 'static'],
            format_func=lambda x: get_freshness_display(x)
        )
        
        filtered_recs = [
            r for r in benefit_analysis.recommendations
            if r.cache_level in filter_level 
            and r.priority in filter_priority
            and r.freshness_tag in filter_freshness
        ]
        
        content_hash_dup = benefit_analysis.content_hash_duplication
        if content_hash_dup and content_hash_dup.get('total_duplicate_groups', 0) > 0:
            st.info(f"""
            🔍 **内容哈希分析结果**: 发现 {content_hash_dup.get('total_duplicate_groups', 0)} 组相同内容, 
            涉及 {content_hash_dup.get('total_same_content_requests', 0)} 次请求, 
            潜在节省 {format_size(content_hash_dup.get('potential_savings_bytes', 0))}
            """)
        
        st.markdown(f"**共 {len(filtered_recs)} 条推荐**")
        
        for i, rec in enumerate(filtered_recs, 1):
            with st.expander(f"{i}. {rec.endpoint}", expanded=(i <= 3)):
                col1, col2, col3, col4, col5 = st.columns(5)
                
                with col1:
                    st.markdown("**缓存级别**")
                    st.markdown(
                        f'<span class="{get_cache_level_class(rec.cache_level)}">'
                        f'{"响应级缓存" if rec.cache_level == "response" else "字段级缓存" if rec.cache_level == "field" else "不建议缓存"}'
                        f'</span>',
                        unsafe_allow_html=True
                    )
                
                with col2:
                    st.markdown("**优先级**")
                    st.markdown(
                        f'<span class="{get_priority_class(rec.priority)}">'
                        f'{"🔴 关键" if rec.priority == "critical" else "🟠 高" if rec.priority == "high" else "🟡 中" if rec.priority == "medium" else "⚪ 低"}'
                        f'</span>',
                        unsafe_allow_html=True
                    )
                
                with col3:
                    st.markdown("**数据时效性**")
                    st.markdown(
                        f'<span class="{get_freshness_class(rec.freshness_tag)}">'
                        f'{get_freshness_display(rec.freshness_tag)}'
                        f'</span>',
                        unsafe_allow_html=True
                    )
                
                with col4:
                    st.metric("预测命中率", f"{rec.predicted_hit_rate:.1%}")
                
                with col5:
                    st.metric("推荐TTL", format_ttl(rec.recommended_ttl))
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric(
                        "预估节省",
                        format_size(rec.estimated_savings_bytes),
                        f"{rec.estimated_savings_percent:.1%}"
                    )
                
                with col2:
                    st.metric("置信度", f"{rec.confidence:.1%}")
                
                with col3:
                    st.metric("请求次数", f"{len(engine.analyzer.get_requests_dataframe()[engine.analyzer.get_requests_dataframe()['pattern'] == rec.endpoint]):,}")
                
                if rec.content_hash:
                    st.markdown(f"**内容哈希:** <span class='content-hash-badge'>{rec.content_hash[:16]}...</span>", unsafe_allow_html=True)
                
                if rec.normalized_params:
                    with st.expander("📋 归一化参数", expanded=False):
                        st.json(rec.normalized_params)
                
                if rec.original_size_bytes > 0:
                    st.markdown("**📦 序列化统计:**")
                    st.markdown(
                        f'<div class="serialization-stats">'
                        f'原始大小: <b>{format_size(rec.original_size_bytes)}</b> | '
                        f'序列化后: <b>{format_size(rec.serialized_size_bytes)}</b> | '
                        f'节省: <b>{rec.serialization_savings_percent:.1%}</b>'
                        f'</div>',
                        unsafe_allow_html=True
                    )
                
                if rec.hot_fields:
                    st.markdown(f"**🔥 热点字段 ({len(rec.hot_fields)} 个):**")
                    for field in rec.hot_fields[:10]:
                        st.markdown(f'<div class="hot-field">🔥 {field}</div>', unsafe_allow_html=True)
                    if len(rec.hot_fields) > 10:
                        st.markdown(f"... 还有 {len(rec.hot_fields) - 10} 个字段")
                
                if rec.fields_to_cache:
                    st.markdown("**建议缓存的字段:**")
                    st.code(", ".join(rec.fields_to_cache), language="text")
                
                if rec.fields_to_exclude:
                    st.markdown("**建议排除的字段:**")
                    st.code(", ".join(rec.fields_to_exclude), language="text")
                
                st.markdown("**推荐理由:**")
                for reason in rec.reasoning:
                    st.markdown(f"- {reason}")
                
                if st.button("🔧 优化TTL配置", key=f"ttl_opt_{i}"):
                    ttl_result = engine.optimize_ttl_for_endpoint(rec.endpoint)
                    if ttl_result:
                        st.markdown("**TTL优化建议:**")
                        st.json(ttl_result)
                
                field_recs = engine.get_field_level_analysis(rec.endpoint)
                if field_recs:
                    st.markdown("**字段级分析:**")
                    field_fig = plot_field_redundancy(field_recs, top_n=10)
                    if field_fig:
                        st.pyplot(field_fig)
                    
                    field_df = pd.DataFrame([{
                        '字段路径': f.field_path,
                        '热度评分': f"{f.hotness_score:.2f}",
                        '综合评分': f"{f.combined_score:.2f}",
                        '冗余比率': f"{f.redundancy_ratio:.1%}",
                        '唯一值数量': f.unique_values,
                        '总数量': f.total_values,
                        '建议': '✅ 缓存' if f.recommended_action == 'cache' else '🤔 考虑' if f.recommended_action == 'consider' else '❌ 排除',
                        '预估节省': format_size(f.estimated_savings_bytes)
                    } for f in field_recs])
                    st.dataframe(field_df, use_container_width=True, hide_index=True)
    
    with tab5:
        st.subheader("布隆过滤器状态")
        
        bloom_stats = benefit_analysis.bloom_filter_stats
        if bloom_stats:
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**端点过滤器**")
                ep_filter = bloom_stats.get('endpoint_filter', {})
                st.info(f"""
                - 容量: {ep_filter.get('capacity', 0):,}
                - 已存储: {ep_filter.get('items_count', 0):,}
                - 位数组大小: {ep_filter.get('bit_size', 0):,} bits
                - 哈希函数数量: {ep_filter.get('hash_count', 0)}
                - 内存使用: {ep_filter.get('memory_usage_kb', 0):.2f} KB
                - 当前误报率: {ep_filter.get('current_fpr', 0):.4%}
                """)
            
            with col2:
                st.markdown("**字段过滤器**")
                f_filter = bloom_stats.get('field_filter', {})
                st.info(f"""
                - 容量: {f_filter.get('capacity', 0):,}
                - 已存储: {f_filter.get('items_count', 0):,}
                - 位数组大小: {f_filter.get('bit_size', 0):,} bits
                - 哈希函数数量: {f_filter.get('hash_count', 0)}
                - 内存使用: {f_filter.get('memory_usage_kb', 0):.2f} KB
                - 当前误报率: {f_filter.get('current_fpr', 0):.4%}
                """)
            
            st.divider()
            
            st.markdown("**测试端点缓存存在性**")
            test_endpoint = st.text_input("输入要检查的端点路径", value="/api/v1/products")
            if st.button("检查"):
                result = engine.check_cache_exists(test_endpoint)
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("可能存在", "✅ 是" if result['may_exist'] else "❌ 否")
                with col2:
                    st.metric("历史请求次数", result['historical_count'])
                with col3:
                    st.metric("缓存命中概率", f"{result['cache_hit_probability']:.1%}")
            
            st.divider()
            
            st.subheader("布隆过滤器原理")
            st.markdown("""
            布隆过滤器是一种空间效率很高的概率性数据结构，用于判断一个元素是否在一个集合中。
            
            **特点:**
            - ✅ 空间效率极高：仅需少量内存即可存储大量元素
            - ✅ 查询速度极快：O(k) 时间复杂度，k为哈希函数数量
            - ⚠️ 存在误报率：可能会把不存在的元素判断为存在，但不会把存在的判断为不存在
            - ❌ 不支持删除：标准布隆过滤器不支持删除操作
            
            **在本系统中的应用:**
            1. **端点级缓存检查**：快速判断某个API端点是否已被缓存
            2. **字段级缓存检查**：判断响应中的特定字段是否可缓存
            3. **预热优化**：基于历史数据提前填充布隆过滤器，优化缓存判断
            """)
    
    with tab6:
        st.subheader("🔄 自适应缓存策略")
        st.markdown("实时监控缓存指标，自动调整缓存参数以优化性能")
        
        adaptive_engine = AdaptiveCacheStrategyEngine(engine)
        
        with st.expander("⚙️ 策略配置", expanded=False):
            col1, col2, col3 = st.columns(3)
            with col1:
                min_hit_rate = st.slider("最低命中率阈值", 0.0, 1.0, 0.5, 0.05)
                target_hit_rate = st.slider("目标命中率", 0.0, 1.0, 0.75, 0.05)
            with col2:
                max_memory_ratio = st.slider("最大内存使用率", 0.0, 1.0, 0.9, 0.05)
                ttl_adjust_factor = st.slider("TTL调整因子", 0.1, 0.5, 0.2, 0.05)
            with col3:
                check_interval = st.slider("检查间隔(秒)", 60, 3600, 300, 60)
                hotness_threshold = st.slider("热度阈值", 0.0, 1.0, 0.4, 0.05)
        
        adaptive_engine.config.min_hit_rate_threshold = min_hit_rate
        adaptive_engine.config.target_hit_rate = target_hit_rate
        adaptive_engine.config.max_memory_usage_ratio = max_memory_ratio
        adaptive_engine.config.ttl_adjustment_factor = ttl_adjust_factor
        adaptive_engine.config.check_interval_seconds = check_interval
        adaptive_engine.config.hotness_threshold = hotness_threshold
        
        state = adaptive_engine.analyze_current_state()
        if 'error' not in state:
            current_metrics = state['current_metrics']
            
            st.markdown("### 📊 当前缓存状态")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("当前命中率", f"{current_metrics.hit_rate:.1%}")
            with col2:
                st.metric("请求总数", f"{current_metrics.request_count:,}")
            with col3:
                st.metric("内存使用", format_size(current_metrics.memory_usage_bytes))
            with col4:
                memory_ratio = (current_metrics.memory_usage_bytes / current_metrics.memory_limit_bytes 
                              if current_metrics.memory_limit_bytes > 0 else 0)
                st.metric("内存使用率", f"{memory_ratio:.1%}")
            
            st.divider()
            
            st.markdown("### 📈 自适应策略建议")
            recommendations = adaptive_engine.generate_adaptive_recommendations()
            
            if recommendations:
                for i, rec in enumerate(recommendations[:5], 1):
                    with st.expander(f"{i}. {rec.endpoint}", expanded=(i == 1)):
                        st.markdown(f"**分析时间**: {rec.analysis_timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
                        
                        if rec.trend_analysis.get('insufficient_data'):
                            st.info("📊 趋势分析数据不足，需要更多历史记录")
                        else:
                            trend = rec.trend_analysis.get('hit_rate_trend', 'stable')
                            trend_icon = "📈" if trend == 'rising' else "📉" if trend == 'falling' else "➡️"
                            st.info(f"{trend_icon} 命中率趋势: {trend}")
                        
                        if rec.recommended_adjustments:
                            st.markdown("#### 建议调整:")
                            for adj in rec.recommended_adjustments:
                                adj_type_display = {
                                    'ttl_increase': '⏫ TTL增加',
                                    'ttl_decrease': '⏬ TTL减少',
                                    'field_cache_expansion': '📦 字段缓存扩展'
                                }.get(adj.adjustment_type, adj.adjustment_type)
                                
                                st.warning(f"""
                                **{adj_type_display}**  
                                原因: {adj.reason}  
                                当前值: `{adj.previous_value}` → 建议值: `{adj.new_value}`  
                                预期提升: {adj.expected_improvement:.1%} (置信度: {adj.confidence:.1%})
                                """)
                        else:
                            st.success("✅ 当前策略运行良好，无需调整")
            else:
                st.info("暂无可调整的策略建议")
        else:
            st.info("请先加载数据进行分析")
    
    with tab7:
        st.subheader("🔥 缓存预热模拟")
        st.markdown("模拟缓存预热效果，预估命中率提升和性能改善")
        
        warmup_duration = st.slider("预定时长(分钟)", 5, 120, 30, 5)
        
        adaptive_engine = AdaptiveCacheStrategyEngine(engine)
        
        with st.spinner("正在模拟预热过程..."):
            warmup_report = adaptive_engine.simulate_warmup(warmup_duration)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(
                "预热前命中率",
                f"{warmup_report.overall_result['original_hit_rate']:.1%}"
            )
        with col2:
            st.metric(
                "预热后命中率",
                f"{warmup_report.overall_result['warmed_hit_rate']:.1%}",
                f"+{warmup_report.total_estimated_hit_rate_improvement:.1%}"
            )
        with col3:
            st.metric(
                "预估延迟降低",
                f"{warmup_report.total_estimated_latency_improvement_ms:.1f} ms"
            )
        
        st.divider()
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric(
                "预加载数据量",
                f"{len(warmup_report.preload_plan)} 个端点"
            )
        with col2:
            st.metric(
                "预估内存占用",
                format_size(warmup_report.total_estimated_memory_bytes)
            )
        
        st.divider()
        
        st.markdown("### 📋 预热计划")
        if warmup_report.preload_plan:
            plan_df = pd.DataFrame(warmup_report.preload_plan)
            plan_df['estimated_size'] = plan_df['estimated_size_bytes'].apply(format_size)
            
            priority_map = {'critical': '🔴 关键', 'high': '🟠 高', 'normal': '🟡 中'}
            plan_df['priority_display'] = plan_df['priority'].map(priority_map)
            
            display_df = plan_df[[
                'endpoint', 'priority_display', 'hotness', 
                'request_count', 'estimated_size'
            ]].copy()
            display_df.columns = [
                '端点', '优先级', '热度', '请求次数', '预估大小'
            ]
            display_df['热度'] = display_df['热度'].apply(lambda x: f"{x:.2f}")
            
            st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        st.divider()
        
        st.markdown("### 🔄 预热阶段")
        stages = [
            {"阶段": "1️⃣ 关键数据预加载", "时长": "前5分钟", "目标": "Top 20%热点数据", "说明": "立即加载最关键的热点数据，快速提升命中率"},
            {"阶段": "2️⃣ 渐进加载", "时长": f"5-{warmup_duration}分钟", "目标": "剩余热点数据", "说明": "逐步加载剩余热点数据，避免影响系统性能"},
            {"阶段": "3️⃣ 持续监控", "时长": "预热完成后", "目标": "命中率稳定", "说明": "持续监控命中率，动态调整预热策略"}
        ]
        st.table(pd.DataFrame(stages))
    
    with tab8:
        st.subheader("🛡️ 缓存穿透防护")
        st.markdown("检测缓存穿透风险，提供布隆过滤和热点数据预加载防护方案")
        
        adaptive_engine = AdaptiveCacheStrategyEngine(engine)
        
        with st.spinner("正在分析穿透风险..."):
            protection_report = adaptive_engine.analyze_penetration_risks()
        
        risk_level_colors = {
            'high': 'background: linear-gradient(90deg, #dc3545, #ff6b6b); color: white; padding: 0.5rem 1rem; border-radius: 0.5rem; font-weight: bold;',
            'medium': 'background: linear-gradient(90deg, #fd7e14, #ffa94d); color: white; padding: 0.5rem 1rem; border-radius: 0.5rem; font-weight: bold;',
            'low': 'background: linear-gradient(90deg, #40c057, #69db7c); color: white; padding: 0.5rem 1rem; border-radius: 0.5rem; font-weight: bold;'
        }
        
        col1, col2, col3 = st.columns(3)
        with col1:
            risk_display = {
                'high': '🔴 高风险',
                'medium': '🟠 中风险',
                'low': '🟢 低风险'
            }.get(protection_report.overall_risk_level, '🟢 低风险')
            st.metric("整体风险等级", risk_display)
        with col2:
            st.metric(
                "布隆过滤器覆盖率",
                f"{protection_report.bloom_filter_coverage:.1%}"
            )
        with col3:
            st.metric(
                "空值缓存数量",
                protection_report.null_value_cache_stats['cached_count']
            )
        
        st.divider()
        
        st.markdown("### ⚠️ 检测到的穿透风险")
        if protection_report.detected_risks:
            risk_df = pd.DataFrame(protection_report.detected_risks)
            risk_df['miss_rate_display'] = risk_df['miss_rate'].apply(lambda x: f"{x:.1%}")
            
            display_df = risk_df[[
                'endpoint', 'request_count', 'miss_rate_display', 
                'risk_level', 'recommendation'
            ]].copy()
            display_df.columns = [
                '端点', '请求次数', '未命中率', '风险等级', '建议'
            ]
            
            def highlight_risk(row):
                if row['风险等级'] == 'high':
                    return ['background-color: #ffebee'] * len(row)
                elif row['风险等级'] == 'medium':
                    return ['background-color: #fff3e0'] * len(row)
                return [''] * len(row)
            
            st.dataframe(
                display_df.style.apply(highlight_risk, axis=1),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.success("✅ 未检测到明显的穿透风险")
        
        st.divider()
        
        st.markdown("### 🔐 防护配置")
        config = protection_report.protection_config
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"""
            **布隆过滤器**: {'✅ 启用' if config.bloom_filter_enabled else '❌ 禁用'}  
            **空值缓存**: {'✅ 启用' if config.null_value_caching else '❌ 禁用'}  
            **空值TTL**: {config.null_value_ttl_seconds}秒
            """)
        with col2:
            st.info(f"""
            **热点预加载**: {'✅ 启用' if config.hot_data_preload else '❌ 禁用'}  
            **预加载阈值**: {config.preload_threshold:.1%}  
            **最大预加载数**: {config.max_preload_count}
            """)
        
        st.divider()
        
        st.markdown("### 📦 热点数据预加载计划")
        preload_plan = adaptive_engine.generate_hot_data_preload_plan(top_n=20)
        if preload_plan:
            plan_df = pd.DataFrame(preload_plan)
            plan_df['size_display'] = plan_df['estimated_size_bytes'].apply(format_size)
            plan_df['ttl_display'] = plan_df['recommended_ttl'].apply(lambda x: f"{x//60}分钟")
            
            priority_map = {'critical': '🔴', 'high': '🟠', 'medium': '🟡', 'low': '⚪'}
            plan_df['priority_icon'] = plan_df['priority'].map(priority_map)
            
            display_df = plan_df[[
                'priority_icon', 'endpoint', 'hotness', 
                'request_count', 'size_display', 'ttl_display'
            ]].copy()
            display_df.columns = [
                '', '端点', '热度', '请求次数', '预估大小', '推荐TTL'
            ]
            display_df['热度'] = display_df['热度'].apply(lambda x: f"{x:.2f}")
            
            st.dataframe(display_df, use_container_width=True, hide_index=True)
            
            st.download_button(
                "📥 下载预加载计划",
                json.dumps(preload_plan, ensure_ascii=False, indent=2),
                "preload_plan.json",
                "application/json"
            )
        else:
            st.info("暂无可预加载的热点数据")


if __name__ == "__main__":
    if 'data_loaded' not in st.session_state:
        st.session_state['data_loaded'] = False
    
    main()
