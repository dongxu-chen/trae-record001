import os
import subprocess
import json
import numpy as np
import cv2
from pathlib import Path
from config import BITRATE_CONFIG, QUALITY_PRESETS


class FFmpegProcessor:
    def __init__(self, config=None):
        self.config = config or BITRATE_CONFIG
        self.ffmpeg_path = self._find_ffmpeg()
        self.ffprobe_path = self._find_ffprobe()
        self.enable_texture_analysis = self.config.get('enable_texture_analysis', True)
        self.texture_weight = self.config.get('texture_weight', 0.6)
        self.motion_weight = self.config.get('motion_weight', 0.4)

    def _find_ffmpeg(self):
        try:
            result = subprocess.run(['where', 'ffmpeg'], capture_output=True, text=True, check=True)
            return result.stdout.strip().split('\n')[0]
        except:
            try:
                result = subprocess.run(['which', 'ffmpeg'], capture_output=True, text=True, check=True)
                return result.stdout.strip()
            except:
                return 'ffmpeg'

    def _find_ffprobe(self):
        try:
            result = subprocess.run(['where', 'ffprobe'], capture_output=True, text=True, check=True)
            return result.stdout.strip().split('\n')[0]
        except:
            try:
                result = subprocess.run(['which', 'ffprobe'], capture_output=True, text=True, check=True)
                return result.stdout.strip()
            except:
                return 'ffprobe'

    def check_ffmpeg(self):
        try:
            result = subprocess.run([self.ffmpeg_path, '-version'], capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except:
            return False

    def probe_video(self, video_path):
        try:
            cmd = [
                self.ffprobe_path, '-v', 'quiet', '-print_format', 'json',
                '-show_format', '-show_streams', video_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            info = json.loads(result.stdout)

            video_stream = next(s for s in info['streams'] if s['codec_type'] == 'video')
            return {
                'width': int(video_stream['width']),
                'height': int(video_stream['height']),
                'fps': eval(video_stream['r_frame_rate']),
                'duration': float(info['format']['duration']),
                'bitrate': int(info['format'].get('bit_rate', 0)),
                'codec': video_stream['codec_name'],
                'nb_frames': int(video_stream.get('nb_frames', 0)),
            }
        except Exception as e:
            print(f"Warning: Could not probe video: {e}")
            return None

    def _compute_texture_complexity(self, frame):
        if len(frame.shape) == 3:
            gray = cv2.cvtColor((frame * 255).astype(np.uint8), cv2.COLOR_BGR2GRAY)
        else:
            gray = (frame * 255).astype(np.uint8)
        
        sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobel_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        gradient_mag = np.sqrt(sobel_x ** 2 + sobel_y ** 2)
        edge_density = np.mean(gradient_mag) / 255.0
        
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        laplacian_var = np.var(laplacian) / (255.0 ** 2)
        
        hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
        hist = hist.flatten() / hist.sum()
        entropy = -np.sum(hist[hist > 0] * np.log2(hist[hist > 0])) / 8.0
        
        texture_score = (edge_density * 0.4 + np.sqrt(laplacian_var) * 0.3 + entropy * 0.3)
        
        return np.clip(texture_score, 0, 1)

    def _compute_motion_complexity(self, frame1, frame2):
        if len(frame1.shape) == 3:
            gray1 = cv2.cvtColor((frame1 * 255).astype(np.uint8), cv2.COLOR_BGR2GRAY)
            gray2 = cv2.cvtColor((frame2 * 255).astype(np.uint8), cv2.COLOR_BGR2GRAY)
        else:
            gray1 = (frame1 * 255).astype(np.uint8)
            gray2 = (frame2 * 255).astype(np.uint8)
        
        flow = cv2.calcOpticalFlowFarneback(
            gray1, gray2, None,
            pyr_scale=0.5, levels=2, winsize=11,
            iterations=2, poly_n=5, poly_sigma=1.2, flags=0
        )
        
        flow_mag = np.sqrt(flow[..., 0] ** 2 + flow[..., 1] ** 2)
        motion_score = np.mean(flow_mag) / 20.0
        
        frame_diff = np.abs(gray1.astype(np.float32) - gray2.astype(np.float32)).mean() / 255.0
        
        combined_motion = motion_score * 0.6 + frame_diff * 0.4
        
        return np.clip(combined_motion, 0, 1)

    def _compute_spatial_activity(self, frame):
        if len(frame.shape) == 3:
            gray = cv2.cvtColor((frame * 255).astype(np.uint8), cv2.COLOR_BGR2GRAY)
        else:
            gray = (frame * 255).astype(np.uint8)
        
        h, w = gray.shape
        block_size = 16
        num_blocks_h = h // block_size
        num_blocks_w = w // block_size
        
        block_variances = []
        
        for i in range(num_blocks_h):
            for j in range(num_blocks_w):
                block = gray[i*block_size:(i+1)*block_size, j*block_size:(j+1)*block_size]
                block_variances.append(np.var(block))
        
        block_variances = np.array(block_variances)
        
        high_var_ratio = np.mean(block_variances > np.median(block_variances) * 2)
        
        spatial_score = np.sqrt(np.mean(block_variances)) / 255.0
        
        return np.clip(spatial_score * (1 + high_var_ratio * 0.5), 0, 1)

    def analyze_video_complexity(self, video_path, num_sample_frames=20):
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return {'overall': 'medium', 'texture_score': 0.5, 'motion_score': 0.5, 'combined_score': 0.5}
        
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        sample_interval = max(1, total_frames // num_sample_frames)
        
        texture_scores = []
        motion_scores = []
        spatial_scores = []
        
        prev_frame = None
        frame_count = 0
        sampled_count = 0
        
        while sampled_count < num_sample_frames and frame_count < total_frames:
            ret, frame = cap.read()
            if not ret:
                break
            
            if frame_count % sample_interval == 0:
                frame_float = frame.astype(np.float32) / 255.0
                
                texture_score = self._compute_texture_complexity(frame_float)
                texture_scores.append(texture_score)
                
                spatial_score = self._compute_spatial_activity(frame_float)
                spatial_scores.append(spatial_score)
                
                if prev_frame is not None:
                    motion_score = self._compute_motion_complexity(prev_frame, frame_float)
                    motion_scores.append(motion_score)
                
                prev_frame = frame_float
                sampled_count += 1
            
            frame_count += 1
        
        cap.release()
        
        if len(texture_scores) == 0:
            return {'overall': 'medium', 'texture_score': 0.5, 'motion_score': 0.5, 'combined_score': 0.5}
        
        avg_texture = np.mean(texture_scores)
        avg_motion = np.mean(motion_scores) if len(motion_scores) > 0 else 0.3
        avg_spatial = np.mean(spatial_scores)
        
        combined_texture = (avg_texture + avg_spatial) / 2
        
        combined_score = combined_texture * self.texture_weight + avg_motion * self.motion_weight
        
        if combined_score < 0.25:
            overall = 'very_low'
        elif combined_score < 0.4:
            overall = 'low'
        elif combined_score < 0.55:
            overall = 'medium'
        elif combined_score < 0.7:
            overall = 'high'
        else:
            overall = 'very_high'
        
        return {
            'overall': overall,
            'texture_score': float(avg_texture),
            'motion_score': float(avg_motion),
            'spatial_score': float(avg_spatial),
            'combined_score': float(combined_score),
            'texture_std': float(np.std(texture_scores)),
            'motion_std': float(np.std(motion_scores)) if len(motion_scores) > 0 else 0.0,
        }

    def calculate_optimal_bitrate(self, video_info, target_quality='high', scale=1, complexity_analysis=None):
        preset = QUALITY_PRESETS.get(target_quality, QUALITY_PRESETS['high'])
        
        base_bitrate = video_info['width'] * video_info['height'] * video_info['fps'] * 0.1 * scale * scale
        
        if complexity_analysis is not None and self.enable_texture_analysis:
            complexity_factor = {
                'very_low': 0.6,
                'low': 0.8,
                'medium': 1.0,
                'high': 1.3,
                'very_high': 1.6,
            }.get(complexity_analysis['overall'], 1.0)
            
            texture_boost = 1.0 + complexity_analysis['texture_score'] * 0.3
            motion_boost = 1.0 + complexity_analysis['motion_score'] * 0.2
            
            total_factor = complexity_factor * texture_boost * motion_boost
            optimal_bitrate = int(base_bitrate * preset['bitrate_factor'] * total_factor)
        else:
            optimal_bitrate = int(base_bitrate * preset['bitrate_factor'])
        
        return optimal_bitrate

    def calculate_crf(self, video_info, target_quality='high', complexity_analysis=None):
        preset = QUALITY_PRESETS.get(target_quality, QUALITY_PRESETS['high'])
        base_crf = preset['crf']
        
        if complexity_analysis is not None and self.enable_texture_analysis:
            texture_score = complexity_analysis['texture_score']
            motion_score = complexity_analysis['motion_score']
            
            texture_adjust = (texture_score - 0.5) * 4
            motion_adjust = (motion_score - 0.5) * 2
            
            crf_adjust = texture_adjust * self.texture_weight + motion_adjust * self.motion_weight
            crf = base_crf - crf_adjust
        else:
            crf = base_crf
        
        crf = max(self.config['crf_range'][0], min(self.config['crf_range'][1], crf))
        
        return int(crf)

    def _estimate_complexity(self, video_path, num_frames=10):
        info = self.probe_video(video_path)
        if info is None:
            return 'medium'

        cmd = [
            self.ffmpeg_path, '-i', video_path, '-vframes', str(num_frames),
            '-f', 'rawvideo', '-pix_fmt', 'yuv420p', '-'
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, check=True)
            frame_size = info['width'] * info['height'] * 3 // 2
            frames = np.frombuffer(result.stdout, dtype=np.uint8)
            num_frames_actual = len(frames) // frame_size

            variances = []
            for i in range(num_frames_actual):
                frame = frames[i * frame_size:(i + 1) * frame_size]
                variances.append(np.var(frame))

            avg_variance = np.mean(variances)
            if avg_variance < 500:
                return 'low'
            elif avg_variance < 2000:
                return 'medium'
            else:
                return 'high'
        except:
            return 'medium'

    def adaptive_bitrate_params(self, video_path, target_quality='high', scale=1):
        info = self.probe_video(video_path)
        if info is None:
            return {
                'codec': self.config['codec'],
                'crf': QUALITY_PRESETS[target_quality]['crf'],
                'preset': QUALITY_PRESETS[target_quality]['preset'],
            }

        preset = QUALITY_PRESETS.get(target_quality, QUALITY_PRESETS['high'])
        
        if self.enable_texture_analysis:
            complexity_analysis = self.analyze_video_complexity(video_path)
            crf = self.calculate_crf(info, target_quality, complexity_analysis)
            optimal_bitrate = self.calculate_optimal_bitrate(info, target_quality, scale, complexity_analysis)
        else:
            complexity = self._estimate_complexity(video_path)
            complexity_factor = {'low': 0.8, 'medium': 1.0, 'high': 1.2}.get(complexity, 1.0)
            crf = preset['crf'] + (1 - complexity_factor) * 5
            crf = max(self.config['crf_range'][0], min(self.config['crf_range'][1], crf))
            optimal_bitrate = self.calculate_optimal_bitrate(info, target_quality, scale)
            complexity_analysis = None

        return {
            'codec': self.config['codec'],
            'crf': int(crf),
            'preset': preset['preset'],
            'bitrate': optimal_bitrate,
            'max_bitrate': int(optimal_bitrate * 1.5),
            'buf_size': int(optimal_bitrate * 2),
            'complexity_analysis': complexity_analysis,
        }

    def extract_frames(self, video_path, output_dir, fps=None, start_time=None, duration=None):
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        output_pattern = os.path.join(output_dir, 'frame_%08d.png')

        cmd = [self.ffmpeg_path, '-y', '-i', video_path]
        if start_time is not None:
            cmd += ['-ss', str(start_time)]
        if duration is not None:
            cmd += ['-t', str(duration)]
        if fps is not None:
            cmd += ['-vf', f'fps={fps}']
        cmd += ['-q:v', '1', output_pattern]

        try:
            subprocess.run(cmd, check=True, capture_output=True)
            frames = sorted(Path(output_dir).glob('frame_*.png'))
            return [str(f) for f in frames]
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"FFmpeg frame extraction failed: {e.stderr.decode()}")

    def images_to_video(self, image_dir, output_path, fps=30, params=None, audio_source=None):
        if params is None:
            params = self.adaptive_bitrate_params(audio_source or image_dir)

        image_pattern = os.path.join(image_dir, 'frame_%08d.png')

        cmd = [self.ffmpeg_path, '-y', '-framerate', str(fps), '-i', image_pattern]

        if audio_source:
            cmd += ['-i', audio_source, '-c:a', 'aac', '-b:a', '192k']

        cmd += [
            '-c:v', params['codec'],
            '-preset', params['preset'],
            '-crf', str(params['crf']),
            '-pix_fmt', 'yuv420p',
        ]

        if 'max_bitrate' in params and 'buf_size' in params:
            cmd += [
                '-maxrate', str(params['max_bitrate']),
                '-bufsize', str(params['buf_size']),
            ]

        if audio_source:
            cmd += ['-shortest']

        cmd.append(output_path)

        try:
            subprocess.run(cmd, check=True, capture_output=True)
            return output_path
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"FFmpeg video encoding failed: {e.stderr.decode()}")

    def extract_audio(self, video_path, output_path):
        cmd = [
            self.ffmpeg_path, '-y', '-i', video_path,
            '-vn', '-acodec', 'copy', output_path
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            return output_path
        except:
            try:
                cmd = [
                    self.ffmpeg_path, '-y', '-i', video_path,
                    '-vn', '-acodec', 'aac', '-b:a', '192k', output_path
                ]
                subprocess.run(cmd, check=True, capture_output=True)
                return output_path
            except subprocess.CalledProcessError as e:
                raise RuntimeError(f"Audio extraction failed: {e.stderr.decode()}")

    def get_frame_count(self, video_path):
        info = self.probe_video(video_path)
        if info and info['nb_frames'] > 0:
            return info['nb_frames']

        cmd = [
            self.ffmpeg_path, '-v', 'error', '-select_streams', 'v:0',
            '-show_entries', 'stream=nb_frames', '-of', 'default=nokey=1:noprint_wrappers=1',
            video_path
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return int(result.stdout.strip())
        except:
            return 0

    def compress_video(self, input_path, output_path, target_size_mb=None):
        info = self.probe_video(input_path)
        if info is None or target_size_mb is None:
            params = self.adaptive_bitrate_params(input_path)
            return self.images_to_video(
                os.path.dirname(input_path), output_path,
                fps=info['fps'] if info else 30, params=params
            )

        target_size_bits = target_size_mb * 8 * 1024 * 1024
        duration = info['duration']
        target_bitrate = int(target_size_bits / duration)
        audio_bitrate = 192000
        video_bitrate = max(target_bitrate - audio_bitrate, 100000)

        cmd = [
            self.ffmpeg_path, '-y', '-i', input_path,
            '-c:v', self.config['codec'],
            '-b:v', str(video_bitrate),
            '-maxrate', str(int(video_bitrate * 1.5)),
            '-bufsize', str(int(video_bitrate * 2)),
            '-preset', QUALITY_PRESETS[self.config['target_quality']]['preset'],
            '-c:a', 'aac', '-b:a', '192k',
            output_path
        ]

        try:
            subprocess.run(cmd, check=True, capture_output=True)
            return output_path
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Video compression failed: {e.stderr.decode()}")
