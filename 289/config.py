import os

class Config:
    REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
    REDIS_DB = int(os.getenv('REDIS_DB', 0))
    
    WEBSOCKET_HOST = os.getenv('WEBSOCKET_HOST', 'localhost')
    WEBSOCKET_PORT = int(os.getenv('WEBSOCKET_PORT', 8765))
    
    HTTP_HOST = os.getenv('HTTP_HOST', 'localhost')
    HTTP_PORT = int(os.getenv('HTTP_PORT', 8080))
    
    GPS_UPDATE_INTERVAL = 2
    PREDICTION_INTERVAL = 5
    
    MODEL_PATH = 'models/bus_arrival_model.json'
    SCALER_PATH = 'models/scaler.pkl'
    
    BUS_ROUTES = {
        '101': {
            'name': '101路',
            'stations': [
                {'id': 'S001', 'name': '火车站', 'lat': 31.2304, 'lon': 121.4737, 'order': 1},
                {'id': 'S002', 'name': '人民广场', 'lat': 31.2325, 'lon': 121.4695, 'order': 2},
                {'id': 'S003', 'name': '南京路', 'lat': 31.2370, 'lon': 121.4750, 'order': 3},
                {'id': 'S004', 'name': '外滩', 'lat': 31.2395, 'lon': 121.4900, 'order': 4},
                {'id': 'S005', 'name': '陆家嘴', 'lat': 31.2400, 'lon': 121.5010, 'order': 5},
                {'id': 'S006', 'name': '世纪公园', 'lat': 31.2250, 'lon': 121.5400, 'order': 6},
            ],
            'stop_light_density': [2.5, 3.0, 2.0, 1.5, 1.0],
            'scheduled_interval': 15
        },
        '202': {
            'name': '202路',
            'stations': [
                {'id': 'S101', 'name': '虹桥机场', 'lat': 31.1960, 'lon': 121.3360, 'order': 1},
                {'id': 'S102', 'name': '徐家汇', 'lat': 31.1950, 'lon': 121.4370, 'order': 2},
                {'id': 'S103', 'name': '衡山路', 'lat': 31.2050, 'lon': 121.4450, 'order': 3},
                {'id': 'S104', 'name': '静安寺', 'lat': 31.2240, 'lon': 121.4480, 'order': 4},
                {'id': 'S105', 'name': '中山公园', 'lat': 31.2200, 'lon': 121.4200, 'order': 5},
            ],
            'stop_light_density': [1.5, 2.5, 2.0, 3.0],
            'scheduled_interval': 12
        }
    }
    
    TRAFFIC_LEVELS = {
        0: '畅通',
        1: '轻度拥堵',
        2: '中度拥堵',
        3: '严重拥堵'
    }
    
    DELAY_WARNING_THRESHOLD = 180
    EARLY_WARNING_THRESHOLD = 60
