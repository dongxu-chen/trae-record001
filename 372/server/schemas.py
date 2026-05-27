from pydantic import BaseModel
from typing import List, Optional, Literal, Union
from enum import Enum

class AnnotationType(str, Enum):
    POLYGON = "polygon"
    POINT = "point"
    RECTANGLE = "rectangle"
    BRUSH = "brush"
    SAM = "sam"

class Point(BaseModel):
    x: float
    y: float

class BaseAnnotation(BaseModel):
    id: str
    type: AnnotationType
    label: str
    color: str
    visible: bool = True
    createdAt: int
    pixelArea: Optional[int] = None
    pixelPercentage: Optional[float] = None

class PolygonAnnotation(BaseAnnotation):
    type: Literal[AnnotationType.POLYGON]
    points: List[Point]
    closed: bool = True

class PointAnnotation(BaseAnnotation):
    type: Literal[AnnotationType.POINT]
    position: Point
    radius: float = 3.0

class RectangleAnnotation(BaseAnnotation):
    type: Literal[AnnotationType.RECTANGLE]
    x: float
    y: float
    width: float
    height: float

class BrushAnnotation(BaseAnnotation):
    type: Literal[AnnotationType.BRUSH]
    points: List[Point]
    strokeWidth: float = 5.0

class SAMAnnotation(BaseAnnotation):
    type: Literal[AnnotationType.SAM]
    mask: List[int]
    width: int
    height: int

Annotation = Union[PolygonAnnotation, PointAnnotation, RectangleAnnotation, BrushAnnotation, SAMAnnotation]

class SAMRequest(BaseModel):
    imageId: str
    point: Point
    mode: str = "click"

class SAMResponse(BaseModel):
    mask: List[int]
    width: int
    height: int
    confidence: float

class ImageInfo(BaseModel):
    id: str
    filename: str
    width: int
    height: int
    uploadedAt: int
    url: Optional[str] = None

class ExportRequest(BaseModel):
    imageId: str
    annotations: List[dict]
    format: str = "json"

class SAMStatus(BaseModel):
    loaded: bool
    modelType: str
    error: Optional[str] = None

class WsClientMessage(BaseModel):
    type: str
    payload: Union[SAMRequest, dict, None] = None

class WsServerMessage(BaseModel):
    type: str
    payload: Union[SAMResponse, dict, None] = None
