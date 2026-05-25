import numpy as np
import matplotlib.pyplot as plt
from lens import LensSystem, create_singlet_lens
from ray_tracer import RayTracer, ImageAnalysis
from visualization import OpticalSystemVisualizer

def main():
    print("=" * 60)
    print("Example 1: Single Spherical Lens Simulation")
    print("=" * 60)

    focal_length = 100.0
    aperture_radius = 15.0
    lens_thickness = 8.0

    system = LensSystem(name='Single BK7 Lens (f=100mm)')

    lens = create_singlet_lens(
        focal_length=focal_length,
        z_position=0,
        thickness=lens_thickness,
        material='BK7',
        aperture_radius=aperture_radius,
        biconvex=True
    )

    for surf in lens.get_surfaces():
        system.add_element(surf)

    print(f"\nLens Parameters:")
    print(f"  Focal length (design): {focal_length} mm")
    print(f"  Material: BK7")
    print(f"  Front radius R1: {lens.r1:.2f} mm")
    print(f"  Back radius R2: {lens.r2:.2f} mm")
    print(f"  Thickness: {lens_thickness} mm")
    print(f"  Aperture radius: {aperture_radius} mm")

    f_paraxial = lens.get_focal_length(wavelength=0.587)
    bfl = lens.get_back_focal_length(wavelength=0.587)
    print(f"\nParaxial Analysis (d-line, 587nm):")
    print(f"  Focal length: {f_paraxial:.2f} mm")
    print(f"  Back focal length: {bfl:.2f} mm")
    print(f"  f/#: {f_paraxial / (2 * aperture_radius):.2f}")

    tracer = RayTracer(system)

    print("\nFinding best image plane...")
    best_z, best_rms, zs, rms = tracer.find_best_image_plane(
        wavelength=0.587,
        z_min=lens.z_position + lens_thickness + 50,
        z_max=lens.z_position + lens_thickness + 150,
        num_points=30,
        max_height=aperture_radius,
        num_rays=11
    )
    print(f"  Best image plane: z = {best_z:.2f} mm")
    print(f"  Best RMS spot size: {best_rms * 1000:.2f} μm")

    system.set_image_plane(best_z, size=10)

    analysis = ImageAnalysis(system, tracer)

    print("\nAberration Analysis:")
    sa = analysis.calculate_spherical_aberration(
        max_height=aperture_radius, wavelength=0.587, num_rays=50
    )
    if sa is not None:
        print(f"  Longitudinal spherical aberration: {sa * 1000:.2f} μm")

    ca = analysis.calculate_chromatic_aberration(
        wavelengths=[0.486, 0.656], max_height=aperture_radius * 0.1
    )
    print(f"  Axial chromatic aberration (F-C): {ca * 1000:.2f} μm")

    spot_data = analysis.get_spot_diagram(
        object_height=0,
        wavelengths=[0.486, 0.587, 0.656],
        num_rays=50,
        max_height=aperture_radius
    )
    for wl, positions in spot_data.items():
        if len(positions) > 0:
            centroid = np.mean(positions, axis=0)
            rms = np.sqrt(np.mean(np.sum((positions - centroid)**2, axis=1)))
            print(f"  RMS spot size ({wl * 1000:.0f}nm): {rms * 1000:.2f} μm")

    report = analysis.generate_report(wavelength=0.587)
    print(f"\nPerformance Summary:")
    print(f"  Max distortion: {report['max_distortion']:.3f}%")

    visualizer = OpticalSystemVisualizer(system, tracer)

    print("\nGenerating visualization...")
    fig1, ax1 = plt.subplots(figsize=(14, 6))
    visualizer.plot_optical_layout(
        ax=ax1,
        wavelength=0.587,
        num_rays=15,
        max_height=aperture_radius,
        object_height=0,
        title=f'Single BK7 Lens (f={focal_length}mm) - Optical Layout'
    )
    plt.tight_layout()
    plt.savefig('example1_layout.png', dpi=150)
    print("  Saved: example1_layout.png")

    fig2, ax2 = plt.subplots(figsize=(8, 8))
    visualizer.plot_spot_diagram(
        spot_data, ax=ax2,
        show_airy=True,
        f_number=f_paraxial / (2 * aperture_radius),
        wavelength=0.587
    )
    plt.tight_layout()
    plt.savefig('example1_spot.png', dpi=150)
    print("  Saved: example1_spot.png")

    fig3, ax3 = plt.subplots(figsize=(10, 6))
    visualizer.plot_fan_diagram(
        object_height=0,
        wavelengths=[0.486, 0.587, 0.656],
        num_rays=50,
        max_height=aperture_radius,
        ax=ax3
    )
    plt.tight_layout()
    plt.savefig('example1_fan.png', dpi=150)
    print("  Saved: example1_fan.png")

    print("\nGenerating comprehensive report (this may take a while)...")
    fig4 = visualizer.create_comprehensive_report(
        object_height=0,
        max_height=aperture_radius,
        wavelengths=[0.587],
        filename='example1_report.png'
    )
    print("  Saved: example1_report.png")

    print("\n" + "=" * 60)
    print("Simulation complete!")
    print("=" * 60)

    plt.close('all')
    return system, tracer, analysis

if __name__ == '__main__':
    main()
