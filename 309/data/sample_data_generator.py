import pandas as pd
import numpy as np
from typing import List, Dict
import logging
from datetime import datetime, timedelta
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SampleDataGenerator:
    def __init__(self, seed: int = 42):
        np.random.seed(seed)
        self.products = self._generate_products()
        self.regions = ['North', 'South', 'East', 'West']
        self.warehouses = ['WH001', 'WH002', 'WH003', 'WH004', 'WH005']

    def _generate_products(self) -> List[Dict]:
        categories = ['Electronics', 'Clothing', 'Food', 'Home', 'Beauty']
        products = []
        product_id = 1

        for category in categories:
            for i in range(5):
                products.append({
                    'product_id': f'P{product_id:04d}',
                    'product_name': f'{category} Product {i+1}',
                    'category': category,
                    'launch_date': (datetime(2022, 1, 1) + timedelta(days=np.random.randint(0, 365))).strftime('%Y-%m-%d'),
                    'base_demand': np.random.randint(50, 500),
                    'seasonality_strength': np.random.uniform(0.1, 0.5),
                    'trend': np.random.uniform(-0.05, 0.1)
                })
                product_id += 1

        return products

    def generate_sales_data(self, start_date: str = '2023-01-01',
                            end_date: str = '2025-12-31') -> pd.DataFrame:
        logger.info("Generating sample sales data...")
        date_range = pd.date_range(start=start_date, end=end_date, freq='D')

        records = []
        for product in self.products:
            for region in self.regions:
                for warehouse in self.warehouses[:3]:
                    base_demand = product['base_demand'] * (0.5 + np.random.random())

                    for date in date_range:
                        day_of_year = date.dayofyear
                        month = date.month

                        seasonality = np.sin(2 * np.pi * day_of_year / 365) * product['seasonality_strength']
                        trend = product['trend'] * (date - date_range[0]).days / 365

                        weekend_factor = 1.3 if date.dayofweek >= 5 else 1.0
                        month_factor = 1.5 if month in [11, 12] else 1.0

                        noise = np.random.normal(0, 0.2)

                        demand = base_demand * (1 + seasonality + trend) * weekend_factor * month_factor * (1 + noise)
                        demand = max(0, int(demand))

                        records.append({
                            'date': date,
                            'product_id': product['product_id'],
                            'region': region,
                            'warehouse': warehouse,
                            'quantity': demand
                        })

        df = pd.DataFrame(records)
        logger.info(f"Generated {len(df)} sales records")
        return df

    def generate_inventory_data(self, sales_df: pd.DataFrame) -> pd.DataFrame:
        logger.info("Generating sample inventory data...")
        records = []

        grouped = sales_df.groupby(['product_id', 'warehouse'])
        for (product_id, warehouse), group in grouped:
            group = group.sort_values('date')
            current_stock = np.random.randint(500, 2000)
            lead_time = np.random.randint(3, 14)
            order_qty = np.random.randint(1000, 5000)

            for _, row in group.iterrows():
                current_stock -= row['quantity']
                if current_stock < 200:
                    current_stock += order_qty
                current_stock = max(0, current_stock)

                records.append({
                    'date': row['date'],
                    'product_id': product_id,
                    'warehouse': warehouse,
                    'stock_quantity': current_stock,
                    'reorder_point': 300,
                    'lead_time_days': lead_time
                })

        df = pd.DataFrame(records)
        logger.info(f"Generated {len(df)} inventory records")
        return df

    def generate_promotion_data(self, start_date: str = '2023-01-01',
                                end_date: str = '2025-12-31') -> pd.DataFrame:
        logger.info("Generating sample promotion data...")
        records = []
        date_range = pd.date_range(start=start_date, end=end_date, freq='D')

        promo_types = ['Discount', 'Bundle', 'Flash Sale', 'Coupon', 'Seasonal']
        promo_months = [1, 2, 5, 6, 11, 12]

        for product in self.products:
            num_promos = np.random.randint(4, 12)
            for _ in range(num_promos):
                promo_month = np.random.choice(promo_months)
                promo_year = np.random.choice([2023, 2024, 2025])

                try:
                    start_day = np.random.randint(1, 20)
                    start_dt = datetime(promo_year, promo_month, start_day)
                    duration = np.random.randint(3, 15)
                    end_dt = start_dt + timedelta(days=duration)

                    if start_dt >= date_range[0] and end_dt <= date_range[-1]:
                        records.append({
                            'product_id': product['product_id'],
                            'start_date': start_dt,
                            'end_date': end_dt,
                            'promotion_type': np.random.choice(promo_types),
                            'discount': round(np.random.uniform(0.1, 0.4), 2),
                            'expected_uplift': round(np.random.uniform(1.2, 2.5), 2)
                        })
                except ValueError:
                    continue

        df = pd.DataFrame(records)
        logger.info(f"Generated {len(df)} promotion records")
        return df

    def generate_supplier_data(self) -> pd.DataFrame:
        logger.info("Generating sample supplier data...")
        suppliers = ['Supplier_A', 'Supplier_B', 'Supplier_C', 'Supplier_D', 'Supplier_E']
        records = []

        for product in self.products:
            supplier = np.random.choice(suppliers)
            records.append({
                'product_id': product['product_id'],
                'supplier_name': supplier,
                'lead_time_days': np.random.randint(3, 21),
                'min_order_qty': np.random.randint(50, 500),
                'unit_cost': round(np.random.uniform(5, 500), 2),
                'reliability_score': round(np.random.uniform(0.7, 0.99), 2)
            })

        df = pd.DataFrame(records)
        logger.info(f"Generated {len(df)} supplier records")
        return df

    def generate_product_data(self) -> pd.DataFrame:
        logger.info("Generating sample product data...")
        df = pd.DataFrame(self.products)
        df = df.drop(['base_demand', 'seasonality_strength', 'trend'], axis=1)
        return df

    def generate_new_products(self, num_products: int = 5) -> pd.DataFrame:
        logger.info(f"Generating {num_products} new products for ramp-up analysis...")
        categories = ['Electronics', 'Clothing', 'Food', 'Home', 'Beauty']
        records = []
        max_id = max(int(p['product_id'][1:]) for p in self.products)

        for i in range(num_products):
            product_id = f'P{max_id + i + 1:04d}'
            category = np.random.choice(categories)
            records.append({
                'product_id': product_id,
                'product_name': f'New {category} Product {i+1}',
                'category': category,
                'launch_date': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
                'base_demand': np.random.randint(100, 400),
                'similar_product_id': np.random.choice([p['product_id'] for p in self.products if p['category'] == category])
            })

        df = pd.DataFrame(records)
        logger.info(f"Generated {len(df)} new product records")
        return df

    def generate_all(self, output_dir: str = None) -> Dict[str, pd.DataFrame]:
        logger.info("Generating all sample data...")

        sales_df = self.generate_sales_data()
        inventory_df = self.generate_inventory_data(sales_df)
        promotion_df = self.generate_promotion_data()
        supplier_df = self.generate_supplier_data()
        product_df = self.generate_product_data()
        new_products_df = self.generate_new_products()

        data = {
            'sales': sales_df,
            'inventory': inventory_df,
            'promotion': promotion_df,
            'supplier': supplier_df,
            'product': product_df,
            'new_products': new_products_df
        }

        if output_dir:
            self.save_to_csv(data, output_dir)

        return data

    def save_to_csv(self, data: Dict[str, pd.DataFrame], output_dir: str):
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        for name, df in data.items():
            file_path = output_path / f"{name}.csv"
            df.to_csv(file_path, index=False)
            logger.info(f"Saved {name} data to {file_path}")
