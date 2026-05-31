import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import seaborn as sns
from collections import defaultdict

from data_generator import AIRPORTS


class DelayTrendAnalyzer:
    def __init__(self, historical_data: pd.DataFrame = None):
        self.historical_data = historical_data
        self.hot_routes = None
        self.time_distribution = None
        
    def analyze_hot_routes(self, top_n: int = 10) -> pd.DataFrame:
        if self.historical_data is None:
            self._generate_sample_historical_data()
        
        df = self.historical_data.copy()
        df['route'] = df['departure_airport'] + '-' + df['arrival_airport']
        
        route_stats = df.groupby('route').agg({
            'flight_id': 'count',
            'is_delayed': 'mean',
            'delay_minutes': ['mean', 'std', 'max'],
            'compensation': 'mean'
        }).round(2)
        
        route_stats.columns = [
            'flight_count', 'delay_rate', 'avg_delay_minutes', 
            'delay_std', 'max_delay_minutes', 'avg_compensation'
        ]
        
        route_stats = route_stats.reset_index()
        route_stats = route_stats[route_stats['flight_count'] >= 5]
        
        route_stats['delay_score'] = (
            route_stats['delay_rate'] * 0.4 +
            (route_stats['avg_delay_minutes'] / route_stats['avg_delay_minutes'].max()) * 0.4 +
            (route_stats['flight_count'] / route_stats['flight_count'].max()) * 0.2
        )
        
        route_stats = route_stats.sort_values('delay_score', ascending=False)
        
        self.hot_routes = route_stats.head(top_n)
        return self.hot_routes
    
    def analyze_time_distribution(self) -> Dict:
        if self.historical_data is None:
            self._generate_sample_historical_data()
        
        df = self.historical_data.copy()
        
        hourly_dist = df.groupby('departure_hour').agg({
            'is_delayed': ['count', 'mean'],
            'delay_minutes': 'mean'
        }).round(3)
        hourly_dist.columns = ['flight_count', 'delay_rate', 'avg_delay_minutes']
        
        weekday_dist = df.groupby('day_of_week').agg({
            'is_delayed': ['count', 'mean'],
            'delay_minutes': 'mean'
        }).round(3)
        weekday_dist.columns = ['flight_count', 'delay_rate', 'avg_delay_minutes']
        
        monthly_dist = df.groupby('month').agg({
            'is_delayed': ['count', 'mean'],
            'delay_minutes': 'mean'
        }).round(3)
        monthly_dist.columns = ['flight_count', 'delay_rate', 'avg_delay_minutes']
        
        peak_hours = hourly_dist[hourly_dist['delay_rate'] > hourly_dist['delay_rate'].mean() * 1.2]
        peak_hours = peak_hours.sort_values('delay_rate', ascending=False)
        
        self.time_distribution = {
            'hourly': hourly_dist,
            'weekday': weekday_dist,
            'monthly': monthly_dist,
            'peak_hours': peak_hours
        }
        
        return self.time_distribution
    
    def _generate_sample_historical_data(self, n_samples: int = 10000):
        np.random.seed(42)
        
        routes = []
        for dep in AIRPORTS:
            for arr in AIRPORTS:
                if dep != arr:
                    routes.append((dep, arr))
        
        data = []
        for route in routes:
            dep, arr = route
            route_delay_factor = np.random.uniform(0.1, 0.5)
            
            for hour in range(6, 24):
                hour_factor = 0.2 if 7 <= hour <= 9 else \
                             0.25 if 17 <= hour <= 20 else 0.1
                
                for day in range(7):
                    day_factor = 0.15 if day >= 5 else 0.05
                    
                    for month in [1, 4, 7, 10]:
                        month_factor = 0.2 if month in [1, 7] else 0.1
                        
                        n_flights = np.random.poisson(3)
                        for _ in range(n_flights):
                            delay_prob = min(0.8, route_delay_factor + hour_factor + day_factor + month_factor)
                            is_delayed = np.random.random() < delay_prob
                            
                            if is_delayed:
                                delay_minutes = int(np.random.exponential(45) + 15)
                            else:
                                delay_minutes = 0
                            
                            data.append({
                                'flight_id': f"FL{np.random.randint(10000, 99999)}",
                                'departure_airport': dep,
                                'arrival_airport': arr,
                                'departure_hour': hour,
                                'day_of_week': day,
                                'month': month,
                                'is_delayed': is_delayed,
                                'delay_minutes': delay_minutes,
                                'compensation': delay_minutes * 3 if delay_minutes >= 60 else 0
                            })
        
        self.historical_data = pd.DataFrame(data)
    
    def get_route_delay_forecast(self, departure_airport: str, 
                                  arrival_airport: str) -> Dict:
        if self.historical_data is None:
            self._generate_sample_historical_data()
        
        route_data = self.historical_data[
            (self.historical_data['departure_airport'] == departure_airport) &
            (self.historical_data['arrival_airport'] == arrival_airport)
        ]
        
        if len(route_data) == 0:
            return {'error': '无此航线历史数据'}
        
        hourly_pattern = route_data.groupby('departure_hour')['is_delayed'].mean()
        
        best_hours = hourly_pattern.nsmallest(5).index.tolist()
        worst_hours = hourly_pattern.nlargest(5).index.tolist()
        
        weekday_pattern = route_data.groupby('day_of_week')['is_delayed'].mean()
        
        forecast = {
            'total_flights': len(route_data),
            'overall_delay_rate': round(route_data['is_delayed'].mean() * 100, 1),
            'avg_delay_minutes': round(route_data['delay_minutes'].mean(), 1),
            'best_hours': best_hours,
            'worst_hours': worst_hours,
            'hourly_pattern': hourly_pattern.to_dict(),
            'weekday_pattern': weekday_pattern.to_dict()
        }
        
        return forecast
    
    def generate_delay_heatmap_data(self, departure_airport: str = None) -> pd.DataFrame:
        if self.historical_data is None:
            self._generate_sample_historical_data()
        
        df = self.historical_data.copy()
        if departure_airport:
            df = df[df['departure_airport'] == departure_airport]
        
        heatmap_data = df.pivot_table(
            index='departure_hour',
            columns='day_of_week',
            values='is_delayed',
            aggfunc='mean',
            fill_value=0
        )
        
        return heatmap_data
    
    def get_delay_alert_summary(self) -> Dict:
        if self.time_distribution is None:
            self.analyze_time_distribution()
        
        if self.hot_routes is None:
            self.analyze_hot_routes()
        
        peak_hour_list = self.time_distribution['peak_hours'].index.tolist()
        peak_hour_str = ', '.join([f"{h}:00" for h in sorted(peak_hour_list)])
        
        top_routes = self.hot_routes.head(5)[['route', 'delay_rate', 'avg_delay_minutes']]
        top_routes_list = []
        for _, row in top_routes.iterrows():
            top_routes_list.append({
                'route': row['route'],
                'delay_rate': f"{row['delay_rate'] * 100:.1f}%",
                'avg_delay': f"{row['avg_delay_minutes']:.0f}分钟"
            })
        
        monthly_peak = self.time_distribution['monthly']['delay_rate'].nlargest(3)
        month_names = {1: '1月', 2: '2月', 3: '3月', 4: '4月', 5: '5月', 6: '6月',
                      7: '7月', 8: '8月', 9: '9月', 10: '10月', 11: '11月', 12: '12月'}
        peak_months = [month_names.get(m, f"{m}月") for m in monthly_peak.index]
        
        return {
            'peak_hours': peak_hour_str,
            'top_high_risk_routes': top_routes_list,
            'peak_months': peak_months,
            'high_risk_weekdays': [5, 6]
        }


def plot_hourly_delay_distribution(hourly_data: pd.DataFrame, figsize=(12, 6)):
    fig, ax1 = plt.subplots(figsize=figsize)
    
    colors = sns.color_palette("RdYlGn_r", len(hourly_data))
    sorted_colors = [colors[i] for i in np.argsort(hourly_data['delay_rate'].values)]
    
    bars = ax1.bar(hourly_data.index, hourly_data['delay_rate'] * 100, 
                   color=sorted_colors, alpha=0.7, label='延误率')
    ax1.set_xlabel('起飞小时')
    ax1.set_ylabel('延误率 (%)', color='#e74c3c')
    ax1.tick_params(axis='y', labelcolor='#e74c3c')
    ax1.set_xticks(hourly_data.index)
    ax1.set_title('各时段延误分布')
    
    ax2 = ax1.twinx()
    ax2.plot(hourly_data.index, hourly_data['avg_delay_minutes'], 
             color='#3498db', marker='o', linewidth=2, label='平均延误时长')
    ax2.set_ylabel('平均延误时长 (分钟)', color='#3498db')
    ax2.tick_params(axis='y', labelcolor='#3498db')
    
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
    
    plt.tight_layout()
    return fig


def plot_weekday_delay_distribution(weekday_data: pd.DataFrame, figsize=(10, 6)):
    fig, ax = plt.subplots(figsize=figsize)
    
    day_names = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
    weekday_data = weekday_data.reindex(range(7))
    
    colors = ['#27ae60' if v < weekday_data['delay_rate'].mean() * 0.9 else 
              '#f39c12' if v < weekday_data['delay_rate'].mean() * 1.1 else '#e74c3c'
              for v in weekday_data['delay_rate'].values]
    
    bars = ax.bar(day_names, weekday_data['delay_rate'] * 100, color=colors)
    ax.set_xlabel('星期')
    ax.set_ylabel('延误率 (%)')
    ax.set_title('各星期延误分布')
    
    for i, bar in enumerate(bars):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                f'{weekday_data.iloc[i]["delay_rate"]*100:.1f}%',
                ha='center', va='bottom')
    
    plt.tight_layout()
    return fig


def plot_delay_heatmap(heatmap_data: pd.DataFrame, figsize=(12, 8)):
    fig, ax = plt.subplots(figsize=figsize)
    
    day_names = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
    
    sns.heatmap(heatmap_data * 100, 
                cmap='RdYlGn_r', 
                annot=True, 
                fmt='.1f',
                cbar_kws={'label': '延误率 (%)'},
                xticklabels=day_names,
                yticklabels=[f"{h}:00" for h in heatmap_data.index],
                ax=ax)
    
    ax.set_title('延误热力图：小时 × 星期')
    ax.set_xlabel('星期')
    ax.set_ylabel('起飞时间')
    
    plt.tight_layout()
    return fig


def plot_hot_routes(hot_routes: pd.DataFrame, figsize=(12, 8)):
    fig, ax = plt.subplots(figsize=figsize)
    
    y_pos = np.arange(len(hot_routes))
    
    bars = ax.barh(y_pos, hot_routes['delay_rate'] * 100, 
                   color=plt.cm.Reds(hot_routes['delay_score'] / hot_routes['delay_score'].max()))
    
    ax.set_yticks(y_pos)
    ax.set_yticklabels(hot_routes['route'])
    ax.set_xlabel('延误率 (%)')
    ax.set_title('Top 高延误风险航线')
    ax.invert_yaxis()
    
    for i, bar in enumerate(bars):
        width = bar.get_width()
        route_data = hot_routes.iloc[i]
        ax.text(width + 0.5, bar.get_y() + bar.get_height()/2,
                f"{width:.1f}% (平均{route_data['avg_delay_minutes']:.0f}分钟)",
                va='center')
    
    plt.tight_layout()
    return fig


if __name__ == '__main__':
    analyzer = DelayTrendAnalyzer()
    
    print("=== 测试延误趋势分析 ===")
    
    print("\n1. 热点航线分析:")
    hot_routes = analyzer.analyze_hot_routes(top_n=5)
    print(hot_routes[['route', 'flight_count', 'delay_rate', 'avg_delay_minutes', 'delay_score']])
    
    print("\n2. 时间分布分析:")
    time_dist = analyzer.analyze_time_distribution()
    print("高峰时段:", time_dist['peak_hours'].index.tolist())
    print("\n小时延误率:")
    print(time_dist['hourly']['delay_rate'].sort_values(ascending=False).head())
    
    print("\n3. 航线延误预测:")
    forecast = analyzer.get_route_delay_forecast('PEK', 'SHA')
    print(f"PEK-SHA 航线延误率: {forecast['overall_delay_rate']}%")
    print(f"最佳时段: {forecast['best_hours']}")
    print(f"高风险时段: {forecast['worst_hours']}")
    
    print("\n4. 延误预警摘要:")
    alert = analyzer.get_delay_alert_summary()
    print(f"高峰时段: {alert['peak_hours']}")
    print(f"高风险月份: {', '.join(alert['peak_months'])}")
    print("Top 高风险航线:")
    for route in alert['top_high_risk_routes']:
        print(f"  - {route['route']}: {route['delay_rate']}, 平均{route['avg_delay']}")
