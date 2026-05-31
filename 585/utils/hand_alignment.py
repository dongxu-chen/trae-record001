import numpy as np
import torch
from typing import List, Optional, Tuple, Dict
from dataclasses import dataclass
from scipy.optimize import minimize


@dataclass
class HandAlignmentResult:
    aligned_hand_joints: np.ndarray
    scale_factor: float
    rotation_matrix: np.ndarray
    translation_vector: np.ndarray
    alignment_error: float


class GlobalHandAligner:
    def __init__(self, num_body_joints: int = 24, num_hand_joints: int = 21):
        self.num_body_joints = num_body_joints
        self.num_hand_joints = num_hand_joints
        
        self.SMPL_SKELETON = [
            (0, 1), (0, 2), (0, 3), (1, 4), (2, 5), (3, 6),
            (4, 7), (5, 8), (6, 9), (7, 10), (8, 11), (9, 12),
            (9, 13), (9, 14), (12, 15), (13, 16), (14, 17),
            (16, 18), (17, 19), (18, 20), (19, 21), (20, 22), (21, 23)
        ]
        
        self.BODY_WRIST_INDICES = {
            'right': 21,
            'left': 20
        }
        
        self.HAND_WRIST_INDEX = 0
        
        self.AVERAGE_ARM_LENGTH = 0.55
        self.AVERAGE_HAND_SIZE = 0.18
        
        self.FOREARM_INDICES = {
            'right': (16, 18),
            'left': (17, 19)
        }
        
        self.UPPERARM_INDICES = {
            'right': (14, 16),
            'left': (13, 17)
        }
    
    def compute_body_scale(self, body_joints_3d: np.ndarray) -> float:
        if body_joints_3d.ndim == 3:
            body_joints_3d = body_joints_3d[0]
        
        bone_lengths = []
        for parent, child in self.SMPL_SKELETON:
            if parent < len(body_joints_3d) and child < len(body_joints_3d):
                length = np.linalg.norm(body_joints_3d[child] - body_joints_3d[parent])
                if length > 0.05:
                    bone_lengths.append(length)
        
        if len(bone_lengths) == 0:
            return 1.0
        
        avg_bone_length = np.mean(bone_lengths)
        reference_length = 0.3
        
        return avg_bone_length / reference_length
    
    def compute_arm_orientation(self, body_joints_3d: np.ndarray, 
                                  hand_side: str) -> np.ndarray:
        if body_joints_3d.ndim == 3:
            body_joints_3d = body_joints_3d[0]
        
        shoulder_idx, elbow_idx = self.UPPERARM_INDICES[hand_side]
        _, wrist_idx = self.FOREARM_INDICES[hand_side]
        
        if (elbow_idx >= len(body_joints_3d) or 
            wrist_idx >= len(body_joints_3d)):
            return np.eye(3)
        
        forearm_dir = body_joints_3d[wrist_idx] - body_joints_3d[elbow_idx]
        forearm_dir = forearm_dir / (np.linalg.norm(forearm_dir) + 1e-6)
        
        up_vec = np.array([0, 1, 0])
        
        x_axis = forearm_dir
        y_axis = np.cross(up_vec, x_axis)
        y_axis = y_axis / (np.linalg.norm(y_axis) + 1e-6)
        z_axis = np.cross(x_axis, y_axis)
        z_axis = z_axis / (np.linalg.norm(z_axis) + 1e-6)
        
        rotation = np.column_stack([x_axis, y_axis, z_axis])
        
        return rotation
    
    def estimate_hand_scale_from_body(self, body_joints_3d: np.ndarray,
                                       hand_side: str) -> float:
        if body_joints_3d.ndim == 3:
            body_joints_3d = body_joints_3d[0]
        
        shoulder_idx, elbow_idx = self.UPPERARM_INDICES[hand_side]
        _, wrist_idx = self.FOREARM_INDICES[hand_side]
        
        if (shoulder_idx >= len(body_joints_3d) or
            elbow_idx >= len(body_joints_3d) or
            wrist_idx >= len(body_joints_3d)):
            return 1.0
        
        upper_arm_len = np.linalg.norm(
            body_joints_3d[elbow_idx] - body_joints_3d[shoulder_idx]
        )
        forearm_len = np.linalg.norm(
            body_joints_3d[wrist_idx] - body_joints_3d[elbow_idx]
        )
        
        arm_len = upper_arm_len + forearm_len
        
        hand_size_ratio = 0.33
        estimated_hand_size = arm_len * hand_size_ratio
        
        reference_hand_size = self.AVERAGE_HAND_SIZE
        
        scale_factor = estimated_hand_size / reference_hand_size
        
        return scale_factor
    
    def procrustes_analysis(self, source_points: np.ndarray, 
                             target_points: np.ndarray,
                             compute_scale: bool = True) -> Tuple[np.ndarray, np.ndarray, float]:
        assert source_points.shape == target_points.shape
        
        source_mean = np.mean(source_points, axis=0)
        target_mean = np.mean(target_points, axis=0)
        
        source_centered = source_points - source_mean
        target_centered = target_points - target_mean
        
        if compute_scale:
            source_scale = np.sqrt(np.sum(source_centered ** 2) / source_points.shape[0])
            target_scale = np.sqrt(np.sum(target_centered ** 2) / target_points.shape[0])
            source_centered = source_centered / source_scale
            target_centered = target_centered / target_scale
        else:
            source_scale = 1.0
            target_scale = 1.0
        
        H = source_centered.T @ target_centered
        
        U, S, Vt = np.linalg.svd(H)
        R = Vt.T @ U.T
        
        if np.linalg.det(R) < 0:
            Vt[-1, :] *= -1
            R = Vt.T @ U.T
        
        if compute_scale:
            scale = np.trace(np.diag(S)) * target_scale / source_scale
        else:
            scale = 1.0
        
        translation = target_mean - scale * R @ source_mean
        
        aligned_source = scale * (R @ source_centered.T).T * source_scale + target_mean
        error = np.mean(np.linalg.norm(aligned_source - target_points, axis=1))
        
        return R, translation, scale, error
    
    def align_hand_to_body(self, hand_joints_2d: List[Optional[object]],
                            body_joints_3d: np.ndarray,
                            camera_params: np.ndarray,
                            hand_side: str) -> HandAlignmentResult:
        if body_joints_3d.ndim == 3:
            body_joints_3d = body_joints_3d[0]
        
        wrist_idx = self.BODY_WRIST_INDICES[hand_side]
        if wrist_idx >= len(body_joints_3d):
            wrist_idx = min(wrist_idx, len(body_joints_3d) - 1)
        
        body_wrist_3d = body_joints_3d[wrist_idx]
        
        hand_2d_array = []
        valid_indices = []
        for i, kp in enumerate(hand_joints_2d):
            if kp is not None:
                hand_2d_array.append([kp.x, kp.y])
                valid_indices.append(i)
        
        if len(valid_indices) < 3:
            return HandAlignmentResult(
                aligned_hand_joints=np.zeros((self.num_hand_joints, 3)),
                scale_factor=1.0,
                rotation_matrix=np.eye(3),
                translation_vector=body_wrist_3d,
                alignment_error=float('inf')
            )
        
        hand_2d_array = np.array(hand_2d_array)
        
        body_scale = self.compute_body_scale(body_joints_3d)
        hand_scale = self.estimate_hand_scale_from_body(body_joints_3d, hand_side)
        global_scale = body_scale * hand_scale
        
        arm_rotation = self.compute_arm_orientation(body_joints_3d, hand_side)
        
        scale = camera_params[0]
        trans = camera_params[1:]
        
        hand_joints_3d_init = np.zeros((self.num_hand_joints, 3))
        
        for idx, orig_idx in enumerate(valid_indices):
            if orig_idx == self.HAND_WRIST_INDEX:
                hand_joints_3d_init[orig_idx] = body_wrist_3d
            else:
                wrist_2d = None
                for i, kp in enumerate(hand_joints_2d):
                    if i == self.HAND_WRIST_INDEX and kp is not None:
                        wrist_2d = np.array([kp.x, kp.y])
                        break
                
                if wrist_2d is not None:
                    delta_2d = (hand_2d_array[idx] - wrist_2d) / scale
                    depth_factor = global_scale * 0.5
                    
                    hand_joints_3d_init[orig_idx, :2] = body_wrist_3d[:2] + delta_2d
                    hand_joints_3d_init[orig_idx, 2] = body_wrist_3d[2] + depth_factor * np.linalg.norm(delta_2d)
        
        hand_3d_lifted = self._refine_hand_joints_3d(
            hand_joints_3d_init, hand_2d_array, valid_indices,
            body_wrist_3d, camera_params, global_scale
        )
        
        hand_wrist_3d = hand_3d_lifted[self.HAND_WRIST_INDEX]
        translation = body_wrist_3d - hand_wrist_3d
        hand_3d_translated = hand_3d_lifted + translation
        
        forearm_dir = body_wrist_3d - body_joints_3d[self.FOREARM_INDICES[hand_side][0]]
        forearm_dir = forearm_dir / (np.linalg.norm(forearm_dir) + 1e-6)
        
        hand_dir = np.mean(hand_3d_translated[5:9] - hand_3d_translated[0], axis=0)
        hand_dir = hand_dir / (np.linalg.norm(hand_dir) + 1e-6)
        
        rotation_axis = np.cross(hand_dir, forearm_dir)
        rotation_axis = rotation_axis / (np.linalg.norm(rotation_axis) + 1e-6)
        rotation_angle = np.arccos(np.clip(np.dot(hand_dir, forearm_dir), -1, 1))
        
        R = self._axis_angle_to_matrix(rotation_axis, rotation_angle)
        
        hand_centered = hand_3d_translated - body_wrist_3d
        hand_rotated = (R @ hand_centered.T).T + body_wrist_3d
        
        final_error = self._compute_reprojection_error(
            hand_rotated, hand_joints_2d, camera_params
        )
        
        return HandAlignmentResult(
            aligned_hand_joints=hand_rotated,
            scale_factor=global_scale,
            rotation_matrix=R,
            translation_vector=translation,
            alignment_error=final_error
        )
    
    def _axis_angle_to_matrix(self, axis: np.ndarray, angle: float) -> np.ndarray:
        cos_a = np.cos(angle)
        sin_a = np.sin(angle)
        
        x, y, z = axis
        
        R = np.array([
            [cos_a + x*x*(1-cos_a), x*y*(1-cos_a) - z*sin_a, x*z*(1-cos_a) + y*sin_a],
            [y*x*(1-cos_a) + z*sin_a, cos_a + y*y*(1-cos_a), y*z*(1-cos_a) - x*sin_a],
            [z*x*(1-cos_a) - y*sin_a, z*y*(1-cos_a) + x*sin_a, cos_a + z*z*(1-cos_a)]
        ])
        
        return R
    
    def _refine_hand_joints_3d(self, initial_3d: np.ndarray,
                                hand_2d: np.ndarray,
                                valid_indices: List[int],
                                wrist_3d: np.ndarray,
                                camera_params: np.ndarray,
                                hand_scale: float) -> np.ndarray:
        refined = initial_3d.copy()
        
        scale = camera_params[0]
        trans = camera_params[1:]
        
        for _ in range(20):
            for idx, orig_idx in enumerate(valid_indices):
                if orig_idx == self.HAND_WRIST_INDEX:
                    continue
                
                projected = scale * (refined[orig_idx, :2] + trans)
                error = hand_2d[idx] - projected
                
                grad = scale * error
                refined[orig_idx, :2] += 0.01 * grad
        
        bone_constraints = [
            (0, 1), (1, 2), (2, 3), (3, 4),
            (0, 5), (5, 6), (6, 7), (7, 8),
            (0, 9), (9, 10), (10, 11), (11, 12),
            (0, 13), (13, 14), (14, 15), (15, 16),
            (0, 17), (17, 18), (18, 19), (19, 20)
        ]
        
        reference_lengths = [0.05, 0.05, 0.05, 0.05,
                            0.07, 0.07, 0.07, 0.07,
                            0.08, 0.07, 0.07, 0.07,
                            0.07, 0.07, 0.07, 0.07,
                            0.06, 0.06, 0.06, 0.06]
        
        for _ in range(10):
            for (parent, child), ref_len in zip(bone_constraints, reference_lengths):
                if parent >= len(refined) or child >= len(refined):
                    continue
                
                current_vec = refined[child] - refined[parent]
                current_len = np.linalg.norm(current_vec)
                
                if current_len > 0:
                    target_len = ref_len * hand_scale
                    correction = (target_len - current_len) * 0.1
                    direction = current_vec / current_len
                    refined[child] += direction * correction
        
        return refined
    
    def _compute_reprojection_error(self, joints_3d: np.ndarray,
                                     keypoints_2d: List[Optional[object]],
                                     camera_params: np.ndarray) -> float:
        scale = camera_params[0]
        trans = camera_params[1:]
        
        errors = []
        for i, kp in enumerate(keypoints_2d):
            if kp is None or i >= len(joints_3d):
                continue
            
            projected = scale * (joints_3d[i, :2] + trans)
            error = np.linalg.norm(np.array([kp.x, kp.y]) - projected)
            errors.append(error * kp.confidence)
        
        if len(errors) == 0:
            return float('inf')
        
        return float(np.mean(errors))
    
    def merge_hands_with_body(self, body_joints_3d: np.ndarray,
                               right_hand_result: Optional[HandAlignmentResult],
                               left_hand_result: Optional[HandAlignmentResult]
                               ) -> np.ndarray:
        if body_joints_3d.ndim == 3:
            body_joints_3d = body_joints_3d[0]
        
        total_joints = self.num_body_joints
        if right_hand_result is not None:
            total_joints += self.num_hand_joints
        if left_hand_result is not None:
            total_joints += self.num_hand_joints
        
        merged = np.zeros((total_joints, 3))
        merged[:self.num_body_joints] = body_joints_3d
        
        idx = self.num_body_joints
        if right_hand_result is not None:
            merged[idx:idx + self.num_hand_joints] = right_hand_result.aligned_hand_joints
            idx += self.num_hand_joints
        
        if left_hand_result is not None:
            merged[idx:idx + self.num_hand_joints] = left_hand_result.aligned_hand_joints
        
        return merged


class TemporalHandAligner:
    def __init__(self, num_hand_joints: int = 21, 
                 smoothing_window: int = 5):
        self.num_hand_joints = num_hand_joints
        self.smoothing_window = smoothing_window
        
        self.hand_history = {}
        self.scale_history = {}
    
    def update(self, track_id: int, hand_side: str,
               hand_result: HandAlignmentResult) -> HandAlignmentResult:
        key = f"{track_id}_{hand_side}"
        
        if key not in self.hand_history:
            self.hand_history[key] = []
            self.scale_history[key] = []
        
        self.hand_history[key].append(hand_result.aligned_hand_joints.copy())
        self.scale_history[key].append(hand_result.scale_factor)
        
        if len(self.hand_history[key]) > self.smoothing_window:
            self.hand_history[key].pop(0)
            self.scale_history[key].pop(0)
        
        if len(self.hand_history[key]) > 1:
            smoothed_joints = np.mean(self.hand_history[key], axis=0)
            smoothed_scale = np.mean(self.scale_history[key])
            
            return HandAlignmentResult(
                aligned_hand_joints=smoothed_joints,
                scale_factor=smoothed_scale,
                rotation_matrix=hand_result.rotation_matrix,
                translation_vector=hand_result.translation_vector,
                alignment_error=hand_result.alignment_error
            )
        
        return hand_result
    
    def reset(self, track_id: Optional[int] = None):
        if track_id is not None:
            keys_to_remove = [k for k in self.hand_history.keys() 
                             if k.startswith(f"{track_id}_")]
            for k in keys_to_remove:
                del self.hand_history[k]
                del self.scale_history[k]
        else:
            self.hand_history.clear()
            self.scale_history.clear()
