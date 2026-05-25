import warnings
warnings.filterwarnings('ignore')
import sys

print("Testing cross_elasticity...")
try:
    from data_generator import generate_multi_product_sales_data, preprocess_multi_product_data
    from cross_elasticity import CrossElasticityAnalyzer
    import numpy as np
    
    df = generate_multi_product_sales_data(n_products=3, n_periods=60)
    df_p = preprocess_multi_product_data(df)
    analyzer = CrossElasticityAnalyzer(n_bootstrap=5)
    result = analyzer.fit(df_p)
    print("  cross_elasticity_matrix:", result['cross_elasticity_matrix'].shape)
    print("  own_elasticities:", len(result['own_elasticities']))
    print("  [OK] cross_elasticity")
except Exception as e:
    print(f"  [FAIL] cross_elasticity: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\nTesting dynamic_pricing...")
try:
    from data_generator import generate_historical_sales_data, preprocess_data
    from logit_elasticity_model import PriceElasticityModel
    from dynamic_pricing import DynamicPricingSimulator, PricingStrategyType
    
    df = generate_historical_sales_data(n_periods=100)
    df_p = preprocess_data(df)
    model = PriceElasticityModel(n_bootstrap=10)
    model.fit(df_p, feature_set='full')
    
    simulator = DynamicPricingSimulator(product_model=model, variable_cost=50)
    strategies = simulator.create_default_strategies(base_price=100)
    print(f"  strategies: {len(strategies)}")
    
    result = simulator.simulate_strategy(df_p, strategies[0], n_days=7)
    print(f"  simulation days: {len(result['simulation_data'])}")
    print(f"  total_revenue: {result['comparison']['total_revenue']:.0f}")
    print("  [OK] dynamic_pricing")
except Exception as e:
    print(f"  [FAIL] dynamic_pricing: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\nTesting price_threshold...")
try:
    from price_threshold import PriceThresholdDetector
    
    detector = PriceThresholdDetector(n_clusters=3)
    result = detector.detect_thresholds(df_p, method='combined')
    print(f"  kmeans thresholds: {len(result['kmeans']['thresholds'])}")
    print(f"  combined thresholds: {len(result['combined']['thresholds'])}")
    print(f"  price_segments: {len(detector.price_segments)}")
    
    recs = detector.get_threshold_recommendations()
    print(f"  recommendations generated")
    print("  [OK] price_threshold")
except Exception as e:
    print(f"  [FAIL] price_threshold: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*50)
print("[ALL TESTS PASSED]")
print("="*50)
