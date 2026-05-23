import asyncio
import websockets
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import threading
import time


@dataclass
class Order:
    order_id: str
    stock: str
    side: str
    quantity: int
    price: float
    status: str
    timestamp: datetime


@dataclass
class Position:
    stock: str
    quantity: int
    avg_cost: float
    current_price: float


@dataclass
class FactorSignal:
    timestamp: str
    factor_name: str
    stock: str
    factor_value: float
    group: int
    action: str


class SimulatedBroker:
    def __init__(self, initial_capital: float = 1000000.0):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions: Dict[str, Position] = {}
        self.orders: List[Order] = []
        self.order_id_counter = 0
        self.trade_history = []
        
    def get_portfolio_value(self, current_prices: Dict[str, float]) -> float:
        position_value = 0
        for stock, pos in self.positions.items():
            if stock in current_prices:
                position_value += pos.quantity * current_prices[stock]
        return self.cash + position_value
    
    def place_order(self, stock: str, side: str, quantity: int, 
                    price: float) -> Optional[Order]:
        self.order_id_counter += 1
        order_id = f"ORD_{self.order_id_counter:06d}"
        
        if side == 'BUY':
            total_cost = quantity * price
            if total_cost > self.cash:
                return None
        
        order = Order(
            order_id=order_id,
            stock=stock,
            side=side,
            quantity=quantity,
            price=price,
            status='FILLED',
            timestamp=datetime.now()
        )
        
        self._execute_order(order)
        return order
    
    def _execute_order(self, order: Order):
        if order.side == 'BUY':
            total_cost = order.quantity * order.price
            self.cash -= total_cost
            
            if order.stock in self.positions:
                pos = self.positions[order.stock]
                total_qty = pos.quantity + order.quantity
                total_cost = pos.quantity * pos.avg_cost + order.quantity * order.price
                pos.quantity = total_qty
                pos.avg_cost = total_cost / total_qty
            else:
                self.positions[order.stock] = Position(
                    stock=order.stock,
                    quantity=order.quantity,
                    avg_cost=order.price,
                    current_price=order.price
                )
        
        elif order.side == 'SELL':
            if order.stock in self.positions:
                pos = self.positions[order.stock]
                if pos.quantity >= order.quantity:
                    self.cash += order.quantity * order.price
                    pos.quantity -= order.quantity
                    if pos.quantity == 0:
                        del self.positions[order.stock]
        
        self.orders.append(order)
        self.trade_history.append(asdict(order))
    
    def get_positions_summary(self) -> Dict:
        return {
            'cash': self.cash,
            'positions': [asdict(pos) for pos in self.positions.values()],
            'position_count': len(self.positions)
        }


class SignalPusher:
    def __init__(self, host: str = 'localhost', port: int = 8765):
        self.host = host
        self.port = port
        self.clients = set()
        self.broker = SimulatedBroker()
        self.current_prices = {}
        self.is_running = False
        
    async def register_client(self, websocket):
        self.clients.add(websocket)
        print(f"新客户端连接, 当前连接数: {len(self.clients)}")
        
        try:
            await websocket.wait_closed()
        finally:
            self.clients.remove(websocket)
            print(f"客户端断开, 当前连接数: {len(self.clients)}")
    
    async def broadcast_signal(self, signal: FactorSignal):
        if not self.clients:
            return
        
        message = json.dumps({
            'type': 'SIGNAL',
            'data': {
                'timestamp': signal.timestamp,
                'factor_name': signal.factor_name,
                'stock': signal.stock,
                'factor_value': signal.factor_value,
                'group': signal.group,
                'action': signal.action
            }
        }, default=str)
        
        disconnected = set()
        for client in self.clients:
            try:
                await client.send(message)
            except:
                disconnected.add(client)
        
        for client in disconnected:
            self.clients.remove(client)
    
    async def broadcast_portfolio(self):
        if not self.clients:
            return
        
        portfolio_value = self.broker.get_portfolio_value(self.current_prices)
        
        message = json.dumps({
            'type': 'PORTFOLIO',
            'data': {
                'timestamp': datetime.now().isoformat(),
                'portfolio_value': portfolio_value,
                'cash': self.broker.cash,
                'positions': self.broker.get_positions_summary(),
                'pnl': portfolio_value - self.broker.initial_capital,
                'pnl_pct': (portfolio_value - self.broker.initial_capital) / self.broker.initial_capital * 100
            }
        }, default=str)
        
        disconnected = set()
        for client in self.clients:
            try:
                await client.send(message)
            except:
                disconnected.add(client)
        
        for client in disconnected:
            self.clients.remove(client)
    
    async def handle_message(self, websocket, path):
        await self.register_client(websocket)
        try:
            async for message in websocket:
                data = json.loads(message)
                if data.get('type') == 'ORDER':
                    order_data = data.get('data', {})
                    order = self.broker.place_order(
                        stock=order_data.get('stock'),
                        side=order_data.get('side'),
                        quantity=order_data.get('quantity', 100),
                        price=order_data.get('price', 0)
                    )
                    if order:
                        response = json.dumps({
                            'type': 'ORDER_CONFIRM',
                            'data': asdict(order)
                        }, default=str)
                        await websocket.send(response)
        except websockets.exceptions.ConnectionClosed:
            pass
    
    async def start_server(self):
        self.is_running = True
        server = await websockets.serve(self.handle_message, self.host, self.port)
        print(f"WebSocket服务启动: ws://{self.host}:{self.port}")
        await server.wait_closed()


class TradingSimulator:
    def __init__(self, factor_values: pd.DataFrame, 
                 price_data: pd.DataFrame,
                 groups: pd.DataFrame = None):
        self.factor_values = factor_values
        self.price_data = price_data
        self.groups = groups
        self.pusher = SignalPusher()
        self.current_date_idx = 0
        
    def generate_signals(self, date: pd.Timestamp, 
                         factor_name: str = 'factor') -> List[FactorSignal]:
        signals = []
        
        if date not in self.factor_values.index:
            return signals
        
        factor_on_date = self.factor_values.loc[date].dropna()
        
        for stock, value in factor_on_date.items():
            group = None
            if self.groups is not None and date in self.groups.index:
                group = self.groups.loc[date, stock]
                if pd.isna(group):
                    continue
                group = int(group)
            
            action = 'HOLD'
            if group == 1:
                action = 'STRONG_BUY'
            elif group <= 3:
                action = 'BUY'
            elif group >= 9:
                action = 'SELL'
            elif group == 10:
                action = 'STRONG_SELL'
            
            signal = FactorSignal(
                timestamp=date.isoformat(),
                factor_name=factor_name,
                stock=stock,
                factor_value=float(value),
                group=group,
                action=action
            )
            signals.append(signal)
        
        return signals
    
    async def run_simulation(self, start_idx: int = 0, 
                             factor_name: str = 'factor',
                             speed: float = 1.0):
        print(f"开始模拟交易, 因子: {factor_name}")
        
        server_thread = threading.Thread(
            target=lambda: asyncio.run(self.pusher.start_server()),
            daemon=True
        )
        server_thread.start()
        time.sleep(1)
        
        dates = self.factor_values.index[start_idx:]
        
        for i, date in enumerate(dates):
            self.current_date_idx = i
            
            if date in self.price_data.index:
                self.pusher.current_prices = self.price_data.loc[date].to_dict()
            
            signals = self.generate_signals(date, factor_name)
            
            for signal in signals[:20]:
                await self.pusher.broadcast_signal(signal)
                await asyncio.sleep(0.01 / speed)
            
            await self.pusher.broadcast_portfolio()
            
            print(f"\r模拟进度: {i+1}/{len(dates)} 日期: {date.date()}", end='')
            
            await asyncio.sleep(0.1 / speed)
        
        print("\n模拟完成!")
    
    def run_simulation_sync(self, **kwargs):
        asyncio.run(self.run_simulation(**kwargs))


class MockTradingClient:
    def __init__(self, uri: str = "ws://localhost:8765"):
        self.uri = uri
        self.received_signals = []
        self.portfolio_updates = []
        
    async def connect(self):
        async with websockets.connect(self.uri) as websocket:
            print(f"已连接到模拟交易服务器: {self.uri}")
            
            async for message in websocket:
                data = json.loads(message)
                msg_type = data.get('type')
                
                if msg_type == 'SIGNAL':
                    self.received_signals.append(data['data'])
                    if len(self.received_signals) % 100 == 0:
                        print(f"已接收 {len(self.received_signals)} 个信号")
                
                elif msg_type == 'PORTFOLIO':
                    self.portfolio_updates.append(data['data'])
                    portfolio = data['data']
                    print(f"\n资产净值: {portfolio['portfolio_value']:.2f}, "
                          f"盈亏: {portfolio['pnl']:.2f} ({portfolio['pnl_pct']:.2f}%)")
    
    def run(self):
        asyncio.run(self.connect())


def run_demo_server():
    from data_loader import DataLoader
    from factor_engine import FactorEngine
    from backtest import BacktestEngine
    
    print("=" * 60)
    print("模拟交易系统启动")
    print("=" * 60)
    
    loader = DataLoader()
    loader.generate_sample_data(n_stocks=50, start_date='2023-01-01', end_date='2023-12-31')
    price, factors, suspend, delist, industry = loader.load_data()
    returns = loader.calculate_daily_returns()
    mkt_cap = factors.get('MKT_CAP')
    
    engine = FactorEngine(factors)
    factor = engine.calculate_factor('1 / PE')
    factor_ffill = loader.forward_fill_factor_for_suspend(factor)
    
    backtest = BacktestEngine(returns, suspend, delist, industry, mkt_cap)
    rebalance_dates = backtest.get_rebalance_dates(freq='W')
    groups = backtest.assign_groups(factor_ffill, rebalance_dates)
    
    simulator = TradingSimulator(factor_ffill, price, groups)
    
    print("\nWebSocket服务器将在 ws://localhost:8765 启动")
    print("运行以下命令启动客户端进行监听:")
    print("  python simulated_trading.py --client")
    print("\n按 Ctrl+C 停止服务器")
    print("=" * 60)
    
    try:
        simulator.run_simulation_sync(factor_name='EP_Factor', speed=2.0)
    except KeyboardInterrupt:
        print("\n模拟已停止")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='模拟交易系统')
    parser.add_argument('--client', action='store_true', help='运行客户端')
    
    args = parser.parse_args()
    
    if args.client:
        client = MockTradingClient()
        client.run()
    else:
        run_demo_server()
