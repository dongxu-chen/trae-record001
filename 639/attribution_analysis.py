import pandas as pd
import numpy as np
import shap
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Tuple


class DelayAttributionAnalyzer:
    def __init__(self, model, feature_names):
        self.model = model
        self.feature_names = feature_names
        self.explainer = None
        self.shap_values = None
        
    def init_shap_explainer(self, X_sample):
        if hasattr(self.model.delay_model, 'get_booster'):
            self.explainer = shap.TreeExplainer(self.model.delay_model)
            self.shap_values = self.explainer.shap_values(X_sample)
        return self.explainer
    
    def get_feature_shap_importance(self, X_sample, top_n=10):
        if self.shap_values is None:
            self.init_shap_explainer(X_sample)
        
        shap_abs_mean = np.abs(self.shap_values).mean(axis=0)
        
        importance_df = pd.DataFrame({
            'feature': self.feature_names,
            'shap_importance': shap_abs_mean
        }).sort_values('shap_importance', ascending=False).head(top_n)
        
        return importance_df
    
    def analyze_single_prediction(self, X_single):
        if self.explainer is None:
            self.init_shap_explainer(X_single)
        
        shap_val = self.explainer.shap_values(X_single)[0]
        base_value = self.explainer.expected_value
        
        feature_contributions = pd.DataFrame({
            'feature': self.feature_names,
            'shap_value': shap_val,
            'feature_value': X_single.iloc[0].values
        })
        feature_contributions['abs_shap'] = np.abs(feature_contributions['shap_value'])
        feature_contributions = feature_contributions.sort_values('abs_shap', ascending=False)
        
        return feature_contributions, base_value
    
    def get_delay_reason_probability(self, prediction, weather, flow_control, airline):
        base_prob = prediction['delay_probability']
        
        weather_impact = {
            '晴朗': 0.05, '多云': 0.1, '小雨': 0.3, '中雨': 0.5,
            '雷暴': 0.7, '大雾': 0.8, '大雪': 0.9
        }
        
        flow_impact = {'无': 0.1, '轻度': 0.25, '中度': 0.45, '重度': 0.7}
        
        airline_delay_factor = {
            'CA': 0.28, 'MU': 0.32, 'CZ': 0.30, 'HU': 0.25, '3U': 0.22
        }
        
        w_impact = weather_impact.get(weather, 0.1)
        f_impact = flow_impact.get(flow_control, 0.1)
        a_factor = airline_delay_factor.get(airline, 0.25)
        
        total_factor = w_impact * 0.4 + f_impact * 0.4 + a_factor * 0.2
        
        reasons = {
            '天气原因': w_impact * base_prob * 0.8,
            '流量控制': f_impact * base_prob * 0.8,
            '航空公司计划': a_factor * base_prob * 0.5,
            '机械故障': 0.08 * base_prob,
            '机场保障': 0.06 * base_prob,
            '空中交通管制': f_impact * base_prob * 0.6,
            '旅客原因': 0.03 * base_prob,
            '油料供应': 0.04 * base_prob
        }
        
        total = sum(reasons.values())
        if total > 0:
            reasons = {k: v / total for k, v in reasons.items()}
        
        return sorted(reasons.items(), key=lambda x: x[1], reverse=True)
    
    def generate_attribution_report(self, X_single, prediction, weather, flow_control, airline, 
                                     dep_sector=None, arr_sector=None, is_same_sector=None):
        feature_contrib, base_value = self.analyze_single_prediction(X_single)
        reason_probs = self.get_delay_reason_probability(prediction, weather, flow_control, airline)
        
        top_drivers = feature_contrib.head(6)
        driver_names = {
            'weather_severity': '天气状况',
            'flow_severity': '流量控制等级',
            'airline_encoded': '航空公司',
            'historical_delay_30d_scaled': '30天历史延误',
            'historical_delay_7d_scaled': '7天历史延误',
            'is_peak_hour': '是否高峰时段',
            'is_peak_season': '是否旺季',
            'departure_hour_scaled': '起飞时段',
            'day_of_week': '星期几',
            'month': '月份',
            'weather_flow_interaction': '天气-流量交互影响',
            'delay_trend_scaled': '延误趋势',
            'route_encoded': '航线',
            'departure_airport_encoded': '起飞机场',
            'arrival_airport_encoded': '到达机场',
            'sector_flow_combined_scaled': '扇区-流量综合影响',
            'sector_congestion_scaled': '扇区拥堵程度',
            'cross_region_penalty_scaled': '跨区域影响',
            'sector_weather_flow_scaled': '扇区-天气-流量交互',
            'is_same_sector': '是否同扇区',
            'is_same_region': '是否同区域',
            'departure_sector_encoded': '起飞扇区',
            'arrival_sector_encoded': '到达扇区',
            'departure_region_encoded': '起飞区域',
            'arrival_region_encoded': '到达区域'
        }
        
        drivers_report = []
        for _, row in top_drivers.iterrows():
            feature_name = driver_names.get(row['feature'], row['feature'])
            impact = '增加' if row['shap_value'] > 0 else '降低'
            drivers_report.append({
                'feature': feature_name,
                'impact': impact,
                'magnitude': abs(row['shap_value'])
            })
        
        sector_info = None
        if dep_sector and arr_sector:
            sector_info = {
                'departure_sector': dep_sector,
                'arrival_sector': arr_sector,
                'is_same_sector': is_same_sector,
                'cross_region_risk': '低' if is_same_sector else '高'
            }
        
        return {
            'top_drivers': drivers_report,
            'delay_reasons': reason_probs,
            'base_probability': base_value,
            'final_probability': prediction['delay_probability'],
            'sector_info': sector_info
        }
    
    def get_airline_comparison(self, airline_df, current_airline=None):
        comparison = airline_df.copy()
        
        comparison['delay_risk_score'] = (100 - comparison['on_time_rate']) * 0.6 + \
                                         (comparison['avg_compensation'] / 10) * 0.3 + \
                                         (10 - comparison['customer_rating']) * 10 * 0.1
        
        comparison = comparison.sort_values('delay_risk_score')
        comparison['rank'] = range(1, len(comparison) + 1)
        
        if current_airline:
            current_row = comparison[comparison['airline_code'] == current_airline]
            if not current_row.empty:
                comparison['is_current'] = comparison['airline_code'] == current_airline
        
        return comparison


def create_visualization_assets():
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
    plt.rcParams['axes.unicode_minus'] = False


def plot_delay_reason_distribution(reason_probs, figsize=(10, 6)):
    create_visualization_assets()
    
    reasons, probs = zip(*reason_probs)
    colors = plt.cm.Reds(np.linspace(0.3, 0.8, len(reasons)))
    
    fig, ax = plt.subplots(figsize=figsize)
    bars = ax.barh(reasons, [p * 100 for p in probs], color=colors)
    ax.set_xlabel('概率 (%)')
    ax.set_title('延误原因概率分布')
    
    for i, bar in enumerate(bars):
        width = bar.get_width()
        ax.text(width + 1, bar.get_y() + bar.get_height()/2, 
                f'{probs[i]*100:.1f}%', va='center')
    
    plt.tight_layout()
    return fig


def plot_feature_drivers(drivers_report, figsize=(10, 6)):
    create_visualization_assets()
    
    features = [d['feature'] for d in drivers_report]
    magnitudes = [d['magnitude'] for d in drivers_report]
    impacts = [1 if d['impact'] == '增加' else -1 for d in drivers_report]
    
    colors = ['#e74c3c' if i > 0 else '#27ae60' for i in impacts]
    
    fig, ax = plt.subplots(figsize=figsize)
    bars = ax.barh(features, [m * i for m, i in zip(magnitudes, impacts)], color=colors)
    ax.set_xlabel('影响程度 (SHAP值)')
    ax.set_title('延误主要影响因素')
    ax.axvline(x=0, color='black', linestyle='-', linewidth=0.5)
    
    plt.tight_layout()
    return fig


def plot_airline_comparison(comparison_df, figsize=(12, 6)):
    create_visualization_assets()
    
    fig, axes = plt.subplots(1, 3, figsize=figsize)
    
    axes[0].barh(comparison_df['airline_name'], comparison_df['on_time_rate'], 
                 color='#3498db')
    axes[0].set_title('准点率 (%)')
    axes[0].set_xlim(60, 100)
    
    axes[1].barh(comparison_df['airline_name'], comparison_df['avg_compensation'], 
                 color='#e67e22')
    axes[1].set_title('平均赔付 (元)')
    
    axes[2].barh(comparison_df['airline_name'], comparison_df['customer_rating'], 
                 color='#2ecc71')
    axes[2].set_title('客户评分')
    axes[2].set_xlim(6, 10)
    
    plt.tight_layout()
    return fig


def plot_airline_radar_chart(comparison_df, current_airline_code=None, figsize=(10, 10)):
    create_visualization_assets()
    
    radar_dimensions = [
        ('on_time_rate', '准点率', 100),
        ('service_quality', '服务质量', 10),
        ('compensation_adequacy', '赔付合理性', 10),
        ('flight_network', '航线网络', 10),
        ('baggage_handling', '行李处理', 10),
        ('customer_satisfaction', '客户满意度', 10)
    ]
    
    fig = plt.figure(figsize=figsize)
    ax = fig.add_subplot(111, projection='polar')
    
    num_vars = len(radar_dimensions)
    angles = [n / float(num_vars) * 2 * np.pi for n in range(num_vars)]
    angles += angles[:1]
    
    colors = plt.cm.Set3(np.linspace(0, 1, len(comparison_df)))
    
    for idx, (_, row) in enumerate(comparison_df.iterrows()):
        values = []
        for col, _, max_val in radar_dimensions:
            if col == 'on_time_rate':
                val = row[col]
            else:
                val = row[col] * 10 if row[col] <= 10 else row[col]
            values.append(val / max_val * 100)
        
        values += values[:1]
        
        linewidth = 3 if row['airline_code'] == current_airline_code else 1.5
        alpha = 1.0 if row['airline_code'] == current_airline_code else 0.6
        
        ax.plot(angles, values, linewidth=linewidth, linestyle='solid', 
                label=row['airline_name'], color=colors[idx], alpha=alpha)
        ax.fill(angles, values, color=colors[idx], alpha=0.1 if alpha < 1 else 0.25)
    
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels([dim[1] for dim in radar_dimensions], fontsize=11)
    
    ax.set_ylim(0, 100)
    ax.set_yticks([20, 40, 60, 80, 100])
    ax.set_yticklabels(['20%', '40%', '60%', '80%', '100%'], fontsize=9)
    ax.grid(True)
    
    ax.set_title('航空公司多维度对比雷达图', fontsize=14, pad=20)
    ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.0), fontsize=10)
    
    plt.tight_layout()
    return fig


def plot_policy_multipliers(policy_learner, figsize=(12, 6)):
    create_visualization_assets()
    
    multipliers = policy_learner.current_policy['reason_multipliers']
    reasons = list(multipliers.keys())
    values = list(multipliers.values())
    
    colors = ['#27ae60' if v < 0.8 else '#f39c12' if v < 1.2 else '#e74c3c' for v in values]
    
    fig, ax = plt.subplots(figsize=figsize)
    bars = ax.bar(reasons, values, color=colors, edgecolor='black', linewidth=0.5)
    
    ax.axhline(y=1.0, color='gray', linestyle='--', linewidth=1, label='基准水平')
    
    for i, bar in enumerate(bars):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + 0.02,
                f'{values[i]:.2f}', ha='center', va='bottom', fontsize=10)
    
    ax.set_xlabel('延误原因')
    ax.set_ylabel('赔付系数')
    ax.set_title(f'当前赔付政策系数 (版本 {policy_learner.current_policy["version"]})')
    ax.legend()
    ax.set_ylim(0, max(values) + 0.3)
    
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    return fig


def plot_sector_flow_analysis(sector_data, figsize=(12, 8)):
    create_visualization_assets()
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=figsize)
    
    sector_names = list(sector_data.keys())
    congestion_values = [d['congestion'] for d in sector_data.values()]
    delay_rates = [d.get('avg_delay_rate', 0) for d in sector_data.values()]
    
    colors = plt.cm.RdYlGn_r([min(v, 0.95) for v in congestion_values])
    
    ax1.bar(sector_names, [v * 100 for v in congestion_values], color=colors)
    ax1.set_title('各扇区拥堵指数 (%)')
    ax1.set_ylabel('拥堵指数 (%)')
    ax1.set_ylim(0, 100)
    for i, v in enumerate(congestion_values):
        ax1.text(i, v * 100 + 1, f'{v*100:.0f}%', ha='center', va='bottom')
    
    flow_levels = ['无', '轻度', '中度', '重度']
    flow_probabilities = [0.5, 0.25, 0.18, 0.07]
    
    ax2.pie(flow_probabilities, labels=flow_levels, autopct='%1.1f%%',
            colors=['#27ae60', '#f1c40f', '#e67e22', '#e74c3c'], startangle=90)
    ax2.set_title('流量控制等级概率分布')
    
    plt.tight_layout()
    return fig


if __name__ == '__main__':
    print("归因分析模块已就绪")
