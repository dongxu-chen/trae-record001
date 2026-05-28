import os
from collections import deque
import torch
import torch.nn as nn
import numpy as np
import cv2
from typing import Optional, Tuple, Dict, List

try:
    import tensorrt as trt
    TENSORRT_AVAILABLE = True
except ImportError:
    TENSORRT_AVAILABLE = False


class ResidualBlock(nn.Module):
    def __init__(self, channels: int):
        super().__init__()
        self.conv1 = nn.Conv2d(channels, channels, kernel_size=3, padding=1)
        self.bn1 = nn.BatchNorm2d(channels)
        self.relu = nn.ReLU(inplace=True)
        self.conv2 = nn.Conv2d(channels, channels, kernel_size=3, padding=1)
        self.bn2 = nn.BatchNorm2d(channels)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        residual = x
        out = self.relu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        return out + residual


class TransformerNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv1 = nn.Conv2d(3, 32, kernel_size=9, padding=4)
        self.bn1 = nn.BatchNorm2d(32)
        self.conv2 = nn.Conv2d(32, 64, kernel_size=3, stride=2, padding=1)
        self.bn2 = nn.BatchNorm2d(64)
        self.conv3 = nn.Conv2d(64, 128, kernel_size=3, stride=2, padding=1)
        self.bn3 = nn.BatchNorm2d(128)

        self.res1 = ResidualBlock(128)
        self.res2 = ResidualBlock(128)
        self.res3 = ResidualBlock(128)
        self.res4 = ResidualBlock(128)
        self.res5 = ResidualBlock(128)

        self.deconv1 = nn.ConvTranspose2d(128, 64, kernel_size=3, stride=2, padding=1, output_padding=1)
        self.bn4 = nn.BatchNorm2d(64)
        self.deconv2 = nn.ConvTranspose2d(64, 32, kernel_size=3, stride=2, padding=1, output_padding=1)
        self.bn5 = nn.BatchNorm2d(32)
        self.deconv3 = nn.Conv2d(32, 3, kernel_size=9, padding=4)

        self.relu = nn.ReLU(inplace=True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.relu(self.bn1(self.conv1(x)))
        x = self.relu(self.bn2(self.conv2(x)))
        x = self.relu(self.bn3(self.conv3(x)))
        x = self.res1(x)
        x = self.res2(x)
        x = self.res3(x)
        x = self.res4(x)
        x = self.res5(x)
        x = self.relu(self.bn4(self.deconv1(x)))
        x = self.relu(self.bn5(self.deconv2(x)))
        return torch.tanh(self.deconv3(x))


class TileProcessor:
    def __init__(self, tile_size: int = 512, overlap: int = 64):
        self.tile_size = tile_size
        self.overlap = overlap

    def split_image(self, image: np.ndarray) -> Tuple[List[np.ndarray], List[Tuple[int, int, int, int]], Tuple[int, int]]:
        h, w = image.shape[:2]
        tiles = []
        positions = []

        step = self.tile_size - self.overlap

        y = 0
        while y < h:
            x = 0
            while x < w:
                y1 = y
                y2 = min(y + self.tile_size, h)
                x1 = x
                x2 = min(x + self.tile_size, w)

                tile = image[y1:y2, x1:x2]

                if tile.shape[0] < self.tile_size or tile.shape[1] < self.tile_size:
                    pad_h = self.tile_size - tile.shape[0] if tile.shape[0] < self.tile_size else 0
                    pad_w = self.tile_size - tile.shape[1] if tile.shape[1] < self.tile_size else 0
                    tile = cv2.copyMakeBorder(tile, 0, pad_h, 0, pad_w, cv2.BORDER_REFLECT)

                tiles.append(tile)
                positions.append((y1, y2, x1, x2))

                x += step
                if x >= w:
                    break
            y += step
            if y >= h:
                break

        return tiles, positions, (h, w)

    def merge_tiles(self, tiles: List[np.ndarray], positions: List[Tuple[int, int, int, int]],
                    original_size: Tuple[int, int]) -> np.ndarray:
        h, w = original_size
        result = np.zeros((h, w, 3), dtype=np.float32)
        weight = np.zeros((h, w, 3), dtype=np.float32)

        for tile, (y1, y2, x1, x2) in zip(tiles, positions):
            tile_h = y2 - y1
            tile_w = x2 - x1
            tile_cropped = tile[:tile_h, :tile_w]

            blend_mask = self._create_blend_mask(tile_h, tile_w, (y1, y2, x1, x2), (h, w))
            blend_mask_3d = np.stack([blend_mask] * 3, axis=-1)

            result[y1:y2, x1:x2] += tile_cropped.astype(np.float32) * blend_mask_3d
            weight[y1:y2, x1:x2] += blend_mask_3d

        weight = np.maximum(weight, 1e-6)
        result = result / weight
        return np.clip(result, 0, 255).astype(np.uint8)

    def _create_blend_mask(self, h: int, w: int, position: Tuple[int, int, int, int],
                           image_size: Tuple[int, int]) -> np.ndarray:
        y1, y2, x1, x2 = position
        img_h, img_w = image_size

        mask = np.ones((h, w), dtype=np.float32)

        if self.overlap > 0:
            fade = np.linspace(0, 1, self.overlap)

            if y1 > 0:
                top_fade = np.minimum(np.arange(h) / self.overlap, 1)
                mask *= top_fade[:, np.newaxis]

            if y2 < img_h:
                bottom_fade = np.minimum((h - np.arange(h) - 1) / self.overlap, 1)
                mask *= bottom_fade[:, np.newaxis]

            if x1 > 0:
                left_fade = np.minimum(np.arange(w) / self.overlap, 1)
                mask *= left_fade[np.newaxis, :]

            if x2 < img_w:
                right_fade = np.minimum((w - np.arange(w) - 1) / self.overlap, 1)
                mask *= right_fade[np.newaxis, :]

        return mask


class StyleTransferModel:
    def __init__(self, use_gpu: bool = True, use_tensorrt: bool = False,
                 use_tiling: bool = True, tile_size: int = 512, overlap: int = 64):
        self.use_gpu = use_gpu and torch.cuda.is_available()
        self.use_tensorrt = use_tensorrt and TENSORRT_AVAILABLE and self.use_gpu
        self.device = torch.device("cuda" if self.use_gpu else "cpu")
        self.model: Optional[nn.Module] = None
        self.current_style: Optional[str] = None
        self.trt_engine = None
        self.trt_context = None
        self.trt_inputs = []
        self.trt_outputs = []
        self.trt_bindings = []
        self.trt_stream = None

        self.use_tiling = use_tiling
        self.tile_processor = TileProcessor(tile_size=tile_size, overlap=overlap)

        print(f"Device: {self.device}")
        print(f"TensorRT available: {TENSORRT_AVAILABLE}, enabled: {self.use_tensorrt}")
        print(f"Tiling: {'enabled' if use_tiling else 'disabled'}, tile_size={tile_size}, overlap={overlap}")

    def load_model(self, model_path: str, style_name: str) -> bool:
        try:
            if not os.path.exists(model_path):
                print(f"Model file not found: {model_path}")
                return False

            self.model = TransformerNet()
            state_dict = torch.load(model_path, map_location=self.device)

            new_state_dict = {}
            for k, v in state_dict.items():
                if k.startswith('module.'):
                    k = k[7:]
                new_state_dict[k] = v

            self.model.load_state_dict(new_state_dict)
            self.model.eval()
            self.model.to(self.device)

            if self.use_tensorrt:
                trt_engine_path = os.path.splitext(model_path)[0] + ".trt"
                if os.path.exists(trt_engine_path):
                    print(f"Loading pre-built TensorRT engine: {trt_engine_path}")
                    self._load_tensorrt_engine(trt_engine_path)
                else:
                    print(f"TensorRT engine not found: {trt_engine_path}")
                    print("Run 'python build_tensorrt.py' to pre-build engine, falling back to PyTorch")
                    self.use_tensorrt = False

            self.current_style = style_name
            print(f"Loaded style: {style_name}")
            return True
        except Exception as e:
            print(f"Error loading model: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _load_tensorrt_engine(self, engine_path: str):
        if not TENSORRT_AVAILABLE:
            return False

        try:
            import pycuda.driver as cuda
            import pycuda.autoinit

            logger = trt.Logger(trt.Logger.WARNING)
            runtime = trt.Runtime(logger)

            with open(engine_path, "rb") as f:
                engine_data = f.read()
            self.trt_engine = runtime.deserialize_cuda_engine(engine_data)

            if self.trt_engine is None:
                raise RuntimeError("Failed to deserialize TensorRT engine")

            self.trt_context = self.trt_engine.create_execution_context()

            self.trt_inputs = []
            self.trt_outputs = []
            self.trt_bindings = []
            self.trt_stream = cuda.Stream()

            for binding in self.trt_engine:
                size = trt.volume(self.trt_engine.get_binding_shape(binding)) * self.trt_engine.max_batch_size
                dtype = trt.nptype(self.trt_engine.get_binding_dtype(binding))
                host_mem = cuda.pagelocked_empty(size, dtype)
                device_mem = cuda.mem_alloc(host_mem.nbytes)
                self.trt_bindings.append(int(device_mem))
                if self.trt_engine.binding_is_input(binding):
                    self.trt_inputs.append({'host': host_mem, 'device': device_mem})
                else:
                    self.trt_outputs.append({'host': host_mem, 'device': device_mem})

            print("TensorRT engine loaded successfully")
            return True
        except Exception as e:
            print(f"TensorRT engine loading failed: {e}")
            self.trt_engine = None
            self.trt_context = None
            self.use_tensorrt = False
            return False

    def preprocess(self, image: np.ndarray) -> torch.Tensor:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        image = image.astype(np.float32) / 255.0
        image = image.transpose(2, 0, 1)
        image = torch.from_numpy(image).unsqueeze(0)
        return image.to(self.device)

    def postprocess(self, tensor: torch.Tensor) -> np.ndarray:
        tensor = tensor.detach().cpu()
        tensor = tensor.squeeze(0).clamp(0, 1)
        image = tensor.numpy().transpose(1, 2, 0)
        image = (image * 255).astype(np.uint8)
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        return image

    def stylize(self, image: np.ndarray, strength: float = 1.0,
                target_size: Optional[Tuple[int, int]] = None) -> np.ndarray:
        if self.model is None:
            return image

        original_h, original_w = image.shape[:2]

        if target_size is not None:
            image = cv2.resize(image, (target_size[1], target_size[0]))

        if self.use_tiling and (image.shape[0] > self.tile_processor.tile_size or
                                image.shape[1] > self.tile_processor.tile_size):
            stylized = self._stylize_tiled(image)
        else:
            input_tensor = self.preprocess(image)
            with torch.no_grad():
                if self.use_tensorrt and self.trt_engine is not None:
                    output = self._infer_tensorrt(input_tensor)
                else:
                    output = self.model(input_tensor)
            stylized = self.postprocess(output)

        if strength < 1.0:
            stylized = cv2.addWeighted(image, 1 - strength, stylized, strength, 0)

        if target_size is not None:
            stylized = cv2.resize(stylized, (original_w, original_h))

        return stylized

    def _stylize_tiled(self, image: np.ndarray) -> np.ndarray:
        tiles, positions, original_size = self.tile_processor.split_image(image)

        stylized_tiles = []
        for tile in tiles:
            input_tensor = self.preprocess(tile)
            with torch.no_grad():
                if self.use_tensorrt and self.trt_engine is not None:
                    output = self._infer_tensorrt(input_tensor)
                else:
                    output = self.model(input_tensor)
            stylized_tile = self.postprocess(output)
            stylized_tiles.append(stylized_tile)

        return self.tile_processor.merge_tiles(stylized_tiles, positions, original_size)

    def _infer_tensorrt(self, input_tensor: torch.Tensor) -> torch.Tensor:
        import pycuda.driver as cuda

        input_np = input_tensor.detach().cpu().numpy()
        np.copyto(self.trt_inputs[0]['host'], input_np.ravel())

        cuda.memcpy_htod_async(
            self.trt_inputs[0]['device'], self.trt_inputs[0]['host'], self.trt_stream)

        self.trt_context.execute_async_v2(
            bindings=self.trt_bindings, stream_handle=self.trt_stream.handle)

        cuda.memcpy_dtoh_async(
            self.trt_outputs[0]['host'], self.trt_outputs[0]['device'], self.trt_stream)

        self.trt_stream.synchronize()

        output_shape = input_tensor.shape
        output_np = self.trt_outputs[0]['host'].reshape(output_shape)
        return torch.from_numpy(output_np).to(self.device)

    def get_available_styles(self, models_dir: str) -> Dict[str, str]:
        styles = {}
        if not os.path.exists(models_dir):
            return styles

        for filename in os.listdir(models_dir):
            if filename.endswith('.pth') or filename.endswith('.pt'):
                style_name = os.path.splitext(filename)[0]
                styles[style_name] = os.path.join(models_dir, filename)
        return styles

    def unload(self):
        self.model = None
        self.current_style = None
        self.trt_engine = None
        self.trt_context = None
        self.trt_inputs = []
        self.trt_outputs = []
        self.trt_bindings = []
        self.trt_stream = None
        if self.use_gpu:
            torch.cuda.empty_cache()


class ContentComplexityAnalyzer:
    def __init__(self, edge_threshold: float = 50.0, texture_threshold: float = 30.0):
        self.edge_threshold = edge_threshold
        self.texture_threshold = texture_threshold
        self.complexity_history = deque(maxlen=30)
        self.smoothing_factor = 0.2

    def analyze(self, image: np.ndarray) -> Dict[str, float]:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges > 0) / (edges.shape[0] * edges.shape[1])

        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        texture_variance = np.var(laplacian)

        hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
        hist = hist.flatten() / hist.sum()
        entropy = -np.sum(hist * np.log2(hist + 1e-10))

        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        color_diversity = np.std(hsv[:, :, 0])

        complexity_score = (
            edge_density * 0.35 +
            min(texture_variance / 1000.0, 1.0) * 0.25 +
            min(entropy / 8.0, 1.0) * 0.20 +
            min(color_diversity / 100.0, 1.0) * 0.20
        )

        result = {
            'edge_density': edge_density,
            'texture_variance': texture_variance,
            'entropy': entropy,
            'color_diversity': color_diversity,
            'complexity': complexity_score
        }

        self.complexity_history.append(complexity_score)

        return result

    def get_smoothed_complexity(self) -> float:
        if not self.complexity_history:
            return 0.5
        return sum(self.complexity_history) / len(self.complexity_history)

    def compute_auto_strength(self, base_strength: float = 0.8,
                               min_strength: float = 0.4,
                               max_strength: float = 1.0) -> float:
        complexity = self.get_smoothed_complexity()

        if complexity < 0.2:
            strength = max_strength
        elif complexity < 0.5:
            strength = base_strength + (max_strength - base_strength) * (0.5 - complexity) / 0.3
        elif complexity < 0.7:
            strength = base_strength
        else:
            strength = min_strength + (base_strength - min_strength) * (1.0 - complexity) / 0.3

        return max(min_strength, min(max_strength, strength))


class MultiStyleTransferModel:
    def __init__(self, use_gpu: bool = True, use_tensorrt: bool = False,
                 use_tiling: bool = True, tile_size: int = 512, overlap: int = 64):
        self.use_gpu = use_gpu and torch.cuda.is_available()
        self.use_tensorrt = use_tensorrt and TENSORRT_AVAILABLE and self.use_gpu
        self.device = torch.device("cuda" if self.use_gpu else "cpu")
        self.models: Dict[str, StyleTransferModel] = {}
        self.style_weights: Dict[str, float] = {}
        self.use_tiling = use_tiling
        self.tile_size = tile_size
        self.overlap = overlap
        self.complexity_analyzer = ContentComplexityAnalyzer()
        self.auto_strength = False
        self.base_strength = 0.8

    def add_style(self, model_path: str, style_name: str, weight: float = 0.5) -> bool:
        if style_name in self.models:
            self.style_weights[style_name] = weight
            return True

        model = StyleTransferModel(
            use_gpu=self.use_gpu,
            use_tensorrt=self.use_tensorrt,
            use_tiling=self.use_tiling,
            tile_size=self.tile_size,
            overlap=self.overlap
        )

        success = model.load_model(model_path, style_name)
        if success:
            self.models[style_name] = model
            self.style_weights[style_name] = weight
            print(f"Added style: {style_name} (weight={weight:.2f})")
            return True
        return False

    def remove_style(self, style_name: str) -> bool:
        if style_name in self.models:
            self.models[style_name].unload()
            del self.models[style_name]
            del self.style_weights[style_name]
            print(f"Removed style: {style_name}")
            return True
        return False

    def set_style_weight(self, style_name: str, weight: float):
        if style_name in self.style_weights:
            self.style_weights[style_name] = max(0.0, min(1.0, weight))

    def set_auto_strength(self, enabled: bool, base_strength: float = 0.8):
        self.auto_strength = enabled
        self.base_strength = base_strength

    def get_loaded_styles(self) -> List[str]:
        return list(self.models.keys())

    def stylize(self, image: np.ndarray, strength: float = 1.0,
                target_size: Optional[Tuple[int, int]] = None,
                segmentation_mask: Optional[np.ndarray] = None,
                bg_style_name: Optional[str] = None) -> np.ndarray:
        if not self.models:
            return image

        original_h, original_w = image.shape[:2]

        if target_size is not None:
            image = cv2.resize(image, (target_size[1], target_size[0]))

        if self.auto_strength:
            self.complexity_analyzer.analyze(image)
            auto_strength = self.complexity_analyzer.compute_auto_strength(
                base_strength=self.base_strength
            )
            strength = strength * auto_strength

        total_weight = sum(self.style_weights.values())
        if total_weight <= 0:
            total_weight = 1.0

        result = np.zeros_like(image, dtype=np.float32)

        for style_name, model in self.models.items():
            weight = self.style_weights[style_name] / total_weight
            if weight <= 0:
                continue

            stylized = model.stylize(image, strength=1.0, target_size=None)
            result += stylized.astype(np.float32) * weight

        result = np.clip(result, 0, 255).astype(np.uint8)

        if segmentation_mask is not None and bg_style_name is not None and bg_style_name in self.models:
            fg_mask = segmentation_mask.astype(np.float32)
            if fg_mask.max() > 1.0:
                fg_mask = fg_mask / 255.0

            bg_model = self.models[bg_style_name]
            bg_stylized = bg_model.stylize(image, strength=1.0, target_size=None)

            fg_mask_3d = np.stack([fg_mask] * 3, axis=-1)
            result = (result.astype(np.float32) * fg_mask_3d +
                     bg_stylized.astype(np.float32) * (1 - fg_mask_3d))
            result = np.clip(result, 0, 255).astype(np.uint8)

        if strength < 1.0:
            result = cv2.addWeighted(image, 1 - strength, result, strength, 0)

        if target_size is not None:
            result = cv2.resize(result, (original_w, original_h))

        return result

    def stylize_with_mask(self, image: np.ndarray,
                          fg_styles: Dict[str, float],
                          bg_styles: Dict[str, float],
                          segmentation_mask: np.ndarray,
                          strength: float = 1.0,
                          target_size: Optional[Tuple[int, int]] = None) -> np.ndarray:
        original_h, original_w = image.shape[:2]

        if target_size is not None:
            image = cv2.resize(image, (target_size[1], target_size[0]))

        fg_mask = segmentation_mask.astype(np.float32)
        if fg_mask.max() > 1.0:
            fg_mask = fg_mask / 255.0
        fg_mask_3d = np.stack([fg_mask] * 3, axis=-1)

        fg_result = np.zeros_like(image, dtype=np.float32)
        bg_result = np.zeros_like(image, dtype=np.float32)

        fg_total_weight = sum(fg_styles.values()) if fg_styles else 0
        bg_total_weight = sum(bg_styles.values()) if bg_styles else 0

        for style_name, weight in fg_styles.items():
            if style_name in self.models and weight > 0:
                stylized = self.models[style_name].stylize(image, strength=1.0)
                fg_result += stylized.astype(np.float32) * (weight / max(fg_total_weight, 0.001))

        for style_name, weight in bg_styles.items():
            if style_name in self.models and weight > 0:
                stylized = self.models[style_name].stylize(image, strength=1.0)
                bg_result += stylized.astype(np.float32) * (weight / max(bg_total_weight, 0.001))

        if fg_total_weight <= 0:
            fg_result = image.astype(np.float32)
        if bg_total_weight <= 0:
            bg_result = image.astype(np.float32)

        result = (fg_result * fg_mask_3d + bg_result * (1 - fg_mask_3d))
        result = np.clip(result, 0, 255).astype(np.uint8)

        if strength < 1.0:
            result = cv2.addWeighted(image, 1 - strength, result, strength, 0)

        if target_size is not None:
            result = cv2.resize(result, (original_w, original_h))

        return result

    def unload_all(self):
        for model in self.models.values():
            model.unload()
        self.models.clear()
        self.style_weights.clear()
        if self.use_gpu:
            torch.cuda.empty_cache()
