import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from sklearn.metrics import confusion_matrix
import spectral as spy


def plot_confusion_matrix(cm, class_names=None, title='Confusion Matrix', 
                          normalize=True, figsize=(12, 10), save_path=None):
    if normalize:
        cm = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]
        fmt = '.2f'
    else:
        fmt = 'd'
    
    if class_names is None:
        class_names = [f'C{i+1}' for i in range(cm.shape[0])]
    
    plt.figure(figsize=figsize)
    sns.heatmap(cm, annot=True, fmt=fmt, cmap='Blues', 
                xticklabels=class_names, 
                yticklabels=class_names)
    plt.title(title, fontsize=16)
    plt.ylabel('True Label', fontsize=14)
    plt.xlabel('Predicted Label', fontsize=14)
    plt.xticks(rotation=45, ha='right')
    plt.yticks(rotation=0)
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f'Confusion matrix saved to {save_path}')
    plt.show()
    plt.close()


def plot_training_history(history, save_path=None):
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    axes[0].plot(history['train_loss'], label='Train Loss')
    axes[0].plot(history['val_loss'], label='Val Loss')
    axes[0].set_title('Training and Validation Loss', fontsize=14)
    axes[0].set_xlabel('Epoch', fontsize=12)
    axes[0].set_ylabel('Loss', fontsize=12)
    axes[0].legend(fontsize=12)
    axes[0].grid(True, alpha=0.3)
    
    axes[1].plot(history['train_acc'], label='Train Acc')
    axes[1].plot(history['val_acc'], label='Val Acc')
    axes[1].set_title('Training and Validation Accuracy', fontsize=14)
    axes[1].set_xlabel('Epoch', fontsize=12)
    axes[1].set_ylabel('Accuracy', fontsize=12)
    axes[1].legend(fontsize=12)
    axes[1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f'Training history saved to {save_path}')
    plt.show()
    plt.close()


def plot_class_distribution(labels, class_names=None, title='Class Distribution', save_path=None):
    unique, counts = np.unique(labels, return_counts=True)
    
    if class_names is None:
        class_names = [f'C{i+1}' for i in range(len(unique))]
    
    plt.figure(figsize=(12, 6))
    bars = plt.bar(class_names, counts, color='steelblue', edgecolor='black')
    plt.title(title, fontsize=14)
    plt.xlabel('Classes', fontsize=12)
    plt.ylabel('Number of Samples', fontsize=12)
    plt.xticks(rotation=45, ha='right')
    
    for bar, count in zip(bars, counts):
        plt.text(bar.get_x() + bar.get_width()/2., bar.get_height(),
                f'{count}', ha='center', va='bottom', fontsize=10)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f'Class distribution saved to {save_path}')
    plt.show()
    plt.close()


def visualize_data_samples(data, gt, class_names=None, save_path=None):
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    
    band_img = data[:, :, 0]
    im1 = axes[0].imshow(band_img, cmap='gray')
    axes[0].set_title('First Band', fontsize=14)
    plt.colorbar(im1, ax=axes[0])
    
    im2 = axes[1].imshow(gt, cmap='nipy_spectral')
    axes[1].set_title('Ground Truth', fontsize=14)
    plt.colorbar(im2, ax=axes[1])
    
    rgb_indices = [29, 19, 9]
    if data.shape[2] > max(rgb_indices):
        rgb_img = np.zeros((data.shape[0], data.shape[1], 3))
        for i, idx in enumerate(rgb_indices):
            band = data[:, :, idx]
            band = (band - band.min()) / (band.max() - band.min())
            rgb_img[:, :, i] = band
        axes[2].imshow(rgb_img)
        axes[2].set_title('False Color Composite', fontsize=14)
    else:
        axes[2].imshow(data[:, :, 0], cmap='jet')
        axes[2].set_title('Band 1 (Jet Colormap', fontsize=14)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f'Data visualization saved to {save_path}')
    plt.show()
    plt.close()


def plot_class_accuracies(class_accs, class_names=None, title='Class-wise Accuracies', save_path=None):
    if class_names is None:
        class_names = [f'C{i+1}' for i in range(len(class_accs))]
    
    plt.figure(figsize=(12, 6))
    bars = plt.bar(class_names, class_accs, color='coral', edgecolor='black')
    plt.title(title, fontsize=14)
    plt.xlabel('Classes', fontsize=12)
    plt.ylabel('Accuracy', fontsize=12)
    plt.ylim([0, 1.05])
    plt.xticks(rotation=45, ha='right')
    
    for bar, acc in zip(bars, class_accs):
        plt.text(bar.get_x() + bar.get_width()/2., bar.get_height(),
                f'{acc:.3f}', ha='center', va='bottom', fontsize=9)
    
    plt.axhline(y=np.mean(class_accs), color='red', linestyle='--', 
                label=f'Mean: {np.mean(class_accs):.3f}')
    plt.legend(fontsize=12)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f'Class accuracies saved to {save_path}')
    plt.show()
    plt.close()


def plot_pca_variance(pca, save_path=None):
    plt.figure(figsize=(10, 6))
    cumulative_variance = np.cumsum(pca.explained_variance_ratio_)
    plt.plot(range(1, len(cumulative_variance) + 1), cumulative_variance, 
            'bo-', markersize=4)
    plt.xlabel('Number of Components', fontsize=12)
    plt.ylabel('Cumulative Explained Variance', fontsize=12)
    plt.title('PCA Cumulative Explained Variance', fontsize=14)
    plt.grid(True, alpha=0.3)
    plt.axhline(y=0.95, color='r', linestyle='--', label='95% Variance')
    plt.legend(fontsize=12)
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f'PCA variance plot saved to {save_path}')
    plt.show()
    plt.close()


def plot_prediction_map(data_shape, predictions, test_indices, patch_size, save_path=None):
    h, w = data_shape[:2]
    pred_map = np.zeros((h, w))
    
    idx = 0
    padding = patch_size // 2
    for i in range(h):
        for j in range(w):
            if (i, j) in test_indices_set:
                if idx < len(predictions):
                    pred_map[i, j] = predictions[idx] + 1
                    idx += 1
    
    plt.figure(figsize=(10, 8))
    plt.imshow(pred_map, cmap='nipy_spectral')
    plt.title('Predicted Classification Map', fontsize=14)
    plt.colorbar()
    plt.axis('off')
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f'Prediction map saved to {save_path}')
    plt.show()
    plt.close()
