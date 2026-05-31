import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from scipy.interpolate import griddata
from scipy.spatial.distance import cdist


@dataclass
class SpatialPoint:
    latitude: float
    longitude: float
    site_name: str
    source_contributions: Dict[str, float] = field(default_factory=dict)


@dataclass
class SpatialAnalysisResult:
    points: List[SpatialPoint]
    grid_data: Dict[str, np.ndarray]
    grid_lat: np.ndarray
    grid_lon: np.ndarray
    source_names: List[str]
    spatial_stats: pd.DataFrame
    hotspots: Dict[str, List[SpatialPoint]]


def generate_simulated_spatial_data(
    source_contribution: pd.DataFrame,
    n_sites: int = 20,
    center_lat: float = 39.9,
    center_lon: float = 116.4,
    spread: float = 0.5
) -> List[SpatialPoint]:
    np.random.seed(42)
    
    source_names = source_contribution.columns.tolist()
    avg_contributions = source_contribution.mean().to_dict()
    
    spatial_patterns = {
        '工业源': lambda lat, lon: np.exp(-((lat - center_lat - 0.1)**2 + (lon - center_lon + 0.1)**2) / 0.05),
        '交通源': lambda lat, lon: np.exp(-((lat - center_lat)**2 + (lon - center_lon)**2) / 0.03) + 0.5,
        '扬尘源': lambda lat, lon: 0.5 + 0.5 * np.exp(-((lat - center_lat + 0.15)**2 + (lon - center_lon - 0.1)**2) / 0.08),
        '燃煤源': lambda lat, lon: np.exp(-((lat - center_lat + 0.2)**2 + (lon - center_lon + 0.15)**2) / 0.06),
        '农业源': lambda lat, lon: 0.3 + 0.7 * np.exp(-((lat - center_lat - 0.2)**2 + (lon - center_lon + 0.05)**2) / 0.1)
    }
    
    points = []
    lats = np.random.uniform(center_lat - spread, center_lat + spread, n_sites)
    lons = np.random.uniform(center_lon - spread, center_lon + spread, n_sites)
    
    for i in range(n_sites):
        site_name = f"监测站-{i+1:03d}"
        
        source_contribs = {}
        for source in source_names:
            pattern_func = spatial_patterns.get(source, lambda lat, lon: 1.0)
            spatial_factor = pattern_func(lats[i], lons[i])
            base_value = avg_contributions.get(source, 10.0)
            noise = np.random.normal(1.0, 0.15)
            source_contribs[source] = base_value * spatial_factor * noise
        
        point = SpatialPoint(
            latitude=float(lats[i]),
            longitude=float(lons[i]),
            site_name=site_name,
            source_contributions=source_contribs
        )
        points.append(point)
    
    return points


def create_spatial_grid(
    points: List[SpatialPoint],
    source_names: List[str],
    resolution: int = 100
) -> Tuple[np.ndarray, np.ndarray, Dict[str, np.ndarray]]:
    lats = np.array([p.latitude for p in points])
    lons = np.array([p.longitude for p in points])
    
    lat_min, lat_max = lats.min(), lats.max()
    lon_min, lon_max = lons.min(), lons.max()
    
    padding = 0.02
    lat_min -= padding
    lat_max += padding
    lon_min -= padding
    lon_max += padding
    
    grid_lat, grid_lon = np.meshgrid(
        np.linspace(lat_min, lat_max, resolution),
        np.linspace(lon_min, lon_max, resolution)
    )
    
    grid_data = {}
    for source in source_names:
        values = np.array([p.source_contributions.get(source, 0.0) for p in points])
        grid = griddata(
            (lats, lons),
            values,
            (grid_lat, grid_lon),
            method='cubic',
            fill_value=np.nan
        )
        mask = np.isnan(grid)
        if mask.any():
            grid_nearest = griddata(
                (lats, lons),
                values,
                (grid_lat, grid_lon),
                method='nearest'
            )
            grid[mask] = grid_nearest[mask]
        grid_data[source] = grid
    
    return grid_lat, grid_lon, grid_data


def calculate_spatial_stats(
    points: List[SpatialPoint],
    source_names: List[str]
) -> pd.DataFrame:
    stats = []
    for source in source_names:
        values = [p.source_contributions.get(source, 0.0) for p in points]
        stats.append({
            '污染源': source,
            '最小值': np.min(values),
            '最大值': np.max(values),
            '平均值': np.mean(values),
            '标准差': np.std(values),
            '变异系数': np.std(values) / np.mean(values) if np.mean(values) > 0 else 0,
            '空间分布均匀度': 1 - (np.std(values) / np.mean(values) / 2) if np.mean(values) > 0 else 0
        })
    return pd.DataFrame(stats)


def detect_hotspots(
    points: List[SpatialPoint],
    source_names: List[str],
    threshold_percentile: float = 75
) -> Dict[str, List[SpatialPoint]]:
    hotspots = {}
    
    for source in source_names:
        values = [p.source_contributions.get(source, 0.0) for p in points]
        threshold = np.percentile(values, threshold_percentile)
        
        source_hotspots = [
            p for p in points
            if p.source_contributions.get(source, 0.0) >= threshold
        ]
        hotspots[source] = source_hotspots
    
    return hotspots


def run_spatial_analysis(
    source_contribution: pd.DataFrame,
    n_sites: int = 20,
    center_lat: float = 39.9,
    center_lon: float = 116.4,
    spread: float = 0.5,
    resolution: int = 100,
    hotspot_threshold: float = 75
) -> SpatialAnalysisResult:
    source_names = source_contribution.columns.tolist()
    
    points = generate_simulated_spatial_data(
        source_contribution, n_sites, center_lat, center_lon, spread
    )
    
    grid_lat, grid_lon, grid_data = create_spatial_grid(points, source_names, resolution)
    
    spatial_stats = calculate_spatial_stats(points, source_names)
    
    hotspots = detect_hotspots(points, source_names, hotspot_threshold)
    
    return SpatialAnalysisResult(
        points=points,
        grid_data=grid_data,
        grid_lat=grid_lat,
        grid_lon=grid_lon,
        source_names=source_names,
        spatial_stats=spatial_stats,
        hotspots=hotspots
    )


def get_hotspot_summary(hotspots: Dict[str, List[SpatialPoint]]) -> pd.DataFrame:
    data = []
    for source, points in hotspots.items():
        for point in points:
            data.append({
                '污染源': source,
                '监测站': point.site_name,
                '纬度': point.latitude,
                '经度': point.longitude,
                '源贡献': point.source_contributions.get(source, 0.0)
            })
    return pd.DataFrame(data)
