import matplotlib
matplotlib.use('Agg')

from cpd_nonrigid_registration import NonRigidCPDRegistration
import numpy as np
import os

os.makedirs('./results', exist_ok=True)

print("=" * 60)
print("Testing Non-Rigid CPD Registration")
print("=" * 60)

cpd = NonRigidCPDRegistration(
    alpha=2.0,
    beta=0.5,
    max_iterations=30,
    tolerance=1e-6
)

print("\n1. Generating synthetic data...")
source, target = cpd.generate_synthetic_data(
    num_points=200,
    shape='sphere',
    deformation_scale=0.2
)
print(f"   Source: {source.shape}, Target: {target.shape}")
print(f"   Initial mean error: {np.mean(np.linalg.norm(source - target, axis=1)):.6f}")

print("\n2. Performing registration...")
registered, deformation = cpd.register()
print(f"   Registration completed!")
print(f"   Deformation field shape: {deformation.shape}")

print("\n3. Evaluating results...")
metrics = cpd.evaluate_registration()

print("\n4. Saving visualizations...")
cpd.visualize_point_clouds(save_path='./results/test_point_clouds.png')
cpd.visualize_deformation_field(save_path='./results/test_deformation_field.png', subsample=10)
cpd.visualize_deformation_magnitude(save_path='./results/test_deformation_magnitude.png')
cpd.visualize_gmm_components(save_path='./results/test_gmm.png', num_components=8)
print("   Visualizations saved to ./results/")

print("\n5. Saving results...")
cpd.save_results('./results')

print("\n" + "=" * 60)
print("All tests passed successfully!")
print("=" * 60)
