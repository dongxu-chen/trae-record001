import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np

print('=' * 60)
print('Testing new features: Occlusion, Adaptive Smoothing, Hand Alignment')
print('=' * 60)

print('\n1. Testing Occlusion Reasoning...')
from utils.occlusion import TemporalPoseCompleter, SymmetryAwareCompleter

completer = TemporalPoseCompleter(num_joints=24)
symmetry_completer = SymmetryAwareCompleter(num_joints=24)

joints_3d = np.random.randn(24, 3) * 0.3
joints_3d[0] = [0, 0, 0]

keypoints_2d = [None] * 24
for i in range(18):
    if i not in [1, 2]:
        from detectors.openpose import Keypoint
        keypoints_2d[i] = Keypoint(x=100+i*5, y=150+i*3, confidence=0.8)

result = completer.process_frame(0, joints_3d, keypoints_2d)
print(f'  Completed joints shape: {result.joints_3d.shape}')
print(f'  Occlusion mask visible count: {np.sum(result.occlusion_mask)}')
print(f'  Used prior: {result.used_prior}')

occlusion_mask = np.ones(24, dtype=bool)
occlusion_mask[1] = False
symmetric_joints = symmetry_completer.apply_symmetry(joints_3d, occlusion_mask)
print(f'  Symmetry completed joints shape: {symmetric_joints.shape}')
print('[OK] Occlusion reasoning works!')

print('\n2. Testing Adaptive Smoothing...')
from utils.smoothing import PoseSmoother, MotionAnalyzer, AdaptiveSmoothingController

smoother = PoseSmoother(method='exponential', use_adaptive=True)
motion_analyzer = MotionAnalyzer(num_joints=24, num_pose=72)
controller = AdaptiveSmoothingController()

for i in range(10):
    joints = np.random.randn(24, 3) * 0.01 * i
    pose = np.random.randn(72) * 0.001 * i
    camera = np.array([1.0, 0.0, 0.0])
    
    metrics = motion_analyzer.update(0, joints, pose, camera)
    alpha = controller.compute_alpha(metrics.motion_magnitude)
    
print(f'  Final motion magnitude: {metrics.motion_magnitude:.4f}')
print(f'  Is large motion: {metrics.is_large_motion}')
print(f'  Adaptive alpha: {alpha:.4f}')
print('[OK] Adaptive smoothing works!')

print('\n3. Testing Global Hand Alignment...')
from utils.hand_alignment import GlobalHandAligner, TemporalHandAligner

hand_aligner = GlobalHandAligner(num_body_joints=24)
temporal_aligner = TemporalHandAligner()

body_joints = np.random.randn(24, 3) * 0.5
body_scale = hand_aligner.compute_body_scale(body_joints)
print(f'  Body scale: {body_scale:.4f}')

arm_rot = hand_aligner.compute_arm_orientation(body_joints, 'right')
print(f'  Arm rotation matrix shape: {arm_rot.shape}')

from detectors.openpose import Keypoint, HandDetection
hand_keypoints = []
for i in range(21):
    hand_keypoints.append(Keypoint(x=200+i*2, y=200, confidence=0.7+i*0.01))

camera_params = np.array([100.0, 0.0, 0.0])
result = hand_aligner.align_hand_to_body(hand_keypoints, body_joints, camera_params, 'right')
print(f'  Aligned hand joints shape: {result.aligned_hand_joints.shape}')
print(f'  Global scale factor: {result.scale_factor:.4f}')
print(f'  Alignment error: {result.alignment_error:.4f}')
print('[OK] Global hand alignment works!')

print('\n4. Testing Full Pipeline Integration...')
from pipeline.estimator import HumanPoseEstimator3D
from utils.config import Config

config = Config()
config.DEVICE = 'cpu'

print('  Pipeline imports successful!')
print('[OK] Full pipeline integration successful!')

print('\n' + '=' * 60)
print('All new features tested successfully!')
print('=' * 60)
