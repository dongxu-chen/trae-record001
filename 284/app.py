import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from io import StringIO

from data_generator import PromotionDataGenerator
from did_model import DIDModel
from psm_model import PSMModel
from prediction_model import PromotionPredictor
from channel_attribution import ChannelAttribution
from promotion_fatigue import PromotionFatigueDetector
from budget_simulator import BudgetSimulator

st.set_page_config(
    page_title="促销活动效果评估模型",
    page_icon="📊",
    layout="wide"
)

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

def main():
    st.title("📊 促销活动效果评估模型")
    st.markdown("""
    本工具使用**因果推断方法**（双重差分法、倾向性得分匹配）来评估促销活动的真实效果，
    剥离自然增长因素，准确估计促销带来的增量销售。
    """)
    
    with st.sidebar:
        st.header("⚙️ 设置")
        method = st.radio(
            "选择因果推断方法",
            ["双重差分法 (DID)", "倾向性得分匹配 (PSM)", "两种方法对比"]
        )
        
        st.subheader("数据设置")
        data_source = st.radio(
            "数据来源",
            ["使用模拟数据", "上传CSV数据"]
        )
        
        if data_source == "使用模拟数据":
            n_products = st.slider("商品数量", 50, 500, 200)
            n_periods = st.slider("时间周期数", 4, 12, 8)
            seed = st.number_input("随机种子", 1, 100, 42)
        else:
            uploaded_file = st.file_uploader("上传CSV文件", type="csv")
    
    if data_source == "使用模拟数据":
        generator = PromotionDataGenerator(seed=seed)
        df = generator.generate_synthetic_data(n_products, n_periods)
        st.success(f"✅ 已生成 {len(df)} 条模拟数据，包含 {n_products} 个商品，{n_periods} 个时间周期")
    else:
        if uploaded_file is not None:
            df = pd.read_csv(uploaded_file)
            st.success(f"✅ 已加载 {len(df)} 条数据")
        else:
            st.info("👆 请在左侧上传CSV文件")
            st.stop()
    
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📈 数据概览", 
        "🔬 因果分析", 
        "🎯 多渠道归因",
        "� 促销疲劳检测",
        "💰 预算模拟推演",
        "� 预测模拟器"
    ])
    
    with tab1:
        show_data_overview(df)
    
    with tab2:
        if method == "双重差分法 (DID)":
            run_did_analysis(df)
        elif method == "倾向性得分匹配 (PSM)":
            run_psm_analysis(df)
        else:
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("双重差分法 (DID)")
                did_results = run_did_analysis(df, show_ui=False)
            with col2:
                st.subheader("倾向性得分匹配 (PSM)")
                psm_results = run_psm_analysis(df, show_ui=False)
            
            st.subheader("📊 方法对比")
            comparison_df = pd.DataFrame({
                '指标': ['销售提升率 (%)', 'p值', '统计显著性', '样本量'],
                '双重差分法 (DID)': [
                    f"{did_results['treatment_effect_pct']:.2f}%",
                    f"{did_results['p_value']:.4f}",
                    '显著' if did_results['is_significant'] else '不显著',
                    did_results['n_observations']
                ],
                '倾向性得分匹配 (PSM)': [
                    f"{psm_results['att_pct']:.2f}%",
                    f"{psm_results['p_value']:.4f}",
                    '显著' if psm_results['is_significant'] else '不显著',
                    psm_results['n_treated'] + psm_results['n_control']
                ]
            })
            st.table(comparison_df)
    
    with tab3:
        show_channel_attribution()
    
    with tab4:
        show_promotion_fatigue()
    
    with tab5:
        show_budget_simulation()
    
    with tab6:
        show_prediction_simulator()

def show_data_overview(df):
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("商品总数", df['product_id'].nunique())
    with col2:
        st.metric("时间周期数", df['period'].nunique())
    with col3:
        st.metric("参与促销商品数", df[df['is_treated'] == True]['product_id'].nunique())
    with col4:
        st.metric("平均销售额", f"¥{df['sales'].mean():,.0f}")
    
    st.subheader("数据预览")
    st.dataframe(df.head(20), use_container_width=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("销售额趋势")
        sales_trend = df.groupby('period')['sales'].mean().reset_index()
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(sales_trend['period'], sales_trend['sales'], marker='o', linewidth=2)
        ax.set_xlabel('时间周期')
        ax.set_ylabel('平均销售额')
        ax.set_title('整体销售额趋势')
        ax.grid(True, alpha=0.3)
        st.pyplot(fig)
    
    with col2:
        st.subheader("按类别销售分布")
        category_sales = df.groupby('category')['sales'].mean().sort_values(ascending=True)
        fig, ax = plt.subplots(figsize=(10, 5))
        category_sales.plot(kind='barh', ax=ax, color='skyblue')
        ax.set_xlabel('平均销售额')
        ax.set_title('各类别平均销售额')
        st.pyplot(fig)
    
    st.subheader("处理组 vs 控制组对比")
    group_stats = df.groupby('is_treated').agg({
        'sales': ['mean', 'std', 'count'],
        'base_sales': 'mean'
    }).round(2)
    group_stats.index = ['控制组', '处理组']
    st.dataframe(group_stats, use_container_width=True)

def run_did_analysis(df, show_ui=True):
    generator = PromotionDataGenerator()
    df_did = generator.prepare_did_data(df)
    
    did_model = DIDModel()
    
    with st.spinner("正在运行双重差分模型..."):
        results = did_model.fit(df_did)
    
    if show_ui:
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric(
                "促销活动真实效果",
                f"{results['treatment_effect_pct']:.2f}%",
                delta="统计显著" if results['is_significant'] else "不显著",
                delta_color="normal"
            )
        
        with col2:
            st.metric(
                "95%置信区间",
                f"[{results['ci_lower']:.2f}%, {results['ci_upper']:.2f}%]"
            )
        
        st.subheader("📊 详细结果")
        col1, col2 = st.columns(2)
        
        with col1:
            st.dataframe(pd.DataFrame({
                '指标': ['销售提升率', '绝对提升额', 'p值', 'R平方', '观测值数量'],
                '数值': [
                    f"{results['treatment_effect_pct']:.2f}%",
                    f"¥{results['treatment_effect_absolute']:,.2f}",
                    f"{results['p_value']:.6f}",
                    f"{results['r_squared']:.4f}",
                    f"{int(results['n_observations'])}"
                ]
            }), use_container_width=True)
        
        with col2:
            st.pyplot(did_model.plot_treatment_effect())
        
        st.subheader("📈 平行趋势检验")
        parallel_test = did_model.parallel_trend_test(df_did)
        
        if 'p_value' in parallel_test:
            if parallel_test['warning_level'] == 'high':
                st.error(parallel_test['warnings'][0])
                st.warning(parallel_test['warnings'][1])
            elif parallel_test['warning_level'] == 'medium':
                st.warning(parallel_test['warnings'][0])
                st.info(parallel_test['warnings'][1])
            else:
                st.success("✅ 平行趋势假设成立，DID结果可靠")
            
            col1, col2 = st.columns(2)
            with col1:
                st.info(f"""
                **平行趋势检验结果:**
                - F统计量: {parallel_test['f_statistic']:.4f}
                - p值: {parallel_test['p_value']:.4f}
                - 结论: {parallel_test['hypothesis']}
                - 事前周期数: {parallel_test['total_pre_periods']}
                - 显著偏离周期数: {parallel_test['significant_violations']}
                """)
            with col2:
                st.pyplot(did_model.plot_parallel_trend(df_did))
            
            if 'period_coefficients' in parallel_test:
                st.subheader("📊 事前趋势系数图 (事件研究法)")
                st.pyplot(did_model.plot_pre_trend_coefficients(parallel_test))
                st.caption("* 表示该周期处理效应在5%水平上统计显著，若事前周期存在大量显著系数，则平行趋势假设不成立")
        else:
            st.info(parallel_test['message'])
        
        with st.expander("查看完整模型摘要"):
            st.text(did_model.get_summary())
    
    return results

def run_psm_analysis(df, show_ui=True):
    generator = PromotionDataGenerator()
    df_psm = generator.prepare_psm_data(df)
    
    psm_model = PSMModel()
    
    with st.spinner("正在估计倾向性得分..."):
        df_with_ps = psm_model.estimate_propensity_score(df_psm)
    
    with st.spinner("正在进行匹配..."):
        matched_data = psm_model.match(df_with_ps, caliper=0.05)
        results = psm_model.calculate_treatment_effect()
    
    if show_ui:
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric(
                "平均处理效应 (ATT)",
                f"{results['att_pct']:.2f}%",
                delta="统计显著" if results['is_significant'] else "不显著",
                delta_color="normal"
            )
        
        with col2:
            st.metric(
                "匹配后样本量",
                f"{results['n_treated'] + results['n_control']}",
                delta=f"处理组: {results['n_treated']}, 控制组: {results['n_control']}"
            )
        
        st.subheader("📊 详细结果")
        col1, col2 = st.columns(2)
        
        with col1:
            st.dataframe(pd.DataFrame({
                '指标': ['销售提升率 (ATT)', '绝对提升额', '处理组均值', '控制组均值', 'p值'],
                '数值': [
                    f"{results['att_pct']:.2f}%",
                    f"¥{results['att_absolute']:,.2f}",
                    f"¥{results['treated_mean']:,.2f}",
                    f"¥{results['control_mean']:,.2f}",
                    f"{results['p_value']:.6f}"
                ]
            }), use_container_width=True)
        
        with col2:
            st.pyplot(psm_model.plot_treatment_effect(results))
        
        st.subheader("🎯 平衡性检验")
        col1, col2 = st.columns(2)
        
        with col1:
            st.pyplot(psm_model.plot_propensity_score_distribution(df_with_ps))
        
        with col2:
            covariates = [
                'base_sales', 'avg_sales_pre', 'sales_trend_pre', 
                'sales_std_pre', 'max_sales_pre', 'min_sales_pre',
                'sales_volatility', 'historical_growth_rate', 
                'avg_order_value', 'review_score', 'return_rate',
                'customer_age', 'customer_tenure', 
                'purchase_frequency', 'customer_ltv'
            ]
            available_covariates = [c for c in covariates if c in matched_data.columns]
            balance_df = psm_model.balance_check(matched_data, available_covariates)
            st.pyplot(psm_model.plot_balance_check(balance_df))
        
        st.subheader("匹配后协变量平衡情况")
        balanced_count = balance_df['balanced'].sum()
        total_count = len(balance_df)
        st.metric(
            "协变量平衡率", 
            f"{balanced_count}/{total_count} ({balanced_count/total_count*100:.1f}%)",
            delta="优秀" if balanced_count/total_count >= 0.9 else "良好" if balanced_count/total_count >= 0.8 else "需改进"
        )
        st.dataframe(balance_df.style.applymap(
            lambda x: 'background-color: #90EE90' if x else 'background-color: #FFB6C1',
            subset=['balanced']
        ).format({
            'mean_treated': '{:.2f}',
            'mean_control': '{:.2f}',
            'std_diff': '{:.4f}',
            'p_value': '{:.4f}'
        }), use_container_width=True)
        
        with st.expander("查看完整模型摘要"):
            st.text(psm_model.get_summary(results))
    
    return results

def show_prediction_simulator():
    st.subheader("🔮 促销效果预测模拟器")
    st.markdown("根据历史数据，使用Bootstrap方法预测不同促销参数下的销售提升率及置信区间")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("⚙️ 促销参数设置")
        discount = st.slider("折扣力度", 0.05, 0.5, 0.2, 0.05, format="%.2f")
        duration = st.slider("活动时长 (周期)", 1, 7, 3)
        category = st.selectbox("商品类别", ['电子产品', '服装', '食品', '家居', '美妆'])
        channel = st.selectbox("投放渠道", ['线上商城', '社交媒体', '线下门店', '邮件营销', '直播带货'])
        price_tier = st.selectbox("价格档位", ['低价位', '中价位', '高价位'])
        customer_segment = st.selectbox("客户细分", ['新用户', '活跃用户', '忠诚用户', '流失风险用户'])
        
        st.subheader("📊 Bootstrap设置")
        n_bootstrap = st.slider("Bootstrap抽样次数", 100, 5000, 1000, 100)
        confidence_level = st.slider("置信水平", 0.80, 0.99, 0.95, 0.01)
        
        base_sales = st.number_input("基准销售额", 1000, 50000, 5000, 1000)
        avg_order_value = st.number_input("平均客单价", 50, 1000, 200, 50)
        review_score = st.slider("商品评分", 3.0, 5.0, 4.2, 0.1)
    
    with col2:
        predictor = PromotionPredictor(n_bootstrap=n_bootstrap)
        predictor._train_synthetic_model()
        
        with st.spinner("正在进行Bootstrap预测..."):
            pred_results = predictor.predict(
                discount=discount,
                duration=duration,
                category=category,
                channel=channel,
                price_tier=price_tier,
                customer_segment=customer_segment,
                base_sales=base_sales,
                avg_order_value=avg_order_value,
                review_score=review_score,
                confidence_level=confidence_level
            )
        
        st.markdown("### 📊 预测结果")
        
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.metric(
                "预计销售提升率",
                f"{pred_results['predicted_lift']:.1f}%",
                delta=f"中位数: {pred_results['median_lift']:.1f}%"
            )
        with col_b:
            st.metric(
                f"{int(confidence_level*100)}% 置信区间",
                f"[{pred_results['ci_lower']:.1f}%, {pred_results['ci_upper']:.1f}%]"
            )
        with col_c:
            st.metric(
                "预测标准差",
                f"{pred_results['std_lift']:.2f}%"
            )
        
        st.markdown("### 📈 预测分布")
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.hist(pred_results['predictions'], bins=50, alpha=0.7, color='#3498db', edgecolor='white')
        ax.axvline(pred_results['predicted_lift'], color='red', linestyle='--', linewidth=2, label=f'均值: {pred_results["predicted_lift"]:.1f}%')
        ax.axvline(pred_results['ci_lower'], color='orange', linestyle='--', linewidth=2, label=f'{int(confidence_level*100)}% CI下限')
        ax.axvline(pred_results['ci_upper'], color='orange', linestyle='--', linewidth=2, label=f'{int(confidence_level*100)}% CI上限')
        ax.set_xlabel('销售提升率 (%)')
        ax.set_ylabel('频数')
        ax.set_title(f'Bootstrap预测分布 (n={pred_results["n_bootstrap"]})')
        ax.legend()
        ax.grid(True, alpha=0.3)
        st.pyplot(fig)
        
        category_effect = predictor.category_effects[category]
        channel_effect = predictor.channel_effects[channel]
        price_effect = predictor.price_effects[price_tier]
        segment_effect = predictor.segment_effects[customer_segment]
        
        base_lift = 15
        discount_contribution = discount * 100 * 0.6
        duration_contribution = duration * 1.5
        
        with st.expander("📋 影响因素分解"):
            st.info(f"""
            **各因素对销售提升率的贡献:**
            
            - 基础提升率: {base_lift:.1f}%
            - 折扣力度 ({discount*100:.0f}%): +{discount_contribution:.1f}%
            - 活动时长 ({duration}周期): +{duration_contribution:.1f}%
            - 商品类别 ({category}): ×{category_effect:.2f}
            - 投放渠道 ({channel}): ×{channel_effect:.2f}
            - 价格档位 ({price_tier}): ×{price_effect:.2f}
            - 客户细分 ({customer_segment}): ×{segment_effect:.2f}
            """)
    
    st.subheader("💡 优化建议")
    recommendations = []
    
    if discount < 0.15:
        recommendations.append("📌 当前折扣力度较低，建议提高到15%-30%以获得更好效果")
    elif discount > 0.35:
        recommendations.append("📌 当前折扣力度较高，需关注利润空间")
    
    if channel in ['邮件营销', '线下门店']:
        recommendations.append("📌 建议增加直播带货或社交媒体渠道投入，这些渠道的促销效果更好")
    
    if category in ['食品', '家居']:
        recommendations.append("📌 该类别的促销敏感度较低，建议结合其他营销策略")
    
    if duration < 2:
        recommendations.append("📌 活动时长建议至少2个周期，让消费者充分感知")
    
    if customer_segment in ['新用户', '流失风险用户']:
        recommendations.append("📌 针对新用户或流失风险用户，建议搭配首单优惠或召回活动")
    
    if pred_results['ci_upper'] - pred_results['ci_lower'] > 15:
        recommendations.append("⚠️ 预测区间较宽，建议增加历史数据量以提高预测精度")
    
    if recommendations:
        for rec in recommendations:
            st.write(rec)
    else:
        st.success("✅ 当前促销参数设置合理")

def show_channel_attribution():
    st.subheader("🎯 多渠道归因分析")
    st.markdown("使用Shapley值法拆分各营销渠道对销售的贡献度，分析渠道间协同效应")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("⚙️ 分析设置")
        n_products = st.slider("商品数量", 50, 300, 150)
        n_periods = st.slider("时间周期数", 6, 24, 12)
        analyze_roi = st.checkbox("计算ROI", value=True)
        analyze_interactions = st.checkbox("分析渠道协同", value=True)
        
        channel_costs = {
            '线上商城': st.number_input("线上商城成本", 1000, 20000, 5000),
            '社交媒体': st.number_input("社交媒体成本", 1000, 20000, 3000),
            '线下门店': st.number_input("线下门店成本", 1000, 20000, 8000),
            '邮件营销': st.number_input("邮件营销成本", 500, 10000, 1000),
            '直播带货': st.number_input("直播带货成本", 1000, 20000, 6000)
        }
    
    with col2:
        attribution = ChannelAttribution()
        
        with st.spinner("正在生成多渠道数据并计算Shapley值..."):
            df_channel = attribution.generate_multi_channel_data(n_products, n_periods)
            shapley_results = attribution.calculate_shapley_values(df_channel)
            
            if analyze_roi:
                roi_results = attribution.calculate_roi(df_channel, channel_costs)
            
            if analyze_interactions:
                interactions = attribution.analyze_channel_interactions(df_channel)
        
        st.markdown("### 📊 渠道贡献度结果")
        col_a, col_b, col_c = st.columns(3)
        
        sorted_channels = sorted(
            shapley_results['shapley_percentage'].items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        with col_a:
            st.metric(
                "最高贡献渠道",
                sorted_channels[0][0],
                delta=f"{sorted_channels[0][1]:.1f}%"
            )
        
        with col_b:
            st.metric(
                "总渠道贡献额",
                f"¥{shapley_results['total_contribution']:,.0f}"
            )
        
        with col_c:
            if analyze_roi:
                roi_sorted = sorted(
                    roi_results.items(),
                    key=lambda x: x[1]['roi'],
                    reverse=True
                )
                st.metric(
                    "ROI最高渠道",
                    roi_sorted[0][0],
                    delta=f"{roi_sorted[0][1]['roi']:.0f}%"
                )
        
        st.pyplot(attribution.plot_shapley_values())
        
        if analyze_interactions:
            st.markdown("### 🔗 渠道协同效应")
            st.pyplot(attribution.plot_channel_interactions())
            
            top_interactions = sorted(
                interactions.items(),
                key=lambda x: x[1]['synergy_pct'],
                reverse=True
            )[:5]
            
            st.markdown("**Top 5 渠道组合协同效应:**")
            for combo, data in top_interactions:
                if data['synergy_pct'] > 0:
                    st.success(f"✅ {combo}: 协同效应 +{data['synergy_pct']:.1f}%")
                elif data['synergy_pct'] < 0:
                    st.warning(f"⚠️ {combo}: 替代效应 {data['synergy_pct']:.1f}%")

def show_promotion_fatigue():
    st.subheader("😴 促销疲劳检测")
    st.markdown("识别频繁促销对用户敏感度下降的影响，计算最优促销频率")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("⚙️ 分析设置")
        n_products = st.slider("商品数量", 50, 200, 100)
        n_periods = st.slider("时间周期数", 12, 36, 24)
        
        analyze_optimal_freq = st.checkbox("计算最优频率", value=True)
        show_product_detail = st.checkbox("显示商品详情", value=True)
        
        if show_product_detail:
            selected_product = st.selectbox(
                "选择商品分析",
                range(n_products)
            )
    
    with col2:
        detector = PromotionFatigueDetector()
        
        with st.spinner("正在生成数据并检测促销疲劳..."):
            df_fatigue = detector.generate_fatigue_data(n_products, n_periods)
            fatigue_scores = detector.calculate_fatigue_score(df_fatigue)
            sensitivity_decay = detector.analyze_sensitivity_decay(df_fatigue)
            
            if analyze_optimal_freq:
                optimal_freq = detector.calculate_optimal_frequency(df_fatigue)
        
        st.markdown("### 📊 疲劳检测概览")
        
        high_fatigue = sum(1 for v in fatigue_scores.values() if v['fatigue_level'] == '高疲劳')
        medium_high_fatigue = sum(1 for v in fatigue_scores.values() if v['fatigue_level'] in ['较高疲劳', '高疲劳'])
        
        col_a, col_b, col_c = st.columns(3)
        
        with col_a:
            st.metric(
                "高疲劳商品数",
                f"{high_fatigue}/{len(fatigue_scores)}",
                delta=f"{high_fatigue/len(fatigue_scores)*100:.1f}%"
            )
        
        with col_b:
            avg_score = np.mean([v['fatigue_score'] for v in fatigue_scores.values()])
            st.metric(
                "平均疲劳指数",
                f"{avg_score:.1f}/100",
                delta="危险" if avg_score > 50 else "健康"
            )
        
        with col_c:
            if optimal_freq:
                avg_gap = np.mean([v['optimal_gap'] for v in optimal_freq.values()])
                st.metric(
                    "推荐促销间隔",
                    f"每{avg_gap:.1f}周期"
                )
        
        st.pyplot(detector.plot_fatigue_distribution())
        
        recommendations = detector.generate_recommendations(df_fatigue)
        st.markdown("### 💡 建议")
        for rec in recommendations:
            st.write(rec)
        
        if show_product_detail:
            st.markdown(f"### 📦 商品 {selected_product} 敏感度分析")
            st.pyplot(detector.plot_sensitivity_decay(df_fatigue, product_id=selected_product))
        
        if analyze_optimal_freq and optimal_freq:
            st.markdown("### 📅 最优促销频率")
            st.pyplot(detector.plot_optimal_frequency(df_fatigue))

def show_budget_simulation():
    st.subheader("💰 预算模拟推演")
    st.markdown("输入促销力度和预算，模拟预期增量，辅助制定营销预算")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("⚙️ 模拟设置")
        
        simulation_mode = st.radio(
            "模拟模式",
            ["单预算优化", "预算区间分析", "假设分析"]
        )
        
        if simulation_mode == "单预算优化":
            total_budget = st.slider("总预算 (¥)", 10000, 500000, 100000, 10000)
            target_roi = st.slider("目标ROI (%)", 50, 200, 100)
            n_simulations = st.slider("模拟次数", 100, 2000, 500)
            
        elif simulation_mode == "预算区间分析":
            min_budget = st.slider("最小预算 (¥)", 10000, 100000, 30000, 10000)
            max_budget = st.slider("最大预算 (¥)", 50000, 500000, 200000, 10000)
            
        else:
            base_budget = st.number_input("基准预算", 10000, 200000, 50000)
            base_discount = st.slider("基准折扣", 0.1, 0.5, 0.2)
            base_duration = st.slider("基准时长", 1, 7, 3)
    
    with col2:
        simulator = BudgetSimulator()
        
        if simulation_mode == "单预算优化":
            with st.spinner("正在进行预算优化模拟..."):
                sim_results = simulator.run_budget_simulation(
                    total_budget=total_budget,
                    n_simulations=n_simulations,
                    include_fatigue=True
                )
                
                optimal = simulator.optimize_budget_allocation(
                    total_budget=total_budget,
                    target_roi=target_roi
                )
            
            st.markdown("### 📊 优化结果")
            
            col_a, col_b, col_c, col_d = st.columns(4)
            
            with col_a:
                st.metric(
                    "预期收入",
                    f"¥{optimal['expected_revenue']:,.0f}"
                )
            
            with col_b:
                st.metric(
                    "预期利润",
                    f"¥{optimal['expected_profit']:,.0f}",
                    delta="达标" if optimal['meets_target_roi'] else "未达标"
                )
            
            with col_c:
                st.metric(
                    "预期ROI",
                    f"{optimal['expected_roi']:.1f}%",
                    delta=f"目标: {target_roi}%"
                )
            
            with col_d:
                st.metric(
                    "模拟次数",
                    f"{n_simulations}次"
                )
            
            st.pyplot(simulator.plot_simulation_results())
            
            st.markdown("### 💸 详细预算分配")
            allocation_df = pd.DataFrame([
                {
                    '渠道': ch,
                    '预算': f"¥{data['budget']:,.0f}",
                    '占比': f"{data['budget_pct']:.1f}%",
                    '预期收入': f"¥{data['expected_revenue']:,.0f}",
                    '预期ROI': f"{data['expected_roi']:.1f}%"
                }
                for ch, data in sorted(
                    optimal['channel_allocation'].items(),
                    key=lambda x: x[1]['budget'],
                    reverse=True
                )
            ])
            st.dataframe(allocation_df, use_container_width=True)
            
            recs = simulator.generate_budget_recommendations(total_budget)
            st.markdown("### 💡 建议")
            for rec in recs:
                st.write(rec)
        
        elif simulation_mode == "预算区间分析":
            with st.spinner("正在分析预算区间..."):
                fig = simulator.plot_budget_vs_roi_curve(
                    budget_range=(min_budget, max_budget),
                    n_points=15
                )
            
            st.pyplot(fig)
            
            st.info("""
            📊 **解读:**
            - ROI曲线：随着预算增加，由于边际收益递减，ROI会逐渐下降
            - 利润曲线：存在最优预算点，超过该点后利润增长放缓甚至下降
            - 建议：选择ROI和利润都较高的预算区间
            """)
        
        else:
            with st.spinner("正在进行假设分析..."):
                variations = {
                    'total_budget': [base_budget * 0.7, base_budget, base_budget * 1.3],
                    'discount': [base_discount - 0.05, base_discount, base_discount + 0.05],
                    'duration': [max(1, base_duration - 1), base_duration, base_duration + 1]
                }
                
                what_if_results = simulator.what_if_analysis(
                    base_scenario={
                        'total_budget': base_budget,
                        'discount': base_discount,
                        'duration': base_duration
                    },
                    variations=variations
                )
            
            st.markdown("### 📊 假设分析结果")
            st.dataframe(
                what_if_results.sort_values('expected_profit', ascending=False).style.format({
                    'total_budget': '¥{:,.0f}',
                    'discount': '{:.1%}',
                    'duration': '{:.0f}',
                    'expected_revenue': '¥{:,.0f}',
                    'expected_profit': '¥{:,.0f}',
                    'expected_roi': '{:.1f}%'
                }),
                use_container_width=True
            )
            
            best_scenario = what_if_results.iloc[what_if_results['expected_profit'].argmax()]
            st.success(f"""
            🏆 最优场景:
            - 预算: ¥{best_scenario['total_budget']:,.0f}
            - 折扣: {best_scenario['discount']:.1%}
            - 时长: {best_scenario['duration']:.0f}周期
            - 预期利润: ¥{best_scenario['expected_profit']:,.0f}
            - 预期ROI: {best_scenario['expected_roi']:.1f}%
            """)

if __name__ == "__main__":
    main()
