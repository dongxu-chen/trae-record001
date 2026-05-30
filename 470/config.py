import os

class Config:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    
    INPUT_DIR = os.path.join(BASE_DIR, 'input')
    OUTPUT_DIR = os.path.join(BASE_DIR, 'output')
    CHECKPOINT_DIR = os.path.join(BASE_DIR, 'checkpoints')
    
    BASNET_CHECKPOINT = os.path.join(CHECKPOINT_DIR, 'basnet.pth')
    POOLNET_CHECKPOINT = os.path.join(CHECKPOINT_DIR, 'poolnet.pth')
    
    BASNET_ONNX = os.path.join(CHECKPOINT_DIR, 'basnet.onnx')
    POOLNET_ONNX = os.path.join(CHECKPOINT_DIR, 'poolnet.onnx')
    BASNET_TRT = os.path.join(CHECKPOINT_DIR, 'basnet.trt')
    POOLNET_TRT = os.path.join(CHECKPOINT_DIR, 'poolnet.trt')
    
    IMAGE_SIZE = 256
    BATCH_SIZE = 4
    MAX_BATCH_SIZE = 8
    
    USE_TENSORRT = True
    TRT_FP16 = True
    TRT_INT8 = False
    
    TARGET_INFERENCE_TIME = 50
    
    @staticmethod
    def get_device():
        try:
            import torch
            return 'cuda' if torch.cuda.is_available() else 'cpu'
        except:
            return 'cpu'
    
    DEVICE = None
    
    DEFAULT_MODEL = 'basnet'
    
    THRESHOLD = 0.5
    EDGE_THINNING = True
    MORPH_KERNEL_SIZE = 3
    
    FLASK_HOST = '0.0.0.0'
    FLASK_PORT = 5000
    DEBUG = True
    
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'bmp', 'tiff'}
    
    @staticmethod
    def ensure_dirs():
        for dir_path in [Config.INPUT_DIR, Config.OUTPUT_DIR, Config.CHECKPOINT_DIR]:
            os.makedirs(dir_path, exist_ok=True)
