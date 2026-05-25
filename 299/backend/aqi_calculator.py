import numpy as np
from config import AQI_BREAKPOINTS, AQI_LEVELS


def calculate_iaqi(concentration, pollutant):
    breakpoints = AQI_BREAKPOINTS.get(pollutant, [])
    if not breakpoints:
        return 0
    
    concentration = float(concentration)
    
    for i in range(len(breakpoints) - 1):
        c_low, aqi_low = breakpoints[i]
        c_high, aqi_high = breakpoints[i + 1]
        
        if c_low <= concentration <= c_high:
            if c_high == c_low:
                return aqi_low
            iaqi = (aqi_high - aqi_low) / (c_high - c_low) * (concentration - c_low) + aqi_low
            return round(iaqi)
    
    return 500


def calculate_aqi(pollutants):
    iaqi_values = {}
    for pollutant, concentration in pollutants.items():
        iaqi = calculate_iaqi(concentration, pollutant)
        iaqi_values[pollutant] = iaqi
    
    aqi = max(iaqi_values.values()) if iaqi_values else 0
    primary_pollutant = max(iaqi_values, key=iaqi_values.get) if iaqi_values else None
    
    return aqi, primary_pollutant, iaqi_values


def get_aqi_level(aqi):
    for low, high, level, color in AQI_LEVELS:
        if low <= aqi <= high:
            return level, color
    return '严重污染', '#7E0023'


def calculate_aqi_grid(pollutant_data):
    time_steps, ny, nx = pollutant_data[list(pollutant_data.keys())[0]].shape
    aqi_grid = np.zeros((time_steps, ny, nx), dtype=np.int32)
    primary_grid = np.empty((time_steps, ny, nx), dtype=object)
    
    for t in range(time_steps):
        for j in range(ny):
            for i in range(nx):
                pollutants = {}
                for var, data in pollutant_data.items():
                    pollutants[var] = data[t, j, i]
                aqi, primary, _ = calculate_aqi(pollutants)
                aqi_grid[t, j, i] = aqi
                primary_grid[t, j, i] = primary
    
    return aqi_grid, primary_grid
