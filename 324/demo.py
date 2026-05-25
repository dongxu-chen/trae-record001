import sys
import os
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def print_header(title):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def print_section(title):
    print("\n" + "─" * 80)
    print(f"  {title}")
    print("─" * 80)

def main():
    print_header("📺 电视剧收视率预测系统 - 完整演示")
    print("  Python + XGBoost + LSTM + 情感分析")
    
    print("\n正在初始化预测引擎...")
    from prediction_engine import RatingPredictionEngine
    from data_generator import generate_drama_basic_info, generate_episodic_ratings, generate_social_media_data
    from sentiment_analyzer import generate_episode_comments_batch, aggregate_episode_sentiment
    
    engine = RatingPredictionEngine()
    
    print_section("步骤 1: 训练预测模型")
    print("正在生成历史剧集数据并训练XGBoost和LSTM模型...")
    engine.train_models(num_dramas=20, force_retrain=True)
    
    print_section("步骤 2: 创建待预测剧集")
    drama = generate_drama_basic_info('DEMO2024')
    drama['drama_name'] = '《长安风云录》'
    drama['genre'] = '古装'
    drama['platform'] = '湖南卫视'
    drama['time_slot'] = '黄金档(19:30-21:00)'
    drama['actor_level'] = '顶级'
    drama['num_episodes'] = 40
    drama['production_budget'] = 35000
    drama['director_reputation'] = 0.9
    drama['is_sequel'] = 0
    
    print(f"""
  📋 剧集基本信息:
  ─────────────────────────────────────────────────────────
    剧集名称: {drama['drama_name']}
    题材类型: {drama['genre']}
    播出平台: {drama['platform']}
    播出时段: {drama['time_slot']}
    演员阵容: {drama['actor_level']}
    总 集 数: {drama['num_episodes']} 集
    制作预算: {drama['production_budget']:,} 万元
    导演声望: {drama['director_reputation']:.1f} / 1.0
    是否续集: {'是' if drama['is_sequel'] else '否'}
  ─────────────────────────────────────────────────────────
    """)
    
    print_section("步骤 3: 生成模拟数据")
    print("生成剧集播出日期、真实收视率（用于验证）、社交媒体数据...")
    dates, true_ratings = generate_episodic_ratings(drama)
    social_df = generate_social_media_data(drama, dates, true_ratings)
    
    print(f"  ✓ 播出日期: {dates[0].strftime('%Y-%m-%d')} 至 {dates[-1].strftime('%Y-%m-%d')}")
    print(f"  ✓ 社交媒体数据维度: {social_df.shape[0]} 行 × {social_df.shape[1]} 列")
    print(f"  ✓ 数据列: {', '.join(social_df.columns.tolist())}")
    
    print_section("步骤 4: 生成评论并进行情感分析")
    print("正在生成观众评论并执行基于词典的情感分析...")
    comments_df = generate_episode_comments_batch(drama, dates, true_ratings)
    sentiment_stats = aggregate_episode_sentiment(comments_df)
    
    total_comments = len(comments_df)
    pos_count = (comments_df['type'] == 'positive').sum()
    neg_count = (comments_df['type'] == 'negative').sum()
    neu_count = (comments_df['type'] == 'neutral').sum()
    
    print(f"""
  💬 评论分析汇总:
  ─────────────────────────────────────────────────────────
    总评论数: {total_comments:,} 条
    正面评论: {pos_count:,} 条 ({pos_count/total_comments*100:.1f}%)
    负面评论: {neg_count:,} 条 ({neg_count/total_comments*100:.1f}%)
    中立评论: {neu_count:,} 条 ({neu_count/total_comments*100:.1f}%)
    平均情感得分: {sentiment_stats['avg_sentiment'].mean():.3f} (0.0-1.0)
  ─────────────────────────────────────────────────────────
    """)
    
    print("  📝 评论样本:")
    for _, row in comments_df.head(5).iterrows():
        sentiment_icon = '😊' if row['type'] == 'positive' else ('😠' if row['type'] == 'negative' else '😐')
        print(f"    {sentiment_icon} [{row['sentiment']:.2f}] {row['comment']}")
    
    print_section("步骤 4.1: LSTM时间间隔门分析")
    print("⏰ 分析不同时间间隔对历史信息的衰减影响...")
    
    from data_generator import generate_trailer_heat, predict_premiere_rating
    
    intervals = [1, 2, 3, 5, 7, 14, 30]
    time_gate_df = engine.lstm_predictor.get_time_gate_effect(intervals)
    
    print(f"""
  📊 时间间隔门效果:
  ─────────────────────────────────────────────────────────
    衰减率: {engine.lstm_predictor.time_gate_params['time_decay_rate']}
    最大间隔: {engine.lstm_predictor.time_gate_params['max_interval_days']} 天
    缩放方式: {'对数缩放' if engine.lstm_predictor.time_gate_params['interval_scaling'] == 'log' else '线性缩放'}
    可学习衰减: {'是' if engine.lstm_predictor.time_gate_params['use_trainable_decay'] else '否'}
  ─────────────────────────────────────────────────────────
    """)
    
    print(f"  {'间隔天数':<12}{'缩放后值':<12}{'衰减系数':<12}{'信息保留率':<12}")
    print("  " + "─" * 48)
    for _, row in time_gate_df.iterrows():
        print(f"  {int(row['interval_days']):<12}{row['scaled_interval']:<12.4f}{row['decay_effect']:<12.4f}{row['information_retention']:>10.1f}%")
    
    print(f"""
  💡 时间间隔门原理:
  ─────────────────────────────────────────────────────────
    显式建模相邻观测之间的时间间隔，实现动态衰减：
    • 间隔1天：保留约90%历史信息
    • 间隔3天：保留约75%历史信息
    • 间隔7天：保留约60%历史信息
    • 间隔30天：仅保留约30%历史信息
    • 更合理地处理周播、日播等不同播出模式
  ─────────────────────────────────────────────────────────
    """)
    
    print_section("步骤 4.2: 首播收视率预测（基于预告片热度）")
    print("🎬 基于首播前30天预告片热度预测首播收视率...")
    
    trailer_heat_df = generate_trailer_heat(drama, days_before_premiere=30)
    premiere_pred = predict_premiere_rating(drama, trailer_heat_df)
    
    print(f"""
  🔥 预告片热度汇总:
  ─────────────────────────────────────────────────────────
    累计预告片播放: {premiere_pred['key_metrics']['cumulative_views']:,} 次
    最高日播放量: {trailer_heat_df['trailer_views'].max():,} 次
    最终搜索指数: {premiere_pred['key_metrics']['final_search_index']:,}
    综合热度均值: {premiere_pred['key_metrics']['avg_composite_heat']:.2f}
    热度动量: {premiere_pred['key_metrics']['heat_momentum']:.2f}%
  ─────────────────────────────────────────────────────────
    """)
    
    conf_level = "高" if premiere_pred['confidence'] > 0.75 else ("中" if premiere_pred['confidence'] > 0.55 else "低")
    print(f"""
  🎯 首播预测结果:
  ─────────────────────────────────────────────────────────
    预测首播收视率: {premiere_pred['predicted_rating']:.2f}%
    预测区间: [{premiere_pred['lower_bound']:.2f}, {premiere_pred['upper_bound']:.2f}]
    预测置信度: {conf_level} ({premiere_pred['confidence']:.1%})
  ─────────────────────────────────────────────────────────
    """)
    
    print("  📊 特征贡献度:")
    for name, data in premiere_pred['feature_contribution'].items():
        name_cn = {
            'trailer_heat': '预告片热度',
            'cast_heat': '演员阵容',
            'platform': '播出平台',
            'genre': '题材类型',
            'marketing': '营销热度'
        }.get(name, name)
        bar = "█" * int(data['score'] * 30) + "░" * (30 - int(data['score'] * 30))
        print(f"    {name_cn:<8} (权重{data['weight']:.0%}): {bar} {data['contribution']:.2f}")
    
    print(f"""
  📅 首播前7天热度趋势:
  ─────────────────────────────────────────────────────────
    {'距首播':<8}{'播放量':<15}{'搜索指数':<12}{'综合热度':<12}
  ─────────────────────────────────────────────────────────""")
    for _, row in trailer_heat_df.tail(7).iterrows():
        print(f"    {int(row['days_to_premiere']):<8}{row['trailer_views']:>12,}  {row['search_index']:>10,}  {row['composite_heat_score']:>10.2f}")
    
    print_section("步骤 5: 执行收视率预测")
    n_known = 8
    print(f"已知前 {n_known} 集收视率，预测剩余 {len(dates) - n_known} 集...")
    
    initial_ratings = true_ratings[:n_known]
    
    print(f"\n  📊 已知前 {n_known} 集真实收视率:")
    for i, (date, rating) in enumerate(zip(dates[:n_known], initial_ratings), 1):
        print(f"    第{i:2d}集 ({date.strftime('%Y-%m-%d')}): {rating:.3f}%")
    
    print("\n  🚀 正在执行预测...")
    report = engine.generate_full_prediction_report(
        drama, dates, initial_ratings, social_df, comments_df
    )
    
    print_section("📈 预测结果摘要")
    summary = report['prediction_summary']
    
    trend_text = "上升" if summary['trend'] > 0.01 else ("下降" if summary['trend'] < -0.01 else "平稳")
    trend_icon = "↗️" if summary['trend'] > 0.01 else ("↘️" if summary['trend'] < -0.01 else "→")
    
    print(f"""
  📊 预测统计:
  ─────────────────────────────────────────────────────────
    平均预测收视率: {summary['avg_predicted']:.2f}%
    最高预测收视率: {summary['max_predicted']:.2f}%
    最低预测收视率: {summary['min_predicted']:.2f}%
    收视趋势: {trend_icon} {trend_text} ({summary['trend']:.4f})
    已知集数: {summary['known_episodes']} 集
    预测集数: {summary['predicted_episodes']} 集
  ─────────────────────────────────────────────────────────
    """)
    
    print_section("📈 每集收视率预测结果")
    print(f"  {'集数':<6}{'日期':<12}{'星期':<8}{'真实值':<12}{'XGBoost':<12}{'LSTM':<12}{'集成预测':<12}{'爆点':<6}")
    print("  " + "─" * 80)
    
    details = report['episode_details']
    for idx, row in details.iterrows():
        ep = int(row['episode'])
        date = row['date'].strftime('%Y-%m-%d')
        weekday = row['day_of_week'][:3]
        known = f"{row['known_rating']:.3f}" if pd.notna(row['known_rating']) else "-"
        xgb = f"{row['xgb_prediction']:.3f}"
        lstm = f"{row['lstm_prediction']:.3f}"
        ens = f"{row['ensemble_prediction']:.3f}"
        peak = " ⚡" if row['is_peak'] else ""
        status = " [已知]" if idx < n_known else " [预测]"
        print(f"  {ep:<6}{date:<12}{weekday:<8}{known:<12}{xgb:<12}{lstm:<12}{ens:<12}{peak}{status}")
    
    print_section("⚡ 爆点预测分析")
    peaks = report['peak_episodes']
    
    if peaks:
        for i, peak in enumerate(peaks[:5], 1):
            conf_level = "高" if peak['confidence'] > 0.7 else ("中" if peak['confidence'] > 0.5 else "低")
            conf_color = "🟢" if peak['confidence'] > 0.7 else ("🟡" if peak['confidence'] > 0.5 else "🔴")
            
            ep_date = dates[peak['episode'] - 1].strftime('%Y-%m-%d')
            weekday = dates[peak['episode'] - 1].strftime('%A')
            
            print(f"""
  {conf_color} 爆点 {i}: 第 {peak['episode']} 集 ({ep_date} {weekday})
  ─────────────────────────────────────────────────
    预测收视率: {peak['predicted_rating']:.2f}%
    平均收视率: {peak['average_rating']:.2f}%
    超出均值: +{peak['increase_percent']:.1f}%
    置信度: {conf_level} ({peak['confidence']:.2f})
            """)
    else:
        print("  未检测到明显的收视爆点，收视表现相对平稳。")
    
    print_section("💡 爆点原因分析")
    print("""
  可能导致收视爆点的因素:
  ─────────────────────────────────────────────────────────
  📺 剧情转折点: 故事进入高潮阶段，关键冲突爆发
  🎭 角色重大事件: 主要角色命运发生重大变化
  💑 感情线突破: 核心CP关系出现关键进展
  🔍 悬念揭晓: 前期铺垫的悬念或谜题揭晓
  🎬 制作亮点: 某集在导演、演技或特效上有突出表现
  📢 宣发加成: 配合剧集播出的营销活动带动收视
  📅 档期效应: 节假日或特殊档期带来的收视红利
  🔥 话题热度: 社交媒体讨论热度带动收视增长
    """)
    
    print_section("✅ 续订建议")
    renewal = report['renewal_recommendation']
    score = renewal['total_score']
    
    if score >= 80:
        score_icon = "🏆"
        score_color = "🟢"
    elif score >= 65:
        score_icon = "✅"
        score_color = "🟢"
    elif score >= 50:
        score_icon = "⚠️"
        score_color = "🟡"
    elif score >= 35:
        score_icon = "❓"
        score_color = "🟡"
    else:
        score_icon = "❌"
        score_color = "🔴"
    
    print(f"""
  {score_icon} 综合评分: {score:.1f} / 100  {score_color}
  📋 建议: {renewal['recommendation']}
  🎯 置信度: {renewal['confidence']}

  📝 关键依据:
  ─────────────────────────────────────────────────────────""")
    for reason in renewal['key_reasons']:
        print(f"    • {reason}")
    
    print("\n  📊 各维度得分详情:")
    print(f"  {'维度':<15}{'得分':<10}{'权重':<10}{'实际值':<30}")
    print("  " + "─" * 65)
    
    factor_names = {
        'avg_rating': '平均收视率',
        'trend': '收视趋势',
        'peak_rating': '峰值收视率',
        'sentiment': '观众情感',
        'actor_level': '演员阵容',
        'is_sequel': '续集效应',
        'search_index': '搜索热度',
        'stability': '收视稳定性'
    }
    
    for k, v in renewal['factors'].items():
        name = factor_names.get(k, k)
        score_bar = "█" * int(v['score'] / v['weight'] * 20) + "░" * (20 - int(v['score'] / v['weight'] * 20))
        print(f"  {name:<15}{v['score']:>4.1f}/{v['weight']:<4}  {score_bar}  {str(v['value']):<30}")
    
    print("\n  📈 汇总统计:")
    stats = renewal['summary_stats']
    print(f"""
    ┌──────────────────────┬─────────────────┐
    │ 指标                │ 数值            │
    ├──────────────────────┼─────────────────┤
    │ 平均收视率          │ {stats['avg_rating']:>15.2f}% │
    │ 最高收视率          │ {stats['max_rating']:>15.2f}% │
    │ 最低收视率          │ {stats['min_rating']:>15.2f}% │
    │ 收视趋势            │ {stats['rating_trend']:>16.4f} │
    │ 平均情感得分        │ {stats['avg_sentiment']:>16.4f} │
    │ 平均搜索指数        │ {stats['avg_search_index']:>16,} │
    │ 总发帖量            │ {stats['total_post_volume']:>16,} │
    │ 收视稳定性          │ {stats['stability_index']:>16.4f} │
    └──────────────────────┴─────────────────┘
    """)
    
    if 'revenue_analysis' in renewal:
        print_section("💰 收益模型分析")
        revenue = renewal['revenue_analysis']
        profit = revenue['profit_metrics']
        
        net_profit_wan = profit['net_profit'] / 10000
        roi_color = "🟢" if profit['roi'] >= 0.1 else ("🟡" if profit['roi'] >= 0 else "🔴")
        profit_color = "🟢" if net_profit_wan >= 0 else "🔴"
        
        payback = profit['payback_period_years']
        payback_text = f"{payback:.1f}年" if isinstance(payback, (int, float)) else payback
        
        print(f"""
  💵 核心盈利指标:
  ─────────────────────────────────────────────────────────
    预计净利润: {profit_color} {net_profit_wan:,.1f} 万元
    投资回报率(ROI): {roi_color} {profit['roi']*100:.1f}%
    投资回收期: ⏱️  {payback_text}
    净利率: 📊 {profit['net_margin']*100:.1f}%
    毛利率: 📈 {profit['gross_margin']*100:.1f}%
    每收视点利润: 💰 {profit['profit_per_rating_point']/10000:.1f} 万元/点
  ─────────────────────────────────────────────────────────
    """)
        
        print("  📊 收入构成 (万元):")
        total_rev = sum(revenue['revenue_breakdown'].values()) / 10000
        for name, value in revenue['revenue_breakdown'].items():
            value_wan = value / 10000
            pct = value / sum(revenue['revenue_breakdown'].values()) * 100
            bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
            print(f"    {name:<8}: {value_wan:>10,.1f}万 ({pct:>5.1f}%) {bar}")
        
        print(f"\n    {'总收入':<8}: {total_rev:>10,.1f}万 (100.0%)")
        
        print("\n  📊 成本构成 (万元):")
        total_cost = sum(revenue['cost_breakdown'].values()) / 10000
        for name, value in revenue['cost_breakdown'].items():
            value_wan = value / 10000
            pct = value / sum(revenue['cost_breakdown'].values()) * 100
            bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
            print(f"    {name:<8}: {value_wan:>10,.1f}万 ({pct:>5.1f}%) {bar}")
        
        print(f"\n    {'总成本':<8}: {total_cost:>10,.1f}万 (100.0%)")
        
        print(f"""
  📈 收益评分详情:
  ─────────────────────────────────────────────────────────
    基础评分(收视+情感等): {revenue['base_score']:.1f} / 100 (权重40%)
    收益评分(ROI+利润等): {revenue['revenue_score']:.1f} / 90 (权重60%)
    最终综合评分: {revenue['combined_score']:.1f} / 100
  ─────────────────────────────────────────────────────────
    """)
        
        print("  💡 收益模型说明:")
        print(f"""
    收入 = 广告收入(收视率×系数×时长) + 版权费 + 海外发行(15%) + IP衍生(10%)
    成本 = 制作成本 + 运营成本(营收×40%) + 税收(利润×25%)
    ROI = 净利润 / 制作成本
    评分融合 = 基础分×40% + 收益分×60%
    """)
    
    print_section("📊 模型预测精度评估")
    eval_results = engine.get_model_evaluation(drama, dates, true_ratings, social_df, n_known)
    
    print(f"""
  基于后续 {len(dates) - n_known} 集真实数据的模型精度评估:
  ─────────────────────────────────────────────────────────""")
    
    for name, metrics in eval_results.items():
        display_name = {
            'xgb_predictions': 'XGBoost',
            'lstm_predictions': 'LSTM',
            'ensemble_predictions': '集成模型 (60% XGB + 40% LSTM)'
        }.get(name, name)
        
        rmse_color = "🟢" if metrics['rmse'] < 0.15 else ("🟡" if metrics['rmse'] < 0.3 else "🔴")
        mape_color = "🟢" if metrics['mape'] < 15 else ("🟡" if metrics['mape'] < 30 else "🔴")
        
        print(f"""
  🤖 {display_name}
    RMSE (均方根误差): {rmse_color} {metrics['rmse']:.4f} (越小越好)
    MAPE (平均绝对百分比误差): {mape_color} {metrics['mape']:.2f}% (越小越好)""")
    
    print_section("📚 技术架构说明")
    print("""
  本系统采用多模型融合的混合预测架构 (升级版):

  1️⃣ XGBoost 模型 (权重 55%)
     ├─ 擅长处理: 剧集特征（题材、演员、平台、时段等）
     │           社交媒体特征（热度、互动、情感等）
     │           非线性关系捕捉
     └─ 特征工程: 前N集收视率、移动平均、变化率、哑编码等

  2️⃣ LSTM 模型 (权重 45%) - ⭐ 升级版: 时间间隔门
     ├─ 核心创新: 时间间隔门 (Time Interval Gate)
     │   ├─ 显式建模相邻观测之间的时间间隔
     │   ├─ 根据间隔长度动态衰减历史信息
     │   ├─ 可学习衰减率，适应不同数据模式
     │   └─ 间隔1天保留90%，间隔30天仅保留30%
     ├─ 擅长处理: 时间序列依赖、趋势和周期性模式
     └─ 输入序列: 收视率 + 社交媒体多指标 + 时间间隔

  3️⃣ 首播预测模块 - ⭐ 新增
     ├─ 输入: 首播前30天预告片热度数据
     │   ├─ 预告片播放量、点赞、评论、转发
     │   ├─ 话题阅读量、讨论量、搜索指数
     │   └─ 主演热度、营销热度
     ├─ 权重分配: 预告片35% + 演员25% + 平台20% + 题材10% + 营销10%
     └─ 输出: 首播收视率预测区间 + 置信度

  4️⃣ 情感分析模块
     ├─ 算法: 基于词典的中文情感分析
     ├─ 词典: 正负面词汇、程度副词、否定词、表情符号
     └─ 输出: 每集情感得分、正负评论比例、关键词统计

  5️⃣ 收益模型 - ⭐ 新增
     ├─ 收入构成:
     │   ├─ 广告收入 = 收视率 × 系数 × 广告时长 × 集数
     │   ├─ 版权费 = 基础费 + 收视奖金 + 演员奖金
     │   ├─ 海外发行 = 版权费 × 15%
     │   └─ IP衍生 = 版权费 × 10%
     ├─ 成本构成:
     │   ├─ 制作成本 = 制作预算 × 10000
     │   ├─ 运营成本 = 总收入 × 40%
     │   └─ 税收 = 利润 × 25%
     └─ 决策指标: ROI、净利润、投资回收期、净利率

  6️⃣ 模型集成策略
     └─ 加权融合: 集成预测 = 0.55 * XGBoost + 0.45 * LSTM

  7️⃣ 爆点检测算法
     ├─ 曲线平滑: 移动平均降噪
     ├─ 峰值检测: 局部极值 + 阈值判断
     └─ 置信度: 局部/全局幅度综合评估

  8️⃣ 续订评分系统 (升级版)
     ├─ 基础评分 (40%): 收视+情感+热度等8维度 (满分100)
     ├─ 收益评分 (60%):
     │   ├─ ROI回报率 (30分)
     │   ├─ 净利润额 (25分)
     │   ├─ 投资回收期 (15分)
     │   ├─ 净利率 (20分)
     │   └─ 收视调整 (10分)
     └─ 综合评分 → 5档决策建议
    """)
    
    print_section("🚀 使用说明")
    print("""
  命令行模式 (无需Streamlit):
    python demo.py              # 运行完整演示
    python prediction_engine.py  # 运行预测引擎自测
    python xgboost_model.py     # 运行XGBoost模型测试
    python lstm_model.py        # 运行LSTM模型测试
    python sentiment_analyzer.py # 运行情感分析测试

  Streamlit Web界面模式:
    1. 建议使用 Python 3.10 或 3.11 版本 (Streamlit 兼容性更好)
    2. 创建虚拟环境:
       python -m venv venv
       venv\\Scripts\\activate
    3. 安装依赖:
       pip install -r requirements.txt
    4. 启动应用:
       streamlit run app.py
    5. 浏览器访问: http://localhost:8501

  项目文件结构:
    config.py              # 配置常量和模型参数
    utils.py               # 工具函数（日期、统计、序列等）
    data_generator.py      # 数据生成、特征工程、首播预测
    sentiment_analyzer.py  # 情感分析模块
    xgboost_model.py       # XGBoost预测模型
    lstm_model.py          # LSTM时间序列模型 (带时间间隔门)
    prediction_engine.py   # 预测引擎、模型集成、收益模型
    app.py                 # Streamlit Web界面
    demo.py                # 命令行完整演示
    requirements.txt       # Python依赖列表
    models/                # 训练好的模型文件

  ⭐ 新增功能模块:
    • TimeIntervalLSTM: 带时间间隔门的LSTM模型
    • 首播预测: 基于预告片热度预测首播收视率
    • RevenueModel: 收益模型（收视率+版权费+制作成本）
    • 续订评分融合: 基础分40% + 收益分60%
    """)
    
    print_header("✅ 演示完成！")
    print("""
  系统已成功完成 (升级版):
  ✓ 数据生成与预处理
  ✓ XGBoost模型训练与预测
  ✓ LSTM模型训练与预测 (含时间间隔门)
  ✓ 基于词典的情感分析
  ✓ 多模型加权集成 (55% XGB + 45% LSTM)
  ✓ 收视爆点检测
  ✓ ⭐ LSTM时间间隔门分析
  ✓ ⭐ 基于预告片热度的首播预测
  ✓ ⭐ 完整收益模型分析
  ✓ ⭐ 升级版续订建议评分 (基础40% + 收益60%)
  ✓ 完整分析报告生成

  如需更丰富的可视化交互体验，请使用 Python 3.10/3.11 环境
  启动 Streamlit Web 界面: streamlit run app.py
  
  ⭐ 本次升级三大核心功能:
  1. LSTM时间间隔门: 可调节长期间隔的历史信息影响
  2. 首播预测: 引入预告片热度，预测首播收视率
  3. 收益模型: 综合收视率+版权费+制作成本决策
  """)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️  演示已中断。")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
