import pandas as pd
import numpy as np
from typing import Dict, Optional, List, Tuple, Union
import logging
from datetime import datetime, timedelta
from scipy.stats import norm
from scipy.optimize import minimize, brentq
from dataclasses import dataclass, field
import warnings
warnings.filterwarnings('ignore')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class CostParameters:
    unit_cost: float = 10.0
    holding_cost_rate: float = 0.25
    ordering_cost: float = 100.0
    stockout_cost_per_unit: float = 20.0
    stockout_cost_multiplier: float = 2.0
    obsolescence_rate: float = 0.1
    cost_of_capital: float = 0.15
    storage_cost_per_unit: float = 5.0
    handling_cost_per_order: float = 50.0


@dataclass
class OptimizationResult:
    product_id: str
    warehouse: str
    optimal_safety_stock: float
    optimal_reorder_point: float
    optimal_order_qty: float
    target_service_level: float
    achieved_service_level: float
    total_annual_cost: float
    holding_cost: float
    ordering_cost: float
    stockout_cost: float
    avg_inventory: float
    inventory_turnover: float
    fill_rate: float
    cost_breakdown: Dict


class InventoryCostOptimizer:
    def __init__(self, config: Optional[Dict] = None):
        from config import Config
        self.config = config or Config().config
        self.cost_config = self.config.get('cost_optimization', {})
        self.default_params = CostParameters(
            unit_cost=self.cost_config.get('unit_cost', 10.0),
            holding_cost_rate=self.cost_config.get('holding_cost_rate', 0.25),
            ordering_cost=self.cost_config.get('ordering_cost', 100.0),
            stockout_cost_per_unit=self.cost_config.get('stockout_cost_per_unit', 20.0),
            stockout_cost_multiplier=self.cost_config.get('stockout_cost_multiplier', 2.0),
            obsolescence_rate=self.cost_config.get('obsolescence_rate', 0.1),
            cost_of_capital=self.cost_config.get('cost_of_capital', 0.15),
            storage_cost_per_unit=self.cost_config.get('storage_cost_per_unit', 5.0),
            handling_cost_per_order=self.cost_config.get('handling_cost_per_order', 50.0)
        )

    def calculate_eoq(self, annual_demand: float,
                       ordering_cost: float = None,
                       unit_cost: float = None,
                       holding_cost_rate: float = None) -> float:
        ordering_cost = ordering_cost or self.default_params.ordering_cost
        unit_cost = unit_cost or self.default_params.unit_cost
        holding_cost_rate = holding_cost_rate or self.default_params.holding_cost_rate

        annual_holding_cost_per_unit = unit_cost * holding_cost_rate

        if annual_holding_cost_per_unit <= 0 or annual_demand <= 0:
            return 0

        eoq = np.sqrt((2 * annual_demand * ordering_cost) / annual_holding_cost_per_unit)
        return eoq

    def calculate_safety_stock_for_service_level(self,
                                                   service_level: float,
                                                   demand_std: float,
                                                   lead_time_days: float,
                                                   review_period_days: float = 0,
                                                   lead_time_std: float = 0) -> float:
        z_score = norm.ppf(service_level)

        protected_period_days = lead_time_days + review_period_days

        demand_variance = demand_std ** 2 * protected_period_days

        avg_daily_demand = demand_std / demand_std if demand_std > 0 else 1
        lead_time_variance = (lead_time_std * avg_daily_demand) ** 2

        total_std = np.sqrt(demand_variance + lead_time_variance)
        safety_stock = z_score * total_std

        return max(0, safety_stock)

    def calculate_total_cost(self,
                              safety_stock: float,
                              order_qty: float,
                              avg_daily_demand: float,
                              demand_std: float,
                              lead_time_days: float,
                              lead_time_std: float = 0,
                              review_period_days: float = 0,
                              cost_params: CostParameters = None,
                              service_level: float = None) -> Dict:
        cost_params = cost_params or self.default_params

        annual_demand = avg_daily_demand * 365

        cycle_stock = order_qty / 2
        avg_inventory = cycle_stock + safety_stock

        annual_holding_cost = (
            avg_inventory * cost_params.unit_cost *
            (cost_params.holding_cost_rate + cost_params.obsolescence_rate)
        ) + (avg_inventory * cost_params.storage_cost_per_unit)

        num_orders = annual_demand / order_qty if order_qty > 0 else 0
        annual_ordering_cost = num_orders * (cost_params.ordering_cost + cost_params.handling_cost_per_order)

        if service_level is None:
            z_score = safety_stock / (demand_std * np.sqrt(lead_time_days + review_period_days) + 1e-6)
            service_level = norm.cdf(z_score)

        stockout_probability = 1 - service_level

        expected_stockout_per_cycle = self._calculate_expected_stockout(
            safety_stock, demand_std, lead_time_days, order_qty
        )
        annual_stockout_units = expected_stockout_per_cycle * num_orders
        annual_stockout_cost = (
            annual_stockout_units * cost_params.unit_cost * cost_params.stockout_cost_multiplier +
            annual_stockout_units * cost_params.stockout_cost_per_unit
        )

        total_annual_cost = annual_holding_cost + annual_ordering_cost + annual_stockout_cost

        fill_rate = 1 - (annual_stockout_units / annual_demand if annual_demand > 0 else 0)
        fill_rate = max(0, min(1, fill_rate))

        inventory_turnover = annual_demand / avg_inventory if avg_inventory > 0 else 0

        return {
            'safety_stock': safety_stock,
            'order_qty': order_qty,
            'cycle_stock': cycle_stock,
            'avg_inventory': avg_inventory,
            'service_level': service_level,
            'fill_rate': fill_rate,
            'stockout_probability': stockout_probability,
            'expected_stockout_per_cycle': expected_stockout_per_cycle,
            'annual_stockout_units': annual_stockout_units,
            'num_orders': num_orders,
            'holding_cost': annual_holding_cost,
            'ordering_cost': annual_ordering_cost,
            'stockout_cost': annual_stockout_cost,
            'total_cost': total_annual_cost,
            'inventory_turnover': inventory_turnover
        }

    def _calculate_expected_stockout(self, safety_stock: float,
                                      demand_std: float,
                                      lead_time_days: float,
                                      order_qty: float) -> float:
        if demand_std <= 0 or lead_time_days <= 0:
            return 0

        lead_time_std = demand_std * np.sqrt(lead_time_days)

        if lead_time_std <= 0:
            return 0

        z = safety_stock / lead_time_std
        unit_normal_loss = norm.pdf(z) - z * (1 - norm.cdf(z))

        expected_stockout = lead_time_std * unit_normal_loss

        return expected_stockout

    def find_optimal_service_level(self,
                                    avg_daily_demand: float,
                                    demand_std: float,
                                    lead_time_days: float,
                                    lead_time_std: float = 0,
                                    review_period_days: float = 0,
                                    cost_params: CostParameters = None,
                                    bounds: Tuple[float, float] = (0.5, 0.999)) -> Dict:
        cost_params = cost_params or self.default_params

        def cost_function(service_level):
            order_qty = self.calculate_eoq(
                avg_daily_demand * 365,
                cost_params.ordering_cost,
                cost_params.unit_cost,
                cost_params.holding_cost_rate
            )

            safety_stock = self.calculate_safety_stock_for_service_level(
                service_level, demand_std, lead_time_days, review_period_days, lead_time_std
            )

            costs = self.calculate_total_cost(
                safety_stock, order_qty, avg_daily_demand, demand_std,
                lead_time_days, lead_time_std, review_period_days,
                cost_params, service_level
            )

            return costs['total_cost']

        try:
            optimal_service_level = brentq(
                lambda sl: cost_function(sl + 0.001) - cost_function(sl - 0.001),
                bounds[0], bounds[1],
                maxiter=100
            )
        except:
            service_levels = np.linspace(bounds[0], bounds[1], 100)
            costs = [cost_function(sl) for sl in service_levels]
            optimal_idx = np.argmin(costs)
            optimal_service_level = service_levels[optimal_idx]

        optimal_order_qty = self.calculate_eoq(
            avg_daily_demand * 365,
            cost_params.ordering_cost,
            cost_params.unit_cost,
            cost_params.holding_cost_rate
        )

        optimal_safety_stock = self.calculate_safety_stock_for_service_level(
            optimal_service_level, demand_std, lead_time_days, review_period_days, lead_time_std
        )

        optimal_costs = self.calculate_total_cost(
            optimal_safety_stock, optimal_order_qty, avg_daily_demand, demand_std,
            lead_time_days, lead_time_std, review_period_days,
            cost_params, optimal_service_level
        )

        return {
            'optimal_service_level': optimal_service_level,
            'optimal_safety_stock': optimal_safety_stock,
            'optimal_order_qty': optimal_order_qty,
            'optimal_reorder_point': optimal_safety_stock + avg_daily_demand * lead_time_days,
            'costs': optimal_costs
        }

    def find_optimal_inventory_policy(self,
                                       product_id: str,
                                       warehouse: str,
                                       sales_df: pd.DataFrame,
                                       lead_time_days: float,
                                       lead_time_std: float = 0,
                                       review_period_days: float = 0,
                                       target_service_level: float = None,
                                       cost_params: CostParameters = None,
                                       supplier_risk_multiplier: float = 1.0) -> OptimizationResult:
        logger.info(f"Optimizing inventory policy for {product_id} at {warehouse}...")

        cost_params = cost_params or self.default_params

        product_sales = sales_df[
            (sales_df['product_id'] == product_id) &
            (sales_df['warehouse'] == warehouse)
        ] if 'warehouse' in sales_df.columns else sales_df[sales_df['product_id'] == product_id]

        if len(product_sales) == 0:
            product_sales = sales_df[sales_df['product_id'] == product_id] if 'product_id' in sales_df.columns else sales_df

        daily_sales = product_sales.groupby('date')['quantity'].sum()
        avg_daily_demand = daily_sales.mean()
        demand_std = daily_sales.std(ddof=1) if len(daily_sales) > 1 else avg_daily_demand * 0.2

        adjusted_lead_time_std = lead_time_std * supplier_risk_multiplier

        if target_service_level is None:
            optimization = self.find_optimal_service_level(
                avg_daily_demand, demand_std, lead_time_days,
                adjusted_lead_time_std, review_period_days, cost_params
            )
            target_service_level = optimization['optimal_service_level']
            optimal_safety_stock = optimization['optimal_safety_stock']
            optimal_order_qty = optimization['optimal_order_qty']
            costs = optimization['costs']
        else:
            optimal_order_qty = self.calculate_eoq(
                avg_daily_demand * 365,
                cost_params.ordering_cost,
                cost_params.unit_cost,
                cost_params.holding_cost_rate
            )
            optimal_safety_stock = self.calculate_safety_stock_for_service_level(
                target_service_level, demand_std, lead_time_days,
                review_period_days, adjusted_lead_time_std
            )
            costs = self.calculate_total_cost(
                optimal_safety_stock, optimal_order_qty, avg_daily_demand, demand_std,
                lead_time_days, adjusted_lead_time_std, review_period_days,
                cost_params, target_service_level
            )

        result = OptimizationResult(
            product_id=product_id,
            warehouse=warehouse,
            optimal_safety_stock=optimal_safety_stock,
            optimal_reorder_point=optimal_safety_stock + avg_daily_demand * lead_time_days,
            optimal_order_qty=optimal_order_qty,
            target_service_level=target_service_level,
            achieved_service_level=costs['service_level'],
            total_annual_cost=costs['total_cost'],
            holding_cost=costs['holding_cost'],
            ordering_cost=costs['ordering_cost'],
            stockout_cost=costs['stockout_cost'],
            avg_inventory=costs['avg_inventory'],
            inventory_turnover=costs['inventory_turnover'],
            fill_rate=costs['fill_rate'],
            cost_breakdown={
                'cycle_stock': costs['cycle_stock'],
                'safety_stock_component': optimal_safety_stock,
                'num_orders': costs['num_orders'],
                'stockout_probability': costs['stockout_probability'],
                'annual_stockout_units': costs['annual_stockout_units'],
                'holding_cost_rate': cost_params.holding_cost_rate,
                'stockout_cost_multiplier': cost_params.stockout_cost_multiplier
            }
        )

        logger.info(f"Optimization complete for {product_id}: "
                    f"SL={result.achieved_service_level:.2%}, "
                    f"SS={result.optimal_safety_stock:.0f}, "
                    f"EOQ={result.optimal_order_qty:.0f}, "
                    f"Cost=${result.total_annual_cost:.2f}")

        return result

    def optimize_all_products(self,
                               products: List[Tuple[str, str]],
                               sales_df: pd.DataFrame,
                               supplier_df: pd.DataFrame,
                               supplier_risk_df: pd.DataFrame = None,
                               target_service_level: float = None,
                               cost_params: CostParameters = None) -> pd.DataFrame:
        logger.info(f"Optimizing inventory policy for {len(products)} product-warehouse combinations...")

        results = []

        for product_id, warehouse in products:
            product_supplier = supplier_df[supplier_df['product_id'] == product_id]
            if len(product_supplier) > 0:
                lead_time_days = product_supplier['lead_time_days'].mean()
                lead_time_std = product_supplier['lead_time_days'].std(ddof=1) if len(product_supplier) > 1 else lead_time_days * 0.2
                unit_cost = product_supplier['unit_cost'].mean()
            else:
                lead_time_days = 7
                lead_time_std = 2
                unit_cost = 10.0

            supplier_risk_multiplier = 1.0
            if supplier_risk_df is not None and len(product_supplier) > 0:
                supplier_name = product_supplier.iloc[0]['supplier_name']
                risk_data = supplier_risk_df[supplier_risk_df['supplier_name'] == supplier_name]
                if len(risk_data) > 0:
                    risk_score = risk_data.iloc[0]['overall_risk_score']
                    supplier_risk_multiplier = 1 + risk_score

            product_cost_params = cost_params or self.default_params
            product_cost_params.unit_cost = unit_cost

            result = self.find_optimal_inventory_policy(
                product_id, warehouse, sales_df,
                lead_time_days, lead_time_std,
                target_service_level=target_service_level,
                cost_params=product_cost_params,
                supplier_risk_multiplier=supplier_risk_multiplier
            )

            results.append({
                'product_id': product_id,
                'warehouse': warehouse,
                'lead_time_days': lead_time_days,
                'optimal_safety_stock': result.optimal_safety_stock,
                'optimal_reorder_point': result.optimal_reorder_point,
                'optimal_order_qty': result.optimal_order_qty,
                'target_service_level': result.target_service_level,
                'achieved_service_level': result.achieved_service_level,
                'fill_rate': result.fill_rate,
                'avg_inventory': result.avg_inventory,
                'inventory_turnover': result.inventory_turnover,
                'total_annual_cost': result.total_annual_cost,
                'holding_cost': result.holding_cost,
                'ordering_cost': result.ordering_cost,
                'stockout_cost': result.stockout_cost,
                'supplier_risk_multiplier': supplier_risk_multiplier
            })

        return pd.DataFrame(results).sort_values('total_annual_cost', ascending=False)

    def generate_cost_curve(self,
                             product_id: str,
                             warehouse: str,
                             sales_df: pd.DataFrame,
                             lead_time_days: float,
                             lead_time_std: float = 0,
                             cost_params: CostParameters = None,
                             service_level_range: Tuple[float, float] = (0.8, 0.99)) -> pd.DataFrame:
        logger.info(f"Generating cost curve for {product_id}...")

        cost_params = cost_params or self.default_params

        product_sales = sales_df[
            (sales_df['product_id'] == product_id) &
            (sales_df['warehouse'] == warehouse)
        ] if 'warehouse' in sales_df.columns else sales_df[sales_df['product_id'] == product_id]

        if len(product_sales) == 0:
            product_sales = sales_df[sales_df['product_id'] == product_id] if 'product_id' in sales_df.columns else sales_df

        daily_sales = product_sales.groupby('date')['quantity'].sum()
        avg_daily_demand = daily_sales.mean()
        demand_std = daily_sales.std(ddof=1) if len(daily_sales) > 1 else avg_daily_demand * 0.2

        service_levels = np.linspace(service_level_range[0], service_level_range[1], 50)

        curve_data = []
        for sl in service_levels:
            order_qty = self.calculate_eoq(
                avg_daily_demand * 365,
                cost_params.ordering_cost,
                cost_params.unit_cost,
                cost_params.holding_cost_rate
            )

            safety_stock = self.calculate_safety_stock_for_service_level(
                sl, demand_std, lead_time_days, 0, lead_time_std
            )

            costs = self.calculate_total_cost(
                safety_stock, order_qty, avg_daily_demand, demand_std,
                lead_time_days, lead_time_std, 0, cost_params, sl
            )

            curve_data.append({
                'service_level': sl,
                'safety_stock': safety_stock,
                'avg_inventory': costs['avg_inventory'],
                'holding_cost': costs['holding_cost'],
                'ordering_cost': costs['ordering_cost'],
                'stockout_cost': costs['stockout_cost'],
                'total_cost': costs['total_cost'],
                'inventory_turnover': costs['inventory_turnover'],
                'fill_rate': costs['fill_rate']
            })

        return pd.DataFrame(curve_data)

    def compare_cost_scenarios(self,
                                product_id: str,
                                warehouse: str,
                                sales_df: pd.DataFrame,
                                lead_time_days: float,
                                scenarios: Dict[str, Dict],
                                lead_time_std: float = 0) -> pd.DataFrame:
        logger.info(f"Comparing cost scenarios for {product_id}...")

        results = []

        for scenario_name, scenario_params in scenarios.items():
            cost_params = CostParameters(**{**self.default_params.__dict__, **scenario_params})

            result = self.find_optimal_inventory_policy(
                product_id, warehouse, sales_df,
                lead_time_days, lead_time_std,
                cost_params=cost_params
            )

            results.append({
                'scenario': scenario_name,
                **scenario_params,
                'optimal_safety_stock': result.optimal_safety_stock,
                'optimal_reorder_point': result.optimal_reorder_point,
                'optimal_order_qty': result.optimal_order_qty,
                'service_level': result.achieved_service_level,
                'total_cost': result.total_annual_cost,
                'holding_cost': result.holding_cost,
                'ordering_cost': result.ordering_cost,
                'stockout_cost': result.stockout_cost,
                'avg_inventory': result.avg_inventory,
                'inventory_turnover': result.inventory_turnover
            })

        return pd.DataFrame(results)

    def calculate_roi_for_safety_stock_investment(self,
                                                    current_safety_stock: float,
                                                    proposed_safety_stock: float,
                                                    current_service_level: float,
                                                    proposed_service_level: float,
                                                    avg_daily_demand: float,
                                                    unit_cost: float,
                                                    stockout_cost_per_unit: float,
                                                    holding_cost_rate: float = 0.25) -> Dict:
        additional_inventory = proposed_safety_stock - current_safety_stock
        investment = additional_inventory * unit_cost

        stockout_reduction = max(0, current_service_level - proposed_service_level)
        annual_demand = avg_daily_demand * 365
        annual_stockout_reduction = annual_demand * stockout_reduction
        annual_savings = annual_stockout_reduction * stockout_cost_per_unit

        additional_holding_cost = additional_inventory * unit_cost * holding_cost_rate
        net_annual_savings = annual_savings - additional_holding_cost

        roi = net_annual_savings / investment if investment > 0 else np.inf
        payback_months = investment / (net_annual_savings / 12) if net_annual_savings > 0 else np.inf

        return {
            'additional_inventory_units': additional_inventory,
            'additional_inventory_value': investment,
            'additional_holding_cost': additional_holding_cost,
            'annual_stockout_reduction_units': annual_stockout_reduction,
            'annual_stockout_cost_savings': annual_savings,
            'net_annual_savings': net_annual_savings,
            'roi': roi,
            'payback_months': payback_months,
            'recommendation': 'APPROVE' if roi > 0 and payback_months < 12 else 'REVIEW' if roi > 0 else 'REJECT'
        }

    def plot_cost_curve(self, cost_curve_df: pd.DataFrame):
        try:
            import matplotlib.pyplot as plt

            fig, axes = plt.subplots(2, 2, figsize=(14, 10))

            axes[0, 0].plot(cost_curve_df['service_level'], cost_curve_df['total_cost'],
                            'b-', linewidth=2, label='Total Cost')
            axes[0, 0].plot(cost_curve_df['service_level'], cost_curve_df['holding_cost'],
                            'g--', label='Holding Cost')
            axes[0, 0].plot(cost_curve_df['service_level'], cost_curve_df['stockout_cost'],
                            'r--', label='Stockout Cost')
            axes[0, 0].plot(cost_curve_df['service_level'], cost_curve_df['ordering_cost'],
                            'y--', label='Ordering Cost')

            min_idx = cost_curve_df['total_cost'].idxmin()
            min_sl = cost_curve_df.loc[min_idx, 'service_level']
            min_cost = cost_curve_df.loc[min_idx, 'total_cost']
            axes[0, 0].axvline(x=min_sl, color='k', linestyle=':',
                               label=f'Optimal SL: {min_sl:.2%}')
            axes[0, 0].scatter([min_sl], [min_cost], color='red', s=100, zorder=5)

            axes[0, 0].set_xlabel('Service Level')
            axes[0, 0].set_ylabel('Annual Cost ($)')
            axes[0, 0].set_title('Cost vs Service Level')
            axes[0, 0].legend()
            axes[0, 0].grid(True, alpha=0.3)

            axes[0, 1].plot(cost_curve_df['service_level'], cost_curve_df['safety_stock'], 'b-', linewidth=2)
            axes[0, 1].axvline(x=min_sl, color='k', linestyle=':')
            axes[0, 1].set_xlabel('Service Level')
            axes[0, 1].set_ylabel('Safety Stock (Units)')
            axes[0, 1].set_title('Safety Stock vs Service Level')
            axes[0, 1].grid(True, alpha=0.3)

            axes[1, 0].plot(cost_curve_df['service_level'], cost_curve_df['fill_rate'], 'g-', linewidth=2)
            axes[1, 0].axvline(x=min_sl, color='k', linestyle=':')
            axes[1, 0].axhline(y=0.95, color='r', linestyle='--', label='95% Fill Rate')
            axes[1, 0].set_xlabel('Service Level')
            axes[1, 0].set_ylabel('Fill Rate')
            axes[1, 0].set_title('Fill Rate vs Service Level')
            axes[1, 0].legend()
            axes[1, 0].grid(True, alpha=0.3)

            axes[1, 1].plot(cost_curve_df['service_level'], cost_curve_df['inventory_turnover'], 'purple', linewidth=2)
            axes[1, 1].axvline(x=min_sl, color='k', linestyle=':')
            axes[1, 1].set_xlabel('Service Level')
            axes[1, 1].set_ylabel('Inventory Turnover')
            axes[1, 1].set_title('Inventory Turnover vs Service Level')
            axes[1, 1].grid(True, alpha=0.3)

            plt.tight_layout()
            return plt

        except Exception as e:
            logger.warning(f"Could not plot cost curve: {e}")
            return None

    def plot_scenario_comparison(self, scenario_df: pd.DataFrame):
        try:
            import matplotlib.pyplot as plt

            fig, axes = plt.subplots(2, 2, figsize=(14, 10))

            x = np.arange(len(scenario_df))

            axes[0, 0].bar(x, scenario_df['total_cost'], color='steelblue', alpha=0.8)
            axes[0, 0].set_xlabel('Scenario')
            axes[0, 0].set_ylabel('Total Annual Cost ($)')
            axes[0, 0].set_title('Total Cost by Scenario')
            axes[0, 0].set_xticks(x)
            axes[0, 0].set_xticklabels(scenario_df['scenario'], rotation=45, ha='right')
            axes[0, 0].grid(True, alpha=0.3, axis='y')
            for i, v in enumerate(scenario_df['total_cost']):
                axes[0, 0].text(i, v, f'${v:.0f}', ha='center', va='bottom')

            width = 0.25
            axes[0, 1].bar(x - width, scenario_df['holding_cost'], width, label='Holding', color='blue')
            axes[0, 1].bar(x, scenario_df['ordering_cost'], width, label='Ordering', color='green')
            axes[0, 1].bar(x + width, scenario_df['stockout_cost'], width, label='Stockout', color='red')
            axes[0, 1].set_xlabel('Scenario')
            axes[0, 1].set_ylabel('Annual Cost ($)')
            axes[0, 1].set_title('Cost Breakdown by Scenario')
            axes[0, 1].set_xticks(x)
            axes[0, 1].set_xticklabels(scenario_df['scenario'], rotation=45, ha='right')
            axes[0, 1].legend()
            axes[0, 1].grid(True, alpha=0.3, axis='y')

            axes[1, 0].bar(x, scenario_df['service_level'], color='green', alpha=0.8)
            axes[1, 0].axhline(y=0.95, color='r', linestyle='--', label='95% Target')
            axes[1, 0].set_xlabel('Scenario')
            axes[1, 0].set_ylabel('Service Level')
            axes[1, 0].set_title('Service Level by Scenario')
            axes[1, 0].set_xticks(x)
            axes[1, 0].set_xticklabels(scenario_df['scenario'], rotation=45, ha='right')
            axes[1, 0].set_ylim(0.8, 1.02)
            axes[1, 0].legend()
            axes[1, 0].grid(True, alpha=0.3, axis='y')

            axes[1, 1].bar(x, scenario_df['optimal_safety_stock'], color='orange', alpha=0.8)
            axes[1, 1].set_xlabel('Scenario')
            axes[1, 1].set_ylabel('Optimal Safety Stock')
            axes[1, 1].set_title('Optimal Safety Stock by Scenario')
            axes[1, 1].set_xticks(x)
            axes[1, 1].set_xticklabels(scenario_df['scenario'], rotation=45, ha='right')
            axes[1, 1].grid(True, alpha=0.3, axis='y')

            plt.tight_layout()
            return plt

        except Exception as e:
            logger.warning(f"Could not plot scenario comparison: {e}")
            return None
