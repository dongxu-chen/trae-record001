import os
from typing import List


class Config:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    YOLO_MODEL_PATH = os.path.join(BASE_DIR, "models", "yolov8n.pt")
    YOLO_CONF = 0.25
    YOLO_IOU = 0.45
    YOLO_IMGSZ = 640
    YOLO_DEVICE = "cuda"
    YOLO_CLASSES: List[int] = None

    MAX_AGE = 30
    N_INIT = 3
    NN_BUDGET = 100
    MAX_COSINE_DISTANCE = 0.2
    MAX_IOU_DISTANCE = 0.7

    FEATURE_MATCH_WEIGHT = 0.4
    MOTION_PREDICT_WEIGHT = 0.3
    IOU_MATCH_WEIGHT = 0.3
    MOTION_UNCERTAINTY_THRESHOLD = 5.0

    MAX_TRACK_LENGTH = 50

    SMALL_OBJECT_AREA_THRESHOLD = 32 * 32
    HIGH_RESOLUTION_SCALE = 2.0
    HIGH_RESOLUTION_ENABLE = True
    HIGH_RESOLUTION_CONF = 0.15

    SKIP_FRAME_ENABLE = True
    DETECT_INTERVAL = 2
    MOTION_INTERPOLATION_ENABLE = True

    ANOMALY_ENABLE = True
    LOITERING_DISTANCE_THRESHOLD = 150.0
    LOITERING_TIME_THRESHOLD = 30
    WRONG_DIRECTION_ANGLE_THRESHOLD = 120.0
    WRONG_DIRECTION_MIN_SPEED = 2.0
    SPEED_ANOMALY_MULTIPLIER = 3.0
    ANOMALY_TRAIL_MIN_LENGTH = 10

    CROSS_CAMERA_ENABLE = True
    CROSS_CAMERA_FEATURE_THRESHOLD = 0.6
    CROSS_CAMERA_TIME_WINDOW = 30.0
    CROSS_CAMERA_IOU_THRESHOLD = 0.3

    METRICS_ENABLE = True
    METRICS_WINDOW_SIZE = 100
    METRICS_DISPLAY_FPS = True

    LINE_THICKNESS = 2
    TEXT_SCALE = 0.6
    TEXT_THICKNESS = 2
    SHOW_TRAILS = True
    TRAIL_LENGTH = 30

    API_HOST = "0.0.0.0"
    API_PORT = 8000

    OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
    MODEL_DIR = os.path.join(BASE_DIR, "models")
    UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")

    @classmethod
    def ensure_dirs(cls):
        for dir_path in [cls.OUTPUT_DIR, cls.MODEL_DIR, cls.UPLOAD_DIR]:
            os.makedirs(dir_path, exist_ok=True)
