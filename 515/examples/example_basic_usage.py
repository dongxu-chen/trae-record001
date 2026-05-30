#!/usr/bin/env python3
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import cv2
from src import (
    correct_fisheye_image,
    FisheyeCorrector,
    CorrectionMethod,
    FisheyeProjectionType,
    create_projection_model,
    estimate_fisheye_params_auto,
    FisheyeVisualizer,
)


def generate_synthetic_fisheye_image(
    size: int = 800, fov_degrees: float = 180.0
) -> np.ndarray:
    image = np.zeros((size, size, 3), dtype=np.uint8)

    center = (size // 2, size // 2)
    max_r = size // 2 - 10

    for i in range(0, size, 50):
        for j in range(0, size, 50):
            dx = j - center[0]
            dy = i - center[1]
            r = np.sqrt(dx**2 + dy**2)

            if r < max_r:
                theta = np.arcsin(r / max_r) * (fov_degrees / 180.0) * np.pi / 2
                r_fisheye = 2.0 * (size / 3.0) * np.sin(theta / 2.0)

                x_f = int(center[0] + r_fisheye * dx / r) if r > 0 else center[0]
                y_f = int(center[1] + r_fisheye * dy / r) if r > 0 else center[1]

                color = (
                    int(255 * (j / size)),
                    int(255 * (i / size)),
                    int(255 * (1 - i / size)),
                )
                cv2.rectangle(image, (x_f - 10, y_f - 10), (x_f + 10, y_f + 10), color, -1)

    cv2.circle(image, center, max_r, (255, 255, 255), 2)

    return image


def example_1_auto_correction():
    print("Example 1: Auto correction with parameter estimation")
    print("=" * 60)

    fisheye_img = generate_synthetic_fisheye_image()

    params = estimate_fisheye_params_auto(fisheye_img)
    print(f"Estimated parameters:")
    print(f"  FOV: {params['fov_degrees']:.1f}°")
    print(f"  Center: ({params['center'][0]:.1f}, {params['center'][1]:.1f})")
    print(f"  Focal length: {params['focal_length']:.1f}")
    print(f"  Projection type: {params['projection_type'].value}")

    corrected = correct_fisheye_image(fisheye_img)

    visualizer = FisheyeVisualizer(figsize=(12, 6))
    visualizer.show_image_pair(
        fisheye_img,
        corrected,
        "Synthetic Fisheye Image",
        "Auto-Corrected Image",
        save_path="output/example_1_result.png",
    )
    visualizer.close()

    os.makedirs("output", exist_ok=True)
    cv2.imwrite("output/example_1_fisheye.png", fisheye_img)
    cv2.imwrite("output/example_1_corrected.png", corrected)

    print("  -> Saved to output/example_1_*.png")
    print()


def example_2_different_projection_models():
    print("Example 2: Comparing different projection models")
    print("=" * 60)

    fisheye_img = generate_synthetic_fisheye_image()

    center = (fisheye_img.shape[1] // 2, fisheye_img.shape[0] // 2)
    focal_length = fisheye_img.shape[0] / 3.0

    visualizer = FisheyeVisualizer(figsize=(14, 10))
    visualizer.show_projection_models(
        fisheye_img,
        center=center,
        focal_length=focal_length,
        save_path="output/example_2_projections.png",
    )
    visualizer.close()

    print("  -> Saved to output/example_2_projections.png")
    print()


def example_3_different_correction_methods():
    print("Example 3: Comparing different correction methods")
    print("=" * 60)

    fisheye_img = generate_synthetic_fisheye_image()

    visualizer = FisheyeVisualizer(figsize=(18, 6))
    visualizer.show_all_methods(
        fisheye_img,
        save_path="output/example_3_methods.png",
    )
    visualizer.close()

    print("  -> Saved to output/example_3_methods.png")
    print()


def example_4_custom_rotation():
    print("Example 4: Custom rotation (changing viewpoint)")
    print("=" * 60)

    fisheye_img = generate_synthetic_fisheye_image()

    params = estimate_fisheye_params_auto(fisheye_img)
    corrector = FisheyeCorrector(distortion_model=params["model"])

    visualizer = FisheyeVisualizer(figsize=(18, 6))
    visualizer.show_rotation_effect(
        fisheye_img,
        distortion_model=params["model"],
        yaw_angles=[-30, 0, 30],
        pitch=0,
        save_path="output/example_4_rotation.png",
    )
    visualizer.close()

    print("  -> Saved to output/example_4_rotation.png")
    print()


def example_5_distortion_grid():
    print("Example 5: Distortion grid visualization")
    print("=" * 60)

    fisheye_img = generate_synthetic_fisheye_image()

    visualizer = FisheyeVisualizer(figsize=(14, 7))
    visualizer.show_distortion_grid(
        fisheye_img,
        grid_spacing=40,
        save_path="output/example_5_grid.png",
    )
    visualizer.close()

    print("  -> Saved to output/example_5_grid.png")
    print()


def example_6_projection_curves():
    print("Example 6: Projection model curves")
    print("=" * 60)

    visualizer = FisheyeVisualizer(figsize=(14, 6))
    visualizer.show_projection_curves(
        fov_degrees=180.0,
        save_path="output/example_6_curves.png",
    )
    visualizer.close()

    print("  -> Saved to output/example_6_curves.png")
    print()


def example_7_manual_parameters():
    print("Example 7: Using manual parameters")
    print("=" * 60)

    fisheye_img = generate_synthetic_fisheye_image(size=600, fov_degrees=150)

    h, w = fisheye_img.shape[:2]
    center = (w / 2, h / 2)
    focal_length = 200.0

    model = create_projection_model(
        FisheyeProjectionType.EQUISOLID, focal_length, center
    )

    corrector = FisheyeCorrector(
        distortion_model=model,
        method=CorrectionMethod.SPHERICAL_PROJECTION,
        output_size=(int(h * 1.2), int(w * 1.2)),
    )

    corrected = corrector.correct(fisheye_img)

    visualizer = FisheyeVisualizer(figsize=(12, 6))
    visualizer.show_image_pair(
        fisheye_img,
        corrected,
        f"Fisheye (FOV=150°)",
        "Corrected (Manual Params)",
        save_path="output/example_7_manual.png",
    )
    visualizer.close()

    cv2.imwrite("output/example_7_corrected.png", corrected)
    print("  -> Saved to output/example_7_*.png")
    print()


def example_8_intensity_analysis():
    print("Example 8: Intensity profile analysis")
    print("=" * 60)

    fisheye_img = generate_synthetic_fisheye_image()
    corrected = correct_fisheye_image(fisheye_img)

    visualizer = FisheyeVisualizer(figsize=(14, 10))
    visualizer.show_intensity_profile(
        fisheye_img,
        corrected,
        save_path="output/example_8_intensity.png",
    )
    visualizer.close()

    print("  -> Saved to output/example_8_intensity.png")
    print()


def main():
    os.makedirs("output", exist_ok=True)

    examples = [
        example_1_auto_correction,
        example_2_different_projection_models,
        example_3_different_correction_methods,
        example_4_custom_rotation,
        example_5_distortion_grid,
        example_6_projection_curves,
        example_7_manual_parameters,
        example_8_intensity_analysis,
    ]

    print("Fisheye Correction Examples")
    print("=" * 60)
    print()

    for i, example in enumerate(examples, 1):
        try:
            example()
        except Exception as e:
            print(f"Error in example {i}: {e}")
            import traceback

            traceback.print_exc()

    print("All examples completed!")
    print("Check the 'output' directory for results.")


if __name__ == "__main__":
    main()
