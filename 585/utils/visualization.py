import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from typing import List, Optional, Tuple
import io
from PIL import Image
import cv2

try:
    import open3d as o3d
    HAS_OPEN3D = True
except ImportError:
    HAS_OPEN3D = False


class PoseVisualizer3D:
    def __init__(self, joint_size: int = 5, line_width: int = 2,
                 figure_size: Tuple[int, int] = (12, 6), enable_mesh: bool = True):
        self.joint_size = joint_size
        self.line_width = line_width
        self.figure_size = figure_size
        self.enable_mesh = enable_mesh
        
        self.SMPL_SKELETON = [
            (0, 1), (0, 2), (0, 3), (1, 4), (2, 5), (3, 6),
            (4, 7), (5, 8), (6, 9), (7, 10), (8, 11), (9, 12),
            (9, 13), (9, 14), (12, 15), (13, 16), (14, 17),
            (16, 18), (17, 19), (18, 20), (19, 21), (20, 22), (21, 23)
        ]
        
        self.SMPL_JOINT_NAMES = [
            'Pelvis', 'L_Hip', 'R_Hip', 'Spine1', 'L_Knee', 'R_Knee',
            'Spine2', 'L_Ankle', 'R_Ankle', 'Spine3', 'L_Foot', 'R_Foot',
            'Neck', 'L_Collar', 'R_Collar', 'Head', 'L_Shoulder', 'R_Shoulder',
            'L_Elbow', 'R_Elbow', 'L_Wrist', 'R_Wrist', 'L_Hand', 'R_Hand'
        ]
        
        self.HAND_SKELETON = [
            (0, 1), (1, 2), (2, 3), (3, 4),
            (0, 5), (5, 6), (6, 7), (7, 8),
            (0, 9), (9, 10), (10, 11), (11, 12),
            (0, 13), (13, 14), (14, 15), (15, 16),
            (0, 17), (17, 18), (18, 19), (19, 20)
        ]
    
    def plot_pose_3d(self, joints_3d: np.ndarray,
                     vertices: Optional[np.ndarray] = None,
                     faces: Optional[np.ndarray] = None,
                     hand_joints: Optional[np.ndarray] = None,
                     title: str = "3D Human Pose",
                     view_angle: Tuple[int, int] = (30, 60)) -> plt.Figure:
        if joints_3d.ndim == 3:
            joints_3d = joints_3d[0]
        
        fig = plt.figure(figsize=self.figure_size)
        
        ax1 = fig.add_subplot(121, projection='3d')
        self._plot_skeleton(ax1, joints_3d, color='blue', label='SMPL Joints')
        
        if vertices is not None and faces is not None and self.enable_mesh:
            self._plot_mesh(ax1, vertices, faces, alpha=0.3)
        
        ax1.set_title(title)
        ax1.set_xlabel('X')
        ax1.set_ylabel('Y')
        ax1.set_zlabel('Z')
        ax1.view_init(*view_angle)
        self._equal_aspect_ratio(ax1, joints_3d)
        
        ax2 = fig.add_subplot(122, projection='3d')
        self._plot_skeleton(ax2, joints_3d, color='red', label='Front View')
        
        if hand_joints is not None:
            self._plot_hand(ax2, hand_joints, offset=len(joints_3d))
        
        ax2.set_title("Front View")
        ax2.set_xlabel('X')
        ax2.set_ylabel('Y')
        ax2.set_zlabel('Z')
        ax2.view_init(0, 90)
        self._equal_aspect_ratio(ax2, joints_3d)
        
        plt.tight_layout()
        return fig
    
    def _plot_skeleton(self, ax: Axes3D, joints_3d: np.ndarray,
                       color: str = 'blue', label: str = 'Joints'):
        for parent, child in self.SMPL_SKELETON:
            if parent < len(joints_3d) and child < len(joints_3d):
                ax.plot3D(
                    [joints_3d[parent, 0], joints_3d[child, 0]],
                    [joints_3d[parent, 1], joints_3d[child, 1]],
                    [joints_3d[parent, 2], joints_3d[child, 2]],
                    color=color, linewidth=self.line_width
                )
        
        ax.scatter3D(
            joints_3d[:, 0], joints_3d[:, 1], joints_3d[:, 2],
            color=color, s=self.joint_size * 10, label=label
        )
    
    def _plot_hand(self, ax: Axes3D, hand_joints: np.ndarray, offset: int = 24):
        start_idx = offset
        end_idx = start_idx + 21
        
        if end_idx > len(hand_joints):
            return
        
        for parent, child in self.HAND_SKELETON:
            p_idx = start_idx + parent
            c_idx = start_idx + child
            if p_idx < len(hand_joints) and c_idx < len(hand_joints):
                ax.plot3D(
                    [hand_joints[p_idx, 0], hand_joints[c_idx, 0]],
                    [hand_joints[p_idx, 1], hand_joints[c_idx, 1]],
                    [hand_joints[p_idx, 2], hand_joints[c_idx, 2]],
                    color='green', linewidth=self.line_width
                )
        
        ax.scatter3D(
            hand_joints[start_idx:end_idx, 0],
            hand_joints[start_idx:end_idx, 1],
            hand_joints[start_idx:end_idx, 2],
            color='green', s=self.joint_size * 8, label='Hand Joints'
        )
    
    def _plot_mesh(self, ax: Axes3D, vertices: np.ndarray, faces: np.ndarray, alpha: float = 0.3):
        if vertices.ndim == 3:
            vertices = vertices[0]
        
        ax.plot_trisurf(
            vertices[:, 0], vertices[:, 1], vertices[:, 2],
            triangles=faces, alpha=alpha, color='lightblue',
            edgecolor='gray', linewidth=0.1
        )
    
    def _equal_aspect_ratio(self, ax: Axes3D, joints_3d: np.ndarray):
        x = joints_3d[:, 0]
        y = joints_3d[:, 1]
        z = joints_3d[:, 2]
        
        max_range = np.array([x.max() - x.min(), y.max() - y.min(), z.max() - z.min()]).max() / 2.0
        
        mid_x = (x.max() + x.min()) * 0.5
        mid_y = (y.max() + y.min()) * 0.5
        mid_z = (z.max() + z.min()) * 0.5
        
        ax.set_xlim(mid_x - max_range, mid_x + max_range)
        ax.set_ylim(mid_y - max_range, mid_y + max_range)
        ax.set_zlim(mid_z - max_range, mid_z + max_range)
    
    def plot_multiple_poses(self, all_joints: List[np.ndarray],
                            person_ids: List[int],
                            title: str = "Multi-Person 3D Poses") -> plt.Figure:
        fig = plt.figure(figsize=self.figure_size)
        ax = fig.add_subplot(111, projection='3d')
        
        colors = plt.cm.tab10(np.linspace(0, 1, len(all_joints)))
        
        for i, (joints, pid) in enumerate(zip(all_joints, person_ids)):
            if joints.ndim == 3:
                joints = joints[0]
            self._plot_skeleton(ax, joints, color=colors[i], label=f'Person {pid}')
        
        ax.set_title(title)
        ax.set_xlabel('X')
        ax.set_ylabel('Y')
        ax.set_zlabel('Z')
        ax.legend()
        
        all_joints_array = np.vstack(all_joints)
        self._equal_aspect_ratio(ax, all_joints_array)
        
        plt.tight_layout()
        return fig
    
    def plot_pose_comparison(self, joints_1: np.ndarray, joints_2: np.ndarray,
                             label_1: str = "Original", label_2: str = "Smoothed",
                             title: str = "Pose Comparison") -> plt.Figure:
        fig = plt.figure(figsize=self.figure_size)
        
        ax1 = fig.add_subplot(121, projection='3d')
        self._plot_skeleton(ax1, joints_1, color='blue', label=label_1)
        ax1.set_title(label_1)
        ax1.set_xlabel('X')
        ax1.set_ylabel('Y')
        ax1.set_zlabel('Z')
        self._equal_aspect_ratio(ax1, joints_1)
        
        ax2 = fig.add_subplot(122, projection='3d')
        self._plot_skeleton(ax2, joints_2, color='red', label=label_2)
        ax2.set_title(label_2)
        ax2.set_xlabel('X')
        ax2.set_ylabel('Y')
        ax2.set_zlabel('Z')
        self._equal_aspect_ratio(ax2, joints_2)
        
        fig.suptitle(title)
        plt.tight_layout()
        return fig
    
    def figure_to_image(self, fig: plt.Figure) -> np.ndarray:
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        buf.seek(0)
        img = Image.open(buf)
        img_array = np.array(img)
        plt.close(fig)
        return cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
    
    def visualize_with_image(self, input_image: np.ndarray,
                              joints_3d: np.ndarray,
                              joints_2d: Optional[np.ndarray] = None,
                              title: str = "Input + 3D Pose") -> np.ndarray:
        fig_3d = self.plot_pose_3d(joints_3d, title=title)
        img_3d = self.figure_to_image(fig_3d)
        
        if isinstance(input_image, torch.Tensor):
            input_image = input_image.detach().cpu().numpy()
            input_image = np.transpose(input_image, (1, 2, 0))
            input_image = (input_image * [0.229, 0.224, 0.225] + [0.485, 0.456, 0.406]) * 255
            input_image = input_image.astype(np.uint8)
        
        if input_image.shape[2] == 3:
            input_image = cv2.cvtColor(input_image, cv2.COLOR_RGB2BGR)
        
        h1, w1 = input_image.shape[:2]
        h2, w2 = img_3d.shape[:2]
        
        target_height = max(h1, h2)
        input_image_resized = cv2.resize(input_image, (int(w1 * target_height / h1), target_height))
        img_3d_resized = cv2.resize(img_3d, (int(w2 * target_height / h2), target_height))
        
        combined = np.hstack([input_image_resized, img_3d_resized])
        
        return combined
    
    def create_open3d_visualization(self, joints_3d: np.ndarray,
                                     vertices: Optional[np.ndarray] = None,
                                     faces: Optional[np.ndarray] = None):
        if not HAS_OPEN3D:
            print("Open3D not available, using matplotlib instead")
            return None
        
        if joints_3d.ndim == 3:
            joints_3d = joints_3d[0]
        
        geometries = []
        
        skeleton = o3d.geometry.LineSet()
        points = o3d.utility.Vector3dVector(joints_3d)
        lines = o3d.utility.Vector2iVector(self.SMPL_SKELETON)
        skeleton.points = points
        skeleton.lines = lines
        
        colors = [[0, 0, 1] for _ in range(len(self.SMPL_SKELETON))]
        skeleton.colors = o3d.utility.Vector3dVector(colors)
        geometries.append(skeleton)
        
        joint_spheres = [o3d.geometry.TriangleMesh.create_sphere(radius=0.02) 
                        for _ in range(len(joints_3d))]
        for i, sphere in enumerate(joint_spheres):
            sphere.translate(joints_3d[i])
            sphere.paint_uniform_color([1, 0, 0])
            geometries.append(sphere)
        
        if vertices is not None and faces is not None:
            if vertices.ndim == 3:
                vertices = vertices[0]
            mesh = o3d.geometry.TriangleMesh()
            mesh.vertices = o3d.utility.Vector3dVector(vertices)
            mesh.triangles = o3d.utility.Vector3iVector(faces)
            mesh.compute_vertex_normals()
            mesh.paint_uniform_color([0.8, 0.8, 1.0])
            geometries.append(mesh)
        
        return geometries


def draw_skeleton_2d(image: np.ndarray, joints_2d: np.ndarray,
                     skeleton: List[Tuple[int, int]],
                     joint_color: Tuple[int, int, int] = (0, 255, 0),
                     line_color: Tuple[int, int, int] = (255, 0, 0),
                     thickness: int = 2) -> np.ndarray:
    img_copy = image.copy()
    
    for parent, child in skeleton:
        if parent < len(joints_2d) and child < len(joints_2d):
            if np.all(joints_2d[parent] != 0) and np.all(joints_2d[child] != 0):
                cv2.line(img_copy,
                          (int(joints_2d[parent, 0]), int(joints_2d[parent, 1])),
                          (int(joints_2d[child, 0]), int(joints_2d[child, 1])),
                          line_color, thickness)
    
    for i, joint in enumerate(joints_2d):
        if np.all(joint != 0):
            cv2.circle(img_copy, (int(joint[0]), int(joint[1])), 5, joint_color, -1)
    
    return img_copy


import torch
