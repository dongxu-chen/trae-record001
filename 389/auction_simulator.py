import numpy as np
import pandas as pd
from typing import Dict, Optional, Callable, Tuple
from datetime import datetime


class AuctionSimulator:
    def __init__(self, auction_logs: Optional[pd.DataFrame] = None):
        self.auction_logs = auction_logs
        self._bid_cols: list = []
        self._ad_id_cols: list = []
        self._n_bids: int = 0

    def load_auction_logs(self, df_auctions: pd.DataFrame) -> None:
        self.auction_logs = df_auctions.copy()
        
        bid_cols = [c for c in df_auctions.columns if c.startswith('bid_') and c[4:].isdigit()]
        ad_id_cols = [c for c in df_auctions.columns if c.startswith('ad_id_') and c[6:].isdigit()]
        
        bid_nums = sorted([int(c[4:]) for c in bid_cols])
        ad_id_nums = sorted([int(c[6:]) for c in ad_id_cols])
        
        self._bid_cols = [f'bid_{n}' for n in bid_nums]
        self._ad_id_cols = [f'ad_id_{n}' for n in ad_id_nums]
        self._n_bids = min(len(bid_nums), len(ad_id_nums))
        
        self.auction_logs['_date'] = pd.to_datetime(self.auction_logs['timestamp']).dt.date

    def simulate_strategy(self, ad_id: int, bid_strategy_func: Callable) -> pd.DataFrame:
        if self.auction_logs is None:
            raise ValueError("Auction logs not loaded. Call load_auction_logs first.")
        
        ad_mask = pd.Series(False, index=self.auction_logs.index)
        for col in self._ad_id_cols:
            ad_mask = ad_mask | (self.auction_logs[col] == ad_id)
        
        ad_auctions = self.auction_logs[ad_mask].copy()
        
        if len(ad_auctions) == 0:
            return pd.DataFrame()
        
        ad_position = ad_auctions[self._ad_id_cols].apply(
            lambda row: next((i + 1 for i, col in enumerate(self._ad_id_cols) if row[col] == ad_id), None),
            axis=1
        )
        
        original_bids = ad_auctions.apply(
            lambda row: row[f'bid_{int(ad_position.loc[row.name])}'],
            axis=1
        )
        
        new_bids = bid_strategy_func(ad_auctions, original_bids, ad_id)
        
        all_bids = []
        for idx, row in ad_auctions.iterrows():
            pos = int(ad_position.loc[idx])
            bids = [row[f'bid_{i}'] for i in range(1, self._n_bids + 1)]
            bids[pos - 1] = new_bids.loc[idx]
            all_bids.append(bids)
        
        all_bids_array = np.array(all_bids)
        
        sorted_indices = np.argsort(-all_bids_array, axis=1)
        new_winning_pos = sorted_indices[:, 0]
        new_second_highest_bid = np.take_along_axis(
            all_bids_array, 
            sorted_indices[:, 1:2], 
            axis=1
        ).flatten()
        
        ad_won = (new_winning_pos + 1) == ad_position.values
        actual_paid = np.where(ad_won, new_second_highest_bid, 0)
        
        click = ad_auctions.get('click', pd.Series(0, index=ad_auctions.index))
        conversion = ad_auctions.get('conversion', pd.Series(0, index=ad_auctions.index))
        conversion_value = ad_auctions.get('conversion_value', pd.Series(0, index=ad_auctions.index))
        
        results = pd.DataFrame({
            'auction_id': ad_auctions['auction_id'],
            'impression_id': ad_auctions['impression_id'],
            'timestamp': ad_auctions['timestamp'],
            'position_id': ad_auctions['position_id'],
            'ad_id': ad_id,
            'original_bid': original_bids.values,
            'new_bid': new_bids.values,
            'won': ad_won,
            'paid_price': actual_paid,
            'click': click.values * ad_won.astype(int),
            'conversion': conversion.values * ad_won.astype(int),
            'conversion_value': conversion_value.values * ad_won.astype(int)
        }, index=ad_auctions.index)
        
        return results

    def calculate_key_metrics(self, simulation_results: pd.DataFrame) -> pd.DataFrame:
        if len(simulation_results) == 0:
            return pd.DataFrame()
        
        total_auctions = len(simulation_results)
        total_wins = simulation_results['won'].sum()
        total_spend = simulation_results['paid_price'].sum()
        total_impressions = total_wins
        total_clicks = simulation_results['click'].sum()
        total_conversions = simulation_results['conversion'].sum()
        total_conversion_value = simulation_results['conversion_value'].sum()
        
        win_rate = total_wins / total_auctions if total_auctions > 0 else 0
        eCPI = total_spend / total_impressions if total_impressions > 0 else 0
        eCPC = total_spend / total_clicks if total_clicks > 0 else 0
        eCPA = total_spend / total_conversions if total_conversions > 0 else 0
        ROI = (total_conversion_value - total_spend) / total_spend if total_spend > 0 else 0
        
        metrics = pd.DataFrame({
            'metric': [
                'win_rate', 'eCPI', 'eCPC', 'eCPA',
                'total_spend', 'total_impressions', 'total_clicks',
                'total_conversions', 'total_conversion_value', 'ROI'
            ],
            'value': [
                win_rate, eCPI, eCPC, eCPA,
                total_spend, total_impressions, total_clicks,
                total_conversions, total_conversion_value, ROI
            ]
        })
        
        return metrics

    def compare_strategies(self, ad_id: int, strategies_dict: Dict[str, Callable]) -> pd.DataFrame:
        all_metrics = []
        
        for strategy_name, strategy_func in strategies_dict.items():
            sim_results = self.simulate_strategy(ad_id, strategy_func)
            metrics = self.calculate_key_metrics(sim_results)
            metrics = metrics.set_index('metric')
            metrics.columns = [strategy_name]
            all_metrics.append(metrics)
        
        if not all_metrics:
            return pd.DataFrame()
        
        comparison = pd.concat(all_metrics, axis=1)
        return comparison.reset_index()

    def backtest_budget_pacing(
        self, 
        ad_id: int, 
        daily_budgets: Dict[str, float], 
        bid_strategy_func: Callable
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        if self.auction_logs is None:
            raise ValueError("Auction logs not loaded. Call load_auction_logs first.")
        
        sim_results = self.simulate_strategy(ad_id, bid_strategy_func)
        
        if len(sim_results) == 0:
            return pd.DataFrame(), pd.DataFrame()
        
        sim_results['_date'] = pd.to_datetime(sim_results['timestamp']).dt.date.astype(str)
        
        daily_data = []
        cumulative_spend = 0
        cumulative_budget = 0
        
        for date_str, day_budget in daily_budgets.items():
            day_results = sim_results[sim_results['_date'] == date_str].copy()
            day_results = day_results.sort_values('timestamp')
            
            day_spend = 0
            day_wins = 0
            day_clicks = 0
            day_conversions = 0
            day_conversion_value = 0
            wins_blocked = 0
            
            remaining_budget = day_budget
            
            for _, row in day_results.iterrows():
                if row['won'] and remaining_budget >= row['paid_price']:
                    day_spend += row['paid_price']
                    day_wins += 1
                    day_clicks += row['click']
                    day_conversions += row['conversion']
                    day_conversion_value += row['conversion_value']
                    remaining_budget -= row['paid_price']
                elif row['won']:
                    wins_blocked += 1
            
            total_potential_spend = day_results[day_results['won']]['paid_price'].sum()
            total_potential_wins = day_results['won'].sum()
            
            underspend = max(0, day_budget - day_spend)
            overspend = max(0, day_spend - day_budget)
            
            cumulative_spend += day_spend
            cumulative_budget += day_budget
            
            daily_data.append({
                'date': date_str,
                'daily_budget': day_budget,
                'actual_spend': day_spend,
                'underspend': underspend,
                'overspend': overspend,
                'remaining_budget': remaining_budget,
                'wins': day_wins,
                'potential_wins': total_potential_wins,
                'wins_blocked_budget': wins_blocked,
                'clicks': day_clicks,
                'conversions': day_conversions,
                'conversion_value': day_conversion_value,
                'cumulative_spend': cumulative_spend,
                'cumulative_budget': cumulative_budget,
                'pacing_rate': day_spend / day_budget if day_budget > 0 else 0
            })
        
        daily_df = pd.DataFrame(daily_data)
        
        total_budget = sum(daily_budgets.values())
        total_spend = daily_df['actual_spend'].sum()
        total_underspend = daily_df['underspend'].sum()
        total_overspend = daily_df['overspend'].sum()
        total_wins = daily_df['wins'].sum()
        total_potential_wins = daily_df['potential_wins'].sum()
        total_clicks = daily_df['clicks'].sum()
        total_conversions = daily_df['conversions'].sum()
        total_conversion_value = daily_df['conversion_value'].sum()
        
        overall_roi = (total_conversion_value - total_spend) / total_spend if total_spend > 0 else 0
        
        summary_df = pd.DataFrame({
            'metric': [
                'total_budget', 'total_spend', 'total_underspend', 'total_overspend',
                'underspend_pct', 'overspend_pct', 'total_wins', 'total_potential_wins',
                'win_block_rate', 'total_clicks', 'total_conversions', 'total_conversion_value',
                'ROI', 'avg_pacing_rate'
            ],
            'value': [
                total_budget, total_spend, total_underspend, total_overspend,
                total_underspend / total_budget if total_budget > 0 else 0,
                total_overspend / total_budget if total_budget > 0 else 0,
                total_wins, total_potential_wins,
                (total_potential_wins - total_wins) / total_potential_wins if total_potential_wins > 0 else 0,
                total_clicks, total_conversions, total_conversion_value,
                overall_roi, daily_df['pacing_rate'].mean()
            ]
        })
        
        return daily_df, summary_df
