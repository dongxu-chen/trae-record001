import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats

class BudgetSimulator:
    def __init__(self, random_state: int = 42):
        self.random_state = random_state
        np.random.seed(random_state)
        self.simulation_results = None
        self.optimal_allocation = None
        
        self.channel_base_costs = {
            '线上商城': 5000,
            '社交媒体': 3000,
            '线下门店': 8000,
            '邮件营销': 1000,
            '直播带货': 6000
        }
        
        self.channel_base_roi = {
            '线上商城': 2.5,
            '社交媒体': 2.0,
            '线下门店': 1.5,
            '邮件营销': 3.0,
            '直播带货': 3.5
        }
        
        self.diminishing_returns = {
            '线上商城': 0.15,
            '社交媒体': 0.2,
            '线下门店': 0.1,
            '邮件营销': 0.25,
            '直播带货': 0.12
        }
    
    def run_budget_simulation(
        self,
        total_budget: float,
        discount_range: Tuple[float, float] = (0.1, 0.4),
        duration_range: Tuple[int, int] = (1, 7),
        channels: List[str] = None,
        n_simulations: int = 1000,
        include_fatigue: bool = True
    ) -> Dict:
        if channels is None:
            channels = ['线上商城', '社交媒体', '线下门店', '邮件营销', '直播带货']
        
        results = []
        
        for _ in range(n_simulations):
            budget_allocations = np.random.dirichlet(np.ones(len(channels))) * total_budget
            discount = np.random.uniform(*discount_range)
            duration = np.random.randint(*duration_range)
            
            total_revenue = 0
            channel_contributions = {}
            
            for i, ch in enumerate(channels):
                budget = budget_allocations[i]
                base_cost = self.channel_base_costs[ch]
                base_roi = self.channel_base_roi[ch]
                dim_return = self.diminishing_returns[ch]
                
                budget_multiplier = budget / base_cost
                
                effective_roi = base_roi * (1 - dim_return * np.log(budget_multiplier + 1))
                effective_roi = max(0.5, effective_roi)
                
                if include_fatigue:
                    fatigue_factor = 1 / (1 + 0.05 * budget / 10000)
                    effective_roi *= fatigue_factor
                
                revenue = budget * effective_roi
                total_revenue += revenue
                channel_contributions[ch] = revenue
            
            discount_effect = discount * 100 * 0.8
            duration_effect = duration * 1.2
            
            total_revenue = total_revenue * (1 + (discount_effect + duration_effect) / 100)
            
            profit = total_revenue - total_budget
            roi = (profit / total_budget) * 100 if total_budget > 0 else 0
            
            results.append({
                'total_budget': total_budget,
                'discount': discount,
                'duration': duration,
                'total_revenue': total_revenue,
                'profit': profit,
                'roi': roi,
                'channel_allocations': dict(zip(channels, budget_allocations)),
                'channel_contributions': channel_contributions
            })
        
        self.simulation_results = pd.DataFrame(results)
        return self.analyze_simulation_results()
    
    def analyze_simulation_results(self) -> Dict:
        if self.simulation_results is None:
            raise ValueError("请先运行run_budget_simulation方法")
        
        df = self.simulation_results
        
        top_20_pct = df.nlargest(int(len(df) * 0.2), 'profit')
        
        avg_channel_alloc = {}
        for ch in top_20_pct['channel_allocations'].iloc[0].keys():
            avg_channel_alloc[ch] = top_20_pct['channel_allocations'].apply(
                lambda x: x[ch]
            ).mean()
        
        optimal_allocation = {}
        for ch, alloc in avg_channel_alloc.items():
            optimal_allocation[ch] = {
                'recommended_budget': alloc,
                'budget_pct': (alloc / df['total_budget'].iloc[0]) * 100,
                'expected_roi': self.channel_base_roi[ch]
            }
        
        self.optimal_allocation = optimal_allocation
        
        return {
            'summary': {
                'n_simulations': len(df),
                'avg_revenue': df['total_revenue'].mean(),
                'avg_profit': df['profit'].mean(),
                'avg_roi': df['roi'].mean(),
                'max_profit': df['profit'].max(),
                'max_roi': df['roi'].max(),
                'min_profit': df['profit'].min(),
                'revenue_std': df['total_revenue'].std(),
                'profit_std': df['profit'].std()
            },
            'optimal_allocation': optimal_allocation,
            'top_scenarios': top_20_pct,
            'all_results': df
        }
    
    def optimize_budget_allocation(
        self,
        total_budget: float,
        target_roi: float = 100.0,
        channels: List[str] = None
    ) -> Dict:
        if channels is None:
            channels = list(self.channel_base_costs.keys())
        
        from scipy.optimize import minimize
        
        def objective(x):
            total_revenue = 0
            for i, ch in enumerate(channels):
                budget = x[i] * total_budget
                base_cost = self.channel_base_costs[ch]
                base_roi = self.channel_base_roi[ch]
                dim_return = self.diminishing_returns[ch]
                
                budget_multiplier = max(0.1, budget / base_cost)
                effective_roi = base_roi * (1 - dim_return * np.log(budget_multiplier + 1))
                effective_roi = max(0.5, effective_roi)
                
                total_revenue += budget * effective_roi
            
            return -total_revenue
        
        constraints = [
            {'type': 'eq', 'fun': lambda x: np.sum(x) - 1}
        ]
        bounds = [(0.05, 0.5) for _ in channels]
        x0 = np.array([1/len(channels)] * len(channels))
        
        result = minimize(
            objective,
            x0,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints
        )
        
        optimal_weights = result.x
        
        allocation = {}
        total_revenue = 0
        
        for i, ch in enumerate(channels):
            budget = optimal_weights[i] * total_budget
            base_cost = self.channel_base_costs[ch]
            base_roi = self.channel_base_roi[ch]
            dim_return = self.diminishing_returns[ch]
            
            budget_multiplier = max(0.1, budget / base_cost)
            effective_roi = base_roi * (1 - dim_return * np.log(budget_multiplier + 1))
            effective_roi = max(0.5, effective_roi)
            
            revenue = budget * effective_roi
            total_revenue += revenue
            
            allocation[ch] = {
                'budget': budget,
                'budget_pct': optimal_weights[i] * 100,
                'expected_revenue': revenue,
                'expected_roi': (revenue - budget) / budget * 100 if budget > 0 else 0
            }
        
        total_profit = total_revenue - total_budget
        total_roi = (total_profit / total_budget) * 100 if total_budget > 0 else 0
        
        return {
            'total_budget': total_budget,
            'expected_revenue': total_revenue,
            'expected_profit': total_profit,
            'expected_roi': total_roi,
            'meets_target_roi': total_roi >= target_roi,
            'channel_allocation': allocation,
            'optimization_success': result.success
        }
    
    def what_if_analysis(
        self,
        base_scenario: Dict,
        variations: Dict[str, List]
    ) -> pd.DataFrame:
        results = []
        
        base_keys = list(base_scenario.keys())
        
        def generate_scenarios(current, remaining_variations):
            if not remaining_variations:
                scenario = base_scenario.copy()
                scenario.update(current)
                
                total_budget = scenario.get('total_budget', 50000)
                channels = scenario.get('channels', list(self.channel_base_costs.keys()))
                
                total_revenue = 0
                for ch in channels:
                    ch_budget = total_budget * scenario.get(f'{ch}_pct', 1/len(channels))
                    base_cost = self.channel_base_costs[ch]
                    base_roi = self.channel_base_roi[ch]
                    dim_return = self.diminishing_returns[ch]
                    
                    budget_multiplier = max(0.1, ch_budget / base_cost)
                    effective_roi = base_roi * (1 - dim_return * np.log(budget_multiplier + 1))
                    effective_roi = max(0.5, effective_roi)
                    
                    total_revenue += ch_budget * effective_roi
                
                discount = scenario.get('discount', 0.2)
                duration = scenario.get('duration', 3)
                discount_effect = discount * 100 * 0.8
                duration_effect = duration * 1.2
                total_revenue = total_revenue * (1 + (discount_effect + duration_effect) / 100)
                
                profit = total_revenue - total_budget
                roi = (profit / total_budget) * 100 if total_budget > 0 else 0
                
                result = scenario.copy()
                result['expected_revenue'] = total_revenue
                result['expected_profit'] = profit
                result['expected_roi'] = roi
                results.append(result)
                return
            
            key = remaining_variations[0]
            values = remaining_variations[1]
            for val in values:
                current[key] = val
                generate_scenarios(current, remaining_variations[2:])
                del current[key]
        
        var_list = list(variations.items())
        generate_scenarios({}, var_list)
        
        return pd.DataFrame(results)
    
    def plot_simulation_results(
        self,
        figsize: Tuple[int, int] = (15, 10)
    ) -> plt.Figure:
        if self.simulation_results is None:
            raise ValueError("请先运行run_budget_simulation方法")
        
        df = self.simulation_results
        
        fig = plt.figure(figsize=figsize)
        gs = fig.add_gridspec(2, 2)
        
        ax1 = fig.add_subplot(gs[0, 0])
        ax1.hist(df['profit'], bins=30, alpha=0.7, color='#2ecc71', edgecolor='white')
        ax1.axvline(df['profit'].mean(), color='red', linestyle='--', linewidth=2, 
                   label=f'平均利润: ¥{df["profit"].mean():,.0f}')
        ax1.set_xlabel('利润 (¥)')
        ax1.set_ylabel('模拟次数')
        ax1.set_title('利润分布')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        ax2 = fig.add_subplot(gs[0, 1])
        ax2.scatter(df['total_budget'], df['roi'], alpha=0.5, s=50, c=df['profit'], cmap='viridis')
        ax2.set_xlabel('总预算 (¥)')
        ax2.set_ylabel('ROI (%)')
        ax2.set_title('预算 vs ROI')
        ax2.grid(True, alpha=0.3)
        cbar = plt.colorbar(ax2.collections[0], ax=ax2)
        cbar.set_label('利润 (¥)')
        
        ax3 = fig.add_subplot(gs[1, :])
        
        if self.optimal_allocation:
            channels = list(self.optimal_allocation.keys())
            budgets = [v['recommended_budget'] for v in self.optimal_allocation.values()]
            pcts = [v['budget_pct'] for v in self.optimal_allocation.values()]
            
            bars = ax3.bar(channels, budgets, alpha=0.7, color='skyblue')
            ax3.set_ylabel('推荐预算 (¥)')
            ax3.set_title('最优渠道预算分配')
            ax3.grid(True, alpha=0.3, axis='y')
            
            for bar, pct in zip(bars, pcts):
                height = bar.get_height()
                ax3.text(bar.get_x() + bar.get_width()/2., height + max(budgets)*0.01,
                        f'{pct:.1f}%', ha='center', va='bottom', fontweight='bold')
        
        plt.tight_layout()
        return fig
    
    def plot_budget_vs_roi_curve(
        self,
        budget_range: Tuple[float, float] = (10000, 200000),
        n_points: int = 20,
        figsize: Tuple[int, int] = (10, 6)
    ) -> plt.Figure:
        budgets = np.linspace(*budget_range, n_points)
        rois = []
        profits = []
        
        for budget in budgets:
            result = self.optimize_budget_allocation(budget)
            rois.append(result['expected_roi'])
            profits.append(result['expected_profit'])
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=figsize)
        
        ax1.plot(budgets, rois, 'o-', linewidth=2, color='#3498db', markersize=6)
        ax1.axhline(y=100, color='red', linestyle='--', alpha=0.5, label='ROI=100% (盈亏平衡)')
        ax1.set_xlabel('总预算 (¥)')
        ax1.set_ylabel('预期 ROI (%)')
        ax1.set_title('预算 vs ROI 曲线')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        ax2.plot(budgets, profits, 'o-', linewidth=2, color='#2ecc71', markersize=6)
        ax2.axhline(y=0, color='red', linestyle='--', alpha=0.5, label='盈亏平衡')
        ax2.set_xlabel('总预算 (¥)')
        ax2.set_ylabel('预期利润 (¥)')
        ax2.set_title('预算 vs 利润曲线')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        max_roi_idx = np.argmax(rois)
        ax1.annotate(
            f'最优预算: ¥{budgets[max_roi_idx]:,.0f}\nROI: {rois[max_roi_idx]:.1f}%',
            xy=(budgets[max_roi_idx], rois[max_roi_idx]),
            xytext=(budgets[max_roi_idx]*0.7, rois[max_roi_idx]*0.8),
            arrowprops=dict(arrowstyle='->')
        )
        
        plt.tight_layout()
        return fig
    
    def generate_budget_recommendations(
        self,
        total_budget: float
    ) -> List[str]:
        recommendations = []
        
        optimal = self.optimize_budget_allocation(total_budget)
        
        recommendations.append(f"📊 总预算: ¥{total_budget:,.0f}")
        recommendations.append(f"💰 预期收入: ¥{optimal['expected_revenue']:,.0f}")
        recommendations.append(f"📈 预期利润: ¥{optimal['expected_profit']:,.0f}")
        recommendations.append(f"📊 预期 ROI: {optimal['expected_roi']:.1f}%")
        recommendations.append("")
        
        sorted_channels = sorted(
            optimal['channel_allocation'].items(),
            key=lambda x: x[1]['budget'],
            reverse=True
        )
        
        recommendations.append("💸 推荐渠道预算分配:")
        for ch, data in sorted_channels:
            recommendations.append(
                f"  - {ch}: ¥{data['budget']:,.0f} ({data['budget_pct']:.1f}%) "
                f"- 预期 ROI: {data['expected_roi']:.1f}%"
            )
        
        recommendations.append("")
        
        if optimal['expected_roi'] < 50:
            recommendations.append("⚠️ 警告：预期ROI较低，建议减少预算或优化渠道组合")
        elif optimal['expected_roi'] > 200:
            recommendations.append("✅ 优秀：预期ROI很高，可考虑增加预算")
        
        high_roi_channels = [
            ch for ch, data in sorted_channels 
            if data['expected_roi'] > 150
        ]
        if high_roi_channels:
            recommendations.append(
                f"💡 建议向高ROI渠道倾斜更多预算: {', '.join(high_roi_channels)}"
            )
        
        return recommendations
