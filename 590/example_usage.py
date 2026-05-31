import cv2
import os
from underwater_enhancer import UnderwaterImageEnhancer
from video_enhancer import VideoProcessor, RealTimeEnhancer
from quality_evaluator import NoReferenceEvaluator


def example_single_image_enhancement(image_path):
    print(f"Processing image: {image_path}")
    
    img = cv2.imread(image_path)
    if img is None:
        print("Image not found!")
        return
    
    enhancer = UnderwaterImageEnhancer(use_adaptive=True)
    
    enhanced, info = enhancer.enhance(img)
    
    metrics = NoReferenceEvaluator.compare(img, enhanced)
    
    print("\nQuality Improvement:")
    print(f"  Overall Quality: {metrics['original']['overall_quality']:.3f -> {metrics['enhanced']['overall_quality']:.3f")
    print(f"  Contrast: {metrics['improvement']['contrast']:+.3f}")
    print(f"  Sharpness: {metrics['improvement']['sharpness']:+.3f")
    
    output_path = "enhanced_" + os.path.basename(image_path)
    cv2.imwrite(output_path, enhanced)
    print(f"\nSaved enhanced image to: {output_path}")
    
    return enhanced, info


def example_batch_processing(image_paths):
    print("Batch processing...")
    
    enhancer = UnderwaterImageEnhancer(use_adaptive=True)
    
    for idx, path in enumerate(image_paths):
        img = cv2.imread(path)
        if img is None:
            continue
        
        enhanced, _ = enhancer.enhance(img)
        output_path = f"enhanced_{idx}.jpg"
        cv2.imwrite(output_path, enhanced)
        print(f"  Processed {path} -> {output_path}")


def example_video_processing(input_video_path, output_video_path):
    print(f"Processing video: {input_video_path}")
    
    processor = VideoProcessor(use_adaptive=True)
    
    result = processor.process_video_file(
        input_video_path,
        output_video_path,
        display_fps=True
    )
    
    print(f"\nVideo processing complete!")
    print(f"  Total frames: {result['total_frames']")
    print(f"  Processing FPS: {result['processing_fps']:.1f}")
    print(f"  Output: {output_video_path}")


def example_realtime_camera():
    print("Starting real-time camera...")
    print("Press 'q' to quit, 's' to save snapshot")
    
    rt = RealTimeEnhancer(use_adaptive=True, downscale_factor=0.7)
    rt.run_camera(camera_id=0)


def example_custom_parameters():
    print("Using custom parameters...")
    
    enhancer = UnderwaterImageEnhancer(
        use_adaptive=False,
        red_boost=1.5,
        blue_scale=0.85,
        omega=0.95,
        gamma=0.9,
        clahe_clip=2.5,
        sharpen_strength=0.7,
        patch_size=15
    )
    
    print("Custom enhancer created with custom parameters")
    return enhancer


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "image" and len(sys.argv) > 2:
            example_single_image_enhancement(sys.argv[2])
        elif command == "video" and len(sys.argv) > 3:
            example_video_processing(sys.argv[2], sys.argv[3])
        elif command == "camera":
            example_realtime_camera()
        elif command == "custom":
            example_custom_parameters()
        else:
            print("Usage:")
            print("  python example_usage.py image <image_path>")
            print("  python example_usage.py video <input_video> <output_video>")
            print("  python example_usage.py camera")
            print("  python example_usage.py custom")
    else:
        print("Run tests first...")
        from test_enhancer import run_all_tests
        run_all_tests()
