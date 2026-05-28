import matplotlib
matplotlib.use('Agg')

from cpd_nonrigid_registration import NonRigidCPDRegistration
import numpy as np
import os

os.makedirs('./results', exist_ok=True)

print("Quick test of advanced features...")

cpd = NonRigidCPDRegistration(
    alpha=2.0, beta=0.5, max_iterations=10,
    tolerance=1e-5, w=0.1,
    use_two_stage=True, coarse_sample_ratio=0.3, coarse_max_iter=5
)

source, target = cpd.generate_synthetic_data(
    num_points=100, shape='sphere', deformation_scale=0.15
)

print(f"Source: {source.shape}, Target: {target.shape}")

registered, deformation = cpd.register()
print("Registration done!")

metrics = cpd.evaluate_registration()

print("\nGMM outlier params:")
print(f"  Num outliers: {cpd.gmm_params['num_outliers']}")
print(f"  Outlier ratio: {cpd.gmm_params['outlier_ratio']:.4f}")

print("\nSaving visualizations...")
cpd.visualize_point_clouds(save_path='./results/qt_point_clouds.png')
cpd.visualize_two_stage_progress(save_path='./results/qt_two_stage.png')
cpd.visualize_deformation_streamlines(save_path='./results/qt_streamlines.png', num_seed_points=8)
cpd.visualize_critical_regions(save_path='./results/qt_critical.png', num_regions=3)
cpd.visualize_gmm_components(save_path='./results/qt_gmm.png', num_components=5)

print("\nAll tests passed!")
