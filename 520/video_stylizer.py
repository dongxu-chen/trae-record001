import torch
import torch.nn as nn
import cv2
import numpy as np
import os
from PIL import Image
from torchvision import transforms
from style_decomposer import StyleDecomposer
from adain_model import calc_mean_std


class VideoStylizer:
    def __init__(self, device='cpu'):
        self.device = device
        self.decomposer = StyleDecomposer(device)
        self.transform = transforms.Compose([
            transforms.Resize((512, 512)),
            transforms.ToTensor(),
        ])

    def preprocess(self, image):
        if isinstance(image, np.ndarray):
            image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        return self.transform(image).unsqueeze(0).to(self.device)

    def postprocess(self, tensor):
        tensor = tensor.clamp(0, 1)
        img = tensor.squeeze(0).cpu().permute(1, 2, 0).numpy()
        img = (img * 255).astype(np.uint8)
        return cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

    def extract_frames(self, video_path, max_frames=None, frame_step=1):
        cap = cv2.VideoCapture(video_path)
        frames = []
        frame_idx = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            if frame_idx % frame_step == 0:
                frames.append(frame)
                if max_frames is not None and len(frames) >= max_frames:
                    break
            frame_idx += 1
        cap.release()
        return frames

    def compute_optical_flow(self, prev_frame, curr_frame):
        prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
        curr_gray = cv2.cvtColor(curr_frame, cv2.COLOR_BGR2GRAY)
        flow = cv2.calcOpticalFlowFarneback(
            prev_gray, curr_gray, None,
            pyr_scale=0.5, levels=3, winsize=15,
            iterations=3, poly_n=5, poly_sigma=1.2, flags=0
        )
        return flow

    def warp_image(self, img, flow):
        h, w = img.shape[:2]
        y_coords, x_coords = np.mgrid[0:h, 0:w].astype(np.float32)
        map_x = x_coords + flow[:, :, 0]
        map_y = y_coords + flow[:, :, 1]
        warped = cv2.remap(img, map_x, map_y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        return warped

    def temporal_blend(self, current_stylized, prev_stylized, flow, blend_weight=0.7):
        warped_prev = self.warp_image(prev_stylized, flow)
        blended = cv2.addWeighted(current_stylized, 1 - blend_weight, warped_prev, blend_weight, 0)
        return blended

    def stylize_single_frame(self, frame, style_tensor, content_feats_cache, alpha=1.0):
        frame_tensor = self.preprocess(frame)
        content_feats = self.decomposer.adain.encode_content(frame_tensor)
        style_feats = self.decomposer.adain.encode_style(style_tensor)

        t = self.decomposer.adain.style_transfer(content_feats[-1], style_feats, alpha)
        stylized = self.decomposer.adain.decode(t)
        return self.postprocess(stylized)

    def stylize_video(self, video_path, style_img, output_path=None,
                      alpha=0.8, temporal_weight=0.5, max_frames=None,
                      frame_step=1, fps=None, progress_callback=None):
        if isinstance(style_img, str):
            style_img = cv2.imread(style_img)
        style_img_resized = cv2.resize(style_img, (512, 512))

        frames = self.extract_frames(video_path, max_frames, frame_step)
        if len(frames) == 0:
            return None

        if fps is None:
            cap = cv2.VideoCapture(video_path)
            fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
            cap.release()

        style_tensor = self.preprocess(style_img_resized)
        style_feats = self.decomposer.adain.encode_style(style_tensor)

        stylized_frames = []
        prev_stylized = None
        total = len(frames)

        for i, frame in enumerate(frames):
            frame_resized = cv2.resize(frame, (512, 512))
            frame_tensor = self.preprocess(frame_resized)
            content_feats = self.decomposer.adain.encode_content(frame_tensor)

            t = self.decomposer.adain.style_transfer(content_feats[-1], style_feats, alpha)
            stylized = self.decomposer.adain.decode(t)
            current_stylized = self.postprocess(stylized)

            if prev_stylized is not None and temporal_weight > 0:
                flow = self.compute_optical_flow(prev_stylized, current_stylized)
                current_stylized = self.temporal_blend(
                    current_stylized, prev_stylized, flow, blend_weight=temporal_weight
                )

            prev_stylized = current_stylized.copy()
            h, w = frame.shape[:2]
            result = cv2.resize(current_stylized, (w, h))
            stylized_frames.append(result)

            if progress_callback:
                progress_callback(i + 1, total)

        if output_path is None:
            output_path = 'stylized_output.mp4'

        self._write_video(stylized_frames, output_path, fps)
        return output_path, stylized_frames

    def stylize_video_with_consistency(self, video_path, style_img, output_path=None,
                                        alpha=0.8, temporal_weight=0.5, short_term_window=3,
                                        max_frames=None, frame_step=1, fps=None,
                                        progress_callback=None):
        if isinstance(style_img, str):
            style_img = cv2.imread(style_img)
        style_img_resized = cv2.resize(style_img, (512, 512))

        frames = self.extract_frames(video_path, max_frames, frame_step)
        if len(frames) == 0:
            return None

        if fps is None:
            cap = cv2.VideoCapture(video_path)
            fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
            cap.release()

        style_tensor = self.preprocess(style_img_resized)
        style_feats = self.decomposer.adain.encode_style(style_tensor)

        raw_stylized = []
        for i, frame in enumerate(frames):
            frame_resized = cv2.resize(frame, (512, 512))
            frame_tensor = self.preprocess(frame_resized)
            content_feats = self.decomposer.adain.encode_content(frame_tensor)
            t = self.decomposer.adain.style_transfer(content_feats[-1], style_feats, alpha)
            stylized = self.decomposer.adain.decode(t)
            raw_stylized.append(self.postprocess(stylized))

            if progress_callback:
                progress_callback(i + 1, len(frames))

        consistent_frames = self._apply_short_term_consistency(
            raw_stylized, window=short_term_window, temporal_weight=temporal_weight
        )

        final_frames = []
        for i, (orig, stylized) in enumerate(zip(frames, consistent_frames)):
            h, w = orig.shape[:2]
            final_frames.append(cv2.resize(stylized, (w, h)))

        if output_path is None:
            output_path = 'stylized_output.mp4'

        self._write_video(final_frames, output_path, fps)
        return output_path, final_frames

    def _apply_short_term_consistency(self, frames, window=3, temporal_weight=0.5):
        n = len(frames)
        result = [frames[0].copy()]
        buffer = [frames[0].copy()]

        for i in range(1, n):
            current = frames[i].copy()

            for j in range(max(0, i - window), i):
                prev = result[j]
                flow = self.compute_optical_flow(prev, current)
                warped = self.warp_image(prev, flow)
                current = cv2.addWeighted(current, 1 - temporal_weight / window,
                                          warped, temporal_weight / window, 0)

            result.append(current)

        return result

    def _write_video(self, frames, output_path, fps):
        if len(frames) == 0:
            return
        h, w = frames[0].shape[:2]
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (w, h))
        for frame in frames:
            out.write(frame)
        out.release()
