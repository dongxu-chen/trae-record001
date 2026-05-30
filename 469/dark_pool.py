import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from scipy import stats as sp_stats


class DarkPoolSimulator:
    def __init__(self, mid_price: float, daily_volume: int = 1000000,
                 dark_pool_params: Dict = None):
        self.mid_price = mid_price
        self.daily_volume = daily_volume
        self.params = dark_pool_params or self._default_params()
    
    def _default_params(self) -> Dict:
        return {
            'dark_pool_participation_rate': 0.15,
            'dark_pool_fill_rate': 0.65,
            'dark_pool_midpoint_execution': True,
            'dark_pool_price_improvement_bps': 2.0,
            'information_leakage_factor': 0.1,
            'dark_pool_delay_seconds': 5.0,
            'adverse_selection_factor': 0.3,
            'min_fill_size': 100,
            'dark_pool_venue_count': 3
        }
    
    def simulate_dark_pool_execution(self, quantity: int, side: str,
                                      order_book_df: pd.DataFrame = None) -> Dict:
        p = self.params
        
        filled_qty = int(quantity * p['dark_pool_fill_rate'])
        unfilled_qty = quantity - filled_qty
        
        midpoint = self.mid_price
        
        if p['dark_pool_midpoint_execution']:
            dark_avg_price = midpoint
        else:
            price_improvement = p['dark_pool_price_improvement_bps'] / 10000
            if side == 'buy':
                dark_avg_price = midpoint * (1 - price_improvement)
            else:
                dark_avg_price = midpoint * (1 + price_improvement)
        
        adverse_impact = p['adverse_selection_factor'] * (quantity / self.daily_volume) * 5
        dark_avg_price_adjusted = dark_avg_price * (
            1 + adverse_impact / 10000 if side == 'buy' else 1 - adverse_impact / 10000
        )
        
        info_leakage_bps = p['information_leakage_factor'] * np.sqrt(quantity / self.daily_volume) * 100
        
        dark_slippage_bps = abs(dark_avg_price_adjusted - midpoint) / midpoint * 10000
        
        dark_total_cost = dark_avg_price_adjusted * filled_qty
        
        lit_impact_bps = 0.0
        lit_avg_price = 0.0
        lit_total_cost = 0.0
        
        if unfilled_qty > 0 and order_book_df is not None:
            from order_book import MarketImpactCalculator
            calc = MarketImpactCalculator(order_book_df)
            lit_avg_price, lit_impact_bps, _ = calc.calculate_impact(unfilled_qty, side)
            lit_total_cost = lit_avg_price * unfilled_qty
        
        combined_avg_price = (dark_total_cost + lit_total_cost) / quantity if quantity > 0 else 0
        combined_slippage_bps = abs(combined_avg_price - midpoint) / midpoint * 10000
        
        if side == 'buy':
            pure_lit_slippage = lit_impact_bps * (unfilled_qty / quantity) if quantity > 0 else 0
        else:
            pure_lit_slippage = lit_impact_bps * (unfilled_qty / quantity) if quantity > 0 else 0
        
        dark_savings_bps = pure_lit_slippage - dark_slippage_bps if pure_lit_slippage > dark_slippage_bps else 0
        
        return {
            'total_quantity': quantity,
            'dark_filled_qty': filled_qty,
            'lit_unfilled_qty': unfilled_qty,
            'dark_fill_rate': filled_qty / quantity,
            'dark_avg_price': dark_avg_price_adjusted,
            'lit_avg_price': lit_avg_price if unfilled_qty > 0 else 0,
            'combined_avg_price': combined_avg_price,
            'dark_slippage_bps': dark_slippage_bps,
            'lit_slippage_bps': lit_impact_bps,
            'combined_slippage_bps': combined_slippage_bps,
            'dark_savings_bps': dark_savings_bps,
            'info_leakage_bps': info_leakage_bps,
            'adverse_selection_bps': adverse_impact,
            'dark_total_cost': dark_total_cost,
            'lit_total_cost': lit_total_cost,
            'combined_total_cost': dark_total_cost + lit_total_cost
        }
    
    def compare_lit_vs_dark(self, quantity: int, side: str,
                             order_book_df: pd.DataFrame) -> Dict:
        from order_book import MarketImpactCalculator
        calc = MarketImpactCalculator(order_book_df)
        lit_avg, lit_slip, _ = calc.calculate_impact(quantity, side)
        
        dark_result = self.simulate_dark_pool_execution(quantity, side, order_book_df)
        
        return {
            'lit_only': {
                'avg_price': lit_avg,
                'slippage_bps': lit_slip,
                'total_cost': lit_avg * quantity
            },
            'dark_pool': dark_result,
            'savings_bps': lit_slip - dark_result['combined_slippage_bps'],
            'savings_dollar': (lit_avg - dark_result['combined_avg_price']) * quantity,
            'dark_participation': dark_result['dark_fill_rate'],
            'recommended_split': '暗池优先' if dark_result['combined_slippage_bps'] < lit_slip else '明池优先'
        }
    
    def dark_pool_impact_curve(self, max_quantity: int, side: str,
                                order_book_df: pd.DataFrame,
                                steps: int = 20) -> pd.DataFrame:
        quantities = np.linspace(100, max_quantity, steps, dtype=int)
        results = []
        
        for qty in quantities:
            comparison = self.compare_lit_vs_dark(qty, side, order_book_df)
            results.append({
                'quantity': qty,
                'lit_slippage_bps': comparison['lit_only']['slippage_bps'],
                'dark_slippage_bps': comparison['dark_pool']['combined_slippage_bps'],
                'dark_fill_rate': comparison['dark_pool']['dark_fill_rate'],
                'savings_bps': comparison['savings_bps'],
                'info_leakage_bps': comparison['dark_pool']['info_leakage_bps']
            })
        
        return pd.DataFrame(results)


class ImpactPredictionInterval:
    def __init__(self, order_book_df: pd.DataFrame):
        self.order_book = order_book_df.sort_values('level')
        self._estimate_uncertainty()
    
    def _estimate_uncertainty(self):
        self.volatility = 0.001
        self.depth_uncertainty = 0.1
        self.spread_uncertainty = 0.05
        
        ask_prices = self.order_book['ask_price'].values
        ask_quantities = self.order_book['ask_quantity'].values
        bid_prices = self.order_book['bid_price'].values
        bid_quantities = self.order_book['bid_quantity'].values
        
        if len(ask_prices) > 2:
            qty_changes = np.diff(ask_quantities)
            self.depth_uncertainty = np.std(qty_changes) / np.mean(ask_quantities) if np.mean(ask_quantities) > 0 else 0.1
        
        self.base_spread = (ask_prices[0] - bid_prices[0]) / ((ask_prices[0] + bid_prices[0]) / 2)
    
    def predict_interval(self, quantity: int, side: str,
                          confidence_levels: List[float] = None) -> Dict:
        if confidence_levels is None:
            confidence_levels = [0.50, 0.68, 0.80, 0.90, 0.95, 0.99]
        
        from order_book import MarketImpactCalculator
        calc = MarketImpactCalculator(self.order_book)
        point_estimate, _, _ = calc.calculate_impact(quantity, side)
        
        start_price = self.order_book.iloc[0]['ask_price' if side == 'buy' else 'bid_price']
        point_slippage_bps = abs(point_estimate - start_price) / start_price * 10000
        
        mid_price = (self.order_book.iloc[0]['ask_price'] + self.order_book.iloc[0]['bid_price']) / 2
        
        qty_participation = quantity / self.order_book['ask_quantity' if side == 'buy' else 'bid_quantity'].sum()
        
        base_uncertainty = point_slippage_bps * (
            self.depth_uncertainty + 
            self.volatility * np.sqrt(quantity) * 10 +
            qty_participation * 0.5
        )
        
        uncertainty = max(base_uncertainty, point_slippage_bps * 0.1)
        
        intervals = {}
        for cl in confidence_levels:
            z_score = sp_stats.norm.ppf((1 + cl) / 2)
            lower = max(0, point_slippage_bps - z_score * uncertainty)
            upper = point_slippage_bps + z_score * uncertainty
            
            intervals[f'{int(cl*100)}%'] = {
                'confidence': cl,
                'lower_bps': lower,
                'upper_bps': upper,
                'width_bps': upper - lower,
                'z_score': z_score,
                'lower_price': mid_price * (1 + lower / 10000) if side == 'buy' else mid_price * (1 - lower / 10000),
                'upper_price': mid_price * (1 + upper / 10000) if side == 'buy' else mid_price * (1 - upper / 10000)
            }
        
        return {
            'point_estimate_bps': point_slippage_bps,
            'point_estimate_price': point_estimate,
            'uncertainty_bps': uncertainty,
            'intervals': intervals
        }
    
    def get_interval_curve(self, max_quantity: int, side: str,
                           confidence_level: float = 0.90,
                           steps: int = 20) -> pd.DataFrame:
        quantities = np.linspace(100, max_quantity, steps, dtype=int)
        results = []
        
        for qty in quantities:
            pred = self.predict_interval(qty, side, [confidence_level])
            interval = pred['intervals'][f'{int(confidence_level*100)}%']
            
            results.append({
                'quantity': qty,
                'point_estimate': pred['point_estimate_bps'],
                'lower': interval['lower_bps'],
                'upper': interval['upper_bps'],
                'width': interval['width_bps']
            })
        
        return pd.DataFrame(results)
    
    def get_multi_confidence_curve(self, quantity: int, side: str) -> pd.DataFrame:
        pred = self.predict_interval(quantity, side)
        data = []
        for key, interval in pred['intervals'].items():
            data.append({
                'confidence_level': f"{int(interval['confidence']*100)}%",
                'lower_bps': interval['lower_bps'],
                'upper_bps': interval['upper_bps'],
                'width_bps': interval['width_bps'],
                'z_score': interval['z_score']
            })
        return pd.DataFrame(data)


class TradingCostAttribution:
    def __init__(self, order_book_df: pd.DataFrame, quantity: int, side: str):
        self.order_book = order_book_df.sort_values('level')
        self.quantity = quantity
        self.side = side
        
        self.best_bid = order_book_df.iloc[0]['bid_price']
        self.best_ask = order_book_df.iloc[0]['ask_price']
        self.mid_price = (self.best_bid + self.best_ask) / 2
        self.spread = self.best_ask - self.best_bid
    
    def attribute_costs(self) -> Dict:
        spread_cost_bps = (self.spread / 2) / self.mid_price * 10000
        spread_cost_dollar = (self.spread / 2) * self.quantity
        
        from order_book import MarketImpactCalculator
        calc = MarketImpactCalculator(self.order_book)
        actual_avg, actual_slip, trades = calc.calculate_impact(self.quantity, self.side)
        
        total_slippage_bps = actual_slip
        total_slippage_dollar = abs(actual_avg - self.mid_price) * self.quantity
        
        impact_cost_bps = total_slippage_bps - spread_cost_bps
        impact_cost_dollar = total_slippage_dollar - spread_cost_dollar
        
        impact_cost_bps = max(0, impact_cost_bps)
        impact_cost_dollar = max(0, impact_cost_dollar)
        
        timing_cost_bps = 0.5 * np.random.uniform(0, 1)
        timing_cost_dollar = timing_cost_bps / 10000 * self.mid_price * self.quantity
        
        opportunity_cost_bps = 0.0
        participation_rate = self.quantity / self.order_book['ask_quantity' if self.side == 'buy' else 'bid_quantity'].sum()
        if participation_rate > 0.1:
            opportunity_cost_bps = (participation_rate - 0.1) * 2
        
        opportunity_cost_dollar = opportunity_cost_bps / 10000 * self.mid_price * self.quantity
        
        commission_bps = 0.5
        commission_dollar = commission_bps / 10000 * self.mid_price * self.quantity
        
        total_cost_bps = spread_cost_bps + impact_cost_bps + timing_cost_bps + opportunity_cost_bps + commission_bps
        total_cost_dollar = spread_cost_dollar + impact_cost_dollar + timing_cost_dollar + opportunity_cost_dollar + commission_dollar
        
        market_impact_share = impact_cost_bps / total_cost_bps * 100 if total_cost_bps > 0 else 0
        spread_share = spread_cost_bps / total_cost_bps * 100 if total_cost_bps > 0 else 0
        timing_share = timing_cost_bps / total_cost_bps * 100 if total_cost_bps > 0 else 0
        opportunity_share = opportunity_cost_bps / total_cost_bps * 100 if total_cost_bps > 0 else 0
        commission_share = commission_bps / total_cost_bps * 100 if total_cost_bps > 0 else 0
        
        return {
            'total_cost_bps': total_cost_bps,
            'total_cost_dollar': total_cost_dollar,
            'components': {
                'spread': {
                    'bps': spread_cost_bps,
                    'dollar': spread_cost_dollar,
                    'share_pct': spread_share,
                    'description': '半价差成本(买卖价差的一半)'
                },
                'market_impact': {
                    'bps': impact_cost_bps,
                    'dollar': impact_cost_dollar,
                    'share_pct': market_impact_share,
                    'description': '订单消耗深度导致的价格移动'
                },
                'timing': {
                    'bps': timing_cost_bps,
                    'dollar': timing_cost_dollar,
                    'share_pct': timing_share,
                    'description': '执行期间价格不利漂移'
                },
                'opportunity': {
                    'bps': opportunity_cost_bps,
                    'dollar': opportunity_cost_dollar,
                    'share_pct': opportunity_share,
                    'description': '未成交部分的机会成本'
                },
                'commission': {
                    'bps': commission_bps,
                    'dollar': commission_dollar,
                    'share_pct': commission_share,
                    'description': '交易佣金'
                }
            },
            'impact_vs_others': {
                'market_impact_pct': market_impact_share,
                'other_costs_pct': 100 - market_impact_share,
                'impact_is_dominant': market_impact_share > 50
            }
        }
    
    def get_attribution_curve(self, max_quantity: int, steps: int = 20) -> pd.DataFrame:
        original_qty = self.quantity
        results = []
        
        for qty in np.linspace(100, max_quantity, steps, dtype=int):
            self.quantity = qty
            attr = self.attribute_costs()
            
            results.append({
                'quantity': qty,
                'total_bps': attr['total_cost_bps'],
                'spread_bps': attr['components']['spread']['bps'],
                'impact_bps': attr['components']['market_impact']['bps'],
                'timing_bps': attr['components']['timing']['bps'],
                'opportunity_bps': attr['components']['opportunity']['bps'],
                'commission_bps': attr['components']['commission']['bps']
            })
        
        self.quantity = original_qty
        return pd.DataFrame(results)
