import pandas as pd
import numpy as np
from scipy import stats


class SensitivityAnalyzer:
    def __init__(self, df, treatment_col, outcome_col, covariates, estimate, se):
        self.df = df.copy()
        self.treatment_col = treatment_col
        self.outcome_col = outcome_col
        self.covariates = covariates
        self.estimate = estimate
        self.se = se
        self.z_stat = estimate / se if se > 0 else 0

    def calculate_e_value(self):
        if self.estimate == 0:
            return {'e_value': 1.0, 'lower_ci_e_value': 1.0}
        
        rr = np.exp(self.estimate)
        lower_bound = np.exp(self.estimate - 1.96 * self.se)
        
        def e_value_formula(rr_val):
            if rr_val >= 1:
                return rr_val + np.sqrt(rr_val * (rr_val - 1))
            else:
                rr_inv = 1 / rr_val
                return rr_inv + np.sqrt(rr_inv * (rr_inv - 1))
        
        e_value = e_value_formula(rr)
        lower_ci_e_value = e_value_formula(lower_bound)
        
        if lower_bound > 1:
            lower_ci_e_value = lower_ci_e_value
        else:
            lower_ci_e_value = 1.0
        
        return {
            'e_value': float(e_value),
            'lower_ci_e_value': float(lower_ci_e_value),
            'risk_ratio': float(rr),
            'lower_bound_rr': float(lower_bound),
            'interpretation': f"未观测混杂需要使关联强度达到{e_value:.2f}倍以上才能推翻结论"
        }

    def rosenbaum_bounds(self, gamma_values=[1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0]):
        results = []
        
        for gamma in gamma_values:
            p_upper = gamma / (1 + gamma)
            p_lower = 1 / (1 + gamma)
            
            z_upper = self.z_stat - np.sqrt(2 * np.log(gamma))
            z_lower = self.z_stat + np.sqrt(2 * np.log(gamma))
            
            p_upper_tail = 1 - stats.norm.cdf(z_upper)
            p_lower_tail = 1 - stats.norm.cdf(z_lower)
            
            sig_upper = p_upper_tail < 0.05
            sig_lower = p_lower_tail < 0.05
            
            results.append({
                'gamma': float(gamma),
                'p_upper': float(p_upper),
                'p_lower': float(p_lower),
                'z_upper': float(z_upper),
                'z_lower': float(z_lower),
                'p_value_upper': float(p_upper_tail),
                'p_value_lower': float(p_lower_tail),
                'significant_upper': bool(sig_upper),
                'significant_lower': bool(sig_lower),
                'range': [float(p_lower_tail), float(p_upper_tail)]
            })
        
        critical_gamma = 1.0
        for res in results:
            if not res['significant_upper']:
                critical_gamma = res['gamma']
                break
        
        if all(r['significant_upper'] for r in results):
            critical_gamma = gamma_values[-1]
        
        return {
            'bounds': results,
            'critical_gamma': float(critical_gamma),
            'interpretation': f"当Γ > {critical_gamma:.2f}时，结论可能被未观测混杂推翻"
        }

    def omitted_variable_bias(self, r_yz=0.3, r_xz=0.3):
        delta = self.estimate * (r_yz * r_xz) / (1 - r_xz**2)
        adjusted_estimate = self.estimate - delta
        adjusted_se = self.se * np.sqrt(1 - r_yz**2 * (1 - r_xz**2))
        
        z_stat_adj = adjusted_estimate / adjusted_se if adjusted_se > 0 else 0
        p_value_adj = 2 * (1 - stats.norm.cdf(abs(z_stat_adj)))
        
        return {
            'assumed_correlation_with_outcome': r_yz,
            'assumed_correlation_with_treatment': r_xz,
            'bias_magnitude': float(delta),
            'adjusted_estimate': float(adjusted_estimate),
            'adjusted_se': float(adjusted_se),
            'adjusted_p_value': float(p_value_adj),
            'still_significant': p_value_adj < 0.05
        }

    def calculate_convergence_correlation(self):
        abs_z = abs(self.z_stat)
        
        if abs_z < 1.96:
            r_crit = 0.0
        else:
            r_crit = (abs_z - 1.96) / abs_z
        
        return {
            'critical_correlation': float(r_crit),
            'z_statistic': float(self.z_stat),
            'interpretation': f"未观测变量需要与处理和结果的相关系数乘积达到{r_crit:.3f}才能推翻结论"
        }

    def run_all_analysis(self):
        e_value = self.calculate_e_value()
        rosenbaum = self.rosenbaum_bounds()
        convergence = self.calculate_convergence_correlation()
        
        omv_scenarios = []
        for r_yz, r_xz in [(0.1, 0.1), (0.2, 0.2), (0.3, 0.3), (0.4, 0.4), (0.5, 0.5)]:
            omv_scenarios.append(self.omitted_variable_bias(r_yz, r_xz))
        
        return {
            'e_value': e_value,
            'rosenbaum_bounds': rosenbaum,
            'convergence_correlation': convergence,
            'omitted_variable_scenarios': omv_scenarios,
            'robustness_summary': {
                'e_value_gt_2': e_value['e_value'] > 2,
                'critical_gamma_gt_1_5': rosenbaum['critical_gamma'] > 1.5,
                'overall_robustness': 'high' if e_value['e_value'] > 2 and rosenbaum['critical_gamma'] > 1.5 
                else 'medium' if e_value['e_value'] > 1.5 or rosenbaum['critical_gamma'] > 1.25
                else 'low'
            }
        }
