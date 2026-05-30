import numpy as np
import cv2
from collections import deque, defaultdict
from skimage.color import rgb2lab
from skimage.util import img_as_float
from superpixel_core import SuperpixelSegmenter, SuperpixelClassifier


class SuperpixelTracker:

    def __init__(self, max_history=5):
        self.max_history = max_history
        self.prev_segments = None
        self.prev_features = None
        self.prev_image = None
        self.id_counter = 0
        self.track_history = defaultdict(lambda: deque(maxlen=max_history))
        self.optical_flow = None

    def reset(self):
        self.prev_segments = None
        self.prev_features = None
        self.prev_image = None
        self.id_counter = 0
        self.track_history.clear()
        self.optical_flow = None

    def _compute_optical_flow(self, prev_gray, curr_gray):
        flow = cv2.calcOpticalFlowFarneback(
            prev_gray, curr_gray, None,
            pyr_scale=0.5, levels=3, winsize=15,
            iterations=3, poly_n=5, poly_sigma=1.2, flags=0
        )
        return flow

    def _warp_segments(self, segments, flow):
        h, w = segments.shape
        warped = np.zeros_like(segments)
        yy, xx = np.mgrid[0:h, 0:w]
        new_xx = np.clip(xx + flow[:, :, 0], 0, w - 1).astype(np.int32)
        new_yy = np.clip(yy + flow[:, :, 1], 0, h - 1).astype(np.int32)
        warped[new_yy, new_xx] = segments[yy, xx]
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        for _ in range(2):
            mask = warped == 0
            if not mask.any():
                break
            temp = cv2.dilate(warped.astype(np.uint16), kernel)
            warped[mask] = temp[mask]
        return warped

    def _extract_segment_features(self, image, segments):
        lab = rgb2lab(img_as_float(image))
        features = {}
        seg_ids = np.unique(segments)
        for sid in seg_ids:
            mask = segments == sid
            if mask.sum() == 0:
                continue
            mean_lab = lab[mask].mean(axis=0)
            var_lab = lab[mask].var(axis=0)
            ys, xs = np.where(mask)
            centroid = np.array([xs.mean(), ys.mean()])
            features[sid] = {
                "mean_lab": mean_lab,
                "var_lab": var_lab,
                "centroid": centroid,
                "area": float(mask.sum()),
            }
        return features

    def _compute_overlap(self, seg1, seg2, id1, id2):
        mask1 = seg1 == id1
        mask2 = seg2 == id2
        intersection = np.logical_and(mask1, mask2).sum()
        union = np.logical_or(mask1, mask2).sum()
        return intersection / union if union > 0 else 0.0

    def track(self, curr_image, curr_segments, use_flow=True):
        if self.prev_segments is None:
            self.id_counter = int(np.max(curr_segments)) + 1
            new_segments = curr_segments.copy()
            self.prev_features = self._extract_segment_features(curr_image, new_segments)
            for sid in np.unique(new_segments):
                self.track_history[sid].append(self.prev_features[sid]["centroid"])
            self.prev_segments = new_segments
            self.prev_image = curr_image
            return new_segments

        prev_gray = cv2.cvtColor(self.prev_image, cv2.COLOR_RGB2GRAY)
        curr_gray = cv2.cvtColor(curr_image, cv2.COLOR_RGB2GRAY)

        if use_flow:
            try:
                self.optical_flow = self._compute_optical_flow(prev_gray, curr_gray)
                warped = self._warp_segments(self.prev_segments, self.optical_flow)
            except Exception:
                warped = self.prev_segments
        else:
            warped = self.prev_segments

        curr_features = self._extract_segment_features(curr_image, curr_segments)
        prev_features = self.prev_features

        prev_ids = list(prev_features.keys())
        curr_ids = list(curr_features.keys())

        matches = {}
        used_curr = set()

        for pid in prev_ids:
            best_cid = None
            best_score = -1.0
            for cid in curr_ids:
                if cid in used_curr:
                    continue
                overlap = self._compute_overlap(warped, curr_segments, pid, cid)
                if overlap < 0.05:
                    continue
                color_dist = np.linalg.norm(
                    prev_features[pid]["mean_lab"] - curr_features[cid]["mean_lab"]
                )
                color_sim = max(0, 1.0 - color_dist / 30.0)
                if use_flow and self.optical_flow is not None:
                    cy, cx = int(prev_features[pid]["centroid"][1]), int(prev_features[pid]["centroid"][0])
                    cy = np.clip(cy, 0, self.optical_flow.shape[0] - 1)
                    cx = np.clip(cx, 0, self.optical_flow.shape[1] - 1)
                    pred_pos = prev_features[pid]["centroid"] + self.optical_flow[cy, cx]
                    flow_dist = np.linalg.norm(pred_pos - curr_features[cid]["centroid"])
                    flow_sim = max(0, 1.0 - flow_dist / 50.0)
                else:
                    flow_sim = 1.0
                area_p = prev_features[pid]["area"]
                area_c = curr_features[cid]["area"]
                area_sim = 1.0 - abs(area_p - area_c) / max(area_p, area_c)
                score = 0.4 * overlap + 0.3 * color_sim + 0.2 * flow_sim + 0.1 * area_sim
                if score > best_score and score > 0.25:
                    best_score = score
                    best_cid = cid
            if best_cid is not None:
                matches[best_cid] = pid
                used_curr.add(best_cid)

        new_segments = curr_segments.copy()
        new_features = {}
        for cid in curr_ids:
            if cid in matches:
                new_id = matches[cid]
            else:
                new_id = self.id_counter
                self.id_counter += 1
            new_segments[curr_segments == cid] = new_id
            feat = curr_features[cid].copy()
            new_features[new_id] = feat
            self.track_history[new_id].append(feat["centroid"])

        self.prev_segments = new_segments
        self.prev_features = new_features
        self.prev_image = curr_image
        return new_segments

    def get_track_colors(self):
        colors = {}
        rng = np.random.RandomState(42)
        for tid in self.track_history:
            colors[tid] = rng.randint(0, 256, 3)
        return colors


class VideoSuperpixel:

    def __init__(self, algorithm="SLIC", n_segments=100, compactness_mode="auto",
                 edge_guided=False, temporal_weight=0.5):
        self.algorithm = algorithm
        self.n_segments = n_segments
        self.compactness_mode = compactness_mode
        self.edge_guided = edge_guided
        self.temporal_weight = temporal_weight
        self.tracker = SuperpixelTracker(max_history=10)
        self.classifier = SuperpixelClassifier(method="knn", n_neighbors=5)
        self.video_path = None
        self.video_capture = None
        self.fps = 0
        self.frame_count = 0
        self.current_frame_idx = 0
        self.frame_width = 0
        self.frame_height = 0
        self.frames_buffer = []
        self.segmentations = []
        self.prediction_history = []
        self.max_buffer = 100

    def open_video(self, video_path):
        self.video_capture = cv2.VideoCapture(video_path)
        if not self.video_capture.isOpened():
            raise FileNotFoundError(f"Cannot open video: {video_path}")
        self.video_path = video_path
        self.fps = self.video_capture.get(cv2.CAP_PROP_FPS)
        self.frame_count = int(self.video_capture.get(cv2.CAP_PROP_FRAME_COUNT))
        self.frame_width = int(self.video_capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.frame_height = int(self.video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.frames_buffer = []
        self.segmentations = []
        self.prediction_history = []
        self.tracker.reset()
        self.current_frame_idx = 0
        return True

    def close_video(self):
        if self.video_capture is not None:
            self.video_capture.release()
        self.video_capture = None

    def read_frame(self, frame_idx=None):
        if self.video_capture is None:
            return None
        if frame_idx is not None and frame_idx != self.current_frame_idx:
            self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            self.current_frame_idx = frame_idx
        ret, frame = self.video_capture.read()
        if not ret:
            return None
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        self.current_frame_idx += 1
        if len(self.frames_buffer) >= self.max_buffer:
            self.frames_buffer.pop(0)
            if len(self.segmentations) > 0:
                self.segmentations.pop(0)
            if len(self.prediction_history) > 0:
                self.prediction_history.pop(0)
        self.frames_buffer.append(frame)
        return frame

    def process_frame(self, frame, use_tracking=True, **kwargs):
        if self.temporal_weight > 0 and len(self.segmentations) > 0:
            prev_frame = self.frames_buffer[-2] if len(self.frames_buffer) >= 2 else frame
            blended = cv2.addWeighted(
                prev_frame, self.temporal_weight * 0.3,
                frame, 1.0 - self.temporal_weight * 0.3, 0
            )
            seg_image = blended
        else:
            seg_image = frame

        segmenter = SuperpixelSegmenter(seg_image)
        if self.algorithm == "SLIC":
            segments = segmenter.run_slic(
                n_segments=self.n_segments,
                compactness_mode=self.compactness_mode,
                edge_guided=self.edge_guided,
                **kwargs,
            )
        else:
            segments = segmenter.run_felzenszwalb(
                edge_guided=self.edge_guided,
                **kwargs,
            )

        if use_tracking:
            segments = self.tracker.track(frame, segments)

        self.segmentations.append(segments)

        if self.classifier.model is not None:
            pred_mask, preds = self.classifier.classify_image(frame, segments)
            self.prediction_history.append((pred_mask, preds))
        else:
            self.prediction_history.append(None)

        return segments, segmenter

    def process_video(self, max_frames=None, progress_callback=None):
        results = []
        frame_idx = 0
        while True:
            if max_frames is not None and frame_idx >= max_frames:
                break
            frame = self.read_frame()
            if frame is None:
                break
            segments, segmenter = self.process_frame(frame)
            results.append((frame, segments, segmenter))
            if progress_callback is not None:
                progress_callback(frame_idx, self.frame_count)
            frame_idx += 1
        return results

    def get_visualization(self, frame_idx=-1, mode="boundaries",
                         show_tracks=False, show_classification=False):
        if len(self.segmentations) == 0 or len(self.frames_buffer) == 0:
            return None
        segments = self.segmentations[frame_idx]
        frame = self.frames_buffer[frame_idx]
        temp_segmenter = SuperpixelSegmenter(frame)
        temp_segmenter.segments = segments

        if mode == "boundaries":
            vis = temp_segmenter.visualize_boundaries()
        elif mode == "mean_color":
            vis = temp_segmenter.visualize_mean_color()
        else:
            vis = temp_segmenter.visualize_random_color()

        if show_tracks:
            colors = self.tracker.get_track_colors()
            for tid, history in self.tracker.track_history.items():
                if len(history) < 2:
                    continue
                color = colors[tid].tolist()
                for i in range(len(history) - 1):
                    pt1 = tuple(history[i].astype(int))
                    pt2 = tuple(history[i + 1].astype(int))
                    cv2.line(vis, pt1, pt2, color, 2)
                last_pt = tuple(history[-1].astype(int))
                cv2.circle(vis, last_pt, 4, color, -1)
                cv2.putText(vis, str(tid), (last_pt[0] + 6, last_pt[1] - 6),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

        if show_classification and self.prediction_history[frame_idx] is not None:
            pred_mask, preds = self.prediction_history[frame_idx]
            vis = cv2.addWeighted(vis, 0.6, pred_mask, 0.4, 0)
            rng = np.random.RandomState(7)
            class_colors = {}
            for label in self.classifier.class_names:
                class_colors[label] = rng.randint(80, 256, 3)
            for sid, (label, prob) in preds.items():
                mask = segments == sid
                if mask.sum() == 0:
                    continue
                ys, xs = np.where(mask)
                cy, cx = int(ys.mean()), int(xs.mean())
                cname = self.classifier.class_names.get(label, str(label))
                color = class_colors.get(label, [255, 255, 255]).tolist()
                cv2.putText(vis, f"{cname}:{prob:.2f}", (cx - 20, cy),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.35, color, 1)

        return vis

    def save_output_video(self, output_path, mode="boundaries", show_tracks=False,
                          show_classification=False, max_frames=None):
        if len(self.frames_buffer) == 0:
            return False
        h, w = self.frames_buffer[0].shape[:2]
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter(output_path, fourcc, self.fps if self.fps > 0 else 20, (w, h))
        n_frames = len(self.segmentations)
        if max_frames is not None:
            n_frames = min(n_frames, max_frames)
        for i in range(n_frames):
            vis = self.get_visualization(i, mode, show_tracks, show_classification)
            if vis is None:
                continue
            vis_bgr = cv2.cvtColor(vis, cv2.COLOR_RGB2BGR)
            out.write(vis_bgr)
        out.release()
        return True

    def add_classification_sample(self, frame_idx, seg_id, class_label, class_name=None):
        if frame_idx >= len(self.frames_buffer) or frame_idx >= len(self.segmentations):
            return False
        return self.classifier.add_training_sample(
            self.frames_buffer[frame_idx],
            self.segmentations[frame_idx],
            seg_id, class_label, class_name
        )

    def train_classifier(self):
        return self.classifier.train()
