from pydantic import BaseModel, Field
from typing import List, Optional, Tuple
from enum import Enum


class MessageType(str, Enum):
    START = "start"
    STOP = "stop"
    PAUSE = "pause"
    RESUME = "resume"
    CONFIG = "config"
    RESULT = "result"
    TEMPORAL = "temporal"
    FRAME = "frame"
    STATUS = "status"
    ERROR = "error"
    PREDICTION = "prediction"
    WEAKLY_LABEL = "weakly_label"
    PSEUDO_GT = "pseudo_gt"


class SourceType(str, Enum):
    CAMERA = "camera"
    FILE = "file"


class ModelType(str, Enum):
    TIMESFORMER = "timesformer"
    VIDEOMAE = "videomae"
    MOBILENETV2 = "mobilenetv2"
    SHUFFLENETV2 = "shufflenetv2"
    LIGHTWEIGHT = "lightweight"


class StatusType(str, Enum):
    IDLE = "idle"
    CONNECTING = "connecting"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"


class BaseMessage(BaseModel):
    type: MessageType


class StartMessage(BaseMessage):
    type: MessageType = MessageType.START
    source: SourceType
    camera_index: Optional[int] = Field(default=0)
    file_path: Optional[str] = None
    model_type: ModelType = ModelType.TIMESFORMER
    fps: int = Field(default=16, ge=1, le=60)
    confidence_threshold: float = Field(default=0.5, ge=0.0, le=1.0)


class StopMessage(BaseMessage):
    type: MessageType = MessageType.STOP


class PauseMessage(BaseMessage):
    type: MessageType = MessageType.PAUSE


class ResumeMessage(BaseMessage):
    type: MessageType = MessageType.RESUME


class ConfigMessage(BaseMessage):
    type: MessageType = MessageType.CONFIG
    confidence_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    model_type: Optional[ModelType] = None


class Prediction(BaseModel):
    action: str
    confidence: float
    bounding_box: Optional[Tuple[float, float, float, float]] = None


class RecognitionResult(BaseMessage):
    type: MessageType = MessageType.RESULT
    timestamp: float
    frame_index: int
    predictions: List[Prediction]
    fps: float
    latency: float


class TemporalResult(BaseMessage):
    type: MessageType = MessageType.TEMPORAL
    action: str
    start_time: float
    end_time: float
    duration: float
    avg_confidence: float


class FrameData(BaseMessage):
    type: MessageType = MessageType.FRAME
    timestamp: float
    width: int
    height: int


class StatusUpdate(BaseMessage):
    type: MessageType = MessageType.STATUS
    status: StatusType
    message: Optional[str] = None


class PredictionItem(BaseModel):
    class_idx: int
    action: str
    confidence: float
    prediction_step: int


class ActionPrediction(BaseMessage):
    type: MessageType = MessageType.PREDICTION
    predictions: List[PredictionItem]
    multi_step_predictions: Optional[List[List[PredictionItem]]] = None
    transition_matrix: Optional[List[List[float]]] = None
    prediction_confidence: float
    is_ready: bool


class WeaklyLabelMessage(BaseMessage):
    type: MessageType = MessageType.WEAKLY_LABEL
    video_level_label: int
    timestamp: float


class PseudoGroundTruth(BaseMessage):
    type: MessageType = MessageType.PSEUDO_GT
    num_segments: int
    segments: List[dict]
    video_level_labels: List[int]
    method: str


class ErrorMessage(BaseMessage):
    type: MessageType = MessageType.ERROR
    error_code: int
    error_message: str
