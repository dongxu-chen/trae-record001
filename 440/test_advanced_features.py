import matplotlib
matplotlib.use('Agg')

from cpd_nonrigid_registration import NonRigidCPDRegistration
import numpy as np
import os

os.makedirs('./results', exist_ok=True)

print("=" * 70)
print("Testing Advanced CPD Registration Features")
print("=" * 70)

print("\n" + "=" * 70)
print("Test 1: Two-Stage Coarse-to-Fine Registration")
print("=" * 70)

cpd = NonRigidCPDRegistration(
    alpha=2.0,
    beta=0.5,
    max_iterations=30,
    tolerance=1e-6,
    w=0.1,
    use_two_stage=True,
    coarse_sample_ratio=0.3,
    coarse_max_iter=15
)

source, target = cpd.generate_synthetic_data(
    num_points=300,
    shape='sphere',
    deformation_scale=0.2
)

print(f"Source: {source.shape}, Target: {target.shape}")

registered, deformation = cpd.register()
metrics = cpd.evaluate_registration()

cpd.visualize_two_stage_progress(save_path='./results/adv_two_stage.png')

print("\n" + "=" * 70)
print("Test 2: GMM with Outlier Modeling")
print("=" * 70)

print(f"Outlier detection results:")
print(f"  Number of outliers: {cpd.gmm_params['num_outliers']}")
print(f"  Outlier ratio: {cpd.gmm_params['outlier_ratio']*100:.2f}%")
print(f"  Noise component weight: {cpd.gmm_params['noise_component']['weight']:.6f}")

cpd.visualize_gmm_components(save_path='./results/adv_gmm_outliers.png', num_components=8)

print("\n" + "=" * 70)
print("Test 3: Deformation Streamlines Visualization")
print("=" * 70)

streamlines = cpd.visualize_deformation_streamlines(
    save_path='./results/adv_streamlines.png',
    num_seed_points=12,
    integration_steps=8
)

print(f"Generated {len(streamlines)} streamlines")

print("\n" + "=" * 70)
print("Test 4: Critical Regions Detection")
print("=" * 70)

critical_regions = cpd.visualize_critical_regions(
    save_path='./results/adv_critical_regions.png',
    num_regions=5
)

print("Top 5 critical regions:")
for i, region in enumerate(critical_regions):
    print(f"  Region {i+1}: max_deform={region['max_magnitude']:.4f}, "
          f"mean_deform={region['mean_magnitude']:.4f}, "
          f"points={region['num_points']}")

print("\n" + "=" * 70)
print("Test 5: Compare Single-Stage vs Two-Stage")
print("=" * 70)

cpd_single = NonRigidCPDRegistration(
    alpha=2.0,
    beta=0.5,
    max_iterations=30,
    tolerance=1e-6,
    w=0.1,
    use_two_stage=False
)

cpd_single.source_original = source.copy()
cpd_single.target_original = target.copy()
cpd_single._single_stage_register()
metrics_single = cpd_single.evaluate_registration()

print("\nComparison:")
print(f"  Two-Stage  Final Error: {metrics['final_mean_error']:.6f}")
print(f"  Single-Stage Final Error: {metrics_single['final_mean_error']:.6f}")
print(f"  Improvement: {(metrics_single['final_mean_error'] - metrics['final_mean_error']) / metrics_single['final_mean_error'] * 100:.2f}%")

cpd.visualize_point_clouds(save_path='./results/adv_point_clouds.png')
cpd.visualize_deformation_field(save_path='./results/adv_deformation_field.png', subsample=15)

cpd.save_results('./results')

print("\n" + "=" * 70)
print("All advanced feature tests completed successfully!")
print("=" * 70)
