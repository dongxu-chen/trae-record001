import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
import warnings
warnings.filterwarnings('ignore')


class FactorStatus(Enum):
    ACTIVE = "正常"
    WEAKENING = "衰减中"
    DEGRADED = "退化"
    INVALID = "失效"


@dataclass
class DecayReport:
    factor_name: str
    status: FactorStatus
    current_ic: float
    historical_ic: float
    ic_decay_rate: float
    ic_half_life: float
    rolling_ic: pd.Series
    warning_message: str = ""
    decay_details: Dict = field(default_factory=dict)


class FactorDecayTracker:
    def __init__(self,
                 ic_warning_threshold: float = 0.03,
                 ic_critical_threshold: float = 0.01,
                 decay_window: int = 20,
                 min_observations: int = 30):
        self.ic_warning_threshold = ic_warning_threshold
        self.ic_critical_threshold = ic_critical_threshold
        self.decay_window = decay_window
        self.min_observations = min_observations
        self.factor_history = {}
    
    def calculate_rolling_ic(self, factor: pd.Series, forward_returns: pd.Series,
                             window: int = 20) -> pd.Series:
        aligned = pd.concat([factor, forward_returns], axis=1).dropna()
        if len(aligned) < window:
            return pd.Series(dtype=float)
        
        dates = aligned.index.get_level_values('date').unique()
        rolling_ics = []
        
        for i in range(window, len(dates)):
            window_dates = dates[i - window:i]
            window_data = aligned.loc[window_dates]
            
            if len(window_data) < 10:
                continue
            
            ic = window_data.iloc[:, 0].corr(window_data.iloc[:, 1])
            rolling_ics.append({'date': dates[i], 'ic': ic})
        
        if not rolling_ics:
            return pd.Series(dtype=float)
        
        ic_df = pd.DataFrame(rolling_ics).set_index('date')['ic']
        return ic_df
    
    def calculate_ic_decay_rate(self, rolling_ic: pd.Series) -> float:
        if len(rolling_ic) < self.min_observations:
            return 0.0
        
        n = len(rolling_ic)
        x = np.arange(n)
        y = rolling_ic.values
        
        mask = ~(np.isnan(y) | np.isinf(y))
        if mask.sum() < 5:
            return 0.0
        
        x_clean = x[mask]
        y_clean = y[mask]
        
        slope = np.polyfit(x_clean, y_clean, 1)[0]
        return slope
    
    def calculate_ic_half_life(self, rolling_ic: pd.Series) -> float:
        if len(rolling_ic) < self.min_observations:
            return np.inf
        
        abs_ic = rolling_ic.abs().values
        initial_ic = np.mean(abs_ic[:min(10, len(abs_ic))])
        
        if initial_ic < 1e-8:
            return 0.0
        
        decay_rate = self.calculate_ic_decay_rate(rolling_ic)
        
        if decay_rate >= 0:
            return np.inf
        
        abs_decay_rate = abs(decay_rate) / initial_ic
        
        if abs_decay_rate < 1e-10:
            return np.inf
        
        half_life = np.log(2) / abs_decay_rate
        return half_life
    
    def _determine_status(self, rolling_ic: pd.Series, decay_rate: float) -> FactorStatus:
        if len(rolling_ic) < self.min_observations:
            return FactorStatus.ACTIVE
        
        recent_ic = rolling_ic.iloc[-min(self.decay_window, len(rolling_ic)):].mean()
        
        if abs(recent_ic) < self.ic_critical_threshold:
            return FactorStatus.INVALID
        
        if abs(recent_ic) < self.ic_warning_threshold:
            return FactorStatus.DEGRADED
        
        if decay_rate < -0.001:
            return FactorStatus.WEAKENING
        
        return FactorStatus.ACTIVE
    
    def _generate_warning(self, report: DecayReport) -> str:
        messages = []
        
        if report.status == FactorStatus.INVALID:
            messages.append(f"因子已失效！当前IC={report.current_ic:.4f}，低于临界阈值{self.ic_critical_threshold}")
        elif report.status == FactorStatus.DEGRADED:
            messages.append(f"因子严重退化！当前IC={report.current_ic:.4f}，低于预警阈值{self.ic_warning_threshold}")
        elif report.status == FactorStatus.WEAKENING:
            messages.append(f"因子正在衰减，IC衰减速率={report.ic_decay_rate:.6f}/期")
        
        if report.ic_half_life < 50 and report.ic_half_life != np.inf:
            messages.append(f"IC半衰期仅{report.ic_half_life:.1f}期，因子效力快速下降")
        
        if report.ic_decay_rate < -0.005:
            messages.append("衰减速率极快，建议立即替换该因子")
        
        return '；'.join(messages) if messages else "因子表现正常"
    
    def track_factor(self, factor_name: str, factor: pd.Series,
                     forward_returns: pd.Series) -> DecayReport:
        rolling_ic = self.calculate_rolling_ic(factor, forward_returns, self.decay_window)
        
        if len(rolling_ic) == 0:
            return DecayReport(
                factor_name=factor_name,
                status=FactorStatus.ACTIVE,
                current_ic=np.nan,
                historical_ic=np.nan,
                ic_decay_rate=0.0,
                ic_half_life=np.inf,
                rolling_ic=rolling_ic,
                warning_message="数据不足，无法计算衰减指标"
            )
        
        decay_rate = self.calculate_ic_decay_rate(rolling_ic)
        half_life = self.calculate_ic_half_life(rolling_ic)
        current_ic = rolling_ic.iloc[-1] if len(rolling_ic) > 0 else np.nan
        historical_ic = rolling_ic.mean()
        status = self._determine_status(rolling_ic, decay_rate)
        
        report = DecayReport(
            factor_name=factor_name,
            status=status,
            current_ic=current_ic,
            historical_ic=historical_ic,
            ic_decay_rate=decay_rate,
            ic_half_life=half_life,
            rolling_ic=rolling_ic,
            decay_details={
                'ic_std': rolling_ic.std(),
                'ic_max': rolling_ic.max(),
                'ic_min': rolling_ic.min(),
                'recent_5d_ic': rolling_ic.iloc[-5:].mean() if len(rolling_ic) >= 5 else np.nan,
                'recent_20d_ic': rolling_ic.iloc[-20:].mean() if len(rolling_ic) >= 20 else np.nan,
                'positive_ic_ratio': (rolling_ic > 0).mean(),
            }
        )
        
        report.warning_message = self._generate_warning(report)
        
        if factor_name not in self.factor_history:
            self.factor_history[factor_name] = []
        self.factor_history[factor_name].append({
            'date': rolling_ic.index[-1] if len(rolling_ic) > 0 else None,
            'ic': current_ic,
            'status': status.value,
            'decay_rate': decay_rate
        })
        
        return report
    
    def track_factors_batch(self, factor_names: List[str], factors: List[pd.Series],
                           forward_returns: pd.Series) -> List[DecayReport]:
        reports = []
        for name, factor in zip(factor_names, factors):
            report = self.track_factor(name, factor, forward_returns)
            reports.append(report)
        return reports
    
    def get_summary(self, reports: List[DecayReport]) -> pd.DataFrame:
        rows = []
        for r in reports:
            rows.append({
                '因子名称': r.factor_name,
                '状态': r.status.value,
                '当前IC': round(r.current_ic, 4) if not np.isnan(r.current_ic) else 'N/A',
                '历史IC': round(r.historical_ic, 4) if not np.isnan(r.historical_ic) else 'N/A',
                'IC衰减率': round(r.ic_decay_rate, 6),
                'IC半衰期': round(r.ic_half_life, 1) if r.ic_half_life != np.inf else '∞',
                '预警信息': r.warning_message
            })
        return pd.DataFrame(rows)
    
    def get_invalid_factors(self, reports: List[DecayReport]) -> List[str]:
        return [r.factor_name for r in reports 
                if r.status in (FactorStatus.INVALID, FactorStatus.DEGRADED)]
    
    def get_active_factors(self, reports: List[DecayReport]) -> List[str]:
        return [r.factor_name for r in reports 
                if r.status == FactorStatus.ACTIVE]
