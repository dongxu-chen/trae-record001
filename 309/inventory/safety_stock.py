import pandas as pd
import numpy as np
from typing import Dict, Optional, List, Tuple
import logging
from scipy.stats import norm
from datetime import datetime, timedelta

from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SafetyStockCalculator:
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or Config().config
        self.service_level = self.config.get('safety_stock.service_level', 0.95)
        self.default_lead_time = self.config.get('safety_stock.lead_time_days', 7)
        self.review_period = self.config.get('safety_stock.review_period_days', 7)
        self.min_stock_days = self.config.get('safety_stock.min_stock_days', 3)
        self.safety_stock_multiplier = self.config.get('replenishment.safety_stock_multiplier', 1.0)

    def calculate_demand_variability(self, sales_df: pd.DataFrame,
                                      product_id: str = None,
                                      warehouse: str = None,
                                      window_days: int = 90) -> Dict:
        logger.info("Calculating demand variability...")

        df = sales_df.copy()
        if product_id:
            df = df[df['product_id'] == product_id]
        if warehouse:
            df = df[df['warehouse'] == warehouse]

        if len(df) == 0:
            return {
                'avg_daily_demand': 0,
                'std_daily_demand': 0,
                'cv_demand': 0,
                'max_daily_demand': 0,
                'min_daily_demand': 0
            }

        max_date = df['date'].max()
        start_date = max_date - timedelta(days=window_days)
        df_recent = df[df['date'] >= start_date]

        daily_demand = df_recent.groupby('date')['quantity'].sum()

        avg_demand = daily_demand.mean()
        std_demand = daily_demand.std() if len(daily_demand) > 1 else 0
        cv_demand = std_demand / avg_demand if avg_demand > 0 else 0

        return {
            'avg_daily_demand': avg_demand,
            'std_daily_demand': std_demand,
            'cv_demand': cv_demand,
            'max_daily_demand': daily_demand.max(),
            'min_daily_demand': daily_demand.min()
        }

    def calculate_lead_time_variability(self, supplier_df: pd.DataFrame,
                                         product_id: str = None) -> Dict:
        logger.info("Calculating lead time variability...")

        df = supplier_df.copy()
        if product_id:
            df = df[df['product_id'] == product_id]

        if len(df) == 0:
            return {
                'avg_lead_time': self.default_lead_time,
                'std_lead_time': self.default_lead_time * 0.3,
                'min_lead_time': self.default_lead_time,
                'max_lead_time': self.default_lead_time * 2
            }

        if 'lead_time_days' in df.columns:
            avg_lead_time = df['lead_time_days'].mean()
            std_lead_time = df['lead_time_days'].std() if len(df) > 1 else avg_lead_time * 0.3
            min_lead_time = df['lead_time_days'].min()
            max_lead_time = df['lead_time_days'].max()
        else:
            avg_lead_time = self.default_lead_time
            std_lead_time = self.default_lead_time * 0.3
            min_lead_time = self.default_lead_time
            max_lead_time = self.default_lead_time * 2

        if 'reliability_score' in df.columns:
            reliability = df['reliability_score'].mean()
            std_lead_time = std_lead_time * (1 + (1 - reliability))

        return {
            'avg_lead_time': avg_lead_time,
            'std_lead_time': std_lead_time,
            'min_lead_time': min_lead_time,
            'max_lead_time': max_lead_time
        }

    def calculate_safety_stock(self, avg_demand: float, std_demand: float,
                                avg_lead_time: float, std_lead_time: float,
                                service_level: float = None,
                                method: str = 'traditional') -> float:
        service_level = service_level or self.service_level

        if method == 'traditional':
            return self._traditional_safety_stock(
                avg_demand, std_demand, avg_lead_time, std_lead_time, service_level
            )
        elif method == 'demand_only':
            return self._demand_only_safety_stock(
                avg_demand, std_demand, avg_lead_time, service_level
            )
        elif method == 'lead_time_only':
            return self._lead_time_only_safety_stock(
                avg_demand, avg_lead_time, std_lead_time, service_level
            )
        elif method == 'periodic_review':
            return self._periodic_review_safety_stock(
                avg_demand, std_demand, avg_lead_time, std_lead_time,
                self.review_period, service_level
            )
        else:
            raise ValueError(f"Unknown method: {method}")

    def _traditional_safety_stock(self, avg_demand: float, std_demand: float,
                                   avg_lead_time: float, std_lead_time: float,
                                   service_level: float) -> float:
        z_score = norm.ppf(service_level)

        demand_variance = (std_demand ** 2) * avg_lead_time
        lead_time_variance = (std_lead_time ** 2) * (avg_demand ** 2)

        safety_stock = z_score * np.sqrt(demand_variance + lead_time_variance)
        return max(0, safety_stock * self.safety_stock_multiplier)

    def _demand_only_safety_stock(self, avg_demand: float, std_demand: float,
                                   avg_lead_time: float, service_level: float) -> float:
        z_score = norm.ppf(service_level)
        safety_stock = z_score * std_demand * np.sqrt(avg_lead_time)
        return max(0, safety_stock * self.safety_stock_multiplier)

    def _lead_time_only_safety_stock(self, avg_demand: float, avg_lead_time: float,
                                      std_lead_time: float, service_level: float) -> float:
        z_score = norm.ppf(service_level)
        safety_stock = z_score * avg_demand * std_lead_time
        return max(0, safety_stock * self.safety_stock_multiplier)

    def _periodic_review_safety_stock(self, avg_demand: float, std_demand: float,
                                       avg_lead_time: float, std_lead_time: float,
                                       review_period: int, service_level: float) -> float:
        z_score = norm.ppf(service_level)
        total_period = avg_lead_time + review_period

        demand_variance = (std_demand ** 2) * total_period
        lead_time_variance = (std_lead_time ** 2) * (avg_demand ** 2)

        safety_stock = z_score * np.sqrt(demand_variance + lead_time_variance)
        return max(0, safety_stock * self.safety_stock_multiplier)

    def calculate_reorder_point(self, avg_demand: float, avg_lead_time: float,
                                 safety_stock: float) -> float:
        lead_time_demand = avg_demand * avg_lead_time
        return lead_time_demand + safety_stock

    def calculate_service_level_metrics(self, safety_stock: float,
                                         avg_demand: float, std_demand: float,
                                         avg_lead_time: float) -> Dict:
        if std_demand == 0 or avg_lead_time == 0:
            return {
                'service_level': self.service_level,
                'z_score': norm.ppf(self.service_level),
                'stockout_risk': 1 - self.service_level,
                'fill_rate': 0.95
            }

        std_lead_time_demand = std_demand * np.sqrt(avg_lead_time)
        z_score = safety_stock / std_lead_time_demand if std_lead_time_demand > 0 else 0

        actual_service_level = norm.cdf(z_score)
        stockout_risk = 1 - actual_service_level

        if std_lead_time_demand > 0:
            fill_rate = 1 - (std_lead_time_demand / avg_demand) * (
                norm.pdf(z_score) - z_score * (1 - norm.cdf(z_score))
            )
        else:
            fill_rate = 1.0

        return {
            'service_level': actual_service_level,
            'z_score': z_score,
            'stockout_risk': stockout_risk,
            'fill_rate': max(0, min(1, fill_rate))
        }

    def calculate_for_products(self, sales_df: pd.DataFrame,
                                supplier_df: pd.DataFrame,
                                forecast_df: pd.DataFrame = None,
                                product_ids: List[str] = None,
                                warehouses: List[str] = None) -> pd.DataFrame:
        logger.info("Calculating safety stock for all products...")

        df = sales_df.copy()
        if product_ids:
            df = df[df['product_id'].isin(product_ids)]
        if warehouses:
            df = df[df['warehouse'].isin(warehouses)]

        groups = df.groupby(['product_id', 'warehouse'])
        results = []

        for (product_id, warehouse), group in groups:
            try:
                demand_stats = self.calculate_demand_variability(
                    group, product_id, warehouse
                )

                lead_time_stats = self.calculate_lead_time_variability(
                    supplier_df, product_id
                )

                avg_demand = demand_stats['avg_daily_demand']
                std_demand = demand_stats['std_daily_demand']
                avg_lead_time = lead_time_stats['avg_lead_time']
                std_lead_time = lead_time_stats['std_lead_time']

                if forecast_df is not None:
                    forecast_group = forecast_df[
                        (forecast_df['product_id'] == product_id) &
                        (forecast_df['warehouse'] == warehouse)
                    ]
                    if len(forecast_group) > 0:
                        future_avg = forecast_group['forecast'].mean()
                        future_std = forecast_group['forecast'].std()
                        if future_avg > 0:
                            weight = 0.6
                            avg_demand = weight * future_avg + (1 - weight) * avg_demand
                            std_demand = weight * future_std + (1 - weight) * std_demand

                safety_stock_traditional = self.calculate_safety_stock(
                    avg_demand, std_demand, avg_lead_time, std_lead_time,
                    method='traditional'
                )

                safety_stock_periodic = self.calculate_safety_stock(
                    avg_demand, std_demand, avg_lead_time, std_lead_time,
                    method='periodic_review'
                )

                reorder_point = self.calculate_reorder_point(
                    avg_demand, avg_lead_time, safety_stock_traditional
                )

                service_metrics = self.calculate_service_level_metrics(
                    safety_stock_traditional, avg_demand, std_demand, avg_lead_time
                )

                min_stock = max(avg_demand * self.min_stock_days, safety_stock_traditional * 0.5)

                results.append({
                    'product_id': product_id,
                    'warehouse': warehouse,
                    'avg_daily_demand': avg_demand,
                    'std_daily_demand': std_demand,
                    'cv_demand': demand_stats['cv_demand'],
                    'avg_lead_time': avg_lead_time,
                    'std_lead_time': std_lead_time,
                    'safety_stock_traditional': safety_stock_traditional,
                    'safety_stock_periodic': safety_stock_periodic,
                    'safety_stock_recommended': max(safety_stock_traditional, safety_stock_periodic),
                    'reorder_point': reorder_point,
                    'min_stock_level': min_stock,
                    'max_stock_level': reorder_point + (avg_demand * self.review_period),
                    'service_level': service_metrics['service_level'],
                    'stockout_risk': service_metrics['stockout_risk'],
                    'fill_rate': service_metrics['fill_rate'],
                    'lead_time_demand': avg_demand * avg_lead_time,
                    'days_of_coverage': safety_stock_traditional / avg_demand if avg_demand > 0 else 0
                })

            except Exception as e:
                logger.error(f"Error calculating safety stock for {product_id} at {warehouse}: {e}")
                continue

        result_df = pd.DataFrame(results)
        logger.info(f"Calculated safety stock for {len(result_df)} product-warehouse combinations")
        return result_df

    def what_if_analysis(self, base_params: Dict,
                          service_levels: List[float] = None,
                          lead_time_changes: List[float] = None) -> pd.DataFrame:
        if service_levels is None:
            service_levels = [0.8, 0.85, 0.9, 0.95, 0.97, 0.99]
        if lead_time_changes is None:
            lead_time_changes = [-2, -1, 0, 1, 2, 3]

        avg_demand = base_params['avg_demand']
        std_demand = base_params['std_demand']
        base_lead_time = base_params['avg_lead_time']
        std_lead_time = base_params['std_lead_time']

        scenarios = []

        for sl in service_levels:
            for lt_change in lead_time_changes:
                avg_lead_time = max(1, base_lead_time + lt_change)

                safety_stock = self.calculate_safety_stock(
                    avg_demand, std_demand, avg_lead_time, std_lead_time,
                    service_level=sl, method='traditional'
                )

                reorder_point = self.calculate_reorder_point(
                    avg_demand, avg_lead_time, safety_stock
                )

                service_metrics = self.calculate_service_level_metrics(
                    safety_stock, avg_demand, std_demand, avg_lead_time
                )

                scenarios.append({
                    'service_level': sl,
                    'lead_time_change_days': lt_change,
                    'avg_lead_time': avg_lead_time,
                    'safety_stock': safety_stock,
                    'reorder_point': reorder_point,
                    'stockout_risk': service_metrics['stockout_risk'],
                    'fill_rate': service_metrics['fill_rate'],
                    'safety_stock_change_pct': (
                        (safety_stock - base_params.get('base_safety_stock', safety_stock)) /
                        base_params.get('base_safety_stock', safety_stock) * 100
                        if base_params.get('base_safety_stock', 0) > 0 else 0
                    )
                })

        return pd.DataFrame(scenarios)

    def optimize_safety_stock(self, avg_demand: float, std_demand: float,
                               avg_lead_time: float, std_lead_time: float,
                               holding_cost: float, stockout_cost: float,
                               order_cost: float) -> Dict:
        logger.info("Optimizing safety stock based on costs...")

        best_cost = float('inf')
        best_params = None

        for service_level in np.arange(0.8, 0.999, 0.01):
            safety_stock = self.calculate_safety_stock(
                avg_demand, std_demand, avg_lead_time, std_lead_time,
                service_level=service_level, method='traditional'
            )

            annual_holding_cost = safety_stock * holding_cost

            order_cycle = np.sqrt(2 * order_cost / (avg_demand * 365 * holding_cost))
            orders_per_year = 365 / (order_cycle * 365) if order_cycle > 0 else 12

            stockout_risk = 1 - service_level
            expected_stockout_per_order = stockout_risk * safety_stock * 0.3
            annual_stockout_cost = orders_per_year * expected_stockout_per_order * stockout_cost

            total_cost = annual_holding_cost + annual_stockout_cost

            if total_cost < best_cost:
                best_cost = total_cost
                best_params = {
                    'optimal_service_level': service_level,
                    'optimal_safety_stock': safety_stock,
                    'annual_holding_cost': annual_holding_cost,
                    'annual_stockout_cost': annual_stockout_cost,
                    'total_annual_cost': total_cost,
                    'orders_per_year': orders_per_year
                }

        return best_params
