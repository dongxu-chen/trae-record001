import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
import seaborn as sns
from datetime import datetime, date
import io
import uuid

from classifier import TransactionClassifier
from merchant_db import MerchantDatabase, CATEGORIES, MerchantInfo
from rule_engine import RuleEngine, Rule, RuleCondition, RuleConditionType, RuleAction
from anomaly_detection import AnomalyDetector
from tax_calculator import TaxCalculator, TaxConfig, SPECIAL_DEDUCTIONS
from budget_manager import BudgetManager
from trend_analysis import TrendAnalyzer

st.set_page_config(
    page_title="信用卡消费分类系统",
    page_icon="💳",
    layout="wide"
)

CITIES = ["", "北京", "上海", "广州", "深圳", "杭州", "成都", "武汉", "西安", "南京", "重庆"]

@st.cache_resource
def get_classifier():
    return TransactionClassifier()

@st.cache_resource
def get_merchant_db():
    return MerchantDatabase()

@st.cache_resource
def get_rule_engine():
    return RuleEngine()

@st.cache_resource
def get_anomaly_detector():
    return AnomalyDetector()

@st.cache_resource
def get_tax_calculator():
    return TaxCalculator()

@st.cache_resource
def get_budget_manager():
    return BudgetManager()

@st.cache_resource
def get_trend_analyzer():
    return TrendAnalyzer()

classifier = get_classifier()
merchant_db = get_merchant_db()
rule_engine = get_rule_engine()
anomaly_detector = get_anomaly_detector()
tax_calculator = get_tax_calculator()
budget_manager = get_budget_manager()
trend_analyzer = get_trend_analyzer()

def main():
    st.title("💳 信用卡消费分类系统")
    
    model_info = classifier.get_model_info()
    if model_info.get('is_cold_start'):
        st.sidebar.info("🔄 冷启动模式：使用父类分类兜底")
    else:
        st.sidebar.success("✅ 模型已加载")
    
    if 'transactions' not in st.session_state:
        st.session_state.transactions = pd.DataFrame()
    
    if 'classified_transactions' not in st.session_state:
        st.session_state.classified_transactions = pd.DataFrame()
    
    page = st.sidebar.selectbox(
        "功能菜单",
        ["数据导入", "消费分类", "月度报表", "异常检测", "税务计算", "预算管理", "趋势分析", "商户库管理", "规则引擎"]
    )
    
    if page == "数据导入":
        data_import_page()
    elif page == "消费分类":
        classification_page()
    elif page == "月度报表":
        monthly_report_page()
    elif page == "异常检测":
        anomaly_detection_page()
    elif page == "税务计算":
        tax_calculation_page()
    elif page == "预算管理":
        budget_management_page()
    elif page == "趋势分析":
        trend_analysis_page()
    elif page == "商户库管理":
        merchant_management_page()
    elif page == "规则引擎":
        rule_engine_page()

def data_import_page():
    st.header("📊 数据导入")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("上传数据文件")
        uploaded_file = st.file_uploader("选择CSV或Excel文件", type=['csv', 'xlsx'])
        
        if uploaded_file is not None:
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            
            st.success(f"文件上传成功！共 {len(df)} 条记录")
            st.dataframe(df.head())
            
            st.subheader("字段映射")
            columns = list(df.columns)
            
            merchant_col = st.selectbox("商户名称字段", columns, index=columns.index('merchant') if 'merchant' in columns else 0)
            amount_col = st.selectbox("交易金额字段", columns, index=columns.index('amount') if 'amount' in columns else 0)
            date_col = st.selectbox("交易日期字段", columns, index=columns.index('date') if 'date' in columns else 0)
            time_col = st.selectbox("交易时间字段（可选）", ['无'] + columns, index=0)
            location_col = st.selectbox("地理位置字段（可选）", ['无'] + columns, index=columns.index('location') + 1 if 'location' in columns else 0)
            
            if st.button("确认导入并分类"):
                mapped_df = pd.DataFrame()
                mapped_df['merchant'] = df[merchant_col].astype(str)
                mapped_df['amount'] = pd.to_numeric(df[amount_col], errors='coerce')
                mapped_df['date'] = pd.to_datetime(df[date_col]).dt.strftime('%Y-%m-%d')
                
                if time_col != '无':
                    mapped_df['time'] = df[time_col].astype(str)
                else:
                    mapped_df['time'] = '12:00:00'
                
                if location_col != '无':
                    mapped_df['location'] = df[location_col].astype(str)
                else:
                    mapped_df['location'] = ''
                
                st.session_state.transactions = mapped_df
                
                with st.spinner("正在分类中..."):
                    transactions_list = mapped_df.to_dict('records')
                    classified = classifier.classify_batch(transactions_list)
                    st.session_state.classified_transactions = pd.DataFrame(classified)
                
                st.success("分类完成！")
                st.rerun()
    
    with col2:
        st.subheader("手动输入交易")
        with st.form("manual_input_form"):
            merchant = st.text_input("商户名称")
            amount = st.number_input("交易金额", min_value=0.0, step=0.01)
            location = st.selectbox("消费城市", CITIES)
            trans_date = st.date_input("交易日期", value=date.today())
            trans_time = st.time_input("交易时间", value=datetime.now().time())
            
            submitted = st.form_submit_button("添加并分类")
            
            if submitted and merchant and amount > 0:
                new_transaction = {
                    'merchant': merchant,
                    'amount': amount,
                    'location': location if location else '',
                    'date': trans_date.strftime('%Y-%m-%d'),
                    'time': trans_time.strftime('%H:%M:%S')
                }
                
                result = classifier.classify(new_transaction)
                result.update(new_transaction)
                
                new_df = pd.DataFrame([result])
                st.session_state.classified_transactions = pd.concat(
                    [st.session_state.classified_transactions, new_df],
                    ignore_index=True
                )
                
                st.success(f"添加成功！分类结果：{result['category']} ({result['method']}, 置信度: {result['confidence']:.2%})")
                if result.get('city'):
                    st.info(f"识别城市：{result['city']}")
                if result.get('sub_category'):
                    st.info(f"子分类：{result['sub_category']}")
                if '父类兜底' in result.get('tags', []):
                    st.warning("冷启动模式：使用父类分类兜底")
                st.rerun()
    
    st.subheader("当前数据")
    if not st.session_state.classified_transactions.empty:
        display_cols = ['merchant', 'amount', 'date', 'category', 'sub_category', 'city', 'confidence', 'method']
        available_cols = [col for col in display_cols if col in st.session_state.classified_transactions.columns]
        st.dataframe(st.session_state.classified_transactions[available_cols])
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("总交易数", len(st.session_state.classified_transactions))
        with col2:
            st.metric("总金额", f"¥{st.session_state.classified_transactions['amount'].sum():,.2f}")
        with col3:
            st.metric("分类类别数", st.session_state.classified_transactions['category'].nunique())
        with col4:
            if 'city' in st.session_state.classified_transactions.columns:
                city_count = st.session_state.classified_transactions['city'].nunique()
                st.metric("覆盖城市数", city_count)
        
        csv = st.session_state.classified_transactions.to_csv(index=False).encode('utf-8')
        st.download_button(
            "下载分类结果",
            csv,
            "classified_transactions.csv",
            "text/csv",
            key='download-csv'
        )
    else:
        st.info("暂无数据，请上传文件或手动输入交易")

def classification_page():
    st.header("🏷️ 消费分类")
    
    if st.session_state.classified_transactions.empty:
        st.warning("请先导入数据")
        return
    
    df = st.session_state.classified_transactions
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("分类统计")
        category_stats = df.groupby('category').agg({
            'amount': ['sum', 'count', 'mean']
        }).round(2)
        category_stats.columns = ['总金额', '交易次数', '平均金额']
        category_stats = category_stats.sort_values('总金额', ascending=False)
        st.dataframe(category_stats)
    
    with col2:
        st.subheader("分类方法分布")
        method_stats = df['method'].value_counts()
        st.dataframe(method_stats)
    
    if 'sub_category' in df.columns and df['sub_category'].notna().any():
        st.subheader("子分类统计")
        sub_cat_stats = df.groupby('sub_category').agg({
            'amount': ['sum', 'count']
        }).round(2)
        sub_cat_stats.columns = ['总金额', '交易次数']
        st.dataframe(sub_cat_stats, use_container_width=True)
    
    if 'city' in df.columns and df['city'].notna().any():
        st.subheader("城市消费分布")
        city_stats = df.groupby('city').agg({
            'amount': ['sum', 'count']
        }).round(2)
        city_stats.columns = ['总金额', '交易次数']
        city_stats = city_stats.sort_values('总金额', ascending=False)
        st.dataframe(city_stats, use_container_width=True)
    
    st.subheader("分类分布图表")
    col1, col2 = st.columns(2)
    
    with col1:
        fig, ax = plt.subplots(figsize=(8, 6))
        category_amounts = df.groupby('category')['amount'].sum()
        category_amounts.plot(kind='pie', autopct='%1.1f%%', ax=ax)
        ax.set_title('各类别金额占比')
        ax.set_ylabel('')
        st.pyplot(fig)
    
    with col2:
        fig, ax = plt.subplots(figsize=(8, 6))
        sns.barplot(x=category_amounts.index, y=category_amounts.values, ax=ax)
        ax.set_title('各类别消费金额')
        ax.set_xlabel('类别')
        ax.set_ylabel('金额')
        plt.xticks(rotation=45)
        st.pyplot(fig)
    
    st.subheader("分类详情")
    selected_category = st.selectbox("选择类别查看详情", ['全部'] + CATEGORIES)
    
    if selected_category != '全部':
        filtered_df = df[df['category'] == selected_category]
    else:
        filtered_df = df
    
    display_cols = ['merchant', 'amount', 'date', 'category', 'sub_category', 'city', 'confidence', 'method', 'tags']
    available_cols = [col for col in display_cols if col in filtered_df.columns]
    st.dataframe(filtered_df[available_cols])
    
    st.subheader("手动修正分类")
    if not filtered_df.empty:
        selected_idx = st.selectbox("选择交易记录（索引）", filtered_df.index)
        selected_row = filtered_df.loc[selected_idx]
        
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**商户**：{selected_row['merchant']}")
            st.write(f"**金额**：¥{selected_row['amount']:.2f}")
            st.write(f"**当前分类**：{selected_row['category']}")
            if 'sub_category' in selected_row and pd.notna(selected_row['sub_category']):
                st.write(f"**子分类**：{selected_row['sub_category']}")
            if 'city' in selected_row and pd.notna(selected_row['city']):
                st.write(f"**城市**：{selected_row['city']}")
            st.write(f"**分类方法**：{selected_row['method']}")
            st.write(f"**置信度**：{selected_row['confidence']:.2%}")
        
        with col2:
            new_category = st.selectbox("新分类", CATEGORIES, 
                index=CATEGORIES.index(selected_row['category']) if selected_row['category'] in CATEGORIES else 0)
            
            sub_categories = []
            hierarchy = merchant_db.get_category_hierarchy()
            if new_category in hierarchy:
                sub_categories = hierarchy[new_category].get('children', [])
            new_sub_category = st.selectbox("新子分类", ['无'] + sub_categories)
            
            new_city = st.selectbox("新城市", ['无'] + CITIES[1:])
            
            if st.button("修正分类"):
                st.session_state.classified_transactions.at[selected_idx, 'category'] = new_category
                st.session_state.classified_transactions.at[selected_idx, 'sub_category'] = new_sub_category if new_sub_category != '无' else None
                st.session_state.classified_transactions.at[selected_idx, 'city'] = new_city if new_city != '无' else None
                st.session_state.classified_transactions.at[selected_idx, 'method'] = 'manual'
                st.success("分类已修正")
                st.rerun()

def monthly_report_page():
    st.header("📈 月度报表")
    
    if st.session_state.classified_transactions.empty:
        st.warning("请先导入数据")
        return
    
    df = st.session_state.classified_transactions.copy()
    df['date'] = pd.to_datetime(df['date'])
    df['year_month'] = df['date'].dt.to_period('M')
    
    months = sorted(df['year_month'].unique(), reverse=True)
    
    if len(months) == 0:
        st.warning("没有足够的数据生成报表")
        return
    
    selected_month = st.selectbox("选择月份", months, format_func=lambda x: x.strftime('%Y年%m月'))
    
    month_df = df[df['year_month'] == selected_month]
    
    st.subheader(f"{selected_month.strftime('%Y年%m月')} 消费概览")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("总交易笔数", len(month_df))
    with col2:
        st.metric("总消费金额", f"¥{month_df['amount'].sum():,.2f}")
    with col3:
        st.metric("日均消费", f"¥{month_df['amount'].sum() / month_df['date'].dt.day.nunique():,.2f}")
    with col4:
        st.metric("单笔最高", f"¥{month_df['amount'].max():,.2f}")
    
    st.subheader("类别消费分析")
    
    col1, col2 = st.columns(2)
    
    with col1:
        category_summary = month_df.groupby('category').agg({
            'amount': ['sum', 'count'],
        }).round(2)
        category_summary.columns = ['金额', '笔数']
        category_summary['金额占比'] = (category_summary['金额'] / category_summary['金额'].sum() * 100).round(1).astype(str) + '%'
        category_summary = category_summary.sort_values('金额', ascending=False)
        st.dataframe(category_summary)
    
    with col2:
        fig, ax = plt.subplots(figsize=(10, 6))
        category_amounts = month_df.groupby('category')['amount'].sum().sort_values(ascending=True)
        category_amounts.plot(kind='barh', ax=ax)
        ax.set_title('各类别消费金额')
        ax.set_xlabel('金额')
        for i, v in enumerate(category_amounts.values):
            ax.text(v, i, f'¥{v:,.0f}', va='center')
        st.pyplot(fig)
    
    if 'city' in month_df.columns and month_df['city'].notna().any():
        st.subheader("城市消费分析")
        city_summary = month_df.groupby('city').agg({
            'amount': ['sum', 'count'],
        }).round(2)
        city_summary.columns = ['金额', '笔数']
        city_summary = city_summary.sort_values('金额', ascending=False)
        st.dataframe(city_summary)
    
    st.subheader("每日消费趋势")
    
    daily_amounts = month_df.groupby(month_df['date'].dt.day)['amount'].sum()
    
    fig, ax = plt.subplots(figsize=(12, 6))
    daily_amounts.plot(kind='line', marker='o', ax=ax)
    ax.set_title(f'{selected_month.strftime("%Y年%m月")} 每日消费趋势')
    ax.set_xlabel('日期')
    ax.set_ylabel('金额')
    ax.grid(True, alpha=0.3)
    st.pyplot(fig)
    
    st.subheader("TOP 10 商户消费")
    top_merchants = month_df.groupby('merchant')['amount'].sum().sort_values(ascending=False).head(10)
    
    fig, ax = plt.subplots(figsize=(12, 6))
    top_merchants.plot(kind='bar', ax=ax)
    ax.set_title('TOP 10 商户消费金额')
    ax.set_xlabel('商户')
    ax.set_ylabel('金额')
    plt.xticks(rotation=45, ha='right')
    st.pyplot(fig)
    
    st.subheader("导出报表")
    report_name = f"消费报表_{selected_month.strftime('%Y%m')}"
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        category_summary.to_excel(writer, sheet_name='类别统计')
        month_df.to_excel(writer, sheet_name='交易明细', index=False)
    
    st.download_button(
        "下载Excel报表",
        output.getvalue(),
        f"{report_name}.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

def anomaly_detection_page():
    st.header("🚨 异常检测")
    
    if st.session_state.classified_transactions.empty:
        st.warning("请先导入数据")
        return
    
    df = st.session_state.classified_transactions.copy()
    
    if st.button("开始异常检测"):
        with st.spinner("正在检测异常..."):
            transactions_list = df.to_dict('records')
            anomalies = anomaly_detector.detect_anomalies(transactions_list)
            st.session_state.anomalies = anomalies
            st.rerun()
    
    if 'anomalies' in st.session_state and st.session_state.anomalies:
        anomalies = st.session_state.anomalies
        summary = anomaly_detector.get_anomaly_summary(anomalies)
        
        st.subheader("动态阈值设置")
        threshold_info = summary.get('threshold_used', {})
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            amt_q = threshold_info.get('amount_quantile')
            st.metric("金额95分位数阈值", f"¥{amt_q:,.2f}" if amt_q else "N/A")
        with col2:
            freq_q = threshold_info.get('frequency_quantile')
            st.metric("频次95分位数阈值", f"{freq_q:.0f}笔/天" if freq_q else "N/A")
        with col3:
            new_q = threshold_info.get('new_merchant_quantile')
            st.metric("新商户75分位数阈值", f"¥{new_q:,.2f}" if new_q else "N/A")
        with col4:
            hour_q = threshold_info.get('unusual_hour_quantile')
            st.metric("异常时段中位数阈值", f"¥{hour_q:,.2f}" if hour_q else "N/A")
        
        st.subheader("异常统计")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("异常总数", summary['total_anomalies'])
        with col2:
            st.metric("高风险", summary['by_severity']['high'])
        with col3:
            st.metric("中风险", summary['by_severity']['medium'])
        with col4:
            st.metric("高风险金额", f"¥{summary['high_risk_amount']:,.2f}")
        
        st.subheader("异常类型分布")
        anomaly_types = pd.Series(summary['by_type'])
        fig, ax = plt.subplots(figsize=(10, 6))
        anomaly_types.plot(kind='bar', ax=ax)
        ax.set_title('异常类型分布')
        ax.set_ylabel('数量')
        st.pyplot(fig)
        
        st.subheader("异常详情")
        
        severity_colors = {
            'high': '🔴 高风险',
            'medium': '🟡 中风险',
            'low': '🟢 低风险'
        }
        
        for anomaly in anomalies:
            with st.expander(f"{severity_colors.get(anomaly['severity'], '⚪')} - {anomaly['type']}"):
                st.write(f"**描述**: {anomaly['description']}")
                st.write(f"**商户**: {anomaly.get('merchant', 'N/A')}")
                st.write(f"**类别**: {anomaly.get('category', 'N/A')}")
                st.write(f"**金额**: ¥{anomaly.get('amount', 0):,.2f}")
                if 'anomaly_count' in anomaly:
                    st.write(f"**异常维度**: {anomaly['anomaly_count']} 个")
                if 'threshold_info' in anomaly:
                    th_info = anomaly['threshold_info']
                    st.write(f"**阈值类型**: {th_info.get('type', 'N/A')}")
                    if th_info.get('type') == 'quantile':
                        st.write(f"**分位数**: {th_info.get('quantile', 0) * 100:.0f}%")
    else:
        st.info("点击按钮开始异常检测，或暂无检测到的异常")
    
    st.subheader("异常检测说明")
    st.markdown("""
    - **异常金额**: 超过该类别消费金额的95分位数（动态阈值，基于用户历史消费）
    - **高频消费**: 当日消费次数超过95分位数（动态阈值，基于用户历史消费）
    - **异常时段消费**: 凌晨0-6点或深夜23点后的消费，金额超过消费中位数
    - **新商户大额消费**: 首次在新商户的消费超过75分位数
    - **多维度异常**: 同时触发多个异常规则
    """)

def merchant_management_page():
    st.header("🏪 商户库管理")
    
    tab1, tab2, tab3 = st.tabs(["查看商户", "添加商户", "搜索商户"])
    
    with tab1:
        selected_category = st.selectbox("选择类别", CATEGORIES)
        merchants = merchant_db.get_merchants_by_category(selected_category)
        
        st.write(f"共 {len(merchants)} 个商户")
        
        if merchants:
            merchant_data = []
            for m in merchants:
                merchant_data.append({
                    '商户名称': m.name,
                    '子分类': m.sub_category or '-',
                    '城市': m.city or '-',
                    '品牌': m.brand or '-'
                })
            df = pd.DataFrame(merchant_data)
            st.dataframe(df, use_container_width=True)
            
            merchant_to_delete = st.selectbox("选择要删除的商户", [''] + [m.name for m in merchants])
            city_to_delete = st.selectbox("选择城市（可选）", ['全部'] + list(set([m.city for m in merchants if m.city])))
            if merchant_to_delete and st.button("删除商户"):
                city = None if city_to_delete == '全部' else city_to_delete
                if merchant_db.remove_merchant(merchant_to_delete, city):
                    st.success(f"已删除商户: {merchant_to_delete}")
                    st.rerun()
                else:
                    st.error("删除失败")
    
    with tab2:
        st.subheader("添加新商户")
        with st.form("add_merchant_form"):
            new_merchant = st.text_input("商户名称")
            new_category = st.selectbox("所属类别", CATEGORIES)
            
            hierarchy = merchant_db.get_category_hierarchy()
            sub_categories = []
            if new_category in hierarchy:
                sub_categories = hierarchy[new_category].get('children', [])
            new_sub_category = st.selectbox("子分类", ['无'] + sub_categories)
            
            new_city = st.selectbox("城市", ['无'] + CITIES[1:])
            new_brand = st.text_input("品牌（可选）")
            
            if st.form_submit_button("添加"):
                if new_merchant:
                    merchant_info = MerchantInfo(
                        name=new_merchant,
                        category=new_category,
                        sub_category=new_sub_category if new_sub_category != '无' else None,
                        city=new_city if new_city != '无' else None,
                        brand=new_brand if new_brand else None,
                        keywords=[new_merchant]
                    )
                    if merchant_db.add_merchant(merchant_info):
                        st.success(f"已添加商户: {new_merchant} -> {new_category}")
                    else:
                        st.error("添加失败（商户可能已存在）")
                else:
                    st.error("请输入商户名称")
    
    with tab3:
        st.subheader("搜索商户")
        search_keyword = st.text_input("输入关键词")
        if search_keyword:
            results = merchant_db.search_merchants(search_keyword)
            if results:
                result_data = []
                for m in results:
                    result_data.append({
                        '商户名称': m.name,
                        '类别': m.category,
                        '子分类': m.sub_category or '-',
                        '城市': m.city or '-',
                        '品牌': m.brand or '-'
                    })
                df = pd.DataFrame(result_data)
                st.dataframe(df, use_container_width=True)
            else:
                st.info("未找到匹配的商户")
    
    st.subheader("模糊匹配测试")
    test_merchant = st.text_input("输入商户名称测试匹配")
    test_location = st.selectbox("输入城市（可选）", ['无'] + CITIES[1:])
    if test_merchant:
        location = test_location if test_location != '无' else None
        category, score, merchant_info = merchant_db.fuzzy_match(test_merchant, location)
        st.write(f"匹配结果: {category or '未匹配'} (置信度: {score}%)")
        if merchant_info:
            st.write(f"匹配商户: {merchant_info.name}")
            if merchant_info.city:
                st.write(f"城市: {merchant_info.city}")
            if merchant_info.sub_category:
                st.write(f"子分类: {merchant_info.sub_category}")

def rule_engine_page():
    st.header("⚙️ 规则引擎")
    
    tab1, tab2, tab3 = st.tabs(["查看规则", "添加规则", "测试规则"])
    
    with tab1:
        rules = rule_engine.get_all_rules()
        
        for rule in rules:
            col1, col2, col3 = st.columns([3, 1, 1])
            
            with col1:
                status_icon = "✅" if rule.enabled else "❌"
                with st.expander(f"{status_icon} [{rule.priority}] {rule.name}"):
                    st.write(f"**ID**: {rule.id}")
                    st.write(f"**逻辑操作**: {rule.logical_op}")
                    st.write("**条件**:")
                    for cond in rule.conditions:
                        st.write(f"  - {cond.type.value}: {cond.value} ({cond.field})")
                    st.write(f"**动作**: {rule.action.value} -> {rule.action_value}")
            
            with col2:
                if st.button("启用/禁用", key=f"toggle_{rule.id}"):
                    rule_engine.toggle_rule(rule.id)
                    st.rerun()
            
            with col3:
                if st.button("删除", key=f"delete_{rule.id}"):
                    if rule_engine.delete_rule(rule.id):
                        st.success(f"已删除规则: {rule.name}")
                        st.rerun()
    
    with tab2:
        st.subheader("添加新规则")
        with st.form("add_rule_form"):
            rule_name = st.text_input("规则名称")
            rule_priority = st.number_input("优先级", min_value=0, max_value=100, value=0)
            
            st.subheader("条件设置")
            cond_type = st.selectbox(
                "条件类型",
                [e.value for e in RuleConditionType]
            )
            cond_field = st.text_input("字段", value="merchant")
            cond_value = st.text_input("值 (多个值用逗号分隔)")
            
            logical_op = st.selectbox("条件逻辑", ["AND", "OR"])
            
            st.subheader("动作设置")
            action_type = st.selectbox(
                "动作类型",
                [e.value for e in RuleAction]
            )
            action_value = st.text_input("动作值")
            
            if st.form_submit_button("添加规则"):
                values = [v.strip() for v in cond_value.split(',')] if ',' in cond_value else cond_value
                
                try:
                    condition = RuleCondition(
                        type=RuleConditionType(cond_type),
                        value=values,
                        field=cond_field
                    )
                    
                    new_rule = Rule(
                        id=f"rule_{uuid.uuid4().hex[:8]}",
                        name=rule_name,
                        conditions=[condition],
                        action=RuleAction(action_type),
                        action_value=action_value,
                        priority=rule_priority,
                        enabled=True,
                        logical_op=logical_op
                    )
                    
                    if rule_engine.add_rule(new_rule):
                        st.success(f"规则添加成功: {rule_name}")
                    else:
                        st.error("规则添加失败")
                except Exception as e:
                    st.error(f"错误: {e}")
    
    with tab3:
        st.subheader("规则测试")
        test_merchant = st.text_input("测试商户名称")
        test_amount = st.number_input("测试金额", min_value=0.0, value=100.0)
        test_location = st.selectbox("测试城市", CITIES)
        test_date = st.date_input("测试日期", value=date.today())
        test_time = st.time_input("测试时间", value=datetime.now().time())
        
        if st.button("测试规则"):
            test_transaction = {
                'merchant': test_merchant,
                'amount': test_amount,
                'location': test_location if test_location else '',
                'date': test_date.strftime('%Y-%m-%d'),
                'time': test_time.strftime('%H:%M:%S')
            }
            
            result = rule_engine.apply_rules(test_transaction)
            
            st.write("**测试结果:**")
            st.write(f"匹配规则: {result['matched_rules']}")
            st.write(f"分类结果: {result['category']}")
            st.write(f"标签: {result['tags']}")
            st.write(f"异常标记: {result['anomaly_flags']}")

def tax_calculation_page():
    st.header("💰 税务计算")
    
    if st.session_state.classified_transactions.empty:
        st.warning("请先导入数据")
        return
    
    df = st.session_state.classified_transactions.copy()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("税务参数设置")
        tax_mode = st.selectbox("计算模式", ["个人所得税", "企业所得税"])
        tax_year = st.number_input("纳税年度", min_value=2020, max_value=2030, value=datetime.now().year)
        
        if tax_mode == "个人所得税":
            annual_income = st.number_input("年度税前收入", min_value=0.0, value=200000.0, step=1000.0)
            tax_rate = st.number_input("适用税率", min_value=0.0, max_value=1.0, value=0.25, step=0.01)
            
            st.subheader("专项附加扣除")
            special_deductions = {}
            for ded_name, ded_info in SPECIAL_DEDUCTIONS.items():
                default_amount = ded_info.get("amount", 0.0)
                amount = st.number_input(f"{ded_name}", min_value=0.0, value=default_amount, step=100.0, help=ded_info.get("description", ""))
                if amount > 0:
                    special_deductions[ded_name] = amount
            
            other_deductions = st.number_input("其他扣除", min_value=0.0, value=0.0, step=100.0)
            
            if st.button("计算个税抵扣"):
                config = TaxConfig(
                    tax_type="personal",
                    annual_income=annual_income,
                    tax_rate=tax_rate,
                    special_deductions=special_deductions,
                    other_deductions=other_deductions
                )
                tax_calculator.update_config(config)
                
                transactions_list = df.to_dict('records')
                result = tax_calculator.calculate_personal_deduction(transactions_list, tax_year)
                st.session_state.tax_result = result
                st.rerun()
        else:
            annual_revenue = st.number_input("年度营业收入", min_value=0.0, value=1000000.0, step=10000.0)
            business_type = st.selectbox("企业类型", ["enterprise", "small_business", "individual"])
            tax_rate = st.number_input("企业所得税率", min_value=0.0, max_value=1.0, value=0.25, step=0.01)
            
            if st.button("计算企业抵扣"):
                config = TaxConfig(
                    tax_type="business",
                    annual_income=annual_revenue,
                    tax_rate=tax_rate
                )
                tax_calculator.update_config(config)
                
                transactions_list = df.to_dict('records')
                result = tax_calculator.calculate_business_deduction(transactions_list, business_type, annual_revenue)
                st.session_state.tax_result = result
                st.rerun()
    
    with col2:
        if 'tax_result' in st.session_state and st.session_state.tax_result:
            result = st.session_state.tax_result
            
            st.subheader("计算结果")
            
            if tax_mode == "个人所得税":
                col_a, col_b = st.columns(2)
                with col_a:
                    st.metric("年度收入", f"¥{result.get('annual_income', 0):,.2f}")
                    st.metric("总扣除额", f"¥{result.get('total_deduction', 0):,.2f}")
                    st.metric("应纳税所得额", f"¥{result.get('taxable_income', 0):,.2f}")
                with col_b:
                    st.metric("应缴个税", f"¥{result.get('tax_payable', 0):,.2f}")
                    st.metric("节税金额", f"¥{result.get('tax_saved', 0):,.2f}")
                    st.metric("实际税率", f"{result.get('effective_tax_rate', 0):.2f}%")
                
                st.info(f"""
                **扣除明细：**
                - 基本减除费用：¥{result.get('basic_deduction', 60000):,.2f}
                - 消费类可抵扣：¥{sum(d['deductible_amount'] for d in result.get('category_deductions', [])):,.2f}
                - 专项附加扣除：¥{result.get('special_total', 0):,.2f}
                - 其他扣除：¥{result.get('other_deductions', 0):,.2f}
                """)
                
                if result.get('special_deductions'):
                    st.subheader("专项附加扣除明细")
                    special_df = pd.DataFrame([
                        {'项目': k, '金额': f"¥{v:,.2f}"}
                        for k, v in result['special_deductions'].items()
                    ])
                    st.dataframe(special_df, use_container_width=True)
            else:
                col_a, col_b = st.columns(2)
                with col_a:
                    st.metric("年度营业收入", f"¥{result.get('annual_revenue', 0):,.2f}")
                    st.metric("总可抵扣额", f"¥{result.get('total_deductible', 0):,.2f}")
                with col_b:
                    st.metric("预计节税", f"¥{result.get('tax_saved', 0):,.2f}")
                    st.metric("适用税率", f"{result.get('effective_tax_rate', 0) * 100:.1f}%")
            
            st.subheader("各类别抵扣明细")
            deductions_df = tax_calculator.get_deduction_summary(df.to_dict('records'), "personal" if tax_mode == "个人所得税" else "business")
            if not deductions_df.empty:
                display_cols = ['category', 'total_amount', 'deductible_amount', 'rate', 'eligible', 'description']
                available_cols = [c for c in display_cols if c in deductions_df.columns]
                styled_df = deductions_df[available_cols].copy()
                styled_df.columns = ['类别', '总金额', '可抵扣额', '抵扣率', '可抵扣', '说明']
                styled_df['总金额'] = styled_df['总金额'].apply(lambda x: f"¥{x:,.2f}")
                styled_df['可抵扣额'] = styled_df['可抵扣额'].apply(lambda x: f"¥{x:,.2f}")
                styled_df['抵扣率'] = styled_df['抵扣率'].apply(lambda x: f"{x*100:.0f}%")
                styled_df['可抵扣'] = styled_df['可抵扣'].apply(lambda x: "✅" if x else "❌")
                st.dataframe(styled_df, use_container_width=True)
        else:
            st.info("请在左侧设置参数并点击计算按钮")
    
    st.subheader("抵扣规则说明")
    if tax_mode == "个人所得税":
        st.markdown("""
        - **交通费用**：公务交通可全额抵扣，上限18,000元/年
        - **医疗费用**：超过15,000元部分可抵扣，上限80,000元/年
        - **餐饮/购物/娱乐**：个人消费不可抵扣个税
        - **专项附加扣除**：子女教育、继续教育、住房贷款等可按规定扣除
        """)
    else:
        st.markdown("""
        - **餐饮/娱乐**：业务招待费按60%扣除，上限为营业收入的5‰
        - **交通**：差旅费、交通费可100%扣除
        - **购物**：办公用品、设备购置可100%扣除
        - **医疗**：补充医疗可在职工福利费中扣除
        """)

def budget_management_page():
    st.header("📊 预算管理")
    
    if st.session_state.classified_transactions.empty:
        st.warning("请先导入数据")
        return
    
    df = st.session_state.classified_transactions.copy()
    transactions_list = df.to_dict('records')
    
    alerts = budget_manager.check_budget_alerts(transactions_list)
    
    if alerts:
        st.subheader("⚠️ 预算预警")
        for alert in alerts:
            if alert.alert_level == "critical":
                st.error(alert.message)
            else:
                st.warning(alert.message)
    
    tab1, tab2, tab3, tab4 = st.tabs(["预算概览", "设置预算", "预算对比", "调整建议"])
    
    with tab1:
        st.subheader("本月预算执行情况")
        
        budget_summary = budget_manager.get_budget_summary(transactions_list)
        if not budget_summary.empty:
            col1, col2, col3, col4 = st.columns(4)
            total_budget = budget_summary['预算金额'].sum()
            total_spent = budget_summary['已消费'].sum()
            total_remaining = budget_summary['剩余预算'].sum()
            completion_rate = total_spent / total_budget * 100 if total_budget > 0 else 0
            
            with col1:
                st.metric("总预算", f"¥{total_budget:,.2f}")
            with col2:
                st.metric("已消费", f"¥{total_spent:,.2f}", f"{completion_rate:.1f}%")
            with col3:
                st.metric("剩余预算", f"¥{total_remaining:,.2f}")
            with col4:
                alert_count = len(alerts)
                st.metric("预警数", alert_count, delta_color="inverse")
            
            st.dataframe(budget_summary, use_container_width=True)
            
            fig, ax = plt.subplots(figsize=(12, 6))
            categories = budget_summary['类别']
            x = range(len(categories))
            width = 0.35
            
            ax.bar([i - width/2 for i in x], budget_summary['预算金额'], width, label='预算', alpha=0.7)
            ax.bar([i + width/2 for i in x], budget_summary['已消费'], width, label='已消费', alpha=0.7)
            
            ax.set_xlabel('类别')
            ax.set_ylabel('金额')
            ax.set_title('各类别预算执行情况')
            ax.set_xticks(x)
            ax.set_xticklabels(categories, rotation=45)
            ax.legend()
            ax.grid(True, alpha=0.3)
            st.pyplot(fig)
        
        if alerts:
            st.subheader("预警详情")
            for alert in alerts:
                with st.expander(f"{alert.category} - {'🔴' if alert.alert_level == 'critical' else '🟡'}"):
                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        st.write(f"**已消费**: ¥{alert.current_spending:,.2f}")
                        st.write(f"**预算**: ¥{alert.budget:,.2f}")
                    with col_b:
                        st.write(f"**完成比例**: {alert.ratio*100:.1f}%")
                        st.write(f"**剩余天数**: {alert.remaining_days}天")
                    with col_c:
                        st.write(f"**剩余预算**: ¥{alert.remaining_budget:,.2f}")
                        st.write(f"**日均可用**: ¥{alert.daily_allowed:,.2f}")
                    st.write(f"**预计月末消费**: ¥{alert.projected_spending:,.2f}")
    
    with tab2:
        st.subheader("设置类别预算")
        
        budgets = budget_manager.get_all_budgets()
        
        for category, budget in budgets.items():
            col_a, col_b, col_c = st.columns([2, 1, 1])
            with col_a:
                st.write(f"**{category}**")
            with col_b:
                new_amount = st.number_input(
                    f"预算金额_{category}",
                    min_value=0.0,
                    value=budget.monthly_budget,
                    step=100.0,
                    label_visibility="collapsed"
                )
            with col_c:
                if st.button(f"更新_{category}", key=f"update_{category}"):
                    budget_manager.set_budget(category, new_amount)
                    st.success(f"{category}预算已更新")
                    st.rerun()
        
        st.divider()
        st.subheader("添加新类别预算")
        new_category = st.text_input("新类别名称")
        new_category_budget = st.number_input("新类别预算", min_value=0.0, value=1000.0, step=100.0)
        if st.button("添加类别预算") and new_category:
            budget_manager.set_budget(new_category, new_category_budget)
            st.success(f"已添加 {new_category} 预算")
            st.rerun()
        
        st.divider()
        st.subheader("预算阈值设置")
        warning_threshold = st.slider("预警阈值（%）", min_value=50, max_value=90, value=80)
        critical_threshold = st.slider("严重预警阈值（%）", min_value=80, max_value=100, value=95)
        
        if st.button("应用阈值到所有类别"):
            for category in budgets.keys():
                budget_manager.set_budget(
                    category,
                    budgets[category].monthly_budget,
                    warning_threshold=warning_threshold / 100,
                    critical_threshold=critical_threshold / 100
                )
            st.success("阈值已更新")
            st.rerun()
    
    with tab3:
        st.subheader("预算vs实际对比")
        months = st.slider("查看最近几个月", min_value=3, max_value=12, value=6)
        
        comparison_df = budget_manager.get_budget_vs_actual(transactions_list, months)
        if not comparison_df.empty:
            st.dataframe(comparison_df, use_container_width=True)
            
            fig, axes = plt.subplots(1, 2, figsize=(15, 6))
            
            pivot_df = comparison_df.pivot(index='月份', columns='类别', values='差额')
            pivot_df.plot(kind='bar', ax=axes[0], title='各月差额（实际-预算）')
            axes[0].set_ylabel('差额')
            axes[0].axhline(y=0, color='black', linewidth=0.5)
            axes[0].grid(True, alpha=0.3)
            
            completion_pivot = comparison_df.pivot(index='月份', columns='类别', values='完成率')
            completion_pivot.plot(kind='line', marker='o', ax=axes[1], title='各月预算完成率（%）')
            axes[1].set_ylabel('完成率（%）')
            axes[1].axhline(y=100, color='red', linestyle='--', label='预算线')
            axes[1].legend()
            axes[1].grid(True, alpha=0.3)
            
            plt.tight_layout()
            st.pyplot(fig)
    
    with tab4:
        st.subheader("预算调整建议")
        months = st.slider("分析历史月份", min_value=2, max_value=6, value=3, key="suggest_months")
        
        suggestions = budget_manager.suggest_budget_adjustment(transactions_list, months)
        if suggestions:
            for s in suggestions:
                col_a, col_b, col_c = st.columns([2, 1, 1])
                with col_a:
                    st.write(f"**{s['category']}**")
                    st.write(f"{s['suggestion']}（偏离 {s['deviation']:+.1f}%）")
                    st.caption(f"近{months}个月月均: ¥{s['monthly_average']:,.2f}")
                with col_b:
                    st.write(f"**当前预算**: ¥{s['current_budget']:,.2f}")
                    st.write(f"**建议预算**: ¥{s['recommended_budget']:,.2f}")
                with col_c:
                    if st.button(f"应用建议_{s['category']}", key=f"apply_{s['category']}"):
                        budget_manager.set_budget(s['category'], s['recommended_budget'])
                        st.success(f"{s['category']}预算已调整")
                        st.rerun()
        else:
            st.info("当前预算设置合理，无需调整")

def trend_analysis_page():
    st.header("📈 消费趋势分析")
    
    if st.session_state.classified_transactions.empty:
        st.warning("请先导入数据")
        return
    
    df = st.session_state.classified_transactions.copy()
    transactions_list = df.to_dict('records')
    
    st.subheader("📊 同期对比")
    
    compare_type = st.radio("对比方式", ["环比（上月）", "同比（去年同月）"], horizontal=True)
    compare_key = "previous_month" if compare_type == "环比（上月）" else "same_month_last_year"
    
    comparison = trend_analyzer.compare_month_over_month(transactions_list, compare_key)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(comparison.current_period, f"¥{comparison.current_total:,.2f}")
    with col2:
        st.metric(comparison.previous_period, f"¥{comparison.previous_total:,.2f}")
    with col3:
        delta = f"+{comparison.change_amount:,.2f}" if comparison.is_increase else f"{comparison.change_amount:,.2f}"
        delta_pct = f"+{comparison.change_percent:.1f}%" if comparison.is_increase else f"{comparison.change_percent:.1f}%"
        st.metric("变动额", f"¥{delta}", delta_pct)
    with col4:
        trend_icon = "📈" if comparison.is_increase else "📉"
        st.metric("趋势", f"{trend_icon} {comparison.trend}")
    
    st.divider()
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["类别涨跌", "月度趋势", "周内规律", "时段分析", "消费预测"])
    
    with tab1:
        st.subheader("各类别涨跌情况")
        
        category_trends = trend_analyzer.get_category_trend(transactions_list, compare_key)
        
        if category_trends:
            trend_df = pd.DataFrame([{
                '类别': t.category,
                '本期': f"¥{t.current_amount:,.2f}",
                '上期': f"¥{t.previous_amount:,.2f}",
                '变动额': f"¥{t.change_amount:+,.2f}",
                '变动率': f"{t.change_percent:+.1f}%",
                '趋势': t.trend,
                '占比': f"{t.contribution:.1f}%"
            } for t in category_trends])
            
            st.dataframe(trend_df, use_container_width=True)
            
            fig, ax = plt.subplots(figsize=(12, 6))
            categories = [t.category for t in category_trends]
            changes = [t.change_percent for t in category_trends]
            colors = ['green' if c >= 0 else 'red' for c in changes]
            
            bars = ax.bar(categories, changes, color=colors, alpha=0.7)
            ax.axhline(y=0, color='black', linewidth=0.5)
            ax.set_title(f'{compare_type}各类别涨跌（%）')
            ax.set_ylabel('变动率（%）')
            ax.set_xlabel('类别')
            plt.xticks(rotation=45)
            
            for bar, change in zip(bars, changes):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{change:+.1f}%', ha='center', va='bottom' if height >= 0 else 'top')
            
            ax.grid(True, alpha=0.3, axis='y')
            st.pyplot(fig)
            
            col_grow, col_decline = st.columns(2)
            with col_grow:
                st.subheader("📈 涨幅TOP3")
                growing = trend_analyzer.get_top_growing_categories(transactions_list, top_n=3)
                for g in growing:
                    st.info(f"**{g['category']}**: +{g['change_percent']:.1f}% (¥{g['current_amount']:,.2f})")
            with col_decline:
                st.subheader("📉 跌幅TOP3")
                declining = trend_analyzer.get_top_declining_categories(transactions_list, top_n=3)
                for d in declining:
                    st.info(f"**{d['category']}**: {d['change_percent']:.1f}% (¥{d['current_amount']:,.2f})")
    
    with tab2:
        st.subheader("月度消费趋势")
        months = st.slider("显示最近几个月", min_value=3, max_value=24, value=12, key="trend_months")
        
        monthly_df = trend_analyzer.get_monthly_trend(transactions_list, months)
        if not monthly_df.empty:
            st.dataframe(monthly_df, use_container_width=True)
            
            fig, ax = plt.subplots(figsize=(12, 6))
            ax.plot(monthly_df['月份'], monthly_df['总消费'], marker='o', linewidth=2, label='总消费')
            
            category_cols = [c for c in monthly_df.columns if c not in ['月份', '总消费']]
            for col in category_cols:
                ax.plot(monthly_df['月份'], monthly_df[col], marker='.', linestyle='--', label=col, alpha=0.7)
            
            ax.set_title(f'近{months}个月消费趋势')
            ax.set_xlabel('月份')
            ax.set_ylabel('消费金额')
            ax.legend(loc='best')
            ax.grid(True, alpha=0.3)
            plt.xticks(rotation=45)
            st.pyplot(fig)
            
            st.subheader("季度趋势")
            quarters = st.slider("显示最近几个季度", min_value=2, max_value=12, value=6)
            quarterly_df = trend_analyzer.get_quarterly_trend(transactions_list, quarters)
            if not quarterly_df.empty:
                fig, ax = plt.subplots(figsize=(12, 6))
                ax.plot(quarterly_df['季度'], quarterly_df['总消费'], marker='s', linewidth=2, color='orange')
                ax.set_title(f'近{quarters}个季度消费趋势')
                ax.set_xlabel('季度')
                ax.set_ylabel('消费金额')
                ax.grid(True, alpha=0.3)
                plt.xticks(rotation=45)
                st.pyplot(fig)
    
    with tab3:
        st.subheader("周内消费规律")
        weeks = st.slider("分析最近几周", min_value=4, max_value=24, value=12, key="week_pattern")
        
        weekday_df = trend_analyzer.get_weekday_pattern(transactions_list, weeks)
        if not weekday_df.empty:
            st.dataframe(weekday_df, use_container_width=True)
            
            fig, axes = plt.subplots(1, 3, figsize=(18, 5))
            
            axes[0].bar(weekday_df['星期'], weekday_df['总消费'], color='skyblue', alpha=0.7)
            axes[0].set_title('各天总消费')
            axes[0].set_ylabel('金额')
            axes[0].tick_params(axis='x', rotation=45)
            
            axes[1].bar(weekday_df['星期'], weekday_df['平均每笔'], color='lightgreen', alpha=0.7)
            axes[1].set_title('各天单笔平均消费')
            axes[1].set_ylabel('金额')
            axes[1].tick_params(axis='x', rotation=45)
            
            axes[2].bar(weekday_df['星期'], weekday_df['交易次数'], color='salmon', alpha=0.7)
            axes[2].set_title('各天交易次数')
            axes[2].set_ylabel('次数')
            axes[2].tick_params(axis='x', rotation=45)
            
            for ax in axes:
                ax.grid(True, alpha=0.3, axis='y')
            
            plt.tight_layout()
            st.pyplot(fig)
    
    with tab4:
        st.subheader("时段消费分析")
        weeks = st.slider("分析最近几周", min_value=2, max_value=12, value=4, key="hour_pattern")
        
        hourly_df = trend_analyzer.get_hourly_pattern(transactions_list, weeks)
        if not hourly_df.empty:
            st.dataframe(hourly_df, use_container_width=True)
            
            fig, axes = plt.subplots(1, 3, figsize=(18, 5))
            
            axes[0].bar(hourly_df['时段'], hourly_df['总消费'], color='skyblue', alpha=0.7)
            axes[0].set_title('各时段总消费')
            axes[0].set_ylabel('金额')
            axes[0].tick_params(axis='x', rotation=90)
            
            axes[1].bar(hourly_df['时段'], hourly_df['平均每笔'], color='lightgreen', alpha=0.7)
            axes[1].set_title('各时段单笔平均消费')
            axes[1].set_ylabel('金额')
            axes[1].tick_params(axis='x', rotation=90)
            
            axes[2].bar(hourly_df['时段'], hourly_df['交易次数'], color='salmon', alpha=0.7)
            axes[2].set_title('各时段交易次数')
            axes[2].set_ylabel('次数')
            axes[2].tick_params(axis='x', rotation=90)
            
            for ax in axes:
                ax.grid(True, alpha=0.3, axis='y')
            
            plt.tight_layout()
            st.pyplot(fig)
    
    with tab5:
        st.subheader("下月消费预测")
        
        forecast_method = st.selectbox(
            "预测方法",
            ["moving_average", "weighted_moving_average", "trend"],
            format_func=lambda x: {
                'moving_average': '移动平均法',
                'weighted_moving_average': '加权移动平均法',
                'trend': '趋势外推法'
            }[x]
        )
        
        forecast = trend_analyzer.forecast_next_month(transactions_list, forecast_method)
        
        if forecast:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("预测消费", f"¥{forecast['forecast']:,.2f}")
            with col2:
                st.metric("预测区间", f"¥{forecast['lower']:,.2f} ~ ¥{forecast['upper']:,.2f}")
            with col3:
                st.metric("置信度", f"{forecast['confidence']*100:.0f}%")
            
            st.info(f"""
            **预测详情：**
            - 方法：{forecast_method}
            - 历史数据点：{forecast['historical_points']} 个月
            - 95%置信区间下限：¥{forecast['lower']:,.2f}
            - 95%置信区间上限：¥{forecast['upper']:,.2f}
            """)
            
            st.warning("⚠️ 预测仅供参考，实际消费可能因节假日、特殊事件等因素有所不同")

if __name__ == "__main__":
    main()
