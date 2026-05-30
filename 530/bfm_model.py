import torch
import numpy as np
from scipy.io import loadmat
import config


class BFMModel:
    def __init__(self, model_path=None, device='cpu'):
        self.device = device
        if model_path is None:
            model_path = config.BFM_MODEL_PATH
        
        self._load_model(model_path)
        self._to_tensor()
    
    def _load_model(self, model_path):
        try:
            model = loadmat(model_path)
            self.meanshape = model['meanshape'].astype(np.float32)
            self.idBase = model['idBase'].astype(np.float32)
            self.expBase = model['expBase'].astype(np.float32)
            self.meantex = model['meantex'].astype(np.float32)
            self.texBase = model['texBase'].astype(np.float32)
            self.tri = model['tri'].astype(np.int32) - 1
            self.keypoints = model['keypoints'].astype(np.int32).flatten() - 1
            self.point_buf = model['point_buf'].astype(np.int32) - 1
        except:
            self._create_synthetic_model()
        
        self.n_vertices = self.meanshape.shape[0] // 3
        self.n_triangles = self.tri.shape[0]
    
    def _create_synthetic_model(self):
        print("Warning: BFM model file not found, creating synthetic model for demonstration...")
        
        self.n_vertices = 35709
        self.n_triangles = 70789
        
        self.meanshape = np.zeros((self.n_vertices * 3, 1), dtype=np.float32)
        self.idBase = np.random.randn(self.n_vertices * 3, config.SHAPE_DIM).astype(np.float32) * 1e-5
        self.expBase = np.random.randn(self.n_vertices * 3, config.EXP_DIM).astype(np.float32) * 1e-5
        self.meantex = np.ones((self.n_vertices * 3, 1), dtype=np.float32) * 128
        self.texBase = np.random.randn(self.n_vertices * 3, config.TEX_DIM).astype(np.float32) * 1e-3
        
        self.tri = self._generate_triangles(self.n_vertices)
        
        self.keypoints = self._generate_keypoints()
        
        self.point_buf = self._generate_point_buf()
    
    def _generate_triangles(self, n_vertices):
        import math
        grid_size = int(math.sqrt(n_vertices))
        triangles = []
        
        for i in range(grid_size - 1):
            for j in range(grid_size - 1):
                idx = i * grid_size + j
                triangles.append([idx, idx + 1, idx + grid_size])
                triangles.append([idx + 1, idx + grid_size + 1, idx + grid_size])
        
        triangles = np.array(triangles, dtype=np.int32)
        return triangles[:self.n_triangles]
    
    def _generate_keypoints(self):
        kpts = []
        grid_size = int(np.sqrt(self.n_vertices))
        
        center = grid_size // 2
        
        kpts.extend([center - 30 + i * 5 for i in range(17)])
        
        kpts.extend([center * grid_size + center - 20 + i * 5 for i in range(5)])
        kpts.extend([center * grid_size + center + i * 5 for i in range(5)])
        
        kpts.extend([center * grid_size + center - 10 + i * 2 for i in range(5)])
        kpts.extend([center * grid_size + center + i * 2 for i in range(5)])
        kpts.extend([center * grid_size + center - 5 + i for i in range(6)])
        
        kpts.extend([center * grid_size + center + 10 + i * 3 for i in range(7)])
        kpts.extend([center * grid_size + center + 20 + i * 2 for i in range(5)])
        
        return np.array(kpts[:68], dtype=np.int32)
    
    def _generate_point_buf(self):
        point_buf = np.zeros((self.n_vertices, 8), dtype=np.int32) - 1
        for i, tri in enumerate(self.tri):
            for v in tri:
                for j in range(8):
                    if point_buf[v, j] == -1:
                        point_buf[v, j] = i
                        break
        return point_buf
    
    def _to_tensor(self):
        self.meanshape_t = torch.from_numpy(self.meanshape).float().to(self.device)
        self.idBase_t = torch.from_numpy(self.idBase).float().to(self.device)
        self.expBase_t = torch.from_numpy(self.expBase).float().to(self.device)
        self.meantex_t = torch.from_numpy(self.meantex).float().to(self.device)
        self.texBase_t = torch.from_numpy(self.texBase).float().to(self.device)
        self.tri_t = torch.from_numpy(self.tri).long().to(self.device)
        self.keypoints_t = torch.from_numpy(self.keypoints).long().to(self.device)
    
    def compute_shape(self, id_param, exp_param):
        id_param = id_param.to(self.device)
        exp_param = exp_param.to(self.device)
        
        batch_size = id_param.shape[0]
        
        meanshape = self.meanshape_t.view(1, -1).repeat(batch_size, 1)
        id_offset = torch.matmul(id_param, self.idBase_t.t())
        exp_offset = torch.matmul(exp_param, self.expBase_t.t())
        
        vertices = meanshape + id_offset + exp_offset
        vertices = vertices.view(batch_size, -1, 3)
        
        return vertices
    
    def compute_texture(self, tex_param):
        tex_param = tex_param.to(self.device)
        
        batch_size = tex_param.shape[0]
        
        meantex = self.meantex_t.view(1, -1).repeat(batch_size, 1)
        tex_offset = torch.matmul(tex_param, self.texBase_t.t())
        
        texture = meantex + tex_offset
        texture = texture.view(batch_size, -1, 3)
        texture = torch.clamp(texture, 0, 255)
        
        return texture
    
    def get_landmarks(self, vertices):
        batch_size = vertices.shape[0]
        landmarks = vertices[:, self.keypoints_t, :]
        return landmarks
    
    def transform_vertices(self, vertices, pose):
        batch_size = vertices.shape[0]
        
        angles = pose[:, :3]
        translation = pose[:, 3:6]
        
        rotation_matrix = self._compute_rotation_matrix(angles)
        
        vertices_transformed = torch.matmul(vertices, rotation_matrix.transpose(1, 2))
        vertices_transformed = vertices_transformed + translation.view(batch_size, 1, 3)
        
        return vertices_transformed
    
    def _compute_rotation_matrix(self, angles):
        batch_size = angles.shape[0]
        
        pitch = angles[:, 0]
        yaw = angles[:, 1]
        roll = angles[:, 2]
        
        cos_p = torch.cos(pitch)
        sin_p = torch.sin(pitch)
        cos_y = torch.cos(yaw)
        sin_y = torch.sin(yaw)
        cos_r = torch.cos(roll)
        sin_r = torch.sin(roll)
        
        R_x = torch.zeros(batch_size, 3, 3, device=self.device)
        R_x[:, 0, 0] = 1
        R_x[:, 1, 1] = cos_p
        R_x[:, 1, 2] = -sin_p
        R_x[:, 2, 1] = sin_p
        R_x[:, 2, 2] = cos_p
        
        R_y = torch.zeros(batch_size, 3, 3, device=self.device)
        R_y[:, 0, 0] = cos_y
        R_y[:, 0, 2] = sin_y
        R_y[:, 1, 1] = 1
        R_y[:, 2, 0] = -sin_y
        R_y[:, 2, 2] = cos_y
        
        R_z = torch.zeros(batch_size, 3, 3, device=self.device)
        R_z[:, 0, 0] = cos_r
        R_z[:, 0, 1] = -sin_r
        R_z[:, 1, 0] = sin_r
        R_z[:, 1, 1] = cos_r
        R_z[:, 2, 2] = 1
        
        R = torch.matmul(R_z, torch.matmul(R_y, R_x))
        
        return R
    
    def apply_lighting(self, vertices, texture, light_param):
        batch_size = vertices.shape[0]
        
        normals = self._compute_normals(vertices)
        
        sh_coeffs = light_param.view(batch_size, 9, 3)
        
        shading = self._compute_spherical_harmonics(normals, sh_coeffs)
        
        lit_texture = texture * shading
        lit_texture = torch.clamp(lit_texture, 0, 255)
        
        return lit_texture, shading
    
    def _compute_normals(self, vertices):
        batch_size = vertices.shape[0]
        
        v0 = vertices[:, self.tri_t[:, 0], :]
        v1 = vertices[:, self.tri_t[:, 1], :]
        v2 = vertices[:, self.tri_t[:, 2], :]
        
        face_normals = torch.cross(v1 - v0, v2 - v0, dim=2)
        face_normals = face_normals / (torch.norm(face_normals, dim=2, keepdim=True) + 1e-6)
        
        vertex_normals = torch.zeros_like(vertices)
        for i in range(3):
            idx = self.tri_t[:, i].view(1, -1, 1).repeat(batch_size, 1, 3)
            vertex_normals.scatter_add_(1, idx, face_normals.unsqueeze(2).repeat(1, 1, 3, 1).view(batch_size, -1, 3))
        
        vertex_normals = vertex_normals / (torch.norm(vertex_normals, dim=2, keepdim=True) + 1e-6)
        
        return vertex_normals
    
    def _compute_spherical_harmonics(self, normals, sh_coeffs):
        batch_size = normals.shape[0]
        n_vertices = normals.shape[1]
        
        x = normals[:, :, 0]
        y = normals[:, :, 1]
        z = normals[:, :, 2]
        
        sh_basis = torch.zeros(batch_size, n_vertices, 9, device=self.device)
        
        sh_basis[:, :, 0] = 1 / np.sqrt(4 * np.pi)
        sh_basis[:, :, 1] = (np.sqrt(3) / np.sqrt(4 * np.pi)) * y
        sh_basis[:, :, 2] = (np.sqrt(3) / np.sqrt(4 * np.pi)) * z
        sh_basis[:, :, 3] = (np.sqrt(3) / np.sqrt(4 * np.pi)) * x
        sh_basis[:, :, 4] = (np.sqrt(15) / np.sqrt(4 * np.pi)) * x * y
        sh_basis[:, :, 5] = (np.sqrt(15) / np.sqrt(4 * np.pi)) * y * z
        sh_basis[:, :, 6] = (np.sqrt(5) / np.sqrt(16 * np.pi)) * (3 * z**2 - 1)
        sh_basis[:, :, 7] = (np.sqrt(15) / np.sqrt(4 * np.pi)) * x * z
        sh_basis[:, :, 8] = (np.sqrt(15) / np.sqrt(16 * np.pi)) * (x**2 - y**2)
        
        shading = torch.matmul(sh_basis.unsqueeze(2), sh_coeffs.unsqueeze(1).repeat(1, n_vertices, 1, 1))
        shading = shading.squeeze(2)
        
        return shading
    
    def project_vertices(self, vertices, f=1015.0, cx=112.0, cy=112.0):
        batch_size = vertices.shape[0]
        
        z = vertices[:, :, 2:3]
        x = vertices[:, :, 0:1] * f / z + cx
        y = vertices[:, :, 1:2] * f / z + cy
        
        vertices_2d = torch.cat([x, y], dim=2)
        
        return vertices_2d
