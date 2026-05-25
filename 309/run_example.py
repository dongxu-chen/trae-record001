import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

from data import SampleDataGenerator
from models import EnsembleModel
from forecasting import HierarchicalForecaster
from analysis import RampUpAnalyzer
from inventory import SafetyStockCalculator, ReplenishmentPlanner
from visualization import TableauIntegration
from data.feature_engineer import FeatureEngineer

print("="*70)
print("SUPPLY CHAIN DEMAND FORECASTING PLATFORM - EXAMPLE WORKFLOW")
print("="*70)

output_dir = Path('./output/example')
output_dir.mkdir(parents=True, exist_ok=True)

print("\n" + "="*70)
print("STEP 1: GENERATING SAMPLE DATA")
print("="*70)

generator = SampleDataGenerator(seed=42)
data = generator.generate_all(output_dir='./data/sample')

print(f"\nGenerated data:")
print(f"  - Sales: {len(data['sales']):,} records")
print(f"  - Inventory: {len(data['inventory']):,} records")
print(f"  - Promotions: {len(data['promotion']):,} records")
print(f"  - Suppliers: {len(data['supplier']):,} records")
print(f"  - Products: {len(data['product']):,} records")
print(f"  - New Products: {len(data['new_products']):,} records")

print("\n" + "="*70)
print("STEP 2: FEATURE ENGINEERING")
print("="*70)

from data.data_preprocessor import DataPreprocessor

preprocessor = DataPreprocessor()
processed = preprocessor.preprocess_all(data)
merged_df = preprocessor.merge_for_forecasting(processed)

feature_engineer = FeatureEngineer(country_code='CN')
features_df = feature_engineer.create_all_features(merged_df)

print(f"\nFeature engineering complete:")
print(f"  - Total records: {len(features_df):,}")
print(f"  - Features created: {len(feature_engineer.get_feature_columns(features_df))}")
print(f"  - Date range: {features_df['date'].min().date()} to {features_df['date'].max().date()}")

print("\n" + "="*70)
print("STEP 3: SINGLE PRODUCT FORECASTING (Prophet + LightGBM + Ensemble)")
print("="*70)

sample_product = features_df['product_id'].unique()[0]
sample_region = features_df['region'].unique()[0]
sample_warehouse = features_df['warehouse'].unique()[0]

product_data = features_df[
    (features_df['product_id'] == sample_product) &
    (features_df['region'] == sample_region) &
    (features_df['warehouse'] == sample_warehouse)
].copy()

print(f"\nForecasting for: {sample_product} / {sample_region} / {sample_warehouse}")
print(f"Training data: {len(product_data)} days")

train_end = product_data['date'].max() - pd.Timedelta(days=30)
train_df = product_data[product_data['date'] <= train_end]
test_df = product_data[product_data['date'] > train_end]

feature_cols = feature_engineer.get_feature_columns(train_df)

ensemble = EnsembleModel()
valid_split = int(len(train_df) * 0.8)
train_part = train_df.iloc[:valid_split]
valid_part = train_df.iloc[valid_split:]

ensemble.fit(
    train_part,
    feature_cols=feature_cols,
    target_col='quantity',
    valid_df=valid_part,
    product_id=sample_product,
    region=sample_region,
    warehouse=sample_warehouse
)

forecast_horizon = 90
forecast = ensemble.predict(periods=forecast_horizon)

metrics = ensemble.evaluate(test_df)

print(f"\nModel Performance:")
for model_type, metric_values in metrics.items():
    print(f"  {model_type.upper()}:")
    print(f"    - MAPE: {metric_values['mape']:.2f}%")
    print(f"    - RMSE: {metric_values['rmse']:.2f}")
    print(f"    - MAE: {metric_values['mae']:.2f}")

print(f"\nEnsemble Weights: {ensemble.weights}")

forecast_path = output_dir / f'forecast_{sample_product}.csv'
forecast.to_csv(forecast_path, index=False)
print(f"\nForecast saved to: {forecast_path}")

print("\n" + "="*70)
print("STEP 4: FEATURE IMPORTANCE ANALYSIS")
print("="*70)

feature_importance = ensemble.get_feature_importance()
print(f"\nTop 10 Most Important Features:")
print(feature_importance.head(10).to_string(index=False))

fi_path = output_dir / 'feature_importance.csv'
feature_importance.to_csv(fi_path, index=False)

print("\n" + "="*70)
print("STEP 5: RAMP-UP ANALYSIS FOR NEW PRODUCTS")
print("="*70)

ramp_analyzer = RampUpAnalyzer()

ramp_analyzer.analyze_historical_ramps(data['sales'], data['product'])

new_product = data['new_products'].iloc[0]
print(f"\nAnalyzing new product: {new_product['product_name']} ({new_product['product_id']})")
print(f"  Category: {new_product['category']}")
print(f"  Launch Date: {new_product['launch_date']}")
print(f"  Similar Product: {new_product['similar_product_id']}")

ramp_forecast = ramp_analyzer.predict_new_product_ramp(
    new_product.to_dict(),
    similar_products=[new_product['similar_product_id']],
    forecast_days=180
)

ramp_metrics = ramp_analyzer.get_ramp_metrics(ramp_forecast)
print(f"\nRamp-Up Forecast Metrics:")
print(f"  - Total 90-day forecast: {ramp_metrics['total_forecast_90d']:,.0f} units")
print(f"  - Total 180-day forecast: {ramp_metrics['total_forecast_180d']:,.0f} units")
print(f"  - Peak daily demand: {ramp_metrics['peak_daily_demand']:,.0f} units (day {ramp_metrics['peak_day']})")
print(f"  - Growth rate (launch to early): {ramp_metrics['growth_rate_launch_to_early']:.1f}%")
print(f"  - Days to 80% penetration: {ramp_metrics['days_to_80_penetration']} days")

ramp_path = output_dir / f'ramp_up_{new_product["product_id"]}.csv'
ramp_forecast.to_csv(ramp_path, index=False)
print(f"\nRamp-up forecast saved to: {ramp_path}")

print("\n" + "="*70)
print("STEP 6: SAFETY STOCK CALCULATION")
print("="*70)

safety_stock_calc = SafetyStockCalculator()

forecast_for_ss = forecast.copy()
forecast_for_ss['product_id'] = sample_product
forecast_for_ss['region'] = sample_region
forecast_for_ss['warehouse'] = sample_warehouse

safety_stock_df = safety_stock_calc.calculate_for_products(
    data['sales'],
    data['supplier'],
    forecast_df=forecast_for_ss
)

print(f"\nSafety Stock Summary:")
for _, row in safety_stock_df.iterrows():
    print(f"\n  {row['product_id']} at {row['warehouse']}:")
    print(f"    - Avg Daily Demand: {row['avg_daily_demand']:.1f}")
    print(f"    - Demand CV: {row['cv_demand']:.3f}")
    print(f"    - Avg Lead Time: {row['avg_lead_time']:.0f} days")
    print(f"    - Safety Stock: {row['safety_stock_recommended']:.0f} units")
    print(f"    - Reorder Point: {row['reorder_point']:.0f} units")
    print(f"    - Service Level: {row['service_level']*100:.1f}%")
    print(f"    - Days of Coverage: {row['days_of_coverage']:.1f} days")

ss_path = output_dir / 'safety_stock.csv'
safety_stock_df.to_csv(ss_path, index=False)

print("\n" + "="*70)
print("STEP 7: WHAT-IF ANALYSIS FOR SAFETY STOCK")
print("="*70)

base_params = {
    'avg_demand': safety_stock_df.iloc[0]['avg_daily_demand'],
    'std_demand': safety_stock_df.iloc[0]['std_daily_demand'],
    'avg_lead_time': safety_stock_df.iloc[0]['avg_lead_time'],
    'std_lead_time': safety_stock_df.iloc[0]['std_lead_time'],
    'base_safety_stock': safety_stock_df.iloc[0]['safety_stock_recommended']
}

what_if_df = safety_stock_calc.what_if_analysis(base_params)
print(f"\nWhat-If Analysis (Service Level vs Lead Time):")
print(what_if_df[['service_level', 'lead_time_change_days', 'safety_stock',
                 'stockout_risk', 'safety_stock_change_pct']].head(12).to_string(index=False))

whatif_path = output_dir / 'safety_stock_whatif.csv'
what_if_df.to_csv(whatif_path, index=False)

print("\n" + "="*70)
print("STEP 8: REPLENISHMENT PLANNING")
print("="*70)

replenishment_planner = ReplenishmentPlanner()

replenishment_plan = replenishment_planner.generate_replenishment_plan(
    data['sales'],
    data['inventory'],
    forecast_for_ss,
    data['supplier'],
    safety_stock_df,
    horizon_days=90
)

orders = replenishment_plan[replenishment_plan['order_quantity'].fillna(0) > 0]

print(f"\nReplenishment Plan:")
print(f"  - Planning horizon: {replenishment_plan['date'].nunique()} days")
print(f"  - Total orders: {len(orders)}")
print(f"  - Total quantity: {orders['order_quantity'].sum():,.0f} units")
if 'total_cost' in orders.columns:
    print(f"  - Total cost: ${orders['total_cost'].sum():,.2f}")

print(f"\nUpcoming Orders:")
for _, order in orders.head(5).iterrows():
    print(f"  {order['date'].date()}: Order {order['order_quantity']:.0f} units of {order['product_id']} "
          f"(arrival: {order['expected_arrival_date'].date()}) - {order.get('reason', 'Regular')}")

plan_path = output_dir / 'replenishment_plan.csv'
replenishment_plan.to_csv(plan_path, index=False)

print("\n" + "="*70)
print("STEP 9: PURCHASE ORDER GENERATION")
print("="*70)

purchase_orders = replenishment_planner.generate_purchase_orders(
    replenishment_plan,
    start_date=replenishment_plan['date'].min(),
    end_date=replenishment_plan['date'].min() + pd.Timedelta(days=30)
)

if len(purchase_orders) > 0:
    print(f"\nGenerated {len(purchase_orders)} Purchase Orders:")
    for _, po in purchase_orders.iterrows():
        print(f"  {po['po_number']}: {po['product_id']} - {po['order_quantity']:.0f} units "
              f"@ ${po.get('unit_cost', 0):.2f} = ${po.get('total_cost', 0):,.2f}")

    po_path = output_dir / 'purchase_orders.csv'
    purchase_orders.to_csv(po_path, index=False)

print("\n" + "="*70)
print("STEP 10: INVENTORY SIMULATION (MONTE CARLO)")
print("="*70)

simulation_results = replenishment_planner.simulate_stockout_risk(
    replenishment_plan,
    num_simulations=50
)

print(f"\nStockout Risk Simulation Results (50 simulations):")
for _, row in simulation_results.iterrows():
    print(f"\n  {row['product_id']} at {row['warehouse']}:")
    print(f"    - Average stockout days: {row['avg_stockout_days']:.1f}")
    print(f"    - Stockout probability: {row['stockout_probability']*100:.1f}%")
    print(f"    - Achieved service level: {row['service_level']*100:.1f}%")

sim_path = output_dir / 'simulation_results.csv'
simulation_results.to_csv(sim_path, index=False)

print("\n" + "="*70)
print("STEP 11: TABLEAU DATA EXPORT")
print("="*70)

tableau = TableauIntegration()

tableau_forecast = tableau.prepare_forecast_data(forecast, actual_df=test_df)
tableau_inventory = tableau.prepare_inventory_data(
    data['inventory'].head(1000),
    safety_stock_df,
    replenishment_plan
)
tableau_ramp = tableau.prepare_ramp_up_data(ramp_forecast, ramp_analyzer.historical_ramps)

print(f"\nPrepared Tableau datasets:")
print(f"  - Forecast: {len(tableau_forecast):,} records")
print(f"  - Inventory: {len(tableau_inventory):,} records")
print(f"  - Ramp-Up: {len(tableau_ramp):,} records")

output_files = tableau.export_all_for_tableau(
    forecast_df=forecast,
    inventory_df=data['inventory'].head(1000),
    safety_stock_df=safety_stock_df,
    replenishment_df=replenishment_plan,
    ramp_df=ramp_forecast,
    output_dir='./output/example/tableau',
    publish=False
)

print(f"\nExported files:")
for name, path in output_files.items():
    print(f"  - {name}: {path}")

print("\n" + "="*70)
print("STEP 12: COST OPTIMIZATION")
print("="*70)

holding_cost_rate = 0.25
order_cost = 150.0
stockout_cost = 50.0

print(f"\nCost Parameters:")
print(f"  - Holding cost rate: {holding_cost_rate*100:.0f}% per year")
print(f"  - Order cost: ${order_cost:.2f} per order")
print(f"  - Stockout cost: ${stockout_cost:.2f} per unit")

optimized_orders = replenishment_planner.optimize_order_quantities(
    replenishment_plan,
    holding_cost_rate=holding_cost_rate,
    order_cost=order_cost
)

original_total = replenishment_plan[replenishment_plan['order_quantity'] > 0]['order_quantity'].sum()
optimized_total = optimized_orders[optimized_orders['order_quantity'] > 0]['order_quantity'].sum()

print(f"\nOrder Optimization Results:")
print(f"  - Original avg order qty: {replenishment_plan['order_quantity'].mean():.0f}")
print(f"  - Optimized avg order qty: {optimized_orders['order_quantity'].mean():.0f}")
print(f"  - Quantity change: {(optimized_total - original_total)/original_total*100:+.1f}%")

optimized_plan_path = output_dir / 'replenishment_plan_optimized.csv'
optimized_orders.to_csv(optimized_plan_path, index=False)

print("\n" + "="*70)
print("EXECUTION COMPLETE")
print("="*70)

print(f"\nAll output files saved to: {output_dir}/")
print("\nGenerated files:")
for file in sorted(output_dir.glob('*.csv')):
    size = file.stat().st_size / 1024
    print(f"  - {file.name}: {size:.1f} KB")

print("\n" + "="*70)
print("SUMMARY OF KEY METRICS")
print("="*70)

print(f"""
FORECASTING:
  - Product: {sample_product}
  - Test MAPE (Ensemble): {metrics['ensemble']['mape']:.2f}%
  - Forecast Horizon: {forecast_horizon} days

RAMP-UP ANALYSIS:
  - New Product: {new_product['product_id']}
  - 90-Day Forecast: {ramp_metrics['total_forecast_90d']:,.0f} units
  - Peak Demand: {ramp_metrics['peak_daily_demand']:,.0f} units/day

INVENTORY:
  - Safety Stock: {safety_stock_df.iloc[0]['safety_stock_recommended']:.0f} units
  - Reorder Point: {safety_stock_df.iloc[0]['reorder_point']:.0f} units
  - Service Level: {safety_stock_df.iloc[0]['service_level']*100:.1f}%

REPLENISHMENT:
  - Orders Generated: {len(orders)}
  - Total Quantity: {orders['order_quantity'].sum():,.0f} units
  - Simulated Service Level: {simulation_results.iloc[0]['service_level']*100:.1f}%
""")

print("="*70)
print("Example workflow completed successfully!")
print("="*70)
