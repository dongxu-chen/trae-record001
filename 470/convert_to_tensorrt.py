import os
import sys
import argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
from config import Config
from models import get_model

Config.ensure_dirs()


def convert_model_to_tensorrt(model_name='basnet', max_batch_size=8, 
                              fp16=True, int8=False, 
                              calibration_samples=100):
    print("=" * 60)
    print(f"Converting {model_name.upper()} to TensorRT")
    print("=" * 60)
    
    print(f"\nLoading PyTorch model: {model_name}")
    model = get_model(model_name, pretrained=False, device='cpu')
    
    calibration_data = None
    if int8:
        print(f"\nGenerating calibration data ({calibration_samples} samples)...")
        calibration_data = np.random.randn(
            calibration_samples, 3, Config.IMAGE_SIZE, Config.IMAGE_SIZE
        ).astype(np.float32)
    
    print(f"\nModel export settings:")
    print(f"  Max batch size: {max_batch_size}")
    print(f"  FP16 precision: {fp16}")
    print(f"  INT8 precision: {int8}")
    print(f"  Image size: {Config.IMAGE_SIZE}x{Config.IMAGE_SIZE}")
    
    trt_path = Config.BASNET_TRT if model_name == 'basnet' else Config.POOLNET_TRT
    onnx_path = Config.BASNET_ONNX if model_name == 'basnet' else Config.POOLNET_ONNX
    
    print(f"\nONNX path: {onnx_path}")
    print(f"TensorRT engine path: {trt_path}")
    
    print("\nStarting conversion...")
    success, trt_path = model.export_to_tensorrt(
        trt_path=trt_path,
        input_size=Config.IMAGE_SIZE,
        max_batch_size=max_batch_size,
        fp16=fp16,
        int8=int8,
        calibration_data=calibration_data
    )
    
    if success:
        print("\n" + "=" * 60)
        print("CONVERSION SUCCESSFUL!")
        print("=" * 60)
        print(f"\nTensorRT engine saved to: {trt_path}")
        print("\nYou can now use TensorRT acceleration:")
        print(f"  from core import SaliencyInferencer")
        print(f"  inferencer = SaliencyInferencer(model_name='{model_name}', use_tensorrt=True)")
        return True
    else:
        print("\n" + "=" * 60)
        print("CONVERSION FAILED")
        print("=" * 60)
        return False


def main():
    parser = argparse.ArgumentParser(description='Convert PyTorch models to TensorRT')
    parser.add_argument('--model', '-m', default='basnet', 
                       choices=['basnet', 'poolnet', 'all'],
                       help='Model to convert')
    parser.add_argument('--max-batch-size', '-b', type=int, default=8,
                       help='Maximum batch size for TensorRT engine')
    parser.add_argument('--fp16', action='store_true', default=True,
                       help='Enable FP16 precision')
    parser.add_argument('--int8', action='store_true',
                       help='Enable INT8 precision (requires calibration)')
    parser.add_argument('--calibration-samples', type=int, default=100,
                       help='Number of calibration samples for INT8')
    
    args = parser.parse_args()
    
    models_to_convert = ['basnet', 'poolnet'] if args.model == 'all' else [args.model]
    
    results = []
    for model_name in models_to_convert:
        success = convert_model_to_tensorrt(
            model_name=model_name,
            max_batch_size=args.max_batch_size,
            fp16=args.fp16,
            int8=args.int8,
            calibration_samples=args.calibration_samples
        )
        results.append((model_name, success))
        print("\n" + "=" * 60 + "\n")
    
    print("\nSummary:")
    for model_name, success in results:
        status = "SUCCESS" if success else "FAILED"
        print(f"  {model_name.upper()}: {status}")
    
    all_success = all(success for _, success in results)
    return 0 if all_success else 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except ImportError as e:
        print(f"\nError: TensorRT not available")
        print(f"Please install TensorRT and pycuda:")
        print(f"  pip install tensorrt pycuda")
        print(f"\nOr install from NVIDIA:")
        print(f"  https://developer.nvidia.com/tensorrt")
        sys.exit(1)
