import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
MOCK_DATA_DIR = os.path.join(DATA_DIR, 'mock')

NETCDF_FILE = os.path.join(MOCK_DATA_DIR, 'aqi_forecast.nc')

GRID_CONFIG = {
    'lon_min': 105.0,
    'lon_max': 125.0,
    'lat_min': 20.0,
    'lat_max': 40.0,
    'nx': 100,
    'ny': 100,
}

TIME_CONFIG = {
    'steps': 72,
    'start_hours_from_now': 0,
}

VARIABLES = ['PM25', 'PM10', 'O3', 'NO2', 'SO2', 'CO']

AQI_BREAKPOINTS = {
    'PM25': [(0, 0), (35, 50), (75, 100), (115, 150), (150, 200), (250, 300), (350, 400), (500, 500)],
    'PM10': [(0, 0), (50, 50), (150, 100), (250, 150), (350, 200), (420, 300), (500, 400), (600, 500)],
    'O3': [(0, 0), (160, 50), (200, 100), (300, 150), (400, 200), (800, 300), (1000, 400), (1200, 500)],
    'NO2': [(0, 0), (100, 50), (200, 100), (700, 150), (1200, 200), (2340, 300), (3090, 400), (3840, 500)],
    'SO2': [(0, 0), (150, 50), (500, 100), (650, 150), (800, 200), (1600, 300), (2100, 400), (2620, 500)],
    'CO': [(0, 0), (5, 50), (10, 100), (35, 150), (60, 200), (90, 300), (120, 400), (150, 500)],
}

AQI_LEVELS = [
    (0, 50, '优', '#00E400'),
    (51, 100, '良', '#FFFF00'),
    (101, 150, '轻度污染', '#FF7E00'),
    (151, 200, '中度污染', '#FF0000'),
    (201, 300, '重度污染', '#99004C'),
    (301, 500, '严重污染', '#7E0023'),
]

CACHE_SIZE = 10

CACHE_DIR = os.path.join(DATA_DIR, 'cache', 'tiles')

TILE_CONFIG = {
    'tile_size': 256,
    'min_zoom': 4,
    'max_zoom': 10,
    'pregenerate_hours': 24,
    'memory_cache_size': 500,
}

AQI_COLORS = {
    'excellent': (0, 228, 0),
    'good': (255, 255, 0),
    'light': (255, 126, 0),
    'moderate': (255, 0, 0),
    'heavy': (153, 0, 76),
    'severe': (126, 0, 35),
}

LOG_MAX = 6.2169
