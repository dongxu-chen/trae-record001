import numpy as np
import torch
from typing import List, Optional, Tuple, Dict
from dataclasses import dataclass, field
from collections import deque


@dataclass
class OcclusionInfo:
    joint_id: int
    is_occluded: bool
    confidence: float
    occlusion_reason: str
    visible_neighbors: List[int]


@dataclass
class PoseCompletionResult:
    joints_3d: np.ndarray
    occlusion_mask: np.ndarray
    completion_confidence: np.ndarray
    used_prior: bool


class PosePriorModel:
    def __init__(self, num_joints: int = 24, device: str = 'cpu'):
        self.num_joints = num_joints
        self.device = device
        
        self.SMPL_SKELETON = [
            (0, 1), (0, 2), (0, 3), (1, 4), (2, 5), (3, 6),
            (4, 7), (5, 8), (6, 9), (7, 10), (8, 11), (9, 12),
            (9, 13), (9, 14), (12, 15), (13, 16), (14, 17),
            (16, 18), (17, 19), (18, 20), (19, 21), (20, 22), (21, 23)
        ]
        
        self.joint_parents = {}
        for parent, child in self.SMPL_SKELETON:
            self.joint_parents[child] = parent
        self.joint_parents[0] = -1
        
        self.BONE_LENGTHS_MEAN = np.array([
            0.12, 0.12, 0.05, 0.38, 0.38, 0.05,
            0.40, 0.40, 0.05, 0.12, 0.12, 0.08,
            0.12, 0.12, 0.15, 0.18, 0.18,
            0.28, 0.28, 0.24, 0.24, 0.08, 0.08
        ])
        
        self.BONE_LENGTHS_STD = np.array([
            0.02, 0.02, 0.01, 0.05, 0.05, 0.01,
            0.05, 0.05, 0.01, 0.02, 0.02, 0.02,
            0.02, 0.02, 0.03, 0.03, 0.03,
            0.04, 0.04, 0.03, 0.03, 0.02, 0.02
        ])
    
    def get_bone_lengths(self, joints_3d: np.ndarray) -> np.ndarray:
        if joints_3d.ndim == 3:
            joints_3d = joints_3d[0]
        
        bone_lengths = np.zeros(len(self.SMPL_SKELETON))
        for i, (parent, child) in enumerate(self.SMPL_SKELETON):
            if parent < len(joints_3d) and child < len(joints_3d):
                bone_lengths[i] = np.linalg.norm(joints_3d[child] - joints_3d[parent])
        
        return bone_lengths
    
    def estimate_bone_lengths(self, visible_joints: np.ndarray, 
                                visibility_mask: np.ndarray) -> np.ndarray:
        estimated_lengths = self.BONE_LENGTHS_MEAN.copy()
        
        for i, (parent, child) in enumerate(self.SMPL_SKELETON):
            if (visibility_mask[parent] and visibility_mask[child] and 
                parent < len(visible_joints) and child < len(visible_joints)):
                estimated_lengths[i] = np.linalg.norm(
                    visible_joints[child] - visible_joints[parent]
                )
        
        return estimated_lengths


class OcclusionDetector:
    def __init__(self, num_joints: int = 24, 
                 conf_threshold: float = 0.3,
                 temporal_window: int = 5):
        self.num_joints = num_joints
        self.conf_threshold = conf_threshold
        self.temporal_window = temporal_window
        
        self.confidence_history = {}
    
    def detect_occlusions_2d(self, keypoints_2d: List[Optional[object]]) -> np.ndarray:
        occlusion_mask = np.ones(self.num_joints, dtype=bool)
        
        for i, kp in enumerate(keypoints_2d):
            if i >= self.num_joints:
                break
            if kp is None or kp.confidence < self.conf_threshold:
                occlusion_mask[i] = False
        
        return occlusion_mask
    
    def detect_occlusions_3d(self, joints_3d: np.ndarray, 
                              history_joints: List[np.ndarray],
                              reproj_error: Optional[np.ndarray] = None) -> np.ndarray:
        if joints_3d.ndim == 3:
            joints_3d = joints_3d[0]
        
        occlusion_mask = np.ones(min(len(joints_3d), self.num_joints), dtype=bool)
        
        if len(history_joints) < 2:
            return occlusion_mask
        
        recent_joints = history_joints[-self.temporal_window:]
        if len(recent_joints) < 2:
            return occlusion_mask
        
        velocities = []
        for i in range(1, len(recent_joints)):
            if len(recent_joints[i]) == len(recent_joints[i-1]):
                vel = np.linalg.norm(recent_joints[i] - recent_joints[i-1], axis=1)
                velocities.append(vel)
        
        if len(velocities) == 0:
            return occlusion_mask
        
        mean_vel = np.mean(velocities, axis=0)
        std_vel = np.std(velocities, axis=0) + 1e-6
        
        if len(recent_joints) > 0 and len(recent_joints[-1]) == len(joints_3d):
            current_vel = np.linalg.norm(joints_3d - recent_joints[-1], axis=1)
            
            z_scores = np.abs(current_vel - mean_vel) / (std_vel + 1e-6)
            occlusion_mask[z_scores > 3.0] = False
        
        if reproj_error is not None:
            reproj_normalized = reproj_error / (np.mean(reproj_error) + 1e-6)
            occlusion_mask[reproj_normalized > 2.0] = False
        
        return occlusion_mask
    
    def update_history(self, track_id: int, joints_3d: np.ndarray):
        if track_id not in self.confidence_history:
            self.confidence_history[track_id] = deque(maxlen=self.temporal_window)
        
        if joints_3d.ndim == 3:
            joints_3d = joints_3d[0]
        
        self.confidence_history[track_id].append(joints_3d.copy())
    
    def get_history(self, track_id: int) -> List[np.ndarray]:
        return list(self.confidence_history.get(track_id, []))
    
    def reset(self, track_id: Optional[int] = None):
        if track_id is not None:
            if track_id in self.confidence_history:
                del self.confidence_history[track_id]
        else:
            self.confidence_history.clear()


class PoseCompleter:
    def __init__(self, num_joints: int = 24, device: str = 'cpu'):
        self.num_joints = num_joints
        self.device = device
        self.prior = PosePriorModel(num_joints, device)
    
    def complete_pose(self, joints_3d: np.ndarray, 
                       occlusion_mask: np.ndarray,
                       bone_lengths: Optional[np.ndarray] = None) -> PoseCompletionResult:
        if joints_3d.ndim == 3:
            joints_3d = joints_3d[0]
        
        completed_joints = joints_3d.copy()
        completion_confidence = np.ones(self.num_joints)
        used_prior = False
        
        if bone_lengths is None:
            bone_lengths = self.prior.estimate_bone_lengths(joints_3d, occlusion_mask)
        
        root_visible = occlusion_mask[0]
        if not root_visible:
            visible_roots = [i for i in range(min(4, len(occlusion_mask))) if occlusion_mask[i]]
            if len(visible_roots) > 0:
                completed_joints[0] = np.mean(completed_joints[visible_roots], axis=0)
                completion_confidence[0] = 0.5
                used_prior = True
        
        order = list(range(1, self.num_joints))
        order.sort(key=lambda x: self._get_depth(x))
        
        for joint_id in order:
            if joint_id >= len(occlusion_mask):
                continue
                
            if not occlusion_mask[joint_id]:
                parent_id = self.prior.joint_parents.get(joint_id, -1)
                
                if parent_id != -1 and parent_id < len(completed_joints):
                    completed_joints[joint_id] = self._complete_from_parent(
                        completed_joints, joint_id, parent_id, bone_lengths
                    )
                    completion_confidence[joint_id] = 0.7
                    used_prior = True
                else:
                    visible_neighbors = self._get_visible_neighbors(joint_id, occlusion_mask)
                    if len(visible_neighbors) > 0:
                        completed_joints[joint_id] = np.mean(
                            completed_joints[visible_neighbors], axis=0
                        )
                        completion_confidence[joint_id] = 0.5
                        used_prior = True
        
        return PoseCompletionResult(
            joints_3d=completed_joints,
            occlusion_mask=occlusion_mask,
            completion_confidence=completion_confidence,
            used_prior=used_prior
        )
    
    def _get_depth(self, joint_id: int) -> int:
        depth = 0
        current = joint_id
        while current != 0 and current in self.prior.joint_parents:
            current = self.prior.joint_parents[current]
            depth += 1
            if depth > 10:
                break
        return depth
    
    def _complete_from_parent(self, joints: np.ndarray, joint_id: int, 
                               parent_id: int, bone_lengths: np.ndarray) -> np.ndarray:
        parent_pos = joints[parent_id]
        
        bone_idx = -1
        for i, (p, c) in enumerate(self.prior.SMPL_SKELETON):
            if c == joint_id and p == parent_id:
                bone_idx = i
                break
        
        if bone_idx >= 0 and bone_idx < len(bone_lengths):
            bone_len = bone_lengths[bone_idx]
        else:
            bone_len = 0.2
        
        direction = np.array([0, -1, 0])
        
        if joint_id in [1, 4, 7, 10]:
            direction = np.array([0.3, -0.5, 0])
        elif joint_id in [2, 5, 8, 11]:
            direction = np.array([-0.3, -0.5, 0])
        elif joint_id in [13, 16, 18, 20, 22]:
            direction = np.array([0.8, 0, 0])
        elif joint_id in [14, 17, 19, 21, 23]:
            direction = np.array([-0.8, 0, 0])
        
        direction = direction / (np.linalg.norm(direction) + 1e-6)
        
        return parent_pos + direction * bone_len
    
    def _get_visible_neighbors(self, joint_id: int, 
                                occlusion_mask: np.ndarray) -> List[int]:
        neighbors = []
        
        for parent, child in self.prior.SMPL_SKELETON:
            if parent == joint_id and child < len(occlusion_mask) and occlusion_mask[child]:
                neighbors.append(child)
            if child == joint_id and parent < len(occlusion_mask) and occlusion_mask[parent]:
                neighbors.append(parent)
        
        return neighbors


class TemporalPoseCompleter:
    def __init__(self, num_joints: int = 24, 
                 max_history: int = 30,
                 device: str = 'cpu'):
        self.num_joints = num_joints
        self.max_history = max_history
        self.device = device
        
        self.occlusion_detector = OcclusionDetector(num_joints)
        self.pose_completer = PoseCompleter(num_joints, device)
        self.pose_history = {}
    
    def process_frame(self, track_id: int, joints_3d: np.ndarray,
                       keypoints_2d: Optional[List[Optional[object]]] = None,
                       reproj_error: Optional[np.ndarray] = None) -> PoseCompletionResult:
        if joints_3d.ndim == 3:
            joints_3d = joints_3d[0]
        
        self.occlusion_detector.update_history(track_id, joints_3d)
        history = self.occlusion_detector.get_history(track_id)
        
        occlusion_mask_2d = np.ones(min(len(joints_3d), self.num_joints), dtype=bool)
        if keypoints_2d is not None:
            occlusion_mask_2d = self.occlusion_detector.detect_occlusions_2d(keypoints_2d)
            if len(occlusion_mask_2d) > len(joints_3d):
                occlusion_mask_2d = occlusion_mask_2d[:len(joints_3d)]
        
        occlusion_mask_3d = self.occlusion_detector.detect_occlusions_3d(
            joints_3d, history[:-1], reproj_error
        )
        
        combined_mask = occlusion_mask_2d & occlusion_mask_3d[:len(occlusion_mask_2d)]
        
        bone_lengths = self._estimate_bone_lengths_from_history(track_id, combined_mask)
        
        result = self.pose_completer.complete_pose(
            joints_3d, combined_mask, bone_lengths
        )
        
        if track_id not in self.pose_history:
            self.pose_history[track_id] = deque(maxlen=self.max_history)
        self.pose_history[track_id].append(result.joints_3d)
        
        return result
    
    def _estimate_bone_lengths_from_history(self, track_id: int, 
                                              occlusion_mask: np.ndarray) -> np.ndarray:
        history = self.pose_history.get(track_id, deque())
        
        if len(history) == 0:
            return self.pose_completer.prior.BONE_LENGTHS_MEAN
        
        all_bone_lengths = []
        for joints in history:
            bone_lengths = self.pose_completer.prior.get_bone_lengths(joints)
            all_bone_lengths.append(bone_lengths)
        
        if len(all_bone_lengths) > 0:
            return np.mean(all_bone_lengths, axis=0)
        
        return self.pose_completer.prior.BONE_LENGTHS_MEAN
    
    def reset(self, track_id: Optional[int] = None):
        self.occlusion_detector.reset(track_id)
        if track_id is not None:
            if track_id in self.pose_history:
                del self.pose_history[track_id]
        else:
            self.pose_history.clear()


class SymmetryAwareCompleter:
    def __init__(self, num_joints: int = 24):
        self.num_joints = num_joints
        
        self.symmetric_pairs = [
            (1, 2), (4, 5), (7, 8), (10, 11),
            (13, 14), (16, 17), (18, 19), (20, 21), (22, 23)
        ]
        
        self.left_joints = [1, 4, 7, 10, 13, 16, 18, 20, 22]
        self.right_joints = [2, 5, 8, 11, 14, 17, 19, 21, 23]
    
    def apply_symmetry(self, joints_3d: np.ndarray, 
                        occlusion_mask: np.ndarray) -> np.ndarray:
        if joints_3d.ndim == 3:
            joints_3d = joints_3d[0]
        
        symmetric_joints = joints_3d.copy()
        
        mid_spine = joints_3d[9] if len(joints_3d) > 9 else np.mean(joints_3d[:4], axis=0)
        
        for left_id, right_id in self.symmetric_pairs:
            if left_id >= len(occlusion_mask) or right_id >= len(occlusion_mask):
                continue
                
            left_visible = occlusion_mask[left_id]
            right_visible = occlusion_mask[right_id]
            
            if left_visible and not right_visible:
                rel_vec = joints_3d[left_id] - mid_spine
                rel_vec[0] = -rel_vec[0]
                symmetric_joints[right_id] = mid_spine + rel_vec
            elif right_visible and not left_visible:
                rel_vec = joints_3d[right_id] - mid_spine
                rel_vec[0] = -rel_vec[0]
                symmetric_joints[left_id] = mid_spine + rel_vec
            elif left_visible and right_visible:
                avg_vec = (joints_3d[left_id] + joints_3d[right_id]) / 2 - mid_spine
                avg_vec[0] = abs(avg_vec[0])
                symmetric_joints[left_id] = mid_spine + np.array([-avg_vec[0], avg_vec[1], avg_vec[2]])
                symmetric_joints[right_id] = mid_spine + avg_vec
        
        return symmetric_joints
