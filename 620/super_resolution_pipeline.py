import os
import sys
import time
import shutil
import tempfile
import numpy as np
import torch
import cv2
from pathlib import Path
from tqdm import tqdm

from models import get_model, load_pretrained_weights
from processors import MultiFrameDenoiser, TemporalConsistency, FFmpegProcessor
from processors import FaceEnhancer, SubtitleEnhancer, RealtimeSuperResolution
from utils.common import get_device, ensure_dir, img2tensor, tensor2img, read_img, save_img
from config import PROCESS_CONFIG, DENOISE_CONFIG, TEMPORAL_CONFIG, BITRATE_CONFIG
from config import FACE_ENHANCE_CONFIG, SUBTITLE_CONFIG, REALTIME_CONFIG


class SuperResolutionPipeline:
    def __init__(
        self,
        model_name='edsr',
        scale=4,
        device=None,
        weight_path=None,
        enable_denoise=True,
        enable_temporal=True,
        enable_bitrate_adapt=True,
        enable_face_enhance=False,
        enable_subtitle_enhance=False,
        enable_realtime=False,
        half_precision=False,
    ):
        self.model_name = model_name.lower()
        self.scale = scale
        self.device = device or get_device()
        self.half_precision = half_precision

        self.enable_denoise = enable_denoise
        self.enable_temporal = enable_temporal
        self.enable_bitrate_adapt = enable_bitrate_adapt
        self.enable_face_enhance = enable_face_enhance
        self.enable_subtitle_enhance = enable_subtitle_enhance
        self.enable_realtime = enable_realtime

        print(f"Initializing {self.model_name.upper()} x{scale} model...")
        self.model = get_model(self.model_name, scale=self.scale)
        self.model = self.model.to(self.device)
        self.model.eval()

        if weight_path and os.path.exists(weight_path):
            print(f"Loading pretrained weights from: {weight_path}")
            self.model = load_pretrained_weights(self.model, weight_path, self.device)

        if self.half_precision:
            self.model = self.model.half()
            print("Using half precision (FP16)")

        self.denoiser = MultiFrameDenoiser(DENOISE_CONFIG) if self.enable_denoise else None
        self.temporal_consistency = TemporalConsistency(TEMPORAL_CONFIG) if self.enable_temporal else None
        self.ffmpeg = FFmpegProcessor(BITRATE_CONFIG if self.enable_bitrate_adapt else None)
        
        self.face_enhancer = None
        if self.enable_face_enhance:
            face_config = FACE_ENHANCE_CONFIG.copy()
            face_config['enable'] = True
            self.face_enhancer = FaceEnhancer(face_config, self.device)
            print("Face enhancement enabled")
        
        self.subtitle_enhancer = None
        if self.enable_subtitle_enhance:
            sub_config = SUBTITLE_CONFIG.copy()
            sub_config['enable'] = True
            self.subtitle_enhancer = SubtitleEnhancer(sub_config, self.device)
            print("Subtitle enhancement enabled")
        
        self.realtime_engine = None
        if self.enable_realtime:
            rt_config = REALTIME_CONFIG.copy()
            rt_config['enable'] = True
            self.realtime_engine = RealtimeSuperResolution(self, rt_config, self.device)
            print("Realtime super-resolution enabled")

        print(f"Pipeline initialized. Device: {self.device}")
        if not self.ffmpeg.check_ffmpeg():
            print("Warning: FFmpeg not found. Some features may be limited.")

    def _preprocess_frame(self, frame):
        if frame.shape[2] == 4:
            frame = frame[:, :, :3]
        if frame.dtype == np.uint8:
            frame = frame.astype(np.float32) / 255.0
        return frame

    def _super_resolve_single(self, img):
        tensor = img2tensor(img, bgr2rgb=True).unsqueeze(0)
        tensor = tensor.to(self.device)

        if self.half_precision:
            tensor = tensor.half()

        with torch.no_grad():
            sr_tensor = self.model(tensor)

        sr_img = tensor2img(sr_tensor, rgb_range=255, out_type=np.float32, min_max=(0, 1))
        sr_img = sr_img[:, :, ::-1]
        return sr_img

    def _super_resolve_batch(self, frames):
        if len(frames) == 0:
            return []

        tensors = []
        for frame in frames:
            tensor = img2tensor(frame, bgr2rgb=True)
            if self.half_precision:
                tensor = tensor.half()
            tensors.append(tensor)

        batch_tensor = torch.stack(tensors).to(self.device)

        with torch.no_grad():
            sr_batch = self.model(batch_tensor)

        sr_frames = []
        for i in range(sr_batch.size(0)):
            sr_img = tensor2img(sr_batch[i], rgb_range=255, out_type=np.float32, min_max=(0, 1))
            sr_img = sr_img[:, :, ::-1]
            sr_frames.append(sr_img)

        return sr_frames

    def enhance(self, lr_frame):
        lr_frame = self._preprocess_frame(lr_frame)
        
        if self.denoiser:
            lr_frame = self.denoiser.process(lr_frame)
        
        sr_frame = self._super_resolve_single(lr_frame)
        
        if self.temporal_consistency:
            sr_frame = self.temporal_consistency.process(sr_frame)
        
        if self.face_enhancer:
            sr_frame, faces = self.face_enhancer.process(sr_frame, sr_func=self._enhance_face_roi)
        
        if self.subtitle_enhancer:
            sr_frame, subtitles = self.subtitle_enhancer.process(sr_frame)
        
        return sr_frame
    
    def _enhance_face_roi(self, face_roi):
        return self._super_resolve_single(face_roi)
    
    def _process_frame_sequence(self, lr_frames, progress_callback=None):
        if self.denoiser:
            self.denoiser.reset()
        if self.temporal_consistency:
            self.temporal_consistency.reset()
        if self.face_enhancer:
            self.face_enhancer.reset()
        if self.subtitle_enhancer:
            self.subtitle_enhancer.reset()

        sr_frames = []
        total_frames = len(lr_frames)

        for idx, lr_frame in enumerate(tqdm(lr_frames, desc="Super-resolving", unit="frame")):
            lr_frame = self._preprocess_frame(lr_frame)

            if self.denoiser:
                lr_frame = self.denoiser.process(lr_frame)

            sr_frame = self._super_resolve_single(lr_frame)

            if self.temporal_consistency:
                sr_frame = self.temporal_consistency.process(sr_frame)
            
            if self.face_enhancer:
                sr_frame, faces = self.face_enhancer.process(sr_frame, sr_func=self._enhance_face_roi)
            
            if self.subtitle_enhancer:
                sr_frame, subtitles = self.subtitle_enhancer.process(sr_frame)

            sr_frames.append(sr_frame)

            if progress_callback:
                progress_callback(idx + 1, total_frames)

        return sr_frames

    def process_video(
        self,
        input_path,
        output_path=None,
        start_time=None,
        duration=None,
        target_fps=None,
        target_quality='high',
        progress_callback=None,
    ):
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input video not found: {input_path}")

        video_info = self.ffmpeg.probe_video(input_path)
        if video_info is None:
            raise RuntimeError("Could not read video information")

        fps = target_fps or video_info['fps']
        temp_dir = tempfile.mkdtemp(prefix='sr_video_')
        lr_frames_dir = os.path.join(temp_dir, 'lr_frames')
        sr_frames_dir = os.path.join(temp_dir, 'sr_frames')
        audio_path = os.path.join(temp_dir, 'audio.aac')

        try:
            print(f"Extracting frames at {fps} FPS...")
            lr_frame_paths = self.ffmpeg.extract_frames(
                input_path, lr_frames_dir,
                fps=fps, start_time=start_time, duration=duration
            )

            if len(lr_frame_paths) == 0:
                raise RuntimeError("No frames extracted from video")

            print(f"Extracted {len(lr_frame_paths)} frames")

            try:
                self.ffmpeg.extract_audio(input_path, audio_path)
                has_audio = True
            except:
                has_audio = False
                audio_path = None

            print("Loading frames...")
            lr_frames = []
            for path in tqdm(lr_frame_paths, desc="Loading", unit="frame"):
                lr_frames.append(read_img(path))

            print("Processing frames...")
            sr_frames = self._process_frame_sequence(lr_frames, progress_callback)

            print("Saving super-resolved frames...")
            ensure_dir(sr_frames_dir)
            for idx, sr_frame in enumerate(tqdm(sr_frames, desc="Saving", unit="frame")):
                output_frame_path = os.path.join(sr_frames_dir, f'frame_{idx+1:08d}.png')
                save_img(sr_frame, output_frame_path)

            if output_path is None:
                input_name = os.path.splitext(os.path.basename(input_path))[0]
                output_path = os.path.join(
                    PROCESS_CONFIG['output_dir'],
                    f'{input_name}_{self.model_name}_x{self.scale}.mp4'
                )

            ensure_dir(os.path.dirname(output_path))

            print("Encoding video...")
            encode_params = self.ffmpeg.adaptive_bitrate_params(
                input_path, target_quality=target_quality, scale=self.scale
            )
            
            complexity_analysis = encode_params.get('complexity_analysis')
            if complexity_analysis:
                print(f"视频复杂度分析: {complexity_analysis['overall']}")
                print(f"  - 纹理得分: {complexity_analysis['texture_score']:.3f}")
                print(f"  - 运动得分: {complexity_analysis['motion_score']:.3f}")
                print(f"  - 综合得分: {complexity_analysis['combined_score']:.3f}")
                print(f"  - 编码CRF: {encode_params['crf']}")

            self.ffmpeg.images_to_video(
                sr_frames_dir, output_path,
                fps=fps, params=encode_params,
                audio_source=audio_path if has_audio else None
            )

            print(f"Video saved to: {output_path}")

            result = {
                'output_path': output_path,
                'num_frames': len(sr_frames),
                'fps': fps,
                'resolution': (sr_frames[0].shape[1], sr_frames[0].shape[0]),
                'original_resolution': (video_info['width'], video_info['height']),
                'scale': self.scale,
                'model': self.model_name,
                'has_audio': has_audio,
                'encode_params': {
                    'crf': encode_params['crf'],
                    'bitrate': encode_params['bitrate'],
                    'preset': encode_params['preset'],
                },
                'complexity_analysis': complexity_analysis,
                'face_enhance_enabled': self.enable_face_enhance,
                'subtitle_enhance_enabled': self.enable_subtitle_enhance,
                'realtime_enabled': self.enable_realtime,
            }
            
            if self.realtime_engine:
                result['realtime_stats'] = self.realtime_engine.get_stats()
            
            return result

        finally:
            print("Cleaning up temporary files...")
            shutil.rmtree(temp_dir, ignore_errors=True)

    def process_image(self, input_path, output_path=None):
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input image not found: {input_path}")

        lr_img = read_img(input_path)

        if self.denoiser:
            self.denoiser.reset()
            for _ in range(self.denoiser.num_frames // 2):
                self.denoiser.add_frame(lr_img)

        sr_img = self._process_frame_sequence([lr_img])[0]

        if output_path is None:
            input_name = os.path.splitext(os.path.basename(input_path))[0]
            output_path = os.path.join(
                PROCESS_CONFIG['output_dir'],
                f'{input_name}_{self.model_name}_x{self.scale}.png'
            )

        ensure_dir(os.path.dirname(output_path))
        save_img(sr_img, output_path)

        return {
            'output_path': output_path,
            'resolution': (sr_img.shape[1], sr_img.shape[0]),
            'original_resolution': (lr_img.shape[1], lr_img.shape[0]),
            'scale': self.scale,
            'model': self.model_name,
        }

    def process_video_stream(self, frame_generator, output_dir, fps=30, target_quality='high'):
        ensure_dir(output_dir)
        frame_count = 0

        if self.denoiser:
            self.denoiser.reset()
        if self.temporal_consistency:
            self.temporal_consistency.reset()
        if self.face_enhancer:
            self.face_enhancer.reset()
        if self.subtitle_enhancer:
            self.subtitle_enhancer.reset()

        for lr_frame in frame_generator:
            lr_frame = self._preprocess_frame(lr_frame)

            if self.denoiser:
                lr_frame = self.denoiser.process(lr_frame)

            sr_frame = self._super_resolve_single(lr_frame)

            if self.temporal_consistency:
                sr_frame = self.temporal_consistency.process(sr_frame)
            
            if self.face_enhancer:
                sr_frame, faces = self.face_enhancer.process(sr_frame, sr_func=self._enhance_face_roi)
            
            if self.subtitle_enhancer:
                sr_frame, subtitles = self.subtitle_enhancer.process(sr_frame)

            output_frame_path = os.path.join(output_dir, f'frame_{frame_count+1:08d}.png')
            save_img(sr_frame, output_frame_path)
            frame_count += 1

            yield {
                'frame_index': frame_count,
                'lr_frame': lr_frame,
                'sr_frame': sr_frame,
                'output_path': output_frame_path,
            }

    def process_video_frames_dir(
        self,
        input_dir,
        output_dir,
        progress_callback=None,
    ):
        frame_paths = sorted(Path(input_dir).glob('*.png') + Path(input_dir).glob('*.jpg') + Path(input_dir).glob('*.jpeg'))
        if len(frame_paths) == 0:
            raise RuntimeError(f"No frames found in {input_dir}")

        ensure_dir(output_dir)

        lr_frames = []
        for path in tqdm(frame_paths, desc="Loading", unit="frame"):
            lr_frames.append(read_img(str(path)))

        sr_frames = self._process_frame_sequence(lr_frames, progress_callback)

        for idx, sr_frame in enumerate(tqdm(sr_frames, desc="Saving", unit="frame")):
            output_frame_path = os.path.join(output_dir, f'frame_{idx+1:08d}.png')
            save_img(sr_frame, output_frame_path)

        return {
            'num_frames': len(sr_frames),
            'resolution': (sr_frames[0].shape[1], sr_frames[0].shape[0]),
            'original_resolution': (lr_frames[0].shape[1], lr_frames[0].shape[0]),
            'output_dir': output_dir,
        }


def get_available_models():
    return ['edsr', 'rcan']


def get_available_scales():
    return [2, 3, 4]


def compare_with_bicubic(lr_img, scale=4):
    h, w = lr_img.shape[:2]
    bicubic = cv2.resize(
        (lr_img * 255).astype(np.uint8),
        (w * scale, h * scale),
        interpolation=cv2.INTER_CUBIC
    ).astype(np.float32) / 255.0
    return bicubic
