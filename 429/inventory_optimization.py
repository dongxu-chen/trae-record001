import numpy as np
import pandas as pd
from scipy import stats
from scipy.stats import norm
from typing import Dict, Tuple, List, Optional
from scipy.optimize import minimize
from dataclasses import dataclass, field


class NewsvendorModel:
    def __init__(self, cost_price: float, selling_price: float, salvage_value: float = 0):
        self.cost_price = cost_price
        self.selling_price = selling_price
        self.salvage_value = salvage_value
        
        self.underage_cost = selling_price - cost_price
        self.overage_cost = cost_price - salvage_value
        
        self.critical_fractile = self.underage_cost / (self.underage_cost + self.overage_cost)
    
    def calculate_optimal_order_quantity(self, demand_mean: float, demand_std: float) -> float:
        z_score = norm.ppf(self.critical_fractile)
        optimal_qty = demand_mean + z_score * demand_std
        return max(0, optimal_qty)
    
    def calculate_expected_profit(self, order_qty: float, demand_mean: float, demand_std: float) -> float:
        z = (order_qty - demand_mean) / demand_std
        expected_sales = demand_mean * norm.cdf(z) - demand_std * norm.pdf(z)
        expected_salvage = (order_qty - demand_mean) * norm.cdf(z) + demand_std * norm.pdf(z)
        
        profit = (self.selling_price * expected_sales 
                  + self.salvage_value * expected_salvage 
                  - self.cost_price * order_qty)
        return profit
    
    def calculate_service_level(self, order_qty: float, demand_mean: float, demand_std: float) -> float:
        z = (order_qty - demand_mean) / demand_std
        return norm.cdf(z)


class SafetyStockCalculator:
    def __init__(self, service_level: float = 0.95):
        self.service_level = service_level
        self.z_score = norm.ppf(service_level)
    
    def calculate_safety_stock(self, demand_std: float, lead_time_days: int) -> float:
        return self.z_score * demand_std * np.sqrt(lead_time_days)
    
    def calculate_reorder_point(self, avg_daily_demand: float, lead_time_days: int, 
                                safety_stock: float) -> float:
        demand_during_lead_time = avg_daily_demand * lead_time_days
        return demand_during_lead_time + safety_stock
    
    def calculate_demand_std(self, forecast: pd.DataFrame) -> float:
        forecast_errors = forecast['yhat_upper'] - forecast['yhat']
        return forecast_errors.mean() / self.z_score


class CostParameterEstimator:
    def __init__(self):
        pass
    
    def estimate_from_history(self, historical_sales: pd.DataFrame,
                              historical_inventory: pd.DataFrame = None,
                              historical_orders: pd.DataFrame = None,
                              target_service_level: float = 0.95) -> Dict:
        sales = historical_sales.copy()
        sales['date'] = pd.to_datetime(sales['date'])
        sales = sales.sort_values('date')
        
        daily_demand = sales['sales'].values
        demand_mean = np.mean(daily_demand)
        demand_std = np.std(daily_demand)
        
        avg_inventory = demand_mean * 7
        if historical_inventory is not None and len(historical_inventory) > 0:
            inv = historical_inventory.copy()
            inv['date'] = pd.to_datetime(inv['date'])
            inv = inv.sort_values('date')
            avg_inventory = inv['inventory'].mean()
        
        stockout_rate = 0.05
        stockout_events = 0
        total_periods = len(daily_demand)
        if historical_inventory is not None and len(historical_inventory) > 0:
            merged = inv.merge(sales, on='date', how='inner')
            stockout_events = len(merged[merged['inventory'] <= 0])
            total_periods = len(merged)
            if total_periods > 0:
                stockout_rate = stockout_events / total_periods
        
        order_frequency = 1 / 7
        avg_order_qty = demand_mean * 7
        if historical_orders is not None and len(historical_orders) > 0:
            orders = historical_orders.copy()
            orders['date'] = pd.to_datetime(orders['date'])
            orders = orders.sort_values('date')
            if len(orders) > 1:
                days_span = (orders['date'].max() - orders['date'].min()).days
                if days_span > 0:
                    order_frequency = len(orders) / days_span
            avg_order_qty = orders['quantity'].mean()
        
        holding_cost = avg_order_qty * 0.05
        
        stockout_cost = holding_cost * 15
        
        if stockout_rate > 0:
            stockout_cost = (holding_cost * avg_inventory) / max(stockout_rate, 0.01)
        
        if avg_order_qty > 0:
            implicit_service_level = norm.cdf((avg_order_qty - demand_mean) / max(demand_std, 1))
            implicit_service_level = min(max(implicit_service_level, 0.5), 0.99)
        else:
            implicit_service_level = target_service_level
        
        estimated_safety_stock = norm.ppf(target_service_level) * demand_std
        
        return {
            'demand_mean': demand_mean,
            'demand_std': demand_std,
            'avg_inventory': avg_inventory,
            'stockout_rate': stockout_rate,
            'order_frequency': order_frequency,
            'avg_order_qty': avg_order_qty,
            'estimated_holding_cost': holding_cost,
            'estimated_stockout_cost': stockout_cost,
            'estimated_safety_stock': estimated_safety_stock,
            'implicit_service_level': implicit_service_level
        }
    
    def optimize_cost_parameters(self, historical_sales: pd.DataFrame,
                                 historical_inventory: pd.DataFrame = None,
                                 historical_orders: pd.DataFrame = None,
                                 current_stock: float = 0,
                                 lead_time_days: int = 7,
                                 target_service_level: float = 0.95) -> Dict:
        base_estimation = self.estimate_from_history(
            historical_sales, historical_inventory, 
            historical_orders, target_service_level
        )
        
        demand_mean = base_estimation['demand_mean']
        demand_std = base_estimation['demand_std']
        
        def total_cost_function(params):
            holding_cost_ratio, stockout_cost_ratio = params
            
            holding_cost = holding_cost_ratio * 0.01
            stockout_cost = stockout_cost_ratio * 100
            
            z = norm.ppf(target_service_level)
            safety_stock = z * demand_std * np.sqrt(lead_time_days)
            order_qty = demand_mean * lead_time_days + safety_stock
            
            avg_inventory_level = order_qty / 2 + safety_stock
            holding_cost_total = avg_inventory_level * holding_cost
            
            stockout_prob = 1 - target_service_level
            stockout_cost_total = stockout_prob * stockout_cost
            
            return holding_cost_total + stockout_cost_total
        
        bounds = [(0.1, 10), (1, 50)]
        
        result = minimize(
            total_cost_function, 
            x0=[5, 10],
            bounds=bounds,
            method='L-BFGS-B'
        )
        
        optimal_holding_ratio, optimal_stockout_ratio = result.x
        
        optimal_holding_cost = optimal_holding_ratio * 0.01
        optimal_stockout_cost = optimal_stockout_ratio * 100
        
        z = norm.ppf(target_service_level)
        optimal_safety_stock = z * demand_std * np.sqrt(lead_time_days)
        optimal_order_qty = demand_mean * lead_time_days + optimal_safety_stock
        
        base_estimation.update({
            'optimal_holding_cost': optimal_holding_cost,
            'optimal_stockout_cost': optimal_stockout_cost,
            'optimal_safety_stock': optimal_safety_stock,
            'optimal_order_quantity': optimal_order_qty,
            'minimized_total_cost': result.fun,
            'optimization_success': result.success
        })
        
        return base_estimation


class InventoryOptimizer:
    def __init__(self, cost_price: float, selling_price: float, salvage_value: float = 0, 
                 service_level: float = 0.95, lead_time_days: int = 7):
        self.newsvendor = NewsvendorModel(cost_price, selling_price, salvage_value)
        self.safety_calc = SafetyStockCalculator(service_level)
        self.cost_estimator = CostParameterEstimator()
        self.lead_time_days = lead_time_days
    
    def estimate_costs(self, historical_sales: pd.DataFrame,
                    historical_inventory: pd.DataFrame = None,
                    historical_orders: pd.DataFrame = None,
                    optimize: bool = False) -> Dict:
        if optimize:
            return self.cost_estimator.optimize_cost_parameters(
                historical_sales, historical_inventory, historical_orders,
                current_stock=0,
                lead_time_days=self.lead_time_days,
                target_service_level=self.safety_calc.service_level
            )
        else:
            return self.cost_estimator.estimate_from_history(
                historical_sales, historical_inventory, historical_orders,
                self.safety_calc.service_level
            )
    
    def optimize_inventory(self, forecast: pd.DataFrame, current_stock: float = 0) -> Dict:
        forecast = forecast.copy()
        forecast = forecast.sort_values('ds')
        
        daily_forecast = forecast['yhat'].values
        daily_std = (forecast['yhat_upper'] - forecast['yhat']) / self.safety_calc.z_score
        avg_daily_std = daily_std.mean()
        avg_daily_demand = daily_forecast.mean()
        
        safety_stock = self.safety_calc.calculate_safety_stock(avg_daily_std, self.lead_time_days)
        reorder_point = self.safety_calc.calculate_reorder_point(
            avg_daily_demand, self.lead_time_days, safety_stock
        )
        
        lead_time_demand = avg_daily_demand * self.lead_time_days
        lead_time_std = avg_daily_std * np.sqrt(self.lead_time_days)
        optimal_order_qty = self.newsvendor.calculate_optimal_order_quantity(
            lead_time_demand, lead_time_std
        )
        
        net_stock_needed = max(0, optimal_order_qty - current_stock)
        
        service_level = self.newsvendor.calculate_service_level(
            optimal_order_qty, lead_time_demand, lead_time_std
        )
        
        expected_profit = self.newsvendor.calculate_expected_profit(
            optimal_order_qty, lead_time_demand, lead_time_std
        )
        
        return {
            'avg_daily_demand': avg_daily_demand,
            'avg_daily_std': avg_daily_std,
            'lead_time_days': self.lead_time_days,
            'safety_stock': safety_stock,
            'reorder_point': reorder_point,
            'lead_time_demand': lead_time_demand,
            'optimal_order_quantity': optimal_order_qty,
            'net_order_quantity': net_stock_needed,
            'service_level': service_level,
            'expected_profit': expected_profit,
            'critical_fractile': self.newsvendor.critical_fractile,
            'z_score': self.safety_calc.z_score
        }
    
    def generate_replenishment_plan(self, forecast: pd.DataFrame, current_stock: float, 
                                    review_period_days: int = 7) -> pd.DataFrame:
        forecast = forecast.copy()
        forecast = forecast.sort_values('ds')
        
        plan = []
        stock = current_stock
        
        for i in range(0, len(forecast), review_period_days):
            period_forecast = forecast.iloc[i:i + review_period_days]
            if len(period_forecast) == 0:
                break
            
            period_demand = period_forecast['yhat'].sum()
            period_std = (period_forecast['yhat_upper'] - period_forecast['yhat']).mean() / self.safety_calc.z_score * np.sqrt(len(period_forecast))
            
            safety_stock = self.safety_calc.calculate_safety_stock(
                period_std / np.sqrt(len(period_forecast)), self.lead_time_days
            )
            
            reorder_point = period_forecast['yhat'].mean() * self.lead_time_days + safety_stock
            
            projected_stock = stock - period_demand
            
            if projected_stock <= reorder_point:
                order_qty = max(0, period_demand + safety_stock - stock)
                plan.append({
                    'date': period_forecast['ds'].iloc[0],
                    'action': 'order',
                    'order_quantity': order_qty,
                    'projected_stock_before': stock,
                    'projected_stock_after': stock + order_qty,
                    'expected_demand': period_demand,
                    'safety_stock': safety_stock,
                    'reorder_point': reorder_point
                })
                stock = stock + order_qty - period_demand
            else:
                plan.append({
                    'date': period_forecast['ds'].iloc[0],
                    'action': 'hold',
                    'order_quantity': 0,
                    'projected_stock_before': stock,
                    'projected_stock_after': stock - period_demand,
                    'expected_demand': period_demand,
                    'safety_stock': safety_stock,
                    'reorder_point': reorder_point
                })
                stock = stock - period_demand
        
        return pd.DataFrame(plan)


@dataclass
class LocationNode:
    name: str
    node_type: str
    parent: Optional[str] = None
    current_stock: float = 0
    capacity: float = float('inf')
    holding_cost_rate: float = 1.0
    demand_mean: float = 0
    demand_std: float = 0


@dataclass
class TransferAction:
    from_location: str
    to_location: str
    quantity: float
    cost_per_unit: float = 0.5
    lead_time_days: int = 1


class MultiEchelonInventoryOptimizer:
    def __init__(self, locations: List[LocationNode], service_level: float = 0.95):
        self.locations = {loc.name: loc for loc in locations}
        self.service_level = service_level
        self.z_score = norm.ppf(service_level)
        
    def calculate_location_safety_stock(self, location_name: str, lead_time_days: int) -> float:
        loc = self.locations[location_name]
        return self.z_score * loc.demand_std * np.sqrt(lead_time_days)
    
    def calculate_reorder_point(self, location_name: str, lead_time_days: int) -> float:
        loc = self.locations[location_name]
        demand_during_lead = loc.demand_mean * lead_time_days
        safety_stock = self.calculate_location_safety_stock(location_name, lead_time_days)
        return demand_during_lead + safety_stock
    
    def optimize_allocation(self, total_inventory: float, 
                           location_names: Optional[List[str]] = None) -> Dict[str, float]:
        if location_names is None:
            location_names = list(self.locations.keys())
        
        target_locations = [self.locations[name] for name in location_names 
                           if self.locations[name].demand_mean > 0]
        
        if not target_locations:
            return {name: 0 for name in location_names}
        
        total_demand = sum(loc.demand_mean for loc in target_locations)
        total_std = np.sqrt(sum(loc.demand_std**2 for loc in target_locations))
        
        allocations = {}
        remaining = total_inventory
        
        for i, loc in enumerate(target_locations):
            if i == len(target_locations) - 1:
                allocations[loc.name] = max(0, remaining)
            else:
                weight = loc.demand_mean / total_demand if total_demand > 0 else 1.0/len(target_locations)
                share = total_inventory * weight
                allocations[loc.name] = max(0, min(share, loc.capacity))
                remaining -= allocations[loc.name]
                remaining = max(0, remaining)
        
        for name in location_names:
            if name not in allocations:
                allocations[name] = 0
        
        return allocations
    
    def optimize_transfers(self, warehouse_name: str, 
                          store_names: List[str],
                          transfer_cost: float = 0.5,
                          emergency_cost: float = 2.0) -> List[TransferAction]:
        transfers = []
        
        warehouse = self.locations.get(warehouse_name)
        if warehouse is None:
            return transfers
        
        warehouse_stock = warehouse.current_stock
        
        for store_name in store_names:
            store = self.locations.get(store_name)
            if store is None:
                continue
            
            reorder_point = self.calculate_reorder_point(store_name, store.get('lead_time_days', 1) 
                                                        if isinstance(store, dict) else 1)
            
            if store.current_stock <= reorder_point:
                safety_stock = self.calculate_location_safety_stock(store_name, 1)
                needed = max(0, safety_stock + store.demand_mean * 7 - store.current_stock)
                available = max(0, warehouse_stock - self.calculate_safety_stock_for_warehouse(warehouse_name))
                transfer_qty = min(needed, available)
                
                if transfer_qty > 0:
                    cost = emergency_cost if store.current_stock <= 0 else transfer_cost
                    transfers.append(TransferAction(
                        from_location=warehouse_name,
                        to_location=store_name,
                        quantity=transfer_qty,
                        cost_per_unit=cost
                    ))
                    warehouse_stock -= transfer_qty
        
        return transfers
    
    def calculate_safety_stock_for_warehouse(self, warehouse_name: str) -> float:
        children = [loc for loc in self.locations.values() if loc.parent == warehouse_name]
        
        if not children:
            warehouse = self.locations[warehouse_name]
            return self.z_score * warehouse.demand_std * np.sqrt(7)
        
        total_variance = sum(loc.demand_std**2 for loc in children)
        total_std = np.sqrt(total_variance)
        return self.z_score * total_std * np.sqrt(7)
    
    def generate_multi_echelon_plan(self, forecast: pd.DataFrame, 
                                   warehouse_name: str,
                                   store_names: List[str],
                                   review_period_days: int = 7) -> Dict:
        forecast = forecast.copy()
        forecast = forecast.sort_values('ds')
        
        plan = {
            'warehouse': {},
            'stores': {},
            'transfers': [],
            'total_cost': 0,
            'summary': {}
        }
        
        warehouse = self.locations.get(warehouse_name)
        if warehouse is None:
            return plan
        
        warehouse_lead_time = 7
        warehouse_ss = self.calculate_safety_stock_for_warehouse(warehouse_name)
        warehouse_rp = warehouse.demand_mean * warehouse_lead_time + warehouse_ss
        
        plan['warehouse'] = {
            'name': warehouse_name,
            'current_stock': warehouse.current_stock,
            'safety_stock': warehouse_ss,
            'reorder_point': warehouse_rp,
            'needs_replenishment': warehouse.current_stock <= warehouse_rp,
            'order_quantity': max(0, warehouse_rp - warehouse.current_stock) if warehouse.current_stock <= warehouse_rp else 0
        }
        
        for store_name in store_names:
            store = self.locations.get(store_name)
            if store is None:
                continue
            
            store_ss = self.calculate_location_safety_stock(store_name, 1)
            store_rp = self.calculate_reorder_point(store_name, 1)
            
            plan['stores'][store_name] = {
                'current_stock': store.current_stock,
                'safety_stock': store_ss,
                'reorder_point': store_rp,
                'needs_transfer': store.current_stock <= store_rp,
                'transfer_needed': max(0, store_rp - store.current_stock) if store.current_stock <= store_rp else 0
            }
        
        transfers = self.optimize_transfers(warehouse_name, store_names)
        plan['transfers'] = [
            {
                'from': t.from_location,
                'to': t.to_location,
                'quantity': t.quantity,
                'cost_per_unit': t.cost_per_unit,
                'total_cost': t.quantity * t.cost_per_unit
            }
            for t in transfers
        ]
        
        total_transfer_cost = sum(t['total_cost'] for t in plan['transfers'])
        plan['total_cost'] = total_transfer_cost
        
        total_stores_need = sum(s['transfer_needed'] for s in plan['stores'].values())
        plan['summary'] = {
            'total_transfer_cost': total_transfer_cost,
            'stores_needing_transfer': len([s for s in plan['stores'].values() if s['needs_transfer']]),
            'total_transfer_needed': total_stores_need,
            'warehouse_coverage': min(1.0, plan['warehouse']['current_stock'] / max(total_stores_need, 1))
        }
        
        return plan


@dataclass
class SupplierDelivery:
    supplier_id: str
    supplier_name: str
    order_date: pd.Timestamp
    actual_delivery_date: pd.Timestamp
    promised_delivery_date: pd.Timestamp
    quantity: float
    order_quantity: float
    
    @property
    def actual_lead_time(self) -> int:
        return (self.actual_delivery_date - self.order_date).days
    
    @property
    def promised_lead_time(self) -> int:
        return (self.promised_delivery_date - self.order_date).days
    
    @property
    def deviation(self) -> int:
        return self.actual_lead_time - self.promised_lead_time


class SupplierVariabilityAnalyzer:
    def __init__(self, deliveries: List[SupplierDelivery] = None):
        self.deliveries = deliveries or []
        
    def add_delivery(self, delivery: SupplierDelivery):
        self.deliveries.append(delivery)
    
    def analyze_supplier(self, supplier_id: str) -> Dict:
        supplier_deliveries = [d for d in self.deliveries if d.supplier_id == supplier_id]
        
        if not supplier_deliveries:
            return {'error': 'No delivery data for this supplier'}
        
        actual_lead_times = [d.actual_lead_time for d in supplier_deliveries]
        promised_lead_times = [d.promised_lead_time for d in supplier_deliveries]
        deviations = [d.deviation for d in supplier_deliveries]
        
        avg_actual_lead_time = np.mean(actual_lead_times)
        avg_promised_lead_time = np.mean(promised_lead_times)
        std_lead_time = np.std(actual_lead_times)
        avg_deviation = np.mean(deviations)
        
        on_time_deliveries = len([d for d in supplier_deliveries if d.deviation <= 0])
        on_time_rate = on_time_deliveries / len(supplier_deliveries)
        
        early_deliveries = len([d for d in supplier_deliveries if d.deviation < -2])
        late_deliveries = len([d for d in supplier_deliveries if d.deviation > 2])
        
        variability_score = std_lead_time / avg_actual_lead_time if avg_actual_lead_time > 0 else 0
        
        risk_level = 'low'
        if variability_score > 0.3 or on_time_rate < 0.7:
            risk_level = 'high'
        elif variability_score > 0.15 or on_time_rate < 0.85:
            risk_level = 'medium'
        
        return {
            'supplier_id': supplier_id,
            'supplier_name': supplier_deliveries[0].supplier_name,
            'total_deliveries': len(supplier_deliveries),
            'avg_actual_lead_time': avg_actual_lead_time,
            'avg_promised_lead_time': avg_promised_lead_time,
            'std_lead_time': std_lead_time,
            'avg_deviation': avg_deviation,
            'on_time_rate': on_time_rate,
            'early_rate': early_deliveries / len(supplier_deliveries),
            'late_rate': late_deliveries / len(supplier_deliveries),
            'variability_score': variability_score,
            'risk_level': risk_level,
            'min_lead_time': min(actual_lead_times),
            'max_lead_time': max(actual_lead_times)
        }
    
    def calculate_adjusted_safety_stock(self, supplier_id: str, 
                                       base_safety_stock: float,
                                       base_lead_time: int) -> Dict:
        analysis = self.analyze_supplier(supplier_id)
        
        if 'error' in analysis:
            return {'adjusted_safety_stock': base_safety_stock}
        
        avg_lead_time = analysis['avg_actual_lead_time']
        std_lead_time = analysis['std_lead_time']
        
        z = norm.ppf(0.95)
        base_demand_std = base_safety_stock / (z * np.sqrt(base_lead_time))
        
        adjusted_lead_time = avg_lead_time + 1.645 * std_lead_time
        adjusted_safety_stock = z * base_demand_std * np.sqrt(adjusted_lead_time)
        
        buffer_factor = 1.0
        if analysis['risk_level'] == 'high':
            buffer_factor = 1.3
        elif analysis['risk_level'] == 'medium':
            buffer_factor = 1.15
        
        final_safety_stock = adjusted_safety_stock * buffer_factor
        
        return {
            'base_safety_stock': base_safety_stock,
            'adjusted_lead_time': adjusted_lead_time,
            'adjusted_safety_stock': adjusted_safety_stock,
            'buffer_factor': buffer_factor,
            'final_safety_stock': final_safety_stock,
            'increase_percentage': (final_safety_stock - base_safety_stock) / base_safety_stock * 100 if base_safety_stock > 0 else 0,
            'risk_level': analysis['risk_level'],
            'on_time_rate': analysis['on_time_rate'],
            'variability_score': analysis['variability_score']
        }
    
    def get_all_suppliers_analysis(self) -> pd.DataFrame:
        supplier_ids = list(set(d.supplier_id for d in self.deliveries))
        results = []
        
        for supplier_id in supplier_ids:
            analysis = self.analyze_supplier(supplier_id)
            if 'error' not in analysis:
                results.append(analysis)
        
        return pd.DataFrame(results)
    
    def rank_suppliers_by_risk(self) -> List[Dict]:
        analysis_df = self.get_all_suppliers_analysis()
        if len(analysis_df) == 0:
            return []
        
        analysis_df = analysis_df.sort_values('variability_score', ascending=False)
        return analysis_df.to_dict('records')


@dataclass
class HealthMetric:
    name: str
    value: float
    weight: float
    score: float
    max_value: float
    description: str


class InventoryHealthScorer:
    def __init__(self):
        pass
    
    def calculate_turnover_rate(self, cost_of_goods_sold: float, 
                               average_inventory: float) -> float:
        if average_inventory == 0:
            return 0
        return cost_of_goods_sold / average_inventory
    
    def calculate_stockout_rate(self, stockout_events: int, 
                               total_periods: int) -> float:
        if total_periods == 0:
            return 0
        return stockout_events / total_periods
    
    def calculate_obsolete_rate(self, obsolete_inventory: float, 
                               total_inventory: float) -> float:
        if total_inventory == 0:
            return 0
        return obsolete_inventory / total_inventory
    
    def calculate_fill_rate(self, fulfilled_orders: int, 
                           total_orders: int) -> float:
        if total_orders == 0:
            return 1.0
        return fulfilled_orders / total_orders
    
    def calculate_days_of_supply(self, current_inventory: float, 
                                avg_daily_demand: float) -> float:
        if avg_daily_demand == 0:
            return float('inf')
        return current_inventory / avg_daily_demand
    
    def score_turnover(self, turnover_rate: float, 
                      industry_average: float = 12.0) -> HealthMetric:
        if industry_average > 0:
            ratio = turnover_rate / industry_average
        else:
            ratio = 1.0
        
        if ratio >= 1.5:
            score = 100
        elif ratio >= 1.0:
            score = 85
        elif ratio >= 0.7:
            score = 70
        elif ratio >= 0.5:
            score = 50
        elif ratio >= 0.3:
            score = 30
        else:
            score = 10
        
        return HealthMetric(
            name='库存周转率',
            value=turnover_rate,
            weight=0.25,
            score=score,
            max_value=100,
            description=f'库存周转率 {turnover_rate:.2f}次/年，行业平均 {industry_average}次/年'
        )
    
    def score_stockout(self, stockout_rate: float, 
                      target_rate: float = 0.02) -> HealthMetric:
        if target_rate > 0:
            ratio = stockout_rate / target_rate
        else:
            ratio = 0
        
        if ratio <= 0.5:
            score = 100
        elif ratio <= 1.0:
            score = 80
        elif ratio <= 1.5:
            score = 60
        elif ratio <= 2.0:
            score = 40
        elif ratio <= 3.0:
            score = 20
        else:
            score = 10
        
        return HealthMetric(
            name='缺货率',
            value=stockout_rate,
            weight=0.30,
            score=score,
            max_value=100,
            description=f'缺货率 {stockout_rate:.2%}，目标 {target_rate:.2%}'
        )
    
    def score_obsolete(self, obsolete_rate: float, 
                      target_rate: float = 0.05) -> HealthMetric:
        if target_rate > 0:
            ratio = obsolete_rate / target_rate
        else:
            ratio = 0
        
        if ratio <= 0.3:
            score = 100
        elif ratio <= 0.7:
            score = 85
        elif ratio <= 1.0:
            score = 70
        elif ratio <= 1.5:
            score = 50
        elif ratio <= 2.0:
            score = 30
        else:
            score = 10
        
        return HealthMetric(
            name='滞销率',
            value=obsolete_rate,
            weight=0.20,
            score=score,
            max_value=100,
            description=f'滞销率 {obsolete_rate:.2%}，目标 {target_rate:.2%}'
        )
    
    def score_fill_rate(self, fill_rate: float, 
                       target_rate: float = 0.95) -> HealthMetric:
        if fill_rate >= target_rate:
            score = 100
        elif fill_rate >= 0.9:
            score = 85
        elif fill_rate >= 0.85:
            score = 70
        elif fill_rate >= 0.8:
            score = 50
        elif fill_rate >= 0.7:
            score = 30
        else:
            score = 15
        
        return HealthMetric(
            name='订单满足率',
            value=fill_rate,
            weight=0.15,
            score=score,
            max_value=100,
            description=f'订单满足率 {fill_rate:.2%}，目标 {target_rate:.2%}'
        )
    
    def score_days_of_supply(self, days_of_supply: float, 
                            min_days: int = 7, 
                            max_days: int = 30) -> HealthMetric:
        if days_of_supply == float('inf'):
            score = 50
        elif days_of_supply < min_days:
            score = 30
        elif days_of_supply <= max_days:
            score = 100 - (days_of_supply - min_days) / (max_days - min_days) * 20
            score = max(80, min(100, score))
        elif days_of_supply <= max_days * 1.5:
            score = 70
        elif days_of_supply <= max_days * 2:
            score = 50
        else:
            score = 30
        
        return HealthMetric(
            name='库存天数',
            value=days_of_supply,
            weight=0.10,
            score=score,
            max_value=100,
            description=f'库存可供应 {days_of_supply:.1f}天，目标 {min_days}-{max_days}天'
        )
    
    def calculate_health_score(self, turnover_rate: float,
                               stockout_rate: float,
                               obsolete_rate: float,
                               fill_rate: float = 0.95,
                               days_of_supply: float = 15,
                               industry_turnover: float = 12.0,
                               target_stockout_rate: float = 0.02,
                               target_obsolete_rate: float = 0.05,
                               target_fill_rate: float = 0.95,
                               min_days_supply: int = 7,
                               max_days_supply: int = 30) -> Dict:
        metrics = [
            self.score_turnover(turnover_rate, industry_turnover),
            self.score_stockout(stockout_rate, target_stockout_rate),
            self.score_obsolete(obsolete_rate, target_obsolete_rate),
            self.score_fill_rate(fill_rate, target_fill_rate),
            self.score_days_of_supply(days_of_supply, min_days_supply, max_days_supply)
        ]
        
        total_weight = sum(m.weight for m in metrics)
        weighted_score = sum(m.weight * m.score for m in metrics) / total_weight if total_weight > 0 else 0
        
        if weighted_score >= 85:
            health_level = '优秀'
            health_color = '#00cc96'
        elif weighted_score >= 70:
            health_level = '良好'
            health_color = '#636efa'
        elif weighted_score >= 50:
            health_level = '中等'
            health_color = '#ffa500'
        elif weighted_score >= 30:
            health_level = '较差'
            health_color = '#ff6b6b'
        else:
            health_level = '危险'
            health_color = '#c92a2a'
        
        return {
            'overall_score': weighted_score,
            'health_level': health_level,
            'health_color': health_color,
            'metrics': [
                {
                    'name': m.name,
                    'value': m.value,
                    'weight': m.weight,
                    'score': m.score,
                    'description': m.description
                }
                for m in metrics
            ],
            'recommendations': self._generate_recommendations(metrics),
            'total_weight': total_weight
        }
    
    def _generate_recommendations(self, metrics: List[HealthMetric]) -> List[str]:
        recommendations = []
        
        turnover = next((m for m in metrics if m.name == '库存周转率'), None)
        if turnover and turnover.score < 70:
            recommendations.append(f'库存周转率偏低（得分{turnover.score}），建议优化补货策略，减少库存积压')
        
        stockout = next((m for m in metrics if m.name == '缺货率'), None)
        if stockout and stockout.score < 70:
            recommendations.append(f'缺货率过高（得分{stockout.score}），建议增加安全库存或优化补货点')
        
        obsolete = next((m for m in metrics if m.name == '滞销率'), None)
        if obsolete and obsolete.score < 70:
            recommendations.append(f'滞销率偏高（得分{obsolete.score}），建议清理滞销商品，减少采购量')
        
        fill_rate = next((m for m in metrics if m.name == '订单满足率'), None)
        if fill_rate and fill_rate.score < 85:
            recommendations.append(f'订单满足率偏低（得分{fill_rate.score}），建议提高库存可用性')
        
        days = next((m for m in metrics if m.name == '库存天数'), None)
        if days:
            if days.value < 7:
                recommendations.append('库存天数过低，存在缺货风险，建议增加补货频率')
            elif days.value > 30:
                recommendations.append('库存天数过高，占用资金过多，建议优化订货量')
        
        if not recommendations:
            recommendations.append('库存健康状况良好，继续保持当前策略')
        
        return recommendations
    
    def from_inventory_data(self, sales_data: pd.DataFrame,
                           inventory_data: pd.DataFrame,
                           orders_data: pd.DataFrame = None,
                           cost_price: float = 50.0) -> Dict:
        sales = sales_data.copy()
        sales['date'] = pd.to_datetime(sales['date'])
        sales = sales.sort_values('date')
        
        inv = inventory_data.copy()
        inv['date'] = pd.to_datetime(inv['date'])
        inv = inv.sort_values('date')
        
        total_sales = sales['sales'].sum()
        cost_of_goods_sold = total_sales * cost_price
        
        avg_inventory = inv['inventory'].mean()
        avg_daily_demand = sales['sales'].mean()
        
        days_of_supply = self.calculate_days_of_supply(avg_inventory, avg_daily_demand)
        turnover_rate = self.calculate_turnover_rate(cost_of_goods_sold, avg_inventory) if avg_inventory > 0 else 0
        
        stockout_events = len(inv[inv['inventory'] <= 0])
        stockout_rate = self.calculate_stockout_rate(stockout_events, len(inv))
        
        obsolete_threshold = avg_daily_demand * 60
        obsolete_inventory = inv[inv['inventory'] > obsolete_threshold]['inventory'].sum() if len(inv) > 0 else 0
        total_inventory = inv['inventory'].sum()
        obsolete_rate = self.calculate_obsolete_rate(obsolete_inventory, total_inventory)
        
        fill_rate = 0.95
        if orders_data is not None and len(orders_data) > 0:
            orders = orders_data.copy()
            if 'fulfilled' in orders.columns:
                fulfilled_orders = orders[orders['fulfilled'] == True]
                fill_rate = len(fulfilled_orders) / len(orders)
        
        return self.calculate_health_score(
            turnover_rate=turnover_rate,
            stockout_rate=stockout_rate,
            obsolete_rate=obsolete_rate,
            fill_rate=fill_rate,
            days_of_supply=days_of_supply
        )
