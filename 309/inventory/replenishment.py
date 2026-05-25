import pandas as pd
import numpy as np
from typing import Dict, Optional, List, Tuple
import logging
from datetime import datetime, timedelta

from config import Config
from .safety_stock import SafetyStockCalculator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ReplenishmentPlanner:
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or Config().config
        self.order_frequency = self.config.get('replenishment.order_frequency_days', 7)
        self.min_order_qty = self.config.get('replenishment.min_order_qty', 100)
        self.capacity_config = self.config.get('capacity', {})
        self.default_warehouse_capacity = self.capacity_config.get('default_warehouse_capacity', 10000)
        self.default_daily_throughput = self.capacity_config.get('default_daily_throughput', 2000)
        self.default_transport_capacity = self.capacity_config.get('default_transport_capacity', 5000)
        self.capacity_warning_threshold = self.capacity_config.get('warning_threshold', 0.8)
        self.safety_stock_calculator = SafetyStockCalculator(config)
        self.warehouse_capacities: Dict[str, float] = {}
        self.transport_capacities: Dict[str, float] = {}
        self.capacity_violations: List[Dict] = []

    def set_warehouse_capacity(self, warehouse_name: str, capacity: float,
                                daily_throughput: float = None):
        self.warehouse_capacities[warehouse_name] = capacity
        if daily_throughput is not None:
            self.transport_capacities[f"{warehouse_name}_throughput"] = daily_throughput
        logger.info(f"Set capacity for {warehouse_name}: {capacity} units")

    def set_transport_capacity(self, route_name: str, capacity: float):
        self.transport_capacities[route_name] = capacity
        logger.info(f"Set transport capacity for {route_name}: {capacity} units")

    def _get_warehouse_capacity(self, warehouse_name: str) -> float:
        return self.warehouse_capacities.get(warehouse_name, self.default_warehouse_capacity)

    def _get_transport_capacity(self, route_name: str) -> float:
        return self.transport_capacities.get(route_name, self.default_transport_capacity)

    def generate_replenishment_plan(self,
                                     sales_df: pd.DataFrame,
                                     inventory_df: pd.DataFrame,
                                     forecast_df: pd.DataFrame,
                                     supplier_df: pd.DataFrame,
                                     safety_stock_df: pd.DataFrame = None,
                                     start_date: str = None,
                                     horizon_days: int = 180,
                                     enforce_capacity: bool = True,
                                     capacity_warehouse_df: pd.DataFrame = None) -> pd.DataFrame:
        logger.info("Generating replenishment plan...")

        if capacity_warehouse_df is not None:
            self._load_warehouse_capacities(capacity_warehouse_df)

        if start_date is None:
            start_date = sales_df['date'].max() + timedelta(days=1)
        else:
            start_date = pd.to_datetime(start_date)

        end_date = start_date + timedelta(days=horizon_days)
        plan_dates = pd.date_range(start=start_date, end=end_date, freq='D')

        if safety_stock_df is None:
            safety_stock_df = self.safety_stock_calculator.calculate_for_products(
                sales_df, supplier_df, forecast_df
            )

        combinations = safety_stock_df[['product_id', 'warehouse']].drop_duplicates()

        all_plans = []
        self.capacity_violations = []

        for _, combo in combinations.iterrows():
            product_id = combo['product_id']
            warehouse = combo['warehouse']

            try:
                product_plan = self._generate_product_plan(
                    product_id, warehouse,
                    sales_df, inventory_df, forecast_df,
                    supplier_df, safety_stock_df,
                    plan_dates, enforce_capacity
                )
                all_plans.append(product_plan)
            except Exception as e:
                logger.error(f"Error generating plan for {product_id} at {warehouse}: {e}")
                continue

        if not all_plans:
            return pd.DataFrame()

        replenishment_plan = pd.concat(all_plans, ignore_index=True)

        if enforce_capacity:
            replenishment_plan = self._adjust_for_warehouse_capacity(
                replenishment_plan, inventory_df, combinations, plan_dates
            )
            replenishment_plan = self._adjust_for_transport_capacity(
                replenishment_plan, supplier_df
            )

        return self._finalize_plan(replenishment_plan, supplier_df)

    def _load_warehouse_capacities(self, capacity_df: pd.DataFrame):
        logger.info("Loading warehouse capacities from dataframe...")

        required_cols = ['warehouse', 'capacity']
        if not all(col in capacity_df.columns for col in required_cols):
            logger.warning(f"Capacity dataframe missing required columns: {required_cols}")
            return

        for _, row in capacity_df.iterrows():
            warehouse = row['warehouse']
            capacity = row['capacity']
            throughput = row.get('daily_throughput', None)
            self.set_warehouse_capacity(warehouse, capacity, throughput)

        logger.info(f"Loaded capacities for {len(capacity_df)} warehouses")

    def _generate_product_plan(self, product_id: str, warehouse: str,
                                sales_df: pd.DataFrame,
                                inventory_df: pd.DataFrame,
                                forecast_df: pd.DataFrame,
                                supplier_df: pd.DataFrame,
                                safety_stock_df: pd.DataFrame,
                                plan_dates: pd.DatetimeIndex,
                                enforce_capacity: bool = True) -> pd.DataFrame:
        product_sales = sales_df[
            (sales_df['product_id'] == product_id) &
            (sales_df['warehouse'] == warehouse)
        ]

        product_inventory = inventory_df[
            (inventory_df['product_id'] == product_id) &
            (inventory_df['warehouse'] == warehouse)
        ].sort_values('date')

        product_forecast = forecast_df[
            (forecast_df['product_id'] == product_id) &
            (forecast_df['warehouse'] == warehouse)
        ] if 'product_id' in forecast_df.columns else forecast_df

        ss_row = safety_stock_df[
            (safety_stock_df['product_id'] == product_id) &
            (safety_stock_df['warehouse'] == warehouse)
        ]

        if len(ss_row) == 0:
            return pd.DataFrame()

        safety_stock = ss_row['safety_stock_recommended'].iloc[0]
        reorder_point = ss_row['reorder_point'].iloc[0]
        avg_lead_time = int(ss_row['avg_lead_time'].iloc[0])

        supplier = supplier_df[supplier_df['product_id'] == product_id]
        min_order_qty = supplier['min_order_qty'].iloc[0] if len(supplier) > 0 else self.min_order_qty
        unit_cost = supplier['unit_cost'].iloc[0] if len(supplier) > 0 and 'unit_cost' in supplier.columns else 0

        if len(product_inventory) > 0:
            current_stock = product_inventory['stock_quantity'].iloc[-1]
        else:
            current_stock = safety_stock * 1.5

        forecast_dict = dict(zip(product_forecast['date'], product_forecast['forecast']))

        projected_stock = current_stock
        stock_levels = []
        orders = []
        in_transit = {}

        for i, plan_date in enumerate(plan_dates):
            forecast_demand = forecast_dict.get(plan_date, product_forecast['forecast'].mean())

            if plan_date in in_transit:
                projected_stock += in_transit.pop(plan_date)

            projected_stock -= forecast_demand
            projected_stock = max(0, projected_stock)

            stock_levels.append({
                'date': plan_date,
                'product_id': product_id,
                'warehouse': warehouse,
                'projected_stock': projected_stock,
                'forecast_demand': forecast_demand,
                'safety_stock': safety_stock,
                'reorder_point': reorder_point,
                'stock_coverage_days': projected_stock / forecast_demand if forecast_demand > 0 else 0
            })

            is_order_day = (i % self.order_frequency == 0)
            needs_order = projected_stock < reorder_point

            if is_order_day and needs_order:
                lead_time_demand = forecast_demand * avg_lead_time
                review_period_demand = forecast_demand * self.order_frequency

                order_qty = (
                    lead_time_demand + review_period_demand + safety_stock - projected_stock
                )
                order_qty = max(order_qty, min_order_qty)
                order_qty = np.ceil(order_qty / min_order_qty) * min_order_qty

                if enforce_capacity:
                    warehouse_capacity = self._get_warehouse_capacity(warehouse)
                    projected_stock_after = projected_stock + order_qty

                    if projected_stock_after > warehouse_capacity:
                        violation = {
                            'date': plan_date,
                            'product_id': product_id,
                            'warehouse': warehouse,
                            'original_qty': order_qty,
                            'projected_stock_after': projected_stock_after,
                            'capacity': warehouse_capacity,
                            'over_capacity': projected_stock_after - warehouse_capacity
                        }
                        self.capacity_violations.append(violation)

                        max_allowed_qty = max(0, warehouse_capacity - projected_stock)
                        if max_allowed_qty >= min_order_qty:
                            order_qty = np.floor(max_allowed_qty / min_order_qty) * min_order_qty
                        else:
                            order_qty = 0

                arrival_date = plan_date + timedelta(days=avg_lead_time)
                if arrival_date <= plan_dates[-1] and order_qty > 0:
                    in_transit[arrival_date] = order_qty

                if order_qty > 0:
                    orders.append({
                        'order_date': plan_date,
                        'product_id': product_id,
                        'warehouse': warehouse,
                        'order_quantity': order_qty,
                        'expected_arrival_date': arrival_date,
                        'unit_cost': unit_cost,
                        'total_cost': order_qty * unit_cost,
                        'reason': self._get_order_reason(
                            projected_stock, reorder_point, safety_stock, forecast_demand
                        ),
                        'capacity_adjusted': order_qty < (lead_time_demand + review_period_demand + safety_stock - projected_stock)
                    })

        stock_df = pd.DataFrame(stock_levels)

        if orders:
            orders_df = pd.DataFrame(orders)
            result_df = stock_df.merge(
                orders_df,
                left_on=['date', 'product_id', 'warehouse'],
                right_on=['order_date', 'product_id', 'warehouse'],
                how='left'
            )
        else:
            stock_df['order_quantity'] = 0
            stock_df['order_date'] = pd.NaT
            stock_df['expected_arrival_date'] = pd.NaT
            stock_df['unit_cost'] = unit_cost
            stock_df['total_cost'] = 0
            stock_df['reason'] = ''
            result_df = stock_df

        result_df['stock_status'] = result_df['projected_stock'].apply(
            lambda x: 'Critical' if x < safety_stock * 0.3
            else 'Low' if x < safety_stock
            else 'Normal' if x < safety_stock * 2
            else 'Overstock'
        )

        result_df['action_needed'] = result_df['order_quantity'].fillna(0) > 0

        return result_df

    def _get_order_reason(self, current_stock: float, reorder_point: float,
                          safety_stock: float, forecast_demand: float) -> str:
        if current_stock < safety_stock * 0.5:
            return 'Emergency - Stock critically low'
        elif current_stock < safety_stock:
            return 'Safety stock breach'
        elif current_stock < reorder_point:
            return 'Reorder point reached'
        elif forecast_demand > (safety_stock * 0.5):
            return 'Anticipated high demand'
        else:
            return 'Regular review cycle'

    def _finalize_plan(self, plan_df: pd.DataFrame, supplier_df: pd.DataFrame) -> pd.DataFrame:
        if plan_df.empty:
            return plan_df

        plan_df = plan_df.sort_values(['product_id', 'warehouse', 'date'])

        plan_df['week'] = plan_df['date'].dt.isocalendar().week
        plan_df['month'] = plan_df['date'].dt.month
        plan_df['year'] = plan_df['date'].dt.year

        if 'product_id' in supplier_df.columns and 'supplier_name' in supplier_df.columns:
            plan_df = plan_df.merge(
                supplier_df[['product_id', 'supplier_name', 'lead_time_days']],
                on='product_id',
                how='left'
            )

        return plan_df

    def get_order_summary(self, plan_df: pd.DataFrame,
                           group_by: List[str] = None) -> pd.DataFrame:
        if plan_df.empty:
            return pd.DataFrame()

        if group_by is None:
            group_by = ['product_id', 'warehouse']

        orders = plan_df[plan_df['order_quantity'].fillna(0) > 0].copy()

        if len(orders) == 0:
            return pd.DataFrame(columns=group_by + ['total_orders', 'total_quantity', 'total_cost'])

        summary = orders.groupby(group_by).agg({
            'order_quantity': ['count', 'sum'],
            'total_cost': 'sum'
        }).reset_index()

        summary.columns = group_by + ['total_orders', 'total_quantity', 'total_cost']

        summary['avg_order_qty'] = summary['total_quantity'] / summary['total_orders']

        return summary.sort_values('total_cost', ascending=False)

    def optimize_order_quantities(self, plan_df: pd.DataFrame,
                                   holding_cost_rate: float = 0.2,
                                   order_cost: float = 100) -> pd.DataFrame:
        if plan_df.empty:
            return plan_df

        logger.info("Optimizing order quantities using EOQ...")

        optimized = plan_df.copy()

        product_groups = optimized.groupby(['product_id', 'warehouse'])

        for (product_id, warehouse), group in product_groups:
            if len(group) == 0:
                continue

            annual_demand = group['forecast_demand'].sum() * (365 / len(group))
            unit_cost = group['unit_cost'].iloc[0] if 'unit_cost' in group.columns else 10
            holding_cost = unit_cost * holding_cost_rate

            if annual_demand > 0 and holding_cost > 0:
                eoq = np.sqrt((2 * annual_demand * order_cost) / holding_cost)

                mask = (optimized['product_id'] == product_id) & \
                       (optimized['warehouse'] == warehouse) & \
                       (optimized['order_quantity'].fillna(0) > 0)

                if mask.any():
                    original_qty = optimized.loc[mask, 'order_quantity'].sum()
                    num_orders = mask.sum()

                    if num_orders > 0:
                        optimized_eoq = max(eoq, original_qty / num_orders)
                        optimized.loc[mask, 'order_quantity'] = np.ceil(optimized_eoq / 10) * 10
                        optimized.loc[mask, 'total_cost'] = optimized.loc[mask, 'order_quantity'] * unit_cost

        return optimized

    def simulate_stockout_risk(self, plan_df: pd.DataFrame,
                                num_simulations: int = 100) -> pd.DataFrame:
        if plan_df.empty:
            return plan_df

        logger.info(f"Simulating stockout risk with {num_simulations} simulations...")

        simulation_results = []

        product_groups = plan_df.groupby(['product_id', 'warehouse'])

        for (product_id, warehouse), group in product_groups:
            group = group.sort_values('date').reset_index(drop=True)

            stockouts = 0
            stockout_days = []

            for sim in range(num_simulations):
                np.random.seed(sim)

                current_stock = group['projected_stock'].iloc[0]
                in_transit = {}
                sim_stockouts = 0

                for i, row in group.iterrows():
                    plan_date = row['date']
                    forecast = row['forecast_demand']

                    actual_demand = max(0, np.random.normal(forecast, forecast * 0.2))

                    if plan_date in in_transit:
                        current_stock += in_transit.pop(plan_date)

                    current_stock -= actual_demand

                    if current_stock < 0:
                        sim_stockouts += 1
                        current_stock = 0

                    if row['order_quantity'] > 0 and not pd.isna(row['order_quantity']):
                        lead_time = int(row.get('lead_time_days', 7))
                        actual_lead_time = max(1, int(np.random.normal(lead_time, lead_time * 0.3)))
                        arrival_date = plan_date + timedelta(days=actual_lead_time)
                        if arrival_date <= group['date'].max():
                            in_transit[arrival_date] = row['order_quantity']

                stockouts += sim_stockouts

            avg_stockouts = stockouts / num_simulations
            stockout_probability = avg_stockouts / len(group)

            simulation_results.append({
                'product_id': product_id,
                'warehouse': warehouse,
                'avg_stockout_days': avg_stockouts,
                'stockout_probability': stockout_probability,
                'service_level': 1 - stockout_probability,
                'simulation_count': num_simulations
            })

        return pd.DataFrame(simulation_results)

    def generate_purchase_orders(self, plan_df: pd.DataFrame,
                                  start_date: str = None,
                                  end_date: str = None) -> pd.DataFrame:
        if plan_df.empty:
            return pd.DataFrame()

        orders = plan_df[plan_df['order_quantity'].fillna(0) > 0].copy()

        if start_date:
            orders = orders[orders['date'] >= pd.to_datetime(start_date)]
        if end_date:
            orders = orders[orders['date'] <= pd.to_datetime(end_date)]

        if len(orders) == 0:
            return pd.DataFrame()

        po_columns = [
            'date', 'product_id', 'warehouse', 'supplier_name',
            'order_quantity', 'unit_cost', 'total_cost',
            'expected_arrival_date', 'lead_time_days', 'reason'
        ]

        available_cols = [col for col in po_columns if col in orders.columns]
        purchase_orders = orders[available_cols].copy()

        purchase_orders = purchase_orders.rename(columns={'date': 'po_date'})
        purchase_orders['po_number'] = [f"PO-{i+1:06d}" for i in range(len(purchase_orders))]
        purchase_orders['status'] = 'Pending'

        return purchase_orders.sort_values('po_date')

    def get_inventory_projection(self, plan_df: pd.DataFrame) -> pd.DataFrame:
        if plan_df.empty:
            return pd.DataFrame()

        projection = plan_df[[
            'date', 'product_id', 'warehouse', 'projected_stock',
            'forecast_demand', 'safety_stock', 'stock_status', 'order_quantity'
        ]].copy()

        projection['cumulative_demand'] = projection.groupby(
            ['product_id', 'warehouse']
        )['forecast_demand'].cumsum()

        projection['cumulative_orders'] = projection.groupby(
            ['product_id', 'warehouse']
        )['order_quantity'].cumsum().fillna(0)

        return projection

    def identify_slow_moving_items(self, plan_df: pd.DataFrame,
                                    sales_df: pd.DataFrame,
                                    threshold_days: int = 90) -> pd.DataFrame:
        logger.info("Identifying slow-moving items...")

        summary = plan_df.groupby(['product_id', 'warehouse']).agg({
            'projected_stock': 'mean',
            'forecast_demand': 'mean'
        }).reset_index()

        summary['turnover_days'] = np.where(
            summary['forecast_demand'] > 0,
            summary['projected_stock'] / summary['forecast_demand'],
            threshold_days + 1
        )

        summary['is_slow_moving'] = summary['turnover_days'] > threshold_days
        summary['holding_cost_30d'] = summary['projected_stock'] * 0.02

        return summary.sort_values('turnover_days', ascending=False)

    def recommend_transfers(self, plan_df: pd.DataFrame) -> pd.DataFrame:
        if plan_df.empty or 'warehouse' not in plan_df.columns:
            return pd.DataFrame()

        logger.info("Identifying potential warehouse transfers...")

        latest_projection = plan_df.sort_values('date').groupby(
            ['product_id', 'warehouse']
        ).last().reset_index()

        overstock = latest_projection[latest_projection['stock_status'] == 'Overstock'].copy()
        understock = latest_projection[latest_projection['stock_status'] == 'Critical'].copy()

        transfers = []

        for _, under in understock.iterrows():
            product_id = under['product_id']
            needed = under['safety_stock'] - under['projected_stock']

            if needed <= 0:
                continue

            product_overstock = overstock[overstock['product_id'] == product_id]

            for _, over in product_overstock.iterrows():
                available = over['projected_stock'] - over['safety_stock']

                if available > 0:
                    transfer_qty = min(needed, available)
                    transfers.append({
                        'product_id': product_id,
                        'from_warehouse': over['warehouse'],
                        'to_warehouse': under['warehouse'],
                        'transfer_quantity': transfer_qty,
                        'urgency': 'High' if under['projected_stock'] < under['safety_stock'] * 0.3 else 'Medium',
                        'estimated_days_covered': transfer_qty / under['forecast_demand']
                    })
                    needed -= transfer_qty

                if needed <= 0:
                    break

        return pd.DataFrame(transfers) if transfers else pd.DataFrame()

    def _adjust_for_warehouse_capacity(self, plan_df: pd.DataFrame,
                                        inventory_df: pd.DataFrame,
                                        combinations: pd.DataFrame,
                                        plan_dates: pd.DatetimeIndex) -> pd.DataFrame:
        logger.info("Adjusting replenishment plan for warehouse capacity constraints...")

        adjusted_plan = plan_df.copy()

        for warehouse in adjusted_plan['warehouse'].unique():
            warehouse_capacity = self._get_warehouse_capacity(warehouse)

            warehouse_plan = adjusted_plan[adjusted_plan['warehouse'] == warehouse].copy()
            warehouse_products = warehouse_plan['product_id'].unique()

            daily_total_stock = {}
            daily_orders = {}

            for date in plan_dates:
                date_mask = warehouse_plan['date'] == date
                total_stock = warehouse_plan.loc[date_mask, 'projected_stock'].sum()
                total_orders = warehouse_plan.loc[date_mask, 'order_quantity'].fillna(0).sum()

                daily_total_stock[date] = total_stock
                daily_orders[date] = total_orders

                if total_stock > warehouse_capacity * self.capacity_warning_threshold:
                    excess_stock = total_stock - warehouse_capacity * self.capacity_warning_threshold

                    date_orders = warehouse_plan[date_mask & (warehouse_plan['order_quantity'].fillna(0) > 0)]

                    if len(date_orders) > 0:
                        total_order_qty = date_orders['order_quantity'].sum()
                        reduction_ratio = max(0, 1 - excess_stock / (total_order_qty + 1))

                        for idx in date_orders.index:
                            original_qty = adjusted_plan.loc[idx, 'order_quantity']
                            if original_qty > 0:
                                min_order = adjusted_plan.loc[idx, 'order_quantity'].min() if hasattr(adjusted_plan.loc[idx, 'order_quantity'], 'min') else self.min_order_qty
                                adjusted_qty = max(min_order, np.floor(original_qty * reduction_ratio))
                                adjusted_plan.loc[idx, 'order_quantity'] = adjusted_qty
                                adjusted_plan.loc[idx, 'total_cost'] = adjusted_qty * adjusted_plan.loc[idx, 'unit_cost']
                                adjusted_plan.loc[idx, 'capacity_adjusted'] = True

                        logger.info(
                            f"Warehouse {warehouse} at {date}: capacity warning. "
                            f"Reduced orders by {100 - reduction_ratio * 100:.1f}%"
                        )

        return adjusted_plan

    def _adjust_for_transport_capacity(self, plan_df: pd.DataFrame,
                                        supplier_df: pd.DataFrame) -> pd.DataFrame:
        logger.info("Adjusting replenishment plan for transport capacity constraints...")

        adjusted_plan = plan_df.copy()

        if 'expected_arrival_date' not in adjusted_plan.columns:
            return adjusted_plan

        arrival_dates = adjusted_plan['expected_arrival_date'].dropna().unique()

        for arrival_date in arrival_dates:
            arrival_mask = adjusted_plan['expected_arrival_date'] == arrival_date
            arrival_orders = adjusted_plan[arrival_mask & (adjusted_plan['order_quantity'].fillna(0) > 0)]

            if len(arrival_orders) == 0:
                continue

            for supplier in arrival_orders.get('supplier_name', 'Unknown').unique():
                route_key = f"supplier_{supplier}"
                transport_capacity = self._get_transport_capacity(route_key)

                supplier_mask = arrival_orders.get('supplier_name', 'Unknown') == supplier
                supplier_orders = arrival_orders[supplier_mask]

                if len(supplier_orders) == 0:
                    continue

                total_qty = supplier_orders['order_quantity'].sum()

                if total_qty > transport_capacity:
                    excess_qty = total_qty - transport_capacity

                    logger.warning(
                        f"Transport capacity exceeded for {route_key} on {arrival_date}: "
                        f"{total_qty:.0f} > {transport_capacity:.0f}. "
                        f"Spreading excess over later dates."
                    )

                    reduction_ratio = transport_capacity / total_qty

                    for idx in supplier_orders.index:
                        original_qty = adjusted_plan.loc[idx, 'order_quantity']
                        adjusted_qty = np.floor(original_qty * reduction_ratio)
                        adjusted_plan.loc[idx, 'order_quantity'] = adjusted_qty
                        adjusted_plan.loc[idx, 'total_cost'] = adjusted_qty * adjusted_plan.loc[idx, 'unit_cost']
                        adjusted_plan.loc[idx, 'transport_adjusted'] = True

                        remaining_qty = original_qty - adjusted_qty

                        if remaining_qty > 0:
                            lead_time = int(adjusted_plan.loc[idx, 'lead_time_days']) if 'lead_time_days' in adjusted_plan.columns else 7
                            new_arrival_date = arrival_date + timedelta(days=7)
                            new_order_date = new_arrival_date - timedelta(days=lead_time)

                            if new_order_date in adjusted_plan['date'].values:
                                product_id = adjusted_plan.loc[idx, 'product_id']
                                warehouse = adjusted_plan.loc[idx, 'warehouse']

                                existing_mask = (
                                    (adjusted_plan['date'] == new_order_date) &
                                    (adjusted_plan['product_id'] == product_id) &
                                    (adjusted_plan['warehouse'] == warehouse)
                                )

                                if existing_mask.any():
                                    existing_idx = adjusted_plan[existing_mask].index[0]
                                    adjusted_plan.loc[existing_idx, 'order_quantity'] = (
                                        adjusted_plan.loc[existing_idx, 'order_quantity'] + remaining_qty
                                    )
                                    adjusted_plan.loc[existing_idx, 'total_cost'] = (
                                        adjusted_plan.loc[existing_idx, 'order_quantity'] *
                                        adjusted_plan.loc[existing_idx, 'unit_cost']
                                    )
                                    adjusted_plan.loc[existing_idx, 'transport_adjusted'] = True

        return adjusted_plan

    def get_capacity_report(self, plan_df: pd.DataFrame) -> pd.DataFrame:
        logger.info("Generating capacity utilization report...")

        report = []

        for warehouse in plan_df['warehouse'].unique():
            warehouse_capacity = self._get_warehouse_capacity(warehouse)
            warehouse_plan = plan_df[plan_df['warehouse'] == warehouse]

            daily_stock = warehouse_plan.groupby('date')['projected_stock'].sum()
            daily_orders = warehouse_plan.groupby('date')['order_quantity'].sum().fillna(0)

            peak_stock = daily_stock.max()
            avg_stock = daily_stock.mean()
            peak_orders = daily_orders.max()

            capacity_utilization_peak = peak_stock / warehouse_capacity
            capacity_utilization_avg = avg_stock / warehouse_capacity

            warning_days = (daily_stock > warehouse_capacity * self.capacity_warning_threshold).sum()
            violation_days = (daily_stock > warehouse_capacity).sum()

            report.append({
                'warehouse': warehouse,
                'capacity': warehouse_capacity,
                'peak_stock': peak_stock,
                'avg_stock': avg_stock,
                'peak_daily_orders': peak_orders,
                'capacity_utilization_peak': capacity_utilization_peak,
                'capacity_utilization_avg': capacity_utilization_avg,
                'warning_days': warning_days,
                'violation_days': violation_days,
                'status': 'Critical' if violation_days > 0
                else 'Warning' if warning_days > 0
                else 'Normal'
            })

        return pd.DataFrame(report)

    def get_capacity_violations(self) -> pd.DataFrame:
        if not self.capacity_violations:
            return pd.DataFrame(columns=[
                'date', 'product_id', 'warehouse', 'original_qty',
                'projected_stock_after', 'capacity', 'over_capacity'
            ])
        return pd.DataFrame(self.capacity_violations)

    def optimize_with_capacity(self, plan_df: pd.DataFrame,
                                holding_cost_rate: float = 0.2,
                                order_cost: float = 100,
                                max_iterations: int = 10) -> pd.DataFrame:
        logger.info("Optimizing replenishment plan with capacity constraints...")

        optimized_plan = plan_df.copy()

        for iteration in range(max_iterations):
            capacity_report = self.get_capacity_report(optimized_plan)
            critical_warehouses = capacity_report[capacity_report['status'] == 'Critical']['warehouse'].tolist()

            if not critical_warehouses:
                logger.info(f"Capacity optimization converged after {iteration + 1} iterations")
                break

            for warehouse in critical_warehouses:
                warehouse_capacity = self._get_warehouse_capacity(warehouse)
                warehouse_mask = optimized_plan['warehouse'] == warehouse

                warehouse_data = optimized_plan[warehouse_mask].copy()
                products = warehouse_data['product_id'].unique()

                for product_id in products:
                    product_mask = warehouse_mask & (optimized_plan['product_id'] == product_id)
                    product_orders = optimized_plan[product_mask & (optimized_plan['order_quantity'].fillna(0) > 0)]

                    if len(product_orders) >= 2:
                        total_qty = product_orders['order_quantity'].sum()
                        new_frequency = max(1, int(np.ceil(len(product_orders) * 1.5)))
                        new_qty_per_order = np.ceil(total_qty / new_frequency / self.min_order_qty) * self.min_order_qty

                        order_indices = product_orders.index
                        keep_indices = order_indices[::2] if len(order_indices) > 2 else order_indices[:1]

                        for idx in order_indices:
                            if idx in keep_indices:
                                optimized_plan.loc[idx, 'order_quantity'] = new_qty_per_order
                                optimized_plan.loc[idx, 'total_cost'] = new_qty_per_order * optimized_plan.loc[idx, 'unit_cost']
                            else:
                                optimized_plan.loc[idx, 'order_quantity'] = 0
                                optimized_plan.loc[idx, 'total_cost'] = 0

            optimized_plan = self._adjust_for_warehouse_capacity(
                optimized_plan, None,
                optimized_plan[['product_id', 'warehouse']].drop_duplicates(),
                optimized_plan['date'].unique()
            )

        return optimized_plan

    def what_if_capacity_analysis(self, plan_df: pd.DataFrame,
                                   capacity_scenarios: Dict[str, float]) -> pd.DataFrame:
        logger.info("Running what-if capacity analysis...")

        results = []
        original_capacities = self.warehouse_capacities.copy()

        for scenario_name, capacity_multiplier in capacity_scenarios.items():
            for warehouse in original_capacities:
                self.warehouse_capacities[warehouse] = original_capacities[warehouse] * capacity_multiplier

            adjusted_plan = self._adjust_for_warehouse_capacity(
                plan_df, None,
                plan_df[['product_id', 'warehouse']].drop_duplicates(),
                plan_df['date'].unique()
            )

            total_cost = adjusted_plan['total_cost'].sum()
            total_orders = (adjusted_plan['order_quantity'].fillna(0) > 0).sum()
            capacity_report = self.get_capacity_report(adjusted_plan)

            results.append({
                'scenario': scenario_name,
                'capacity_multiplier': capacity_multiplier,
                'total_cost': total_cost,
                'total_orders': total_orders,
                'avg_utilization': capacity_report['capacity_utilization_avg'].mean(),
                'peak_utilization': capacity_report['capacity_utilization_peak'].max(),
                'violation_days': capacity_report['violation_days'].sum(),
                'warning_days': capacity_report['warning_days'].sum()
            })

        self.warehouse_capacities = original_capacities

        return pd.DataFrame(results)
