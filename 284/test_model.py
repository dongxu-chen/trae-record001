import sys
import traceback

def test_imports():
    print("测试导入模块...")
    try:
        import pandas as pd
        import numpy as np
        import statsmodels.api as sm
        from sklearn.linear_model import LogisticRegression
        import matplotlib.pyplot as plt
        print("✅ 基础库导入成功")
        return True
    except Exception as e:
        print(f"❌ 基础库导入失败: {e}")
        return False

def test_data_generator():
    print("\n测试数据生成器...")
    try:
        from data_generator import PromotionDataGenerator
        generator = PromotionDataGenerator(seed=42)
        df = generator.generate_synthetic_data(n_products=50, n_periods=6)
        print(f"✅ 数据生成成功，共 {len(df)} 条记录")
        
        df_did = generator.prepare_did_data(df)
        print(f"✅ DID数据准备成功，列: {list(df_did.columns)}")
        
        df_psm = generator.prepare_psm_data(df)
        print(f"✅ PSM数据准备成功，列: {list(df_psm.columns)}")
        
        actual_lift = generator.calculate_actual_lift(df)
        print(f"✅ 实际提升率计算成功: {actual_lift}")
        
        return df
    except Exception as e:
        print(f"❌ 数据生成器测试失败: {e}")
        traceback.print_exc()
        return None

def test_did_model(df):
    print("\n测试DID模型...")
    try:
        from did_model import DIDModel
        from data_generator import PromotionDataGenerator
        
        generator = PromotionDataGenerator()
        df_did = generator.prepare_did_data(df)
        
        did_model = DIDModel()
        results = did_model.fit(df_did)
        
        print(f"✅ DID模型拟合成功")
        print(f"   - 销售提升率: {results['treatment_effect_pct']:.2f}%")
        print(f"   - p值: {results['p_value']:.4f}")
        print(f"   - 显著: {results['is_significant']}")
        
        parallel_test = did_model.parallel_trend_test(df_did)
        if 'warning_level' in parallel_test:
            print(f"✅ 增强平行趋势检验成功")
            print(f"   - F统计量: {parallel_test['f_statistic']:.4f}")
            print(f"   - p值: {parallel_test['p_value']:.4f}")
            print(f"   - 警告级别: {parallel_test['warning_level']}")
            print(f"   - 事前周期数: {parallel_test['total_pre_periods']}")
            print(f"   - 显著偏离周期数: {parallel_test['significant_violations']}")
        else:
            print(f"✅ 平行趋势检验: {parallel_test}")
        
        return True
    except Exception as e:
        print(f"❌ DID模型测试失败: {e}")
        traceback.print_exc()
        return False

def test_psm_model(df):
    print("\n测试PSM模型...")
    try:
        from psm_model import PSMModel
        from data_generator import PromotionDataGenerator
        
        generator = PromotionDataGenerator()
        df_psm = generator.prepare_psm_data(df)
        
        psm_covariates = [c for c in df_psm.columns if c.startswith(('cat_', 'ch_', 'price_', 'seg_'))]
        print(f"✅ 新增协变量: {len(psm_covariates)} 个类别虚拟变量")
        
        psm_model = PSMModel()
        df_with_ps = psm_model.estimate_propensity_score(df_psm)
        print(f"✅ 倾向性得分估计成功")
        
        matched_data = psm_model.match(df_with_ps, caliper=0.1)
        print(f"✅ 匹配完成，匹配后样本数: {len(matched_data)}")
        
        results = psm_model.calculate_treatment_effect()
        print(f"✅ PSM处理效应计算成功")
        print(f"   - ATT: {results['att_pct']:.2f}%")
        print(f"   - p值: {results['p_value']:.4f}")
        print(f"   - 显著: {results['is_significant']}")
        
        balance_covariates = [
            'base_sales', 'avg_sales_pre', 'sales_trend_pre', 
            'sales_std_pre', 'max_sales_pre', 'min_sales_pre'
        ]
        available_covariates = [c for c in balance_covariates if c in matched_data.columns]
        balance_df = psm_model.balance_check(matched_data, available_covariates)
        print(f"✅ 平衡性检验完成，检查了 {len(balance_df)} 个协变量")
        
        return True
    except Exception as e:
        print(f"❌ PSM模型测试失败: {e}")
        traceback.print_exc()
        return False

def test_prediction_model():
    print("\n测试Bootstrap预测模型...")
    try:
        from prediction_model import PromotionPredictor
        
        predictor = PromotionPredictor(n_bootstrap=100)
        predictor._train_synthetic_model()
        print(f"✅ 预测模型初始化成功")
        
        pred_results = predictor.predict(
            discount=0.2,
            duration=3,
            category='电子产品',
            channel='直播带货',
            price_tier='中价位',
            customer_segment='活跃用户',
            base_sales=5000,
            avg_order_value=200,
            review_score=4.2,
            confidence_level=0.95
        )
        
        print(f"✅ Bootstrap预测完成")
        print(f"   - 预测提升率: {pred_results['predicted_lift']:.2f}%")
        print(f"   - 95%置信区间: [{pred_results['ci_lower']:.2f}%, {pred_results['ci_upper']:.2f}%]")
        print(f"   - 标准差: {pred_results['std_lift']:.2f}%")
        print(f"   - Bootstrap次数: {pred_results['n_bootstrap']}")
        
        return True
    except Exception as e:
        print(f"❌ 预测模型测试失败: {e}")
        traceback.print_exc()
        return False

def test_channel_attribution():
    print("\n测试多渠道归因模型...")
    try:
        from channel_attribution import ChannelAttribution
        
        attribution = ChannelAttribution()
        df = attribution.generate_multi_channel_data(n_products=50, n_periods=8)
        print(f"✅ 多渠道数据生成成功，共 {len(df)} 条记录")
        
        shapley_results = attribution.calculate_shapley_values(df)
        print(f"✅ Shapley值计算成功")
        for ch, pct in shapley_results['shapley_percentage'].items():
            print(f"   - {ch}: {pct:.1f}%")
        
        channel_costs = {
            '线上商城': 5000, '社交媒体': 3000, '线下门店': 8000,
            '邮件营销': 1000, '直播带货': 6000
        }
        roi_results = attribution.calculate_roi(df, channel_costs)
        print(f"✅ ROI计算成功")
        
        interactions = attribution.analyze_channel_interactions(df)
        print(f"✅ 渠道协同效应分析成功，共分析 {len(interactions)} 对渠道组合")
        
        return True
    except Exception as e:
        print(f"❌ 多渠道归因测试失败: {e}")
        traceback.print_exc()
        return False

def test_promotion_fatigue():
    print("\n测试促销疲劳检测...")
    try:
        from promotion_fatigue import PromotionFatigueDetector
        
        detector = PromotionFatigueDetector()
        df = detector.generate_fatigue_data(n_products=50, n_periods=12)
        print(f"✅ 疲劳数据生成成功，共 {len(df)} 条记录")
        
        fatigue_scores = detector.calculate_fatigue_score(df)
        print(f"✅ 疲劳指数计算成功，共分析 {len(fatigue_scores)} 个商品")
        
        high_fatigue = sum(1 for v in fatigue_scores.values() if v['fatigue_level'] == '高疲劳')
        print(f"   - 高疲劳商品数: {high_fatigue}")
        
        sensitivity_decay = detector.analyze_sensitivity_decay(df)
        print(f"✅ 敏感度衰减分析成功")
        for cat, data in sensitivity_decay.get('category', {}).items():
            print(f"   - {cat}: 衰减系数={data['decay_coefficient']:.1f}")
        
        optimal_freq = detector.calculate_optimal_frequency(df)
        print(f"✅ 最优频率计算成功，共 {len(optimal_freq)} 个商品有结果")
        
        recommendations = detector.generate_recommendations(df)
        print(f"✅ 生成了 {len(recommendations)} 条建议")
        
        return True
    except Exception as e:
        print(f"❌ 促销疲劳检测测试失败: {e}")
        traceback.print_exc()
        return False

def test_budget_simulator():
    print("\n测试预算模拟推演...")
    try:
        from budget_simulator import BudgetSimulator
        
        simulator = BudgetSimulator()
        
        sim_results = simulator.run_budget_simulation(
            total_budget=50000,
            n_simulations=100,
            include_fatigue=True
        )
        print(f"✅ 预算模拟完成，共 {sim_results['summary']['n_simulations']} 次模拟")
        print(f"   - 平均利润: ¥{sim_results['summary']['avg_profit']:,.0f}")
        print(f"   - 平均ROI: {sim_results['summary']['avg_roi']:.1f}%")
        
        optimal = simulator.optimize_budget_allocation(
            total_budget=50000,
            target_roi=100
        )
        print(f"✅ 预算优化完成")
        print(f"   - 预期收入: ¥{optimal['expected_revenue']:,.0f}")
        print(f"   - 预期利润: ¥{optimal['expected_profit']:,.0f}")
        print(f"   - 预期ROI: {optimal['expected_roi']:.1f}%")
        
        what_if_results = simulator.what_if_analysis(
            base_scenario={'total_budget': 50000, 'discount': 0.2, 'duration': 3},
            variations={
                'total_budget': [40000, 50000, 60000],
                'discount': [0.15, 0.2, 0.25]
            }
        )
        print(f"✅ 假设分析完成，共 {len(what_if_results)} 个场景")
        
        recommendations = simulator.generate_budget_recommendations(50000)
        print(f"✅ 生成了 {len(recommendations)} 条预算建议")
        
        return True
    except Exception as e:
        print(f"❌ 预算模拟测试失败: {e}")
        traceback.print_exc()
        return False

def main():
    print("=" * 50)
    print("促销活动效果评估模型 - 完整测试套件")
    print("=" * 50)
    
    if not test_imports():
        sys.exit(1)
    
    df = test_data_generator()
    if df is None:
        sys.exit(1)
    
    test_did_model(df)
    test_psm_model(df)
    test_prediction_model()
    test_channel_attribution()
    test_promotion_fatigue()
    test_budget_simulator()
    
    print("\n" + "=" * 50)
    print("所有测试完成！")
    print("=" * 50)

if __name__ == "__main__":
    main()
