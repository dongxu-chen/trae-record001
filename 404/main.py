import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    YOLO_MODEL_PATH, TRT_ENGINE_PATH,
    CONF_THRESHOLD, INPUT_WIDTH, INPUT_HEIGHT,
    FP16_QUANTIZATION, INT8_QUANTIZATION,
    API_HOST, API_PORT
)


def cmd_detect(args):
    import cv2
    from detector import YOLODetector

    detector = YOLODetector(
        model_path=args.model,
        conf_threshold=args.conf,
        iou_threshold=args.iou,
        input_width=args.width,
        input_height=args.height,
        use_enhanced_fpn=not args.no_fpn,
        small_target_threshold=args.small_threshold,
        high_res_scale=args.high_res_scale
    )

    image = cv2.imread(args.input)
    if image is None:
        print(f"[ERROR] Cannot read image: {args.input}")
        return 1

    detections = detector.detect(image)
    print(f"\n[RESULT] Found {len(detections)} traffic signs:\n")

    for i, det in enumerate(detections, 1):
        print(f"  [{i}] {det.class_name_zh} ({det.class_name})")
        print(f"      Confidence: {det.confidence:.4f}")
        print(f"      Category: {det.category}")
        print(f"      BBox: {det.bbox}")
        print()

    if args.output:
        annotated = detector.draw_detections(image, detections)
        cv2.imwrite(args.output, annotated)
        print(f"[INFO] Annotated image saved: {args.output}")

    if args.display:
        annotated = detector.draw_detections(image, detections)
        cv2.imshow("Traffic Sign Detection", annotated)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    return 0


def cmd_video(args):
    from detector import YOLODetector
    from processor import VideoProcessor

    detector = YOLODetector(
        model_path=args.model,
        conf_threshold=args.conf,
        input_width=args.width,
        input_height=args.height,
        use_enhanced_fpn=not args.no_fpn,
        small_target_threshold=args.small_threshold,
        high_res_scale=args.high_res_scale
    )

    processor = VideoProcessor(
        detector=detector,
        source=args.source,
        width=args.width,
        height=args.height,
        fps=args.fps,
        conf_threshold=args.conf,
        display=True,
        enable_adaptive_resolution=not args.no_adaptive,
        process_every_frame=not args.skip_frames,
        enable_temporal_fusion=not args.no_temporal,
        enable_distance_estimation=not args.no_distance,
        enable_country_adaptation=not args.no_country,
        country_code=args.country,
        temporal_window_size=args.temporal_window,
        focal_length=args.focal_length,
        camera_height=args.camera_height
    )

    print("[INFO] Press 'q' to quit, 's' to show statistics")

    if args.input:
        processor.process_video_file(
            video_path=args.input,
            output_path=args.output
        )
    else:
        if not processor.start():
            print("[ERROR] Failed to start video processor")
            return 1

        try:
            while True:
                import time
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n[INFO] Stopping...")
        finally:
            processor.stop()

    return 0


def cmd_quantize(args):
    from detector import ModelQuantizer

    quantizer = ModelQuantizer(
        yolo_model_path=args.model,
        trt_engine_path=args.engine,
        input_width=args.width,
        input_height=args.height,
        fp16=not args.no_fp16,
        int8=args.int8,
        calibration_images=args.calibration_images,
        use_hard_example_mining=not args.no_hard_mining,
        hard_example_dir=args.hard_example_dir
    )

    print("[INFO] Model Quantization Info:")
    for k, v in quantizer.get_quantization_info().items():
        print(f"  {k}: {v}")

    if args.onnx_only:
        onnx_path = quantizer.export_to_onnx()
        if onnx_path:
            print(f"[SUCCESS] ONNX model exported: {onnx_path}")
            return 0
        return 1

    success = quantizer.quantize_model()
    if success:
        print("[SUCCESS] Model quantization complete!")
        return 0
    return 1


def cmd_api(args):
    import uvicorn
    from api.app import app

    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        reload=args.reload
    )


def main():
    parser = argparse.ArgumentParser(
        description="Traffic Sign Recognition System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py detect -i road.jpg -o result.jpg
  python main.py video --source 0
  python main.py video -i video.mp4 -o output.mp4
  python main.py quantize --model yolov8n.pt --fp16
  python main.py api --host 0.0.0.0 --port 8000
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    detect_parser = subparsers.add_parser("detect", help="Detect traffic signs in an image")
    detect_parser.add_argument("-i", "--input", required=True, help="Input image path")
    detect_parser.add_argument("-o", "--output", help="Output annotated image path")
    detect_parser.add_argument("-m", "--model", default=YOLO_MODEL_PATH, help="Model path")
    detect_parser.add_argument("--conf", type=float, default=CONF_THRESHOLD, help="Confidence threshold")
    detect_parser.add_argument("--iou", type=float, default=0.45, help="IoU threshold")
    detect_parser.add_argument("--width", type=int, default=INPUT_WIDTH, help="Input width")
    detect_parser.add_argument("--height", type=int, default=INPUT_HEIGHT, help="Input height")
    detect_parser.add_argument("--display", action="store_true", help="Display result")
    detect_parser.add_argument("--no-fpn", action="store_true", help="Disable enhanced FPN for small targets")
    detect_parser.add_argument("--small-threshold", type=int, default=32, help="Small target size threshold")
    detect_parser.add_argument("--high-res-scale", type=float, default=2.0, help="High resolution scale factor")

    video_parser = subparsers.add_parser("video", help="Process video stream")
    video_parser.add_argument("-i", "--input", help="Input video file path")
    video_parser.add_argument("-o", "--output", help="Output video path")
    video_parser.add_argument("-s", "--source", type=int, default=0, help="Camera index")
    video_parser.add_argument("-m", "--model", default=YOLO_MODEL_PATH, help="Model path")
    video_parser.add_argument("--conf", type=float, default=CONF_THRESHOLD, help="Confidence threshold")
    video_parser.add_argument("--width", type=int, default=INPUT_WIDTH, help="Frame width")
    video_parser.add_argument("--height", type=int, default=INPUT_HEIGHT, help="Frame height")
    video_parser.add_argument("--fps", type=int, default=30, help="Target FPS")
    video_parser.add_argument("--no-fpn", action="store_true", help="Disable enhanced FPN")
    video_parser.add_argument("--small-threshold", type=int, default=32, help="Small target size threshold")
    video_parser.add_argument("--high-res-scale", type=float, default=2.0, help="High resolution scale factor")
    video_parser.add_argument("--no-adaptive", action="store_true", help="Disable adaptive resolution")
    video_parser.add_argument("--skip-frames", action="store_true", help="Enable frame skipping (not recommended)")
    video_parser.add_argument("--no-temporal", action="store_true", help="Disable temporal fusion")
    video_parser.add_argument("--no-distance", action="store_true", help="Disable distance estimation")
    video_parser.add_argument("--no-country", action="store_true", help="Disable country adaptation")
    video_parser.add_argument("--country", default="CN", help="Country code (CN, US, EU, JP, GB, DE, AU, IN, BR, RU)")
    video_parser.add_argument("--temporal-window", type=int, default=5, help="Temporal fusion window size")
    video_parser.add_argument("--focal-length", type=float, default=800.0, help="Camera focal length")
    video_parser.add_argument("--camera-height", type=float, default=1.5, help="Camera height in meters")

    quantize_parser = subparsers.add_parser("quantize", help="Quantize model for TensorRT")
    quantize_parser.add_argument("-m", "--model", default=YOLO_MODEL_PATH, help="YOLO model path")
    quantize_parser.add_argument("-e", "--engine", default=TRT_ENGINE_PATH, help="TensorRT engine path")
    quantize_parser.add_argument("--width", type=int, default=INPUT_WIDTH, help="Input width")
    quantize_parser.add_argument("--height", type=int, default=INPUT_HEIGHT, help="Input height")
    quantize_parser.add_argument("--no-fp16", action="store_true", help="Disable FP16 quantization")
    quantize_parser.add_argument("--int8", action="store_true", help="Enable INT8 quantization")
    quantize_parser.add_argument("--calibration-images", nargs="*", help="Calibration images for INT8")
    quantize_parser.add_argument("--onnx-only", action="store_true", help="Export to ONNX only")
    quantize_parser.add_argument("--no-hard-mining", action="store_true", help="Disable hard example mining")
    quantize_parser.add_argument("--hard-example-dir", default="hard_examples", help="Directory for hard examples")

    api_parser = subparsers.add_parser("api", help="Start API server")
    api_parser.add_argument("--host", default=API_HOST, help="API host")
    api_parser.add_argument("--port", type=int, default=API_PORT, help="API port")
    api_parser.add_argument("--reload", action="store_true", help="Enable auto-reload")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 0

    if args.command == "detect":
        return cmd_detect(args)
    elif args.command == "video":
        return cmd_video(args)
    elif args.command == "quantize":
        return cmd_quantize(args)
    elif args.command == "api":
        cmd_api(args)
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
