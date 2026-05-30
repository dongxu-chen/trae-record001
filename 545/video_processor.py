import os
import cv2
import numpy as np
from typing import Dict, Any, Optional, List, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum

from tone_mapping import ToneMapper, ToneMappingOperator
from scene_analyzer import SceneAnalyzer, SceneFeatures, SceneType


class StabilizationMode(Enum):
    NONE = "none"
    LIGHT = "light"
    MEDIUM = "medium"
    STRONG = "strong"


@dataclass
class VideoFrameInfo:
    frame_index: int
    timestamp: float
    features: Optional[SceneFeatures] = None
    operator: Optional[ToneMappingOperator] = None
    params: Optional[Dict[str, float]] = None
    exposure_change: float = 0.0
    brightness_change: float = 0.0


@dataclass
class TemporalFilterState:
    prev_brightness: float = 0.0
    prev_exposure: float = 1.0
    prev_params: Dict[ToneMappingOperator, Dict[str, float]] = field(default_factory=dict)
    prev_operator: Optional[ToneMappingOperator] = None
    frame_buffer: List[np.ndarray] = field(default_factory=list)
    brightness_history: List[float] = field(default_factory=list)


class HDRVideoProcessor:
    def __init__(self, use_gpu: bool = False, stabilization_mode: StabilizationMode = StabilizationMode.MEDIUM):
        self.tonemapper = ToneMapper(use_gpu=use_gpu)
        self.scene_analyzer = SceneAnalyzer()
        self.use_gpu = use_gpu
        self.stabilization_mode = stabilization_mode
        self.filter_state = TemporalFilterState()

        self._init_stabilization_params()

    def _init_stabilization_params(self):
        params = {
            StabilizationMode.NONE: {
                'brightness_smoothing': 1.0,
                'param_smoothing': 1.0,
                'operator_switch_threshold': 0.0,
                'max_param_change': 1.0
            },
            StabilizationMode.LIGHT: {
                'brightness_smoothing': 0.3,
                'param_smoothing': 0.5,
                'operator_switch_threshold': 0.3,
                'max_param_change': 0.2
            },
            StabilizationMode.MEDIUM: {
                'brightness_smoothing': 0.15,
                'param_smoothing': 0.3,
                'operator_switch_threshold': 0.5,
                'max_param_change': 0.1
            },
            StabilizationMode.STRONG: {
                'brightness_smoothing': 0.05,
                'param_smoothing': 0.15,
                'operator_switch_threshold': 0.7,
                'max_param_change': 0.05
            }
        }
        self._stab_params = params[self.stabilization_mode]

    def set_stabilization_mode(self, mode: StabilizationMode):
        self.stabilization_mode = mode
        self._init_stabilization_params()

    def reset_state(self):
        self.filter_state = TemporalFilterState()

    def _temporal_smooth_params(self, op: ToneMappingOperator, new_params: Dict[str, float],
                                frame_idx: int) -> Dict[str, float]:
        if frame_idx == 0 or self.stabilization_mode == StabilizationMode.NONE:
            self.filter_state.prev_params[op] = new_params.copy()
            return new_params.copy()

        prev_params = self.filter_state.prev_params.get(op, {})
        smoothed_params = {}
        alpha = self._stab_params['param_smoothing']
        max_change = self._stab_params['max_param_change']

        for name, new_val in new_params.items():
            prev_val = prev_params.get(name, new_val)
            target_val = alpha * new_val + (1 - alpha) * prev_val

            if abs(target_val - prev_val) > max_change * abs(new_val - prev_val + 1e-6):
                if target_val > prev_val:
                    target_val = prev_val + max_change * abs(new_val - prev_val)
                else:
                    target_val = prev_val - max_change * abs(new_val - prev_val)

            smoothed_params[name] = target_val

        self.filter_state.prev_params[op] = smoothed_params.copy()
        return smoothed_params

    def _smooth_operator_selection(self, new_op: ToneMappingOperator, new_confidence: float,
                                    frame_idx: int) -> ToneMappingOperator:
        if frame_idx == 0 or self.stabilization_mode == StabilizationMode.NONE:
            self.filter_state.prev_operator = new_op
            return new_op

        threshold = self._stab_params['operator_switch_threshold']
        prev_op = self.filter_state.prev_operator

        if new_confidence > threshold and new_op != prev_op:
            self.filter_state.prev_operator = new_op
            return new_op
        elif new_op == prev_op:
            return new_op
        else:
            return prev_op

    def _adjust_exposure_for_stability(self, hdr_frame: np.ndarray,
                                       current_features: SceneFeatures,
                                       frame_idx: int) -> float:
        if frame_idx == 0 or self.stabilization_mode == StabilizationMode.NONE:
            self.filter_state.prev_brightness = current_features.mean_brightness
            return 1.0

        alpha = self._stab_params['brightness_smoothing']
        target_brightness = self.filter_state.prev_brightness
        current_brightness = current_features.mean_brightness

        if abs(current_brightness - target_brightness) > 0.01:
            smooth_brightness = alpha * current_brightness + (1 - alpha) * target_brightness
            exposure_adjust = smooth_brightness / (current_brightness + 1e-6)
            self.filter_state.prev_brightness = smooth_brightness
            return float(exposure_adjust)
        else:
            self.filter_state.prev_brightness = current_brightness
            return 1.0

    def process_frame(self, hdr_frame: np.ndarray, frame_idx: int,
                      auto_operator: bool = True,
                      fixed_operator: Optional[ToneMappingOperator] = None) -> Tuple[np.ndarray, VideoFrameInfo]:
        if hdr_frame is None:
            raise ValueError("Input frame is None")

        if hdr_frame.dtype != np.float32:
            hdr_frame = hdr_frame.astype(np.float32)

        info = VideoFrameInfo(frame_index=frame_idx, timestamp=frame_idx / 30.0)

        features = self.scene_analyzer.analyze_image(hdr_frame)
        info.features = features

        exposure_adjust = self._adjust_exposure_for_stability(hdr_frame, features, frame_idx)
        if exposure_adjust != 1.0:
            hdr_frame = np.clip(hdr_frame * exposure_adjust, 0, None).astype(np.float32)

        if auto_operator:
            best_op, params, confidence = self.scene_analyzer.select_optimal_operator(features)
            final_op = self._smooth_operator_selection(best_op, confidence, frame_idx)
            final_params = self._temporal_smooth_params(final_op, params, frame_idx)
        elif fixed_operator is not None:
            final_op = fixed_operator
            raw_params = self.tonemapper.get_params(final_op)
            final_params = self._temporal_smooth_params(final_op, raw_params, frame_idx)
        else:
            raise ValueError("Must enable auto_operator or provide fixed_operator")

        info.operator = final_op
        info.params = final_params

        for name, value in final_params.items():
            self.tonemapper.set_param(final_op, name, value)

        result = self.tonemapper.process(hdr_frame, final_op)

        return result, info

    def process_video(self, input_path: str, output_path: str,
                      auto_operator: bool = True,
                      fixed_operator: Optional[ToneMappingOperator] = None,
                      progress_callback: Optional[Callable[[int, int, str], None]] = None,
                      max_frames: Optional[int] = None) -> Dict[str, Any]:
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input video not found: {input_path}")

        self.reset_state()

        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            raise ValueError(f"Could not open video: {input_path}")

        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        if max_frames is not None:
            total_frames = min(total_frames, max_frames)

        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        frame_infos: List[VideoFrameInfo] = []
        processed_frames = 0

        try:
            while processed_frames < total_frames:
                ret, frame = cap.read()
                if not ret:
                    break

                hdr_frame = frame.astype(np.float32) / 255.0
                hdr_frame = self._linearize_frame(hdr_frame)

                result, info = self.process_frame(
                    hdr_frame, processed_frames, auto_operator, fixed_operator
                )
                frame_infos.append(info)

                out.write(result)
                processed_frames += 1

                if progress_callback and processed_frames % 10 == 0:
                    progress_callback(processed_frames, total_frames, f"处理帧 {processed_frames}/{total_frames}")

        finally:
            cap.release()
            out.release()

        return {
            'output_path': output_path,
            'total_frames': processed_frames,
            'fps': fps,
            'resolution': (width, height),
            'frame_infos': frame_infos
        }

    def _linearize_frame(self, frame: np.ndarray) -> np.ndarray:
        linear = np.power(frame, 2.2).astype(np.float32)
        return linear

    @staticmethod
    def extract_hdr_frames(video_path: str, output_dir: str,
                           frame_interval: int = 1,
                           max_frames: Optional[int] = None) -> List[str]:
        os.makedirs(output_dir, exist_ok=True)

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Could not open video: {video_path}")

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if max_frames is not None:
            total_frames = min(total_frames, max_frames * frame_interval)

        frame_paths: List[str] = []
        frame_idx = 0
        saved_idx = 0

        try:
            while frame_idx < total_frames:
                ret, frame = cap.read()
                if not ret:
                    break

                if frame_idx % frame_interval == 0:
                    hdr_frame = frame.astype(np.float32) / 255.0
                    hdr_frame = np.power(hdr_frame, 2.2)

                    output_path = os.path.join(output_dir, f"frame_{saved_idx:06d}.hdr")
                    cv2.imwrite(output_path, hdr_frame)
                    frame_paths.append(output_path)
                    saved_idx += 1

                frame_idx += 1

        finally:
            cap.release()

        return frame_paths
