import cv2
import numpy as np
import time
from depth_estimator import MiDaSDepthEstimator
from crf_optimizer import FastCRFDepthOptimizer
from depth_super_resolution import (
    DepthSuperResolution,
    align_depth_to_rgb,
    create_aligned_colored_depth,
    compute_depth_metrics,
    MetricsAccumulator,
)
from utils import (
    colorize_depth,
    colorize_depth_dynamic,
    enhance_edges,
    overlay_edges_on_depth,
    temporal_smooth,
    create_side_by_side,
    upsample_depth,
    align_and_colorize,
    format_metrics_display,
)


class VideoProcessor:
    def __init__(
        self,
        model_type="DPT_Hybrid",
        use_crf=True,
        colormap="turbo",
        edge_method="canny",
        edge_overlay=False,
        temporal_alpha=0.7,
        crf_iterations=3,
        target_width=640,
        crf_downscale=2,
        use_fast_approx=True,
        adaptive_edges=True,
        dynamic_colorization=True,
        texture_skip_threshold=0.01,
        use_super_resolution=False,
        sr_method="bilinear_guided",
        sr_scale=2,
        align_depth_to_rgb_flag=True,
        alpha_blend=0.0,
        evaluate=False,
        gt_depth_path=None,
    ):
        self.estimator = MiDaSDepthEstimator(model_type=model_type)
        self.crf_optimizer = None
        if use_crf:
            self.crf_optimizer = FastCRFDepthOptimizer(
                num_iterations=crf_iterations,
                downscale=crf_downscale,
                use_approx=use_fast_approx,
                texture_skip_threshold=texture_skip_threshold,
            )
        self.use_crf = use_crf
        self.colormap = colormap
        self.edge_method = edge_method
        self.edge_overlay = edge_overlay
        self.temporal_alpha = temporal_alpha
        self.target_width = target_width
        self.adaptive_edges = adaptive_edges
        self.dynamic_colorization = dynamic_colorization
        self.prev_depth = None
        self.fps = 0.0

        self.use_super_resolution = use_super_resolution
        if use_super_resolution:
            self.sr = DepthSuperResolution(method=sr_method, scale_factor=sr_scale)
        else:
            self.sr = None
        self.sr_method = sr_method
        self.sr_scale = sr_scale

        self.align_depth_to_rgb_flag = align_depth_to_rgb_flag
        self.alpha_blend = alpha_blend

        self.evaluate = evaluate
        self.metrics_accumulator = MetricsAccumulator() if evaluate else None
        self.gt_depth_path = gt_depth_path
        self.last_metrics = {}

    def _resize_frame(self, frame):
        h, w = frame.shape[:2]
        if w > self.target_width:
            scale = self.target_width / w
            frame = cv2.resize(frame, (self.target_width, int(h * scale)))
        return frame

    def process_frame(self, frame, gt_depth=None):
        start_time = time.time()

        frame_full = frame.copy()
        frame = self._resize_frame(frame)
        depth_map = self.estimator.estimate(frame)

        if depth_map is None:
            return None, None, 0.0, {}

        depth_low_res = depth_map.copy()

        if self.use_crf and self.crf_optimizer is not None:
            edges = enhance_edges(
                frame,
                method=self.edge_method,
                low_threshold=30,
                high_threshold=90,
                adaptive=self.adaptive_edges,
                min_enhancement=0.3,
                max_enhancement=1.0,
                texture_threshold=0.25,
            )
            if edges is not None:
                edge_map = edges.astype(np.float32) / 255.0
            else:
                edge_map = None
            depth_map = self.crf_optimizer.optimize_with_edge_guidance(frame, depth_map, edge_map)

        depth_map = temporal_smooth(self.prev_depth, depth_map, self.temporal_alpha)
        self.prev_depth = depth_map.copy()

        if self.use_super_resolution and self.sr is not None:
            h_full, w_full = frame_full.shape[:2]
            depth_map = self.sr.upsample(depth_map, frame_full, (h_full, w_full))

        if self.align_depth_to_rgb_flag:
            h_full, w_full = frame_full.shape[:2]
            depth_map, _ = align_depth_to_rgb(depth_map, frame_full)
            if depth_map.shape[:2] != (h_full, w_full):
                depth_map = cv2.resize(depth_map, (w_full, h_full), interpolation=cv2.INTER_LINEAR)

        if self.dynamic_colorization:
            if self.align_depth_to_rgb_flag:
                depth_colorized = create_aligned_colored_depth(
                    depth_map, frame_full, colormap=self.colormap,
                    dynamic_mapping=True, alpha_blend=self.alpha_blend
                )
            else:
                depth_colorized = colorize_depth_dynamic(depth_map, colormap=self.colormap, adaptive=True)
        else:
            if self.align_depth_to_rgb_flag:
                depth_colorized = create_aligned_colored_depth(
                    depth_map, frame_full, colormap=self.colormap,
                    dynamic_mapping=False, alpha_blend=self.alpha_blend
                )
            else:
                depth_colorized = colorize_depth(depth_map, colormap=self.colormap)

        if self.edge_overlay:
            edges = enhance_edges(
                frame_full if self.align_depth_to_rgb_flag else frame,
                method=self.edge_method,
                low_threshold=30,
                high_threshold=90,
                adaptive=self.adaptive_edges,
            )
            if edges is not None:
                if depth_colorized.shape[:2] != edges.shape[:2]:
                    edges = cv2.resize(edges, (depth_colorized.shape[1], depth_colorized.shape[0]))
                depth_colorized = overlay_edges_on_depth(depth_colorized, edges, alpha=0.3, color=(0, 255, 0))

        metrics = {}
        if self.evaluate and gt_depth is not None:
            metrics = compute_depth_metrics(depth_map, gt_depth)
            self.last_metrics = metrics
            if self.metrics_accumulator is not None:
                self.metrics_accumulator.update(metrics)

        elapsed = time.time() - start_time
        self.fps = 1.0 / max(elapsed, 1e-6)

        return depth_map, depth_colorized, self.fps, metrics

    def process_video_file(self, video_path, output_path=None, display_callback=None):
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {video_path}")

        writer = None
        if output_path:
            fps_video = cap.get(cv2.CAP_PROP_FPS)
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(output_path, fourcc, fps_video, (w * 2, h))

        self.prev_depth = None
        frame_count = 0

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                depth_map, depth_colorized, fps = self.process_frame(frame)
                if depth_map is None:
                    continue

                result = create_side_by_side(frame, depth_colorized)

                if writer is not None:
                    result_resized = cv2.resize(result, (w * 2, h))
                    writer.write(result_resized)

                if display_callback:
                    display_callback(frame, depth_map, depth_colorized, fps, frame_count)

                frame_count += 1
        finally:
            cap.release()
            if writer is not None:
                writer.release()

        return frame_count

    def process_webcam(self, camera_id=0, display_callback=None):
        cap = cv2.VideoCapture(camera_id)
        if not cap.isOpened():
            raise ValueError(f"Cannot open camera: {camera_id}")

        self.prev_depth = None

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                depth_map, depth_colorized, fps, metrics = self.process_frame(frame)
                if depth_map is None:
                    continue

                result = create_side_by_side(frame, depth_colorized)

                fps_text = f"FPS: {fps:.1f}"
                cv2.putText(result, fps_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

                if metrics and "rmse" in metrics and not np.isnan(metrics["rmse"]):
                    metrics_text = f"RMSE: {metrics['rmse']:.4f}  δ1: {metrics['delta1']*100:.1f}%"
                    cv2.putText(result, metrics_text, (10, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

                if self.use_super_resolution:
                    sr_text = f"SR: {self.sr_method} x{self.sr_scale}"
                    cv2.putText(result, sr_text, (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

                cv2.imshow("Monocular Depth Estimation", result)
                key = cv2.waitKey(1) & 0xFF
                if key == 27 or key == ord("q"):
                    break

                if display_callback:
                    display_callback(frame, depth_map, depth_colorized, fps, 0, metrics)
        finally:
            cap.release()
            cv2.destroyAllWindows()

    def reset_temporal(self):
        self.prev_depth = None


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Real-time depth estimation with CRF optimization")
    parser.add_argument("--webcam", action="store_true", help="Use webcam")
    parser.add_argument("--video", type=str, default=None, help="Video file path")
    parser.add_argument("--model", type=str, default="DPT_Hybrid", choices=["MiDaS_small", "DPT_Hybrid", "DPT_Large"])
    parser.add_argument("--no-crf", action="store_true", help="Disable CRF optimization")
    parser.add_argument("--target-width", type=int, default=640)
    parser.add_argument("--colormap", type=str, default="turbo")
    parser.add_argument("--no-fast", action="store_true", help="Disable fast CRF approximation")
    parser.add_argument("--no-adaptive", action="store_true", help="Disable adaptive edge enhancement")
    parser.add_argument("--no-dynamic-color", action="store_true", help="Disable dynamic colorization")
    parser.add_argument("--sr", action="store_true", help="Enable depth super-resolution")
    parser.add_argument("--sr-method", type=str, default="bilinear_guided",
                        choices=["nearest", "bilinear", "bicubic", "bilinear_guided", "laplacian_pyramid", "edge_preserving"])
    parser.add_argument("--sr-scale", type=int, default=2, help="Super-resolution scale factor")
    parser.add_argument("--no-align", action="store_true", help="Disable depth-RGB alignment")
    parser.add_argument("--alpha-blend", type=float, default=0.0, help="Alpha blend for aligned depth (0-1)")
    parser.add_argument("--evaluate", action="store_true", help="Enable evaluation metrics (need GT depth)")
    parser.add_argument("--gt-depth", type=str, default=None, help="Ground truth depth path for evaluation")
    args = parser.parse_args()

    proc = VideoProcessor(
        model_type=args.model,
        use_crf=not args.no_crf,
        colormap=args.colormap,
        target_width=args.target_width,
        use_fast_approx=not args.no_fast,
        adaptive_edges=not args.no_adaptive,
        dynamic_colorization=not args.no_dynamic_color,
        use_super_resolution=args.sr,
        sr_method=args.sr_method,
        sr_scale=args.sr_scale,
        align_depth_to_rgb_flag=not args.no_align,
        alpha_blend=args.alpha_blend,
        evaluate=args.evaluate,
        gt_depth_path=args.gt_depth,
    )

    if args.webcam:
        proc.process_webcam()
    elif args.video:
        proc.process_video_file(args.video)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
