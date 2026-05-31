import numpy as np
import time
import traceback
import sys

try:
    from raytracer import *
    
    print("Creating demo scene...", flush=True)
    scene = create_demo_scene()
    print(f"Scene: {len(scene.objects)} objects, {len(scene.lights)} lights, BVH={scene.bvh is not None}", flush=True)
    
    lookfrom = Vec3(8, 3, 6)
    lookat = Vec3(0, 1, 0)
    camera = Camera(
        lookfrom=lookfrom, lookat=lookat, vup=Vec3(0, 1, 0),
        vfov=35, aspect_ratio=4/3, aperture=0.05,
        focus_dist=(lookfrom - lookat).length(),
    )
    
    rng = np.random.RandomState(123)
    
    print("Tracing single pixel...", flush=True)
    start = time.time()
    ray = camera.get_ray(0.5, 0.5, rng)
    color = ray_color(ray, scene, 5, 5, rng)
    elapsed = time.time() - start
    print(f"Pixel: {color}, time: {elapsed:.4f}s", flush=True)
    
    width, height = 80, 60
    samples = 2
    max_depth = 3
    
    print(f"Rendering {width}x{height}...", flush=True)
    start = time.time()
    
    import cv2
    image = np.zeros((height, width, 3), dtype=np.float64)
    inv_w = 1.0 / max(width - 1, 1)
    inv_h = 1.0 / max(height - 1, 1)
    
    for j in range(height):
        pixel_y = height - 1 - j
        for i in range(width):
            cr, cg, cb = 0.0, 0.0, 0.0
            for _ in range(samples):
                u = (i + rng.random()) * inv_w
                v = (pixel_y + rng.random()) * inv_h
                ray = camera.get_ray(u, v, rng)
                color = ray_color(ray, scene, max_depth, max_depth, rng)
                cr += color.x
                cg += color.y
                cb += color.z
            inv_s = 1.0 / samples
            image[j, i, 0] = cr * inv_s
            image[j, i, 1] = cg * inv_s
            image[j, i, 2] = cb * inv_s
        if (j + 1) % 20 == 0:
            elapsed = time.time() - start
            print(f"  Row {j+1}/{height} - {elapsed:.1f}s", flush=True)
    
    total = time.time() - start
    print(f"Done in {total:.2f}s", flush=True)
    
    image = np.clip(image, 0, None)
    image = np.sqrt(image)
    image = np.clip(image * 255, 0, 255).astype(np.uint8)
    image_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
    cv2.imwrite('test_v2.png', image_bgr)
    print(f"Saved test_v2.png ({image.shape})", flush=True)
    
except Exception as e:
    traceback.print_exc()
    sys.exit(1)
