# Copyright (c) Remote Sensing Change Detection Team. All rights reserved.

import torch
import torch.nn as nn
import torch.nn.functional as F
from .builder import DISTILLERS, build_segmentor


@DISTILLERS.register_module()
class SingleTeacherDistiller(nn.Module):
    def __init__(self, teacher, student, distill_losses=None, teacher_ckpt=None, teacher_trainable=False):
        super().__init__()
        self.teacher_trainable = teacher_trainable
        
        self.teacher = build_segmentor(teacher)
        if teacher_ckpt is not None:
            self.teacher.load_state_dict(torch.load(teacher_ckpt, map_location='cpu'), strict=False)
        
        if not teacher_trainable:
            for param in self.teacher.parameters():
                param.requires_grad = False
            self.teacher.eval()
        
        self.student = build_segmentor(student)
        
        self.distill_losses = nn.ModuleDict()
        if distill_losses is not None:
            for name, loss_cfg in distill_losses.items():
                self.distill_losses[name] = self._build_loss(loss_cfg)

    def _build_loss(self, loss_cfg):
        loss_type = loss_cfg.pop('type')
        if loss_type == 'KD':
            return KDLoss(**loss_cfg)
        elif loss_type == 'AttentionTransfer':
            return AttentionTransferLoss(**loss_cfg)
        elif loss_type == 'FeatureMSE':
            return FeatureMSELoss(**loss_cfg)
        else:
            raise ValueError(f"Unsupported distill loss type: {loss_type}")

    def train(self, mode=True):
        super().train(mode)
        if not self.teacher_trainable:
            self.teacher.eval()

    def forward_train(self, img1, img2, img_metas, gt_semantic_seg, **kwargs):
        if self.teacher_trainable:
            with torch.set_grad_enabled(True):
                teacher_logits = self.teacher(img1, img2)
        else:
            with torch.no_grad():
                teacher_logits = self.teacher(img1, img2)
        
        student_logits = self.student(img1, img2)
        
        losses = {}
        
        if 'logits' in self.distill_losses:
            losses['loss_kd'] = self.distill_losses['logits'](student_logits, teacher_logits)
        
        return student_logits, losses

    def forward_test(self, imgs1, imgs2, img_metas, **kwargs):
        return self.student(imgs1, imgs2)

    def forward(self, img1, img2, return_loss=False, **kwargs):
        if return_loss and self.training:
            return self.forward_train(img1, img2, None, kwargs.get('gt_semantic_seg', None), **kwargs)
        return self.student(img1, img2)


class KDLoss(nn.Module):
    def __init__(self, temperature=4.0, loss_weight=1.0):
        super().__init__()
        self.temperature = temperature
        self.loss_weight = loss_weight

    def forward(self, student_logits, teacher_logits):
        student_prob = F.log_softmax(student_logits / self.temperature, dim=1)
        teacher_prob = F.softmax(teacher_logits / self.temperature, dim=1)
        loss = F.kl_div(student_prob, teacher_prob, reduction='batchmean') * (self.temperature ** 2)
        return self.loss_weight * loss


class AttentionTransferLoss(nn.Module):
    def __init__(self, p=2, loss_weight=1.0):
        super().__init__()
        self.p = p
        self.loss_weight = loss_weight

    def forward(self, student_features, teacher_features):
        losses = []
        for s_feat, t_feat in zip(student_features, teacher_features):
            s_attention = self._attention_map(s_feat)
            t_attention = self._attention_map(t_feat)
            loss = F.mse_loss(s_attention, t_attention)
            losses.append(loss)
        return self.loss_weight * sum(losses) / len(losses)

    def _attention_map(self, x):
        attention = torch.norm(x, p=self.p, dim=1, keepdim=True)
        attention = F.normalize(attention.flatten(1), p=2, dim=1)
        return attention


class FeatureMSELoss(nn.Module):
    def __init__(self, loss_weight=1.0):
        super().__init__()
        self.loss_weight = loss_weight

    def forward(self, student_features, teacher_features):
        losses = []
        for s_feat, t_feat in zip(student_features, teacher_features):
            if s_feat.shape != t_feat.shape:
                s_feat = F.interpolate(s_feat, size=t_feat.shape[2:], mode='bilinear', align_corners=True)
            loss = F.mse_loss(s_feat, t_feat)
            losses.append(loss)
        return self.loss_weight * sum(losses) / len(losses)


@DISTILLERS.register_module()
class EnsembleDistiller(nn.Module):
    def __init__(self, models, weights=None, fusion_type='average'):
        super().__init__()
        self.models = nn.ModuleList([build_segmentor(cfg) for cfg in models])
        self.weights = weights or [1.0 / len(models)] * len(models)
        self.fusion_type = fusion_type

    def forward(self, img1, img2, **kwargs):
        predictions = []
        
        for model in self.models:
            model.eval()
            with torch.no_grad():
                pred = model(img1, img2)
                predictions.append(pred)
        
        if self.fusion_type == 'average':
            ensemble_pred = sum(w * pred for w, pred in zip(self.weights, predictions))
        elif self.fusion_type == 'weighted_average':
            total_weight = sum(self.weights)
            ensemble_pred = sum(w * pred for w, pred in zip(self.weights, predictions)) / total_weight
        elif self.fusion_type == 'max':
            ensemble_pred = torch.max(torch.stack(predictions), dim=0)[0]
        else:
            raise ValueError(f"Unsupported fusion type: {self.fusion_type}")
        
        return ensemble_pred

    def train(self, mode=True):
        super().train(mode)
        for model in self.models:
            model.eval()


class ModelEnsemble(nn.Module):
    def __init__(self, model_cfgs, checkpoint_paths=None, weights=None):
        super().__init__()
        self.models = nn.ModuleList()
        
        for i, cfg in enumerate(model_cfgs):
            model = build_segmentor(cfg)
            if checkpoint_paths and i < len(checkpoint_paths) and checkpoint_paths[i]:
                model.load_state_dict(torch.load(checkpoint_paths[i], map_location='cpu'), strict=False)
            self.models.append(model)
        
        self.weights = weights or [1.0 / len(model_cfgs)] * len(model_cfgs)
        
        for model in self.models:
            model.eval()

    @torch.no_grad()
    def forward(self, img1, img2, fusion='prob'):
        predictions = []
        
        for model in self.models:
            logits = model(img1, img2)
            if fusion == 'prob':
                pred = torch.sigmoid(logits)
            else:
                pred = logits
            predictions.append(pred)
        
        if fusion in ['prob', 'logits']:
            ensemble_pred = sum(w * pred for w, pred in zip(self.weights, predictions))
        elif fusion == 'max':
            ensemble_pred = torch.max(torch.stack(predictions), dim=0)[0]
        elif fusion == 'voting':
            binary_preds = [(pred > 0.5).float() for pred in predictions]
            votes = sum(w * pred for w, pred in zip(self.weights, binary_preds))
            ensemble_pred = (votes > 0.5).float()
        else:
            raise ValueError(f"Unsupported fusion type: {fusion}")
        
        return ensemble_pred
