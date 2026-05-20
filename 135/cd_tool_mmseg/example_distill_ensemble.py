#!/usr/bin/env python
"""
知识蒸馏与模型集成示例
"""

import os
import torch
import torch.nn as nn
import numpy as np
from PIL import Image

# 导入新框架模块
from cd_tool_mmseg.models.builder import build_segmentor, build_distiller
from cd_tool_mmseg.models.distiller import ModelEnsemble


def create_simple_model_config(model_name='base'):
    """创建简单的模型配置"""
    if model_name == 'base':
        return dict(
            type='ChangeDetector',
            backbone=dict(
                type='UNetBackbone',
                in_channels=3,
                base_channels=64,
                num_stages=4,
                out_indices=(0, 1, 2, 3),
            ),
            decode_head=dict(
                type='FCNHead',
                in_channels=192,
                channels=64,
                num_classes=1,
                dropout_ratio=0.1,
            ),
        )
    elif model_name == 'large':
        return dict(
            type='ChangeDetector',
            backbone=dict(
                type='UNetBackbone',
                in_channels=3,
                base_channels=96,
                num_stages=4,
                out_indices=(0, 1, 2, 3),
            ),
            decode_head=dict(
                type='FCNHead',
                in_channels=288,
                channels=96,
                num_classes=1,
                dropout_ratio=0.1,
            ),
        )


def example_knowledge_distillation():
    """知识蒸馏示例"""
    print("=" * 60)
    print("知识蒸馏示例")
    print("=" * 60)
    
    # 教师模型配置（更大的模型）
    teacher_cfg = create_simple_model_config('large')
    
    # 学生模型配置（更小的模型）
    student_cfg = create_simple_model_config('base')
    
    # 蒸馏配置
    distill_cfg = dict(
        type='SingleTeacherDistiller',
        teacher=teacher_cfg,
        student=student_cfg,
        distill_losses=dict(
            logits=dict(type='KD', temperature=4.0, loss_weight=1.0),
        ),
        teacher_ckpt=None,
        teacher_trainable=False,
    )
    
    # 构建蒸馏器
    distiller = build_distiller(distill_cfg)
    
    print(f"教师模型参数数量: {sum(p.numel() for p in distiller.teacher.parameters())}")
    print(f"学生模型参数数量: {sum(p.numel() for p in distiller.student.parameters())}")
    
    # 测试前向传播
    print("\n测试蒸馏前向传播...")
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    distiller = distiller.to(device)
    
    img1 = torch.randn(1, 3, 256, 256).to(device)
    img2 = torch.randn(1, 3, 256, 256).to(device)
    mask = torch.randint(0, 2, (1, 1, 256, 256)).float().to(device)
    
    # 训练模式
    distiller.train()
    
    # 注意：这里需要传入 gt_semantic_seg 参数
    student_output, losses = distiller(img1, img2, return_loss=True, gt_semantic_seg=mask)
    
    print(f"学生模型输出形状: {student_output.shape}")
    print(f"蒸馏损失: {losses}")
    
    # 推理模式（只使用学生模型）
    distiller.eval()
    with torch.no_grad():
        output = distiller(img1, img2)
    print(f"推理输出形状: {output.shape}")
    
    print("知识蒸馏示例完成！\n")


def example_model_ensemble():
    """模型集成示例"""
    print("=" * 60)
    print("模型集成示例")
    print("=" * 60)
    
    # 创建多个不同配置的模型
    model_cfgs = [
        create_simple_model_config('base'),
        create_simple_model_config('base'),
        create_simple_model_config('base'),
    ]
    
    # 构建模型集成
    print("构建模型集成器 (3个模型)...")
    ensemble = ModelEnsemble(
        model_cfgs=model_cfgs,
        checkpoint_paths=None,
        weights=[0.4, 0.3, 0.3],
    )
    
    print(f"集成模型总数: {len(ensemble.models)}")
    print(f"集成权重: {ensemble.weights}")
    
    # 测试集成推理
    print("\n测试集成推理...")
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    ensemble = ensemble.to(device)
    
    img1 = torch.randn(2, 3, 256, 256).to(device)
    img2 = torch.randn(2, 3, 256, 256).to(device)
    
    # 不同的集成策略
    print("\n不同融合策略:")
    
    # 1. 概率平均
    output_prob = ensemble(img1, img2, fusion='prob')
    print(f"概率平均融合 - 输出形状: {output_prob.shape}")
    
    # 2. Logits平均
    output_logits = ensemble(img1, img2, fusion='logits')
    print(f"Logits平均融合 - 输出形状: {output_logits.shape}")
    
    # 3. 投票
    output_voting = ensemble(img1, img2, fusion='voting')
    print(f"投票融合 - 输出形状: {output_voting.shape}")
    
    print("模型集成示例完成！\n")


def example_ensemble_distiller():
    """集成蒸馏器示例（多个教师模型）
    """
    print("=" * 60)
    print("集成蒸馏器示例")
    print("=" * 60)
    
    # 多个教师模型配置
    model_cfgs = [
        create_simple_model_config('base'),
        create_simple_model_config('base'),
    ]
    
    # 构建集成蒸馏器
    ensemble_distill_cfg = dict(
        type='EnsembleDistiller',
        models=model_cfgs,
        weights=[0.5, 0.5],
        fusion_type='average',
    )
    
    ensemble_distiller = build_distiller(ensemble_distill_cfg)
    
    print(f"集成蒸馏器模型数量: {len(ensemble_distiller.models)}")
    print(f"融合类型: {ensemble_distiller.fusion_type}")
    
    # 测试推理
    print("\n测试集成蒸馏器推理...")
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    ensemble_distiller = ensemble_distiller.to(device)
    
    img1 = torch.randn(1, 3, 256, 256).to(device)
    img2 = torch.randn(1, 3, 256, 256).to(device)
    
    ensemble_distiller.eval()
    with torch.no_grad():
        output = ensemble_distiller(img1, img2)
    
    print(f"集成输出形状: {output.shape}")
    print("集成蒸馏器示例完成！\n")


def main():
    print("\n" + "=" * 80)
    print("MMSegmentation 风格框架 - 知识蒸馏与模型集成")
    print("=" * 80 + "\n")
    
    # 1. 知识蒸馏
    example_knowledge_distillation()
    
    # 2. 模型集成
    example_model_ensemble()
    
    # 3. 集成蒸馏器
    example_ensemble_distiller()
    
    print("=" * 80)
    print("所有示例完成！")
    print("=" * 80)


if __name__ == '__main__':
    main()
