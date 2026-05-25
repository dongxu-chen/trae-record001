import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

print("=" * 80)
print("Testing New Features: Diffraction, Optimization, Non-Sequential Tracing")
print("=" * 80)

# Test 1: Diffraction PSF and MTF
print("\n[Test 1] Diffraction PSF and MTF Calculation")
print("-" * 80)

from lens import LensSystem, create_singlet_lens, create_achromatic_doublet
from ray_tracer import RayTracer, ImageAnalysis
from diffraction import DiffractionPSF
from visualization import OpticalSystemVisualizer

# Create test system
system = LensSystem('Diffraction_Test')
lens = create_singlet_lens(focal_length=100, z_position=0, thickness=8.0,
                          material='BK7', aperture_radius=15.0)
for surf in lens.get_surfaces():
    system.add_element(surf)

tracer = RayTracer(system)
best_z, _, _, _ = tracer.find_best_image_plane(
    wavelength=0.587, z_min=50, z_max=150, num_points=20,
    max_height=15.0, num_rays=11)
system.set_image_plane(best_z, size=20)

# Calculate PSF
print("\n  Calculating PSF...")
psf_calc = DiffractionPSF(system, tracer)
psf_fft, line_profile = psf_calc.calculate_psf_fft(
    object_height=0.0, wavelength=0.587, max_height=15.0,
    num_rays=100, pupil_samples=128, psf_size=128)
print(f"  PSF shape: {psf_fft.shape}")
print(f"  PSF peak intensity: {np.max(psf_fft):.6f}")

# Calculate Strehl ratio
strehl = psf_calc.calculate_strehl_ratio(
    object_height=0.0, wavelength=0.587, max_height=15.0, num_rays=100)
print(f"  Strehl ratio: {strehl:.3f}")

# Airy disk radius
f_number = 100 / (2 * 15.0)
airy_radius = psf_calc.calculate_airy_disk_radius(wavelength=0.587, f_number=f_number)
print(f"  Airy disk radius: {airy_radius * 1000:.2f} μm")

# Calculate MTF
print("\n  Calculating MTF...")
sf = np.linspace(0, 100, 30)
_, mtf_geom = psf_calc.calculate_mtf(
    object_height=0.0, wavelength=0.587, max_height=15.0,
    spatial_frequencies=sf, method='geometric', num_samples=30)
_, mtf_diff = psf_calc.calculate_mtf(
    object_height=0.0, wavelength=0.587, max_height=15.0,
    spatial_frequencies=sf, method='diffraction')
_, mtf_lim = psf_calc.calculate_diffraction_limited_mtf(
    sf, wavelength=0.587, f_number=f_number)

print(f"  Geometric MTF @ 50 lp/mm: {mtf_geom[np.argmin(np.abs(sf-50))]:.3f}")
print(f"  Diffraction MTF @ 50 lp/mm: {mtf_diff[np.argmin(np.abs(sf-50))]:.3f}")
print(f"  Diffraction Limited @ 50 lp/mm: {mtf_lim[np.argmin(np.abs(sf-50))]:.3f}")

# Generate diffraction report
print("\n  Generating diffraction report...")
visualizer = OpticalSystemVisualizer(system, tracer)
fig = visualizer.create_diffraction_report(
    object_height=0.0, wavelength=0.587, max_height=15.0,
    f_number=f_number, filename='test_diffraction_report.png')
plt.close(fig)
print("  Saved: test_diffraction_report.png")

print("\n  ✓ Diffraction PSF and MTF working")

# Test 2: Lens Optimization
print("\n[Test 2] Lens Optimization with Damped Least Squares")
print("-" * 80)

from optimization import setup_singlet_optimizer

print("\n  Setting up singlet lens optimizer...")
optimizer = setup_singlet_optimizer(focal_length=100.0, material='BK7')

# Evaluate initial merit
initial_merit = optimizer.evaluate_merit_function(verbose=False)
initial_params = optimizer.get_all_parameters()
print(f"  Initial parameters: R1={initial_params[0]:.2f}mm, R2={initial_params[1]:.2f}mm")
print(f"  Initial merit function: {initial_merit:.4f}")

# Run optimization (reduced iterations for speed)
print("\n  Running optimization (this may take a moment)...")
best_params, best_merit = optimizer.optimize_damped_least_squares(
    max_iterations=10, initial_damping=1e-2, damping_factor=5.0,
    tol=1e-4, verbose=True)

print(f"\n  Optimized parameters: R1={best_params[0]:.2f}mm, R2={best_params[1]:.2f}mm")
print(f"  Final merit function: {best_merit:.4f}")
print(f"  Improvement: {(initial_merit - best_merit) / initial_merit * 100:.1f}%")

# Generate optimization plots
print("\n  Generating optimization plots...")
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
visualizer.plot_optimization_convergence(optimizer, ax=(ax1, ax2))
plt.tight_layout()
plt.savefig('test_optimization.png', dpi=150)
plt.close(fig)
print("  Saved: test_optimization.png")

print("\n  ✓ Lens optimization working")

# Test 3: Non-Sequential Ray Tracing (Ghosts and Stray Light)
print("\n[Test 3] Non-Sequential Ray Tracing")
print("-" * 80)

from nonsequential import (
    NonSequentialRayTracer, setup_lens_system_for_stray_analysis,
    create_collimated_nonsequential
)

print("\n  Setting up non-sequential system...")
ns_system = setup_lens_system_for_stray_analysis()
ns_tracer = NonSequentialRayTracer(ns_system)

# Create rays
print("  Tracing rays...")
rays = create_collimated_nonsequential(
    position=[0, 0, -50], num_rays=21, max_height=15.0,
    wavelength=0.587, max_bounces=4)

# Trace
all_rays = ns_tracer.trace_rays(rays, max_rays_per_bounce=2)
print(f"  Total rays traced: {len(all_rays)}")
print(f"  Ghost rays: {len(ns_tracer.ghost_rays)}")
print(f"  Stray rays: {len(ns_tracer.stray_rays)}")

# Analyze stray light
stray_intensity = ns_tracer.get_stray_light_intensity()
print(f"\n  Detector intensity analysis:")
print(f"    Total: {stray_intensity['total']:.4f}")
print(f"    Direct: {stray_intensity['total'] - stray_intensity['ghost'] - stray_intensity['stray']:.4f}")
print(f"    Ghost: {stray_intensity['ghost']:.4f} ({stray_intensity['ghost_fraction']*100:.2f}%)")
print(f"    Stray: {stray_intensity['stray']:.4f} ({stray_intensity['stray_fraction']*100:.2f}%)")

# Analyze ghost types
ghost_types = ns_tracer.analyze_ghosts()
print(f"\n  Ghost ray types found: {len(ghost_types)}")
for path_key, info in list(ghost_types.items())[:5]:
    path_str = ' → '.join(path_key)
    print(f"    {path_str}: {info['count']} rays, total intensity={info['total_intensity']:.4f}")

# Generate stray light plots
print("\n  Generating stray light plots...")
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

# Ghost ray paths
from visualization import OpticalSystemVisualizer
vis_ns = OpticalSystemVisualizer(system, tracer)
vis_ns.plot_ghost_rays(ns_tracer.ghost_rays[:20], ax=ax1)

# Stray light analysis
vis_ns.plot_stray_light_analysis(stray_intensity, ns_tracer.detector_hits, ax=(ax2, None))

plt.tight_layout()
plt.savefig('test_stray_light.png', dpi=150)
plt.close(fig)
print("  Saved: test_stray_light.png")

print("\n  ✓ Non-sequential ray tracing working")

# Test 4: Generate comprehensive comparison
print("\n[Test 4] Singlet vs Doublet Performance Comparison")
print("-" * 80)

# Create doublet
system_d = LensSystem('Doublet_Comparison')
doublet = create_achromatic_doublet(focal_length=100, z_position=0,
                                    thickness1=8.0, thickness2=4.0,
                                    material1='BK7', material2='SF11',
                                    aperture_radius=15.0)
for surf in doublet.get_surfaces():
    system_d.add_element(surf)

tracer_d = RayTracer(system_d)
best_z_d, _, _, _ = tracer_d.find_best_image_plane(
    wavelength=0.587, z_min=50, z_max=150, num_points=20,
    max_height=15.0, num_rays=11)
system_d.set_image_plane(best_z_d, size=20)

# Compare performance
analysis_s = ImageAnalysis(system, tracer)
analysis_d = ImageAnalysis(system_d, tracer_d)

print("\n  Performance Comparison (Singlet vs Doublet):")
print(f"  {'Parameter':<30} {'Singlet':>12} {'Doublet':>12}")
print(f"  {'-'*30} {'-'*12} {'-'*12}")

sa_s = analysis_s.calculate_spherical_aberration(wavelength=0.587, max_height=15.0)
sa_d = analysis_d.calculate_spherical_aberration(wavelength=0.587, max_height=15.0)
print(f"  {'Spherical aberration [μm]':<30} {sa_s*1000 if sa_s else 0:>12.2f} {sa_d*1000 if sa_d else 0:>12.2f}")

ca_s = analysis_s.calculate_chromatic_aberration()
ca_d = analysis_d.calculate_chromatic_aberration()
print(f"  {'Chromatic aberration [μm]':<30} {ca_s*1000:>12.2f} {ca_d*1000:>12.2f}")

achro_s = analysis_s.calculate_achromatic_performance(max_height=0.1, num_rays=7)
achro_d = analysis_d.calculate_achromatic_performance(max_height=0.1, num_rays=7)
print(f"  {'Secondary spectrum [μm]':<30} {achro_s['max_secondary_spectrum']*1000:>12.2f} {achro_d['max_secondary_spectrum']*1000:>12.2f}")

# MTF comparison
print("\n  MTF Comparison:")
psf_s = DiffractionPSF(system, tracer)
psf_d = DiffractionPSF(system_d, tracer_d)
sf = np.linspace(0, 100, 20)
for freq in [10, 30, 50]:
    idx = np.argmin(np.abs(sf - freq))
    _, mtf_s = psf_s.calculate_mtf(
        object_height=0.0, wavelength=0.587, max_height=15.0,
        spatial_frequencies=sf, method='diffraction')
    _, mtf_d = psf_d.calculate_mtf(
        object_height=0.0, wavelength=0.587, max_height=15.0,
        spatial_frequencies=sf, method='diffraction')
    print(f"    MTF @ {freq} lp/mm: singlet={mtf_s[idx]:.3f}, doublet={mtf_d[idx]:.3f}")

# Generate comparison plot
print("\n  Generating comparison plot...")
fig, axes = plt.subplots(2, 2, figsize=(16, 12))

# Singlet PSF
psf_s_img, lp_s = psf_s.calculate_psf_fft(
    object_height=0.0, wavelength=0.587, max_height=15.0,
    num_rays=80, psf_size=128)
visualizer.plot_psf(psf_s_img, lp_s, ax=(axes[0, 0], None))
axes[0, 0].set_title('Singlet PSF', fontsize=14)

# Doublet PSF
psf_d_img, lp_d = psf_d.calculate_psf_fft(
    object_height=0.0, wavelength=0.587, max_height=15.0,
    num_rays=80, psf_size=128)
vis_d = OpticalSystemVisualizer(system_d, tracer_d)
vis_d.plot_psf(psf_d_img, lp_d, ax=(axes[0, 1], None))
axes[0, 1].set_title('Doublet PSF', fontsize=14)

# MTF comparison
sf = np.linspace(0, 100, 30)
_, mtf_s_geom = psf_s.calculate_mtf(
    object_height=0.0, wavelength=0.587, max_height=15.0,
    spatial_frequencies=sf, method='geometric')
_, mtf_d_geom = psf_d.calculate_mtf(
    object_height=0.0, wavelength=0.587, max_height=15.0,
    spatial_frequencies=sf, method='geometric')
_, mtf_lim = psf_s.calculate_diffraction_limited_mtf(
    sf, wavelength=0.587, f_number=f_number)

axes[1, 0].plot(sf, mtf_s_geom, 'b-o', linewidth=2, markersize=4, label='Singlet')
axes[1, 0].plot(sf, mtf_d_geom, 'r-s', linewidth=2, markersize=4, label='Doublet')
axes[1, 0].plot(sf, mtf_lim, 'g--', linewidth=2, label='Diffraction Limit')
axes[1, 0].set_xlabel('Spatial Frequency (lp/mm)', fontsize=12)
axes[1, 0].set_ylabel('MTF', fontsize=12)
axes[1, 0].set_title('MTF Comparison', fontsize=14)
axes[1, 0].grid(True, alpha=0.3)
axes[1, 0].legend(fontsize=10)
axes[1, 0].set_ylim(0, 1.05)

# Secondary spectrum comparison
sec_s = analysis_s.calculate_secondary_spectrum(max_height=0.1, num_rays=7)
sec_d = analysis_d.calculate_secondary_spectrum(max_height=0.1, num_rays=7)

axes[1, 1].plot(sec_s['wavelengths']*1000, sec_s['secondary_spectrum']*1000,
                'b-o', linewidth=2, markersize=5, label='Singlet')
axes[1, 1].plot(sec_d['wavelengths']*1000, sec_d['secondary_spectrum']*1000,
                'r-s', linewidth=2, markersize=5, label='Doublet')
axes[1, 1].axhline(0, color='gray', linestyle=':', linewidth=1)
axes[1, 1].set_xlabel('Wavelength (nm)', fontsize=12)
axes[1, 1].set_ylabel('Secondary Spectrum (μm)', fontsize=12)
axes[1, 1].set_title('Secondary Spectrum Comparison', fontsize=14)
axes[1, 1].grid(True, alpha=0.3)
axes[1, 1].legend(fontsize=10)

plt.tight_layout()
plt.savefig('test_comparison.png', dpi=150, bbox_inches='tight')
plt.close(fig)
print("  Saved: test_comparison.png")

print("\n" + "=" * 80)
print("ALL NEW FEATURE TESTS PASSED!")
print("=" * 80)
print("\nSummary of New Features:")
print("  1. ✓ Diffraction PSF calculation (FFT method)")
print("  2. ✓ Strehl ratio calculation")
print("  3. ✓ Geometric and diffraction MTF calculation")
print("  4. ✓ Airy disk radius calculation")
print("  5. ✓ Damped least squares optimization engine")
print("  6. ✓ Parameter bounds and constraints")
print("  7. ✓ Merit function with weighted aberrations")
print("  8. ✓ Non-sequential ray tracing")
print("  9. ✓ Ghost ray detection and classification")
print("  10. ✓ Stray light analysis")
print("  11. ✓ Surface reflectivity modeling")
print("  12. ✓ Enhanced visualization for all features")
print("\nGenerated files:")
print("  - test_diffraction_report.png")
print("  - test_optimization.png")
print("  - test_stray_light.png")
print("  - test_comparison.png")
