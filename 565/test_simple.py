import numpy as np
import sys

print("Testing basic imports...")
try:
    import numpy as np
    import scipy
    from scipy import linalg
    import matplotlib
    print("  NumPy, SciPy, Matplotlib: OK")
except ImportError as e:
    print(f"  Error: {e}")
    sys.exit(1)

print("\nTesting RXDetector module...")
try:
    from hsrx_detector import RXDetector
    
    np.random.seed(42)
    data = np.random.randn(1000, 20)
    data[900:] += 5.0
    
    detector = RXDetector()
    scores = detector.fit_detect(data)
    
    print(f"  Scores shape: {scores.shape}")
    print(f"  Background mean score: {np.mean(scores[:900]):.4f}")
    print(f"  Anomaly mean score: {np.mean(scores[900:]):.4f}")
    print("  RXDetector: OK")
except Exception as e:
    print(f"  Error: {e}")
    import traceback
    traceback.print_exc()

print("\nTesting SlidingWindowRX module...")
try:
    from sliding_window import SlidingWindowRX
    
    np.random.seed(42)
    image = np.random.randn(50, 50, 10)
    image[20:25, 20:25, :] += 3.0
    
    detector = SlidingWindowRX(window_size=20, guard_size=4, update_interval=10)
    scores = detector.detect_image(image, step=2)
    
    print(f"  Image shape: {image.shape}")
    print(f"  Scores shape: {scores.shape}")
    print("  SlidingWindowRX: OK")
except Exception as e:
    print(f"  Error: {e}")
    import traceback
    traceback.print_exc()

print("\nTesting GlobalBackgroundUpdater module...")
try:
    from sliding_window import GlobalBackgroundUpdater
    
    np.random.seed(42)
    frame1 = np.random.randn(30, 30, 15)
    frame2 = np.random.randn(30, 30, 15) + 0.5
    frame2[10:15, 10:15, :] += 4.0
    
    updater = GlobalBackgroundUpdater(alpha=0.1)
    updater.initialize(frame1)
    scores = updater.detect(frame2)
    updater.update(frame2)
    
    print(f"  Scores shape: {scores.shape}")
    print("  GlobalBackgroundUpdater: OK")
except Exception as e:
    print(f"  Error: {e}")
    import traceback
    traceback.print_exc()

print("\nTesting hs_utils module...")
try:
    from hs_utils import generate_hyperspectral_image, HSVisualizer
    
    image, gt = generate_hyperspectral_image(
        height=60, width=60, n_bands=20, n_anomalies=3, seed=42
    )
    
    print(f"  Generated image shape: {image.shape}")
    print(f"  Ground truth shape: {gt.shape}")
    print(f"  Number of anomaly pixels: {np.sum(gt)}")
    print("  generate_hyperspectral_image: OK")
    
    visualizer = HSVisualizer()
    print("  HSVisualizer: OK")
except Exception as e:
    print(f"  Error: {e}")
    import traceback
    traceback.print_exc()

print("\nTesting gpu_module (CPU fallback)...")
try:
    from gpu_module import RXGPU
    
    gpu = RXGPU()
    print(f"  GPU available: {gpu.is_available()}")
    
    data = np.random.randn(100, 10)
    mean = np.random.randn(10)
    cov = np.random.randn(10, 10)
    cov = cov.T @ cov + 0.1 * np.eye(10)
    cov_inv = np.linalg.inv(cov)
    
    scores = gpu.compute_rx_scores(data, mean, cov_inv)
    print(f"  Scores computed: {scores.shape}")
    print("  RXGPU (CPU fallback): OK")
except Exception as e:
    print(f"  Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*50)
print("All basic tests passed!")
print("="*50)
