"""
可视化模块 - 天气衍生品定价结果的图表展示
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
from typing import Dict, Optional

matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
matplotlib.rcParams['axes.unicode_minus'] = False


class Visualizer:
    """天气衍生品可视化工具"""

    def __init__(self, output_dir: str = 'output'):
        self.output_dir = output_dir

    def plot_temperature_data(self, weather_df: pd.DataFrame, title: str = "温度时间序列"):
        fig, axes = plt.subplots(3, 1, figsize=(14, 12))

        axes[0].plot(weather_df['date'], weather_df['temperature'], 'b-', alpha=0.7, label='日温度')
        axes[0].plot(weather_df['date'], weather_df['seasonal'], 'r--', alpha=0.5, label='季节性成分')
        axes[0].axhline(y=18, color='gray', linestyle=':', alpha=0.5, label='基准温度(18°C)')
        axes[0].set_title(f'{title} - 温度变化', fontsize=14)
        axes[0].set_xlabel('日期')
        axes[0].set_ylabel('温度 (°C)')
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)

        axes[1].plot(weather_df['date'], weather_df['HDD'], 'orange', alpha=0.7, label='HDD')
        axes[1].plot(weather_df['date'], weather_df['CDD'], 'red', alpha=0.7, label='CDD')
        axes[1].set_title('每日HDD/CDD指数', fontsize=14)
        axes[1].set_xlabel('日期')
        axes[1].set_ylabel('指数值')
        axes[1].legend()
        axes[1].grid(True, alpha=0.3)

        axes[2].plot(weather_df['date'], weather_df['cum_HDD'], 'orange', label='累计HDD')
        axes[2].plot(weather_df['date'], weather_df['cum_CDD'], 'red', label='累计CDD')
        axes[2].set_title('累计HDD/CDD指数', fontsize=14)
        axes[2].set_xlabel('日期')
        axes[2].set_ylabel('累计值')
        axes[2].legend()
        axes[2].grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(f'{self.output_dir}/temperature_analysis.png', dpi=150, bbox_inches='tight')
        plt.close()
        print(f"温度分析图表已保存: {self.output_dir}/temperature_analysis.png")

    def plot_rainfall_data(self, weather_df: pd.DataFrame, title: str = "降雨量分析"):
        fig, axes = plt.subplots(2, 1, figsize=(14, 8))

        axes[0].bar(weather_df['date'], weather_df['rainfall'], alpha=0.7, color='blue', width=1)
        axes[0].set_title(f'{title} - 日降雨量', fontsize=14)
        axes[0].set_xlabel('日期')
        axes[0].set_ylabel('降雨量 (mm)')
        axes[0].grid(True, alpha=0.3)

        axes[1].plot(weather_df['date'], weather_df['cum_rainfall'], 'blue', label='累计降雨量')
        axes[1].fill_between(weather_df['date'], 0, weather_df['cum_rainfall'], alpha=0.3, color='blue')
        axes[1].set_title('累计降雨量', fontsize=14)
        axes[1].set_xlabel('日期')
        axes[1].set_ylabel('累计降雨量 (mm)')
        axes[1].legend()
        axes[1].grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(f'{self.output_dir}/rainfall_analysis.png', dpi=150, bbox_inches='tight')
        plt.close()
        print(f"降雨量分析图表已保存: {self.output_dir}/rainfall_analysis.png")

    def plot_pricing_curve(self, pricing_df: pd.DataFrame, contract_name: str = "HDD期权"):
        fig, axes = plt.subplots(2, 2, figsize=(14, 12))

        axes[0, 0].plot(pricing_df['temperature'], pricing_df['price'], 'b-', linewidth=2)
        axes[0, 0].fill_between(pricing_df['temperature'],
                                pricing_df['price_ci_low'],
                                pricing_df['price_ci_high'],
                                alpha=0.3, color='blue')
        axes[0, 0].set_title(f'{contract_name} - 定价曲线', fontsize=14)
        axes[0, 0].set_xlabel('初始温度 (°C)')
        axes[0, 0].set_ylabel('期权价格')
        axes[0, 0].grid(True, alpha=0.3)

        axes[0, 1].plot(pricing_df['temperature'], pricing_df['price_std'], 'r-', linewidth=2)
        axes[0, 1].set_title('定价标准误差', fontsize=14)
        axes[0, 1].set_xlabel('初始温度 (°C)')
        axes[0, 1].set_ylabel('标准误差')
        axes[0, 1].grid(True, alpha=0.3)

        axes[1, 0].plot(pricing_df['temperature'], pricing_df['hdd_mean'], 'g-', linewidth=2)
        axes[1, 0].set_title('预期HDD累计值', fontsize=14)
        axes[1, 0].set_xlabel('初始温度 (°C)')
        axes[1, 0].set_ylabel('预期HDD')
        axes[1, 0].grid(True, alpha=0.3)

        axes[1, 1].plot(pricing_df['temperature'], pricing_df['exercise_prob'], 'purple', linewidth=2)
        axes[1, 1].set_title('行权概率', fontsize=14)
        axes[1, 1].set_xlabel('初始温度 (°C)')
        axes[1, 1].set_ylabel('概率')
        axes[1, 1].set_ylim(0, 1)
        axes[1, 1].grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(f'{self.output_dir}/pricing_curve.png', dpi=150, bbox_inches='tight')
        plt.close()
        print(f"定价曲线图表已保存: {self.output_dir}/pricing_curve.png")

    def plot_greeks(self, greeks_result: Dict, pricing_curve_df: pd.DataFrame):
        fig, axes = plt.subplots(2, 2, figsize=(14, 12))

        deltas = []
        gammas = []
        temps = pricing_curve_df['temperature'].values

        for i in range(1, len(temps) - 1):
            delta = (pricing_curve_df['price'].iloc[i+1] - pricing_curve_df['price'].iloc[i-1]) / \
                    (temps[i+1] - temps[i-1])
            gamma = (pricing_curve_df['price'].iloc[i+1] - 2*pricing_curve_df['price'].iloc[i] +
                     pricing_curve_df['price'].iloc[i-1]) / ((temps[i+1] - temps[i])**2)
            deltas.append(delta)
            gammas.append(gamma)

        axes[0, 0].plot(temps[1:-1], deltas, 'b-', linewidth=2)
        axes[0, 0].set_title('Delta - 温度敏感度', fontsize=14)
        axes[0, 0].set_xlabel('温度 (°C)')
        axes[0, 0].set_ylabel('Delta')
        axes[0, 0].axhline(y=0, color='gray', linestyle='--', alpha=0.5)
        axes[0, 0].grid(True, alpha=0.3)

        axes[0, 1].plot(temps[1:-1], gammas, 'r-', linewidth=2)
        axes[0, 1].set_title('Gamma - Delta的变化率', fontsize=14)
        axes[0, 1].set_xlabel('温度 (°C)')
        axes[0, 1].set_ylabel('Gamma')
        axes[0, 1].axhline(y=0, color='gray', linestyle='--', alpha=0.5)
        axes[0, 1].grid(True, alpha=0.3)

        price_changes = pricing_curve_df['price'].diff().dropna()
        axes[1, 0].hist(price_changes, bins=50, color='blue', alpha=0.7, edgecolor='black')
        axes[1, 0].set_title('价格变化分布', fontsize=14)
        axes[1, 0].set_xlabel('价格变化')
        axes[1, 0].set_ylabel('频率')
        axes[1, 0].grid(True, alpha=0.3)

        axes[1, 1].plot(pricing_curve_df['temperature'], pricing_curve_df['exercise_prob'], 'g-', linewidth=2)
        axes[1, 1].fill_between(pricing_curve_df['temperature'], 0, pricing_curve_df['exercise_prob'],
                                alpha=0.3, color='green')
        axes[1, 1].set_title('行权概率随温度变化', fontsize=14)
        axes[1, 1].set_xlabel('温度 (°C)')
        axes[1, 1].set_ylabel('行权概率')
        axes[1, 1].set_ylim(0, 1)
        axes[1, 1].grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(f'{self.output_dir}/greeks_analysis.png', dpi=150, bbox_inches='tight')
        plt.close()
        print(f"希腊值分析图表已保存: {self.output_dir}/greeks_analysis.png")

    def plot_stress_test_results(self, stress_results: Dict):
        fig, axes = plt.subplots(2, 2, figsize=(16, 14))

        temp_test = stress_results['temperature_stress']
        axes[0, 0].plot(temp_test['temp_shift'], temp_test['price'], 'b-', linewidth=2)
        axes[0, 0].fill_between(temp_test['temp_shift'],
                                temp_test['price'] - temp_test['price_std']*1.96,
                                temp_test['price'] + temp_test['price_std']*1.96,
                                alpha=0.2, color='blue')
        axes[0, 0].axvline(x=0, color='red', linestyle='--', alpha=0.5)
        axes[0, 0].set_title('温度压力测试 - 期权价格', fontsize=14)
        axes[0, 0].set_xlabel('温度偏移 (°C)')
        axes[0, 0].set_ylabel('期权价格')
        axes[0, 0].grid(True, alpha=0.3)

        vol_test = stress_results['volatility_stress']
        axes[0, 1].plot(vol_test['vol_multiplier'], vol_test['price'], 'r-', linewidth=2, marker='o')
        axes[0, 1].axvline(x=1.0, color='gray', linestyle='--', alpha=0.5)
        axes[0, 1].set_title('波动率压力测试', fontsize=14)
        axes[0, 1].set_xlabel('波动率倍数')
        axes[0, 1].set_ylabel('期权价格')
        axes[0, 1].grid(True, alpha=0.3)

        extreme_test = stress_results['extreme_scenarios']
        colors = ['red' if x < -20 else 'orange' if x < -10 else 'gray' if x < 10 else 'lightblue' if x < 20 else 'blue'
                  for x in extreme_test['price_change_pct']]
        bars = axes[1, 0].barh(extreme_test['scenario'], extreme_test['price_change_pct'], color=colors, alpha=0.8)
        axes[1, 0].axvline(x=0, color='black', linewidth=0.5)
        axes[1, 0].set_title('极端情景测试 - 价格变化百分比', fontsize=14)
        axes[1, 0].set_xlabel('价格变化 (%)')
        axes[1, 0].grid(True, alpha=0.3, axis='x')

        var_data = stress_results['value_at_risk']
        var_labels = [k for k in var_data.keys() if k.startswith('VaR')]
        var_values = [var_data[k] for k in var_labels]
        axes[1, 1].bar(range(len(var_labels)), var_values, color='steelblue', alpha=0.8)
        axes[1, 1].set_xticks(range(len(var_labels)))
        axes[1, 1].set_xticklabels([l.replace('VaR_', 'VaR ').replace('%', '%') for l in var_labels],
                                   rotation=45, ha='right')
        axes[1, 1].set_title('风险价值 (VaR) 分析', fontsize=14)
        axes[1, 1].set_ylabel('VaR 值')
        axes[1, 1].grid(True, alpha=0.3, axis='y')

        plt.tight_layout()
        plt.savefig(f'{self.output_dir}/stress_test_results.png', dpi=150, bbox_inches='tight')
        plt.close()
        print(f"压力测试结果图表已保存: {self.output_dir}/stress_test_results.png")

    def plot_mc_convergence(self, payoffs: np.ndarray, true_price: float = None):
        n_sims = len(payoffs)
        running_mean = np.cumsum(payoffs) / np.arange(1, n_sims + 1)
        running_std = np.zeros(n_sims)

        for i in range(1, n_sims):
            running_std[i] = np.std(payoffs[:i+1]) / np.sqrt(i+1)

        fig, axes = plt.subplots(2, 1, figsize=(14, 10))

        axes[0].plot(range(1, n_sims + 1), running_mean, 'b-', linewidth=1, alpha=0.7)
        if true_price is not None:
            axes[0].axhline(y=true_price, color='red', linestyle='--', label='真实价格')
        axes[0].set_title('蒙特卡洛收敛性分析', fontsize=14)
        axes[0].set_xlabel('模拟次数')
        axes[0].set_ylabel('累积平均价格')
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)

        axes[1].plot(range(1, n_sims + 1), running_std, 'r-', linewidth=1, alpha=0.7)
        axes[1].set_title('标准误差收敛性', fontsize=14)
        axes[1].set_xlabel('模拟次数')
        axes[1].set_ylabel('标准误差')
        axes[1].grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(f'{self.output_dir}/mc_convergence.png', dpi=150, bbox_inches='tight')
        plt.close()
        print(f"蒙特卡洛收敛性图表已保存: {self.output_dir}/mc_convergence.png")

    def plot_heatmap(self, pricing_df: pd.DataFrame, title: str = "期权价格热力图"):
        pivot = pricing_df.pivot(index='temperature', columns='strike', values='price')

        fig, ax = plt.subplots(figsize=(12, 8))
        im = ax.imshow(pivot.values, aspect='auto', cmap='RdYlBu_r')

        ax.set_xticks(range(len(pivot.columns)))
        ax.set_xticklabels([f'{c:.0f}' for c in pivot.columns], rotation=45)
        ax.set_yticks(range(len(pivot.index)))
        ax.set_yticklabels([f'{v:.1f}' for v in pivot.index])

        ax.set_xlabel('行权价')
        ax.set_ylabel('初始温度 (°C)')
        ax.set_title(title, fontsize=14)

        plt.colorbar(im, ax=ax, label='期权价格')

        for i in range(len(pivot.index)):
            for j in range(len(pivot.columns)):
                ax.text(j, i, f'{pivot.values[i, j]:.1f}', ha='center', va='center',
                       fontsize=8, color='white' if pivot.values[i, j] > pivot.values.max()/2 else 'black')

        plt.tight_layout()
        plt.savefig(f'{self.output_dir}/price_heatmap.png', dpi=150, bbox_inches='tight')
        plt.close()
        print(f"价格热力图已保存: {self.output_dir}/price_heatmap.png")
