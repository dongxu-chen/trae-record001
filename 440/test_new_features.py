import matplotlib
matplotlib.use('Agg')

from cpd_nonrigid_registration import NonRigidCPDRegistration
import numpy as np
import os

os.makedirs('./results', exist_ok=True)

print("=" * 70)
print("Testing New CPD Features: Anisotropic + Robust + Temporal")
print("=" * 70)

print("\n" + "=" * 70)
print("Test 1: Anisotropic CPD Registration")
print("=" * 70)

cpd_ani = NonRigidCPDRegistration(
    alpha=2.0, beta=0.5, max_iterations=20,
    tolerance=1e-5, w=0.1, use_two_stage=False,
    anisotropic_weights=[1.5, 0.8, 1.0]
)

source, target = cpd_ani.generate_synthetic_data(
    num_points=150, shape='sphere', deformation_scale=0.2
)

print(f"Anisotropic weights: {cpd_ani.anisotropic_weights}")

registered, deformation = cpd_ani.register_anisotropic()
metrics = cpd_ani.evaluate_registration()

cpd_ani.visualize_anisotropic_comparison(save_path='./results/new_anisotropic.png')

print("\n" + "=" * 70)
print("Test 2: Robust CPD with Tukey Kernel")
print("=" * 70)

cpd_robust = NonRigidCPDRegistration(
    alpha=2.0, beta=0.5, max_iterations=20,
    tolerance=1e-5, w=0.1, use_two_stage=False,
    robust_kernel='tukey', kernel_param=0.3
)

np.random.seed(42)
source_robust = cpd_robust._generate_sphere(150)
target_robust = cpd_robust._apply_nonrigid_deformation(source_robust, 0.2)

num_noise = 30
noise_idx = np.random.choice(len(target_robust), num_noise, replace=False)
target_robust[noise_idx] += np.random.randn(num_noise, 3) * 0.5

print(f"Added {num_noise} outlier points to target")
print(f"Using {cpd_robust.robust_kernel} kernel with param={cpd_robust.kernel_param}")

registered_rob, deformation_rob = cpd_robust.register_robust(source=source_robust, target=target_robust)
metrics_rob = cpd_robust.evaluate_registration()

cpd_robust.visualize_robust_kernel_comparison(save_path='./results/new_robust.png')

print("\n" + "=" * 70)
print("Test 3: Spatio-Temporal Sequence Registration")
print("=" * 70)

cpd_temp = NonRigidCPDRegistration(
    alpha=2.0, beta=0.5, max_iterations=15,
    tolerance=1e-5, w=0.1, use_two_stage=False,
    temporal_smoothing=0.3
)

sequence, target_frame = cpd_temp.generate_synthetic_sequence(
    num_frames=5, num_points=100, shape='sphere',
    deformation_scale=0.2, motion_type='wave'
)

print(f"Sequence length: {len(sequence)}")
print(f"Temporal smoothing: {cpd_temp.temporal_smoothing}")

results = cpd_temp.register_sequence(sequence, target_frame)

cpd_temp.visualize_sequence_results(save_path='./results/new_temporal.png')

print("\n" + "=" * 70)
print("Test 4: Combined Features")
print("=" * 70)

cpd_combined = NonRigidCPDRegistration(
    alpha=2.0, beta=0.5, max_iterations=15,
    tolerance=1e-5, w=0.1,
    use_two_stage=True, coarse_sample_ratio=0.4, coarse_max_iter=10,
    robust_kernel='huber', kernel_param=0.2
)

source_c, target_c = cpd_combined.generate_synthetic_data(
    num_points=200, shape='sphere', deformation_scale=0.2
)

print("Two-stage + Robust kernel combined")
registered_c, deformation_c = cpd_combined.register()
metrics_c = cpd_combined.evaluate_registration()

cpd_combined.visualize_point_clouds(save_path='./results/new_combined.png')
cpd_combined.visualize_two_stage_progress(save_path='./results/new_combined_two_stage.png')

print("\n" + "=" * 70)
print("All new feature tests completed successfully!")
print("=" * 70)
