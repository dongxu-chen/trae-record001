"""
图像加载、保存和显示工具
支持分块处理、重叠拼贴、宽高比保持
"""

import torch
import torchvision.transforms as transforms
from PIL import Image
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path


def prepare_transform(image_size=512, normalize=True):
    """
    准备图像变换

    Args:
        image_size: 目标图像大小，int或(高度, 宽度)元组
        normalize: 是否归一化到VGG所需范围

    Returns:
        变换组合
    """
    if isinstance(image_size, int):
        image_size = (image_size, image_size)

    transform_list = [
        transforms.Resize(image_size),
        transforms.ToTensor(),
    ]

    if normalize:
        transform_list.append(
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                               std=[0.229, 0.224, 0.225])
        )

    return transforms.Compose(transform_list)


def load_image(image_path, image_size=512, device='cpu', keep_aspect_ratio=False, pad_value=0):
    """
    加载图像并转换为张量

    Args:
        image_path: 图像路径
        image_size: 目标图像大小，int或(高度, 宽度)元组
        device: 计算设备
        keep_aspect_ratio: 是否保持宽高比，True则使用黑边填充
        pad_value: 填充值，0为黑色，1为白色

    Returns:
        图像张量 [1, 3, H, W]
    """
    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"图像文件不存在: {image_path}")

    image = Image.open(image_path).convert('RGB')
    orig_width, orig_height = image.size

    if isinstance(image_size, int):
        target_size = (image_size, image_size)
    else:
        target_size = image_size

    if keep_aspect_ratio:
        scale = min(target_size[0] / orig_height, target_size[1] / orig_width)
        new_size = (int(orig_height * scale), int(orig_width * scale))

        image = image.resize((new_size[1], new_size[0]), Image.BICUBIC)

        pad_top = (target_size[0] - new_size[0]) // 2
        pad_bottom = target_size[0] - new_size[0] - pad_top
        pad_left = (target_size[1] - new_size[1]) // 2
        pad_right = target_size[1] - new_size[1] - pad_left

        transform = transforms.Compose([
            transforms.ToTensor(),
        ])
        tensor = transform(image).unsqueeze(0)

        padding = (pad_left, pad_right, pad_top, pad_bottom)
        tensor = torch.nn.functional.pad(tensor, padding, value=pad_value)

        return tensor.to(device), (pad_top, pad_bottom, pad_left, pad_right), (orig_height, orig_width)
    else:
        transform = prepare_transform(target_size, normalize=False)
        tensor = transform(image).unsqueeze(0)
        return tensor.to(device), (0, 0, 0, 0), (orig_height, orig_width)


def save_image(tensor, save_path, denormalize=True, padding=None, original_size=None):
    """
    保存图像张量到文件

    Args:
        tensor: 图像张量 [1, 3, H, W] 或 [3, H, W]
        save_path: 保存路径
        denormalize: 是否反归一化
        padding: 填充信息 (top, bottom, left, right)，如果提供则去除填充
        original_size: 原始尺寸 (height, width)，如果提供则调整回原始大小

    Returns:
        保存的文件路径
    """
    save_path = Path(save_path)
    save_path.parent.mkdir(parents=True, exist_ok=True)

    image = tensor.clone().cpu()

    if image.dim() == 4:
        image = image.squeeze(0)

    if denormalize:
        mean = torch.tensor([0.485, 0.456, 0.406]).view(3, 1, 1)
        std = torch.tensor([0.229, 0.224, 0.225]).view(3, 1, 1)
        image = image * std + mean

    image = torch.clamp(image, 0, 1)

    if padding is not None:
        pad_top, pad_bottom, pad_left, pad_right = padding
        _, height, width = image.shape
        image = image[:, pad_top:height - pad_bottom, pad_left:width - pad_right]

    pil_image = transforms.ToPILImage()(image)

    if original_size is not None:
        orig_height, orig_width = original_size
        pil_image = pil_image.resize((orig_width, orig_height), Image.BICUBIC)

    pil_image.save(str(save_path))

    return save_path


def tensor_to_pil(tensor, denormalize=True):
    """
    将张量转换为PIL图像

    Args:
        tensor: 图像张量
        denormalize: 是否反归一化

    Returns:
        PIL图像
    """
    image = tensor.clone().cpu()

    if image.dim() == 4:
        image = image.squeeze(0)

    if denormalize:
        mean = torch.tensor([0.485, 0.456, 0.406]).view(3, 1, 1)
        std = torch.tensor([0.229, 0.224, 0.225]).view(3, 1, 1)
        image = image * std + mean

    image = torch.clamp(image, 0, 1)
    return transforms.ToPILImage()(image)


def show_images(images, titles=None, figsize=(15, 5), save_path=None):
    """
    显示多幅图像

    Args:
        images: 图像张量列表或PIL图像列表
        titles: 图像标题列表
        figsize: 图像大小
        save_path: 保存路径，None则不保存
    """
    if isinstance(images, torch.Tensor):
        images = [images]

    n = len(images)
    fig, axes = plt.subplots(1, n, figsize=figsize)

    if n == 1:
        axes = [axes]

    for idx, (ax, img) in enumerate(zip(axes, images)):
        if isinstance(img, torch.Tensor):
            img = tensor_to_pil(img)

        ax.imshow(img)
        ax.axis('off')

        if titles and idx < len(titles):
            ax.set_title(titles[idx])

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')

    plt.show()
    return fig


def extract_patches(image_tensor, patch_size=512, overlap=128):
    """
    将图像分割成重叠的块

    Args:
        image_tensor: 输入图像张量 [1, 3, H, W]
        patch_size: 块大小
        overlap: 重叠区域大小

    Returns:
        patches: 块列表 [N, 3, patch_size, patch_size]
        positions: 每个块的位置信息 [(top, left, height, width), ...]
        original_size: 原始图像尺寸 (height, width)
    """
    _, channels, height, width = image_tensor.shape
    original_size = (height, width)

    stride = patch_size - overlap

    patches = []
    positions = []

    for top in range(0, height, stride):
        for left in range(0, width, stride):
            if top + patch_size > height:
                top = height - patch_size
            if left + patch_size > width:
                left = width - patch_size

            patch = image_tensor[:, :, top:top + patch_size, left:left + patch_size]
            patches.append(patch)
            positions.append((top, left, patch_size, patch_size))

    patches = torch.cat(patches, dim=0)

    return patches, positions, original_size


def create_blend_mask(patch_size, overlap, device='cpu'):
    """
    创建用于重叠拼贴的权重掩码

    Args:
        patch_size: 块大小
        overlap: 重叠区域大小
        device: 计算设备

    Returns:
        权重掩码 [1, 1, patch_size, patch_size]
    """
    mask = torch.ones(1, 1, patch_size, patch_size, device=device)

    fade = torch.linspace(0, 1, overlap, device=device)

    mask[:, :, :overlap, :] *= fade.view(1, 1, -1, 1)
    mask[:, :, -overlap:, :] *= fade.flip(0).view(1, 1, -1, 1)
    mask[:, :, :, :overlap] *= fade.view(1, 1, 1, -1)
    mask[:, :, :, -overlap:] *= fade.flip(0).view(1, 1, 1, -1)

    return mask


def merge_patches(patches, positions, original_size, overlap=128, device='cpu'):
    """
    将处理后的块拼合回完整图像，使用加权融合减少接缝

    Args:
        patches: 处理后的块列表 [N, 3, H, W] 或张量列表
        positions: 每个块的位置信息
        original_size: 原始图像尺寸 (height, width)
        overlap: 重叠区域大小
        device: 计算设备

    Returns:
        合并后的图像张量 [1, 3, H, W]
    """
    height, width = original_size
    channels = 3

    result = torch.zeros(1, channels, height, width, device=device)
    weight_sum = torch.zeros(1, 1, height, width, device=device)

    patch_size = patches[0].shape[2] if isinstance(patches, list) else patches.shape[2]
    blend_mask = create_blend_mask(patch_size, overlap, device)

    for i, (patch, (top, left, _, _)) in enumerate(zip(patches, positions)):
        if isinstance(patch, torch.Tensor):
            patch = patch.unsqueeze(0) if patch.dim() == 3 else patch

        mask = blend_mask.to(patch.device)

        result[:, :, top:top + patch_size, left:left + patch_size] += patch * mask
        weight_sum[:, :, top:top + patch_size, left:left + patch_size] += mask

    weight_sum = torch.clamp(weight_sum, min=1e-6)
    result = result / weight_sum

    return result
