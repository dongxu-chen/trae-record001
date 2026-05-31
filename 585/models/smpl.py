import pickle
import numpy as np
import torch
import torch.nn as nn
from typing import Tuple, Optional


class SMPL(nn.Module):
    def __init__(self, model_path: str, device: str = 'cpu'):
        super(SMPL, self).__init__()
        self.device = device
        self._load_model(model_path)
        self._build_kinematic_tree()
    
    def _load_model(self, model_path: str):
        with open(model_path, 'rb') as f:
            smpl_model = pickle.load(f, encoding='latin1')
        
        self.register_buffer('v_template', 
            torch.tensor(smpl_model['v_template'], dtype=torch.float32, device=self.device))
        
        self.register_buffer('shapedirs', 
            torch.tensor(smpl_model['shapedirs'], dtype=torch.float32, device=self.device))
        
        self.register_buffer('posedirs', 
            torch.tensor(smpl_model['posedirs'], dtype=torch.float32, device=self.device))
        
        self.register_buffer('J_regressor', 
            torch.tensor(smpl_model['J_regressor'].toarray(), dtype=torch.float32, device=self.device))
        
        self.register_buffer('weights', 
            torch.tensor(smpl_model['weights'], dtype=torch.float32, device=self.device))
        
        self.kintree_table = smpl_model['kintree_table'].astype(np.int32)
        self.faces = smpl_model['f'].astype(np.int32)
        
        self.num_vertices = self.v_template.shape[0]
        self.num_joints = self.J_regressor.shape[0]
        self.num_shape_params = self.shapedirs.shape[-1]
    
    def _build_kinematic_tree(self):
        self.parent = {}
        for i in range(self.kintree_table.shape[1]):
            child = self.kintree_table[1, i]
            parent = self.kintree_table[0, i]
            if child != -1:
                self.parent[child] = parent
            else:
                self.parent[self.kintree_table[1, i]] = -1
        
        self.root_joint = 0
        self.children = {}
        for child, parent in self.parent.items():
            if parent not in self.children:
                self.children[parent] = []
            self.children[parent].append(child)
    
    def _axis_angle_to_matrix(self, axis_angle: torch.Tensor) -> torch.Tensor:
        angle = torch.norm(axis_angle + 1e-8, dim=-1, keepdim=True)
        axis = axis_angle / (angle + 1e-8)
        
        cos = torch.cos(angle)
        sin = torch.sin(angle)
        
        x, y, z = axis[..., 0], axis[..., 1], axis[..., 2]
        
        row1 = torch.stack([cos + x*x*(1-cos), x*y*(1-cos) - z*sin, x*z*(1-cos) + y*sin], dim=-1)
        row2 = torch.stack([y*x*(1-cos) + z*sin, cos + y*y*(1-cos), y*z*(1-cos) - x*sin], dim=-1)
        row3 = torch.stack([z*x*(1-cos) - y*sin, z*y*(1-cos) + x*sin, cos + z*z*(1-cos)], dim=-1)
        
        return torch.stack([row1, row2, row3], dim=-2)
    
    def _compute_vertices_shaped(self, betas: torch.Tensor) -> torch.Tensor:
        v_shaped = self.v_template + torch.einsum('bl,lkm->bkm', betas, self.shapedirs)
        return v_shaped
    
    def _compute_joints(self, v_shaped: torch.Tensor) -> torch.Tensor:
        J = torch.einsum('bik,ji->bjk', v_shaped, self.J_regressor)
        return J
    
    def _lbs(self, pose: torch.Tensor, v_shaped: torch.Tensor, J: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        batch_size = pose.shape[0]
        
        pose_matrix = self._axis_angle_to_matrix(pose.view(-1, 3)).view(batch_size, -1, 3, 3)
        
        pose_feature = (pose_matrix[:, 1:] - torch.eye(3, device=self.device)).view(batch_size, -1)
        v_posed = v_shaped + torch.einsum('bl,lkm->bkm', pose_feature, self.posedirs)
        
        J = J.unsqueeze(-1)
        
        G = torch.zeros(batch_size, self.num_joints, 4, 4, device=self.device)
        G[:, :, :3, :3] = pose_matrix
        G[:, :, :3, 3] = J.squeeze(-1)
        G[:, :, 3, 3] = 1.0
        
        for i in range(1, self.num_joints):
            parent = self.parent[i]
            G[:, i] = torch.bmm(G[:, parent].clone(), G[:, i].clone())
        
        G = G.view(batch_size, self.num_joints, 16)
        
        v_posed_hom = torch.cat([v_posed, torch.ones(batch_size, self.num_vertices, 1, device=self.device)], dim=-1)
        
        weights_expanded = self.weights.unsqueeze(0).unsqueeze(-1)
        G_expanded = G.unsqueeze(1).expand(-1, self.num_vertices, -1, -1)
        
        T = torch.sum(weights_expanded * G_expanded, dim=2).view(batch_size, self.num_vertices, 4, 4)
        
        v_transformed = torch.bmm(T.reshape(-1, 4, 4), v_posed_hom.reshape(-1, 4, 1))
        v_transformed = v_transformed.reshape(batch_size, self.num_vertices, 4)
        
        vertices = v_transformed[..., :3]
        
        joints = G[..., 3].view(batch_size, self.num_joints, 4, 4)[..., :3, 3]
        
        return vertices, joints
    
    def forward(self, betas: torch.Tensor, pose: torch.Tensor, 
                trans: Optional[torch.Tensor] = None) -> Tuple[torch.Tensor, torch.Tensor]:
        batch_size = betas.shape[0]
        
        if betas.shape[1] < self.num_shape_params:
            padding = torch.zeros(batch_size, self.num_shape_params - betas.shape[1], 
                                device=self.device)
            betas = torch.cat([betas, padding], dim=1)
        
        v_shaped = self._compute_vertices_shaped(betas)
        J = self._compute_joints(v_shaped)
        vertices, joints = self._lbs(pose, v_shaped, J)
        
        if trans is not None:
            vertices = vertices + trans.unsqueeze(1)
            joints = joints + trans.unsqueeze(1)
        
        return vertices, joints
    
    def get_faces(self) -> np.ndarray:
        return self.faces
    
    def get_joint_regressor(self) -> torch.Tensor:
        return self.J_regressor


class SMPLJointExtractor(nn.Module):
    def __init__(self, smpl_model: SMPL, device: str = 'cpu'):
        super(SMPLJointExtractor, self).__init__()
        self.smpl = smpl_model
        self.device = device
        
        self.extra_joints_regressor = torch.zeros(14, self.smpl.num_vertices, device=self.device)
        
        self.joint_map = {
            'nose': 0, 'reye': 1, 'leye': 2, 'rear': 3, 'lear': 4,
            'rwrist': 5, 'lwrist': 6, 'rankle': 7, 'lankle': 8,
            'rbigtoe': 9, 'lbigtoe': 10, 'rsmalltoe': 11, 'lsmalltoe': 12, 'heel': 13
        }
    
    def forward(self, vertices: torch.Tensor) -> torch.Tensor:
        extra_joints = torch.einsum('bik,ji->bjk', vertices, self.extra_joints_regressor)
        
        smpl_joints = torch.einsum('bik,ji->bjk', vertices, self.smpl.J_regressor)
        
        all_joints = torch.cat([smpl_joints, extra_joints], dim=1)
        
        return all_joints
