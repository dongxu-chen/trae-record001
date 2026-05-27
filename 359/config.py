import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    AMAP_API_KEY = os.getenv('AMAP_API_KEY', '')
    BAIDU_API_KEY = os.getenv('BAIDU_API_KEY', '')
    WEATHER_API_KEY = os.getenv('WEATHER_API_KEY', '')
    
    MODEL_PATH = 'models/delivery_model.pkl'
    DATA_PATH = 'data/training_data.csv'
    
    CONFIDENCE_LEVEL = 0.95
    
    USE_MOCK_DATA = True
    
    CITY_COORDS = {
        '北京': [116.4074, 39.9042],
        '上海': [121.4737, 31.2304],
        '广州': [113.2644, 23.1291],
        '深圳': [114.0579, 22.5431],
        '杭州': [120.1551, 30.2741],
        '南京': [118.7969, 32.0603],
        '成都': [104.0668, 30.5728],
        '武汉': [114.3054, 30.5931],
        '西安': [108.9398, 34.3416],
        '重庆': [106.5516, 29.5630]
    }
