import os
from pydantic import BaseModel
from typing import List, Optional

class Config(BaseModel):
    APP_NAME: str = "在线考试防作弊系统"
    APP_VERSION: str = "1.0.0"
    
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    BASE_DIR: str = os.path.dirname(os.path.abspath(__file__))
    
    DATA_DIR: str = os.path.join(BASE_DIR, "data")
    MODEL_DIR: str = os.path.join(BASE_DIR, "models")
    RECORDINGS_DIR: str = os.path.join(DATA_DIR, "recordings")
    UPLOADS_DIR: str = os.path.join(DATA_DIR, "uploads")
    
    FACE_RECOGNITION_THRESHOLD: float = 0.6
    FACE_DETECTION_INTERVAL: float = 5.0
    
    ENABLE_LIVENESS_DETECTION: bool = True
    LIVENESS_BLINK_THRESHOLD: int = 2
    LIVENESS_MOVEMENT_THRESHOLD: float = 0.1
    LIVENESS_TEXTURE_THRESHOLD: float = 0.3
    LIVENESS_ANTI_PHOTO_THRESHOLD: float = 0.5
    
    ENABLE_SINGLE_FACE_LOCK: bool = True
    MULTIPLE_FACE_GRACE_PERIOD: float = 5.0
    ENABLE_AUTO_PAUSE_ON_MULTIPLE_FACES: bool = True
    
    SCREEN_RECORD_FPS: int = 10
    SCREEN_RECORD_QUALITY: int = 80
    
    TAB_SWITCH_THRESHOLD: int = 3
    TAB_SWITCH_WINDOW: int = 60
    
    ENABLE_FULLSCREEN_DETECTION: bool = True
    FULLSCREEN_CHECK_INTERVAL: float = 1.0
    
    ENABLE_MULTI_MONITOR_DETECTION: bool = True
    MONITOR_DETECTION_INTERVAL: float = 5.0
    
    SIMILARITY_THRESHOLD: float = 0.85
    STRUCTURED_SIMILARITY_THRESHOLD: float = 0.85
    STRUCTURED_SIMILARITY_RISK_THRESHOLD: float = 0.7
    
    QUESTION_COUNT_PER_EXAM: int = 10
    
    WEBRTC_STUN_SERVER: str = "stun:stun.l.google.com:19302"
    
    JWT_SECRET_KEY: str = "your-secret-key-keep-it-safe-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 120
    
    DATABASE_URL: str = "sqlite:///./data/exam.db"
    
    LOG_LEVEL: str = "INFO"
    
    ENABLE_MONITORING: bool = True
    ENABLE_RECORDING: bool = True
    ENABLE_FACE_DETECTION: bool = True
    ENABLE_TAB_DETECTION: bool = True
    ENABLE_SIMILARITY_CHECK: bool = True
    ENABLE_AUDIO_MONITORING: bool = True
    ENABLE_REMOTE_MONITOR: bool = True
    ENABLE_RISK_SCORING: bool = True

    AUDIO_SAMPLE_RATE: int = 16000
    AUDIO_CHUNK_SIZE: int = 4096
    SPEECH_DETECTION_THRESHOLD: float = 0.6
    HIGH_VOLUME_THRESHOLD: float = -20.0
    SUSPICIOUS_SOUND_THRESHOLD: float = 0.7

    REMOTE_THUMBNAIL_WIDTH: int = 320
    REMOTE_THUMBNAIL_HEIGHT: int = 240
    REMOTE_MAX_HISTORY: int = 50
    REMOTE_IMAGE_QUALITY: int = 85

    RISK_AUTO_REVIEW_THRESHOLD: float = 60.0
    RISK_CRITICAL_THRESHOLD: float = 80.0
    RISK_MEDIUM_THRESHOLD: float = 30.0

config = Config()

os.makedirs(config.DATA_DIR, exist_ok=True)
os.makedirs(config.MODEL_DIR, exist_ok=True)
os.makedirs(config.RECORDINGS_DIR, exist_ok=True)
os.makedirs(config.UPLOADS_DIR, exist_ok=True)
