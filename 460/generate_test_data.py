import os
import argparse
import numpy as np
import cv2


def generate_multi_focus_images(output_dir, size=256, num_images=3):
    os.makedirs(output_dir, exist_ok=True)
    h, w = size, size

    background = np.ones((h, w, 3), dtype=np.uint8) * 180

    for y in range(h):
        for x in range(w):
            if (x // 32 + y // 32) % 2 == 0:
                background[y, x] = [160, 160, 160]
            else:
                background[y, x] = [200, 200, 200]

    def draw_text_texture(img, x0, y0, size_t, color, spacing=4):
        for y in range(y0, min(y0 + size_t, h), spacing):
            for x in range(x0, min(x0 + size_t, w), spacing):
                if np.random.random() < 0.3:
                    img[y, x] = color

    def draw_circle(img, cx, cy, r, color):
        for y in range(max(0, cy - r), min(h, cy + r)):
            for x in range(max(0, cx - r), min(w, cx + r)):
                if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                    img[y, x] = color

    np.random.seed(42)

    objects = [
        {"cx": 60, "cy": 60, "r": 30, "color": [200, 60, 60]},
        {"cx": 196, "cy": 60, "r": 25, "color": [60, 200, 60]},
        {"cx": 128, "cy": 128, "r": 40, "color": [60, 60, 200]},
        {"cx": 60, "cy": 196, "r": 25, "color": [200, 200, 60]},
        {"cx": 196, "cy": 196, "r": 30, "color": [200, 60, 200]},
    ]

    focus_points = [
        {"label": "foreground", "blur_bg": 11, "blur_far": 7, "focus_indices": [0, 1, 2]},
        {"label": "midground", "blur_bg": 7, "blur_far": 7, "focus_indices": [2, 3]},
        {"label": "background", "blur_bg": 7, "blur_far": 11, "focus_indices": [3, 4]},
    ]

    images = []
    for fp in focus_points[:num_images]:
        img = background.copy()
        for obj in objects:
            draw_circle(img, obj["cx"], obj["cy"], obj["r"], obj["color"])
            draw_text_texture(img, obj["cx"] - obj["r"], obj["cy"] - obj["r"],
                              obj["r"] * 2, [min(c + 40, 255) for c in obj["color"]])

        mask_focus = np.zeros((h, w), dtype=np.float32)
        for idx in fp["focus_indices"]:
            obj = objects[idx]
            for y in range(max(0, obj["cy"] - obj["r"] - 5), min(h, obj["cy"] + obj["r"] + 5)):
                for x in range(max(0, obj["cx"] - obj["r"] - 5), min(w, obj["cx"] + obj["r"] + 5)):
                    if (x - obj["cx"]) ** 2 + (y - obj["cy"]) ** 2 <= (obj["r"] + 5) ** 2:
                        mask_focus[y, x] = 1.0

        mask_blur = 1.0 - mask_focus
        sharp_region = img.copy().astype(np.float32)
        blurred_region = cv2.GaussianBlur(img, (fp["blur_bg"], fp["blur_bg"]), 0).astype(np.float32)

        result = (sharp_region * mask_focus[:, :, np.newaxis] +
                  blurred_region * mask_blur[:, :, np.newaxis]).astype(np.uint8)
        images.append(result)

        path = os.path.join(output_dir, f"focus_{fp['label']}.png")
        cv2.imwrite(path, result)
        print(f"Saved: {path}")

    gt = background.copy()
    for obj in objects:
        draw_circle(gt, obj["cx"], obj["cy"], obj["r"], obj["color"])
    gt_path = os.path.join(output_dir, "ground_truth.png")
    cv2.imwrite(gt_path, gt)
    print(f"Saved: {gt_path}")
    return images


def generate_dynamic_scene(output_dir, size=256):
    os.makedirs(output_dir, exist_ok=True)
    h, w = size, size

    background = np.ones((h, w, 3), dtype=np.uint8) * 180
    for y in range(h):
        for x in range(w):
            if (x // 32 + y // 32) % 2 == 0:
                background[y, x] = [160, 160, 160]

    def draw_moving_object(img, cx, cy, r, color):
        for y in range(max(0, cy - r), min(h, cy + r)):
            for x in range(max(0, cx - r), min(w, cx + r)):
                if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                    img[y, x] = color

    positions = [
        (80, 80),
        (100, 120),
    ]

    for i, (mx, my) in enumerate(positions):
        img = background.copy()
        draw_moving_object(img, 60, 196, 25, [200, 200, 60])
        draw_moving_object(img, 196, 196, 30, [200, 60, 200])
        draw_moving_object(img, mx, my, 30, [200, 60, 60])

        if i == 0:
            focus_mask = np.zeros((h, w), dtype=np.float32)
            for y in range(max(0, 60 - 30), min(h, 60 + 30)):
                for x in range(max(0, 196 - 30), min(w, 196 + 30)):
                    if (x - 196) ** 2 + (y - 60) ** 2 <= 900:
                        focus_mask[y, x] = 1.0
            blur_mask = 1.0 - focus_mask
            result = (img.astype(np.float32) * focus_mask[:, :, np.newaxis] +
                      cv2.GaussianBlur(img, (11, 11), 0).astype(np.float32) * blur_mask[:, :, np.newaxis]
                      ).astype(np.uint8)
        else:
            focus_mask = np.zeros((h, w), dtype=np.float32)
            for y in range(max(0, 60 - 30), min(h, 60 + 30)):
                for x in range(max(0, 196 - 30), min(w, 196 + 30)):
                    if (x - 196) ** 2 + (y - 60) ** 2 <= 900:
                        focus_mask[y, x] = 1.0
            for y in range(max(0, my - 30), min(h, my + 30)):
                for x in range(max(0, mx - 30), min(w, mx + 30)):
                    if (x - mx) ** 2 + (y - my) ** 2 <= 900:
                        focus_mask[y, x] = 1.0
            blur_mask = 1.0 - focus_mask
            result = (img.astype(np.float32) * focus_mask[:, :, np.newaxis] +
                      cv2.GaussianBlur(img, (11, 11), 0).astype(np.float32) * blur_mask[:, :, np.newaxis]
                      ).astype(np.uint8)

        path = os.path.join(output_dir, f"dynamic_{i + 1}.png")
        cv2.imwrite(path, result)
        print(f"Saved: {path}")


def main():
    parser = argparse.ArgumentParser(description="Generate test data for multi-focus fusion")
    parser.add_argument("--output", type=str, default="test_data", help="Output directory")
    parser.add_argument("--size", type=int, default=256, help="Image size")
    parser.add_argument("--num", type=int, default=3, help="Number of focus images")
    parser.add_argument("--dynamic", action="store_true", help="Also generate dynamic scene")
    args = parser.parse_args()

    generate_multi_focus_images(args.output, args.size, args.num)
    if args.dynamic:
        dynamic_dir = os.path.join(args.output, "dynamic")
        generate_dynamic_scene(dynamic_dir, args.size)


if __name__ == "__main__":
    main()
