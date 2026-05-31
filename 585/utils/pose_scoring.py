import numpy as np
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field
from collections import deque
import json
from enum import Enum


class ScoreLevel(str, Enum):
    EXCELLENT = "Excellent"
    GOOD = "Good"
    FAIR = "Fair"
    POOR = "Poor"
    CRITICAL = "Critical"


@dataclass
class JointAngle:
    name: str
    value: float
    target: Optional[float] = None
    score: Optional[float] = None
    
    def __post_init__(self):
        if self.target is not None:
            self.score = self._compute_score()
    
    def _compute_score(self) -> float:
        diff = abs(self.value - self.target)
        if diff < 5:
            return 100.0
        elif diff < 15:
            return 85.0
        elif diff < 30:
            return 65.0
        elif diff < 45:
            return 40.0
        else:
            return max(0.0, 100.0 - diff)
    
    def get_level(self) -> ScoreLevel:
        if self.score >= 85:
            return ScoreLevel.EXCELLENT
        elif self.score >= 70:
            return ScoreLevel.GOOD
        elif self.score >= 50:
            return ScoreLevel.FAIR
        elif self.score >= 30:
            return ScoreLevel.POOR
        else:
            return ScoreLevel.CRITICAL


@dataclass
class SymmetryScore:
    name: str
    left_value: float
    right_value: float
    symmetry_ratio: float
    score: float
    
    def get_level(self) -> ScoreLevel:
        if self.score >= 90:
            return ScoreLevel.EXCELLENT
        elif self.score >= 75:
            return ScoreLevel.GOOD
        elif self.score >= 60:
            return ScoreLevel.FAIR
        elif self.score >= 40:
            return ScoreLevel.POOR
        else:
            return ScoreLevel.CRITICAL


@dataclass
class PoseScoreResult:
    overall_score: float
    angle_scores: Dict[str, JointAngle]
    symmetry_scores: Dict[str, SymmetryScore]
    temporal_score: float
    feedback: List[str]
    template_match_score: Optional[float] = None
    action_name: Optional[str] = None
    
    def get_level(self) -> ScoreLevel:
        if self.overall_score >= 85:
            return ScoreLevel.EXCELLENT
        elif self.overall_score >= 70:
            return ScoreLevel.GOOD
        elif self.overall_score >= 50:
            return ScoreLevel.FAIR
        elif self.overall_score >= 30:
            return ScoreLevel.POOR
        else:
            return ScoreLevel.CRITICAL
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'overall_score': self.overall_score,
            'level': self.get_level().value,
            'angle_scores': {
                k: {
                    'value': v.value,
                    'target': v.target,
                    'score': v.score,
                    'level': v.get_level().value
                } for k, v in self.angle_scores.items()
            },
            'symmetry_scores': {
                k: {
                    'left': v.left_value,
                    'right': v.right_value,
                    'ratio': v.symmetry_ratio,
                    'score': v.score,
                    'level': v.get_level().value
                } for k, v in self.symmetry_scores.items()
            },
            'temporal_score': self.temporal_score,
            'template_match_score': self.template_match_score,
            'feedback': self.feedback,
            'action_name': self.action_name
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)


class PoseTemplate:
    def __init__(self, name: str, description: str = "",
                 joints_3d: Optional[np.ndarray] = None,
                 joint_angles: Optional[Dict[str, float]] = None,
                 tolerance: float = 15.0):
        self.name = name
        self.description = description
        self.joints_3d = joints_3d
        self.joint_angles = joint_angles or {}
        self.tolerance = tolerance
        
        self.angle_weights = {k: 1.0 for k in self.joint_angles.keys()}
    
    def match(self, joints_3d: np.ndarray, 
              joint_angles: Optional[Dict[str, float]] = None) -> Tuple[float, Dict[str, JointAngle]]:
        if joint_angles is None:
            joint_angles = compute_all_joint_angles(joints_3d)
        
        angle_scores = {}
        total_score = 0.0
        total_weight = 0.0
        
        for angle_name, target_angle in self.joint_angles.items():
            if angle_name in joint_angles:
                weight = self.angle_weights.get(angle_name, 1.0)
                angle_score = JointAngle(
                    name=angle_name,
                    value=joint_angles[angle_name],
                    target=target_angle
                )
                angle_scores[angle_name] = angle_score
                total_score += angle_score.score * weight
                total_weight += weight
        
        if total_weight > 0:
            match_score = total_score / total_weight
        else:
            match_score = 0.0
        
        if self.joints_3d is not None and joints_3d.shape == self.joints_3d.shape:
            mse = np.mean((joints_3d - self.joints_3d) ** 2)
            position_score = max(0.0, 100.0 - mse * 100)
            match_score = 0.7 * match_score + 0.3 * position_score
        
        return match_score, angle_scores


class SquatTemplate(PoseTemplate):
    def __init__(self):
        super().__init__(
            name="深蹲",
            description="标准深蹲动作模板",
            joint_angles={
                'Left_Knee_Angle': 90.0,
                'Right_Knee_Angle': 90.0,
                'Left_Hip_Angle': 90.0,
                'Right_Hip_Angle': 90.0,
                'Back_Lean_Angle': 45.0,
            },
            tolerance=15.0
        )
        
        self.angle_weights = {
            'Left_Knee_Angle': 1.5,
            'Right_Knee_Angle': 1.5,
            'Left_Hip_Angle': 1.2,
            'Right_Hip_Angle': 1.2,
            'Back_Lean_Angle': 1.0,
        }


class PushUpTemplate(PoseTemplate):
    def __init__(self):
        super().__init__(
            name="俯卧撑",
            description="标准俯卧撑动作模板",
            joint_angles={
                'Left_Elbow_Angle': 90.0,
                'Right_Elbow_Angle': 90.0,
                'Left_Shoulder_Angle': 45.0,
                'Right_Shoulder_Angle': 45.0,
                'Body_Alignment': 180.0,
            },
            tolerance=15.0
        )


class StandTemplate(PoseTemplate):
    def __init__(self):
        super().__init__(
            name="站立",
            description="标准站立姿势模板",
            joint_angles={
                'Left_Knee_Angle': 180.0,
                'Right_Knee_Angle': 180.0,
                'Left_Hip_Angle': 180.0,
                'Right_Hip_Angle': 180.0,
                'Back_Lean_Angle': 0.0,
            },
            tolerance=10.0
        )


class RehabArmRaiseTemplate(PoseTemplate):
    def __init__(self):
        super().__init__(
            name="康复-抬臂",
            description="康复训练-手臂侧平举",
            joint_angles={
                'Left_Shoulder_Abduction': 90.0,
                'Right_Shoulder_Abduction': 90.0,
                'Left_Elbow_Angle': 180.0,
                'Right_Elbow_Angle': 180.0,
            },
            tolerance=10.0
        )


def compute_joint_angle(joints: np.ndarray,
                        prev_idx: int, joint_idx: int, next_idx: int) -> Optional[float]:
    if prev_idx >= len(joints) or joint_idx >= len(joints) or next_idx >= len(joints):
        return None
    
    v1 = joints[prev_idx] - joints[joint_idx]
    v2 = joints[next_idx] - joints[joint_idx]
    
    v1 = v1 / (np.linalg.norm(v1) + 1e-6)
    v2 = v2 / (np.linalg.norm(v2) + 1e-6)
    
    dot = np.clip(np.dot(v1, v2), -1.0, 1.0)
    angle = np.degrees(np.arccos(dot))
    
    return float(angle)


def compute_all_joint_angles(joints: np.ndarray) -> Dict[str, float]:
    angles = {}
    
    if joints.shape[0] < 24:
        return angles
    
    angles['Left_Knee_Angle'] = compute_joint_angle(joints, 1, 4, 7) or 0
    angles['Right_Knee_Angle'] = compute_joint_angle(joints, 2, 5, 8) or 0
    angles['Left_Hip_Angle'] = compute_joint_angle(joints, 0, 1, 4) or 0
    angles['Right_Hip_Angle'] = compute_joint_angle(joints, 0, 2, 5) or 0
    angles['Left_Elbow_Angle'] = compute_joint_angle(joints, 16, 18, 20) or 0
    angles['Right_Elbow_Angle'] = compute_joint_angle(joints, 17, 19, 21) or 0
    angles['Left_Shoulder_Angle'] = compute_joint_angle(joints, 9, 16, 18) or 0
    angles['Right_Shoulder_Angle'] = compute_joint_angle(joints, 9, 17, 19) or 0
    
    if 9 < len(joints) and 12 < len(joints) and 15 < len(joints):
        v1 = joints[9] - joints[12]
        v2 = joints[15] - joints[12]
        v1 = v1 / (np.linalg.norm(v1) + 1e-6)
        v2 = v2 / (np.linalg.norm(v2) + 1e-6)
        angles['Head_Spine_Angle'] = float(np.degrees(np.arccos(np.clip(np.dot(v1, v2), -1.0, 1.0))))
    
    if 0 < len(joints) and 3 < len(joints) and 6 < len(joints) and 9 < len(joints):
        spine_vec = joints[9] - joints[0]
        vertical = np.array([0, 1, 0])
        spine_vec = spine_vec / (np.linalg.norm(spine_vec) + 1e-6)
        angles['Back_Lean_Angle'] = float(np.degrees(np.arccos(np.clip(np.dot(spine_vec, vertical), -1.0, 1.0))))
    
    if 16 < len(joints) and 18 < len(joints) and 9 < len(joints):
        arm_vec = joints[18] - joints[16]
        body_vec = joints[16] - joints[9]
        arm_vec = arm_vec / (np.linalg.norm(arm_vec) + 1e-6)
        body_vec = body_vec / (np.linalg.norm(body_vec) + 1e-6)
        angles['Left_Shoulder_Abduction'] = float(np.degrees(np.arccos(np.clip(np.dot(arm_vec, body_vec), -1.0, 1.0))))
    
    if 17 < len(joints) and 19 < len(joints) and 9 < len(joints):
        arm_vec = joints[19] - joints[17]
        body_vec = joints[17] - joints[9]
        arm_vec = arm_vec / (np.linalg.norm(arm_vec) + 1e-6)
        body_vec = body_vec / (np.linalg.norm(body_vec) + 1e-6)
        angles['Right_Shoulder_Abduction'] = float(np.degrees(np.arccos(np.clip(np.dot(arm_vec, body_vec), -1.0, 1.0))))
    
    if 9 < len(joints) and 15 < len(joints) and 0 < len(joints):
        head_to_feet = joints[15] - joints[0]
        head_to_feet = head_to_feet / (np.linalg.norm(head_to_feet) + 1e-6)
        vertical = np.array([0, 1, 0])
        angles['Body_Alignment'] = float(np.degrees(np.arccos(np.clip(np.dot(head_to_feet, vertical), -1.0, 1.0))))
    
    return angles


def compute_symmetry_scores(angles: Dict[str, float]) -> Dict[str, SymmetryScore]:
    symmetry_scores = {}
    
    pairs = [
        ('Knee', 'Left_Knee_Angle', 'Right_Knee_Angle'),
        ('Hip', 'Left_Hip_Angle', 'Right_Hip_Angle'),
        ('Elbow', 'Left_Elbow_Angle', 'Right_Elbow_Angle'),
        ('Shoulder', 'Left_Shoulder_Angle', 'Right_Shoulder_Angle'),
        ('Shoulder_Abduction', 'Left_Shoulder_Abduction', 'Right_Shoulder_Abduction'),
    ]
    
    for name, left_key, right_key in pairs:
        if left_key in angles and right_key in angles:
            left_val = angles[left_key]
            right_val = angles[right_key]
            
            max_val = max(abs(left_val), abs(right_val), 1e-6)
            diff = abs(left_val - right_val)
            symmetry_ratio = 1.0 - (diff / max_val)
            symmetry_ratio = max(0.0, min(1.0, symmetry_ratio))
            
            score = symmetry_ratio * 100.0
            
            symmetry_scores[name] = SymmetryScore(
                name=name,
                left_value=left_val,
                right_value=right_val,
                symmetry_ratio=symmetry_ratio,
                score=score
            )
    
    return symmetry_scores


class TemporalSmoother:
    def __init__(self, window_size: int = 5):
        self.window_size = window_size
        self.score_history = deque(maxlen=window_size)
        self.jerk_history = deque(maxlen=window_size)
        self.prev_velocity = None
        self.prev_acceleration = None
    
    def update(self, joints_3d: np.ndarray) -> Tuple[float, float]:
        if self.prev_velocity is None:
            if joints_3d.ndim == 3:
                joints_3d = joints_3d[0]
            self.prev_velocity = np.zeros_like(joints_3d)
            self.prev_acceleration = np.zeros_like(joints_3d)
            return 100.0, 100.0
        
        if joints_3d.ndim == 3:
            joints_3d = joints_3d[0]
        
        velocity = np.gradient(joints_3d, axis=0)
        acceleration = np.gradient(velocity, axis=0)
        jerk = np.gradient(acceleration, axis=0)
        
        jerk_norm = np.linalg.norm(jerk)
        smoothness_score = max(0.0, 100.0 - jerk_norm * 50)
        
        velocity_norm = np.linalg.norm(velocity - self.prev_velocity)
        acceleration_norm = np.linalg.norm(acceleration - self.prev_acceleration)
        continuity_score = max(0.0, 100.0 - velocity_norm * 10 - acceleration_norm * 5)
        
        self.prev_velocity = velocity
        self.prev_acceleration = acceleration
        
        self.jerk_history.append(jerk_norm)
        avg_smoothness = 100.0 - (sum(self.jerk_history) / len(self.jerk_history)) * 50
        avg_smoothness = max(0.0, avg_smoothness)
        
        self.score_history.append(continuity_score)
        avg_continuity = sum(self.score_history) / len(self.score_history)
        
        return avg_smoothness, avg_continuity
    
    def reset(self):
        self.score_history.clear()
        self.jerk_history.clear()
        self.prev_velocity = None
        self.prev_acceleration = None


class PoseScorer:
    def __init__(self, templates: Optional[List[PoseTemplate]] = None):
        self.templates = templates or self._get_default_templates()
        self.temporal_smoother = TemporalSmoother()
        self.score_history = deque(maxlen=100)
        
        self.angle_weight = 0.4
        self.symmetry_weight = 0.3
        self.temporal_weight = 0.2
        self.template_weight = 0.1
    
    def _get_default_templates(self) -> List[PoseTemplate]:
        return [
            SquatTemplate(),
            PushUpTemplate(),
            StandTemplate(),
            RehabArmRaiseTemplate(),
        ]
    
    def _find_matching_template(self, joints_3d: np.ndarray,
                                 action_name: Optional[str] = None) -> Optional[PoseTemplate]:
        if action_name:
            for template in self.templates:
                if action_name.lower() in template.name.lower():
                    return template
        
        angles = compute_all_joint_angles(joints_3d)
        best_score = -1
        best_template = None
        
        for template in self.templates:
            score, _ = template.match(joints_3d, angles)
            if score > best_score:
                best_score = score
                best_template = template
        
        return best_template if best_score > 50 else None
    
    def _generate_feedback(self, joint_angles: Dict[str, JointAngle],
                           symmetry_scores: Dict[str, SymmetryScore],
                           temporal_score: float) -> List[str]:
        feedback = []
        
        for name, angle in joint_angles.items():
            if angle.target is not None:
                diff = angle.value - angle.target
                if abs(diff) > angle._compute_score():
                    if diff > 0:
                        feedback.append(f"[警告] {name}过大 ({angle.value:.1f}°，目标 {angle.target}°)")
                    else:
                        feedback.append(f"[警告] {name}过小 ({angle.value:.1f}°，目标 {angle.target}°)")
        
        for name, sym in symmetry_scores.items():
            if sym.score < 70:
                feedback.append(f"[警告] {name}不对称 (左 {sym.left_value:.1f}° vs 右 {sym.right_value:.1f}°)")
        
        if temporal_score < 50:
            feedback.append("[建议] 动作不够流畅，请保持匀速运动")
        
        if len(feedback) == 0:
            feedback.append("[OK] 动作标准，继续保持！")
        
        return feedback
    
    def score_pose(self, joints_3d: np.ndarray,
                   action_name: Optional[str] = None) -> PoseScoreResult:
        if joints_3d.ndim == 3:
            joints_3d = joints_3d[0]
        
        if joints_3d.shape[0] < 18:
            raise ValueError(f"需要至少18个关节点，当前有 {joints_3d.shape[0]} 个")
        
        current_angles = compute_all_joint_angles(joints_3d)
        template = self._find_matching_template(joints_3d, action_name)
        
        if template is not None:
            template_match_score, angle_scores = template.match(joints_3d, current_angles)
            action_used = template.name
        else:
            template_match_score = None
            angle_scores = {k: JointAngle(name=k, value=v) for k, v in current_angles.items()}
            action_used = action_name or "Unknown"
        
        symmetry_scores = compute_symmetry_scores(current_angles)
        smoothness, continuity = self.temporal_smoother.update(joints_3d)
        temporal_score = 0.6 * smoothness + 0.4 * continuity
        
        if angle_scores:
            avg_angle_score = np.mean([a.score if a.score is not None else 0 
                                       for a in angle_scores.values()])
        else:
            avg_angle_score = 0.0
        
        if symmetry_scores:
            avg_symmetry_score = np.mean([s.score for s in symmetry_scores.values()])
        else:
            avg_symmetry_score = 0.0
        
        components = []
        weights = []
        
        components.append(avg_angle_score)
        weights.append(self.angle_weight)
        
        components.append(avg_symmetry_score)
        weights.append(self.symmetry_weight)
        
        components.append(temporal_score)
        weights.append(self.temporal_weight)
        
        if template_match_score is not None:
            components.append(template_match_score)
            weights.append(self.template_weight)
        
        total_weight = sum(weights)
        if total_weight > 0:
            overall_score = sum(c * w for c, w in zip(components, weights)) / total_weight
        else:
            overall_score = 0.0
        
        feedback = self._generate_feedback(
            {k: v for k, v in angle_scores.items() if v.target is not None},
            symmetry_scores,
            temporal_score
        )
        
        result = PoseScoreResult(
            overall_score=float(overall_score),
            angle_scores=angle_scores,
            symmetry_scores=symmetry_scores,
            temporal_score=float(temporal_score),
            feedback=feedback,
            template_match_score=template_match_score,
            action_name=action_used
        )
        
        self.score_history.append(result)
        
        return result
    
    def get_average_score(self, window_size: int = 10) -> float:
        if len(self.score_history) == 0:
            return 0.0
        
        recent = list(self.score_history)[-window_size:]
        return float(np.mean([s.overall_score for s in recent]))
    
    def reset(self):
        self.temporal_smoother.reset()
        self.score_history.clear()
    
    def get_score_history(self) -> List[PoseScoreResult]:
        return list(self.score_history)
