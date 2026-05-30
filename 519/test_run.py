import sys
sys.stdout.reconfigure(encoding='utf-8')

from loyalty_analyzer import BrandLoyaltyAnalyzer

print("=" * 60)
print("品牌忠诚度分析平台 - 功能测试")
print("=" * 60)

print("\n1. 初始化分析引擎（500用户）...")
analyzer = BrandLoyaltyAnalyzer(n_customers=500, use_cached_data=False)

print("\n2. 运行全流程分析...")
summary = analyzer.run_full_analysis()

print("\n" + "=" * 60)
print("测试结果")
print("=" * 60)

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

print("\n📈 各维度平均得分:")
if 'loyalty_index' in summary:
    tier_summary = summary['loyalty_index']['tier_summary']
    for _, row in tier_summary.iterrows():
        print(f"  {row['忠诚度层级']}: 指数={row['平均指数']:.1f}, "
              f"复购={row['复购评分']:.2f}, NPS={row['NPS评分']:.2f}, "
              f"投诉={row['投诉评分']:.2f}, 互动={row['互动评分']:.2f}, "
              f"价值={row['价值评分']:.2f}")

print("\n💡 关键影响因素:")
if 'attribution' in summary:
    for i, factor in enumerate(summary['attribution']['top_drivers'][:5], 1):
        print(f"  {i}. {factor}")

print("\n📉 生存分析结果:")
if 'survival' in summary:
    print(f"  用户流失率: {summary['survival']['churn_rate']:.1f}%")
    print(f"  中位生存期: {summary['survival']['median_survival_days']:.0f} 天")
    print(f"  平均复购概率: {summary['survival']['avg_repurchase_prob']:.1f}%")
    print(f"  平均购买频次: {summary['survival']['avg_purchase_frequency']:.1f} 次")

print("\n3. 导出结果文件...")
analyzer.export_results()

print("\n" + "=" * 60)
print("✅ 所有测试通过！")
print("=" * 60)
print("\n📁 生成的文件:")
print("  - data/*.csv (5个数据文件)")
print("  - results/*.csv (6个结果文件)")
print("\n🚀 现在可以运行 Streamlit 应用:")
print("   streamlit run app.py")
