import numpy as np
import torch
from typing import List, Optional, Tuple, Dict
from dataclasses import dataclass


@dataclass
class FusedKeypoints:
    body_joints_3d: np.ndarray
    hand_joints_3d: Optional[np.ndarray]
    hand_side: Optional[str]
    confidence: float


class KeypointFusion:
    def __init__(self, num_body_joints: int = 24, num_hand_joints: int = 21,
                 device: str = 'cpu'):
        self.num_body_joints = num_body_joints
        self.num_hand_joints = num_hand_joints
        self.device = device
        
        self.SMPL_TO_OPENPOSE = [
            12, 16, 17, 18, 2,  5,  9, 13, 10, 3,
            6,  7,  11, 14, 15, 1,  4,  19
        ]
        
        self.OPENPOSE_BODY_PARTS = {
            "Nose": 0, "Neck": 1, "RShoulder": 2, "RElbow": 3, "RWrist": 4,
            "LShoulder": 5, "LElbow": 6, "LWrist": 7, "RHip": 8, "RKnee": 9,
            "RAnkle": 10, "LHip": 11, "LKnee": 12, "LAnkle": 13, "REye": 14,
            "LEye": 15, "REar": 16, "LEar": 17, "Background": 18
        }
        
        self.HAND_WRIST_IDX = 0
        self.BODY_RWrist_IDX = 4
        self.BODY_LWrist_IDX = 7
    
    def fuse_body_hand(self, body_joints_3d: np.ndarray,
                       hand_detections: List[object],
                       camera_params: np.ndarray) -> np.ndarray:
        if body_joints_3d.ndim == 3:
            body_joints_3d = body_joints_3d[0]
        
        fused_joints = body_joints_3d.copy()
        
        if hand_detections is None or len(hand_detections) == 0:
            return fused_joints
        
        for hand in hand_detections:
            hand_joints_2d = hand.keypoints
            
            if hand_joints_2d is None or len(hand_joints_2d) == 0:
                continue
            
            wrist_idx = self.BODY_RWrist_IDX if hand.hand_side == "right" else self.BODY_LWrist_IDX
            
            openpose_indices = [v for k, v in self.OPENPOSE_BODY_PARTS.items() if k != "Background"]
            
            if wrist_idx < len(openpose_indices):
                smpl_wrist_idx = self.SMPL_TO_OPENPOSE.index(openpose_indices[wrist_idx]) if openpose_indices[wrist_idx] in self.SMPL_TO_OPENPOSE else wrist_idx
                
                if smpl_wrist_idx < len(fused_joints):
                    wrist_3d = fused_joints[smpl_wrist_idx]
                    
                    hand_3d = self._lift_hand_2d_to_3d(
                        hand_joints_2d, wrist_3d, camera_params
                    )
                    
                    fused_joints = self._merge_hand_to_body(
                        fused_joints, hand_3d, hand.hand_side, smpl_wrist_idx
                    )
        
        return fused_joints
    
    def _lift_hand_2d_to_3d(self, hand_keypoints_2d: List[Optional[object]],
                           wrist_3d: np.ndarray,
                           camera_params: np.ndarray) -> np.ndarray:
        scale = camera_params[0]
        trans = camera_params[1:]
        
        hand_3d = np.zeros((len(hand_keypoints_2d), 3))
        
        valid_indices = [i for i, kp in enumerate(hand_keypoints_2d) if kp is not None]
        
        if len(valid_indices) == 0:
            return hand_3d
        
        wrist_kp = hand_keypoints_2d[self.HAND_WRIST_IDX]
        
        if wrist_kp is None:
            return hand_3d
        
        wrist_2d = np.array([wrist_kp.x, wrist_kp.y])
        
        for i in valid_indices:
            kp = hand_keypoints_2d[i]
            if kp is None:
                continue
            
            kp_2d = np.array([kp.x, kp.y])
            delta_2d = (kp_2d - wrist_2d) / scale
            
            length_ratio = self._estimate_hand_length_ratio(i)
            
            hand_3d[i, :2] = wrist_3d[:2] + delta_2d
            hand_3d[i, 2] = wrist_3d[2] + length_ratio * np.linalg.norm(delta_2d)
        
        return hand_3d
    
    def _estimate_hand_length_ratio(self, joint_idx: int) -> float:
        hand_bone_ratios = {
            0: 0.0,
            1: 0.2, 2: 0.4, 3: 0.6, 4: 0.8,
            5: 0.25, 6: 0.5, 7: 0.75, 8: 1.0,
            9: 0.25, 10: 0.5, 11: 0.75, 12: 1.0,
            13: 0.25, 14: 0.5, 15: 0.75, 16: 1.0,
            17: 0.2, 18: 0.4, 19: 0.6, 20: 0.8
        }
        
        return hand_bone_ratios.get(joint_idx, 0.5)
    
    def _merge_hand_to_body(self, body_joints_3d: np.ndarray,
                           hand_joints_3d: np.ndarray,
                           hand_side: str,
                           wrist_smpl_idx: int) -> np.ndarray:
        merged = body_joints_3d.copy()
        
        if hand_side == "right":
            for i in range(1, len(hand_joints_3d)):
                if np.any(hand_joints_3d[i] != 0):
                    idx = len(merged) + i - 1
                    if idx >= len(merged):
                        merged = np.vstack([merged, np.zeros((idx - len(merged) + 1, 3))])
                    merged[idx] = hand_joints_3d[i]
        else:
            for i in range(1, len(hand_joints_3d)):
                if np.any(hand_joints_3d[i] != 0):
                    idx = len(merged) + len(hand_joints_3d) - 1 + i - 1
                    if idx >= len(merged):
                        merged = np.vstack([merged, np.zeros((idx - len(merged) + 1, 3))])
                    merged[idx] = hand_joints_3d[i]
        
        return merged
    
    def align_smpl_to_openpose(self, smpl_joints: torch.Tensor) -> torch.Tensor:
        if smpl_joints.ndim == 3:
            smpl_joints = smpl_joints[0]
        
        smpl_joints_np = smpl_joints.detach().cpu().numpy()
        
        aligned = np.zeros((len(self.OPENPOSE_BODY_PARTS) - 1, 3))
        
        for openpose_idx, smpl_idx in enumerate(self.SMPL_TO_OPENPOSE):
            if smpl_idx < len(smpl_joints_np):
                aligned[openpose_idx] = smpl_joints_np[smpl_idx]
        
        return torch.tensor(aligned, dtype=torch.float32, device=self.device)
    
    def compute_reprojection_error(self, joints_3d: np.ndarray,
                                   keypoints_2d: List[Optional[object]],
                                   camera_params: np.ndarray) -> float:
        scale = camera_params[0]
        trans = camera_params[1:]
        
        projected = scale * (joints_3d[:, :2] + trans)
        
        errors = []
        for i, kp in enumerate(keypoints_2d):
            if kp is None or i >= len(projected):
                continue
            error = np.sqrt((kp.x - projected[i, 0]) ** 2 + (kp.y - projected[i, 1]) ** 2)
            errors.append(error * kp.confidence)
        
        if len(errors) == 0:
            return float('inf')
        
        return float(np.mean(errors))
    
    def refine_with_2d_constraints(self, joints_3d: np.ndarray,
                                   keypoints_2d: List[Optional[object]],
                                   camera_params: np.ndarray,
                                   num_iters: int = 10,
                                   lr: float = 0.01) -> np.ndarray:
        refined = joints_3d.copy()
        scale = camera_params[0]
        trans = camera_params[1:]
        
        for _ in range(num_iters):
            for i, kp in enumerate(keypoints_2d):
                if kp is None or i >= len(refined):
                    continue
                
                projected = scale * (refined[i, :2] + trans)
                error = np.array([kp.x - projected[0], kp.y - projected[1]])
                
                grad = scale * error
                refined[i, :2] += lr * grad * kp.confidence
        
        return refined


def convert_openpose_to_smpl_format(keypoints_2d: List[Optional[object]],
                                      body_parts: Dict[str, int]) -> np.ndarray:
    smpl_order = [
        'Pelvis', 'L_Hip', 'R_Hip', 'Spine1', 'L_Knee', 'R_Knee',
        'Spine2', 'L_Ankle', 'R_Ankle', 'Spine3', 'L_Foot', 'R_Foot',
        'Neck', 'L_Collar', 'R_Collar', 'Head', 'L_Shoulder', 'R_Shoulder',
        'L_Elbow', 'R_Elbow', 'L_Wrist', 'R_Wrist', 'L_Hand', 'R_Hand'
    ]
    
    openpose_to_smpl = {
        'LHip': 'L_Hip', 'RHip': 'R_Hip',
        'LKnee': 'L_Knee', 'RKnee': 'R_Knee',
        'LAnkle': 'L_Ankle', 'RAnkle': 'R_Ankle',
        'Neck': 'Neck', 'Nose': 'Head',
        'LShoulder': 'L_Shoulder', 'RShoulder': 'R_Shoulder',
        'LElbow': 'L_Elbow', 'RElbow': 'R_Elbow',
        'LWrist': 'L_Wrist', 'RWrist': 'R_Wrist'
    }
    
    smpl_keypoints = np.zeros((24, 3))
    
    for openpose_name, smpl_name in openpose_to_smpl.items():
        if openpose_name in body_parts:
            idx = body_parts[openpose_name]
            if idx < len(keypoints_2d) and keypoints_2d[idx] is not None:
                kp = keypoints_2d[idx]
                smpl_idx = smpl_order.index(smpl_name) if smpl_name in smpl_order else -1
                if smpl_idx >= 0:
                    smpl_keypoints[smpl_idx, 0] = kp.x
                    smpl_keypoints[smpl_idx, 1] = kp.y
                    smpl_keypoints[smpl_idx, 2] = kp.confidence
    
    return smpl_keypoints
