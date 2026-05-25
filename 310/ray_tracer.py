import numpy as np
from copy import deepcopy
from ray import Ray, create_ray_bundle, create_collimated_rays
from optical_constants import refractive_index


class RayTracer:
    def __init__(self, optical_system):
        self.optical_system = optical_system
        self.traced_rays = []

    def trace_ray(self, ray, keep_history=True):
        ray = deepcopy(ray)
        elements = self.optical_system.get_sorted_elements()
        for element in elements:
            if not ray.active:
                break
            element.interact(ray)
        return ray

    def trace_rays(self, rays, keep_history=True):
        traced = []
        for ray in rays:
            traced.append(self.trace_ray(ray, keep_history))
        self.traced_rays.extend(traced)
        return traced

    def trace_rays_parallel(self, rays, keep_history=True):
        return self.trace_rays(rays, keep_history)

    def get_focal_length(self, wavelength=0.587, max_height=1.0, z_start=-1000.0):
        elements = self.optical_system.elements
        if not elements:
            return None
        rays = create_collimated_rays(object_height=0.0, num_rays=3,
                                     max_height=max_height,
                                     wavelength=wavelength,
                                     initial_z=z_start)
        traced = self.trace_rays(rays)
        active_rays = [r for r in traced if r.active and r.final_position is not None]
        if len(active_rays) < 2:
            return None
        z1, z2 = None, None
        for i in range(len(active_rays[0].history) - 1):
            p1_a, d1_a = active_rays[0].history[i]
            p2_a, d2_a = active_rays[0].history[i + 1]
            p1_b, d1_b = active_rays[1].history[i]
            p2_b, d2_b = active_rays[1].history[i + 1]
            if abs(d1_a[2]) < 1e-12 or abs(d1_b[2]) < 1e-12:
                continue
            x1_a, x2_a = p1_a[0], p2_a[0]
            z1_a, z2_a = p1_a[2], p2_a[2]
            k_a = (x2_a - x1_a) / (z2_a - z1_a) if abs(z2_a - z1_a) > 1e-12 else 0
            x1_b, x2_b = p1_b[0], p2_b[0]
            z1_b, z2_b = p1_b[2], p2_b[2]
            k_b = (x2_b - x1_b) / (z2_b - z1_b) if abs(z2_b - z1_b) > 1e-12 else 0
            if abs(k_a - k_b) < 1e-12:
                continue
            z_intersect = (x1_b - x1_a + k_a * z1_a - k_b * z1_b) / (k_a - k_b)
            x_intersect = x1_a + k_a * (z_intersect - z1_a)
            if (z1_a <= z_intersect <= z2_a or z2_a <= z_intersect <= z1_a) and \
               (z1_b <= z_intersect <= z2_b or z2_b <= z_intersect <= z1_b):
                return z_intersect
        return None

    def find_best_image_plane(self, wavelength=0.587, z_min=None, z_max=None,
                              num_points=30, object_height=0.0,
                              max_height=10.0, num_rays=11):
        z_min_e, z_max_e = self.optical_system.get_z_extent()
        if z_min is None:
            z_min = z_max_e + 10
        if z_max is None:
            z_max = z_max_e + 200
        z_positions = np.linspace(z_min, z_max, num_points)
        rms_values = []
        for z in z_positions:
            self.optical_system.set_image_plane(z, size=50)
            rays = create_ray_bundle(object_height=object_height, num_rays=num_rays,
                                    max_height=max_height, wavelength=wavelength,
                                    initial_z=z_min_e - 50, distribution='meridional')
            traced = self.trace_rays(rays)
            positions = []
            for ray in traced:
                if ray.active and ray.final_position is not None:
                    positions.append(ray.final_position[:2])
            if len(positions) < 2:
                rms_values.append(float('inf'))
                continue
            positions = np.array(positions)
            centroid = np.mean(positions, axis=0)
            rms = np.sqrt(np.mean(np.sum((positions - centroid)**2, axis=1)))
            rms_values.append(rms)
        rms_values = np.array(rms_values)
        best_idx = np.argmin(rms_values)
        best_z = z_positions[best_idx]
        return best_z, rms_values[best_idx], z_positions, rms_values


class ImageAnalysis:
    def __init__(self, optical_system, ray_tracer=None):
        self.optical_system = optical_system
        self.ray_tracer = ray_tracer or RayTracer(optical_system)

    def get_spot_diagram(self, object_height=0.0, wavelengths=None,
                         num_rays=100, max_height=10.0,
                         initial_z=None):
        if wavelengths is None:
            wavelengths = [0.486, 0.587, 0.656]
        if initial_z is None:
            z_min, _ = self.optical_system.get_z_extent()
            initial_z = z_min - 50
        results = {}
        for wl in wavelengths:
            rays = create_ray_bundle(object_height=object_height,
                                    num_rays=num_rays,
                                    max_height=max_height,
                                    wavelength=wl,
                                    initial_z=initial_z,
                                    distribution='radial')
            traced = self.ray_tracer.trace_rays(rays)
            positions = []
            for ray in traced:
                if ray.active and ray.final_position is not None:
                    positions.append(ray.final_position[:2].copy())
            results[wl] = np.array(positions) if positions else np.array([])
        return results

    def calculate_rms_spot_size(self, spot_data, wavelength=None):
        if wavelength is not None:
            if wavelength not in spot_data or len(spot_data[wavelength]) == 0:
                return 0.0
            positions = spot_data[wavelength]
            if positions.ndim == 1:
                positions = positions.reshape(-1, 2)
            centroid = np.mean(positions, axis=0)
            rms = np.sqrt(np.mean(np.sum((positions - centroid)**2, axis=1)))
            return rms
        total = 0.0
        count = 0
        for wl, positions in spot_data.items():
            if len(positions) == 0:
                continue
            if positions.ndim == 1:
                positions = positions.reshape(-1, 2)
            centroid = np.mean(positions, axis=0)
            rms = np.sqrt(np.mean(np.sum((positions - centroid)**2, axis=1)))
            total += rms
            count += 1
        return total / count if count > 0 else 0.0

    def calculate_geometric_aberration(self, object_height=0.0,
                                      max_height=10.0,
                                      wavelength=0.587, num_rays=50):
        z_min, _ = self.optical_system.get_z_extent()
        initial_z = z_min - 50
        rays = create_ray_bundle(object_height=object_height,
                                num_rays=num_rays,
                                max_height=max_height,
                                wavelength=wavelength,
                                initial_z=initial_z,
                                distribution='meridional')
        traced = self.ray_tracer.trace_rays(rays)
        positions = []
        heights = []
        for ray in traced:
            if not ray.active or ray.final_position is None:
                continue
            h = ray.history[0][0]
            positions.append(ray.final_position[0])
            heights.append(h)
        if not positions:
            return None, None
        return np.array(heights), np.array(positions)

    def calculate_spherical_aberration(self, max_height=10.0,
                                         wavelength=0.587, num_rays=50):
        heights, positions = self.calculate_geometric_aberration(
            object_height=0.0, max_height=max_height,
            wavelength=wavelength, num_rays=num_rays)
        if heights is None:
            return None
        marginal_ray_idx = np.argmax(np.abs(heights))
        paraxial_indices = np.where(np.abs(heights) < max_height * 0.1)[0]
        if len(paraxial_indices) == 0:
            return None
        marginal_pos = positions[marginal_ray_idx]
        paraxial_pos = np.mean(positions[paraxial_indices])
        sa = marginal_pos - paraxial_pos
        return sa

    def calculate_chromatic_aberration(self, wavelengths=None,
                                          max_height=0.1, num_rays=21):
        if wavelengths is None:
            wavelengths = [0.486, 0.656]
        z_min, _ = self.optical_system.get_z_extent()
        initial_z = z_min - 50
        positions_by_wl = {}
        for wl in wavelengths:
            rays = create_ray_bundle(object_height=0.0,
                                    num_rays=num_rays,
                                    max_height=max_height,
                                    wavelength=wl,
                                    initial_z=initial_z,
                                    distribution='meridional')
            traced = self.ray_tracer.trace_rays(rays)
            positions = []
            for ray in traced:
                if ray.active and ray.final_position is not None:
                    positions.append(ray.final_position[0])
            positions_by_wl[wl] = np.mean(positions) if positions else 0
        if len(wavelengths) >= 2:
            return abs(positions_by_wl[wavelengths[1]] - positions_by_wl[wavelengths[0]])
        return 0.0

    def calculate_distortion(self, object_heights=None, max_height=10.0,
                              wavelength=0.587, num_rays=11):
        if object_heights is None:
            object_heights = [0, 2, 5, 8, 10]
        z_min, _ = self.optical_system.get_z_extent()
        initial_z = z_min - 50
        image_heights = []
        for oh in object_heights:
            rays = create_ray_bundle(object_height=oh,
                                    num_rays=num_rays,
                                    max_height=max_height * 0.1,
                                    wavelength=wavelength,
                                    initial_z=initial_z,
                                    distribution='meridional')
            traced = self.ray_tracer.trace_rays(rays)
            positions = []
            for ray in traced:
                if ray.active and ray.final_position is not None:
                    positions.append(ray.final_position[0])
            if positions:
                image_heights.append(np.mean(positions))
            else:
                image_heights.append(0)
        object_heights = np.array(object_heights)
        image_heights = np.array(image_heights)
        if len(object_heights) < 2:
            return object_heights, image_heights, np.zeros_like(image_heights)
        ideal_image = np.zeros_like(object_heights, dtype=float)
        valid = object_heights != 0
        if np.any(valid) and object_heights[-1] != 0:
            scale = image_heights[-1] / object_heights[-1]
            ideal_image[valid] = scale * object_heights[valid]
        distortion = np.zeros_like(ideal_image)
        valid_ideal = ideal_image != 0
        distortion[valid_ideal] = (image_heights[valid_ideal] - ideal_image[valid_ideal]) / ideal_image[valid_ideal] * 100
        return object_heights, image_heights, distortion

    def calculate_field_curvature(self, field_angles=None, max_height=10.0,
                                    wavelength=0.587, num_rays=21):
        if field_angles is None:
            field_angles = [0, 5, 10, 15, 20]
        z_min, z_max = self.optical_system.get_z_extent()
        initial_z = z_min - 50
        best_zs = []
        rms_vals = []
        for angle in field_angles:
            angle_rad = np.deg2rad(angle)
            object_height = np.tan(angle_rad) * 50
            best_z, best_rms, _, _ = self.ray_tracer.find_best_image_plane(
                wavelength=wavelength, z_min=z_max + 10, z_max=z_max + 200,
                num_points=50, object_height=object_height,
                max_height=max_height, num_rays=num_rays)
            best_zs.append(best_z)
            rms_vals.append(best_rms)
        return np.array(field_angles), np.array(best_zs), np.array(rms_vals)

    def calculate_mtf(self, spatial_frequencies=None, max_height=10.0,
                  wavelength=0.587, num_rays=200):
        if spatial_frequencies is None:
            spatial_frequencies = np.linspace(0, 100, 20)
        spot_data = self.get_spot_diagram(
            object_height=0.0, wavelengths=[wavelength],
            num_rays=num_rays, max_height=max_height)
        if wavelength not in spot_data or len(spot_data[wavelength]) == 0:
            return spatial_frequencies, np.zeros_like(spatial_frequencies)
        positions = spot_data[wavelength]
        mtf_values = []
        for freq in spatial_frequencies:
            if freq == 0:
                mtf_values.append(1.0)
                continue
            phase = 2 * np.pi * freq * positions[:, 0] / 1000
            otf = np.mean(np.exp(-1j * phase))
            mtf_values.append(np.abs(otf))
        return spatial_frequencies, np.array(mtf_values)

    def calculate_longitudinal_chromatic_aberration(self, wavelength1=0.486,
                                                     wavelength2=0.656,
                                                     reference_wavelength=0.587,
                                                     max_height=0.1, num_rays=11):
        z_min, z_max = self.optical_system.get_z_extent()
        z_search_min = z_max + 10
        z_search_max = z_max + 200
        positions = {}
        for wl in [wavelength1, wavelength2, reference_wavelength]:
            best_z, _, _, _ = self.ray_tracer.find_best_image_plane(
                wavelength=wl, z_min=z_search_min, z_max=z_search_max,
                num_points=30, object_height=0.0,
                max_height=max_height, num_rays=num_rays)
            positions[wl] = best_z
        lca = abs(positions[wavelength2] - positions[wavelength1])
        return lca, positions

    def calculate_lateral_chromatic_aberration(self, wavelength1=0.486,
                                                wavelength2=0.656,
                                                object_height=10.0,
                                                max_height=0.1, num_rays=11):
        z_min, _ = self.optical_system.get_z_extent()
        initial_z = z_min - 50
        image_heights = {}
        for wl in [wavelength1, wavelength2]:
            rays = create_ray_bundle(object_height=object_height,
                                    num_rays=num_rays,
                                    max_height=max_height,
                                    wavelength=wl,
                                    initial_z=initial_z,
                                    distribution='meridional')
            traced = self.ray_tracer.trace_rays(rays)
            pos = [ray.final_position[0] for ray in traced
                   if ray.active and ray.final_position is not None]
            image_heights[wl] = np.mean(pos) if pos else 0
        lca_lateral = abs(image_heights[wavelength2] - image_heights[wavelength1])
        return lca_lateral, image_heights

    def calculate_secondary_spectrum(self, wavelengths=None,
                                      reference_wavelength=0.587,
                                      max_height=0.1, num_rays=11):
        if wavelengths is None:
            from optical_constants import DEFAULT_WAVELENGTHS_VISIBLE
            wavelengths = DEFAULT_WAVELENGTHS_VISIBLE
        z_min, z_max = self.optical_system.get_z_extent()
        z_search_min = z_max + 10
        z_search_max = z_max + 200
        positions = {}
        for wl in wavelengths:
            best_z, _, _, _ = self.ray_tracer.find_best_image_plane(
                wavelength=wl, z_min=z_search_min, z_max=z_search_max,
                num_points=30, object_height=0.0,
                max_height=max_height, num_rays=num_rays)
            positions[wl] = best_z
        sorted_wls = sorted(wavelengths)
        sorted_positions = np.array([positions[wl] for wl in sorted_wls])
        f_pos = positions.get(0.486, sorted_positions[0])
        c_pos = positions.get(0.656, sorted_positions[-1])
        achromatic_slope = (c_pos - f_pos) / (0.656 - 0.486) if abs(0.656 - 0.486) > 1e-12 else 0
        achromatic_line = f_pos + achromatic_slope * (np.array(sorted_wls) - 0.486)
        secondary_spectrum = sorted_positions - achromatic_line
        d_deviation = positions.get(reference_wavelength, 0) - (f_pos + achromatic_slope * (reference_wavelength - 0.486))
        return {
            'wavelengths': np.array(sorted_wls),
            'focus_positions': sorted_positions,
            'achromatic_line': achromatic_line,
            'secondary_spectrum': secondary_spectrum,
            'd_line_deviation': d_deviation,
            'max_deviation': np.max(np.abs(secondary_spectrum))
        }

    def calculate_chromatic_focus_shift(self, wavelengths=None,
                                        max_height=10.0, num_rays=11):
        if wavelengths is None:
            from optical_constants import DEFAULT_WAVELENGTHS_VISIBLE
            wavelengths = DEFAULT_WAVELENGTHS_VISIBLE
        z_min, z_max = self.optical_system.get_z_extent()
        best_zs = []
        for wl in wavelengths:
            best_z, best_rms, _, _ = self.ray_tracer.find_best_image_plane(
                wavelength=wl, z_min=z_max + 10, z_max=z_max + 200,
                num_points=20, object_height=0.0,
                max_height=max_height, num_rays=num_rays)
            best_zs.append(best_z)
        return np.array(wavelengths), np.array(best_zs)

    def calculate_achromatic_performance(self, max_height=0.1, num_rays=11):
        from optical_constants import DEFAULT_WAVELENGTHS_ABERRATION
        wl_F, wl_d, wl_C = DEFAULT_WAVELENGTHS_ABERRATION
        lca, positions = self.calculate_longitudinal_chromatic_aberration(
            wavelength1=wl_F, wavelength2=wl_C, reference_wavelength=wl_d,
            max_height=max_height, num_rays=num_rays)
        secondary = self.calculate_secondary_spectrum(
            max_height=max_height, num_rays=num_rays)
        return {
            'axial_chromatic_aberration_FC': lca,
            'focus_position_F': positions[wl_F],
            'focus_position_d': positions[wl_d],
            'focus_position_C': positions[wl_C],
            'secondary_spectrum_dF': positions[wl_d] - positions[wl_F],
            'secondary_spectrum_dC': positions[wl_d] - positions[wl_C],
            'd_line_deviation': secondary['d_line_deviation'],
            'max_secondary_spectrum': secondary['max_deviation']
        }

    def generate_report(self, wavelength=0.587, full_chromatic=False):
        from optical_constants import DEFAULT_WAVELENGTHS_ABERRATION
        report = {}
        report['spherical_aberration'] = self.calculate_spherical_aberration(
            wavelength=wavelength)
        if full_chromatic:
            achro_perf = self.calculate_achromatic_performance()
            report.update(achro_perf)
            report['chromatic_aberration'] = achro_perf['axial_chromatic_aberration_FC']
            secondary = self.calculate_secondary_spectrum()
            report['secondary_spectrum'] = secondary
        else:
            report['chromatic_aberration'] = self.calculate_chromatic_aberration(
                wavelengths=DEFAULT_WAVELENGTHS_ABERRATION)
        spot_data = self.get_spot_diagram(wavelengths=[wavelength])
        report['rms_spot_size'] = self.calculate_rms_spot_size(spot_data, wavelength)
        _, _, distortion = self.calculate_distortion(wavelength=wavelength)
        report['max_distortion'] = np.max(np.abs(distortion)) if len(distortion) > 0 else 0
        return report
