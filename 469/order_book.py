import numpy as np
import pandas as pd
from typing import Tuple, List, Dict, Optional
from dataclasses import dataclass
from enum import Enum
import heapq


class OrderType(Enum):
    LIMIT = 'limit'
    MARKET = 'market'
    CANCEL = 'cancel'


class OrderSide(Enum):
    BUY = 'buy'
    SELL = 'sell'


@dataclass
class Order:
    order_id: int
    timestamp: pd.Timestamp
    side: OrderSide
    price: float
    quantity: int
    order_type: OrderType


class HighFrequencyOrderBook:
    def __init__(
        self,
        initial_mid_price: float = 100.0,
        tick_size: float = 0.01,
        num_levels: int = 50,
        hft_params: Dict = None
    ):
        self.tick_size = tick_size
        self.num_levels = num_levels
        self.current_mid_price = initial_mid_price
        self.hft_params = hft_params or self._default_hft_params()
        
        self.bid_book: Dict[float, List[Tuple[int, int]]] = {}
        self.ask_book: Dict[float, List[Tuple[int, int]]] = {}
        self.order_id_counter = 0
        self.timestamp = pd.Timestamp.now()
        
        self.event_history: List[Dict] = []
        self.order_book_snapshots: List[Dict] = []
        
        self._initialize_book()
    
    def _default_hft_params(self) -> Dict:
        return {
            'arrival_rate': 100,
            'cancellation_rate': 30,
            'market_order_rate': 10,
            'order_size_mean': 200,
            'order_size_std': 100,
            'price_spread_ticks': 2,
            'mean_reversion_speed': 0.1,
            'volatility': 0.0001,
            'liquidity_mean': 1000,
            'liquidity_std': 200
        }
    
    def _initialize_book(self):
        params = self.hft_params
        best_bid = self.current_mid_price - self.tick_size
        best_ask = self.current_mid_price + self.tick_size
        
        for level in range(self.num_levels):
            bid_price = best_bid - level * self.tick_size
            ask_price = best_ask + level * self.tick_size
            
            depth_factor = 1.0 / (level + 1) ** 0.8
            bid_qty = max(50, int(params['liquidity_mean'] * depth_factor * (0.8 + np.random.rand() * 0.4)))
            ask_qty = max(50, int(params['liquidity_mean'] * depth_factor * (0.8 + np.random.rand() * 0.4)))
            
            self.bid_book[bid_price] = [(self._next_order_id(), bid_qty)]
            self.ask_book[ask_price] = [(self._next_order_id(), ask_qty)]
    
    def _next_order_id(self) -> int:
        self.order_id_counter += 1
        return self.order_id_counter
    
    def _update_timestamp_ns(self):
        nanos = np.random.exponential(1000)
        self.timestamp += pd.Timedelta(nanoseconds=int(nanos))
    
    def _round_to_tick(self, price: float) -> float:
        return round(price / self.tick_size) * self.tick_size
    
    def add_limit_order(self, side: OrderSide, price: float, quantity: int) -> Order:
        self._update_timestamp_ns()
        order_id = self._next_order_id()
        order = Order(order_id, self.timestamp, side, price, quantity, OrderType.LIMIT)
        
        price = self._round_to_tick(price)
        book = self.bid_book if side == OrderSide.BUY else self.ask_book
        
        if price not in book:
            book[price] = []
        book[price].append((order_id, quantity))
        
        self.event_history.append({
            'timestamp': self.timestamp,
            'event_type': 'add_limit',
            'side': side.value,
            'price': price,
            'quantity': quantity,
            'order_id': order_id
        })
        
        return order
    
    def cancel_order(self, side: OrderSide, price: float, order_id: int):
        self._update_timestamp_ns()
        book = self.bid_book if side == OrderSide.BUY else self.ask_book
        
        if price in book:
            book[price] = [(oid, qty) for oid, qty in book[price] if oid != order_id]
            if not book[price]:
                del book[price]
        
        self.event_history.append({
            'timestamp': self.timestamp,
            'event_type': 'cancel',
            'side': side.value,
            'price': price,
            'order_id': order_id
        })
    
    def execute_market_order(self, side: OrderSide, quantity: int) -> Tuple[float, List[Dict]]:
        self._update_timestamp_ns()
        
        if side == OrderSide.BUY:
            book = self.ask_book
            sorted_prices = sorted(book.keys())
        else:
            book = self.bid_book
            sorted_prices = sorted(book.keys(), reverse=True)
        
        remaining_qty = quantity
        total_cost = 0.0
        trades = []
        
        for price in sorted_prices:
            if remaining_qty <= 0:
                break
            
            orders_at_price = book[price]
            new_orders_at_price = []
            
            for order_id, order_qty in orders_at_price:
                if remaining_qty <= 0:
                    new_orders_at_price.append((order_id, order_qty))
                    continue
                
                executed_qty = min(remaining_qty, order_qty)
                total_cost += executed_qty * price
                remaining_qty -= executed_qty
                
                trades.append({
                    'timestamp': self.timestamp,
                    'price': price,
                    'quantity': executed_qty,
                    'order_id': order_id
                })
                
                if order_qty > executed_qty:
                    new_orders_at_price.append((order_id, order_qty - executed_qty))
            
            if new_orders_at_price:
                book[price] = new_orders_at_price
            else:
                del book[price]
        
        self.event_history.append({
            'timestamp': self.timestamp,
            'event_type': 'market_order',
            'side': side.value,
            'quantity': quantity,
            'trades': trades
        })
        
        avg_price = total_cost / (quantity - remaining_qty) if (quantity - remaining_qty) > 0 else 0
        return avg_price, trades
    
    def simulate_hft_events(self, duration_ns: int = 1_000_000_000, snapshot_interval_ns: int = 100_000) -> pd.DataFrame:
        params = self.hft_params
        start_time = self.timestamp
        end_time = start_time + pd.Timedelta(nanoseconds=duration_ns)
        last_snapshot = start_time
        
        while self.timestamp < end_time:
            event_type = np.random.choice(
                ['add_limit', 'cancel', 'market'],
                p=[0.6, 0.25, 0.15]
            )
            
            side = OrderSide.BUY if np.random.rand() < 0.5 else OrderSide.SELL
            
            if event_type == 'add_limit':
                best_bid = self.get_best_bid()
                best_ask = self.get_best_ask()
                
                if side == OrderSide.BUY and best_ask:
                    price_offset = np.random.randint(-20, 2) * self.tick_size
                    price = self._round_to_tick(best_ask + price_offset)
                elif side == OrderSide.SELL and best_bid:
                    price_offset = np.random.randint(-2, 20) * self.tick_size
                    price = self._round_to_tick(best_bid + price_offset)
                else:
                    price = self.current_mid_price
                
                quantity = max(10, int(np.random.normal(params['order_size_mean'], params['order_size_std'])))
                self.add_limit_order(side, price, quantity)
            
            elif event_type == 'cancel':
                book = self.bid_book if side == OrderSide.BUY else self.ask_book
                if book:
                    prices = list(book.keys())
                    if prices:
                        price = np.random.choice(prices)
                        if book[price]:
                            order_id, _ = book[price][0]
                            self.cancel_order(side, price, order_id)
            
            elif event_type == 'market':
                quantity = max(10, int(np.random.normal(params['order_size_mean'] * 2, params['order_size_std'])))
                self.execute_market_order(side, quantity)
            
            time_since_snapshot = (self.timestamp - last_snapshot).value
            if time_since_snapshot >= snapshot_interval_ns:
                self._take_snapshot()
                last_snapshot = self.timestamp
        
        return self.get_snapshots_dataframe()
    
    def _take_snapshot(self):
        snapshot = {
            'timestamp': self.timestamp,
            'mid_price': self.get_mid_price(),
            'best_bid': self.get_best_bid(),
            'best_ask': self.get_best_ask(),
            'bid_depth': self.get_total_depth(OrderSide.BUY),
            'ask_depth': self.get_total_depth(OrderSide.SELL),
            'bid_book': {p: sum(q for _, q in orders) for p, orders in self.bid_book.items()},
            'ask_book': {p: sum(q for _, q in orders) for p, orders in self.ask_book.items()}
        }
        self.order_book_snapshots.append(snapshot)
    
    def get_best_bid(self) -> Optional[float]:
        if not self.bid_book:
            return None
        return max(self.bid_book.keys())
    
    def get_best_ask(self) -> Optional[float]:
        if not self.ask_book:
            return None
        return min(self.ask_book.keys())
    
    def get_mid_price(self) -> float:
        best_bid = self.get_best_bid() or self.current_mid_price - self.tick_size
        best_ask = self.get_best_ask() or self.current_mid_price + self.tick_size
        return (best_bid + best_ask) / 2
    
    def get_total_depth(self, side: OrderSide) -> int:
        book = self.bid_book if side == OrderSide.BUY else self.ask_book
        return sum(sum(qty for _, qty in orders) for orders in book.values())
    
    def get_snapshots_dataframe(self) -> pd.DataFrame:
        data = []
        for snap in self.order_book_snapshots:
            data.append({
                'timestamp': snap['timestamp'],
                'mid_price': snap['mid_price'],
                'best_bid': snap['best_bid'],
                'best_ask': snap['best_ask'],
                'spread': snap['best_ask'] - snap['best_bid'] if snap['best_bid'] and snap['best_ask'] else None,
                'bid_depth': snap['bid_depth'],
                'ask_depth': snap['ask_depth'],
                'book_imbalance': (snap['bid_depth'] - snap['ask_depth']) / (snap['bid_depth'] + snap['ask_depth']) if (snap['bid_depth'] + snap['ask_depth']) > 0 else 0
            })
        return pd.DataFrame(data)
    
    def get_order_book_dataframe(self, num_levels: int = 20) -> pd.DataFrame:
        best_bid = self.get_best_bid()
        best_ask = self.get_best_ask()
        
        if best_bid is None or best_ask is None:
            return pd.DataFrame()
        
        data = []
        for level in range(num_levels):
            bid_price = best_bid - level * self.tick_size
            ask_price = best_ask + level * self.tick_size
            
            bid_qty = sum(q for _, q in self.bid_book.get(bid_price, []))
            ask_qty = sum(q for _, q in self.ask_book.get(ask_price, []))
            
            data.append({
                'level': level + 1,
                'bid_price': bid_price,
                'bid_quantity': bid_qty,
                'ask_price': ask_price,
                'ask_quantity': ask_qty
            })
        
        return pd.DataFrame(data)


class QuadraticImpactModel:
    def __init__(self, order_book_df: pd.DataFrame):
        self.order_book = order_book_df.sort_values('level')
        self._calibrate_parameters()
    
    def _calibrate_parameters(self):
        ask_prices = self.order_book['ask_price'].values
        ask_quantities = self.order_book['ask_quantity'].values
        bid_prices = self.order_book['bid_price'].values
        bid_quantities = self.order_book['bid_quantity'].values
        
        self.ask_elasticity = self._estimate_elasticity(ask_prices, ask_quantities)
        self.bid_elasticity = self._estimate_elasticity(bid_prices, bid_quantities)
        
        self.ask_k = self._estimate_quadratic_coeff(ask_prices, ask_quantities)
        self.bid_k = self._estimate_quadratic_coeff(bid_prices, bid_quantities)
    
    def _estimate_elasticity(self, prices: np.ndarray, quantities: np.ndarray) -> float:
        if len(prices) < 2:
            return 1.0
        
        price_diffs = np.diff(prices)
        cum_qty = np.cumsum(quantities)
        qty_diffs = np.diff(cum_qty)
        
        valid = (price_diffs != 0) & (qty_diffs != 0)
        if not np.any(valid):
            return 1.0
        
        elasticities = np.abs((qty_diffs[valid] / cum_qty[:-1][valid]) / (price_diffs[valid] / prices[:-1][valid]))
        return np.mean(elasticities[np.isfinite(elasticities)]) if len(elasticities) > 0 else 1.0
    
    def _estimate_quadratic_coeff(self, prices: np.ndarray, quantities: np.ndarray) -> float:
        cum_qty = np.cumsum(quantities)
        price_from_best = (prices - prices[0]) / prices[0]
        
        if len(cum_qty) < 3:
            return 1e-8
        
        X = np.column_stack([cum_qty, cum_qty ** 2])
        y = price_from_best
        
        try:
            coeffs, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
            return max(1e-10, abs(coeffs[1]))
        except:
            return 1e-8
    
    def calculate_impact(self, quantity: int, side: str) -> Tuple[float, float, float]:
        if side == 'buy':
            k = self.ask_k
            elasticity = self.ask_elasticity
            start_price = self.order_book.iloc[0]['ask_price']
        else:
            k = self.bid_k
            elasticity = self.bid_elasticity
            start_price = self.order_book.iloc[0]['bid_price']
        
        linear_impact = quantity ** (1 / elasticity) if elasticity > 0 else quantity
        quadratic_impact = k * quantity ** 2
        total_impact = (0.3 * linear_impact + 0.7 * quadratic_impact) * 10000
        
        if side == 'buy':
            avg_price = start_price * (1 + total_impact / 10000)
        else:
            avg_price = start_price * (1 - total_impact / 10000)
        
        slippage_bps = abs(avg_price - start_price) / start_price * 10000
        
        return avg_price, slippage_bps, quadratic_impact * 10000
    
    def get_impact_curve(self, max_quantity: int, steps: int = 30) -> pd.DataFrame:
        quantities = np.linspace(100, max_quantity, steps, dtype=int)
        
        results = []
        for qty in quantities:
            buy_avg, buy_slip, buy_quad = self.calculate_impact(qty, 'buy')
            sell_avg, sell_slip, sell_quad = self.calculate_impact(qty, 'sell')
            
            results.append({
                'quantity': qty,
                'buy_avg_price': buy_avg,
                'sell_avg_price': sell_avg,
                'buy_slippage_bps': buy_slip,
                'sell_slippage_bps': sell_slip,
                'buy_quadratic_component_bps': buy_quad,
                'sell_quadratic_component_bps': sell_quad
            })
        
        return pd.DataFrame(results)
    
    def get_model_parameters(self) -> Dict:
        return {
            'ask_elasticity': self.ask_elasticity,
            'bid_elasticity': self.bid_elasticity,
            'ask_quadratic_coeff': self.ask_k,
            'bid_quadratic_coeff': self.bid_k
        }


class OrderBookSimulator:
    def __init__(
        self,
        mid_price: float = 100.0,
        tick_size: float = 0.01,
        num_levels: int = 20,
        spread: float = 0.02,
        liquidity_params: Dict = None
    ):
        self.mid_price = mid_price
        self.tick_size = tick_size
        self.num_levels = num_levels
        self.spread = spread
        self.liquidity_params = liquidity_params or self._default_liquidity_params()
        self.order_book = None
        
    def _default_liquidity_params(self) -> Dict:
        return {
            'base_depth': 1000,
            'depth_decay': 0.85,
            'volatility': 0.001,
            'bid_ask_imbalance': 0.0,
            'shape_param': 1.5
        }
    
    def generate_order_book(self, timestamp: pd.Timestamp = None) -> pd.DataFrame:
        if timestamp is None:
            timestamp = pd.Timestamp.now()
        
        params = self.liquidity_params
        bid_prices = []
        bid_quantities = []
        ask_prices = []
        ask_quantities = []
        
        best_bid = self.mid_price - self.spread / 2
        best_ask = self.mid_price + self.spread / 2
        
        for level in range(self.num_levels):
            bid_price = best_bid - level * self.tick_size
            ask_price = best_ask + level * self.tick_size
            
            depth_factor = (params['depth_decay'] ** level) * params['shape_param']
            base_quantity = params['base_depth'] * depth_factor
            
            volatility_noise = np.random.normal(0, params['volatility'] * base_quantity)
            
            bid_qty = max(10, int(base_quantity * (1 + params['bid_ask_imbalance']) + volatility_noise))
            ask_qty = max(10, int(base_quantity * (1 - params['bid_ask_imbalance']) - volatility_noise))
            
            bid_prices.append(round(bid_price, 2))
            bid_quantities.append(bid_qty)
            ask_prices.append(round(ask_price, 2))
            ask_quantities.append(ask_qty)
        
        order_book_data = {
            'timestamp': [timestamp] * self.num_levels,
            'level': list(range(1, self.num_levels + 1)),
            'bid_price': bid_prices,
            'bid_quantity': bid_quantities,
            'ask_price': ask_prices,
            'ask_quantity': ask_quantities
        }
        
        self.order_book = pd.DataFrame(order_book_data)
        return self.order_book
    
    def generate_historical_data(
        self,
        num_timestamps: int = 100,
        freq: str = '1S'
    ) -> pd.DataFrame:
        all_data = []
        base_time = pd.Timestamp.now().replace(microsecond=0)
        
        for i in range(num_timestamps):
            timestamp = base_time + pd.Timedelta(seconds=i)
            self.mid_price = self.mid_price * (1 + np.random.normal(0, 0.0005))
            self.liquidity_params['bid_ask_imbalance'] = np.random.uniform(-0.2, 0.2)
            
            ob = self.generate_order_book(timestamp)
            all_data.append(ob)
        
        return pd.concat(all_data, ignore_index=True)
    
    def get_book_summary(self) -> Dict:
        if self.order_book is None:
            self.generate_order_book()
        
        best_bid = self.order_book.iloc[0]['bid_price']
        best_ask = self.order_book.iloc[0]['ask_price']
        mid_price = (best_bid + best_ask) / 2
        
        total_bid_depth = self.order_book['bid_quantity'].sum()
        total_ask_depth = self.order_book['ask_quantity'].sum()
        
        bid_depth_5 = self.order_book.head(5)['bid_quantity'].sum()
        ask_depth_5 = self.order_book.head(5)['ask_quantity'].sum()
        
        return {
            'mid_price': mid_price,
            'best_bid': best_bid,
            'best_ask': best_ask,
            'spread': best_ask - best_bid,
            'spread_bps': (best_ask - best_bid) / mid_price * 10000,
            'total_bid_depth': total_bid_depth,
            'total_ask_depth': total_ask_depth,
            'bid_depth_5': bid_depth_5,
            'ask_depth_5': ask_depth_5,
            'book_imbalance': (total_bid_depth - total_ask_depth) / (total_bid_depth + total_ask_depth)
        }


class MarketImpactCalculator:
    def __init__(self, order_book: pd.DataFrame):
        self.order_book = order_book.sort_values('level')
        
    def calculate_impact(self, quantity: int, side: str) -> Tuple[float, float, List[Dict]]:
        if side == 'buy':
            prices = self.order_book['ask_price'].values
            quantities = self.order_book['ask_quantity'].values
            start_price = prices[0]
        else:
            prices = self.order_book['bid_price'].values
            quantities = self.order_book['bid_quantity'].values
            start_price = prices[0]
        
        remaining_qty = quantity
        total_cost = 0.0
        executed_trades = []
        
        for level in range(len(prices)):
            if remaining_qty <= 0:
                break
                
            price = prices[level]
            available_qty = quantities[level]
            executed_qty = min(remaining_qty, available_qty)
            
            trade_cost = executed_qty * price
            total_cost += trade_cost
            
            executed_trades.append({
                'level': level + 1,
                'price': price,
                'quantity': executed_qty,
                'cost': trade_cost
            })
            
            remaining_qty -= executed_qty
        
        if remaining_qty > 0:
            price_impact = 0.001 * (quantity / quantities[0])
            final_price = prices[-1] * (1 + price_impact if side == 'buy' else 1 - price_impact)
            trade_cost = remaining_qty * final_price
            total_cost += trade_cost
            
            executed_trades.append({
                'level': len(prices) + 1,
                'price': final_price,
                'quantity': remaining_qty,
                'cost': trade_cost
            })
        
        avg_price = total_cost / quantity if quantity > 0 else 0
        
        if side == 'buy':
            slippage_bps = (avg_price - start_price) / start_price * 10000
        else:
            slippage_bps = (start_price - avg_price) / start_price * 10000
        
        return avg_price, slippage_bps, executed_trades
    
    def get_impact_curve(self, max_quantity: int, steps: int = 20) -> pd.DataFrame:
        quantities = np.linspace(100, max_quantity, steps, dtype=int)
        
        results = []
        for qty in quantities:
            buy_avg, buy_slip, _ = self.calculate_impact(qty, 'buy')
            sell_avg, sell_slip, _ = self.calculate_impact(qty, 'sell')
            
            results.append({
                'quantity': qty,
                'buy_avg_price': buy_avg,
                'sell_avg_price': sell_avg,
                'buy_slippage_bps': buy_slip,
                'sell_slippage_bps': sell_slip
            })
        
        return pd.DataFrame(results)
    
    def get_depth_summary(self) -> pd.DataFrame:
        depth_data = []
        cumulative_bid = 0
        cumulative_ask = 0
        
        for _, row in self.order_book.iterrows():
            cumulative_bid += row['bid_quantity']
            cumulative_ask += row['ask_quantity']
            
            depth_data.append({
                'level': row['level'],
                'bid_price': row['bid_price'],
                'ask_price': row['ask_price'],
                'bid_quantity': row['bid_quantity'],
                'ask_quantity': row['ask_quantity'],
                'cumulative_bid': cumulative_bid,
                'cumulative_ask': cumulative_ask
            })
        
        return pd.DataFrame(depth_data)
