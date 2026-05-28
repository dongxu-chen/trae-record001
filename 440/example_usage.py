from cpd_nonrigid_registration import NonRigidCPDRegistration
import numpy as np


def example_sphere_registration():
    print("=" * 60)
    print("Example 1: Sphere with Non-Rigid Deformation")
    print("=" * 60)
    
    cpd = NonRigidCPDRegistration(
        alpha=2.0,
        beta=0.5,
        max_iterations=30,
        tolerance=1e-6
    )
    
    source, target = cpd.generate_synthetic_data(
        num_points=300,
        shape='sphere',
        deformation_scale=0.25
    )
    
    print(f"Source shape: {source.shape}")
    print(f"Target shape: {target.shape}")
    
    registered, deformation = cpd.register()
    metrics = cpd.evaluate_registration()
    
    cpd.visualize_point_clouds()
    cpd.visualize_deformation_field(subsample=15)
    cpd.visualize_deformation_magnitude()
    
    return cpd


def example_plane_registration():
    print("\n" + "=" * 60)
    print("Example 2: Wavy Plane Registration")
    print("=" * 60)
    
    cpd = NonRigidCPDRegistration(
        alpha=3.0,
        beta=0.3,
        max_iterations=50,
        tolerance=1e-7
    )
    
    source, target = cpd.generate_synthetic_data(
        num_points=400,
        shape='plane',
        deformation_scale=0.15
    )
    
    print(f"Source shape: {source.shape}")
    print(f"Target shape: {target.shape}")
    
    registered, deformation = cpd.register()
    metrics = cpd.evaluate_registration()
    
    cpd.visualize_point_clouds()
    cpd.visualize_deformation_field(subsample=20)
    
    return cpd


def example_custom_data():
    print("\n" + "=" * 60)
    print("Example 3: Using Custom Point Cloud Data")
    print("=" * 60)
    
    source = np.random.randn(200, 3) * 0.5
    target = source.copy()
    
    x, y, z = target[:, 0], target[:, 1], target[:, 2]
    target[:, 0] += 0.2 * np.sin(2 * np.pi * y)
    target[:, 1] += 0.1 * np.cos(2 * np.pi * x * z)
    target[:, 2] += 0.15 * np.sin(np.pi * x * y)
    
    cpd = NonRigidCPDRegistration(
        alpha=2.0,
        beta=0.5,
        max_iterations=40
    )
    
    registered, deformation = cpd.register(source=source, target=target)
    metrics = cpd.evaluate_registration()
    
    cpd.visualize_point_clouds()
    cpd.visualize_gmm_components(num_components=8)
    
    return cpd


if __name__ == '__main__':
    cpd1 = example_sphere_registration()
    cpd2 = example_plane_registration()
    cpd3 = example_custom_data()
    
    print("\n" + "=" * 60)
    print("All examples completed successfully!")
    print("=" * 60)
