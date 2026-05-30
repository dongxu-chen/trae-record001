import os
import cv2
import numpy as np
import torch
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Callable
from tqdm import tqdm
import time
import copy

from models import VESPCN, LightweightVESPCN, create_vespcn_model, create_lightweight_model, initialize_weights
from utils import (
    frame_to_tensor, tensor_to_frame,
    get_video_info, extract_frames, frames_to_video,
    clean_temp_dir, process_in_patches,
    VideoReader, VideoWriter, Timer, AverageMeter
)
from quality_metrics import QualityMetrics, create_quality_evaluator
from model_compression import (
    ModelCompressor, InferenceOptimizer, create_compressor
)
from config import DEVICE, TEMP_DIR, OUTPUT_DIR, PROCESSING_CONFIG, MODEL_WEIGHTS_DIR


class VideoEnhancer:
    def __init__(self, model: VESPCN = None, device: str = None,
                 use_patch_processing: bool = False, patch_size: int = 512,
                 use_temporal_alignment: bool = True,
                 use_compressed_model: bool = False,
                 target_fps: float = 15.0,
                 quality_weight: float = 0.5,
                 use_lightweight: bool = False,
                 scale_factor: int = 2):
        self.device = torch.device(device or DEVICE)
        self.use_patch_processing = use_patch_processing
        self.patch_size = patch_size
        self.scale_factor = scale_factor
        self.frame_rate_multiplier = 2
        self.use_temporal_alignment = use_temporal_alignment
        self.use_compressed_model = use_compressed_model
        self.target_fps = target_fps
        self.quality_weight = quality_weight
        self.use_lightweight = use_lightweight
        self.original_model = None
        self.compressed_model = None
        self.optimized_model = None
        self.compression_result = None
        self.is_optimized = False
        self.use_half_precision = False

        if use_lightweight:
            self.model = create_lightweight_model(
                scale_factor=scale_factor,
                device=str(self.device),
                use_temporal_alignment=use_temporal_alignment
            )
            self.model.apply(initialize_weights)
        elif model is None:
            self.model = create_vespcn_model(
                scale_factor=scale_factor,
                pretrained=False,
                device=str(self.device),
                use_temporal_alignment=use_temporal_alignment,
                quality_weight=quality_weight
            )
            self.model.apply(initialize_weights)
        else:
            self.model = model.to(self.device)
            if hasattr(self.model, 'set_quality_weight'):
                self.model.set_quality_weight(quality_weight)

        self.original_model = copy.deepcopy(self.model)
        self.model.eval()
        self.quality_evaluator = create_quality_evaluator(
            device=str(self.device),
            metrics=['psnr', 'ssim', 'lpips']
        )

    def load_weights(self, weights_path: str):
        state_dict = torch.load(weights_path, map_location=self.device)
        self.model.load_state_dict(state_dict)
        self.original_model = copy.deepcopy(self.model)
        print(f"Loaded weights from {weights_path}")

    def set_quality_weight(self, weight: float):
        self.quality_weight = max(0.0, min(1.0, weight))
        if hasattr(self.model, 'set_quality_weight'):
            self.model.set_quality_weight(self.quality_weight)
        if hasattr(self.original_model, 'set_quality_weight'):
            self.original_model.set_quality_weight(self.quality_weight)

    def deploy_to_mobile(self, output_dir: str = None, model_format: str = 'onnx',
                          target_device: str = 'android',
                          input_resolution: tuple = (480, 640)) -> Dict:
        try:
            from mobile_deploy import MobileModelConverter, MobileConfig
        except ImportError:
            raise ImportError("mobile_deploy module not found")

        if output_dir is None:
            output_dir = OUTPUT_DIR / "mobile_deploy"
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        config = MobileConfig(
            target_device=target_device,
            model_format=model_format,
            input_resolution=input_resolution,
            scale_factor=self.scale_factor,
            target_fps=self.target_fps,
        )

        converter = MobileModelConverter(self.model, device=str(self.device))

        result = {'config': config}

        if model_format in ('onnx', 'tflite'):
            onnx_path = str(output_dir / "model.onnx")
            converter.convert_to_onnx(
                output_path=onnx_path,
                input_shape=(1, 3, input_resolution[0], input_resolution[1])
            )
            result['onnx_path'] = onnx_path
            result['onnx_size_mb'] = Path(onnx_path).stat().st_size / 1e6 if Path(onnx_path).exists() else 0

            if model_format == 'tflite':
                try:
                    tflite_path = str(output_dir / "model.tflite")
                    converter.convert_to_tflite(onnx_path, tflite_path)
                    result['tflite_path'] = tflite_path
                except Exception as e:
                    result['tflite_error'] = str(e)

        elif model_format == 'torchscript':
            ts_path = str(output_dir / "model.pt")
            converter.convert_to_torchscript(
                output_path=ts_path,
                input_shape=(1, 3, input_resolution[0], input_resolution[1])
            )
            result['torchscript_path'] = ts_path
            result['torchscript_size_mb'] = Path(ts_path).stat().st_size / 1e6 if Path(ts_path).exists() else 0

        result['output_dir'] = str(output_dir)
        return result

    def compress_model(self, target_fps: float = None, prune_amount: float = None,
                       use_quantization: bool = True) -> Tuple[nn.Module, Dict]:
        target_fps = target_fps or self.target_fps
        print(f"开始模型压缩，目标FPS: {target_fps}")

        compressor = create_compressor(self.original_model, device=str(self.device))

        if prune_amount is not None:
            compressed_model, result = compressor.prune_and_quantize(
                prune_amount=prune_amount,
                quantize=use_quantization
            )
        else:
            compressed_model, result = compressor.optimize_for_inference(
                target_fps=target_fps
            )

        self.compressed_model = compressed_model
        self.compression_result = result
        self.model = compressed_model.to(self.device)
        self.model.eval()
        self.use_compressed_model = True

        print(f"压缩完成: FPS={result['compressed_performance']['fps']:.1f}, "
              f"压缩比={result['size_compression_ratio']:.1f}x")

        return compressed_model, result

    def optimize_for_inference(self, use_half: bool = True,
                               use_channels_last: bool = True,
                               use_jit: bool = True) -> nn.Module:
        print("开始推理优化...")

        model_to_optimize = self.compressed_model or self.original_model

        optimizer = InferenceOptimizer(model_to_optimize, device=str(self.device))
        optimized = optimizer.optimize(
            use_half=use_half,
            use_channels_last=use_channels_last,
            use_jit=use_jit
        )

        self.optimized_model = optimized
        self.model = optimized
        self.is_optimized = True
        self.use_half_precision = use_half and self.device.type == 'cuda'

        perf = optimizer.benchmark()
        print(f"优化完成: FPS={perf['fps']:.1f}, 平均时间={perf['avg_time_ms']:.1f}ms")

        return optimized

    def get_inference_model(self) -> nn.Module:
        if self.optimized_model is not None:
            return self.optimized_model
        elif self.compressed_model is not None:
            return self.compressed_model
        else:
            return self.model

    def _prepare_tensor(self, frame: np.ndarray) -> torch.Tensor:
        tensor = frame_to_tensor(frame, device=str(self.device), normalize=True)
        if self.use_half_precision:
            tensor = tensor.half()
        return tensor

    def enhance_frame(self, frame: np.ndarray) -> np.ndarray:
        tensor = self._prepare_tensor(frame)
        model = self.get_inference_model()

        with torch.no_grad():
            if self.use_patch_processing:
                enhanced_tensor = process_in_patches(
                    model, tensor,
                    patch_size=self.patch_size,
                    overlap=32
                )
            else:
                enhanced_tensor = model.process_single_frame(tensor)

        enhanced_frame = tensor_to_frame(enhanced_tensor.float(), denormalize=True)
        return enhanced_frame

    def interpolate_and_enhance(self, prev_frame: np.ndarray,
                                next_frame: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        prev_tensor = self._prepare_tensor(prev_frame)
        next_tensor = self._prepare_tensor(next_frame)
        model = self.get_inference_model()

        with torch.no_grad():
            interpolated_tensor = model.interpolate_frame(prev_tensor, next_tensor)

            enhanced_prev = model.process_single_frame(prev_tensor)
            enhanced_interp = model.process_single_frame(interpolated_tensor)
            enhanced_next = model.process_single_frame(next_tensor)

        enhanced_prev_frame = tensor_to_frame(enhanced_prev.float(), denormalize=True)
        enhanced_interp_frame = tensor_to_frame(enhanced_interp.float(), denormalize=True)
        enhanced_next_frame = tensor_to_frame(enhanced_next.float(), denormalize=True)

        return enhanced_prev_frame, enhanced_interp_frame, enhanced_next_frame

    def process_video(self, input_path: str, output_path: str = None,
                      max_frames: Optional[int] = None,
                      progress_callback: Optional[Callable[[int, int], None]] = None,
                      enable_quality_metrics: bool = False) -> Dict:
        input_path = Path(input_path)
        if not input_path.exists():
            raise FileNotFoundError(f"Video file not found: {input_path}")

        video_info = get_video_info(str(input_path))
        total_frames = min(video_info['total_frames'], max_frames) if max_frames else video_info['total_frames']
        output_fps = video_info['fps'] * self.frame_rate_multiplier
        output_width = video_info['width'] * self.scale_factor
        output_height = video_info['height'] * self.scale_factor

        if output_path is None:
            suffix = "_enhanced"
            if self.use_compressed_model:
                suffix += "_compressed"
            output_path = OUTPUT_DIR / f"{input_path.stem}{suffix}{input_path.suffix}"
        output_path = Path(output_path)

        temp_input_dir = TEMP_DIR / "input_frames"
        temp_output_dir = TEMP_DIR / "output_frames"
        clean_temp_dir(str(temp_input_dir))
        clean_temp_dir(str(temp_output_dir))

        print("Extracting frames...")
        frame_paths = extract_frames(str(input_path), str(temp_input_dir), max_frames=max_frames)
        print(f"Extracted {len(frame_paths)} frames")

        output_frame_paths = []
        processing_times = AverageMeter()
        quality_metrics_list = []

        print("Processing frames...")
        for i in tqdm(range(len(frame_paths) - 1)):
            prev_frame = cv2.imread(frame_paths[i])
            next_frame = cv2.imread(frame_paths[i + 1])

            with Timer() as timer:
                enhanced_prev, enhanced_interp, enhanced_next = self.interpolate_and_enhance(
                    prev_frame, next_frame
                )
            processing_times.update(timer.elapsed_time)

            if i == 0:
                out_prev_path = str(temp_output_dir / f"frame_{0:06d}.png")
                cv2.imwrite(out_prev_path, enhanced_prev)
                output_frame_paths.append(out_prev_path)

            out_interp_path = str(temp_output_dir / f"frame_{2 * i + 1:06d}.png")
            cv2.imwrite(out_interp_path, enhanced_interp)
            output_frame_paths.append(out_interp_path)

            out_next_path = str(temp_output_dir / f"frame_{2 * i + 2:06d}.png")
            cv2.imwrite(out_next_path, enhanced_next)
            output_frame_paths.append(out_next_path)

            if enable_quality_metrics and i < len(frame_paths) - 1:
                with torch.no_grad():
                    prev_tensor = frame_to_tensor(prev_frame, device=str(self.device))
                    next_tensor = frame_to_tensor(next_frame, device=str(self.device))
                    interp_tensor = frame_to_tensor(enhanced_interp, device=str(self.device))

                    interp_down = torch.nn.functional.interpolate(
                        interp_tensor, scale_factor=0.5, mode='bilinear', align_corners=False
                    )
                    metrics = self.quality_evaluator.calculate_all(
                        (prev_tensor + next_tensor) / 2, interp_down
                    )
                    quality_metrics_list.append(metrics)

            if progress_callback:
                progress_callback(i + 1, len(frame_paths) - 1)

        print("Creating output video...")
        frames_to_video(
            output_frame_paths,
            str(output_path),
            fps=output_fps,
            codec=PROCESSING_CONFIG['codec'],
            crf=PROCESSING_CONFIG['crf']
        )

        clean_temp_dir(str(temp_input_dir))
        clean_temp_dir(str(temp_output_dir))

        actual_fps = len(output_frame_paths) / processing_times.sum if processing_times.sum > 0 else 0

        result = {
            'output_path': str(output_path),
            'input_frames': len(frame_paths),
            'output_frames': len(output_frame_paths),
            'input_fps': video_info['fps'],
            'output_fps': output_fps,
            'actual_processing_fps': actual_fps,
            'input_resolution': f"{video_info['width']}x{video_info['height']}",
            'output_resolution': f"{output_width}x{output_height}",
            'avg_processing_time': processing_times.avg,
            'total_processing_time': processing_times.sum,
            'target_fps_met': actual_fps >= self.target_fps,
            'use_compressed_model': self.use_compressed_model,
            'use_temporal_alignment': self.use_temporal_alignment,
        }

        if self.compression_result:
            result['compression_info'] = {
                'sparsity': self.compression_result['sparsity']['sparsity'],
                'compression_ratio': self.compression_result['size_compression_ratio'],
                'speedup_ratio': self.compression_result['speedup_ratio'],
            }

        if quality_metrics_list:
            avg_metrics = {
                metric: np.mean([m[metric] for m in quality_metrics_list])
                for metric in quality_metrics_list[0].keys()
            }
            result['quality_metrics'] = avg_metrics

        return result

    def process_video_realtime(self, input_path: str, output_path: str = None,
                               display_callback: Optional[Callable[[np.ndarray], None]] = None,
                               max_frames: Optional[int] = None) -> Dict:
        input_path = Path(input_path)
        if not input_path.exists():
            raise FileNotFoundError(f"Video file not found: {input_path}")

        video_info = get_video_info(str(input_path))
        output_fps = video_info['fps'] * self.frame_rate_multiplier
        output_width = video_info['width'] * self.scale_factor
        output_height = video_info['height'] * self.scale_factor

        if output_path is None:
            suffix = "_realtime_enhanced"
            if self.use_compressed_model:
                suffix += "_compressed"
            output_path = OUTPUT_DIR / f"{input_path.stem}{suffix}{input_path.suffix}"

        reader = VideoReader(str(input_path))
        writer = VideoWriter(str(output_path), output_fps, output_width, output_height)

        processing_times = AverageMeter()
        frame_count = 0
        fps_actual = 0

        try:
            prev_frame = None
            for curr_frame in reader:
                if max_frames and frame_count >= max_frames:
                    break

                if prev_frame is not None:
                    with Timer() as timer:
                        enhanced_prev, enhanced_interp, enhanced_curr = self.interpolate_and_enhance(
                            prev_frame, curr_frame
                        )
                    processing_times.update(timer.elapsed_time)

                    if frame_count == 1:
                        writer.write_frame(enhanced_prev)

                    writer.write_frame(enhanced_interp)
                    writer.write_frame(enhanced_curr)

                    if display_callback:
                        display_callback(enhanced_curr)
                else:
                    with Timer() as timer:
                        enhanced_first = self.enhance_frame(curr_frame)
                    processing_times.update(timer.elapsed_time)
                    writer.write_frame(enhanced_first)

                    if display_callback:
                        display_callback(enhanced_first)

                prev_frame = curr_frame
                frame_count += 1

                if processing_times.count > 0:
                    fps_actual = (frame_count * 2 - 1) / processing_times.sum

                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
        finally:
            reader.release()
            writer.release()
            cv2.destroyAllWindows()

        return {
            'output_path': str(output_path),
            'processed_frames': frame_count,
            'input_fps': video_info['fps'],
            'output_fps': output_fps,
            'actual_fps': fps_actual,
            'avg_processing_time': processing_times.avg,
            'total_processing_time': processing_times.sum,
            'realtime_factor': fps_actual / video_info['fps'] if video_info['fps'] > 0 else 0,
            'target_fps_met': fps_actual >= self.target_fps,
            'use_compressed_model': self.use_compressed_model,
        }

    def process_frame_batch(self, frames: List[np.ndarray]) -> List[np.ndarray]:
        if len(frames) == 0:
            return []
        if len(frames) == 1:
            return [self.enhance_frame(frames[0])]

        enhanced_frames = []
        for i in range(len(frames) - 1):
            enhanced_prev, enhanced_interp, enhanced_next = self.interpolate_and_enhance(
                frames[i], frames[i + 1]
            )
            if i == 0:
                enhanced_frames.append(enhanced_prev)
            enhanced_frames.append(enhanced_interp)
            enhanced_frames.append(enhanced_next)

        return enhanced_frames

    def benchmark(self, input_path: str = None, num_runs: int = 100,
                  resolution: Tuple[int, int] = (128, 128)) -> Dict:
        if input_path and Path(input_path).exists():
            frame = cv2.imread(input_path)
            if frame is None:
                cap = cv2.VideoCapture(input_path)
                ret, frame = cap.read()
                cap.release()
        else:
            frame = np.random.randint(0, 255, (resolution[1], resolution[0], 3), dtype=np.uint8)

        warmup_runs = 10
        for _ in range(warmup_runs):
            _ = self.enhance_frame(frame)

        times = []
        for _ in range(num_runs):
            with Timer() as timer:
                _ = self.enhance_frame(frame)
            times.append(timer.elapsed_time)

        fps = 1.0 / np.mean(times)

        return {
            'resolution': f"{frame.shape[1]}x{frame.shape[0]}",
            'avg_time_ms': np.mean(times) * 1000,
            'std_time_ms': np.std(times) * 1000,
            'min_time_ms': np.min(times) * 1000,
            'max_time_ms': np.max(times) * 1000,
            'fps': fps,
            'target_fps': self.target_fps,
            'target_met': fps >= self.target_fps,
            'device': str(self.device),
            'use_compressed': self.use_compressed_model,
            'is_optimized': self.is_optimized,
        }

    def benchmark_full_pipeline(self, input_path: str = None,
                                 num_runs: int = 50,
                                 resolution: Tuple[int, int] = (128, 128)) -> Dict:
        if input_path and Path(input_path).exists():
            frame1 = cv2.imread(input_path)
            frame2 = cv2.imread(input_path)
        else:
            frame1 = np.random.randint(0, 255, (resolution[1], resolution[0], 3), dtype=np.uint8)
            frame2 = np.random.randint(0, 255, (resolution[1], resolution[0], 3), dtype=np.uint8)

        warmup_runs = 5
        for _ in range(warmup_runs):
            _ = self.interpolate_and_enhance(frame1, frame2)

        times = []
        for _ in range(num_runs):
            with Timer() as timer:
                _ = self.interpolate_and_enhance(frame1, frame2)
            times.append(timer.elapsed_time)

        fps = 3.0 / np.mean(times)

        return {
            'resolution': f"{frame1.shape[1]}x{frame1.shape[0]}",
            'avg_time_ms': np.mean(times) * 1000,
            'std_time_ms': np.std(times) * 1000,
            'fps': fps,
            'target_fps': self.target_fps,
            'target_met': fps >= self.target_fps,
            'device': str(self.device),
            'use_compressed': self.use_compressed_model,
            'is_optimized': self.is_optimized,
        }

    def save_compressed_model(self, output_path: str = None):
        if self.compressed_model is None:
            raise ValueError("没有压缩的模型可保存")

        if output_path is None:
            output_path = MODEL_WEIGHTS_DIR / "compressed_vespcn.pth"

        output_path = Path(output_path)
        torch.save(self.compressed_model.state_dict(), output_path)

        if self.compression_result:
            info_path = output_path.with_suffix('.json')
            import json
            with open(info_path, 'w') as f:
                json.dump({
                    'sparsity': self.compression_result['sparsity'],
                    'compression_ratio': self.compression_result['size_compression_ratio'],
                    'speedup_ratio': self.compression_result['speedup_ratio'],
                    'fps': self.compression_result['compressed_performance']['fps'],
                }, f, indent=2)

        print(f"压缩模型已保存到: {output_path}")
        return str(output_path)

    def get_model_info(self) -> Dict:
        total_params = sum(p.numel() for p in self.original_model.parameters())
        trainable_params = sum(p.numel() for p in self.original_model.parameters() if p.requires_grad)

        info = {
            'total_params': total_params,
            'trainable_params': trainable_params,
            'device': str(self.device),
            'scale_factor': self.scale_factor,
            'frame_rate_multiplier': self.frame_rate_multiplier,
            'use_temporal_alignment': self.use_temporal_alignment,
            'use_compressed_model': self.use_compressed_model,
            'is_optimized': self.is_optimized,
            'use_half_precision': self.use_half_precision,
            'target_fps': self.target_fps,
        }

        if self.compression_result:
            info['compression'] = {
                'sparsity': self.compression_result['sparsity']['sparsity'],
                'compression_ratio': self.compression_result['size_compression_ratio'],
                'speedup_ratio': self.compression_result['speedup_ratio'],
                'original_size_mb': self.compression_result['original_size_mb'],
                'compressed_size_mb': self.compression_result['compressed_size_mb'],
            }

        return info


class RealTimeProcessor:
    def __init__(self, enhancer: VideoEnhancer, source: int = 0):
        self.enhancer = enhancer
        self.source = source
        self.running = False
        self.stats = {
            'fps': 0,
            'processing_time': 0,
            'frame_count': 0,
            'target_fps_met': False,
        }

    def start(self, window_name: str = "Real-Time Video Enhancement"):
        cap = cv2.VideoCapture(self.source)
        if not cap.isOpened():
            raise ValueError(f"Cannot open camera source: {self.source}")

        self.running = True
        prev_frame = None
        frame_times = []

        try:
            while self.running:
                ret, frame = cap.read()
                if not ret:
                    break

                start_time = time.time()

                if prev_frame is not None:
                    _, _, enhanced = self.enhancer.interpolate_and_enhance(prev_frame, frame)
                else:
                    enhanced = self.enhancer.enhance_frame(frame)

                processing_time = time.time() - start_time
                frame_times.append(processing_time)

                if len(frame_times) > 30:
                    frame_times.pop(0)

                self.stats['fps'] = 1.0 / np.mean(frame_times)
                self.stats['processing_time'] = np.mean(frame_times) * 1000
                self.stats['frame_count'] += 1
                self.stats['target_fps_met'] = self.stats['fps'] >= self.enhancer.target_fps

                status_color = (0, 255, 0) if self.stats['target_fps_met'] else (0, 0, 255)
                status_text = "✓ TARGET MET" if self.stats['target_fps_met'] else "✗ TARGET NOT MET"

                info_lines = [
                    f"FPS: {self.stats['fps']:.1f} / Target: {self.enhancer.target_fps:.1f}",
                    f"Time: {self.stats['processing_time']:.1f}ms",
                    f"Resolution: {enhanced.shape[1]}x{enhanced.shape[0]}",
                    status_text
                ]

                for i, line in enumerate(info_lines):
                    y_pos = 30 + i * 25
                    color = (0, 255, 0) if i < 3 else status_color
                    cv2.putText(enhanced, line, (10, y_pos),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

                cv2.imshow(window_name, enhanced)

                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

                prev_frame = frame
        finally:
            cap.release()
            cv2.destroyAllWindows()

    def stop(self):
        self.running = False


def create_video_enhancer(weights_path: str = None, device: str = None,
                          use_patch_processing: bool = False,
                          use_temporal_alignment: bool = True,
                          use_compressed_model: bool = False,
                          compress: bool = False, target_fps: float = 15.0,
                          optimize_inference: bool = False,
                          quality_weight: float = 0.5,
                          use_lightweight: bool = False,
                          scale_factor: int = 2) -> VideoEnhancer:
    enhancer = VideoEnhancer(
        device=device,
        use_patch_processing=use_patch_processing,
        use_temporal_alignment=use_temporal_alignment,
        use_compressed_model=use_compressed_model,
        target_fps=target_fps,
        quality_weight=quality_weight,
        use_lightweight=use_lightweight,
        scale_factor=scale_factor
    )

    if weights_path and Path(weights_path).exists():
        enhancer.load_weights(weights_path)

    if compress or use_compressed_model:
        enhancer.compress_model(target_fps=target_fps)

    if optimize_inference:
        enhancer.optimize_for_inference()

    return enhancer


if __name__ == "__main__":
    print("=== 测试视频增强器 ===")
    enhancer = create_video_enhancer(optimize_inference=False)

    print("\n模型信息:")
    info = enhancer.get_model_info()
    for k, v in info.items():
        if isinstance(v, dict):
            print(f"  {k}:")
            for k2, v2 in v.items():
                print(f"    {k2}: {v2}")
        else:
            print(f"  {k}: {v}")

    print("\n基准测试 (原始模型):")
    bench_original = enhancer.benchmark()
    print(f"  FPS: {bench_original['fps']:.1f}, 时间: {bench_original['avg_time_ms']:.1f}ms")
    print(f"  达到目标FPS {enhancer.target_fps}: {bench_original['target_met']}")

    print("\n开始模型压缩...")
    try:
        enhancer.compress_model(target_fps=15.0)

        print("\n基准测试 (压缩模型):")
        bench_compressed = enhancer.benchmark()
        print(f"  FPS: {bench_compressed['fps']:.1f}, 时间: {bench_compressed['avg_time_ms']:.1f}ms")
        print(f"  达到目标FPS {enhancer.target_fps}: {bench_compressed['target_met']}")
    except Exception as e:
        print(f"  压缩跳过: {e}")

    print("\n✅ 测试完成!")
