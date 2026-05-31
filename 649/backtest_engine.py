import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum


class PositionType(Enum):
    LONG = "long"
    SHORT = "short"
    FLAT = "flat"


@dataclass
class Trade:
    entry_date: pd.Timestamp
    entry_price: float
    exit_date: Optional[pd.Timestamp] = None
    exit_price: Optional[float] = None
    position_type: PositionType = PositionType.LONG
    pattern: str = ""
    confidence: float = 0.0
    pnl: float = 0.0
    pnl_pct: float = 0.0
    entry_slippage: float = 0.0
    exit_slippage: float = 0.0
    commission: float = 0.0
    total_cost: float = 0.0


@dataclass
class BacktestResult:
    total_return: float
    annual_return: float
    volatility: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    avg_pnl_per_trade: float
    avg_win_pnl: float
    avg_loss_pnl: float
    profit_factor: float
    total_slippage: float
    total_commission: float
    total_trading_cost: float
    trades: List[Trade]
    equity_curve: pd.Series


class SlippageModel:
    def __init__(self, 
                 fixed_slippage: float = 0.0,
                 percentage_slippage: float = 0.001,
                 commission_rate: float = 0.0003,
                 min_commission: float = 5.0):
        self.fixed_slippage = fixed_slippage
        self.percentage_slippage = percentage_slippage
        self.commission_rate = commission_rate
        self.min_commission = min_commission
    
    def calculate_entry_slippage(self, price: float, quantity: float, is_long: bool) -> float:
        slippage = self.fixed_slippage + (price * self.percentage_slippage)
        if is_long:
            return slippage * quantity
        else:
            return -slippage * quantity
    
    def calculate_exit_slippage(self, price: float, quantity: float, is_long: bool) -> float:
        slippage = self.fixed_slippage + (price * self.percentage_slippage)
        if is_long:
            return -slippage * quantity
        else:
            return slippage * quantity
    
    def calculate_commission(self, notional_value: float) -> float:
        commission = notional_value * self.commission_rate
        return max(commission, self.min_commission)
    
    def calculate_total_cost(self, 
                           entry_price: float, 
                           exit_price: float, 
                           quantity: float,
                           is_long: bool) -> Dict[str, float]:
        entry_slippage = self.calculate_entry_slippage(entry_price, quantity, is_long)
        exit_slippage = self.calculate_exit_slippage(exit_price, quantity, is_long)
        
        entry_notional = entry_price * quantity
        exit_notional = exit_price * quantity
        entry_commission = self.calculate_commission(entry_notional)
        exit_commission = self.calculate_commission(exit_notional)
        total_commission = entry_commission + exit_commission
        
        total_slippage = entry_slippage + exit_slippage
        total_cost = total_slippage + total_commission
        
        return {
            'entry_slippage': entry_slippage,
            'exit_slippage': exit_slippage,
            'entry_commission': entry_commission,
            'exit_commission': exit_commission,
            'total_slippage': total_slippage,
            'total_commission': total_commission,
            'total_cost': total_cost
        }


class BacktestEngine:
    def __init__(self, 
                 df: pd.DataFrame,
                 initial_capital: float = 100000.0,
                 position_size: float = 0.1,
                 stop_loss_pct: float = 0.02,
                 take_profit_pct: float = 0.04,
                 hold_period: int = 10,
                 slippage_model: Optional[SlippageModel] = None):
        self.df = df.copy().sort_index()
        self.initial_capital = initial_capital
        self.position_size = position_size
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.hold_period = hold_period
        self.slippage_model = slippage_model or SlippageModel()
        
        self._validate_data()
    
    def _validate_data(self):
        required_cols = ['Open', 'High', 'Low', 'Close']
        for col in required_cols:
            if col not in self.df.columns:
                raise ValueError(f"DataFrame must contain '{col}' column")
    
    def run_backtest(self, patterns: List[Dict]) -> BacktestResult:
        capital = self.initial_capital
        equity_history = [capital]
        dates = [self.df.index[0]]
        
        open_trades: List[Trade] = []
        closed_trades: List[Trade] = []
        
        total_slippage = 0.0
        total_commission = 0.0
        
        pattern_dict = {p['index']: p for p in patterns}
        
        for idx, (date, row) in enumerate(self.df.iterrows()):
            current_price = row['Close']
            
            trades_to_close = []
            for i, trade in enumerate(open_trades):
                trade_idx = self.df.index.get_loc(trade.entry_date)
                days_held = idx - trade_idx
                
                exit_trade = False
                exit_price = current_price
                
                is_long = trade.position_type == PositionType.LONG
                
                if is_long:
                    stop_loss_price = trade.entry_price * (1 - self.stop_loss_pct)
                    take_profit_price = trade.entry_price * (1 + self.take_profit_pct)
                    
                    if row['Low'] <= stop_loss_price:
                        exit_price = stop_loss_price
                        exit_trade = True
                    elif row['High'] >= take_profit_price:
                        exit_price = take_profit_price
                        exit_trade = True
                    elif days_held >= self.hold_period:
                        exit_trade = True
                else:
                    stop_loss_price = trade.entry_price * (1 + self.stop_loss_pct)
                    take_profit_price = trade.entry_price * (1 - self.take_profit_pct)
                    
                    if row['High'] >= stop_loss_price:
                        exit_price = stop_loss_price
                        exit_trade = True
                    elif row['Low'] <= take_profit_price:
                        exit_price = take_profit_price
                        exit_trade = True
                    elif days_held >= self.hold_period:
                        exit_trade = True
                
                if exit_trade:
                    trade.exit_date = date
                    trade.exit_price = exit_price
                    
                    notional_value = capital * self.position_size
                    quantity = notional_value / trade.entry_price
                    
                    costs = self.slippage_model.calculate_total_cost(
                        trade.entry_price, exit_price, quantity, is_long
                    )
                    
                    trade.entry_slippage = costs['entry_slippage']
                    trade.exit_slippage = costs['exit_slippage']
                    trade.commission = costs['total_commission']
                    trade.total_cost = costs['total_cost']
                    
                    total_slippage += costs['total_slippage']
                    total_commission += costs['total_commission']
                    
                    if is_long:
                        gross_pnl = (exit_price - trade.entry_price) * quantity
                    else:
                        gross_pnl = (trade.entry_price - exit_price) * quantity
                    
                    trade.pnl = gross_pnl - trade.total_cost
                    trade.pnl_pct = trade.pnl / notional_value if notional_value > 0 else 0
                    
                    capital += trade.pnl
                    trades_to_close.append(i)
            
            for i in sorted(trades_to_close, reverse=True):
                closed_trades.append(open_trades.pop(i))
            
            if idx in pattern_dict and len(open_trades) < 5:
                pattern = pattern_dict[idx]
                position_type = PositionType.LONG if pattern['prediction'] == 'up' else PositionType.SHORT
                
                trade = Trade(
                    entry_date=date,
                    entry_price=current_price,
                    position_type=position_type,
                    pattern=pattern['pattern'],
                    confidence=pattern['confidence']
                )
                open_trades.append(trade)
            
            total_open_pnl = 0
            for trade in open_trades:
                notional_value = capital * self.position_size
                quantity = notional_value / trade.entry_price
                is_long = trade.position_type == PositionType.LONG
                
                if is_long:
                    unrealized_pnl = (current_price - trade.entry_price) * quantity
                else:
                    unrealized_pnl = (trade.entry_price - current_price) * quantity
                total_open_pnl += unrealized_pnl
            
            equity_history.append(capital + total_open_pnl)
            dates.append(date)
        
        for trade in open_trades:
            trade.exit_date = self.df.index[-1]
            trade.exit_price = self.df['Close'].iloc[-1]
            
            notional_value = capital * self.position_size
            quantity = notional_value / trade.entry_price
            is_long = trade.position_type == PositionType.LONG
            
            costs = self.slippage_model.calculate_total_cost(
                trade.entry_price, trade.exit_price, quantity, is_long
            )
            
            trade.entry_slippage = costs['entry_slippage']
            trade.exit_slippage = costs['exit_slippage']
            trade.commission = costs['total_commission']
            trade.total_cost = costs['total_cost']
            
            total_slippage += costs['total_slippage']
            total_commission += costs['total_commission']
            
            if is_long:
                gross_pnl = (trade.exit_price - trade.entry_price) * quantity
            else:
                gross_pnl = (trade.entry_price - trade.exit_price) * quantity
            
            trade.pnl = gross_pnl - trade.total_cost
            trade.pnl_pct = trade.pnl / notional_value if notional_value > 0 else 0
            
            capital += trade.pnl
            closed_trades.append(trade)
        
        equity_curve = pd.Series(equity_history, index=pd.DatetimeIndex(dates), name='Equity')
        
        return self._calculate_metrics(
            closed_trades, 
            equity_curve, 
            total_slippage, 
            total_commission
        )
    
    def _calculate_metrics(self, 
                          trades: List[Trade], 
                          equity_curve: pd.Series,
                          total_slippage: float,
                          total_commission: float) -> BacktestResult:
        if len(trades) == 0:
            return BacktestResult(
                total_return=0,
                annual_return=0,
                volatility=0,
                sharpe_ratio=0,
                max_drawdown=0,
                win_rate=0,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                avg_pnl_per_trade=0,
                avg_win_pnl=0,
                avg_loss_pnl=0,
                profit_factor=0,
                total_slippage=total_slippage,
                total_commission=total_commission,
                total_trading_cost=total_slippage + total_commission,
                trades=trades,
                equity_curve=equity_curve
            )
        
        final_equity = equity_curve.iloc[-1]
        total_return = (final_equity - self.initial_capital) / self.initial_capital
        
        days = (equity_curve.index[-1] - equity_curve.index[0]).days
        annual_return = (1 + total_return) ** (365 / max(1, days)) - 1 if days > 0 else 0
        
        daily_returns = equity_curve.pct_change().dropna()
        volatility = daily_returns.std() * np.sqrt(252) if len(daily_returns) > 0 else 0
        
        risk_free_rate = 0.02
        sharpe_ratio = (annual_return - risk_free_rate) / volatility if volatility > 0 else 0
        
        running_max = equity_curve.expanding().max()
        drawdown = (equity_curve - running_max) / running_max
        max_drawdown = drawdown.min()
        
        winning_trades = [t for t in trades if t.pnl > 0]
        losing_trades = [t for t in trades if t.pnl <= 0]
        
        win_rate = len(winning_trades) / len(trades) if trades else 0
        
        avg_pnl_per_trade = sum(t.pnl for t in trades) / len(trades) if trades else 0
        avg_win_pnl = sum(t.pnl for t in winning_trades) / len(winning_trades) if winning_trades else 0
        avg_loss_pnl = sum(t.pnl for t in losing_trades) / len(losing_trades) if losing_trades else 0
        
        gross_profit = sum(t.pnl for t in winning_trades)
        gross_loss = abs(sum(t.pnl for t in losing_trades))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        total_trading_cost = total_slippage + total_commission
        
        return BacktestResult(
            total_return=total_return,
            annual_return=annual_return,
            volatility=volatility,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            total_trades=len(trades),
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            avg_pnl_per_trade=avg_pnl_per_trade,
            avg_win_pnl=avg_win_pnl,
            avg_loss_pnl=avg_loss_pnl,
            profit_factor=profit_factor,
            total_slippage=total_slippage,
            total_commission=total_commission,
            total_trading_cost=total_trading_cost,
            trades=trades,
            equity_curve=equity_curve
        )
    
    def get_pattern_analysis(self, trades: List[Trade]) -> pd.DataFrame:
        pattern_stats = {}
        
        for trade in trades:
            pattern = trade.pattern
            if pattern not in pattern_stats:
                pattern_stats[pattern] = {
                    'total': 0,
                    'wins': 0,
                    'losses': 0,
                    'total_pnl': 0,
                    'avg_pnl': 0,
                    'win_rate': 0,
                    'total_cost': 0
                }
            
            pattern_stats[pattern]['total'] += 1
            pattern_stats[pattern]['total_pnl'] += trade.pnl
            pattern_stats[pattern]['total_cost'] += trade.total_cost
            
            if trade.pnl > 0:
                pattern_stats[pattern]['wins'] += 1
            else:
                pattern_stats[pattern]['losses'] += 1
        
        for pattern in pattern_stats:
            stats = pattern_stats[pattern]
            stats['avg_pnl'] = stats['total_pnl'] / stats['total']
            stats['win_rate'] = stats['wins'] / stats['total']
        
        df = pd.DataFrame.from_dict(pattern_stats, orient='index')
        df = df.sort_values('total_pnl', ascending=False)
        
        return df
