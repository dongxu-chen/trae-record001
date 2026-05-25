import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from logit_elasticity_model import PriceElasticityModel
from cross_elasticity import CrossElasticityAnalyzer


class PricingStrategyType(Enum):
    FIXED_PRICE = 'fixed_price'
    FOLLOW_COMPETITOR = 'follow_competitor'
    DYNAMIC_MARGIN = 'dynamic_margin'
    ELASTICITY_BASED = 'elasticity_based'
    TIME_BASED = 'time_based'


@dataclass
class PricingStrategy:
    strategy_type: PricingStrategyType
    parameters: Dict = field(default_factory=dict)
    product_id: Optional[int] = None
    

class DynamicPricingSimulator:
    
    def __init__(
        self,
        product_model: Optional[PriceElasticityModel] = None,
        cross_analyzer: Optional[CrossElasticityAnalyzer] = None,
        variable_cost: float = 0.0,
        fixed_cost: float = 0.0
    ):
        self.product_model = product_model
        self.cross_analyzer = cross_analyzer
        self.variable_cost = variable_cost
        self.fixed_cost = fixed_cost
        
    def _calculate_price(
        self,
        strategy: PricingStrategy,
        current_state: Dict,
        day_idx: int
    ) -> float:
        base_price = current_state.get('base_price', 100.0)
        competitor_price = current_state.get('competitor_price', base_price)
        current_elasticity = current_state.get('elasticity', -2.0)
        demand_forecast = current_state.get('demand_forecast', None)
        
        if strategy.strategy_type == PricingStrategyType.FIXED_PRICE:
            return strategy.parameters.get('price', base_price)
            
        elif strategy.strategy_type == PricingStrategyType.FOLLOW_COMPETITOR:
            price_floor = strategy.parameters.get('price_floor', base_price * 0.8)
            price_ceiling = strategy.parameters.get('price_ceiling', base_price * 1.2)
            markup = strategy.parameters.get('markup', 0.0)
            lag_days = strategy.parameters.get('lag_days', 0)
            
            target_price = competitor_price * (1 + markup)
            target_price = max(price_floor, min(price_ceiling, target_price))
            
            return target_price
            
        elif strategy.strategy_type == PricingStrategyType.DYNAMIC_MARGIN:
            target_margin = strategy.parameters.get('target_margin', 0.3)
            variable_cost = strategy.parameters.get('variable_cost', self.variable_cost)
            price_floor = strategy.parameters.get('price_floor', base_price * 0.7)
            
            target_price = variable_cost / (1 - target_margin)
            target_price = max(price_floor, target_price)
            
            return target_price
            
        elif strategy.strategy_type == PricingStrategyType.ELASTICITY_BASED:
            optimal_markup = -1 / (1 + current_elasticity) if current_elasticity < -1 else 0.2
            max_markup = strategy.parameters.get('max_markup', 0.5)
            min_markup = strategy.parameters.get('min_markup', 0.1)
            
            optimal_markup = max(min_markup, min(max_markup, optimal_markup))
            variable_cost = strategy.parameters.get('variable_cost', self.variable_cost)
            target_price = variable_cost * (1 + optimal_markup)
            
            price_floor = strategy.parameters.get('price_floor', base_price * 0.8)
            price_ceiling = strategy.parameters.get('price_ceiling', base_price * 1.2)
            target_price = max(price_floor, min(price_ceiling, target_price))
            
            return target_price
            
        elif strategy.strategy_type == PricingStrategyType.TIME_BASED:
            time_pattern = strategy.parameters.get('time_pattern', {})
            day_of_week = current_state.get('day_of_week', 0)
            month = current_state.get('month', 1)
            
            key = f'dow_{day_of_week}'
            if key in time_pattern:
                adjustment = time_pattern[key]
            elif f'month_{month}' in time_pattern:
                adjustment = time_pattern[f'month_{month}']
            else:
                adjustment = strategy.parameters.get('default_adjustment', 0.0)
            
            return base_price * (1 + adjustment)
            
        else:
            return base_price
    
    def simulate_strategy(
        self,
        df: pd.DataFrame,
        strategy: PricingStrategy,
        n_days: int = 90,
        start_date: Optional[pd.Timestamp] = None,
        include_cross_impact: bool = True
    ) -> Dict:
        if self.product_model is None:
            raise ValueError("Product model is required for simulation")
        
        df_sorted = df.sort_values('date').copy()
        
        if start_date is None:
            start_date = df_sorted['date'].iloc[0]
        
        base_price = strategy.parameters.get('base_price', df_sorted['effective_price'].mean())
        avg_sales = df_sorted['sales_quantity'].mean()
        avg_competitor_price = df_sorted['competitor_price'].mean()
        
        simulation_dates = pd.date_range(start=start_date, periods=n_days, freq='D')
        
        simulation_results = []
        current_price = base_price
        inventory = avg_sales * 7
        
        for day_idx, date in enumerate(simulation_dates):
            day_of_week = date.dayofweek
            month = date.month
            is_weekend = 1 if day_of_week >= 5 else 0
            
            competitor_price = avg_competitor_price * (1 + np.random.normal(0, 0.02))
            
            current_state = {
                'base_price': base_price,
                'competitor_price': competitor_price,
                'day_of_week': day_of_week,
                'month': month,
                'is_weekend': is_weekend,
                'inventory': inventory,
                'date': date
            }
            
            elasticity_df = self.product_model.calculate_price_elasticity(
                df_sorted, 
                price_range=(base_price * 0.8, base_price * 1.2),
                n_points=50,
                include_bootstrap_ci=False
            )
            current_state['elasticity'] = elasticity_df['point_elasticity'].mean()
            
            new_price = self._calculate_price(strategy, current_state, day_idx)
            
            price_change_pct = (new_price - base_price) / base_price
            
            impact = self.product_model.predict_sales_impact(
                df_sorted,
                base_price=base_price,
                price_change_pct=price_change_pct,
                is_promotion=abs(price_change_pct) > 0.1
            )
            
            base_demand = impact.get('base_sales', avg_sales)
            expected_sales_change = impact.get('expected_sales_change_pct', 0)
            predicted_sales = base_demand * (1 + expected_sales_change)
            
            if include_cross_impact and self.cross_analyzer is not None and strategy.product_id is not None:
                cross_impact = self.cross_analyzer.simulate_price_change_impact(
                    source_product_id=strategy.product_id,
                    price_change_pct=price_change_pct
                )
                total_cross_impact = cross_impact[
                    cross_impact['product_id'] != strategy.product_id
                ]['expected_sales_change'].sum()
            else:
                total_cross_impact = 0
            
            revenue = new_price * predicted_sales
            cost = self.variable_cost * predicted_sales + self.fixed_cost / n_days
            profit = revenue - cost
            
            cross_revenue_impact = total_cross_impact * base_price
            
            inventory -= predicted_sales
            if inventory < avg_sales * 3:
                inventory += avg_sales * 7
            
            simulation_results.append({
                'date': date,
                'day': day_idx + 1,
                'price': new_price,
                'price_change_pct': price_change_pct,
                'base_price': base_price,
                'competitor_price': competitor_price,
                'predicted_sales': predicted_sales,
                'base_sales': base_demand,
                'sales_change_pct': expected_sales_change,
                'revenue': revenue,
                'cost': cost,
                'profit': profit,
                'cross_sales_impact': total_cross_impact,
                'cross_revenue_impact': cross_revenue_impact,
                'net_revenue_with_cross': revenue + cross_revenue_impact,
                'inventory': inventory,
                'strategy': strategy.strategy_type.value
            })
        
        results_df = pd.DataFrame(simulation_results)
        
        baseline_revenue = base_price * avg_sales * n_days
        baseline_profit = (base_price - self.variable_cost) * avg_sales * n_days - self.fixed_cost
        
        comparison = {
            'total_revenue': results_df['revenue'].sum(),
            'total_profit': results_df['profit'].sum(),
            'total_sales': results_df['predicted_sales'].sum(),
            'avg_price': results_df['price'].mean(),
            'total_cross_revenue_impact': results_df['cross_revenue_impact'].sum(),
            'net_revenue_with_cross': results_df['net_revenue_with_cross'].sum(),
            'baseline_revenue': baseline_revenue,
            'baseline_profit': baseline_profit,
            'revenue_change_pct': (results_df['revenue'].sum() - baseline_revenue) / baseline_revenue,
            'profit_change_pct': (results_df['profit'].sum() - baseline_profit) / baseline_profit if baseline_profit > 0 else 0
        }
        
        return {
            'simulation_data': results_df,
            'comparison': comparison,
            'strategy': strategy
        }
    
    def compare_strategies(
        self,
        df: pd.DataFrame,
        strategies: List[PricingStrategy],
        n_days: int = 90,
        start_date: Optional[pd.Timestamp] = None
    ) -> Dict:
        all_results = {}
        comparisons = []
        
        for strategy in strategies:
            result = self.simulate_strategy(df, strategy, n_days, start_date)
            all_results[strategy.strategy_type.value] = result
            
            comparison_row = {
                'strategy': strategy.strategy_type.value,
                'description': self._get_strategy_description(strategy),
                'total_revenue': result['comparison']['total_revenue'],
                'total_profit': result['comparison']['total_profit'],
                'total_sales': result['comparison']['total_sales'],
                'avg_price': result['comparison']['avg_price'],
                'revenue_change_pct': result['comparison']['revenue_change_pct'],
                'profit_change_pct': result['comparison']['profit_change_pct'],
                'cross_revenue_impact': result['comparison']['total_cross_revenue_impact'],
                'net_revenue': result['comparison']['net_revenue_with_cross']
            }
            comparisons.append(comparison_row)
        
        comparison_df = pd.DataFrame(comparisons)
        comparison_df = comparison_df.sort_values('total_profit', ascending=False)
        
        return {
            'all_results': all_results,
            'comparison_summary': comparison_df,
            'best_strategy': comparison_df.iloc[0]['strategy'] if len(comparison_df) > 0 else None
        }
    
    def _get_strategy_description(self, strategy: PricingStrategy) -> str:
        descriptions = {
            PricingStrategyType.FIXED_PRICE: '固定价格策略',
            PricingStrategyType.FOLLOW_COMPETITOR: '跟随竞品策略',
            PricingStrategyType.DYNAMIC_MARGIN: '动态毛利策略',
            PricingStrategyType.ELASTICITY_BASED: '弹性优化策略',
            PricingStrategyType.TIME_BASED: '时段定价策略'
        }
        return descriptions.get(strategy.strategy_type, '未知策略')
    
    def create_default_strategies(
        self,
        base_price: float,
        product_id: Optional[int] = None
    ) -> List[PricingStrategy]:
        strategies = []
        
        strategies.append(PricingStrategy(
            strategy_type=PricingStrategyType.FIXED_PRICE,
            parameters={'price': base_price, 'base_price': base_price},
            product_id=product_id
        ))
        
        strategies.append(PricingStrategy(
            strategy_type=PricingStrategyType.FOLLOW_COMPETITOR,
            parameters={
                'markup': 0.05,
                'price_floor': base_price * 0.85,
                'price_ceiling': base_price * 1.15,
                'lag_days': 1,
                'base_price': base_price
            },
            product_id=product_id
        ))
        
        strategies.append(PricingStrategy(
            strategy_type=PricingStrategyType.DYNAMIC_MARGIN,
            parameters={
                'target_margin': 0.35,
                'variable_cost': self.variable_cost,
                'price_floor': base_price * 0.8,
                'base_price': base_price
            },
            product_id=product_id
        ))
        
        strategies.append(PricingStrategy(
            strategy_type=PricingStrategyType.ELASTICITY_BASED,
            parameters={
                'max_markup': 0.6,
                'min_markup': 0.15,
                'variable_cost': self.variable_cost,
                'price_floor': base_price * 0.8,
                'price_ceiling': base_price * 1.3,
                'base_price': base_price
            },
            product_id=product_id
        ))
        
        strategies.append(PricingStrategy(
            strategy_type=PricingStrategyType.TIME_BASED,
            parameters={
                'time_pattern': {
                    'dow_5': 0.1,
                    'dow_6': 0.1,
                    'dow_0': -0.05,
                    'dow_1': -0.05,
                    'dow_2': -0.05,
                    'dow_3': -0.05,
                    'dow_4': -0.02
                },
                'default_adjustment': 0.0,
                'base_price': base_price
            },
            product_id=product_id
        ))
        
        return strategies


def generate_time_based_pattern(
    df: pd.DataFrame,
    time_unit: str = 'day_of_week'
) -> Dict:
    if time_unit == 'day_of_week':
        sales_by_day = df.groupby(df['date'].dt.dayofweek)['sales_quantity'].mean()
        avg_sales = df['sales_quantity'].mean()
        
        pattern = {}
        for dow in range(7):
            if dow in sales_by_day.index:
                adjustment = (sales_by_day[dow] - avg_sales) / avg_sales * 0.3
                pattern[f'dow_{dow}'] = max(-0.15, min(0.2, adjustment))
            else:
                pattern[f'dow_{dow}'] = 0.0
        
        return pattern
    
    elif time_unit == 'month':
        sales_by_month = df.groupby(df['date'].dt.month)['sales_quantity'].mean()
        avg_sales = df['sales_quantity'].mean()
        
        pattern = {}
        for month in range(1, 13):
            if month in sales_by_month.index:
                adjustment = (sales_by_month[month] - avg_sales) / avg_sales * 0.3
                pattern[f'month_{month}'] = max(-0.15, min(0.2, adjustment))
            else:
                pattern[f'month_{month}'] = 0.0
        
        return pattern
    
    else:
        return {}
