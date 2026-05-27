"""
推理模块
使用训练好的模型进行整图变化检测
"""

import os
import numpy as np
import torch
from torch.utils.data import DataLoader
from tqdm import tqdm

from models.unet import UNet
from data_loader import FullImageDataset
from config import MODEL_CONFIG, TRAIN_CONFIG, CHECKPOINT_DIR


def load_model(checkpoint_path, device):
    model = UNet(
        in_channels=MODEL_CONFIG['in_channels'],
        out_channels=MODEL_CONFIG['out_channels'],
        bilinear=MODEL_CONFIG['bilinear']
    ).to(device)

    if os.path.exists(checkpoint_path):
        checkpoint = torch.load(checkpoint_path, map_location=device)
        model.load_state_dict(checkpoint['model_state_dict'])
        print(f'模型加载成功: {checkpoint_path}')
    else:
        print(f'警告: 检查点不存在 {checkpoint_path}, 使用随机初始化模型')

    model.eval()
    return model


def predict_whole_image(model, image1_path, image2_path, device):
    dataset = FullImageDataset(
        image1_path, image2_path,
        patch_size=TRAIN_CONFIG['patch_size'],
        stride=TRAIN_CONFIG['stride']
    )

    dataloader = DataLoader(
        dataset,
        batch_size=TRAIN_CONFIG['batch_size'],
        shuffle=False,
        num_workers=TRAIN_CONFIG['num_workers']
    )

    height, width = dataset.height, dataset.width
    num_classes = MODEL_CONFIG['out_channels']

    output_prob = np.zeros((num_classes, height, width), dtype=np.float32)
    count_map = np.zeros((height, width), dtype=np.float32)

    with torch.no_grad():
        for img1, img2, coords in tqdm(dataloader, desc='推理中'):
            img1 = img1.to(device)
            img2 = img2.to(device)

            outputs = model(img1, img2)
            probs = torch.softmax(outputs, dim=1)
            probs = probs.cpu().numpy()

            for i in range(len(coords)):
                y, x = coords[i].numpy()
                ps = TRAIN_CONFIG['patch_size']

                y_end = min(y + ps, height)
                x_end = min(x + ps, width)
                actual_h = y_end - y
                actual_w = x_end - x

                output_prob[:, y:y_end, x:x_end] += probs[i, :, :actual_h, :actual_w]
                count_map[y:y_end, x:x_end] += 1.0

    count_map = np.maximum(count_map, 1.0)
    output_prob /= count_map[np.newaxis, :, :]

    change_map = np.argmax(output_prob, axis=0).astype(np.uint8)
    change_prob = np.max(output_prob, axis=0)

    return change_map, change_prob, dataset


def predict_with_tta(model, image1_path, image2_path, device):
    dataset = FullImageDataset(
        image1_path, image2_path,
        patch_size=TRAIN_CONFIG['patch_size'],
        stride=TRAIN_CONFIG['stride']
    )

    dataloader = DataLoader(
        dataset,
        batch_size=TRAIN_CONFIG['batch_size'],
        shuffle=False,
        num_workers=TRAIN_CONFIG['num_workers']
    )

    height, width = dataset.height, dataset.width
    num_classes = MODEL_CONFIG['out_channels']

    output_prob = np.zeros((num_classes, height, width), dtype=np.float32)
    count_map = np.zeros((height, width), dtype=np.float32)

    tta_transforms = [
        (0, False),
        (0, True),
        (1, False),
        (2, False),
        (3, False),
    ]

    with torch.no_grad():
        for img1, img2, coords in tqdm(dataloader, desc='TTA推理中'):
            batch_prob = np.zeros((img1.shape[0], num_classes, img1.shape[2], img1.shape[3]),
                                  dtype=np.float32)

            for k, flip in tta_transforms:
                img1_tta = torch.rot90(img1, k, [2, 3])
                img2_tta = torch.rot90(img2, k, [2, 3])
                if flip:
                    img1_tta = torch.flip(img1_tta, [3])
                    img2_tta = torch.flip(img2_tta, [3])

                img1_tta = img1_tta.to(device)
                img2_tta = img2_tta.to(device)

                outputs = model(img1_tta, img2_tta)
                probs = torch.softmax(outputs, dim=1)

                if flip:
                    probs = torch.flip(probs, [3])
                probs = torch.rot90(probs, -k, [2, 3])

                batch_prob += probs.cpu().numpy()

            batch_prob /= len(tta_transforms)

            for i in range(len(coords)):
                y, x = coords[i].numpy()
                ps = TRAIN_CONFIG['patch_size']

                y_end = min(y + ps, height)
                x_end = min(x + ps, width)
                actual_h = y_end - y
                actual_w = x_end - x

                output_prob[:, y:y_end, x:x_end] += batch_prob[i, :, :actual_h, :actual_w]
                count_map[y:y_end, x:x_end] += 1.0

    count_map = np.maximum(count_map, 1.0)
    output_prob /= count_map[np.newaxis, :, :]

    change_map = np.argmax(output_prob, axis=0).astype(np.uint8)
    change_prob = np.max(output_prob, axis=0)

    return change_map, change_prob, dataset
