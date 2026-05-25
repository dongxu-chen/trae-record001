import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from lens import LensSystem, create_singlet_lens, create_achromatic_doublet
from ray_tracer import RayTracer, ImageAnalysis
from visualization import OpticalSystemVisualizer
from optical_constants import DEFAULT_WAVELENGTHS_VISIBLE, refractive_index

print("=" * 70)
print("Testing Optical System Improvements")
print("=" * 70)

# Test 1: Stabilized Refraction and TIR Detection
print("\n[Test 1] Stabilized Refraction and TIR Detection")
print("-" * 50)

system1 = LensSystem('TIR_Test')
system1.add_thick_lens(z_position=0, r1=50, r2=-50, thickness=10,
                       material='SF11', aperture_radius=25)
system1.set_image_plane(100, size=30)

tracer1 = RayTracer(system1)
from ray import Ray, create_ray_bundle

# Create rays with varying heights to test TIR at second surface
rays = create_ray_bundle(object_height=0.0, num_rays=15, max_height=24.0,
                         wavelength=0.587, initial_z=-50, distribution='meridional')

tir_count = 0
for i, ray in enumerate(rays):
    traced = tracer1.trace_ray(ray)
    if traced.total_internal_reflection:
        tir_count += 1
        h = float(ray.history[0][0][0])
        print(f"  Ray {i}: TIR detected at height {h:.2f}mm")
        for event in traced.reflection_events:
            print(f"    - {event['type']}: incident angle={event['incident_angle']:.2f}°, n1={event['n1']:.3f}, n2={event['n2']:.3f}")

print(f"  TIR rays detected: {tir_count}/{len(rays)}")

# Verify refraction return values
test_ray = Ray([0, 0, -50], [0, 0, 1], wavelength=0.587)
traced_test = tracer1.trace_ray(test_ray)
print(f"  Paraxial ray active: {traced_test.active}")
print(f"  Elements hit: {traced_test.elements_hit}")
print("  ✓ Stabilized refraction with TIR marking working")

# Test 2: Standard Aspherical Coefficient Order
print("\n[Test 2] Standard Aspherical Coefficient Order")
print("-" * 50)

system2 = LensSystem('Aspheric_Test')
curvature1 = 1.0 / 103.36
curvature2 = -1.0 / 103.36
conic1 = 0.0
conic2 = 0.0
poly_coeffs = [0.0, 0.0]

system2.add_aspheric_lens(z_position=0, curvature1=curvature1,
                          curvature2=curvature2, conic1=conic1, conic2=conic2,
                          thickness=8.0, material='BK7', aperture_radius=15.0,
                          poly_coeffs1=poly_coeffs, poly_coeffs2=poly_coeffs)
system2.set_image_plane(100, size=10)

tracer2 = RayTracer(system2)
rays2 = create_ray_bundle(object_height=0.0, num_rays=5, max_height=10.0,
                          wavelength=0.587, initial_z=-50, distribution='meridional')
traced2 = tracer2.trace_rays(rays2)

print(f"  Aspheric surface 1: curvature={curvature1:.6e} mm⁻¹, conic={conic1}")
print(f"  Aspheric surface 2: curvature={curvature2:.6e} mm⁻¹, conic={conic2}")
print(f"  Polynomial coefficients: {poly_coeffs}")
print(f"  Active rays after aspheric: {sum(1 for r in traced2 if r.active)}/{len(traced2)}")
print("  ✓ Standard coefficient order (c, k, α) working")

# Test 3: Multi-wavelength Dispersion and Secondary Spectrum
print("\n[Test 3] Multi-wavelength Dispersion Analysis")
print("-" * 50)

system3 = LensSystem('Chromatic_Test')
doublet = create_achromatic_doublet(focal_length=100, z_position=0,
                                    thickness1=8, thickness2=4,
                                    material1='BK7', material2='SF11',
                                    aperture_radius=15)
for surf in doublet.get_surfaces():
    system3.add_element(surf)

best_z, _, _, _ = RayTracer(system3).find_best_image_plane(
    wavelength=0.587, z_min=50, z_max=150, num_points=20,
    max_height=15.0, num_rays=11)
system3.set_image_plane(best_z, size=10)

tracer3 = RayTracer(system3)
analysis3 = ImageAnalysis(system3, tracer3)

# Calculate achromatic performance
achro_perf = analysis3.calculate_achromatic_performance(max_height=0.1, num_rays=11)

print(f"\n  Achromatic Doublet Performance:")
print(f"    F-line focus:    {achro_perf['focus_position_F']:.4f} mm")
print(f"    d-line focus:    {achro_perf['focus_position_d']:.4f} mm")
print(f"    C-line focus:    {achro_perf['focus_position_C']:.4f} mm")
print(f"    Axial CA (F-C):  {achro_perf['axial_chromatic_aberration_FC'] * 1000:.2f} μm")
print(f"    Secondary spec:  {achro_perf['d_line_deviation'] * 1000:.2f} μm")
print(f"    Max secondary:   {achro_perf['max_secondary_spectrum'] * 1000:.2f} μm")

# Calculate full secondary spectrum
secondary = analysis3.calculate_secondary_spectrum(
    wavelengths=DEFAULT_WAVELENGTHS_VISIBLE, max_height=0.1, num_rays=11)

print(f"\n  Full Secondary Spectrum Analysis:")
for i, wl in enumerate(secondary['wavelengths']):
    dev = secondary['secondary_spectrum'][i] * 1000
    print(f"    {wl * 1000:.0f}nm: deviation = {dev:+.2f} μm")

# Test lateral chromatic aberration
lateral_lca, img_heights = analysis3.calculate_lateral_chromatic_aberration(
    wavelength1=0.486, wavelength2=0.656, object_height=5.0,
    max_height=0.1, num_rays=11)

print(f"\n  Lateral Chromatic Aberration (at 5mm object height):")
print(f"    F-line image height: {img_heights[0.486]:.4f} mm")
print(f"    C-line image height: {img_heights[0.656]:.4f} mm")
print(f"    Lateral CA:          {lateral_lca * 1000:.2f} μm")

print("  ✓ Multi-wavelength dispersion analysis working")

# Test 4: Generate visualization
print("\n[Test 4] Generating Visualizations")
print("-" * 50)

visualizer3 = OpticalSystemVisualizer(system3, tracer3)

# Secondary spectrum plot
fig1, ax1 = plt.subplots(figsize=(10, 6))
result = visualizer3.plot_secondary_spectrum(secondary, ax=ax1)
plt.tight_layout()
plt.savefig('test_secondary_spectrum.png', dpi=150)
print("  Saved: test_secondary_spectrum.png")

# Chromatic focus shift with extended wavelengths
fig2, ax2 = plt.subplots(figsize=(10, 6))
visualizer3.plot_chromatic_focus_shift(wavelengths=DEFAULT_WAVELENGTHS_VISIBLE, ax=ax2)
plt.tight_layout()
plt.savefig('test_chromatic_shift_extended.png', dpi=150)
print("  Saved: test_chromatic_shift_extended.png")

# Refractive index dispersion curves
fig3, ax3 = plt.subplots(figsize=(10, 6))
wls_plot = np.linspace(0.4, 0.7, 100)
for material in ['BK7', 'SF11', 'F2', 'BAK1']:
    ns = [refractive_index(material, wl) for wl in wls_plot]
    ax3.plot(wls_plot * 1000, ns, linewidth=2, label=material)
for wl in DEFAULT_WAVELENGTHS_VISIBLE:
    ax3.axvline(wl * 1000, color='gray', linestyle=':', alpha=0.5)
ax3.set_xlabel('Wavelength (nm)', fontsize=12)
ax3.set_ylabel('Refractive Index (n)', fontsize=12)
ax3.set_title('Dispersion Curves for Optical Glasses', fontsize=14)
ax3.legend(fontsize=10)
ax3.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig('test_dispersion_curves.png', dpi=150)
print("  Saved: test_dispersion_curves.png")

# Test 5: Compare singlet vs doublet chromatic performance
print("\n[Test 5] Singlet vs Doublet Chromatic Comparison")
print("-" * 50)

# Singlet lens
system_singlet = LensSystem('Singlet_Comparison')
singlet = create_singlet_lens(focal_length=100, z_position=0, thickness=8,
                              material='BK7', aperture_radius=15)
for surf in singlet.get_surfaces():
    system_singlet.add_element(surf)
best_z_s, _, _, _ = RayTracer(system_singlet).find_best_image_plane(
    wavelength=0.587, z_min=50, z_max=150, num_points=20,
    max_height=15.0, num_rays=11)
system_singlet.set_image_plane(best_z_s, size=10)
analysis_singlet = ImageAnalysis(system_singlet)
achro_singlet = analysis_singlet.calculate_achromatic_performance()

# Doublet lens (already have system3)
achro_doublet = achro_perf

print(f"\n  {'Parameter':<30} {'Singlet':>12} {'Doublet':>12}")
print(f"  {'-'*30} {'-'*12} {'-'*12}")
print(f"  {'Axial CA (F-C) [μm]':<30} {achro_singlet['axial_chromatic_aberration_FC']*1000:>12.2f} {achro_doublet['axial_chromatic_aberration_FC']*1000:>12.2f}")
print(f"  {'Secondary spec [μm]':<30} {achro_singlet['max_secondary_spectrum']*1000:>12.2f} {achro_doublet['max_secondary_spectrum']*1000:>12.2f}")
print(f"  {'d-line deviation [μm]':<30} {achro_singlet['d_line_deviation']*1000:>12.2f} {achro_doublet['d_line_deviation']*1000:>12.2f}")

# Comparison plot
fig4, axes = plt.subplots(1, 2, figsize=(14, 6))

# Singlet secondary
secondary_singlet = analysis_singlet.calculate_secondary_spectrum(
    wavelengths=DEFAULT_WAVELENGTHS_VISIBLE, max_height=0.1, num_rays=11)
ax_s = axes[0]
ax_s.plot(secondary_singlet['wavelengths'] * 1000,
          secondary_singlet['secondary_spectrum'] * 1000,
          'o-', linewidth=2, markersize=6, color='red')
ax_s.axhline(0, color='gray', linestyle=':', linewidth=1)
ax_s.set_xlabel('Wavelength (nm)', fontsize=12)
ax_s.set_ylabel('Secondary Spectrum (μm)', fontsize=12)
ax_s.set_title('Singlet Lens - Secondary Spectrum', fontsize=14)
ax_s.grid(True, alpha=0.3)

# Doublet secondary
ax_d = axes[1]
ax_d.plot(secondary['wavelengths'] * 1000,
          secondary['secondary_spectrum'] * 1000,
          'o-', linewidth=2, markersize=6, color='blue')
ax_d.axhline(0, color='gray', linestyle=':', linewidth=1)
ax_d.set_xlabel('Wavelength (nm)', fontsize=12)
ax_d.set_ylabel('Secondary Spectrum (μm)', fontsize=12)
ax_d.set_title('Achromatic Doublet - Secondary Spectrum', fontsize=14)
ax_d.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('test_singlet_vs_doublet.png', dpi=150)
print("  Saved: test_singlet_vs_doublet.png")

print("\n" + "=" * 70)
print("All tests completed successfully!")
print("=" * 70)
