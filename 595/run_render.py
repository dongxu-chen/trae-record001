import numpy as np
import cv2
import time
import sys
import os
import random

LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'render_progress.log')

def log(msg):
    with open(LOG_FILE, 'a') as f:
        f.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")
    print(msg, flush=True)


def render_single_frame(scene, camera, width, height, base_samples, max_depth, rng,
                        adaptive_max_samples=0, adaptive_threshold=0.1):
    inv_w = 1.0 / max(width - 1, 1)
    inv_h = 1.0 / max(height - 1, 1)
    from raytracer import ray_color, EPSILON

    if adaptive_max_samples <= base_samples:
        adaptive_max_samples = base_samples

    def trace_pixel(i, pixel_y, num_samples):
        cr, cg, cb = 0.0, 0.0, 0.0
        for _ in range(num_samples):
            u = (i + rng.random()) * inv_w
            v = (pixel_y + rng.random()) * inv_h
            ray = camera.get_ray(u, v, rng)
            color = ray_color(ray, scene, max_depth, max_depth, rng)
            cr += color.x
            cg += color.y
            cb += color.z
        return cr, cg, cb

    pixels_accum = np.zeros((height, width, 3), dtype=np.float64)
    sample_counts = np.ones((height, width), dtype=np.int32) * base_samples

    for j in range(height):
        pixel_y = height - 1 - j
        for i in range(width):
            cr, cg, cb = trace_pixel(i, pixel_y, base_samples)
            pixels_accum[j, i, 0] = cr
            pixels_accum[j, i, 1] = cg
            pixels_accum[j, i, 2] = cb

    edge_count = 0
    if adaptive_max_samples > base_samples:
        for j in range(height):
            for i in range(width):
                need_more = False
                neighbors = []
                if i > 0:
                    neighbors.append(pixels_accum[j, i - 1])
                if i < width - 1:
                    neighbors.append(pixels_accum[j, i + 1])
                if j > 0:
                    neighbors.append(pixels_accum[j - 1, i])
                if j < height - 1:
                    neighbors.append(pixels_accum[j + 1, i])

                if neighbors:
                    curr = pixels_accum[j, i]
                    max_diff = 0.0
                    for n in neighbors:
                        diff_r = abs(curr[0] - n[0]) / max(base_samples, 1)
                        diff_g = abs(curr[1] - n[1]) / max(base_samples, 1)
                        diff_b = abs(curr[2] - n[2]) / max(base_samples, 1)
                        max_diff = max(max_diff, diff_r, diff_g, diff_b)

                    if max_diff > adaptive_threshold:
                        need_more = True

                if need_more:
                    edge_count += 1
                    pixel_y = height - 1 - j
                    extra_samples = adaptive_max_samples - base_samples
                    cr, cg, cb = trace_pixel(i, pixel_y, extra_samples)
                    pixels_accum[j, i, 0] += cr
                    pixels_accum[j, i, 1] += cg
                    pixels_accum[j, i, 2] += cb
                    sample_counts[j, i] = adaptive_max_samples

    image = np.zeros((height, width, 3), dtype=np.float64)
    for j in range(height):
        for i in range(width):
            inv_s = 1.0 / sample_counts[j, i]
            image[j, i, 0] = pixels_accum[j, i, 0] * inv_s
            image[j, i, 1] = pixels_accum[j, i, 1] * inv_s
            image[j, i, 2] = pixels_accum[j, i, 2] * inv_s

    return image, edge_count


if __name__ == '__main__':
    mode = 'single'
    if len(sys.argv) > 1 and sys.argv[1] in ('animation', 'anim'):
        mode = 'animation'
        sys.argv = sys.argv[1:]
    elif len(sys.argv) > 1 and sys.argv[1] in ('photon', 'caustic'):
        mode = 'photon'
        sys.argv = sys.argv[1:]
    elif len(sys.argv) > 1 and sys.argv[1] in ('texture', 'textured'):
        mode = 'texture'
        sys.argv = sys.argv[1:]

    width = 320
    height = 240
    samples = 8
    max_depth = 5
    adaptive_max_samples = 0
    adaptive_threshold = 0.1
    num_frames = 10
    fps = 24
    texture_path = ''

    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == '--width' and i + 1 < len(sys.argv):
            width = int(sys.argv[i + 1]); i += 2
        elif arg == '--height' and i + 1 < len(sys.argv):
            height = int(sys.argv[i + 1]); i += 2
        elif arg == '--samples' and i + 1 < len(sys.argv):
            samples = int(sys.argv[i + 1]); i += 2
        elif arg == '--depth' and i + 1 < len(sys.argv):
            max_depth = int(sys.argv[i + 1]); i += 2
        elif arg == '--adaptive-max' and i + 1 < len(sys.argv):
            adaptive_max_samples = int(sys.argv[i + 1]); i += 2
        elif arg == '--adaptive-thresh' and i + 1 < len(sys.argv):
            adaptive_threshold = float(sys.argv[i + 1]); i += 2
        elif arg == '--frames' and i + 1 < len(sys.argv):
            num_frames = int(sys.argv[i + 1]); i += 2
        elif arg == '--fps' and i + 1 < len(sys.argv):
            fps = int(sys.argv[i + 1]); i += 2
        elif arg == '--texture' and i + 1 < len(sys.argv):
            texture_path = sys.argv[i + 1]; i += 2
        else:
            try:
                if i == 1: width = int(arg)
                elif i == 2: height = int(arg)
                elif i == 3: samples = int(arg)
                elif i == 4: max_depth = int(arg)
                elif i == 5: adaptive_max_samples = int(arg)
                elif i == 6: adaptive_threshold = float(arg)
            except ValueError:
                pass
            i += 1

    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)

    from raytracer import *

    if mode == 'animation':
        log("=== Animation Rendering Mode ===")
        keyframes = [
            AnimKeyframe(0.0, Vec3(10, 4, 8), Vec3(0, 1, 0), 40.0),
            AnimKeyframe(0.25, Vec3(8, 3, -5), Vec3(0, 1, 0), 35.0),
            AnimKeyframe(0.5, Vec3(-6, 5, 4), Vec3(0, 1, 0), 30.0),
            AnimKeyframe(0.75, Vec3(-4, 2, -6), Vec3(0, 1, 0), 45.0),
            AnimKeyframe(1.0, Vec3(10, 4, 8), Vec3(0, 1, 0), 40.0),
        ]
        log(f"Animation: {num_frames} frames, {fps} fps")
        log(f"Resolution: {width}x{height}, {samples} samples, depth {max_depth}")
        render_animation(
            create_demo_scene,
            keyframes,
            width=width,
            height=height,
            samples_per_pixel=samples,
            max_depth=max_depth,
            num_frames=num_frames,
            output_dir='frames',
            fps=fps,
            adaptive_threshold=adaptive_threshold,
            adaptive_max_samples=adaptive_max_samples,
        )

    elif mode == 'photon':
        log("=== Photon Mapping (Caustics) Mode ===")
        log(f"Building photon map...")
        scene = create_textured_scene(use_photon_map=True)
        log(f"Scene: {len(scene.objects)} objects, {len(scene.lights)} lights")
        if scene.caustic_photon_map:
            log(f"Caustic photons: {len(scene.caustic_photon_map.photons)}")
        if scene.photon_map:
            log(f"Global photons: {len(scene.photon_map.photons)}")

        lookfrom = Vec3(8, 4, 8)
        lookat = Vec3(0, 1, 0)
        camera = Camera(
            lookfrom=lookfrom, lookat=lookat, vup=Vec3(0, 1, 0),
            vfov=35, aspect_ratio=width / height, aperture=0.05,
            focus_dist=(lookfrom - lookat).length(),
        )

        if adaptive_max_samples <= samples:
            adaptive_max_samples = samples
            base_samples = samples
        else:
            base_samples = samples

        start_time = time.time()
        log(f"Rendering {width}x{height}, depth {max_depth}")
        rng = random.Random(SCENE_SEED + 1)
        image, edge_count = render_single_frame(
            scene, camera, width, height, base_samples, max_depth, rng,
            adaptive_max_samples, adaptive_threshold,
        )

        image = np.clip(image, 0, None)
        image = np.sqrt(image)
        image = np.clip(image * 255, 0, 255).astype(np.uint8)
        image_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        cv2.imwrite('output_photon.png', image_bgr)

        total_time = time.time() - start_time
        log(f"Render complete in {total_time:.2f}s")
        log(f"Output: output_photon.png ({width}x{height})")

    elif mode == 'texture':
        log("=== Textured Scene Mode ===")
        scene = create_textured_scene(texture_path=texture_path if texture_path else None)
        log(f"Scene: {len(scene.objects)} objects, {len(scene.lights)} lights")

        lookfrom = Vec3(8, 4, 8)
        lookat = Vec3(0, 1, 0)
        camera = Camera(
            lookfrom=lookfrom, lookat=lookat, vup=Vec3(0, 1, 0),
            vfov=35, aspect_ratio=width / height, aperture=0.05,
            focus_dist=(lookfrom - lookat).length(),
        )

        if adaptive_max_samples <= samples:
            adaptive_max_samples = samples
            base_samples = samples
        else:
            base_samples = samples

        start_time = time.time()
        log(f"Rendering {width}x{height}, depth {max_depth}")
        rng = random.Random(SCENE_SEED + 1)
        image, edge_count = render_single_frame(
            scene, camera, width, height, base_samples, max_depth, rng,
            adaptive_max_samples, adaptive_threshold,
        )

        image = np.clip(image, 0, None)
        image = np.sqrt(image)
        image = np.clip(image * 255, 0, 255).astype(np.uint8)
        image_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        cv2.imwrite('output_textured.png', image_bgr)

        total_time = time.time() - start_time
        log(f"Render complete in {total_time:.2f}s")
        log(f"Output: output_textured.png ({width}x{height})")

    else:
        log("=== Standard Rendering Mode ===")
        scene = create_demo_scene()
        log(f"Scene: {len(scene.objects)} objects, {len(scene.lights)} lights")

        lookfrom = Vec3(8, 3, 6)
        lookat = Vec3(0, 1, 0)
        camera = Camera(
            lookfrom=lookfrom, lookat=lookat, vup=Vec3(0, 1, 0),
            vfov=35, aspect_ratio=width / height, aperture=0.05,
            focus_dist=(lookfrom - lookat).length(),
        )

        if adaptive_max_samples <= samples:
            adaptive_max_samples = samples
            base_samples = samples
        else:
            base_samples = samples

        start_time = time.time()
        if adaptive_max_samples > base_samples:
            log(f"Adaptive sampling: {base_samples} base -> {adaptive_max_samples} max (threshold={adaptive_threshold})")
            log(f"Rendering {width}x{height}, depth {max_depth}")
            est_min = width * height * base_samples
            est_max = width * height * adaptive_max_samples
            log(f"Estimated rays: {est_min:,} ~ {est_max:,}")
        else:
            log(f"Rendering {width}x{height}, {samples} samples, depth {max_depth}")
            log(f"Estimated total rays: {width * height * samples:,}")

        rng = random.Random(SCENE_SEED + 1)
        image, edge_count = render_single_frame(
            scene, camera, width, height, base_samples, max_depth, rng,
            adaptive_max_samples, adaptive_threshold,
        )

        image = np.clip(image, 0, None)
        image = np.sqrt(image)
        image = np.clip(image * 255, 0, 255).astype(np.uint8)
        image_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        cv2.imwrite('output.png', image_bgr)

        total_time = time.time() - start_time
        log(f"Render complete in {total_time:.2f}s")
        log(f"Output: output.png ({width}x{height})")

        with open('render_log.txt', 'w') as f:
            f.write(f"Render time: {total_time:.2f}s\n")
            f.write(f"Resolution: {width}x{height}\n")
            f.write(f"Base samples: {base_samples}\n")
            f.write(f"Adaptive max samples: {adaptive_max_samples}\n")
            f.write(f"Adaptive threshold: {adaptive_threshold}\n")
            f.write(f"Edge pixels: {edge_count}\n")
            f.write(f"Max depth: {max_depth}\n")
