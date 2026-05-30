import cv2
import numpy as np
import torch
from collections import deque
import time
import threading
from queue import Queue

import config
from face_detection import FaceDetector, LandmarkDetector
from param_regression import build_model, load_checkpoint
from bfm_model import BFMModel


class OneEuroFilter:
    def __init__(self, min_cutoff=0.004, beta=0.7, d_cutoff=1.0):
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff
        self.x_prev = None
        self.dx_prev = None
        self.t_prev = None
    
    def __call__(self, x, t=None):
        if t is None:
            t = time.time()
        
        if self.x_prev is None:
            self.x_prev = x
            self.dx_prev = np.zeros_like(x)
            self.t_prev = t
            return x
        
        te = t - self.t_prev
        
        a_d = 2.0 * np.pi * self.d_cutoff * te
        alpha_d = a_d / (1.0 + a_d)
        dx = (x - self.x_prev) / te
        dx = alpha_d * dx + (1.0 - alpha_d) * self.dx_prev
        
        cutoff = self.min_cutoff + self.beta * np.abs(dx)
        a = 2.0 * np.pi * cutoff * te
        alpha = a / (1.0 + a)
        
        x_hat = alpha * x + (1.0 - alpha) * self.x_prev
        
        self.x_prev = x_hat
        self.dx_prev = dx
        self.t_prev = t
        
        return x_hat


class SmoothParamsFilter:
    def __init__(self, param_dims, window_size=5):
        self.param_dims = param_dims
        self.window_size = window_size
        self.param_history = {
            name: deque(maxlen=window_size) for name in param_dims
        }
        self.filters = {
            name: OneEuroFilter(min_cutoff=0.01, beta=0.5) 
            for name in param_dims
        }
    
    def smooth(self, params_dict):
        smoothed = {}
        for name, param in params_dict.items():
            if isinstance(param, torch.Tensor):
                param_np = param.detach().cpu().numpy()
            else:
                param_np = param
            
            param_flat = param_np.flatten()
            
            filtered = self.filters[name](param_flat)
            
            self.param_history[name].append(param_flat)
            
            if len(self.param_history[name]) > 1:
                history = np.array(self.param_history[name])
                smoothed_param = np.mean(history, axis=0)
                smoothed_param = 0.7 * filtered + 0.3 * smoothed_param
            else:
                smoothed_param = filtered
            
            smoothed[name] = smoothed_param.reshape(param_np.shape)
        
        return smoothed
    
    def reset(self):
        for name in self.param_history:
            self.param_history[name].clear()
        self.filters = {
            name: OneEuroFilter(min_cutoff=0.01, beta=0.5) 
            for name in self.param_dims
        }


class RealtimeFaceTracker:
    def __init__(self, device='cuda' if torch.cuda.is_available() else 'cpu', 
                 checkpoint_path=None, smooth=True):
        self.device = device
        self.smooth = smooth
        
        self.face_detector = FaceDetector()
        self.landmark_detector = LandmarkDetector()
        self.bfm_model = BFMModel(device=device)
        self.model = build_model(backbone='resnet50', pretrained=True, device=device)
        
        if checkpoint_path and os.path.exists(checkpoint_path):
            self.model, _, _, _ = load_checkpoint(self.model, None, checkpoint_path, device)
        
        self.model.eval()
        
        if smooth:
            self.param_filter = SmoothParamsFilter({
                'shape': config.SHAPE_DIM,
                'exp': config.EXP_DIM,
                'pose': config.POSE_DIM
            })
        
        self.last_face_box = None
        self.tracking = False
        self.frame_count = 0
        
        from torchvision import transforms
        self.transform = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize((config.IMG_SIZE, config.IMG_SIZE)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])
    
    def track_frame(self, frame):
        self.frame_count += 1
        
        faces = self.face_detector.detect(frame)
        
        if len(faces) > 0:
            face_box = faces[0]
            self.last_face_box = face_box
            self.tracking = True
            
            face_aligned, _ = self.face_detector.align_face(frame, face_box, output_size=config.IMG_SIZE)
            
            landmarks = self.landmark_detector.detect_landmarks(face_aligned, (0, 0, config.IMG_SIZE, config.IMG_SIZE))
            
            input_tensor = self.transform(cv2.cvtColor(face_aligned, cv2.COLOR_BGR2RGB))
            input_tensor = input_tensor.unsqueeze(0).to(self.device)
            
            with torch.no_grad():
                params = self.model(input_tensor)
            
            if self.smooth:
                params_np = {k: v.cpu().numpy() for k, v in params.items()}
                params_smooth = self.param_filter.smooth(params_np)
                params = {k: torch.from_numpy(v).to(self.device) for k, v in params_smooth.items()}
            
            return {
                'tracked': True,
                'face_box': face_box,
                'landmarks': landmarks,
                'params': params,
                'face_aligned': face_aligned
            }
        else:
            self.tracking = False
            return {
                'tracked': False,
                'face_box': None,
                'landmarks': None,
                'params': None,
                'face_aligned': None
            }
    
    def get_3d_vertices(self, params):
        shape_param = params['shape']
        exp_param = params['exp']
        pose_param = params['pose']
        
        if isinstance(shape_param, np.ndarray):
            shape_param = torch.from_numpy(shape_param).float().to(self.device)
            exp_param = torch.from_numpy(exp_param).float().to(self.device)
            pose_param = torch.from_numpy(pose_param).float().to(self.device)
        
        if len(shape_param.shape) == 1:
            shape_param = shape_param.unsqueeze(0)
            exp_param = exp_param.unsqueeze(0)
            pose_param = pose_param.unsqueeze(0)
        
        vertices = self.bfm_model.compute_shape(shape_param, exp_param)
        vertices = self.bfm_model.transform_vertices(vertices, pose_param)
        
        return vertices.squeeze(0).cpu().numpy()


class RealtimeVideoDriver:
    def __init__(self, source=0, device='cuda' if torch.cuda.is_available() else 'cpu',
                 show_preview=True, record_fps=False):
        self.source = source
        self.device = device
        self.show_preview = show_preview
        self.record_fps = record_fps
        
        self.tracker = RealtimeFaceTracker(device=device, smooth=True)
        
        self.running = False
        self.frame_queue = Queue(maxsize=30)
        self.result_queue = Queue(maxsize=30)
        
        self.fps_history = deque(maxlen=30)
        self.last_time = time.time()
        
        self.blend_shapes = None
        self.animation_callback = None
    
    def start(self):
        self.running = True
        
        if self.show_preview:
            self._run_with_preview()
        else:
            self._run_background()
    
    def _run_with_preview(self):
        cap = cv2.VideoCapture(self.source)
        
        if not cap.isOpened():
            print(f"Error: Cannot open video source {self.source}")
            return
        
        print("Starting real-time face tracking...")
        print("Press 'q' to quit")
        print("Press 'r' to reset smoothing")
        
        while self.running:
            ret, frame = cap.read()
            if not ret:
                break
            
            current_time = time.time()
            fps = 1.0 / (current_time - self.last_time)
            self.fps_history.append(fps)
            self.last_time = current_time
            
            result = self.tracker.track_frame(frame)
            
            display_frame = frame.copy()
            
            if result['tracked']:
                x, y, w, h = result['face_box']
                cv2.rectangle(display_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                
                landmarks = result['landmarks']
                for pt in landmarks:
                    cv2.circle(display_frame, (int(pt[0] + x), int(pt[1] + y)), 2, (0, 0, 255), -1)
                
                if self.animation_callback:
                    self.animation_callback(result['params'])
            
            avg_fps = np.mean(self.fps_history)
            cv2.putText(display_frame, f"FPS: {avg_fps:.1f}", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            status = "Tracking" if result['tracked'] else "No Face"
            cv2.putText(display_frame, f"Status: {status}", (10, 70), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            cv2.imshow('Real-time 3D Face Driver', display_frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('r'):
                self.tracker.param_filter.reset()
                print("Smoothing reset")
        
        cap.release()
        cv2.destroyAllWindows()
    
    def _run_background(self):
        def capture_thread():
            cap = cv2.VideoCapture(self.source)
            while self.running:
                ret, frame = cap.read()
                if ret and not self.frame_queue.full():
                    self.frame_queue.put(frame)
            cap.release()
        
        def process_thread():
            while self.running:
                if not self.frame_queue.empty():
                    frame = self.frame_queue.get()
                    result = self.tracker.track_frame(frame)
                    if not self.result_queue.full():
                        self.result_queue.put(result)
        
        t1 = threading.Thread(target=capture_thread)
        t2 = threading.Thread(target=process_thread)
        t1.start()
        t2.start()
        
        t1.join()
        t2.join()
    
    def stop(self):
        self.running = False
    
    def get_latest_result(self):
        if not self.result_queue.empty():
            return self.result_queue.get()
        return None
    
    def set_animation_callback(self, callback):
        self.animation_callback = callback


class BlendShapeAnimator:
    def __init__(self, num_blend_shapes=52):
        self.num_blend_shapes = num_blend_shapes
        self.blend_shape_weights = np.zeros(num_blend_shapes)
        self.blend_shape_names = self._get_arkit_names()
    
    def _get_arkit_names(self):
        return [
            'eyeBlinkLeft', 'eyeLookDownLeft', 'eyeLookInLeft', 'eyeLookOutLeft', 'eyeLookUpLeft',
            'eyeSquintLeft', 'eyeWideLeft', 'eyeBlinkRight', 'eyeLookDownRight', 'eyeLookInRight',
            'eyeLookOutRight', 'eyeLookUpRight', 'eyeSquintRight', 'eyeWideRight', 'jawForward',
            'jawLeft', 'jawRight', 'jawOpen', 'mouthClose', 'mouthFunnel', 'mouthPucker', 'mouthLeft',
            'mouthRight', 'mouthSmileLeft', 'mouthSmileRight', 'mouthFrownLeft', 'mouthFrownRight',
            'mouthDimpleLeft', 'mouthDimpleRight', 'mouthStretchLeft', 'mouthStretchRight',
            'mouthRollLower', 'mouthRollUpper', 'mouthShrugLower', 'mouthShrugUpper', 'mouthPressLeft',
            'mouthPressRight', 'mouthLowerDownLeft', 'mouthLowerDownRight', 'mouthUpperUpLeft',
            'mouthUpperUpRight', 'browDownLeft', 'browDownRight', 'browInnerUp', 'browOuterUpLeft',
            'browOuterUpRight', 'cheekPuff', 'cheekSquintLeft', 'cheekSquintRight', 'noseSneerLeft',
            'noseSneerRight', 'tongueOut'
        ]
    
    def compute_from_params(self, params):
        exp_param = params['exp']
        
        if isinstance(exp_param, torch.Tensor):
            exp_param = exp_param.detach().cpu().numpy()
        
        exp_param = exp_param.flatten()
        
        weights = np.zeros(self.num_blend_shapes)
        
        if len(exp_param) >= 29:
            weights[17] = np.clip(exp_param[0] * 2.0, 0, 1)
            
            mouth_corner = np.clip(exp_param[1], -1, 1)
            weights[23] = max(mouth_corner, 0)
            weights[24] = max(mouth_corner, 0)
            weights[25] = max(-mouth_corner, 0)
            weights[26] = max(-mouth_corner, 0)
            
            jaw_open = np.clip(exp_param[2] * 1.5, 0, 1)
            weights[17] = jaw_open
            
            eye_blink = np.clip(exp_param[3] * 2.0, 0, 1)
            weights[0] = eye_blink
            weights[7] = eye_blink
            
            brow_up = np.clip(exp_param[4] * 1.5, 0, 1)
            weights[42] = brow_up
            weights[43] = brow_up
            
            brow_down = np.clip(exp_param[5] * 1.5, 0, 1)
            weights[40] = brow_down
            weights[41] = brow_down
            
            eye_wide = np.clip(exp_param[6] * 2.0, 0, 1)
            weights[6] = eye_wide
            weights[13] = eye_wide
            
            nose_sneer = np.clip(exp_param[7] * 1.5, 0, 1)
            weights[50] = nose_sneer
            weights[51] = nose_sneer
            
            cheek_squint = np.clip(exp_param[8] * 1.5, 0, 1)
            weights[47] = cheek_squint
            weights[48] = cheek_squint
            
            for i in range(min(29, self.num_blend_shapes)):
                weights[i] = max(weights[i], np.abs(exp_param[i]) * 0.3)
        
        self.blend_shape_weights = weights
        return weights
    
    def get_active_blend_shapes(self, threshold=0.1):
        active = []
        for i, weight in enumerate(self.blend_shape_weights):
            if weight > threshold:
                active.append((self.blend_shape_names[i], weight))
        return sorted(active, key=lambda x: -x[1])


def run_realtime_demo():
    driver = RealtimeVideoDriver(source=0, show_preview=True)
    
    animator = BlendShapeAnimator()
    
    def animation_callback(params):
        weights = animator.compute_from_params(params)
        active = animator.get_active_blend_shapes(threshold=0.3)
        if len(active) > 0:
            pass
    
    driver.set_animation_callback(animation_callback)
    driver.start()


if __name__ == '__main__':
    import os
    run_realtime_demo()
