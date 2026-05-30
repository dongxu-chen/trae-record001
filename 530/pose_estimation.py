import numpy as np
import cv2
import torch


class PoseEstimator:
    def __init__(self, camera_intrinsics=None):
        if camera_intrinsics is None:
            self.focal_length = 1015.0
            self.center = (112.0, 112.0)
        else:
            self.focal_length = camera_intrinsics['f']
            self.center = camera_intrinsics['c']
        
        self.camera_matrix = np.array([
            [self.focal_length, 0, self.center[0]],
            [0, self.focal_length, self.center[1]],
            [0, 0, 1]
        ], dtype=np.float32)
        
        self.dist_coeffs = np.zeros((5, 1), dtype=np.float32)
    
    def estimate_pose(self, landmarks_2d, landmarks_3d):
        success, rvec, tvec = cv2.solvePnP(
            landmarks_3d.astype(np.float32),
            landmarks_2d.astype(np.float32),
            self.camera_matrix,
            self.dist_coeffs,
            flags=cv2.SOLVEPNP_EPNP
        )
        
        if success:
            rotation_matrix, _ = cv2.Rodrigues(rvec)
            euler_angles = self._rotation_matrix_to_euler(rotation_matrix)
            return euler_angles, tvec.flatten(), rotation_matrix
        else:
            return np.zeros(3), np.zeros(3), np.eye(3)
    
    def _rotation_matrix_to_euler(self, R):
        sy = np.sqrt(R[0, 0] ** 2 + R[1, 0] ** 2)
        
        singular = sy < 1e-6
        
        if not singular:
            x = np.arctan2(R[2, 1], R[2, 2])
            y = np.arctan2(-R[2, 0], sy)
            z = np.arctan2(R[1, 0], R[0, 0])
        else:
            x = np.arctan2(-R[1, 2], R[1, 1])
            y = np.arctan2(-R[2, 0], sy)
            z = 0
        
        return np.array([x, y, z], dtype=np.float32)
    
    def project_points(self, points_3d, rvec, tvec):
        points_2d, _ = cv2.projectPoints(
            points_3d,
            rvec,
            tvec,
            self.camera_matrix,
            self.dist_coeffs
        )
        return points_2d.reshape(-1, 2)


class LightEstimator:
    def __init__(self):
        self.num_sh_bands = 3
        self.num_sh_coeffs = 9
    
    def estimate_lighting(self, image, vertices, normals, triangles):
        h, w = image.shape[:2]
        
        vertices_2d = vertices[:, :2]
        vertices_2d[:, 0] = np.clip(vertices_2d[:, 0], 0, w - 1)
        vertices_2d[:, 1] = np.clip(vertices_2d[:, 1], 0, h - 1)
        
        colors = np.zeros((len(vertices), 3), dtype=np.float32)
        for i, (x, y) in enumerate(vertices_2d):
            colors[i] = image[int(y), int(x)] / 255.0
        
        sh_coeffs = self._solve_sh_coeffs(normals, colors)
        
        return sh_coeffs
    
    def _solve_sh_coeffs(self, normals, colors):
        n = len(normals)
        A = np.zeros((n, self.num_sh_coeffs), dtype=np.float32)
        
        x, y, z = normals[:, 0], normals[:, 1], normals[:, 2]
        
        A[:, 0] = 1 / np.sqrt(4 * np.pi)
        A[:, 1] = np.sqrt(3) / np.sqrt(4 * np.pi) * y
        A[:, 2] = np.sqrt(3) / np.sqrt(4 * np.pi) * z
        A[:, 3] = np.sqrt(3) / np.sqrt(4 * np.pi) * x
        A[:, 4] = np.sqrt(15) / np.sqrt(4 * np.pi) * x * y
        A[:, 5] = np.sqrt(15) / np.sqrt(4 * np.pi) * y * z
        A[:, 6] = np.sqrt(5) / np.sqrt(16 * np.pi) * (3 * z**2 - 1)
        A[:, 7] = np.sqrt(15) / np.sqrt(4 * np.pi) * x * z
        A[:, 8] = np.sqrt(15) / np.sqrt(16 * np.pi) * (x**2 - y**2)
        
        sh_coeffs = np.zeros((3, self.num_sh_coeffs), dtype=np.float32)
        for c in range(3):
            sh_coeffs[c] = np.linalg.lstsq(A, colors[:, c], rcond=None)[0]
        
        return sh_coeffs.T.flatten()


def compute_face_normals(vertices, triangles):
    normals = np.zeros_like(vertices)
    
    for tri in triangles:
        v0 = vertices[tri[0]]
        v1 = vertices[tri[1]]
        v2 = vertices[tri[2]]
        
        face_normal = np.cross(v1 - v0, v2 - v0)
        face_normal = face_normal / (np.linalg.norm(face_normal) + 1e-8)
        
        normals[tri[0]] += face_normal
        normals[tri[1]] += face_normal
        normals[tri[2]] += face_normal
    
    norms = np.linalg.norm(normals, axis=1, keepdims=True)
    normals = normals / (norms + 1e-8)
    
    return normals


def render_lighting(vertices, normals, sh_coeffs, colors=None):
    n = len(vertices)
    shading = np.zeros((n, 3), dtype=np.float32)
    
    sh_coeffs = sh_coeffs.reshape(9, 3)
    
    x, y, z = normals[:, 0], normals[:, 1], normals[:, 2]
    
    sh_basis = np.zeros((n, 9), dtype=np.float32)
    sh_basis[:, 0] = 1 / np.sqrt(4 * np.pi)
    sh_basis[:, 1] = np.sqrt(3) / np.sqrt(4 * np.pi) * y
    sh_basis[:, 2] = np.sqrt(3) / np.sqrt(4 * np.pi) * z
    sh_basis[:, 3] = np.sqrt(3) / np.sqrt(4 * np.pi) * x
    sh_basis[:, 4] = np.sqrt(15) / np.sqrt(4 * np.pi) * x * y
    sh_basis[:, 5] = np.sqrt(15) / np.sqrt(4 * np.pi) * y * z
    sh_basis[:, 6] = np.sqrt(5) / np.sqrt(16 * np.pi) * (3 * z**2 - 1)
    sh_basis[:, 7] = np.sqrt(15) / np.sqrt(4 * np.pi) * x * z
    sh_basis[:, 8] = np.sqrt(15) / np.sqrt(16 * np.pi) * (x**2 - y**2)
    
    shading = np.dot(sh_basis, sh_coeffs)
    
    if colors is not None:
        lit_colors = colors * shading
        lit_colors = np.clip(lit_colors, 0, 1)
        return lit_colors, shading
    
    return shading
