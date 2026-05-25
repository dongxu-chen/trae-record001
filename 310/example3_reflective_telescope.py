import numpy as np
import matplotlib.pyplot as plt
from lens import LensSystem
from ray_tracer import RayTracer, ImageAnalysis
from visualization import OpticalSystemVisualizer
from ray import create_ray_bundle

def main():
    print("=" * 60)
    print("Example 3: Newtonian Reflector Telescope Simulation")
    print("=" * 60)

    primary_mirror_focal_length = 500.0
    primary_mirror_R = 2 * primary_mirror_focal_length
    primary_aperture_radius = 50.0

    secondary_flat_position = 350.0
    secondary_size = 25.0

    system = LensSystem(name='Newtonian Reflector (f=500mm)')

    primary = system.add_mirror(
        z_position=0,
        radius_of_curvature=-primary_mirror_R,
        aperture_radius=primary_aperture_radius,
        conic_constant=-1.0,
        name='Primary'
    )

    secondary = system.add_mirror(
        z_position=secondary_flat_position,
        radius_of_curvature=float('inf'),
        aperture_radius=secondary_size,
        conic_constant=0,
        name='Secondary'
    )

    system.set_image_plane(secondary_flat_position - 50, size=20)

    print(f"\nTelescope Parameters:")
    print(f"  Primary mirror:")
    print(f"    Radius of curvature: {primary_mirror_R:.1f} mm")
    print(f"    Focal length: {primary_mirror_focal_length:.1f} mm")
    print(f"    Aperture: {2 * primary_aperture_radius:.1f} mm")
    print(f"    Conic constant: {primary.conic_constant} (paraboloid)")
    print(f"  Secondary flat mirror:")
    print(f"    Position: z = {secondary_flat_position:.1f} mm")
    print(f"    Size: {secondary_size * 2:.1f} mm")
    print(f"  f/#: {primary_mirror_focal_length / (2 * primary_aperture_radius):.1f}")
    print(f"  Focal ratio: f/{primary_mirror_focal_length / (2 * primary_aperture_radius):.1f}")

    tracer = RayTracer(system)

    def trace_rays_for_reflector(object_height=0.0, wavelength=0.587, num_rays=21):
        rays = []
        heights = np.linspace(-primary_aperture_radius, primary_aperture_radius, num_rays)
        for h in heights:
            pos = np.array([h + object_height, 0, 1000.0])
            angle = object_height / 1000.0
            dir_ = np.array([angle, 0, -1.0])
            dir_ = dir_ / np.linalg.norm(dir_)
            from ray import Ray
            ray = Ray(pos, dir_, wavelength=wavelength)
            rays.append(ray)
        return tracer.trace_rays(rays)

    print("\nTracing rays for on-axis image...")
    traced_rays = trace_rays_for_reflector(object_height=0.0, wavelength=0.587, num_rays=31)

    active_rays = [r for r in traced_rays if r.active and r.final_position is not None]
    print(f"  Active rays: {len(active_rays)}/{len(traced_rays)}")

    if active_rays:
        positions = np.array([r.final_position[:2] for r in active_rays])
        centroid = np.mean(positions, axis=0)
        rms = np.sqrt(np.mean(np.sum((positions - centroid)**2, axis=1)))
        print(f"  RMS spot size: {rms * 1000:.2f} μm")

    print("\n" + "-" * 40)
    print("Spot analysis for multiple wavelengths")
    print("-" * 40)

    wavelengths = [0.486, 0.587, 0.656]
    spot_data = {}

    for wl in wavelengths:
        traced = trace_rays_for_reflector(object_height=0.0, wavelength=wl, num_rays=61)
        positions = []
        for r in traced:
            if r.active and r.final_position is not None:
                positions.append(r.final_position[:2].copy())
        spot_data[wl] = np.array(positions) if positions else np.array([])
        if len(spot_data[wl]) > 0:
            centroid = np.mean(spot_data[wl], axis=0)
            rms = np.sqrt(np.mean(np.sum((spot_data[wl] - centroid)**2, axis=1)))
            print(f"  {wl * 1000:.0f}nm: RMS = {rms * 1000:.2f} μm")

    print("\nNote: Reflective systems have NO chromatic aberration!")

    print("\nGenerating visualization...")
    visualizer = OpticalSystemVisualizer(system, tracer)

    traced_layout = trace_rays_for_reflector(object_height=0.0, wavelength=0.587, num_rays=15)

    fig1, ax1 = plt.subplots(figsize=(16, 6))
    for ray in traced_layout:
        if not ray.active:
            continue
        xs = []
        ys = []
        for pos, dir_ in ray.history:
            xs.append(pos[2])
            ys.append(pos[0])
        if len(xs) >= 2:
            ax1.plot(xs, ys, color=ray.get_color(), linewidth=1, alpha=0.7)
        if ray.final_position is not None:
            ax1.plot(ray.final_position[2], ray.final_position[0], 'o',
                    color=ray.get_color(), markersize=4)

    r_prim = np.linspace(-primary_aperture_radius, primary_aperture_radius, 200)
    z_prim = primary.get_surface_height(np.abs(r_prim))
    ax1.plot(z_prim, r_prim, 'k-', linewidth=2.5, label='Primary (Paraboloid)')

    r_sec = np.linspace(-secondary_size, secondary_size, 20)
    z_sec = np.ones_like(r_sec) * secondary_flat_position
    ax1.plot(z_sec, r_sec, 'b-', linewidth=2.5, label='Secondary (Flat)')

    ip = system.image_plane
    ax1.axhline(0, color='k', linestyle=':', linewidth=0.5)
    ax1.axvline(ip.z_position, color='k', linestyle='--', linewidth=1, label='Image Plane')

    ax1.set_xlabel('Z Position (mm)', fontsize=12)
    ax1.set_ylabel('Y Position (mm)', fontsize=12)
    ax1.set_title('Newtonian Reflector Telescope - Optical Layout', fontsize=14)
    ax1.legend(fontsize=10, loc='lower right')
    ax1.grid(True, alpha=0.3)
    ax1.set_aspect('equal')
    ax1.set_xlim(-100, secondary_flat_position + 60)
    ax1.set_ylim(-primary_aperture_radius * 1.3, primary_aperture_radius * 1.3)

    plt.tight_layout()
    plt.savefig('example3_layout.png', dpi=150)
    print("  Saved: example3_layout.png")

    fig2, ax2 = plt.subplots(figsize=(8, 8))
    visualizer.plot_spot_diagram(
        spot_data, ax=ax2,
        show_airy=True,
        f_number=primary_mirror_focal_length / (2 * primary_aperture_radius),
        wavelength=0.587
    )
    ax2.set_title('Newtonian Reflector - Spot Diagram\n(No chromatic aberration!)')
    plt.tight_layout()
    plt.savefig('example3_spot.png', dpi=150)
    print("  Saved: example3_spot.png")

    print("\n" + "-" * 40)
    print("Off-axis performance analysis")
    print("-" * 40)

    off_axis_heights = [0, 5, 10, 15]
    rms_values = []

    for oh in off_axis_heights:
        traced = trace_rays_for_reflector(object_height=oh, wavelength=0.587, num_rays=61)
        positions = []
        for r in traced:
            if r.active and r.final_position is not None:
                positions.append(r.final_position[:2].copy())
        if positions:
            positions = np.array(positions)
            centroid = np.mean(positions, axis=0)
            rms = np.sqrt(np.mean(np.sum((positions - centroid)**2, axis=1)))
            rms_values.append(rms * 1000)
        else:
            rms_values.append(0)
        print(f"  Object height {oh}mm: RMS = {rms_values[-1]:.2f} μm")

    fig3, ax3 = plt.subplots(figsize=(10, 6))
    ax3.plot(off_axis_heights, rms_values, 'o-', linewidth=2, markersize=6)
    ax3.set_xlabel('Object Height (mm)', fontsize=12)
    ax3.set_ylabel('RMS Spot Size (μm)', fontsize=12)
    ax3.set_title('Newtonian Reflector - Off-axis Performance', fontsize=14)
    ax3.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig('example3_off_axis.png', dpi=150)
    print("  Saved: example3_off_axis.png")

    print("\n" + "-" * 40)
    print("Comparison: Spherical vs Paraboloidal Primary")
    print("-" * 40)

    system_spherical = LensSystem(name='Newtonian with Spherical Primary')
    primary_sph = system_spherical.add_mirror(
        z_position=0,
        radius_of_curvature=-primary_mirror_R,
        aperture_radius=primary_aperture_radius,
        conic_constant=0.0,
        name='Primary_Spherical'
    )
    secondary_sph = system_spherical.add_mirror(
        z_position=secondary_flat_position,
        radius_of_curvature=float('inf'),
        aperture_radius=secondary_size,
        conic_constant=0,
        name='Secondary'
    )
    system_spherical.set_image_plane(secondary_flat_position - 50, size=20)
    tracer_sph = RayTracer(system_spherical)

    def trace_spherical(object_height=0.0, wavelength=0.587, num_rays=21):
        rays = []
        heights = np.linspace(-primary_aperture_radius, primary_aperture_radius, num_rays)
        for h in heights:
            pos = np.array([h + object_height, 0, 1000.0])
            angle = object_height / 1000.0
            dir_ = np.array([angle, 0, -1.0])
            dir_ = dir_ / np.linalg.norm(dir_)
            from ray import Ray
            ray = Ray(pos, dir_, wavelength=wavelength)
            rays.append(ray)
        return tracer_sph.trace_rays(rays)

    traced_sph = trace_spherical(object_height=0.0, wavelength=0.587, num_rays=61)
    positions_sph = []
    for r in traced_sph:
        if r.active and r.final_position is not None:
            positions_sph.append(r.final_position[:2].copy())

    if positions_sph:
        positions_sph = np.array(positions_sph)
        centroid_sph = np.mean(positions_sph, axis=0)
        rms_sph = np.sqrt(np.mean(np.sum((positions_sph - centroid_sph)**2, axis=1)))
        print(f"  Spherical primary RMS: {rms_sph * 1000:.2f} μm")
        print(f"  Paraboloidal primary RMS: {rms * 1000:.2f} μm")
        print(f"  Improvement: {(rms_sph - rms) * 1000:.2f} μm ({(1 - rms/rms_sph)*100:.1f}% better)")

    fig4, (ax4a, ax4b) = plt.subplots(1, 2, figsize=(16, 6))

    for ax, traced, title in [(ax4a, traced_sph, 'Spherical Primary'),
                              (ax4b, traced_rays, 'Paraboloidal Primary')]:
        for ray in traced:
            if not ray.active:
                continue
            xs = []
            ys = []
            for pos, dir_ in ray.history:
                xs.append(pos[2])
                ys.append(pos[0])
            if len(xs) >= 2:
                ax.plot(xs, ys, color=ray.get_color(), linewidth=1, alpha=0.7)
        ax.plot(z_prim, r_prim, 'k-', linewidth=2.5)
        ax.plot(z_sec, r_sec, 'b-', linewidth=2.5)
        ax.axvline(ip.z_position, color='k', linestyle='--', linewidth=1)
        ax.set_xlabel('Z Position (mm)', fontsize=12)
        ax.set_ylabel('Y Position (mm)', fontsize=12)
        ax.set_title(title, fontsize=14)
        ax.grid(True, alpha=0.3)
        ax.set_aspect('equal')
        ax.set_xlim(-100, secondary_flat_position + 60)
        ax.set_ylim(-primary_aperture_radius * 1.3, primary_aperture_radius * 1.3)

    plt.tight_layout()
    plt.savefig('example3_spherical_vs_parabolic.png', dpi=150)
    print("  Saved: example3_spherical_vs_parabolic.png")

    print("\n" + "=" * 60)
    print("Simulation complete!")
    print("=" * 60)

    plt.close('all')
    return system, tracer

if __name__ == '__main__':
    main()
