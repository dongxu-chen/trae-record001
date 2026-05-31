import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from copy import deepcopy


@dataclass
class ReductionScenario:
    scenario_id: str
    name: str
    description: str
    source_reductions: Dict[str, float]
    is_implemented: bool = False


@dataclass
class ReductionResult:
    original_concentration: pd.DataFrame
    reduced_concentration: pd.DataFrame
    concentration_change: pd.DataFrame
    concentration_change_percent: pd.DataFrame
    original_source_contribution: pd.DataFrame
    reduced_source_contribution: pd.DataFrame
    source_reductions: Dict[str, float]
    pollutant_reductions: pd.DataFrame
    total_reduction_stats: Dict[str, float]


DEFAULT_SCENARIOS = [
    ReductionScenario(
        scenario_id='INDUSTRIAL_30',
        name='工业减排30%',
        description='工业污染源排放减少30%',
        source_reductions={'工业源': 0.3}
    ),
    ReductionScenario(
        scenario_id='TRAFFIC_40',
        name='交通减排40%',
        description='交通污染源排放减少40%',
        source_reductions={'交通源': 0.4}
    ),
    ReductionScenario(
        scenario_id='DUST_50',
        name='扬尘治理50%',
        description='扬尘污染源排放减少50%',
        source_reductions={'扬尘源': 0.5}
    ),
    ReductionScenario(
        scenario_id='MIXED_20',
        name='综合减排20%',
        description='所有污染源排放减少20%',
        source_reductions={}
    ),
    ReductionScenario(
        scenario_id='COAL_60',
        name='燃煤减排60%',
        description='燃煤污染源排放减少60%',
        source_reductions={'燃煤源': 0.6}
    )
]


def create_custom_scenario(
    scenario_id: str,
    name: str,
    description: str,
    source_reductions: Dict[str, float]
) -> ReductionScenario:
    return ReductionScenario(
        scenario_id=scenario_id,
        name=name,
        description=description,
        source_reductions=source_reductions
    )


def simulate_emission_reduction(
    source_contribution: pd.DataFrame,
    concentration_data: pd.DataFrame,
    source_profile: pd.DataFrame,
    source_reductions: Dict[str, float],
    default_reduction: float = 0.0
) -> ReductionResult:
    source_names = source_contribution.columns.tolist()
    species = concentration_data.columns.tolist()
    
    reduction_factors = {}
    for source in source_names:
        if source in source_reductions:
            reduction_factors[source] = 1 - source_reductions[source]
        elif default_reduction > 0:
            reduction_factors[source] = 1 - default_reduction
        else:
            reduction_factors[source] = 1.0
    
    reduced_source_contribution = source_contribution.copy()
    for source, factor in reduction_factors.items():
        if source in reduced_source_contribution.columns:
            reduced_source_contribution[source] = reduced_source_contribution[source] * factor
    
    original_concentration = concentration_data.copy()
    reduced_concentration = pd.DataFrame(
        index=concentration_data.index,
        columns=concentration_data.columns,
        dtype=float
    )
    
    for spec in species:
        spec_profile = source_profile[spec].values if spec in source_profile.columns else np.ones(len(source_names))
        spec_profile = spec_profile / spec_profile.sum()
        
        original_contrib = np.zeros(len(concentration_data))
        reduced_contrib = np.zeros(len(concentration_data))
        
        for i, source in enumerate(source_names):
            if source in source_contribution.columns:
                original_contrib += source_contribution[source].values * spec_profile[i]
                reduced_contrib += reduced_source_contribution[source].values * spec_profile[i]
        
        scale_factor = (concentration_data[spec].values / original_contrib) if original_contrib.sum() > 0 else 1.0
        scale_factor = np.where(np.isfinite(scale_factor), scale_factor, 1.0)
        
        reduced_concentration[spec] = reduced_contrib * scale_factor
        reduced_concentration[spec] = reduced_concentration[spec].clip(lower=0)
    
    concentration_change = reduced_concentration - original_concentration
    concentration_change_percent = (concentration_change / original_concentration * 100).replace(
        [np.inf, -np.inf, np.nan], 0
    )
    
    pollutant_reductions = pd.DataFrame({
        '污染物': species,
        '原始均值': original_concentration.mean().values,
        '减排后均值': reduced_concentration.mean().values,
        '绝对变化': concentration_change.mean().values,
        '相对变化(%)': concentration_change_percent.mean().values
    })
    
    total_reduction_stats = {
        '总原始浓度': original_concentration.sum().sum(),
        '总减排后浓度': reduced_concentration.sum().sum(),
        '总绝对减排量': concentration_change.sum().sum(),
        '总相对减排率(%)': (concentration_change.sum().sum() / original_concentration.sum().sum() * 100),
        'PM2.5减排率(%)': concentration_change_percent.get('PM2.5', pd.Series([0])).mean(),
        'PM10减排率(%)': concentration_change_percent.get('PM10', pd.Series([0])).mean()
    }
    
    return ReductionResult(
        original_concentration=original_concentration,
        reduced_concentration=reduced_concentration,
        concentration_change=concentration_change,
        concentration_change_percent=concentration_change_percent,
        original_source_contribution=source_contribution,
        reduced_source_contribution=reduced_source_contribution,
        source_reductions=source_reductions,
        pollutant_reductions=pollutant_reductions,
        total_reduction_stats=total_reduction_stats
    )


def simulate_multiple_scenarios(
    source_contribution: pd.DataFrame,
    concentration_data: pd.DataFrame,
    source_profile: pd.DataFrame,
    scenarios: List[ReductionScenario]
) -> Dict[str, ReductionResult]:
    results = {}
    for scenario in scenarios:
        if len(scenario.source_reductions) == 0:
            source_names = source_contribution.columns.tolist()
            source_reductions = {s: 0.2 for s in source_names}
        else:
            source_reductions = scenario.source_reductions
        
        result = simulate_emission_reduction(
            source_contribution,
            concentration_data,
            source_profile,
            source_reductions
        )
        results[scenario.scenario_id] = result
    
    return results


def compare_scenarios(
    results: Dict[str, ReductionResult],
    scenarios: List[ReductionScenario]
) -> pd.DataFrame:
    comparison = []
    for scenario in scenarios:
        if scenario.scenario_id in results:
            result = results[scenario.scenario_id]
            stats = result.total_reduction_stats
            comparison.append({
                '场景ID': scenario.scenario_id,
                '场景名称': scenario.name,
                '描述': scenario.description,
                '总减排率(%)': f"{stats['总相对减排率(%)']:.2f}",
                'PM2.5减排率(%)': f"{stats['PM2.5减排率(%)']:.2f}",
                'PM10减排率(%)': f"{stats['PM10减排率(%)']:.2f}",
                '总减排量': f"{abs(stats['总绝对减排量']):.2f}"
            })
    return pd.DataFrame(comparison)


def get_reduction_timeseries(
    result: ReductionResult,
    pollutant: str
) -> pd.DataFrame:
    ts_data = pd.DataFrame({
        '日期': result.original_concentration.index,
        '原始浓度': result.original_concentration[pollutant].values,
        '减排后浓度': result.reduced_concentration[pollutant].values,
        '浓度变化': result.concentration_change[pollutant].values,
        '变化率(%)': result.concentration_change_percent[pollutant].values
    })
    return ts_data


def find_optimized_reduction(
    source_contribution: pd.DataFrame,
    concentration_data: pd.DataFrame,
    source_profile: pd.DataFrame,
    target_pollutant: str = 'PM2.5',
    target_reduction_percent: float = 30.0,
    max_total_reduction: float = 0.5
) -> Dict[str, float]:
    source_names = source_contribution.columns.tolist()
    species = source_profile.columns.tolist()
    
    if target_pollutant in species:
        spec_idx = species.index(target_pollutant)
        source_importance = source_profile.iloc[:, spec_idx].values
        source_importance = source_importance / source_importance.sum()
    else:
        source_importance = np.ones(len(source_names)) / len(source_names)
    
    avg_contribution = source_contribution.mean().values
    weighted_importance = source_importance * avg_contribution
    weighted_importance = weighted_importance / weighted_importance.sum()
    
    base_reduction = target_reduction_percent / 100.0
    reductions = {}
    
    for i, source in enumerate(source_names):
        source_reduction = base_reduction * weighted_importance[i] * len(source_names)
        source_reduction = min(source_reduction, max_total_reduction)
        source_reduction = max(source_reduction, 0.05)
        reductions[source] = round(source_reduction, 3)
    
    return reductions
