"""
CIFAR-10 数据加载器
包含训练、验证和测试数据的加载和预处理
"""

import torch
import torchvision
import torchvision.transforms as transforms
from torch.utils.data import DataLoader, SubsetRandomSampler
import numpy as np


class Cutout:
    """Cutout 数据增强 - 随机遮挡图像的一部分"""
    def __init__(self, length):
        self.length = length

    def __call__(self, img):
        h, w = img.size(1), img.size(2)
        mask = np.ones((h, w), np.float32)
        y = np.random.randint(h)
        x = np.random.randint(w)

        y1 = np.clip(y - self.length // 2, 0, h)
        y2 = np.clip(y + self.length // 2, 0, h)
        x1 = np.clip(x - self.length // 2, 0, w)
        x2 = np.clip(x + self.length // 2, 0, w)

        mask[y1:y2, x1:x2] = 0.0
        mask = torch.from_numpy(mask)
        mask = mask.expand_as(img)
        img *= mask
        return img


def get_search_transforms():
    """获取搜索阶段的数据增强"""
    train_transform = transforms.Compose([
        transforms.RandomCrop(32, padding=4),
        transforms.RandomHorizontalFlip(),
        transforms.ToTensor(),
        transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2023, 0.1994, 0.2010)),
    ])
    
    valid_transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2023, 0.1994, 0.2010)),
    ])
    
    return train_transform, valid_transform


def get_final_transforms(cutout=True, cutout_length=16):
    """获取最终训练阶段的数据增强"""
    train_transform_list = [
        transforms.RandomCrop(32, padding=4),
        transforms.RandomHorizontalFlip(),
        transforms.ToTensor(),
        transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2023, 0.1994, 0.2010)),
    ]
    
    if cutout:
        train_transform_list.append(Cutout(cutout_length))
    
    train_transform = transforms.Compose(train_transform_list)
    
    valid_transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2023, 0.1994, 0.2010)),
    ])
    
    return train_transform, valid_transform


def get_search_dataloaders(data_path='./data', batch_size=64, num_workers=2, valid_portion=0.5):
    """
    获取架构搜索阶段的数据加载器
    将训练集分为两部分：一部分用于训练权重，一部分用于训练架构参数
    
    Args:
        data_path: 数据存储路径
        batch_size: 批次大小
        num_workers: 数据加载线程数
        valid_portion: 用于架构参数验证的数据比例
    
    Returns:
        train_loader: 权重训练数据加载器
        valid_loader: 架构参数验证数据加载器
        test_loader: 测试数据加载器
    """
    train_transform, valid_transform = get_search_transforms()
    
    # 下载并加载训练集
    train_dataset = torchvision.datasets.CIFAR10(
        root=data_path, train=True, download=True, transform=train_transform
    )
    
    # 将训练集分为训练集和验证集
    num_train = len(train_dataset)
    indices = list(range(num_train))
    split = int(np.floor(valid_portion * num_train))
    
    np.random.shuffle(indices)
    train_idx, valid_idx = indices[split:], indices[:split]
    
    train_sampler = SubsetRandomSampler(train_idx)
    valid_sampler = SubsetRandomSampler(valid_idx)
    
    train_loader = DataLoader(
        train_dataset, batch_size=batch_size, sampler=train_sampler,
        num_workers=num_workers, pin_memory=True
    )
    
    valid_loader = DataLoader(
        train_dataset, batch_size=batch_size, sampler=valid_sampler,
        num_workers=num_workers, pin_memory=True
    )
    
    # 测试集
    test_dataset = torchvision.datasets.CIFAR10(
        root=data_path, train=False, download=True, transform=valid_transform
    )
    
    test_loader = DataLoader(
        test_dataset, batch_size=batch_size, shuffle=False,
        num_workers=num_workers, pin_memory=True
    )
    
    return train_loader, valid_loader, test_loader


def get_final_dataloaders(data_path='./data', batch_size=96, num_workers=2, 
                          cutout=True, cutout_length=16):
    """
    获取最终模型训练阶段的数据加载器
    使用完整训练集进行训练
    
    Args:
        data_path: 数据存储路径
        batch_size: 批次大小
        num_workers: 数据加载线程数
        cutout: 是否使用Cutout增强
        cutout_length: Cutout遮挡长度
    
    Returns:
        train_loader: 训练数据加载器
        test_loader: 测试数据加载器
    """
    train_transform, valid_transform = get_final_transforms(cutout, cutout_length)
    
    # 完整训练集
    train_dataset = torchvision.datasets.CIFAR10(
        root=data_path, train=True, download=True, transform=train_transform
    )
    
    train_loader = DataLoader(
        train_dataset, batch_size=batch_size, shuffle=True,
        num_workers=num_workers, pin_memory=True
    )
    
    # 测试集
    test_dataset = torchvision.datasets.CIFAR10(
        root=data_path, train=False, download=True, transform=valid_transform
    )
    
    test_loader = DataLoader(
        test_dataset, batch_size=batch_size, shuffle=False,
        num_workers=num_workers, pin_memory=True
    )
    
    return train_loader, test_loader
