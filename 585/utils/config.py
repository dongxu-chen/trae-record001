import os
from dataclasses import dataclass, field
from typing import List, Tuple


@dataclass
class HMRConfig:
    SMPL_MODEL_PATH: str = "models/smpl/basicModel_neutral_lbs_10_207_0_v1.0.0.pkl"
    HMR_CHECKPOINT_PATH: str = "models/hmr/hmr_pretrained.pt"
    
    IMAGE_SIZE: int = 224
    BATCH_SIZE: int = 1
    
    SMPL_NUM_JOINTS: int = 24
    SMPL_NUM_SHAPE_PARAMS: int = 10
    SMPL_NUM_POSE_PARAMS: int = 72
    
    MEAN: List[float] = field(default_factory=lambda: [0.485, 0.456, 0.406])
    STD: List[float] = field(default_factory=lambda: [0.229, 0.224, 0.225])


@dataclass
class OpenPoseConfig:
    PROTO_PATH: str = "models/openpose/pose_deploy_linevec.prototxt"
    WEIGHTS_PATH: str = "models/openpose/pose_iter_440000.caffemodel"
    
    HAND_PROTO_PATH: str = "models/openpose/pose_deploy.prototxt"
    HAND_WEIGHTS_PATH: str = "models/openpose/pose_iter_102000.caffemodel"
    
    NET_INPUT_SIZE: Tuple[int, int] = (368, 368)
    THRESHOLD: float = 0.1
    
    BODY_PARTS: dict = field(default_factory=lambda: {
        "Nose": 0, "Neck": 1, "RShoulder": 2, "RElbow": 3, "RWrist": 4,
        "LShoulder": 5, "LElbow": 6, "LWrist": 7, "RHip": 8, "RKnee": 9,
        "RAnkle": 10, "LHip": 11, "LKnee": 12, "LAnkle": 13, "REye": 14,
        "LEye": 15, "REar": 16, "LEar": 17, "Background": 18
    })
    
    POSE_PAIRS: list = field(default_factory=lambda: [
        ["Neck", "RShoulder"], ["Neck", "LShoulder"], ["RShoulder", "RElbow"],
        ["RElbow", "RWrist"], ["LShoulder", "LElbow"], ["LElbow", "LWrist"],
        ["Neck", "RHip"], ["RHip", "RKnee"], ["RKnee", "RAnkle"],
        ["Neck", "LHip"], ["LHip", "LKnee"], ["LKnee", "LAnkle"],
        ["Neck", "Nose"], ["Nose", "REye"], ["REye", "REar"],
        ["Nose", "LEye"], ["LEye", "LEar"]
    ])


@dataclass
class TrackingConfig:
    MAX_AGE: int = 30
    MIN_HITS: int = 3
    IOU_THRESHOLD: float = 0.3
    USE_KALMAN: bool = True


@dataclass
class SmoothingConfig:
    METHOD: str = "kalman"
    ALPHA: float = 0.7
    PROCESS_NOISE: float = 0.01
    MEASUREMENT_NOISE: float = 0.1


@dataclass
class VisualizationConfig:
    JOINT_SIZE: int = 5
    LINE_WIDTH: int = 2
    FIGURE_SIZE: Tuple[int, int] = (12, 6)
    ENABLE_MESH: bool = True


@dataclass
class Config:
    hmr: HMRConfig = field(default_factory=HMRConfig)
    openpose: OpenPoseConfig = field(default_factory=OpenPoseConfig)
    tracking: TrackingConfig = field(default_factory=TrackingConfig)
    smoothing: SmoothingConfig = field(default_factory=SmoothingConfig)
    visualization: VisualizationConfig = field(default_factory=VisualizationConfig)
    
    DEVICE: str = "cuda" if os.environ.get("CUDA_VISIBLE_DEVICES") else "cpu"
    MULTI_PERSON: bool = True
    ENABLE_HAND: bool = True
    ENABLE_TEMPORAL_SMOOTHING: bool = True
    
    OUTPUT_DIR: str = "output"
    
    def __post_init__(self):
        os.makedirs(self.OUTPUT_DIR, exist_ok=True)
        os.makedirs("models/smpl", exist_ok=True)
        os.makedirs("models/hmr", exist_ok=True)
        os.makedirs("models/openpose", exist_ok=True)


config = Config()
