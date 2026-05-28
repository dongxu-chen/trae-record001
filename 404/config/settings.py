import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MODEL_DIR = os.path.join(BASE_DIR, "models")
WEIGHTS_DIR = os.path.join(MODEL_DIR, "weights")
TRT_ENGINE_DIR = os.path.join(MODEL_DIR, "trt_engines")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

for d in [MODEL_DIR, WEIGHTS_DIR, TRT_ENGINE_DIR, OUTPUT_DIR]:
    os.makedirs(d, exist_ok=True)

YOLO_MODEL_PATH = os.path.join(WEIGHTS_DIR, "yolov8n_traffic_sign.pt")
TRT_ENGINE_PATH = os.path.join(TRT_ENGINE_DIR, "yolov8n_traffic_sign.engine")

INPUT_WIDTH = 640
INPUT_HEIGHT = 640
CONF_THRESHOLD = 0.25
IOU_THRESHOLD = 0.45
MAX_DETECTIONS = 300

FP16_QUANTIZATION = True
INT8_QUANTIZATION = False

API_HOST = "0.0.0.0"
API_PORT = 8000
API_TITLE = "Traffic Sign Recognition API"
API_VERSION = "1.0.0"

VIDEO_STREAM_WIDTH = 640
VIDEO_STREAM_HEIGHT = 480
VIDEO_STREAM_FPS = 30
