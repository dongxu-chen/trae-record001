import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
MODEL_DIR = os.path.join(BASE_DIR, 'models')

STATIONS = [f'站点{i:02d}' for i in range(1, 11)]

PREDICTION_HOURS = 1
CONFIDENCE_INTERVAL = 0.95

WEATHER_TYPES = ['晴', '多云', '阴', '小雨', '中雨', '大雨', '雪']
