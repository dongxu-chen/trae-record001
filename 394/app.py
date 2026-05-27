import streamlit as st
import numpy as np
import pandas as pd
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from src.models import (
    SleepStageClassifier,
    SleepQualityAnalyzer,
    FactorAnalyzer,
    SHAPAnalyzer,
    SleepPrescriptionGenerator,
    CircadianRhythmAnalyzer,
    AgeGroupComparator,
    train_and_save_model
)
from src.features import SleepDataGenerator
from src.visualization import (
    create_sleep_stage_hypnogram,
    create_sleep_stage_pie,
    create_sleep_score_gauge,
    create_score_components_bar,
    create_factor_impact_radar,
    create_attribution_bar,
    create_signal_comparison,
    create_feature_importance_plot,
    create_shap_summary_plot,
    create_circadian_schedule_plot,
    create_circadian_alignment_gauge,
    create_age_percentile_chart,
    create_age_group_comparison_radar,
    create_prescription_timeline,
    create_weekly_plan_timeline
)


st.set_page_config(
    page_title="睡眠质量分析系统",
    page_icon="🌙",
    layout="wide",
    initial_sidebar_state="expanded"
)


st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1E3A8A;
        text-align: center;
        padding: 1rem 0;
    }
    .sub-header {
        font-size: 1.5rem;
        font-weight: bold;
        color: #3B82F6;
        padding: 0.5rem 0;
    }
    .metric-card {
        background-color: #F0F9FF;
        padding: 1rem;
        border-radius: 10px;
        border-left: 5px solid #3B82F6;
    }
    .aasm-card {
        background-color: #F0FDFA;
        padding: 1rem;
        border-radius: 10px;
        border-left: 5px solid #0D9488;
    }
    .recommendation-card {
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
    }
    .high-priority {
        background-color: #FEF2F2;
        border-left: 5px solid #EF4444;
    }
    .medium-priority {
        background-color: #FFFBEB;
        border-left: 5px solid #F59E0B;
    }
    .low-priority {
        background-color: #F0FDF4;
        border-left: 5px solid #10B981;
    }
    .overfit-good {
        background-color: #F0FDF4;
        border-left: 5px solid #10B981;
    }
    .overfit-warn {
        background-color: #FFFBEB;
        border-left: 5px solid #F59E0B;
    }
    .overfit-bad {
        background-color: #FEF2F2;
        border-left: 5px solid #EF4444;
    }
    .prescription-card {
        background-color: #EFF6FF;
        padding: 1rem;
        border-radius: 10px;
        border-left: 5px solid #6366F1;
        margin: 0.5rem 0;
    }
    .circadian-card {
        background-color: #FDF4FF;
        padding: 1rem;
        border-radius: 10px;
        border-left: 5px solid #A855F7;
    }
    .percentile-card {
        background-color: #FFF7ED;
        padding: 1rem;
        border-radius: 10px;
        border-left: 5px solid #F97316;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource(show_spinner="正在加载模型...")
def load_or_train_model():
    model_path = 'models'
    if os.path.exists(os.path.join(model_path, 'sleep_stage_model.joblib')):
        classifier = SleepStageClassifier(use_augmentation=True, use_dropout=True)
        classifier.load_model(model_path)
        return classifier
    else:
        return train_and_save_model()


@st.cache_data(show_spinner="正在生成模拟数据...")
def generate_sample_data():
    generator = SleepDataGenerator(n_subjects=1, n_nights=1, n_epochs=720)
    return generator.generate_subject_data(0, 0)


def main():
    st.markdown('<p class="main-header">🌙 睡眠质量智能分析系统</p>', unsafe_allow_html=True)
    st.markdown("---")

    classifier = load_or_train_model()
    quality_analyzer = SleepQualityAnalyzer()
    factor_analyzer = FactorAnalyzer()
    shap_analyzer = SHAPAnalyzer(classifier)
    prescription_generator = SleepPrescriptionGenerator()
    circadian_analyzer = CircadianRhythmAnalyzer()
    age_comparator = AgeGroupComparator()

    with st.sidebar:
        st.markdown('<p class="sub-header">📊 数据源设置</p>', unsafe_allow_html=True)
        data_source = st.radio(
            "选择数据来源",
            ["使用模拟数据", "上传CSV数据", "手动输入参数"],
            index=0
        )

        st.markdown("---")
        st.markdown('<p class="sub-header">🧑 个人信息</p>', unsafe_allow_html=True)
        user_age = st.slider("您的年龄", 18, 80, 30)
        user_gender = st.selectbox("性别", ["男", "女"], index=0)
        usual_bedtime = st.slider("通常入睡时间", 20, 26, 23, format="%d:00")
        usual_wakeup = st.slider("通常起床时间", 4, 12, 7, format="%d:00")
        gender_map = {"男": "male", "女": "female"}

        st.markdown("---")
        st.markdown('<p class="sub-header">🏃 今日生活方式</p>', unsafe_allow_html=True)
        exercise_minutes = st.slider("今日运动时长 (分钟)", 0, 180, 45)
        exercise_intensity = st.selectbox("运动强度", ["低", "中等", "高"], index=1)
        caffeine_intake = st.slider("咖啡因摄入 (杯/份)", 0, 5, 1)
        alcohol_intake = st.slider("酒精摄入 (杯)", 0, 5, 0)
        stress_level = st.slider("今日压力水平 (1-10)", 1, 10, 5)
        bedtime_consistency = st.slider("作息规律性 (1-10)", 1, 10, 7)

        intensity_map = {"低": "low", "中等": "moderate", "高": "high"}
        lifestyle_factors = {
            'exercise_minutes': exercise_minutes,
            'exercise_intensity': intensity_map[exercise_intensity],
            'caffeine_intake': caffeine_intake,
            'alcohol_intake': alcohol_intake,
            'stress_level': stress_level,
            'bedtime_consistency': bedtime_consistency,
            'bedtime_hour': float(usual_bedtime % 24)
        }

        st.markdown("---")
        with st.expander("📅 前3天运动历史 (影响长期睡眠)", expanded=False):
            st.markdown("*运动对睡眠有滞后影响，前几天的运动也会影响今日睡眠质量*")
            ex_d1 = st.slider("1天前运动 (分钟)", 0, 180, 30, key="ex_d1")
            ex_d2 = st.slider("2天前运动 (分钟)", 0, 180, 50, key="ex_d2")
            ex_d3 = st.slider("3天前运动 (分钟)", 0, 180, 20, key="ex_d3")
            st_d1 = st.slider("1天前压力 (1-10)", 1, 10, 4, key="st_d1")
            st_d2 = st.slider("2天前压力 (1-10)", 1, 10, 6, key="st_d2")
            st_d3 = st.slider("3天前压力 (1-10)", 1, 10, 5, key="st_d3")

        history_factors = {
            'exercise_minutes_1d': ex_d1,
            'exercise_minutes_2d': ex_d2,
            'exercise_minutes_3d': ex_d3,
            'stress_level_1d': st_d1,
            'stress_level_2d': st_d2,
            'stress_level_3d': st_d3,
            'caffeine_intake_1d': 1,
            'caffeine_intake_2d': 2,
            'caffeine_intake_3d': 1,
            'alcohol_intake_1d': 0,
            'alcohol_intake_2d': 0,
            'alcohol_intake_3d': 0,
            'bedtime_hour_1d': 23.0,
            'bedtime_hour_2d': 23.5,
            'bedtime_hour_3d': 22.8,
            'sleep_duration_1d': 7.2,
            'sleep_duration_2d': 7.8,
            'sleep_duration_3d': 6.5,
        }

        st.markdown("---")
        analyze_button = st.button("🔍 开始分析", type="primary", use_container_width=True)

    sample_data = generate_sample_data()
    hr_data = sample_data['heart_rate']
    resp_data = sample_data['respiration']
    act_data = sample_data['activity']

    if data_source == "上传CSV数据":
        uploaded_file = st.sidebar.file_uploader("上传睡眠数据CSV", type=['csv'])
        if uploaded_file:
            try:
                df = pd.read_csv(uploaded_file)
                if 'heart_rate' in df.columns:
                    hr_data = df['heart_rate'].values
                if 'respiration' in df.columns:
                    resp_data = df['respiration'].values
                if 'activity' in df.columns:
                    act_data = df['activity'].values
                st.sidebar.success("数据上传成功！")
            except Exception as e:
                st.sidebar.error(f"数据读取错误: {e}")

    if analyze_button or 'analysis_done' not in st.session_state:
        with st.spinner('正在分析睡眠数据...'):
            prediction_result = classifier.predict_single_night(hr_data, resp_data, act_data)
            stages = prediction_result['stages']
            timestamps = prediction_result['timestamps']
            features_df = prediction_result['features']

            stage_analysis = quality_analyzer.analyze_sleep_stages(stages)
            sleep_score = quality_analyzer.calculate_sleep_score(stage_analysis)
            regularity_analysis = quality_analyzer.analyze_sleep_regularity(stages)
            recommendations = quality_analyzer.generate_recommendations(
                sleep_score, stage_analysis, regularity_analysis
            )

            factor_analysis = factor_analyzer.analyze_lifestyle_impact(
                lifestyle_factors, sleep_score['total_score'], history_factors
            )
            factor_recommendations = factor_analyzer.generate_factor_recommendations(factor_analysis)

            prescription = prescription_generator.generate_prescription(
                sleep_score, stage_analysis, regularity_analysis,
                lifestyle_factors, history_factors
            )

            circadian_result = circadian_analyzer.predict_circadian_type(
                stages, bedtime_hour=float(usual_bedtime % 24),
                wakeup_hour=float(usual_wakeup), history_factors=history_factors
            )

            percentile_result = age_comparator.calculate_percentile_rank(
                sleep_score['total_score'], age=user_age,
                gender=gender_map[user_gender]
            )
            comparison_result = age_comparator.compare_to_group(
                stage_analysis, age=user_age, gender=gender_map[user_gender]
            )
            chart_data = age_comparator.generate_comparison_chart_data(
                sleep_score['total_score'], age=user_age
            )

            st.session_state['analysis_done'] = True
            st.session_state['prediction_result'] = prediction_result
            st.session_state['stage_analysis'] = stage_analysis
            st.session_state['sleep_score'] = sleep_score
            st.session_state['regularity_analysis'] = regularity_analysis
            st.session_state['recommendations'] = recommendations
            st.session_state['factor_analysis'] = factor_analysis
            st.session_state['factor_recommendations'] = factor_recommendations
            st.session_state['features_df'] = features_df
            st.session_state['history_factors'] = history_factors
            st.session_state['prescription'] = prescription
            st.session_state['circadian_result'] = circadian_result
            st.session_state['percentile_result'] = percentile_result
            st.session_state['comparison_result'] = comparison_result
            st.session_state['chart_data'] = chart_data
            st.session_state['user_age'] = user_age
            st.session_state['user_gender'] = user_gender
    else:
        prediction_result = st.session_state['prediction_result']
        stage_analysis = st.session_state['stage_analysis']
        sleep_score = st.session_state['sleep_score']
        regularity_analysis = st.session_state['regularity_analysis']
        recommendations = st.session_state['recommendations']
        factor_analysis = st.session_state['factor_analysis']
        factor_recommendations = st.session_state['factor_recommendations']
        features_df = st.session_state['features_df']
        history_factors = st.session_state['history_factors']
        prescription = st.session_state['prescription']
        circadian_result = st.session_state['circadian_result']
        percentile_result = st.session_state['percentile_result']
        comparison_result = st.session_state['comparison_result']
        chart_data = st.session_state['chart_data']
        user_age = st.session_state['user_age']
        user_gender = st.session_state['user_gender']
        stages = prediction_result['stages']
        timestamps = prediction_result['timestamps']

    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "📊 睡眠概览",
        "💤 睡眠阶段分析",
        "🏆 睡眠质量评分",
        "🎯 影响因素分析",
        "💊 睡眠处方",
        "🕐 生物钟推算",
        "👥 同龄对比"
    ])

    with tab1:
        col1, col2, col3 = st.columns([1, 1, 1])

        with col1:
            fig = create_sleep_score_gauge(sleep_score['total_score'], sleep_score['grade'])
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric("总睡眠时长", f"{stage_analysis['total_sleep_duration']:.1f} 小时",
                     delta=f"AASM推荐 7-9h", delta_color="off")
            st.metric("睡眠效率", f"{stage_analysis['sleep_efficiency']:.1f} %",
                     delta="AASM推荐 ≥85%", delta_color="off")
            st.metric("入睡潜伏期", f"{stage_analysis['sleep_latency']:.0f} 分钟",
                     delta="AASM推荐 ≤20min", delta_color="off")
            st.markdown('</div>', unsafe_allow_html=True)

        with col3:
            stage_dist = stage_analysis['stage_distribution']
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            for stage in ['深睡', '浅睡', 'REM', '清醒']:
                col_a, col_b = st.columns(2)
                with col_a:
                    st.text(f"{stage}")
                with col_b:
                    st.text(f"{stage_dist[stage]['minutes']:.0f}分 ({stage_dist[stage]['percentage']:.1f}%)")
            st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("---")
        col_aasm1, col_aasm2 = st.columns([2, 1])
        with col_aasm1:
            st.markdown('<p class="sub-header">📈 原始生理信号</p>', unsafe_allow_html=True)
            fig = create_signal_comparison(hr_data, resp_data, act_data)
            st.plotly_chart(fig, use_container_width=True)

        with col_aasm2:
            st.markdown('<p class="sub-header">📋 AASM睡眠医学标准</p>', unsafe_allow_html=True)
            aasm = quality_analyzer.aasm_standards
            st.markdown('<div class="aasm-card">', unsafe_allow_html=True)
            st.markdown(f"""
            **睡眠效率:** ≥{aasm['sleep_efficiency_min']}% (最佳 >{aasm['sleep_efficiency_optimal']}%)\n
            **总睡眠时间:** {aasm['total_sleep_min']}-{aasm['total_sleep_max']} 小时\n
            **深睡(N3):** {aasm['n3_min_pct']}-{aasm['n3_max_pct']}%\n
            **REM睡眠:** {aasm['rem_min_pct']}-{aasm['rem_max_pct']}%\n
            **入睡潜伏期:** ≤{aasm['sleep_latency_max']} 分钟\n
            **WASO:** ≤{aasm['waso_max_pct']}%\n
            **觉醒指数:** ≤{aasm['arousal_index_max']} 次/小时
            """)
            st.markdown('</div>', unsafe_allow_html=True)
            st.caption("*参考: AASM (美国睡眠医学会) 临床睡眠医学标准*")

    with tab2:
        st.markdown('<p class="sub-header">🌙 睡眠阶段时序图</p>', unsafe_allow_html=True)
        fig = create_sleep_stage_hypnogram(stages, timestamps)
        st.plotly_chart(fig, use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            st.markdown('<p class="sub-header">🥧 睡眠阶段分布</p>', unsafe_allow_html=True)
            fig = create_sleep_stage_pie(stage_analysis['stage_distribution'])
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown('<p class="sub-header">📊 睡眠规律性分析</p>', unsafe_allow_html=True)
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric("阶段转换次数", f"{regularity_analysis['transitions_count']} 次")
            st.metric("觉醒指数", f"{regularity_analysis['transitions_per_hour']:.1f} 次/小时",
                     delta=f"AASM ≤{aasm['arousal_index_max']}", delta_color="off")
            st.metric("平均阶段持续时间", f"{regularity_analysis['average_stage_duration_min']:.1f} 分钟")
            st.metric("最长连续阶段", f"{regularity_analysis['max_stage_duration_min']:.1f} 分钟")
            st.metric("检测到的睡眠周期", f"{regularity_analysis['sleep_cycles_count']} 个")
            st.markdown('</div>', unsafe_allow_html=True)

    with tab3:
        col1, col2 = st.columns([1, 1])

        with col1:
            st.markdown('<p class="sub-header">🏆 睡眠质量评分构成 (AASM校准)</p>', unsafe_allow_html=True)
            fig = create_score_components_bar(sleep_score['components'])
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown('<p class="sub-header">💡 改善建议 (AASM标准)</p>', unsafe_allow_html=True)
            for rec in recommendations:
                priority_class = {
                    'high': 'high-priority',
                    'medium': 'medium-priority',
                    'low': 'low-priority'
                }.get(rec['priority'], 'low-priority')
                priority_label = {
                    'high': '🔴 高优先级',
                    'medium': '🟡 中优先级',
                    'low': '🟢 低优先级'
                }.get(rec['priority'], '低优先级')
                st.markdown(f'''
                <div class="recommendation-card {priority_class}">
                    <strong>{priority_label}</strong><br>
                    {rec['message']}
                </div>
                ''', unsafe_allow_html=True)

        st.markdown("---")
        st.markdown('<p class="sub-header">📊 评分构成详情</p>', unsafe_allow_html=True)
        comp_data = []
        labels_map = {
            'sleep_efficiency': '睡眠效率',
            'sleep_duration': '睡眠时长',
            'n3_sleep': '深睡(N3)',
            'rem_sleep': 'REM睡眠',
            'sleep_fragmentation': '睡眠连续性',
            'sleep_latency': '入睡潜伏期'
        }
        for key, comp in sleep_score['components'].items():
            comp_data.append({
                '指标': labels_map.get(key, key),
                '得分': f"{comp['score']:.1f}/100",
                '权重': f"{comp['weight']*100:.0f}%",
                'AASM标准': {
                    'sleep_efficiency': '≥85%',
                    'sleep_duration': '7-9h',
                    'n3_sleep': '13-23%',
                    'rem_sleep': '20-25%',
                    'sleep_fragmentation': '≤5次/小时',
                    'sleep_latency': '≤20分钟'
                }.get(key, '-')
            })
        st.table(pd.DataFrame(comp_data))

    with tab4:
        col1, col2 = st.columns([1, 1])

        with col1:
            st.markdown('<p class="sub-header">📊 因素影响评估</p>', unsafe_allow_html=True)
            fig = create_factor_impact_radar(factor_analysis['factor_impacts'])
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown('<p class="sub-header">🎯 归因分析</p>', unsafe_allow_html=True)
            fig = create_attribution_bar(factor_analysis['attribution'])
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        cum_ex = factor_analysis.get('cumulative_exercise')
        if cum_ex:
            st.markdown('<p class="sub-header">🏃 运动滞后影响分析</p>', unsafe_allow_html=True)
            col_ex1, col_ex2, col_ex3 = st.columns(3)
            with col_ex1:
                st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                st.metric("近4天总运动", f"{cum_ex['total_4day']:.0f} 分钟")
                st.metric("加权运动得分", f"{cum_ex['weighted_score']:.1f}")
                st.markdown('</div>', unsafe_allow_html=True)
            with col_ex2:
                st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                st.metric("运动一致性", f"{cum_ex['consistency']:.0%}")
                trend_map = {'upward': '↗️ 上升趋势', 'downward': '↘️ 下降趋势', 'stable': '➡️ 稳定'}
                st.metric("运动趋势", trend_map.get(cum_ex['trend'], cum_ex['trend']))
                st.markdown('</div>', unsafe_allow_html=True)
            with col_ex3:
                st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                daily = cum_ex['daily_values']
                st.text(f"今日: {daily[0]:.0f}分钟")
                st.text(f"1天前: {daily[1]:.0f}分钟")
                st.text(f"2天前: {daily[2]:.0f}分钟")
                st.text(f"3天前: {daily[3]:.0f}分钟")
                st.markdown('</div>', unsafe_allow_html=True)

            if cum_ex['consistency'] < 0.5:
                st.warning(f"⚠️ 运动一致性较低 ({cum_ex['consistency']:.0%})，建议保持每日规律运动以获得更好的睡眠效果。")
            elif cum_ex['consistency'] > 0.8:
                st.success(f"✅ 运动一致性良好 ({cum_ex['consistency']:.0%})，继续保持！")

        st.markdown("---")
        st.markdown('<p class="sub-header">📝 生活方式建议</p>', unsafe_allow_html=True)
        for rec in factor_recommendations:
            type_label = "🔧 改进方向" if rec['type'] == 'improvement' else "✅ 保持项目"
            expected_text = f"**预期改善:** {rec.get('expected_improvement', '')}" if rec['type'] == 'improvement' else f"**状态:** {rec.get('expected_impact', '')}"
            priority_class = {
                'high': 'high-priority',
                'medium': 'medium-priority',
                'low': 'low-priority'
            }.get(rec['priority'], 'low-priority')
            st.markdown(f'''
            <div class="recommendation-card {priority_class}">
                <strong>{type_label} - {rec['factor']}</strong><br>
                {rec['suggestion']}<br>
                {expected_text}
            </div>
            ''', unsafe_allow_html=True)

    with tab5:
        summary = prescription['summary']
        st.markdown('<p class="sub-header">💊 睡眠处方概览</p>', unsafe_allow_html=True)
        st.markdown(f'''
        <div class="prescription-card">
            <strong>睡眠处方总结</strong><br>
            当前评分: {summary['current_score']:.1f}分 ({summary['current_grade']})<br>
            {summary['summary_text']}
        </div>
        ''', unsafe_allow_html=True)

        col_rx1, col_rx2 = st.columns(2)

        with col_rx1:
            st.markdown('<p class="sub-header">⏰ 作息调整方案</p>', unsafe_allow_html=True)
            schedule = prescription['schedule_adjustment']
            st.markdown(f'''
            <div class="prescription-card">
                <strong>当前入睡:</strong> {int(schedule['current_bedtime'])}:{int((schedule['current_bedtime']%1)*60):02d}<br>
                <strong>{schedule['bedtime_text']}</strong><br>
                <strong>{schedule['wakeup_text']}</strong><br>
                <strong>作息评估:</strong> {schedule['schedule_grade']}<br>
                <strong>目标睡眠时长:</strong> {schedule['target_sleep_duration']:.1f}小时
            </div>
            ''', unsafe_allow_html=True)

            if schedule['adjustments']:
                for adj in schedule['adjustments']:
                    st.markdown(f'''
                    <div class="prescription-card">
                        <strong>{adj['action']} ({adj['change']})</strong><br>
                        目标: {adj['target']}<br>
                        原因: {adj['reason']}
                    </div>
                    ''', unsafe_allow_html=True)

            fig = create_prescription_timeline(prescription)
            st.plotly_chart(fig, use_container_width=True)

        with col_rx2:
            st.markdown('<p class="sub-header">🌙 睡前仪式</p>', unsafe_allow_html=True)
            routine = prescription['pre_sleep_routine']
            st.markdown(f'<div class="prescription-card"><strong>准备时长: {routine["prep_duration"]}分钟</strong></div>',
                       unsafe_allow_html=True)
            for step in routine['routine_steps']:
                st.markdown(f'''
                <div class="prescription-card">
                    <strong>{step['time']}</strong> - {step['activity']} ({step['duration']})
                </div>
                ''', unsafe_allow_html=True)
            st.markdown(f'''
            <div class="prescription-card">
                <strong>⚠️ 避免事项:</strong> {'、'.join(routine['avoid_activities'])}
            </div>
            ''', unsafe_allow_html=True)

        st.markdown("---")
        st.markdown('<p class="sub-header">🏃 运动处方</p>', unsafe_allow_html=True)
        for ex_rec in prescription['exercise_prescription']:
            st.markdown(f'''
            <div class="prescription-card">
                <strong>{ex_rec['type']}</strong><br>
                {ex_rec['recommendation']}
            </div>
            ''', unsafe_allow_html=True)

        st.markdown("---")
        st.markdown('<p class="sub-header">🏡 睡眠环境处方</p>', unsafe_allow_html=True)
        for env_rec in prescription['environment_prescription']:
            priority_class = {'high': 'high-priority', 'medium': 'medium-priority', 'low': 'low-priority'}.get(env_rec['priority'], 'low-priority')
            st.markdown(f'''
            <div class="recommendation-card {priority_class}">
                <strong>{env_rec['aspect']}</strong>: {env_rec['recommendation']}<br>
                <em>{env_rec['evidence']}</em>
            </div>
            ''', unsafe_allow_html=True)

        st.markdown("---")
        st.markdown('<p class="sub-header">📋 周改善计划</p>', unsafe_allow_html=True)
        weekly = prescription['weekly_plan']
        fig = create_weekly_plan_timeline(weekly)
        st.plotly_chart(fig, use_container_width=True)

        improvement = prescription['expected_improvement']
        st.markdown(f'''
        <div class="prescription-card">
            <strong>预期改善效果</strong><br>
            当前评分: {improvement['current_score']:.1f} → 潜在评分: {improvement['potential_score']:.1f}<br>
            预计提升: +{improvement['potential_gain']:.1f}分<br>
            {'、'.join([f"{f['factor']}(+{f['potential_gain']:.1f})" for f in improvement['factor_breakdown']])}<br>
            <em>{improvement['timeframe']}</em>
        </div>
        ''', unsafe_allow_html=True)

    with tab6:
        st.markdown('<p class="sub-header">🕐 生物钟类型推算</p>', unsafe_allow_html=True)
        cr = circadian_result

        col_cr1, col_cr2 = st.columns([1, 1])

        with col_cr1:
            fig = create_circadian_alignment_gauge(cr['alignment_score'], cr['chronotype_label'])
            st.plotly_chart(fig, use_container_width=True)

            st.markdown(f'''
            <div class="circadian-card">
                <strong>{cr['chronotype_label']}</strong><br>
                {cr['chronotype_description']}<br><br>
                <strong>最佳入睡时间:</strong> {int(cr['optimal_bedtime'])}:{int((cr['optimal_bedtime']%1)*60):02d}<br>
                <strong>最佳起床时间:</strong> {int(cr['optimal_wakeup'])}:{int((cr['optimal_wakeup']%1)*60):02d}<br>
                <strong>推荐睡眠时长:</strong> {cr['optimal_sleep_duration']:.1f}小时
            </div>
            ''', unsafe_allow_html=True)

        with col_cr2:
            st.markdown('<p class="sub-header">🧬 生物节律标志</p>', unsafe_allow_html=True)
            markers = cr['biological_markers']
            st.markdown(f'''
            <div class="circadian-card">
                <strong>褪黑素开始分泌:</strong> {int(markers['melatonin_start'])}:00<br>
                <strong>褪黑素分泌高峰:</strong> {int(markers['melatonin_peak'])}:00<br>
                <strong>皮质醇上升时间:</strong> {int(markers['cortisol_rise'])}:00<br>
                <strong>核心体温最低点:</strong> {int(markers['core_body_temp_min'])}:00<br>
                <strong>最佳运动时间:</strong> {int(markers['best_exercise_time'])}:00<br>
                <strong>最佳认知时间:</strong> {int(markers['best_cognitive_time'])}:00
            </div>
            ''', unsafe_allow_html=True)

            adj = cr['adjustment_recommendation']
            adj_class = 'low-priority' if adj['status'] == '已对齐' else 'high-priority'
            st.markdown(f'''
            <div class="recommendation-card {adj_class}">
                <strong>生物钟对齐: {adj['status']}</strong><br>
                {adj['recommendation']}
            </div>
            ''', unsafe_allow_html=True)
            if adj.get('steps'):
                for step in adj['steps']:
                    st.markdown(f'<div class="prescription-card">{step}</div>', unsafe_allow_html=True)

        st.markdown("---")
        st.markdown('<p class="sub-header">📅 最佳作息时间表</p>', unsafe_allow_html=True)
        schedule_data = cr['optimal_schedule']
        schedule_df = pd.DataFrame(schedule_data)
        st.table(schedule_df)

    with tab7:
        st.markdown('<p class="sub-header">👥 同年龄段对比分析</p>', unsafe_allow_html=True)

        pr = percentile_result

        col_pct1, col_pct2 = st.columns([1, 1])

        with col_pct1:
            rank_colors = {
                '极佳': '#2ed573', '优秀': '#7bed9f', '良好': '#ffd93d',
                '中等': '#ffa502', '中下': '#ff7f0e', '较低': '#ff4b5c'
            }
            rank_color = rank_colors.get(pr['rank'], '#666')
            st.markdown(f'''
            <div class="percentile-card">
                <h2 style="color: {rank_color}; text-align: center;">{pr['rank']}</h2>
                <p style="text-align: center; font-size: 1.2rem;">{pr['description']}</p>
                <p style="text-align: center;"><strong>百分位排名: 第{pr['percentile']:.1f}百分位</strong></p>
                <p style="text-align: center;">{pr['age_group_label']}</p>
            </div>
            ''', unsafe_allow_html=True)

        with col_pct2:
            fig = create_age_percentile_chart(chart_data, pr['age_group_label'])
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        st.markdown('<p class="sub-header">📊 逐项对比</p>', unsafe_allow_html=True)
        comp = comparison_result
        comparison_rows = []
        for c in comp['comparisons']:
            status_emoji = {'优秀': '🌟', '良好': '✅', '达标': '✅', '偏低': '⚠️',
                          '不足': '❌', '过多': '⚠️', '偏长': '⚠️', '过长': '❌',
                          '偏高': '⚠️', '过高': '❌', '良好': '✅'}
            comparison_rows.append({
                '指标': c['metric'],
                '您的数据': c['your_value'],
                '同龄均值': c['group_mean'],
                '差异': c['difference'],
                '状态': f"{status_emoji.get(c['status'], '')} {c['status']}",
                '参考标准': c['reference']
            })
        st.table(pd.DataFrame(comparison_rows))

        st.markdown(f'''
        <div class="percentile-card">
            <strong>对比总结</strong><br>
            {comp['summary']}
        </div>
        ''', unsafe_allow_html=True)

        st.markdown("---")
        st.markdown('<p class="sub-header">🎯 您 vs 同龄人雷达图</p>', unsafe_allow_html=True)
        fig = create_age_group_comparison_radar(stage_analysis, pr['group_norm'])
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        st.markdown(f'''
        <div class="aasm-card">
            <strong>📊 参考数据说明</strong><br>
            同龄人参考数据基于大规模流行病学研究，包含睡眠时长、睡眠效率、深睡比例、REM比例等指标。
            不同年龄段睡眠特征存在自然差异：随年龄增长，深睡比例自然减少，睡眠效率降低，总睡眠时长缩短。
            这些是正常的生理变化，不必过度焦虑。参考: AASM睡眠医学标准 + NHANES流行病学数据。
        </div>
        ''', unsafe_allow_html=True)

    st.markdown("---")
    st.info("""
    💡 **使用说明**: 
    - 系统使用XGBoost模型基于心率、呼吸率和活动量数据预测睡眠阶段
    - **数据增强+Dropout**: 增强训练数据，减少过拟合，提升泛化能力
    - **运动滞后影响**: 前3天的运动数据也会影响今日睡眠质量分析
    - **AASM标准**: 睡眠评分基于美国睡眠医学会(AASM)临床标准校准
    - **睡眠处方**: 根据分析结果生成个性化作息调整方案
    - **生物钟推算**: 基于作息习惯推算生物钟类型，预测最佳入睡/起床时间
    - **同龄对比**: 与同年龄段人群对比睡眠质量，计算百分位排名
    - 使用SHAP进行模型可解释性分析
    """)


if __name__ == "__main__":
    main()