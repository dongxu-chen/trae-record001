import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.config import Config
from depth_estimation import (
    MidasModel,
    DepthPostProcessor,
    VideoDepthEstimator,
    PointCloudGenerator,
)
import cv2
import numpy as np


def parse_args():
    parser = argparse.ArgumentParser(description="MiDaS Depth Estimation System")
    parser.add_argument(
        "--mode",
        type=str,
        default="image",
        choices=["image", "video", "webcam", "pointcloud", "export_onnx"],
        help="Operation mode",
    )
    parser.add_argument("--input", type=str, default=None, help="Input image or video path")
    parser.add_argument("--output", type=str, default=None, help="Output path")
    parser.add_argument(
        "--model-type",
        type=str,
        default="DPT_Large",
        choices=["DPT_Large", "DPT_Hybrid", "MiDaS_small", "MiDaS_v21"],
        help="MiDaS model type",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cuda",
        choices=["cuda", "cpu", "mps"],
        help="Device for inference",
    )
    parser.add_argument("--use-onnx", action="store_true", help="Use ONNX Runtime for inference")
    parser.add_argument("--onnx-path", type=str, default=None, help="Path to ONNX model")
    parser.add_argument("--no-display", action="store_true", help="Disable display")
    parser.add_argument("--save-pointcloud", action="store_true", help="Save point cloud")
    
    return parser.parse_args()


def run_image_mode(args, config: Config):
    if not args.input or not os.path.exists(args.input):
        raise FileNotFoundError(f"Input image not found: {args.input}")
    
    print(f"Processing image: {args.input}")
    
    model = MidasModel(config.model)
    post_processor = DepthPostProcessor(config.post_processing)
    
    image = cv2.imread(args.input)
    if image is None:
        raise ValueError(f"Failed to load image: {args.input}")
    
    raw_depth = model.predict(image)
    processed_depth = post_processor.process(raw_depth, image)
    
    depth_colored = DepthPostProcessor.apply_colormap(processed_depth)
    
    if not args.no_display:
        combined = np.hstack((image, depth_colored))
        cv2.imshow("Depth Estimation", combined)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    
    if args.output:
        depth_output_path = args.output
        if os.path.splitext(depth_output_path)[1] == '':
            depth_output_path += "_depth.png"
        cv2.imwrite(depth_output_path, depth_colored)
        print(f"Depth map saved to: {depth_output_path}")
        
        raw_depth_path = os.path.splitext(depth_output_path)[0] + "_raw.npy"
        np.save(raw_depth_path, processed_depth)
        print(f"Raw depth data saved to: {raw_depth_path}")
    
    if args.save_pointcloud:
        pc_config = config.point_cloud
        if args.output:
            pc_config.save_path = os.path.splitext(args.output)[0] + "_pointcloud.ply"
        pc_config.show = not args.no_display
        
        pc_generator = PointCloudGenerator(pc_config)
        pcd = pc_generator.generate(image, processed_depth)
        print(f"Point cloud generated with {len(pcd.points)} points")
    
    print("Image processing complete.")


def run_video_mode(args, config: Config):
    if not args.input or not os.path.exists(args.input):
        raise FileNotFoundError(f"Input video not found: {args.input}")
    
    print(f"Processing video: {args.input}")
    
    model = MidasModel(config.model)
    post_processor = DepthPostProcessor(config.post_processing)
    
    video_config = config.video
    video_config.source = args.input
    if args.output:
        video_config.output_path = args.output
        video_config.save_video = True
    video_config.display_depth = not args.no_display
    
    estimator = VideoDepthEstimator(model, post_processor, video_config)
    estimator.process_video_file(args.input, args.output)


def run_webcam_mode(args, config: Config):
    print("Starting webcam depth estimation...")
    
    model = MidasModel(config.model)
    post_processor = DepthPostProcessor(config.post_processing)
    
    video_config = config.video
    video_config.source = "0"
    if args.output:
        video_config.output_path = args.output
        video_config.save_video = True
    video_config.display_depth = not args.no_display
    
    estimator = VideoDepthEstimator(model, post_processor, video_config)
    estimator.run()


def run_pointcloud_mode(args, config: Config):
    if not args.input or not os.path.exists(args.input):
        raise FileNotFoundError(f"Input image not found: {args.input}")
    
    print(f"Generating point cloud from: {args.input}")
    
    model = MidasModel(config.model)
    post_processor = DepthPostProcessor(config.post_processing)
    
    image = cv2.imread(args.input)
    if image is None:
        raise ValueError(f"Failed to load image: {args.input}")
    
    raw_depth = model.predict(image)
    processed_depth = post_processor.process(raw_depth, image)
    
    pc_config = config.point_cloud
    if args.output:
        pc_config.save_path = args.output
    pc_config.show = not args.no_display
    
    pc_generator = PointCloudGenerator(pc_config)
    pcd = pc_generator.generate(image, processed_depth)
    
    stats = pc_generator.get_point_cloud_stats()
    print(f"Point cloud stats: {stats}")
    
    print("Point cloud generation complete.")


def run_export_onnx_mode(args, config: Config):
    if not args.output:
        raise ValueError("Output path is required for ONNX export")
    
    print(f"Exporting model to ONNX: {args.output}")
    
    model = MidasModel(config.model)
    model.export_to_onnx(args.output)
    
    print("ONNX export complete.")


def main():
    args = parse_args()
    
    config = Config()
    config.model.model_type = args.model_type
    config.model.device = args.device
    config.model.use_onnx = args.use_onnx
    config.model.onnx_path = args.onnx_path
    
    if args.mode == "image":
        run_image_mode(args, config)
    elif args.mode == "video":
        run_video_mode(args, config)
    elif args.mode == "webcam":
        run_webcam_mode(args, config)
    elif args.mode == "pointcloud":
        run_pointcloud_mode(args, config)
    elif args.mode == "export_onnx":
        run_export_onnx_mode(args, config)
    else:
        raise ValueError(f"Unknown mode: {args.mode}")


if __name__ == "__main__":
    main()
