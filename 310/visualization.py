import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
from optical_constants import WAVELENGTH_COLORS, WAVELENGTH_NAMES
from ray import create_ray_bundle, create_collimated_rays


class OpticalSystemVisualizer:
    def __init__(self, optical_system, ray_tracer=None):
        self.optical_system = optical_system
        self.ray_tracer = ray_tracer

    def plot_optical_layout(self, ax=None, rays=None, show_rays=True,
                            wavelength=0.587, num_rays=11, max_height=10.0,
                            object_height=0.0, initial_z=None,
                            xlim=None, ylim=None, title=''):
        if ax is None:
            fig, ax = plt.subplots(figsize=(12, 6))
        if initial_z is None:
            z_min, z_max = self.optical_system.get_z_extent()
            initial_z = z_min - 50
        if show_rays and rays is None:
            rays = create_ray_bundle(object_height=object_height,
                                    num_rays=num_rays,
                                    max_height=max_height,
                                    wavelength=wavelength,
                                    initial_z=initial_z,
                                    distribution='meridional')
            if self.ray_tracer is not None:
                rays = self.ray_tracer.trace_rays(rays)
        if rays is not None:
            for ray in rays:
                self._plot_ray(ax, ray)
        self._plot_elements(ax)
        if self.optical_system.image_plane is not None:
            ip = self.optical_system.image_plane
            ax.axvline(ip.z_position, color='k', linestyle='--', linewidth=1)
            ax.text(ip.z_position, -ip.aperture_radius - 2,
                    'Image\nPlane', ha='center', va='top', fontsize=10)
        if xlim is None:
            z_min, z_max = self.optical_system.get_z_extent()
            ax.set_xlim(initial_z - 10, z_max + 50)
        else:
            ax.set_xlim(xlim)
        if ylim is None:
            max_ap = max([e.aperture_radius for e in self.optical_system.elements])
            if self.optical_system.image_plane is not None:
                max_ap = max(max_ap, self.optical_system.image_plane.aperture_radius)
            ax.set_ylim(-max_ap * 1.5, max_ap * 1.5)
        else:
            ax.set_ylim(ylim)
        ax.set_xlabel('Z Position (mm)', fontsize=12)
        ax.set_ylabel('Y Position (mm)', fontsize=12)
        ax.set_title(title or f'{self.optical_system.name} - Optical Layout', fontsize=14)
        ax.grid(True, alpha=0.3)
        ax.set_aspect('equal')
        return ax

    def _plot_ray(self, ax, ray, alpha=0.6):
        if not ray.active:
            return
        color = ray.get_color()
        xs = []
        ys = []
        for pos, dir_ in ray.history:
            xs.append(pos[2])
            ys.append(pos[0])
        if len(xs) >= 2:
            ax.plot(xs, ys, color=color, linewidth=1, alpha=alpha)
        if ray.final_position is not None:
            ax.plot(ray.final_position[2], ray.final_position[0], 'o',
                    color=color, markersize=4, alpha=alpha)

    def _plot_elements(self, ax):
        elements = sorted(self.optical_system.elements, key=lambda e: e.z_position)
        for i, element in enumerate(elements):
            self._plot_element(ax, element)

    def _plot_element(self, ax, element):
        if element.element_type == 'spherical_surface' or \
           element.element_type == 'aspherical_surface':
            self._plot_lens_surface(ax, element)
        elif element.element_type == 'reflective_surface':
            self._plot_mirror(ax, element)
        elif element.element_type == 'aperture_stop':
            self._plot_stop(ax, element)

    def _plot_lens_surface(self, ax, surface):
        r, z = surface.get_edges(num_points=200)
        if hasattr(surface, 'material') and surface.material != 'air':
            if surface.side == 'first':
                next_surfaces = [e for e in self.optical_system.elements
                                if e.z_position > surface.z_position and
                                e.element_type in ['spherical_surface', 'aspherical_surface']]
                if next_surfaces:
                    next_surf = next_surfaces[0]
                    self._fill_lens(ax, surface, next_surf, surface.material)
        ax.plot(z, r, 'k-', linewidth=1.5)

    def _fill_lens(self, ax, surf1, surf2, material):
        r1, z1 = surf1.get_edges(num_points=100)
        r2, z2 = surf2.get_edges(num_points=100)
        z_fill = np.concatenate([z1, z2[::-1]])
        r_fill = np.concatenate([r1, r2[::-1]])
        color_map = {
            'BK7': (0.8, 0.9, 1.0, 0.5),
            'SF11': (0.9, 0.8, 0.8, 0.5),
            'F2': (0.8, 0.85, 0.95, 0.5),
            'BAK1': (0.85, 0.95, 0.85, 0.5),
        }
        color = color_map.get(material, (0.9, 0.9, 0.9, 0.5))
        ax.fill(z_fill, r_fill, color=color, edgecolor='none')

    def _plot_mirror(self, ax, mirror):
        r, z = mirror.get_edges(num_points=200)
        ax.plot(z, r, 'k-', linewidth=2.5)
        for i in range(0, len(r), 10):
            if i >= len(r):
                break
            normal = mirror.get_normal_at(r[i], 0)
            normal[2] = abs(normal[2])
            offset = normal * 1.5
            ax.plot([z[i], z[i] + offset[2]], [r[i], r[i] + offset[0]],
                    'k-', linewidth=0.5, alpha=0.5)

    def _plot_stop(self, ax, stop):
        y_max = stop.aperture_radius
        ax.plot([stop.z_position, stop.z_position], [-y_max - 2, -y_max],
                'k-', linewidth=3)
        ax.plot([stop.z_position, stop.z_position], [y_max, y_max + 2],
                'k-', linewidth=3)
        ax.text(stop.z_position, y_max + 4, 'STOP', ha='center', va='bottom',
                fontsize=9, color='red')

    def plot_spot_diagram(self, spot_data, ax=None, show_centroid=True,
                         show_airy=False, f_number=5, wavelength=0.587):
        if ax is None:
            fig, ax = plt.subplots(figsize=(8, 8))
        max_extent = 0
        all_x = []
        all_y = []
        for wl, positions in spot_data.items():
            if len(positions) == 0:
                continue
            color = self._get_wavelength_color(wl)
            label = self._get_wavelength_label(wl)
            x = positions[:, 0] * 1000
            y = positions[:, 1] * 1000
            all_x.extend(x)
            all_y.extend(y)
            ax.plot(x, y, 'o', color=color, markersize=3, alpha=0.7, label=label)
            if show_centroid:
                cx = np.mean(x)
                cy = np.mean(y)
                ax.plot(cx, cy, '+', color=color, markersize=12, markeredgewidth=2)
            max_extent = max(max_extent, np.max(np.abs(x)), np.max(np.abs(y)))
        if show_airy and all_x:
            airy_radius = 2.44 * f_number * wavelength * 1000 / 2
            circle = Circle((0, 0), airy_radius, fill=False, color='red',
                          linestyle='--', linewidth=1.5,
                          label=f'Airy Disk (r={airy_radius:.1f} μm)')
            ax.add_artist(circle)
        if max_extent < 1:
            max_extent = 10
        ax.set_xlim(-max_extent * 1.2, max_extent * 1.2)
        ax.set_ylim(-max_extent * 1.2, max_extent * 1.2)
        ax.set_aspect('equal')
        ax.set_xlabel('X Position (μm)', fontsize=12)
        ax.set_ylabel('Y Position (μm)', fontsize=12)
        ax.set_title('Spot Diagram', fontsize=14)
        ax.grid(True, alpha=0.3)
        if len(spot_data) > 1:
            ax.legend(loc='best', fontsize=10)
        ax.axvline(0, color='k', linestyle=':', linewidth=0.5)
        ax.axhline(0, color='k', linestyle=':', linewidth=0.5)
        return ax

    def plot_ray_intercept_curve(self, heights, positions, ax=None,
                                  wavelength=0.587):
        if ax is None:
            fig, ax = plt.subplots(figsize=(8, 6))
        color = self._get_wavelength_color(wavelength)
        label = self._get_wavelength_label(wavelength)
        ax.plot(heights, positions * 1000, 'o-', color=color,
               markersize=4, label=label, linewidth=1.5)
        ax.axhline(0, color='k', linestyle='--', linewidth=1)
        ax.set_xlabel('Entrance Pupil Height (mm)', fontsize=12)
        ax.set_ylabel('Image Plane Position (μm)', fontsize=12)
        ax.set_title('Ray Intercept Curve (Transverse Aberration)', fontsize=14)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=10)
        return ax

    def plot_fan_diagram(self, object_height=0.0, wavelengths=None,
                         num_rays=50, max_height=10.0, ax=None):
        if wavelengths is None:
            wavelengths = [0.486, 0.587, 0.656]
        if ax is None:
            fig, ax = plt.subplots(figsize=(10, 6))
        z_min, _ = self.optical_system.get_z_extent()
        initial_z = z_min - 50
        for wl in wavelengths:
            rays = create_ray_bundle(object_height=object_height,
                                    num_rays=num_rays,
                                    max_height=max_height,
                                    wavelength=wl,
                                    initial_z=initial_z,
                                    distribution='meridional')
            if self.ray_tracer is not None:
                traced = self.ray_tracer.trace_rays(rays)
            else:
                traced = rays
            heights = []
            positions = []
            for ray in traced:
                if ray.active and ray.final_position is not None:
                    h = ray.history[0][0]
                    heights.append(h)
                    positions.append(ray.final_position[0] * 1000)
            color = self._get_wavelength_color(wl)
            label = self._get_wavelength_label(wl)
            ax.plot(heights, positions, '-', color=color, linewidth=1.5,
                   label=label)
        ax.axhline(0, color='k', linestyle='--', linewidth=1)
        ax.set_xlabel('Entrance Pupil Height (mm)', fontsize=12)
        ax.set_ylabel('Image Height (μm)', fontsize=12)
        ax.set_title('Meridional Fan Diagram', fontsize=14)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=10)
        return ax

    def plot_distortion_curve(self, object_heights, image_heights, distortion,
                               ax=None, wavelength=0.587):
        if ax is None:
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
            created_fig = True
        else:
            if isinstance(ax, (list, tuple)) and len(ax) >= 2:
                ax1, ax2 = ax[0], ax[1]
            else:
                ax1 = ax
                ax2 = None
            created_fig = False
        color = self._get_wavelength_color(wavelength)
        ax1.plot(object_heights, image_heights, 'o-', color=color,
                markersize=5, linewidth=1.5, label='Actual')
        if len(object_heights) > 1:
            ideal = (image_heights[-1] / object_heights[-1]) * object_heights
            ax1.plot(object_heights, ideal, 'k--', linewidth=1, label='Ideal')
        ax1.set_xlabel('Object Height (mm)', fontsize=12)
        ax1.set_ylabel('Image Height (mm)', fontsize=12)
        ax1.set_title('Distortion - Image Height', fontsize=14)
        ax1.grid(True, alpha=0.3)
        ax1.legend(fontsize=10)
        if ax2 is not None:
            ax2.plot(object_heights, distortion, 'o-', color=color,
                    markersize=5, linewidth=1.5)
            ax2.axhline(0, color='k', linestyle='--', linewidth=1)
            ax2.set_xlabel('Object Height (mm)', fontsize=12)
            ax2.set_ylabel('Distortion (%)', fontsize=12)
            ax2.set_title('Distortion (%)', fontsize=14)
            ax2.grid(True, alpha=0.3)
        return (ax1, ax2) if ax2 is not None else ax1

    def plot_mtf_curve(self, spatial_freq, mtf_values, ax=None,
                        wavelength=0.587):
        if ax is None:
            fig, ax = plt.subplots(figsize=(10, 6))
        color = self._get_wavelength_color(wavelength)
        label = self._get_wavelength_label(wavelength)
        ax.plot(spatial_freq, mtf_values, color=color, linewidth=2,
               label=label)
        ax.set_xlabel('Spatial Frequency (lp/mm)', fontsize=12)
        ax.set_ylabel('MTF', fontsize=12)
        ax.set_title('Modulation Transfer Function', fontsize=14)
        ax.set_ylim(0, 1.05)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=10)
        return ax

    def plot_field_curvature(self, field_angles, best_zs, ax=None):
        if ax is None:
            fig, ax = plt.subplots(figsize=(8, 6))
        ax.plot(field_angles, best_zs - np.mean(best_zs), 'o-',
               linewidth=2, markersize=5)
        ax.axhline(0, color='k', linestyle='--', linewidth=1)
        ax.set_xlabel('Field Angle (deg)', fontsize=12)
        ax.set_ylabel('Best Focus Position (mm)', fontsize=12)
        ax.set_title('Field Curvature', fontsize=14)
        ax.grid(True, alpha=0.3)
        return ax

    def plot_chromatic_focus_shift(self, wavelengths=None, num_points=15,
                                    ax=None):
        if wavelengths is None:
            from optical_constants import DEFAULT_WAVELENGTHS_VISIBLE
            wavelengths = DEFAULT_WAVELENGTHS_VISIBLE
        if ax is None:
            fig, ax = plt.subplots(figsize=(10, 6))
        z_min, z_max = self.optical_system.get_z_extent()
        best_zs = []
        for wl in wavelengths:
            best_z, _, _, _ = self.ray_tracer.find_best_image_plane(
                wavelength=wl, z_min=z_max + 10, z_max=z_max + 200,
                num_points=20, max_height=10.0, num_rays=11)
            best_zs.append(best_z)
        best_zs = np.array(best_zs)
        ax.plot(wavelengths * 1000, best_zs - np.mean(best_zs), 'o-',
               linewidth=2, markersize=4, color='gray', alpha=0.7)
        for wl in wavelengths:
            color = self._get_wavelength_color(wl)
            idx = np.argmin(np.abs(wavelengths - wl))
            ax.plot(wl * 1000, best_zs[idx] - np.mean(best_zs), 'o',
                   color=color, markersize=8,
                   label=self._get_wavelength_label(wl))
        ax.set_xlabel('Wavelength (nm)', fontsize=12)
        ax.set_ylabel('Focus Shift (mm)', fontsize=12)
        ax.set_title('Chromatic Focus Shift', fontsize=14)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=10, loc='best')
        return ax

    def plot_secondary_spectrum(self, secondary_data, ax=None):
        if ax is None:
            fig, ax = plt.subplots(figsize=(10, 6))
        wls = secondary_data['wavelengths'] * 1000
        focus_pos = secondary_data['focus_positions']
        achromatic = secondary_data['achromatic_line']
        secondary_spec = secondary_data['secondary_spectrum']
        ax.plot(wls, focus_pos, 'o-', color='blue', linewidth=2,
               markersize=6, label='Actual Focus')
        ax.plot(wls, achromatic, '--', color='red', linewidth=2,
               label='Achromatic Line (F-C)')
        for i, wl in enumerate(secondary_data['wavelengths']):
            color = self._get_wavelength_color(wl)
            ax.plot(wl * 1000, focus_pos[i], 'o', color=color, markersize=10)
        ax.set_xlabel('Wavelength (nm)', fontsize=12)
        ax.set_ylabel('Focus Position (mm)', fontsize=12)
        ax.set_title('Secondary Spectrum Analysis', fontsize=14)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=10)
        ax2 = ax.twinx()
        ax2.plot(wls, secondary_spec * 1000, 's-', color='green',
                linewidth=2, markersize=5, label='Deviation')
        ax2.axhline(0, color='gray', linestyle=':', linewidth=1)
        ax2.set_ylabel('Deviation from Achromatic (μm)', fontsize=12, color='green')
        ax2.tick_params(axis='y', labelcolor='green')
        return ax, ax2

    def plot_chromatic_aberration_summary(self, lca_data, max_height=10.0, ax=None):
        if ax is None:
            fig, ax = plt.subplots(figsize=(12, 6))
        wavelengths = sorted(lca_data.keys())
        heights = np.linspace(-max_height, max_height, 100)
        for wl in wavelengths:
            color = self._get_wavelength_color(wl)
            label = self._get_wavelength_label(wl)
            ax.plot(heights, lca_data[wl] * np.ones_like(heights),
                   color=color, linewidth=2, label=label)
        ax.set_xlabel('Ray Height (mm)', fontsize=12)
        ax.set_ylabel('Image Position (mm)', fontsize=12)
        ax.set_title('Longitudinal Chromatic Aberration', fontsize=14)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=10)
        return ax

    def _get_wavelength_color(self, wavelength):
        wls = sorted(WAVELENGTH_COLORS.keys())
        closest = min(wls, key=lambda w: abs(w - wavelength))
        return WAVELENGTH_COLORS[closest]

    def _get_wavelength_label(self, wavelength):
        wls = sorted(WAVELENGTH_NAMES.keys())
        closest = min(wls, key=lambda w: abs(w - wavelength))
        return WAVELENGTH_NAMES[closest]

    def create_comprehensive_report(self, object_height=0.0, max_height=10.0,
                                     wavelengths=None, filename=None):
        if wavelengths is None:
            wavelengths = [0.486, 0.587, 0.656]
        fig = plt.figure(figsize=(16, 12))
        gs = fig.add_gridspec(3, 2, hspace=0.3, wspace=0.3)
        ax1 = fig.add_subplot(gs[0, :])
        self.plot_optical_layout(ax=ax1, wavelength=0.587,
                                max_height=max_height,
                                object_height=object_height,
                                num_rays=15)
        from ray_tracer import ImageAnalysis
        analysis = ImageAnalysis(self.optical_system, self.ray_tracer)
        ax2 = fig.add_subplot(gs[1, 0])
        spot_data = analysis.get_spot_diagram(object_height=object_height,
                                             wavelengths=wavelengths,
                                             max_height=max_height)
        self.plot_spot_diagram(spot_data, ax=ax2)
        ax3 = fig.add_subplot(gs[1, 1])
        self.plot_fan_diagram(object_height=object_height,
                             wavelengths=wavelengths,
                             max_height=max_height, ax=ax3)
        ax4 = fig.add_subplot(gs[2, 0])
        obj_h, img_h, dist = analysis.calculate_distortion(
            wavelength=0.587, max_height=max_height)
        result = self.plot_distortion_curve(obj_h, img_h, dist, ax=(ax4, None))
        if isinstance(result, tuple):
            ax4_dist = result[0]
        else:
            ax4_dist = result
        ax5 = fig.add_subplot(gs[2, 1])
        sf, mtf = analysis.calculate_mtf(wavelength=0.587,
                                        max_height=max_height)
        self.plot_mtf_curve(sf, mtf, ax=ax5)
        fig.suptitle(f'{self.optical_system.name} - Performance Analysis',
                    fontsize=16, y=0.995)
        if filename:
            plt.savefig(filename, dpi=150, bbox_inches='tight')
        return fig

    def plot_psf(self, psf, line_profile=None, ax=None, log_scale=False):
        if ax is None:
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
        else:
            ax1 = ax[0] if isinstance(ax, (list, tuple)) else ax
            ax2 = None
        if log_scale:
            psf_display = np.log10(psf + 1e-10)
        else:
            psf_display = psf
        im = ax1.imshow(psf_display, cmap='hot', origin='lower')
        ax1.set_title('Point Spread Function (PSF)', fontsize=14)
        ax1.set_xlabel('Pixel X', fontsize=12)
        ax1.set_ylabel('Pixel Y', fontsize=12)
        plt.colorbar(im, ax=ax1, label='Intensity (log)' if log_scale else 'Intensity')
        if line_profile is not None and ax2 is not None:
            ax2.plot(line_profile, 'b-', linewidth=2)
            ax2.set_xlabel('Pixel', fontsize=12)
            ax2.set_ylabel('Intensity', fontsize=12)
            ax2.set_title('PSF Line Profile', fontsize=14)
            ax2.grid(True, alpha=0.3)
            half = len(line_profile) // 2
            fwhm_idx = np.where(line_profile > line_profile.max() / 2)[0]
            if len(fwhm_idx) > 1:
                fwhm = fwhm_idx[-1] - fwhm_idx[0]
                ax2.axhline(line_profile.max() / 2, color='r', linestyle='--',
                           label=f'FWHM = {fwhm} pixels')
                ax2.legend(fontsize=10)
        return (ax1, ax2) if ax2 else ax1

    def plot_mtf_comparison(self, spatial_freqs, mtf_geometric=None,
                             mtf_diffraction=None, mtf_diffraction_limited=None,
                             ax=None):
        if ax is None:
            fig, ax = plt.subplots(figsize=(10, 6))
        if mtf_geometric is not None:
            ax.plot(spatial_freqs, mtf_geometric, 'b-o', linewidth=2,
                   markersize=4, label='Geometric MTF')
        if mtf_diffraction is not None:
            ax.plot(spatial_freqs, mtf_diffraction, 'r-s', linewidth=2,
                   markersize=4, label='Diffraction MTF')
        if mtf_diffraction_limited is not None:
            ax.plot(spatial_freqs, mtf_diffraction_limited, 'g--', linewidth=2,
                   label='Diffraction Limited')
        ax.axhline(0.5, color='k', linestyle=':', alpha=0.5, label='50% Contrast')
        ax.set_xlabel('Spatial Frequency (lp/mm)', fontsize=12)
        ax.set_ylabel('MTF', fontsize=12)
        ax.set_title('Modulation Transfer Function Comparison', fontsize=14)
        ax.set_ylim(0, 1.05)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=10)
        return ax

    def plot_optimization_convergence(self, optimizer, ax=None):
        if ax is None:
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
        else:
            ax1 = ax[0] if isinstance(ax, (list, tuple)) else ax
            ax2 = None
        optimizer.plot_convergence(ax=ax1)
        if ax2 is not None:
            optimizer.compare_before_after(ax=ax2)
            plt.tight_layout()
        return (ax1, ax2) if ax2 else ax1

    def plot_ghost_rays(self, ghost_rays, ax=None, show_legend=True):
        if ax is None:
            fig, ax = plt.subplots(figsize=(12, 6))
        self._plot_elements(ax)
        for ray in ghost_rays:
            if len(ray.history) < 2:
                continue
            xs = []
            ys = []
            for pos, dir_ in ray.history:
                xs.append(pos[2])
                ys.append(pos[0])
            intensity = min(ray.intensity, 1.0)
            alpha = 0.3 + 0.7 * intensity
            ax.plot(xs, ys, 'r--', linewidth=1 + intensity, alpha=alpha,
                   label='Ghost Ray' if show_legend else None)
            show_legend = False
        ax.set_xlabel('Z Position (mm)', fontsize=12)
        ax.set_ylabel('Y Position (mm)', fontsize=12)
        ax.set_title('Ghost Ray Paths', fontsize=14)
        ax.grid(True, alpha=0.3)
        ax.legend()
        return ax

    def plot_stray_light_analysis(self, stray_intensity, detector_hits=None, ax=None):
        if ax is None:
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
        else:
            ax1 = ax[0] if isinstance(ax, (list, tuple)) else ax
            ax2 = None
        categories = ['Direct Signal', 'Ghost Light', 'Stray Light']
        direct = stray_intensity['total'] - stray_intensity['ghost'] - stray_intensity['stray']
        intensities = [direct, stray_intensity['ghost'], stray_intensity['stray']]
        colors = ['green', 'red', 'orange']
        ax1.bar(categories, intensities, color=colors, alpha=0.7)
        ax1.set_ylabel('Total Intensity', fontsize=12)
        ax1.set_title('Stray Light Analysis', fontsize=14)
        ax1.grid(True, alpha=0.3, axis='y')
        for i, v in enumerate(intensities):
            ax1.text(i, v, f'{v:.3f}', ha='center', va='bottom')
        if ax2 is not None and detector_hits is not None and len(detector_hits) > 0:
            positions = np.array([h['position'] for h in detector_hits])
            intensities = np.array([h['intensity'] for h in detector_hits])
            is_ghost = np.array([h['is_ghost'] for h in detector_hits])
            is_stray = np.array([h['is_stray'] for h in detector_hits])
            direct_mask = ~is_ghost & ~is_stray
            if np.any(direct_mask):
                ax2.scatter(positions[direct_mask, 0], positions[direct_mask, 1],
                           c='green', s=intensities[direct_mask]*100, alpha=0.6,
                           label='Direct Signal')
            if np.any(is_ghost):
                ax2.scatter(positions[is_ghost, 0], positions[is_ghost, 1],
                           c='red', s=intensities[is_ghost]*100, alpha=0.6,
                           label='Ghost Light')
            if np.any(is_stray):
                ax2.scatter(positions[is_stray, 0], positions[is_stray, 1],
                           c='orange', s=intensities[is_stray]*100, alpha=0.6,
                           label='Stray Light')
            ax2.set_xlabel('X Position (mm)', fontsize=12)
            ax2.set_ylabel('Y Position (mm)', fontsize=12)
            ax2.set_title('Detector Illumination Pattern', fontsize=14)
            ax2.grid(True, alpha=0.3)
            ax2.legend()
            ax2.set_aspect('equal')
        return (ax1, ax2) if ax2 else ax1

    def create_diffraction_report(self, object_height=0.0, wavelength=0.587,
                                   max_height=10.0, f_number=3.0,
                                   filename=None):
        from diffraction import DiffractionPSF
        psf_calc = DiffractionPSF(self.optical_system, self.ray_tracer)
        fig = plt.figure(figsize=(16, 12))
        gs = fig.add_gridspec(3, 2, hspace=0.3, wspace=0.3)
        ax1 = fig.add_subplot(gs[0, 0])
        psf, line_profile = psf_calc.calculate_psf_fft(
            object_height=object_height, wavelength=wavelength,
            max_height=max_height, num_rays=100, psf_size=128)
        self.plot_psf(psf, line_profile, ax=(ax1, None))
        ax2 = fig.add_subplot(gs[0, 1])
        strehl = psf_calc.calculate_strehl_ratio(
            object_height=object_height, wavelength=wavelength,
            max_height=max_height, num_rays=100)
        airy_radius = psf_calc.calculate_airy_disk_radius(wavelength=wavelength,
                                                          f_number=f_number)
        ax2.text(0.1, 0.9, f'Strehl Ratio: {strehl:.3f}', transform=ax2.transAxes,
                fontsize=12, bbox=dict(facecolor='white', alpha=0.8))
        ax2.text(0.1, 0.8, f'Airy Radius: {airy_radius*1000:.2f} μm',
                transform=ax2.transAxes, fontsize=12,
                bbox=dict(facecolor='white', alpha=0.8))
        ax2.text(0.1, 0.7, f'f/#: {f_number:.2f}', transform=ax2.transAxes,
                fontsize=12, bbox=dict(facecolor='white', alpha=0.8))
        ax2.axis('off')
        ax2.set_title('Diffraction Performance', fontsize=14)
        ax3 = fig.add_subplot(gs[1, :])
        sf = np.linspace(0, 100, 50)
        _, mtf_geom = psf_calc.calculate_mtf(
            object_height=object_height, wavelength=wavelength,
            max_height=max_height, spatial_frequencies=sf, method='geometric')
        _, mtf_diff = psf_calc.calculate_mtf(
            object_height=object_height, wavelength=wavelength,
            max_height=max_height, spatial_frequencies=sf, method='diffraction')
        _, mtf_lim = psf_calc.calculate_diffraction_limited_mtf(
            sf, wavelength=wavelength, f_number=f_number)
        self.plot_mtf_comparison(sf, mtf_geom, mtf_diff, mtf_lim, ax=ax3)
        ax4 = fig.add_subplot(gs[2, :])
        self.plot_optical_layout(ax=ax4, wavelength=wavelength,
                                max_height=max_height,
                                object_height=object_height, num_rays=15)
        fig.suptitle(f'Diffraction Analysis - {wavelength*1000:.0f}nm',
                    fontsize=16, y=0.995)
        if filename:
            plt.savefig(filename, dpi=150, bbox_inches='tight')
        return fig
