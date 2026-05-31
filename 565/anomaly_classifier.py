import numpy as np
from typing import Dict, List, Optional, Tuple
from scipy.ndimage import label, binary_fill_holes, binary_closing
from scipy.spatial.distance import cdist
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA

from hs_utils import regularized_covariance, safe_inverse_covariance


class AnomalyClassifier:
    MAN_MADE = 0
    NATURAL = 1

    def __init__(self, n_spectral_features: int = 5, spatial_compactness: float = 0.5,
                 reg_lambda: float = 1e-4, reg_method: str = 'ridge'):
        self.n_spectral_features = n_spectral_features
        self.spatial_compactness = spatial_compactness
        self.reg_lambda = reg_lambda
        self.reg_method = reg_method

        self._background_mean = None
        self._background_cov = None
        self._background_cov_inv = None
        self._pca = None

    def fit_background(self, image: np.ndarray, background_mask: Optional[np.ndarray] = None) -> None:
        h, w, bands = image.shape
        if background_mask is None:
            flat = image.reshape(-1, bands)
            n = flat.shape[0]
            n_bg = max(1, int(n * 0.5))
            scores = np.sum(flat ** 2, axis=1)
            bg_indices = np.argsort(scores)[:n_bg]
            background_data = flat[bg_indices]
        else:
            background_data = image[background_mask]

        if background_data.ndim == 3:
            background_data = background_data.reshape(-1, background_data.shape[-1])

        self._background_cov, self._background_mean = regularized_covariance(
            background_data, reg_lambda=self.reg_lambda, reg_method=self.reg_method
        )
        self._background_cov_inv = safe_inverse_covariance(self._background_cov)

        if bands > self.n_spectral_features:
            self._pca = PCA(n_components=self.n_spectral_features)
            self._pca.fit(background_data)

    def _extract_connected_components(self, anomaly_mask: np.ndarray) -> List[Dict]:
        labeled_array, n_features = label(anomaly_mask)
        components = []

        for i in range(1, n_features + 1):
            component_mask = labeled_array == i
            pixels = np.argwhere(component_mask)

            if len(pixels) == 0:
                continue

            y_min, x_min = pixels.min(axis=0)
            y_max, x_max = pixels.max(axis=0)
            area = len(pixels)

            perimeter = 0
            for p in pixels:
                for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    ny, nx = p[0] + dy, p[1] + dx
                    if (ny < 0 or ny >= anomaly_mask.shape[0] or
                            nx < 0 or nx >= anomaly_mask.shape[1] or
                            not anomaly_mask[ny, nx]):
                        perimeter += 1

            circularity = 4 * np.pi * area / (perimeter ** 2 + 1e-10)

            aspect_ratio = (y_max - y_min + 1) / (x_max - x_min + 1 + 1e-10)

            fill_ratio = area / ((y_max - y_min + 1) * (x_max - x_min + 1) + 1e-10)

            components.append({
                'id': i,
                'pixels': pixels,
                'area': area,
                'perimeter': perimeter,
                'circularity': circularity,
                'aspect_ratio': aspect_ratio,
                'fill_ratio': fill_ratio,
                'bbox': (y_min, y_max, x_min, x_max),
                'mask': component_mask
            })

        return components

    def _compute_spectral_features(self, image: np.ndarray, component: Dict) -> Dict:
        mask = component['mask']
        spectra = image[mask]

        mean_spec = np.mean(spectra, axis=0)
        std_spec = np.std(spectra, axis=0)
        spectral_range = np.max(spectra, axis=0) - np.min(spectra, axis=0)

        centered = mean_spec - self._background_mean
        rx_score = float(centered @ self._background_cov_inv @ centered.T)

        spectral_cv = np.mean(std_spec / (np.abs(mean_spec) + 1e-10))

        n_bands = len(mean_spec)
        gradients = np.abs(np.diff(mean_spec))
        spectral_smoothness = np.mean(gradients)

        spectral_features = {
            'rx_score': rx_score,
            'spectral_cv': spectral_cv,
            'spectral_smoothness': spectral_smoothness,
            'spectral_range_mean': np.mean(spectral_range),
            'spectral_range_std': np.std(spectral_range),
            'mean_intensity': np.mean(mean_spec),
            'std_intensity': np.mean(std_spec)
        }

        if self._pca is not None:
            pca_scores = self._pca.transform(mean_spec.reshape(1, -1))
            for i, score in enumerate(pca_scores[0]):
                spectral_features[f'pca_{i}'] = score

        return spectral_features

    def _compute_spatial_features(self, component: Dict, image_shape: Tuple) -> Dict:
        area = component['area']
        perimeter = component['perimeter']
        circularity = component['circularity']
        aspect_ratio = component['aspect_ratio']
        fill_ratio = component['fill_ratio']

        h, w = image_shape[:2]
        relative_area = area / (h * w)

        y_min, y_max, x_min, x_max = component['bbox']
        bbox_area = (y_max - y_min + 1) * (x_max - x_min + 1)
        extent = area / (bbox_area + 1e-10)

        pixels = component['pixels']
        cy = np.mean(pixels[:, 0])
        cx = np.mean(pixels[:, 1])
        center_dist = np.sqrt((cy - h / 2) ** 2 + (cx - w / 2) ** 2) / (np.sqrt(h ** 2 + w ** 2) / 2)

        spatial_features = {
            'area': area,
            'relative_area': relative_area,
            'perimeter': perimeter,
            'circularity': circularity,
            'aspect_ratio': aspect_ratio,
            'fill_ratio': fill_ratio,
            'extent': extent,
            'center_distance': center_dist
        }

        return spatial_features

    def _classify_component(self, spatial_features: Dict, spectral_features: Dict) -> Tuple[int, float]:
        man_made_score = 0.0
        natural_score = 0.0

        circ = spatial_features['circularity']
        if circ > 0.6:
            man_made_score += 2.0
        elif circ > 0.3:
            man_made_score += 0.5
            natural_score += 0.5
        else:
            natural_score += 1.5

        ar = spatial_features['aspect_ratio']
        if 0.5 < ar < 2.0:
            man_made_score += 1.0
        else:
            natural_score += 1.0

        fill = spatial_features['fill_ratio']
        if fill > 0.7:
            man_made_score += 1.5
        elif fill > 0.4:
            man_made_score += 0.5
            natural_score += 0.5
        else:
            natural_score += 1.5

        area = spatial_features['relative_area']
        if area < 0.005:
            man_made_score += 1.0
        elif area < 0.02:
            natural_score += 0.5
            man_made_score += 0.5
        else:
            natural_score += 1.5

        rx = spectral_features['rx_score']
        if rx > 100:
            man_made_score += 1.5
        elif rx > 20:
            man_made_score += 0.5
            natural_score += 0.5
        else:
            natural_score += 1.0

        cv = spectral_features['spectral_cv']
        if cv < 0.3:
            man_made_score += 1.5
        elif cv < 0.6:
            man_made_score += 0.5
            natural_score += 0.5
        else:
            natural_score += 1.5

        smoothness = spectral_features['spectral_smoothness']
        if smoothness < 1.0:
            man_made_score += 1.0
        else:
            natural_score += 1.0

        total = man_made_score + natural_score
        confidence = max(man_made_score, natural_score) / (total + 1e-10)

        if man_made_score > natural_score:
            return self.MAN_MADE, confidence
        else:
            return self.NATURAL, confidence

    def classify(self, image: np.ndarray, scores: np.ndarray,
                 threshold_percentile: float = 95) -> Dict:
        if self._background_mean is None:
            self.fit_background(image)

        h, w, bands = image.shape
        threshold = np.percentile(scores, threshold_percentile)
        anomaly_mask = scores > threshold

        anomaly_mask = binary_closing(anomaly_mask, structure=np.ones((3, 3)))
        anomaly_mask = binary_fill_holes(anomaly_mask)

        components = self._extract_connected_components(anomaly_mask)

        classification_map = np.full((h, w), -1, dtype=int)
        confidence_map = np.zeros((h, w), dtype=np.float64)
        component_info = []

        for comp in components:
            spatial_feat = self._compute_spatial_features(comp, image.shape)
            spectral_feat = self._compute_spectral_features(image, comp)

            label_type, confidence = self._classify_component(spatial_feat, spectral_feat)

            classification_map[comp['mask']] = label_type
            confidence_map[comp['mask']] = confidence

            info = {
                'id': comp['id'],
                'classification': 'man_made' if label_type == self.MAN_MADE else 'natural',
                'confidence': confidence,
                'area': comp['area'],
                'spatial_features': spatial_feat,
                'spectral_features': spectral_feat
            }
            component_info.append(info)

        return {
            'classification_map': classification_map,
            'confidence_map': confidence_map,
            'anomaly_mask': anomaly_mask,
            'threshold': threshold,
            'n_components': len(components),
            'n_man_made': sum(1 for c in component_info if c['classification'] == 'man_made'),
            'n_natural': sum(1 for c in component_info if c['classification'] == 'natural'),
            'component_info': component_info
        }

    def classify_spectral(self, image: np.ndarray, scores: np.ndarray,
                          threshold_percentile: float = 95,
                          n_clusters: int = 2) -> Dict:
        if self._background_mean is None:
            self.fit_background(image)

        h, w, bands = image.shape
        threshold = np.percentile(scores, threshold_percentile)
        anomaly_mask = scores > threshold

        anomaly_mask = binary_closing(anomaly_mask, structure=np.ones((3, 3)))
        anomaly_mask = binary_fill_holes(anomaly_mask)

        anomaly_spectra = image[anomaly_mask]

        if len(anomaly_spectra) < n_clusters + 1:
            return self.classify(image, scores, threshold_percentile)

        if self._pca is not None:
            features = self._pca.transform(anomaly_spectra)
        else:
            features = anomaly_spectra.copy()

        spatial_coords = np.argwhere(anomaly_mask).astype(np.float64)
        spatial_coords[:, 0] /= h
        spatial_coords[:, 1] /= w
        spatial_coords *= self.spatial_compactness
        features = np.hstack([features, spatial_coords])

        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        cluster_labels = kmeans.fit_predict(features)

        cluster_stats = []
        for c in range(n_clusters):
            c_mask = cluster_labels == c
            c_spectra = anomaly_spectra[c_mask]
            c_mean = np.mean(c_spectra, axis=0)
            centered = c_mean - self._background_mean
            rx = float(centered @ self._background_cov_inv @ centered.T)
            cluster_stats.append({
                'cluster': c,
                'count': int(np.sum(c_mask)),
                'rx_score': rx,
                'mean_intensity': float(np.mean(c_mean))
            })

        man_made_cluster = max(cluster_stats, key=lambda x: x['rx_score'])['cluster']

        classification_map = np.full((h, w), -1, dtype=int)
        confidence_map = np.zeros((h, w), dtype=np.float64)

        anomaly_pixels = np.argwhere(anomaly_mask)
        for i, (y, x) in enumerate(anomaly_pixels):
            if cluster_labels[i] == man_made_cluster:
                classification_map[y, x] = self.MAN_MADE
                dist = np.min(cdist(features[i:i + 1], kmeans.cluster_centers_[[c for c in range(n_clusters) if c != man_made_cluster]]))
            else:
                classification_map[y, x] = self.NATURAL
                dist = np.min(cdist(features[i:i + 1], kmeans.cluster_centers_[[man_made_cluster]]))
            confidence_map[y, x] = 1.0 / (1.0 + dist + 1e-10)

        components = self._extract_connected_components(anomaly_mask)
        component_info = []
        for comp in components:
            comp_pixels = comp['mask']
            comp_classes = classification_map[comp_pixels]
            valid_classes = comp_classes[comp_classes >= 0]
            if len(valid_classes) == 0:
                continue
            majority_class = np.bincount(valid_classes.astype(int) + 1).argmax() - 1
            info = {
                'id': comp['id'],
                'classification': 'man_made' if majority_class == self.MAN_MADE else 'natural',
                'confidence': float(np.mean(confidence_map[comp_pixels])),
                'area': comp['area']
            }
            component_info.append(info)

        return {
            'classification_map': classification_map,
            'confidence_map': confidence_map,
            'anomaly_mask': anomaly_mask,
            'threshold': threshold,
            'n_components': len(components),
            'n_man_made': sum(1 for c in component_info if c['classification'] == 'man_made'),
            'n_natural': sum(1 for c in component_info if c['classification'] == 'natural'),
            'component_info': component_info,
            'cluster_stats': cluster_stats
        }
