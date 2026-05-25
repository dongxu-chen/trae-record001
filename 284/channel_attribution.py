import pandas as pd
import numpy as np
from itertools import combinations
from typing import Dict, List, Tuple
import matplotlib.pyplot as plt
import seaborn as sns

class ChannelAttribution:
    def __init__(self, random_state: int = 42):
        self.random_state = random_state
        np.random.seed(random_state)
        self.channel_effects = {}
        self.shapley_values = {}
        self.interaction_effects = {}
    
    def generate_multi_channel_data(
        self,
        n_products: int = 200,
        n_periods: int = 12
    ) -> pd.DataFrame:
        channels = ['线上商城', '社交媒体', '线下门店', '邮件营销', '直播带货']
        categories = ['电子产品', '服装', '食品', '家居', '美妆']
        
        data = []
        
        for product_id in range(n_products):
            category = np.random.choice(categories)
            base_sales = np.random.uniform(1000, 10000)
            trend = np.random.uniform(0.002, 0.015)
            
            channel_base_effects = {
                '线上商城': np.random.uniform(0.1, 0.2),
                '社交媒体': np.random.uniform(0.08, 0.18),
                '线下门店': np.random.uniform(0.05, 0.15),
                '邮件营销': np.random.uniform(0.03, 0.1),
                '直播带货': np.random.uniform(0.15, 0.3)
            }
            
            category_multiplier = {
                '电子产品': 1.3, '服装': 1.0, '食品': 0.7,
                '家居': 0.9, '美妆': 1.1
            }[category]
            
            promotion_history = []
            promotion_count = 0
            
            for period in range(n_periods):
                active_channels = []
                for ch in channels:
                    if np.random.binomial(1, 0.3):
                        active_channels.append(ch)
                
                discount = np.random.uniform(0.05, 0.35) if len(active_channels) > 0 else 0
                
                time_factor = 1 + trend * period
                seasonality = 1 + 0.08 * np.sin(2 * np.pi * period / 4)
                
                channel_contribution = 0
                for ch in active_channels:
                    fatigue_factor = 1 / (1 + 0.1 * promotion_count)
                    channel_contribution += channel_base_effects[ch] * fatigue_factor
                
                synergy = 0
                if len(active_channels) >= 2:
                    for i in range(len(active_channels)):
                        for j in range(i+1, len(active_channels)):
                            synergy += np.random.uniform(0.01, 0.03)
                
                total_effect = 1 + channel_contribution + synergy
                
                sales = (
                    base_sales * 
                    time_factor * 
                    seasonality * 
                    category_multiplier * 
                    total_effect *
                    np.random.normal(1, 0.07)
                )
                
                if len(active_channels) > 0:
                    promotion_count += 1
                    promotion_history.append(period)
                
                data.append({
                    'product_id': product_id,
                    'period': period,
                    'category': category,
                    'base_sales': base_sales,
                    'active_channels': ','.join(active_channels) if active_channels else '无',
                    'n_channels': len(active_channels),
                    'discount': discount,
                    'promotion_count': promotion_count,
                    'sales': max(0, sales)
                })
        
        df = pd.DataFrame(data)
        
        for ch in channels:
            df[f'channel_{ch}'] = df['active_channels'].apply(
                lambda x: 1 if ch in x else 0
            )
        
        return df
    
    def calculate_shapley_values(
        self,
        df: pd.DataFrame,
        channels: List[str] = None
    ) -> Dict:
        if channels is None:
            channels = ['线上商城', '社交媒体', '线下门店', '邮件营销', '直播带货']
        
        channel_cols = [f'channel_{ch}' for ch in channels]
        
        n = len(channels)
        shapley_values = {ch: 0.0 for ch in channels}
        
        for ch in channels:
            marginal_contributions = []
            
            other_channels = [c for c in channels if c != ch]
            
            for subset_size in range(n):
                for subset in combinations(other_channels, subset_size):
                    subset_with = list(subset) + [ch]
                    subset_without = list(subset)
                    
                    def calculate_subset_effect(subset_list):
                        if not subset_list:
                            return df[df['n_channels'] == 0]['sales'].mean()
                        
                        mask = pd.Series(True, index=df.index)
                        for s in subset_list:
                            mask = mask & (df[f'channel_{s}'] == 1)
                        
                        for c in channels:
                            if c not in subset_list:
                                mask = mask & (df[f'channel_{c}'] == 0)
                        
                        subset_data = df[mask]
                        if len(subset_data) > 0:
                            return subset_data['sales'].mean()
                        return df['sales'].mean()
                    
                    effect_with = calculate_subset_effect(subset_with)
                    effect_without = calculate_subset_effect(subset_without)
                    
                    marginal = effect_with - effect_without
                    weight = 1 / (n * len(list(combinations(other_channels, subset_size))))
                    
                    marginal_contributions.append(marginal * weight)
            
            shapley_values[ch] = sum(marginal_contributions)
        
        total_value = sum(shapley_values.values())
        shapley_pct = {ch: (val / total_value * 100 if total_value > 0 else 0) 
                       for ch, val in shapley_values.items()}
        
        self.shapley_values = shapley_values
        self.shapley_pct = shapley_pct
        
        return {
            'shapley_values': shapley_values,
            'shapley_percentage': shapley_pct,
            'total_contribution': total_value
        }
    
    def calculate_roi(
        self,
        df: pd.DataFrame,
        channel_costs: Dict[str, float] = None
    ) -> Dict:
        if channel_costs is None:
            channel_costs = {
                '线上商城': 5000,
                '社交媒体': 3000, 
                '线下门店': 8000,
                '邮件营销': 1000,
                '直播带货': 6000
            }
        
        if not self.shapley_values:
            self.calculate_shapley_values(df)
        
        roi_results = {}
        for ch, value in self.shapley_values.items():
            cost = channel_costs.get(ch, 1000)
            roi = (value / cost) * 100 if cost > 0 else 0
            roi_results[ch] = {
                'contribution': value,
                'cost': cost,
                'roi': roi,
                'roi_multiple': value / cost if cost > 0 else 0
            }
        
        self.roi_results = roi_results
        return roi_results
    
    def analyze_channel_interactions(
        self,
        df: pd.DataFrame,
        channels: List[str] = None
    ) -> Dict:
        if channels is None:
            channels = ['线上商城', '社交媒体', '线下门店', '邮件营销', '直播带货']
        
        interactions = {}
        
        for ch1, ch2 in combinations(channels, 2):
            both = df[
                (df[f'channel_{ch1}'] == 1) & 
                (df[f'channel_{ch2}'] == 1)
            ]['sales'].mean()
            
            only_ch1 = df[
                (df[f'channel_{ch1}'] == 1) & 
                (df[f'channel_{ch2}'] == 0)
            ]['sales'].mean()
            
            only_ch2 = df[
                (df[f'channel_{ch1}'] == 0) & 
                (df[f'channel_{ch2}'] == 1)
            ]['sales'].mean()
            
            neither = df[
                (df[f'channel_{ch1}'] == 0) & 
                (df[f'channel_{ch2}'] == 0)
            ]['sales'].mean()
            
            synergy = both - (only_ch1 + only_ch2 - neither)
            synergy_pct = (synergy / neither) * 100 if neither > 0 else 0
            
            interactions[f'{ch1}×{ch2}'] = {
                'synergy': synergy,
                'synergy_pct': synergy_pct,
                'both_mean': both,
                'only_ch1_mean': only_ch1,
                'only_ch2_mean': only_ch2
            }
        
        self.interaction_effects = interactions
        return interactions
    
    def plot_shapley_values(
        self,
        figsize: Tuple[int, int] = (10, 6)
    ) -> plt.Figure:
        if not self.shapley_values:
            raise ValueError("请先运行calculate_shapley_values方法")
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=figsize)
        
        sorted_items = sorted(self.shapley_pct.items(), key=lambda x: x[1], reverse=True)
        channels = [item[0] for item in sorted_items]
        values = [item[1] for item in sorted_items]
        
        colors = plt.cm.viridis(np.linspace(0.3, 0.9, len(channels)))
        
        ax1.barh(channels, values, color=colors, alpha=0.8)
        ax1.set_xlabel('贡献度 (%)')
        ax1.set_title('各渠道Shapley值贡献度')
        ax1.grid(True, alpha=0.3, axis='x')
        
        for i, v in enumerate(values):
            ax1.text(v + 0.5, i, f'{v:.1f}%', va='center')
        
        if hasattr(self, 'roi_results'):
            roi_data = sorted(
                [(ch, data['roi']) for ch, data in self.roi_results.items()],
                key=lambda x: x[1],
                reverse=True
            )
            roi_channels = [x[0] for x in roi_data]
            roi_values = [x[1] for x in roi_data]
            
            roi_colors = ['#2ecc71' if r > 100 else '#f39c12' if r > 50 else '#e74c3c' 
                         for _, r in roi_data]
            
            ax2.barh(roi_channels, roi_values, color=roi_colors, alpha=0.8)
            ax2.set_xlabel('ROI (%)')
            ax2.set_title('各渠道投资回报率')
            ax2.grid(True, alpha=0.3, axis='x')
            
            for i, v in enumerate(roi_values):
                ax2.text(v + 1, i, f'{v:.0f}%', va='center')
        else:
            absolute_values = sorted(self.shapley_values.items(), key=lambda x: x[1], reverse=True)
            abs_values = [x[1] for x in absolute_values]
            
            ax2.barh(channels, abs_values, color=colors, alpha=0.8)
            ax2.set_xlabel('贡献额 (销售额)')
            ax2.set_title('各渠道绝对贡献额')
            ax2.grid(True, alpha=0.3, axis='x')
            
            for i, v in enumerate(abs_values):
                ax2.text(v + 10, i, f'¥{v:,.0f}', va='center')
        
        plt.tight_layout()
        return fig
    
    def plot_channel_interactions(
        self,
        figsize: Tuple[int, int] = (10, 8)
    ) -> plt.Figure:
        if not self.interaction_effects:
            raise ValueError("请先运行analyze_channel_interactions方法")
        
        channels = ['线上商城', '社交媒体', '线下门店', '邮件营销', '直播带货']
        n = len(channels)
        matrix = np.zeros((n, n))
        
        for i, ch1 in enumerate(channels):
            for j, ch2 in enumerate(channels):
                if i != j:
                    key = f'{ch1}×{ch2}' if f'{ch1}×{ch2}' in self.interaction_effects else f'{ch2}×{ch1}'
                    if key in self.interaction_effects:
                        matrix[i, j] = self.interaction_effects[key]['synergy_pct']
        
        fig, ax = plt.subplots(figsize=figsize)
        
        sns.heatmap(
            matrix,
            annot=True,
            fmt='.1f',
            cmap='RdYlGn',
            center=0,
            xticklabels=channels,
            yticklabels=channels,
            ax=ax,
            cbar_kws={'label': '协同效应 (%)'}
        )
        
        ax.set_title('渠道间协同效应热力图', fontsize=14, fontweight='bold')
        
        plt.tight_layout()
        return fig
    
    def get_summary(self) -> str:
        summary = """
========================================
多渠道归因分析结果摘要
========================================
"""
        if self.shapley_values:
            summary += "\n【Shapley值贡献度】\n"
            sorted_items = sorted(self.shapley_pct.items(), key=lambda x: x[1], reverse=True)
            for ch, pct in sorted_items:
                summary += f"  - {ch}: {pct:.1f}% (¥{self.shapley_values[ch]:,.0f})\n"
        
        if hasattr(self, 'roi_results'):
            summary += "\n【投资回报率 (ROI)】\n"
            roi_sorted = sorted(
                self.roi_results.items(), 
                key=lambda x: x[1]['roi'], 
                reverse=True
            )
            for ch, data in roi_sorted:
                summary += f"  - {ch}: ROI {data['roi']:.0f}% (投入¥{data['cost']:,})\n"
        
        return summary
