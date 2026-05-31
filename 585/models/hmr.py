import torch
import torch.nn as nn
import torchvision.models as models
from typing import Tuple, Optional


class ResNetBackbone(nn.Module):
    def __init__(self, pretrained: bool = True):
        super(ResNetBackbone, self).__init__()
        resnet = models.resnet50(pretrained=pretrained)
        
        self.conv1 = resnet.conv1
        self.bn1 = resnet.bn1
        self.relu = resnet.relu
        self.maxpool = resnet.maxpool
        
        self.layer1 = resnet.layer1
        self.layer2 = resnet.layer2
        self.layer3 = resnet.layer3
        self.layer4 = resnet.layer4
        
        self.avgpool = resnet.avgpool
        
        self.num_features = resnet.fc.in_features
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.conv1(x)
        x = self.bn1(x)
        x = self.relu(x)
        x = self.maxpool(x)
        
        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        x = self.layer4(x)
        
        x = self.avgpool(x)
        x = x.view(x.size(0), -1)
        
        return x


class HMREncoder(nn.Module):
    def __init__(self, num_features: int = 2048, hidden_dim: int = 1024,
                 num_shape_params: int = 10, num_pose_params: int = 72):
        super(HMREncoder, self).__init__()
        
        self.num_shape_params = num_shape_params
        self.num_pose_params = num_pose_params
        
        self.fc1 = nn.Linear(num_features, hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, hidden_dim)
        
        self.dropout = nn.Dropout(0.5)
        self.relu = nn.ReLU()
        
        self.beta_head = nn.Linear(hidden_dim, num_shape_params)
        self.pose_head = nn.Linear(hidden_dim, num_pose_params)
        self.camera_head = nn.Linear(hidden_dim, 3)
    
    def forward(self, features: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        x = self.relu(self.fc1(features))
        x = self.dropout(x)
        x = self.relu(self.fc2(x))
        
        betas = self.beta_head(x)
        pose = self.pose_head(x)
        camera = self.camera_head(x)
        
        return betas, pose, camera


class IterativeFeedback(nn.Module):
    def __init__(self, num_features: int = 2048, smpl_param_dim: int = 85,
                 hidden_dim: int = 1024):
        super(IterativeFeedback, self).__init__()
        
        self.fc_input = nn.Linear(num_features + smpl_param_dim, hidden_dim)
        self.fc_hidden = nn.Linear(hidden_dim, hidden_dim)
        self.fc_output = nn.Linear(hidden_dim, smpl_param_dim)
        
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(0.5)
    
    def forward(self, features: torch.Tensor, 
                prev_params: torch.Tensor) -> torch.Tensor:
        x = torch.cat([features, prev_params], dim=1)
        x = self.relu(self.fc_input(x))
        x = self.dropout(x)
        x = self.relu(self.fc_hidden(x))
        x = self.dropout(x)
        delta = self.fc_output(x)
        return prev_params + delta


class HMR(nn.Module):
    def __init__(self, num_shape_params: int = 10, num_pose_params: int = 72,
                 num_iterations: int = 3, pretrained_backbone: bool = True):
        super(HMR, self).__init__()
        
        self.num_shape_params = num_shape_params
        self.num_pose_params = num_pose_params
        self.num_iterations = num_iterations
        
        self.backbone = ResNetBackbone(pretrained=pretrained_backbone)
        
        self.encoder = HMREncoder(
            num_features=self.backbone.num_features,
            num_shape_params=num_shape_params,
            num_pose_params=num_pose_params
        )
        
        smpl_param_dim = num_shape_params + num_pose_params + 3
        self.feedback = IterativeFeedback(
            num_features=self.backbone.num_features,
            smpl_param_dim=smpl_param_dim
        )
    
    def forward(self, images: torch.Tensor, 
                return_all_iterations: bool = False
                ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        features = self.backbone(images)
        
        betas, pose, camera = self.encoder(features)
        
        all_betas = [betas]
        all_poses = [pose]
        all_cameras = [camera]
        
        for _ in range(self.num_iterations - 1):
            prev_params = torch.cat([betas, pose, camera], dim=1)
            delta_params = self.feedback(features, prev_params)
            
            betas = delta_params[:, :self.num_shape_params]
            pose = delta_params[:, self.num_shape_params:self.num_shape_params + self.num_pose_params]
            camera = delta_params[:, -3:]
            
            all_betas.append(betas)
            all_poses.append(pose)
            all_cameras.append(camera)
        
        if return_all_iterations:
            return torch.stack(all_betas), torch.stack(all_poses), torch.stack(all_cameras)
        
        return betas, pose, camera
    
    def load_pretrained(self, checkpoint_path: str, device: str = 'cpu'):
        try:
            checkpoint = torch.load(checkpoint_path, map_location=device)
            
            if 'model_state_dict' in checkpoint:
                state_dict = checkpoint['model_state_dict']
            elif 'state_dict' in checkpoint:
                state_dict = checkpoint['state_dict']
            else:
                state_dict = checkpoint
            
            self.load_state_dict(state_dict, strict=False)
            print(f"Loaded pretrained weights from {checkpoint_path}")
        except Exception as e:
            print(f"Warning: Could not load pretrained weights: {e}")
            print("Using randomly initialized weights.")


class WeakPerspectiveCamera(nn.Module):
    def __init__(self):
        super(WeakPerspectiveCamera, self).__init__()
    
    def forward(self, points_3d: torch.Tensor, camera: torch.Tensor) -> torch.Tensor:
        scale = camera[:, 0:1].unsqueeze(-1)
        translation = camera[:, 1:].unsqueeze(1)
        
        points_2d = scale * (points_3d[:, :, :2] + translation)
        
        return points_2d
    
    def project(self, points_3d: torch.Tensor, camera: torch.Tensor) -> torch.Tensor:
        return self.forward(points_3d, camera)
