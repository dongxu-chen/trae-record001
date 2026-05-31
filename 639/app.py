import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, date
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data_generator import (generate_flight_data, generate_airline_comparison_data, 
                           AIRLINES, AIRPORTS, AIRPORT_SECTORS, get_sector_info)
from feature_engineering import FeatureEngineer, get_compensation_range
from model import DelayPredictionModel
from attribution_analysis import (DelayAttributionAnalyzer, plot_delay_reason_distribution, 
                                 plot_feature_drivers, plot_airline_comparison,
                                 plot_airline_radar_chart, plot_policy_multipliers,
                                 plot_sector_flow_analysis)
from policy_learner import CompensationPolicyLearner, generate_mock_feedback_data
from delay_insurance import DelayInsuranceRecommender, get_risk_preference_description
from flight_rebooking import RebookingRecommender, get_priority_description
from delay_trend_analyzer import (DelayTrendAnalyzer, plot_hourly_delay_distribution,
                                   plot_weekday_delay_distribution, plot_delay_heatmap,
                                   plot_hot_routes)

st.set_page_config(
    page_title="航空延误赔付预测系统",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

@st.cache_resource(show_spinner=False)
def initialize_system():
    with st.spinner("正在初始化系统和训练模型..."):
        df = generate_flight_data(n_samples=8000)
        
        from feature_engineering import prepare_training_data
        X, y_delay, y_minutes, y_comp, y_range, range_enc, fe = prepare_training_data(df)
        
        model = DelayPredictionModel()
        model.train_all(X, y_delay, y_comp, y_range, X.columns.tolist())
        
        analyzer = DelayAttributionAnalyzer(model, X.columns.tolist())
        analyzer.init_shap_explainer(X.sample(100, random_state=42))
        
        airline_comp = generate_airline_comparison_data()
        
        policy_learner = CompensationPolicyLearner()
        insurance_recommender = DelayInsuranceRecommender()
        rebooking_recommender = RebookingRecommender()
        trend_analyzer = DelayTrendAnalyzer()
        trend_analyzer.analyze_hot_routes()
        trend_analyzer.analyze_time_distribution()
        
        return df, fe, model, analyzer, range_enc, airline_comp, policy_learner, insurance_recommender, rebooking_recommender, trend_analyzer


def get_range_label(index, range_enc):
    return range_enc.inverse_transform([index])[0]


def main():
    st.title("✈️ 航空延误赔付预测系统")
    st.markdown("---")
    
    try:
        df, fe, model, analyzer, range_enc, airline_comp, policy_learner, insurance_recommender, rebooking_recommender, trend_analyzer = initialize_system()
    except Exception as e:
        st.error(f"系统初始化失败: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        st.stop()
    
    with st.sidebar:
        st.header("📝 航班信息输入")
        
        airline = st.selectbox(
            "航空公司",
            options=list(AIRLINES.keys()),
            format_func=lambda x: f"{x} - {AIRLINES[x]['name']}"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            dep_airport = st.selectbox("起飞机场", AIRPORTS)
        with col2:
            arr_options = [a for a in AIRPORTS if a != dep_airport]
            arr_airport = st.selectbox("到达机场", arr_options)
        
        sector_info = get_sector_info(dep_airport, arr_airport)
        st.info(f"📍 起飞扇区: {sector_info['departure_sector']}\n📍 到达扇区: {sector_info['arrival_sector']}\n🔄 跨区域: {'是' if not sector_info['is_same_region'] else '否'}")
        
        flight_date = st.date_input("航班日期", value=date.today())
        
        col3, col4 = st.columns(2)
        with col3:
            dep_hour = st.slider("起飞小时", 6, 23, 12)
        with col4:
            dep_minute = st.slider("起飞分钟", 0, 59, 0)
        
        st.subheader("🌤️ 天气与流量")
        weather = st.selectbox(
            "天气状况",
            ['晴朗', '多云', '小雨', '中雨', '雷暴', '大雾', '大雪']
        )
        
        flow_control = st.select_slider(
            "流量控制等级",
            options=['无', '轻度', '中度', '重度']
        )
        
        st.subheader("📊 历史延误数据")
        hist_7d = st.slider("7天平均延误(分钟)", 0, 120, 15)
        hist_30d = st.slider("30天平均延误(分钟)", 0, 150, 20)
        
        st.markdown("---")
        st.subheader("⚙️ 政策设置")
        use_dynamic_policy = st.checkbox("启用动态赔付政策", value=True)
        
        st.markdown("---")
        st.subheader("🛡️ 保险推荐设置")
        risk_preference = st.selectbox(
            "风险偏好",
            options=['balanced', 'conservative', 'aggressive'],
            format_func=lambda x: {
                'conservative': '保守型 - 优先低保费',
                'balanced': '平衡型 - 综合考虑',
                'aggressive': '进取型 - 优先高保额'
            }[x]
        )
        insurance_budget = st.slider("保险预算(元)", 0, 100, 50)
        
        st.markdown("---")
        st.subheader("🔄 改签建议设置")
        rebooking_priority = st.selectbox(
            "改签优先级",
            options=['balanced', 'time', 'reliability', 'price'],
            format_func=lambda x: {
                'time': '时间优先',
                'reliability': '准点优先',
                'price': '价格优先',
                'balanced': '综合平衡'
            }[x]
        )
        max_search_hours = st.slider("搜索时间范围(小时)", 2, 24, 8)
        
        predict_button = st.button("🔮 开始预测", type="primary", use_container_width=True)
    
    if predict_button:
        input_data = pd.DataFrame([{
            'flight_id': f"{airline}0000",
            'airline': airline,
            'departure_airport': dep_airport,
            'arrival_airport': arr_airport,
            'date': pd.to_datetime(flight_date),
            'departure_hour': dep_hour,
            'departure_minute': dep_minute,
            'weather': weather,
            'flow_control': flow_control,
            'departure_sector': sector_info['departure_sector'],
            'arrival_sector': sector_info['arrival_sector'],
            'departure_region': sector_info['departure_region'],
            'arrival_region': sector_info['arrival_region'],
            'is_same_sector': sector_info['is_same_sector'],
            'is_same_region': sector_info['is_same_region'],
            'sector_congestion': sector_info['sector_congestion'],
            'cross_region_penalty': sector_info['cross_region_penalty'],
            'historical_delay_7d': hist_7d,
            'historical_delay_30d': hist_30d,
            'is_weekend': flight_date.weekday() >= 5,
            'is_peak_season': flight_date.month in [1, 2, 7, 8],
        }])
        
        X_pred = fe.prepare_features(input_data, fit=False)
        
        prediction = model.predict(X_pred)
        
        if use_dynamic_policy:
            from data_generator import calculate_compensation
            base_rate = AIRLINES[airline]['compensation_base']
            pred_delay_minutes = prediction['compensation_amount'] / base_rate * 60 if base_rate > 0 else 0
            delay_reason = prediction.get('main_reason', '天气原因')
            dynamic_comp = calculate_compensation(
                max(pred_delay_minutes, prediction['compensation_amount'] / 5),
                base_rate, delay_reason, policy_learner
            )
            prediction['compensation_amount'] = max(prediction['compensation_amount'], dynamic_comp * 0.8)
        
        attribution_report = analyzer.generate_attribution_report(
            X_pred, prediction, weather, flow_control, airline,
            sector_info['departure_sector'], sector_info['arrival_sector'],
            sector_info['is_same_sector']
        )
        
        st.header("📊 预测结果")
        
        col_a, col_b, col_c, col_d = st.columns(4)
        
        with col_a:
            delay_prob = prediction['delay_probability']
            prob_color = "🟢" if delay_prob < 0.3 else "🟡" if delay_prob < 0.6 else "🔴"
            st.metric(
                label=f"{prob_color} 延误概率",
                value=f"{delay_prob * 100:.1f}%"
            )
            
            if delay_prob < 0.3:
                st.success("低风险 - 准点率较高")
            elif delay_prob < 0.6:
                st.warning("中等风险 - 存在延误可能")
            else:
                st.error("高风险 - 延误概率较大")
        
        with col_b:
            comp_amount = prediction['compensation_amount']
            st.metric(
                label="💰 预计赔付金额",
                value=f"¥{comp_amount:.0f}"
            )
            
            range_label = get_range_label(prediction['compensation_range_pred'], range_enc)
            st.info(f"赔付区间: {range_label}")
        
        with col_c:
            range_probs = prediction['compensation_range_probabilities']
            range_labels = range_enc.classes_
            
            max_prob_idx = np.argmax(range_probs)
            st.metric(
                label="📈 最可能赔付区间",
                value=range_labels[max_prob_idx],
                delta=f"{range_probs[max_prob_idx] * 100:.1f}%"
            )
        
        with col_d:
            congestion_level = "高" if sector_info['sector_congestion'] > 0.8 else "中" if sector_info['sector_congestion'] > 0.65 else "低"
            st.metric(
                label="📍 扇区拥堵指数",
                value=f"{sector_info['sector_congestion'] * 100:.0f}%",
                delta=f"{congestion_level}拥堵"
            )
            st.info(f"跨区域影响: {sector_info['cross_region_penalty'] * 100:.0f}% 额外风险")
        
        st.markdown("---")
        
        tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
            "📊 赔付区间分布", "🎯 延误原因分析", "🔍 影响因素分析", 
            "🏢 航司多维对比", "⚙️ 赔付政策管理",
            "🛡️ 延误保险推荐", "🔄 改签建议", "📈 延误趋势分析"
        ])
        
        with tab1:
            st.subheader("赔付区间概率分布")
            
            range_df = pd.DataFrame({
                '赔付区间': range_labels,
                '概率': [p * 100 for p in range_probs]
            })
            range_df = range_df.sort_values('概率', ascending=False)
            
            st.bar_chart(
                range_df.set_index('赔付区间'),
                color='#FF6B6B',
                use_container_width=True
            )
            
            col_chart, col_table = st.columns([2, 1])
            with col_table:
                st.dataframe(
                    range_df.style.format({'概率': '{:.1f}%'}),
                    hide_index=True,
                    use_container_width=True
                )
            
            with col_chart:
                if use_dynamic_policy:
                    st.subheader("📋 当前生效赔付政策")
                    policy_report = policy_learner.get_policy_report()
                    col_v1, col_v2 = st.columns(2)
                    with col_v1:
                        st.info(f"📅 政策版本: {policy_report['version']}")
                    with col_v2:
                        st.info(f"🕐 生效日期: {policy_report['effective_date']}")
                    
                    fig_policy = plot_policy_multipliers(policy_learner)
                    st.pyplot(fig_policy)
        
        with tab2:
            st.subheader("延误原因概率分析")
            
            reason_probs = attribution_report['delay_reasons']
            
            col_chart, col_table = st.columns([2, 1])
            
            with col_chart:
                fig1 = plot_delay_reason_distribution(reason_probs)
                st.pyplot(fig1)
            
            with col_table:
                st.markdown("#### 原因排名")
                for i, (reason, prob) in enumerate(reason_probs[:5], 1):
                    st.write(f"{i}. **{reason}**: {prob * 100:.1f}%")
            
            st.markdown("---")
            st.subheader("🌐 扇区流量分析")
            fig_sector = plot_sector_flow_analysis(AIRPORT_SECTORS)
            st.pyplot(fig_sector)
        
        with tab3:
            st.subheader("主要影响因素分析")
            
            drivers = attribution_report['top_drivers']
            
            col_chart2, col_details = st.columns([2, 1])
            
            with col_chart2:
                fig2 = plot_feature_drivers(drivers)
                st.pyplot(fig2)
            
            with col_details:
                st.markdown("#### 影响因素详情")
                for driver in drivers:
                    color = "🔴" if driver['impact'] == '增加' else "🟢"
                    st.write(f"{color} **{driver['feature']}**")
                    st.write(f"   影响: {driver['impact']}延误风险")
                    st.write(f"   程度: {driver['magnitude']:.4f}")
            
            if attribution_report.get('sector_info'):
                st.markdown("---")
                st.subheader("📍 扇区信息详情")
                sec_info = attribution_report['sector_info']
                col_s1, col_s2, col_s3 = st.columns(3)
                with col_s1:
                    st.info(f"起飞扇区: {sec_info['departure_sector']}")
                with col_s2:
                    st.info(f"到达扇区: {sec_info['arrival_sector']}")
                with col_s3:
                    risk_color = "🟢" if sec_info['cross_region_risk'] == '低' else "🔴"
                    st.info(f"{risk_color} 跨区域风险: {sec_info['cross_region_risk']}")
        
        with tab4:
            st.subheader("🏢 航空公司多维度对比分析")
            
            airline_comparison = analyzer.get_airline_comparison(airline_comp, current_airline=airline)
            
            col_radar, col_bars = st.columns([3, 2])
            
            with col_radar:
                fig_radar = plot_airline_radar_chart(airline_comparison, current_airline_code=airline)
                st.pyplot(fig_radar)
            
            with col_bars:
                fig3 = plot_airline_comparison(airline_comparison, figsize=(8, 6))
                st.pyplot(fig3)
            
            st.markdown("---")
            st.subheader("📋 详细对比数据")
            
            display_cols = ['rank', 'airline_code', 'airline_name', 'on_time_rate', 
                           'service_quality', 'compensation_adequacy', 'flight_network',
                           'baggage_handling', 'customer_satisfaction', 'delay_risk_score']
            display_df = airline_comparison[display_cols].copy()
            display_df.columns = [
                '排名', '代码', '航空公司', '准点率(%)', '服务质量', 
                '赔付合理性', '航线网络', '行李处理', '客户满意度', '风险指数'
            ]
            
            def highlight_current(row):
                if row['代码'] == airline:
                    return ['background-color: rgba(255, 215, 0, 0.3)'] * len(row)
                return [''] * len(row)
            
            st.dataframe(
                display_df.style
                .format({
                    '准点率(%)': '{:.1f}',
                    '服务质量': '{:.1f}',
                    '赔付合理性': '{:.1f}',
                    '航线网络': '{:.1f}',
                    '行李处理': '{:.1f}',
                    '客户满意度': '{:.1f}',
                    '风险指数': '{:.1f}'
                })
                .apply(highlight_current, axis=1),
                hide_index=True,
                use_container_width=True
            )
            
            current_airline_data = airline_comparison[airline_comparison['airline_code'] == airline].iloc[0]
            rank = current_airline_data['rank']
            total = len(airline_comparison)
            
            st.info(f"📊 {AIRLINES[airline]['name']} 在 {total} 家航空公司中排名第 {rank}，风险指数 {current_airline_data['delay_risk_score']:.1f}")
        
        with tab5:
            st.subheader("⚙️ 赔付政策动态管理")
            
            policy_report = policy_learner.get_policy_report()
            
            col_p1, col_p2, col_p3 = st.columns(3)
            with col_p1:
                st.metric("当前政策版本", policy_report['version'])
            with col_p2:
                st.metric("生效日期", policy_report['effective_date'])
            with col_p3:
                st.metric("历史调整次数", policy_report['change_history_count'])
            
            st.markdown("---")
            
            col_learn, col_simulate, col_reset = st.columns(3)
            
            with col_learn:
                st.subheader("📚 政策学习")
                if st.button("基于模拟反馈更新政策", use_container_width=True):
                    with st.spinner("正在分析反馈并更新政策..."):
                        feedback = generate_mock_feedback_data(500)
                        result = policy_learner.learn_from_feedback(feedback)
                        st.success(result)
                        st.rerun()
            
            with col_simulate:
                st.subheader("🔬 政策影响模拟")
                if st.button("模拟新政策影响", use_container_width=True):
                    with st.spinner("正在模拟政策影响..."):
                        feedback = generate_mock_feedback_data(300)
                        impact = policy_learner.simulate_policy_impact(feedback)
                        
                        col_s1, col_s2 = st.columns(2)
                        with col_s1:
                            st.metric("原赔付总额", f"¥{impact['old_total']:,.0f}")
                        with col_s2:
                            st.metric("新赔付总额", f"¥{impact['new_total']:,.0f}")
                        
                        change_pct = impact['change_percent']
                        if change_pct > 0:
                            st.error(f"赔付预计增加: +{change_pct:.1f}%")
                        elif change_pct < 0:
                            st.success(f"赔付预计减少: {change_pct:.1f}%")
                        else:
                            st.info("赔付预计无变化")
            
            with col_reset:
                st.subheader("🔄 重置政策")
                if st.button("重置为默认政策", use_container_width=True):
                    result = policy_learner.reset_to_default()
                    st.success(result)
                    st.rerun()
            
            st.markdown("---")
            st.subheader("📋 当前政策详情")
            
            multipliers_df = pd.DataFrame([
                {'延误原因': reason, '赔付系数': value}
                for reason, value in policy_report['reason_multipliers'].items()
            ])
            
            st.dataframe(
                multipliers_df.style.format({'赔付系数': '{:.2f}'}),
                hide_index=True,
                use_container_width=True
            )
            
            st.markdown("---")
            st.subheader("⏰ 延误时间赔付标准")
            thresholds_df = pd.DataFrame(policy_report['delay_thresholds'])
            st.dataframe(
                thresholds_df.rename(columns={
                    'threshold': '延误时长(分钟)',
                    'ratio': '赔付倍数',
                    'label': '说明'
                }).style.format({'延误时长(分钟)': '{:.0f}', '赔付倍数': '{:.1f}'}),
                hide_index=True,
                use_container_width=True
            )
            
            if policy_report['recent_changes']:
                st.markdown("---")
                st.subheader("📜 最近政策变更记录")
                for change in reversed(policy_report['recent_changes']):
                    with st.expander(f"版本 {change['old_version']} → {change['new_version']} | {change['timestamp'][:19]}"):
                        for adj in change['adjustments']:
                            st.write(f"- **{adj['target']}**: {adj['old_value']} → **{adj['new_value']}**")
                            st.caption(adj['rationale'])
        
        with tab6:
            st.subheader("🛡️ 延误保险推荐")
            
            st.info(get_risk_preference_description(risk_preference))
            
            main_reason = attribution_report['delay_reasons'][0][0] if attribution_report['delay_reasons'] else '天气原因'
            
            insurance_recs = insurance_recommender.recommend_insurance(
                delay_probability=delay_prob,
                predicted_delay_minutes=comp_amount / 5 if comp_amount > 0 else 0,
                predicted_delay_reason=main_reason,
                risk_preference=risk_preference,
                budget=insurance_budget
            )
            
            best_rec = insurance_recommender.get_best_recommendation(insurance_recs)
            
            if best_rec:
                st.markdown("### 🌟 最佳推荐")
                rec_level_color = {
                    '强烈推荐': 'success',
                    '推荐': 'info',
                    '可考虑': 'warning',
                    '不推荐': 'error'
                }.get(best_rec['recommendation_level'], 'info')
                
                col_best1, col_best2, col_best3, col_best4 = st.columns(4)
                with col_best1:
                    st.metric("保险产品", best_rec['product_name'])
                with col_best2:
                    st.metric("保费", f"¥{best_rec['premium']}")
                with col_best3:
                    st.metric("保额", f"¥{best_rec['coverage_amount']}")
                with col_best4:
                    st.metric("预期赔付", f"¥{best_rec['expected_payout']:.0f}")
                
                if best_rec['recommendation_level'] == '强烈推荐':
                    st.success(f"✅ {best_rec['recommendation_level']}")
                elif best_rec['recommendation_level'] == '推荐':
                    st.info(f"ℹ️ {best_rec['recommendation_level']}")
                elif best_rec['recommendation_level'] == '可考虑':
                    st.warning(f"⚠️ {best_rec['recommendation_level']}")
                else:
                    st.error(f"❌ {best_rec['recommendation_level']}")
                
                col_v, col_n = st.columns(2)
                with col_v:
                    st.metric("净收益", f"¥{best_rec['net_value']:.0f}", 
                             delta="+" if best_rec['net_value'] > 0 else "")
                with col_n:
                    st.metric("投资回报率", f"{best_rec['roi']:.1f}%")
                
                st.markdown("#### 📋 产品详情")
                st.write(f"**保险公司**: {best_rec['provider']}")
                st.write(f"**保障范围**: {', '.join(best_rec['covered_reasons'][:4])}")
                st.write(f"**产品说明**: {best_rec['description']}")
                st.write(f"**用户评分**: {'⭐' * int(best_rec['rating'])} ({best_rec['rating']}/5)")
            
            st.markdown("---")
            st.subheader("📊 所有保险产品对比")
            
            insurance_table = insurance_recommender.generate_insurance_comparison_table(insurance_recs)
            
            def highlight_recommendation(row):
                styles = []
                for col in row.index:
                    level = row['推荐等级']
                    if level == '强烈推荐':
                        styles.append('background-color: rgba(46, 204, 113, 0.2)')
                    elif level == '推荐':
                        styles.append('background-color: rgba(52, 152, 219, 0.2)')
                    elif level == '可考虑':
                        styles.append('background-color: rgba(241, 196, 15, 0.2)')
                    else:
                        styles.append('background-color: rgba(231, 76, 60, 0.1)')
                return styles
            
            st.dataframe(
                insurance_table.style
                .format({
                    '保费(元)': '{:.0f}',
                    '保额(元)': '{:.0f}',
                    '最低延误(分钟)': '{:.0f}',
                    '评分': '{:.1f}',
                    '预期赔付(元)': '{:.0f}',
                    '净收益(元)': '{:.0f}',
                    '投资回报率(%)': '{:.1f}'
                })
                .apply(highlight_recommendation, axis=1),
                hide_index=True,
                use_container_width=True
            )
        
        with tab7:
            st.subheader("🔄 改签建议")
            
            st.info(get_priority_description(rebooking_priority))
            
            original_departure = datetime.combine(
                flight_date, 
                datetime.min.time().replace(hour=dep_hour, minute=dep_minute)
            )
            
            pred_delay = prediction['compensation_amount'] / 5 if prediction['compensation_amount'] > 0 else 30
            
            alternatives = rebooking_recommender.generate_alternative_flights(
                original_dep_airport=dep_airport,
                original_arr_airport=arr_airport,
                original_date=flight_date,
                original_departure_hour=dep_hour,
                original_departure_minute=dep_minute,
                max_search_hours=max_search_hours,
                num_flights=10
            )
            
            scored_flights = rebooking_recommender.recommend_rebooking(
                alternatives, original_departure, 
                original_delay_minutes=pred_delay,
                priority=rebooking_priority,
                top_n=8
            )
            
            best_rebooking = rebooking_recommender.get_best_recommendation(scored_flights)
            
            if best_rebooking:
                st.markdown("### 🌟 最佳改签推荐")
                rec_level_color = {
                    '强烈推荐': 'success',
                    '推荐': 'info',
                    '可考虑': 'warning',
                    '不推荐': 'error'
                }.get(best_rebooking['recommendation_level'], 'info')
                
                col_r1, col_r2, col_r3, col_r4 = st.columns(4)
                with col_r1:
                    st.metric("航班号", best_rebooking['flight_id'])
                with col_r2:
                    st.metric("航空公司", best_rebooking['airline_name'])
                with col_r3:
                    st.metric("起飞时间", best_rebooking['departure_time'])
                with col_r4:
                    st.metric("价格", f"¥{best_rebooking['price']}")
                
                if best_rebooking['recommendation_level'] == '强烈推荐':
                    st.success(f"✅ {best_rebooking['recommendation_level']}")
                elif best_rebooking['recommendation_level'] == '推荐':
                    st.info(f"ℹ️ {best_rebooking['recommendation_level']}")
                elif best_rebooking['recommendation_level'] == '可考虑':
                    st.warning(f"⚠️ {best_rebooking['recommendation_level']}")
                else:
                    st.error(f"❌ {best_rebooking['recommendation_level']}")
                
                col_s1, col_s2, col_s3, col_s4 = st.columns(4)
                with col_s1:
                    st.metric("时间评分", f"{best_rebooking['time_score']}/100")
                with col_s2:
                    st.metric("准点评分", f"{best_rebooking['reliability_score']}/100")
                with col_s3:
                    st.metric("价格评分", f"{best_rebooking['price_score']}/100")
                with col_s4:
                    st.metric("综合评分", f"{best_rebooking['total_score']}/100")
                
                col_d1, col_d2, col_d3 = st.columns(3)
                with col_d1:
                    st.metric("延误概率", f"{best_rebooking['estimated_delay_prob']}%")
                with col_d2:
                    st.metric("预计延误", f"{best_rebooking['estimated_delay_minutes']:.0f}分钟")
                with col_d3:
                    st.metric("舱位", best_rebooking['cabin_class'])
            
            st.markdown("---")
            st.subheader("📋 所有备选航班")
            
            display_flights = pd.DataFrame(scored_flights)
            display_flights = display_flights[[
                'flight_id', 'airline_name', 'departure_time', 'arrival_time',
                'duration', 'estimated_delay_prob', 'price', 'cabin_class',
                'seats_available', 'total_score', 'recommendation_level'
            ]]
            display_flights.columns = [
                '航班号', '航空公司', '起飞时间', '到达时间', '飞行时长',
                '延误概率(%)', '价格(元)', '舱位', '剩余座位', '综合评分', '推荐等级'
            ]
            
            def highlight_flight(row):
                styles = []
                for col in row.index:
                    level = row['推荐等级']
                    if level == '强烈推荐':
                        styles.append('background-color: rgba(46, 204, 113, 0.2)')
                    elif level == '推荐':
                        styles.append('background-color: rgba(52, 152, 219, 0.2)')
                    elif level == '可考虑':
                        styles.append('background-color: rgba(241, 196, 15, 0.2)')
                    else:
                        styles.append('background-color: rgba(231, 76, 60, 0.1)')
                return styles
            
            st.dataframe(
                display_flights.style
                .format({
                    '延误概率(%)': '{:.1f}',
                    '价格(元)': '{:.0f}',
                    '综合评分': '{:.1f}'
                })
                .apply(highlight_flight, axis=1),
                hide_index=True,
                use_container_width=True
            )
        
        with tab8:
            st.subheader("📈 延误趋势分析")
            
            alert_summary = trend_analyzer.get_delay_alert_summary()
            
            st.markdown("### ⚠️ 延误预警摘要")
            col_a1, col_a2, col_a3 = st.columns(3)
            with col_a1:
                st.warning(f"🕐 高峰时段: {alert_summary['peak_hours']}")
            with col_a2:
                st.warning(f"📅 高峰月份: {', '.join(alert_summary['peak_months'])}")
            with col_a3:
                st.warning(f"🛫 周末高风险: 周六、周日")
            
            st.markdown("### 🔥 Top 高延误风险航线")
            col_routes, col_detail = st.columns([2, 1])
            
            with col_routes:
                fig_hot = plot_hot_routes(trend_analyzer.hot_routes)
                st.pyplot(fig_hot)
            
            with col_detail:
                st.markdown("#### 航线详情")
                for route in alert_summary['top_high_risk_routes']:
                    st.write(f"**{route['route']}**")
                    st.write(f"  延误率: {route['delay_rate']}")
                    st.write(f"  平均延误: {route['avg_delay']}")
                    st.write("---")
            
            st.markdown("---")
            route_forecast = trend_analyzer.get_route_delay_forecast(dep_airport, arr_airport)
            
            if 'error' not in route_forecast:
                st.markdown(f"### 📊 {dep_airport}-{arr_airport} 航线延误预测")
                
                col_f1, col_f2, col_f3 = st.columns(3)
                with col_f1:
                    st.metric("历史航班数", route_forecast['total_flights'])
                with col_f2:
                    st.metric("整体延误率", f"{route_forecast['overall_delay_rate']}%")
                with col_f3:
                    st.metric("平均延误", f"{route_forecast['avg_delay_minutes']}分钟")
                
                col_best, col_worst = st.columns(2)
                with col_best:
                    st.success(f"✅ 最佳时段: {', '.join([f'{h}:00' for h in sorted(route_forecast['best_hours'][:3])])}")
                with col_worst:
                    st.error(f"⚠️ 高风险时段: {', '.join([f'{h}:00' for h in sorted(route_forecast['worst_hours'][:3])])}")
            
            st.markdown("---")
            st.markdown("### ⏰ 时间分布分析")
            
            time_dist = trend_analyzer.time_distribution
            
            col_hour, col_week = st.columns(2)
            with col_hour:
                fig_hourly = plot_hourly_delay_distribution(time_dist['hourly'])
                st.pyplot(fig_hourly)
            
            with col_week:
                fig_weekday = plot_weekday_delay_distribution(time_dist['weekday'])
                st.pyplot(fig_weekday)
            
            st.markdown("---")
            st.markdown("### 🌡️ 延误热力图（小时 × 星期）")
            
            heatmap_data = trend_analyzer.generate_delay_heatmap_data(dep_airport)
            fig_heatmap = plot_delay_heatmap(heatmap_data)
            st.pyplot(fig_heatmap)
        
        st.markdown("---")
        
    else:
        st.info("👈 请在左侧输入航班信息，然后点击「开始预测」按钮")
        
        col_welcome1, col_welcome2 = st.columns([2, 1])
        
        with col_welcome1:
            st.subheader("📋 系统功能说明")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("### 🔮 延误预测")
                st.write("基于XGBoost模型，综合天气、流量、历史数据等多维度特征，精准预测航班延误概率。")
                
            with col2:
                st.markdown("### 💰 赔付估算")
                st.write("根据延误时长、延误原因和动态调整的赔付政策，智能估算可能的赔付金额区间。")
                
            with col3:
                st.markdown("### 📊 归因分析")
                st.write("使用SHAP值进行可解释性分析，结合扇区区域特征，明确各因素对延误的影响程度。")
            
            st.markdown("---")
            col4, col5, col6 = st.columns(3)
            
            with col4:
                st.markdown("### 🌐 扇区特征")
                st.write("细化流量控制影响，引入区域扇区、拥堵指数、跨区域惩罚等特征，提升预测精准度。")
                
            with col5:
                st.markdown("### ⚙️ 政策学习")
                st.write("支持赔付政策动态学习，可根据实际反馈自动调整赔付系数，适应新规变化。")
                
            with col6:
                st.markdown("### 📈 多维对比")
                st.write("通过雷达图直观展示各航空公司在准点率、服务质量、赔付合理性等维度的优劣。")
            
            st.markdown("---")
            col7, col8, col9 = st.columns(3)
            
            with col7:
                st.markdown("### 🛡️ 保险推荐")
                st.write("根据延误概率智能推荐延误保险产品，计算预期赔付和投资回报率，辅助购买决策。")
                
            with col8:
                st.markdown("### 🔄 改签建议")
                st.write("延误高风险时智能推荐后续替代航班，综合时间、准点率、价格进行多维度评分。")
                
            with col9:
                st.markdown("### 📉 趋势分析")
                st.write("热点延误航线分析，小时/星期/月度时间分布热力图，辅助出行决策。")
        
        with col_welcome2:
            st.subheader("📈 数据概览")
            col_a, col_b = st.columns(2)
            
            with col_a:
                st.metric("训练样本数", f"{len(df):,}")
                st.metric("特征维度", "36")
            with col_b:
                st.metric("整体延误率", f"{df['is_delayed'].mean() * 100:.1f}%")
                st.metric("航司数量", "5")
            
            st.metric("平均延误时长", f"{df['delay_minutes'].mean():.0f}分钟")
            st.metric("平均赔付金额", f"¥{df['compensation'].mean():.0f}")
            
            st.markdown("---")
            st.subheader("⚠️ 延误预警")
            alert_summary = trend_analyzer.get_delay_alert_summary()
            st.warning(f"🕐 高峰时段: {alert_summary['peak_hours']}")
            st.warning(f"📅 高峰月份: {', '.join(alert_summary['peak_months'])}")
        
        st.markdown("---")
        st.subheader("🏆 航空公司准点率排名")
        
        rank_df = airline_comp.sort_values('on_time_rate', ascending=False)
        rank_df = rank_df[['airline_code', 'airline_name', 'on_time_rate', 
                          'service_quality', 'customer_satisfaction', 'avg_compensation']]
        rank_df.columns = ['代码', '航空公司', '准点率(%)', '服务质量', '客户满意度', '平均赔付(元)']
        
        st.dataframe(
            rank_df.style.format({
                '准点率(%)': '{:.1f}',
                '服务质量': '{:.1f}',
                '客户满意度': '{:.1f}',
                '平均赔付(元)': '{:.0f}'
            }),
            hide_index=True,
            use_container_width=True
        )
        
        st.markdown("---")
        col_radar_demo, _ = st.columns([2, 1])
        with col_radar_demo:
            st.subheader("📊 航司多维度对比雷达图 (预览)")
            fig_radar_demo = plot_airline_radar_chart(airline_comp)
            st.pyplot(fig_radar_demo)


if __name__ == '__main__':
    main()
