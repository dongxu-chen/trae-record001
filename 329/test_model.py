import sys
import traceback
import numpy as np

def test_all_modules():
    print("=" * 60)
    print("商品价格弹性分析模型 - 功能测试")
    print("=" * 60)
    
    tests_passed = 0
    tests_failed = 0
    
    df_raw = None
    df_processed = None
    model = None
    results = None
    elasticity_df = None
    impact_data = None
    optimal_pricing = None
    promo_simulator = None
    simulation_results = None
    
    try:
        print("\n[1/9] 测试数据生成模块...")
        from data_generator import generate_historical_sales_data, preprocess_data, create_price_bins
        
        df_raw = generate_historical_sales_data(
            base_price=100.0,
            base_demand=500,
            price_elasticity=-2.5,
            n_periods=365
        )
        print(f"  OK 生成数据成功: {len(df_raw)} 行, {len(df_raw.columns)} 列")
        
        df_processed = preprocess_data(df_raw)
        print(f"  OK 数据预处理成功: {len(df_processed)} 行, {len(df_processed.columns)} 列")
        
        df_binned, bin_stats = create_price_bins(df_processed)
        print(f"  OK 价格分箱成功: {len(bin_stats)} 个价格区间")
        tests_passed += 1
        
    except Exception as e:
        print(f"  FAIL 数据生成模块测试失败: {e}")
        traceback.print_exc()
        tests_failed += 1
    
    if df_processed is not None:
        try:
            print("\n[2/9] 测试Logit弹性模型模块（促销解耦 + Bootstrap）...")
            from logit_elasticity_model import PriceElasticityModel
            
            model = PriceElasticityModel(
                threshold_quantile=0.5,
                decouple_promotion=True,
                n_bootstrap=500,
                confidence_level=0.95
            )
            results = model.fit(df_processed, feature_set='full')
            
            print(f"  OK 模型训练成功")
            print(f"  - 准确率: {results['metrics']['accuracy']:.4f}")
            print(f"  - AUC: {results['metrics']['roc_auc']:.4f}")
            print(f"  - 高销量阈值: {results['sales_threshold']:.0f}")
            print(f"  - 促销解耦: {'已启用' if model.decouple_promotion else '未启用'}")
            
            if model.bootstrap_results is not None:
                print(f"  OK Bootstrap采样完成: {model.n_bootstrap} 次重采样")
                ci_non_promo = model.bootstrap_results.get('elasticity_non_promo_ci', {})
                ci_promo = model.bootstrap_results.get('elasticity_promo_ci', {})
                
                def format_val(v):
                    return f"{v:.3f}" if v is not None and not np.isnan(v) else "N/A"
                
                print(f"  - 非促销期弹性 CI: [{format_val(ci_non_promo.get('ci_lower'))}, {format_val(ci_non_promo.get('ci_upper'))}]")
                print(f"  - 促销期弹性 CI: [{format_val(ci_promo.get('ci_lower'))}, {format_val(ci_promo.get('ci_upper'))}]")
            
            elasticity_df = model.calculate_price_elasticity(df_processed)
            print(f"  OK 弹性计算成功: {len(elasticity_df)} 个价格点")
            print(f"  - 平均弹性: {elasticity_df['point_elasticity'].mean():.3f}")
            
            if 'is_promotion' in elasticity_df.columns:
                promo_elasticity = elasticity_df[elasticity_df['is_promotion'] == 1]['point_elasticity'].mean()
                non_promo_elasticity = elasticity_df[elasticity_df['is_promotion'] == 0]['point_elasticity'].mean()
                print(f"  - 促销期平均弹性: {promo_elasticity:.3f}")
                print(f"  - 非促销期平均弹性: {non_promo_elasticity:.3f}")
            
            if 'prob_ci_lower' in elasticity_df.columns:
                print(f"  OK 置信区间计算成功")
            
            elasticity_summary = model.get_elasticity_summary(elasticity_df)
            print(f"  OK 弹性摘要计算成功")
            print(f"  - 单位弹性价格: {elasticity_summary['unitary_elasticity_price']:.2f} 元")
            
            tests_passed += 1
            
        except Exception as e:
            print(f"  FAIL Logit弹性模型测试失败: {e}")
            traceback.print_exc()
            tests_failed += 1
    else:
        print("\n[2/9] 测试Logit弹性模型模块...")
        print("  FAIL 跳过: 数据预处理失败")
        tests_failed += 1
    
    if model is not None:
        try:
            print("\n[3/9] 测试价格影响预测...")
            impact_data = model.predict_sales_impact(
                df_processed,
                base_price=100.0,
                price_change_pct=-0.10
            )
            print(f"  OK 销售影响预测成功")
            print(f"  - 降价10% 预计销量变化: {impact_data['sales_change_pct']*100:+.1f}%")
            print(f"  - 降价10% 预计收入变化: {impact_data['revenue_change_pct']*100:+.1f}%")
            
            tests_passed += 1
            
        except Exception as e:
            print(f"  FAIL 价格影响预测测试失败: {e}")
            traceback.print_exc()
            tests_failed += 1
    else:
        print("\n[3/9] 测试价格影响预测...")
        print("  FAIL 跳过: 模型训练失败")
        tests_failed += 1
    
    if model is not None:
        try:
            print("\n[4/9] 测试最优定价模块（支持Bootstrap CI）...")
            from optimal_pricing import OptimalPricing
            
            optimal_pricing = OptimalPricing(
                model=model,
                df=df_processed,
                variable_cost=30.0,
                fixed_cost=10000.0
            )
            
            profit_opt = optimal_pricing.find_optimal_price(objective='profit')
            print(f"  OK 利润最优价格计算成功: {profit_opt['optimal_price']:.2f} 元")
            print(f"  - 最优利润: {profit_opt['optimal_profit']:,.0f} 元")
            print(f"  - 利润提升: {profit_opt['profit_improvement_pct']:.1f}%")
            
            sensitivity_matrix = optimal_pricing.calculate_price_sensitivity_matrix()
            print(f"  OK 价格敏感度矩阵计算成功: {len(sensitivity_matrix)} 个场景")
            
            segment_analysis = optimal_pricing.analyze_price_segmentation()
            print(f"  OK 价格区间分析成功: {len(segment_analysis)} 个区间")
            
            pricing_recs = optimal_pricing.generate_pricing_recommendations()
            print(f"  OK 定价建议生成成功: {len(pricing_recs['recommendations'])} 条建议")
            
            tests_passed += 1
            
        except Exception as e:
            print(f"  FAIL 最优定价模块测试失败: {e}")
            traceback.print_exc()
            tests_failed += 1
    else:
        print("\n[4/9] 测试最优定价模块...")
        print("  FAIL 跳过: 模型训练失败")
        tests_failed += 1
    
    if model is not None:
        try:
            print("\n[5/9] 测试促销模拟模块（含延后效应）...")
            from promotion_simulation import PromotionSimulator
            
            promo_simulator = PromotionSimulator(
                model=model,
                df=df_processed,
                base_price=100.0,
                variable_cost=30.0
            )
            
            promo_result = promo_simulator.simulate_promotion(
                discount_pct=0.20,
                duration_days=7,
                strategy='direct_discount',
                include_post_promo=True
            )
            print(f"  OK 促销模拟成功（含延后效应）")
            print(f"  - 销量提升: {promo_result['sales_lift_pct']*100:+.1f}%")
            print(f"  - 毛利润变化: {promo_result['profit_change']:,.0f} 元")
            print(f"  - 促销后损失: {promo_result.get('post_promo_loss', 0):,.0f} 元")
            print(f"  - 净利润变化: {promo_result.get('net_profit_change', 0):,.0f} 元")
            print(f"  - ROI: {promo_result['roi']:.2f}")
            
            simulation_results = promo_simulator.run_multiple_simulations(
                discount_range=(0.05, 0.30),
                duration_range=(3, 14),
                n_discounts=4,
                n_durations=3
            )
            print(f"  OK 多场景模拟成功: {len(simulation_results)} 个模拟")
            
            optimal_promo = promo_simulator.find_optimal_promotion(simulation_results, 'profit')
            print(f"  OK 最优促销方案找到: {optimal_promo['best_promotion']['strategy']}")
            
            promo_thresholds = promo_simulator.calculate_promotion_thresholds()
            print(f"  OK 促销阈值计算成功")
            print(f"  - 最低有效折扣: {promo_thresholds['min_effective_discount_pct']:.1f}%")
            print(f"  - 最优折扣: {promo_thresholds['optimal_discount_pct']:.1f}%")
            
            tests_passed += 1
            
        except Exception as e:
            print(f"  FAIL 促销模拟模块测试失败: {e}")
            traceback.print_exc()
            tests_failed += 1
    else:
        print("\n[5/9] 测试促销模拟模块...")
        print("  FAIL 跳过: 模型训练失败")
        tests_failed += 1
    
    if elasticity_df is not None and results is not None and impact_data is not None and simulation_results is not None:
        try:
            print("\n[6/9] 测试可视化模块（含置信区间和Bootstrap）...")
            from visualization import (
                plot_price_sales_scatter,
                plot_elasticity_curve,
                plot_feature_importance,
                plot_sales_impact,
                plot_promotion_simulation,
                plot_bootstrap_distribution,
                plot_post_promotion_effect,
                plot_promotion_timeline
            )
            
            fig1 = plot_price_sales_scatter(df_processed, interactive=True)
            print(f"  OK 价格销量散点图生成成功")
            
            fig2 = plot_elasticity_curve(elasticity_df, interactive=True, show_ci=True)
            print(f"  OK 弹性曲线生成成功（含置信区间）")
            
            fig3 = plot_feature_importance(results['feature_importance'], interactive=True)
            print(f"  OK 特征重要性图生成成功")
            
            fig4 = plot_sales_impact(impact_data, interactive=True)
            print(f"  OK 销售影响图生成成功")
            
            fig5 = plot_promotion_simulation(simulation_results, interactive=True)
            print(f"  OK 促销模拟图生成成功")
            
            if model.bootstrap_results is not None:
                fig6 = plot_bootstrap_distribution(model.bootstrap_results, interactive=True)
                print(f"  OK Bootstrap分布图生成成功")
            
            if 'post_promo_data' in promo_result and promo_result['post_promo_data'] is not None:
                fig7 = plot_post_promotion_effect(promo_result['post_promo_data'], interactive=True)
                print(f"  OK 促销后效应图生成成功")
            
            timeline_df = promo_simulator.simulate_promotion_timeline(
                discount_pct=0.20,
                duration_days=7
            )
            fig8 = plot_promotion_timeline(timeline_df, interactive=True)
            print(f"  OK 促销时间线图生成成功")
            
            tests_passed += 1
            
        except Exception as e:
            print(f"  FAIL 可视化模块测试失败: {e}")
            traceback.print_exc()
            tests_failed += 1
    else:
        print("\n[6/9] 测试可视化模块...")
        print("  FAIL 跳过: 前置测试失败")
        tests_failed += 1
    
    if promo_simulator is not None:
        try:
            print("\n[7/9] 测试促销时间线模拟...")
            timeline_df = promo_simulator.simulate_promotion_timeline(
                discount_pct=0.20,
                duration_days=7
            )
            print(f"  OK 促销时间线模拟成功: {len(timeline_df)} 天数据")
            print(f"  - 促销前: {(timeline_df['period']=='促销前').sum()} 天")
            print(f"  - 促销中: {(timeline_df['period']=='促销中').sum()} 天")
            print(f"  - 促销后: {(timeline_df['period']=='促销后').sum()} 天")
            
            tests_passed += 1
            
        except Exception as e:
            print(f"  FAIL 促销时间线模拟测试失败: {e}")
            traceback.print_exc()
            tests_failed += 1
    else:
        print("\n[7/9] 测试促销时间线模拟...")
        print("  FAIL 跳过: 促销模拟模块测试失败")
        tests_failed += 1
    
    if promo_simulator is not None and simulation_results is not None:
        try:
            print("\n[8/9] 测试促销策略分析...")
            promo_analysis = promo_simulator.analyze_promotion_strategies(simulation_results)
            print(f"  OK 促销策略分析成功")
            print(f"  - 策略对比: {len(promo_analysis['strategy_comparison'])} 种策略")
            print(f"  - 建议数量: {len(promo_analysis['recommendations'])} 条")
            
            tests_passed += 1
            
        except Exception as e:
            print(f"  FAIL 促销策略分析测试失败: {e}")
            traceback.print_exc()
            tests_failed += 1
    else:
        print("\n[8/9] 测试促销策略分析...")
        print("  FAIL 跳过: 前置测试失败")
        tests_failed += 1
    
    if promo_simulator is not None:
        try:
            print("\n[9/9] 测试促销延后效应敏感性分析...")
            
            sensitivity = promo_simulator._analyze_post_promo_sensitivity()
            print(f"  OK 延后效应敏感性分析成功")
            print(f"  - 推荐促销周期: {sensitivity['optimal_duration']} 天")
            print(f"  - 推荐折扣力度: {sensitivity['optimal_discount']*100:.0f}%")
            print(f"  - 分析场景数: {len(sensitivity['sensitivity_data'])} 个")
            
            tests_passed += 1
            
        except Exception as e:
            print(f"  FAIL 延后效应敏感性分析测试失败: {e}")
            traceback.print_exc()
            tests_failed += 1
    else:
        print("\n[9/12] 测试促销延后效应敏感性分析...")
        print("  FAIL 跳过: 前置测试失败")
        tests_failed += 1
    
    try:
        print("\n[10/12] 测试交叉弹性分析模块...")
        from cross_elasticity import CrossElasticityAnalyzer
        from data_generator import generate_multi_product_sales_data, preprocess_multi_product_data
        
        df_multi_raw = generate_multi_product_sales_data(
            n_products=5,
            n_periods=180
        )
        print(f"  OK 多商品数据生成成功: {len(df_multi_raw)} 行, {df_multi_raw['product_id'].nunique()} 个商品")
        
        df_multi_processed = preprocess_multi_product_data(df_multi_raw)
        print(f"  OK 多商品数据预处理成功: {len(df_multi_processed)} 行")
        
        cross_analyzer = CrossElasticityAnalyzer(
            n_bootstrap=200,
            confidence_level=0.95
        )
        cross_results = cross_analyzer.fit(df_multi_processed)
        print(f"  OK 交叉弹性模型训练成功")
        
        if 'cross_elasticity_matrix' in cross_results:
            print(f"  - 交叉弹性矩阵: {cross_results['cross_elasticity_matrix'].shape}")
        if 'significant_cross_pairs' in cross_results and len(cross_results['significant_cross_pairs']) > 0:
            print(f"  - 显著交叉关系: {len(cross_results['significant_cross_pairs'])} 对")
        
        product_ids = sorted(df_multi_processed['product_id'].unique())
        cross_impact = cross_analyzer.simulate_price_change_impact(
            source_product_id=product_ids[0],
            price_change_pct=-0.10
        )
        print(f"  OK 调价影响模拟成功: {len(cross_impact)} 个商品受影响")
        print(f"  - 总销量变化: {cross_impact['expected_sales_change'].sum():+.0f} 件")
        
        heatmap_data = cross_analyzer.get_elasticity_heatmap_data()
        print(f"  OK 热力图数据生成成功")
        
        tests_passed += 1
        
    except Exception as e:
        print(f"  FAIL 交叉弹性分析测试失败: {e}")
        traceback.print_exc()
        tests_failed += 1
    
    if model is not None:
        try:
            print("\n[11/12] 测试动态定价模拟模块...")
            from dynamic_pricing import DynamicPricingSimulator, PricingStrategyType
            
            dynamic_simulator = DynamicPricingSimulator(
                product_model=model,
                cross_analyzer=cross_analyzer if 'cross_analyzer' in locals() else None,
                variable_cost=50.0,
                fixed_cost=10000.0
            )
            print(f"  OK 动态定价模拟器初始化成功")
            
            default_strategies = dynamic_simulator.create_default_strategies(
                base_price=100.0,
                product_id=0
            )
            print(f"  OK 默认策略生成成功: {len(default_strategies)} 个策略")
            
            test_strategy = next(s for s in default_strategies 
                                if s.strategy_type == PricingStrategyType.FIXED_PRICE)
            single_result = dynamic_simulator.simulate_strategy(
                df_processed,
                test_strategy,
                n_days=30
            )
            print(f"  OK 单策略模拟成功")
            print(f"  - 总收益: {single_result['comparison']['total_revenue']:,.0f} 元")
            print(f"  - 总利润: {single_result['comparison']['total_profit']:,.0f} 元")
            
            compare_result = dynamic_simulator.compare_strategies(
                df_processed,
                default_strategies[:3],
                n_days=30
            )
            print(f"  OK 多策略对比成功: {len(compare_result['comparison_summary'])} 个策略")
            print(f"  - 最优策略: {compare_result['best_strategy']}")
            
            tests_passed += 1
            
        except Exception as e:
            print(f"  FAIL 动态定价模拟测试失败: {e}")
            traceback.print_exc()
            tests_failed += 1
    else:
        print("\n[11/12] 测试动态定价模拟模块...")
        print("  FAIL 跳过: 前置模型训练失败")
        tests_failed += 1
    
    try:
        print("\n[12/12] 测试价格阈值检测模块...")
        from price_threshold import PriceThresholdDetector
        
        detector = PriceThresholdDetector(
            n_clusters=4,
            min_bootstrap_samples=100,
            confidence_level=0.95
        )
        print(f"  OK 阈值检测器初始化成功")
        
        threshold_results = detector.detect_thresholds(
            df_processed,
            price_col='effective_price',
            sales_col='sales_quantity',
            method='combined'
        )
        print(f"  OK 阈值检测完成")
        
        thresholds = threshold_results.get('combined', {}).get('thresholds', [])
        print(f"  - 检测到阈值数: {len(thresholds)} 个")
        for t in thresholds[:3]:
            print(f"    * {t['threshold_price']:.0f} 元 (置信度: {t.get('confidence', 0):.0%})")
        
        price_segments = detector.price_segments
        if price_segments is not None and len(price_segments) > 0:
            print(f"  OK 价格区间划分成功: {len(price_segments)} 个区间")
        
        recommendations = detector.get_threshold_recommendations()
        print(f"  OK 定价建议生成成功")
        if recommendations['optimal_price_segment']:
            opt = recommendations['optimal_price_segment']
            print(f"  - 最优定价区间: {opt['price_range_lower']:.0f} - {opt['price_range_upper']:.0f} 元")
        
        segment_data = detector.get_segment_comparison_data()
        print(f"  OK 区间对比数据生成成功")
        
        tests_passed += 1
        
    except Exception as e:
        print(f"  FAIL 价格阈值检测测试失败: {e}")
        traceback.print_exc()
        tests_failed += 1
    
    print("\n" + "=" * 60)
    print(f"测试完成: {tests_passed}/{tests_passed + tests_failed} 通过")
    print("=" * 60)
    
    if tests_failed > 0:
        print(f"\n[FAIL] 有 {tests_failed} 个测试失败，请检查错误信息")
        return False
    else:
        print("\n[PASS] 所有测试通过！模型功能正常。")
        return True

if __name__ == "__main__":
    success = test_all_modules()
    sys.exit(0 if success else 1)
