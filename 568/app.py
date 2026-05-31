import streamlit as st
import json
import pandas as pd
from typing import Optional
import io

from config import AppConfig, DatabaseConfig, RewriteConfig
from sql_analyzer import SQLParser
from rewriter import SQLRewriter, RewriteResult
from performance import PerformanceComparator, PerformanceComparisonResult
from execution_plan import (
    MySQLExecutionPlanAnalyzer,
    PostgreSQLExecutionPlanAnalyzer,
)
from slow_query_log import SlowQueryLogParser, LogReplayer
from index_optimizer import IndexRecommender, IndexRewriteCoordinator
from deployment import SQLDeployer, DeploymentStatus
from monitoring import PerformanceTracker, TrackingConfig

st.set_page_config(
    page_title="慢SQL自动重写工具",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    .main .block-container {
        padding-top: 2rem;
    }
    .css-1d391kg {
        background: rgba(255, 255, 255, 0.95);
    }
    .stButton>button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 0.75rem 2rem;
        border-radius: 10px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 20px rgba(102, 126, 234, 0.4);
    }
    .sql-box {
        background: #1e1e1e;
        color: #d4d4d4;
        padding: 1rem;
        border-radius: 10px;
        font-family: 'Consolas', 'Monaco', monospace;
        font-size: 0.9rem;
        line-height: 1.6;
        overflow-x: auto;
    }
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        text-align: center;
    }
    .improvement-positive {
        color: #22c55e;
        font-size: 1.5rem;
        font-weight: bold;
    }
    .improvement-negative {
        color: #ef4444;
        font-size: 1.5rem;
        font-weight: bold;
    }
    .status-success {
        background: #dcfce7;
        color: #166534;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: 600;
    }
    .status-error {
        background: #fee2e2;
        color: #991b1b;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: 600;
    }
    </style>
""", unsafe_allow_html=True)

EXAMPLE_SQLS = {
    "子查询优化": """
SELECT *
FROM orders o
WHERE o.customer_id IN (
    SELECT c.id
    FROM customers c
    WHERE c.country = 'China'
    AND c.status = 'active'
)
AND o.order_date >= '2024-01-01'
AND o.total_amount > 1000
ORDER BY o.order_date DESC
LIMIT 100
    """.strip(),
    "OR改UNION": """
SELECT *
FROM orders
WHERE status = 'pending'
   OR status = 'processing'
ORDER BY order_date DESC
LIMIT 100
    """.strip(),
    "NOT EXISTS优化": """
SELECT c.id, c.name
FROM customers c
WHERE NOT EXISTS (
    SELECT 1
    FROM orders o
    WHERE o.customer_id = c.id
    AND o.order_date >= '2024-01-01'
)
ORDER BY c.name
    """.strip(),
    "隐式连接转换": """
SELECT *
FROM orders o, customers c, products p
WHERE o.customer_id = c.id
AND o.product_id = p.id
AND c.country = 'USA'
AND p.category = 'Electronics'
AND o.total_amount > 500
ORDER BY o.order_date DESC
    """.strip(),
    "条件简化": """
SELECT *
FROM orders
WHERE status = 'pending'
  AND status = 'pending'
  AND total_amount > 100
  AND NOT (total_amount <= 100)
ORDER BY order_date
    """.strip(),
    "HAVING优化": """
SELECT customer_id, COUNT(*) as order_count, SUM(total_amount) as total
FROM orders
GROUP BY customer_id
HAVING customer_id > 1000
   AND SUM(total_amount) > 10000
ORDER BY total DESC
    """.strip(),
}


def init_session_state():
    if "app_config" not in st.session_state:
        st.session_state.app_config = AppConfig()
    if "db_connected" not in st.session_state:
        st.session_state.db_connected = False
    if "parsed_sql" not in st.session_state:
        st.session_state.parsed_sql = None
    if "rewrite_result" not in st.session_state:
        st.session_state.rewrite_result = None
    if "comparison_result" not in st.session_state:
        st.session_state.comparison_result = None
    if "original_plan" not in st.session_state:
        st.session_state.original_plan = None
    if "rewritten_plan" not in st.session_state:
        st.session_state.rewritten_plan = None
    if "slow_log_entries" not in st.session_state:
        st.session_state.slow_log_entries = None
    if "replay_summary" not in st.session_state:
        st.session_state.replay_summary = None
    if "index_recommendations" not in st.session_state:
        st.session_state.index_recommendations = None
    if "deployment_result" not in st.session_state:
        st.session_state.deployment_result = None
    if "deployment_history" not in st.session_state:
        st.session_state.deployment_history = []
    if "monitoring_snapshots" not in st.session_state:
        st.session_state.monitoring_snapshots = []
    if "active_tab" not in st.session_state:
        st.session_state.active_tab = 0


def sidebar():
    with st.sidebar:
        st.title("⚡ 配置中心")
        st.markdown("---")

        st.subheader("📊 数据库连接")
        db_type = st.selectbox(
            "数据库类型",
            ["mysql", "postgresql"],
            index=0,
        )

        host = st.text_input("主机", "localhost")
        port = st.number_input("端口", min_value=1, max_value=65535, value=3306 if db_type == "mysql" else 5432)
        user = st.text_input("用户名", "root" if db_type == "mysql" else "postgres")
        password = st.text_input("密码", type="password")
        database = st.text_input("数据库名", "")

        st.markdown("---")
        st.subheader("🔧 重写规则")
        enable_redundant = st.checkbox("移除冗余列", value=True)
        enable_simplify = st.checkbox("简化条件", value=True)
        enable_or_union = st.checkbox("OR转UNION", value=True)
        enable_not_exists = st.checkbox("NOT EXISTS转LEFT JOIN", value=True)
        enable_subquery = st.checkbox("子查询展开", value=True)
        enable_predicate = st.checkbox("谓词下推", value=True)
        enable_join = st.checkbox("JOIN优化", value=True)
        enable_index_hint = st.checkbox("索引提示(MySQL)", value=False)
        max_attempts = st.slider("最大重写次数", min_value=1, max_value=10, value=5)

        st.markdown("---")
        st.subheader("⚙️ 性能测试")
        iterations = st.slider("执行次数", min_value=1, max_value=10, value=3)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔌 测试连接", use_container_width=True):
                test_connection(db_type, host, port, user, password, database)
        with col2:
            if st.button("💾 保存配置", use_container_width=True):
                save_config(db_type, host, port, user, password, database,
                           enable_subquery, enable_join, enable_predicate,
                           enable_redundant, enable_simplify, enable_index_hint,
                           enable_or_union, enable_not_exists,
                           max_attempts, iterations)

        if st.session_state.db_connected:
            st.success("✅ 数据库已连接")
        else:
            st.warning("⚠️ 未连接数据库")

        st.markdown("---")
        st.caption("慢SQL自动重写工具 v1.0")


def test_connection(db_type, host, port, user, password, database):
    try:
        db_config = DatabaseConfig(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            db_type=db_type,
        )
        comparator = PerformanceComparator(db_config)
        if comparator.connector.connect():
            st.session_state.db_connected = True
            st.success("✅ 连接成功！")
            tables = comparator.connector.get_tables()
            if tables:
                st.info(f"📋 找到 {len(tables)} 张表")
        else:
            st.session_state.db_connected = False
            st.error("❌ 连接失败")
        comparator.close()
    except Exception as e:
        st.session_state.db_connected = False
        st.error(f"❌ 连接错误: {str(e)}")


def save_config(db_type, host, port, user, password, database,
                enable_subquery, enable_join, enable_predicate,
                enable_redundant, enable_simplify, enable_index_hint,
                enable_or_union, enable_not_exists,
                max_attempts, iterations):
    config = st.session_state.app_config
    config.update_db_config(
        db_type=db_type,
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
    )
    config.update_rewrite_config(
        enable_subquery_unfolding=enable_subquery,
        enable_optimize_joins=enable_join,
        enable_push_predicates=enable_predicate,
        enable_remove_redundant=enable_redundant,
        enable_simplify_conditions=enable_simplify,
        enable_use_index_hints=enable_index_hint,
        enable_or_to_union=enable_or_union,
        enable_not_exists_to_leftjoin=enable_not_exists,
        max_rewrite_attempts=max_attempts,
    )
    st.session_state.benchmark_iterations = iterations
    st.success("✅ 配置已保存")


def main_content():
    st.title("⚡ 慢SQL自动重写工具")
    st.markdown("""
    智能分析慢SQL执行计划，自动应用多种优化规则，生成等价高效SQL，
    并提供重写前后的性能对比。支持MySQL和PostgreSQL。
    """)

    st.markdown("---")

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📝 单SQL优化",
        "📊 慢查询日志回放",
        "🔍 索引推荐",
        "🚀 自动部署",
        "📈 性能监控"
    ])

    with tab1:
        single_query_tab()

    with tab2:
        slow_log_replay_tab()

    with tab3:
        index_recommendation_tab()

    with tab4:
        auto_deployment_tab()

    with tab5:
        performance_monitoring_tab()


def single_query_tab():
    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader("📝 输入SQL")
    with col2:
        example = st.selectbox("📋 示例SQL", list(EXAMPLE_SQLS.keys()), index=0)
        if st.button("📥 加载示例", use_container_width=True):
            st.session_state.input_sql = EXAMPLE_SQLS[example]

    if "input_sql" not in st.session_state:
        st.session_state.input_sql = EXAMPLE_SQLS["子查询优化"]

    input_sql = st.text_area(
        "慢SQL语句",
        value=st.session_state.input_sql,
        height=200,
        placeholder="请输入需要优化的SQL语句...",
        key="input_sql_area",
    )
    st.session_state.input_sql = input_sql

    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("🔍 解析SQL", use_container_width=True, type="primary"):
            parse_sql(input_sql)
    with col2:
        if st.button("✨ 自动重写", use_container_width=True, type="primary"):
            rewrite_sql(input_sql)
    with col3:
        if st.button("📊 性能对比", use_container_width=True, type="primary"):
            compare_performance(input_sql)

    st.markdown("---")

    if st.session_state.parsed_sql:
        show_parsed_info()

    if st.session_state.rewrite_result:
        show_rewrite_result()

    if st.session_state.comparison_result:
        show_comparison_result()


def slow_log_replay_tab():
    st.subheader("📊 慢查询日志回放")

    config = st.session_state.app_config
    log_parser = SlowQueryLogParser(config.database.db_type)

    col1, col2 = st.columns(2)
    with col1:
        db_type_log = st.selectbox("日志类型", ["mysql", "postgresql"], index=0)
        log_parser.db_type = db_type_log
    with col2:
        min_query_time = st.number_input("最小查询时间(s)", min_value=0.0, value=0.1, step=0.1)

    uploaded_file = st.file_uploader("上传慢查询日志文件", type=["log", "txt"])

    if uploaded_file is not None:
        try:
            content = uploaded_file.getvalue().decode("utf-8")
            entries = log_parser.parse_string(content)

            if min_query_time > 0:
                entries = log_parser.filter_by_query_time(entries, min_query_time)

            entries = log_parser.sort_by_query_time(entries, descending=True)
            st.session_state.slow_log_entries = entries

            summary = log_parser.get_summary(entries)
            st.success(f"✅ 解析完成，共 {len(entries)} 条慢查询")

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("总查询数", summary["count"])
            with col2:
                st.metric("总查询时间", f"{summary['total_query_time']:.2f}s")
            with col3:
                st.metric("平均查询时间", f"{summary['avg_query_time']:.4f}s")
            with col4:
                st.metric("最长查询时间", f"{summary['max_query_time']:.4f}s")

            st.markdown("---")
            st.subheader("📋 查询列表")

            df_data = []
            for i, entry in enumerate(entries[:20]):
                df_data.append({
                    "序号": i + 1,
                    "SQL": entry.sql[:80] + "..." if len(entry.sql) > 80 else entry.sql,
                    "查询时间(s)": f"{entry.query_time:.4f}",
                    "数据库": entry.database,
                })

            if df_data:
                df = pd.DataFrame(df_data)
                st.table(df)

            st.markdown("---")
            col1, col2 = st.columns(2)
            with col1:
                replay_count = st.number_input("回放查询数量", min_value=1, max_value=min(10, len(entries)), value=min(3, len(entries)))
            with col2:
                benchmark_iterations = st.number_input("每个查询执行次数", min_value=1, max_value=5, value=1)

            if st.button("🚀 开始重放并优化", use_container_width=True, type="primary"):
                if not st.session_state.db_connected:
                    st.error("❌ 请先连接数据库")
                else:
                    with st.spinner("⏳ 正在重放并优化慢查询..."):
                        replay_entries = entries[:replay_count]
                        config = st.session_state.app_config
                        comparator = PerformanceComparator(config.database, config)
                        replayer = LogReplayer(comparator.connector, config.database.db_type, comparator)

                        summary = replayer.replay(
                            replay_entries,
                            benchmark_iterations=benchmark_iterations,
                            skip_errors=True
                        )
                        st.session_state.replay_summary = summary

                        st.success("✅ 重放完成！")
                        report = replayer.generate_report(summary)
                        st.text_area("重放报告", report, height=400)

                        if summary.results:
                            df = summary.to_dataframe()
                            st.dataframe(df)

                        comparator.connector.close()

        except Exception as e:
            st.error(f"❌ 解析错误: {str(e)}")

    st.info("💡 提示：MySQL慢查询日志需要开启slow_query_log，PostgreSQL需要设置log_min_duration_statement")


def parse_sql(sql: str):
    try:
        config = st.session_state.app_config
        parser = SQLParser(dialect=config.database.db_type)
        parsed = parser.parse(sql)
        st.session_state.parsed_sql = parsed

        if parsed.is_valid:
            st.success("✅ SQL解析成功")
        else:
            st.error(f"❌ SQL解析失败: {parsed.error}")
    except Exception as e:
        st.error(f"❌ 解析错误: {str(e)}")


def rewrite_sql(sql: str):
    try:
        config = st.session_state.app_config
        rewriter = SQLRewriter(
            dialect=config.database.db_type,
            config=config.rewrite,
        )

        plan_analysis = None
        if st.session_state.original_plan:
            plan_analysis = st.session_state.original_plan.plan_analysis

        result = rewriter.rewrite(sql, plan_analysis=plan_analysis)
        st.session_state.rewrite_result = result

        if result.is_rewritten:
            st.success(f"✅ 重写完成，应用了 {result.rules_applied} 条规则")
        else:
            if result.error:
                st.error(f"❌ 重写失败: {result.error}")
            else:
                st.info("ℹ️ SQL已是最优，无需重写")
    except Exception as e:
        st.error(f"❌ 重写错误: {str(e)}")


def compare_performance(sql: str):
    if not st.session_state.db_connected:
        st.error("❌ 请先连接数据库")
        return

    try:
        config = st.session_state.app_config
        comparator = PerformanceComparator(config.database, config)

        rewrite_result = st.session_state.rewrite_result
        rewritten_sql = rewrite_result.rewritten_sql if rewrite_result else sql

        with st.spinner("⏳ 正在执行性能对比测试..."):
            iterations = getattr(st.session_state, "benchmark_iterations", 3)
            comparison = comparator.compare(
                original_sql=sql,
                rewritten_sql=rewritten_sql,
                rewrite_result=rewrite_result,
                iterations=iterations,
            )

        st.session_state.comparison_result = comparison
        st.session_state.original_plan = comparison.original
        st.session_state.rewritten_plan = comparison.rewritten

        if comparison.is_faster:
            st.success(f"✅ 性能提升 {comparison.improvement_percent:.1f}%")
        else:
            st.info("ℹ️ 重写后性能未提升")

        comparator.close()
    except Exception as e:
        st.error(f"❌ 性能对比错误: {str(e)}")


def show_parsed_info():
    parsed = st.session_state.parsed_sql
    if not parsed:
        return

    st.subheader("📋 SQL分析结果")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("SQL类型", parsed.sql_type)
    with col2:
        st.metric("涉及表数", len(parsed.tables))
    with col3:
        st.metric("涉及列数", len(parsed.columns))
    with col4:
        st.metric("子查询数", len(parsed.subqueries))

    tab1, tab2, tab3, tab4 = st.tabs(["📊 基础信息", "🔗 JOIN信息", "📋 WHERE条件", "⚠️ 特征检测"])

    with tab1:
        st.write("**涉及表:**")
        if parsed.tables:
            st.write(", ".join(parsed.tables))
        else:
            st.info("无")

        st.write("**涉及列:**")
        if parsed.columns:
            st.write(", ".join(parsed.columns))
        else:
            st.info("无")

    with tab2:
        if parsed.joins:
            for join in parsed.joins:
                st.markdown(f"""
                - **类型:** {join['type']}
                - **表:** {join['table']}
                - **条件:** {join['on']}
                """)
        else:
            st.info("无JOIN操作")

    with tab3:
        if parsed.where_conditions:
            for cond in parsed.where_conditions:
                st.code(cond, language="sql")
        else:
            st.info("无WHERE条件")

    with tab4:
        features = []
        if parsed.has_order_by:
            features.append(("ORDER BY", "⚠️ 可能需要filesort"))
        if parsed.has_group_by:
            features.append(("GROUP BY", "⚠️ 可能需要临时表"))
        if parsed.has_having:
            features.append(("HAVING", "💡 考虑下推到WHERE"))
        if parsed.has_limit:
            features.append(("LIMIT", "✅ 可尝试下推"))
        if parsed.has_distinct:
            features.append(("DISTINCT", "⚠️ 可能影响性能"))
        if parsed.has_union:
            features.append(("UNION", "⚠️ 考虑UNION ALL"))

        if features:
            df = pd.DataFrame(features, columns=["特征", "说明"])
            st.table(df)
        else:
            st.info("无特殊特征")


def show_rewrite_result():
    result = st.session_state.rewrite_result
    if not result:
        return

    st.subheader("✨ 重写结果")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🔴 原始SQL")
        st.markdown(f'<div class="sql-box">{result.original_sql}</div>', unsafe_allow_html=True)

    with col2:
        st.markdown("### 🟢 重写后SQL")
        st.markdown(f'<div class="sql-box">{result.rewritten_sql}</div>', unsafe_allow_html=True)

    if result.is_rewritten:
        st.markdown("---")
        st.subheader("📝 重写步骤")

        for i, step in enumerate(result.steps):
            if step.applied:
                with st.expander(f"✅ {i+1}. {step.rule_name}"):
                    st.write(f"**说明:** {step.rule_description}")
                    for change in step.changes:
                        st.success(f"💡 {change}")

        st.download_button(
            "📥 下载重写后SQL",
            result.rewritten_sql,
            file_name="optimized_query.sql",
            mime="text/plain",
        )


def show_comparison_result():
    comparison = st.session_state.comparison_result
    if not comparison:
        return

    st.subheader("📊 性能对比")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.write("**原始耗时**")
        st.write(f"<h2 style='color: #ef4444;'>{comparison.original.avg_time_ms:.2f} ms</h2>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.write("**重写后耗时**")
        st.write(f"<h2 style='color: #22c55e;'>{comparison.rewritten.avg_time_ms:.2f} ms</h2>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col3:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.write("**性能提升**")
        if comparison.is_faster:
            st.write(f'<div class="improvement-positive">+{comparison.improvement_percent:.1f}%</div>', unsafe_allow_html=True)
        else:
            st.write(f'<div class="improvement-negative">{comparison.improvement_percent:.1f}%</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col4:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.write("**结果验证**")
        if comparison.validation_passed:
            st.markdown('<div class="status-success">✅ 通过</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="status-error">❌ 失败</div>', unsafe_allow_html=True)
            st.caption(comparison.validation_message)
        st.markdown('</div>', unsafe_allow_html=True)

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📈 对比图表", "📋 详细数据", "✅ 结果集验证", "🔴 原始执行计划", "🟢 重写后执行计划"])

    with tab1:
        chart_type = st.radio("图表类型", ["柱状图", "雷达图", "仪表盘"], horizontal=True)

        config = st.session_state.app_config
        comparator = PerformanceComparator(config.database, config)

        if chart_type == "柱状图":
            fig = comparator.generate_comparison_chart(comparison, "bar")
        elif chart_type == "雷达图":
            fig = comparator.generate_comparison_chart(comparison, "radar")
        else:
            fig = comparator.generate_comparison_chart(comparison, "gauge")

        st.plotly_chart(fig, use_container_width=True)
        comparator.close()

    with tab2:
        config = st.session_state.app_config
        comparator = PerformanceComparator(config.database, config)
        df = comparator.generate_comparison_table(comparison)
        st.table(df)
        comparator.close()

    with tab3:
        st.subheader("✅ 结果集验证详情")

        if comparison.validation_result:
            vr = comparison.validation_result

            st.write(f"**验证状态:** {'✅ 通过' if vr.passed else '❌ 失败'}")
            st.write(f"**验证消息:** {vr.message}")

            if vr.details:
                st.markdown("---")
                st.write("**详细信息:**")

                col1, col2 = st.columns(2)
                with col1:
                    st.write("**原始查询**")
                    if "original" in vr.details:
                        orig = vr.details["original"]
                        st.write(f"- 列数: {len(orig.get('columns', []))}")
                        st.write(f"- 列名: {', '.join(orig.get('columns', []))}")
                        st.write(f"- 行数: {orig.get('row_count', 0)}")
                with col2:
                    st.write("**重写后查询**")
                    if "rewritten" in vr.details:
                        rw = vr.details["rewritten"]
                        st.write(f"- 列数: {len(rw.get('columns', []))}")
                        st.write(f"- 列名: {', '.join(rw.get('columns', []))}")
                        st.write(f"- 行数: {rw.get('row_count', 0)}")

            if vr.mismatches:
                st.markdown("---")
                st.error("**不匹配项:")
                for i, mismatch in enumerate(vr.mismatches[:10], 1):
                    st.warning(f"{i}. {mismatch}")

            if comparison.original_result and comparison.rewritten_result:
                st.markdown("---")
                st.write("**样本数据对比:**")

                col1, col2 = st.columns(2)
                with col1:
                    st.write("原始数据(前5行)")
                    if comparison.original_result.rows[:5]:
                        for row in comparison.original_result.rows[:5]:
                            st.code(str(row))
                with col2:
                    st.write("重写后数据(前5行)")
                    for row in comparison.rewritten_result.rows[:5]:
                        st.code(str(row))
        else:
                            st.info("未执行完整的结果集验证")

    with tab4:
        if comparison.original.plan_analysis:
            plan = comparison.original.plan_analysis
            show_plan_analysis(plan, "original")
        else:
            st.info("无执行计划数据")

    with tab5:
        if comparison.rewritten.plan_analysis:
            plan = comparison.rewritten.plan_analysis
            show_plan_analysis(plan, "rewritten")
        else:
            st.info("无执行计划数据")


def show_plan_analysis(plan, prefix: str):
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("预估成本", f"{plan.total_cost:.2f}")
    with col2:
        st.metric("预估行数", f"{plan.estimated_rows:,}")
    with col3:
        status = "⚠️ 有" if plan.has_full_table_scan else "✅ 无"
        st.metric("全表扫描", status)

    if plan.potential_problems:
        st.write("**⚠️ 潜在问题:**")
        for problem in plan.potential_problems:
            st.warning(problem)

    if plan.recommendations:
        st.write("**💡 优化建议:**")
        for rec in plan.recommendations:
            st.success(rec)

    if plan.plan_tree:
        st.write("**🌳 执行计划树:**")
        show_plan_tree(plan.plan_tree)

    if plan.raw_plan:
        with st.expander("📄 原始JSON数据"):
            st.json(plan.raw_plan)


def show_plan_tree(node, level: int = 0):
    indent = "  " * level
    icon = "📊" if level == 0 else "├─ "
    extra = f" [{node.extra}]" if node.extra else ""
    st.write(f"{indent}{icon}**{node.operation}** {node.table_name} "
             f"(rows: {node.rows:,}, cost: {node.total_cost:.2f}){extra}")

    for child in node.children:
        show_plan_tree(child, level + 1)


def index_recommendation_tab():
    st.subheader("🔍 索引推荐引擎")
    st.markdown("分析查询模式，自动推荐最优索引，配合SQL重写实现双重优化。")

    col1, col2 = st.columns([3, 1])
    with col1:
        st.write("**输入SQL进行索引分析**")
    with col2:
        if st.button("📋 加载当前SQL", use_container_width=True):
            if "input_sql" in st.session_state:
                st.session_state.index_input_sql = st.session_state.input_sql

    if "index_input_sql" not in st.session_state:
        st.session_state.index_input_sql = EXAMPLE_SQLS.get("OR改UNION", "")

    input_sql = st.text_area(
        "SQL语句",
        value=st.session_state.index_input_sql,
        height=150,
        placeholder="请输入需要分析索引的SQL语句...",
        key="index_sql_area",
    )
    st.session_state.index_input_sql = input_sql

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔍 分析并推荐索引", use_container_width=True, type="primary"):
            analyze_indexes(input_sql)

    with col2:
        if st.button("✨ 协同优化（重写+索引）", use_container_width=True, type="primary"):
            combined_optimization(input_sql)

    st.markdown("---")

    if st.session_state.index_recommendations:
        show_index_recommendations()


def analyze_indexes(sql: str):
    if not st.session_state.db_connected:
        st.error("❌ 请先连接数据库")
        return

    try:
        config = st.session_state.app_config
        comparator = PerformanceComparator(config.database, config)

        index_recommender = IndexRecommender(
            comparator.connector,
            dialect=config.database.db_type,
        )

        plan_analysis = None
        if st.session_state.original_plan:
            plan_analysis = st.session_state.original_plan.plan_analysis

        with st.spinner("⏳ 正在分析查询模式并推荐索引..."):
            result = index_recommender.recommend_for_query(sql, plan_analysis)

        st.session_state.index_recommendations = result
        st.success(f"✅ 分析完成，推荐 {len(result.recommendations)} 个索引")

        comparator.close()
    except Exception as e:
        st.error(f"❌ 索引分析错误: {str(e)}")


def combined_optimization(sql: str):
    if not st.session_state.db_connected:
        st.error("❌ 请先连接数据库")
        return

    try:
        config = st.session_state.app_config
        comparator = PerformanceComparator(config.database, config)

        rewriter = SQLRewriter(
            dialect=config.database.db_type,
            config=config.rewrite,
        )

        index_recommender = IndexRecommender(
            comparator.connector,
            dialect=config.database.db_type,
        )

        coordinator = IndexRewriteCoordinator(
            rewriter=rewriter,
            index_recommender=index_recommender,
            dialect=config.database.db_type,
        )

        with st.spinner("⏳ 正在执行协同优化（重写+索引推荐）..."):
            result = coordinator.optimize(sql)

        st.session_state.rewrite_result = result.rewrite_result
        st.session_state.index_recommendations = result.index_recommendations

        msg_parts = []
        if result.is_rewritten:
            msg_parts.append(f"重写完成，应用 {result.rewrite_result.rules_applied} 条规则")
        if result.has_index_recommendations:
            msg_parts.append(f"推荐 {len(result.index_recommendations.recommendations)} 个索引")

        if msg_parts:
            st.success("✅ " + "，".join(msg_parts))
        else:
            st.info("ℹ️ SQL已是最优，无需重写或新增索引")

        comparator.close()
    except Exception as e:
        st.error(f"❌ 协同优化错误: {str(e)}")


def show_index_recommendations():
    result = st.session_state.index_recommendations
    if not result:
        return

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("推荐索引数", len(result.recommendations))
    with col2:
        st.metric("分析表数", len(result.analyzed_tables))
    with col3:
        st.metric("现有索引数", sum(len(idx) for idx in result.existing_indexes.values()))

    if result.recommendations:
        st.markdown("---")
        st.subheader("💡 推荐索引")

        sorted_recs = result.sort_by_benefit()

        for i, rec in enumerate(sorted_recs, 1):
            with st.expander(f"**{i}. {rec.table_name}** - 收益评分: {rec.estimated_benefit:.1f}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**表名:** {rec.table_name}")
                    st.write(f"**列名:** {', '.join(rec.columns)}")
                    st.write(f"**索引类型:** {rec.index_type}")
                with col2:
                    st.write(f"**置信度:** {rec.confidence:.0%}")
                    st.write(f"**收益预估:** {rec.estimated_benefit:.1f}")
                    st.write(f"**唯一索引:** {'是' if rec.is_unique else '否'}")

                st.write(f"**推荐理由:** {rec.reason}")
                st.code(rec.to_sql(dialect=st.session_state.app_config.database.db_type), language="sql")

                if st.button(f"📋 复制索引SQL", key=f"copy_idx_{i}", use_container_width=True):
                    st.code(rec.to_sql(dialect=st.session_state.app_config.database.db_type), language="sql")

    if result.existing_indexes:
        st.markdown("---")
        st.subheader("📋 现有索引")

        for table, indexes in result.existing_indexes.items():
            with st.expander(f"**{table}** ({len(indexes)} 个索引)"):
                for idx in indexes:
                    unique = " [UNIQUE]" if idx.get("unique", False) else ""
                    st.write(f"- **{idx['name']}**{unique}: ({', '.join(idx['columns'])})")


def auto_deployment_tab():
    st.subheader("🚀 SQL自动部署")
    st.markdown("安全地部署优化后的SQL，包含备份、验证、回滚机制。")

    col1, col2 = st.columns(2)
    with col1:
        original_sql = st.text_area(
            "原始SQL",
            value=st.session_state.get("input_sql", ""),
            height=120,
            key="deploy_original",
        )
    with col2:
        rewritten_sql = st.text_area(
            "优化后SQL",
            value=st.session_state.rewrite_result.rewritten_sql if st.session_state.rewrite_result else "",
            height=120,
            key="deploy_rewritten",
        )

    st.markdown("---")
    st.subheader("⚙️ 部署配置")

    col1, col2, col3 = st.columns(3)
    with col1:
        enable_backup = st.checkbox("启用备份", value=True)
    with col2:
        enable_validation = st.checkbox("启用结果验证", value=True)
    with col3:
        enable_performance_check = st.checkbox("启用性能检查", value=True)

    min_improvement = st.slider(
        "最小性能提升阈值 (%)",
        min_value=0,
        max_value=100,
        value=10,
        help="如果性能提升低于此阈值，将发出警告"
    )

    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔍 预验证部署", use_container_width=True):
            validate_deployment(
                original_sql,
                rewritten_sql,
                enable_backup,
                enable_validation,
                enable_performance_check,
                min_improvement,
                execute=False,
            )

    with col2:
        if st.button("🚀 执行部署", use_container_width=True, type="primary"):
            if not st.session_state.db_connected:
                st.error("❌ 请先连接数据库")
            else:
                validate_deployment(
                    original_sql,
                    rewritten_sql,
                    enable_backup,
                    enable_validation,
                    enable_performance_check,
                    min_improvement,
                    execute=True,
                )

    st.markdown("---")

    if st.session_state.deployment_result:
        show_deployment_result()

    if st.session_state.deployment_history:
        st.subheader("📜 部署历史")
        show_deployment_history()


def validate_deployment(
    original_sql: str,
    rewritten_sql: str,
    enable_backup: bool,
    enable_validation: bool,
    enable_performance_check: bool,
    min_improvement: float,
    execute: bool = False,
):
    if not original_sql or not rewritten_sql:
        st.error("❌ 请输入原始SQL和优化后SQL")
        return

    try:
        config = st.session_state.app_config
        comparator = PerformanceComparator(config.database, config)

        deployer = SQLDeployer(
            db_connector=comparator.connector,
            backup_dir="./deployments/backups",
            enable_backup=enable_backup,
            enable_validation=enable_validation,
            enable_performance_check=enable_performance_check,
            min_improvement_pct=min_improvement,
            dialect=config.database.db_type,
        )

        with st.spinner("⏳ 正在执行部署验证..."):
            result = deployer.deploy(
                original_sql=original_sql,
                optimized_sql=rewritten_sql,
                execute_on_target=execute,
                verify_before_deploy=True,
            )

        st.session_state.deployment_result = result
        st.session_state.deployment_history.insert(0, result)

        if result.status == DeploymentStatus.SUCCESS:
            st.success("✅ 部署验证成功！" if not execute else "✅ 部署成功！")
        elif result.status == DeploymentStatus.ROLLED_BACK:
            st.warning("⚠️ 部署失败，已自动回滚")
        else:
            st.error(f"❌ 部署失败: {result.error_message}")

        comparator.close()
    except Exception as e:
        st.error(f"❌ 部署错误: {str(e)}")


def show_deployment_result():
    result = st.session_state.deployment_result
    if not result:
        return

    st.subheader("📊 部署结果")

    status_colors = {
        DeploymentStatus.SUCCESS: "#22c55e",
        DeploymentStatus.FAILED: "#ef4444",
        DeploymentStatus.ROLLED_BACK: "#f59e0b",
        DeploymentStatus.PENDING: "#6366f1",
    }

    status_color = status_colors.get(result.status, "#6366f1")
    st.markdown(
        f'<div style="background: {status_color}; color: white; padding: 1rem; '
        f'border-radius: 10px; text-align: center; font-size: 1.2rem; font-weight: bold;">'
        f'状态: {result.status.value.upper()}</div>',
        unsafe_allow_html=True,
    )

    st.markdown("---")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("部署ID", result.deployment_id[:20] + "...")
    with col2:
        if result.performance_improvement_pct > 0:
            st.metric("性能提升", f"+{result.performance_improvement_pct:.1f}%")
        else:
            st.metric("性能变化", f"{result.performance_improvement_pct:.1f}%")
    with col3:
        if result.validation_result:
            status = "✅ 通过" if result.validation_result.is_valid else "❌ 失败"
            st.metric("结果验证", status)

    if result.backup_path:
        st.info(f"💾 备份文件: {result.backup_path}")

    if result.error_message:
        st.error(f"❌ 错误信息: {result.error_message}")


def show_deployment_history():
    history = st.session_state.deployment_history[:10]

    df_data = []
    for i, result in enumerate(history):
        df_data.append({
            "序号": i + 1,
            "部署ID": result.deployment_id[:16],
            "状态": result.status.value,
            "性能提升(%)": f"{result.performance_improvement_pct:.1f}",
            "时间": result.start_time.strftime("%H:%M:%S"),
        })

    df = pd.DataFrame(df_data)
    st.table(df)


def performance_monitoring_tab():
    st.subheader("📈 性能监控与追踪")
    st.markdown("持续监控优化效果，追踪SQL性能变化趋势。")

    config = st.session_state.app_config
    comparator = PerformanceComparator(config.database, config)
    tracker = PerformanceTracker(
        db_connector=comparator.connector,
        config=TrackingConfig(
            tracking_interval_minutes=60,
            retention_days=30,
            alert_threshold_pct=20.0,
        ),
        data_dir="./monitoring/data",
    )

    col1, col2, col3, col4 = st.columns(4)
    stats = tracker.get_summary_stats()

    with col1:
        st.metric("唯一查询", stats["total_unique_queries"])
    with col2:
        st.metric("已优化查询", stats["optimized_queries"])
    with col3:
        st.metric("平均提升", f"{stats['avg_improvement_pct']:.1f}%")
    with col4:
        st.metric("活跃告警", stats["active_alerts"])

    st.markdown("---")

    tab1, tab2, tab3 = st.tabs(["🔍 查询快照", "📊 优化影响报告", "⚠️ 告警"])

    with tab1:
        st.subheader("📋 查询性能快照")

        snapshots = tracker.get_all_snapshots()
        if snapshots:
            df_data = []
            for snap in snapshots[:20]:
                trend = snap.get_trend()
                trend_icon = {
                    "improving": "📈",
                    "declining": "📉",
                    "stable": "➡️",
                    "unknown": "❓",
                }.get(trend.value, "❓")

                avg_time = snap.get_avg_exec_time() or 0
                improvement = snap.get_improvement_since_baseline()

                df_data.append({
                    "SQL": snap.sql_text[:60] + "..." if len(snap.sql_text) > 60 else snap.sql_text,
                    "平均耗时(ms)": f"{avg_time:.2f}",
                    "P95耗时(ms)": f"{snap.get_p95_exec_time() or 0:.2f}",
                    "趋势": f"{trend_icon} {trend.value}",
                    "基线提升(%)": f"{improvement:.1f}" if improvement else "N/A",
                    "已优化": "✅" if snap.is_optimized else "❌",
                })

            df = pd.DataFrame(df_data)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("暂无性能数据，先执行性能对比测试")

    with tab2:
        st.subheader("📊 优化影响报告")

        report = tracker.get_optimization_impact_report()

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("总优化查询", report["total_optimized_queries"])
        with col2:
            st.metric("平均提升", f"{report.get('avg_improvement_pct', 0):.1f}%")
        with col3:
            st.metric("性能提升", report["queries_improved"])
        with col4:
            st.metric("性能回退", report["queries_regressed"])

        if report["details"]:
            st.markdown("---")
            st.write("**优化详情:**")

            detail_df = pd.DataFrame(report["details"])
            st.dataframe(detail_df, use_container_width=True)

    with tab3:
        st.subheader("⚠️ 性能告警")

        alerts = tracker.get_alerts()
        if alerts:
            for alert in alerts:
                severity_color = {
                    "warning": "#f59e0b",
                    "critical": "#ef4444",
                }.get(alert["severity"], "#6366f1")

                st.markdown(
                    f'<div style="background: {severity_color}; color: white; '
                    f'padding: 1rem; border-radius: 10px; margin-bottom: 0.5rem;">'
                    f'<strong>【{alert["severity"].upper()}】</strong> {alert["message"]}<br>'
                    f'变化: {alert["change_pct"]:.1f}% | '
                    f'{alert["avg_before_ms"]:.1f}ms → {alert["avg_after_ms"]:.1f}ms</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.success("✅ 暂无性能告警，系统运行正常！")

    st.markdown("---")
    st.subheader("➕ 添加性能数据")

    col1, col2 = st.columns([3, 1])
    with col1:
        track_sql = st.text_area(
            "SQL语句",
            value=st.session_state.get("input_sql", ""),
            height=100,
            key="track_sql_input",
        )
    with col2:
        is_optimized = st.checkbox("已优化", value=False)
        original_sql = st.text_input("原始SQL(可选)", value="")

    if st.button("📝 记录性能数据", use_container_width=True):
        if not st.session_state.db_connected:
            st.error("❌ 请先连接数据库")
        else:
            with st.spinner("⏳ 正在执行并记录性能..."):
                try:
                    perf = comparator.benchmark_query(track_sql, iterations=1)
                    tracker.track_query(
                        sql=track_sql,
                        performance=perf,
                        is_optimized=is_optimized,
                        original_sql=original_sql if original_sql else None,
                        optimization_notes="手动添加",
                    )
                    st.success("✅ 性能数据已记录")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ 记录失败: {str(e)}")

    comparator.close()


def main():
    init_session_state()
    sidebar()
    main_content()


if __name__ == "__main__":
    main()
