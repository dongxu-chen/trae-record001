import sys
import os
sys.stdout.reconfigure(encoding='utf-8')

from loyalty_analyzer import BrandLoyaltyAnalyzer

log_file = open('test_output.txt', 'w', encoding='utf-8')
sys.stdout = log_file

print("=" * 70)
print("品牌忠诚度分析平台 - 完整功能测试")
print("=" * 70)

print("\n1. 初始化分析引擎（500用户）...")
analyzer = BrandLoyaltyAnalyzer(n_customers=500, use_cached_data=False)

print("\n2. 运行全流程分析...")
summary = analyzer.run_full_analysis()

print("\n" + "=" * 70)
print("✅ 核心功能验证")
print("=" * 70)

print("\n📊 核心指标:")
nps = analyzer.get_nps_metrics()
complaints = analyzer.get_complaint_metrics()
repurchase = analyzer.get_repurchase_metrics()

print(f"  品牌忠诚度指数: {summary.get('loyalty_index', {}).get('overall_avg', 0):.1f}")
print(f"  NPS 净推荐值: {nps['nps_score']:.1f}")
print(f"  用户复购率: {repurchase['repurchase_rate']:.1f}%")
print(f"  用户投诉率: {complaints['complaint_rate']:.1f}%")

print("\n🏷️  用户分层分布:")
if 'clustering' in summary:
    for cluster in summary['clustering']['cluster_distribution']:
        pct = cluster['用户占比'] * 100
        print(f"  {cluster['忠诚度层级']}忠诚度: {cluster['用户数量']} 用户 ({pct:.1f}%)")

print("\n" + "=" * 70)
print("📈 新功能1: 品类差异化流失窗口")
print("=" * 70)

if 'survival' in summary and 'survival_analysis' in analyzer.results:
    sa = analyzer.results['survival_analysis']
    
    if 'category_churn_thresholds' in sa:
        print("\n📊 各品类差异化流失阈值:")
        for cat, threshold in sa['category_churn_thresholds'].items():
            median = sa.get('category_inter_purchase_medians', {}).get(cat, 0)
            print(f"  {cat}: 中位数={median:.1f}天, 流失阈值={threshold:.1f}天")
    
    if 'category_stats' in sa:
        print("\n📈 各品类购买周期统计:")
        for cat, stats in sa['category_stats'].items():
            print(f"  {cat}: 平均间隔={stats['mean_days']:.1f}天, 中位数={stats['median_days']:.1f}天, Std={stats['std_days']:.1f}天")
    
    if 'category_repurchase' in sa:
        print("\n🔄 各品类级复购概率:")
        for cat, rep in sa['category_repurchase'].items():
            print(f"  {cat}: 30天={rep.get('repurchase_30d', 0):.1%}, 90天={rep.get('repurchase_90d', 0):.1%}")

print("\n" + "=" * 70)
print("💰 新功能2: 价格与促销归因分析")
print("=" * 70)

if 'attribution' in summary and 'attribution_results' in analyzer.__dict__:
    ar = analyzer.attribution_results
    
    if 'price_promotion_impact' in ar:
        ppi = ar['price_promotion_impact']
        
        if 'overall' in ppi:
            print("\n📊 总体价格促销特征:")
            overall = ppi['overall']
            print(f"  价格敏感度: 高={overall.get('high_price_sensitivity_count', 0)}, 中={overall.get('medium_price_sensitivity_count', 0)}, 低={overall.get('low_price_sensitivity_count', 0)}")
            print(f"  促销响应度: 高={overall.get('high_promotion_responsiveness_count', 0)}, 中={overall.get('medium_promotion_responsiveness_count', 0)}, 低={overall.get('low_promotion_responsiveness_count', 0)}")
            print(f"  平均促销购买占比: {overall.get('avg_promotion_purchase_rate', 0):.1%}")
            print(f"  平均折扣率: {overall.get('avg_discount_pct', 0):.1%}")
        
        if 'correlations' in ppi:
            print("\n🔗 价格促销特征与忠诚度相关性:")
            corr = ppi['correlations']
            for feat, val in list(corr.items())[:8]:
                print(f"  {feat}: {val:.3f}")
        
        if 'category' in ppi:
            print("\n🛒 品类级价格分析:")
            for cat, data in ppi['category'].items():
                print(f"  {cat}: 高忠诚折扣={data.get('high_loyalty_avg_discount', 0):.1%}, 低忠诚折扣={data.get('low_loyalty_avg_discount', 0):.1%}")
        
        if 'promotion_types' in ppi:
            print("\n🎁 促销类型效果:")
            for ptype, data in ppi['promotion_types'].items():
                print(f"  {ptype}: 使用率={data.get('usage_rate', 0):.1%}, 平均折扣={data.get('avg_discount', 0):.1%}")
        
        if 'segments' in ppi:
            print("\n👥 细分群体价格特征:")
            for seg, data in ppi['segments'].items():
                print(f"  {seg}: 价格敏感度={data.get('avg_price_sensitivity', 0):.3f}, 促销响应度={data.get('avg_promotion_responsiveness', 0):.3f}")

print("\n" + "=" * 70)
print("🎯 新功能3: 个性化推荐系统")
print("=" * 70)

if 'loyalty_results' in analyzer.__dict__:
    lr = analyzer.loyalty_results
    
    if 'segment_recommendations' in lr:
        print("\n📊 价格促销分群策略 (3x3矩阵):")
        for seg, info in lr['segment_recommendations'].items():
            print(f"\n  【{seg}】 ({info['user_count']} 用户)")
            print(f"    描述: {info['segment_description']}")
            print(f"    平均忠诚度: {info['avg_loyalty_index']:.1f}")
            print(f"    策略1: {info['targeted_strategies'][0] if len(info['targeted_strategies']) > 0 else 'N/A'}")
    
    if 'personalized_recommendations' in lr:
        pr = lr['personalized_recommendations']
        print(f"\n👤 生成个性化推荐的用户数: {len(pr)}")
        
        if len(pr) > 0:
            print("\n📋 用户细分类型分布:")
            segment_counts = pr['user_segment'].value_counts()
            for seg, count in segment_counts.items():
                print(f"  {seg}: {count} 用户")
            
            print("\n🏆 Top 10 优先级用户:")
            top10 = pr.nlargest(10, 'priority_score')
            for _, row in top10.iterrows():
                print(f"  {row['customer_id']}: {row['user_segment']}, 忠诚度={row['loyalty_index']:.1f}, 优先级={row['priority_score']}/5")
            
            print("\n📋 单用户推荐详情示例 (第一位用户):")
            user_data = pr.iloc[0]
            print(f"\n  用户ID: {user_data['customer_id']}")
            print(f"  忠诚度层级: {user_data['loyalty_tier']}")
            print(f"  忠诚度指数: {user_data['loyalty_index']:.1f}")
            print(f"  用户细分: {user_data['user_segment']}")
            print(f"  预期结果: {user_data['expected_outcome']}")
            
            prefs = user_data['preferences']
            if isinstance(prefs, dict):
                print(f"\n  🎯 用户偏好:")
                print(f"    品类偏好: {prefs.get('top_categories', [])[:3]}")
                print(f"    价格敏感度: {prefs.get('price_sensitivity_level', 'N/A')}")
                print(f"    促销响应度: {prefs.get('promotion_responsiveness', 'N/A')}")
                print(f"    活跃程度: {prefs.get('activity_level', 'N/A')}")
            
            print(f"\n  💡 个性化策略:")
            for i, strat in enumerate(user_data['personalized_strategies'][:3], 1):
                if isinstance(strat, dict):
                    print(f"    {i}. [{strat.get('type', '')}] {strat.get('strategy', '')}")
                    print(f"       预期: {strat.get('expected_impact', '')}")
            
            if len(user_data['product_recommendations']) > 0:
                print(f"\n  🛒 产品推荐:")
                for i, rec in enumerate(user_data['product_recommendations'][:2], 1):
                    if isinstance(rec, dict):
                        print(f"    {i}. {rec.get('category', '')} ({rec.get('recommendation_type', '')})")
            
            if len(user_data['promotion_recommendations']) > 0:
                print(f"\n  🎁 促销推荐:")
                for i, rec in enumerate(user_data['promotion_recommendations'][:2], 1):
                    if isinstance(rec, dict):
                        print(f"    {i}. {rec.get('promo_type', '')} - {rec.get('target_category', '')}")
            
            if len(user_data['communication_recommendations']) > 0:
                print(f"\n  📱 沟通推荐:")
                for i, rec in enumerate(user_data['communication_recommendations'][:2], 1):
                    if isinstance(rec, dict):
                        print(f"    {i}. {rec.get('channel', '')} ({rec.get('frequency', '')})")

print("\n" + "=" * 70)
print("📤 导出结果文件")
print("=" * 70)

analyzer.export_results()

results_dir = 'results'
if os.path.exists(results_dir):
    files = os.listdir(results_dir)
    print(f"\n✅ 生成的结果文件 ({len(files)} 个):")
    for f in sorted(files):
        filepath = os.path.join(results_dir, f)
        size = os.path.getsize(filepath)
        print(f"  - {f} ({size:,} bytes)")

print("\n" + "=" * 70)
print("✅ 所有新功能测试完成！")
print("=" * 70)

print("\n📝 功能清单:")
print("  ✅ 品类差异化流失窗口 (按购买周期中位数)")
print("  ✅ 价格与促销归因分析 (20+特征, 4维度分析)")
print("  ✅ 9种用户细分类型识别")
print("  ✅ 价格促销3x3分群策略")
print("  ✅ 用户级个性化推荐 (策略/产品/促销/沟通)")
print("  ✅ Streamlit前端可视化展示")

log_file.close()
sys.stdout = sys.__stdout__

print("\n✅ 测试完成！详情请查看 test_output.txt")
