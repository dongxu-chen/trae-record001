import os
import time
import logging
import threading
import queue
import numpy as np
import cv2
import torch
import open3d as o3d
from collections import deque

logger = logging.getLogger(__name__)


class VideoStreamProcessor:
    def __init__(
        self,
        depth_estimator,
        cam_dicts=None,
        frame_skip=2,
        max_queue_size=30,
        voxel_size=0.01,
    ):
        self.depth_estimator = depth_estimator
        self.cam_dicts = cam_dicts or {}
        self.frame_skip = frame_skip
        self.max_queue_size = max_queue_size
        self.voxel_size = voxel_size

        self.frame_queue = queue.Queue(maxsize=max_queue_size)
        self.result_queue = queue.Queue(maxsize=max_queue_size)

        self._running = False
        self._processing = False
        self._frame_count = 0
        self._processed_count = 0
        self._start_time = None

        self.cumulative_pcd = o3d.geometry.PointCloud()
        self.pcd_lock = threading.Lock()

        self.keyframes = deque(maxlen=10)
        self.keyframe_interval = 5

    def start_stream(self, video_source=0):
        self._running = True
        self._start_time = time.time()
        self._frame_count = 0
        self._processed_count = 0

        self.capture_thread = threading.Thread(
            target=self._capture_loop, args=(video_source,), daemon=True
        )
        self.process_thread = threading.Thread(
            target=self._process_loop, daemon=True
        )

        self.capture_thread.start()
        self.process_thread.start()

        logger.info(f"Video stream started: source={video_source}")

    def stop_stream(self):
        self._running = False
        self._processing = False

        while not self.frame_queue.empty():
            try:
                self.frame_queue.get_nowait()
            except queue.Empty:
                break

        logger.info(
            f"Stream stopped: {self._processed_count} frames processed "
            f"in {time.time() - self._start_time:.1f}s"
        )

    def _capture_loop(self, video_source):
        cap = cv2.VideoCapture(video_source)
        if not cap.isOpened():
            logger.error(f"Cannot open video source: {video_source}")
            self._running = False
            return

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        frame_interval = 1.0 / fps

        while self._running:
            ret, frame = cap.read()
            if not ret:
                logger.warning("Failed to read frame, retrying...")
                time.sleep(0.1)
                continue

            self._frame_count += 1

            if self._frame_count % self.frame_skip != 0:
                continue

            if self._frame_count % self.keyframe_interval == 0:
                self.keyframes.append(frame.copy())

            try:
                self.frame_queue.put_nowait((self._frame_count, frame, time.time()))
            except queue.Full:
                try:
                    self.frame_queue.get_nowait()
                except queue.Empty:
                    pass
                self.frame_queue.put_nowait((self._frame_count, frame, time.time()))

            time.sleep(frame_interval * self.frame_skip * 0.5)

        cap.release()
        logger.info("Capture loop ended")

    def _process_loop(self):
        self._processing = True

        while self._running or not self.frame_queue.empty():
            try:
                frame_data = self.frame_queue.get(timeout=1.0)
            except queue.Empty:
                continue

            frame_idx, frame, timestamp = frame_data

            try:
                pcd_frame = self._process_frame(frame_idx, frame)

                if pcd_frame is not None and len(pcd_frame.points) > 0:
                    with self.pcd_lock:
                        self.cumulative_pcd += pcd_frame
                        self.cumulative_pcd = self.cumulative_pcd.voxel_down_sample(
                            self.voxel_size
                        )

                    result = {
                        "frame_idx": frame_idx,
                        "timestamp": timestamp,
                        "num_points": len(self.cumulative_pcd.points),
                        "num_frame_points": len(pcd_frame.points),
                        "total_frames": self._frame_count,
                        "processed_frames": self._processed_count,
                    }

                    try:
                        self.result_queue.put_nowait(result)
                    except queue.Full:
                        try:
                            self.result_queue.get_nowait()
                        except queue.Empty:
                            pass
                        self.result_queue.put_nowait(result)

                self._processed_count += 1

            except Exception as e:
                logger.error(f"Error processing frame {frame_idx}: {e}")

        self._processing = False
        logger.info("Process loop ended")

    def _process_frame(self, frame_idx, frame):
        if len(self.keyframes) < 2:
            return None

        ref_img = frame.copy()
        h, w = ref_img.shape[:2]

        ref_img_f = ref_img.astype(np.float32) / 255.0
        ref_img_f = ref_img_f.transpose(2, 0, 1)

        src_frames = list(self.keyframes)[-3:]
        src_imgs = [
            (src.astype(np.float32) / 255.0).transpose(2, 0, 1)
            for src in src_frames
        ]

        ref_cam = self._estimate_camera(frame_idx)
        src_cams = [self._estimate_camera(i) for i in range(len(src_frames))]

        try:
            from utils.helpers import generate_depth_values, to_tensor, load_cam_from_dict
            from config import MVSNET_CONFIG

            depth_min = MVSNET_CONFIG["depth_min"]
            depth_max = MVSNET_CONFIG["depth_max"]
            num_depth = min(MVSNET_CONFIG["num_depth"], 96)
            interval_scale = MVSNET_CONFIG["interval_scale"]

            depth_values = generate_depth_values(depth_min, depth_max, num_depth, interval_scale)

            device = self.depth_estimator.device

            ref_tensor = to_tensor(ref_img_f).unsqueeze(0).to(device)
            src_tensors = [to_tensor(s).unsqueeze(0).to(device) for s in src_imgs]

            ref_proj = ref_cam
            src_projs = src_cams

            ref_proj_tensor = to_tensor(ref_proj).unsqueeze(0).to(device)
            src_proj_tensors = [to_tensor(sp).unsqueeze(0).to(device) for sp in src_projs]
            depth_values_tensor = to_tensor(depth_values).unsqueeze(0).to(device)

            with torch.no_grad():
                depth_est, prob_volume = self.depth_estimator.model(
                    ref_tensor, src_tensors, ref_proj_tensor,
                    src_proj_tensors, depth_values_tensor
                )

            depth_map = depth_est.squeeze().cpu().numpy()
            prob_map = prob_volume.squeeze().cpu().numpy()

            prob_threshold = 0.5
            mask = prob_map.max(axis=0) > prob_threshold
            depth_map[~mask] = 0

            pcd = self._depth_to_point_cloud(depth_map, ref_cam, ref_img)
            return pcd

        except Exception as e:
            logger.error(f"Depth estimation failed for frame {frame_idx}: {e}")
            return None

    def _estimate_camera(self, frame_idx):
        if frame_idx in self.cam_dicts:
            cam = self.cam_dicts[frame_idx]
            import numpy as np
            return np.array(cam.get("proj", cam.get("intrinsic", np.eye(4))))

        h, w = 480, 640
        fx, fy = 500.0, 500.0
        cx, cy = w / 2.0, h / 2.0

        intrinsic = np.array([
            [fx, 0, cx, 0],
            [0, fy, cy, 0],
            [0, 0, 1, 0],
            [0, 0, 0, 1],
        ], dtype=np.float32)

        return intrinsic

    def _depth_to_point_cloud(self, depth_map, proj, image=None):
        h, w = depth_map.shape

        if proj.shape[0] == 4 and proj.shape[1] == 4:
            intrinsic = proj[:3, :3]
            extrinsic = np.eye(4)
        else:
            intrinsic = proj
            extrinsic = np.eye(4)

        fx = intrinsic[0, 0] if intrinsic.shape[0] >= 1 else 500.0
        fy = intrinsic[1, 1] if intrinsic.shape[0] >= 2 else 500.0
        cx = intrinsic[0, 2] if intrinsic.shape[0] >= 1 else w / 2.0
        cy = intrinsic[1, 2] if intrinsic.shape[0] >= 2 else h / 2.0

        mask = depth_map > 0
        ys, xs = np.where(mask)
        ds = depth_map[mask]

        x_cam = (xs - cx) * ds / fx
        y_cam = (ys - cy) * ds / fy
        z_cam = ds

        pts_cam = np.stack([x_cam, y_cam, z_cam], axis=-1)

        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(pts_cam)

        if image is not None:
            if image.max() > 1.0:
                colors = image[ys, xs].astype(np.float64) / 255.0
            else:
                colors = image[ys, xs].astype(np.float64)
            pcd.colors = o3d.utility.Vector3dVector(colors)

        return pcd

    def get_cumulative_point_cloud(self):
        with self.pcd_lock:
            pcd_copy = o3d.geometry.PointCloud(self.cumulative_pcd)
        return pcd_copy

    def get_stream_stats(self):
        elapsed = time.time() - self._start_time if self._start_time else 0
        fps = self._processed_count / elapsed if elapsed > 0 else 0
        return {
            "running": self._running,
            "total_frames_captured": self._frame_count,
            "frames_processed": self._processed_count,
            "queue_size": self.frame_queue.qsize(),
            "total_points": len(self.cumulative_pcd.points),
            "processing_fps": round(fps, 2),
            "elapsed_seconds": round(elapsed, 1),
        }

    def get_latest_result(self):
        try:
            return self.result_queue.get_nowait()
        except queue.Empty:
            return None

    def save_point_cloud(self, output_path):
        with self.pcd_lock:
            pcd = o3d.geometry.PointCloud(self.cumulative_pcd)
        o3d.io.write_point_cloud(output_path, pcd)
        logger.info(f"Saved real-time point cloud: {output_path} ({len(pcd.points)} points)")
        return output_path


class IncrementalReconstructor:
    def __init__(self, voxel_size=0.01, max_keyframes=20, min_motion=5.0):
        self.voxel_size = voxel_size
        self.max_keyframes = max_keyframes
        self.min_motion = min_motion

        self.keyframes = []
        self.keyframe_depths = []
        self.cumulative_pcd = o3d.geometry.PointCloud()
        self.pcd_lock = threading.Lock()

        self.prev_gray = None
        self.trajectory = []

    def add_frame(self, frame, depth_map=None, cam_dict=None):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame

        is_keyframe = self._should_add_keyframe(gray)

        if is_keyframe:
            self.keyframes.append(frame.copy())
            if depth_map is not None:
                self.keyframe_depths.append(depth_map.copy())

            if len(self.keyframes) > self.max_keyframes:
                self.keyframes.pop(0)
                if self.keyframe_depths:
                    self.keyframe_depths.pop(0)

        if depth_map is not None:
            self._integrate_depth(depth_map, frame, cam_dict)

        self.prev_gray = gray.copy()
        return is_keyframe

    def _should_add_keyframe(self, gray):
        if self.prev_gray is None:
            return True

        if len(self.keyframes) == 0:
            return True

        try:
            flow = cv2.calcOpticalFlowFarneback(
                self.prev_gray, gray, None, 0.5, 3, 15, 3, 5, 1.2, 0
            )
            magnitude = np.sqrt(flow[..., 0] ** 2 + flow[..., 1] ** 2)
            avg_motion = np.mean(magnitude)

            return avg_motion > self.min_motion
        except Exception:
            return True

    def _integrate_depth(self, depth_map, image, cam_dict):
        h, w = depth_map.shape

        if cam_dict is not None:
            intrinsic = np.array(cam_dict.get("intrinsic", np.eye(3)))
            extrinsic = np.array(cam_dict.get("extrinsic", np.eye(4)))
        else:
            intrinsic = np.array([[500, 0, w / 2], [0, 500, h / 2], [0, 0, 1]], dtype=np.float64)
            extrinsic = np.eye(4)

        fx, fy = intrinsic[0, 0], intrinsic[1, 1]
        cx, cy = intrinsic[0, 2], intrinsic[1, 2]
        R = extrinsic[:3, :3]
        t = extrinsic[:3, 3]

        mask = depth_map > 0
        ys, xs = np.where(mask)
        ds = depth_map[mask]

        x_cam = (xs - cx) * ds / fx
        y_cam = (ys - cy) * ds / fy
        z_cam = ds

        pts_cam = np.stack([x_cam, y_cam, z_cam], axis=-1)
        pts_world = (R.T @ (pts_cam - t).T).T

        pcd_frame = o3d.geometry.PointCloud()
        pcd_frame.points = o3d.utility.Vector3dVector(pts_world)

        if image is not None:
            img_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB) if image.ndim == 3 else image
            colors = img_rgb[ys, xs].astype(np.float64) / 255.0
            pcd_frame.colors = o3d.utility.Vector3dVector(colors)

        with self.pcd_lock:
            self.cumulative_pcd += pcd_frame
            self.cumulative_pcd = self.cumulative_pcd.voxel_down_sample(self.voxel_size)

    def get_point_cloud(self):
        with self.pcd_lock:
            return o3d.geometry.PointCloud(self.cumulative_pcd)

    def get_stats(self):
        return {
            "num_keyframes": len(self.keyframes),
            "total_points": len(self.cumulative_pcd.points),
        }
