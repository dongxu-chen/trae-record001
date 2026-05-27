import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.data_generator import (
    generate_customer_profiles,
    generate_transaction_history,
    generate_behavior_logs,
    prepare_model_data
)
from src.bg_nbd_model import BGNBDModel
from src.gamma_gamma_model import GammaGammaModel
from src.ltv_analysis import LTVAnalyzer
from src.strategy_engine import StrategyEngine
from src.marketing_simulator import MarketingSimulator
from src.change_detector import ChangeDetector
from src.realtime_updater import RealtimeUpdater


def run_full_analysis(n_customers=500, future_months=12, n_segments=4, discount_rate=0.01, 
                       churn_threshold=0.3, use_threshold_segmentation=False, 
                       segment_thresholds=None):
    print("=" * 60)
    print("客户生命周期价值预测系统 - 分析报告")
    print("=" * 60)
    print()
    
    print("📊 步骤1: 生成模拟数据...")
    profiles = generate_customer_profiles(n_customers=n_customers)
    transactions = generate_transaction_history(profiles)
    behavior_logs = generate_behavior_logs(profiles)
    model_data = prepare_model_data(profiles, transactions, behavior_logs)
    
    print(f"  ✓ 客户画像: {len(profiles)} 条")
    print(f"  ✓ 交易记录: {len(transactions)} 条")
    print(f"  ✓ 行为日志: {len(behavior_logs)} 条")
    print(f"  ✓ 建模数据: {len(model_data)} 条 (剔除无购买记录客户)")
    print()
    
    print("🤖 步骤2: 训练BG/NBD模型...")
    bg_nbd = BGNBDModel()
    bg_nbd.fit(model_data)
    print("  ✓ BG/NBD模型训练完成")
    print(f"    参数: {bg_nbd.get_params()}")
    print()
    
    print("🤖 步骤3: 训练Gamma-Gamma模型...")
    gg = GammaGammaModel()
    gg.fit(model_data)
    print("  ✓ Gamma-Gamma模型训练完成")
    print(f"    参数: {gg.get_params()}")
    print()
    
    print("📈 步骤4: 计算LTV (含再激活概率)...")
    analyzer = LTVAnalyzer(bg_nbd, gg)
    ltv_data = analyzer.calculate_ltv(model_data, future_months=future_months, 
                                     discount_rate=discount_rate, churn_threshold=churn_threshold,
                                     include_reactivation=True)
    print(f"  ✓ LTV计算完成，预测周期: {future_months}个月")
    print(f"  ✓ 再激活概率计算完成，流失阈值: {churn_threshold}")
    
    churned_count = (ltv_data['is_churned'] == True).sum()
    print(f"  ✓ 识别流失客户: {churned_count} 人 ({churned_count/len(ltv_data)*100:.1f}%)")
    print()
    
    report = analyzer.generate_ltv_distribution_report(ltv_data)
    print("📋 LTV分布摘要:")
    print(f"  总客户数: {report['total_customers']:,}")
    print(f"  总预测LTV: ¥{report['total_ltv']:,.2f}")
    print(f"  平均LTV: ¥{report['avg_ltv']:,.2f}")
    print(f"  LTV中位数: ¥{report['median_ltv']:,.2f}")
    print(f"  Top 10%客户贡献: {report['top_10_contribution']*100:.1f}%")
    print(f"  Bottom 50%客户贡献: {report['bottom_50_contribution']*100:.1f}%")
    print()
    
    print("📊 步骤5: 客户分群...")
    if use_threshold_segmentation and segment_thresholds:
        segment_names = ['低价值客户', '中价值客户', '高价值客户'][:len(segment_thresholds) + 1]
        ltv_data, segment_stats = analyzer.segment_customers(
            model_data, ltv_data, thresholds=segment_thresholds, 
            segment_names=segment_names
        )
        print(f"  ✓ 阈值分群完成，阈值: {segment_thresholds}")
    else:
        ltv_data, segment_stats = analyzer.segment_customers(model_data, ltv_data, n_segments=n_segments)
        print(f"  ✓ 聚类分群完成，分为 {n_segments} 个客群")
    print()
    
    print("👥 各客群统计:")
    for _, row in segment_stats.iterrows():
        print(f"  {row['segment_name']}:")
        print(f"    客户数: {row['customer_count']}")
        print(f"    平均LTV: ¥{row['ltv_mean']:,.2f}")
        print(f"    平均购买次数: {row['avg_purchases']:.2f}")
        print(f"    平均客单价: ¥{row['avg_amount']:,.2f}")
        print(f"    平均活跃度: {row['avg_prob_alive']*100:.1f}%")
        print(f"    平均再激活概率: {row['avg_reactivation_prob']*100:.1f}%")
        print(f"    流失率: {row['churn_rate']*100:.1f}%")
        print()
    
    print("🎯 步骤6: 生成策略建议...")
    engine = StrategyEngine()
    churn_warning = engine.generate_churn_warning(ltv_data)
    reactivation_plan = engine.generate_reactivation_plan(ltv_data, segment_stats)
    budget = engine.generate_budget_allocation(segment_stats)
    
    print("⚠️  流失预警:")
    print(f"  风险客户数: {churn_warning['at_risk_count']} ({churn_warning['at_risk_percentage']:.1f}%)")
    print(f"  风险LTV总额: ¥{churn_warning['total_ltv_at_risk']:,.2f}")
    print()
    
    print("🔄 再激活计划:")
    print(f"  总流失客户: {reactivation_plan['total_churned']} 人 ({reactivation_plan['churn_rate']:.1f}%)")
    print(f"  潜在召回价值: ¥{reactivation_plan['total_potential_value']:,.2f}")
    for item in reactivation_plan['priority_list'][:3]:
        print(f"    {item['segment']}: {item['churned_count']}人, 潜在价值 ¥{item['potential_value']:,.2f}")
    print()
    
    print("💰 预算分配建议:")
    for b in budget:
        print(f"  {b['segment']} ({b['strategy_type']}): {b['suggested_budget_pct']:.1f}% 预算 (预计ROI: {b['expected_roi']:.2f})")
    print()
    
    print("🎁 步骤7: 营销活动模拟...")
    marketing = MarketingSimulator(bg_nbd, gg, ltv_data)
    sim_result, campaign_impact = marketing.simulate_marketing_campaign(
        {'name': '春节促销活动', 'coupon_type': '满减券', 'coverage_rate': 0.4, 'duration_months': 3},
        future_months=3
    )
    print(f"  ✓ 营销模拟完成")
    print(f"  活动名称: {campaign_impact['campaign_name']}")
    print(f"  触达人数: {campaign_impact['total_reach']:,}")
    print(f"  LTV增长总额: ¥{campaign_impact['total_ltv_increase']:,.2f}")
    print(f"  预计ROI: {campaign_impact['estimated_roi']:.2f}")
    print()
    
    print("📊 步骤8: 异动分析...")
    detector = ChangeDetector()
    change_report = detector.generate_change_report(ltv_data)
    print(f"  ✓ 异动分析完成")
    print(f"  流失风险客户数: {change_report['churn_risk_count']}")
    print()
    
    print("⚡ 步骤9: 实时更新配置...")
    updater = RealtimeUpdater(bg_nbd, gg, analyzer)
    status = updater.get_update_status()
    print(f"  ✓ 实时更新模块就绪")
    print(f"  模型版本: v{status['model_version']}")
    print()
    
    print("=" * 60)
    print("分析完成！")
    print("=" * 60)
    
    return {
        'profiles': profiles,
        'transactions': transactions,
        'behavior_logs': behavior_logs,
        'model_data': model_data,
        'bg_nbd': bg_nbd,
        'gg': gg,
        'analyzer': analyzer,
        'ltv_data': ltv_data,
        'segment_stats': segment_stats,
        'engine': engine
    }


if __name__ == '__main__':
    results = run_full_analysis(n_customers=500, future_months=12, n_segments=4, 
                               churn_threshold=0.3, use_threshold_segmentation=False)
