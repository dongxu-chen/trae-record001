# 基础变化检测模型配置

# model settings
model = dict(
    type='ChangeDetector',
    backbone=dict(
        type='ResNet',
        depth=50,
        in_channels=3,
        num_stages=4,
        out_indices=(0, 1, 2, 3),
        frozen_stages=-1,
    ),
    decode_head=dict(
        type='FCNHead',
        in_channels=6144,
        channels=512,
        num_classes=1,
        dropout_ratio=0.1,
    ),
    loss_decode=dict(
        type='CrossEntropyLoss',
        use_sigmoid=True,
        loss_weight=1.0,
    ),
)
