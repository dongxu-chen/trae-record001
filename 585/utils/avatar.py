import numpy as np
import torch
from typing import List, Optional, Tuple, Dict
from dataclasses import dataclass, field
from collections import deque
import cv2
from PIL import Image
import io
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

try:
    import trimesh
    HAS_TRIMESH = True
except ImportError:
    HAS_TRIMESH = False

try:
    import open3d as o3d
    HAS_OPEN3D = True
except ImportError:
    HAS_OPEN3D = False


@dataclass
class AvatarPose:
    joints_3d: np.ndarray
    bones: List[Tuple[int, int, np.ndarray]]
    rotation_matrices: Dict[int, np.ndarray]
    root_translation: np.ndarray
    timestamp: float


@dataclass
class AvatarAnimationFrame:
    pose: AvatarPose
    mesh_vertices: Optional[np.ndarray]
    mesh_faces: Optional[np.ndarray]
    action_name: Optional[str] = None


class Avatar:
    def __init__(self, name: str = "Default",
                 color: Tuple[float, float, float] = (0.2, 0.6, 1.0),
                 num_joints: int = 24):
        self.name = name
        self.color = color
        self.num_joints = num_joints
        
        self.SMPL_SKELETON = [
            (0, 1), (0, 2), (0, 3), (1, 4), (2, 5), (3, 6),
            (4, 7), (5, 8), (6, 9), (7, 10), (8, 11), (9, 12),
            (9, 13), (9, 14), (12, 15), (13, 16), (14, 17),
            (16, 18), (17, 19), (18, 20), (19, 21), (20, 22), (21, 23)
        ]
        
        self.JOINT_NAMES = [
            'Pelvis', 'L_Hip', 'R_Hip', 'Spine1', 'L_Knee', 'R_Knee',
            'Spine2', 'L_Ankle', 'R_Ankle', 'Spine3', 'L_Foot', 'R_Foot',
            'Neck', 'L_Collar', 'R_Collar', 'Head', 'L_Shoulder', 'R_Shoulder',
            'L_Elbow', 'R_Elbow', 'L_Wrist', 'R_Wrist', 'L_Hand', 'R_Hand'
        ]
        
        self.BONE_RADIUS = {
            (0, 1): 0.04, (0, 2): 0.04, (0, 3): 0.05,
            (1, 4): 0.04, (2, 5): 0.04, (3, 6): 0.05,
            (4, 7): 0.035, (5, 8): 0.035, (6, 9): 0.05,
            (7, 10): 0.03, (8, 11): 0.03, (9, 12): 0.04,
            (9, 13): 0.04, (9, 14): 0.04, (12, 15): 0.08,
            (13, 16): 0.035, (14, 17): 0.035,
            (16, 18): 0.03, (17, 19): 0.03,
            (18, 20): 0.025, (19, 21): 0.025,
            (20, 22): 0.02, (21, 23): 0.02
        }
        
        self.joint_positions = np.zeros((num_joints, 3))
        self.rotation_matrices = {}
        self.animation_history = deque(maxlen=100)
        
        self._build_bone_meshes()
    
    def _build_bone_meshes(self):
        self.bone_meshes = {}
        for (parent, child) in self.SMPL_SKELETON:
            radius = self.BONE_RADIUS.get((parent, child), 0.03)
            self.bone_meshes[(parent, child)] = self._create_cylinder_mesh(radius)
        
        self.head_mesh = self._create_sphere_mesh(0.1)
        self.joint_mesh = self._create_sphere_mesh(0.03)
    
    def _create_cylinder_mesh(self, radius: float, height: float = 1.0) -> object:
        if not HAS_TRIMESH:
            return None
        
        cylinder = trimesh.creation.cylinder(radius=radius, height=height, sections=16)
        return cylinder
    
    def _create_sphere_mesh(self, radius: float) -> object:
        if not HAS_TRIMESH:
            return None
        
        sphere = trimesh.creation.icosphere(radius=radius, subdivisions=2)
        return sphere
    
    def update_pose(self, joints_3d: np.ndarray, 
                    mesh_vertices: Optional[np.ndarray] = None,
                    mesh_faces: Optional[np.ndarray] = None,
                    action_name: Optional[str] = None) -> AvatarAnimationFrame:
        if joints_3d.ndim == 3:
            joints_3d = joints_3d[0]
        
        if joints_3d.shape[0] > self.num_joints:
            joints_3d = joints_3d[:self.num_joints, :]
        
        self.joint_positions = joints_3d.copy()
        
        bones = []
        for (parent, child) in self.SMPL_SKELETON:
            if parent < len(joints_3d) and child < len(joints_3d):
                bone_vec = joints_3d[child] - joints_3d[parent]
                bones.append((parent, child, bone_vec))
        
        rotation_matrices = self._compute_rotation_matrices(joints_3d)
        
        root_translation = joints_3d[0].copy()
        
        avatar_pose = AvatarPose(
            joints_3d=joints_3d,
            bones=bones,
            rotation_matrices=rotation_matrices,
            root_translation=root_translation,
            timestamp=time.time()
        )
        
        frame = AvatarAnimationFrame(
            pose=avatar_pose,
            mesh_vertices=mesh_vertices,
            mesh_faces=mesh_faces,
            action_name=action_name
        )
        
        self.animation_history.append(frame)
        
        return frame
    
    def _compute_rotation_matrices(self, joints_3d: np.ndarray) -> Dict[int, np.ndarray]:
        rotations = {}
        
        rotations[0] = np.eye(3)
        
        for (parent, child) in self.SMPL_SKELETON:
            if parent < len(joints_3d) and child < len(joints_3d):
                bone_vec = joints_3d[child] - joints_3d[parent]
                bone_vec = bone_vec / (np.linalg.norm(bone_vec) + 1e-6)
                
                if parent in rotations:
                    parent_rot = rotations[parent]
                    local_vec = parent_rot.T @ bone_vec
                    
                    rest_vec = np.array([0, -1, 0])
                    if child in [1, 4, 7, 10]:
                        rest_vec = np.array([0.3, -0.5, 0])
                    elif child in [2, 5, 8, 11]:
                        rest_vec = np.array([-0.3, -0.5, 0])
                    elif child in [13, 16, 18, 20, 22]:
                        rest_vec = np.array([0.8, 0, 0])
                    elif child in [14, 17, 19, 21, 23]:
                        rest_vec = np.array([-0.8, 0, 0])
                    
                    rest_vec = rest_vec / (np.linalg.norm(rest_vec) + 1e-6)
                    
                    rotation = self._rotation_between_vectors(rest_vec, local_vec)
                    rotations[child] = parent_rot @ rotation
        
        return rotations
    
    def _rotation_between_vectors(self, v1: np.ndarray, v2: np.ndarray) -> np.ndarray:
        v1 = v1 / (np.linalg.norm(v1) + 1e-6)
        v2 = v2 / (np.linalg.norm(v2) + 1e-6)
        
        cross = np.cross(v1, v2)
        dot = np.dot(v1, v2)
        
        if np.isclose(dot, 1.0):
            return np.eye(3)
        elif np.isclose(dot, -1.0):
            return -np.eye(3)
        
        s = np.linalg.norm(cross)
        c = dot
        
        skew = np.array([
            [0, -cross[2], cross[1]],
            [cross[2], 0, -cross[0]],
            [-cross[1], cross[0], 0]
        ])
        
        R = np.eye(3) + skew + skew @ skew * (1 - c) / (s * s + 1e-6)
        
        return R
    
    def get_joint_rotation(self, joint_name: str) -> Optional[np.ndarray]:
        if joint_name in self.JOINT_NAMES:
            joint_idx = self.JOINT_NAMES.index(joint_name)
            return self.rotation_matrices.get(joint_idx)
        return None
    
    def get_bone_length(self, parent: int, child: int) -> float:
        if parent < len(self.joint_positions) and child < len(self.joint_positions):
            return float(np.linalg.norm(
                self.joint_positions[child] - self.joint_positions[parent]
            ))
        return 0.0


class AvatarVisualizer:
    def __init__(self, figure_size: Tuple[int, int] = (12, 8)):
        self.figure_size = figure_size
        
        self.SMPL_SKELETON = [
            (0, 1), (0, 2), (0, 3), (1, 4), (2, 5), (3, 6),
            (4, 7), (5, 8), (6, 9), (7, 10), (8, 11), (9, 12),
            (9, 13), (9, 14), (12, 15), (13, 16), (14, 17),
            (16, 18), (17, 19), (18, 20), (19, 21), (20, 22), (21, 23)
        ]
    
    def render_avatar(self, avatar_frame: AvatarAnimationFrame,
                       show_original: bool = True,
                       show_skeleton: bool = True,
                       show_mesh: bool = True,
                       title: str = "Avatar Pose") -> np.ndarray:
        fig = plt.figure(figsize=self.figure_size)
        
        ncols = 1
        if show_original and show_skeleton and show_mesh:
            ncols = 3
        elif (show_original and show_skeleton) or (show_original and show_mesh) or (show_skeleton and show_mesh):
            ncols = 2
        
        col_idx = 1
        
        if show_original:
            ax = fig.add_subplot(1, ncols, col_idx, projection='3d')
            self._plot_skeleton(ax, avatar_frame.pose.joints_3d, color='blue')
            ax.set_title("Original Pose")
            self._set_axes_equal(ax, avatar_frame.pose.joints_3d)
            col_idx += 1
        
        if show_skeleton:
            ax = fig.add_subplot(1, ncols, col_idx, projection='3d')
            self._plot_avatar_skeleton(ax, avatar_frame.pose, color='green')
            ax.set_title("Avatar Skeleton")
            self._set_axes_equal(ax, avatar_frame.pose.joints_3d)
            col_idx += 1
        
        if show_mesh and avatar_frame.mesh_vertices is not None:
            ax = fig.add_subplot(1, ncols, col_idx, projection='3d')
            self._plot_mesh(ax, avatar_frame.mesh_vertices, avatar_frame.mesh_faces, alpha=0.6)
            self._plot_skeleton(ax, avatar_frame.pose.joints_3d, color='red', alpha=0.8)
            ax.set_title("Avatar with Mesh")
            self._set_axes_equal(ax, avatar_frame.mesh_vertices)
        
        if avatar_frame.action_name:
            fig.suptitle(f"Action: {avatar_frame.action_name}", fontsize=14)
        
        fig.tight_layout()
        img = self._fig_to_image(fig)
        plt.close(fig)
        
        return img
    
    def _plot_skeleton(self, ax: Axes3D, joints: np.ndarray, 
                       color: str = 'blue', alpha: float = 1.0):
        for (parent, child) in self.SMPL_SKELETON:
            if parent < len(joints) and child < len(joints):
                ax.plot3D(
                    [joints[parent, 0], joints[child, 0]],
                    [joints[parent, 1], joints[child, 1]],
                    [joints[parent, 2], joints[child, 2]],
                    color=color, linewidth=2, alpha=alpha
                )
        
        ax.scatter3D(
            joints[:, 0], joints[:, 1], joints[:, 2],
            color=color, s=50, alpha=alpha
        )
    
    def _plot_avatar_skeleton(self, ax: Axes3D, pose: AvatarPose, color: str = 'green'):
        self._plot_skeleton(ax, pose.joints_3d, color=color)
        
        ax.scatter3D(
            pose.joints_3d[0, 0], pose.joints_3d[0, 1], pose.joints_3d[0, 2],
            color='red', s=100, label='Root'
        )
        
        head_idx = 15
        if head_idx < len(pose.joints_3d):
            ax.scatter3D(
                pose.joints_3d[head_idx, 0], 
                pose.joints_3d[head_idx, 1], 
                pose.joints_3d[head_idx, 2],
                color='yellow', s=200, alpha=0.5, label='Head'
            )
        
        ax.legend()
    
    def _plot_mesh(self, ax: Axes3D, vertices: np.ndarray, faces: np.ndarray, alpha: float = 0.6):
        if vertices.ndim == 3:
            vertices = vertices[0]
        
        ax.plot_trisurf(
            vertices[:, 0], vertices[:, 1], vertices[:, 2],
            triangles=faces, alpha=alpha, color='lightblue',
            edgecolor='gray', linewidth=0.1
        )
    
    def _set_axes_equal(self, ax: Axes3D, points: np.ndarray):
        x = points[:, 0]
        y = points[:, 1]
        z = points[:, 2]
        
        max_range = np.array([x.max() - x.min(), y.max() - y.min(), z.max() - z.min()]).max() / 2.0
        
        mid_x = (x.max() + x.min()) * 0.5
        mid_y = (y.max() + y.min()) * 0.5
        mid_z = (z.max() + z.min()) * 0.5
        
        ax.set_xlim(mid_x - max_range, mid_x + max_range)
        ax.set_ylim(mid_y - max_range, mid_y + max_range)
        ax.set_zlim(mid_z - max_range, mid_z + max_range)
        
        ax.set_xlabel('X')
        ax.set_ylabel('Y')
        ax.set_zlabel('Z')
    
    def _fig_to_image(self, fig: plt.Figure) -> np.ndarray:
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        buf.seek(0)
        img = Image.open(buf)
        img_array = np.array(img)
        return cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
    
    def render_animation(self, frames: List[AvatarAnimationFrame],
                         output_path: Optional[str] = None,
                         fps: int = 30) -> Optional[str]:
        if len(frames) == 0:
            return None
        
        first_img = self.render_avatar(frames[0])
        height, width = first_img.shape[:2]
        
        if output_path is None:
            output_path = "avatar_animation.mp4"
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        try:
            for frame in frames:
                img = self.render_avatar(frame)
                writer.write(img)
        finally:
            writer.release()
        
        return output_path


class RealTimeAvatarDriver:
    def __init__(self, num_joints: int = 24, device: str = 'cpu'):
        self.avatar = Avatar(num_joints=num_joints)
        self.visualizer = AvatarVisualizer()
        self.device = device
        
        self.smoothing_alpha = 0.7
        self.prev_joints = None
        
        self.open3d_vis = None
        if HAS_OPEN3D:
            self._init_open3d()
    
    def _init_open3d(self):
        try:
            self.open3d_vis = o3d.visualization.Visualizer()
            self.open3d_vis.create_window(width=800, height=600)
            
            self.o3d_skeleton = o3d.geometry.LineSet()
            self.o3d_skeleton.points = o3d.utility.Vector3dVector(np.zeros((24, 3)))
            self.o3d_skeleton.lines = o3d.utility.Vector2iVector(self.avatar.SMPL_SKELETON)
            self.o3d_skeleton.colors = o3d.utility.Vector3dVector(
                np.zeros((len(self.avatar.SMPL_SKELETON), 3)) + np.array([0, 1, 0])
            )
            
            self.open3d_vis.add_geometry(self.o3d_skeleton)
            
            for i in range(24):
                sphere = o3d.geometry.TriangleMesh.create_sphere(radius=0.03)
                sphere.paint_uniform_color([1, 0, 0])
                self.open3d_vis.add_geometry(sphere)
            
            self.open3d_vis.get_view_control().set_front([0, 0, -1])
        except Exception as e:
            print(f"Could not initialize Open3D visualizer: {e}")
            self.open3d_vis = None
    
    def update(self, joints_3d: np.ndarray, 
               mesh_vertices: Optional[np.ndarray] = None,
               mesh_faces: Optional[np.ndarray] = None,
               action_name: Optional[str] = None) -> AvatarAnimationFrame:
        
        if joints_3d.ndim == 3:
            joints_3d = joints_3d[0]
        
        if joints_3d.shape[0] > self.avatar.num_joints:
            joints_3d = joints_3d[:self.avatar.num_joints, :]
        
        if self.prev_joints is not None:
            joints_3d = (self.smoothing_alpha * joints_3d + 
                        (1 - self.smoothing_alpha) * self.prev_joints)
        
        self.prev_joints = joints_3d.copy()
        
        frame = self.avatar.update_pose(joints_3d, mesh_vertices, mesh_faces, action_name)
        
        if self.open3d_vis is not None:
            self._update_open3d(joints_3d)
        
        return frame
    
    def _update_open3d(self, joints_3d: np.ndarray):
        try:
            self.o3d_skeleton.points = o3d.utility.Vector3dVector(joints_3d)
            self.open3d_vis.update_geometry(self.o3d_skeleton)
            self.open3d_vis.poll_events()
            self.open3d_vis.update_renderer()
        except Exception as e:
            print(f"Error updating Open3D: {e}")
    
    def render(self, frame: AvatarAnimationFrame) -> np.ndarray:
        return self.visualizer.render_avatar(frame)
    
    def close(self):
        if self.open3d_vis is not None:
            self.open3d_vis.destroy_window()
            self.open3d_vis = None
    
    def save_animation(self, output_path: str, fps: int = 30) -> Optional[str]:
        frames = list(self.avatar.animation_history)
        return self.visualizer.render_animation(frames, output_path, fps)
    
    def reset(self):
        self.prev_joints = None
        self.avatar.animation_history.clear()


import time
