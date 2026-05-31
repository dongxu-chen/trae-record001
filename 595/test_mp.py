import numpy as np
import time
import traceback
import sys

try:
    from raytracer import *
    
    print("Testing multi-process render...", flush=True)
    scene = create_demo_scene()
    
    start = time.time()
    render(
        scene,
        width=80,
        height=60,
        samples_per_pixel=2,
        max_depth=3,
        num_workers=2,
        output_path='test_mp.png',
    )
    elapsed = time.time() - start
    print(f"Multi-process render took {elapsed:.1f}s", flush=True)
    
except Exception as e:
    traceback.print_exc()
    print(f"Error: {e}", flush=True)
    sys.exit(1)
