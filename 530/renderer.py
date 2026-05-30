import numpy as np
import cv2
import torch
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import config


class FaceRenderer:
    def __init__(self, image_size=224, device='cpu'):
        self.image_size = image_size
        self.device = device
    
    def render_depth(self, vertices, triangles, f=1015.0, cx=112.0, cy=112.0):
        vertices = vertices.detach().cpu().numpy() if torch.is_tensor(vertices) else vertices
        triangles = triangles.detach().cpu().numpy() if torch.is_tensor(triangles) else triangles
        
        depth_map = np.zeros((self.image_size, self.image_size), dtype=np.float32)
        
        n = len(vertices)
        z = vertices[:, 2]
        x = vertices[:, 0] * f / z + cx
        y = vertices[:, 1] * f / z + cy
        
        for tri in triangles:
            v0 = np.array([x[tri[0]], y[tri[0]], z[tri[0]]])
            v1 = np.array([x[tri[1]], y[tri[1]], z[tri[1]]])
            v2 = np.array([x[tri[2]], y[tri[2]], z[tri[2]]])
            
            self._rasterize_triangle(v0, v1, v2, depth_map)
        
        return depth_map
    
    def _rasterize_triangle(self, v0, v1, v2, depth_map):
        h, w = depth_map.shape
        
        min_x = max(0, int(min(v0[0], v1[0], v2[0])))
        max_x = min(w - 1, int(max(v0[0], v1[0], v2[0])))
        min_y = max(0, int(min(v0[1], v1[1], v2[1])))
        max_y = min(h - 1, int(max(v0[1], v1[1], v2[1])))
        
        for y in range(min_y, max_y + 1):
            for x in range(min_x, max_x + 1):
                p = np.array([x + 0.5, y + 0.5, 0])
                
                area = self._compute_area(v0, v1, v2)
                if area == 0:
                    continue
                
                w0 = self._compute_area(v1, v2, p) / area
                w1 = self._compute_area(v2, v0, p) / area
                w2 = self._compute_area(v0, v1, p) / area
                
                if w0 >= 0 and w1 >= 0 and w2 >= 0:
                    depth = w0 * v0[2] + w1 * v1[2] + w2 * v2[2]
                    if depth_map[y, x] == 0 or depth < depth_map[y, x]:
                        depth_map[y, x] = depth
    
    def _compute_area(self, v0, v1, v2):
        return 0.5 * ((v1[0] - v0[0]) * (v2[1] - v0[1]) - (v1[1] - v0[1]) * (v2[0] - v0[0]))
    
    def render_texture(self, vertices, triangles, colors, f=1015.0, cx=112.0, cy=112.0):
        vertices = vertices.detach().cpu().numpy() if torch.is_tensor(vertices) else vertices
        triangles = triangles.detach().cpu().numpy() if torch.is_tensor(triangles) else triangles
        colors = colors.detach().cpu().numpy() if torch.is_tensor(colors) else colors
        
        image = np.zeros((self.image_size, self.image_size, 3), dtype=np.uint8)
        depth_buffer = np.zeros((self.image_size, self.image_size), dtype=np.float32)
        
        n = len(vertices)
        z = vertices[:, 2]
        x = vertices[:, 0] * f / z + cx
        y = vertices[:, 1] * f / z + cy
        
        for tri in triangles:
            idx = [tri[0], tri[1], tri[2]]
            pts_2d = np.array([[x[i], y[i]] for i in idx], dtype=np.int32)
            pts_3d = np.array([[x[i], y[i], z[i]] for i in idx])
            tri_colors = np.array([colors[i] for i in idx])
            
            self._rasterize_texture_triangle(pts_3d, tri_colors, image, depth_buffer)
        
        return image
    
    def _rasterize_texture_triangle(self, pts_3d, colors, image, depth_buffer):
        h, w = image.shape[:2]
        
        min_x = max(0, int(min(pts_3d[0, 0], pts_3d[1, 0], pts_3d[2, 0])))
        max_x = min(w - 1, int(max(pts_3d[0, 0], pts_3d[1, 0], pts_3d[2, 0])))
        min_y = max(0, int(min(pts_3d[0, 1], pts_3d[1, 1], pts_3d[2, 1])))
        max_y = min(h - 1, int(max(pts_3d[0, 1], pts_3d[1, 1], pts_3d[2, 1])))
        
        for y in range(min_y, max_y + 1):
            for x in range(min_x, max_x + 1):
                px, py = x + 0.5, y + 0.5
                
                denom = ((pts_3d[1, 1] - pts_3d[2, 1]) * (pts_3d[0, 0] - pts_3d[2, 0]) +
                        (pts_3d[2, 0] - pts_3d[1, 0]) * (pts_3d[0, 1] - pts_3d[2, 1]))
                if denom == 0:
                    continue
                
                w0 = ((pts_3d[1, 1] - pts_3d[2, 1]) * (px - pts_3d[2, 0]) +
                      (pts_3d[2, 0] - pts_3d[1, 0]) * (py - pts_3d[2, 1])) / denom
                w1 = ((pts_3d[2, 1] - pts_3d[0, 1]) * (px - pts_3d[2, 0]) +
                      (pts_3d[0, 0] - pts_3d[2, 0]) * (py - pts_3d[2, 1])) / denom
                w2 = 1 - w0 - w1
                
                if w0 >= 0 and w1 >= 0 and w2 >= 0:
                    depth = w0 * pts_3d[0, 2] + w1 * pts_3d[1, 2] + w2 * pts_3d[2, 2]
                    if depth_buffer[y, x] == 0 or depth < depth_buffer[y, x]:
                        depth_buffer[y, x] = depth
                        color = w0 * colors[0] + w1 * colors[1] + w2 * colors[2]
                        image[y, x] = np.clip(color, 0, 255).astype(np.uint8)
    
    def render_landmarks(self, image, landmarks_2d, color=(0, 255, 0), radius=2):
        img = image.copy()
        for pt in landmarks_2d:
            cv2.circle(img, (int(pt[0]), int(pt[1])), radius, color, -1)
        return img
    
    def render_mesh_overlay(self, image, vertices, triangles, f=1015.0, cx=112.0, cy=112.0, color=(0, 255, 0), thickness=1):
        img = image.copy()
        
        vertices = vertices.detach().cpu().numpy() if torch.is_tensor(vertices) else vertices
        triangles = triangles.detach().cpu().numpy() if torch.is_tensor(triangles) else triangles
        
        z = vertices[:, 2]
        x = vertices[:, 0] * f / z + cx
        y = vertices[:, 1] * f / z + cy
        
        for tri in triangles:
            pts = np.array([
                [x[tri[0]], y[tri[0]]],
                [x[tri[1]], y[tri[1]]],
                [x[tri[2]], y[tri[2]]]
            ], dtype=np.int32)
            cv2.polylines(img, [pts], True, color, thickness)
        
        return img


class Visualizer:
    def __init__(self, figsize=(15, 10)):
        self.figsize = figsize
    
    def plot_3d_face(self, vertices, triangles, save_path=None, show=False):
        fig = plt.figure(figsize=self.figsize)
        ax = fig.add_subplot(111, projection='3d')
        
        vertices = vertices.detach().cpu().numpy() if torch.is_tensor(vertices) else vertices
        triangles = triangles.detach().cpu().numpy() if torch.is_tensor(triangles) else triangles
        
        ax.plot_trisurf(vertices[:, 0], vertices[:, 1], vertices[:, 2], 
                       triangles=triangles, cmap='viridis', edgecolor='none', alpha=0.8)
        
        ax.set_xlabel('X')
        ax.set_ylabel('Y')
        ax.set_zlabel('Z')
        
        ax.view_init(elev=-90, azim=-90)
        
        ax.axis('equal')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
        
        if show:
            plt.show()
        
        plt.close()
    
    def plot_landmarks_3d(self, landmarks_3d, save_path=None, show=False):
        fig = plt.figure(figsize=self.figsize)
        ax = fig.add_subplot(111, projection='3d')
        
        landmarks = landmarks_3d.detach().cpu().numpy() if torch.is_tensor(landmarks_3d) else landmarks_3d
        
        ax.scatter(landmarks[:, 0], landmarks[:, 1], landmarks[:, 2], c='red', s=20, marker='o')
        
        for i in range(len(landmarks)):
            ax.text(landmarks[i, 0], landmarks[i, 1], landmarks[i, 2], 
                    str(i), fontsize=8)
        
        jaw_idx = list(range(0, 17))
        left_brow = list(range(17, 22))
        right_brow = list(range(22, 27))
        nose = list(range(27, 36))
        left_eye = list(range(36, 42)) + [36]
        right_eye = list(range(42, 48)) + [42]
        outer_mouth = list(range(48, 60)) + [48]
        inner_mouth = list(range(60, 68)) + [60]
        
        for idx in [jaw_idx, left_brow, right_brow, nose, left_eye, right_eye, outer_mouth, inner_mouth]:
            ax.plot(landmarks[idx, 0], landmarks[idx, 1], landmarks[idx, 2], '-b')
        
        ax.set_xlabel('X')
        ax.set_ylabel('Y')
        ax.set_zlabel('Z')
        ax.axis('equal')
        ax.view_init(elev=-90, azim=-90)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
        
        if show:
            plt.show()
        
        plt.close()
    
    def plot_results_comparison(self, original_image, landmarks_2d, rendered_image, 
                                depth_map, save_path=None, show=False):
        fig, axes = plt.subplots(2, 2, figsize=self.figsize)
        
        img_with_landmarks = original_image.copy()
        for pt in landmarks_2d:
            cv2.circle(img_with_landmarks, (int(pt[0]), int(pt[1])), 3, (0, 255, 0), -1)
        
        axes[0, 0].imshow(cv2.cvtColor(original_image, cv2.COLOR_BGR2RGB))
        axes[0, 0].set_title('Original Image')
        axes[0, 0].axis('off')
        
        axes[0, 1].imshow(cv2.cvtColor(img_with_landmarks, cv2.COLOR_BGR2RGB))
        axes[0, 1].set_title('Image with Landmarks')
        axes[0, 1].axis('off')
        
        axes[1, 0].imshow(cv2.cvtColor(rendered_image, cv2.COLOR_BGR2RGB))
        axes[1, 0].set_title('Rendered 3D Face')
        axes[1, 0].axis('off')
        
        im = axes[1, 1].imshow(depth_map, cmap='jet')
        axes[1, 1].set_title('Depth Map')
        axes[1, 1].axis('off')
        plt.colorbar(im, ax=axes[1, 1])
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
        
        if show:
            plt.show()
        
        plt.close()
    
    def plot_params(self, params_dict, save_path=None, show=False):
        num_params = len(params_dict)
        fig, axes = plt.subplots(num_params, 1, figsize=(10, 3 * num_params))
        
        if num_params == 1:
            axes = [axes]
        
        for i, (name, params) in enumerate(params_dict.items()):
            params = params.detach().cpu().numpy().flatten() if torch.is_tensor(params) else params.flatten()
            axes[i].bar(range(len(params)), params)
            axes[i].set_title(f'{name} Parameters ({len(params)} dims)')
            axes[i].set_xlabel('Dimension')
            axes[i].set_ylabel('Value')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
        
        if show:
            plt.show()
        
        plt.close()


def save_obj(vertices, triangles, colors=None, filepath='output.obj'):
    vertices = vertices.detach().cpu().numpy() if torch.is_tensor(vertices) else vertices
    triangles = triangles.detach().cpu().numpy() if torch.is_tensor(triangles) else triangles
    if colors is not None:
        colors = colors.detach().cpu().numpy() if torch.is_tensor(colors) else colors
    
    with open(filepath, 'w') as f:
        if colors is not None:
            for v, c in zip(vertices, colors):
                f.write(f'v {v[0]} {v[1]} {v[2]} {c[0]/255:.4f} {c[1]/255:.4f} {c[2]/255:.4f}\n')
        else:
            for v in vertices:
                f.write(f'v {v[0]} {v[1]} {v[2]}\n')
        
        for tri in triangles:
            f.write(f'f {tri[0]+1} {tri[1]+1} {tri[2]+1}\n')
    
    print(f'Saved mesh to {filepath}')


def save_ply(vertices, triangles, colors=None, filepath='output.ply'):
    vertices = vertices.detach().cpu().numpy() if torch.is_tensor(vertices) else vertices
    triangles = triangles.detach().cpu().numpy() if torch.is_tensor(triangles) else triangles
    if colors is not None:
        colors = colors.detach().cpu().numpy() if torch.is_tensor(colors) else colors
    
    n_verts = len(vertices)
    n_faces = len(triangles)
    
    with open(filepath, 'w') as f:
        f.write('ply\n')
        f.write('format ascii 1.0\n')
        f.write(f'element vertex {n_verts}\n')
        f.write('property float x\n')
        f.write('property float y\n')
        f.write('property float z\n')
        if colors is not None:
            f.write('property uchar red\n')
            f.write('property uchar green\n')
            f.write('property uchar blue\n')
        f.write(f'element face {n_faces}\n')
        f.write('property list uchar int vertex_index\n')
        f.write('end_header\n')
        
        if colors is not None:
            for v, c in zip(vertices, colors):
                f.write(f'{v[0]} {v[1]} {v[2]} {int(c[0])} {int(c[1])} {int(c[2])}\n')
        else:
            for v in vertices:
                f.write(f'{v[0]} {v[1]} {v[2]}\n')
        
        for tri in triangles:
            f.write(f'3 {tri[0]} {tri[1]} {tri[2]}\n')
    
    print(f'Saved mesh to {filepath}')
