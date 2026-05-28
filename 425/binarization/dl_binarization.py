import os
import numpy as np
import cv2
from typing import Dict, Tuple, List, Optional
from skimage.filters import threshold_sauvola
from .core import binarize_pipeline


try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


try:
    import onnxruntime as ort
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False


DBNET_AVAILABLE = TORCH_AVAILABLE or ONNX_AVAILABLE


class DBNetTraditional:
    def __init__(
        self,
        shrink_ratio: float = 0.4,
        threshold: float = 0.3,
        adaptive: bool = True,
    ):
        self.shrink_ratio = shrink_ratio
        self.threshold = threshold
        self.adaptive = adaptive

    def __call__(self, image: np.ndarray) -> np.ndarray:
        if image.ndim == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        h, w = gray.shape

        if self.adaptive:
            window_size = min(h, w) // 20
            if window_size % 2 == 0:
                window_size += 1
            if window_size < 15:
                window_size = 15

            prob_map = threshold_sauvola(gray, window_size=window_size, k=0.2, r=128.0)
            prob_map = (gray > prob_map).astype(np.float32)
        else:
            _, prob_map = (gray > 128).astype(np.float32)

        if self.shrink_ratio < 1.0:
            kernel_size = max(3, int(5 * (1.0 - self.shrink_ratio)))
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_size, kernel_size))
            shrunk = cv2.erode((prob_map * 255).astype(np.uint8), kernel, iterations=1)
            prob_map = shrunk.astype(np.float32) / 255.0

        binary = (prob_map > self.threshold).astype(np.uint8) * 255

        return binary, prob_map


class DBNetPostprocessor:
    def __init__(self, threshold: float = 0.3, box_thresh: float = 0.5):
        self.threshold = threshold
        self.box_thresh = box_thresh

    def __call__(self, prob_map: np.ndarray, thresh_map: Optional[np.ndarray] = None) -> np.ndarray:
        if thresh_map is not None:
            prob_map = np.where(thresh_map > self.threshold, 1.0, prob_map)

        binary = (prob_map > self.threshold).astype(np.uint8) * 255

        return binary


def dbnet_binarize(
    image: np.ndarray,
    model_path: Optional[str] = None,
    device: str = "cpu",
    use_traditional_fallback: bool = True,
) -> Tuple[np.ndarray, np.ndarray]:
    if not DBNET_AVAILABLE and not use_traditional_fallback:
        raise ImportError(
            "DBNet requires PyTorch or ONNX Runtime. "
            "Install with: pip install torch onnxruntime"
        )

    if image.ndim == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()

    prob_map = None
    thresh_map = None

    if TORCH_AVAILABLE and model_path and os.path.exists(model_path):
        try:
            model = _load_torch_model(model_path, device)
            prob_map, thresh_map = _infer_torch(model, image, device)
        except Exception as e:
            print(f"PyTorch inference failed: {e}")
            if use_traditional_fallback:
                dbnet = DBNetTraditional()
                _, prob_map = dbnet(image)
    elif ONNX_AVAILABLE and model_path and os.path.exists(model_path):
        try:
            prob_map, thresh_map = _infer_onnx(model_path, image)
        except Exception as e:
            print(f"ONNX inference failed: {e}")
            if use_traditional_fallback:
                dbnet = DBNetTraditional()
                _, prob_map = dbnet(image)
    else:
        if use_traditional_fallback:
            dbnet = DBNetTraditional()
            binary, prob_map = dbnet(image)
            thresh_map = None
        else:
            raise ValueError(
                "No model available. Provide a valid model_path or enable use_traditional_fallback"
            )

    postprocessor = DBNetPostprocessor()
    binary = postprocessor(prob_map, thresh_map)

    return binary, prob_map


def _load_torch_model(model_path: str, device: str = "cpu"):
    if not TORCH_AVAILABLE:
        raise ImportError("PyTorch is not available")

    state_dict = torch.load(model_path, map_location=device)

    from collections import OrderedDict
    new_state_dict = OrderedDict()
    for k, v in state_dict.items():
        name = k[7:] if k.startswith('module.') else k
        new_state_dict[k] = v

    model = _build_dbnet_model()
    model.load_state_dict(new_state_dict)
    model.to(device)
    model.eval()
    return model


def _build_dbnet_model():
    class SimpleDBNet(nn.Module):
        def __init__(self):
            super().__init__()
            self.backbone = nn.Sequential(
                nn.Conv2d(3, 64, 3, 2, 1),
                nn.ReLU(inplace=True),
                nn.Conv2d(64, 128, 3, 2, 1),
                nn.ReLU(inplace=True),
                nn.Conv2d(128, 256, 3, 1, 1),
                nn.ReLU(inplace=True),
            )
            self.head = nn.Sequential(
                nn.Conv2d(256, 64, 3, 1, 1),
                nn.ReLU(inplace=True),
                nn.Conv2d(64, 2, 3, 1, 1),
                nn.Sigmoid(),
            )

        def forward(self, x):
            features = self.backbone(x)
            out = self.head(features)
            out = F.interpolate(out, size=x.shape[2:], mode='bilinear', align_corners=True)
            return out[:, 0, :, :], out[:, 1, :, :]

    return SimpleDBNet()


def _infer_torch(model, image: np.ndarray, device: str) -> Tuple[np.ndarray, np.ndarray]:
    h, w = image.shape[:2]

    if image.ndim == 3:
        img_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    else:
        img_rgb = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)

    img_tensor = torch.from_numpy(img_rgb).float().permute(2, 0, 1).unsqueeze(0) / 255.0
    img_tensor = img_tensor.to(device)

    with torch.no_grad():
        prob_map, thresh_map = model(img_tensor)

    prob_map = prob_map.squeeze().cpu().numpy()
    thresh_map = thresh_map.squeeze().cpu().numpy()

    return prob_map, thresh_map


def _infer_onnx(model_path: str, image: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    session = ort.InferenceSession(model_path)

    if image.ndim == 3:
        img_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    else:
        img_rgb = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)

    input_name = session.get_inputs()[0].name
    input_shape = session.get_inputs()[0].shape

    h, w = image.shape[:2]
    img_input = img_rgb.transpose(2, 0, 1).astype(np.float32) / 255.0
    img_input = np.expand_dims(img_input, axis=0)

    outputs = session.run(None, {input_name: img_input})

    prob_map = outputs[0][0, 0]
    thresh_map = outputs[0][0, 1] if len(outputs[0].shape) > 1 and outputs[0].shape[1] > 1 else None

    return prob_map, thresh_map


def fuse_binarization_results(
    image: np.ndarray,
    traditional_binary: np.ndarray,
    dl_prob_map: Optional[np.ndarray] = None,
    fusion_method: str = "weighted",
    weights: Dict[str, float] = None,
) -> np.ndarray:
    if dl_prob_map is None:
        return traditional_binary

    h, w = traditional_binary.shape[:2]

    traditional_float = traditional_binary.astype(np.float32) / 255.0

    if dl_prob_map.shape[:2] != (h, w):
        dl_prob_map = cv2.resize(dl_prob_map, (w, h), interpolation=cv2.INTER_LINEAR)

    dl_binary = (dl_prob_map > 0.5).astype(np.float32)

    if weights is None:
        weights = {"traditional": 0.5, "dl": 0.5}

    if fusion_method == "weighted":
        fused = (
            weights["traditional"] * traditional_float + weights["dl"] * dl_binary)
        fused_binary = (fused > 0.5).astype(np.uint8) * 255

    elif fusion_method == "intersection":
        fused_binary = cv2.bitwise_and(traditional_binary, (dl_binary * 255).astype(np.uint8))

    elif fusion_method == "union":
        fused_binary = cv2.bitwise_or(traditional_binary, (dl_binary * 255).astype(np.uint8))

    elif fusion_method == "dl_with_traditional_refine":
        refined = dl_binary.copy()
        mask = traditional_float > 0.5
        refined[mask] = 1.0
        fused_binary = (refined > 0.5).astype(np.uint8) * 255

    elif fusion_method == "traditional_with_dl_refine":
        refined = traditional_float.copy()
        dl_mask = dl_binary > 0.5
        refined[dl_mask] = 1.0
        fused_binary = (refined > 0.5).astype(np.uint8) * 255

    elif fusion_method == "confidence_based":
        dl_conf = dl_prob_map.copy()
        high_conf = dl_conf > 0.7
        low_conf = dl_conf < 0.3
        fused = np.where(high_conf, dl_binary, traditional_float)
        fused = np.where(low_conf, traditional_float, fused)
        fused_binary = (fused > 0.5).astype(np.uint8) * 255

    else:
        fused_binary = traditional_binary

    return fused_binary


class BinarizationFusion:
    def __init__(
        self,
        methods: List[str] = None,
        fusion_method: str = "weighted",
        weights: Dict[str, float] = None,
        dl_model_path: Optional[str] = None,
    ):
        self.methods = methods or ["sauvola", "dbnet"]
        self.fusion_method = fusion_method
        self.weights = weights or {"sauvola": 0.4, "niblack": 0.3, "dbnet": 0.3}
        self.dl_model_path = dl_model_path

    def __call__(self, image: np.ndarray, **kwargs) -> np.ndarray:
        results = {}
        prob_maps = {}

        for method in self.methods:
            if method == "dbnet":
                binary, prob = dbnet_binarize(image, model_path=self.dl_model_path)
                results[method] = binary
                prob_maps[method] = prob
            else:
                binary = binarize_pipeline(image, method=method, **kwargs)
                results[method] = binary
                prob_maps[method] = binary.astype(np.float32) / 255.0

        if len(results) == 0:
            raise ValueError("No binarization results to fuse")

        if len(results) == 1:
            return list(results.values())[0]

        fused = self._fuse_multiple(results, prob_maps)
        return fused

    def _fuse_multiple(
        self,
        results: Dict[str, np.ndarray],
        prob_maps: Dict[str, np.ndarray],
    ) -> np.ndarray:
        h, w = list(results.values())[0].shape[:2]

        if self.fusion_method == "majority_vote":
            stacked = np.stack([r / 255 for r in results.values()], axis=0)
            vote = np.sum(stacked, axis=0)
            threshold = len(results) // 2 + 1
            return (vote >= threshold).astype(np.uint8) * 255

        elif self.fusion_method == "weighted":
            weighted_sum = np.zeros((h, w), dtype=np.float32)
            total_weight = 0.0
            for name, binary in results.items():
                weight = self.weights.get(name, 1.0)
                weighted_sum += weight * (binary.astype(np.float32) / 255.0)
                total_weight += weight
            weighted_sum /= total_weight
            return (weighted_sum > 0.5).astype(np.uint8) * 255

        elif self.fusion_method == "intersection":
            result = None
            for binary in results.values():
                if result is None:
                    result = binary.copy()
                else:
                    result = cv2.bitwise_and(result, binary)
            return result

        elif self.fusion_method == "union":
            result = None
            for binary in results.values():
                if result is None:
                    result = binary.copy()
                else:
                    result = cv2.bitwise_or(result, binary)
            return result

        else:
            return list(results.values())[0]


def binarize_with_fusion(
    image: np.ndarray,
    noise_detection_result: Dict,
    use_dl: bool = False,
    dl_model_path: Optional[str] = None,
    fusion_method: str = "weighted",
) -> np.ndarray:
    recommended_method = noise_detection_result.get("recommended_method", "sauvola")
    recommended_params = noise_detection_result.get("recommended_params", {})

    if not use_dl or (not DBNET_AVAILABLE and dl_model_path is None):
        return binarize_pipeline(image, method=recommended_method, **recommended_params)

    noise_scores = noise_detection_result.get("noise_scores", {})
    primary_noise = noise_detection_result.get("primary_noise", "clean")

    methods_to_fuse = [recommended_method]

    if primary_noise in ["illumination_uneven", "gaussian"]:
        methods_to_fuse.append("niblack")
        if noise_scores.get("salt_pepper", 0) > 0.3:
            methods_to_fuse.append("adaptive")

    if primary_noise == "clean":
        methods_to_fuse = ["otsu", "sauvola"]

    methods_to_fuse = list(set(methods_to_fuse))
    if len(methods_to_fuse) == 1:
        methods_to_fuse.append("sauvola")

    if use_dl and DBNET_AVAILABLE:
        methods_to_fuse.append("dbnet")

    weights = {}
    for i, method in enumerate(methods_to_fuse):
        if method == recommended_method:
            weights[method] = 0.5
        elif method == "dbnet":
            weights[method] = 0.3
        else:
            weights[method] = 0.2

    total = BinarizationFusion(
        methods=methods_to_fuse,
        fusion_method=fusion_method,
        weights=weights,
        dl_model_path=dl_model_path,
    )

    return total(image, **recommended_params)