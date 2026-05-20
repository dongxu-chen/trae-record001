# Copyright (c) Remote Sensing Change Detection Team. All rights reserved.

import torch
import torch.nn as nn
import torch.nn.functional as F
from .builder import SEGMENTORS, build_backbone, build_neck, build_head, build_loss


@SEGMENTORS.register_module()
class EncoderDecoder(nn.Module):
    def __init__(self, backbone, decode_head, neck=None, auxiliary_head=None,
                 train_cfg=None, test_cfg=None, pretrained=None, init_cfg=None):
        super().__init__()
        self.train_cfg = train_cfg
        self.test_cfg = test_cfg

        self.backbone = build_backbone(backbone)
        
        if neck is not None:
            self.neck = build_neck(neck)
        else:
            self.neck = None

        self.decode_head = build_head(decode_head)

        if auxiliary_head is not None:
            self.auxiliary_head = build_head(auxiliary_head)
        else:
            self.auxiliary_head = None

        if pretrained is not None:
            self.init_weights(pretrained)

    def init_weights(self, pretrained=None):
        if pretrained is not None:
            self.backbone.init_weights(pretrained)
        if self.neck is not None:
            self.neck.init_weights()
        self.decode_head.init_weights()
        if self.auxiliary_head is not None:
            self.auxiliary_head.init_weights()

    def extract_feat(self, img):
        x = self.backbone(img)
        if self.neck is not None:
            x = self.neck(x)
        return x

    def forward(self, img):
        x = self.extract_feat(img)
        out = self.decode_head(x)
        
        if out.shape[2:] != img.shape[2:]:
            out = F.interpolate(out, size=img.shape[2:], mode='bilinear', align_corners=True)
        
        return out

    def forward_train(self, img, img_metas, gt_semantic_seg, **kwargs):
        seg_logits = self.forward(img)
        return seg_logits

    def forward_test(self, imgs, img_metas, **kwargs):
        seg_logits = self.forward(imgs)
        return seg_logits


@SEGMENTORS.register_module()
class SiameseEncoderDecoder(nn.Module):
    def __init__(self, backbone, decode_head, neck=None, auxiliary_head=None,
                 train_cfg=None, test_cfg=None, pretrained=None, fusion_type='concat'):
        super().__init__()
        self.train_cfg = train_cfg
        self.test_cfg = test_cfg
        self.fusion_type = fusion_type

        self.backbone = build_backbone(backbone)
        
        if neck is not None:
            self.neck = build_neck(neck)
        else:
            self.neck = None

        self.decode_head = build_head(decode_head)

        if auxiliary_head is not None:
            self.auxiliary_head = build_head(auxiliary_head)
        else:
            self.auxiliary_head = None

        if pretrained is not None:
            self.init_weights(pretrained)

    def init_weights(self, pretrained=None):
        if pretrained is not None:
            self.backbone.init_weights(pretrained)
        if self.neck is not None:
            self.neck.init_weights()
        self.decode_head.init_weights()
        if self.auxiliary_head is not None:
            self.auxiliary_head.init_weights()

    def extract_feat(self, img1, img2):
        x1 = self.backbone(img1)
        x2 = self.backbone(img2)
        
        if isinstance(x1, (list, tuple)):
            fused_features = []
            for feat1, feat2 in zip(x1, x2):
                if self.fusion_type == 'concat':
                    fused = torch.cat([feat1, feat2], dim=1)
                elif self.fusion_type == 'diff':
                    fused = torch.abs(feat1 - feat2)
                elif self.fusion_type == 'add':
                    fused = feat1 + feat2
                else:
                    raise ValueError(f"Unsupported fusion type: {self.fusion_type}")
                fused_features.append(fused)
            x = tuple(fused_features)
        else:
            if self.fusion_type == 'concat':
                x = torch.cat([x1, x2], dim=1)
            elif self.fusion_type == 'diff':
                x = torch.abs(x1 - x2)
            elif self.fusion_type == 'add':
                x = x1 + x2
            else:
                raise ValueError(f"Unsupported fusion type: {self.fusion_type}")
        
        if self.neck is not None:
            x = self.neck(x)
        return x

    def forward(self, img1, img2):
        x = self.extract_feat(img1, img2)
        out = self.decode_head(x)
        
        if out.shape[2:] != img1.shape[2:]:
            out = F.interpolate(out, size=img1.shape[2:], mode='bilinear', align_corners=True)
        
        return out

    def forward_train(self, img1, img2, img_metas, gt_semantic_seg, **kwargs):
        seg_logits = self.forward(img1, img2)
        return seg_logits

    def forward_test(self, imgs1, imgs2, img_metas, **kwargs):
        seg_logits = self.forward(imgs1, imgs2)
        return seg_logits


@SEGMENTORS.register_module()
class ChangeDetector(nn.Module):
    def __init__(self, backbone, decode_head, neck=None, loss_decode=None,
                 auxiliary_head=None, train_cfg=None, test_cfg=None, 
                 pretrained=None, init_cfg=None):
        super().__init__()
        self.train_cfg = train_cfg
        self.test_cfg = test_cfg

        self.backbone = build_backbone(backbone)
        
        if neck is not None:
            self.neck = build_neck(neck)
        else:
            self.neck = None

        self.decode_head = build_head(decode_head)

        if auxiliary_head is not None:
            self.auxiliary_head = build_head(auxiliary_head)
        else:
            self.auxiliary_head = None

        if loss_decode is not None:
            self.loss_decode = build_loss(loss_decode)
        else:
            self.loss_decode = None

        if pretrained is not None:
            self.init_weights(pretrained)

    def init_weights(self, pretrained=None):
        if pretrained is not None:
            self.backbone.init_weights(pretrained)
        if self.neck is not None:
            self.neck.init_weights()
        self.decode_head.init_weights()
        if self.auxiliary_head is not None:
            self.auxiliary_head.init_weights()

    def extract_feat(self, img1, img2):
        x1 = self.backbone(img1)
        x2 = self.backbone(img2)
        
        if isinstance(x1, (list, tuple)):
            fused_features = []
            for feat1, feat2 in zip(x1, x2):
                diff = torch.abs(feat1 - feat2)
                fused = torch.cat([feat1, feat2, diff], dim=1)
                fused_features.append(fused)
            x = tuple(fused_features)
        else:
            diff = torch.abs(x1 - x2)
            x = torch.cat([x1, x2, diff], dim=1)
        
        if self.neck is not None:
            x = self.neck(x)
        return x

    def forward(self, img1, img2, return_loss=False, **kwargs):
        x = self.extract_feat(img1, img2)
        out = self.decode_head(x)
        
        if out.shape[2:] != img1.shape[2:]:
            out = F.interpolate(out, size=img1.shape[2:], mode='bilinear', align_corners=True)
        
        if return_loss and self.loss_decode is not None and 'gt_semantic_seg' in kwargs:
            loss = self.loss_decode(out, kwargs['gt_semantic_seg'])
            return out, loss
        
        return out

    def forward_train(self, img1, img2, img_metas, gt_semantic_seg, **kwargs):
        seg_logits = self.forward(img1, img2)
        return seg_logits

    def forward_test(self, imgs1, imgs2, img_metas, **kwargs):
        seg_logits = self.forward(imgs1, imgs2)
        return seg_logits
