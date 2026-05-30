#!/usr/bin/env python3
import argparse
import sys
import os
import numpy as np
import cv2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src import (
    FisheyeCorrector,
    CorrectionMethod,
    BorderHandlingMode,
    FisheyeProjectionType,
    BatchProcessor,
    FisheyeVisualizer,
    FisheyeCalibrator,
    LensConfigManager,
    estimate_fisheye_params_auto,
    self_calibrate_from_lines,
    create_projection_model,
    correct_fisheye_image,
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Fisheye Image Correction Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Correct a single image with auto parameter estimation
  python main.py --input input.jpg --output output.jpg

  # Correct with specific projection model and parameters
  python main.py --input input.jpg --output output.jpg --projection equisolid --focal 500 --center 640 480

  # Use equirectangular projection for panorama
  python main.py --input input.jpg --output panorama.jpg --method equirectangular

  # Batch process a directory
  python main.py --input-dir ./fisheye_images --output-dir ./corrected

  # Calibrate with chessboard images first, then process
  python main.py --calibration-dir ./calib_images --input-dir ./fisheye --output-dir ./corrected

  # Process a video
  python main.py --video input.mp4 --output-video output.mp4

  # Show visualization comparison
  python main.py --input input.jpg --visualize
        """,
    )

    parser.add_argument("--input", "-i", type=str, help="Input image path")
    parser.add_argument("--output", "-o", type=str, help="Output image path")
    parser.add_argument(
        "--input-dir", type=str, help="Input directory for batch processing"
    )
    parser.add_argument(
        "--output-dir", type=str, help="Output directory for batch processing"
    )
    parser.add_argument("--video", type=str, help="Input video path")
    parser.add_argument("--output-video", type=str, help="Output video path")

    parser.add_argument(
        "--method",
        "-m",
        type=str,
        default="spherical",
        choices=["spherical", "equirectangular", "perspective"],
        help="Correction method (default: spherical)",
    )
    parser.add_argument(
        "--projection",
        "-p",
        type=str,
        default="auto",
        choices=["auto", "equidistant", "equisolid", "orthographic", "stereographic"],
        help="Fisheye projection model (default: auto)",
    )
    parser.add_argument(
        "--focal", type=float, help="Focal length in pixels (auto-estimated if not set)"
    )
    parser.add_argument(
        "--center",
        type=float,
        nargs=2,
        metavar=("CX", "CY"),
        help="Principal point (center) coordinates (auto-estimated if not set)",
    )
    parser.add_argument(
        "--fov", type=float, help="Field of view in degrees (for auto estimation)"
    )
    parser.add_argument(
        "--output-size",
        type=int,
        nargs=2,
        metavar=("W", "H"),
        help="Output image size (width height)",
    )

    parser.add_argument(
        "--calibration-dir",
        type=str,
        help="Directory containing chessboard images for calibration",
    )
    parser.add_argument(
        "--chessboard",
        type=int,
        nargs=2,
        default=(9, 6),
        metavar=("W", "H"),
        help="Chessboard inner corners count (default: 9 6)",
    )
    parser.add_argument(
        "--square-size",
        type=float,
        default=1.0,
        help="Chessboard square size in real units (default: 1.0)",
    )

    parser.add_argument(
        "--visualize", action="store_true", help="Show visualization of results"
    )
    parser.add_argument(
        "--compare-methods",
        action="store_true",
        help="Compare all correction methods",
    )
    parser.add_argument(
        "--show-projection-curves",
        action="store_true",
        help="Show projection model curves",
    )
    parser.add_argument(
        "--show-grid", action="store_true", help="Show distortion grid overlay"
    )

    parser.add_argument(
        "--yaw", type=float, default=0.0, help="Yaw rotation angle in degrees"
    )
    parser.add_argument(
        "--pitch", type=float, default=0.0, help="Pitch rotation angle in degrees"
    )
    parser.add_argument(
        "--roll", type=float, default=0.0, help="Roll rotation angle in degrees"
    )

    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Number of worker threads for batch processing (default: 4)",
    )
    parser.add_argument(
        "--frame-interval",
        type=int,
        default=1,
        help="Process every Nth frame for video (default: 1)",
    )

    parser.add_argument(
        "--interpolation",
        type=str,
        default="linear",
        choices=["nearest", "linear", "cubic", "lanczos4"],
        help="Interpolation method (default: linear)",
    )

    parser.add_argument(
        "--self-calibrate",
        action="store_true",
        help="Use line-based self-calibration for parameter estimation",
    )
    parser.add_argument(
        "--border-mode",
        type=str,
        default="full",
        choices=["full", "crop", "pad"],
        help="Border handling mode (default: full)",
    )
    parser.add_argument(
        "--lens-config",
        type=str,
        help="Lens configuration file (JSON format)",
    )
    parser.add_argument(
        "--active-lens",
        type=str,
        help="Name of the lens to use from lens config",
    )
    parser.add_argument(
        "--list-lenses",
        action="store_true",
        help="List all available lenses in the config",
    )
    parser.add_argument(
        "--calibrate-lens",
        type=str,
        metavar="LENS_NAME",
        help="Calibrate a new lens from input image(s) and save to config",
    )
    parser.add_argument(
        "--group-by-lens",
        action="store_true",
        help="Group and process images by detected lens from filenames",
    )
    parser.add_argument(
        "--save-config",
        type=str,
        help="Save lens configuration to file",
    )

    return parser.parse_args()


def get_interpolation_flag(method: str) -> int:
    flags = {
        "nearest": cv2.INTER_NEAREST,
        "linear": cv2.INTER_LINEAR,
        "cubic": cv2.INTER_CUBIC,
        "lanczos4": cv2.INTER_LANCZOS4,
    }
    return flags.get(method, cv2.INTER_LINEAR)


def get_correction_method(method: str) -> CorrectionMethod:
    methods = {
        "spherical": CorrectionMethod.SPHERICAL_PROJECTION,
        "equirectangular": CorrectionMethod.EQURECTANGULAR_PROJECTION,
        "perspective": CorrectionMethod.PERSPECTIVE_PROJECTION,
    }
    return methods.get(method, CorrectionMethod.SPHERICAL_PROJECTION)


def get_projection_type(projection: str) -> FisheyeProjectionType:
    projections = {
        "equidistant": FisheyeProjectionType.EQUIDISTANT,
        "equisolid": FisheyeProjectionType.EQUISOLID,
        "orthographic": FisheyeProjectionType.ORTHOGRAPHIC,
        "stereographic": FisheyeProjectionType.STEREOGRAPHIC,
    }
    return projections.get(projection)


def get_border_mode(mode: str) -> BorderHandlingMode:
    modes = {
        "full": BorderHandlingMode.FULL,
        "crop": BorderHandlingMode.CROP,
        "pad": BorderHandlingMode.PAD,
    }
    return modes.get(mode, BorderHandlingMode.FULL)


def get_distortion_model(args, image=None, lens_config_manager=None):
    if lens_config_manager is not None and args.active_lens:
        lens = lens_config_manager.get_lens(args.active_lens)
        if lens is not None:
            print(f"Using lens configuration: {args.active_lens}")
            return lens.get_model()

    if args.self_calibrate and image is not None:
        print("Using line-based self-calibration...")
        params = self_calibrate_from_lines(image, verbose=True)
        print(f"Self-calibration method: {params.get('method', 'unknown')}")
        if 'mean_residual' in params:
            print(f"Mean residual: {params['mean_residual']:.4f}")
        return params["model"]

    if args.projection == "auto" and image is not None:
        params = estimate_fisheye_params_auto(image, initial_fov=args.fov)
        return params["model"]

    if args.focal is not None and args.center is not None:
        projection_type = get_projection_type(args.projection)
        if projection_type is None:
            projection_type = FisheyeProjectionType.EQUISOLID
        return create_projection_model(projection_type, args.focal, tuple(args.center))

    if image is not None:
        params = estimate_fisheye_params_auto(image, initial_fov=args.fov)
        if args.projection != "auto":
            projection_type = get_projection_type(args.projection)
            return create_projection_model(
                projection_type, params["focal_length"], params["center"]
            )
        return params["model"]

    return None


def calibrate_from_chessboard(args):
    calibrator = FisheyeCalibrator(
        chessboard_size=tuple(args.chessboard), square_size=args.square_size
    )

    import glob

    image_files = []
    for ext in ["*.jpg", "*.jpeg", "*.png", "*.bmp"]:
        pattern = os.path.join(args.calibration_dir, ext)
        image_files.extend(glob.glob(pattern))

    if len(image_files) == 0:
        print(f"No calibration images found in {args.calibration_dir}")
        return None

    print(f"Found {len(image_files)} calibration images")
    success = calibrator.calibrate_from_images(image_files)

    if success:
        print(f"Calibration successful!")
        print(f"  Focal length: {calibrator.focal_length:.2f}")
        print(f"  Center: ({calibrator.center[0]:.2f}, {calibrator.center[1]:.2f})")
        print(f"  Reprojection error: {calibrator.reprojection_error:.4f}")
        return calibrator.get_projection_model()
    else:
        print("Calibration failed")
        return None


def main():
    args = parse_args()

    if args.show_projection_curves:
        visualizer = FisheyeVisualizer()
        fov = args.fov if args.fov else 180.0
        visualizer.show_projection_curves(fov_degrees=fov)
        visualizer.close()
        return

    lens_config_manager = None
    if args.lens_config:
        if os.path.exists(args.lens_config):
            lens_config_manager = LensConfigManager(args.lens_config)
            print(f"Loaded lens configuration from: {args.lens_config}")
        else:
            lens_config_manager = LensConfigManager()
            print(f"Created new lens configuration manager")

    if args.list_lenses:
        if lens_config_manager is None:
            lens_config_manager = LensConfigManager()
        lens_config_manager.print_summary()
        return

    if args.calibrate_lens:
        if lens_config_manager is None:
            lens_config_manager = LensConfigManager()

        if args.input_dir:
            import glob
            image_files = []
            for ext in ["*.jpg", "*.jpeg", "*.png", "*.bmp"]:
                image_files.extend(glob.glob(os.path.join(args.input_dir, ext)))
            if len(image_files) == 0:
                print("No images found for calibration")
                return
            print(f"Calibrating lens '{args.calibrate_lens}' from {len(image_files)} images...")
            lens_config_manager.calibrate_lens_from_images(
                args.calibrate_lens,
                image_files,
                use_line_calibration=args.self_calibrate,
            )
        elif args.input:
            image = cv2.imread(args.input)
            if image is None:
                print(f"Error: Could not read input image: {args.input}")
                return
            print(f"Calibrating lens '{args.calibrate_lens}' from single image...")
            lens_config_manager.calibrate_lens_from_image(
                args.calibrate_lens,
                image,
                use_line_calibration=args.self_calibrate,
            )
        else:
            print("Error: Need --input or --input-dir for lens calibration")
            return

        lens = lens_config_manager.get_lens(args.calibrate_lens)
        if lens:
            print(f"Lens calibrated successfully!")
            print(f"  Focal length: {lens.focal_length:.1f}")
            print(f"  Center: ({lens.center[0]:.1f}, {lens.center[1]:.1f})")
            print(f"  FOV: {lens.fov_degrees:.1f}°")
            print(f"  Projection: {lens.projection_type.value}")

        if args.save_config:
            lens_config_manager.save(args.save_config)
            print(f"Lens configuration saved to: {args.save_config}")
        elif lens_config_manager.config_file:
            lens_config_manager.save()
            print(f"Lens configuration saved to: {lens_config_manager.config_file}")
        return

    if args.save_config and lens_config_manager:
        lens_config_manager.save(args.save_config)
        print(f"Lens configuration saved to: {args.save_config}")
        return

    distortion_model = None

    if args.calibration_dir:
        distortion_model = calibrate_from_chessboard(args)
        if distortion_model is None:
            print("Falling back to auto parameter estimation")

    method = get_correction_method(args.method)
    interpolation = get_interpolation_flag(args.interpolation)
    border_mode = get_border_mode(args.border_mode)
    output_size = tuple(args.output_size) if args.output_size else None

    if args.video and args.output_video:
        print(f"Processing video: {args.video}")
        processor = BatchProcessor(
            distortion_model=distortion_model,
            method=method,
            output_size=output_size,
            num_workers=args.workers,
            border_mode=border_mode,
            lens_config_manager=lens_config_manager,
        )
        result = processor.process_video(
            args.video,
            args.output_video,
            frame_interval=args.frame_interval,
            auto_params=(distortion_model is None),
        )
        if result["success"]:
            print(f"Video processed successfully!")
            print(f"  Output: {result['output']}")
            print(f"  Frames: {result['processed_frames']}/{result['total_frames']}")
        return

    if args.input_dir and args.output_dir:
        print(f"Batch processing: {args.input_dir} -> {args.output_dir}")
        print(f"Border mode: {args.border_mode}")

        processor = BatchProcessor(
            distortion_model=distortion_model,
            method=method,
            output_size=output_size,
            num_workers=args.workers,
            border_mode=border_mode,
            lens_config_manager=lens_config_manager,
        )

        if args.group_by_lens:
            print("Processing images grouped by lens...")
            results = processor.process_groups_by_lens(
                args.input_dir,
                args.output_dir,
            )
        elif lens_config_manager is not None:
            print("Using lens configuration for batch processing...")
            results = processor.process_directory_with_lens_config(
                args.input_dir,
                args.output_dir,
                lens_config_manager=lens_config_manager,
            )
        else:
            results = processor.process_directory(
                args.input_dir,
                args.output_dir,
                auto_params=(distortion_model is None),
            )
        summary = processor.get_summary()
        print(f"\nBatch processing complete!")
        print(f"  Total: {summary['total']}")
        print(f"  Success: {summary['success']}")
        print(f"  Failed: {summary['failed']}")
        print(f"  Success rate: {summary['success_rate']*100:.1f}%")
        return

    if args.input:
        image = cv2.imread(args.input)
        if image is None:
            print(f"Error: Could not read input image: {args.input}")
            return

        if distortion_model is None:
            distortion_model = get_distortion_model(args, image, lens_config_manager)

        if args.yaw != 0 or args.pitch != 0 or args.roll != 0:
            corrector = FisheyeCorrector(
                distortion_model=distortion_model,
                method=method,
                interpolation=interpolation,
                border_mode=border_mode,
            )
            corrected = corrector.correct_with_custom_rotation(
                image,
                yaw=args.yaw,
                pitch=args.pitch,
                roll=args.roll,
                output_size=output_size,
                handling_mode=border_mode,
            )
        else:
            corrected = correct_fisheye_image(
                image,
                method=method,
                focal_length=args.focal,
                center=tuple(args.center) if args.center else None,
                projection_type=get_projection_type(args.projection)
                if args.projection != "auto"
                else FisheyeProjectionType.EQUISOLID,
                output_size=output_size,
                auto_params=(distortion_model is None),
                handling_mode=border_mode,
            )

        if args.output:
            os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
            cv2.imwrite(args.output, corrected)
            print(f"Corrected image saved to: {args.output}")
            print(f"Output size: {corrected.shape[1]}x{corrected.shape[0]}")

        visualizer = FisheyeVisualizer()

        if args.compare_methods:
            visualizer.show_all_methods(image, distortion_model=distortion_model)
        elif args.show_grid:
            visualizer.show_distortion_grid(
                image, distortion_model=distortion_model
            )
        elif args.visualize:
            params = estimate_fisheye_params_auto(image)
            visualizer.show_calibration_result(image, params)

        visualizer.close()

        return

    print("No action specified. Use --help for usage information.")


if __name__ == "__main__":
    main()
