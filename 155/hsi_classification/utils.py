import numpy as np
import spectral
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split


def load_envi_data(hdr_path, img_path=None):
    img = spectral.open_image(hdr_path)
    data = img.load()
    return data


def load_mat_data(file_path, data_key='X', label_key='y'):
    from scipy.io import loadmat
    mat_data = loadmat(file_path)
    X = mat_data[data_key]
    y = mat_data[label_key]
    return X, y


def split_train_test(X, y, train_ratio=0.1, random_state=42, stratified=True):
    height, width = y.shape
    X_flat = X.reshape(-1, X.shape[-1])
    y_flat = y.flatten()
    
    valid_mask = y_flat > 0
    X_valid = X_flat[valid_mask]
    y_valid = y_flat[valid_mask]
    indices = np.arange(len(y_valid))
    
    if stratified:
        train_idx, test_idx = train_test_split(
            indices, 
            train_size=train_ratio,
            random_state=random_state,
            stratify=y_valid
        )
    else:
        train_idx, test_idx = train_test_split(
            indices, 
            train_size=train_ratio,
            random_state=random_state
        )
    
    y_train = np.zeros_like(y_flat)
    y_test = np.zeros_like(y_flat)
    
    train_mask = valid_mask.copy()
    train_mask[valid_mask] = np.in1d(np.arange(len(y_valid)), train_idx)
    y_train[train_mask] = y_flat[train_mask]
    
    test_mask = valid_mask.copy()
    test_mask[valid_mask] = np.in1d(np.arange(len(y_valid)), test_idx)
    y_test[test_mask] = y_flat[test_mask]
    
    y_train = y_train.reshape(height, width)
    y_test = y_test.reshape(height, width)
    
    return X, y_train, y_test


def visualize_band(X, band_idx=0, cmap='viridis', figsize=(8, 6)):
    plt.figure(figsize=figsize)
    plt.imshow(X[:, :, band_idx], cmap=cmap)
    plt.title(f'Band {band_idx + 1}')
    plt.axis('off')
    plt.colorbar(fraction=0.046, pad=0.04)
    plt.tight_layout()
    plt.show()


def visualize_rgb(X, r_band=50, g_band=30, b_band=10, figsize=(8, 6)):
    rgb = np.zeros((X.shape[0], X.shape[1], 3), dtype=np.float32)
    rgb[:, :, 0] = X[:, :, r_band] / np.max(X[:, :, r_band])
    rgb[:, :, 1] = X[:, :, g_band] / np.max(X[:, :, g_band])
    rgb[:, :, 2] = X[:, :, b_band] / np.max(X[:, :, b_band])
    
    plt.figure(figsize=figsize)
    plt.imshow(rgb)
    plt.title(f'RGB Composite (Bands {r_band+1}, {g_band+1}, {b_band+1})')
    plt.axis('off')
    plt.tight_layout()
    plt.show()


def visualize_spectrum(X, x, y, figsize=(10, 4)):
    spectrum = X[x, y, :]
    
    plt.figure(figsize=figsize)
    plt.plot(spectrum)
    plt.title(f'Spectrum at ({x}, {y})')
    plt.xlabel('Band')
    plt.ylabel('Intensity')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()


def visualize_ground_truth(y, class_names=None, figsize=(8, 6)):
    plt.figure(figsize=figsize)
    im = plt.imshow(y, cmap='tab20')
    plt.title('Ground Truth')
    plt.axis('off')
    
    if class_names:
        cbar = plt.colorbar(im, fraction=0.046, pad=0.04)
        cbar.set_ticks(np.arange(len(class_names)) + 1)
        cbar.set_ticklabels(class_names)
    
    plt.tight_layout()
    plt.show()


def generate_sample_data(height=100, width=100, bands=200, num_classes=10, random_state=42):
    np.random.seed(random_state)
    
    X = np.random.randn(height, width, bands) * 0.5
    y = np.zeros((height, width), dtype=np.int32)
    
    centers = [
        (25, 25), (25, 75), (50, 50), (75, 25), (75, 75),
        (20, 50), (80, 50), (50, 20), (50, 80), (35, 65)
    ]
    
    for cls in range(1, num_classes + 1):
        cx, cy = centers[cls - 1]
        for i in range(height):
            for j in range(width):
                dist = np.sqrt((i - cx) ** 2 + (j - cy) ** 2)
                if dist < 15:
                    y[i, j] = cls
                    X[i, j, :] += cls * 0.3
    
    return X, y
