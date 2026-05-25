import pandas as pd
import numpy as np
import statsmodels.api as sm
import statsmodels.formula.api as smf
from typing import Dict, Tuple
import matplotlib.pyplot as plt
import seaborn as sns

class DIDModel:
    def __init__(self):
        self.model = None
        self.results = None
        self.treatment_effect = None
        self.confidence_interval = None
    
    def fit(
        self,
        df: pd.DataFrame,
        outcome_var: str = 'sales',
        treated_var: str = 'treated_group',
        post_var: str = 'post_treatment',
        covariates: list = None
    ) -> Dict:
        df_model = df.copy()
        df_model['post'] = df_model[post_var].astype(int)
        df_model['treated'] = df_model[treated_var].astype(int)
        df_model['did'] = df_model['treated'] * df_model['post']
        
        formula = f"{outcome_var} ~ treated + post + did"
        
        if covariates:
            for cov in covariates:
                formula += f" + {cov}"
        
        self.model = smf.ols(formula, data=df_model)
        self.results = self.model.fit(cov_type='cluster', cov_kwds={'groups': df_model['product_id']})
        
        did_coef = self.results.params['did']
        did_pvalue = self.results.pvalues['did']
        did_ci = self.results.conf_int().loc['did'].values
        
        base_mean = df_model[
            (df_model['treated'] == 0) & (df_model['post'] == 0)
        ][outcome_var].mean()
        
        self.treatment_effect = (did_coef / base_mean) * 100 if base_mean > 0 else did_coef
        self.confidence_interval = (did_ci / base_mean * 100) if base_mean > 0 else did_ci
        
        return {
            'treatment_effect_pct': self.treatment_effect,
            'treatment_effect_absolute': did_coef,
            'p_value': did_pvalue,
            'ci_lower': self.confidence_interval[0],
            'ci_upper': self.confidence_interval[1],
            'r_squared': self.results.rsquared,
            'n_observations': self.results.nobs,
            'is_significant': did_pvalue < 0.05
        }
    
    def parallel_trend_test(self, df: pd.DataFrame, outcome_var: str = 'sales') -> Dict:
        df_test = df.copy()
        df_test['post'] = df_test['post_treatment'].astype(int)
        
        treatment_start = df_test[df_test['is_treated'] == True]['treatment_period'].min()
        
        period_dummies = pd.get_dummies(df_test['period'], prefix='period', drop_first=True)
        df_test = pd.concat([df_test, period_dummies], axis=1)
        
        df_test['treated'] = df_test['treated_group'].astype(int)
        
        interactions = []
        pre_periods = []
        for period in df_test['period'].unique():
            if period < treatment_start:
                col = f'period_{period}'
                if col in df_test.columns:
                    df_test[f'treated_x_{col}'] = df_test['treated'] * df_test[col]
                    interactions.append(f'treated_x_{col}')
                    pre_periods.append(period)
        
        if interactions:
            formula = f"{outcome_var} ~ treated + " + " + ".join(interactions)
            model = smf.ols(formula, data=df_test)
            results = model.fit()
            
            f_test = results.f_test(np.eye(len(interactions))[-len(interactions):])
            
            coefs = []
            for inter in interactions:
                coefs.append({
                    'period': int(inter.split('_')[-1]),
                    'coef': results.params[inter],
                    'p_value': results.pvalues[inter],
                    'ci_lower': results.conf_int().loc[inter, 0],
                    'ci_upper': results.conf_int().loc[inter, 1]
                })
            
            significant_violations = sum(1 for c in coefs if c['p_value'] < 0.05)
            
            warning_level = 'high' if f_test.pvalue < 0.01 else 'medium' if f_test.pvalue < 0.05 else 'low'
            warnings = []
            if warning_level == 'high':
                warnings.append('⚠️ 高度警告：强烈拒绝平行趋势假设，DID结果可能不可靠')
                warnings.append('💡 建议：考虑使用PSM或合成控制法，或重新选择控制组')
            elif warning_level == 'medium':
                warnings.append('⚠️ 中度警告：平行趋势假设存疑，需谨慎解读结果')
                warnings.append('💡 建议：检查是否有其他同期事件影响，考虑增加协变量')
            
            return {
                'f_statistic': f_test.fvalue,
                'p_value': f_test.pvalue,
                'parallel_trend': f_test.pvalue > 0.05,
                'hypothesis': '不能拒绝平行趋势假设' if f_test.pvalue > 0.05 else '拒绝平行趋势假设',
                'warning_level': warning_level,
                'warnings': warnings,
                'pre_periods': pre_periods,
                'period_coefficients': coefs,
                'significant_violations': significant_violations,
                'total_pre_periods': len(pre_periods)
            }
        
        return {'message': '前期数据不足，无法进行平行趋势检验'}
    
    def plot_parallel_trend(
        self,
        df: pd.DataFrame,
        outcome_var: str = 'sales',
        figsize: Tuple[int, int] = (10, 6)
    ) -> plt.Figure:
        df_plot = df.copy()
        df_plot['Group'] = df_plot['treated_group'].map({1: '处理组', 0: '控制组'})
        
        trend_data = df_plot.groupby(['period', 'Group'])[outcome_var].mean().reset_index()
        
        fig, ax = plt.subplots(figsize=figsize)
        
        for group in ['处理组', '控制组']:
            group_data = trend_data[trend_data['Group'] == group]
            ax.plot(
                group_data['period'],
                group_data[outcome_var],
                marker='o',
                label=group,
                linewidth=2
            )
        
        treated_periods = df[df['is_treated']]['treatment_period'].unique()
        if len(treated_periods) > 0:
            treatment_start = treated_periods.min()
            ax.axvline(
                x=treatment_start - 0.5,
                color='red',
                linestyle='--',
                label='政策实施点',
                linewidth=2
            )
            
            ax.axvspan(
                treatment_start - 0.5,
                df_plot['period'].max() + 0.5,
                alpha=0.1,
                color='red',
                label='处理期'
            )
        
        ax.set_xlabel('时间周期', fontsize=12)
        ax.set_ylabel(outcome_var, fontsize=12)
        ax.set_title('平行趋势检验图', fontsize=14, fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        return fig
    
    def plot_pre_trend_coefficients(
        self,
        parallel_test_results: Dict,
        figsize: Tuple[int, int] = (10, 6)
    ) -> plt.Figure:
        if 'period_coefficients' not in parallel_test_results:
            raise ValueError("请先运行parallel_trend_test获取结果")
        
        coefs = parallel_test_results['period_coefficients']
        coefs = sorted(coefs, key=lambda x: x['period'])
        
        periods = [c['period'] for c in coefs]
        values = [c['coef'] for c in coefs]
        ci_lower = [c['ci_lower'] for c in coefs]
        ci_upper = [c['ci_upper'] for c in coefs]
        significant = [c['p_value'] < 0.05 for c in coefs]
        
        fig, ax = plt.subplots(figsize=figsize)
        
        colors = ['#e74c3c' if s else '#3498db' for s in significant]
        
        ax.errorbar(
            x=periods,
            y=values,
            yerr=[
                [v - l for v, l in zip(values, ci_lower)],
                [u - v for v, u in zip(values, ci_upper)]
            ],
            fmt='o',
            capsize=8,
            color='#3498db',
            ecolor=colors,
            markersize=8,
            linewidth=2
        )
        
        ax.axhline(y=0, color='red', linestyle='--', linewidth=2, alpha=0.7, label='零效应线')
        
        ax.set_xlabel('事前周期', fontsize=12)
        ax.set_ylabel('处理效应系数', fontsize=12)
        ax.set_title('事前趋势系数图 (事件研究法)', fontsize=14, fontweight='bold')
        
        for i, (period, sig) in enumerate(zip(periods, significant)):
            if sig:
                ax.annotate(
                    '*',
                    xy=(period, values[i] + (ci_upper[i] - values[i]) + 5),
                    ha='center',
                    fontsize=16,
                    color='red'
                )
        
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        return fig
    
    def plot_treatment_effect(
        self,
        figsize: Tuple[int, int] = (8, 6)
    ) -> plt.Figure:
        if self.treatment_effect is None:
            raise ValueError("模型尚未拟合，请先调用fit()方法")
        
        fig, ax = plt.subplots(figsize=figsize)
        
        effect = self.treatment_effect
        ci_lower, ci_upper = self.confidence_interval
        
        bars = ax.bar(
            ['平均处理效应'],
            [effect],
            yerr=[[effect - ci_lower], [ci_upper - effect]],
            capsize=10,
            color='#2ecc71',
            alpha=0.7
        )
        
        ax.axhline(y=0, color='red', linestyle='--', alpha=0.5)
        ax.set_ylabel('销售提升率 (%)', fontsize=12)
        ax.set_title('促销活动因果效应估计', fontsize=14, fontweight='bold')
        
        for bar in bars:
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                height + (ci_upper - effect) + 0.5,
                f'{height:.2f}%',
                ha='center',
                va='bottom',
                fontsize=12,
                fontweight='bold'
            )
        
        ax.set_ylim(
            min(ci_lower - 2, -5),
            max(ci_upper + 2, 5)
        )
        
        plt.tight_layout()
        return fig
    
    def get_summary(self) -> str:
        if self.results is None:
            return "模型尚未拟合"
        
        summary_text = """
        ========================================
        双重差分法 (DID) 模型结果摘要
        ========================================
        
        模型类型: 聚类标准误OLS (产品层面聚类)
        
        因果效应估计:
        """
        
        summary_text += f"        - 销售提升率: {self.treatment_effect:.2f}%\n"
        summary_text += f"        - 95%置信区间: [{self.confidence_interval[0]:.2f}%, {self.confidence_interval[1]:.2f}%]\n"
        summary_text += f"        - p值: {self.results.pvalues['did']:.4f}\n"
        summary_text += f"        - 统计显著性: {'显著 (p<0.05)' if self.results.pvalues['did'] < 0.05 else '不显著'}\n\n"
        
        summary_text += f"""
        模型拟合指标:
        - R平方: {self.results.rsquared:.4f}
        - 观测值数量: {int(self.results.nobs)}
        """
        
        return summary_text
