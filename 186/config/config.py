import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MYSQL_CONFIG = {
    'host': os.getenv('MYSQL_HOST', 'localhost'),
    'port': int(os.getenv('MYSQL_PORT', 3306)),
    'user': os.getenv('MYSQL_USER', 'root'),
    'password': os.getenv('MYSQL_PASSWORD', 'password'),
    'database': os.getenv('MYSQL_DATABASE', 'drama_audit'),
    'charset': 'utf8mb4',
    'autocommit': True
}

FFMPEG_PATH = os.getenv('FFMPEG_PATH', 'ffmpeg')
FFPROBE_PATH = os.getenv('FFPROBE_PATH', 'ffprobe')

UPLOAD_DIR = os.path.join(BASE_DIR, 'uploads')
FRAMES_DIR = os.path.join(BASE_DIR, 'frames')
LOG_DIR = os.path.join(BASE_DIR, 'logs')

VISION_API_KEY = os.getenv('VISION_API_KEY', '')
VISION_API_ENDPOINT = os.getenv('VISION_API_ENDPOINT', 'https://vision.googleapis.com/v1/images:annotate')

OCR_API_KEY = os.getenv('OCR_API_KEY', '')
OCR_API_ENDPOINT = os.getenv('OCR_API_ENDPOINT', 'https://api.ocr.space/parse/image')

FRAME_INTERVAL = float(os.getenv('FRAME_INTERVAL', 2.0))
MIN_CONFIDENCE = float(os.getenv('MIN_CONFIDENCE', 0.7))

VIOLATION_TYPES = {
    'politics': '涉政违规',
    'porn': '色情违规',
    'violence': '暴力违规',
    'text_politics': '文本涉政',
    'text_porn': '文本色情',
    'text_violence': '文本暴力'
}

MAX_FRAMES_PER_VIDEO = int(os.getenv('MAX_FRAMES_PER_VIDEO', 500))
REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', 30))

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(FRAMES_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)
