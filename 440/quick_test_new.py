import matplotlib
matplotlib.use('Agg')

from cpd_nonrigid_registration import NonRigidCPDRegistration
import numpy as np
import os

os.makedirs('./results', exist_ok=True)

print("Quick test of new features...")

# Test 1: Anisotropic
print("\nTest 1: Anisotropic CPD")
cpd_ani = NonRigidCPDRegistration(
    alpha=2.0, beta=0.5, max_iterations=10,
    tolerance=1e-4, w=0.1, use_two_stage=False,
    anisotropic_weights=[1.5, 0.8, 1.0]
)
source, target = cpd_ani.generate_synthetic_data(num_points=80, shape='sphere', deformation_scale=0.15)
registered, deformation = cpd_ani.register_anisotropic()
print("  Anisotropic done!")
cpd_ani.evaluate_registration()
cpd_ani.visualize_point_clouds(save_path='./results/qt_ani.png')

# Test 2: Robust
print("\nTest 2: Robust CPD")
cpd_rob = NonRigidCPDRegistration(
    alpha=2.0, beta=0.5, max_iterations=10,
    tolerance=1e-4, w=0.1, use_two_stage=False,
    robust_kernel='tukey', kernel_param=0.3
)
source_r, target_r = cpd_rob.generate_synthetic_data(num_points=80, shape='sphere', deformation_scale=0.15)
noise_idx = np.random.choice(len(target_r), 15, replace=False)
target_r[noise_idx] += np.random.randn(15, 3) * 0.4
registered_r, deformation_r = cpd_rob.register_robust(source=source_r, target=target_r)
print("  Robust done!")
cpd_rob.evaluate_registration()

# Test 3: Temporal
print("\nTest 3: Temporal Sequence")
cpd_temp = NonRigidCPDRegistration(
    alpha=2.0, beta=0.5, max_iterations=8,
    tolerance=1e-4, w=0.1, use_two_stage=False,
    temporal_smoothing=0.3
)
sequence, target_frame = cpd_temp.generate_synthetic_sequence(
    num_frames=3, num_points=60, shape='sphere', deformation_scale=0.15, motion_type='wave'
)
results = cpd_temp.register_sequence(sequence, target_frame)
print("  Temporal done!")

print("\nAll new features tested successfully!")
