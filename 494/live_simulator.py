import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import threading
import time
import json
import os
import warnings
warnings.filterwarnings('ignore')

import yfinance as yf

from backtest_engine import BacktestEngine


class Position:
    def __init__(self, symbol: str, direction: str, entry_price: float,
                 size: float, entry_time: datetime, stop_loss: float = None,
                 take_profit: float = None):
        self.symbol = symbol
        self.direction = direction
        self.entry_price = entry_price
        self.size = size
        self.entry_time = entry_time
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.current_price = entry_price
        self.unrealized_pnl = 0.0
        self.max_profit = 0.0
        self.max_loss = 0.0
    
    def update_price(self, current_price: float):
        self.current_price = current_price
        if self.direction == 'long':
            self.unrealized_pnl = (current_price - self.entry_price) * self.size
        else:
            self.unrealized_pnl = (self.entry_price - current_price) * self.size
        
        if self.unrealized_pnl > self.max_profit:
            self.max_profit = self.unrealized_pnl
        if self.unrealized_pnl < self.max_loss:
            self.max_loss = self.unrealized_pnl
    
    def check_stop_loss(self) -> bool:
        if self.stop_loss is None:
            return False
        if self.direction == 'long':
            return self.current_price <= self.stop_loss
        else:
            return self.current_price >= self.stop_loss
    
    def check_take_profit(self) -> bool:
        if self.take_profit is None:
            return False
        if self.direction == 'long':
            return self.current_price >= self.take_profit
        else:
            return self.current_price <= self.take_profit
    
    def to_dict(self) -> Dict:
        return {
            'symbol': self.symbol,
            'direction': self.direction,
            'entry_price': self.entry_price,
            'current_price': self.current_price,
            'size': self.size,
            'entry_time': self.entry_time.isoformat(),
            'unrealized_pnl': self.unrealized_pnl,
            'max_profit': self.max_profit,
            'max_loss': self.max_loss,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit
        }


class Order:
    def __init__(self, symbol: str, direction: str, order_type: str,
                 quantity: float, price: float = None, 
                 stop_price: float = None, limit_price: float = None):
        self.symbol = symbol
        self.direction = direction
        self.order_type = order_type
        self.quantity = quantity
        self.price = price
        self.stop_price = stop_price
        self.limit_price = limit_price
        self.status = 'pending'
        self.fill_price = None
        self.fill_time = None
        self.commission = 0.0
        self.created_time = datetime.now()
    
    def to_dict(self) -> Dict:
        return {
            'symbol': self.symbol,
            'direction': self.direction,
            'order_type': self.order_type,
            'quantity': self.quantity,
            'price': self.price,
            'status': self.status,
            'fill_price': self.fill_price,
            'fill_time': self.fill_time.isoformat() if self.fill_time else None,
            'commission': self.commission,
            'created_time': self.created_time.isoformat()
        }


class LiveSimulator:
    
    def __init__(self, initial_cash: float = 100000.0, commission: float = 0.001,
                 slippage: float = 0.001, strategy_name: str = '双均线策略',
                 strategy_params: Dict = None):
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.commission = commission
        self.slippage = slippage
        self.strategy_name = strategy_name
        self.strategy_params = strategy_params or {}
        
        self.positions: Dict[str, Position] = {}
        self.orders: List[Order] = []
        self.trade_history: List[Dict] = []
        self.equity_history: List[Dict] = []
        
        self.is_running = False
        self._thread = None
        self._stop_event = threading.Event()
        
        self.price_data: Dict[str, pd.DataFrame] = {}
        self.current_prices: Dict[str, float] = {}
        self.last_update: Dict[str, datetime] = {}
        
        self._state_file = 'live_sim_state.json'
    
    def subscribe(self, symbol: str):
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="5d", interval="1m")
            if not hist.empty:
                self.price_data[symbol] = hist
                self.current_prices[symbol] = hist['Close'].iloc[-1]
                self.last_update[symbol] = datetime.now()
        except Exception as e:
            print(f"订阅 {symbol} 失败: {e}")
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        return self.current_prices.get(symbol)
    
    def update_price(self, symbol: str):
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="1d", interval="1m")
            if not hist.empty:
                self.price_data[symbol] = hist
                self.current_prices[symbol] = hist['Close'].iloc[-1]
                self.last_update[symbol] = datetime.now()
                
                if symbol in self.positions:
                    self.positions[symbol].update_price(self.current_prices[symbol])
                    self._check_stop_take_profit(symbol)
        except Exception as e:
            print(f"更新 {symbol} 价格失败: {e}")
    
    def simulate_price_tick(self, symbol: str, base_price: float = None) -> Dict:
        if base_price is None:
            base_price = self.current_prices.get(symbol, 100.0)
        
        drift = np.random.normal(0, 0.002)
        vol = np.random.normal(0, 0.005)
        change_pct = drift + vol
        
        new_price = base_price * (1 + change_pct)
        self.current_prices[symbol] = new_price
        self.last_update[symbol] = datetime.now()
        
        if symbol in self.positions:
            self.positions[symbol].update_price(new_price)
        
        tick = {
            'symbol': symbol,
            'price': new_price,
            'change_pct': change_pct * 100,
            'timestamp': datetime.now().isoformat(),
            'volume': int(np.random.exponential(10000))
        }
        
        return tick
    
    def place_order(self, symbol: str, direction: str, quantity: float,
                     order_type: str = 'market', price: float = None,
                     stop_price: float = None, limit_price: float = None) -> Order:
        order = Order(
            symbol=symbol,
            direction=direction,
            order_type=order_type,
            quantity=quantity,
            price=price,
            stop_price=stop_price,
            limit_price=limit_price
        )
        self.orders.append(order)
        
        if order_type == 'market':
            self._execute_market_order(order)
        
        return order
    
    def _execute_market_order(self, order: Order):
        current_price = self.current_prices.get(order.symbol)
        if current_price is None:
            order.status = 'rejected'
            return
        
        if order.direction == 'buy':
            fill_price = current_price * (1 + self.slippage)
        else:
            fill_price = current_price * (1 - self.slippage)
        
        order.fill_price = fill_price
        order.fill_time = datetime.now()
        order.commission = abs(order.quantity * fill_price * self.commission)
        order.status = 'filled'
        
        if order.direction == 'buy':
            cost = order.quantity * fill_price + order.commission
            if cost > self.cash:
                order.status = 'rejected'
                return
            
            self.cash -= cost
            
            position = Position(
                symbol=order.symbol,
                direction='long',
                entry_price=fill_price,
                size=order.quantity,
                entry_time=datetime.now()
            )
            self.positions[order.symbol] = position
            
        elif order.direction == 'sell':
            if order.symbol not in self.positions:
                order.status = 'rejected'
                return
            
            position = self.positions[order.symbol]
            proceeds = order.quantity * fill_price - order.commission
            realized_pnl = (fill_price - position.entry_price) * order.quantity - order.commission
            
            self.cash += proceeds
            
            self.trade_history.append({
                'symbol': order.symbol,
                'direction': 'sell',
                'entry_price': position.entry_price,
                'exit_price': fill_price,
                'size': order.quantity,
                'realized_pnl': realized_pnl,
                'commission': order.commission,
                'entry_time': position.entry_time.isoformat(),
                'exit_time': datetime.now().isoformat(),
                'max_profit': position.max_profit,
                'max_loss': position.max_loss
            })
            
            del self.positions[order.symbol]
        
        self._record_equity()
    
    def _check_stop_take_profit(self, symbol: str):
        if symbol not in self.positions:
            return
        
        position = self.positions[symbol]
        
        if position.check_stop_loss():
            self.place_order(symbol, 'sell', position.size, 'market')
            self.trade_history[-1]['exit_reason'] = 'stop_loss' if self.trade_history else 'stop_loss'
        
        elif position.check_take_profit():
            self.place_order(symbol, 'sell', position.size, 'market')
            self.trade_history[-1]['exit_reason'] = 'take_profit' if self.trade_history else 'take_profit'
    
    def _record_equity(self):
        total_value = self.cash
        unrealized_pnl = 0.0
        
        for symbol, position in self.positions.items():
            market_value = position.size * position.current_price
            total_value += market_value
            unrealized_pnl += position.unrealized_pnl
        
        self.equity_history.append({
            'timestamp': datetime.now().isoformat(),
            'cash': self.cash,
            'positions_value': total_value - self.cash,
            'total_value': total_value,
            'unrealized_pnl': unrealized_pnl,
            'total_pnl': total_value - self.initial_cash,
            'return_pct': (total_value - self.initial_cash) / self.initial_cash * 100
        })
    
    def get_portfolio_summary(self) -> Dict:
        total_value = self.cash
        positions_list = []
        
        for symbol, position in self.positions.items():
            market_value = position.size * position.current_price
            total_value += market_value
            positions_list.append(position.to_dict())
        
        return {
            'total_value': total_value,
            'cash': self.cash,
            'positions_value': total_value - self.cash,
            'total_pnl': total_value - self.initial_cash,
            'return_pct': (total_value - self.initial_cash) / self.initial_cash * 100,
            'positions': positions_list,
            'num_positions': len(self.positions),
            'num_trades': len(self.trade_history),
            'current_prices': self.current_prices.copy()
        }
    
    def start_simulation(self, symbol: str, mode: str = 'simulated',
                          interval_seconds: int = 5, callback=None):
        self.is_running = True
        self._stop_event.clear()
        
        def run():
            while not self._stop_event.is_set():
                try:
                    if mode == 'live':
                        self.update_price(symbol)
                    else:
                        self.simulate_price_tick(symbol)
                    
                    self._check_stop_take_profit(symbol)
                    
                    if callback:
                        summary = self.get_portfolio_summary()
                        callback(summary)
                    
                    self._stop_event.wait(interval_seconds)
                except Exception as e:
                    print(f"模拟运行错误: {e}")
                    self._stop_event.wait(interval_seconds)
        
        self._thread = threading.Thread(target=run, daemon=True)
        self._thread.start()
    
    def stop_simulation(self):
        self.is_running = False
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=10)
    
    def run_strategy_on_tick(self, symbol: str, data_window: pd.DataFrame) -> Optional[str]:
        if len(data_window) < 30:
            return None
        
        strategy_class = BacktestEngine.STRATEGIES.get(self.strategy_name)
        if not strategy_class:
            return None
        
        try:
            cerebro = bt.Cerebro(stdstats=False)
            cerebro.broker.setcash(self.initial_cash)
            cerebro.broker.setcommission(commission=self.commission)
            cerebro.addstrategy(strategy_class, **self.strategy_params)
            
            bt_data = bt.feeds.PandasData(dataname=data_window)
            cerebro.adddata(bt_data)
            
            results = cerebro.run()
            strat = results[0]
            
            if strat.trades and len(strat.trades) > 0:
                last_trade = strat.trades[-1]
                return last_trade['type']
        except:
            pass
        
        return None
    
    def save_state(self):
        state = {
            'cash': self.cash,
            'initial_cash': self.initial_cash,
            'positions': {k: v.to_dict() for k, v in self.positions.items()},
            'trade_history': self.trade_history,
            'equity_history': self.equity_history[-1000:],
            'current_prices': self.current_prices,
            'strategy_name': self.strategy_name,
            'strategy_params': self.strategy_params,
            'commission': self.commission,
            'slippage': self.slippage
        }
        
        with open(self._state_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, default=str, indent=2)
    
    def load_state(self) -> bool:
        if not os.path.exists(self._state_file):
            return False
        
        try:
            with open(self._state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)
            
            self.cash = state['cash']
            self.initial_cash = state['initial_cash']
            self.current_prices = state.get('current_prices', {})
            self.trade_history = state.get('trade_history', [])
            self.equity_history = state.get('equity_history', [])
            self.strategy_name = state.get('strategy_name', self.strategy_name)
            self.strategy_params = state.get('strategy_params', self.strategy_params)
            self.commission = state.get('commission', self.commission)
            self.slippage = state.get('slippage', self.slippage)
            
            for symbol, pos_data in state.get('positions', {}).items():
                position = Position(
                    symbol=symbol,
                    direction=pos_data['direction'],
                    entry_price=pos_data['entry_price'],
                    size=pos_data['size'],
                    entry_time=datetime.fromisoformat(pos_data['entry_time']),
                    stop_loss=pos_data.get('stop_loss'),
                    take_profit=pos_data.get('take_profit')
                )
                position.current_price = pos_data.get('current_price', pos_data['entry_price'])
                position.unrealized_pnl = pos_data.get('unrealized_pnl', 0)
                self.positions[symbol] = position
            
            return True
        except Exception as e:
            print(f"加载状态失败: {e}")
            return False
    
    def get_trade_statistics(self) -> Dict:
        if not self.trade_history:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'avg_profit': 0,
                'avg_loss': 0,
                'total_pnl': 0,
                'max_win': 0,
                'max_loss': 0,
                'profit_factor': 0
            }
        
        pnls = [t['realized_pnl'] for t in self.trade_history]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]
        
        return {
            'total_trades': len(pnls),
            'winning_trades': len(wins),
            'losing_trades': len(losses),
            'win_rate': len(wins) / len(pnls) * 100 if pnls else 0,
            'avg_profit': np.mean(wins) if wins else 0,
            'avg_loss': np.mean(losses) if losses else 0,
            'total_pnl': sum(pnls),
            'max_win': max(pnls) if pnls else 0,
            'max_loss': min(pnls) if pnls else 0,
            'profit_factor': abs(sum(wins) / sum(losses)) if losses and sum(losses) != 0 else float('inf')
        }
