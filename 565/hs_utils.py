import numpy as np
import matplotlib.pyplot as plt
from typing import Tuple, List, Optional
from scipy.ndimage import gaussian_filter


def mirror_pad_image(image: np.ndarray, pad_size: int) -> np.ndarray:
    if image.ndim == 2:
        return np.pad(image, pad_size, mode='reflect')
    elif image.ndim == 3:
        return np.pad(image, ((pad_size, pad_size), (pad_size, pad_size), (0, 0)), mode='reflect')
    else:
        raise ValueError("Image must be 2D or 3D")


def symmetric_pad_image(image: np.ndarray, pad_height: int, pad_width: int) -> np.ndarray:
    if image.ndim == 2:
        return np.pad(image, ((pad_height, pad_height), (pad_width, pad_width)), mode='symmetric')
    elif image.ndim == 3:
        return np.pad(image, ((pad_height, pad_height), (pad_width, pad_width), (0, 0)), mode='symmetric')
    else:
        raise ValueError("Image must be 2D or 3D")


def edge_pad_image(image: np.ndarray, pad_size: int) -> np.ndarray:
    if image.ndim == 2:
        return np.pad(image, pad_size, mode='edge')
    elif image.ndim == 3:
        return np.pad(image, ((pad_size, pad_size), (pad_size, pad_size), (0, 0)), mode='edge')
    else:
        raise ValueError("Image must be 2D or 3D")


def regularized_covariance(data: np.ndarray, reg_lambda: float = 1e-4, 
                            reg_method: str = 'ridge') -> Tuple[np.ndarray, np.ndarray]:
    n_samples, n_features = data.shape
    
    mean_vec = np.mean(data, axis=0)
    centered = data - mean_vec
    
    if n_samples < n_features:
        reg_lambda = max(reg_lambda, 0.1)
    
    cov_matrix = (centered.T @ centered) / (n_samples - 1)
    
    if reg_method == 'ridge':
        reg_term = reg_lambda * np.eye(n_features)
        cov_reg = cov_matrix + reg_term
    elif reg_method == 'condition':
        eigvals, eigvecs = np.linalg.eigh(cov_matrix)
        min_eig = reg_lambda * np.max(eigvals)
        eigvals_reg = np.maximum(eigvals, min_eig)
        cov_reg = eigvecs @ np.diag(eigvals_reg) @ eigvecs.T
    elif reg_method == 'shrinkage':
        alpha = reg_lambda
        mu = np.trace(cov_matrix) / n_features
        cov_reg = (1 - alpha) * cov_matrix + alpha * mu * np.eye(n_features)
    else:
        raise ValueError(f"Unknown regularization method: {reg_method}")
    
    return cov_reg, mean_vec


def safe_inverse_covariance(cov_matrix: np.ndarray, reg_lambda: float = 1e-6) -> np.ndarray:
    try:
        cov_inv = np.linalg.inv(cov_matrix)
        if np.any(np.isnan(cov_inv)) or np.any(np.isinf(cov_inv)):
            raise np.linalg.LinAlgError("Inverse contains NaN or Inf")
        return cov_inv
    except np.linalg.LinAlgError:
        reg_cov = cov_matrix + reg_lambda * np.eye(cov_matrix.shape[0])
        return np.linalg.inv(reg_cov)


def covariance_condition_number(cov_matrix: np.ndarray) -> float:
    eigvals = np.linalg.eigvalsh(cov_matrix)
    return np.max(eigvals) / (np.min(eigvals) + 1e-10)



def generate_hyperspectral_image(
    height: int = 100,
    width: int = 100,
    n_bands: int = 50,
    n_anomalies: int = 5,
    anomaly_intensity: float = 5.0,
    seed: Optional[int] = None
) -> Tuple[np.ndarray, np.ndarray]:
    if seed is not None:
        np.random.seed(seed)

    n_background_components = 3
    background = np.zeros((height, width, n_bands))

    for i in range(n_background_components):
        mean_spec = np.random.randn(n_bands) * 2
        spatial_map = np.random.randn(height, width)
        spatial_map = gaussian_filter(spatial_map, sigma=5)
        spatial_map = (spatial_map - spatial_map.mean()) / spatial_map.std()
        background += np.outer(spatial_map, mean_spec).reshape(height, width, n_bands)

    noise = np.random.randn(height, width, n_bands) * 0.5
    image = background + noise

    ground_truth = np.zeros((height, width), dtype=bool)

    for _ in range(n_anomalies):
        y = np.random.randint(10, height - 10)
        x = np.random.randint(10, width - 10)
        anomaly_size = np.random.randint(2, 6)

        anomaly_spec = np.random.randn(n_bands) * anomaly_intensity

        y_slice = slice(y - anomaly_size, y + anomaly_size + 1)
        x_slice = slice(x - anomaly_size, x + anomaly_size + 1)

        image[y_slice, x_slice, :] += anomaly_spec
        ground_truth[y_slice, x_slice] = True

    return image, ground_truth


def generate_complex_hyperspectral(
    height: int = 200,
    width: int = 200,
    n_bands: int = 100,
    seed: Optional[int] = None
) -> Tuple[np.ndarray, np.ndarray]:
    if seed is not None:
        np.random.seed(seed)

    image = np.zeros((height, width, n_bands))
    ground_truth = np.zeros((height, width), dtype=bool)

    for i in range(n_bands):
        x = np.linspace(0, 1, width)
        y = np.linspace(0, 1, height)
        xx, yy = np.meshgrid(x, y)
        image[:, :, i] = np.sin(2 * np.pi * (i / n_bands) * xx) + np.cos(2 * np.pi * (i / n_bands) * yy)

    image += np.random.randn(height, width, n_bands) * 0.3

    anomaly_spectrum = np.random.randn(n_bands) * 3

    for _ in range(8):
        cy = np.random.randint(20, height - 20)
        cx = np.random.randint(20, width - 20)
        r = np.random.randint(3, 8)

        y, x = np.ogrid[:height, :width]
        mask = (y - cy) ** 2 + (x - cx) ** 2 <= r ** 2
        image[mask, :] += anomaly_spectrum
        ground_truth[mask] = True

    return image, ground_truth


class HSVisualizer:
    def __init__(self, figsize: Tuple[int, int] = (12, 8)):
        self.figsize = figsize

    def plot_rgb_composite(self, image: np.ndarray, ax=None, title: str = "RGB Composite"):
        if ax is None:
            fig, ax = plt.subplots(figsize=self.figsize)

        n_bands = image.shape[-1]
        r_idx = min(n_bands - 1, int(n_bands * 0.75))
        g_idx = min(n_bands - 1, int(n_bands * 0.5))
        b_idx = min(n_bands - 1, int(n_bands * 0.25))

        rgb = np.stack([image[:, :, r_idx], image[:, :, g_idx], image[:, :, b_idx]], axis=-1)
        rgb = (rgb - rgb.min()) / (rgb.max() - rgb.min() + 1e-8)

        ax.imshow(rgb)
        ax.set_title(title)
        ax.axis('off')
        return ax

    def plot_spectrum(self, image: np.ndarray, y: int, x: int, ax=None, title: str = None):
        if ax is None:
            fig, ax = plt.subplots(figsize=self.figsize)

        spectrum = image[y, x, :]
        ax.plot(spectrum)
        ax.set_xlabel('Band')
        ax.set_ylabel('Intensity')
        if title:
            ax.set_title(title)
        else:
            ax.set_title(f'Spectrum at ({y}, {x})')
        ax.grid(True, alpha=0.3)
        return ax

    def plot_detection_results(self, image: np.ndarray, scores: np.ndarray, 
                                 ground_truth: Optional[np.ndarray] = None,
                                 threshold: Optional[float] = None):
        n_plots = 2 if ground_truth is None else 3
        fig, axes = plt.subplots(1, n_plots, figsize=(5 * n_plots, 5))

        self.plot_rgb_composite(image, ax=axes[0], title="Original Image")

        im = axes[1].imshow(scores, cmap='hot')
        axes[1].set_title("RX Anomaly Scores")
        axes[1].axis('off')
        plt.colorbar(im, ax=axes[1], fraction=0.046, pad=0.04)

        if ground_truth is not None:
            if threshold is None:
                threshold = np.percentile(scores, 95)

            detection = scores > threshold
            axes[2].imshow(ground_truth, cmap='gray', alpha=0.5)
            axes[2].imshow(detection, cmap='Reds', alpha=0.5)
            axes[2].set_title(f"Detection (threshold={threshold:.2f})")
            axes[2].axis('off')

        plt.tight_layout()
        return fig, axes

    def plot_score_histogram(self, scores: np.ndarray, ground_truth: Optional[np.ndarray] = None, 
                              ax=None):
        if ax is None:
            fig, ax = plt.subplots(figsize=self.figsize)

        if ground_truth is not None:
            anomaly_scores = scores[ground_truth]
            background_scores = scores[~ground_truth]

            ax.hist(background_scores.flatten(), bins=50, alpha=0.7, 
                    label='Background', density=True)
            ax.hist(anomaly_scores.flatten(), bins=50, alpha=0.7, 
                    label='Anomalies', density=True)
            ax.legend()
        else:
            ax.hist(scores.flatten(), bins=50, alpha=0.7, density=True)

        ax.set_xlabel('RX Score')
        ax.set_ylabel('Density')
        ax.set_title('Score Distribution')
        ax.grid(True, alpha=0.3)
        return ax

    def plot_mean_spectrum(self, image: np.ndarray, ax=None):
        if ax is None:
            fig, ax = plt.subplots(figsize=self.figsize)

        mean_spec = np.mean(image, axis=(0, 1))
        std_spec = np.std(image, axis=(0, 1))

        ax.plot(mean_spec, label='Mean')
        ax.fill_between(range(len(mean_spec)), 
                        mean_spec - std_spec, 
                        mean_spec + std_spec, 
                        alpha=0.3, label='±1 Std')
        ax.set_xlabel('Band')
        ax.set_ylabel('Intensity')
        ax.set_title('Mean Spectrum of Image')
        ax.legend()
        ax.grid(True, alpha=0.3)
        return ax

    def plot_roc_curve(self, scores: np.ndarray, ground_truth: np.ndarray, ax=None):
        from sklearn.metrics import roc_curve, auc

        if ax is None:
            fig, ax = plt.subplots(figsize=self.figsize)

        fpr, tpr, _ = roc_curve(ground_truth.flatten(), scores.flatten())
        roc_auc = auc(fpr, tpr)

        ax.plot(fpr, tpr, label=f'ROC curve (AUC = {roc_auc:.3f})')
        ax.plot([0, 1], [0, 1], 'k--')
        ax.set_xlim([0.0, 1.0])
        ax.set_ylim([0.0, 1.05])
        ax.set_xlabel('False Positive Rate')
        ax.set_ylabel('True Positive Rate')
        ax.set_title('Receiver Operating Characteristic')
        ax.legend(loc="lower right")
        ax.grid(True, alpha=0.3)
        return ax


def compute_metrics(scores: np.ndarray, ground_truth: np.ndarray, 
                     threshold_percentile: float = 95) -> dict:
    from sklearn.metrics import precision_score, recall_score, f1_score, roc_auc_score

    threshold = np.percentile(scores, threshold_percentile)
    predictions = (scores > threshold).astype(int)

    y_true = ground_truth.flatten()
    y_pred = predictions.flatten()

    return {
        'threshold': threshold,
        'precision': precision_score(y_true, y_pred, zero_division=0),
        'recall': recall_score(y_true, y_pred, zero_division=0),
        'f1': f1_score(y_true, y_pred, zero_division=0),
        'auc': roc_auc_score(y_true, scores.flatten()),
        'detection_rate': recall_score(y_true, y_pred, zero_division=0),
        'false_alarm_rate': np.sum(y_pred[y_true == 0]) / np.sum(y_true == 0)
    }
