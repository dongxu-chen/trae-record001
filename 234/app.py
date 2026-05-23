import streamlit as st
import pandas as pd
import numpy as np
from user_behavior_analysis import UserBehaviorAnalyzer

st.set_page_config(
    page_title="用户消费行为轨迹分析 (增强版)",
    page_icon="📊",
    layout="wide"
)

st.title("📊 用户消费行为轨迹分析系统 (增强版)")
st.markdown("**二阶马尔可夫链 + 拉普拉斯平滑 + 行为模拟 + 流失预警 + 时段对比**")

@st.cache_data
def load_data(n_users):
    analyzer = UserBehaviorAnalyzer(laplace_smoothing=st.session_state.get('laplace_alpha', 1.0))
    df, user_df = analyzer.generate_mock_data(n_users=n_users)
    return analyzer, df, user_df

with st.sidebar:
    st.header("⚙️ 分析设置")
    
    st.subheader("模型配置")
    markov_order = st.radio(
        "马尔可夫链阶数",
        options=[1, 2],
        format_func=lambda x: f"{x}阶" + (" (考虑前一步)" if x == 1 else " (考虑前两步)"),
        index=0
    )
    
    use_smoothing = st.checkbox("启用拉普拉斯平滑", value=True)
    laplace_alpha = st.slider(
        "平滑系数 (α)",
        min_value=0.1,
        max_value=5.0,
        value=1.0,
        step=0.1,
        disabled=not use_smoothing,
        help="值越大，平滑效果越强，概率分布越均匀"
    )
    
    st.session_state['laplace_alpha'] = laplace_alpha
    
    n_users = st.slider("模拟用户数量", min_value=100, max_value=5000, value=1000, step=100)
    
    st.subheader("桑基图配置")
    group_low_freq = st.checkbox("合并低频行为节点", value=True)
    group_threshold = st.slider(
        "低频阈值",
        min_value=0.01,
        max_value=0.2,
        value=0.05,
        step=0.01,
        format="%.0%%",
        disabled=not group_low_freq,
        help="平均转移概率低于此阈值的行为将被合并到「其他」"
    )
    
    analyze_button = st.button("🚀 开始分析", type="primary")
    
    st.markdown("---")
    st.header("🔮 行为预测")
    
    if markov_order == 1:
        current_behavior = st.selectbox(
            "选择当前行为",
            ['浏览', '点击', '加购', '购买'],
            index=0
        )
    else:
        col1, col2 = st.columns(2)
        with col1:
            prev_behavior_1 = st.selectbox(
                "前两步行为",
                ['浏览', '点击', '加购', '购买'],
                index=0,
                key="prev1"
            )
        with col2:
            prev_behavior_2 = st.selectbox(
                "前一步行为",
                ['浏览', '点击', '加购', '购买'],
                index=1,
                key="prev2"
            )
        current_behavior = [prev_behavior_1, prev_behavior_2]
    
    predict_segment = st.selectbox(
        "选择用户分群",
        ['总体', '新客', '老客', '高活跃']
    )

if analyze_button or 'analysis_result' not in st.session_state:
    with st.spinner("正在分析数据..."):
        analyzer = UserBehaviorAnalyzer(laplace_smoothing=laplace_alpha if use_smoothing else 0)
        df, user_df = analyzer.generate_mock_data(n_users=n_users)
        result = analyzer.analyze(df, user_df, order=markov_order, use_smoothing=use_smoothing)
        st.session_state.analyzer = analyzer
        st.session_state.result = result
        st.session_state.analysis_result = result
        st.session_state.markov_order = markov_order
        st.session_state.use_smoothing = use_smoothing
        st.success("分析完成！")

if 'analysis_result' in st.session_state:
    analyzer = st.session_state.analyzer
    result = st.session_state.result
    
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "📈 数据概览", 
        "🌊 行为流向桑基图", 
        "🔢 转移概率矩阵",
        "📊 模型对比",
        "👥 分群分析",
        "🎲 行为模拟",
        "⚠️ 流失预警",
        "⏰ 时段对比"
    ])
    
    with tab1:
        st.subheader("用户行为数据概览")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("总用户数", f"{len(result['user_df']):,}")
        with col2:
            st.metric("总行为记录", f"{len(result['df']):,}")
        with col3:
            avg_seq = result['sequences_df']['sequence_length'].mean()
            st.metric("平均行为序列长度", f"{avg_seq:.1f}")
        with col4:
            st.metric("马尔可夫链阶数", f"{st.session_state.markov_order}阶")
        
        st.info(f"💡 **当前配置**: {'启用' if st.session_state.use_smoothing else '禁用'}拉普拉斯平滑 " +
                (f"(α={st.session_state.laplace_alpha})" if st.session_state.use_smoothing else ""))
        
        st.subheader("用户分群分布")
        fig_segment = analyzer.plot_segment_distribution(result['user_df'])
        st.plotly_chart(fig_segment, use_container_width=True)
        
        st.subheader("样本数据预览")
        st.dataframe(result['df'].head(20), use_container_width=True)
    
    with tab2:
        st.subheader("行为流向桑基图 (增强版)")
        
        segment_choice = st.selectbox(
            "选择分群查看桑基图",
            ['总体', '新客', '老客', '高活跃'],
            key='sankey_segment'
        )
        
        if segment_choice == '总体':
            matrix = result['overall_matrix_first']
            title = '总体用户行为流向桑基图'
        else:
            matrix = result['segmented_matrices'].get(segment_choice, result['overall_matrix_first'])
            title = f'{segment_choice}行为流向桑基图'
        
        col1, col2 = st.columns([3, 1])
        with col1:
            fig_sankey = analyzer.plot_enhanced_sankey(
                matrix, 
                title,
                group_low_freq=group_low_freq,
                group_threshold=group_threshold
            )
            st.plotly_chart(fig_sankey, use_container_width=True)
        
        with col2:
            st.markdown("**图表控制**")
            show_detail = st.checkbox("显示详细数据", value=False)
            
            if show_detail:
                st.markdown("**转移概率详情**")
                detail_df = matrix.style.format("{:.2%}")
                st.dataframe(detail_df, use_container_width=True)
                
                sankey_data = analyzer.create_enhanced_sankey_data(
                    matrix, 
                    group_low_freq=group_low_freq,
                    group_threshold=group_threshold
                )
                if sankey_data['low_freq_behaviors']:
                    st.markdown(f"**已合并的低频行为**: {', '.join(sankey_data['low_freq_behaviors'])}")
        
        st.markdown("""
        **图表说明：
        - 左侧节点表示当前行为状态
        - 右侧节点表示后续行为状态
        - 连线宽度表示转移概率大小
        - 颜色对应不同的行为类型
        - 鼠标悬停可查看详细转移概率
        """)
    
    with tab3:
        st.subheader("转移概率矩阵")
        
        view_mode = st.radio(
            "查看模式",
            ["一阶矩阵", "二阶矩阵"],
            index=0 if st.session_state.markov_order == 1 else 1,
            horizontal=True
        )
        
        segment_choice = st.selectbox(
            "选择分群",
            ['总体', '新客', '老客', '高活跃'],
            key='heatmap_segment'
        )
        
        if view_mode == "一阶矩阵":
            if segment_choice == '总体':
                matrix = result['overall_matrix_first']
                title = '一阶转移概率矩阵 (总体)'
            else:
                matrix = result['segmented_matrices'].get(segment_choice, result['overall_matrix_first'])
                if matrix.shape[0] > 4:
                    matrix = result['overall_matrix_first']
                title = f'一阶转移概率矩阵 ({segment_choice})'
            
            fig_heatmap = analyzer.plot_transition_heatmap(matrix, title)
            st.plotly_chart(fig_heatmap, use_container_width=True)
            
            st.subheader("数值矩阵表")
            styled_matrix = matrix.style.format("{:.2%}")
            st.dataframe(styled_matrix, use_container_width=True)
        
        else:
            if result['overall_matrix_second'] is not None:
                fig_heatmap = analyzer.plot_second_order_heatmap(
                    result['overall_matrix_second'], 
                    '二阶转移概率矩阵 (总体)'
                )
                st.plotly_chart(fig_heatmap, use_container_width=True)
                
                with st.expander("查看二阶矩阵数值表"):
                    styled_matrix = result['overall_matrix_second'].style.format("{:.1%}")
                    st.dataframe(styled_matrix, use_container_width=True)
            else:
                st.warning("请重新分析并选择二阶马尔可夫链以查看二阶矩阵")
    
    with tab4:
        st.subheader("一阶 vs 二阶 马尔可夫链对比")
        
        if st.button("运行模型对比测试", type="primary"):
            with st.spinner("正在对比测试..."):
                sequences = result['sequences_df']['sequence'].tolist()
                fig_comp, comp_data = analyzer.plot_model_comparison(sequences)
                st.session_state.model_comparison = (fig_comp, comp_data)
                st.success("对比完成！")
        
        if 'model_comparison' in st.session_state:
            fig_comp, comp_data = st.session_state.model_comparison
            st.plotly_chart(fig_comp, use_container_width=True)
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric(
                    "一阶马尔可夫链准确率",
                    f"{comp_data.iloc[0]['准确率']:.2%}",
                    help="仅考虑前一步行为"
                )
            with col2:
                st.metric(
                    "二阶马尔可夫链准确率",
                    f"{comp_data.iloc[1]['准确率']:.2%}",
                    delta=f"{(comp_data.iloc[1]['准确率'] - comp_data.iloc[0]['准确率']):.2%}",
                    help="考虑前两步行为"
                )
            
            st.markdown("**详细数据**")
            st.dataframe(comp_data.style.format({'准确率': '{:.2%}'}), use_container_width=True)
        
        st.markdown("""
        **测试方法说明：**
        - 将数据集按 8:2 划分为训练集和测试集
        - 在训练集上分别训练一阶和二阶马尔可夫链模型
        - 在测试集上进行预测，计算 Top-1 预测准确率
        - 二阶模型需要至少 3 步行为序列才能进行预测
        """)
    
    with tab5:
        st.subheader("各分群行为转移概率对比")
        fig_comparison = analyzer.plot_segment_comparison(result['segmented_matrices'])
        st.plotly_chart(fig_comparison, use_container_width=True)
        
        st.subheader("各分群详细对比")
        segments = list(result['segmented_matrices'].keys())
        cols = st.columns(len(segments))
        
        for idx, segment in enumerate(segments):
            with cols[idx]:
                st.markdown(f"**{segment}**")
                mat = result['segmented_matrices'][segment]
                if mat.shape[0] > 4:
                    st.write("(二阶矩阵，省略显示)")
                else:
                    styled_mat = mat.style.format("{:.1%}")
                    st.dataframe(styled_mat, use_container_width=True)
    
    with tab6:
        st.subheader("🎲 行为路径模拟 (假设分析)")
        
        col1, col2 = st.columns(2)
        with col1:
            sim_order = st.radio("模拟模型阶数", [1, 2], index=0, horizontal=True)
        with col2:
            sim_length = st.slider("模拟路径长度", 3, 15, 8)
        
        n_samples = st.slider("生成路径数量", 1, 10, 5)
        
        st.markdown("**设置起始状态**")
        if sim_order == 1:
            start_behavior = st.selectbox(
                "起始行为",
                ['浏览', '点击', '加购', '购买'],
                key='sim_start'
            )
            start_state = start_behavior
        else:
            col_a, col_b = st.columns(2)
            with col_a:
                start_1 = st.selectbox("第一步行为", ['浏览', '点击', '加购', '购买'], key='sim_start1')
            with col_b:
                start_2 = st.selectbox("第二步行为", ['浏览', '点击', '加购', '购买'], key='sim_start2', index=1)
            start_state = [start_1, start_2]
        
        sim_segment = st.selectbox(
            "选择用户分群模型",
            ['总体', '新客', '老客', '高活跃'],
            key='sim_segment'
        )
        
        if sim_segment == '总体':
            sim_matrix = result['overall_matrix_first'] if sim_order == 1 else (result['overall_matrix_second'] or result['overall_matrix_first'])
        else:
            sim_matrix = result['segmented_matrices'].get(sim_segment, result['overall_matrix_first'])
        
        if st.button("生成模拟路径", type="primary"):
            with st.spinner("正在生成模拟路径..."):
                sequences = analyzer.generate_behavior_sequence(
                    start_state, sim_matrix, order=sim_order, length=sim_length, n_samples=n_samples
                )
                
                st.session_state.simulated_sequences = sequences
                
                fig_sim = analyzer.plot_generated_sequences(sequences, title='模拟行为路径对比')
                st.plotly_chart(fig_sim, use_container_width=True)
                
                st.markdown("**详细路径列表**")
                for idx, seq in enumerate(sequences, 1):
                    path_prob = analyzer.calculate_path_probability(seq, sim_matrix, order=sim_order)
                    path_html = " → ".join([
                        f"<span style='background-color:{analyzer.colors.get(b, '#636EFA')};"
                        f"color:white;padding:2px 8px;border-radius:4px;margin:1px;display:inline-block;font-size:12px'>{b}</span>"
                        for b in seq
                    ])
                    st.markdown(f"**路径 {idx}** (概率: {path_prob:.2e})<br>{path_html}", unsafe_allow_html=True)
        
        st.markdown("""
        **使用场景：**
        - 假设用户从「浏览」开始，可能的转化路径有哪些？
        - 不同分群用户的行为模式差异
        - 评估营销活动对行为路径的影响
        - 识别关键流失节点
        """)
    
    with tab7:
        st.subheader("⚠️ 用户流失预警分析")
        
        st.markdown("**选择用户行为序列进行风险评估**")
        
        sample_users = result['sequences_df'].sample(n=min(10, len(result['sequences_df'])))
        user_options = [f"用户 {row['user_id']} (长度: {row['sequence_length']})" for _, row in sample_users.iterrows()]
        
        selected_user_idx = st.selectbox(
            "选择样本用户",
            range(len(user_options)),
            format_func=lambda x: user_options[x]
        )
        
        selected_sequence = sample_users.iloc[selected_user_idx]['sequence']
        selected_user_id = sample_users.iloc[selected_user_idx]['user_id']
        
        col1, col2 = st.columns([1, 1])
        with col1:
            st.markdown("**用户行为序列：**")
            path_html = " → ".join([
                f"<span style='background-color:{analyzer.colors.get(b, '#636EFA')};"
                f"color:white;padding:3px 10px;border-radius:4px;margin:2px;display:inline-block'>{b}</span>"
                for b in selected_sequence
            ])
            st.markdown(path_html, unsafe_allow_html=True)
        
        risk_threshold = st.slider("风险阈值", 0.1, 0.7, 0.3, help="高于此阈值标记为高风险")
        
        churn_matrix = result['overall_matrix_first']
        churn_risk = analyzer.analyze_churn_risk(
            selected_sequence, churn_matrix, order=st.session_state.markov_order, risk_threshold=risk_threshold
        )
        
        col1, col2 = st.columns(2)
        with col1:
            fig_gauge = analyzer.plot_churn_risk_gauge(churn_risk['risk_score'], title='用户流失风险指数')
            st.plotly_chart(fig_gauge, use_container_width=True)
        
        with col2:
            risk_color = '#EF553B' if churn_risk['risk_level'] == '高风险' else ('#FFA15A' if churn_risk['risk_level'] == '中风险' else '#00CC96')
            st.markdown(f"<h3 style='color:{risk_color}'>风险等级: {churn_risk['risk_level']}</h3>", unsafe_allow_html=True)
            
            st.metric("风险分数", f"{churn_risk['risk_score']:.1%}")
            st.metric("转化进度", f"{churn_risk['conversion_progress']}%")
            
            if churn_risk['risk_factors']:
                st.markdown("**风险因素：**")
                for factor in churn_risk['risk_factors']:
                    st.markdown(f"- ⚠️ {factor}")
            else:
                st.markdown("✅ 未发现明显风险因素")
        
        st.markdown("---")
        st.subheader("批量用户风险扫描")
        
        if st.button("扫描高风险用户"):
            with st.spinner("正在扫描用户风险..."):
                risk_results = []
                for _, row in result['sequences_df'].iterrows():
                    seq = row['sequence']
                    if len(seq) >= 3:
                        risk = analyzer.analyze_churn_risk(seq, churn_matrix, risk_threshold=risk_threshold)
                        risk_results.append({
                            'user_id': row['user_id'],
                            'sequence_length': row['sequence_length'],
                            'risk_level': risk['risk_level'],
                            'risk_score': risk['risk_score'],
                            'conversion_progress': risk['conversion_progress']
                        })
                
                risk_df = pd.DataFrame(risk_results)
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    high_risk = len(risk_df[risk_df['risk_level'] == '高风险'])
                    st.metric("高风险用户", high_risk)
                with col2:
                    mid_risk = len(risk_df[risk_df['risk_level'] == '中风险'])
                    st.metric("中风险用户", mid_risk)
                with col3:
                    low_risk = len(risk_df[risk_df['risk_level'] == '低风险'])
                    st.metric("低风险用户", low_risk)
                
                st.subheader("高风险用户列表")
                high_risk_df = risk_df[risk_df['risk_level'] == '高风险'].sort_values('risk_score', ascending=False)
                if len(high_risk_df) > 0:
                    st.dataframe(
                        high_risk_df.style.format({'risk_score': '{:.1%}'}),
                        use_container_width=True
                    )
                else:
                    st.success("暂无高风险用户")
    
    with tab8:
        st.subheader("⏰ 跨时段行为对比分析")
        
        col1, col2 = st.columns(2)
        with col1:
            period_metric = st.selectbox(
                "对比指标",
                ['购买', '加购', '点击', '浏览'],
                index=0
            )
        
        fig_period = analyzer.plot_period_comparison(
            result['period_results'], metric=period_metric, title=f'各时段转向「{period_metric}」概率对比'
        )
        st.plotly_chart(fig_period, use_container_width=True)
        
        st.subheader("时段数据统计")
        period_stats_df = pd.DataFrame(result['period_stats']).T
        st.dataframe(period_stats_df, use_container_width=True)
        
        st.subheader("分时段转移矩阵对比")
        
        col1, col2 = st.columns(2)
        with col1:
            period1 = st.selectbox("时段 A", list(result['period_results'].keys()), index=0)
        with col2:
            period2 = st.selectbox("时段 B", list(result['period_results'].keys()), index=1)
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**{period1}**")
            mat1 = result['period_results'][period1]
            st.dataframe(mat1.style.format("{:.1%}"), use_container_width=True)
        with col2:
            st.markdown(f"**{period2}**")
            mat2 = result['period_results'][period2]
            st.dataframe(mat2.style.format("{:.1%}"), use_container_width=True)
        
        st.subheader("差异矩阵")
        diff_matrix = mat1 - mat2
        fig_diff = px.imshow(
            diff_matrix,
            title=f'{period1} - {period2} 转移概率差异',
            labels=dict(x='后续行为', y='当前行为', color='概率差异'),
            color_continuous_scale='RdBu',
            aspect='auto'
        )
        for i in range(len(analyzer.behaviors)):
            for j in range(len(analyzer.behaviors)):
                fig_diff.add_annotation(
                    x=j, y=i,
                    text=f'{diff_matrix.iloc[i, j]:+.1%}',
                    showarrow=False,
                    font=dict(color='white', size=10)
                )
        fig_diff.update_layout(height=500)
        st.plotly_chart(fig_diff, use_container_width=True)
        
        st.markdown("""
        **分析场景：**
        - 周末用户购买意愿是否更强？
        - 活动期间用户加购率提升了多少？
        - 不同时段的行为模式差异
        - 营销策略的时段效果评估
        """)
    
    with st.expander("🔮 行为预测"):
        st.subheader("下一步行为预测")
        
        if predict_segment == '总体':
            if st.session_state.markov_order == 1:
                pred_matrix = result['overall_matrix_first']
            else:
                pred_matrix = result['overall_matrix_second'] if result['overall_matrix_second'] is not None else result['overall_matrix_first']
        else:
            pred_matrix = result['segmented_matrices'].get(predict_segment, result['overall_matrix_first'])
        
        predictions = analyzer.predict_next_behavior(
            current_behavior, 
            pred_matrix, 
            order=st.session_state.markov_order,
            top_k=3
        )
        
        if predictions:
            if st.session_state.markov_order == 1:
                st.markdown(f"### 当前行为：**{current_behavior}**")
            else:
                st.markdown(f"### 行为序列：**{current_behavior[0]} → {current_behavior[1]}**")
            
            st.markdown(f"### 用户分群：**{predict_segment}**")
            st.markdown(f"### 模型：**{st.session_state.markov_order}阶马尔可夫链**")
            
            st.markdown("#### 预测结果：")
            for i, pred in enumerate(predictions, 1):
                prob = pred['probability']
                color = analyzer.colors.get(pred['behavior'], '#636EFA')
                st.markdown(
                    f"{i}. **{pred['behavior']}** - "
                    f"<span style='color:{color};font-weight:bold;font-size:20px'>{prob:.2%}</span>",
                    unsafe_allow_html=True
                )
                
                progress_bar = st.progress(0)
                progress_bar.progress(prob)
            
            st.markdown("---")
            st.subheader("多步预测示例")
            
            steps = st.slider("预测步数", 1, 5, 3, key='pred_steps')
            
            if st.session_state.markov_order == 1:
                current = current_behavior
                prediction_path = [current]
                
                for _ in range(steps):
                    next_preds = analyzer.predict_next_behavior(
                        current, pred_matrix, order=1, top_k=1
                    )
                    if next_preds:
                        current = next_preds[0]['behavior']
                        prediction_path.append(current)
                    else:
                        break
            else:
                prediction_path = current_behavior.copy()
                current_seq = current_behavior.copy()
                
                for _ in range(steps):
                    next_preds = analyzer.predict_next_behavior(
                        current_seq, pred_matrix, order=2, top_k=1
                    )
                    if next_preds:
                        next_behavior = next_preds[0]['behavior']
                        prediction_path.append(next_behavior)
                        current_seq = [current_seq[-1], next_behavior]
                    else:
                        break
            
            st.markdown("#### 预测路径：")
            path_html = " → ".join([
                f"<span style='background-color:{analyzer.colors.get(b, '#636EFA')};"
                f"color:white;padding:4px 12px;border-radius:4px;margin:2px;display:inline-block'>{b}</span>"
                for b in prediction_path
            ])
            st.markdown(path_html, unsafe_allow_html=True)
        
        else:
            st.warning("无法进行预测，请检查输入的行为序列")

else:
    st.info("👈 请在左侧面板点击「开始分析」按钮开始分析")
    
    st.markdown("""
    ## 功能介绍 (增强版)
    
    本系统基于**马尔可夫链**对用户消费行为进行分析，新增增强功能：
    
    ### 1. 二阶马尔可夫链
    - 考虑**前两步行为**对当前行为的影响
    - 相比一阶模型，预测准确率通常提升 5%-15%
    - 更符合真实用户行为的序列依赖性
    
    ### 2. 拉普拉斯平滑
    - 解决稀疏数据问题，避免零概率
    - 对于低频转移模式，引入先验概率
    - 平滑系数可调节，平衡经验与先验
    
    ### 3. 增强版桑基图
    - 自动合并低频行为节点，简化图表
    - 分组展示，支持点击展开细节
    - 鼠标悬停显示详细转移概率
    
    ### 4. 模型对比功能
    - 自动对比一阶 vs 二阶模型准确率
    - 8:2 数据分割，客观评估
    - 帮助选择最佳模型配置
    
    ### 5. 🎲 行为路径模拟
    - 基于马尔可夫链生成多条可能的行为路径
    - 支持假设分析，评估不同起始状态的转化可能性
    
    ### 6. ⚠️ 流失预警
    - 智能识别高风险流失用户
    - 多维度风险评分
    - 批量扫描高风险用户群体
    
    ### 7. ⏰ 跨时段对比
    - 工作日 vs 周末行为差异
    - 活动期 vs 平日效果对比
    - 差异矩阵可视化
    
    点击左侧的「开始分析」按钮开始体验！
    """)
