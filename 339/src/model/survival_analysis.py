import os
import sys
import time
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from lifelines import KaplanMeierFitter
    from lifelines.statistics import logrank_test, multivariate_logrank_test
    LIFELINES_AVAILABLE = True
except ImportError:
    LIFELINES_AVAILABLE = False

try:
    import numpy as np
    import pandas as pd
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

from common.logger import get_logger
from common.utils import load_config, safe_divide

logger = get_logger("SurvivalAnalysis")


@dataclass
class SurvivalCurveData:
    group_name: str
    time_points: List[float]
    survival_probabilities: List[float]
    confidence_lower: List[float]
    confidence_upper: List[float]
    median_survival: float
    num_samples: int
    num_events: int
    censored_count: int


@dataclass
class LogRankResult:
    group_pair: Tuple[str, str]
    test_statistic: float
    p_value: float
    significant: bool
    hazard_ratio: float
    ci_lower: float
    ci_upper: float


class SurvivalCurveComparator:
    def __init__(self, cache_manager=None):
        self.config = load_config()
        self.cache = cache_manager
        self.km_fitters: Dict[str, KaplanMeierFitter] = {}
        self.curve_data: Dict[str, SurvivalCurveData] = {}
        self.comparison_results: Dict[str, Any] = {}
        
        self.group_columns = [
            "user_level",
            "region",
            "channel",
            "risk_segment",
            "engagement_tier"
        ]
        
        self.significance_threshold = self.config.get("analysis", {}).get(
            "significance_threshold", 0.05
        )
        
        logger.info("SurvivalCurveComparator initialized")

    def fit_curves(self, df: pd.DataFrame, 
                   group_columns: Optional[List[str]] = None,
                   duration_col: str = "duration",
                   event_col: str = "event") -> Dict[str, Any]:
        if not LIFELINES_AVAILABLE:
            return {"error": "lifelines library not available"}
        
        if not NUMPY_AVAILABLE:
            return {"error": "numpy/pandas not available"}
        
        group_columns = group_columns or self.group_columns
        results = {
            "curves": {},
            "comparisons": {},
            "summary": {}
        }
        
        for group_col in group_columns:
            if group_col not in df.columns:
                continue
            
            groups = df[group_col].unique()
            if len(groups) < 2:
                continue
            
            logger.info(f"Fitting survival curves by {group_col}: {len(groups)} groups")
            
            curves_by_group = {}
            for group_val in groups:
                group_df = df[df[group_col] == group_val]
                if len(group_df) < 10:
                    continue
                
                kmf = KaplanMeierFitter()
                kmf.fit(group_df[duration_col], group_df[event_col], 
                        label=f"{group_col}_{group_val}")
                
                curve_key = f"{group_col}_{group_val}"
                self.km_fitters[curve_key] = kmf
                
                times = kmf.survival_function_.index.tolist()
                surv_probs = kmf.survival_function_.values.flatten().tolist()
                ci_lower = kmf.confidence_interval_.iloc[:, 0].tolist()
                ci_upper = kmf.confidence_interval_.iloc[:, 1].tolist()
                
                median_surv = float(kmf.median_survival_time_) if not np.isinf(kmf.median_survival_time_) else max(times)
                
                curve_data = SurvivalCurveData(
                    group_name=str(group_val),
                    time_points=times,
                    survival_probabilities=surv_probs,
                    confidence_lower=ci_lower,
                    confidence_upper=ci_upper,
                    median_survival=median_surv,
                    num_samples=len(group_df),
                    num_events=int(group_df[event_col].sum()),
                    censored_count=len(group_df) - int(group_df[event_col].sum())
                )
                
                self.curve_data[curve_key] = curve_data
                curves_by_group[str(group_val)] = self._curve_to_dict(curve_data)
            
            if len(curves_by_group) >= 2:
                group_list = list(curves_by_group.keys())
                pairwise_results = []
                
                for i in range(len(group_list)):
                    for j in range(i + 1, len(group_list)):
                        g1, g2 = group_list[i], group_list[j]
                        
                        df1 = df[df[group_col].astype(str) == g1]
                        df2 = df[df[group_col].astype(str) == g2]
                        
                        try:
                            result = logrank_test(
                                df1[duration_col], df2[duration_col],
                                df1[event_col], df2[event_col]
                            )
                            
                            hr = safe_divide(
                                (df1[event_col].sum() / df1[duration_col].mean()),
                                (df2[event_col].sum() / df2[duration_col].mean()),
                                1.0
                            )
                            
                            logrank_result = LogRankResult(
                                group_pair=(g1, g2),
                                test_statistic=float(result.test_statistic),
                                p_value=float(result.p_value),
                                significant=result.p_value < self.significance_threshold,
                                hazard_ratio=float(hr),
                                ci_lower=float(hr * 0.7),
                                ci_upper=float(hr * 1.3)
                            )
                            
                            pairwise_results.append({
                                "groups": [g1, g2],
                                "test_statistic": logrank_result.test_statistic,
                                "p_value": logrank_result.p_value,
                                "significant": logrank_result.significant,
                                "hazard_ratio": logrank_result.hazard_ratio,
                                "interpretation": self._interpret_logrank(logrank_result)
                            })
                        except Exception as e:
                            logger.warning(f"Log-rank test failed for {g1} vs {g2}: {e}")
                
                try:
                    multi_result = multivariate_logrank_test(
                        df[duration_col], df[group_col].astype(str), df[event_col]
                    )
                    overall_p = float(multi_result.p_value)
                except Exception as e:
                    logger.warning(f"Multivariate log-rank failed: {e}")
                    overall_p = None
                
                results["comparisons"][group_col] = {
                    "pairwise": pairwise_results,
                    "overall_p_value": overall_p,
                    "overall_significant": overall_p is not None and overall_p < self.significance_threshold
                }
                
                results["curves"][group_col] = curves_by_group
                
                results["summary"][group_col] = {
                    "num_groups": len(curves_by_group),
                    "total_samples": sum(c["num_samples"] for c in curves_by_group.values()),
                    "total_events": sum(c["num_events"] for c in curves_by_group.values()),
                    "best_performing": self._find_best_group(curves_by_group),
                    "worst_performing": self._find_worst_group(curves_by_group)
                }
        
        self.comparison_results = results
        return results

    def compare_by_user_level(self, df: pd.DataFrame) -> Dict[str, Any]:
        return self.fit_curves(df, group_columns=["user_level"])

    def compare_by_treatment(self, df: pd.DataFrame, 
                            treatment_col: str = "treatment_group") -> Dict[str, Any]:
        return self.fit_curves(df, group_columns=[treatment_col])

    def generate_comparison_report(self) -> Dict[str, Any]:
        report = {
            "timestamp": datetime.now().isoformat(),
            "significance_threshold": self.significance_threshold,
            "group_analyses": {},
            "key_insights": []
        }
        
        for group_col, comp_data in self.comparison_results.get("comparisons", {}).items():
            curves = self.comparison_results.get("curves", {}).get(group_col, {})
            summary = self.comparison_results.get("summary", {}).get(group_col, {})
            
            group_analysis = {
                "summary": summary,
                "curves": curves,
                "significant_differences": [
                    p for p in comp_data.get("pairwise", []) if p["significant"]
                ],
                "overall_test": {
                    "p_value": comp_data.get("overall_p_value"),
                    "significant": comp_data.get("overall_significant")
                }
            }
            
            report["group_analyses"][group_col] = group_analysis
            
            if comp_data.get("overall_significant"):
                report["key_insights"].append(
                    f"{group_col} groups have statistically significant survival differences "
                    f"(p={comp_data.get('overall_p_value', 0):.4f})"
                )
            
            if summary.get("best_performing") and summary.get("worst_performing"):
                best = summary["best_performing"]
                worst = summary["worst_performing"]
                best_median = curves[best]["median_survival"]
                worst_median = curves[worst]["median_survival"]
                
                if best_median > worst_median:
                    improvement = safe_divide(best_median - worst_median, worst_median, 0) * 100
                    report["key_insights"].append(
                        f"Best group '{best}' has {improvement:.1f}% longer median survival "
                        f"than worst group '{worst}' ({best_median:.1f} vs {worst_median:.1f} days)"
                    )
        
        return report

    def get_curve_at_time(self, group_key: str, time_days: float) -> Optional[Dict[str, float]]:
        if group_key not in self.curve_data:
            return None
        
        curve = self.curve_data[group_key]
        times = np.array(curve.time_points)
        probs = np.array(curve.survival_probabilities)
        
        idx = np.searchsorted(times, time_days)
        if idx >= len(probs):
            surv_prob = float(probs[-1])
        elif idx == 0:
            surv_prob = float(probs[0])
        else:
            t0, t1 = times[idx-1], times[idx]
            p0, p1 = probs[idx-1], probs[idx]
            if t1 == t0:
                surv_prob = float(p1)
            else:
                frac = (time_days - t0) / (t1 - t0)
                surv_prob = float(p0 + frac * (p1 - p0))
        
        return {
            "survival_probability": surv_prob,
            "churn_probability": 1 - surv_prob,
            "time_days": time_days
        }

    def _curve_to_dict(self, curve: SurvivalCurveData) -> Dict[str, Any]:
        times = np.array(curve.time_points)
        probs = np.array(curve.survival_probabilities)
        
        def get_surv_at(target_days):
            if len(times) == 0:
                return None
            idx = np.searchsorted(times, target_days)
            if idx >= len(probs):
                return float(probs[-1])
            elif idx == 0:
                return float(probs[0])
            t0, t1 = times[idx-1], times[idx]
            p0, p1 = probs[idx-1], probs[idx]
            if t1 == t0:
                return float(p1)
            frac = (target_days - t0) / (t1 - t0)
            return float(p0 + frac * (p1 - p0))
        
        return {
            "group_name": curve.group_name,
            "median_survival": curve.median_survival,
            "num_samples": curve.num_samples,
            "num_events": curve.num_events,
            "censored_count": curve.censored_count,
            "time_points": curve.time_points,
            "survival_probabilities": curve.survival_probabilities,
            "confidence_lower": curve.confidence_lower,
            "confidence_upper": curve.confidence_upper,
            "survival_at_7d": get_surv_at(7),
            "survival_at_30d": get_surv_at(30),
            "survival_at_90d": get_surv_at(90)
        }

    def _find_best_group(self, curves: Dict[str, Dict]) -> Optional[str]:
        if not curves:
            return None
        return max(curves.items(), key=lambda x: x[1]["median_survival"])[0]

    def _find_worst_group(self, curves: Dict[str, Dict]) -> Optional[str]:
        if not curves:
            return None
        return min(curves.items(), key=lambda x: x[1]["median_survival"])[0]

    def _interpret_logrank(self, result: LogRankResult) -> str:
        if not result.significant:
            return f"No significant difference between {result.group_pair[0]} and {result.group_pair[1]}"
        
        direction = "higher" if result.hazard_ratio > 1 else "lower"
        return (
            f"{result.group_pair[0]} has {direction} churn risk than {result.group_pair[1]} "
            f"(HR={result.hazard_ratio:.2f}, p={result.p_value:.4f})"
        )


def main():
    if not LIFELINES_AVAILABLE:
        print("Lifelines not available. Cannot run survival analysis demo.")
        return
    
    print("=" * 70)
    print("SURVIVAL CURVE COMPARISON ANALYSIS")
    print("=" * 70)
    
    comparator = SurvivalCurveComparator()
    
    print("\n" + "-" * 70)
    print("Generating synthetic survival data...")
    print("-" * 70)
    
    np.random.seed(42)
    n_users = 500
    
    user_levels = ["new", "bronze", "silver", "gold", "platinum"]
    regions = ["north", "south", "east", "west"]
    channels = ["organic", "paid", "referral"]
    
    data = []
    for i in range(n_users):
        level = np.random.choice(user_levels, p=[0.25, 0.25, 0.25, 0.15, 0.1])
        
        base_duration = {
            "new": 30, "bronze": 45, "silver": 60, "gold": 90, "platinum": 120
        }[level]
        
        duration = max(1, int(np.random.normal(base_duration, base_duration * 0.3)))
        event = np.random.random() < 0.4 if level in ["new", "bronze"] else np.random.random() < 0.25
        
        data.append({
            "user_id": f"user_{i:04d}",
            "user_level": level,
            "region": np.random.choice(regions),
            "channel": np.random.choice(channels),
            "duration": duration,
            "event": int(event)
        })
    
    df = pd.DataFrame(data)
    print(f"Generated {len(df)} samples")
    
    print("\n" + "-" * 70)
    print("Fitting Kaplan-Meier curves by user level...")
    print("-" * 70)
    
    results = comparator.fit_curves(df, group_columns=["user_level", "channel"])
    
    print("\n" + "-" * 70)
    print("SUMMARY BY USER LEVEL")
    print("-" * 70)
    
    curves_by_level = results.get("curves", {}).get("user_level", {})
    for group_name, curve in sorted(curves_by_level.items()):
        print(f"\n  {group_name.upper()}:")
        print(f"    Samples: {curve['num_samples']}, Events: {curve['num_events']}")
        print(f"    Median Survival: {curve['median_survival']:.1f} days")
        print(f"    30-day Survival: {curve.get('survival_at_30d', 0)*100:.1f}%")
        print(f"    90-day Survival: {curve.get('survival_at_90d', 0)*100:.1f}%")
    
    print("\n" + "-" * 70)
    print("STATISTICAL COMPARISONS (LOG-RANK TESTS)")
    print("-" * 70)
    
    comp = results.get("comparisons", {}).get("user_level", {})
    for pair in comp.get("pairwise", []):
        sig_marker = "*" if pair["significant"] else " "
        print(f"\n  {sig_marker} {pair['groups'][0]} vs {pair['groups'][1]}:")
        print(f"    p-value: {pair['p_value']:.4f}")
        print(f"    Hazard Ratio: {pair['hazard_ratio']:.2f}")
        print(f"    Interpretation: {pair['interpretation']}")
    
    print("\n" + "-" * 70)
    print("GENERATED REPORT")
    print("-" * 70)
    
    report = comparator.generate_comparison_report()
    print(f"\nKey Insights:")
    for insight in report["key_insights"]:
        print(f"  - {insight}")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
