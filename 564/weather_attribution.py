import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from scipy import stats
from scipy.stats import pearsonr, spearmanr, f_oneway


@dataclass
class WeatherData:
    temperature: float
    humidity: float
    wind_speed: float
    wind_direction: float
    pressure: float
    precipitation: float
    solar_radiation: Optional[float] = None
    visibility: Optional[float] = None


@dataclass
class WeatherAnalysisResult:
    source_weather_correlation: pd.DataFrame
    weather_source_contribution: Dict[str, pd.DataFrame]
    wind_rose_data: Dict[str, pd.DataFrame]
    seasonal_analysis: pd.DataFrame
    weather_category_stats: pd.DataFrame
    significant_weather_factors: Dict[str, List[str]]


def generate_simulated_weather_data(
    dates: pd.DatetimeIndex,
    seed: int = 42
) -> pd.DataFrame:
    np.random.seed(seed)
    
    n_days = len(dates)
    day_of_year = dates.dayofyear
    
    temp_annual = 15 + 15 * np.sin(2 * np.pi * (day_of_year - 100) / 365)
    temperature = temp_annual + np.random.normal(0, 5, n_days)
    
    humidity_base = 60 + 15 * np.sin(2 * np.pi * (day_of_year - 200) / 365)
    humidity = np.clip(humidity_base + np.random.normal(0, 10, n_days), 20, 100)
    
    wind_speed = np.random.weibull(1.5, n_days) * 3
    wind_speed = np.clip(wind_speed, 0.5, 20)
    
    wind_direction = np.random.uniform(0, 360, n_days)
    wind_seasonal = 270 + 180 * np.sin(2 * np.pi * (day_of_year - 150) / 365)
    wind_direction = (wind_direction * 0.3 + wind_seasonal * 0.7) % 360
    
    pressure = 1013 + np.random.normal(0, 5, n_days)
    pressure += 5 * np.sin(2 * np.pi * (day_of_year - 30) / 365)
    
    precipitation = np.random.exponential(2, n_days)
    precipitation = np.where(np.random.uniform(0, 1, n_days) > 0.7, precipitation, 0)
    precipitation = np.where(
        (day_of_year > 150) & (day_of_year < 270),
        precipitation * 2,
        precipitation * 0.5
    )
    
    solar_radiation = 200 + 300 * np.sin(2 * np.pi * (day_of_year - 170) / 365)
    solar_radiation = np.clip(solar_radiation + np.random.normal(0, 50, n_days), 50, 800)
    
    visibility = 10 - 3 * np.sin(2 * np.pi * (day_of_year - 200) / 365)
    visibility = np.clip(visibility + np.random.normal(0, 2, n_days), 1, 20)
    
    weather_df = pd.DataFrame({
        '温度': temperature,
        '湿度': humidity,
        '风速': wind_speed,
        '风向': wind_direction,
        '气压': pressure,
        '降水量': precipitation,
        '太阳辐射': solar_radiation,
        '能见度': visibility
    }, index=dates)
    
    return weather_df


def calculate_source_weather_correlation(
    source_contribution: pd.DataFrame,
    weather_data: pd.DataFrame,
    method: str = 'pearson'
) -> pd.DataFrame:
    source_names = source_contribution.columns.tolist()
    weather_factors = weather_data.columns.tolist()
    
    corr_matrix = pd.DataFrame(
        index=source_names,
        columns=weather_factors,
        dtype=float
    )
    p_matrix = pd.DataFrame(
        index=source_names,
        columns=weather_factors,
        dtype=float
    )
    
    for source in source_names:
        for factor in weather_factors:
            valid_mask = ~(
                source_contribution[source].isna() |
                weather_data[factor].isna()
            )
            
            if valid_mask.sum() > 10:
                x = source_contribution.loc[valid_mask, source]
                y = weather_data.loc[valid_mask, factor]
                
                if method == 'spearman':
                    corr, p_val = spearmanr(x, y)
                else:
                    corr, p_val = pearsonr(x, y)
                
                corr_matrix.loc[source, factor] = corr
                p_matrix.loc[source, factor] = p_val
            else:
                corr_matrix.loc[source, factor] = np.nan
                p_matrix.loc[source, factor] = np.nan
    
    return corr_matrix


def analyze_by_weather_category(
    source_contribution: pd.DataFrame,
    weather_data: pd.DataFrame,
    weather_factor: str,
    n_bins: int = 4
) -> pd.DataFrame:
    source_names = source_contribution.columns.tolist()
    
    quantiles = np.linspace(0, 100, n_bins + 1)
    bin_edges = np.percentile(
        weather_data[weather_factor].dropna(),
        quantiles
    )
    bin_edges = np.unique(bin_edges)
    
    if len(bin_edges) < 2:
        bin_edges = [
            weather_data[weather_factor].min(),
            weather_data[weather_factor].max()
        ]
    
    categories = pd.cut(
        weather_data[weather_factor],
        bins=bin_edges,
        labels=[f'第{i+1}档' for i in range(len(bin_edges) - 1)],
        include_lowest=True
    )
    
    results = []
    for cat in categories.cat.categories:
        cat_mask = categories == cat
        if cat_mask.sum() > 0:
            cat_contrib = source_contribution[cat_mask]
            for source in source_names:
                results.append({
                    '气象因子': weather_factor,
                    '分类': cat,
                    '分类范围': f'{bin_edges[categories.cat.categories.get_loc(cat)]:.1f} - {bin_edges[categories.cat.categories.get_loc(cat)+1]:.1f}',
                    '污染源': source,
                    '样本数': cat_mask.sum(),
                    '平均贡献': cat_contrib[source].mean(),
                    '贡献标准差': cat_contrib[source].std(),
                    '中位数贡献': cat_contrib[source].median()
                })
    
    return pd.DataFrame(results)


def analyze_wind_impact(
    source_contribution: pd.DataFrame,
    wind_direction: pd.Series,
    wind_speed: pd.Series,
    source_names: List[str],
    n_direction_bins: int = 8,
    n_speed_bins: int = 3
) -> Dict[str, pd.DataFrame]:
    direction_edges = np.linspace(0, 360, n_direction_bins + 1)
    direction_labels = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'][:n_direction_bins]
    
    speed_quantiles = np.linspace(0, 100, n_speed_bins + 1)
    speed_edges = np.percentile(wind_speed.dropna(), speed_quantiles)
    speed_labels = ['低风速', '中风速', '高风速'][:n_speed_bins]
    
    wind_results = {}
    
    for source in source_names:
        source_data = []
        for i in range(n_direction_bins):
            dir_mask = (wind_direction >= direction_edges[i]) & (wind_direction < direction_edges[i + 1])
            if i == n_direction_bins - 1:
                dir_mask |= (wind_direction >= direction_edges[-1])
            
            for j in range(n_speed_bins):
                spd_mask = (wind_speed >= speed_edges[j]) & (wind_speed < speed_edges[j + 1])
                if j == n_speed_bins - 1:
                    spd_mask |= wind_speed >= speed_edges[-1]
                
                combined_mask = dir_mask & spd_mask
                if combined_mask.sum() > 0:
                    avg_contrib = source_contribution.loc[combined_mask, source].mean()
                    source_data.append({
                        '风向': direction_labels[i],
                        '风向角度': (direction_edges[i] + direction_edges[i + 1]) / 2,
                        '风速等级': speed_labels[j],
                        '平均贡献': avg_contrib,
                        '样本数': combined_mask.sum()
                    })
        
        wind_results[source] = pd.DataFrame(source_data)
    
    return wind_results


def analyze_seasonal_variation(
    source_contribution: pd.DataFrame,
    dates: pd.DatetimeIndex
) -> pd.DataFrame:
    source_names = source_contribution.columns.tolist()
    
    seasons = {
        12: '冬季', 1: '冬季', 2: '冬季',
        3: '春季', 4: '春季', 5: '春季',
        6: '夏季', 7: '夏季', 8: '夏季',
        9: '秋季', 10: '秋季', 11: '秋季'
    }
    
    season_series = dates.month.map(seasons)
    
    results = []
    for season in ['春季', '夏季', '秋季', '冬季']:
        season_mask = season_series == season
        if season_mask.sum() > 0:
            season_contrib = source_contribution[season_mask]
            for source in source_names:
                results.append({
                    '季节': season,
                    '污染源': source,
                    '样本数': season_mask.sum(),
                    '平均贡献': season_contrib[source].mean(),
                    '贡献标准差': season_contrib[source].std(),
                    '贡献最大值': season_contrib[source].max(),
                    '贡献最小值': season_contrib[source].min(),
                    '贡献中位数': season_contrib[source].median()
                })
    
    return pd.DataFrame(results)


def find_significant_factors(
    corr_matrix: pd.DataFrame,
    p_threshold: float = 0.05
) -> Dict[str, List[str]]:
    significant = {}
    for source in corr_matrix.index:
        sig_factors = []
        for factor in corr_matrix.columns:
            p_val = corr_matrix.loc[source, factor]
            if abs(p_val) > 0.3:
                sig_factors.append(factor)
        significant[source] = sig_factors
    return significant


def run_weather_attribution_analysis(
    source_contribution: pd.DataFrame,
    weather_data: Optional[pd.DataFrame] = None,
    correlation_method: str = 'pearson',
    significance_threshold: float = 0.05
) -> WeatherAnalysisResult:
    dates = source_contribution.index
    source_names = source_contribution.columns.tolist()
    
    if weather_data is None:
        weather_data = generate_simulated_weather_data(dates)
    
    common_dates = source_contribution.index.intersection(weather_data.index)
    source_contribution = source_contribution.loc[common_dates]
    weather_data = weather_data.loc[common_dates]
    
    source_weather_corr = calculate_source_weather_correlation(
        source_contribution, weather_data, correlation_method
    )
    
    weather_source_contrib = {}
    for factor in ['温度', '湿度', '风速', '气压']:
        if factor in weather_data.columns:
            weather_source_contrib[factor] = analyze_by_weather_category(
                source_contribution, weather_data, factor
            )
    
    wind_rose_data = analyze_wind_impact(
        source_contribution,
        weather_data.get('风向', pd.Series(dtype=float, index=dates)),
        weather_data.get('风速', pd.Series(dtype=float, index=dates)),
        source_names
    )
    
    seasonal_analysis = analyze_seasonal_variation(source_contribution, dates)
    
    weather_category_stats = []
    for factor, df in weather_source_contrib.items():
        if len(df) > 0:
            stats_row = {
                '气象因子': factor,
                '源贡献差异最大': df.groupby('污染源')['平均贡献'].max().idxmax(),
                '最大变异系数': df.groupby('污染源').apply(
                    lambda x: x['平均贡献'].std() / x['平均贡献'].mean()
                ).max()
            }
            weather_category_stats.append(stats_row)
    weather_category_stats = pd.DataFrame(weather_category_stats)
    
    significant_factors = find_significant_factors(
        source_weather_corr, significance_threshold
    )
    
    return WeatherAnalysisResult(
        source_weather_correlation=source_weather_corr,
        weather_source_contribution=weather_source_contrib,
        wind_rose_data=wind_rose_data,
        seasonal_analysis=seasonal_analysis,
        weather_category_stats=weather_category_stats,
        significant_weather_factors=significant_factors
    )


def get_seasonal_summary(seasonal_analysis: pd.DataFrame) -> pd.DataFrame:
    summary = seasonal_analysis.pivot(
        index='污染源',
        columns='季节',
        values='平均贡献'
    ).round(2)
    
    summary['季节变异系数'] = seasonal_analysis.groupby('污染源').apply(
        lambda x: x['平均贡献'].std() / x['平均贡献'].mean()
    ).round(3)
    
    summary['贡献最高季节'] = summary[['春季', '夏季', '秋季', '冬季']].idxmax(axis=1)
    summary['贡献最低季节'] = summary[['春季', '夏季', '秋季', '冬季']].idxmin(axis=1)
    
    return summary
