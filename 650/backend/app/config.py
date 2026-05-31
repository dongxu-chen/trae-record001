from pydantic_settings import BaseSettings
from typing import Dict


class Settings(BaseSettings):
    app_name: str = "Video Action Recognition System"
    version: str = "1.0.0"
    
    host: str = "0.0.0.0"
    port: int = 8000
    
    model_type: str = "timesformer"
    device: str = "cpu"
    fp16: bool = False
    
    confidence_threshold: float = 0.5
    fps: int = 16
    num_frames: int = 16
    sampling_rate: int = 2
    
    frame_size: int = 224
    mean: tuple = (0.45, 0.45, 0.45)
    std: tuple = (0.225, 0.225, 0.225)
    
    temporal_window_size: int = 30
    action_min_duration: float = 0.5
    action_merge_threshold: float = 0.3
    
    websocket_ping_interval: int = 30
    websocket_timeout: int = 60
    
    max_queue_size: int = 100
    max_clients: int = 10
    
    class Config:
        env_file = ".env"


ACTION_CLASSES: Dict[int, str] = {
    0: "跑步",
    1: "跳跃",
    2: "挥手",
    3: "走路",
    4: "站立",
    5: "坐下",
    6: "蹲下",
    7: "其他"
}

ACTION_COLORS: Dict[str, str] = {
    "跑步": "#FF7D00",
    "跳跃": "#00FFA3",
    "挥手": "#165DFF",
    "走路": "#722ED1",
    "站立": "#F53F3F",
    "坐下": "#14C9C9",
    "蹲下": "#FFC53D",
    "其他": "#86909C"
}

settings = Settings()
