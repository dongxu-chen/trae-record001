import numpy as np
import cv2
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass, field
from enum import Enum


class StrokeType(Enum):
    HENG = "横"
    SHU = "竖"
    PIE = "撇"
    NA = "捺"
    DIAN = "点"
    ZHE = "折"
    GOU = "钩"
    WAN = "弯"
    TI = "提"


@dataclass
class Stroke:
    stroke_type: StrokeType
    points: np.ndarray
    start_point: Tuple[float, float]
    end_point: Tuple[float, float]
    length: float
    angle: float
    curvature: float = 0.0
    
    def to_dict(self) -> dict:
        return {
            'type': self.stroke_type.value,
            'start': self.start_point,
            'end': self.end_point,
            'length': self.length,
            'angle': self.angle,
            'curvature': self.curvature
        }


@dataclass
class CharacterStructure:
    char: str
    strokes: List[Stroke] = field(default_factory=list)
    bounding_box: Tuple[float, float, float, float] = (0, 0, 0, 0)
    center: Tuple[float, float] = (0, 0)
    aspect_ratio: float = 1.0
    stroke_count: int = 0
    
    def analyze_structure(self):
        if not self.strokes:
            return
        
        all_points = np.vstack([s.points for s in self.strokes])
        x_min, y_min = np.min(all_points, axis=0)
        x_max, y_max = np.max(all_points, axis=0)
        self.bounding_box = (x_min, y_min, x_max, y_max)
        self.center = ((x_min + x_max) / 2, (y_min + y_max) / 2)
        
        width = x_max - x_min
        height = y_max - y_min
        self.aspect_ratio = width / height if height > 0 else 1.0
        
        self.stroke_count = len(self.strokes)


class StrokeDecomposer:
    def __init__(self):
        self.angle_threshold = 30
        self.curvature_threshold = 0.5
    
    def analyze_image(self, binary_image: np.ndarray) -> CharacterStructure:
        structure = CharacterStructure(char='')
        
        skeleton = self._extract_skeleton(binary_image)
        if skeleton is None:
            return structure
        
        critical_points = self._detect_critical_points(skeleton)
        stroke_segments = self._decompose_strokes(skeleton, critical_points)
        
        for segment in stroke_segments:
            stroke = self._classify_stroke(segment)
            if stroke:
                structure.strokes.append(stroke)
        
        structure.analyze_structure()
        return structure
    
    def _extract_skeleton(self, binary_image: np.ndarray) -> Optional[np.ndarray]:
        if binary_image is None or len(binary_image.shape) != 2:
            return None
        
        _, binary = cv2.threshold(binary_image, 127, 255, cv2.THRESH_BINARY)
        
        skeleton = np.zeros_like(binary, dtype=np.uint8)
        element = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))
        
        img = binary.copy()
        while True:
            open_img = cv2.morphologyEx(img, cv2.MORPH_OPEN, element)
            temp = cv2.subtract(img, open_img)
            eroded = cv2.erode(img, element)
            skeleton = cv2.bitwise_or(skeleton, temp)
            img = eroded.copy()
            
            if cv2.countNonZero(img) == 0:
                break
        
        return skeleton
    
    def _detect_critical_points(self, skeleton: np.ndarray) -> List[Tuple[int, int]]:
        critical_points = []
        contours, _ = cv2.findContours(skeleton, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            if len(contour) < 3:
                continue
            
            for i in range(len(contour)):
                prev_idx = (i - 1) % len(contour)
                next_idx = (i + 1) % len(contour)
                
                prev_point = contour[prev_idx][0]
                curr_point = contour[i][0]
                next_point = contour[next_idx][0]
                
                angle = self._calculate_angle(prev_point, curr_point, next_point)
                
                if abs(180 - angle) > self.angle_threshold:
                    critical_points.append(tuple(curr_point))
        
        return list(set(critical_points))
    
    def _calculate_angle(self, p1: np.ndarray, p2: np.ndarray, p3: np.ndarray) -> float:
        v1 = p1 - p2
        v2 = p3 - p2
        
        dot = np.dot(v1, v2)
        norm_v1 = np.linalg.norm(v1)
        norm_v2 = np.linalg.norm(v2)
        
        if norm_v1 == 0 or norm_v2 == 0:
            return 180.0
        
        cos_angle = dot / (norm_v1 * norm_v2)
        cos_angle = max(-1.0, min(1.0, cos_angle))
        
        angle = np.degrees(np.arccos(cos_angle))
        return angle
    
    def _decompose_strokes(self, skeleton: np.ndarray, critical_points: List[Tuple[int, int]]) -> List[np.ndarray]:
        strokes = []
        contours, _ = cv2.findContours(skeleton, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        
        for contour in contours:
            contour_points = contour.reshape(-1, 2)
            
            if len(contour_points) < 5:
                continue
            
            if len(critical_points) == 0:
                strokes.append(contour_points)
                continue
            
            split_indices = [0]
            for i, point in enumerate(contour_points):
                for cp in critical_points:
                    dist = np.linalg.norm(point - np.array(cp))
                    if dist < 3:
                        split_indices.append(i)
                        break
            
            split_indices = sorted(list(set(split_indices)))
            
            for i in range(len(split_indices) - 1):
                start = split_indices[i]
                end = split_indices[i + 1]
                if end - start > 3:
                    strokes.append(contour_points[start:end])
            
            if split_indices[-1] < len(contour_points) - 1:
                strokes.append(contour_points[split_indices[-1]:])
        
        return strokes
    
    def _classify_stroke(self, points: np.ndarray) -> Optional[Stroke]:
        if len(points) < 2:
            return None
        
        start_point = tuple(points[0])
        end_point = tuple(points[-1])
        
        dx = end_point[0] - start_point[0]
        dy = end_point[1] - start_point[1]
        length = np.sqrt(dx**2 + dy**2)
        
        if length < 5:
            return None
        
        angle = np.degrees(np.arctan2(-dy, dx))
        
        curvature = self._calculate_curvature(points)
        
        stroke_type = self._determine_stroke_type(angle, curvature, length)
        
        return Stroke(
            stroke_type=stroke_type,
            points=points,
            start_point=start_point,
            end_point=end_point,
            length=length,
            angle=angle,
            curvature=curvature
        )
    
    def _calculate_curvature(self, points: np.ndarray) -> float:
        if len(points) < 3:
            return 0.0
        
        total_angle_change = 0.0
        for i in range(1, len(points) - 1):
            angle = self._calculate_angle(points[i-1], points[i], points[i+1])
            total_angle_change += abs(180 - angle)
        
        return total_angle_change / (len(points) - 2)
    
    def _determine_stroke_type(self, angle: float, curvature: float, length: float) -> StrokeType:
        if curvature > self.curvature_threshold * 10:
            if angle < -45 and angle > -135:
                return StrokeType.GOU
            elif abs(angle) > 150 or abs(angle) < 30:
                return StrokeType.ZHE
            else:
                return StrokeType.WAN
        
        angle_abs = abs(angle)
        
        if angle_abs < 15:
            return StrokeType.HENG
        elif angle_abs > 75 and angle_abs < 105:
            return StrokeType.SHU
        elif angle > 105 and angle < 165:
            return StrokeType.PIE
        elif angle > 15 and angle < 75:
            return StrokeType.TI
        elif angle > -165 and angle < -105:
            return StrokeType.NA
        elif length < 15:
            return StrokeType.DIAN
        else:
            return StrokeType.DIAN


class StructureConstraint:
    def __init__(self):
        self.min_stroke_length = 10
        self.max_angle_deviation = 45
        self.aspect_ratio_range = (0.5, 2.0)
    
    def validate_character(self, structure: CharacterStructure) -> Tuple[bool, List[str]]:
        issues = []
        valid = True
        
        if structure.stroke_count == 0:
            issues.append("未检测到笔画")
            valid = False
        
        for i, stroke in enumerate(structure.strokes):
            if stroke.length < self.min_stroke_length:
                issues.append(f"笔画{i+1}过短")
                valid = False
        
        aspect_ratio = structure.aspect_ratio
        if aspect_ratio < self.aspect_ratio_range[0] or aspect_ratio > self.aspect_ratio_range[1]:
            issues.append(f"宽高比异常: {aspect_ratio:.2f}")
            valid = False
        
        return valid, issues
    
    def apply_constraints(self, points: np.ndarray, structure: CharacterStructure) -> np.ndarray:
        if points is None or len(points) == 0:
            return points
        
        constrained_points = points.copy()
        
        if structure.bounding_box != (0, 0, 0, 0):
            x_min, y_min, x_max, y_max = structure.bounding_box
            target_center = ((x_min + x_max) / 2, (y_min + y_max) / 2)
            
            current_center = np.mean(constrained_points, axis=0)
            offset = np.array(target_center) - current_center
            constrained_points = constrained_points + offset
        
        target_aspect = structure.aspect_ratio
        if target_aspect > 0:
            current_bounds = self._get_bounds(constrained_points)
            current_aspect = (current_bounds[2] - current_bounds[0]) / (current_bounds[3] - current_bounds[1]) if current_bounds[3] - current_bounds[1] > 0 else 1.0
            
            scale_x = np.sqrt(target_aspect / current_aspect) if current_aspect > 0 else 1.0
            scale_y = 1.0 / scale_x
            
            center = np.mean(constrained_points, axis=0)
            constrained_points = (constrained_points - center) * np.array([scale_x, scale_y]) + center
        
        return constrained_points
    
    def _get_bounds(self, points: np.ndarray) -> Tuple[float, float, float, float]:
        x_min, y_min = np.min(points, axis=0)
        x_max, y_max = np.max(points, axis=0)
        return (x_min, y_min, x_max, y_max)


class StrokeBasedGenerator:
    def __init__(self):
        self.decomposer = StrokeDecomposer()
        self.constraint = StructureConstraint()
        self.stroke_templates: Dict[str, List[Stroke]] = {}
    
    def learn_stroke_templates(self, char: str, binary_image: np.ndarray) -> bool:
        structure = self.decomposer.analyze_image(binary_image)
        
        if structure.stroke_count == 0:
            return False
        
        self.stroke_templates[char] = structure.strokes
        return True
    
    def generate_with_structure(self, base_points: np.ndarray, reference_char: str) -> np.ndarray:
        if base_points is None or len(base_points) == 0:
            return base_points
        
        if reference_char not in self.stroke_templates:
            return base_points
        
        reference_strokes = self.stroke_templates[reference_char]
        
        generated = base_points.copy()
        
        if reference_strokes:
            avg_length = np.mean([s.length for s in reference_strokes])
            avg_angle = np.mean([s.angle for s in reference_strokes])
            
            current_center = np.mean(generated, axis=0)
            generated = generated - current_center
            
            current_bounds = self._get_bounds(generated)
            current_size = max(current_bounds[2] - current_bounds[0], current_bounds[3] - current_bounds[1])
            
            if current_size > 0:
                target_size = avg_length * 3
                scale = target_size / current_size
                generated = generated * scale
            
            rotation = np.radians(-avg_angle * 0.1)
            rotation_matrix = np.array([
                [np.cos(rotation), -np.sin(rotation)],
                [np.sin(rotation), np.cos(rotation)]
            ])
            generated = np.dot(generated, rotation_matrix.T)
            
            generated = generated + current_center
        
        return generated
    
    def _get_bounds(self, points: np.ndarray) -> Tuple[float, float, float, float]:
        x_min, y_min = np.min(points, axis=0)
        x_max, y_max = np.max(points, axis=0)
        return (x_min, y_min, x_max, y_max)
    
    def get_structure_report(self, char: str, binary_image: np.ndarray) -> dict:
        structure = self.decomposer.analyze_image(binary_image)
        valid, issues = self.constraint.validate_character(structure)
        
        return {
            'char': char,
            'stroke_count': structure.stroke_count,
            'aspect_ratio': structure.aspect_ratio,
            'strokes': [s.to_dict() for s in structure.strokes],
            'valid': valid,
            'issues': issues
        }
