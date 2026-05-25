import pandas as pd
import numpy as np
import logging
from pathlib import Path
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

from config import Config
from data import DataLoader, DataPreprocessor, FeatureEngineer, SampleDataGenerator
from models import EnsembleModel
from forecasting import HierarchicalForecaster
from analysis import RampUpAnalyzer
from inventory import SafetyStockCalculator, ReplenishmentPlanner
from visualization import TableauIntegration

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SupplyChainForecastingPlatform:
    def __init__(self, config_path: str = None):
        self.config = Config()
        self.output_dir = Path('./output')
        self.output_dir.mkdir(exist_ok=True)

        self.data_loader = DataLoader()
        self.preprocessor = DataPreprocessor()
        self.feature_engineer = FeatureEngineer()
        self.forecaster = HierarchicalForecaster()
        self.ramp_analyzer = RampUpAnalyzer()
        self.safety_stock_calc = SafetyStockCalculator()
        self.replenishment_planner = ReplenishmentPlanner()
        self.tableau = TableauIntegration()

        self.data = {}
        self.processed_data = {}
        self.features_df = None
        self.forecasts = {}
        self.safety_stock_df = None
        self.replenishment_plan = None
        self.ramp_forecasts = {}

    def generate_sample_data(self, save: bool = True) -> dict:
        logger.info("Generating sample data...")
        generator = SampleDataGenerator()
        sample_data = generator.generate_all(output_dir='./data/sample' if save else None)
        self.data = sample_data
        return sample_data

    def load_data(self, data_dir: str = './data/sample') -> dict:
        logger.info(f"Loading data from {data_dir}...")
        self.data = self.data_loader.load_all(data_dir)
        self.data_loader.validate_data()
        return self.data

    def preprocess_data(self) -> dict:
        logger.info("Preprocessing data...")
        self.processed_data = self.preprocessor.preprocess_all(self.data)
        self.merged_df = self.preprocessor.merge_for_forecasting(self.processed_data)

        logger.info("Creating features...")
        self.features_df = self.feature_engineer.create_all_features(
            self.merged_df, include_lags=True, include_rolling=True
        )

        return self.processed_data

    def run_forecasting(self, use_subset: bool = True) -> dict:
        logger.info("Running hierarchical forecasting...")

        forecast_df = self.features_df.copy()

        if use_subset:
            sample_products = forecast_df['product_id'].unique()[:3]
            sample_warehouses = forecast_df['warehouse'].unique()[:2]
            forecast_df = forecast_df[
                forecast_df['product_id'].isin(sample_products) &
                forecast_df['warehouse'].isin(sample_warehouses)
            ]
            logger.info(f"Using subset: {len(sample_products)} products, {len(sample_warehouses)} warehouses")

        self.forecaster.fit(forecast_df)
        self.forecasts = self.forecaster.predict()

        self.reconciled_forecasts = self.forecaster.reconcile_forecasts(method='bottom_up')

        self.forecast_metrics = self.forecaster.get_metrics_summary()

        if len(self.forecast_metrics) > 0:
            metrics_path = self.output_dir / 'forecast_metrics.csv'
            self.forecast_metrics.to_csv(metrics_path, index=False)
            logger.info(f"Forecast metrics saved to {metrics_path}")

        return self.forecasts

    def analyze_ramp_up(self) -> dict:
        logger.info("Running ramp-up analysis...")

        if 'new_products' in self.data:
            new_products_df = self.data['new_products']
        else:
            new_products_df = self.ramp_analyzer.identify_new_products(
                self.data.get('sales', pd.DataFrame()),
                self.data.get('product', pd.DataFrame())
            )

        self.ramp_analyzer.analyze_historical_ramps(
            self.data.get('sales', pd.DataFrame()),
            self.data.get('product', pd.DataFrame())
        )

        for _, new_product in new_products_df.iterrows():
            product_id = new_product['product_id']
            similar_product = new_product.get('similar_product_id')

            similar_products = [similar_product] if similar_product else None

            ramp_forecast = self.ramp_analyzer.predict_new_product_ramp(
                new_product.to_dict(),
                similar_products=similar_products,
                forecast_days=180
            )

            self.ramp_forecasts[product_id] = ramp_forecast

            ramp_metrics = self.ramp_analyzer.get_ramp_metrics(ramp_forecast)
            logger.info(f"Ramp-up metrics for {product_id}: {ramp_metrics}")

            ramp_path = self.output_dir / f'ramp_up_{product_id}.csv'
            ramp_forecast.to_csv(ramp_path, index=False)

        return self.ramp_forecasts

    def calculate_safety_stock(self) -> pd.DataFrame:
        logger.info("Calculating safety stock...")

        forecast_df = self.forecasts.get('all', pd.DataFrame())
        if forecast_df.empty:
            forecast_df = None

        self.safety_stock_df = self.safety_stock_calc.calculate_for_products(
            self.data.get('sales', pd.DataFrame()),
            self.data.get('supplier', pd.DataFrame()),
            forecast_df=forecast_df
        )

        ss_path = self.output_dir / 'safety_stock.csv'
        self.safety_stock_df.to_csv(ss_path, index=False)
        logger.info(f"Safety stock calculations saved to {ss_path}")

        return self.safety_stock_df

    def generate_replenishment_plan(self) -> pd.DataFrame:
        logger.info("Generating replenishment plan...")

        forecast_df = self.forecasts.get('all', pd.DataFrame())
        if forecast_df.empty:
            raise ValueError("No forecasts available. Run forecasting first.")

        bottom_forecast = forecast_df[forecast_df['level'] == 'combined'].copy()

        self.replenishment_plan = self.replenishment_planner.generate_replenishment_plan(
            self.data.get('sales', pd.DataFrame()),
            self.data.get('inventory', pd.DataFrame()),
            bottom_forecast,
            self.data.get('supplier', pd.DataFrame()),
            self.safety_stock_df,
            horizon_days=180
        )

        plan_path = self.output_dir / 'replenishment_plan.csv'
        self.replenishment_plan.to_csv(plan_path, index=False)
        logger.info(f"Replenishment plan saved to {plan_path}")

        self.purchase_orders = self.replenishment_planner.generate_purchase_orders(
            self.replenishment_plan
        )

        if len(self.purchase_orders) > 0:
            po_path = self.output_dir / 'purchase_orders.csv'
            self.purchase_orders.to_csv(po_path, index=False)
            logger.info(f"Purchase orders saved to {po_path}")

        self.order_summary = self.replenishment_planner.get_order_summary(
            self.replenishment_plan
        )

        return self.replenishment_plan

    def export_to_tableau(self, publish: bool = False) -> dict:
        logger.info("Exporting data for Tableau...")

        forecast_df = self.forecasts.get('all', pd.DataFrame())
        if forecast_df.empty:
            raise ValueError("No forecasts available. Run forecasting first.")

        ramp_combined = pd.DataFrame()
        if self.ramp_forecasts:
            ramp_dfs = []
            for pid, rdf in self.ramp_forecasts.items():
                rdf = rdf.copy()
                rdf['product_id'] = pid
                ramp_dfs.append(rdf)
            ramp_combined = pd.concat(ramp_dfs, ignore_index=True)

        output_files = self.tableau.export_all_for_tableau(
            forecast_df=forecast_df,
            inventory_df=self.data.get('inventory'),
            safety_stock_df=self.safety_stock_df,
            replenishment_df=self.replenishment_plan,
            ramp_df=ramp_combined if not ramp_combined.empty else None,
            output_dir='./output/tableau',
            publish=publish
        )

        return output_files

    def run_full_pipeline(self, use_sample_data: bool = True,
                          use_subset: bool = True,
                          tableau_publish: bool = False) -> dict:
        logger.info("="*60)
        logger.info("Starting Supply Chain Demand Forecasting Pipeline")
        logger.info("="*60)

        results = {}

        if use_sample_data:
            results['sample_data'] = self.generate_sample_data(save=True)
        else:
            results['raw_data'] = self.load_data()

        results['preprocessed_data'] = self.preprocess_data()
        results['forecasts'] = self.run_forecasting(use_subset=use_subset)
        results['ramp_up_analysis'] = self.analyze_ramp_up()
        results['safety_stock'] = self.calculate_safety_stock()
        results['replenishment_plan'] = self.generate_replenishment_plan()
        results['tableau_exports'] = self.export_to_tableau(publish=tableau_publish)

        logger.info("="*60)
        logger.info("Pipeline completed successfully!")
        logger.info("="*60)

        self._print_summary(results)

        return results

    def _print_summary(self, results: dict):
        print("\n" + "="*60)
        print("EXECUTION SUMMARY")
        print("="*60)

        if 'forecasts' in results and 'all' in results['forecasts']:
            forecast_df = results['forecasts']['all']
            print(f"\n1. FORECASTING")
            print(f"   - Total forecast records: {len(forecast_df)}")
            print(f"   - Forecast horizon: {forecast_df['date'].nunique()} days")
            print(f"   - Products forecasted: {forecast_df['product_id'].nunique()}")

            if hasattr(self, 'forecast_metrics') and len(self.forecast_metrics) > 0:
                avg_mape = self.forecast_metrics[self.forecast_metrics['model_type'] == 'ensemble']['mape'].mean()
                avg_rmse = self.forecast_metrics[self.forecast_metrics['model_type'] == 'ensemble']['rmse'].mean()
                print(f"   - Average MAPE (Ensemble): {avg_mape:.2f}%")
                print(f"   - Average RMSE (Ensemble): {avg_rmse:.2f}")

        if 'ramp_up_analysis' in results and results['ramp_up_analysis']:
            print(f"\n2. RAMP-UP ANALYSIS")
            print(f"   - New products analyzed: {len(results['ramp_up_analysis'])}")
            for pid, rdf in results['ramp_up_analysis'].items():
                if len(rdf) > 0:
                    metrics = self.ramp_analyzer.get_ramp_metrics(rdf)
                    print(f"   - {pid}: 90d forecast = {metrics['total_forecast_90d']:,.0f} units")

        if 'safety_stock' in results and len(results['safety_stock']) > 0:
            ss_df = results['safety_stock']
            print(f"\n3. SAFETY STOCK")
            print(f"   - SKU-Warehouse combinations: {len(ss_df)}")
            print(f"   - Average safety stock: {ss_df['safety_stock_recommended'].mean():.1f} units")
            print(f"   - Average reorder point: {ss_df['reorder_point'].mean():.1f} units")
            print(f"   - Average service level: {ss_df['service_level'].mean()*100:.1f}%")

        if 'replenishment_plan' in results and len(results['replenishment_plan']) > 0:
            plan_df = results['replenishment_plan']
            orders = plan_df[plan_df['order_quantity'].fillna(0) > 0]
            print(f"\n4. REPLENISHMENT PLAN")
            print(f"   - Planning horizon: {plan_df['date'].nunique()} days")
            print(f"   - Total orders generated: {len(orders)}")
            print(f"   - Total order quantity: {orders['order_quantity'].sum():,.0f} units")
            if 'total_cost' in orders.columns:
                print(f"   - Total order value: ${orders['total_cost'].sum():,.2f}")

        if 'tableau_exports' in results:
            print(f"\n5. TABLEAU EXPORTS")
            for name, path in results['tableau_exports'].items():
                print(f"   - {name}: {path}")

        print("\n" + "="*60)
        print("All output files saved to ./output/ directory")
        print("="*60 + "\n")


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Supply Chain Demand Forecasting Platform')
    parser.add_argument('--sample', action='store_true', default=True,
                        help='Use sample data')
    parser.add_argument('--data-dir', type=str, default='./data/sample',
                        help='Directory containing data files')
    parser.add_argument('--no-subset', action='store_true',
                        help='Use full dataset (not recommended for testing)')
    parser.add_argument('--tableau-publish', action='store_true',
                        help='Publish results to Tableau Server')
    parser.add_argument('--step', type=str, default='all',
                        choices=['all', 'data', 'forecast', 'ramp', 'safety', 'replenish', 'tableau'],
                        help='Pipeline step to run')

    args = parser.parse_args()

    platform = SupplyChainForecastingPlatform()

    if args.step == 'all':
        platform.run_full_pipeline(
            use_sample_data=args.sample,
            use_subset=not args.no_subset,
            tableau_publish=args.tableau_publish
        )
    else:
        if args.sample:
            platform.generate_sample_data()
        else:
            platform.load_data(args.data_dir)

        platform.preprocess_data()

        if args.step in ['forecast', 'ramp', 'safety', 'replenish', 'tableau']:
            platform.run_forecasting(use_subset=not args.no_subset)

        if args.step in ['ramp', 'safety', 'replenish', 'tableau']:
            platform.analyze_ramp_up()

        if args.step in ['safety', 'replenish', 'tableau']:
            platform.calculate_safety_stock()

        if args.step in ['replenish', 'tableau']:
            platform.generate_replenishment_plan()

        if args.step == 'tableau':
            platform.export_to_tableau(publish=args.tableau_publish)

    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
