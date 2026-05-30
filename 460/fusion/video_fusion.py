import cv2
import numpy as np
from collections import deque


class TemporalSmoother:
    def __init__(self, window_size=5, temporal_alpha=0.3):
        self.window_size = window_size
        self.temporal_alpha = temporal_alpha
        self.frame_buffer = deque(maxlen=window_size)
        self.prev_frame = None

    def smooth_iir(self, current_frame):
        if self.prev_frame is None:
            self.prev_frame = current_frame.astype(np.float64)
            return current_frame
        alpha = self.temporal_alpha
        smoothed = alpha * current_frame.astype(np.float64) + (1 - alpha) * self.prev_frame
        self.prev_frame = smoothed.copy()
        return np.clip(smoothed, 0, 255).astype(np.uint8)

    def smooth_moving_average(self, current_frame):
        self.frame_buffer.append(current_frame.astype(np.float64))
        if len(self.frame_buffer) < 2:
            return current_frame
        weights = np.array([self.temporal_alpha ** i for i in range(len(self.frame_buffer))])
        weights = weights[::-1]
        weights = weights / weights.sum()
        result = np.zeros_like(self.frame_buffer[0])
        for w, frame in zip(weights, self.frame_buffer):
            result += w * frame
        return np.clip(result, 0, 255).astype(np.uint8)

    def reset(self):
        self.frame_buffer.clear()
        self.prev_frame = None


class VideoFusion:
    def __init__(self, fusion_engine=None, temporal_mode="iir", temporal_alpha=0.3, window_size=5):
        self.fusion_engine = fusion_engine
        self.temporal_mode = temporal_mode
        self.temporal_alpha = temporal_alpha
        self.smoother = TemporalSmoother(window_size=window_size, temporal_alpha=temporal_alpha)
        self.frame_count = 0
        self.prev_flow = None

    def _ensure_consistent(self, frames):
        if not frames:
            return frames
        ref_h, ref_w = frames[0].shape[:2]
        resized = []
        for f in frames:
            if f.shape[:2] != (ref_h, ref_w):
                f = cv2.resize(f, (ref_w, ref_h))
            resized.append(f)
        return resized

    def _compute_frame_flow(self, prev_gray, curr_gray):
        flow = cv2.calcOpticalFlowFarneback(
            prev_gray, curr_gray, None,
            pyr_scale=0.5, levels=3, winsize=15,
            iterations=3, poly_n=5, poly_sigma=1.2, flags=0,
        )
        return flow

    def _warp_frame(self, frame, flow):
        h, w = frame.shape[:2]
        grid_x, grid_y = np.meshgrid(np.arange(w), np.arange(h))
        map_x = (grid_x + flow[:, :, 0]).astype(np.float32)
        map_y = (grid_y + flow[:, :, 1]).astype(np.float32)
        return cv2.remap(frame, map_x, map_y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

    def _temporal_warp_consistency(self, fused_frame, prev_fused, curr_gray, prev_gray):
        if prev_fused is None or prev_gray is None:
            return fused_frame
        flow = self._compute_frame_flow(prev_gray, curr_gray)
        warped_prev = self._warp_frame(prev_fused, flow)
        flow_mag = np.sqrt(flow[:, :, 0] ** 2 + flow[:, :, 1] ** 2)
        consistency_weight = np.exp(-flow_mag / 5.0)
        consistency_weight = np.clip(consistency_weight, 0, 1)
        if len(consistency_weight.shape) == 2:
            consistency_weight = consistency_weight[:, :, np.newaxis]
        result = (fused_frame.astype(np.float64) * (1 - consistency_weight * self.temporal_alpha) +
                  warped_prev.astype(np.float64) * (consistency_weight * self.temporal_alpha))
        return np.clip(result, 0, 255).astype(np.uint8)

    def fuse_frame(self, frames, fusion_func=None, reliable_masks=None):
        frames = self._ensure_consistent(frames)
        if fusion_func is not None:
            fused = fusion_func(frames, reliable_masks)
        elif self.fusion_engine is not None:
            if reliable_masks is not None:
                fused = self.fusion_engine.fuse(frames, reliable_masks)
            else:
                fused = self.fusion_engine.fuse(frames)
        else:
            fused = frames[0].copy()

        if self.temporal_mode == "iir":
            fused = self.smoother.smooth_iir(fused)
        elif self.temporal_mode == "moving_average":
            fused = self.smoother.smooth_moving_average(fused)
        elif self.temporal_mode == "flow_warp":
            pass

        self.frame_count += 1
        return fused

    def fuse_frame_with_temporal(self, frames, prev_fused=None, prev_gray=None, fusion_func=None):
        frames = self._ensure_consistent(frames)
        if fusion_func is not None:
            fused = fusion_func(frames)
        elif self.fusion_engine is not None:
            fused = self.fusion_engine.fuse(frames)
        else:
            fused = frames[0].copy()

        curr_gray = cv2.cvtColor(fused, cv2.COLOR_BGR2GRAY) if len(fused.shape) == 3 else fused.copy()

        if self.temporal_mode == "flow_warp" and prev_fused is not None:
            fused = self._temporal_warp_consistency(fused, prev_fused, curr_gray, prev_gray)
        elif self.temporal_mode == "iir":
            fused = self.smoother.smooth_iir(fused)
        elif self.temporal_mode == "moving_average":
            fused = self.smoother.smooth_moving_average(fused)

        self.frame_count += 1
        return fused, curr_gray

    def process_video(self, video_paths, output_path, fusion_func=None, fps=None, show_progress=False):
        caps = []
        for vp in video_paths:
            cap = cv2.VideoCapture(vp)
            if not cap.isOpened():
                print(f"Error: Cannot open {vp}")
                for c in caps:
                    c.release()
                return False
            caps.append(cap)

        ref_w = int(caps[0].get(cv2.CAP_PROP_FRAME_WIDTH))
        ref_h = int(caps[0].get(cv2.CAP_PROP_FRAME_HEIGHT))
        if fps is None:
            fps = caps[0].get(cv2.CAP_PROP_FPS)
            if fps <= 0:
                fps = 30.0
        total_frames = int(caps[0].get(cv2.CAP_PROP_FRAME_COUNT))

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(output_path, fourcc, fps, (ref_w, ref_h))

        self.smoother.reset()
        self.frame_count = 0
        prev_fused = None
        prev_gray = None

        frame_idx = 0
        while True:
            frames = []
            all_ok = True
            for cap in caps:
                ok, frame = cap.read()
                if not ok:
                    all_ok = False
                    break
                if frame.shape[:2] != (ref_h, ref_w):
                    frame = cv2.resize(frame, (ref_w, ref_h))
                frames.append(frame)

            if not all_ok or len(frames) < 1:
                break

            if self.temporal_mode == "flow_warp":
                fused, curr_gray = self.fuse_frame_with_temporal(
                    frames, prev_fused, prev_gray, fusion_func
                )
                prev_fused = fused.copy()
                prev_gray = curr_gray
            else:
                fused = self.fuse_frame(frames, fusion_func)

            writer.write(fused)
            frame_idx += 1

            if show_progress and frame_idx % 30 == 0:
                if total_frames > 0:
                    pct = frame_idx / total_frames * 100
                    print(f"  Frame {frame_idx}/{total_frames} ({pct:.1f}%)")
                else:
                    print(f"  Frame {frame_idx}")

        for cap in caps:
            cap.release()
        writer.release()
        print(f"Video fusion done: {frame_idx} frames -> {output_path}")
        return True

    def process_frame_sequences(self, frame_dirs, output_path, fusion_func=None, fps=30.0, show_progress=False):
        import os
        exts = (".png", ".jpg", ".jpeg", ".bmp", ".tif")
        all_sequences = []
        for d in frame_dirs:
            files = sorted([os.path.join(d, f) for f in os.listdir(d) if f.lower().endswith(exts)])
            all_sequences.append(files)

        if not all_sequences:
            print("No frames found")
            return False

        min_len = min(len(s) for s in all_sequences)
        if min_len == 0:
            print("Empty sequence")
            return False

        sample = cv2.imread(all_sequences[0][0])
        ref_h, ref_w = sample.shape[:2]

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(output_path, fourcc, fps, (ref_w, ref_h))

        self.smoother.reset()
        self.frame_count = 0
        prev_fused = None
        prev_gray = None

        for i in range(min_len):
            frames = []
            for seq in all_sequences:
                img = cv2.imread(seq[i])
                if img is None:
                    break
                if img.shape[:2] != (ref_h, ref_w):
                    img = cv2.resize(img, (ref_w, ref_h))
                frames.append(img)

            if len(frames) != len(all_sequences):
                break

            if self.temporal_mode == "flow_warp":
                fused, curr_gray = self.fuse_frame_with_temporal(
                    frames, prev_fused, prev_gray, fusion_func
                )
                prev_fused = fused.copy()
                prev_gray = curr_gray
            else:
                fused = self.fuse_frame(frames, fusion_func)

            writer.write(fused)

            if show_progress and (i + 1) % 30 == 0:
                print(f"  Frame {i + 1}/{min_len}")

        writer.release()
        print(f"Frame sequence fusion done: {min_len} frames -> {output_path}")
        return True

    @staticmethod
    def get_available_temporal_modes():
        return ["none", "iir", "moving_average", "flow_warp"]

    def set_temporal_params(self, alpha=None, window_size=None, mode=None):
        if alpha is not None:
            self.temporal_alpha = alpha
            self.smoother.temporal_alpha = alpha
        if window_size is not None:
            self.smoother = TemporalSmoother(window_size=window_size, temporal_alpha=self.temporal_alpha)
        if mode is not None:
            self.temporal_mode = mode
