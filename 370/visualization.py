"""
可视化模块
混淆矩阵、变化图展示、训练曲线等
"""

import os
import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics import confusion_matrix, ConfusionMatrixDisplay
from config import CLASS_NAMES, CLASS_COLORS, OUTPUT_DIR

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


def plot_training_curves(history, save_path=None):
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    axes[0].plot(history['train_losses'], label='训练损失', color='blue')
    if history['val_losses']:
        axes[0].plot(history['val_losses'], label='验证损失', color='red')
    axes[0].set_xlabel('Epoch')
    axes[0].set_ylabel('Loss')
    axes[0].set_title('训练损失曲线')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    axes[1].plot(history['train_ious'], label='训练IoU', color='blue')
    if history['val_ious']:
        axes[1].plot(history['val_ious'], label='验证IoU', color='red')
    axes[1].set_xlabel('Epoch')
    axes[1].set_ylabel('IoU')
    axes[1].set_title('训练IoU曲线')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f'训练曲线已保存: {save_path}')
    plt.close()


def plot_confusion_matrix(y_true, y_pred, class_names, save_path=None, normalize='true'):
    cm = confusion_matrix(y_true, y_pred, labels=range(len(class_names)))

    fig, axes = plt.subplots(1, 2, figsize=(16, 6))

    disp1 = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=class_names)
    disp1.plot(ax=axes[0], cmap='Blues', values_format='d', xticks_rotation=45)
    axes[0].set_title('混淆矩阵 (原始计数)')

    if normalize in ['true', 'pred', 'all']:
        if normalize == 'true':
            cm_norm = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]
        elif normalize == 'pred':
            cm_norm = cm.astype('float') / cm.sum(axis=0)[np.newaxis, :]
        else:
            cm_norm = cm.astype('float') / cm.sum()
        cm_norm = np.nan_to_num(cm_norm)

        disp2 = ConfusionMatrixDisplay(confusion_matrix=cm_norm, display_labels=class_names)
        disp2.plot(ax=axes[1], cmap='Blues', values_format='.2f', xticks_rotation=45)
        axes[1].set_title(f'归一化混淆矩阵 (按{normalize})')

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f'混淆矩阵已保存: {save_path}')
    plt.close()

    return cm


def plot_change_detection_results(image1, image2, binary_map, type_map, change_prob,
                                  save_path=None, class_names=None):
    if class_names is None:
        class_names = CLASS_NAMES

    fig, axes = plt.subplots(2, 3, figsize=(20, 12))

    if image1.shape[0] >= 3:
        axes[0, 0].imshow(np.transpose(image1[:3], (1, 2, 0)))
    else:
        axes[0, 0].imshow(image1[0], cmap='gray')
    axes[0, 0].set_title('时相1影像')
    axes[0, 0].axis('off')

    if image2.shape[0] >= 3:
        axes[0, 1].imshow(np.transpose(image2[:3], (1, 2, 0)))
    else:
        axes[0, 1].imshow(image2[0], cmap='gray')
    axes[0, 1].set_title('时相2影像')
    axes[0, 1].axis('off')

    axes[0, 2].imshow(change_prob, cmap='hot', vmin=0, vmax=1)
    axes[0, 2].set_title('变化概率图')
    axes[0, 2].axis('off')

    axes[1, 0].imshow(binary_map, cmap='gray')
    axes[1, 0].set_title('变化二值图')
    axes[1, 0].axis('off')

    color_map = np.zeros((type_map.shape[0], type_map.shape[1], 3), dtype=np.uint8)
    for i, color in enumerate(CLASS_COLORS[:len(class_names)]):
        color_map[type_map == i] = color
    axes[1, 1].imshow(color_map)
    axes[1, 1].set_title('变化类型分类图')
    axes[1, 1].axis('off')

    legend_labels = []
    legend_colors = []
    for i, name in enumerate(class_names):
        if i < len(CLASS_COLORS):
            legend_labels.append(name)
            legend_colors.append(np.array(CLASS_COLORS[i]) / 255.0)
    legend_handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in legend_colors]
    axes[1, 2].legend(legend_handles, legend_labels, loc='center', fontsize=10)
    axes[1, 2].set_title('图例')
    axes[1, 2].axis('off')

    plt.suptitle('遥感图像变化检测结果', fontsize=16)
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f'变化检测结果图已保存: {save_path}')
    plt.close()


def plot_change_type_comparison(type_map1, type_map2, class_names, save_path=None):
    if class_names is None:
        class_names = CLASS_NAMES

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    color_map1 = np.zeros((type_map1.shape[0], type_map1.shape[1], 3), dtype=np.uint8)
    for i, color in enumerate(CLASS_COLORS[:len(class_names)]):
        color_map1[type_map1 == i] = color
    axes[0].imshow(color_map1)
    axes[0].set_title('时相1分类图')
    axes[0].axis('off')

    color_map2 = np.zeros((type_map2.shape[0], type_map2.shape[1], 3), dtype=np.uint8)
    for i, color in enumerate(CLASS_COLORS[:len(class_names)]):
        color_map2[type_map2 == i] = color
    axes[1].imshow(color_map2)
    axes[1].set_title('时相2分类图')
    axes[1].axis('off')

    plt.suptitle('时相对比图', fontsize=14)
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f'对比图已保存: {save_path}')
    plt.close()


def plot_area_statistics(area_stats, class_stats, save_path=None):
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    categories = list(class_stats.keys())
    areas = [class_stats[cat]['area'] for cat in categories]
    ratios = [class_stats[cat]['ratio'] * 100 for cat in categories]

    colors = [tuple(np.array(CLASS_COLORS[i]) / 255.0) for i in range(len(categories))]

    axes[0].barh(categories, areas, color=colors[:len(categories)])
    axes[0].set_xlabel('面积 (像素²)')
    axes[0].set_title('各类变化区域面积统计')
    axes[0].grid(True, alpha=0.3, axis='x')

    axes[1].pie(ratios, labels=categories, colors=colors[:len(categories)],
                autopct='%1.1f%%', startangle=90)
    axes[1].set_title('各类变化区域面积占比')

    plt.suptitle('变化区域面积统计分析', fontsize=14)
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f'面积统计图已保存: {save_path}')
    plt.close()


def plot_region_size_distribution(area_stats, save_path=None):
    if area_stats.get('num_regions', 0) == 0:
        return

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    regions_data = area_stats.get('region_bboxes', [])
    sizes = []
    for bbox in regions_data:
        min_row, min_col, max_row, max_col = bbox
        height = max_row - min_row
        width = max_col - min_col
        sizes.append(height * width)

    if sizes:
        axes[0].hist(sizes, bins=50, color='steelblue', edgecolor='white')
        axes[0].set_xlabel('区域大小 (像素)')
        axes[0].set_ylabel('频数')
        axes[0].set_title('变化区域大小分布直方图')
        axes[0].grid(True, alpha=0.3)

        log_sizes = np.log10(np.array(sizes) + 1)
        axes[1].boxplot(log_sizes, vert=True)
        axes[1].set_ylabel('log10(区域大小)')
        axes[1].set_title('变化区域大小箱线图')
        axes[1].grid(True, alpha=0.3)

    plt.suptitle('变化区域大小分析', fontsize=14)
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f'区域大小分布图已保存: {save_path}')
    plt.close()


def plot_overlay_on_image(image, binary_map, alpha=0.5, save_path=None):
    if image.shape[0] >= 3:
        rgb_image = np.transpose(image[:3], (1, 2, 0))
    else:
        rgb_image = np.stack([image[0]] * 3, axis=-1)

    overlay = rgb_image.copy()
    overlay[binary_map > 0] = [1, 0, 0]

    blended = rgb_image * (1 - alpha) + overlay * alpha
    blended = np.clip(blended, 0, 1)

    fig, ax = plt.subplots(1, 1, figsize=(10, 8))
    ax.imshow(blended)
    ax.set_title('变化区域叠加图 (红色=变化区域)')
    ax.axis('off')

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f'叠加图已保存: {save_path}')
    plt.close()
