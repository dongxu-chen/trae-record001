import pandas as pd
import numpy as np
import statsmodels.api as sm
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from typing import Dict, Tuple, List
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats

class PSMModel:
    def __init__(self):
        self.ps_model = None
        self.matched_data = None
        self.propensity_scores = None
        self.ate = None
        self.att = None
        self.atc = None
        self.treatment_effect = None
    
    def estimate_propensity_score(
        self,
        df: pd.DataFrame,
        treatment_var: str = 'is_treated',
        covariates: List[str] = None
    ) -> pd.DataFrame:
        df_ps = df.copy()
        
        if covariates is None:
            covariates = [
                'base_sales', 'avg_sales_pre', 'sales_trend_pre', 
                'sales_std_pre', 'max_sales_pre', 'min_sales_pre',
                'sales_volatility', 'historical_growth_rate', 
                'avg_order_value', 'review_score', 'return_rate',
                'customer_age', 'customer_tenure', 
                'purchase_frequency', 'customer_ltv'
            ]
            category_cols = [c for c in df_ps.columns if c.startswith('cat_')]
            channel_cols = [c for c in df_ps.columns if c.startswith('ch_')]
            price_cols = [c for c in df_ps.columns if c.startswith('price_')]
            segment_cols = [c for c in df_ps.columns if c.startswith('seg_')]
            covariates += category_cols + channel_cols + price_cols + segment_cols
        
        covariates = [c for c in covariates if c in df_ps.columns]
        
        X = df_ps[covariates]
        y = df_ps[treatment_var].astype(int)
        
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        self.ps_model = LogisticRegression(random_state=42, max_iter=1000)
        self.ps_model.fit(X_scaled, y)
        
        df_ps['propensity_score'] = self.ps_model.predict_proba(X_scaled)[:, 1]
        self.propensity_scores = df_ps['propensity_score'].values
        
        return df_ps
    
    def match(
        self,
        df: pd.DataFrame,
        treatment_var: str = 'is_treated',
        ps_col: str = 'propensity_score',
        outcome_var: str = 'sales',
        caliper: float = 0.05,
        n_matches: int = 1
    ) -> pd.DataFrame:
        treated = df[df[treatment_var] == True].copy()
        control = df[df[treatment_var] == False].copy()
        
        matched_indices = []
        matched_pairs = []
        
        for idx, treated_row in treated.iterrows():
            treated_ps = treated_row[ps_col]
            
            control['distance'] = np.abs(control[ps_col] - treated_ps)
            
            valid_controls = control[
                control['distance'] <= caliper
            ].sort_values('distance').head(n_matches)
            
            if len(valid_controls) > 0:
                matched_indices.append(idx)
                matched_indices.extend(valid_controls.index.tolist())
                
                for _, ctrl_row in valid_controls.iterrows():
                    matched_pairs.append({
                        'treated_idx': idx,
                        'control_idx': ctrl_row.name,
                        'ps_distance': ctrl_row['distance']
                    })
        
        matched_data = df.loc[list(set(matched_indices))].copy()
        matched_data['weight'] = 1.0
        
        control_counts = pd.Series([p['control_idx'] for p in matched_pairs]).value_counts()
        for idx in matched_data.index:
            if matched_data.loc[idx, treatment_var] == False:
                matched_data.loc[idx, 'weight'] = 1.0 / control_counts.get(idx, 1)
        
        self.matched_data = matched_data
        self.matched_pairs = pd.DataFrame(matched_pairs)
        
        return matched_data
    
    def calculate_treatment_effect(
        self,
        outcome_var: str = 'sales'
    ) -> Dict:
        if self.matched_data is None:
            raise ValueError("请先进行匹配")
        
        treated = self.matched_data[self.matched_data['is_treated'] == True]
        control = self.matched_data[self.matched_data['is_treated'] == False]
        
        treated_mean = np.average(treated[outcome_var], weights=treated['weight'])
        control_mean = np.average(control[outcome_var], weights=control['weight'])
        
        att_absolute = treated_mean - control_mean
        att_pct = (att_absolute / control_mean) * 100 if control_mean > 0 else 0
        
        t_stat, p_value = stats.ttest_ind(
            treated[outcome_var],
            control[outcome_var],
            equal_var=False
        )
        
        self.att = att_pct
        self.treatment_effect = att_pct
        
        return {
            'att_pct': att_pct,
            'att_absolute': att_absolute,
            'treated_mean': treated_mean,
            'control_mean': control_mean,
            'p_value': p_value,
            'n_treated': len(treated),
            'n_control': len(control),
            'is_significant': p_value < 0.05
        }
    
    def balance_check(
        self,
        df: pd.DataFrame,
        covariates: List[str],
        treatment_var: str = 'is_treated'
    ) -> pd.DataFrame:
        balance_stats = []
        
        for cov in covariates:
            if cov not in df.columns:
                continue
                
            treated = df[df[treatment_var] == True][cov]
            control = df[df[treatment_var] == False][cov]
            
            mean_treated = treated.mean()
            mean_control = control.mean()
            
            std_treated = treated.std()
            std_control = control.std()
            
            pooled_std = np.sqrt((std_treated ** 2 + std_control ** 2) / 2)
            std_diff = (mean_treated - mean_control) / pooled_std if pooled_std > 0 else 0
            
            t_stat, p_value = stats.ttest_ind(treated, control, equal_var=False)
            
            balance_stats.append({
                'covariate': cov,
                'mean_treated': mean_treated,
                'mean_control': mean_control,
                'std_diff': std_diff,
                'p_value': p_value,
                'balanced': abs(std_diff) < 0.1
            })
        
        return pd.DataFrame(balance_stats)
    
    def plot_propensity_score_distribution(
        self,
        df: pd.DataFrame,
        treatment_var: str = 'is_treated',
        ps_col: str = 'propensity_score',
        figsize: Tuple[int, int] = (10, 6)
    ) -> plt.Figure:
        fig, ax = plt.subplots(figsize=figsize)
        
        treated = df[df[treatment_var] == True]
        control = df[df[treatment_var] == False]
        
        sns.kdeplot(
            data=treated, x=ps_col, ax=ax,
            label='处理组', fill=True, alpha=0.5,
            color='#e74c3c', linewidth=2
        )
        sns.kdeplot(
            data=control, x=ps_col, ax=ax,
            label='控制组', fill=True, alpha=0.5,
            color='#3498db', linewidth=2
        )
        
        ax.set_xlabel('倾向性得分', fontsize=12)
        ax.set_ylabel('密度', fontsize=12)
        ax.set_title('倾向性得分分布图', fontsize=14, fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        return fig
    
    def plot_balance_check(
        self,
        balance_df: pd.DataFrame,
        figsize: Tuple[int, int] = (10, 8)
    ) -> plt.Figure:
        fig, ax = plt.subplots(figsize=figsize)
        
        balance_df = balance_df.sort_values('std_diff', ascending=True)
        
        y_pos = np.arange(len(balance_df))
        
        colors = ['#2ecc71' if b else '#e74c3c' for b in balance_df['balanced']]
        
        ax.barh(y_pos, balance_df['std_diff'], color=colors, alpha=0.7)
        
        ax.axvline(x=-0.1, color='gray', linestyle='--', alpha=0.5)
        ax.axvline(x=0.1, color='gray', linestyle='--', alpha=0.5)
        ax.axvline(x=0, color='black', linestyle='-', alpha=0.3)
        
        ax.set_yticks(y_pos)
        ax.set_yticklabels(balance_df['covariate'])
        ax.set_xlabel('标准化均值差异', fontsize=12)
        ax.set_title('协变量平衡性检验', fontsize=14, fontweight='bold')
        
        ax.legend(['平衡阈值 (±0.1)', '平衡阈值 (±0.1)'], loc='lower right')
        
        plt.tight_layout()
        return fig
    
    def plot_treatment_effect(
        self,
        effect_results: Dict,
        figsize: Tuple[int, int] = (8, 6)
    ) -> plt.Figure:
        fig, ax = plt.subplots(figsize=figsize)
        
        categories = ['控制组', '处理组']
        means = [effect_results['control_mean'], effect_results['treated_mean']]
        colors = ['#3498db', '#e74c3c']
        
        bars = ax.bar(categories, means, color=colors, alpha=0.7)
        
        for bar, mean_val in zip(bars, means):
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                height + max(means) * 0.01,
                f'{mean_val:,.0f}',
                ha='center',
                va='bottom',
                fontsize=12,
                fontweight='bold'
            )
        
        ax.set_ylabel('平均销售额', fontsize=12)
        ax.set_title('匹配后处理效应对比', fontsize=14, fontweight='bold')
        
        effect_pct = effect_results['att_pct']
        ax.text(
            0.5,
            max(means) * 0.9,
            f'处理效应: {effect_pct:.2f}%',
            ha='center',
            fontsize=14,
            fontweight='bold',
            color='green' if effect_pct > 0 else 'red',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.3)
        )
        
        plt.tight_layout()
        return fig
    
    def get_summary(self, effect_results: Dict = None) -> str:
        summary_text = """
        ========================================
        倾向性得分匹配 (PSM) 结果摘要
        ========================================
        """
        
        if self.matched_data is not None:
            summary_text += f"""
        匹配结果:
        - 匹配后处理组样本数: {effect_results['n_treated']}
        - 匹配后控制组样本数: {effect_results['n_control']}
            """
        
        if effect_results:
            summary_text += f"""
        因果效应估计 (ATT):
        - 销售提升率: {effect_results['att_pct']:.2f}%
        - 绝对提升额: {effect_results['att_absolute']:,.2f}
        - p值: {effect_results['p_value']:.4f}
        - 统计显著性: {'显著 (p<0.05)' if effect_results['is_significant'] else '不显著'}
            """
        
        return summary_text
