import cv2
import numpy as np
import os
from typing import List, Tuple, Optional, Callable
from panorama_stitcher import PanoramaStitcher
from feature_matcher import FeatureMatcher
from homography import HomographyEstimator


class VideoPanoramaStitcher:
    def __init__(self, projection_type: str = 'plane',
                 blend_type: str = 'multiband',
                 temporal_smoothing: bool = True,
                 smoothing_window: int = 5,
                 keyframe_interval: int = 30):
        self.projection_type = projection_type
        self.blend_type = blend_type
        self.temporal_smoothing = temporal_smoothing
        self.smoothing_window = smoothing_window
        self.keyframe_interval = keyframe_interval
        
        self.stitcher = PanoramaStitcher(
            projection_type=projection_type,
            blend_type=blend_type
        )
        
        self.feature_matcher = FeatureMatcher()
        self.homography_estimator = HomographyEstimator()
        
        self.frame_buffer = []
        self.homography_history = []
        self.keyframes = []
        
    def extract_frames(self, video_path: str, 
                       max_frames: Optional[int] = None,
                       frame_interval: int = 1,
                       start_frame: int = 0) -> List[np.ndarray]:
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            raise ValueError(f'无法打开视频: {video_path}')
        
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        print(f'视频信息: {total_frames}帧, {fps:.2f}fps')
        
        frames = []
        frame_count = 0
        
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        
        while True:
            ret, frame = cap.read()
            
            if not ret:
                break
            
            if frame_count % frame_interval == 0:
                frames.append(frame)
                
                if max_frames is not None and len(frames) >= max_frames:
                    break
            
            frame_count += 1
        
        cap.release()
        
        print(f'提取了 {len(frames)} 帧')
        
        return frames

    def stabilize_frames(self, frames: List[np.ndarray]) -> List[np.ndarray]:
        if len(frames) < 2:
            return frames
        
        stabilized = [frames[0]]
        
        prev_gray = cv2.cvtColor(frames[0], cv2.COLOR_BGR2GRAY)
        
        for i in range(1, len(frames)):
            curr_gray = cv2.cvtColor(frames[i], cv2.COLOR_BGR2GRAY)
            
            kp1, des1 = self.feature_matcher.detect_and_compute(prev_gray)
            kp2, des2 = self.feature_matcher.detect_and_compute(curr_gray)
            
            matches = self.feature_matcher.match_features(des1, des2)
            
            if len(matches) < 10:
                stabilized.append(frames[i])
                continue
            
            pts1, pts2 = self.feature_matcher.get_matched_points(kp1, kp2, matches)
            
            H, mask = self.homography_estimator.estimate_homography(pts1, pts2)
            
            if H is not None:
                self.homography_history.append(H)
                
                h, w = frames[i].shape[:2]
                stabilized_frame = cv2.warpPerspective(
                    frames[i], H, (w, h),
                    flags=cv2.INTER_LINEAR,
                    borderMode=cv2.BORDER_REPLICATE
                )
                stabilized.append(stabilized_frame)
            else:
                stabilized.append(frames[i])
            
            prev_gray = curr_gray
        
        return stabilized

    def smooth_homographies(self) -> List[np.ndarray]:
        if len(self.homography_history) < 3:
            return self.homography_history
        
        smoothed = []
        window = self.smoothing_window
        
        for i in range(len(self.homography_history)):
            start = max(0, i - window // 2)
            end = min(len(self.homography_history), i + window // 2 + 1)
            
            H_avg = np.zeros_like(self.homography_history[i])
            
            weights = np.array([1.0 / (abs(i - j) + 1) for j in range(start, end)])
            weights /= np.sum(weights)
            
            for idx, j in enumerate(range(start, end)):
                H_avg += self.homography_history[j] * weights[idx]
            
            H_avg[2, :] = [0, 0, 1]
            
            smoothed.append(H_avg)
        
        return smoothed

    def stitch_video_frames(self, frames: List[np.ndarray],
                            output_path: str = 'output_panorama.jpg',
                            stabilize: bool = True,
                            verbose: bool = True) -> np.ndarray:
        if len(frames) == 0:
            raise ValueError('没有帧可拼接')
        
        if len(frames) == 1:
            cv2.imwrite(output_path, frames[0])
            return frames[0]
        
        if stabilize and len(frames) > 1:
            if verbose:
                print('正在稳定帧...')
            frames = self.stabilize_frames(frames)
        
        keyframes = self._select_keyframes(frames)
        
        if verbose:
            print(f'选择了 {len(keyframes)} 个关键帧')
        
        if len(keyframes) == 1:
            result = keyframes[0]
        else:
            if verbose:
                print('正在拼接关键帧...')
            
            self.stitcher.set_images(keyframes)
            self.stitcher.extract_features()
            self.stitcher.estimate_homographies()
            self.stitcher.warp_images()
            result = self.stitcher.blend_images()
        
        cv2.imwrite(output_path, result)
        
        if verbose:
            print(f'结果已保存到: {output_path}')
        
        return result

    def _select_keyframes(self, frames: List[np.ndarray]) -> List[np.ndarray]:
        if len(frames) <= self.keyframe_interval:
            return frames
        
        keyframes = []
        for i in range(0, len(frames), self.keyframe_interval):
            keyframes.append(frames[i])
        
        keyframes.append(frames[-1])
        
        return keyframes

    def stitch_video_to_video(self, video_path: str,
                              output_video_path: str,
                              window_size: int = 30,
                              step_size: int = 15,
                              verbose: bool = True) -> str:
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            raise ValueError(f'无法打开视频: {video_path}')
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        if verbose:
            print(f'视频: {w}x{h}, {fps:.2f}fps')
        
        frames = []
        panorama_frames = []
        frame_count = 0
        
        while True:
            ret, frame = cap.read()
            
            if not ret:
                break
            
            frames.append(frame)
            
            if len(frames) >= window_size:
                panorama = self.stitch_video_frames(
                    frames.copy(),
                    output_path='temp_panorama.jpg',
                    stabilize=False,
                    verbose=False
                )
                
                panorama_resized = cv2.resize(panorama, (w, h))
                panorama_frames.append(panorama_resized)
                
                frames = frames[step_size:]
            
            frame_count += 1
            
            if verbose and frame_count % 100 == 0:
                print(f'处理中... {frame_count}帧')
        
        cap.release()
        
        if verbose:
            print(f'共处理 {frame_count} 帧, 生成 {len(panorama_frames)} 个全景帧')
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_video_path, fourcc, fps / step_size, (w, h))
        
        for panorama_frame in panorama_frames:
            out.write(panorama_frame)
        
        out.release()
        
        if verbose:
            print(f'视频已保存到: {output_video_path}')
        
        if os.path.exists('temp_panorama.jpg'):
            os.remove('temp_panorama.jpg')
        
        return output_video_path

    def real_time_stitch(self, frame: np.ndarray,
                         reset: bool = False) -> Optional[np.ndarray]:
        if reset:
            self.frame_buffer = []
            self.keyframes = []
        
        self.frame_buffer.append(frame)
        
        if len(self.frame_buffer) > 100:
            self.frame_buffer = self.frame_buffer[-100:]
        
        if len(self.frame_buffer) >= 2:
            try:
                keyframes = self._select_keyframes(self.frame_buffer)
                
                if len(keyframes) >= 2:
                    self.stitcher.set_images(keyframes)
                    self.stitcher.extract_features()
                    self.stitcher.estimate_homographies()
                    self.stitcher.warp_images()
                    result = self.stitcher.blend_images()
                    
                    return result
            except Exception:
                pass
        
        return None

    def get_video_info(self, video_path: str) -> dict:
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            raise ValueError(f'无法打开视频: {video_path}')
        
        info = {
            'frame_count': int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
            'fps': cap.get(cv2.CAP_PROP_FPS),
            'width': int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            'height': int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            'duration': int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) / cap.get(cv2.CAP_PROP_FPS)
        }
        
        cap.release()
        
        return info

    def extract_sample_frames(self, video_path: str,
                              num_samples: int = 10,
                              output_dir: str = 'samples') -> List[str]:
        os.makedirs(output_dir, exist_ok=True)
        
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            raise ValueError(f'无法打开视频: {video_path}')
        
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        interval = max(1, total_frames // num_samples)
        
        sample_paths = []
        
        for i in range(num_samples):
            cap.set(cv2.CAP_PROP_POS_FRAMES, i * interval)
            ret, frame = cap.read()
            
            if ret:
                path = os.path.join(output_dir, f'sample_{i:04d}.jpg')
                cv2.imwrite(path, frame)
                sample_paths.append(path)
        
        cap.release()
        
        return sample_paths
