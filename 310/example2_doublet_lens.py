import numpy as np
import matplotlib.pyplot as plt
from lens import LensSystem, create_achromatic_doublet, create_singlet_lens
from ray_tracer import RayTracer, ImageAnalysis
from visualization import OpticalSystemVisualizer

def main():
    print("=" * 60)
    print("Example 2: Achromatic Doublet Lens Simulation")
    print("=" * 60)

    focal_length = 100.0
    aperture_radius = 15.0

    system = LensSystem(name='Achromatic Doublet (f=100mm)')

    doublet = create_achromatic_doublet(
        focal_length=focal_length,
        z_position=0,
        thickness1=8,
        thickness2=4,
        material1='BK7',
        material2='SF11',
        aperture_radius=aperture_radius
    )

    for surf in doublet.get_surfaces():
        system.add_element(surf)

    print(f"\nDoublet Parameters:")
    print(f"  Focal length (design): {focal_length} mm")
    print(f"  Material 1 (crown): BK7")
    print(f"  Material 2 (flint): SF11")
    print(f"  R1: {doublet.r1:.2f} mm")
    print(f"  R2: {doublet.r2:.2f} mm")
    print(f"  R3: {doublet.r3:.2f} mm")
    print(f"  Thickness 1: {doublet.thickness1} mm")
    print(f"  Thickness 2: {doublet.thickness2} mm")
    print(f"  Aperture radius: {aperture_radius} mm")

    f_d = doublet.get_focal_length(wavelength=0.587)
    f_F = doublet.get_focal_length(wavelength=0.486)
    f_C = doublet.get_focal_length(wavelength=0.656)
    print(f"\nParaxial Analysis:")
    print(f"  Focal length (d-line): {f_d:.2f} mm")
    print(f"  Focal length (F-line): {f_F:.2f} mm")
    print(f"  Focal length (C-line): {f_C:.2f} mm")
    print(f"  Chromatic variation: {(f_F - f_C):.3f} mm")
    print(f"  f/#: {f_d / (2 * aperture_radius):.2f}")

    tracer = RayTracer(system)

    print("\nFinding best image plane (d-line)...")
    best_z, best_rms, zs, rms = tracer.find_best_image_plane(
        wavelength=0.587,
        z_min=50,
        z_max=150,
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
        print(f"  Longitudinal spherical aberration (d-line): {sa * 1000:.2f} μm")

    ca = analysis.calculate_chromatic_aberration(
        wavelengths=[0.486, 0.656], max_height=aperture_radius * 0.1
    )
    print(f"  Axial chromatic aberration (F-C): {ca * 1000:.2f} μm")

    print("\n" + "-" * 40)
    print("Comparison: Single Lens vs Achromatic Doublet")
    print("-" * 40)

    singlet = create_singlet_lens(
        focal_length=focal_length,
        z_position=0,
        thickness=12,
        material='BK7',
        aperture_radius=aperture_radius,
        biconvex=True
    )

    system_singlet = LensSystem(name='Single BK7 Lens')
    for surf in singlet.get_surfaces():
        system_singlet.add_element(surf)
    tracer_singlet = RayTracer(system_singlet)

    best_z_s, best_rms_s, _, _ = tracer_singlet.find_best_image_plane(
        wavelength=0.587, z_min=50, z_max=150, num_points=80,
        max_height=aperture_radius, num_rays=21
    )
    system_singlet.set_image_plane(best_z_s, size=10)
    analysis_singlet = ImageAnalysis(system_singlet, tracer_singlet)

    ca_s = analysis_singlet.calculate_chromatic_aberration(
        wavelengths=[0.486, 0.656], max_height=aperture_radius * 0.1
    )
    sa_s = analysis_singlet.calculate_spherical_aberration(
        max_height=aperture_radius, wavelength=0.587, num_rays=50
    )

    print(f"{'Parameter':<30} {'Singlet':>12} {'Doublet':>12}")
    print(f"{'-' * 54}")
    print(f"{'RMS spot size (d-line, μm)':<30} {best_rms_s * 1000:>12.2f} {best_rms * 1000:>12.2f}")
    sa_s_val = sa_s if sa_s is not None else 0
    sa_val = sa if sa is not None else 0
    print(f"{'Spherical aberration (μm)':<30} {sa_s_val * 1000:>12.2f} {sa_val * 1000:>12.2f}")
    print(f"{'Chromatic aberration (μm)':<30} {ca_s * 1000:>12.2f} {ca * 1000:>12.2f}")

    print("\nGenerating visualization...")
    visualizer = OpticalSystemVisualizer(system, tracer)

    fig1, ax1 = plt.subplots(figsize=(14, 6))
    visualizer.plot_optical_layout(
        ax=ax1,
        wavelength=0.587,
        num_rays=15,
        max_height=aperture_radius,
        object_height=0,
        title='Achromatic Doublet (BK7 + SF11) - Optical Layout'
    )
    plt.tight_layout()
    plt.savefig('example2_layout.png', dpi=150)
    print("  Saved: example2_layout.png")

    spot_data = analysis.get_spot_diagram(
        object_height=0,
        wavelengths=[0.486, 0.587, 0.656],
        num_rays=50,
        max_height=aperture_radius
    )

    fig2, ax2 = plt.subplots(figsize=(8, 8))
    visualizer.plot_spot_diagram(
        spot_data, ax=ax2,
        show_airy=True,
        f_number=f_d / (2 * aperture_radius),
        wavelength=0.587
    )
    plt.tight_layout()
    plt.savefig('example2_spot.png', dpi=150)
    print("  Saved: example2_spot.png")

    fig3, (ax3a, ax3b) = plt.subplots(1, 2, figsize=(14, 6))
    visualizer.plot_fan_diagram(
        object_height=0,
        wavelengths=[0.486, 0.587, 0.656],
        num_rays=50,
        max_height=aperture_radius,
        ax=ax3a
    )
    ax3a.set_title('Doublet - Fan Diagram')

    visualizer_s = OpticalSystemVisualizer(system_singlet, tracer_singlet)
    visualizer_s.plot_fan_diagram(
        object_height=0,
        wavelengths=[0.486, 0.587, 0.656],
        num_rays=50,
        max_height=aperture_radius,
        ax=ax3b
    )
    ax3b.set_title('Single Lens - Fan Diagram')

    plt.tight_layout()
    plt.savefig('example2_fan_comparison.png', dpi=150)
    print("  Saved: example2_fan_comparison.png")

    fig4, ax4 = plt.subplots(figsize=(10, 6))
    visualizer.plot_chromatic_focus_shift(
        wavelengths=np.linspace(0.4, 0.7, 15),
        ax=ax4
    )
    plt.tight_layout()
    plt.savefig('example2_chromatic_shift.png', dpi=150)
    print("  Saved: example2_chromatic_shift.png")

    fig5 = visualizer.create_comprehensive_report(
        object_height=0,
        max_height=aperture_radius,
        wavelengths=[0.486, 0.587, 0.656],
        filename='example2_report.png'
    )
    print("  Saved: example2_report.png")

    print("\n" + "=" * 60)
    print("Simulation complete!")
    print("=" * 60)

    plt.close('all')
    return system, tracer, analysis

if __name__ == '__main__':
    main()
