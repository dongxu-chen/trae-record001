import numpy as np
import cv2


class WeightController:
    def __init__(self, num_images=2):
        self.num_images = num_images
        self.weights = np.ones(num_images) / num_images
        self.blend_mode = "weighted_average"
        self.spatial_weights = None

    def set_weights(self, weights):
        if len(weights) != self.num_images:
            raise ValueError(f"Expected {self.num_images} weights, got {len(weights)}")
        total = sum(weights)
        if total <= 0:
            total = 1
        self.weights = np.array([w / total for w in weights])

    def set_num_images(self, num):
        self.num_images = num
        self.weights = np.ones(num) / num
        self.spatial_weights = None

    def get_weights(self):
        return self.weights.copy()

    def fuse_weighted_average(self, images):
        if not images:
            return None
        h, w = images[0].shape[:2]
        result = np.zeros((h, w, 3) if len(images[0].shape) == 3 else (h, w), dtype=np.float64)
        for img, weight in zip(images, self.weights):
            if img.shape[:2] != (h, w):
                img = cv2.resize(img, (w, h))
            result += img.astype(np.float64) * weight
        return np.clip(result, 0, 255).astype(np.uint8)

    def fuse_alpha_blend(self, img_a, img_b, alpha=0.5):
        if img_a.shape[:2] != img_b.shape[:2]:
            img_b = cv2.resize(img_b, (img_a.shape[1], img_a.shape[0]))
        result = img_a.astype(np.float64) * alpha + img_b.astype(np.float64) * (1 - alpha)
        return np.clip(result, 0, 255).astype(np.uint8)

    def fuse_spatial_weighted(self, images, spatial_weights=None):
        if not images:
            return None
        if spatial_weights is None:
            spatial_weights = self.spatial_weights
        if spatial_weights is None:
            return self.fuse_weighted_average(images)

        h, w = images[0].shape[:2]
        result = np.zeros((h, w, 3) if len(images[0].shape) == 3 else (h, w), dtype=np.float64)
        total_weight = np.zeros((h, w), dtype=np.float64)
        for img, sw in zip(images, spatial_weights):
            if img.shape[:2] != (h, w):
                img = cv2.resize(img, (w, h))
            if sw.shape[:2] != (h, w):
                sw = cv2.resize(sw, (w, h))
            sw_f = sw.astype(np.float64)
            if len(sw_f.shape) == 2 and len(result.shape) == 3:
                sw_f = np.stack([sw_f] * 3, axis=-1)
            result += img.astype(np.float64) * sw_f
            total_weight += sw_f if len(sw_f.shape) == 2 else sw_f[:, :, 0]
        total_weight = np.maximum(total_weight, 1e-10)
        if len(result.shape) == 3:
            result = result / total_weight[:, :, np.newaxis]
        else:
            result = result / total_weight
        return np.clip(result, 0, 255).astype(np.uint8)

    @staticmethod
    def create_center_focus_weight(h, w, sigma_ratio=0.3):
        y, x = np.mgrid[0:h, 0:w].astype(np.float64)
        cx, cy = w / 2.0, h / 2.0
        sigma_x = w * sigma_ratio
        sigma_y = h * sigma_ratio
        weight = np.exp(-((x - cx) ** 2 / (2 * sigma_x ** 2) + (y - cy) ** 2 / (2 * sigma_y ** 2)))
        return weight

    @staticmethod
    def create_gradient_weight(h, w, direction="left_to_right"):
        if direction == "left_to_right":
            weight = np.linspace(0, 1, w).reshape(1, -1).repeat(h, axis=0)
        elif direction == "right_to_left":
            weight = np.linspace(1, 0, w).reshape(1, -1).repeat(h, axis=0)
        elif direction == "top_to_bottom":
            weight = np.linspace(0, 1, h).reshape(-1, 1).repeat(w, axis=1)
        elif direction == "bottom_to_top":
            weight = np.linspace(1, 0, h).reshape(-1, 1).repeat(w, axis=1)
        elif direction == "radial":
            weight = WeightController.create_center_focus_weight(h, w)
        else:
            weight = np.ones((h, w), dtype=np.float64) * 0.5
        return weight

    @staticmethod
    def create_depth_based_weight(h, w, focus_map, focus_threshold=128):
        if focus_map.shape[:2] != (h, w):
            focus_map = cv2.resize(focus_map, (w, h))
        if len(focus_map.shape) == 3:
            focus_map = cv2.cvtColor(focus_map, cv2.COLOR_BGR2GRAY)
        focus_map = focus_map.astype(np.float64)
        focus_map = cv2.GaussianBlur(focus_map, (11, 11), 0)
        if focus_map.max() > 1:
            focus_map = focus_map / 255.0
        return focus_map

    def fuse(self, images, **kwargs):
        if self.blend_mode == "weighted_average":
            return self.fuse_weighted_average(images)
        elif self.blend_mode == "alpha_blend":
            if len(images) == 2:
                return self.fuse_alpha_blend(images[0], images[1], alpha=self.weights[0])
            return self.fuse_weighted_average(images)
        elif self.blend_mode == "spatial":
            return self.fuse_spatial_weighted(images, kwargs.get("spatial_weights"))
        else:
            return self.fuse_weighted_average(images)

    @staticmethod
    def get_available_blend_modes():
        return ["weighted_average", "alpha_blend", "spatial"]

    @staticmethod
    def get_available_gradient_directions():
        return ["left_to_right", "right_to_left", "top_to_bottom", "bottom_to_top", "radial"]
