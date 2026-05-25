import os
import numpy as np
import cv2
import torch
import torch.nn as nn
from typing import Optional, Tuple, Union
from config.config import ModelConfig


class MidasModel:
    def __init__(self, config: ModelConfig):
        self.config = config
        self.device = self._get_device()
        self.model = None
        self.transform = None
        self.onnx_session = None
        self.input_size = None
        self._load_model()

    def _get_device(self) -> torch.device:
        if self.config.device == "cuda" and torch.cuda.is_available():
            return torch.device("cuda")
        elif self.config.device == "mps" and torch.backends.mps.is_available():
            return torch.device("mps")
        else:
            return torch.device("cpu")

    def _load_model(self) -> None:
        if self.config.use_onnx:
            self._load_onnx_model()
        else:
            self._load_pytorch_model()

    def _load_pytorch_model(self) -> None:
        print(f"Loading MiDaS model ({self.config.model_type}) on {self.device}...")
        
        if self.config.model_path and os.path.exists(self.config.model_path):
            self.model = torch.load(self.config.model_path, map_location=self.device)
        else:
            self.model = torch.hub.load(
                "intel-isl/MiDaS",
                self.config.model_type,
                pretrained=True,
                verbose=False
            )
        
        self.model.to(self.device)
        self.model.eval()
        
        midas_transforms = torch.hub.load(
            "intel-isl/MiDaS",
            "transforms",
            verbose=False
        )
        
        if self.config.model_type in ["DPT_Large", "DPT_Hybrid"]:
            self.transform = midas_transforms.dpt_transform
        else:
            self.transform = midas_transforms.small_transform
        
        print(f"Model loaded successfully.")

    def _load_onnx_model(self) -> None:
        try:
            import onnxruntime as ort
        except ImportError:
            raise ImportError("onnxruntime is required for ONNX inference. "
                            "Install with: pip install onnxruntime")

        print(f"Loading ONNX model from {self.config.onnx_path}...")
        
        if self.config.onnx_path is None or not os.path.exists(self.config.onnx_path):
            raise FileNotFoundError(f"ONNX model not found at {self.config.onnx_path}")

        providers = ["CPUExecutionProvider"]
        if self.device.type == "cuda":
            providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]

        so = ort.SessionOptions()
        so.log_severity_level = 3
        
        self.onnx_session = ort.InferenceSession(
            self.config.onnx_path,
            sess_options=so,
            providers=providers
        )
        
        input_meta = self.onnx_session.get_inputs()[0]
        self.input_name = input_meta.name
        self.input_size = input_meta.shape[2:]
        
        print(f"ONNX model loaded successfully. Input size: {self.input_size}")

    def _preprocess(self, image: np.ndarray) -> Union[torch.Tensor, np.ndarray]:
        if self.config.use_onnx:
            return self._preprocess_onnx(image)
        else:
            return self._preprocess_pytorch(image)

    def _preprocess_pytorch(self, image: np.ndarray) -> torch.Tensor:
        img_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        input_batch = self.transform(img_rgb).to(self.device)
        
        if self.config.precision == "fp16" and self.device.type == "cuda":
            input_batch = input_batch.half()
            
        return input_batch

    def _preprocess_onnx(self, image: np.ndarray) -> np.ndarray:
        img_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        img = cv2.resize(img_rgb, (self.input_size[1], self.input_size[0]))
        img = img.astype(np.float32) / 255.0
        
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
        img = (img - mean) / std
        
        img = np.transpose(img, (2, 0, 1))
        img = np.expand_dims(img, axis=0)
        
        return img.astype(np.float32)

    @torch.no_grad()
    def predict(self, image: np.ndarray) -> np.ndarray:
        if image is None or image.size == 0:
            raise ValueError("Invalid input image")

        original_shape = image.shape[:2]
        input_data = self._preprocess(image)
        
        if self.config.use_onnx:
            depth_map = self._inference_onnx(input_data)
        else:
            depth_map = self._inference_pytorch(input_data)
        
        depth_map = self._resize_depth(depth_map, original_shape)
        return depth_map

    def _inference_pytorch(self, input_batch: torch.Tensor) -> np.ndarray:
        with torch.no_grad():
            prediction = self.model(input_batch)
            prediction = torch.nn.functional.interpolate(
                prediction.unsqueeze(1),
                size=input_batch.shape[2:],
                mode="bicubic",
                align_corners=False,
            ).squeeze()
        return prediction.cpu().numpy()

    def _inference_onnx(self, input_data: np.ndarray) -> np.ndarray:
        outputs = self.onnx_session.run(None, {self.input_name: input_data})
        depth_map = outputs[0][0]
        return depth_map

    def _resize_depth(self, depth_map: np.ndarray, target_shape: Tuple[int, int]) -> np.ndarray:
        if depth_map.shape != target_shape:
            depth_map = cv2.resize(
                depth_map,
                (target_shape[1], target_shape[0]),
                interpolation=cv2.INTER_CUBIC
            )
        return depth_map

    def export_to_onnx(self, output_path: str, opset_version: int = 17) -> None:
        if self.config.use_onnx or self.model is None:
            raise RuntimeError("Cannot export: model not loaded in PyTorch mode")

        print(f"Exporting model to ONNX format: {output_path}...")
        
        self.model.eval()
        dummy_input = torch.randn(1, 3, 384, 384).to(self.device)
        
        if self.config.precision == "fp16" and self.device.type == "cuda":
            dummy_input = dummy_input.half()
            self.model = self.model.half()

        dynamic_axes = {
            'input': {0: 'batch', 2: 'height', 3: 'width'},
            'output': {0: 'batch', 2: 'height', 3: 'width'}
        }

        torch.onnx.export(
            self.model,
            dummy_input,
            output_path,
            opset_version=opset_version,
            do_constant_folding=True,
            input_names=['input'],
            output_names=['output'],
            dynamic_axes=dynamic_axes,
            verbose=False
        )
        
        print(f"ONNX model exported successfully to {output_path}")

    def get_model_info(self) -> dict:
        return {
            "model_type": self.config.model_type,
            "backend": "ONNX" if self.config.use_onnx else "PyTorch",
            "device": str(self.device),
            "precision": self.config.precision,
            "input_size": self.input_size
        }

    def __del__(self):
        if hasattr(self, 'model') and self.model is not None:
            del self.model
        if hasattr(self, 'onnx_session') and self.onnx_session is not None:
            del self.onnx_session
        if self.device.type == "cuda":
            torch.cuda.empty_cache()
