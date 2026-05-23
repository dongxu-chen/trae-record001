import os
import gc
import argparse
import glob
import torch
from PIL import Image
from torchvision import transforms
from tqdm import tqdm

from models import ESPCN
from utils.metrics import calculate_psnr, calculate_ssim, AverageMeter


def parse_args():
    parser = argparse.ArgumentParser(description='ESPCN Super Resolution Inference')
    parser.add_argument('--input', type=str, required=True, help='Input image path or directory')
    parser.add_argument('--output', type=str, default='./results', help='Output directory')
    parser.add_argument('--checkpoint', type=str, required=True, help='Path to model checkpoint')
    parser.add_argument('--scale', type=int, default=4, help='Scale factor (2 or 4)')
    parser.add_argument('--reference', type=str, default=None, help='Reference HR image path for evaluation')
    parser.add_argument('--device', type=str, default='cuda', help='Device (cuda or cpu)')
    parser.add_argument('--batch_size', type=int, default=1, help='Batch size for processing')
    return parser.parse_args()


def load_model(checkpoint_path, scale_factor, device):
    checkpoint = torch.load(checkpoint_path, map_location=device)
    
    if 'model_state_dict' in checkpoint:
        state_dict = checkpoint['model_state_dict']
    else:
        state_dict = checkpoint
    
    model = ESPCN(scale_factor=scale_factor, num_channels=3, num_features=64).to(device)
    model.load_state_dict(state_dict)
    model.eval()
    
    return model


def image_loader_generator(image_paths, batch_size=1):
    transform = transforms.ToTensor()
    
    for i in range(0, len(image_paths), batch_size):
        batch_paths = image_paths[i:i + batch_size]
        batch_tensors = []
        batch_images = []
        
        for img_path in batch_paths:
            img = Image.open(img_path).convert('RGB')
            img_tensor = transform(img)
            batch_tensors.append(img_tensor)
            batch_images.append(img)
        
        batch_tensor = torch.stack(batch_tensors, dim=0)
        yield batch_tensor, batch_paths, batch_images
        
        del batch_tensor, batch_tensors, batch_images
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()


def preprocess_batch(batch_tensor, device):
    return batch_tensor.to(device)


def postprocess_batch(tensor_batch):
    images = []
    for i in range(tensor_batch.size(0)):
        tensor = tensor_batch[i].clamp(0.0, 1.0)
        img = transforms.ToPILImage()(tensor)
        images.append(img)
    return images


def super_resolve_single(model, image_path, output_dir, device, reference_path=None):
    os.makedirs(output_dir, exist_ok=True)
    
    transform = transforms.ToTensor()
    img = Image.open(image_path).convert('RGB')
    lr_tensor = transform(img).unsqueeze(0).to(device)
    
    with torch.no_grad():
        sr_tensor = model(lr_tensor)
    
    sr_img = transforms.ToPILImage()(sr_tensor[0].clamp(0.0, 1.0))
    
    basename = os.path.splitext(os.path.basename(image_path))[0]
    output_path = os.path.join(output_dir, f'{basename}_x{model.scale_factor}.png')
    sr_img.save(output_path)
    
    metrics = {}
    if reference_path and os.path.exists(reference_path):
        hr_img = Image.open(reference_path).convert('RGB')
        hr_tensor = transform(hr_img).unsqueeze(0).to(device)
        
        psnr = calculate_psnr(sr_tensor, hr_tensor, crop_border=model.scale_factor)
        ssim = calculate_ssim(sr_tensor, hr_tensor, crop_border=model.scale_factor)
        
        metrics['PSNR'] = psnr
        metrics['SSIM'] = ssim
        
        print(f'{basename}: PSNR = {psnr:.2f} dB, SSIM = {ssim:.4f}')
        
        del hr_tensor
    
    del lr_tensor, sr_tensor
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    
    return output_path, metrics


def super_resolve_batch(model, input_dir, output_dir, device, reference_dir=None, batch_size=1):
    os.makedirs(output_dir, exist_ok=True)
    
    image_extensions = ['*.png', '*.jpg', '*.jpeg', '*.bmp']
    image_paths = []
    for ext in image_extensions:
        image_paths.extend(glob.glob(os.path.join(input_dir, ext)))
    image_paths = sorted(image_paths)
    
    if len(image_paths) == 0:
        print(f'No images found in {input_dir}')
        return
    
    print(f'Found {len(image_paths)} images for processing')
    print(f'Using batch size: {batch_size}')
    
    psnr_meter = AverageMeter()
    ssim_meter = AverageMeter()
    
    total_batches = (len(image_paths) + batch_size - 1) // batch_size
    
    for batch_idx, (batch_tensor, batch_paths, _) in enumerate(tqdm(
        image_loader_generator(image_paths, batch_size), 
        total=total_batches, 
        desc='Processing'
    )):
        lr_batch = preprocess_batch(batch_tensor, device)
        
        with torch.no_grad():
            sr_batch = model(lr_batch)
        
        sr_images = postprocess_batch(sr_batch)
        
        for idx, (img_path, sr_img) in enumerate(zip(batch_paths, sr_images)):
            basename = os.path.splitext(os.path.basename(img_path))[0]
            output_path = os.path.join(output_dir, f'{basename}_x{model.scale_factor}.png')
            sr_img.save(output_path)
            
            if reference_dir and os.path.exists(reference_dir):
                ref_path = os.path.join(reference_dir, os.path.basename(img_path))
                if os.path.exists(ref_path):
                    transform = transforms.ToTensor()
                    hr_img = Image.open(ref_path).convert('RGB')
                    hr_tensor = transform(hr_img).unsqueeze(0).to(device)
                    
                    psnr = calculate_psnr(sr_batch[idx:idx+1], hr_tensor, crop_border=model.scale_factor)
                    ssim = calculate_ssim(sr_batch[idx:idx+1], hr_tensor, crop_border=model.scale_factor)
                    
                    psnr_meter.update(psnr)
                    ssim_meter.update(ssim)
                    
                    del hr_tensor
        
        del lr_batch, sr_batch, sr_images
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    
    if psnr_meter.count > 0:
        print(f'\nAverage PSNR: {psnr_meter.avg:.2f} dB')
        print(f'Average SSIM: {ssim_meter.avg:.4f}')


def main():
    args = parse_args()
    
    device = torch.device(args.device if torch.cuda.is_available() else 'cpu')
    print(f'Using device: {device}')
    
    model = load_model(args.checkpoint, args.scale, device)
    print(f'Model loaded. Scale factor: x{model.scale_factor}')
    
    if os.path.isfile(args.input):
        print(f'Processing single image: {args.input}')
        output_path, metrics = super_resolve_single(
            model, args.input, args.output, device, args.reference
        )
        print(f'Result saved to: {output_path}')
    elif os.path.isdir(args.input):
        print(f'Processing batch images from: {args.input}')
        super_resolve_batch(model, args.input, args.output, device, args.reference, args.batch_size)
    else:
        print(f'Input path does not exist: {args.input}')


if __name__ == '__main__':
    main()
