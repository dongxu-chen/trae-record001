import os
import sys
import argparse
import torch
import torch.nn as nn

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.style_transfer import TransformerNet, TENSORRT_AVAILABLE


def build_tensorrt_engine(model_path: str, output_path: Optional[str] = None,
                          min_shape: tuple = (1, 3, 240, 320),
                          opt_shape: tuple = (1, 3, 480, 640),
                          max_shape: tuple = (1, 3, 1080, 1920),
                          workspace_size: int = 1) -> bool:
    if not TENSORRT_AVAILABLE:
        print("TensorRT is not available. Please install tensorrt and pycuda.")
        return False

    try:
        import tensorrt as trt
        import pycuda.driver as cuda
        import pycuda.autoinit
    except ImportError as e:
        print(f"Failed to import TensorRT dependencies: {e}")
        print("Please install: pip install tensorrt pycuda")
        return False

    if not os.path.exists(model_path):
        print(f"Model file not found: {model_path}")
        return False

    if output_path is None:
        output_path = os.path.splitext(model_path)[0] + ".trt"

    print(f"Building TensorRT engine for: {model_path}")
    print(f"Output: {output_path}")
    print(f"Dynamic shape range: min={min_shape}, opt={opt_shape}, max={max_shape}")

    try:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        if device.type != "cuda":
            print("CUDA is not available. TensorRT requires GPU.")
            return False

        print("Loading PyTorch model...")
        model = TransformerNet()
        state_dict = torch.load(model_path, map_location=device)

        new_state_dict = {}
        for k, v in state_dict.items():
            if k.startswith('module.'):
                k = k[7:]
            new_state_dict[k] = v

        model.load_state_dict(new_state_dict)
        model.eval()
        model.to(device)
        print("Model loaded successfully")

        print("Exporting to ONNX...")
        onnx_path = os.path.splitext(model_path)[0] + ".onnx"
        dummy_input = torch.randn(opt_shape).to(device)

        torch.onnx.export(
            model, dummy_input, onnx_path,
            export_params=True, opset_version=12,
            do_constant_folding=True,
            input_names=['input'], output_names=['output'],
            dynamic_axes={
                'input': {0: 'batch_size', 2: 'height', 3: 'width'},
                'output': {0: 'batch_size', 2: 'height', 3: 'width'}
            }
        )
        print(f"ONNX model exported: {onnx_path}")

        print("Building TensorRT engine...")
        logger = trt.Logger(trt.Logger.INFO)
        builder = trt.Builder(logger)
        network = builder.create_network(1 << int(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH))
        parser = trt.OnnxParser(network, logger)

        with open(onnx_path, 'rb') as model_file:
            if not parser.parse(model_file.read()):
                print("Failed to parse ONNX model")
                for error in range(parser.num_errors):
                    print(f"  Error {error}: {parser.get_error(error)}")
                return False

        builder_config = builder.create_builder_config()
        builder_config.set_memory_pool_limit(trt.MemoryPoolType.WORKSPACE, workspace_size << 30)

        profile = builder.create_optimization_profile()
        profile.set_shape("input", min_shape, opt_shape, max_shape)
        builder_config.add_optimization_profile(profile)

        if builder.platform_has_fast_fp16:
            print("Enabling FP16 precision")
            builder_config.set_flag(trt.BuilderFlag.FP16)

        print("Building engine (this may take a few minutes)...")
        serialized_engine = builder.build_serialized_network(network, builder_config)
        if serialized_engine is None:
            print("Failed to build TensorRT engine")
            return False

        with open(output_path, "wb") as f:
            f.write(serialized_engine)

        print(f"TensorRT engine saved: {output_path}")
        print(f"Engine size: {os.path.getsize(output_path) / (1024*1024):.1f} MB")

        if os.path.exists(onnx_path):
            os.remove(onnx_path)
            print(f"Cleaned up ONNX file")

        return True

    except Exception as e:
        print(f"Error building TensorRT engine: {e}")
        import traceback
        traceback.print_exc()
        return False


def build_all_engines(models_dir: str = "models", **kwargs) -> int:
    if not os.path.exists(models_dir):
        print(f"Models directory not found: {models_dir}")
        return 0

    success_count = 0
    for filename in os.listdir(models_dir):
        if filename.endswith('.pth') or filename.endswith('.pt'):
            model_path = os.path.join(models_dir, filename)
            style_name = os.path.splitext(filename)[0]
            trt_path = os.path.join(models_dir, f"{style_name}.trt")

            if os.path.exists(trt_path):
                print(f"Skipping {style_name}: TensorRT engine already exists")
                continue

            print(f"\n{'='*50}")
            print(f"Building engine for: {style_name}")
            print(f"{'='*50}")

            if build_tensorrt_engine(model_path, trt_path, **kwargs):
                success_count += 1

    print(f"\n{'='*50}")
    print(f"Built {success_count} TensorRT engines")
    return success_count


def main():
    parser = argparse.ArgumentParser(description="Build TensorRT engines for style transfer models")
    parser.add_argument(
        "--model", type=str, default=None,
        help="Path to a specific .pth model file to convert"
    )
    parser.add_argument(
        "--models-dir", type=str, default="models",
        help="Directory containing .pth models (default: models)"
    )
    parser.add_argument(
        "--all", action="store_true",
        help="Build engines for all .pth models in the models directory"
    )
    parser.add_argument(
        "--min-shape", type=str, default="1,3,240,320",
        help="Minimum input shape (N,C,H,W) for dynamic batch (default: 1,3,240,320)"
    )
    parser.add_argument(
        "--opt-shape", type=str, default="1,3,480,640",
        help="Optimum input shape (N,C,H,W) for dynamic batch (default: 1,3,480,640)"
    )
    parser.add_argument(
        "--max-shape", type=str, default="1,3,1080,1920",
        help="Maximum input shape (N,C,H,W) for dynamic batch (default: 1,3,1080,1920)"
    )
    parser.add_argument(
        "--workspace", type=int, default=1,
        help="Workspace size in GB (default: 1)"
    )

    args = parser.parse_args()

    min_shape = tuple(map(int, args.min_shape.split(',')))
    opt_shape = tuple(map(int, args.opt_shape.split(',')))
    max_shape = tuple(map(int, args.max_shape.split(',')))

    build_kwargs = {
        'min_shape': min_shape,
        'opt_shape': opt_shape,
        'max_shape': max_shape,
        'workspace_size': args.workspace
    }

    if args.model:
        build_tensorrt_engine(args.model, **build_kwargs)
    elif args.all:
        build_all_engines(args.models_dir, **build_kwargs)
    else:
        parser.print_help()
        print("\nExample usage:")
        print("  Build all models: python build_tensorrt.py --all")
        print("  Build specific model: python build_tensorrt.py --model models/starry_night.pth")


if __name__ == "__main__":
    main()
