import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_data_collector():
    print("=" * 50)
    print("测试数据采集模块...")
    print("=" * 50)
    
    from src.data_collector import CloudResourceDataCollector
    
    collector = CloudResourceDataCollector("aws")
    data = collector.get_all_data()
    
    print(f"✓ 历史成本数据: {len(data['historical_costs'])} 条记录")
    print(f"✓ 实例数据: {len(data['instances'])} 个实例")
    print(f"✓ EBS卷数据: {len(data['ebs_volumes'])} 个卷")
    print(f"✓ 预留实例推荐: {len(data['reservation_recs']['recommendations'])} 条")
    
    return data

def test_cost_analyzer(data):
    print("\n" + "=" * 50)
    print("测试成本分析模块...")
    print("=" * 50)
    
    from src.cost_analyzer import CostAnalyzer
    
    analyzer = CostAnalyzer(data)
    
    cost_summary = analyzer.get_cost_summary()
    print(f"✓ 总成本: ${cost_summary.get('total_cost', 0):,.2f}")
    print(f"✓ 近30天成本: ${cost_summary.get('last_30d_cost', 0):,.2f}")
    print(f"✓ 日均成本: ${cost_summary.get('daily_avg_30d', 0):,.2f}")
    
    util_analysis = analyzer.analyze_instance_utilization()
    print(f"✓ 运行中实例: {util_analysis.get('total_running', 0)}")
    print(f"✓ 未充分利用实例: {util_analysis.get('underutilized_count', 0)}")
    print(f"✓ 空闲实例: {util_analysis.get('idle_count', 0)}")
    print(f"✓ 平均利用率: {util_analysis.get('avg_utilization', 0):.1f}%")
    
    storage_analysis = analyzer.analyze_storage_optimization()
    print(f"✓ 存储总量: {storage_analysis.get('total_storage_gb', 0):,.0f} GB")
    print(f"✓ 未使用存储: {storage_analysis.get('unused_storage_gb', 0):,.0f} GB")
    
    insights = analyzer.generate_cost_insights()
    print(f"✓ 成本洞察: {len(insights)} 条")
    
    return analyzer

def test_optimizer(data):
    print("\n" + "=" * 50)
    print("测试优化算法模块...")
    print("=" * 50)
    
    from src.optimizer import CloudOptimizer, MultiGranularSampler, SavingsPlanAnalyzer, BusinessImpactAnalyzer
    
    optimizer = CloudOptimizer(data)
    
    print("\n--- 多粒度采样分析 ---")
    mg_analysis = optimizer.get_multi_granular_analysis()
    print(f"✓ 总采样点数: {mg_analysis.get('total_samples', 0)}")
    print(f"✓ 峰值点数量: {mg_analysis.get('peak_count', 0)}")
    print(f"✓ 按粒度采样: {mg_analysis.get('samples_by_granularity', {})}")
    peak_features = mg_analysis.get('peak_features', {})
    if peak_features:
        print(f"✓ 峰值P99: ${peak_features.get('peak_99th', 0):,.2f}")
        print(f"✓ 峰值/均值比: {peak_features.get('peak_mean_ratio', 0):.2f}x")
        print(f"✓ 波动性: {peak_features.get('volatility', 0):.2f}")
        print(f"✓ 突增评分: {peak_features.get('burst_score', 0):.2f}")
    
    print("\n--- 业务影响分析 ---")
    impact_analyzer = BusinessImpactAnalyzer()
    impact_test = impact_analyzer.calculate_business_impact(
        environment='production',
        resource_type='database',
        user_traffic_level='high',
        redundancy_count=3
    )
    print(f"✓ 生产数据库影响: {impact_test['impact_level']} ({impact_test['impact_score']})")
    
    print("\n--- 节省计划灵活性分析 ---")
    sp_analyzer = SavingsPlanAnalyzer()
    flex_score = sp_analyzer.calculate_flexibility_score(
        hourly_pattern=np.random.normal(0.7, 0.1, 24),
        instance_age_days=120,
        workload_type='production'
    )
    print(f"✓ 灵活性评分: {flex_score:.2f}")
    
    purchase_rec = sp_analyzer.recommend_purchase_type(
        flexibility_score=flex_score,
        utilization_rate=0.85,
        hourly_on_demand_cost=0.5
    )
    print(f"✓ 推荐购买类型: {purchase_rec['type']}")
    print(f"✓ 推荐理由: {purchase_rec['reason']}")
    
    print("\n--- 优化推荐 ---")
    all_recs = optimizer.generate_all_recommendations()
    print(f"✓ 总推荐数量: {len(all_recs['all_recommendations'])}")
    print(f"✓ 月度潜在节省: ${all_recs['total_monthly_savings']:,.2f}")
    print(f"✓ 年度潜在节省: ${all_recs['total_annual_savings']:,.2f}")
    
    print(f"  - 终止资源: {all_recs['count_by_type']['terminate']} 条")
    print(f"  - 实例降配: {all_recs['count_by_type']['downsize']} 条")
    print(f"  - 存储优化: {all_recs['count_by_type']['storage']} 条")
    print(f"  - 预留实例: {all_recs['count_by_type']['reserve']} 条")
    print(f"  - 节省计划: {all_recs['count_by_type'].get('savings_plan', 0)} 条")
    
    print(f"\n✓ 低业务影响: {len(all_recs['by_business_impact']['low'])} 项")
    print(f"✓ 中业务影响: {len(all_recs['by_business_impact']['medium'])} 项")
    print(f"✓ 高业务影响: {len(all_recs['by_business_impact']['high'])} 项")
    print(f"✓ 低灵活性推荐(按需): {len(all_recs['low_flexibility_recommendations'])} 项")
    
    if all_recs['all_recommendations']:
        top_rec = all_recs['all_recommendations'][0]
        print(f"\n✓ Top推荐优先级: {top_rec.priority_score}")
        print(f"  业务影响: {top_rec.business_impact} ({top_rec.business_impact_score})")
        print(f"  灵活性评分: {top_rec.flexibility_score}")
    
    execution_plan = optimizer.generate_execution_plan(all_recs['all_recommendations'])
    print(f"\n✓ 立即执行: {len(execution_plan['immediate']['items'])} 项, ${execution_plan['immediate']['monthly_savings']:,.2f}/月")
    print(f"  平均影响分: {execution_plan['immediate']['avg_impact_score']:.2f}")
    print(f"✓ 短期计划: {len(execution_plan['short_term']['items'])} 项, ${execution_plan['short_term']['monthly_savings']:,.2f}/月")
    print(f"  平均影响分: {execution_plan['short_term']['avg_impact_score']:.2f}")
    print(f"✓ 长期规划: {len(execution_plan['long_term']['items'])} 项, ${execution_plan['long_term']['monthly_savings']:,.2f}/月")
    print(f"  平均影响分: {execution_plan['long_term']['avg_impact_score']:.2f}")
    
    roi = optimizer.calculate_roi(all_recs['all_recommendations'])
    print(f"\n✓ 投资回收期: {roi['payback_period']}")
    print(f"✓ 首年净节省: ${roi['first_year_net_savings']:,.2f}")
    print(f"✓ 平均灵活性评分: {roi['avg_flexibility_score']:.2f}")
    print(f"✓ 平均业务影响分: {roi['avg_business_impact_score']:.2f}")
    
    return optimizer

def test_forecasting(data):
    print("\n" + "=" * 50)
    print("测试时序预测模块...")
    print("=" * 50)
    
    from src.forecasting import CostForecaster
    
    forecaster = CostForecaster(data['historical_costs'])
    
    forecast_result = forecaster.forecast_prophet(periods=90)
    print(f"✓ 预测方法: {forecast_result.get('method', 'N/A')}")
    print(f"✓ 预测天数: {len(forecast_result.get('forecast_dates', []))}")
    print(f"✓ 预测周期总成本: ${forecast_result.get('total_forecast_period', 0):,.2f}")
    print(f"✓ 预测准确率: {forecast_result.get('accuracy', 0):.1f}%")
    
    run_rate = forecaster.calculate_run_rate()
    print(f"✓ 月度运行率: ${run_rate.get('monthly_run_rate', 0):,.2f}")
    print(f"✓ 年度运行率: ${run_rate.get('annual_run_rate', 0):,.2f}")
    
    anomalies = forecaster.detect_anomalies()
    print(f"✓ 异常点数量: {anomalies.get('total_anomalies', 0)}")
    
    return forecaster

def main():
    print("\n" + "🚀" * 25)
    print("云资源成本优化推荐引擎 - 模块测试")
    print("🚀" * 25 + "\n")
    
    try:
        data = test_data_collector()
        test_cost_analyzer(data)
        test_optimizer(data)
        test_forecasting(data)
        
        print("\n" + "✅" * 25)
        print("所有模块测试通过！")
        print("✅" * 25)
        print("\n可以运行 'streamlit run app.py' 启动Web界面。")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
