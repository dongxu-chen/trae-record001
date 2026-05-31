import numpy as np
import torch
from typing import List, Optional, Tuple
from dataclasses import dataclass, field
from collections import deque

try:
    from filterpy.kalman import KalmanFilter
    HAS_FILTERPY = True
except ImportError:
    HAS_FILTERPY = False


@dataclass
class SmoothedPose:
    joints_3d: np.ndarray
    betas: np.ndarray
    pose: np.ndarray
    camera: np.ndarray
    adaptive_alpha: Optional[float] = None


@dataclass
class MotionMetrics:
    joint_velocity: np.ndarray
    pose_velocity: np.ndarray
    camera_velocity: float
    motion_magnitude: float
    is_large_motion: bool


class MotionAnalyzer:
    def __init__(self, num_joints: int = 24, num_pose: int = 72,
                 velocity_window: int = 5,
                 motion_threshold: float = 0.1):
        self.num_joints = num_joints
        self.num_pose = num_pose
        self.velocity_window = velocity_window
        self.motion_threshold = motion_threshold
        
        self.joint_history = {}
        self.pose_history = {}
        self.camera_history = {}
    
    def update(self, track_id: int, joints_3d: np.ndarray, 
               pose: np.ndarray, camera: np.ndarray) -> MotionMetrics:
        if joints_3d.ndim == 3:
            joints_3d = joints_3d[0]
        
        if track_id not in self.joint_history:
            self.joint_history[track_id] = deque(maxlen=self.velocity_window)
            self.pose_history[track_id] = deque(maxlen=self.velocity_window)
            self.camera_history[track_id] = deque(maxlen=self.velocity_window)
        
        self.joint_history[track_id].append(joints_3d.copy())
        self.pose_history[track_id].append(pose.copy())
        self.camera_history[track_id].append(camera.copy())
        
        joint_vel = np.zeros(self.num_joints)
        pose_vel = np.zeros(self.num_pose)
        camera_vel = 0.0
        
        history = self.joint_history[track_id]
        if len(history) >= 2:
            joint_diffs = []
            for i in range(1, len(history)):
                diff = np.linalg.norm(history[i] - history[i-1], axis=1)
                joint_diffs.append(diff)
            joint_vel = np.mean(joint_diffs, axis=0)
        
        pose_hist = self.pose_history[track_id]
        if len(pose_hist) >= 2:
            pose_diffs = []
            for i in range(1, len(pose_hist)):
                diff = np.linalg.norm(pose_hist[i] - pose_hist[i-1])
                pose_diffs.append(diff)
            pose_vel = np.mean(pose_diffs)
        
        cam_hist = self.camera_history[track_id]
        if len(cam_hist) >= 2:
            cam_diffs = []
            for i in range(1, len(cam_hist)):
                diff = np.linalg.norm(cam_hist[i] - cam_hist[i-1])
                cam_diffs.append(diff)
            camera_vel = np.mean(cam_diffs)
        
        joint_vel_mean = float(np.mean(joint_vel)) if joint_vel.size > 0 else 0.0
        pose_vel_scalar = float(pose_vel) if np.isscalar(pose_vel) else float(np.mean(pose_vel))
        camera_vel_scalar = float(camera_vel) if np.isscalar(camera_vel) else float(np.mean(camera_vel))
        
        motion_magnitude = joint_vel_mean * 0.5 + pose_vel_scalar * 0.3 + camera_vel_scalar * 0.2
        is_large_motion = motion_magnitude > self.motion_threshold
        
        return MotionMetrics(
            joint_velocity=joint_vel,
            pose_velocity=pose_vel,
            camera_velocity=camera_vel,
            motion_magnitude=motion_magnitude,
            is_large_motion=is_large_motion
        )
    
    def reset(self, track_id: Optional[int] = None):
        if track_id is not None:
            if track_id in self.joint_history:
                del self.joint_history[track_id]
            if track_id in self.pose_history:
                del self.pose_history[track_id]
            if track_id in self.camera_history:
                del self.camera_history[track_id]
        else:
            self.joint_history.clear()
            self.pose_history.clear()
            self.camera_history.clear()


class AdaptiveSmoothingController:
    def __init__(self, alpha_min: float = 0.3, alpha_max: float = 0.9,
                 motion_threshold_low: float = 0.05,
                 motion_threshold_high: float = 0.2):
        self.alpha_min = alpha_min
        self.alpha_max = alpha_max
        self.motion_threshold_low = motion_threshold_low
        self.motion_threshold_high = motion_threshold_high
        
        self.process_noise_min = 0.001
        self.process_noise_max = 0.1
        self.measurement_noise_min = 0.01
        self.measurement_noise_max = 0.5
    
    def compute_alpha(self, motion_magnitude: float) -> float:
        if motion_magnitude < self.motion_threshold_low:
            return self.alpha_max
        elif motion_magnitude > self.motion_threshold_high:
            return self.alpha_min
        else:
            t = (motion_magnitude - self.motion_threshold_low) / \
                (self.motion_threshold_high - self.motion_threshold_low)
            t = np.clip(t, 0, 1)
            return self.alpha_max * (1 - t) + self.alpha_min * t
    
    def compute_noise_params(self, motion_magnitude: float) -> Tuple[float, float]:
        t = np.clip((motion_magnitude - self.motion_threshold_low) / 
                    (self.motion_threshold_high - self.motion_threshold_low), 0, 1)
        
        process_noise = self.process_noise_min * (1 - t) + self.process_noise_max * t
        measurement_noise = self.measurement_noise_max * (1 - t) + self.measurement_noise_min * t
        
        return process_noise, measurement_noise
    
    def per_joint_alpha(self, joint_velocities: np.ndarray) -> np.ndarray:
        alphas = np.zeros_like(joint_velocities)
        for i, vel in enumerate(joint_velocities):
            alphas[i] = self.compute_alpha(vel)
        return alphas


class PoseSmoother:
    def __init__(self, method: str = "kalman", alpha: float = 0.7,
                 process_noise: float = 0.01, measurement_noise: float = 0.1,
                 num_joints: int = 24, num_betas: int = 10, num_pose: int = 72,
                 use_adaptive: bool = True):
        self.method = method
        self.base_alpha = alpha
        self.base_process_noise = process_noise
        self.base_measurement_noise = measurement_noise
        self.num_joints = num_joints
        self.num_betas = num_betas
        self.num_pose = num_pose
        self.use_adaptive = use_adaptive
        
        self.state_dim = num_joints * 3 + num_betas + num_pose + 3
        
        self.kalman_filters = {}
        self.prev_poses = {}
        
        self.buffer_size = 10
        self.pose_buffers = {}
        
        if use_adaptive:
            self.motion_analyzer = MotionAnalyzer(num_joints, num_pose)
            self.adaptive_controller = AdaptiveSmoothingController()
    
    def smooth(self, track_id: int, joints_3d: torch.Tensor,
              betas: torch.Tensor, pose: torch.Tensor,
              camera: torch.Tensor) -> SmoothedPose:
        joints_np = joints_3d.detach().cpu().numpy() if isinstance(joints_3d, torch.Tensor) else joints_3d
        betas_np = betas.detach().cpu().numpy() if isinstance(betas, torch.Tensor) else betas
        pose_np = pose.detach().cpu().numpy() if isinstance(pose, torch.Tensor) else pose
        camera_np = camera.detach().cpu().numpy() if isinstance(camera, torch.Tensor) else camera
        
        adaptive_alpha = None
        
        if self.use_adaptive and self.motion_analyzer is not None:
            motion_metrics = self.motion_analyzer.update(track_id, joints_np, pose_np, camera_np)
            adaptive_alpha = self.adaptive_controller.compute_alpha(motion_metrics.motion_magnitude)
            
            if motion_metrics.is_large_motion:
                process_noise, measurement_noise = self.adaptive_controller.compute_noise_params(
                    motion_metrics.motion_magnitude
                )
                self._update_kalman_noise(track_id, process_noise, measurement_noise)
        
        measurement = self._pack_measurement(joints_np, betas_np, pose_np, camera_np)
        
        if self.method == "kalman" and HAS_FILTERPY:
            smoothed = self._kalman_smooth(track_id, measurement, adaptive_alpha)
        elif self.method == "exponential":
            smoothed = self._exponential_smooth(track_id, measurement, adaptive_alpha)
        elif self.method == "moving_average":
            smoothed = self._moving_average_smooth(track_id, measurement)
        else:
            smoothed = measurement
        
        result = self._unpack_measurement(smoothed)
        result.adaptive_alpha = adaptive_alpha
        return result
    
    def _update_kalman_noise(self, track_id: int, process_noise: float, measurement_noise: float):
        if track_id in self.kalman_filters:
            kf = self.kalman_filters[track_id]
            kf.Q = np.eye(self.state_dim) * process_noise
            kf.R = np.eye(self.state_dim) * measurement_noise
    
    def _pack_measurement(self, joints_3d: np.ndarray, betas: np.ndarray,
                          pose: np.ndarray, camera: np.ndarray) -> np.ndarray:
        j = joints_3d.reshape(-1)
        return np.concatenate([j, betas, pose, camera])
    
    def _unpack_measurement(self, measurement: np.ndarray) -> SmoothedPose:
        idx = 0
        joints_3d = measurement[idx:idx + self.num_joints * 3].reshape(self.num_joints, 3)
        idx += self.num_joints * 3
        
        betas = measurement[idx:idx + self.num_betas]
        idx += self.num_betas
        
        pose = measurement[idx:idx + self.num_pose]
        idx += self.num_pose
        
        camera = measurement[idx:idx + 3]
        
        return SmoothedPose(
            joints_3d=joints_3d,
            betas=betas,
            pose=pose,
            camera=camera
        )
    
    def _init_kalman_filter(self, initial_state: np.ndarray) -> KalmanFilter:
        if not HAS_FILTERPY:
            raise ImportError("filterpy is required for Kalman smoothing")
        
        dim_x = self.state_dim
        dim_z = self.state_dim
        
        kf = KalmanFilter(dim_x=dim_x, dim_z=dim_z)
        
        kf.F = np.eye(dim_x)
        kf.H = np.eye(dim_x)
        kf.R = np.eye(dim_x) * self.measurement_noise
        kf.Q = np.eye(dim_x) * self.process_noise
        kf.P = np.eye(dim_x) * 1.0
        kf.x = initial_state.reshape(-1, 1)
        
        return kf
    
    def _kalman_smooth(self, track_id: int, measurement: np.ndarray,
                         adaptive_alpha: Optional[float] = None) -> np.ndarray:
        if track_id not in self.kalman_filters:
            self.kalman_filters[track_id] = self._init_kalman_filter(measurement)
        
        kf = self.kalman_filters[track_id]
        
        kf.predict()
        kf.update(measurement.reshape(-1, 1))
        
        return kf.x.flatten()
    
    def _exponential_smooth(self, track_id: int, measurement: np.ndarray,
                               adaptive_alpha: Optional[float] = None) -> np.ndarray:
        alpha = adaptive_alpha if adaptive_alpha is not None else self.base_alpha
        
        if track_id not in self.prev_poses:
            self.prev_poses[track_id] = measurement
        
        prev = self.prev_poses[track_id]
        smoothed = alpha * measurement + (1 - alpha) * prev
        self.prev_poses[track_id] = smoothed
        
        return smoothed
    
    def _moving_average_smooth(self, track_id: int, measurement: np.ndarray) -> np.ndarray:
        if track_id not in self.pose_buffers:
            self.pose_buffers[track_id] = deque(maxlen=self.buffer_size)
        
        self.pose_buffers[track_id].append(measurement)
        
        return np.mean(self.pose_buffers[track_id], axis=0)
    
    def reset(self, track_id: Optional[int] = None):
        if track_id is not None:
            if track_id in self.kalman_filters:
                del self.kalman_filters[track_id]
            if track_id in self.prev_poses:
                del self.prev_poses[track_id]
            if track_id in self.pose_buffers:
                del self.pose_buffers[track_id]
            if self.use_adaptive and self.motion_analyzer is not None:
                self.motion_analyzer.reset(track_id)
        else:
            self.kalman_filters.clear()
            self.prev_poses.clear()
            self.pose_buffers.clear()
            if self.use_adaptive and self.motion_analyzer is not None:
                self.motion_analyzer.reset()


class JointSmoother3D:
    def __init__(self, alpha: float = 0.6, use_kalman: bool = True):
        self.alpha = alpha
        self.use_kalman = use_kalman and HAS_FILTERPY
        self.prev_joints = {}
        self.kalman_filters = {}
    
    def smooth(self, track_id: int, joints_3d: np.ndarray) -> np.ndarray:
        if joints_3d.ndim == 3:
            joints_3d = joints_3d[0]
        
        if self.use_kalman:
            return self._kalman_smooth(track_id, joints_3d)
        else:
            return self._exponential_smooth(track_id, joints_3d)
    
    def _exponential_smooth(self, track_id: int, joints_3d: np.ndarray) -> np.ndarray:
        if track_id not in self.prev_joints:
            self.prev_joints[track_id] = joints_3d
            return joints_3d
        
        smoothed = self.alpha * joints_3d + (1 - self.alpha) * self.prev_joints[track_id]
        self.prev_joints[track_id] = smoothed
        return smoothed
    
    def _kalman_smooth(self, track_id: int, joints_3d: np.ndarray) -> np.ndarray:
        if track_id not in self.kalman_filters:
            num_joints = joints_3d.shape[0]
            kf = KalmanFilter(dim_x=num_joints * 3, dim_z=num_joints * 3)
            kf.F = np.eye(num_joints * 3)
            kf.H = np.eye(num_joints * 3)
            kf.R = np.eye(num_joints * 3) * 0.1
            kf.Q = np.eye(num_joints * 3) * 0.01
            kf.x = joints_3d.reshape(-1, 1)
            self.kalman_filters[track_id] = kf
        
        kf = self.kalman_filters[track_id]
        kf.predict()
        kf.update(joints_3d.reshape(-1, 1))
        
        return kf.x.reshape(joints_3d.shape)
    
    def reset(self, track_id: Optional[int] = None):
        if track_id is not None:
            if track_id in self.prev_joints:
                del self.prev_joints[track_id]
            if track_id in self.kalman_filters:
                del self.kalman_filters[track_id]
        else:
            self.prev_joints.clear()
            self.kalman_filters.clear()
