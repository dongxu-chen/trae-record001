import numpy as np
import pandas as pd
from scipy import stats
from scipy.stats import ttest_ind, chi2_contingency, mannwhitneyu, beta
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
import warnings
warnings.filterwarnings('ignore')


@dataclass
class ABTestResult:
    variant_a_name: str
    variant_b_name: str
    metric: str
    mean_a: float
    mean_b: float
    delta: float
    delta_percent: float
    p_value: float
    confidence_interval: Tuple[float, float]
    is_significant: bool
    effect_size: float
    power: float
    sample_size_a: int
    sample_size_b: int
    test_type: str
    recommendation: str
    details: Dict[str, Any] = field(default_factory=dict)
    
    def __str__(self):
        sig_str = "✅ 显著" if self.is_significant else "❌ 不显著"
        return (f"[{self.metric}] A/B测试结果\n"
                f"  {self.variant_a_name}: {self.mean_a:.4f}\n"
                f"  {self.variant_b_name}: {self.mean_b:.4f}\n"
                f"  差异: {self.delta:+.4f} ({self.delta_percent:+.2f}%)\n"
                f"  P值: {self.p_value:.4f} | {sig_str}\n"
                f"  95%置信区间: [{self.confidence_interval[0]:.4f}, {self.confidence_interval[1]:.4f}]\n"
                f"  效应量: {self.effect_size:.4f} | 统计功效: {self.power:.2f}\n"
                f"  建议: {self.recommendation}")


class ABTestAnalyzer:
    def __init__(self, alpha: float = 0.05):
        self.alpha = alpha
    
    def _calculate_cohens_d(self, group_a: np.ndarray, group_b: np.ndarray) -> float:
        n_a, n_b = len(group_a), len(group_b)
        var_a, var_b = np.var(group_a, ddof=1), np.var(group_b, ddof=1)
        pooled_std = np.sqrt(((n_a - 1) * var_a + (n_b - 1) * var_b) / (n_a + n_b - 2))
        return (np.mean(group_b) - np.mean(group_a)) / pooled_std
    
    def _calculate_power(self, effect_size: float, n_a: int, n_b: int) -> float:
        from math import sqrt
        from scipy.stats import norm
        
        n = (n_a * n_b) / (n_a + n_b)
        delta = effect_size * sqrt(n)
        z_alpha = norm.ppf(1 - self.alpha / 2)
        power = 1 - norm.cdf(z_alpha - delta) + norm.cdf(-z_alpha - delta)
        return power
    
    def _calculate_confidence_interval(self, group_a: np.ndarray, 
                                  group_b: np.ndarray) -> Tuple[float, float]:
        mean_a, mean_b = np.mean(group_a), np.mean(group_b)
        n_a, n_b = len(group_a), len(group_b)
        var_a, var_b = np.var(group_a, ddof=1), np.var(group_b, ddof=1)
        
        se = np.sqrt(var_a / n_a + var_b / n_b)
        df = min(n_a, n_b) - 1
        t_critical = stats.t.ppf(1 - self.alpha / 2, df)
        
        diff = mean_b - mean_a
        margin = t_critical * se
        
        return (diff - margin, diff + margin)
    
    def test_continuous(self, data_a: np.ndarray, data_b: np.ndarray,
                      metric_name: str,
                      variant_a_name: str = "对照组",
                      variant_b_name: str = "测试组",
                      test_type: str = 'auto') -> ABTestResult:
        data_a = np.asarray(data_a)
        data_b = np.asarray(data_b)
        
        mean_a = np.mean(data_a)
        mean_b = np.mean(data_b)
        n_a, n_b = len(data_a), len(data_b)
        
        delta = mean_b - mean_a
        delta_percent = (delta / mean_a * 100) if mean_a != 0 else 0
        
        if test_type == 'auto':
            stat, p_normal_a = stats.shapiro(data_a)
            stat, p_normal_b = stats.shapiro(data_b)
            if p_normal_a > 0.05 and p_normal_b > 0.05:
                test_type = 't-test'
            else:
                test_type = 'mann-whitney'
        
        if test_type == 't-test':
            stat, p_value = ttest_ind(data_a, data_b, equal_var=False)
        elif test_type == 'mann-whitney':
            stat, p_value = mannwhitneyu(data_a, data_b, alternative='two-sided')
        else:
            raise ValueError(f"未知检验类型: {test_type}")
        
        ci = self._calculate_confidence_interval(data_a, data_b)
        effect_size = self._calculate_cohens_d(data_a, data_b)
        power = self._calculate_power(effect_size, n_a, n_b)
        
        is_significant = p_value < self.alpha
        
        if is_significant:
            if delta > 0:
                recommendation = f"测试组表现显著优于对照组，建议上线测试组方案"
            else:
                recommendation = f"对照组表现显著优于测试组，建议保留对照组方案"
        else:
            if power < 0.8:
                recommendation = "样本量不足，建议增加样本量后再测试"
            else:
                recommendation = "两组无显著差异，可继续观察或调整方案"
        
        return ABTestResult(
            variant_a_name=variant_a_name,
            variant_b_name=variant_b_name,
            metric=metric_name,
            mean_a=mean_a,
            mean_b=mean_b,
            delta=delta,
            delta_percent=delta_percent,
            p_value=p_value,
            confidence_interval=ci,
            is_significant=is_significant,
            effect_size=effect_size,
            power=power,
            sample_size_a=n_a,
            sample_size_b=n_b,
            test_type=test_type,
            recommendation=recommendation,
            details={
                'test_statistic': stat,
                'shapiro_p_a': stats.shapiro(data_a)[1] if test_type == 't-test' else None,
                'shapiro_p_b': stats.shapiro(data_b)[1] if test_type == 't-test' else None,
            }
        )
    
    def test_proportion(self, successes_a: int, trials_a: int,
                       successes_b: int, trials_b: int,
                       metric_name: str,
                       variant_a_name: str = "对照组",
                       variant_b_name: str = "测试组") -> ABTestResult:
        rate_a = successes_a / trials_a
        rate_b = successes_b / trials_b
        delta = rate_b - rate_a
        delta_percent = (delta / rate_a * 100) if rate_a != 0 else 0
        
        table = [[successes_a, trials_a - successes_a],
                 [successes_b, trials_b - successes_b]]
        chi2, p_value, dof, expected = chi2_contingency(table)
        
        pooled_p = (successes_a + successes_b) / (trials_a + trials_b)
        se = np.sqrt(pooled_p * (1 - pooled_p) * (1/trials_a + 1/trials_b))
        z_critical = stats.norm.ppf(1 - self.alpha / 2)
        ci = (delta - z_critical * se, delta + z_critical * se)
        
        effect_size = np.sqrt(chi2 / (trials_a + trials_b))
        power = self._calculate_power(effect_size, trials_a, trials_b)
        
        is_significant = p_value < self.alpha
        
        if is_significant:
            if delta > 0:
                recommendation = f"测试组表现显著优于对照组，建议上线测试组方案"
            else:
                recommendation = f"对照组表现显著优于测试组，建议保留对照组方案"
        else:
            if power < 0.8:
                recommendation = "样本量不足，建议增加样本量后再测试"
            else:
                recommendation = "两组无显著差异，可继续观察或调整方案"
        
        return ABTestResult(
            variant_a_name=variant_a_name,
            variant_b_name=variant_b_name,
            metric=metric_name,
            mean_a=rate_a,
            mean_b=rate_b,
            delta=delta,
            delta_percent=delta_percent,
            p_value=p_value,
            confidence_interval=ci,
            is_significant=is_significant,
            effect_size=effect_size,
            power=power,
            sample_size_a=trials_a,
            sample_size_b=trials_b,
            test_type='chi-square',
            recommendation=recommendation,
            details={
                'chi2_statistic': chi2,
                'expected_frequency': expected,
            }
        )
    
    def test_multiple_metrics(self, metrics_config: List[Dict[str, Any]]) -> List[ABTestResult]:
        results = []
        for config in metrics_config:
            if config['type'] == 'continuous':
                result = self.test_continuous(
                    data_a=config['data_a'],
                    data_b=config['data_b'],
                    metric_name=config['metric'],
                    variant_a_name=config.get('variant_a', '对照组'),
                    variant_b_name=config.get('variant_b', '测试组'),
                    test_type=config.get('test_type', 'auto')
                )
            elif config['type'] == 'proportion':
                result = self.test_proportion(
                    successes_a=config['successes_a'],
                    trials_a=config['trials_a'],
                    successes_b=config['successes_b'],
                    trials_b=config['trials_b'],
                    metric_name=config['metric'],
                    variant_a_name=config.get('variant_a', '对照组'),
                    variant_b_name=config.get('variant_b', '测试组'))
            else:
                continue
            results.append(result)
        return results
    
    def get_bayesian_analysis(self, successes_a: int, trials_a: int,
                                successes_b: int, trials_b: int,
                                prior_alpha: int = 1, prior_beta: int = 1) -> Dict[str, Any]:
        posterior_a = beta(prior_alpha + successes_a, prior_beta + trials_a - successes_a)
        posterior_b = beta(prior_alpha + successes_b, prior_beta + trials_b - successes_b)
        
        n_samples = 100000
        samples_a = posterior_a.rvs(n_samples)
        samples_b = posterior_b.rvs(n_samples)
        
        prob_b_better = np.mean(samples_b > samples_a)
        
        loss_a = np.maximum(0, samples_a - samples_b)
        expected_loss = np.mean(loss_a)
        
        return {
            'prob_b_better': prob_b_better,
            'expected_loss': expected_loss,
            'mean_a': posterior_a.mean(),
            'mean_b': posterior_b.mean(),
            'ci_a': (posterior_a.ppf(0.025), posterior_a.ppf(0.975)),
            'ci_b': (posterior_b.ppf(0.025), posterior_b.ppf(0.975)),
            'samples_a': samples_a,
            'samples_b': samples_b,
        }
    
    def calculate_required_sample_size(self, baseline_rate: float,
                                min_effect: float,
                                power: float = 0.8,
                                ratio: float = 1.0) -> Dict[str, int]:
        from math import sqrt
        from scipy.stats import norm
        
        p1 = baseline_rate
        p2 = baseline_rate * (1 + min_effect)
        
        z_alpha = norm.ppf(1 - self.alpha / 2)
        z_beta = norm.ppf(power)
        
        n = (z_alpha + z_beta) ** 2 * (p1 * (1 - p1) + p2 * (1 - p2)) / (p1 - p2) ** 2
        
        n_a = int(np.ceil(n))
        n_b = int(np.ceil(n * ratio))
        
        return {
            'group_a': n_a,
            'group_b': n_b,
            'total': n_a + n_b
        }


def simulate_ab_test_from_levels(df_players: pd.DataFrame,
                        level_id_a: str,
                        level_id_b: str,
                        analyzer: Optional[ABTestAnalyzer] = None) -> List[ABTestResult]:
    if analyzer is None:
        analyzer = ABTestAnalyzer()
    
    df_a = df_players[df_players['level_id'] == level_id_a].copy()
    df_b = df_players[df_players['level_id'] == level_id_b].copy()
    
    if len(df_a) == 0 or len(df_b) == 0:
        raise ValueError("找不到指定的关卡数据")
    
    metrics_config = [
        {
            'type': 'proportion',
            'metric': '通关率',
            'successes_a': df_a['completed'].sum(),
            'trials_a': len(df_a),
            'successes_b': df_b['completed'].sum(),
            'trials_b': len(df_b),
            'variant_a': level_id_a,
            'variant_b': level_id_b,
        },
        {
            'type': 'continuous',
            'metric': '尝试次数',
            'data_a': df_a['attempts'].values,
            'data_b': df_b['attempts'].values,
            'variant_a': level_id_a,
            'variant_b': level_id_b,
        }
    ]
    
    df_a_completed = df_a[df_a['completed']].copy()
    df_b_completed = df_b[df_b['completed']].copy()
    
    if len(df_a_completed) > 0 and len(df_b_completed) > 0:
        metrics_config.append({
            'type': 'continuous',
            'metric': '通关时间',
            'data_a': df_a_completed['completion_time'].dropna().values,
            'data_b': df_b_completed['completion_time'].dropna().values,
            'variant_a': level_id_a,
            'variant_b': level_id_b,
        })
    
    results = analyzer.test_multiple_metrics(metrics_config)
    
    return results


def generate_ab_test_report(results: List[ABTestResult]) -> pd.DataFrame:
    report_data = []
    for result in results:
        report_data.append({
            '指标': result.metric,
            '对照组均值': result.mean_a,
            '测试组均值': result.mean_b,
            '绝对差异': result.delta,
            '相对差异(%)': result.delta_percent,
            'P值': result.p_value,
            '显著性': '显著' if result.is_significant else '不显著',
            '效应量': result.effect_size,
            '统计功效': result.power,
            '建议': result.recommendation,
        })
    
    return pd.DataFrame(report_data)


if __name__ == "__main__":
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    
    from src.features.data_generator import generate_full_dataset
    
    print("生成数据...")
    df_levels, df_players = generate_full_dataset(n_levels=50, n_players=500)
    
    print("\n=== A/B测试分析 ===")
    analyzer = ABTestAnalyzer(alpha=0.05)
    
    level_a = 'Level_001'
    level_b = 'Level_010'
    
    print(f"\n比较 {level_a} vs {level_b}:")
    results = simulate_ab_test_from_levels(df_players, level_a, level_b, analyzer)
    
    for result in results:
        print(f"\n{result}")
    
    print("\n=== 结果报告:")
    report_df = generate_ab_test_report(results)
    print(report_df.to_string(index=False))
    
    print("\n=== 样本量计算示例:")
    sample_size = analyzer.calculate_required_sample_size(
        baseline_rate=0.6,
        min_effect=0.1,
        power=0.8
    )
    print(f"所需样本量: A组 {sample_size['group_a']}, B组 {sample_size['group_b']}")
    
    print("\n=== 贝叶斯分析示例:")
    df_a = df_players[df_players['level_id'] == level_a]
    df_b = df_players[df_players['level_id'] == level_b]
    
    bayes_result = analyzer.get_bayesian_analysis(
        successes_a=df_a['completed'].sum(),
        trials_a=len(df_a),
        successes_b=df_b['completed'].sum(),
        trials_b=len(df_b)
    )
    
    print(f"B组优于A组的概率: {bayes_result['prob_b_better']:.2%}")
    print(f"预期损失: {bayes_result['expected_loss']:.4f}")
