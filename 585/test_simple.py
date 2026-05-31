import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import torch
import numpy as np

print("=" * 60)
print("Testing 3D Human Pose Estimation System")
print("=" * 60)

print("\n1. Testing imports...")
try:
    from utils.config import config
    print("✓ config loaded")
    
    from models.smpl import SMPL
    print("✓ SMPL imported")
    
    from models.hmr import HMR, WeakPerspectiveCamera
    print("✓ HMR imported")
    
    from detectors.openpose import OpenPoseDetector, Keypoint, PersonDetection, HandDetection
    print("✓ OpenPoseDetector imported")
    
    from utils.tracking import MultiPersonTracker
    print("✓ MultiPersonTracker imported")
    
    from utils.smoothing import PoseSmoother
    print("✓ PoseSmoother imported")
    
    from utils.keypoints import KeypointFusion
    print("✓ KeypointFusion imported")
    
    from utils.visualization import PoseVisualizer3D
    print("✓ PoseVisualizer3D imported")
    
    from pipeline.estimator import HumanPoseEstimator3D
    print("✓ HumanPoseEstimator3D imported")
    
    print("\n✓ All imports successful!")
except Exception as e:
    print(f"✗ Import error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n2. Testing HMR model...")
try:
    hmr = HMR(num_shape_params=10, num_pose_params=72, num_iterations=3, pretrained_backbone=False)
    hmr.eval()
    
    dummy_input = torch.randn(2, 3, 224, 224)
    with torch.no_grad():
        betas, pose, camera = hmr(dummy_input)
    
    print(f"  Input shape: {dummy_input.shape}")
    print(f"  Betas shape: {betas.shape}")
    print(f"  Pose shape: {pose.shape}")
    print(f"  Camera shape: {camera.shape}")
    print("✓ HMR model works!")
except Exception as e:
    print(f"✗ HMR error: {e}")
    import traceback
    traceback.print_exc()

print("\n3. Testing WeakPerspectiveCamera...")
try:
    camera = WeakPerspectiveCamera()
    dummy_joints = torch.randn(2, 24, 3)
    dummy_camera = torch.randn(2, 3)
    
    projected = camera.project(dummy_joints, dummy_camera)
    print(f"  3D joints shape: {dummy_joints.shape}")
    print(f"  Projected 2D shape: {projected.shape}")
    print("✓ Camera projection works!")
except Exception as e:
    print(f"✗ Camera error: {e}")

print("\n4. Testing PoseSmoother...")
try:
    smoother = PoseSmoother(method="exponential", alpha=0.7)
    dummy_joints = np.random.randn(24, 3)
    dummy_betas = np.random.randn(10)
    dummy_pose = np.random.randn(72)
    dummy_camera = np.random.randn(3)
    
    smoothed = smoother.smooth(0, dummy_joints, dummy_betas, dummy_pose, dummy_camera)
    print(f"  Smoothed joints shape: {smoothed.joints_3d.shape}")
    print(f"  Smoothed betas shape: {smoothed.betas.shape}")
    print("✓ PoseSmoother works!")
except Exception as e:
    print(f"✗ Smoother error: {e}")

print("\n5. Testing KeypointFusion...")
try:
    fusion = KeypointFusion()
    dummy_joints = np.random.randn(24, 3)
    dummy_camera = np.array([1.0, 0.0, 0.0])
    
    aligned = fusion.align_smpl_to_openpose(torch.tensor(dummy_joints, dtype=torch.float32))
    print(f"  Aligned joints shape: {aligned.shape}")
    print("✓ KeypointFusion works!")
except Exception as e:
    print(f"✗ Fusion error: {e}")

print("\n6. Testing PoseVisualizer3D...")
try:
    visualizer = PoseVisualizer3D(enable_mesh=False)
    dummy_joints = np.random.randn(24, 3)
    
    fig = visualizer.plot_pose_3d(dummy_joints, title="Test Plot")
    print(f"  Figure created: {fig is not None}")
    import matplotlib.pyplot as plt
    plt.close(fig)
    print("✓ PoseVisualizer3D works!")
except Exception as e:
    print(f"✗ Visualizer error: {e}")
    import traceback
    traceback.print_exc()

print("\n7. Testing MultiPersonTracker...")
try:
    tracker = MultiPersonTracker(use_kalman=False)
    
    dummy_detections = []
    for i in range(2):
        dummy_kps = [None] * 18
        for j in range(5):
            dummy_kps[j] = Keypoint(x=100 + i*50 + j*10, y=100 + j*10, confidence=0.9)
        det = PersonDetection(
            keypoints=dummy_kps,
            bbox=(100 + i*100, 100, 100, 200),
            confidence=0.8,
            person_id=None
        )
        dummy_detections.append(det)
    
    tracks = tracker.update(dummy_detections)
    print(f"  Number of tracks: {len(tracks)}")
    print("✓ MultiPersonTracker works!")
except Exception as e:
    print(f"✗ Tracker error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("All basic tests completed!")
print("=" * 60)
print("\nTo run the full system:")
print("1. Download model weights as described in the documentation")
print("2. Place them in the models/ directory")
print("3. Run: streamlit run app.py")
print("\nFor API usage:")
print("  from pipeline.estimator import HumanPoseEstimator3D")
print("  estimator = HumanPoseEstimator3D()")
print("  result = estimator.process_image_file('test.jpg')")
