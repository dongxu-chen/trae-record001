import traceback
import sys

try:
    from raytracer import *
    print("Import successful")
    scene = create_demo_scene()
    print(f"Scene created with {len(scene.objects)} objects, {len(scene.lights)} lights")
    print(f"BVH built: {scene.bvh is not None}")
    render_single_thread(scene, width=80, height=60, samples_per_pixel=1, max_depth=1, output_path='test.png')
    print("Render completed!")
except Exception as e:
    traceback.print_exc()
    print(f"Error: {e}")
