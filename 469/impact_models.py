import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
import joblib
from scipy.optimize import minimize
from dataclasses import dataclass
from enum import Enum


class TimeHorizon(Enum):
    AGGRESSIVE = 'aggressive'
    MODERATE = 'moderate'
    PATIENT = 'patient'


@dataclass
class ExecutionConstraints:
    max_duration_seconds: float = 300.0
    min_order_interval_seconds: float = 1.0
    urgency: float = 0.5
    completion_penalty: float = 1000.0
    impact_weight: float = 1.0
    time_weight: float = 1.0


@dataclass
class ExecutionSchedule:
    timestamps: List[float]
    quantities: List[int]
    total_cost: float
    expected_impact_bps: float
    expected_duration: float
    completion_probability: float


class MarketImpactModel:
    def __init__(self, model_type: str = 'alfarms'):
        self.model_type = model_type
        self.params = {}
        
    def fit(self, data: pd.DataFrame = None, **kwargs):
        if self.model_type == 'alfarms':
            self.params = {
                'alpha': kwargs.get('alpha', 0.5),
                'beta': kwargs.get('beta', 0.7),
                'sigma': kwargs.get('sigma', 0.002),
                'daily_volume': kwargs.get('daily_volume', 1000000)
            }
        elif self.model_type == 'square_root':
            self.params = {
                'eta': kwargs.get('eta', 0.001),
                'sigma': kwargs.get('sigma', 0.002),
                'daily_volume': kwargs.get('daily_volume', 1000000)
            }
        elif self.model_type == 'power_law':
            self.params = {
                'a': kwargs.get('a', 0.001),
                'b': kwargs.get('b', 0.6),
                'c': kwargs.get('c', 0.5)
            }
        
    def predict_impact(self, quantity: int, duration: float = None, 
                       side: str = 'buy') -> float:
        if self.model_type == 'alfarms':
            return self._alfarms_model(quantity, duration)
        elif self.model_type == 'square_root':
            return self._square_root_model(quantity)
        elif self.model_type == 'power_law':
            return self._power_law_model(quantity)
        return 0.0
    
    def _alfarms_model(self, quantity: int, duration: float) -> float:
        alpha = self.params['alpha']
        beta = self.params['beta']
        sigma = self.params['sigma']
        daily_vol = self.params['daily_volume']
        
        q = quantity / daily_vol
        t = duration / 390 if duration else 1/390
        
        impact = sigma * (q / t) ** beta * (t ** alpha)
        return impact * 10000
    
    def _square_root_model(self, quantity: int) -> float:
        eta = self.params['eta']
        sigma = self.params['sigma']
        daily_vol = self.params['daily_volume']
        
        q = quantity / daily_vol
        impact = eta * sigma * np.sqrt(q)
        return impact * 10000
    
    def _power_law_model(self, quantity: int) -> float:
        a = self.params['a']
        b = self.params['b']
        c = self.params['c']
        
        impact = a * (quantity ** b) * (quantity / 1000000) ** c
        return impact * 10000


class MLImpactPredictor:
    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.feature_names = []
        self.is_trained = False
        
    def _extract_features(self, order_book_df: pd.DataFrame, 
                         quantity: int, side: str) -> Dict:
        depth_summary = order_book_df.sort_values('level')
        
        best_bid = depth_summary.iloc[0]['bid_price']
        best_ask = depth_summary.iloc[0]['ask_price']
        mid_price = (best_bid + best_ask) / 2
        
        bid_vol_5 = depth_summary.head(5)['bid_quantity'].sum()
        ask_vol_5 = depth_summary.head(5)['ask_quantity'].sum()
        bid_vol_10 = depth_summary.head(10)['bid_quantity'].sum()
        ask_vol_10 = depth_summary.head(10)['ask_quantity'].sum()
        bid_vol_20 = depth_summary['bid_quantity'].sum()
        ask_vol_20 = depth_summary['ask_quantity'].sum()
        
        q5 = quantity / ask_vol_5 if side == 'buy' else quantity / bid_vol_5
        q10 = quantity / ask_vol_10 if side == 'buy' else quantity / bid_vol_10
        q20 = quantity / ask_vol_20 if side == 'buy' else quantity / bid_vol_20
        
        spread_bps = (best_ask - best_bid) / mid_price * 10000
        
        slope_bid = self._calculate_slope(depth_summary, 'bid')
        slope_ask = self._calculate_slope(depth_summary, 'ask')
        
        imbalance = (bid_vol_20 - ask_vol_20) / (bid_vol_20 + ask_vol_20)
        
        features = {
            'quantity': quantity,
            'log_quantity': np.log1p(quantity),
            'q5_ratio': q5,
            'q10_ratio': q10,
            'q20_ratio': q20,
            'spread_bps': spread_bps,
            'bid_slope': slope_bid,
            'ask_slope': slope_ask,
            'imbalance': imbalance,
            'side_encoded': 1 if side == 'buy' else 0,
            'mid_price': mid_price,
            'sqrt_quantity': np.sqrt(quantity),
            'quantity_squared': quantity ** 2
        }
        
        return features
    
    def _calculate_slope(self, df: pd.DataFrame, side: str) -> float:
        if side == 'bid':
            prices = df['bid_price'].values
            volumes = df['bid_quantity'].values
        else:
            prices = df['ask_price'].values
            volumes = df['ask_quantity'].values
        
        cumulative_vol = np.cumsum(volumes)
        
        if len(prices) > 1:
            price_diff = np.diff(prices)
            vol_diff = np.diff(cumulative_vol)
            slopes = price_diff / vol_diff
            return np.mean(slopes) * 1000
        return 0
    
    def generate_training_data(self, n_samples: int = 5000) -> Tuple[pd.DataFrame, np.ndarray]:
        from order_book import OrderBookSimulator
        
        features_list = []
        targets = []
        
        for _ in range(n_samples):
            base_depth = np.random.randint(500, 5000)
            depth_decay = np.random.uniform(0.7, 0.95)
            mid_price = np.random.uniform(50, 500)
            spread = np.random.uniform(0.01, 0.1)
            
            simulator = OrderBookSimulator(
                mid_price=mid_price,
                spread=spread,
                num_levels=20,
                liquidity_params={
                    'base_depth': base_depth,
                    'depth_decay': depth_decay,
                    'volatility': 0.001,
                    'bid_ask_imbalance': np.random.uniform(-0.3, 0.3),
                    'shape_param': np.random.uniform(1.0, 2.0)
                }
            )
            
            order_book = simulator.generate_order_book()
            
            from order_book import MarketImpactCalculator
            calculator = MarketImpactCalculator(order_book)
            
            side = np.random.choice(['buy', 'sell'])
            quantity = np.random.randint(100, int(base_depth * 10))
            
            _, slippage_bps, _ = calculator.calculate_impact(quantity, side)
            
            features = self._extract_features(order_book, quantity, side)
            features_list.append(features)
            targets.append(slippage_bps)
        
        features_df = pd.DataFrame(features_list)
        return features_df, np.array(targets)
    
    def train(self, n_samples: int = 5000, test_size: float = 0.2) -> Dict:
        X, y = self.generate_training_data(n_samples)
        
        self.feature_names = X.columns.tolist()
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42
        )
        
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        self.model = GradientBoostingRegressor(
            n_estimators=200,
            learning_rate=0.1,
            max_depth=5,
            random_state=42
        )
        
        self.model.fit(X_train_scaled, y_train)
        
        y_pred_train = self.model.predict(X_train_scaled)
        y_pred_test = self.model.predict(X_test_scaled)
        
        metrics = {
            'train_mse': mean_squared_error(y_train, y_pred_train),
            'test_mse': mean_squared_error(y_test, y_pred_test),
            'train_r2': r2_score(y_train, y_pred_train),
            'test_r2': r2_score(y_test, y_pred_test),
            'train_rmse': np.sqrt(mean_squared_error(y_train, y_pred_train)),
            'test_rmse': np.sqrt(mean_squared_error(y_test, y_pred_test))
        }
        
        self.is_trained = True
        return metrics
    
    def predict(self, order_book_df: pd.DataFrame, quantity: int, side: str) -> float:
        if not self.is_trained:
            self.train(n_samples=2000)
        
        features = self._extract_features(order_book_df, quantity, side)
        features_df = pd.DataFrame([features])[self.feature_names]
        features_scaled = self.scaler.transform(features_df)
        
        prediction = self.model.predict(features_scaled)[0]
        return max(0, prediction)
    
    def get_feature_importance(self) -> pd.DataFrame:
        if not self.is_trained:
            return pd.DataFrame()
        
        importance_df = pd.DataFrame({
            'feature': self.feature_names,
            'importance': self.model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        return importance_df
    
    def save_model(self, filepath: str):
        if self.is_trained:
            joblib.dump({
                'model': self.model,
                'scaler': self.scaler,
                'feature_names': self.feature_names
            }, filepath)
    
    def load_model(self, filepath: str):
        data = joblib.load(filepath)
        self.model = data['model']
        self.scaler = data['scaler']
        self.feature_names = data['feature_names']
        self.is_trained = True


class TimeConstrainedOptimalExecution:
    def __init__(self, order_book_df: pd.DataFrame, total_quantity: int, side: str):
        self.order_book = order_book_df
        self.total_quantity = total_quantity
        self.side = side
        
        from order_book import MarketImpactCalculator, QuadraticImpactModel
        self.impact_calculator = MarketImpactCalculator(order_book_df)
        self.quadratic_model = QuadraticImpactModel(order_book_df)
        
        self.best_price = order_book_df.iloc[0]['ask_price' if side == 'buy' else 'bid_price']
    
    def _calculate_temporary_impact(self, quantity: int) -> float:
        _, slippage, _ = self.quadratic_model.calculate_impact(quantity, self.side)
        return slippage
    
    def _calculate_permanent_impact(self, quantity: int, total_qty: int) -> float:
        ratio = quantity / total_qty
        return 0.3 * ratio * 10
    
    def _calculate_completion_probability(self, duration_seconds: float, 
                                         constraint_seconds: float) -> float:
        if duration_seconds <= constraint_seconds:
            return 1.0
        excess_ratio = (duration_seconds - constraint_seconds) / constraint_seconds
        return max(0.0, 1.0 - 0.5 * excess_ratio)
    
    def _objective_function(self, schedule: np.ndarray, 
                            constraints: ExecutionConstraints) -> float:
        quantities = schedule[:-1] * self.total_quantity
        intervals = schedule[-1]
        
        quantities = np.round(quantities).astype(int)
        quantities[-1] = self.total_quantity - quantities[:-1].sum()
        quantities = np.maximum(quantities, 0)
        
        total_impact = 0.0
        for i, qty in enumerate(quantities):
            if qty <= 0:
                continue
            
            temp_impact = self._calculate_temporary_impact(qty)
            perm_impact = self._calculate_permanent_impact(qty, self.total_quantity) * (i + 1)
            total_impact += temp_impact + perm_impact
        
        num_orders = len(quantities)
        total_duration = num_orders * max(intervals, constraints.min_order_interval_seconds)
        
        completion_prob = self._calculate_completion_probability(
            total_duration, constraints.max_duration_seconds
        )
        completion_penalty = (1 - completion_prob) * constraints.completion_penalty
        
        urgency_penalty = constraints.urgency * total_duration / 60
        
        total_cost = (
            constraints.impact_weight * total_impact +
            constraints.time_weight * urgency_penalty +
            completion_penalty
        )
        
        return total_cost
    
    def optimize_execution(self, constraints: ExecutionConstraints, 
                           num_orders_range: Tuple[int, int] = (3, 20)) -> Dict:
        best_result = None
        best_cost = float('inf')
        
        for num_orders in range(num_orders_range[0], num_orders_range[1] + 1):
            initial_schedule = np.concatenate([
                np.ones(num_orders) / num_orders,
                [constraints.max_duration_seconds / num_orders]
            ])
            
            bounds = [(0.01, 0.9) for _ in range(num_orders)] + \
                     [(constraints.min_order_interval_seconds, 
                       constraints.max_duration_seconds / num_orders)]
            
            constraint = {'type': 'eq', 'fun': lambda x: x[:-1].sum() - 1.0}
            
            try:
                result = minimize(
                    self._objective_function,
                    initial_schedule,
                    args=(constraints,),
                    method='SLSQP',
                    bounds=bounds,
                    constraints=[constraint],
                    options={'maxiter': 100}
                )
                
                if result.fun < best_cost:
                    best_cost = result.fun
                    best_result = {
                        'num_orders': num_orders,
                        'schedule': result.x,
                        'cost': result.fun
                    }
            except:
                continue
        
        if best_result is None:
            return self._fallback_strategy(constraints)
        
        return self._format_result(best_result, constraints)
    
    def _fallback_strategy(self, constraints: ExecutionConstraints) -> Dict:
        num_orders = 10
        quantities = np.ones(num_orders) * (self.total_quantity // num_orders)
        quantities[-1] += self.total_quantity % num_orders
        
        interval = constraints.max_duration_seconds / num_orders
        
        total_impact = 0.0
        for qty in quantities:
            total_impact += self._calculate_temporary_impact(qty)
        
        total_duration = num_orders * interval
        completion_prob = self._calculate_completion_probability(
            total_duration, constraints.max_duration_seconds
        )
        
        return {
            'strategy': 'Fallback TWAP',
            'num_orders': num_orders,
            'quantities': quantities.tolist(),
            'interval_seconds': interval,
            'total_duration': total_duration,
            'expected_impact_bps': total_impact,
            'completion_probability': completion_prob,
            'total_cost': total_impact * constraints.impact_weight + (1 - completion_prob) * constraints.completion_penalty
        }
    
    def _format_result(self, result: Dict, constraints: ExecutionConstraints) -> Dict:
        schedule = result['schedule']
        quantities = schedule[:-1] * self.total_quantity
        quantities = np.round(quantities).astype(int)
        quantities[-1] = self.total_quantity - quantities[:-1].sum()
        quantities = np.maximum(quantities, 0)
        
        interval = schedule[-1]
        total_duration = result['num_orders'] * interval
        
        total_impact = 0.0
        for i, qty in enumerate(quantities):
            if qty <= 0:
                continue
            total_impact += self._calculate_temporary_impact(qty)
        
        completion_prob = self._calculate_completion_probability(
            total_duration, constraints.max_duration_seconds
        )
        
        return {
            'strategy': 'Time-Constrained Optimal',
            'num_orders': result['num_orders'],
            'quantities': quantities.tolist(),
            'interval_seconds': interval,
            'total_duration': total_duration,
            'expected_impact_bps': total_impact,
            'completion_probability': completion_prob,
            'total_cost': result['cost'],
            'is_optimized': True
        }
    
    def generate_twap_schedule(self, num_orders: int, 
                                constraints: ExecutionConstraints) -> Dict:
        quantities = np.ones(num_orders) * (self.total_quantity // num_orders)
        quantities[-1] += self.total_quantity % num_orders
        
        interval = constraints.max_duration_seconds / num_orders
        total_duration = num_orders * interval
        
        total_impact = 0.0
        for qty in quantities:
            total_impact += self._calculate_temporary_impact(qty)
        
        completion_prob = self._calculate_completion_probability(
            total_duration, constraints.max_duration_seconds
        )
        
        return {
            'strategy': f'TWAP ({num_orders} orders)',
            'num_orders': num_orders,
            'quantities': quantities.tolist(),
            'interval_seconds': interval,
            'total_duration': total_duration,
            'expected_impact_bps': total_impact,
            'completion_probability': completion_prob,
            'total_cost': total_impact * constraints.impact_weight + (1 - completion_prob) * constraints.completion_penalty
        }
    
    def generate_vwap_schedule(self, num_orders: int, 
                                constraints: ExecutionConstraints) -> Dict:
        from order_book import MarketImpactCalculator
        depth = MarketImpactCalculator(self.order_book).get_depth_summary()
        
        if self.side == 'buy':
            cumulative_qty = depth['cumulative_ask'].values
        else:
            cumulative_qty = depth['cumulative_bid'].values
        
        weights = []
        for i in range(num_orders):
            if i < len(cumulative_qty):
                weights.append(cumulative_qty[i] if i == 0 else cumulative_qty[i] - cumulative_qty[i-1])
            else:
                weights.append(weights[-1] if weights else 1)
        
        weights = np.array(weights) / sum(weights)
        quantities = np.round(weights * self.total_quantity).astype(int)
        quantities[-1] = self.total_quantity - sum(quantities[:-1])
        quantities = np.maximum(quantities, 0)
        
        interval = constraints.max_duration_seconds / num_orders
        total_duration = num_orders * interval
        
        total_impact = 0.0
        for qty in quantities:
            if qty > 0:
                total_impact += self._calculate_temporary_impact(qty)
        
        completion_prob = self._calculate_completion_probability(
            total_duration, constraints.max_duration_seconds
        )
        
        return {
            'strategy': f'VWAP ({num_orders} orders)',
            'num_orders': num_orders,
            'quantities': quantities.tolist(),
            'interval_seconds': interval,
            'total_duration': total_duration,
            'expected_impact_bps': total_impact,
            'completion_probability': completion_prob,
            'total_cost': total_impact * constraints.impact_weight + (1 - completion_prob) * constraints.completion_penalty
        }


class OptimalExecution:
    def __init__(self, order_book_df: pd.DataFrame, total_quantity: int, side: str):
        self.order_book = order_book_df
        self.total_quantity = total_quantity
        self.side = side
        
        from order_book import MarketImpactCalculator
        self.impact_calculator = MarketImpactCalculator(order_book_df)
        
    def single_order_impact(self) -> Dict:
        avg_price, slippage_bps, trades = self.impact_calculator.calculate_impact(
            self.total_quantity, self.side
        )
        
        return {
            'strategy': 'Single Order',
            'avg_price': avg_price,
            'slippage_bps': slippage_bps,
            'total_cost': avg_price * self.total_quantity,
            'num_orders': 1,
            'trades': trades
        }
    
    def twap_strategy(self, num_intervals: int = 10) -> Dict:
        qty_per_order = self.total_quantity // num_intervals
        remainder = self.total_quantity % num_intervals
        
        total_cost = 0.0
        total_qty = 0
        all_trades = []
        
        for i in range(num_intervals):
            qty = qty_per_order + (1 if i < remainder else 0)
            avg_price, _, trades = self.impact_calculator.calculate_impact(qty, self.side)
            
            total_cost += avg_price * qty
            total_qty += qty
            all_trades.extend(trades)
        
        avg_price = total_cost / total_qty
        best_price = self.order_book.iloc[0]['ask_price' if self.side == 'buy' else 'bid_price']
        
        if self.side == 'buy':
            slippage_bps = (avg_price - best_price) / best_price * 10000
        else:
            slippage_bps = (best_price - avg_price) / best_price * 10000
        
        return {
            'strategy': f'TWAP ({num_intervals} orders)',
            'avg_price': avg_price,
            'slippage_bps': slippage_bps,
            'total_cost': total_cost,
            'num_orders': num_intervals,
            'quantity_per_order': qty_per_order,
            'trades': all_trades
        }
    
    def vwap_profile_strategy(self, num_intervals: int = 10) -> Dict:
        depth = self.impact_calculator.get_depth_summary()
        
        if self.side == 'buy':
            cumulative_qty = depth['cumulative_ask'].values
        else:
            cumulative_qty = depth['cumulative_bid'].values
        
        weights = []
        for i in range(num_intervals):
            if i < len(cumulative_qty):
                weights.append(cumulative_qty[i] if i == 0 else cumulative_qty[i] - cumulative_qty[i-1])
            else:
                weights.append(weights[-1] if weights else 1)
        
        weights = np.array(weights) / sum(weights)
        quantities = np.round(weights * self.total_quantity).astype(int)
        quantities[-1] = self.total_quantity - sum(quantities[:-1])
        
        total_cost = 0.0
        total_qty = 0
        all_trades = []
        
        for qty in quantities:
            if qty <= 0:
                continue
            avg_price, _, trades = self.impact_calculator.calculate_impact(qty, self.side)
            
            total_cost += avg_price * qty
            total_qty += qty
            all_trades.extend(trades)
        
        avg_price = total_cost / total_qty
        best_price = self.order_book.iloc[0]['ask_price' if self.side == 'buy' else 'bid_price']
        
        if self.side == 'buy':
            slippage_bps = (avg_price - best_price) / best_price * 10000
        else:
            slippage_bps = (best_price - avg_price) / best_price * 10000
        
        return {
            'strategy': f'Volume-Weighted ({num_intervals} orders)',
            'avg_price': avg_price,
            'slippage_bps': slippage_bps,
            'total_cost': total_cost,
            'num_orders': num_intervals,
            'trades': all_trades
        }
    
    def optimize_split(self, max_orders: int = 20) -> pd.DataFrame:
        results = []
        
        for n in range(1, max_orders + 1):
            twap_result = self.twap_strategy(n)
            vwap_result = self.vwap_profile_strategy(n)
            
            results.append({
                'num_orders': n,
                'twap_slippage': twap_result['slippage_bps'],
                'vwap_slippage': vwap_result['slippage_bps'],
                'twap_cost': twap_result['total_cost'],
                'vwap_cost': vwap_result['total_cost']
            })
        
        return pd.DataFrame(results)
    
    def get_optimal_strategy(self, risk_aversion: float = 0.5) -> Dict:
        optimization_results = self.optimize_split(max_orders=20)
        
        twap_optimal = optimization_results.loc[optimization_results['twap_slippage'].idxmin()]
        vwap_optimal = optimization_results.loc[optimization_results['vwap_slippage'].idxmin()]
        
        single_order = self.single_order_impact()
        
        twap_saving = single_order['slippage_bps'] - twap_optimal['twap_slippage']
        vwap_saving = single_order['slippage_bps'] - vwap_optimal['vwap_slippage']
        
        recommendations = {
            'single_order': single_order,
            'optimal_twap': {
                'num_orders': int(twap_optimal['num_orders']),
                'slippage_bps': twap_optimal['twap_slippage'],
                'savings_bps': twap_saving
            },
            'optimal_vwap': {
                'num_orders': int(vwap_optimal['num_orders']),
                'slippage_bps': vwap_optimal['vwap_slippage'],
                'savings_bps': vwap_saving
            },
            'recommended_strategy': 'VWAP' if vwap_saving > twap_saving else 'TWAP'
        }
        
        return recommendations
