import os
import sys
import argparse
import time
import numpy as np
import cv2
import torch
from PIL import Image
from tqdm import tqdm
import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.model import create_model
from src.utils import load_checkpoint, calculate_psnr, calculate_ssim, save_image, create_dirs


class SuperResolutionInference:
    def __init__(self, config, checkpoint_path, use_onnx=False):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.config = config
        self.scale = config.get('scale', 4)
        self.use_onnx = use_onnx
        
        if use_onnx:
            self._load_onnx_model(checkpoint_path)
        else:
            self._load_pytorch_model(checkpoint_path)
    
    def _load_pytorch_model(self, checkpoint_path):
        print(f"Loading PyTorch model from {checkpoint_path}")
        self.model = create_model(self.config)
        self.model, _, _, _, _ = load_checkpoint(
            self.model, checkpoint_path, None, self.device
        )
        self.model = self.model.to(self.device)
        self.model.eval()
        print("Model loaded successfully!")
    
    def _load_onnx_model(self, onnx_path):
        print(f"Loading ONNX model from {onnx_path}")
        import onnxruntime as ort
        self.ort_session = ort.InferenceSession(onnx_path)
        self.input_name = self.ort_session.get_inputs()[0].name
        print("ONNX model loaded successfully!")
    
    def _preprocess(self, img_path):
        img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            img = np.array(Image.open(img_path).convert('L'))
        
        h, w = img.shape
        new_h = h - (h % self.scale)
        new_w = w - (w % self.scale)
        if new_h > 0 and new_w > 0:
            img = img[:new_h, :new_w]
        
        img_tensor = torch.from_numpy(img).float().unsqueeze(0).unsqueeze(0) / 255.0
        return img_tensor, img
    
    def _postprocess(self, output_tensor):
        output_tensor = torch.clamp(output_tensor, 0, 1)
        output_img = (output_tensor.squeeze().cpu().numpy() * 255).astype(np.uint8)
        return output_img
    
    def inference_single(self, img_path, save_path=None, hr_path=None):
        lr_tensor, lr_img = self._preprocess(img_path)
        
        start_time = time.time()
        
        if self.use_onnx:
            input_np = lr_tensor.numpy()
            outputs = self.ort_session.run(None, {self.input_name: input_np})
            sr_tensor = torch.from_numpy(outputs[0])
        else:
            with torch.no_grad():
                lr_tensor = lr_tensor.to(self.device)
                sr_tensor = self.model(lr_tensor)
        
        inference_time = time.time() - start_time
        
        sr_img = self._postprocess(sr_tensor)
        
        if save_path:
            save_image(sr_img, save_path)
        
        psnr = None
        ssim = None
        if hr_path and os.path.exists(hr_path):
            hr_img = cv2.imread(hr_path, cv2.IMREAD_GRAYSCALE)
            if hr_img is None:
                hr_img = np.array(Image.open(hr_path).convert('L'))
            h, w = sr_img.shape
            hr_img = hr_img[:h, :w]
            psnr = calculate_psnr(sr_img / 255.0, hr_img / 255.0)
            ssim = calculate_ssim(sr_img / 255.0, hr_img / 255.0)
        
        return sr_img, inference_time, psnr, ssim
    
    def inference_batch(self, input_dir, output_dir, hr_dir=None):
        create_dirs([output_dir])
        
        image_files = sorted([f for f in os.listdir(input_dir) 
                             if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff'))])
        
        print(f"Found {len(image_files)} images for inference")
        
        results = []
        total_time = 0
        
        for img_file in tqdm(image_files, desc="Inference"):
            img_path = os.path.join(input_dir, img_file)
            save_path = os.path.join(output_dir, f"SR_{img_file}")
            
            hr_path = os.path.join(hr_dir, img_file) if hr_dir else None
            
            sr_img, inference_time, psnr, ssim = self.inference_single(
                img_path, save_path, hr_path
            )
            
            total_time += inference_time
            
            results.append({
                'filename': img_file,
                'inference_time': inference_time,
                'psnr': psnr,
                'ssim': ssim
            })
        
        avg_time = total_time / len(image_files)
        print(f"\nBatch inference completed!")
        print(f"Total time: {total_time:.4f}s")
        print(f"Average time per image: {avg_time:.4f}s")
        
        if hr_dir:
            valid_psnrs = [r['psnr'] for r in results if r['psnr'] is not None]
            valid_ssims = [r['ssim'] for r in results if r['ssim'] is not None]
            if valid_psnrs:
                print(f"Average PSNR: {np.mean(valid_psnrs):.4f}")
                print(f"Average SSIM: {np.mean(valid_ssims):.4f}")
        
        return results


def main():
    parser = argparse.ArgumentParser(description='RCAN Inference for Infrared Image Super-Resolution')
    parser.add_argument('--config', type=str, default='config.yaml', help='Path to config file')
    parser.add_argument('--checkpoint', type=str, required=True, help='Path to model checkpoint')
    parser.add_argument('--mode', type=str, choices=['single', 'batch'], default='single', help='Inference mode')
    parser.add_argument('--input', type=str, required=True, help='Input image path or directory')
    parser.add_argument('--output', type=str, default='results', help='Output directory')
    parser.add_argument('--hr', type=str, default=None, help='HR image path or directory (for evaluation)')
    parser.add_argument('--onnx', action='store_true', help='Use ONNX model')
    args = parser.parse_args()
    
    with open(args.config, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    inferencer = SuperResolutionInference(config, args.checkpoint, args.onnx)
    
    if args.mode == 'single':
        sr_img, inference_time, psnr, ssim = inferencer.inference_single(
            args.input, 
            os.path.join(args.output, 'sr_result.png') if args.output else None,
            args.hr
        )
        
        print(f"\nSingle image inference completed!")
        print(f"Inference time: {inference_time:.4f}s")
        if psnr:
            print(f"PSNR: {psnr:.4f} dB")
        if ssim:
            print(f"SSIM: {ssim:.4f}")
        
        if args.output:
            print(f"Result saved to {os.path.join(args.output, 'sr_result.png')}")
    
    else:
        inferencer.inference_batch(args.input, args.output, args.hr)


if __name__ == '__main__':
    main()
