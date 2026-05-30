import torch
import torch.nn as nn
import torch.nn.utils.prune as prune
import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
from pathlib import Path
import copy
import time
import os

from models import VESPCN, LightweightVESPCN, create_vespcn_model, create_lightweight_model, initialize_weights

try:
    import onnx
    HAS_ONNX = True
except ImportError:
    HAS_ONNX = False

try:
    import onnxruntime as ort
    HAS_ORT = True
except ImportError:
    HAS_ORT = False

try:
    import onnx2tf
    HAS_ONNX2TF = True
except ImportError:
    HAS_ONNX2TF = False

try:
    import tflite_runtime.interpreter as tflite_interp
    HAS_TFLITE_RT = True
except ImportError:
    HAS_TFLITE_RT = False

try:
    import tensorflow as tf
    HAS_TF = True
except ImportError:
    HAS_TF = False


class _MultiFrameWrapper(nn.Module):
    def __init__(self, model):
        super().__init__()
        self.model = model

    def forward(self, frames):
        outputs = self.model(frames)
        return torch.stack(outputs, dim=1)


class _SingleFrameWrapper(nn.Module):
    def __init__(self, model):
        super().__init__()
        self.model = model

    def forward(self, frame):
        return self.model.process_single_frame(frame)


@dataclass
class MobileConfig:
    target_device: str = 'android'
    model_format: str = 'onnx'
    input_resolution: tuple = (480, 640)
    scale_factor: int = 2
    max_model_size_mb: float = 10.0
    target_fps: float = 30.0
    use_half: bool = True
    num_threads: int = 4


class MobileModelConverter:
    def __init__(self, model, device='cpu'):
        if device == 'cuda' and not torch.cuda.is_available():
            device = 'cpu'
        self.device = torch.device(device)
        self.model = model.to(self.device)
        self.model.eval()
        self._conversion_info = {
            'original_size_mb': self._get_model_size_mb(),
            'conversions': [],
            'model_type': type(model).__name__
        }

    def _get_model_size_mb(self):
        param_size = sum(p.nelement() * p.element_size() for p in self.model.parameters())
        buffer_size = sum(b.nelement() * b.element_size() for b in self.model.buffers())
        return (param_size + buffer_size) / (1024 ** 2)

    def _make_wrapper(self, input_shape):
        if len(input_shape) == 5:
            return _MultiFrameWrapper(self.model), torch.randn(*input_shape).to(self.device)
        elif len(input_shape) == 4:
            return _SingleFrameWrapper(self.model), torch.randn(*input_shape).to(self.device)
        return None, None

    def convert_to_onnx(self, output_path, input_shape=(1, 3, 3, 480, 640), opset_version=11):
        if not HAS_ONNX:
            self._conversion_info['conversions'].append(
                {'format': 'onnx', 'status': 'failed', 'error': 'onnx not installed'})
            return None

        output_path = str(output_path)
        self.model.eval()
        wrapper, dummy_input = self._make_wrapper(input_shape)
        if wrapper is None:
            self._conversion_info['conversions'].append(
                {'format': 'onnx', 'status': 'failed', 'error': 'invalid input_shape'})
            return None

        wrapper.eval()
        try:
            with torch.no_grad():
                torch.onnx.export(
                    wrapper, dummy_input, output_path,
                    opset_version=opset_version,
                    input_names=['input'], output_names=['output'],
                    dynamic_axes={'input': {0: 'batch_size'}, 'output': {0: 'batch_size'}}
                )
            file_size_mb = os.path.getsize(output_path) / (1024 ** 2)
            self._conversion_info['conversions'].append({
                'format': 'onnx', 'status': 'success',
                'path': output_path, 'size_mb': file_size_mb, 'opset_version': opset_version
            })
            return output_path
        except Exception as e:
            self._conversion_info['conversions'].append(
                {'format': 'onnx', 'status': 'failed', 'error': str(e)})
            return None

    def convert_to_torchscript(self, output_path, input_shape=(1, 3, 3, 480, 640)):
        output_path = str(output_path)
        self.model.eval()
        wrapper, dummy_input = self._make_wrapper(input_shape)
        if wrapper is None:
            self._conversion_info['conversions'].append(
                {'format': 'torchscript', 'status': 'failed', 'error': 'invalid input_shape'})
            return None

        wrapper.eval()
        try:
            with torch.no_grad():
                traced = torch.jit.trace(wrapper, dummy_input)
                traced.save(output_path)
            file_size_mb = os.path.getsize(output_path) / (1024 ** 2)
            self._conversion_info['conversions'].append({
                'format': 'torchscript', 'status': 'success',
                'path': output_path, 'size_mb': file_size_mb
            })
            return output_path
        except Exception as e:
            self._conversion_info['conversions'].append(
                {'format': 'torchscript', 'status': 'failed', 'error': str(e)})
            return None

    def optimize_onnx(self, onnx_path, output_path):
        if not HAS_ONNX:
            return None

        passes = [
            'fuse_bn_into_conv', 'eliminate_deadend', 'eliminate_identity',
            'eliminate_nop_transpose', 'eliminate_nop_pad',
            'eliminate_unused_initializer', 'fuse_add_bias_into_conv',
            'fuse_consecutive_concats', 'fuse_consecutive_reduce_unsqueeze',
            'fuse_consecutive_squeezes', 'fuse_consecutive_transposes',
        ]

        try:
            model = onnx.load(onnx_path)
            try:
                import onnxoptimizer
                optimized = onnxoptimizer.optimize(model, passes)
            except (ImportError, AttributeError):
                try:
                    from onnx import optimizer as onnx_opt
                    optimized = onnx_opt.optimize(model, passes)
                except (ImportError, AttributeError):
                    from onnx import shape_inference
                    optimized = shape_inference.infer_shapes(model)

            onnx.save(optimized, output_path)
            file_size_mb = os.path.getsize(output_path) / (1024 ** 2)
            self._conversion_info['conversions'].append({
                'format': 'onnx_optimized', 'status': 'success',
                'path': output_path, 'size_mb': file_size_mb
            })
            return output_path
        except Exception as e:
            self._conversion_info['conversions'].append(
                {'format': 'onnx_optimized', 'status': 'failed', 'error': str(e)})
            return None

    def convert_to_tflite(self, onnx_path, output_path):
        if not HAS_ONNX2TF:
            self._conversion_info['conversions'].append(
                {'format': 'tflite', 'status': 'skipped', 'error': 'onnx2tf not installed'})
            return None

        try:
            import subprocess
            result = subprocess.run(
                ['onnx2tf', '-i', str(onnx_path), '-o', str(output_path)],
                capture_output=True, text=True, timeout=300
            )
            if result.returncode == 0:
                tflite_path = str(output_path)
                if os.path.isdir(tflite_path):
                    tflite_path = os.path.join(tflite_path, 'model_float32.tflite')
                file_size_mb = os.path.getsize(tflite_path) / (1024 ** 2) if os.path.exists(tflite_path) else 0
                self._conversion_info['conversions'].append({
                    'format': 'tflite', 'status': 'success',
                    'path': tflite_path, 'size_mb': file_size_mb
                })
                return tflite_path
            self._conversion_info['conversions'].append(
                {'format': 'tflite', 'status': 'failed', 'error': result.stderr[:500]})
            return None
        except Exception as e:
            self._conversion_info['conversions'].append(
                {'format': 'tflite', 'status': 'failed', 'error': str(e)})
            return None

    def benchmark_onnx(self, onnx_path, input_shape=(1, 3, 3, 480, 640), num_runs=50):
        if not HAS_ORT:
            return {'error': 'onnxruntime not installed', 'fps': 0, 'avg_latency_ms': 0}

        try:
            sess_opts = ort.SessionOptions()
            sess_opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            session = ort.InferenceSession(onnx_path, sess_opts)

            input_name = session.get_inputs()[0].name
            dummy = np.random.randn(*input_shape).astype(np.float32)

            for _ in range(5):
                session.run(None, {input_name: dummy})

            times = []
            for _ in range(num_runs):
                start = time.time()
                session.run(None, {input_name: dummy})
                times.append(time.time() - start)

            avg = np.mean(times)
            return {
                'fps': 1.0 / avg, 'avg_latency_ms': avg * 1000,
                'std_latency_ms': np.std(times) * 1000,
                'min_latency_ms': np.min(times) * 1000,
                'max_latency_ms': np.max(times) * 1000,
                'num_runs': num_runs, 'device': 'cpu'
            }
        except Exception as e:
            return {'error': str(e), 'fps': 0, 'avg_latency_ms': 0}

    def get_conversion_info(self):
        return dict(self._conversion_info)


class MobileModelOptimizer:
    def __init__(self, model, device='cpu'):
        if device == 'cuda' and not torch.cuda.is_available():
            device = 'cpu'
        self.device = torch.device(device)
        self.model = model.to(self.device)
        self.model.eval()
        self._profile_data = {}
        self._optimizations_applied = []

    def _count_conv_flops(self, conv, h, w):
        if not isinstance(conv, nn.Conv2d):
            return 0
        cout = conv.out_channels
        cin = conv.in_channels // conv.groups
        kh, kw = conv.kernel_size
        return 2 * cout * cin * kh * kw * h * w

    def profile_model(self, input_shape=(1, 3, 3, 480, 640)):
        hooks = []
        layer_info = []

        def make_hook(layer_name):
            def hook_fn(module, inp, out):
                if isinstance(module, nn.Conv2d):
                    h, w = inp[0].shape[2], inp[0].shape[3]
                    flops = self._count_conv_flops(module, h, w)
                    params = sum(p.numel() for p in module.parameters())
                    mem = sum(p.nelement() * p.element_size() for p in module.parameters()) / (1024 ** 2)
                    layer_info.append({
                        'name': layer_name, 'type': 'Conv2d',
                        'in_channels': module.in_channels,
                        'out_channels': module.out_channels,
                        'kernel_size': list(module.kernel_size),
                        'params': params, 'flops': flops, 'memory_mb': mem
                    })
                elif isinstance(module, nn.Linear):
                    params = sum(p.numel() for p in module.parameters())
                    mem = sum(p.nelement() * p.element_size() for p in module.parameters()) / (1024 ** 2)
                    flops = 2 * module.in_features * module.out_features
                    layer_info.append({
                        'name': layer_name, 'type': 'Linear',
                        'in_features': module.in_features,
                        'out_features': module.out_features,
                        'params': params, 'flops': flops, 'memory_mb': mem
                    })
            return hook_fn

        for name, module in self.model.named_modules():
            if isinstance(module, (nn.Conv2d, nn.Linear)):
                hooks.append(module.register_forward_hook(make_hook(name)))

        dummy = torch.randn(*input_shape).to(self.device)
        with torch.no_grad():
            try:
                self.model(dummy)
            except Exception:
                pass

        for h in hooks:
            h.remove()

        total_params = sum(p.numel() for p in self.model.parameters())
        total_flops = sum(l['flops'] for l in layer_info)
        total_mem = sum(p.nelement() * p.element_size() for p in self.model.parameters()) / (1024 ** 2)

        self._profile_data = {
            'total_params': total_params,
            'total_flops': total_flops,
            'total_flops_gflops': total_flops / 1e9,
            'total_memory_mb': total_mem,
            'num_conv_layers': len([l for l in layer_info if l['type'] == 'Conv2d']),
            'num_linear_layers': len([l for l in layer_info if l['type'] == 'Linear']),
            'layer_details': layer_info,
            'model_type': type(self.model).__name__
        }
        return self._profile_data

    def suggest_optimizations(self, input_shape=(1, 3, 3, 480, 640), target_latency_ms=33):
        if not self._profile_data:
            self.profile_model(input_shape)

        suggestions = []
        profile = self._profile_data
        gflops = profile['total_flops_gflops']
        est_latency_ms = gflops / 10.0 * 1000

        if est_latency_ms > target_latency_ms:
            ratio = target_latency_ms / est_latency_ms
            ch_factor = max(0.25, ratio ** 0.5)
            suggestions.append({
                'type': 'reduce_channels',
                'description': f'Reduce base channels to ~{ch_factor:.0%} of current',
                'factor': ch_factor, 'estimated_speedup': 1.0 / ch_factor
            })

        if profile['num_conv_layers'] > 10:
            suggestions.append({
                'type': 'reduce_res_blocks',
                'description': 'Reduce residual blocks to 2-3',
                'count': 2, 'estimated_speedup': 1.5
            })

        if profile['total_memory_mb'] > 10.0:
            suggestions.append({
                'type': 'use_lightweight',
                'description': 'Switch to LightweightVESPCN architecture',
                'estimated_size_mb': profile['total_memory_mb'] * 0.25,
                'estimated_speedup': 3.0
            })

        suggestions.append({
            'type': 'use_half_precision', 'description': 'Use FP16 half precision',
            'estimated_size_reduction': 0.5,
            'estimated_speedup': 1.5 if self.device.type == 'cuda' else 1.1
        })

        suggestions.append({
            'type': 'use_channel_pruning', 'description': 'Prune 30-50% of channels',
            'amount': 0.3, 'estimated_speedup': 1.3
        })

        suggestions.append({
            'type': 'reduce_input_resolution',
            'description': 'Process at lower resolution and upscale',
            'scale': 0.75, 'estimated_speedup': 1.8
        })

        return suggestions

    def apply_optimizations(self, optimizations_list):
        for opt in optimizations_list:
            otype = opt.get('type')

            if otype == 'use_half_precision':
                self.model = self.model.half()
                self._optimizations_applied.append('half_precision')

            elif otype == 'use_channel_pruning':
                amount = opt.get('amount', 0.3)
                for name, module in self.model.named_modules():
                    if isinstance(module, nn.Conv2d):
                        prune.l1_unstructured(module, name='weight', amount=amount)
                for name, module in self.model.named_modules():
                    if isinstance(module, nn.Conv2d):
                        try:
                            prune.remove(module, 'weight')
                        except ValueError:
                            pass
                self._optimizations_applied.append(f'channel_pruning_{amount}')

            elif otype == 'reduce_channels':
                factor = opt.get('factor', 0.5)
                if isinstance(self.model, VESPCN):
                    new_ch = max(16, int(
                        self.model.super_resolution.conv_in.out_channels * factor))
                    new_model = create_vespcn_model(
                        scale_factor=self.model.scale_factor,
                        base_channels=new_ch, num_residual_blocks=3,
                        device=str(self.device), use_temporal_alignment=False
                    )
                    new_model.apply(initialize_weights)
                    self.model = new_model.to(self.device)
                self._optimizations_applied.append(f'reduce_channels_{factor}')

            elif otype == 'reduce_res_blocks':
                count = opt.get('count', 2)
                if isinstance(self.model, VESPCN):
                    new_model = create_vespcn_model(
                        scale_factor=self.model.scale_factor,
                        num_residual_blocks=count,
                        device=str(self.device), use_temporal_alignment=False
                    )
                    new_model.apply(initialize_weights)
                    self.model = new_model.to(self.device)
                self._optimizations_applied.append(f'reduce_res_blocks_{count}')

            elif otype == 'use_lightweight':
                scale = getattr(self.model, 'scale_factor', 2)
                new_model = create_lightweight_model(scale_factor=scale, device=str(self.device))
                new_model.apply(initialize_weights)
                self.model = new_model.to(self.device)
                self._optimizations_applied.append('switch_to_lightweight')

        self.model.eval()
        return self.model

    def create_mobile_variant(self, base_channels=32, num_res_blocks=2, scale_factor=2):
        model = create_vespcn_model(
            scale_factor=scale_factor, base_channels=base_channels,
            num_residual_blocks=num_res_blocks,
            device=str(self.device), use_temporal_alignment=False
        )
        model.apply(initialize_weights)
        model.eval()

        total_params = sum(p.numel() for p in model.parameters())
        size_mb = sum(p.nelement() * p.element_size() for p in model.parameters()) / (1024 ** 2)

        return {
            'model': model, 'total_params': total_params, 'size_mb': size_mb,
            'base_channels': base_channels, 'num_res_blocks': num_res_blocks,
            'scale_factor': scale_factor
        }


class MobileInferenceEngine:
    def __init__(self, model_path, model_format='onnx', device='cpu'):
        self.model_path = str(model_path)
        self.model_format = model_format
        self.device = device
        self.session = None
        self.torch_model = None
        self.tflite_interpreter = None
        self._inference_stats = {
            'total_inferences': 0, 'total_time_ms': 0.0,
            'fps': 0.0, 'avg_latency_ms': 0.0, 'peak_memory_mb': 0.0
        }

        if model_format == 'onnx':
            if HAS_ORT:
                sess_opts = ort.SessionOptions()
                sess_opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
                sess_opts.intra_op_num_threads = 4
                sess_opts.inter_op_num_threads = 4
                self.session = ort.InferenceSession(model_path, sess_opts)
            else:
                raise RuntimeError("onnxruntime not installed, cannot load ONNX model")
        elif model_format == 'torchscript':
            self.torch_model = torch.jit.load(model_path, map_location=device)
            self.torch_model.eval()
        elif model_format == 'tflite':
            if HAS_TFLITE_RT:
                self.tflite_interpreter = tflite_interp.Interpreter(model_path=model_path)
                self.tflite_interpreter.allocate_tensors()
            elif HAS_TF:
                self.tflite_interpreter = tf.lite.Interpreter(model_path=model_path)
                self.tflite_interpreter.allocate_tensors()
            else:
                raise RuntimeError("tflite-runtime or tensorflow not installed")
        else:
            raise ValueError(f"Unsupported model format: {model_format}")

    def _preprocess(self, frame):
        arr = frame.astype(np.float32) / 255.0
        arr = np.transpose(arr, (2, 0, 1))
        arr = np.expand_dims(arr, axis=0)

        if self.model_format == 'onnx' and self.session is not None:
            input_shape = self.session.get_inputs()[0].shape
            if len(input_shape) == 5:
                arr = np.expand_dims(arr, axis=0)
        return arr

    def _postprocess(self, output):
        if isinstance(output, torch.Tensor):
            output = output.cpu().numpy()
        if isinstance(output, np.ndarray):
            if output.ndim == 5:
                output = output[0, 0]
            elif output.ndim == 4:
                output = output[0]
            if output.ndim == 3:
                output = np.transpose(output, (1, 2, 0))
            output = np.clip(output * 255.0, 0, 255).astype(np.uint8)
        return output

    def inference(self, frame):
        start = time.time()

        if self.model_format == 'onnx' and self.session is not None:
            input_name = self.session.get_inputs()[0].name
            input_data = self._preprocess(frame).astype(np.float32)
            outputs = self.session.run(None, {input_name: input_data})
            result = self._postprocess(outputs[0])

        elif self.model_format == 'torchscript' and self.torch_model is not None:
            input_data = self._preprocess(frame)
            input_tensor = torch.from_numpy(input_data).to(self.device)
            if input_tensor.dim() == 5:
                input_tensor = input_tensor.squeeze(0)
            with torch.no_grad():
                output = self.torch_model(input_tensor)
            result = self._postprocess(output)

        elif self.model_format == 'tflite' and self.tflite_interpreter is not None:
            input_data = self._preprocess(frame).astype(np.float32)
            input_details = self.tflite_interpreter.get_input_details()
            output_details = self.tflite_interpreter.get_output_details()
            self.tflite_interpreter.set_tensor(input_details[0]['index'], input_data)
            self.tflite_interpreter.invoke()
            output = self.tflite_interpreter.get_tensor(output_details[0]['index'])
            result = self._postprocess(output)
        else:
            raise RuntimeError("No valid inference session available")

        elapsed_ms = (time.time() - start) * 1000
        self._update_stats(elapsed_ms)
        return result

    def inference_batch(self, frames):
        return [self.inference(f) for f in frames]

    def _update_stats(self, latency_ms):
        self._inference_stats['total_inferences'] += 1
        self._inference_stats['total_time_ms'] += latency_ms
        n = self._inference_stats['total_inferences']
        total = self._inference_stats['total_time_ms']
        self._inference_stats['avg_latency_ms'] = total / n
        self._inference_stats['fps'] = 1000.0 / (total / n) if total > 0 else 0.0

        try:
            import psutil
            process = psutil.Process(os.getpid())
            self._inference_stats['peak_memory_mb'] = max(
                self._inference_stats['peak_memory_mb'],
                process.memory_info().rss / (1024 ** 2)
            )
        except ImportError:
            pass

    def benchmark(self, num_runs=100, resolution=(480, 640)):
        h, w = resolution
        dummy = np.random.randint(0, 255, (h, w, 3), dtype=np.uint8)

        for _ in range(5):
            self.inference(dummy)

        self._inference_stats = {
            'total_inferences': 0, 'total_time_ms': 0.0,
            'fps': 0.0, 'avg_latency_ms': 0.0, 'peak_memory_mb': 0.0
        }

        latencies = []
        for _ in range(num_runs):
            start = time.time()
            self.inference(dummy)
            latencies.append((time.time() - start) * 1000)

        return {
            'fps': 1000.0 / np.mean(latencies),
            'avg_latency_ms': np.mean(latencies),
            'std_latency_ms': np.std(latencies),
            'min_latency_ms': np.min(latencies),
            'max_latency_ms': np.max(latencies),
            'p50_latency_ms': np.percentile(latencies, 50),
            'p95_latency_ms': np.percentile(latencies, 95),
            'p99_latency_ms': np.percentile(latencies, 99),
            'num_runs': num_runs, 'resolution': resolution,
            'model_format': self.model_format
        }

    def get_inference_stats(self):
        return dict(self._inference_stats)


def deploy_to_mobile(model, config):
    output_dir = Path('mobile_deploy_output')
    output_dir.mkdir(exist_ok=True)

    optimizer = MobileModelOptimizer(model, device='cpu')

    profile = optimizer.profile_model(
        input_shape=(1, 3, 3, config.input_resolution[0], config.input_resolution[1])
    )

    suggestions = optimizer.suggest_optimizations(
        input_shape=(1, 3, 3, config.input_resolution[0], config.input_resolution[1]),
        target_latency_ms=1000.0 / config.target_fps
    )

    optimizations_to_apply = []
    for s in suggestions:
        if s['type'] == 'use_lightweight' and profile['total_memory_mb'] > config.max_model_size_mb:
            optimizations_to_apply.append(s)
        elif s['type'] == 'use_half_precision' and config.use_half:
            optimizations_to_apply.append(s)
        elif s['type'] == 'use_channel_pruning' and profile['total_memory_mb'] > config.max_model_size_mb:
            optimizations_to_apply.append(s)

    optimized_model = optimizer.apply_optimizations(optimizations_to_apply)

    if config.use_half and str(optimized_model.dtype).startswith('torch.float16'):
        optimized_model = optimized_model.float()

    converter = MobileModelConverter(optimized_model, device='cpu')
    base_name = f"vespcn_mobile_{config.target_device}"
    input_shape = (1, 3, 3, config.input_resolution[0], config.input_resolution[1])

    converted_path = None

    if config.model_format == 'onnx':
        onnx_path = output_dir / f"{base_name}.onnx"
        converted_path = converter.convert_to_onnx(str(onnx_path), input_shape=input_shape)
        if converted_path:
            opt_path = output_dir / f"{base_name}_optimized.onnx"
            converter.optimize_onnx(converted_path, str(opt_path))

    elif config.model_format == 'torchscript':
        ts_path = output_dir / f"{base_name}.pt"
        converted_path = converter.convert_to_torchscript(str(ts_path), input_shape=input_shape)

    elif config.model_format == 'tflite':
        onnx_path = output_dir / f"{base_name}.onnx"
        converter.convert_to_onnx(str(onnx_path), input_shape=input_shape)
        tflite_path = output_dir / f"{base_name}.tflite"
        if os.path.exists(str(onnx_path)):
            converted_path = converter.convert_to_tflite(str(onnx_path), str(tflite_path))

    validation_result = {'valid': False, 'error': None}
    if converted_path and os.path.exists(converted_path):
        file_size_mb = os.path.getsize(converted_path) / (1024 ** 2)
        validation_result['valid'] = file_size_mb <= config.max_model_size_mb
        validation_result['size_mb'] = file_size_mb
        validation_result['within_size_limit'] = file_size_mb <= config.max_model_size_mb

        if config.model_format == 'onnx' and HAS_ORT:
            bench = converter.benchmark_onnx(converted_path, input_shape=input_shape, num_runs=20)
            validation_result['benchmark'] = bench
            validation_result['meets_fps_target'] = bench.get('fps', 0) >= config.target_fps

    metadata = {
        'config': {
            'target_device': config.target_device,
            'model_format': config.model_format,
            'input_resolution': config.input_resolution,
            'scale_factor': config.scale_factor,
            'max_model_size_mb': config.max_model_size_mb,
            'target_fps': config.target_fps,
            'use_half': config.use_half,
            'num_threads': config.num_threads
        },
        'profile': {
            'total_params': profile['total_params'],
            'total_flops_gflops': profile['total_flops_gflops'],
            'total_memory_mb': profile['total_memory_mb']
        },
        'optimizations_applied': [s['type'] for s in optimizations_to_apply],
        'conversion_info': converter.get_conversion_info(),
        'validation': validation_result,
        'package_path': str(output_dir)
    }

    return str(output_dir), metadata


def create_mobile_converter(model=None, device='cpu'):
    if model is None:
        model = create_lightweight_model(scale_factor=2, device=device)
        model.apply(initialize_weights)
    return MobileModelConverter(model, device=device)
