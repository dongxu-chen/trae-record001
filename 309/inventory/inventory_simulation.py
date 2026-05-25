import pandas as pd
import numpy as np
from typing import Dict, Optional, List, Tuple, Union, Callable
import logging
from datetime import datetime, timedelta
from scipy.stats import norm, poisson, gamma, lognorm
from dataclasses import dataclass, field
from tqdm import tqdm
import warnings
warnings.filterwarnings('ignore')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class SimulationParams:
    num_simulations: int = 1000
    simulation_days: int = 365
    demand_volatility: float = 0.2
    lead_time_volatility: float = 0.3
    random_seed: int = 42
    warmup_days: int = 30


@dataclass
class InventoryStrategy:
    strategy_type: str = 'sS'
    reorder_point: float = 100
    safety_stock: float = 50
    reorder_qty: float = 200
    review_period: int = 7
    max_stock: float = 500
    target_service_level: float = 0.95


@dataclass
class SimulationResult:
    product_id: str
    warehouse: str
    strategy: InventoryStrategy
    avg_inventory: float
    max_inventory: float
    min_inventory: float
    stockout_days: float
    stockout_probability: float
    service_level: float
    avg_stockout_qty: float
    total_cost: float
    holding_cost: float
    stockout_cost: float
    ordering_cost: float
    num_orders: int
    fill_rate: float
    inventory_turnover: float
    daily_results: pd.DataFrame = field(default_factory=pd.DataFrame)


class InventorySimulator:
    def __init__(self, config: Optional[Dict] = None):
        from config import Config
        self.config = config or Config().config
        self.sim_config = self.config.get('simulation', {})
        self.default_params = SimulationParams(
            num_simulations=self.sim_config.get('num_simulations', 1000),
            simulation_days=self.sim_config.get('simulation_days', 365),
            demand_volatility=self.sim_config.get('demand_volatility', 0.2),
            lead_time_volatility=self.sim_config.get('lead_time_volatility', 0.3)
        )

        self.holding_cost_rate = self.sim_config.get('holding_cost_rate', 0.25)
        self.stockout_cost_multiplier = self.sim_config.get('stockout_cost_multiplier', 2.0)
        self.order_cost = self.sim_config.get('order_cost', 100)

    def _generate_demand_scenario(self, base_demand: pd.Series,
                                   num_days: int,
                                   volatility: float,
                                   seed: int) -> np.ndarray:
        np.random.seed(seed)

        if len(base_demand) >= num_days:
            base = base_demand.values[:num_days]
        else:
            base = np.tile(base_demand.values, num_days // len(base_demand) + 1)[:num_days]

        noise = np.random.normal(0, volatility, num_days)
        demand = np.maximum(0, base * (1 + noise))

        if len(base_demand) >= 7:
            weekly_pattern = base_demand.groupby(base_demand.index.dayofweek).mean()
            for i in range(num_days):
                day_idx = i % 7
                if day_idx in weekly_pattern.index:
                    seasonal_factor = weekly_pattern[day_idx] / base.mean()
                    demand[i] *= seasonal_factor

        return demand

    def _generate_lead_time_scenario(self, mean_lead_time: float,
                                      volatility: float,
                                      num_orders: int,
                                      seed: int,
                                      distribution: str = 'gamma') -> np.ndarray:
        np.random.seed(seed + 1000)

        std_lt = mean_lead_time * volatility

        if distribution == 'gamma':
            shape = (mean_lead_time ** 2) / (std_lt ** 2 + 1e-6)
            scale = (std_lt ** 2) / (mean_lead_time + 1e-6)
            lead_times = gamma.rvs(a=shape, scale=scale, size=num_orders)
        elif distribution == 'lognormal':
            sigma = np.sqrt(np.log(1 + (std_lt ** 2) / (mean_lead_time ** 2 + 1e-6)))
            mu = np.log(mean_lead_time) - 0.5 * sigma ** 2
            lead_times = lognorm.rvs(s=sigma, scale=np.exp(mu), size=num_orders)
        elif distribution == 'poisson':
            lead_times = poisson.rvs(mu=mean_lead_time, size=num_orders)
        else:
            lead_times = np.random.normal(mean_lead_time, std_lt, num_orders)

        return np.maximum(1, lead_times.astype(int))

    def _run_single_simulation(self,
                                demand: np.ndarray,
                                lead_times: np.ndarray,
                                strategy: InventoryStrategy,
                                initial_stock: float,
                                unit_cost: float,
                                params: SimulationParams) -> Dict:
        stock = initial_stock
        in_transit = {}
        orders_placed = []
        daily_stock = []
        daily_stockouts = []
        daily_demand_met = []
        order_counter = 0

        for day in range(params.simulation_days):
            today_demand = demand[day]

            if day in in_transit:
                stock += in_transit.pop(day)

            stock_after_demand = stock - today_demand

            if stock_after_demand < 0:
                stockout_qty = abs(stock_after_demand)
                stock = 0
                stockout = True
                demand_met = today_demand - stockout_qty
            else:
                stock = stock_after_demand
                stockout = False
                stockout_qty = 0
                demand_met = today_demand

            daily_stock.append(stock)
            daily_stockouts.append(stockout_qty)
            daily_demand_met.append(demand_met)

            if strategy.strategy_type == 'sS':
                if stock < strategy.reorder_point and day >= params.warmup_days:
                    order_qty = strategy.max_stock - stock
                    if order_qty > 0:
                        lead_time = lead_times[order_counter % len(lead_times)]
                        arrival_day = day + lead_time
                        if arrival_day < params.simulation_days:
                            in_transit[arrival_day] = in_transit.get(arrival_day, 0) + order_qty
                        orders_placed.append({
                            'day': day,
                            'qty': order_qty,
                            'lead_time': lead_time
                        })
                        order_counter += 1

            elif strategy.strategy_type == 'RQ':
                if (day - params.warmup_days) % strategy.review_period == 0 and day >= params.warmup_days:
                    if stock < strategy.reorder_point:
                        order_qty = strategy.reorder_qty
                        lead_time = lead_times[order_counter % len(lead_times)]
                        arrival_day = day + lead_time
                        if arrival_day < params.simulation_days:
                            in_transit[arrival_day] = in_transit.get(arrival_day, 0) + order_qty
                        orders_placed.append({
                            'day': day,
                            'qty': order_qty,
                            'lead_time': lead_time
                        })
                        order_counter += 1

            elif strategy.strategy_type == 'safety_stock':
                if stock < strategy.safety_stock and day >= params.warmup_days:
                    order_qty = strategy.reorder_qty
                    lead_time = lead_times[order_counter % len(lead_times)]
                    arrival_day = day + lead_time
                    if arrival_day < params.simulation_days:
                        in_transit[arrival_day] = in_transit.get(arrival_day, 0) + order_qty
                    orders_placed.append({
                        'day': day,
                        'qty': order_qty,
                        'lead_time': lead_time
                    })
                    order_counter += 1

        warmup_slice = slice(params.warmup_days, params.simulation_days)
        stock_after_warmup = daily_stock[warmup_slice]
        stockouts_after_warmup = daily_stockouts[warmup_slice]
        demand_after_warmup = demand[warmup_slice]
        demand_met_after_warmup = daily_demand_met[warmup_slice]

        num_days = params.simulation_days - params.warmup_days
        stockout_days = sum(1 for s in stockouts_after_warmup if s > 0)
        total_demand = sum(demand_after_warmup)
        total_met = sum(demand_met_after_warmup)
        total_stockout_qty = sum(stockouts_after_warmup)

        avg_inventory = np.mean(stock_after_warmup)
        holding_cost = avg_inventory * unit_cost * self.holding_cost_rate * (num_days / 365)

        stockout_cost = total_stockout_qty * unit_cost * self.stockout_cost_multiplier
        ordering_cost = len(orders_placed) * self.order_cost
        total_cost = holding_cost + stockout_cost + ordering_cost

        return {
            'daily_stock': daily_stock,
            'daily_stockouts': daily_stockouts,
            'daily_demand': demand,
            'daily_demand_met': daily_demand_met,
            'orders': orders_placed,
            'avg_inventory': avg_inventory,
            'max_inventory': max(stock_after_warmup),
            'min_inventory': min(stock_after_warmup),
            'stockout_days': stockout_days,
            'stockout_probability': stockout_days / num_days,
            'service_level': 1 - (stockout_days / num_days),
            'avg_stockout_qty': np.mean(stockouts_after_warmup),
            'total_cost': total_cost,
            'holding_cost': holding_cost,
            'stockout_cost': stockout_cost,
            'ordering_cost': ordering_cost,
            'num_orders': len(orders_placed),
            'fill_rate': total_met / total_demand if total_demand > 0 else 1,
            'inventory_turnover': total_demand / avg_inventory if avg_inventory > 0 else 0
        }

    def simulate_product(self,
                          product_id: str,
                          warehouse: str,
                          sales_df: pd.DataFrame,
                          strategy: InventoryStrategy,
                          supplier_risk_assessor: Optional[object] = None,
                          supplier_name: Optional[str] = None,
                          mean_lead_time: float = 7,
                          initial_stock: Optional[float] = None,
                          unit_cost: float = 10.0,
                          params: Optional[SimulationParams] = None) -> SimulationResult:
        logger.info(f"Running inventory simulation for {product_id} at {warehouse}...")

        params = params or self.default_params

        product_sales = sales_df[
            (sales_df['product_id'] == product_id) &
            (sales_df['warehouse'] == warehouse)
        ] if 'warehouse' in sales_df.columns else sales_df[sales_df['product_id'] == product_id]

        if len(product_sales) == 0:
            product_sales = sales_df[sales_df['product_id'] == product_id] if 'product_id' in sales_df.columns else sales_df

        base_demand = product_sales.groupby('date')['quantity'].sum().sort_index()

        if initial_stock is None:
            initial_stock = strategy.safety_stock * 1.5 + strategy.reorder_point

        all_results = []
        all_daily = []

        for sim in tqdm(range(params.num_simulations), desc=f"Simulating {product_id}", leave=False):
            demand = self._generate_demand_scenario(
                base_demand, params.simulation_days, params.demand_volatility, seed=params.random_seed + sim
            )

            if supplier_risk_assessor and supplier_name:
                lead_times = supplier_risk_assessor.simulate_lead_time(
                    supplier_name, num_samples=params.simulation_days
                )
            else:
                lead_times = self._generate_lead_time_scenario(
                    mean_lead_time, params.lead_time_volatility,
                    params.simulation_days, seed=params.random_seed + sim
                )

            result = self._run_single_simulation(
                demand, lead_times, strategy, initial_stock, unit_cost, params
            )
            all_results.append(result)

            if sim < 5:
                daily_df = pd.DataFrame({
                    'simulation': sim,
                    'day': range(params.simulation_days),
                    'stock': result['daily_stock'],
                    'demand': result['daily_demand'],
                    'stockout_qty': result['daily_stockouts'],
                    'demand_met': result['daily_demand_met']
                })
                all_daily.append(daily_df)

        combined_daily = pd.concat(all_daily, ignore_index=True) if all_daily else pd.DataFrame()

        avg_result = SimulationResult(
            product_id=product_id,
            warehouse=warehouse,
            strategy=strategy,
            avg_inventory=np.mean([r['avg_inventory'] for r in all_results]),
            max_inventory=np.mean([r['max_inventory'] for r in all_results]),
            min_inventory=np.mean([r['min_inventory'] for r in all_results]),
            stockout_days=np.mean([r['stockout_days'] for r in all_results]),
            stockout_probability=np.mean([r['stockout_probability'] for r in all_results]),
            service_level=np.mean([r['service_level'] for r in all_results]),
            avg_stockout_qty=np.mean([r['avg_stockout_qty'] for r in all_results]),
            total_cost=np.mean([r['total_cost'] for r in all_results]),
            holding_cost=np.mean([r['holding_cost'] for r in all_results]),
            stockout_cost=np.mean([r['stockout_cost'] for r in all_results]),
            ordering_cost=np.mean([r['ordering_cost'] for r in all_results]),
            num_orders=int(np.mean([r['num_orders'] for r in all_results])),
            fill_rate=np.mean([r['fill_rate'] for r in all_results]),
            inventory_turnover=np.mean([r['inventory_turnover'] for r in all_results]),
            daily_results=combined_daily
        )

        logger.info(f"Simulation complete for {product_id}: SL={avg_result.service_level:.2%}, "
                    f"Avg Stock={avg_result.avg_inventory:.0f}, Cost={avg_result.total_cost:.2f}")

        return avg_result

    def compare_strategies(self,
                            product_id: str,
                            warehouse: str,
                            sales_df: pd.DataFrame,
                            strategies: List[InventoryStrategy],
                            supplier_risk_assessor: Optional[object] = None,
                            supplier_name: Optional[str] = None,
                            mean_lead_time: float = 7,
                            unit_cost: float = 10.0,
                            params: Optional[SimulationParams] = None) -> pd.DataFrame:
        logger.info(f"Comparing {len(strategies)} strategies for {product_id}...")

        results = []

        for i, strategy in enumerate(strategies):
            result = self.simulate_product(
                product_id, warehouse, sales_df, strategy,
                supplier_risk_assessor, supplier_name,
                mean_lead_time, unit_cost=unit_cost, params=params
            )

            results.append({
                'strategy_id': f'Strategy_{i+1}',
                'strategy_type': strategy.strategy_type,
                'reorder_point': strategy.reorder_point,
                'safety_stock': strategy.safety_stock,
                'reorder_qty': strategy.reorder_qty,
                'review_period': strategy.review_period,
                'max_stock': strategy.max_stock,
                'avg_inventory': result.avg_inventory,
                'stockout_days': result.stockout_days,
                'service_level': result.service_level,
                'fill_rate': result.fill_rate,
                'total_cost': result.total_cost,
                'holding_cost': result.holding_cost,
                'stockout_cost': result.stockout_cost,
                'ordering_cost': result.ordering_cost,
                'num_orders': result.num_orders,
                'inventory_turnover': result.inventory_turnover,
                'result_object': result
            })

        results_df = pd.DataFrame(results).sort_values('total_cost')
        return results_df

    def find_optimal_strategy(self,
                               product_id: str,
                               warehouse: str,
                               sales_df: pd.DataFrame,
                               strategy_type: str = 'sS',
                               target_service_level: float = 0.95,
                               supplier_risk_assessor: Optional[object] = None,
                               supplier_name: Optional[str] = None,
                               mean_lead_time: float = 7,
                               unit_cost: float = 10.0,
                               params: Optional[SimulationParams] = None,
                               search_range: Dict = None) -> Dict:
        logger.info(f"Searching for optimal strategy for {product_id}...")

        params = params or self.default_params
        avg_daily_demand = sales_df[sales_df['product_id'] == product_id]['quantity'].mean() if 'product_id' in sales_df.columns else sales_df['quantity'].mean()

        if search_range is None:
            search_range = {
                'reorder_point_min': avg_daily_demand * mean_lead_time * 0.5,
                'reorder_point_max': avg_daily_demand * mean_lead_time * 2.0,
                'safety_stock_min': avg_daily_demand * 3,
                'safety_stock_max': avg_daily_demand * 15,
                'reorder_qty_min': avg_daily_demand * 7,
                'reorder_qty_max': avg_daily_demand * 30
            }

        best_result = None
        best_cost = np.inf
        best_strategy = None

        num_iterations = 20
        results_list = []

        for i in tqdm(range(num_iterations), desc="Searching optimal strategy", leave=False):
            if i < 10:
                reorder_point = np.linspace(
                    search_range['reorder_point_min'],
                    search_range['reorder_point_max'],
                    10
                )[i]
                safety_stock = np.linspace(
                    search_range['safety_stock_min'],
                    search_range['safety_stock_max'],
                    10
                )[i]
                reorder_qty = np.linspace(
                    search_range['reorder_qty_min'],
                    search_range['reorder_qty_max'],
                    10
                )[i]
            else:
                reorder_point = np.random.uniform(
                    search_range['reorder_point_min'],
                    search_range['reorder_point_max']
                )
                safety_stock = np.random.uniform(
                    search_range['safety_stock_min'],
                    search_range['safety_stock_max']
                )
                reorder_qty = np.random.uniform(
                    search_range['reorder_qty_min'],
                    search_range['reorder_qty_max']
                )

            strategy = InventoryStrategy(
                strategy_type=strategy_type,
                reorder_point=reorder_point,
                safety_stock=safety_stock,
                reorder_qty=reorder_qty,
                max_stock=reorder_point + reorder_qty,
                target_service_level=target_service_level
            )

            result = self.simulate_product(
                product_id, warehouse, sales_df, strategy,
                supplier_risk_assessor, supplier_name,
                mean_lead_time, unit_cost=unit_cost, params=params
            )

            results_list.append({
                'iteration': i,
                'reorder_point': reorder_point,
                'safety_stock': safety_stock,
                'reorder_qty': reorder_qty,
                'service_level': result.service_level,
                'total_cost': result.total_cost,
                'meets_target': result.service_level >= target_service_level
            })

            if (result.service_level >= target_service_level and
                    result.total_cost < best_cost):
                best_cost = result.total_cost
                best_result = result
                best_strategy = strategy

        if best_result is None:
            valid_results = [r for r in results_list if r['service_level'] >= target_service_level]
            if valid_results:
                best = min(valid_results, key=lambda x: x['total_cost'])
                best_strategy = InventoryStrategy(
                    strategy_type=strategy_type,
                    reorder_point=best['reorder_point'],
                    safety_stock=best['safety_stock'],
                    reorder_qty=best['reorder_qty'],
                    max_stock=best['reorder_point'] + best['reorder_qty']
                )
                best_result = self.simulate_product(
                    product_id, warehouse, sales_df, best_strategy,
                    supplier_risk_assessor, supplier_name,
                    mean_lead_time, unit_cost=unit_cost, params=params
                )
            else:
                best = max(results_list, key=lambda x: x['service_level'])
                best_strategy = InventoryStrategy(
                    strategy_type=strategy_type,
                    reorder_point=best['reorder_point'],
                    safety_stock=best['safety_stock'],
                    reorder_qty=best['reorder_qty'],
                    max_stock=best['reorder_point'] + best['reorder_qty']
                )
                best_result = self.simulate_product(
                    product_id, warehouse, sales_df, best_strategy,
                    supplier_risk_assessor, supplier_name,
                    mean_lead_time, unit_cost=unit_cost, params=params
                )

        return {
            'optimal_strategy': best_strategy,
            'simulation_result': best_result,
            'search_history': pd.DataFrame(results_list),
            'target_service_level': target_service_level,
            'achieved_service_level': best_result.service_level,
            'total_cost': best_cost
        }

    def simulate_multiple_products(self,
                                    products: List[Tuple[str, str]],
                                    sales_df: pd.DataFrame,
                                    strategy: InventoryStrategy,
                                    supplier_risk_assessor: Optional[object] = None,
                                    supplier_map: Optional[Dict[str, str]] = None,
                                    mean_lead_time: float = 7,
                                    unit_costs: Optional[Dict[str, float]] = None,
                                    params: Optional[SimulationParams] = None) -> pd.DataFrame:
        logger.info(f"Running simulation for {len(products)} product-warehouse combinations...")

        results = []
        for product_id, warehouse in products:
            supplier_name = supplier_map.get(product_id) if supplier_map else None
            unit_cost = unit_costs.get(product_id, 10.0) if unit_costs else 10.0

            result = self.simulate_product(
                product_id, warehouse, sales_df, strategy,
                supplier_risk_assessor, supplier_name,
                mean_lead_time, unit_cost=unit_cost, params=params
            )

            results.append({
                'product_id': product_id,
                'warehouse': warehouse,
                'avg_inventory': result.avg_inventory,
                'service_level': result.service_level,
                'stockout_days': result.stockout_days,
                'fill_rate': result.fill_rate,
                'total_cost': result.total_cost,
                'holding_cost': result.holding_cost,
                'stockout_cost': result.stockout_cost,
                'ordering_cost': result.ordering_cost,
                'inventory_turnover': result.inventory_turnover
            })

        return pd.DataFrame(results)

    def plot_simulation_results(self, result: SimulationResult):
        try:
            import matplotlib.pyplot as plt

            fig, axes = plt.subplots(2, 2, figsize=(14, 10))

            if not result.daily_results.empty:
                for sim in result.daily_results['simulation'].unique():
                    sim_data = result.daily_results[result.daily_results['simulation'] == sim]
                    axes[0, 0].plot(sim_data['day'], sim_data['stock'],
                                    alpha=0.5, label=f'Sim {sim}')

                axes[0, 0].axhline(y=result.strategy.safety_stock, color='r',
                                   linestyle='--', label='Safety Stock')
                axes[0, 0].axhline(y=result.strategy.reorder_point, color='orange',
                                   linestyle='--', label='Reorder Point')
                axes[0, 0].set_xlabel('Day')
                axes[0, 0].set_ylabel('Inventory Level')
                axes[0, 0].set_title(f'Inventory Level Over Time - {result.product_id}')
                axes[0, 0].legend()
                axes[0, 0].grid(True, alpha=0.3)

                stockouts = result.daily_results[result.daily_results['stockout_qty'] > 0]
                if not stockouts.empty:
                    axes[0, 1].bar(stockouts['day'], stockouts['stockout_qty'], alpha=0.7, color='red')
                    axes[0, 1].set_xlabel('Day')
                    axes[0, 1].set_ylabel('Stockout Quantity')
                    axes[0, 1].set_title('Stockout Events')
                    axes[0, 1].grid(True, alpha=0.3)

            cost_components = [result.holding_cost, result.stockout_cost, result.ordering_cost]
            cost_labels = ['Holding Cost', 'Stockout Cost', 'Ordering Cost']
            cost_colors = ['blue', 'red', 'green']
            axes[1, 0].pie(cost_components, labels=cost_labels, colors=cost_colors,
                           autopct='%1.1f%%', startangle=90)
            axes[1, 0].set_title(f'Cost Breakdown - Total: ${result.total_cost:.2f}')

            metrics = [result.avg_inventory, result.max_inventory,
                       result.min_inventory, result.stockout_days]
            metric_labels = ['Avg Stock', 'Max Stock', 'Min Stock', 'Stockout Days']
            axes[1, 1].bar(metric_labels, metrics, color=['blue', 'green', 'orange', 'red'])
            axes[1, 1].set_title('Key Inventory Metrics')
            axes[1, 1].grid(True, alpha=0.3, axis='y')
            for i, v in enumerate(metrics):
                axes[1, 1].text(i, v, f'{v:.1f}', ha='center', va='bottom')

            plt.tight_layout()
            return plt

        except Exception as e:
            logger.warning(f"Could not plot simulation results: {e}")
            return None

    def plot_strategy_comparison(self, comparison_df: pd.DataFrame):
        try:
            import matplotlib.pyplot as plt

            fig, axes = plt.subplots(2, 2, figsize=(14, 10))

            x = np.arange(len(comparison_df))
            width = 0.35

            axes[0, 0].bar(x - width/2, comparison_df['avg_inventory'], width, label='Avg Inventory', color='blue')
            axes[0, 0].set_xlabel('Strategy')
            axes[0, 0].set_ylabel('Units')
            axes[0, 0].set_title('Average Inventory Comparison')
            axes[0, 0].set_xticks(x)
            axes[0, 0].set_xticklabels(comparison_df['strategy_id'], rotation=45)
            axes[0, 0].legend()
            axes[0, 0].grid(True, alpha=0.3, axis='y')

            ax2 = axes[0, 0].twinx()
            ax2.bar(x + width/2, comparison_df['stockout_days'], width, label='Stockout Days', color='red', alpha=0.6)
            ax2.set_ylabel('Stockout Days')
            ax2.legend(loc='upper right')

            axes[0, 1].bar(x, comparison_df['service_level'], color='green', alpha=0.7)
            axes[0, 1].axhline(y=0.95, color='r', linestyle='--', label='95% Target')
            axes[0, 1].set_xlabel('Strategy')
            axes[0, 1].set_ylabel('Service Level')
            axes[0, 1].set_title('Service Level Comparison')
            axes[0, 1].set_xticks(x)
            axes[0, 1].set_xticklabels(comparison_df['strategy_id'], rotation=45)
            axes[0, 1].set_ylim(0.8, 1.02)
            axes[0, 1].legend()
            axes[0, 1].grid(True, alpha=0.3, axis='y')

            axes[1, 0].bar(x, comparison_df['total_cost'], color='purple', alpha=0.7)
            axes[1, 0].set_xlabel('Strategy')
            axes[1, 0].set_ylabel('Total Cost ($)')
            axes[1, 0].set_title('Total Cost Comparison')
            axes[1, 0].set_xticks(x)
            axes[1, 0].set_xticklabels(comparison_df['strategy_id'], rotation=45)
            axes[1, 0].grid(True, alpha=0.3, axis='y')
            for i, v in enumerate(comparison_df['total_cost']):
                axes[1, 0].text(i, v, f'${v:.0f}', ha='center', va='bottom')

            scatter = axes[1, 1].scatter(
                comparison_df['avg_inventory'],
                comparison_df['service_level'],
                s=comparison_df['total_cost'] / 10,
                c=comparison_df['total_cost'],
                cmap='viridis',
                alpha=0.7
            )
            axes[1, 1].set_xlabel('Average Inventory')
            axes[1, 1].set_ylabel('Service Level')
            axes[1, 1].set_title('Cost vs Service Level vs Inventory')
            axes[1, 1].grid(True, alpha=0.3)
            plt.colorbar(scatter, ax=axes[1, 1], label='Total Cost')

            plt.tight_layout()
            return plt

        except Exception as e:
            logger.warning(f"Could not plot strategy comparison: {e}")
            return None
