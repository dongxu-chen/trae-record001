import os
import sys
import argparse
import torch
import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.model import create_model
from src.utils import load_checkpoint


def export_to_onnx(config, checkpoint_path, output_path, input_size=(1, 1, 64, 64), simplify=False):
    device = torch.device('cpu')
    
    print("Loading model...")
    model = create_model(config)
    model, _, _, _, _ = load_checkpoint(model, checkpoint_path, None, device)
    model.eval()
    
    dummy_input = torch.randn(input_size, device=device)
    
    print(f"Exporting model to ONNX: {output_path}")
    print(f"Input shape: {input_size}")
    
    torch.onnx.export(
        model,
        dummy_input,
        output_path,
        export_params=True,
        opset_version=12,
        do_constant_folding=True,
        input_names=['input'],
        output_names=['output'],
        dynamic_axes={
            'input': {0: 'batch_size', 2: 'height', 3: 'width'},
            'output': {0: 'batch_size', 2: 'height', 3: 'width'}
        },
        verbose=False
    )
    
    print("ONNX model exported successfully!")
    
    if simplify:
        try:
            import onnx
            from onnxsim import simplify
            
            print("Simplifying ONNX model...")
            onnx_model = onnx.load(output_path)
            model_simp, check = simplify(onnx_model)
            assert check, "Simplified ONNX model could not be validated"
            
            onnx.save(model_simp, output_path)
            print("ONNX model simplified and saved!")
        except ImportError:
            print("onnxsim not installed, skipping simplification")
            print("Install with: pip install onnxsim")
    
    validate_onnx(output_path, dummy_input.numpy())


def validate_onnx(onnx_path, test_input):
    try:
        import onnx
        import onnxruntime as ort
        
        print("Validating ONNX model...")
        
        onnx_model = onnx.load(onnx_path)
        onnx.checker.check_model(onnx_model)
        print("ONNX model check passed!")
        
        ort_session = ort.InferenceSession(onnx_path)
        outputs = ort_session.run(None, {'input': test_input})
        
        print(f"ONNX inference successful! Output shape: {outputs[0].shape}")
        
        return True
    except Exception as e:
        print(f"ONNX validation failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Export RCAN model to ONNX format')
    parser.add_argument('--config', type=str, default='config.yaml', help='Path to config file')
    parser.add_argument('--checkpoint', type=str, required=True, help='Path to PyTorch checkpoint')
    parser.add_argument('--output', type=str, default='models/rcan.onnx', help='Output ONNX model path')
    parser.add_argument('--input_size', type=int, nargs=4, default=[1, 1, 64, 64], 
                       help='Input tensor shape (N C H W), default: 1 1 64 64')
    parser.add_argument('--simplify', action='store_true', help='Simplify ONNX model')
    args = parser.parse_args()
    
    with open(args.config, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    
    export_to_onnx(
        config=config,
        checkpoint_path=args.checkpoint,
        output_path=args.output,
        input_size=tuple(args.input_size),
        simplify=args.simplify
    )


if __name__ == '__main__':
    main()
