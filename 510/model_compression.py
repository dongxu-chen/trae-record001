import torch
import torch.nn as nn
import torch.nn.utils.prune as prune
import torch.quantization as quant
from typing import Dict, List, Tuple, Optional
import numpy as np
from pathlib import Path
import copy

from models import VESPCN, initialize_weights


class ModelPruner:
    def __init__(self, model: nn.Module, device: str = 'cuda'):
        if device == 'cuda' and not torch.cuda.is_available():
            device = 'cpu'
        self.device = torch.device(device)
        self.model = model.to(self.device)
        self.pruned_modules = []

    def get_prunable_modules(self) -> List[Tuple[str, nn.Module]]:
        prunable = []
        for name, module in self.model.named_modules():
            if isinstance(module, (nn.Conv2d, nn.Linear)):
                prunable.append((name, module))
        return prunable

    def prune_by_l1(self, amount: float = 0.3) -> nn.Module:
        for name, module in self.get_prunable_modules():
            if isinstance(module, nn.Conv2d):
                prune.l1_unstructured(module, name='weight', amount=amount)
                self.pruned_modules.append((name, module))
        return self.model

    def prune_by_structured(self, amount: float = 0.3, dim: int = 0) -> nn.Module:
        for name, module in self.get_prunable_modules():
            if isinstance(module, nn.Conv2d):
                prune.ln_structured(module, name='weight', amount=amount, n=2, dim=dim)
                self.pruned_modules.append((name, module))
        return self.model

    def prune_by_magnitude(self, threshold: float = 1e-3) -> nn.Module:
        for name, module in self.get_prunable_modules():
            if isinstance(module, nn.Conv2d):
                prune.remove(module, 'weight')
                weight = module.weight.data
                mask = (torch.abs(weight) > threshold).float()
                module.weight.data = weight * mask
        return self.model

    def remove_pruning_reparametrization(self) -> nn.Module:
        for name, module in self.pruned_modules:
            try:
                prune.remove(module, 'weight')
            except ValueError:
                pass
        self.pruned_modules = []
        return self.model

    def get_sparsity_info(self) -> Dict[str, float]:
        total_params = 0
        zero_params = 0
        for name, module in self.get_prunable_modules():
            if isinstance(module, nn.Conv2d):
                weight = module.weight.data
                total_params += weight.numel()
                zero_params += torch.sum(weight == 0).item()
        sparsity = zero_params / total_params if total_params > 0 else 0
        return {
            'total_params': total_params,
            'zero_params': zero_params,
            'sparsity': sparsity,
            'overall_sparsity': sparsity,
            'remaining_params': total_params - zero_params
        }

    def fine_tune(self, dataloader, criterion, optimizer, epochs: int = 5,
                  device: str = None):
        device = device or str(self.device)
        self.model.train()
        for epoch in range(epochs):
            for batch in dataloader:
                inputs, targets = batch
                inputs = inputs.to(device)
                targets = targets.to(device)
                optimizer.zero_grad()
                outputs = self.model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                optimizer.step()
        self.model.eval()
        return self.model


class ModelQuantizer:
    def __init__(self, model: nn.Module, device: str = 'cuda'):
        if device == 'cuda' and not torch.cuda.is_available():
            device = 'cpu'
        self.device = torch.device(device)
        self.model = model.to(self.device)
        self.quantized_model = None

    def dynamic_quantization(self, dtype: torch.dtype = torch.qint8) -> nn.Module:
        model_cpu = copy.deepcopy(self.model).to('cpu')
        model_cpu.eval()

        quantized_model = quant.quantize_dynamic(
            model_cpu,
            {nn.Conv2d, nn.Linear},
            dtype=dtype
        )
        self.quantized_model = quantized_model
        return quantized_model

    def static_quantization(self, calibration_data: torch.Tensor) -> nn.Module:
        model_cpu = copy.deepcopy(self.model).to('cpu')
        model_cpu.eval()

        model_fused = quant.fuse_modules(
            model_cpu,
            [['conv1', 'relu1'], ['conv2', 'relu2']],
            inplace=False
        )

        model_prepared = quant.prepare(model_fused, inplace=False)

        with torch.no_grad():
            for data in calibration_data:
                model_prepared(data)

        self.quantized_model = quant.convert(model_prepared, inplace=False)
        return self.quantized_model

    def qat_quantization(self, calibration_data: torch.Tensor,
                         num_epochs: int = 1) -> nn.Module:
        model_cpu = copy.deepcopy(self.model).to('cpu')
        model_cpu.train()

        model_qat = quant.prepare_qat(model_cpu, inplace=False)

        optimizer = torch.optim.Adam(model_qat.parameters(), lr=1e-4)
        criterion = nn.MSELoss()

        for epoch in range(num_epochs):
            with torch.no_grad():
                for data in calibration_data:
                    output = model_qat(data)

        model_qat.eval()
        self.quantized_model = quant.convert(model_qat.eval(), inplace=False)
        return self.quantized_model

    def get_model_size_mb(self, model: nn.Module = None) -> float:
        model = model or self.quantized_model or self.model
        param_size = 0
        for param in model.parameters():
            param_size += param.nelement() * param.element_size()
        buffer_size = 0
        for buffer in model.buffers():
            buffer_size += buffer.nelement() * buffer.element_size()
        size_all_mb = (param_size + buffer_size) / 1024 ** 2
        return size_all_mb

    def benchmark_inference(self, model: nn.Module = None,
                            input_size: Tuple = (1, 3, 64, 64),
                            num_runs: int = 100) -> Dict:
        import time
        model = model or self.quantized_model or self.model
        device = next(model.parameters()).device

        dummy_input = torch.randn(input_size).to(device)

        with torch.no_grad():
            for _ in range(10):
                _ = model(dummy_input)

        times = []
        with torch.no_grad():
            for _ in range(num_runs):
                start = time.time()
                _ = model(dummy_input)
                times.append(time.time() - start)

        return {
            'avg_time_ms': np.mean(times) * 1000,
            'std_time_ms': np.std(times) * 1000,
            'fps': 1.0 / np.mean(times),
            'device': str(device)
        }


class ModelCompressor:
    def __init__(self, model: nn.Module, device: str = 'cuda'):
        if device == 'cuda' and not torch.cuda.is_available():
            device = 'cpu'
        self.device = torch.device(device)
        self.model = model.to(self.device)
        self.pruner = ModelPruner(model, device)
        self.quantizer = ModelQuantizer(model, device)
        self.compressed_model = None
        self.compression_history = []

    def prune_and_quantize(self, prune_amount: float = 0.5,
                          quantize: bool = True) -> Tuple[nn.Module, Dict]:
        original_model = copy.deepcopy(self.model)

        pruned_model = self.pruner.prune_by_l1(amount=prune_amount)
        pruned_model = self.pruner.remove_pruning_reparametrization()

        sparsity_info = self.pruner.get_sparsity_info()

        if quantize:
            compressed_model = self.quantizer.dynamic_quantization()
            self.compressed_model = compressed_model
        else:
            compressed_model = pruned_model
            self.compressed_model = compressed_model

        original_size = self.quantizer.get_model_size_mb(original_model)
        compressed_size = self.quantizer.get_model_size_mb(compressed_model)

        original_perf = self.quantizer.benchmark_inference(original_model)
        compressed_perf = self.quantizer.benchmark_inference(compressed_model)

        result = {
            'sparsity': sparsity_info,
            'original_size_mb': original_size,
            'compressed_size_mb': compressed_size,
            'size_compression_ratio': original_size / compressed_size,
            'original_performance': original_perf,
            'compressed_performance': compressed_perf,
            'speedup_ratio': compressed_perf['fps'] / original_perf['fps']
        }

        self.compression_history.append(result)
        return compressed_model, result

    def optimize_for_inference(self, target_fps: float = 15.0,
                               max_iterations: int = 5) -> Tuple[nn.Module, Dict]:
        best_model = None
        best_result = None
        prune_amounts = [0.2, 0.3, 0.4, 0.5, 0.6, 0.7]

        for amount in prune_amounts[:max_iterations]:
            print(f"尝试剪枝比例: {amount:.0%}")
            try:
                model, result = self.prune_and_quantize(prune_amount=amount)
                current_fps = result['compressed_performance']['fps']
                print(f"  FPS: {current_fps:.1f}, 压缩比: {result['size_compression_ratio']:.1f}x")

                if current_fps >= target_fps:
                    best_model = model
                    best_result = result
                    print(f"  ✓ 达到目标FPS {target_fps}!")
                    break

                if best_result is None or current_fps > best_result['compressed_performance']['fps']:
                    best_model = model
                    best_result = result
            except Exception as e:
                print(f"  ✗ 失败: {e}")
                continue

        if best_model is None:
            best_model, best_result = self.prune_and_quantize(prune_amount=0.3)

        self.compressed_model = best_model
        return best_model, best_result

    def save_compressed_model(self, output_path: str):
        if self.compressed_model is not None:
            torch.save(self.compressed_model.state_dict(), output_path)
            print(f"压缩模型已保存到: {output_path}")

    def load_compressed_model(self, model_path: str):
        state_dict = torch.load(model_path, map_location=self.device)
        self.compressed_model = copy.deepcopy(self.model)
        self.compressed_model.load_state_dict(state_dict)
        self.compressed_model.to(self.device)
        self.compressed_model.eval()
        return self.compressed_model


def create_compressor(model: nn.Module, device: str = 'cuda') -> ModelCompressor:
    if device == 'cuda' and not torch.cuda.is_available():
        device = 'cpu'
    return ModelCompressor(model, device)


class InferenceOptimizer:
    def __init__(self, model: nn.Module, device: str = 'cuda'):
        if device == 'cuda' and not torch.cuda.is_available():
            device = 'cpu'
        self.device = torch.device(device)
        self.model = model.to(self.device)
        self.original_state_dict = {k: v.clone() for k, v in model.state_dict().items()}
        self.optimized = False

    def optimize(self, use_half: bool = True, use_channels_last: bool = True,
                use_jit: bool = True, batch_size: int = 1) -> nn.Module:
        self.model.eval()

        if use_channels_last and self.device.type == 'cuda':
            self.model = self.model.to(memory_format=torch.channels_last)

        if use_half and self.device.type == 'cuda':
            self.model = self.model.half()

        if use_jit:
            dummy_input = torch.randn(batch_size, 3, 64, 64).to(self.device)
            if use_half and self.device.type == 'cuda':
                dummy_input = dummy_input.half()
            if use_channels_last and self.device.type == 'cuda':
                dummy_input = dummy_input.to(memory_format=torch.channels_last)

            try:
                with torch.no_grad():
                    self.model = torch.jit.trace(self.model, dummy_input)
                print("✓ JIT 编译成功")
            except Exception as e:
                print(f"✗ JIT 编译失败: {e}")

        self.optimized = True
        return self.model

    def benchmark(self, input_size: Tuple = (1, 3, 128, 128),
                  num_runs: int = 100) -> Dict:
        import time

        dummy_input = torch.randn(input_size).to(self.device)
        if self.optimized and self.device.type == 'cuda':
            dummy_input = dummy_input.half().to(memory_format=torch.channels_last)

        with torch.no_grad():
            for _ in range(10):
                _ = self.model(dummy_input)

        times = []
        with torch.no_grad():
            for _ in range(num_runs):
                start = time.time()
                _ = self.model(dummy_input)
                if self.device.type == 'cuda':
                    torch.cuda.synchronize()
                times.append(time.time() - start)

        return {
            'avg_time_ms': np.mean(times) * 1000,
            'std_time_ms': np.std(times) * 1000,
            'fps': 1.0 / np.mean(times),
            'device': str(self.device),
            'optimized': self.optimized
        }


if __name__ == "__main__":
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"使用设备: {device}")

    model = VESPCN(scale_factor=2)
    model.apply(initialize_weights)

    print("\n=== 模型压缩测试 ===")
    compressor = create_compressor(model, device=device)

    optimized_model, result = compressor.optimize_for_inference(target_fps=15.0)

    print("\n压缩结果:")
    print(f"  稀疏度: {result['sparsity']['sparsity']:.1%}")
    print(f"  原始大小: {result['original_size_mb']:.1f} MB")
    print(f"  压缩大小: {result['compressed_size_mb']:.1f} MB")
    print(f"  压缩比: {result['size_compression_ratio']:.1f}x")
    print(f"  原始FPS: {result['original_performance']['fps']:.1f}")
    print(f"  压缩FPS: {result['compressed_performance']['fps']:.1f}")
    print(f"  加速比: {result['speedup_ratio']:.1f}x")

    print("\n=== 推理优化测试 ===")
    optimizer = InferenceOptimizer(model, device=device)
    optimized = optimizer.optimize()
    perf = optimizer.benchmark()
    print(f"优化后FPS: {perf['fps']:.1f}")
    print(f"平均时间: {perf['avg_time_ms']:.1f} ms")
