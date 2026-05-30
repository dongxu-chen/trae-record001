import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np


class OrthogonalityConstraint(nn.Module):
    def __init__(self, weight=1.0):
        super(OrthogonalityConstraint, self).__init__()
        self.weight = weight
    
    def forward(self, id_base, exp_base):
        loss = self._compute_ortho_loss(id_base) + self._compute_ortho_loss(exp_base)
        return self.weight * loss
    
    def _compute_ortho_loss(self, basis):
        basis = basis.view(basis.shape[0], -1)
        basis_norm = F.normalize(basis, p=2, dim=0)
        
        gram = torch.matmul(basis_norm.t(), basis_norm)
        
        identity = torch.eye(gram.shape[0], device=basis.device)
        
        ortho_loss = torch.mean((gram - identity) ** 2)
        return ortho_loss


class IdentityExpressionDecorrelationLoss(nn.Module):
    def __init__(self, weight=1.0):
        super(IdentityExpressionDecorrelationLoss, self).__init__()
        self.weight = weight
    
    def forward(self, id_param, exp_param):
        batch_size = id_param.shape[0]
        
        id_normalized = F.normalize(id_param, p=2, dim=1)
        exp_normalized = F.normalize(exp_param, p=2, dim=1)
        
        correlation = torch.matmul(id_normalized.t(), exp_normalized)
        correlation = correlation / batch_size
        
        decorrelation_loss = torch.sum(torch.abs(correlation))
        
        return self.weight * decorrelation_loss


class ParameterOrthogonalityLoss(nn.Module):
    def __init__(self, id_basis=None, exp_basis=None, 
                 ortho_weight=0.1, decorr_weight=0.1, device='cpu'):
        super(ParameterOrthogonalityLoss, self).__init__()
        
        self.ortho_weight = ortho_weight
        self.decorr_weight = decorr_weight
        self.device = device
        
        self.ortho_constraint = OrthogonalityConstraint(weight=ortho_weight)
        self.decorrelation = IdentityExpressionDecorrelationLoss(weight=decorr_weight)
        
        self.id_basis = id_basis
        self.exp_basis = exp_basis
    
    def forward(self, id_param, exp_param, id_basis=None, exp_basis=None):
        loss = 0.0
        
        if id_basis is None:
            id_basis = self.id_basis
        if exp_basis is None:
            exp_basis = self.exp_basis
        
        if id_basis is not None and exp_basis is not None:
            id_basis = id_basis.to(self.device)
            exp_basis = exp_basis.to(self.device)
            
            cross_correlation = torch.matmul(id_basis.t(), exp_basis)
            cross_ortho_loss = torch.mean(torch.abs(cross_correlation) ** 2)
            loss += self.ortho_weight * 0.5 * cross_ortho_loss
        
        if id_param is not None:
            param_gram = torch.matmul(id_param.t(), id_param) / id_param.shape[0]
            id_identity = torch.eye(id_param.shape[1], device=self.device)
            loss += self.ortho_weight * torch.mean((param_gram - id_identity) ** 2) * 0.5
        
        if exp_param is not None:
            loss += self.decorrelation(id_param, exp_param)
        
        return loss


class LargeAnglePoseLoss(nn.Module):
    def __init__(self, weight=1.0, angle_threshold=60.0):
        super(LargeAnglePoseLoss, self).__init__()
        self.weight = weight
        self.angle_threshold = angle_threshold * np.pi / 180.0
    
    def forward(self, pose_param, target_pose=None):
        angles = pose_param[:, :3]
        
        angle_magnitudes = torch.sum(torch.abs(angles), dim=1)
        
        large_angle_mask = (angle_magnitudes > self.angle_threshold).float()
        
        if target_pose is not None:
            target_angles = target_pose[:, :3]
            pose_error = torch.mean((angles - target_angles) ** 2)
        else:
            pose_error = torch.mean(angle_magnitudes * large_angle_mask)
        
        return self.weight * pose_error


class PoseSmoothnessLoss(nn.Module):
    def __init__(self, weight=0.1):
        super(PoseSmoothnessLoss, self).__init__()
        self.weight = weight
    
    def forward(self, pose_seq):
        if len(pose_seq.shape) == 3:
            pose_diff = pose_seq[:, 1:] - pose_seq[:, :-1]
            smoothness_loss = torch.mean(torch.abs(pose_diff))
        else:
            smoothness_loss = torch.tensor(0.0, device=pose_seq.device)
        
        return self.weight * smoothness_loss


class LightingConsistencyLoss(nn.Module):
    def __init__(self, weight=1.0):
        super(LightingConsistencyLoss, self).__init__()
        self.weight = weight
    
    def forward(self, textures, lighting_params=None):
        batch_size = textures.shape[0]
        
        if batch_size > 1:
            texture_std = torch.std(textures, dim=0)
            consistency_loss = torch.mean(texture_std)
        else:
            consistency_loss = torch.tensor(0.0)
        
        if lighting_params is not None and batch_size > 1:
            lighting_std = torch.std(lighting_params, dim=0)
            consistency_loss += 0.1 * torch.mean(lighting_std)
        
        return self.weight * consistency_loss


class CrossLightingTextureLoss(nn.Module):
    def __init__(self, weight=1.0, num_light_samples=3):
        super(CrossLightingTextureLoss, self).__init__()
        self.weight = weight
        self.num_light_samples = num_light_samples
    
    def forward(self, textures, lit_textures_list):
        batch_size = textures.shape[0]
        loss = 0.0
        
        if len(lit_textures_list) >= 2:
            for i in range(len(lit_textures_list)):
                for j in range(i + 1, len(lit_textures_list)):
                    texture_diff = torch.mean(torch.abs(
                        lit_textures_list[i] - lit_textures_list[j]))
                    loss += texture_diff
            
            loss = loss / (len(lit_textures_list) * (len(lit_textures_list) - 1) / 2)
        
        return self.weight * loss


class AlbedoRegularizationLoss(nn.Module):
    def __init__(self, weight=0.01):
        super(AlbedoRegularizationLoss, self).__init__()
        self.weight = weight
    
    def forward(self, albedo):
        grad_x = torch.abs(albedo[:, :, 1:] - albedo[:, :, :-1])
        grad_y = torch.abs(albedo[:, 1:, :] - albedo[:, :-1, :])
        
        smoothness_loss = torch.mean(grad_x) + torch.mean(grad_y)
        
        return self.weight * smoothness_loss


class EnhancedTotalLoss(nn.Module):
    def __init__(self, weights=None, device='cpu'):
        super(EnhancedTotalLoss, self).__init__()
        
        if weights is None:
            self.weights = {
                'landmark': 1.0,
                'photometric': 0.5,
                'perceptual': 0.1,
                'regularization': 1e-4,
                'orthogonality': 0.01,
                'lighting_consistency': 0.1,
                'cross_lighting': 0.05
            }
        else:
            self.weights = weights
        
        self.device = device
        
        from param_regression import LandmarkLoss, PhotometricLoss, PerceptualLoss
        
        self.landmark_loss = LandmarkLoss()
        self.photometric_loss = PhotometricLoss()
        try:
            self.perceptual_loss = PerceptualLoss(device=device)
        except:
            self.perceptual_loss = None
        
        self.ortho_loss = ParameterOrthogonalityLoss(
            ortho_weight=self.weights.get('orthogonality'),
            decorr_weight=self.weights.get('orthogonality') * 0.5,
            device=device
        )
        
        self.lighting_consistency_loss = LightingConsistencyLoss(
            weight=self.weights.get('lighting_consistency')
        )
        
        self.cross_lighting_loss = CrossLightingTextureLoss(
            weight=self.weights.get('cross_lighting')
        )
    
    def forward(self, pred_dict, target_dict, params=None, id_basis=None, exp_basis=None):
        loss = 0.0
        loss_dict = {}
        
        if 'landmarks' in pred_dict and 'landmarks' in target_dict:
            lm_loss = self.weights['landmark'] * self.landmark_loss(
                pred_dict['landmarks'], target_dict['landmarks'])
            loss += lm_loss
            loss_dict['landmark'] = lm_loss.item()
        
        if 'image' in pred_dict and 'image' in target_dict:
            photo_loss = self.weights['photometric'] * self.photometric_loss(
                pred_dict['image'], target_dict['image'])
            loss += photo_loss
            loss_dict['photometric'] = photo_loss.item()
            
            if self.perceptual_loss is not None:
                perc_loss = self.weights['perceptual'] * self.perceptual_loss(
                    pred_dict['image'], target_dict['image'])
                loss += perc_loss
                loss_dict['perceptual'] = perc_loss.item()
        
        if params is not None:
            reg_loss = 0.0
            for key in ['shape', 'exp', 'tex']:
                if key in params:
                    reg_loss += torch.sum(params[key] ** 2)
            reg_loss = self.weights['regularization'] * reg_loss
            loss += reg_loss
            loss_dict['regularization'] = reg_loss.item()
            
            if 'shape' in params and 'exp' in params:
                ortho_loss = self.ortho_loss(
                    params['shape'], params['exp'], id_basis, exp_basis)
                loss += ortho_loss
                loss_dict['orthogonality'] = ortho_loss.item()
        
        if 'albedo' in pred_dict:
            lighting_loss = self.lighting_consistency_loss(pred_dict['albedo'])
            loss += lighting_loss
            loss_dict['lighting_consistency'] = lighting_loss.item()
        
        return loss, loss_dict


def compute_gradient_penalty(critic, real_data, fake_data, device='cpu'):
    batch_size = real_data.size(0)
    
    alpha = torch.rand(batch_size, 1, 1, device=device)
    
    interpolates = (alpha * real_data + (1 - alpha) * fake_data)
    interpolates.requires_grad_(True)
    
    critic_interpolates = critic(interpolates)
    
    gradients = torch.autograd.grad(
        outputs=critic_interpolates,
        inputs=interpolates,
        grad_outputs=torch.ones_like(critic_interpolates),
        create_graph=True,
        retain_graph=True,
        only_inputs=True,
    )[0]
    
    gradients = gradients.view(batch_size, -1)
    gradient_penalty = ((gradients.norm(2, dim=1) - 1) ** 2).mean()
    
    return gradient_penalty


class AdversarialLoss(nn.Module):
    def __init__(self, weight=0.001):
        super(AdversarialLoss, self).__init__()
        self.weight = weight
    
    def forward(self, real_pred, fake_pred):
        real_loss = torch.mean((real_pred - 1) ** 2)
        fake_loss = torch.mean(fake_pred ** 2)
        return self.weight * (real_loss + fake_loss)
