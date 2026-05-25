import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler

class PromotionFatigueDetector:
    def __init__(self, random_state: int = 42):
        self.random_state = random_state
        np.random.seed(random_state)
        self.fatigue_scores = {}
        self.sensitivity_decay = {}
        self.optimal_frequency = {}
    
    def generate_fatigue_data(
        self,
        n_products: int = 150,
        n_periods: int = 24
    ) -> pd.DataFrame:
        categories = ['电子产品', '服装', '食品', '家居', '美妆']
        channels = ['线上商城', '社交媒体', '线下门店', '邮件营销', '直播带货']
        
        data = []
        
        for product_id in range(n_products):
            category = np.random.choice(categories)
            channel = np.random.choice(channels)
            base_sales = np.random.uniform(1000, 10000)
            
            base_sensitivity = {
                '电子产品': 0.3, '服装': 0.25, '食品': 0.15,
                '家居': 0.2, '美妆': 0.28
            }[category]
            
            fatigue_resistance = np.random.uniform(0.5, 2.0)
            optimal_gap = np.random.randint(2, 6)
            
            promotion_history = []
            cumulative_promotions = 0
            
            for period in range(n_periods):
                time_factor = 1 + 0.005 * period
                seasonality = 1 + 0.1 * np.sin(2 * np.pi * period / 4)
                
                run_promotion = np.random.binomial(1, 0.35)
                
                if run_promotion:
                    discount = np.random.uniform(0.1, 0.4)
                    cumulative_promotions += 1
                    promotion_history.append(period)
                    
                    time_since_last = (
                        period - promotion_history[-2] 
                        if len(promotion_history) > 1 else 999
                    )
                    
                    fatigue_factor = 1 / (1 + 0.15 * cumulative_promotions / fatigue_resistance)
                    
                    gap_effect = 1 - np.exp(-time_since_last / optimal_gap) if time_since_last < 10 else 1
                    
                    effective_sensitivity = base_sensitivity * fatigue_factor * gap_effect
                    
                    promotion_lift = 1 + discount * effective_sensitivity * 2
                    
                    sales = (
                        base_sales * 
                        time_factor * 
                        seasonality * 
                        promotion_lift *
                        np.random.normal(1, 0.08)
                    )
                else:
                    discount = 0
                    time_since_last = 999
                    fatigue_factor = 1
                    effective_sensitivity = base_sensitivity
                    
                    sales = (
                        base_sales * 
                        time_factor * 
                        seasonality *
                        np.random.normal(1, 0.06)
                    )
                
                data.append({
                    'product_id': product_id,
                    'period': period,
                    'category': category,
                    'channel': channel,
                    'base_sales': base_sales,
                    'discount': discount,
                    'is_promotion': run_promotion,
                    'cumulative_promotions': cumulative_promotions,
                    'time_since_last_promotion': time_since_last,
                    'fatigue_factor': fatigue_factor,
                    'effective_sensitivity': effective_sensitivity,
                    'optimal_gap': optimal_gap,
                    'fatigue_resistance': fatigue_resistance,
                    'sales': max(0, sales)
                })
        
        return pd.DataFrame(data)
    
    def calculate_fatigue_score(
        self,
        df: pd.DataFrame
    ) -> Dict:
        fatigue_results = {}
        
        for product_id in df['product_id'].unique():
            product_data = df[df['product_id'] == product_id].sort_values('period')
            
            promotion_data = product_data[product_data['is_promotion'] == True].copy()
            
            if len(promotion_data) < 3:
                continue
            
            promotion_data['promotion_number'] = range(1, len(promotion_data) + 1)
            
            X = promotion_data[['promotion_number', 'discount']].values
            y = promotion_data['sales'].values
            
            if len(X) > 3:
                model = LinearRegression()
                model.fit(X, y)
                
                trend_coef = model.coef_[0]
                
                base_sales = product_data[~product_data['is_promotion']]['sales'].mean()
                avg_lift = (promotion_data['sales'].mean() - base_sales) / base_sales * 100 if base_sales > 0 else 0
                
                first_half = promotion_data.head(len(promotion_data) // 2)['sales'].mean()
                second_half = promotion_data.tail(len(promotion_data) // 2)['sales'].mean()
                decay_rate = (second_half - first_half) / first_half * 100 if first_half > 0 else 0
                
                fatigue_score = max(0, min(100, -decay_rate * 2))
                
                fatigue_results[product_id] = {
                    'fatigue_score': fatigue_score,
                    'trend_coefficient': trend_coef,
                    'decay_rate': decay_rate,
                    'avg_lift_pct': avg_lift,
                    'promotion_count': len(promotion_data),
                    'fatigue_level': self._get_fatigue_level(fatigue_score)
                }
        
        self.fatigue_scores = fatigue_results
        return fatigue_results
    
    def _get_fatigue_level(self, score: float) -> str:
        if score < 20:
            return '低疲劳'
        elif score < 50:
            return '中等疲劳'
        elif score < 75:
            return '较高疲劳'
        else:
            return '高疲劳'
    
    def analyze_sensitivity_decay(
        self,
        df: pd.DataFrame
    ) -> Dict:
        category_decay = {}
        channel_decay = {}
        
        for category in df['category'].unique():
            cat_data = df[
                (df['category'] == category) & 
                (df['is_promotion'] == True)
            ].copy()
            
            if len(cat_data) < 10:
                continue
            
            cat_data['promotion_rank'] = cat_data.groupby('product_id').cumcount() + 1
            
            decay_model = LinearRegression()
            X = cat_data[['promotion_rank', 'discount']]
            y = cat_data['sales']
            decay_model.fit(X, y)
            
            sensitivity = decay_model.coef_[0]
            
            category_decay[category] = {
                'decay_coefficient': sensitivity,
                'avg_promotions': cat_data.groupby('product_id').size().mean(),
                'avg_sales': cat_data['sales'].mean()
            }
        
        for channel in df['channel'].unique():
            ch_data = df[
                (df['channel'] == channel) & 
                (df['is_promotion'] == True)
            ].copy()
            
            if len(ch_data) < 10:
                continue
            
            ch_data['promotion_rank'] = ch_data.groupby('product_id').cumcount() + 1
            
            decay_model = LinearRegression()
            X = ch_data[['promotion_rank', 'discount']]
            y = ch_data['sales']
            decay_model.fit(X, y)
            
            sensitivity = decay_model.coef_[0]
            
            channel_decay[channel] = {
                'decay_coefficient': sensitivity,
                'avg_promotions': ch_data.groupby('product_id').size().mean(),
                'avg_sales': ch_data['sales'].mean()
            }
        
        self.sensitivity_decay = {
            'category': category_decay,
            'channel': channel_decay
        }
        
        return self.sensitivity_decay
    
    def calculate_optimal_frequency(
        self,
        df: pd.DataFrame
    ) -> Dict:
        optimal_results = {}
        
        for product_id in df['product_id'].unique():
            product_data = df[df['product_id'] == product_id].sort_values('period')
            promotion_data = product_data[product_data['is_promotion'] == True]
            
            if len(promotion_data) < 4:
                continue
            
            gaps = []
            lifts = []
            
            for i in range(1, len(promotion_data)):
                gap = promotion_data['period'].iloc[i] - promotion_data['period'].iloc[i-1]
                
                pre_sales = product_data[
                    product_data['period'] < promotion_data['period'].iloc[i]
                ]['sales'].tail(3).mean()
                
                promotion_sales = promotion_data['sales'].iloc[i]
                
                lift = (promotion_sales - pre_sales) / pre_sales * 100 if pre_sales > 0 else 0
                
                gaps.append(gap)
                lifts.append(lift)
            
            if len(gaps) < 3:
                continue
            
            gaps = np.array(gaps)
            lifts = np.array(lifts)
            
            valid_mask = (gaps <= 12) & (lifts > -50)
            gaps = gaps[valid_mask]
            lifts = lifts[valid_mask]
            
            if len(gaps) < 3:
                continue
            
            try:
                from scipy.optimize import curve_fit
                
                def decay_curve(x, a, b, c):
                    return a * (1 - np.exp(-b * x)) + c
                
                popt, _ = curve_fit(
                    decay_curve, 
                    gaps, 
                    lifts, 
                    p0=[20, 0.3, 5],
                    maxfev=1000
                )
                
                x_range = np.arange(1, 13)
                y_pred = decay_curve(x_range, *popt)
                
                target_efficiency = 0.8
                max_lift = max(y_pred)
                target_lift = max_lift * target_efficiency
                
                optimal_gap = x_range[np.argmax(y_pred >= target_lift)] if any(y_pred >= target_lift) else 4
                
                optimal_results[product_id] = {
                    'optimal_gap': int(optimal_gap),
                    'max_expected_lift': max_lift,
                    'optimal_frequency': f"每{optimal_gap}周期一次",
                    'recommended_annual': int(12 / optimal_gap),
                    'curve_params': popt.tolist()
                }
            except:
                optimal_results[product_id] = {
                    'optimal_gap': 4,
                    'max_expected_lift': np.mean(lifts),
                    'optimal_frequency': "每4周期一次",
                    'recommended_annual': 3,
                    'curve_params': None
                }
        
        self.optimal_frequency = optimal_results
        return optimal_results
    
    def generate_recommendations(
        self,
        df: pd.DataFrame
    ) -> List[str]:
        recommendations = []
        
        if not self.fatigue_scores:
            self.calculate_fatigue_score(df)
        
        high_fatigue_count = sum(
            1 for v in self.fatigue_scores.values() 
            if v['fatigue_level'] in ['较高疲劳', '高疲劳']
        )
        total = len(self.fatigue_scores)
        
        if total > 0 and high_fatigue_count / total > 0.3:
            recommendations.append(
                f"⚠️ 警告：{high_fatigue_count}/{total} ({high_fatigue_count/total*100:.0f}%) 的商品处于较高疲劳状态"
            )
            recommendations.append(
                "💡 建议：立即减少促销频率，让用户恢复敏感度"
            )
        
        if self.sensitivity_decay:
            for category, data in self.sensitivity_decay.get('category', {}).items():
                if data['decay_coefficient'] < -50:
                    recommendations.append(
                        f"📉 {category}类敏感度下降较快，建议探索新的促销形式"
                    )
            
            for channel, data in self.sensitivity_decay.get('channel', {}).items():
                if data['decay_coefficient'] < -50:
                    recommendations.append(
                        f"📉 {channel}渠道敏感度下降较快，建议轮换渠道策略"
                    )
        
        if self.optimal_frequency:
            avg_optimal_gap = np.mean([
                v['optimal_gap'] for v in self.optimal_frequency.values()
            ])
            recommendations.append(
                f"📊 整体最优促销间隔：约{avg_optimal_gap:.1f}个周期"
            )
            recommendations.append(
                f"📅 建议年度促销次数：约{int(12/avg_optimal_gap)}次"
            )
        
        if not recommendations:
            recommendations.append("✅ 当前促销策略健康，用户敏感度良好")
        
        return recommendations
    
    def plot_fatigue_distribution(
        self,
        figsize: Tuple[int, int] = (12, 5)
    ) -> plt.Figure:
        if not self.fatigue_scores:
            raise ValueError("请先运行calculate_fatigue_score方法")
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=figsize)
        
        scores = [v['fatigue_score'] for v in self.fatigue_scores.values()]
        
        ax1.hist(scores, bins=20, alpha=0.7, color='#e74c3c', edgecolor='white')
        ax1.axvline(np.mean(scores), color='blue', linestyle='--', linewidth=2, label=f'均值: {np.mean(scores):.1f}')
        ax1.axvline(50, color='orange', linestyle='--', linewidth=2, label='疲劳警戒线')
        ax1.set_xlabel('疲劳指数 (0-100)')
        ax1.set_ylabel('商品数量')
        ax1.set_title('促销疲劳指数分布')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        levels = ['低疲劳', '中等疲劳', '较高疲劳', '高疲劳']
        level_counts = [
            sum(1 for v in self.fatigue_scores.values() if v['fatigue_level'] == level)
            for level in levels
        ]
        colors = ['#2ecc71', '#f1c40f', '#e67e22', '#e74c3c']
        
        ax2.pie(level_counts, labels=levels, colors=colors, autopct='%1.1f%%', startangle=90)
        ax2.set_title('疲劳等级分布')
        
        plt.tight_layout()
        return fig
    
    def plot_sensitivity_decay(
        self,
        df: pd.DataFrame,
        product_id: int = None,
        figsize: Tuple[int, int] = (10, 6)
    ) -> plt.Figure:
        fig, ax = plt.subplots(figsize=figsize)
        
        if product_id is None:
            product_ids = list(self.fatigue_scores.keys())
            if product_ids:
                product_id = product_ids[0]
        
        product_data = df[df['product_id'] == product_id].sort_values('period')
        promotion_data = product_data[product_data['is_promotion'] == True].copy()
        
        if len(promotion_data) < 2:
            ax.text(0.5, 0.5, '该商品促销次数不足，无法分析', 
                    ha='center', va='center', transform=ax.transAxes)
            return fig
        
        promotion_data['promotion_number'] = range(1, len(promotion_data) + 1)
        
        base_sales = product_data[~product_data['is_promotion']]['sales'].mean()
        promotion_data['lift_pct'] = (
            (promotion_data['sales'] - base_sales) / base_sales * 100 
            if base_sales > 0 else 0
        )
        
        ax.scatter(
            promotion_data['promotion_number'],
            promotion_data['lift_pct'],
            s=100,
            alpha=0.7,
            c=promotion_data['discount'],
            cmap='viridis'
        )
        
        if len(promotion_data) >= 3:
            z = np.polyfit(
                promotion_data['promotion_number'], 
                promotion_data['lift_pct'], 
                1
            )
            p = np.poly1d(z)
            x_range = np.arange(1, len(promotion_data) + 1)
            ax.plot(x_range, p(x_range), "r--", alpha=0.8, label=f'趋势线 (斜率={z[0]:.1f})')
        
        cbar = plt.colorbar(ax.collections[0], ax=ax)
        cbar.set_label('折扣力度')
        
        ax.set_xlabel('第N次促销')
        ax.set_ylabel('销售提升率 (%)')
        ax.set_title(f'商品 {product_id} 促销敏感度衰减分析')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        return fig
    
    def plot_optimal_frequency(
        self,
        df: pd.DataFrame,
        figsize: Tuple[int, int] = (10, 6)
    ) -> plt.Figure:
        if not self.optimal_frequency:
            self.calculate_optimal_frequency(df)
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=figsize)
        
        optimal_gaps = [v['optimal_gap'] for v in self.optimal_frequency.values()]
        
        ax1.hist(optimal_gaps, bins=range(1, 13), alpha=0.7, color='#3498db', edgecolor='white')
        ax1.axvline(np.mean(optimal_gaps), color='red', linestyle='--', 
                    linewidth=2, label=f'平均: {np.mean(optimal_gaps):.1f}周期')
        ax1.set_xlabel('最优促销间隔 (周期)')
        ax1.set_ylabel('商品数量')
        ax1.set_title('最优促销间隔分布')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        categories = df['category'].unique()
        cat_gaps = {}
        for cat in categories:
            cat_products = df[df['category'] == cat]['product_id'].unique()
            gaps = [
                self.optimal_frequency[p]['optimal_gap'] 
                for p in cat_products 
                if p in self.optimal_frequency
            ]
            if gaps:
                cat_gaps[cat] = np.mean(gaps)
        
        if cat_gaps:
            sorted_cats = sorted(cat_gaps.items(), key=lambda x: x[1])
            cats = [x[0] for x in sorted_cats]
            gaps = [x[1] for x in sorted_cats]
            
            ax2.barh(cats, gaps, color='skyblue', alpha=0.8)
            ax2.set_xlabel('平均最优间隔 (周期)')
            ax2.set_title('各类别最优促销间隔')
            ax2.grid(True, alpha=0.3, axis='x')
        
        plt.tight_layout()
        return fig
