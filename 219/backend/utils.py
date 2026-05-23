import math
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Tuple, Dict, Optional
from PIL import Image, ImageDraw
import io
from .models import BusGPSData, GridDensity, TimeWindowData


def calculate_bounds_from_data(
    df: pd.DataFrame,
    padding: float = 0.01
) -> Tuple[float, float, float, float]:
    lon_min = df["longitude"].min() - padding
    lon_max = df["longitude"].max() + padding
    lat_min = df["latitude"].min() - padding
    lat_max = df["latitude"].max() + padding
    
    lon_range = lon_max - lon_min
    lat_range = lat_max - lat_min
    
    if lon_range < 0.02:
        center_lon = (lon_min + lon_max) / 2
        lon_min = center_lon - 0.015
        lon_max = center_lon + 0.015
    
    if lat_range < 0.02:
        center_lat = (lat_min + lat_max) / 2
        lat_min = center_lat - 0.015
        lat_max = center_lat + 0.015
    
    return lon_min, lon_max, lat_min, lat_max


def create_grid(
    lon_min: float,
    lon_max: float,
    lat_min: float,
    lat_max: float,
    grid_size: float = 0.001
) -> List[Tuple[str, float, float, float, float, float, float]]:
    grids = []
    lon_steps = math.ceil((lon_max - lon_min) / grid_size)
    lat_steps = math.ceil((lat_max - lat_min) / grid_size)
    
    for i in range(lon_steps):
        for j in range(lat_steps):
            g_lon_min = lon_min + i * grid_size
            g_lon_max = lon_min + (i + 1) * grid_size
            g_lat_min = lat_min + j * grid_size
            g_lat_max = lat_min + (j + 1) * grid_size
            center_lon = (g_lon_min + g_lon_max) / 2
            center_lat = (g_lat_min + g_lat_max) / 2
            grid_id = f"{i}_{j}"
            grids.append((grid_id, g_lon_min, g_lon_max, g_lat_min, g_lat_max, center_lon, center_lat))
    
    return grids


def point_to_grid(
    lon: float,
    lat: float,
    lon_min: float,
    lat_min: float,
    grid_size: float
) -> Tuple[int, int]:
    i = int((lon - lon_min) / grid_size)
    j = int((lat - lat_min) / grid_size)
    return i, j


def parse_gps_data(data_list: List[dict]) -> pd.DataFrame:
    records = []
    for item in data_list:
        try:
            record = {
                "bus_id": str(item.get("bus_id", item.get("vehicleId", ""))),
                "route_id": str(item.get("route_id", item.get("routeId", item.get("line", "")))),
                "longitude": float(item.get("longitude", item.get("lng", 0))),
                "latitude": float(item.get("latitude", item.get("lat", 0))),
                "timestamp": pd.to_datetime(item.get("timestamp", item.get("time", datetime.now())))
            }
            records.append(record)
        except Exception as e:
            continue
    
    return pd.DataFrame(records)


def generate_time_windows(
    start_time: datetime,
    end_time: datetime,
    window_minutes: int = 5
) -> List[Tuple[datetime, datetime]]:
    windows = []
    current = start_time.replace(minute=0, second=0, microsecond=0)
    window_delta = timedelta(minutes=window_minutes)
    
    while current < end_time:
        window_end = current + window_delta
        windows.append((current, window_end))
        current = window_end
    
    return windows


def calculate_grid_densities(
    df_window: pd.DataFrame,
    grids: List[Tuple],
    lon_min: float,
    lat_min: float,
    grid_size: float,
    congestion_threshold: float
) -> Tuple[List[GridDensity], List[dict]]:
    if len(df_window) == 0:
        return [], []
    
    grid_counts = {}
    route_grid_counts = {}
    
    for _, row in df_window.iterrows():
        i, j = point_to_grid(row["longitude"], row["latitude"], lon_min, lat_min, grid_size)
        grid_key = f"{i}_{j}"
        route_id = row["route_id"]
        
        grid_counts[grid_key] = grid_counts.get(grid_key, 0) + 1
        
        if route_id not in route_grid_counts:
            route_grid_counts[route_id] = {}
        route_grid_counts[route_id][grid_key] = route_grid_counts[route_id].get(grid_key, 0) + 1
    
    grid_dict = {g[0]: g for g in grids}
    max_count = max(grid_counts.values()) if grid_counts else 1
    
    densities = []
    for grid_id, count in grid_counts.items():
        if grid_id in grid_dict:
            g = grid_dict[grid_id]
            density = count / max_count if max_count > 0 else 0
            densities.append(GridDensity(
                grid_id=grid_id,
                lon_min=g[1],
                lon_max=g[2],
                lat_min=g[3],
                lat_max=g[4],
                center_lon=g[5],
                center_lat=g[6],
                count=count,
                density=density
            ))
    
    congestion_segments = []
    for route_id, grid_data in route_grid_counts.items():
        for grid_id, count in grid_data.items():
            if grid_id in grid_dict:
                total_in_route = sum(grid_data.values())
                if total_in_route > 0:
                    ratio = count / total_in_route
                    if ratio >= congestion_threshold and count >= 3:
                        g = grid_dict[grid_id]
                        congestion_segments.append({
                            "route_id": route_id,
                            "grid_id": grid_id,
                            "center_lon": g[5],
                            "center_lat": g[6],
                            "count": count,
                            "ratio": ratio
                        })
    
    congestion_segments.sort(key=lambda x: x["count"], reverse=True)
    return densities, congestion_segments


def get_density_color(density: float) -> Tuple[int, int, int, int]:
    if density < 0.001:
        return (0, 0, 0, 0)
    elif density < 0.25:
        alpha = int(100 + density * 600)
        return (0, 255, 0, min(alpha, 200))
    elif density < 0.5:
        t = (density - 0.25) / 0.25
        r = int(t * 255)
        g = 255
        alpha = int(150 + t * 100)
        return (r, g, 0, min(alpha, 220))
    elif density < 0.75:
        t = (density - 0.5) / 0.25
        r = 255
        g = int(255 * (1 - t * 0.5))
        return (r, g, 0, 240)
    else:
        t = (density - 0.75) / 0.25
        r = 255
        g = int(128 * (1 - t))
        return (r, g, 0, 255)


def lonlat_to_pixel(
    lon: float, lat: float,
    lon_min: float, lon_max: float,
    lat_min: float, lat_max: float,
    img_width: int, img_height: int
) -> Tuple[int, int]:
    x = int((lon - lon_min) / (lon_max - lon_min) * img_width)
    y = int((lat_max - lat) / (lat_max - lat_min) * img_height)
    return x, y


def generate_heatmap_tile(
    densities: List[GridDensity],
    lon_min: float, lon_max: float,
    lat_min: float, lat_max: float,
    tile_size: int = 256,
    blur_radius: int = 5
) -> bytes:
    img = Image.new('RGBA', (tile_size, tile_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    radius = max(8, int(tile_size / 32))
    
    for grid in densities:
        if grid.density < 0.01:
            continue
            
        x, y = lonlat_to_pixel(
            grid.center_lon, grid.center_lat,
            lon_min, lon_max, lat_min, lat_max,
            tile_size, tile_size
        )
        
        color = get_density_color(grid.density)
        
        for r in range(radius, 0, -2):
            alpha = int(color[3] * (r / radius))
            fill_color = (color[0], color[1], color[2], alpha)
            draw.ellipse([x-r, y-r, x+r, y+r], fill=fill_color)
    
    img_array = np.array(img)
    from scipy.ndimage import gaussian_filter
    
    rgb = img_array[:, :, :3]
    alpha = img_array[:, :, 3]
    
    alpha_blur = gaussian_filter(alpha.astype(float), sigma=blur_radius)
    alpha_blur = np.clip(alpha_blur, 0, 255).astype(np.uint8)
    
    result = np.dstack([rgb, alpha_blur])
    result_img = Image.fromarray(result, 'RGBA')
    
    buffer = io.BytesIO()
    result_img.save(buffer, format='PNG')
    return buffer.getvalue()


def calculate_density_grid(
    df_window: pd.DataFrame,
    lon_min: float, lon_max: float,
    lat_min: float, lat_max: float,
    grid_size: float = 0.001
) -> Dict[str, float]:
    if len(df_window) == 0:
        return {}
    
    grid_counts = {}
    for _, row in df_window.iterrows():
        if lon_min <= row["longitude"] <= lon_max and lat_min <= row["latitude"] <= lat_max:
            i, j = point_to_grid(row["longitude"], row["latitude"], lon_min, lat_min, grid_size)
            grid_key = f"{i}_{j}"
            grid_counts[grid_key] = grid_counts.get(grid_key, 0) + 1
    
    if not grid_counts:
        return {}
    
    max_count = max(grid_counts.values())
    return {k: v / max_count for k, v in grid_counts.items()}


def generate_heatmap_image(
    df_window: pd.DataFrame,
    lon_min: float, lon_max: float,
    lat_min: float, lat_max: float,
    img_width: int = 1024,
    img_height: int = 1024,
    point_radius: int = 15
) -> bytes:
    if len(df_window) == 0:
        img = Image.new('RGBA', (img_width, img_height), (0, 0, 0, 0))
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()
    
    grid_counts = {}
    for _, row in df_window.iterrows():
        if lon_min <= row["longitude"] <= lon_max and lat_min <= row["latitude"] <= lat_max:
            x, y = lonlat_to_pixel(
                row["longitude"], row["latitude"],
                lon_min, lon_max, lat_min, lat_max,
                img_width, img_height
            )
            grid_key = f"{x//10}_{y//10}"
            grid_counts[grid_key] = grid_counts.get(grid_key, 0) + 1
    
    max_count = max(grid_counts.values()) if grid_counts else 1
    
    img = Image.new('RGBA', (img_width, img_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    for _, row in df_window.iterrows():
        if lon_min <= row["longitude"] <= lon_max and lat_min <= row["latitude"] <= lat_max:
            x, y = lonlat_to_pixel(
                row["longitude"], row["latitude"],
                lon_min, lon_max, lat_min, lat_max,
                img_width, img_height
            )
            
            grid_key = f"{x//10}_{y//10}"
            density = grid_counts.get(grid_key, 0) / max_count
            color = get_density_color(density)
            
            r = int(point_radius * (0.5 + density * 0.5))
            draw.ellipse([x-r, y-r, x+r, y+r], fill=color)
    
    try:
        img_array = np.array(img)
        from scipy.ndimage import gaussian_filter
        
        rgb = img_array[:, :, :3]
        alpha = img_array[:, :, 3]
        
        alpha_blur = gaussian_filter(alpha.astype(float), sigma=3)
        alpha_blur = np.clip(alpha_blur, 0, 255).astype(np.uint8)
        
        result = np.dstack([rgb, alpha_blur])
        result_img = Image.fromarray(result, 'RGBA')
    except ImportError:
        result_img = img
    
    buffer = io.BytesIO()
    result_img.save(buffer, format='PNG')
    return buffer.getvalue()


def process_heatmap_data(
    df: pd.DataFrame,
    grid_size: float = 0.001,
    window_minutes: int = 5,
    congestion_threshold: float = 0.3
) -> Tuple[List[TimeWindowData], dict, dict]:
    if len(df) == 0:
        return [], {}, {}
    
    lon_min, lon_max, lat_min, lat_max = calculate_bounds_from_data(df)
    grids = create_grid(lon_min, lon_max, lat_min, lat_max, grid_size)
    
    start_time = df["timestamp"].min()
    end_time = df["timestamp"].max()
    time_windows = generate_time_windows(start_time, end_time, window_minutes)
    
    results = []
    for t_start, t_end in time_windows:
        mask = (df["timestamp"] >= t_start) & (df["timestamp"] < t_end)
        df_window = df[mask]
        
        densities, congestion = calculate_grid_densities(
            df_window, grids, lon_min, lat_min, grid_size, congestion_threshold
        )
        
        results.append(TimeWindowData(
            time_start=t_start,
            time_end=t_end,
            grid_densities=densities,
            congestion_segments=congestion
        ))
    
    time_range = {
        "start": start_time.isoformat(),
        "end": end_time.isoformat(),
        "total_windows": len(results),
        "window_minutes": window_minutes
    }
    
    bounds = {
        "lon_min": lon_min,
        "lon_max": lon_max,
        "lat_min": lat_min,
        "lat_max": lat_max
    }
    
    return results, time_range, bounds


def get_congestion_alerts(
    df_window: pd.DataFrame,
    lon_min: float, lon_max: float,
    lat_min: float, lat_max: float,
    grid_size: float = 0.001,
    alert_threshold: float = 0.7,
    min_vehicles: int = 5
) -> List[dict]:
    if len(df_window) == 0:
        return []
    
    grid_counts = {}
    grid_vehicles = {}
    
    for _, row in df_window.iterrows():
        if lon_min <= row["longitude"] <= lon_max and lat_min <= row["latitude"] <= lat_max:
            i, j = point_to_grid(row["longitude"], row["latitude"], lon_min, lat_min, grid_size)
            grid_key = f"{i}_{j}"
            
            grid_counts[grid_key] = grid_counts.get(grid_key, 0) + 1
            
            if grid_key not in grid_vehicles:
                grid_vehicles[grid_key] = set()
            grid_vehicles[grid_key].add(row["bus_id"])
    
    if not grid_counts:
        return []
    
    max_count = max(grid_counts.values())
    alerts = []
    
    for grid_key, count in grid_counts.items():
        density = count / max_count if max_count > 0 else 0
        unique_vehicles = len(grid_vehicles.get(grid_key, set()))
        
        if density >= alert_threshold and unique_vehicles >= min_vehicles:
            i, j = map(int, grid_key.split("_"))
            center_lon = lon_min + (i + 0.5) * grid_size
            center_lat = lat_min + (j + 0.5) * grid_size
            
            alerts.append({
                "grid_id": grid_key,
                "center_lon": center_lon,
                "center_lat": center_lat,
                "vehicle_count": count,
                "unique_buses": unique_vehicles,
                "density": density,
                "alert_level": "high" if density >= 0.85 else "medium",
                "severity": int(density * 10)
            })
    
    alerts.sort(key=lambda x: x["density"], reverse=True)
    return alerts


def get_route_trajectory(
    df: pd.DataFrame,
    route_id: str,
    smooth: bool = True
) -> dict:
    route_df = df[df["route_id"] == route_id].copy()
    
    if len(route_df) == 0:
        return {"route_id": route_id, "exists": False, "points": []}
    
    route_df = route_df.sort_values("timestamp")
    
    unique_buses = route_df["bus_id"].unique()
    all_points = []
    
    for bus_id in unique_buses:
        bus_df = route_df[route_df["bus_id"] == bus_id].sort_values("timestamp")
        points = []
        for _, row in bus_df.iterrows():
            points.append({
                "longitude": float(row["longitude"]),
                "latitude": float(row["latitude"]),
                "timestamp": row["timestamp"].isoformat(),
                "bus_id": bus_id
            })
        
        if smooth and len(points) > 10:
            step = max(1, len(points) // 50)
            points = points[::step]
        
        all_points.append({
            "bus_id": bus_id,
            "points": points,
            "point_count": len(points)
        })
    
    combined_points = []
    seen = set()
    for bus_data in all_points:
        for p in bus_data["points"]:
            key = f"{p['longitude']:.4f}_{p['latitude']:.4f}"
            if key not in seen:
                seen.add(key)
                combined_points.append({
                    "longitude": p["longitude"],
                    "latitude": p["latitude"]
                })
    
    return {
        "route_id": route_id,
        "exists": True,
        "bus_count": len(unique_buses),
        "total_points": len(route_df),
        "bus_trajectories": all_points,
        "combined_path": combined_points,
        "time_range": {
            "start": route_df["timestamp"].min().isoformat(),
            "end": route_df["timestamp"].max().isoformat()
        }
    }


def get_all_routes(df: pd.DataFrame) -> List[dict]:
    routes = df["route_id"].unique()
    result = []
    
    for route_id in routes:
        route_df = df[df["route_id"] == route_id]
        result.append({
            "route_id": str(route_id),
            "vehicle_count": route_df["bus_id"].nunique(),
            "record_count": len(route_df),
            "time_span": (route_df["timestamp"].max() - route_df["timestamp"].min()).total_seconds() / 60
        })
    
    result.sort(key=lambda x: x["record_count"], reverse=True)
    return result


def compare_time_windows(
    df: pd.DataFrame,
    window1_start: datetime,
    window1_end: datetime,
    window2_start: datetime,
    window2_end: datetime,
    lon_min: float, lon_max: float,
    lat_min: float, lat_max: float,
    grid_size: float = 0.001
) -> dict:
    mask1 = (df["timestamp"] >= window1_start) & (df["timestamp"] < window1_end)
    df1 = df[mask1]
    
    mask2 = (df["timestamp"] >= window2_start) & (df["timestamp"] < window2_end)
    df2 = df[mask2]
    
    grid_counts1 = {}
    grid_counts2 = {}
    
    for _, row in df1.iterrows():
        if lon_min <= row["longitude"] <= lon_max and lat_min <= row["latitude"] <= lat_max:
            i, j = point_to_grid(row["longitude"], row["latitude"], lon_min, lat_min, grid_size)
            grid_key = f"{i}_{j}"
            grid_counts1[grid_key] = grid_counts1.get(grid_key, 0) + 1
    
    for _, row in df2.iterrows():
        if lon_min <= row["longitude"] <= lon_max and lat_min <= row["latitude"] <= lat_max:
            i, j = point_to_grid(row["longitude"], row["latitude"], lon_min, lat_min, grid_size)
            grid_key = f"{i}_{j}"
            grid_counts2[grid_key] = grid_counts2.get(grid_key, 0) + 1
    
    max_count = max(
        max(grid_counts1.values()) if grid_counts1 else 1,
        max(grid_counts2.values()) if grid_counts2 else 1
    )
    
    all_grids = set(grid_counts1.keys()) | set(grid_counts2.keys())
    diff_data = []
    
    for grid_key in all_grids:
        count1 = grid_counts1.get(grid_key, 0)
        count2 = grid_counts2.get(grid_key, 0)
        
        density1 = count1 / max_count if max_count > 0 else 0
        density2 = count2 / max_count if max_count > 0 else 0
        
        density_diff = density2 - density1
        count_diff = count2 - count1
        
        i, j = map(int, grid_key.split("_"))
        center_lon = lon_min + (i + 0.5) * grid_size
        center_lat = lat_min + (j + 0.5) * grid_size
        
        diff_data.append({
            "grid_id": grid_key,
            "center_lon": center_lon,
            "center_lat": center_lat,
            "count_window1": count1,
            "count_window2": count2,
            "count_diff": count_diff,
            "density_window1": density1,
            "density_window2": density2,
            "density_diff": density_diff,
            "change_type": "increase" if density_diff > 0.1 else "decrease" if density_diff < -0.1 else "stable"
        })
    
    return {
        "window1": {
            "start": window1_start.isoformat(),
            "end": window1_end.isoformat(),
            "total_count": len(df1),
            "active_grids": len(grid_counts1)
        },
        "window2": {
            "start": window2_start.isoformat(),
            "end": window2_end.isoformat(),
            "total_count": len(df2),
            "active_grids": len(grid_counts2)
        },
        "comparison": diff_data,
        "summary": {
            "total_increase": len([d for d in diff_data if d["change_type"] == "increase"]),
            "total_decrease": len([d for d in diff_data if d["change_type"] == "decrease"]),
            "total_stable": len([d for d in diff_data if d["change_type"] == "stable"])
        }
    }
