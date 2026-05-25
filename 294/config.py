import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_DIR = os.path.join(BASE_DIR, 'data')
MODEL_DIR = os.path.join(BASE_DIR, 'models')
LOG_DIR = os.path.join(BASE_DIR, 'logs')

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

VIDEO_CATEGORIES = ['娱乐', '科技', '教育', '游戏', '生活', '美食', '旅游', '体育', '音乐', '动漫']
TAGS_VOCAB_SIZE = 1000
TITLE_VOCAB_SIZE = 5000
USER_HISTORY_SIZE = 100

EMBEDDING_DIM = 16
HIDDEN_UNITS = [128, 64, 32]
DROPOUT_RATE = 0.3
LEARNING_RATE = 0.001
BATCH_SIZE = 256
EPOCHS = 10

MAX_TITLE_LENGTH = 20
MAX_TAGS = 5
MAX_HISTORY_ITEMS = 10

FLASK_HOST = '0.0.0.0'
FLASK_PORT = 5000

FM_PRETRAIN_EPOCHS = 5
FM_LEARNING_RATE = 0.01

COLD_START_THRESHOLD = 5
DEFAULT_USER_EMBEDDING = None
GLOBAL_AVERAGE_CTR = 0.35

MODEL_VERSIONS = {
    'v1': {
        'path': os.path.join(MODEL_DIR, 'v1'),
        'traffic_ratio': 0.7,
        'default': True
    },
    'v2': {
        'path': os.path.join(MODEL_DIR, 'v2'),
        'traffic_ratio': 0.3,
        'default': False
    }
}

GRAYSCALE_ENABLED = True
ROUTING_STRATEGY = 'ratio'

MULTI_TARGET = ['click', 'like', 'share']
TARGET_WEIGHTS = {'click': 1.0, 'like': 0.5, 'share': 0.3}

FEATURE_IMPORTANCE_SAMPLES = 1000
FEATURE_IMPORTANCE_TOP_N = 10

ONLINE_LEARNING_ENABLED = True
ONLINE_LEARNING_RATE = 0.0001
ONLINE_BATCH_SIZE = 32
ONLINE_BUFFER_SIZE = 1000
ONLINE_UPDATE_INTERVAL = 60


