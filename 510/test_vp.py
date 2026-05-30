import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
import numpy as np
from video_processor import create_video_enhancer

e = create_video_enhancer(use_lightweight=True, scale_factor=2, optimize_inference=False)
f1 = np.random.randint(0, 255, (32, 32, 3), dtype=np.uint8)
f2 = np.random.randint(0, 255, (32, 32, 3), dtype=np.uint8)
i, h1, h2 = e.interpolate_and_enhance(f1, f2)
e.set_quality_weight(0.3)
info = e.get_model_info()
print(f'Lightweight: interp={i.shape} hr={h1.shape} qw={e.quality_weight} params={info["total_params"]/1e6:.2f}M')
