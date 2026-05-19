# Copyright (c) Remote Sensing Change Detection Team. All rights reserved.

import torch
import torch.nn as nn
import torch.nn.functional as F
from .builder import LOSSES


def reduce_loss(loss, reduction):
    reduction = reduction.lower()
    if reduction == 'none':
        return loss
    elif reduction == 'mean':
        return loss.mean()
    elif reduction == 'sum':
        return loss.sum()
    else:
        raise ValueError(f"reduction must be either none, mean or sum, but got {reduction}')


def weight_reduce_loss(loss, weight=None, reduction='mean', avg_factor=None):
    if weight is not None:
        loss = loss * weight

    if avg_factor is None:
        loss = reduce_loss(loss, reduction)
    else:
        if reduction == 'mean':
            loss = loss.sum() / avg_factor
        elif reduction != 'none':
            raise ValueError('avg_factor can not be used with reduction="sum"')
    return loss


@LOSSES.register_module()
class CrossEntropyLoss(nn.Module):
    def __init__(self, use_sigmoid=False, use_mask=False, reduction='mean', class_weight=None, loss_weight=1.0):
        super().__init__()
        self.use_sigmoid = use_sigmoid
        self.use_mask = use_mask
        self.reduction = reduction
        self.loss_weight = loss_weight
        self.class_weight = class_weight

    def forward(self, cls_score, label, weight=None, avg_factor=None, reduction_override=None, **kwargs):
        assert reduction_override in (None, 'none', 'mean', 'sum')
        reduction = reduction_override if reduction_override else self.reduction

        if self.use_sigmoid:
            loss = F.binary_cross_entropy_with_logits(cls_score, label.float(), weight=None, reduction='none')
        else:
            loss = F.cross_entropy(cls_score, label, weight=self.class_weight, reduction='none')

        loss = self.loss_weight * weight_reduce_loss(loss, weight, reduction, avg_factor)
        return loss


@LOSSES.register_module()
class DiceLoss(nn.Module):
    def __init__(self, smooth=1.0, exponent=2, reduction='mean', loss_weight=1.0):
        super().__init__()
        self.smooth = smooth
        self.exponent = exponent
        self.reduction = reduction
        self.loss_weight = loss_weight

    def forward(self, pred, target, weight=None, avg_factor=None, reduction_override=None):
        assert reduction_override in (None, 'none', 'mean', 'sum')
        reduction = reduction_override if reduction_override else self.reduction

        pred = torch.sigmoid(pred)
        
        intersection = (pred * target).sum(dim=(2, 3))
        union = (pred ** self.exponent).sum(dim=(2, 3)) + (target ** self.exponent).sum(dim=(2, 3))
        
        dice = (2. * intersection + self.smooth) / (union + self.smooth)
        loss = 1 - dice
        
        loss = self.loss_weight * weight_reduce_loss(loss, weight, reduction, avg_factor)
        return loss


@LOSSES.register_module()
class FocalLoss(nn.Module):
    def __init__(self, use_sigmoid=True, gamma=2.0, alpha=0.25, reduction='mean', loss_weight=1.0):
        super().__init__()
        self.use_sigmoid = use_sigmoid
        self.gamma = gamma
        self.alpha = alpha
        self.reduction = reduction
        self.loss_weight = loss_weight

    def forward(self, pred, target, weight=None, avg_factor=None, reduction_override=None):
        assert reduction_override in (None, 'none', 'mean', 'sum')
        reduction = reduction_override if reduction_override else self.reduction

        if self.use_sigmoid:
            pred_sigmoid = torch.sigmoid(pred)
            pt = target * pred_sigmoid + (1 - target) * (1 - pred_sigmoid)
            logpt = torch.log(pt + 1e-6)
            
            loss = -self.alpha * (1 - pt) ** self.gamma * logpt
        else:
            pred_softmax = F.softmax(pred, dim=1)
            pt = pred_softmax.gather(1, target.unsqueeze(1))
            logpt = torch.log(pt + 1e-6)
            loss = -self.alpha * (1 - pt) ** self.gamma * logpt

        loss = self.loss_weight * weight_reduce_loss(loss, weight, reduction, avg_factor)
        return loss


@LOSSES.register_module()
class LovaszLoss(nn.Module):
    def __init__(self, per_image=True, loss_weight=1.0):
        super().__init__()
        self.per_image = per_image
        self.loss_weight = loss_weight

    def forward(self, pred, target):
        pred = torch.sigmoid(pred)
        
        if self.per_image:
            loss = torch.mean(torch.stack([self.lovasz_hinge_flat(p.flatten(), t.flatten()) for p, t in zip(pred, target)]))
        else:
            loss = self.lovasz_hinge_flat(pred.flatten(), target.flatten())
        
        return self.loss_weight * loss

    @staticmethod
    def lovasz_hinge_flat(logits, labels):
        signs = 2 * labels - 1
        errors = 1 - logits * signs
        errors_sorted, perm = torch.sort(errors, dim=0, descending=True)
        perm = perm.data
        gt_sorted = labels[perm]
        grad = LovaszLoss.lovasz_grad(gt_sorted)
        loss = torch.dot(F.relu(errors_sorted), grad)
        return loss

    @staticmethod
    def lovasz_grad(gt_sorted):
        p = len(gt_sorted)
        gts = gt_sorted.sum()
        intersection = gts - gt_sorted.float().cumsum(0)
        union = gts + (1 - gt_sorted).float().cumsum(0)
        jaccard = 1 - intersection / union
        if p > 1:
            jaccard[1:p] = jaccard[1:p] - jaccard[0:-1]
        return jaccard


@LOSSES.register_module()
class BoundaryLoss(nn.Module):
    def __init__(self, loss_weight=1.0):
        super().__init__()
        self.loss_weight = loss_weight

    def forward(self, pred, target):
        pred = torch.sigmoid(pred)
        
        sobel_x = torch.tensor([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1], dtype=torch.float32).view(1, 1, 3, 3).to(pred.device)
        sobel_y = torch.tensor([[-1, -2, -1], [0, 0, 0], [1, 2, 1], dtype=torch.float32).view(1, 1, 3, 3).to(pred.device)
        
        pred_edge_x = F.conv2d(pred, sobel_x, padding=1)
        pred_edge_y = F.conv2d(pred, sobel_y, padding=1)
        
        target_edge_x = F.conv2d(target, sobel_x, padding=1)
        target_edge_y = F.conv2d(target, sobel_y, padding=1)
        
        pred_edge = torch.sqrt(pred_edge_x ** 2 + pred_edge_y ** 2 + 1e-6)
        target_edge = torch.sqrt(target_edge_x ** 2 + target_edge_y ** 2 + 1e-6)
        
        loss = F.l1_loss(pred_edge, target_edge)
        return self.loss_weight * loss


@LOSSES.register_module()
class CombinedLoss(nn.Module):
    def __init__(self, losses, loss_weights=None):
        super().__init__()
        self.losses = nn.ModuleList(losses)
        self.loss_weights = loss_weights or [1.0] * len(losses)

    def forward(self, pred, target):
        total_loss = 0.0
        for loss_fn, weight in zip(self.losses, self.loss_weights):
            total_loss = total_loss + weight * loss_fn(pred, target)
        return total_loss
