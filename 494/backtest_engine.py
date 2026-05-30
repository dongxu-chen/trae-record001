import backtrader as bt
import pandas as pd
import numpy as np
from datetime import datetime
import yfinance as yf
from typing import Dict, List, Tuple, Optional, Callable


class SlippageModel(bt.Sizer):
    params = (
        ('slippage_perc', 0.001),
    )
    
    def _getsizing(self, comminfo, cash, data, isbuy):
        return 0


class FixedSlippage(bt.CommissionInfo):
    params = (
        ('slippage_fixed', 0.0),
        ('slippage_perc', 0.001),
    )
    
    def getsize(self, price, cash):
        return self.p.leverage * (cash / price)
    
    def getcommission(self, size, price):
        return max(abs(size) * price * self.p.commission, self.p.stamp_duty)
    
    def getoperationcost(self, size, price):
        slippage = price * self.p.slippage_perc + self.p.slippage_fixed
        return abs(size) * (price + slippage) * self.p.commission


class BaseStrategy(bt.Strategy):
    params = ()
    
    def __init__(self):
        self.order = None
        self.buyprice = None
        self.buycomm = None
        self.trades = []
        self.equity_curve = []
        self.init_indicators()
    
    def init_indicators(self):
        pass
    
    def next(self):
        self.equity_curve.append(self.broker.getvalue())
    
    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        
        if order.status in [order.Completed]:
            timestamp = self.data.datetime.datetime(0)
            if order.isbuy():
                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
                self.trades.append({
                    'timestamp': timestamp,
                    'date': timestamp.date(),
                    'type': 'buy',
                    'price': order.executed.price,
                    'size': order.executed.size,
                    'commission': order.executed.comm,
                    'value': order.executed.value,
                    'slippage': abs(order.executed.price - self.data.open[0]) / self.data.open[0]
                })
            else:
                self.trades.append({
                    'timestamp': timestamp,
                    'date': timestamp.date(),
                    'type': 'sell',
                    'price': order.executed.price,
                    'size': order.executed.size,
                    'commission': order.executed.comm,
                    'value': order.executed.value,
                    'slippage': abs(order.executed.price - self.data.open[0]) / self.data.open[0]
                })
        
        self.order = None
    
    def notify_trade(self, trade):
        if not trade.isclosed:
            return
        if self.trades:
            self.trades[-1]['pnl'] = trade.pnl
            self.trades[-1]['pnlcomm'] = trade.pnlcomm


class MACrossStrategy(BaseStrategy):
    params = (
        ('fast_period', 5),
        ('slow_period', 20),
    )
    
    def init_indicators(self):
        self.fast_ma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.params.fast_period)
        self.slow_ma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.params.slow_period)
        self.crossover = bt.indicators.CrossOver(self.fast_ma, self.slow_ma)
    
    def next(self):
        super().next()
        if self.order:
            return
        
        if not self.position:
            if self.crossover > 0:
                self.order = self.buy()
        else:
            if self.crossover < 0:
                self.order = self.sell()


class RSIStrategy(BaseStrategy):
    params = (
        ('rsi_period', 14),
        ('rsi_overbought', 70),
        ('rsi_oversold', 30),
    )
    
    def init_indicators(self):
        self.rsi = bt.indicators.RSI(
            self.data.close, period=self.params.rsi_period)
    
    def next(self):
        super().next()
        if self.order:
            return
        
        if not self.position:
            if self.rsi < self.params.rsi_oversold:
                self.order = self.buy()
        else:
            if self.rsi > self.params.rsi_overbought:
                self.order = self.sell()


class MACDStrategy(BaseStrategy):
    params = (
        ('macd_fast', 12),
        ('macd_slow', 26),
        ('macd_signal', 9),
    )
    
    def init_indicators(self):
        self.macd = bt.indicators.MACD(
            self.data.close,
            period_me1=self.params.macd_fast,
            period_me2=self.params.macd_slow,
            period_signal=self.params.macd_signal
        )
        self.crossover = bt.indicators.CrossOver(
            self.macd.macd, self.macd.signal)
    
    def next(self):
        super().next()
        if self.order:
            return
        
        if not self.position:
            if self.crossover > 0:
                self.order = self.buy()
        else:
            if self.crossover < 0:
                self.order = self.sell()


class BollingerBandsStrategy(BaseStrategy):
    params = (
        ('bb_period', 20),
        ('bb_dev', 2.0),
    )
    
    def init_indicators(self):
        self.bb = bt.indicators.BollingerBands(
            self.data.close,
            period=self.params.bb_period,
            devfactor=self.params.bb_dev
        )
    
    def next(self):
        super().next()
        if self.order:
            return
        
        if not self.position:
            if self.data.close < self.bb.bot:
                self.order = self.buy()
        else:
            if self.data.close > self.bb.top:
                self.order = self.sell()


class BacktestEngine:
    STRATEGIES = {
        '双均线策略': MACrossStrategy,
        'RSI策略': RSIStrategy,
        'MACD策略': MACDStrategy,
        '布林带策略': BollingerBandsStrategy,
    }
    
    def __init__(self, initial_cash: float = 100000.0, commission: float = 0.001, 
                 slippage: float = 0.001, stamp_duty: float = 0.0):
        self.initial_cash = initial_cash
        self.commission = commission
        self.slippage = slippage
        self.stamp_duty = stamp_duty
        self.cerebro = None
        self.results = None
        self.data = None
    
    def load_data(self, ticker: str, start_date: str, end_date: str, 
                  data_source: str = 'yfinance') -> pd.DataFrame:
        if data_source == 'yfinance':
            data = yf.download(ticker, start=start_date, end=end_date)
            if data.empty:
                raise ValueError(f"无法获取股票数据: {ticker}")
            if hasattr(data.columns, 'levels') and len(data.columns.levels) > 1:
                data.columns = data.columns.droplevel(1)
            data = data.rename(columns={
                'Open': 'open',
                'High': 'high',
                'Low': 'low',
                'Close': 'close',
                'Volume': 'volume'
            })
            data = data[['open', 'high', 'low', 'close', 'volume']]
        else:
            raise ValueError(f"不支持的数据源: {data_source}")
        
        self.data = data
        return data
    
    def run_backtest(self, strategy_name: str, data: pd.DataFrame, 
                     strategy_params: Dict = None) -> Dict:
        strategy_params = strategy_params or {}
        
        self.cerebro = bt.Cerebro(stdstats=False)
        self.cerebro.broker.setcash(self.initial_cash)
        
        self.cerebro.broker.setcommission(
            commission=self.commission,
            margin=None,
            mult=1.0
        )
        
        if self.slippage > 0:
            self.cerebro.broker.set_slippage_perc(
                perc=self.slippage,
                slip_open=True,
                slip_match=True,
                slip_out=True
            )
        
        self.cerebro.addsizer(bt.sizers.PercentSizer, percents=95)
        
        strategy_class = self.STRATEGIES.get(strategy_name)
        if not strategy_class:
            raise ValueError(f"策略不存在: {strategy_name}")
        
        self.cerebro.addstrategy(strategy_class, **strategy_params)
        
        bt_data = bt.feeds.PandasData(dataname=data)
        self.cerebro.adddata(bt_data)
        self.data = data
        
        self.cerebro.addobserver(bt.observers.Value)
        self.cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe', 
                                  timeframe=bt.TimeFrame.Days, annualize=True,
                                  riskfreerate=0.03)
        self.cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        self.cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
        self.cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
        self.cerebro.addanalyzer(bt.analyzers.TimeReturn, _name='timereturn')
        
        self.results = self.cerebro.run()
        
        return self._calculate_metrics()
    
    def _calculate_metrics(self) -> Dict:
        strat = self.results[0]
        
        final_value = self.cerebro.broker.getvalue()
        total_return = (final_value - self.initial_cash) / self.initial_cash * 100
        
        sharpe_ratio = strat.analyzers.sharpe.get_analysis().get('sharperatio', 0)
        sharpe_ratio = sharpe_ratio if sharpe_ratio is not None else 0
        
        drawdown = strat.analyzers.drawdown.get_analysis()
        max_drawdown = drawdown.get('max', {}).get('drawdown', 0)
        
        trade_analyzer = strat.analyzers.trades.get_analysis()
        total_trades = trade_analyzer.get('total', {}).get('total', 0)
        won_trades = trade_analyzer.get('won', {}).get('total', 0)
        lost_trades = trade_analyzer.get('lost', {}).get('total', 0)
        
        win_rate = (won_trades / total_trades * 100) if total_trades > 0 else 0
        
        avg_win = trade_analyzer.get('won', {}).get('pnl', {}).get('average', 0)
        avg_loss = trade_analyzer.get('lost', {}).get('pnl', {}).get('average', 0)
        
        profit_factor = abs(avg_win * won_trades / (avg_loss * lost_trades)) if (lost_trades > 0 and avg_loss != 0) else float('inf')
        
        annual_return = strat.analyzers.returns.get_analysis().get('rnorm100', 0)
        
        equity_curve = []
        if hasattr(strat, 'equity_curve') and strat.equity_curve:
            equity_curve = strat.equity_curve
        else:
            for i in range(len(self.data)):
                equity_curve.append(self.initial_cash)
        
        if len(equity_curve) < len(self.data):
            padding = [equity_curve[-1] if equity_curve else self.initial_cash] * (len(self.data) - len(equity_curve))
            equity_curve = equity_curve + padding
        
        total_commission = sum(t.get('commission', 0) for t in strat.trades)
        total_slippage = sum(t.get('slippage', 0) for t in strat.trades)
        avg_slippage = total_slippage / len(strat.trades) if strat.trades else 0
        
        return {
            'final_value': final_value,
            'total_return': total_return,
            'annual_return': annual_return,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'total_trades': total_trades,
            'won_trades': won_trades,
            'lost_trades': lost_trades,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'trades': strat.trades,
            'equity_curve': equity_curve,
            'total_commission': total_commission,
            'avg_slippage': avg_slippage
        }


def create_custom_strategy(indicator_logic: str, buy_condition: str, 
                           sell_condition: str, params: Dict = None) -> type:
    params = params or {}
    
    class CustomStrategy(BaseStrategy):
        param_list = [(k, v) for k, v in params.items()]
        params = tuple(param_list) if param_list else ()
        
        def init_indicators(self):
            self.custom_indicators = {}
            for name, formula in indicator_logic.items():
                exec(f"self.custom_indicators['{name}'] = {formula}")
        
        def next(self):
            super().next()
            if self.order:
                return
            
            try:
                if not self.position:
                    if eval(buy_condition, {'self': self, 'bt': bt}):
                        self.order = self.buy()
                else:
                    if eval(sell_condition, {'self': self, 'bt': bt}):
                        self.order = self.sell()
            except:
                pass
    
    return CustomStrategy
