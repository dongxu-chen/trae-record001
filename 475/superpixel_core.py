import numpy as np
import cv2
from skimage.segmentation import slic, felzenszwalb, mark_boundaries, relabel_sequential
from skimage.color import rgb2lab
from skimage.util import img_as_float, img_as_ubyte
from skimage.measure import regionprops, label as sk_label
from collections import defaultdict


COMPACTNESS_PRESETS = {
    "flat": {"compactness": 3.0, "desc": "Flat regions: low compactness, irregular shapes"},
    "balanced": {"compactness": 10.0, "desc": "Balanced: default compactness"},
    "texture": {"compactness": 30.0, "desc": "Texture: high compactness, regular shapes"},
}


class SuperpixelSegmenter:

    def __init__(self, image):
        self.original_image = image.copy()
        self.image_float = img_as_float(image)
        self.segments = None
        self.algorithm_name = None
        self.edge_map = None
        self.compactness_preset = None
        self.classifier = SuperpixelClassifier()

    def compute_edge_map(self, method="canny", low_thresh=50, high_thresh=150,
                         sobel_ksize=3):
        gray = cv2.cvtColor(self.original_image, cv2.COLOR_RGB2GRAY)
        if method == "canny":
            edges = cv2.Canny(gray, low_thresh, high_thresh, L2gradient=True)
        elif method == "sobel":
            gx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=sobel_ksize)
            gy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=sobel_ksize)
            mag = np.sqrt(gx ** 2 + gy ** 2)
            edges = ((mag / mag.max()) * 255).astype(np.uint8)
        elif method == "laplacian":
            lap = cv2.Laplacian(gray, cv2.CV_64F, ksize=sobel_ksize)
            mag = np.abs(lap)
            edges = ((mag / mag.max()) * 255).astype(np.uint8)
        else:
            raise ValueError(f"Unknown edge method: {method}")
        self.edge_map = edges
        return edges

    def detect_texture_level(self):
        gray = cv2.cvtColor(self.original_image, cv2.COLOR_RGB2GRAY)
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        lap_var = laplacian.var()
        if lap_var < 50:
            return "flat"
        elif lap_var < 200:
            return "balanced"
        else:
            return "texture"

    def resolve_compactness(self, compactness_mode="auto"):
        if isinstance(compactness_mode, (int, float)):
            self.compactness_preset = "custom"
            return float(compactness_mode)
        if compactness_mode == "auto":
            self.compactness_preset = self.detect_texture_level()
            return COMPACTNESS_PRESETS[self.compactness_preset]["compactness"]
        if compactness_mode in COMPACTNESS_PRESETS:
            self.compactness_preset = compactness_mode
            return COMPACTNESS_PRESETS[compactness_mode]["compactness"]
        self.compactness_preset = "balanced"
        return COMPACTNESS_PRESETS["balanced"]["compactness"]

    def _align_boundaries_to_edges(self, segments, edge_map, iterations=2):
        if edge_map is None:
            return segments
        seg = segments.copy()
        h, w = seg.shape
        edge_norm = edge_map.astype(np.float64) / 255.0
        lab = rgb2lab(self.image_float)
        for _ in range(iterations):
            new_seg = seg.copy()
            for y in range(1, h - 1):
                for x in range(1, w - 1):
                    current = seg[y, x]
                    neighbors = [
                        (y - 1, x), (y + 1, x),
                        (y, x - 1), (y, x + 1),
                    ]
                    for ny, nx in neighbors:
                        nlabel = seg[ny, nx]
                        if nlabel == current:
                            continue
                        edge_strength = edge_norm[y, x]
                        if edge_strength < 0.3:
                            continue
                        color_dist = np.linalg.norm(lab[y, x] - lab[ny, nx])
                        if color_dist < 5.0 * (1.0 - edge_strength):
                            new_seg[y, x] = nlabel
                            break
            seg = new_seg
        return relabel_sequential(seg)[0] + 1

    def run_slic(self, n_segments=100, compactness_mode="auto", sigma=1.0,
                 max_iter=10, enforce_connectivity=True,
                 edge_guided=False, edge_method="canny",
                 edge_low=50, edge_high=150):
        self.algorithm_name = "SLIC"
        compactness = self.resolve_compactness(compactness_mode)

        input_image = self.image_float
        if edge_guided:
            self.compute_edge_map(method=edge_method,
                                  low_thresh=edge_low, high_thresh=edge_high)
            edge_weight = self.edge_map.astype(np.float64) / 255.0
            edge_3ch = np.repeat(edge_weight[:, :, np.newaxis], 3, axis=2)
            edge_preserve = self.image_float * (1.0 - edge_3ch * 0.3)
            input_image = edge_preserve

        self.segments = slic(
            input_image,
            n_segments=n_segments,
            compactness=compactness,
            sigma=sigma,
            max_num_iter=max_iter,
            enforce_connectivity=enforce_connectivity,
            start_label=1,
        )

        if edge_guided and self.edge_map is not None:
            self.segments = self._align_boundaries_to_edges(
                self.segments, self.edge_map
            )

        return self.segments

    def run_felzenszwalb(self, scale=100, sigma=0.5, min_size=50,
                         edge_guided=False, edge_method="canny",
                         edge_low=50, edge_high=150):
        self.algorithm_name = "Felzenszwalb"
        self.compactness_preset = None

        input_image = self.image_float
        if edge_guided:
            self.compute_edge_map(method=edge_method,
                                  low_thresh=edge_low, high_thresh=edge_high)
            edge_weight = self.edge_map.astype(np.float64) / 255.0
            edge_3ch = np.repeat(edge_weight[:, :, np.newaxis], 3, axis=2)
            edge_preserve = self.image_float * (1.0 - edge_3ch * 0.3)
            input_image = edge_preserve

        self.segments = felzenszwalb(
            input_image,
            scale=scale,
            sigma=sigma,
            min_size=min_size,
        )
        self.segments = sk_label(self.segments) + 1

        if edge_guided and self.edge_map is not None:
            self.segments = self._align_boundaries_to_edges(
                self.segments, self.edge_map
            )

        return self.segments

    def get_num_segments(self):
        if self.segments is None:
            return 0
        return len(np.unique(self.segments))

    def visualize_boundaries(self, color=(1, 1, 0)):
        if self.segments is None:
            return self.original_image
        return img_as_ubyte(mark_boundaries(self.image_float, self.segments, color=color))

    def visualize_mean_color(self):
        if self.segments is None:
            return self.original_image
        result = self.original_image.copy().astype(np.float64)
        for seg_id in np.unique(self.segments):
            mask = self.segments == seg_id
            for c in range(3):
                result[:, :, c][mask] = self.original_image[:, :, c][mask].mean()
        return result.astype(np.uint8)

    def visualize_random_color(self):
        if self.segments is None:
            return self.original_image
        result = np.zeros_like(self.original_image)
        for seg_id in np.unique(self.segments):
            mask = self.segments == seg_id
            color = np.random.randint(0, 256, 3)
            result[mask] = color
        return result

    def _compute_segment_features(self):
        lab_image = rgb2lab(self.image_float)
        features = {}
        regions = regionprops(self.segments)
        for region in regions:
            seg_id = region.label
            mask = self.segments == seg_id
            mean_lab = lab_image[mask].mean(axis=0)
            var_lab = lab_image[mask].var(axis=0)
            total_var = var_lab.sum()
            features[seg_id] = {
                "mean_lab": mean_lab,
                "var_lab": var_lab,
                "total_var": total_var,
                "area": region.area,
                "centroid": region.centroid,
                "mask": mask,
            }
        return features

    def _find_adjacent_pairs(self):
        adj = defaultdict(set)
        h, w = self.segments.shape
        seg = self.segments
        down = seg[:-1, :] != seg[1:, :]
        right = seg[:, :-1] != seg[:, 1:]
        ys_d, xs_d = np.where(down)
        for y, x in zip(ys_d, xs_d):
            a, b = seg[y, x], seg[y + 1, x]
            adj[a].add(b)
            adj[b].add(a)
        ys_r, xs_r = np.where(right)
        for y, x in zip(ys_r, xs_r):
            a, b = seg[y, x], seg[y, x + 1]
            adj[a].add(b)
            adj[b].add(a)
        return adj

    def merge_small_segments(self, min_size=100):
        if self.segments is None:
            return self.segments
        features = self._compute_segment_features()
        adj = self._find_adjacent_pairs()
        merged = self.segments.copy()
        segments_order = sorted(
            features.keys(), key=lambda sid: features[sid]["area"]
        )
        for seg_id in segments_order:
            current_mask = merged == seg_id
            if current_mask.sum() == 0:
                continue
            area = current_mask.sum()
            if area >= min_size:
                continue
            neighbors = adj.get(seg_id, set())
            best_neighbor = None
            best_dist = float("inf")
            mean_lab = features[seg_id]["mean_lab"]
            for nid in neighbors:
                nid_mask = merged == nid
                if nid_mask.sum() == 0:
                    continue
                if nid in features:
                    nid_lab = features[nid]["mean_lab"]
                else:
                    nid_lab = rgb2lab(self.image_float)[nid_mask].mean(axis=0)
                dist = np.linalg.norm(mean_lab - nid_lab)
                if dist < best_dist:
                    best_dist = dist
                    best_neighbor = nid
            if best_neighbor is not None:
                merged[current_mask] = best_neighbor
                if best_neighbor in features:
                    old_area = features[best_neighbor]["area"]
                    new_area = old_area + area
                    old_mean = features[best_neighbor]["mean_lab"]
                    features[best_neighbor]["mean_lab"] = (
                        old_mean * old_area + mean_lab * area
                    ) / new_area
                    features[best_neighbor]["area"] = new_area
        unique_ids = np.unique(merged)
        remap = np.zeros(int(unique_ids.max()) + 1, dtype=merged.dtype)
        for new_id, old_id in enumerate(unique_ids, start=1):
            remap[old_id] = new_id
        merged = remap[merged]
        self.segments = merged
        return self.segments

    def merge_by_color_similarity(self, base_threshold=5.0, adaptive=True,
                                  sensitivity=1.0):
        if self.segments is None:
            return self.segments

        lab_image = rgb2lab(self.image_float)
        features = self._compute_segment_features()

        seg_ids = list(features.keys())
        mean_lab = {sid: features[sid]["mean_lab"] for sid in seg_ids}
        area = {sid: features[sid]["area"] for sid in seg_ids}
        total_var = {sid: features[sid]["total_var"] for sid in seg_ids}

        if adaptive and len(seg_ids) > 0:
            vars_arr = np.array([total_var[sid] for sid in seg_ids])
            median_var = np.median(vars_arr) + 1e-6
        else:
            median_var = 1.0

        adj = self._find_adjacent_pairs()

        changed = True
        while changed:
            changed = False
            pairs = []
            for sid in list(mean_lab.keys()):
                if area[sid] == 0:
                    continue
                for nid in adj.get(sid, set()):
                    if nid not in mean_lab or area[nid] == 0:
                        continue
                    dist = np.linalg.norm(mean_lab[sid] - mean_lab[nid])
                    if adaptive:
                        var1 = total_var[sid] if sid in total_var else median_var
                        var2 = total_var[nid] if nid in total_var else median_var
                        var_factor = ((var1 + var2) / 2.0) / median_var
                        adaptive_thresh = base_threshold * (
                            1.0 + sensitivity * (var_factor - 1.0) * 0.5
                        )
                        adaptive_thresh = max(adaptive_thresh, base_threshold * 0.3)
                        adaptive_thresh = min(adaptive_thresh, base_threshold * 3.0)
                    else:
                        adaptive_thresh = base_threshold
                    if dist < adaptive_thresh:
                        pairs.append((dist, adaptive_thresh, sid, nid))
            if not pairs:
                break
            pairs.sort(key=lambda p: p[0])
            absorbed = set()
            for dist, thresh, sid, nid in pairs:
                if sid in absorbed or nid in absorbed:
                    continue
                if area[sid] == 0 or area[nid] == 0:
                    continue
                if area[sid] <= area[nid]:
                    small, big = sid, nid
                else:
                    small, big = nid, sid
                new_area = area[sid] + area[nid]
                new_mean = (mean_lab[sid] * area[sid] + mean_lab[nid] * area[nid]) / new_area
                new_var = (
                    (total_var[sid] * area[sid] + total_var[nid] * area[nid])
                    / new_area
                )
                self.segments[self.segments == small] = big
                mean_lab[big] = new_mean
                total_var[big] = new_var
                area[big] = new_area
                area[small] = 0
                del mean_lab[small]
                if small in total_var:
                    del total_var[small]
                adj[big].update(adj.get(small, set()) - {big, small})
                for k in adj:
                    adj[k].discard(small)
                absorbed.add(small)
                changed = True
        unique_ids = np.unique(self.segments)
        remap = np.zeros(int(unique_ids.max()) + 1, dtype=self.segments.dtype)
        for new_id, old_id in enumerate(unique_ids, start=1):
            remap[old_id] = new_id
        self.segments = remap[self.segments]
        return self.segments

    def get_segment_info(self):
        if self.segments is None:
            return {}
        regions = regionprops(self.segments)
        info = {}
        for region in regions:
            info[region.label] = {
                "area": region.area,
                "centroid": region.centroid,
                "bbox": region.bbox,
            }
        return info


class SuperpixelClassifier:

    def __init__(self, method="knn", n_neighbors=5):
        self.method = method
        self.n_neighbors = n_neighbors
        self.model = None
        self.class_names = {}
        self.training_data = []
        self.training_labels = []

    def reset(self):
        self.training_data = []
        self.training_labels = []
        self.class_names = {}
        self.model = None

    def extract_features(self, image, segments, seg_id):
        lab = rgb2lab(img_as_float(image))
        mask = segments == seg_id
        if mask.sum() == 0:
            return None
        mean_lab = lab[mask].mean(axis=0)
        var_lab = lab[mask].var(axis=0)
        hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV).astype(np.float64) / 255.0
        mean_hsv = hsv[mask].mean(axis=0)
        var_hsv = hsv[mask].var(axis=0)
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY).astype(np.float64) / 255.0
        sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobel_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        grad_mag = np.sqrt(sobel_x ** 2 + sobel_y ** 2)
        mean_grad = grad_mag[mask].mean()
        var_grad = grad_mag[mask].var()
        area = float(mask.sum())
        ys, xs = np.where(mask)
        y_min, y_max = ys.min(), ys.max()
        x_min, x_max = xs.min(), xs.max()
        aspect = (x_max - x_min) / (y_max - y_min + 1e-6)
        extent = area / ((y_max - y_min + 1) * (x_max - x_min + 1) + 1e-6)
        feature = np.concatenate([
            mean_lab, var_lab,
            mean_hsv, var_hsv,
            [mean_grad, var_grad, area, aspect, extent]
        ])
        return feature

    def add_training_sample(self, image, segments, seg_id, class_label, class_name=None):
        feat = self.extract_features(image, segments, seg_id)
        if feat is None:
            return False
        self.training_data.append(feat)
        self.training_labels.append(class_label)
        if class_name is not None:
            self.class_names[class_label] = class_name
        return True

    def train(self):
        if len(self.training_data) < 2:
            return False
        try:
            from sklearn.neighbors import KNeighborsClassifier
        except ImportError:
            self.model = None
            return False
        n = len(self.training_data)
        effective_neighbors = min(self.n_neighbors, n - 1, 5)
        effective_neighbors = max(effective_neighbors, 1)
        self.model = KNeighborsClassifier(n_neighbors=effective_neighbors)
        self.model.fit(np.array(self.training_data), np.array(self.training_labels))
        return True

    def predict(self, image, segments):
        if self.model is None or len(self.training_data) < 2:
            return None
        predictions = {}
        seg_ids = np.unique(segments)
        for sid in seg_ids:
            feat = self.extract_features(image, segments, sid)
            if feat is not None:
                pred = self.model.predict(feat.reshape(1, -1))[0]
                prob = self.model.predict_proba(feat.reshape(1, -1)).max()
                predictions[sid] = (int(pred), float(prob))
        return predictions

    def classify_image(self, image, segments):
        predictions = self.predict(image, segments)
        if predictions is None:
            return None
        result = np.zeros((image.shape[0], image.shape[1], 3), dtype=np.uint8)
        rng = np.random.RandomState(7)
        class_colors = {}
        for label in self.class_names:
            class_colors[label] = rng.randint(80, 256, 3)
        for sid, (label, prob) in predictions.items():
            mask = segments == sid
            color = class_colors.get(label, [128, 128, 128])
            result[mask] = color
        return result, predictions
