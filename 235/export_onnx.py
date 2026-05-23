import os
import argparse
import torch

from models import ESPCN


def parse_args():
    parser = argparse.ArgumentParser(description='Export ESPCN to ONNX')
    parser.add_argument('--checkpoint', type=str, required=True, help='Path to model checkpoint')
    parser.add_argument('--output', type=str, default='./checkpoints', help='Output directory')
    parser.add_argument('--scale', type=int, default=4, help='Scale factor (2 or 4)')
    parser.add_argument('--input_size', type=int, nargs='+', default=[1, 3, 256, 256], 
                        help='Input tensor size (NCHW format)')
    parser.add_argument('--simplify', action='store_true', help='Simplify ONNX model')
    return parser.parse_args()


def load_model(checkpoint_path, scale_factor):
    checkpoint = torch.load(checkpoint_path, map_location='cpu')
    
    if 'model_state_dict' in checkpoint:
        state_dict = checkpoint['model_state_dict']
    else:
        state_dict = checkpoint
    
    model = ESPCN(scale_factor=scale_factor, num_channels=3, num_features=64)
    model.load_state_dict(state_dict)
    model.eval()
    
    return model


def export_to_onnx(model, output_path, input_size):
    dummy_input = torch.randn(*input_size)
    
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
        }
    )
    
    print(f'Model exported to: {output_path}')
    return output_path


def verify_onnx(onnx_path, input_size):
    import onnx
    import onnxruntime as ort
    import numpy as np
    
    model = onnx.load(onnx_path)
    onnx.checker.check_model(model)
    print('ONNX model checked successfully')
    
    ort_session = ort.InferenceSession(onnx_path, providers=['CPUExecutionProvider'])
    
    dummy_input = np.random.randn(*input_size).astype(np.float32)
    dummy_input = np.clip(dummy_input, 0.0, 1.0)
    
    ort_inputs = {'input': dummy_input}
    ort_outputs = ort_session.run(None, ort_inputs)
    
    print(f'ONNX inference successful. Output shape: {ort_outputs[0].shape}')
    print(f'Output range: [{ort_outputs[0].min():.4f}, {ort_outputs[0].max():.4f}]')
    
    return True


def simplify_onnx(onnx_path, output_path):
    try:
        import onnxsim
        import onnx
        
        model = onnx.load(onnx_path)
        model_simp, check = onnxsim.simplify(model)
        
        if check:
            onnx.save(model_simp, output_path)
            print(f'Model simplified and saved to: {output_path}')
            return output_path
        else:
            print('Simplification check failed. Using original model.')
            return onnx_path
    except ImportError:
        print('onnxsim not installed. Skipping simplification.')
        return onnx_path


def main():
    args = parse_args()
    
    os.makedirs(args.output, exist_ok=True)
    
    model = load_model(args.checkpoint, args.scale)
    print(f'Model loaded. Scale factor: x{args.scale}')
    print(f'Total parameters: {sum(p.numel() for p in model.parameters()):,}')
    
    input_size = tuple(args.input_size)
    print(f'Input size: {input_size}')
    
    basename = os.path.splitext(os.path.basename(args.checkpoint))[0]
    onnx_path = os.path.join(args.output, f'{basename}.onnx')
    
    export_to_onnx(model, onnx_path, input_size)
    
    if args.simplify:
        simplified_path = os.path.join(args.output, f'{basename}_simplified.onnx')
        onnx_path = simplify_onnx(onnx_path, simplified_path)
    
    verify_onnx(onnx_path, input_size)
    
    print('\nExport completed successfully!')


if __name__ == '__main__':
    main()
