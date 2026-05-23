import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class Config:
    GRID_SIZE = 10
    CITY_CENTER = (31.2304, 121.4737)
    CITY_RADIUS = 0.08
    
    TIME_SLOTS = 24
    HISTORY_DAYS = 7
    PRED_HOURS = 1
    
    BATCH_SIZE = 32
    EPOCHS = 50
    LEARNING_RATE = 0.001
    
    MODEL_PATH = os.path.join(BASE_DIR, 'models', 'od_predictor.pth')
    DATA_PATH = os.path.join(BASE_DIR, 'data', 'od_data.csv')
