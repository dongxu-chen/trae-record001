# Swin-UNet 变化检测模型配置

# model settings
model = dict(
    type='ChangeDetector',
    backbone=dict(
        type='SwinUNet',
        img_size=224,
        patch_size=4,
        in_chans=3,
        num_classes=1,
        embed_dim=96,
        depths=[2, 2, 2, 2],
        num_heads=[3, 6, 12, 24],
        window_size=7,
        mlp_ratio=4.,
        qkv_bias=True,
        qk_scale=None,
        drop_rate=0.,
        attn_drop_rate=0.,
        drop_path_rate=0.1,
        ape=False,
        patch_norm=True,
        use_checkpoint=False,
    ),
    decode_head=dict(
        type='UNetHead',
        in_channels=192,
        num_classes=1,
    ),
    loss_decode=dict(
        type='DiceLoss',
        smooth=1.0,
        exponent=2,
        reduction='mean',
        loss_weight=1.0,
    ),
)
