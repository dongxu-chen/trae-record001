import json
from dataclasses import dataclass, asdict


@dataclass
class Config:
    video_source: int = 0
    video_width: int = 1280
    video_height: int = 720
    video_fps: int = 30
    
    min_detection_confidence: float = 0.5
    min_tracking_confidence: float = 0.5
    
    osc_ip: str = "127.0.0.1"
    osc_port: int = 9000
    
    show_preview: bool = True
    draw_landmarks: bool = True
    show_fps: bool = True
    
    smoothing_factor: float = 0.3
    
    head_pose_scale: float = 1.0
    eye_params_scale: float = 1.0
    mouth_params_scale: float = 1.0
    brow_params_scale: float = 1.0

    def save(self, filepath: str):
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(asdict(self), f, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, filepath: str) -> 'Config':
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return cls(**data)
        except FileNotFoundError:
            return cls()
