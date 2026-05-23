import os
import sys
import argparse
import time
import numpy as np
import cv2
import torch
import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.model import create_model
from src.utils import load_checkpoint
from src.thermal_enhance import ThermalEnhancer


class RealtimeSuperResolution:
    def __init__(self, config, checkpoint_path, colormap='jet', use_onnx=False):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.scale = config.get('scale', 4)
        self.use_onnx = use_onnx
        
        print(f"Loading model... (Device: {self.device})")
        if use_onnx:
            import onnxruntime as ort
            self.ort_session = ort.InferenceSession(checkpoint_path)
            self.input_name = self.ort_session.get_inputs()[0].name
        else:
            self.model = create_model(config)
            self.model, _, _, _, _ = load_checkpoint(
                self.model, checkpoint_path, None, self.device
            )
            self.model = self.model.to(self.device)
            self.model.eval()
        
        self.thermal_enhancer = ThermalEnhancer(colormap)
        print("Model loaded successfully!")
    
    def preprocess(self, frame):
        if len(frame.shape) == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            gray = frame
        
        h, w = gray.shape
        new_h = h - (h % self.scale)
        new_w = w - (w % self.scale)
        if new_h > 0 and new_w > 0:
            gray = gray[:new_h, :new_w]
        
        tensor = torch.from_numpy(gray).float().unsqueeze(0).unsqueeze(0) / 255.0
        return tensor, gray
    
    def postprocess(self, output_tensor):
        output_tensor = torch.clamp(output_tensor, 0, 1)
        sr_img = (output_tensor.squeeze().cpu().numpy() * 255).astype(np.uint8)
        return sr_img
    
    def super_resolve(self, frame):
        input_tensor, lr_gray = self.preprocess(frame)
        
        if self.use_onnx:
            input_np = input_tensor.numpy()
            outputs = self.ort_session.run(None, {self.input_name: input_np})
            sr_tensor = torch.from_numpy(outputs[0])
        else:
            with torch.no_grad():
                input_tensor = input_tensor.to(self.device)
                sr_tensor = self.model(input_tensor)
        
        sr_img = self.postprocess(sr_tensor)
        return sr_img, lr_gray
    
    def enhance_thermal(self, sr_img, colormap=None):
        return self.thermal_enhancer.enhance(
            sr_img, 
            colormap=colormap,
            enhance_contrast=True,
            show_temperature_scale=True
        )
    
    def process_frame(self, frame, show_lr=True, show_heatmap=True):
        sr_img, lr_gray = self.super_resolve(frame)
        
        h, w = sr_img.shape
        
        display_frames = []
        
        if show_lr:
            lr_display = cv2.resize(lr_gray, (w, h), interpolation=cv2.INTER_NEAREST)
            lr_display = cv2.cvtColor(lr_display, cv2.COLOR_GRAY2BGR)
            cv2.putText(lr_display, 'LR Input', (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            display_frames.append(lr_display)
        
        sr_bgr = cv2.cvtColor(sr_img, cv2.COLOR_GRAY2BGR)
        cv2.putText(sr_bgr, f'SR x{self.scale}', (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        display_frames.append(sr_bgr)
        
        if show_heatmap:
            heatmap = self.enhance_thermal(sr_img)
            cv2.putText(heatmap, 'Thermal Heatmap', (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            display_frames.append(heatmap)
        
        combined = np.hstack(display_frames)
        return combined, sr_img


class CameraCapture:
    def __init__(self, camera_id=0, width=320, height=240, fps=30):
        self.camera_id = camera_id
        self.width = width
        self.height = height
        self.fps = fps
        
        self.cap = cv2.VideoCapture(camera_id)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.cap.set(cv2.CAP_PROP_FPS, fps)
        
        if not self.cap.isOpened():
            raise RuntimeError(f"Failed to open camera {camera_id}")
        
        actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps = int(self.cap.get(cv2.CAP_PROP_FPS))
        print(f"Camera opened: {actual_width}x{actual_height} @ {actual_fps}fps")
    
    def read(self):
        ret, frame = self.cap.read()
        if not ret:
            return None
        return frame
    
    def release(self):
        self.cap.release()


def run_realtime_inference(config, checkpoint_path, camera_id=0, 
                            colormap='jet', use_onnx=False,
                            record_video=False, output_path='output.mp4'):
    sr_system = RealtimeSuperResolution(config, checkpoint_path, colormap, use_onnx)
    
    camera = CameraCapture(camera_id, width=320, height=240)
    
    fps_counter = 0
    fps_timer = time.time()
    current_fps = 0
    
    out = None
    if record_video:
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, 10.0, (1920, 480))
    
    print("\nStarting real-time super-resolution...")
    print("Press 'q' to quit")
    print("Press 's' to save current frame")
    print("Press 'c' to change colormap")
    
    colormaps = ['jet', 'hot', 'inferno', 'plasma', 'turbo', 'ironbow']
    colormap_idx = 0
    
    try:
        while True:
            frame = camera.read()
            if frame is None:
                print("Failed to capture frame")
                break
            
            start_time = time.time()
            
            combined, sr_img = sr_system.process_frame(
                frame, 
                show_lr=True, 
                show_heatmap=True
            )
            
            process_time = (time.time() - start_time) * 1000
            
            fps_counter += 1
            if time.time() - fps_timer >= 1.0:
                current_fps = fps_counter
                fps_counter = 0
                fps_timer = time.time()
            
            cv2.putText(combined, f'FPS: {current_fps:.1f}', 
                       (10, combined.shape[0] - 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(combined, f'Latency: {process_time:.1f}ms', 
                       (combined.shape[1] - 200, combined.shape[0] - 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            if out is not None:
                out.write(combined)
            
            cv2.imshow('Real-Time Thermal Super-Resolution', combined)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                save_path = f'results/sr_frame_{timestamp}.png'
                cv2.imwrite(save_path, combined)
                print(f"Frame saved to {save_path}")
            elif key == ord('c'):
                colormap_idx = (colormap_idx + 1) % len(colormaps)
                sr_system.thermal_enhancer.color_mapper.colormap = colormaps[colormap_idx]
                print(f"Colormap changed to: {colormaps[colormap_idx]}")
    
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    finally:
        camera.release()
        if out is not None:
            out.release()
        cv2.destroyAllWindows()
        print("Camera released")


def process_video_file(config, checkpoint_path, input_path, output_path,
                       colormap='jet', use_onnx=False):
    sr_system = RealtimeSuperResolution(config, checkpoint_path, colormap, use_onnx)
    
    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        raise RuntimeError(f"Failed to open video file: {input_path}")
    
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    print(f"Video: {width}x{height} @ {fps}fps, {total_frames} frames")
    
    sr_width = width * sr_system.scale
    sr_height = height * sr_system.scale
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (sr_width * 2, sr_height))
    
    frame_count = 0
    start_time = time.time()
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            combined, _ = sr_system.process_frame(frame, show_lr=False, show_heatmap=True)
            out.write(combined)
            
            frame_count += 1
            if frame_count % 10 == 0:
                elapsed = time.time() - start_time
                eta = (total_frames - frame_count) * elapsed / frame_count
                print(f"Processed: {frame_count}/{total_frames} frames, "
                      f"ETA: {eta:.1f}s", end='\r')
    
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    finally:
        cap.release()
        out.release()
        print(f"\nVideo saved to {output_path}")


def main():
    parser = argparse.ArgumentParser(description='Real-Time Thermal Super-Resolution')
    parser.add_argument('--config', type=str, default='config.yaml', help='Path to config file')
    parser.add_argument('--checkpoint', type=str, required=True, help='Path to model checkpoint')
    parser.add_argument('--mode', type=str, choices=['camera', 'video'], default='camera', 
                       help='Operation mode')
    parser.add_argument('--camera', type=int, default=0, help='Camera ID')
    parser.add_argument('--input', type=str, help='Input video path')
    parser.add_argument('--output', type=str, default='results/output.mp4', help='Output video path')
    parser.add_argument('--colormap', type=str, default='jet', help='Thermal colormap')
    parser.add_argument('--onnx', action='store_true', help='Use ONNX model')
    parser.add_argument('--record', action='store_true', help='Record camera output')
    args = parser.parse_args()
    
    with open(args.config, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    os.makedirs('results', exist_ok=True)
    
    if args.mode == 'camera':
        run_realtime_inference(
            config=config,
            checkpoint_path=args.checkpoint,
            camera_id=args.camera,
            colormap=args.colormap,
            use_onnx=args.onnx,
            record_video=args.record,
            output_path=args.output
        )
    elif args.mode == 'video':
        if not args.input:
            parser.error("--input is required for video mode")
        process_video_file(
            config=config,
            checkpoint_path=args.checkpoint,
            input_path=args.input,
            output_path=args.output,
            colormap=args.colormap,
            use_onnx=args.onnx
        )


if __name__ == '__main__':
    main()
