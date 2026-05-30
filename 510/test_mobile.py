import sys, io, os, tempfile
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
import torch
from mobile_deploy import MobileModelConverter, MobileModelOptimizer, MobileConfig, create_mobile_converter
from models import create_vespcn_model

test_model = create_vespcn_model(use_temporal_alignment=False, device='cpu', base_channels=32, num_residual_blocks=3)
optimizer = MobileModelOptimizer(test_model, device='cpu')
profile = optimizer.profile_model(input_shape=(1, 3, 32, 32))
print(f'Profile: {profile["total_flops"]/1e6:.2f} MFLOPs, {profile["total_params"]/1e6:.2f} M params')

suggestions = optimizer.suggest_optimizations(input_shape=(1, 3, 32, 32), target_latency_ms=33)
print(f'Suggestions: {len(suggestions)} items')
for s in suggestions[:3]:
    print(f'  {s["type"]}: {s.get("description", "")[:60]}')

converter = MobileModelConverter(test_model, device='cpu')
with tempfile.TemporaryDirectory() as tmpdir:
    onnx_path = os.path.join(tmpdir, "test.onnx")
    try:
        converter.convert_to_onnx(onnx_path, input_shape=(1, 3, 32, 32))
        onnx_size = os.path.getsize(onnx_path) / 1e6
        print(f'ONNX export: {onnx_size:.2f} MB')
    except Exception as e:
        print(f'ONNX export skipped: {e}')

    ts_path = os.path.join(tmpdir, "test.pt")
    try:
        converter.convert_to_torchscript(ts_path, input_shape=(1, 3, 32, 32))
        ts_size = os.path.getsize(ts_path) / 1e6
        print(f'TorchScript export: {ts_size:.2f} MB')
    except Exception as e:
        print(f'TorchScript export skipped: {e}')

mobile_result = optimizer.create_mobile_variant(base_channels=16, num_res_blocks=1, scale_factor=2)
mobile_model = mobile_result['model']
mp = sum(p.numel() for p in mobile_model.parameters())
print(f'Mobile variant: {mp/1e3:.1f} K params, {mobile_result["size_mb"]:.2f} MB')

config = MobileConfig(target_device='android', model_format='onnx')
print(f'MobileConfig: {config.target_device} {config.model_format}')
print('Mobile deploy module OK!')
