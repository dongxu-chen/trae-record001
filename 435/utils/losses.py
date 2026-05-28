import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Tuple
from config import Config


class EdgeAwareLoss(nn.Module):
    def __init__(self, loss_type: str = 'l1'):
        super(EdgeAwareLoss, self).__init__()
        
        sobel_x = torch.tensor([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=torch.float32)
        sobel_y = torch.tensor([[1, 2, 1], [0, 0, 0], [-1, -2, -1]], dtype=torch.float32)
        
        self.register_buffer('sobel_x', sobel_x.unsqueeze(0).unsqueeze(0))
        self.register_buffer('sobel_y', sobel_y.unsqueeze(0).unsqueeze(0))
        
        if loss_type == 'l1':
            self.criterion = nn.L1Loss()
        elif loss_type == 'mse':
            self.criterion = nn.MSELoss()
        else:
            raise ValueError(f"Unknown loss type: {loss_type}")

    def compute_edges(self, x: torch.Tensor) -> torch.Tensor:
        batch_size, channels, height, width = x.size()
        
        edges = []
        for c in range(channels):
            channel = x[:, c:c+1, :, :]
            edge_x = F.conv2d(channel, self.sobel_x, padding=1)
            edge_y = F.conv2d(channel, self.sobel_y, padding=1)
            edge = torch.sqrt(edge_x ** 2 + edge_y ** 2 + 1e-8)
            edges.append(edge)
        
        edges = torch.cat(edges, dim=1)
        return edges

    def forward(self, pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        pred_edges = self.compute_edges(pred)
        target_edges = self.compute_edges(target)
        
        loss = self.criterion(pred_edges, target_edges)
        return loss


class LaplacianEdgeLoss(nn.Module):
    def __init__(self, loss_type: str = 'l1'):
        super(LaplacianEdgeLoss, self).__init__()
        
        laplacian = torch.tensor([[0, 1, 0], [1, -4, 1], [0, 1, 0]], dtype=torch.float32)
        self.register_buffer('laplacian', laplacian.unsqueeze(0).unsqueeze(0))
        
        if loss_type == 'l1':
            self.criterion = nn.L1Loss()
        elif loss_type == 'mse':
            self.criterion = nn.MSELoss()

    def compute_laplacian(self, x: torch.Tensor) -> torch.Tensor:
        batch_size, channels, height, width = x.size()
        
        laplacian_images = []
        for c in range(channels):
            channel = x[:, c:c+1, :, :]
            lap = F.conv2d(channel, self.laplacian, padding=1)
            laplacian_images.append(torch.abs(lap))
        
        laplacian_images = torch.cat(laplacian_images, dim=1)
        return laplacian_images

    def forward(self, pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        pred_lap = self.compute_laplacian(pred)
        target_lap = self.compute_laplacian(target)
        
        loss = self.criterion(pred_lap, target_lap)
        return loss


class CombinedLossWithEdge(nn.Module):
    def __init__(self, alpha: float = 0.6, beta: float = 0.2, gamma: float = 0.2):
        super(CombinedLossWithEdge, self).__init__()
        
        self.mse_loss = nn.MSELoss()
        self.l1_loss = nn.L1Loss()
        self.edge_loss = EdgeAwareLoss(loss_type='l1')
        
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma

    def forward(self, pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        mse = self.mse_loss(pred, target)
        l1 = self.l1_loss(pred, target)
        edge = self.edge_loss(pred, target)
        
        total_loss = self.alpha * mse + self.beta * l1 + self.gamma * edge
        return total_loss


class PerceptualLoss(nn.Module):
    def __init__(self, feature_extractor: nn.Module = None):
        super(PerceptualLoss, self).__init__()
        self.feature_extractor = feature_extractor
        self.criterion = nn.L1Loss()

    def forward(self, pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        if self.feature_extractor is None:
            return self.criterion(pred, target)
        
        with torch.no_grad():
            pred_features = self.feature_extractor(pred)
            target_features = self.feature_extractor(target)
        
        loss = self.criterion(pred_features, target_features)
        return loss


class TotalVariationLoss(nn.Module):
    def __init__(self, beta: float = 1.0):
        super(TotalVariationLoss, self).__init__()
        self.beta = beta

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        batch_size = x.size()[0]
        h_x = x.size()[2]
        w_x = x.size()[3]
        
        count_h = (x.size()[2] - 1) * x.size()[3]
        count_w = x.size()[2] * (x.size()[3] - 1)
        
        h_tv = torch.pow((x[:, :, 1:, :] - x[:, :, :h_x-1, :]), 2).sum()
        w_tv = torch.pow((x[:, :, :, 1:] - x[:, :, :, :w_x-1]), 2).sum()
        
        tv = self.beta * 2 * (h_tv / count_h + w_tv / count_w) / batch_size
        return tv


class HeavyRainLoss(nn.Module):
    def __init__(self, alpha: float = 0.5, beta: float = 0.3, gamma: float = 0.2):
        super(HeavyRainLoss, self).__init__()
        
        self.mse_loss = nn.MSELoss()
        self.edge_loss = EdgeAwareLoss(loss_type='l1')
        self.tv_loss = TotalVariationLoss(beta=0.1)
        
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma

    def forward(self, pred: torch.Tensor, target: torch.Tensor) -> Tuple[torch.Tensor, dict]:
        mse = self.mse_loss(pred, target)
        edge = self.edge_loss(pred, target)
        tv = self.tv_loss(pred)
        
        total_loss = self.alpha * mse + self.beta * edge + self.gamma * tv
        
        loss_dict = {
            'mse': mse.item(),
            'edge': edge.item(),
            'tv': tv.item(),
            'total': total_loss.item()
        }
        
        return total_loss, loss_dict


class AdversarialCombinedLoss(nn.Module):
    def __init__(self, alpha: float = 100.0, beta: float = 0.001):
        super(AdversarialCombinedLoss, self).__init__()
        
        self.pixel_loss = CombinedLossWithEdge(alpha=0.6, beta=0.2, gamma=0.2)
        self.alpha = alpha
        self.beta = beta

    def forward(self, pred: torch.Tensor, target: torch.Tensor, 
                adv_pred: torch.Tensor = None) -> Tuple[torch.Tensor, dict]:
        pixel_loss = self.pixel_loss(pred, target)
        
        loss_dict = {
            'pixel': pixel_loss.item()
        }
        
        total_loss = self.alpha * pixel_loss
        
        if adv_pred is not None:
            adv_loss = -torch.log(adv_pred + 1e-8).mean()
            total_loss = total_loss + self.beta * adv_loss
            loss_dict['adversarial'] = adv_loss.item()
            loss_dict['total'] = total_loss.item()
        
        return total_loss, loss_dict


def gradient_penalty(discriminator: nn.Module, real_images: torch.Tensor, 
                   fake_images: torch.Tensor, device: torch.device) -> torch.Tensor:
    batch_size = real_images.size(0)
    
    alpha = torch.rand(batch_size, 1, 1, 1, device=device)
    interpolates = (alpha * real_images + (1 - alpha) * fake_images).detach()
    interpolates.requires_grad_(True)
    
    d_interpolates = discriminator(interpolates)
    
    gradients = torch.autograd.grad(
        outputs=d_interpolates,
        inputs=interpolates,
        grad_outputs=torch.ones(d_interpolates.size(), device=device),
        create_graph=True,
        retain_graph=True,
        only_inputs=True
    )[0]
    
    gradients = gradients.view(gradients.size(0), -1)
    gradient_penalty = ((gradients.norm(2, dim=1) - 1) ** 2).mean()
    return gradient_penalty
