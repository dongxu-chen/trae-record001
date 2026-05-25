import numpy as np
import xarray as xr
from datetime import datetime, timedelta
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))
from config import GRID_CONFIG, TIME_CONFIG, VARIABLES, MOCK_DATA_DIR


def generate_mock_data():
    nx, ny = GRID_CONFIG['nx'], GRID_CONFIG['ny']
    time_steps = TIME_CONFIG['steps']
    
    lon = np.linspace(GRID_CONFIG['lon_min'], GRID_CONFIG['lon_max'], nx)
    lat = np.linspace(GRID_CONFIG['lat_min'], GRID_CONFIG['lat_max'], ny)
    
    start_time = datetime.now().replace(minute=0, second=0, microsecond=0)
    times = [start_time + timedelta(hours=i) for i in range(time_steps)]
    
    lon_grid, lat_grid = np.meshgrid(lon, lat)
    
    data_vars = {}
    
    for t in range(time_steps):
        center_lon = 115.0 + 3 * np.sin(t / 12)
        center_lat = 32.0 + 2 * np.cos(t / 18)
        dist = np.sqrt((lon_grid - center_lon)**2 + (lat_grid - center_lat)**2)
        base_factor = np.exp(-dist**2 / 25)
        
        if t == 0:
            data_vars['PM25'] = np.zeros((time_steps, ny, nx), dtype=np.float32)
            data_vars['PM10'] = np.zeros((time_steps, ny, nx), dtype=np.float32)
            data_vars['O3'] = np.zeros((time_steps, ny, nx), dtype=np.float32)
            data_vars['NO2'] = np.zeros((time_steps, ny, nx), dtype=np.float32)
            data_vars['SO2'] = np.zeros((time_steps, ny, nx), dtype=np.float32)
            data_vars['CO'] = np.zeros((time_steps, ny, nx), dtype=np.float32)
            data_vars['u_wind'] = np.zeros((time_steps, ny, nx), dtype=np.float32)
            data_vars['v_wind'] = np.zeros((time_steps, ny, nx), dtype=np.float32)
        
        data_vars['PM25'][t] = 20 + 100 * base_factor + 10 * np.random.randn(ny, nx)
        data_vars['PM10'][t] = 40 + 120 * base_factor + 15 * np.random.randn(ny, nx)
        data_vars['O3'][t] = 60 + 80 * base_factor + 20 * np.random.randn(ny, nx)
        data_vars['NO2'][t] = 20 + 50 * base_factor + 8 * np.random.randn(ny, nx)
        data_vars['SO2'][t] = 10 + 40 * base_factor + 5 * np.random.randn(ny, nx)
        data_vars['CO'][t] = 0.5 + 2.0 * base_factor + 0.3 * np.random.randn(ny, nx)
        
        data_vars['u_wind'][t] = 2 * np.sin((lon_grid - 110) / 10) + np.sin(t / 6)
        data_vars['v_wind'][t] = 1.5 * np.cos((lat_grid - 30) / 8) + np.cos(t / 8)
    
    for key in data_vars:
        data_vars[key] = np.clip(data_vars[key], 0, None)
    
    ds = xr.Dataset(
        {var: (['time', 'lat', 'lon'], data_vars[var]) for var in data_vars},
        coords={
            'lon': lon,
            'lat': lat,
            'time': times,
        }
    )
    
    os.makedirs(MOCK_DATA_DIR, exist_ok=True)
    output_file = os.path.join(MOCK_DATA_DIR, 'aqi_forecast.nc')
    ds.to_netcdf(output_file)
    print(f'Mock data generated: {output_file}')


if __name__ == '__main__':
    generate_mock_data()
