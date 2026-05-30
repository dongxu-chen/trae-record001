import argparse
import os
import numpy as np
import cv2

from stereo_depth import (
    StereoParams, SGMConfig, StereoDepthPipeline, PointCloudGenerator,
)
from visualize import (
    plot_pipeline_results, plot_disparity, plot_depth,
    colormap_disparity, colormap_depth, visualize_point_cloud_open3d,
    save_point_cloud_ply,
)


def generate_sample_stereo_pair(width=640, height=480):
    np.random.seed(42)
    img_l = np.zeros((height, width, 3), dtype=np.uint8)
    img_r = np.zeros((height, width, 3), dtype=np.uint8)

    for y in range(0, height, 60):
        for x in range(0, width, 80):
            color = np.random.randint(60, 220, size=3).tolist()
            cv2.rectangle(img_l, (x, y), (x + 70, y + 50), color, -1)
            cv2.rectangle(img_r, (x + 20, y), (x + 90, y + 50), color, -1)

    for cx, cy, r, base_d in [(200, 200, 60, 30), (400, 300, 45, 20), (320, 150, 35, 15)]:
        color = np.random.randint(80, 240, size=3).tolist()
        cv2.circle(img_l, (cx, cy), r, color, -1)
        cv2.circle(img_r, (cx + base_d, cy), r, color, -1)

    noise_l = np.random.normal(0, 5, img_l.shape).astype(np.int16)
    noise_r = np.random.normal(0, 5, img_r.shape).astype(np.int16)
    img_l = np.clip(img_l.astype(np.int16) + noise_l, 0, 255).astype(np.uint8)
    img_r = np.clip(img_r.astype(np.int16) + noise_r, 0, 255).astype(np.uint8)

    return img_l, img_r


def create_default_params(width=640, height=480):
    focal = 600.0
    baseline = 0.1
    cx, cy = width / 2.0, height / 2.0

    camera_matrix_l = np.array([[focal, 0, cx], [0, focal, cy], [0, 0, 1]], dtype=np.float64)
    camera_matrix_r = camera_matrix_l.copy()
    dist_coeffs_l = np.zeros((5, 1), dtype=np.float64)
    dist_coeffs_r = np.zeros((5, 1), dtype=np.float64)
    R = np.eye(3, dtype=np.float64)
    T = np.array([[baseline], [0], [0]], dtype=np.float64)

    params = StereoParams(
        camera_matrix_l=camera_matrix_l,
        dist_coeffs_l=dist_coeffs_l,
        camera_matrix_r=camera_matrix_r,
        dist_coeffs_r=dist_coeffs_r,
        R=R, T=T, image_size=(width, height),
    )

    rect_l, rect_r, proj_l, proj_r, Q, roi_l, roi_r = cv2.stereoRectify(
        camera_matrix_l, dist_coeffs_l,
        camera_matrix_r, dist_coeffs_r,
        (width, height), R, T,
        alpha=0, flags=cv2.CALIB_ZERO_DISPARITY,
    )
    params.rect_l = rect_l
    params.rect_r = rect_r
    params.proj_l = proj_l
    params.proj_r = proj_r
    params.Q = Q
    params.roi_l = roi_l
    params.roi_r = roi_r

    map_lx, map_ly = cv2.initUndistortRectifyMap(
        camera_matrix_l, dist_coeffs_l,
        rect_l, proj_l, (width, height), cv2.CV_32FC1,
    )
    map_rx, map_ry = cv2.initUndistortRectifyMap(
        camera_matrix_r, dist_coeffs_r,
        rect_r, proj_r, (width, height), cv2.CV_32FC1,
    )
    params.map_lx = map_lx
    params.map_ly = map_ly
    params.map_rx = map_rx
    params.map_ry = map_ry

    return params


def run_benchmark(args):
    print("=" * 60)
    print("  GPU Performance Benchmark")
    print("=" * 60)

    w, h = 640, 480
    print(f"\nImage size: {w}x{h}")
    img_l, img_r = generate_sample_stereo_pair(w, h)

    sgm_config = SGMConfig(
        min_disparity=args.min_disparity,
        num_disparities=args.num_disparities,
        block_size=args.block_size,
        use_gpu=not args.no_gpu,
        target_fps=args.target_fps,
    )

    params = create_default_params(w, h)
    pipeline = StereoDepthPipeline(params, sgm_config)
    pipeline.rectify(img_l, img_r)

    print(f"\nRunning {args.benchmark_seconds:.1f}s benchmark...")
    bench_result = pipeline.benchmark_gpu(
        pipeline._rect_l, pipeline._rect_r, seconds=args.benchmark_seconds,
    )
    fps = bench_result.get("fps", 0)
    use_cuda = bench_result.get("use_cuda", False)

    print(f"\nResults:")
    print(f"  CUDA Enabled: {use_cuda}")
    print(f"  Average FPS: {fps:.2f}")
    print(f"  Frames: {bench_result.get('frames', 0)}")
    print(f"  Latency: {1000.0 / fps:.2f} ms/frame" if fps > 0 else "  Latency: N/A")

    if fps >= 30:
        print(f"  Status: ✅ PASSED (>=30 FPS target)")
    else:
        print(f"  Status: ⚠️  Below 30 FPS target")

    return fps


def run_demo(args):
    print("=" * 60)
    print("  Stereo Depth Estimation with Adaptive SGM")
    print("=" * 60)

    if args.left and args.right:
        print(f"\nLoading images: {args.left}, {args.right}")
        img_l = cv2.imread(args.left)
        img_r = cv2.imread(args.right)
        if img_l is None or img_r is None:
            print("Error: Could not load images. Using synthetic data.")
            img_l, img_r = generate_sample_stereo_pair()
    else:
        print("\nNo input images specified. Using synthetic stereo pair.")
        img_l, img_r = generate_sample_stereo_pair()

    h, w = img_l.shape[:2]
    print(f"Image size: {w}x{h}")

    sgm_config = SGMConfig(
        min_disparity=args.min_disparity,
        num_disparities=args.num_disparities,
        block_size=args.block_size,
        p1=args.p1,
        p2=args.p2,
        use_mode_hq=args.hq_mode,
        wsl_lambda=args.wls_lambda,
        wsl_sigma=args.wls_sigma,
        fill_holes=args.fill_holes,
        subpixel_refine=args.subpixel,
        adaptive_p2=not args.no_adaptive_p2,
        adaptive_p1=not args.no_adaptive_p1,
        gradient_scale=args.gradient_scale,
        multi_peak_detect=not args.no_multi_peak,
        peak_ratio=args.peak_ratio,
        peak_min_distance=args.peak_min_distance,
        use_gpu=not args.no_gpu,
        use_dl_refine=args.dl_refine,
        dl_device=args.dl_device,
        use_super_res=args.sr,
        sr_scale=args.sr_scale,
        sr_method=args.sr_method,
        enhance_weak_texture=args.enhance_weak,
        weak_texture_grad_thresh=args.weak_grad_thresh,
        use_bilateral_solver=args.bilateral_solver,
        target_fps=args.target_fps,
    )

    adapt_str = "ON" if sgm_config.adaptive_p2 else "OFF"
    mpeak_str = "ON" if sgm_config.multi_peak_detect else "OFF"
    gpu_str = "ON" if sgm_config.use_gpu else "OFF"
    dl_str = "ON" if sgm_config.use_dl_refine else "OFF"
    sr_str = "ON" if sgm_config.use_super_res else "OFF"
    weak_str = "ON" if sgm_config.enhance_weak_texture else "OFF"
    print(f"\nSGM Config: ndisp={sgm_config.num_disparities}, block={sgm_config.block_size}, "
          f"P1={sgm_config.p1}, P2={sgm_config.p2}")
    print(f"  Adaptive P1/P2: {adapt_str} (gradient_scale={sgm_config.gradient_scale})")
    print(f"  Multi-peak detect: {mpeak_str} (ratio={sgm_config.peak_ratio}, "
          f"min_dist={sgm_config.peak_min_distance})")
    print(f"  GPU Acceleration: {gpu_str}, DL Refine: {dl_str}, Super-Res: {sr_str}, Weak enhance: {weak_str}")

    params = create_default_params(w, h)
    pipeline = StereoDepthPipeline(params, sgm_config)

    print("\nRunning pipeline...")
    results = pipeline.run(img_l, img_r, use_lr=args.use_lr, max_depth=args.max_depth)

    disp_raw = results["disparity_raw"]
    disp_filt = results["disparity_filtered"]
    depth = results["depth"]
    points = results["points_3d"]
    colors = results["colors"]
    confidence = results["confidence"]
    gradient = results["gradient"]

    valid_disp = disp_filt[disp_filt > 0]
    valid_depth = depth[depth > 0]
    high_conf = np.sum(confidence > 0.3) if confidence is not None else 0
    total_conf = np.sum(confidence > 0) if confidence is not None else 1
    print(f"\nResults:")
    print(f"  Raw disparity range: [{disp_raw.min():.1f}, {disp_raw.max():.1f}]")
    if valid_disp.size > 0:
        print(f"  Filtered disparity range: [{valid_disp.min():.1f}, {valid_disp.max():.1f}]")
    if valid_depth.size > 0:
        print(f"  Depth range: [{valid_depth.min():.3f}, {valid_depth.max():.3f}] m")
    if confidence is not None:
        print(f"  High-confidence pixels: {high_conf} / {total_conf} "
              f"({100.0 * high_conf / max(total_conf, 1):.1f}%)")
    print(f"  3D points (colored): {points.shape[0]}")

    output_dir = args.output_dir
    os.makedirs(output_dir, exist_ok=True)

    print(f"\nSaving results to {output_dir}/ ...")

    cv2.imwrite(os.path.join(output_dir, "disparity_raw.png"),
                colormap_disparity(disp_raw))
    cv2.imwrite(os.path.join(output_dir, "disparity_filtered.png"),
                colormap_disparity(disp_filt))
    cv2.imwrite(os.path.join(output_dir, "depth_map.png"),
                colormap_depth(depth))
    cv2.imwrite(os.path.join(output_dir, "rectified_left.png"), results["rectified_left"])
    cv2.imwrite(os.path.join(output_dir, "rectified_right.png"), results["rectified_right"])

    if confidence is not None:
        conf_vis = (confidence * 255).astype(np.uint8)
        conf_color = cv2.applyColorMap(conf_vis, cv2.COLORMAP_JET)
        cv2.imwrite(os.path.join(output_dir, "confidence.png"), conf_color)

    if gradient is not None:
        grad_vis = cv2.normalize(gradient, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
        grad_color = cv2.applyColorMap(grad_vis, cv2.COLORMAP_HOT)
        cv2.imwrite(os.path.join(output_dir, "gradient.png"), grad_color)

    np.save(os.path.join(output_dir, "disparity.npy"), disp_filt)
    np.save(os.path.join(output_dir, "depth.npy"), depth)
    if confidence is not None:
        np.save(os.path.join(output_dir, "confidence.npy"), confidence)

    plot_disparity(disp_raw, title="Raw Disparity (Adaptive SGM)",
                   save_path=os.path.join(output_dir, "plot_disparity_raw.png"))
    plot_disparity(disp_filt, title="Filtered Disparity",
                   save_path=os.path.join(output_dir, "plot_disparity_filtered.png"))
    plot_depth(depth, title="Depth Map",
               save_path=os.path.join(output_dir, "plot_depth.png"))
    plot_pipeline_results(results, save_path=os.path.join(output_dir, "plot_pipeline.png"))

    if points.shape[0] > 0:
        ply_path = os.path.join(output_dir, "point_cloud.ply")
        save_point_cloud_ply(points, colors, ply_path)
        print(f"  Point cloud saved (with original image colors): {ply_path}")

    print("\nDone!")
    return results


def main():
    parser = argparse.ArgumentParser(description="Stereo Depth Estimation with Adaptive SGM")
    parser.add_argument("--left", type=str, default="", help="Left image path")
    parser.add_argument("--right", type=str, default="", help="Right image path")
    parser.add_argument("--output-dir", type=str, default="output", help="Output directory")
    parser.add_argument("--min-disparity", type=int, default=0, help="Minimum disparity")
    parser.add_argument("--num-disparities", type=int, default=64, help="Number of disparities (must be multiple of 16)")
    parser.add_argument("--block-size", type=int, default=5, help="Matching block size")
    parser.add_argument("--p1", type=int, default=8, help="Base penalty on disparity change by 1")
    parser.add_argument("--p2", type=int, default=32, help="Base penalty on disparity change by >1")
    parser.add_argument("--gradient-scale", type=float, default=1.0, help="Gradient scale factor for adaptive P1/P2")
    parser.add_argument("--no-adaptive-p2", action="store_true", help="Disable gradient-adaptive P2")
    parser.add_argument("--no-adaptive-p1", action="store_true", help="Disable gradient-adaptive P1")
    parser.add_argument("--no-multi-peak", action="store_true", help="Disable multi-peak detection")
    parser.add_argument("--peak-ratio", type=float, default=0.85, help="Peak ratio threshold (lower=strict)")
    parser.add_argument("--peak-min-distance", type=int, default=3, help="Min disparity distance between peaks")
    parser.add_argument("--wls-lambda", type=float, default=8000.0, help="WLS filter lambda")
    parser.add_argument("--wls-sigma", type=float, default=1.5, help="WLS filter sigma")
    parser.add_argument("--max-depth", type=float, default=10.0, help="Maximum depth for point cloud (m)")
    parser.add_argument("--hq-mode", action="store_true", help="Use HQ SGM mode")
    parser.add_argument("--use-lr", action="store_true", default=True, help="Use LR consistency check")
    parser.add_argument("--fill-holes", action="store_true", default=True, help="Fill invalid disparity holes")
    parser.add_argument("--subpixel", action="store_true", default=True, help="Sub-pixel refinement")
    parser.add_argument("--no-gpu", action="store_true", help="Disable GPU acceleration")
    parser.add_argument("--dl-refine", action="store_true", help="Enable deep learning disparity refinement")
    parser.add_argument("--dl-device", type=str, default="auto", help="DL device: auto/cpu/cuda/mps")
    parser.add_argument("--sr", action="store_true", help="Enable depth super-resolution")
    parser.add_argument("--sr-scale", type=int, default=4, help="Super-resolution scale factor")
    parser.add_argument("--sr-method", type=str, default="hybrid", help="SR method: bicubic/espcn/guided/hybrid")
    parser.add_argument("--enhance-weak", action="store_true", help="Enhance weak texture regions")
    parser.add_argument("--weak-grad-thresh", type=float, default=15.0, help="Weak texture gradient threshold")
    parser.add_argument("--bilateral-solver", action="store_true", help="Use fast bilateral solver")
    parser.add_argument("--target-fps", type=int, default=30, help="Target FPS for real-time mode")
    parser.add_argument("--benchmark", action="store_true", help="Run GPU performance benchmark")
    parser.add_argument("--benchmark-seconds", type=float, default=3.0, help="Benchmark duration (seconds)")
    args = parser.parse_args()
    if args.benchmark:
        run_benchmark(args)
    else:
        run_demo(args)


if __name__ == "__main__":
    main()
