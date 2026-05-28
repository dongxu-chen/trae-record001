import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum


class ScenarioType(Enum):
    NORMAL = "normal"
    DEMAND_SURGE = "demand_surge"
    SUPPLY_DISRUPTION = "supply_disruption"
    HOLIDAY_PEAK = "holiday_peak"
    EXTREME_SCENARIO = "extreme_scenario"
    PANIC_BUYING = "panic_buying"


@dataclass
class ScenarioConfig:
    name: str
    scenario_type: ScenarioType
    demand_multiplier: float = 1.0
    demand_std_multiplier: float = 1.0
    lead_time_multiplier: float = 1.0
    description: str = ""
    
    @classmethod
    def get_default_scenarios(cls) -> List['ScenarioConfig']:
        return [
            cls(
                name="正常场景",
                scenario_type=ScenarioType.NORMAL,
                demand_multiplier=1.0,
                demand_std_multiplier=1.0,
                lead_time_multiplier=1.0,
                description="基于历史数据的正常需求波动"
            ),
            cls(
                name="需求激增 (1.5x)",
                scenario_type=ScenarioType.DEMAND_SURGE,
                demand_multiplier=1.5,
                demand_std_multiplier=1.3,
                lead_time_multiplier=1.0,
                description="市场需求突然增加50%"
            ),
            cls(
                name="供应中断 (交期2x)",
                scenario_type=ScenarioType.SUPPLY_DISRUPTION,
                demand_multiplier=1.0,
                demand_std_multiplier=1.0,
                lead_time_multiplier=2.0,
                description="供应链交期延长一倍"
            ),
            cls(
                name="节假日高峰",
                scenario_type=ScenarioType.HOLIDAY_PEAK,
                demand_multiplier=2.0,
                demand_std_multiplier=1.5,
                lead_time_multiplier=1.3,
                description="电商大促期间的极端需求"
            ),
            cls(
                name="极端场景 (需求3x, 交期3x)",
                scenario_type=ScenarioType.EXTREME_SCENARIO,
                demand_multiplier=3.0,
                demand_std_multiplier=2.0,
                lead_time_multiplier=3.0,
                description="极端恶劣场景：需求激增且供应严重延迟"
            ),
            cls(
                name="恐慌性购买",
                scenario_type=ScenarioType.PANIC_BUYING,
                demand_multiplier=2.5,
                demand_std_multiplier=2.5,
                lead_time_multiplier=1.5,
                description="突发因素导致的恐慌性抢购"
            )
        ]


@dataclass
class ScenarioResult:
    scenario_name: str
    scenario_config: ScenarioConfig
    simulation_result: 'SimulationResult'
    risk_assessment: Dict = field(default_factory=dict)


@dataclass
class SimulationResult:
    days: int
    num_simulations: int
    stock_history: np.ndarray
    demand_history: np.ndarray
    stockout_days: np.ndarray
    average_stock: float
    stockout_rate: float
    average_cost: float
    stockout_risk: float
    daily_metrics: pd.DataFrame
    scenario_type: ScenarioType = ScenarioType.NORMAL


class InventorySimulator:
    def __init__(self, forecast: pd.DataFrame, initial_stock: float, lead_time_days: int, 
                 order_quantity: float, reorder_point: float, safety_stock: float,
                 holding_cost: float = 1.0, stockout_cost: float = 10.0):
        self.forecast = forecast.copy()
        self.initial_stock = initial_stock
        self.base_lead_time_days = lead_time_days
        self.lead_time_std = max(1, int(lead_time_days * 0.2))
        self.base_order_quantity = order_quantity
        self.reorder_point = reorder_point
        self.safety_stock = safety_stock
        self.holding_cost = holding_cost
        self.stockout_cost = stockout_cost
        
        self.forecast = self.forecast.sort_values('ds')
        self.base_demand_mean = self.forecast['yhat'].values
        self.base_demand_std = ((self.forecast['yhat_upper'] - self.forecast['yhat']).values / 1.645)
        self.base_demand_std = np.maximum(self.base_demand_std, 1e-6)
        self.n_days = len(self.forecast)
        
        self.holiday_dates = self._identify_holiday_periods()
    
    def _identify_holiday_periods(self) -> List[int]:
        holiday_indices = []
        dates = self.forecast['ds']
        
        for i, date in enumerate(dates):
            month = date.month
            day = date.day
            
            if (month == 6 and 15 <= day <= 20):
                holiday_indices.append(i)
            elif (month == 11 and 8 <= day <= 13):
                holiday_indices.append(i)
            elif (month == 12 and 10 <= day <= 14):
                holiday_indices.append(i)
            elif (month == 1 and 15 <= day <= 25):
                holiday_indices.append(i)
            elif (month == 2 and 5 <= day <= 15):
                holiday_indices.append(i)
            elif (month == 10 and 1 <= day <= 7):
                holiday_indices.append(i)
        
        return holiday_indices
    
    def _get_scenario_parameters(self, scenario: ScenarioConfig, day: int) -> Tuple[float, float, int]:
        demand_multiplier = scenario.demand_multiplier
        demand_std_multiplier = scenario.demand_std_multiplier
        lead_time_multiplier = scenario.lead_time_multiplier
        
        if scenario.scenario_type == ScenarioType.HOLIDAY_PEAK:
            if day in self.holiday_dates:
                demand_multiplier *= 1.5
                demand_std_multiplier *= 1.3
        
        if scenario.scenario_type == ScenarioType.PANIC_BUYING:
            if day > self.n_days * 0.3 and day < self.n_days * 0.5:
                demand_multiplier *= 1.5
                demand_std_multiplier *= 1.5
        
        adjusted_lead_time = int(self.base_lead_time_days * lead_time_multiplier)
        adjusted_lead_time = max(1, adjusted_lead_time)
        
        return demand_multiplier, demand_std_multiplier, adjusted_lead_time
    
    def run_single_simulation(self, random_seed: int = None, 
                            scenario: Optional[ScenarioConfig] = None) -> Tuple[np.ndarray, np.ndarray, List]:
        if scenario is None:
            scenario = ScenarioConfig.get_default_scenarios()[0]
        
        if random_seed is not None:
            np.random.seed(random_seed)
        
        stock = self.initial_stock
        stock_history = np.zeros(self.n_days)
        demand_history = np.zeros(self.n_days)
        orders_pending = []
        
        for day in range(self.n_days):
            demand_mult, demand_std_mult, lead_time = self._get_scenario_parameters(scenario, day)
            
            base_demand = self.base_demand_mean[day]
            base_std = self.base_demand_std[day]
            
            actual_mean = base_demand * demand_mult
            actual_std = base_std * demand_std_mult
            
            actual_demand = max(0, np.random.normal(actual_mean, actual_std))
            demand_history[day] = actual_demand
            
            new_orders = []
            for order_day, order_qty in orders_pending:
                if order_day <= day:
                    stock += order_qty
                else:
                    new_orders.append((order_day, order_qty))
            orders_pending = new_orders
            
            stock = max(0, stock - actual_demand)
            stock_history[day] = stock
            
            if stock <= self.reorder_point and not any(od > day for od, _ in orders_pending):
                lead_time_variation = max(1, int(np.random.normal(lead_time, self.lead_time_std)))
                arrival_day = day + lead_time_variation
                
                order_qty = self.base_order_quantity * scenario.demand_multiplier
                
                orders_pending.append((arrival_day, order_qty))
        
        return stock_history, demand_history, orders_pending
    
    def run_simulations(self, num_simulations: int = 100,
                       scenario: Optional[ScenarioConfig] = None) -> SimulationResult:
        if scenario is None:
            scenario = ScenarioConfig.get_default_scenarios()[0]
        
        all_stock_histories = []
        all_demand_histories = []
        stockout_rates = []
        total_costs = []
        
        for i in range(num_simulations):
            stock_history, demand_history, _ = self.run_single_simulation(
                random_seed=i, scenario=scenario
            )
            all_stock_histories.append(stock_history)
            all_demand_histories.append(demand_history)
            
            stockout_days = np.sum(stock_history <= 0)
            stockout_rates.append(stockout_days / self.n_days)
            
            avg_stock = np.mean(stock_history)
            holding_cost_total = avg_stock * self.holding_cost
            stockout_cost_total = stockout_days * self.stockout_cost
            total_costs.append(holding_cost_total + stockout_cost_total)
        
        stock_history_array = np.array(all_stock_histories)
        demand_history_array = np.array(all_demand_histories)
        
        avg_stock_per_day = np.mean(stock_history_array, axis=0)
        std_stock_per_day = np.std(stock_history_array, axis=0)
        p5_stock_per_day = np.percentile(stock_history_array, 5, axis=0)
        p95_stock_per_day = np.percentile(stock_history_array, 95, axis=0)
        p99_stock_per_day = np.percentile(stock_history_array, 99, axis=0)
        p1_stock_per_day = np.percentile(stock_history_array, 1, axis=0)
        stockout_prob_per_day = np.mean(stock_history_array <= 0, axis=0)
        
        daily_metrics = pd.DataFrame({
            'date': self.forecast['ds'].values,
            'avg_stock': avg_stock_per_day,
            'std_stock': std_stock_per_day,
            'p5_stock': p5_stock_per_day,
            'p95_stock': p95_stock_per_day,
            'p99_stock': p99_stock_per_day,
            'p1_stock': p1_stock_per_day,
            'stockout_prob': stockout_prob_per_day,
            'forecast_demand': self.base_demand_mean * scenario.demand_multiplier
        })
        
        stockout_days = np.sum(stock_history_array <= 0, axis=1)
        avg_stockout_days = np.mean(stockout_days)
        overall_stockout_rate = np.mean(stockout_rates)
        overall_avg_stock = np.mean(stock_history_array)
        overall_avg_cost = np.mean(total_costs)
        stockout_risk = np.mean(np.any(stock_history_array <= 0, axis=0))
        high_risk_days = np.sum(stockout_risk > 0.1)
        
        return SimulationResult(
            days=self.n_days,
            num_simulations=num_simulations,
            stock_history=stock_history_array,
            demand_history=demand_history_array,
            stockout_days=stockout_days,
            average_stock=overall_avg_stock,
            stockout_rate=overall_stockout_rate,
            average_cost=overall_avg_cost,
            stockout_risk=overall_stockout_rate,
            daily_metrics=daily_metrics,
            scenario_type=scenario.scenario_type
        )
    
    def run_multiple_scenarios(self, scenarios: List[ScenarioConfig], 
                             num_simulations: int = 100) -> List[ScenarioResult]:
        results = []
        
        for scenario in scenarios:
            sim_result = self.run_simulations(
                num_simulations=num_simulations,
                scenario=scenario
            )
            
            risk_levels = self.calculate_risk_levels(sim_result)
            
            risk_assessment = {
                'risk_levels': risk_levels,
                'is_acceptable': sim_result.stockout_rate < 0.05,
                'recommended_safety_stock_increase': max(0, 
                    int((sim_result.stockout_rate - 0.05) * self.safety_stock * 10)
                )
            }
            
            results.append(ScenarioResult(
                scenario_name=scenario.name,
                scenario_config=scenario,
                simulation_result=sim_result,
                risk_assessment=risk_assessment
            ))
        
        return results
    
    def calculate_risk_levels(self, simulation_result: SimulationResult) -> Dict:
        daily_metrics = simulation_result.daily_metrics
        
        high_risk = daily_metrics[daily_metrics['stockout_prob'] > 0.2]
        medium_risk = daily_metrics[(daily_metrics['stockout_prob'] > 0.05) & (daily_metrics['stockout_prob'] <= 0.2)]
        low_risk = daily_metrics[daily_metrics['stockout_prob'] <= 0.05]
        
        extreme_risk = daily_metrics[daily_metrics['stockout_prob'] > 0.5]
        
        return {
            'high_risk_days': len(high_risk),
            'medium_risk_days': len(medium_risk),
            'low_risk_days': len(low_risk),
            'extreme_risk_days': len(extreme_risk),
            'high_risk_periods': high_risk[['date', 'stockout_prob']].to_dict('records') if len(high_risk) else [],
            'medium_risk_periods': medium_risk[['date', 'stockout_prob']].to_dict('records') if len(medium_risk) else [],
            'extreme_risk_periods': extreme_risk[['date', 'stockout_prob']].to_dict('records') if len(extreme_risk) else []
        }
    
    def calculate_extreme_stockout_probability(self, num_simulations: int = 1000) -> Dict:
        extreme_scenario = ScenarioConfig(
            name="极端压力测试",
            scenario_type=ScenarioType.EXTREME_SCENARIO,
            demand_multiplier=3.0,
            demand_std_multiplier=2.5,
            lead_time_multiplier=3.0
        )
        
        sim_result = self.run_simulations(
            num_simulations=num_simulations,
            scenario=extreme_scenario
        )
        
        stockout_days_dist = sim_result.stockout_days
        
        prob_more_than_5_days = np.mean(stockout_days_dist > 5)
        prob_more_than_10_days = np.mean(stockout_days_dist > 10)
        prob_more_than_20_days = np.mean(stockout_days_dist > 20)
        
        max_stockout_days = np.max(stockout_days_dist)
        min_stockout_days = np.min(stockout_days_dist)
        median_stockout_days = np.median(stockout_days_dist)
        
        return {
            'scenario': '极端压力测试',
            'num_simulations': num_simulations,
            'avg_stockout_days': np.mean(stockout_days_dist),
            'median_stockout_days': median_stockout_days,
            'max_stockout_days': max_stockout_days,
            'min_stockout_days': min_stockout_days,
            'prob_more_than_5_days': prob_more_than_5_days,
            'prob_more_than_10_days': prob_more_than_10_days,
            'prob_more_than_20_days': prob_more_than_20_days,
            'stockout_rate': sim_result.stockout_rate,
            'average_stock': sim_result.average_stock,
            'average_cost': sim_result.average_cost
        }


def run_what_if_analysis(forecast: pd.DataFrame, initial_stock: float, 
                      lead_time_options: List[int], 
                      order_quantity_multipliers: List[float],
                      service_levels: List[float]) -> pd.DataFrame:
    results = []
    
    from inventory_optimization import InventoryOptimizer
    
    for lead_time in lead_time_options:
        for multiplier in order_quantity_multipliers:
            for service_level in service_levels:
                optimizer = InventoryOptimizer(
                    cost_price=10, selling_price=20, service_level=service_level,
                    lead_time_days=lead_time
                )
                opt_result = optimizer.optimize_inventory(forecast, current_stock=initial_stock)
                
                adjusted_order_qty = opt_result['optimal_order_quantity'] * multiplier
                
                simulator = InventorySimulator(
                    forecast=forecast,
                    initial_stock=initial_stock,
                    lead_time_days=lead_time,
                    order_quantity=adjusted_order_qty,
                    reorder_point=opt_result['reorder_point'],
                    safety_stock=opt_result['safety_stock'],
                    holding_cost=1.0,
                    stockout_cost=10.0
                )
                
                sim_result = simulator.run_simulations(num_simulations=50)
                
                results.append({
                    'lead_time_days': lead_time,
                    'order_multiplier': multiplier,
                    'service_level': service_level,
                    'optimal_order_qty': opt_result['optimal_order_quantity'],
                    'adjusted_order_qty': adjusted_order_qty,
                    'safety_stock': opt_result['safety_stock'],
                    'reorder_point': opt_result['reorder_point'],
                    'avg_stock': sim_result.average_stock,
                    'stockout_rate': sim_result.stockout_rate,
                    'avg_cost': sim_result.average_cost
                })
    
    return pd.DataFrame(results)


def generate_scenario_comparison(scenario_results: List[ScenarioResult]) -> pd.DataFrame:
    comparison_data = []
    
    for result in scenario_results:
        sim = result.simulation_result
        risk = result.risk_assessment['risk_levels']
        
        comparison_data.append({
            '场景名称': result.scenario_name,
            '场景描述': result.scenario_config.description,
            '需求倍数': result.scenario_config.demand_multiplier,
            '交期倍数': result.scenario_config.lead_time_multiplier,
            '平均库存': f"{sim.average_stock:.1f}",
            '缺货率': f"{sim.stockout_rate:.2%}",
            '平均成本': f"{sim.average_cost:.2f}",
            '高风险天数': risk['high_risk_days'],
            '中风险天数': risk['medium_risk_days'],
            '低风险天数': risk['low_risk_days'],
            '是否可接受': '✅ 是' if result.risk_assessment['is_acceptable'] else '❌ 否'
        })
    
    return pd.DataFrame(comparison_data)
