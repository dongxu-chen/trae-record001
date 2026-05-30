#!/usr/bin/env python3
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import cv2
from src import (
    BatchProcessor,
    FisheyeProjectionType,
    create_projection_model,
    CorrectionMethod,
)


def generate_test_images(output_dir: str, num_images: int = 5):
    os.makedirs(output_dir, exist_ok=True)

    for i in range(num_images):
        size = 600
        image = np.zeros((size, size, 3), dtype=np.uint8)

        center = (size // 2, size // 2)
        max_r = size // 2 - 10

        hue_shift = (i * 360 / num_images) % 180

        for j in range(0, size, 40):
            for k in range(0, size, 40):
                dx = k - center[0]
                dy = j - center[1]
                r = np.sqrt(dx**2 + dy**2)

                if r < max_r:
                    theta = np.arcsin(r / max_r) * np.pi / 2
                    r_fisheye = 2.0 * (size / 3.0) * np.sin(theta / 2.0)

                    x_f = int(center[0] + r_fisheye * dx / r) if r > 0 else center[0]
                    y_f = int(center[1] + r_fisheye * dy / r) if r > 0 else center[1]

                    hsv = np.uint8([[[hue_shift, 255, int(255 * (1 - r / max_r))]]])
                    bgr = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)[0][0]
                    color = tuple(int(c) for c in bgr)

                    cv2.circle(image, (x_f, y_f), 15, color, -1)

        cv2.circle(image, center, max_r, (255, 255, 255), 2)
        cv2.putText(
            image,
            f"Image {i+1}",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (255, 255, 255),
            2,
        )

        cv2.imwrite(os.path.join(output_dir, f"fisheye_{i+1:03d}.jpg"), image)
        print(f"  Generated: fisheye_{i+1:03d}.jpg")


def example_batch_auto():
    print("\nExample: Batch processing with auto parameter estimation")
    print("=" * 60)

    input_dir = "test_images_auto"
    output_dir = "corrected_auto"

    print("Generating test images...")
    generate_test_images(input_dir, num_images=5)

    print("\nProcessing with auto parameter estimation...")
    processor = BatchProcessor(
        method=CorrectionMethod.SPHERICAL_PROJECTION,
        num_workers=2,
    )

    def progress_callback(completed, total, result):
        status = "✓" if result["success"] else "✗"
        print(f"  [{completed}/{total}] {status} {os.path.basename(result['input'])}")

    results = processor.process_directory(
        input_dir,
        output_dir,
        auto_params=True,
        callback=progress_callback,
    )

    summary = processor.get_summary()
    print(f"\nSummary:")
    print(f"  Total: {summary['total']}")
    print(f"  Success: {summary['success']}")
    print(f"  Failed: {summary['failed']}")
    print(f"  Success rate: {summary['success_rate']*100:.1f}%")

    return summary


def example_batch_with_params():
    print("\nExample: Batch processing with predefined parameters")
    print("=" * 60)

    input_dir = "test_images_manual"
    output_dir = "corrected_manual"

    print("Generating test images...")
    generate_test_images(input_dir, num_images=3)

    center = (300.0, 300.0)
    focal_length = 200.0
    model = create_projection_model(
        FisheyeProjectionType.EQUISOLID, focal_length, center
    )

    print(f"\nUsing predefined parameters:")
    print(f"  Center: {center}")
    print(f"  Focal length: {focal_length}")
    print(f"  Projection: {FisheyeProjectionType.EQUISOLID.value}")

    processor = BatchProcessor(
        distortion_model=model,
        method=CorrectionMethod.SPHERICAL_PROJECTION,
        output_size=(720, 720),
        num_workers=2,
    )

    results = processor.process_directory(
        input_dir,
        output_dir,
        auto_params=False,
    )

    summary = processor.get_summary()
    print(f"\nResults saved to: {output_dir}")
    print(f"Success rate: {summary['success_rate']*100:.1f}%")

    return summary


def example_save_load_params():
    print("\nExample: Saving and loading calibration parameters")
    print("=" * 60)

    input_dir = "test_images_params"
    output_dir = "corrected_params"
    param_file = "calibration_params.json"

    generate_test_images(input_dir, num_images=4)

    from src.calibration import estimate_params_from_multiple_images
    import glob

    image_files = glob.glob(os.path.join(input_dir, "*.jpg"))
    print(f"\nEstimating parameters from {len(image_files)} images...")
    params = estimate_params_from_multiple_images(image_files)

    print(f"Estimated parameters:")
    print(f"  FOV: {params['fov_degrees']:.1f}°")
    print(f"  Center: ({params['center'][0]:.1f}, {params['center'][1]:.1f})")
    print(f"  Focal length: {params['focal_length']:.1f}")
    print(f"  Projection: {params['projection_type'].value}")

    processor = BatchProcessor(num_workers=2)
    processor.save_params(param_file, params)
    print(f"\nParameters saved to: {param_file}")

    print("\nProcessing with loaded parameters...")
    processor.process_with_custom_params(
        input_dir,
        output_dir,
        param_file=param_file,
    )

    summary = processor.get_summary()
    print(f"Processing complete. Success rate: {summary['success_rate']*100:.1f}%")

    return summary


def main():
    print("Batch Processing Examples")
    print("=" * 60)

    try:
        example_batch_auto()
    except Exception as e:
        print(f"Error in batch auto example: {e}")
        import traceback

        traceback.print_exc()

    try:
        example_batch_with_params()
    except Exception as e:
        print(f"Error in batch with params example: {e}")
        import traceback

        traceback.print_exc()

    try:
        example_save_load_params()
    except Exception as e:
        print(f"Error in save/load params example: {e}")
        import traceback

        traceback.print_exc()

    print("\nAll batch processing examples completed!")


if __name__ == "__main__":
    main()
