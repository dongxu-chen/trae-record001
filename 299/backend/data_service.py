import os
import numpy as np
import xarray as xr
from datetime import datetime, timedelta
from functools import lru_cache
from config import NETCDF_FILE, GRID_CONFIG, TIME_CONFIG, VARIABLES, CACHE_SIZE
from aqi_calculator import calculate_aqi, get_aqi_level


class DataService:
    def __init__(self):
        self.ds = None
        self._load_data()
    
    def _load_data(self):
        if os.path.exists(NETCDF_FILE):
            self.ds = xr.open_dataset(NETCDF_FILE)
        else:
            self.ds = None
    
    def reload(self):
        self._load_data()
    
    def get_metadata(self):
        if self.ds is None:
            start_time = datetime.now().replace(minute=0, second=0, microsecond=0)
            return {
                'time_steps': TIME_CONFIG['steps'],
                'start_time': start_time.isoformat(),
                'grid_info': GRID_CONFIG,
                'variables': VARIABLES
            }
        
        return {
            'time_steps': len(self.ds.time),
            'start_time': str(self.ds.time.values[0]),
            'grid_info': {
                'lon_min': float(self.ds.lon.min()),
                'lon_max': float(self.ds.lon.max()),
                'lat_min': float(self.ds.lat.min()),
                'lat_max': float(self.ds.lat.max()),
                'nx': len(self.ds.lon),
                'ny': len(self.ds.lat),
            },
            'variables': [v for v in self.ds.data_vars if v not in ['u_wind', 'v_wind', 'AQI']]
        }
    
    @lru_cache(maxsize=CACHE_SIZE)
    def get_aqi_data(self, time_idx):
        if self.ds is None:
            return self._get_mock_aqi_data(time_idx)
        
        time_idx = int(time_idx)
        if time_idx < 0 or time_idx >= len(self.ds.time):
            time_idx = 0
        
        aqi_data = self.ds.AQI.isel(time=time_idx).values
        time_label = str(self.ds.time.values[time_idx])
        
        return {
            'time_index': time_idx,
            'time_label': time_label,
            'aqi_data': aqi_data.tolist(),
            'bounds': [
                float(self.ds.lon.min()),
                float(self.ds.lat.min()),
                float(self.ds.lon.max()),
                float(self.ds.lat.max()),
            ]
        }
    
    def _get_mock_aqi_data(self, time_idx):
        time_idx = int(time_idx)
        nx, ny = GRID_CONFIG['nx'], GRID_CONFIG['ny']
        lon = np.linspace(GRID_CONFIG['lon_min'], GRID_CONFIG['lon_max'], nx)
        lat = np.linspace(GRID_CONFIG['lat_min'], GRID_CONFIG['lat_max'], ny)
        lon_grid, lat_grid = np.meshgrid(lon, lat)
        
        center_lon = 115.0 + 2 * np.sin(time_idx / 12)
        center_lat = 32.0 + 1 * np.cos(time_idx / 18)
        dist = np.sqrt((lon_grid - center_lon)**2 + (lat_grid - center_lat)**2)
        aqi_data = 150 * np.exp(-dist**2 / 20) + 30 + 20 * np.random.rand(ny, nx)
        aqi_data = np.clip(aqi_data, 0, 300).astype(int)
        
        start_time = datetime.now().replace(minute=0, second=0, microsecond=0)
        current_time = start_time + timedelta(hours=time_idx)
        
        return {
            'time_index': time_idx,
            'time_label': current_time.isoformat(),
            'aqi_data': aqi_data.tolist(),
            'bounds': [
                GRID_CONFIG['lon_min'],
                GRID_CONFIG['lat_min'],
                GRID_CONFIG['lon_max'],
                GRID_CONFIG['lat_max'],
            ]
        }
    
    def get_pollutant_detail(self, time_idx, lat, lon):
        if self.ds is None:
            return self._get_mock_pollutant_detail(time_idx, lat, lon)
        
        time_idx = int(time_idx)
        lat_idx = np.abs(self.ds.lat.values - float(lat)).argmin()
        lon_idx = np.abs(self.ds.lon.values - float(lon)).argmin()
        
        pollutants = {}
        for var in VARIABLES:
            if var in self.ds.data_vars:
                val = float(self.ds[var].isel(time=time_idx, lat=lat_idx, lon=lon_idx).values)
                pollutants[var] = val
        
        aqi, primary_pollutant, _ = calculate_aqi(pollutants)
        aqi_level, aqi_color = get_aqi_level(aqi)
        
        return {
            'lon': float(self.ds.lon.values[lon_idx]),
            'lat': float(self.ds.lat.values[lat_idx]),
            'aqi': aqi,
            'aqi_level': aqi_level,
            'aqi_color': aqi_color,
            'primary_pollutant': primary_pollutant,
            'pollutants': {
                'PM25': {'value': pollutants.get('PM25', 0), 'unit': 'μg/m³'},
                'PM10': {'value': pollutants.get('PM10', 0), 'unit': 'μg/m³'},
                'O3': {'value': pollutants.get('O3', 0), 'unit': 'μg/m³'},
                'NO2': {'value': pollutants.get('NO2', 0), 'unit': 'μg/m³'},
                'SO2': {'value': pollutants.get('SO2', 0), 'unit': 'μg/m³'},
                'CO': {'value': pollutants.get('CO', 0), 'unit': 'mg/m³'},
            }
        }
    
    def _get_mock_pollutant_detail(self, time_idx, lat, lon):
        time_idx = int(time_idx)
        lat, lon = float(lat), float(lon)
        
        center_lon = 115.0 + 2 * np.sin(time_idx / 12)
        center_lat = 32.0 + 1 * np.cos(time_idx / 18)
        dist = np.sqrt((lon - center_lon)**2 + (lat - center_lat)**2)
        base_factor = np.exp(-dist**2 / 30)
        
        pollutants = {
            'PM25': round(35 + 80 * base_factor + 10 * np.random.rand(), 1),
            'PM10': round(50 + 100 * base_factor + 15 * np.random.rand(), 1),
            'O3': round(80 + 60 * base_factor + 20 * np.random.rand(), 1),
            'NO2': round(30 + 40 * base_factor + 5 * np.random.rand(), 1),
            'SO2': round(15 + 30 * base_factor + 3 * np.random.rand(), 1),
            'CO': round(0.8 + 1.5 * base_factor + 0.2 * np.random.rand(), 2),
        }
        
        aqi, primary_pollutant, _ = calculate_aqi(pollutants)
        aqi_level, aqi_color = get_aqi_level(aqi)
        
        return {
            'lon': lon,
            'lat': lat,
            'aqi': aqi,
            'aqi_level': aqi_level,
            'aqi_color': aqi_color,
            'primary_pollutant': primary_pollutant,
            'pollutants': {
                'PM25': {'value': pollutants['PM25'], 'unit': 'μg/m³'},
                'PM10': {'value': pollutants['PM10'], 'unit': 'μg/m³'},
                'O3': {'value': pollutants['O3'], 'unit': 'μg/m³'},
                'NO2': {'value': pollutants['NO2'], 'unit': 'μg/m³'},
                'SO2': {'value': pollutants['SO2'], 'unit': 'μg/m³'},
                'CO': {'value': pollutants['CO'], 'unit': 'mg/m³'},
            }
        }
    
    @lru_cache(maxsize=CACHE_SIZE)
    def get_wind_data(self, time_idx):
        if self.ds is None or 'u_wind' not in self.ds.data_vars:
            return self._get_mock_wind_data(time_idx)
        
        time_idx = int(time_idx)
        u_data = self.ds.u_wind.isel(time=time_idx).values
        v_data = self.ds.v_wind.isel(time=time_idx).values
        
        return {
            'time_index': time_idx,
            'u_data': u_data.tolist(),
            'v_data': v_data.tolist(),
            'bounds': [
                float(self.ds.lon.min()),
                float(self.ds.lat.min()),
                float(self.ds.lon.max()),
                float(self.ds.lat.max()),
            ]
        }
    
    def _get_mock_wind_data(self, time_idx):
        time_idx = int(time_idx)
        nx, ny = GRID_CONFIG['nx'], GRID_CONFIG['ny']
        lon = np.linspace(GRID_CONFIG['lon_min'], GRID_CONFIG['lon_max'], nx)
        lat = np.linspace(GRID_CONFIG['lat_min'], GRID_CONFIG['lat_max'], ny)
        lon_grid, lat_grid = np.meshgrid(lon, lat)
        
        u_data = 2 * np.sin((lon_grid - 110) / 10) + np.sin(time_idx / 6) + np.random.randn(ny, nx) * 0.5
        v_data = 1.5 * np.cos((lat_grid - 30) / 8) + np.cos(time_idx / 8) + np.random.randn(ny, nx) * 0.5
        
        return {
            'time_index': time_idx,
            'u_data': u_data.tolist(),
            'v_data': v_data.tolist(),
            'bounds': [
                GRID_CONFIG['lon_min'],
                GRID_CONFIG['lat_min'],
                GRID_CONFIG['lon_max'],
                GRID_CONFIG['lat_max'],
            ]
        }
    
    @lru_cache(maxsize=CACHE_SIZE)
    def get_contour_data(self, time_idx):
        aqi_data = self.get_aqi_data(time_idx)
        levels = [50, 100, 150, 200, 300]
        
        aqi_array = np.array(aqi_data['aqi_data'])
        
        contours = []
        for level in levels:
            contour_lines = self._marching_squares(aqi_array, level)
            contours.append({
                'level': level,
                'lines': contour_lines
            })
        
        return {
            'time_index': time_idx,
            'contours': contours,
            'bounds': aqi_data['bounds']
        }
    
    def _marching_squares(self, data, level):
        ny, nx = data.shape
        lon_min, lat_min, lon_max, lat_max = GRID_CONFIG['lon_min'], GRID_CONFIG['lat_min'], GRID_CONFIG['lon_max'], GRID_CONFIG['lat_max']
        
        lines = []
        for j in range(ny - 1):
            for i in range(nx - 1):
                corners = [
                    data[j, i],
                    data[j, i + 1],
                    data[j + 1, i + 1],
                    data[j + 1, i],
                ]
                
                case = 0
                for k, val in enumerate(corners):
                    if val >= level:
                        case |= (1 << k)
                
                if case == 0 or case == 15:
                    continue
                
                lon0 = lon_min + (lon_max - lon_min) * i / (nx - 1)
                lat0 = lat_min + (lat_max - lat_min) * j / (ny - 1)
                dlon = (lon_max - lon_min) / (nx - 1)
                dlat = (lat_max - lat_min) / (ny - 1)
                
                edges = []
                if case & 1:
                    t = (level - corners[0]) / (corners[1] - corners[0]) if corners[1] != corners[0] else 0.5
                    edges.append([lon0 + t * dlon, lat0])
                if case & 2:
                    t = (level - corners[1]) / (corners[2] - corners[1]) if corners[2] != corners[1] else 0.5
                    edges.append([lon0 + dlon, lat0 + t * dlat])
                if case & 4:
                    t = (level - corners[3]) / (corners[2] - corners[3]) if corners[2] != corners[3] else 0.5
                    edges.append([lon0 + t * dlon, lat0 + dlat])
                if case & 8:
                    t = (level - corners[0]) / (corners[3] - corners[0]) if corners[3] != corners[0] else 0.5
                    edges.append([lon0, lat0 + t * dlat])
                
                if len(edges) >= 2:
                    lines.append(edges[:2])
        
        return lines


data_service = DataService()
