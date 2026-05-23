import os
import cv2
import argparse
import glob
import numpy as np
import torch
from torchvision import transforms
from tqdm import tqdm
from PIL import Image

from models import ESPCN


def parse_args():
    parser = argparse.ArgumentParser(description='ESPCN Video Super Resolution with Temporal Consistency')
    parser.add_argument('--input', type=str, required=True, help='Input video path or image sequence directory')
    parser.add_argument('--output', type=str, default='./video_results', help='Output directory')
    parser.add_argument('--checkpoint', type=str, required=True, help='Path to model checkpoint')
    parser.add_argument('--scale', type=int, default=4, help='Scale factor (2 or 4)')
    parser.add_argument('--device', type=str, default='cuda', help='Device (cuda or cpu)')
    parser.add_argument('--fps', type=int, default=30, help='Output video FPS')
    parser.add_argument('--temporal_alpha', type=float, default=0.3, help='Temporal consistency weight')
    parser.add_argument('--use_flow', action='store_true', help='Use optical flow for temporal consistency')
    parser.add_argument('--flow_method', type=str, default='farneback', help='Optical flow method: farneback, tvl1')
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


def compute_optical_flow(prev_frame, curr_frame, method='farneback'):
    prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
    curr_gray = cv2.cvtColor(curr_frame, cv2.COLOR_BGR2GRAY)
    
    if method == 'farneback':
        flow = cv2.calcOpticalFlowFarneback(
            prev_gray, curr_gray, None,
            pyr_scale=0.5, levels=3, winsize=15,
            iterations=3, poly_n=5, poly_sigma=1.2,
            flags=0
        )
    elif method == 'tvl1':
        dtvl1 = cv2.optflow.DualTVL1OpticalFlow_create()
        flow = dtvl1.calc(prev_gray, curr_gray, None)
    else:
        raise ValueError(f'Unknown flow method: {method}')
    
    return flow


def warp_flow(img, flow):
    h, w = flow.shape[:2]
    flow_map = np.zeros_like(flow)
    
    for y in range(h):
        for x in range(w):
            fx, fy = flow[y, x]
            new_x = int(x + fx + 0.5)
            new_y = int(y + fy + 0.5)
            
            if 0 <= new_x < w and 0 <= new_y < h:
                flow_map[new_y, new_x] = img[y, x]
    
    return flow_map


def apply_temporal_consistency(curr_sr, prev_sr_warped, alpha=0.3):
    blended = alpha * prev_sr_warped + (1 - alpha) * curr_sr
    return np.clip(blended, 0, 255).astype(np.uint8)


def super_resolve_frame(model, frame, device):
    transform = transforms.ToTensor()
    
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    frame_pil = Image.fromarray(frame_rgb)
    
    lr_tensor = transform(frame_pil).unsqueeze(0).to(device)
    
    with torch.no_grad():
        sr_tensor = model(lr_tensor)
    
    sr_np = sr_tensor.squeeze(0).permute(1, 2, 0).cpu().numpy()
    sr_np = np.clip(sr_np * 255, 0, 255).astype(np.uint8)
    sr_bgr = cv2.cvtColor(sr_np, cv2.COLOR_RGB2BGR)
    
    return sr_bgr


def extract_frames(video_path, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    
    cap = cv2.VideoCapture(video_path)
    frame_count = 0
    
    pbar = tqdm(desc='Extracting frames')
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        frame_path = os.path.join(output_dir, f'frame_{frame_count:06d}.png')
        cv2.imwrite(frame_path, frame)
        frame_count += 1
        pbar.update(1)
    
    pbar.close()
    cap.release()
    
    print(f'Extracted {frame_count} frames')
    return output_dir, frame_count


def video_to_frames_generator(video_path):
    cap = cv2.VideoCapture(video_path)
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        yield frame
    
    cap.release()


def frames_generator_from_dir(dir_path):
    image_extensions = ['*.png', '*.jpg', '*.jpeg', '*.bmp']
    frame_paths = []
    
    for ext in image_extensions:
        frame_paths.extend(glob.glob(os.path.join(dir_path, ext)))
    
    frame_paths = sorted(frame_paths)
    
    for path in frame_paths:
        frame = cv2.imread(path)
        if frame is not None:
            yield frame


def process_video(model, input_path, output_dir, device, scale_factor, 
                  fps=30, alpha=0.3, use_flow=False, flow_method='farneback'):
    os.makedirs(output_dir, exist_ok=True)
    
    sr_frames_dir = os.path.join(output_dir, 'sr_frames')
    os.makedirs(sr_frames_dir, exist_ok=True)
    
    if os.path.isfile(input_path):
        frame_gen = video_to_frames_generator(input_path)
        cap = cv2.VideoCapture(input_path)
        orig_fps = cap.get(cv2.CAP_PROP_FPS)
        orig_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        orig_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        if orig_fps > 0:
            fps = orig_fps
    elif os.path.isdir(input_path):
        frame_gen = frames_generator_from_dir(input_path)
    else:
        raise ValueError(f'Input path does not exist: {input_path}')
    
    prev_sr = None
    prev_lr = None
    frame_idx = 0
    
    pbar = tqdm(desc='Processing video')
    
    for frame in frame_gen:
        lr_frame = frame
        
        if use_flow and prev_lr is not None:
            flow = compute_optical_flow(prev_lr, lr_frame, method=flow_method)
            
            flow_scaled = cv2.resize(flow, None, fx=scale_factor, fy=scale_factor, 
                                    interpolation=cv2.INTER_LINEAR)
            flow_scaled *= scale_factor
            
            curr_sr = super_resolve_frame(model, lr_frame, device)
            
            if prev_sr is not None:
                prev_sr_warped = warp_flow(prev_sr, flow_scaled)
                curr_sr = apply_temporal_consistency(curr_sr, prev_sr_warped, alpha=alpha)
        else:
            curr_sr = super_resolve_frame(model, lr_frame, device)
        
        sr_frame_path = os.path.join(sr_frames_dir, f'frame_{frame_idx:06d}.png')
        cv2.imwrite(sr_frame_path, curr_sr)
        
        prev_sr = curr_sr
        prev_lr = lr_frame
        frame_idx += 1
        pbar.update(1)
    
    pbar.close()
    
    output_video_path = os.path.join(output_dir, 'video_sr.mp4')
    frames_to_video(sr_frames_dir, output_video_path, fps=fps)
    
    print(f'Processed {frame_idx} frames')
    print(f'Output video saved to: {output_video_path}')
    
    return output_video_path


def frames_to_video(frames_dir, output_path, fps=30):
    image_extensions = ['*.png', '*.jpg', '*.jpeg']
    frame_paths = []
    
    for ext in image_extensions:
        frame_paths.extend(glob.glob(os.path.join(frames_dir, ext)))
    
    frame_paths = sorted(frame_paths)
    
    if len(frame_paths) == 0:
        raise ValueError(f'No frames found in {frames_dir}')
    
    first_frame = cv2.imread(frame_paths[0])
    height, width = first_frame.shape[:2]
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    for path in tqdm(frame_paths, desc='Writing video'):
        frame = cv2.imread(path)
        out.write(frame)
    
    out.release()
    print(f'Video saved to: {output_path}')


def main():
    args = parse_args()
    
    device = torch.device(args.device if torch.cuda.is_available() else 'cpu')
    print(f'Using device: {device}')
    
    model = load_model(args.checkpoint, args.scale, device)
    print(f'Model loaded. Scale factor: x{model.scale_factor}')
    
    print(f'Temporal consistency: {"Enabled" if args.use_flow else "Disabled"}')
    if args.use_flow:
        print(f'Flow method: {args.flow_method}')
        print(f'Temporal alpha: {args.temporal_alpha}')
    
    try:
        process_video(
            model,
            args.input,
            args.output,
            device,
            args.scale,
            fps=args.fps,
            alpha=args.temporal_alpha,
            use_flow=args.use_flow,
            flow_method=args.flow_method
        )
    except Exception as e:
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
