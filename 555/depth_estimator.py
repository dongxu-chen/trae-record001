import torch
import numpy as np
import cv2


MIDAS_MODELS = {
    "MiDaS_small": "MiDaS_small",
    "DPT_Hybrid": "DPT_Hybrid",
    "DPT_Large": "DPT_Large",
}


class MiDaSDepthEstimator:
    def __init__(self, model_type="DPT_Hybrid", device=None):
        if device is None:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)

        self.model_type = model_type
        self.model = None
        self.transform = None
        self._load_model()

    def _load_model(self):
        model_name = MIDAS_MODELS.get(self.model_type, "DPT_Hybrid")
        self.model = torch.hub.load("intel-isl/MiDaS", model_name, trust_repo=True)
        self.model.to(self.device)
        self.model.eval()

        midas_transforms = torch.hub.load("intel-isl/MiDaS", "transforms", trust_repo=True)
        if self.model_type in ("DPT_Hybrid", "DPT_Large"):
            self.transform = midas_transforms.dpt_transform
        else:
            self.transform = midas_transforms.small_transform

    def estimate(self, image_bgr):
        if image_bgr is None or image_bgr.size == 0:
            return None

        image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        input_batch = self.transform(image_rgb).to(self.device)

        with torch.no_grad():
            prediction = self.model(input_batch)
            prediction = torch.nn.functional.interpolate(
                prediction.unsqueeze(1),
                size=image_bgr.shape[:2],
                mode="bicubic",
                align_corners=False,
            ).squeeze()

        depth_map = prediction.cpu().numpy()
        depth_map = self._normalize_depth(depth_map)
        return depth_map

    def estimate_batch(self, images_bgr):
        results = []
        for img in images_bgr:
            depth = self.estimate(img)
            results.append(depth)
        return results

    @staticmethod
    def _normalize_depth(depth):
        depth_min = depth.min()
        depth_max = depth.max()
        if depth_max - depth_min > 1e-6:
            depth = (depth - depth_min) / (depth_max - depth_min)
        else:
            depth = np.zeros_like(depth)
        return depth.astype(np.float32)

    def get_device_name(self):
        return str(self.device)
