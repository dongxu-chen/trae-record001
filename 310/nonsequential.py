import numpy as np
from copy import deepcopy
from ray import Ray
from optical_constants import refractive_index
from optical_elements import OpticalElement


class NonSequentialRay(Ray):
    def __init__(self, position, direction, wavelength=0.587,
                 intensity=1.0, origin=None, max_bounces=10):
        super().__init__(position, direction, wavelength, intensity, origin)
        self.max_bounces = max_bounces
        self.bounce_count = 0
        self.interaction_history = []
        self.optical_path = 0.0
        self.is_ghost = False
        self.is_stray = False

    def copy(self):
        new_ray = NonSequentialRay(self.position.copy(), self.direction.copy(),
                                   self.wavelength, self.intensity, self.origin,
                                   self.max_bounces)
        new_ray.history = [(p.copy(), d.copy()) for p, d in self.history]
        new_ray.active = self.active
        new_ray.elements_hit = self.elements_hit.copy()
        new_ray.final_position = self.final_position.copy() if self.final_position is not None else None
        new_ray.total_internal_reflection = self.total_internal_reflection
        new_ray.reflection_events = self.reflection_events.copy()
        new_ray.bounce_count = self.bounce_count
        new_ray.interaction_history = self.interaction_history.copy()
        new_ray.optical_path = self.optical_path
        new_ray.is_ghost = self.is_ghost
        new_ray.is_stray = self.is_stray
        return new_ray

    def interact_with_surface(self, element, normal, n1, n2, reflectivity=0.0,
                              transmission=1.0):
        if not self.active:
            return None, None
        if self.bounce_count >= self.max_bounces:
            self.active = False
            return None, None
        normal = np.array(normal, dtype=float)
        normal = normal / np.linalg.norm(normal)
        if np.dot(self.direction, normal) > 0:
            normal = -normal
        cos_theta = -np.dot(self.direction, normal)
        cos_theta = np.clip(cos_theta, 0.0, 1.0)
        sin_theta_sq = max(0.0, 1 - cos_theta ** 2)
        n_ratio = n1 / n2
        sin_theta2_sq = n_ratio ** 2 * sin_theta_sq
        results = []
        if sin_theta2_sq >= 1.0 - 1e-10:
            self.total_internal_reflection = True
            reflected_ray = self._create_reflected(normal, self.intensity, element)
            self.reflection_events.append({
                'position': self.position.copy(),
                'wavelength': self.wavelength,
                'type': 'total_internal_reflection',
                'n1': float(n1),
                'n2': float(n2),
                'incident_angle': float(np.arcsin(np.sqrt(sin_theta_sq)) * 180 / np.pi)
            })
            results.append(('reflect', reflected_ray))
        else:
            if reflectivity > 0:
                reflected_intensity = self.intensity * reflectivity
                if reflected_intensity > 1e-6:
                    reflected_ray = self._create_reflected(
                        normal, reflected_intensity, element)
                    reflected_ray.is_ghost = True
                    results.append(('reflect', reflected_ray))
            if transmission > 0:
                transmitted_intensity = self.intensity * transmission
                if transmitted_intensity > 1e-6:
                    transmitted_ray = self._create_refracted(
                        normal, n1, n2, transmitted_intensity, element,
                        sin_theta2_sq, cos_theta)
                    results.append(('refract', transmitted_ray))
        self.intensity = 0
        self.active = False
        return results

    def _create_reflected(self, normal, intensity, element):
        new_ray = self.copy()
        new_ray.intensity = intensity
        new_ray.bounce_count += 1
        normal = np.array(normal, dtype=float)
        normal = normal / np.linalg.norm(normal)
        if np.dot(new_ray.direction, normal) > 0:
            normal = -normal
        new_ray.direction = new_ray.direction - 2 * np.dot(new_ray.direction, normal) * normal
        new_ray.history.append((new_ray.position.copy(), new_ray.direction.copy()))
        new_ray.interaction_history.append({
            'element': element.name,
            'type': 'reflect',
            'position': new_ray.position.copy(),
            'bounce': new_ray.bounce_count
        })
        return new_ray

    def _create_refracted(self, normal, n1, n2, intensity, element,
                           sin_theta2_sq, cos_theta1):
        new_ray = self.copy()
        new_ray.intensity = intensity
        new_ray.bounce_count += 1
        normal = np.array(normal, dtype=float)
        normal = normal / np.linalg.norm(normal)
        if np.dot(new_ray.direction, normal) > 0:
            normal = -normal
        n_ratio = n1 / n2
        cos_theta2 = np.sqrt(1.0 - sin_theta2_sq)
        new_ray.direction = n_ratio * new_ray.direction + (n_ratio * cos_theta1 - cos_theta2) * normal
        dir_norm = np.linalg.norm(new_ray.direction)
        if dir_norm < 1e-12:
            new_ray.direction = np.array([0.0, 0.0, 1.0])
        else:
            new_ray.direction = new_ray.direction / dir_norm
        new_ray.history.append((new_ray.position.copy(), new_ray.direction.copy()))
        new_ray.interaction_history.append({
            'element': element.name,
            'type': 'refract',
            'position': new_ray.position.copy(),
            'bounce': new_ray.bounce_count
        })
        return new_ray


class NonSequentialOpticalSystem:
    def __init__(self, name='NonSequentialSystem'):
        self.name = name
        self.elements = []
        self.detectors = []
        self.bounding_box = None

    def add_element(self, element, reflectivity=0.05, transmission=0.95):
        self.elements.append({
            'element': element,
            'reflectivity': reflectivity,
            'transmission': transmission
        })
        if self.bounding_box is None:
            self._update_bounding_box(element)

    def add_detector(self, detector):
        self.detectors.append(detector)
        self._update_bounding_box(detector)

    def _update_bounding_box(self, element):
        z = element.z_position
        r = element.aperture_radius if hasattr(element, 'aperture_radius') else 100.0
        if self.bounding_box is None:
            self.bounding_box = {
                'x_min': -r, 'x_max': r,
                'y_min': -r, 'y_max': r,
                'z_min': z - 1, 'z_max': z + 1
            }
        else:
            self.bounding_box['x_min'] = min(self.bounding_box['x_min'], -r)
            self.bounding_box['x_max'] = max(self.bounding_box['x_max'], r)
            self.bounding_box['y_min'] = min(self.bounding_box['y_min'], -r)
            self.bounding_box['y_max'] = max(self.bounding_box['y_max'], r)
            self.bounding_box['z_min'] = min(self.bounding_box['z_min'], z - 1)
            self.bounding_box['z_max'] = max(self.bounding_box['z_max'], z + 1)

    def find_closest_intersection(self, ray):
        if not ray.active:
            return None, None, None, None
        closest_t = float('inf')
        closest_element = None
        closest_point = None
        closest_info = None
        for elem_info in self.elements:
            element = elem_info['element']
            intersection = element.intersect(ray)
            if intersection is not None:
                point, t = intersection
                if t > 1e-6 and t < closest_t:
                    closest_t = t
                    closest_element = elem_info
                    closest_point = point
        if closest_element is None:
            for detector in self.detectors:
                intersection = detector.intersect(ray)
                if intersection is not None:
                    point, t = intersection
                    if t > 1e-6 and t < closest_t:
                        closest_t = t
                        closest_element = {'element': detector, 'is_detector': True}
                        closest_point = point
        return closest_element, closest_point, closest_t, closest_info

    def is_outside_bounding_box(self, ray):
        if self.bounding_box is None:
            return False
        bb = self.bounding_box
        pos = ray.position
        dir_ = ray.direction
        if dir_[2] > 0 and pos[2] > bb['z_max'] + 100:
            return True
        if dir_[2] < 0 and pos[2] < bb['z_min'] - 100:
            return True
        if abs(pos[0]) > bb['x_max'] * 2 or abs(pos[1]) > bb['y_max'] * 2:
            return True
        return False


class NonSequentialRayTracer:
    def __init__(self, optical_system):
        self.optical_system = optical_system
        self.traced_rays = []
        self.ghost_rays = []
        self.stray_rays = []
        self.detector_hits = []

    def trace_ray(self, ray, max_rays_per_bounce=2):
        rays_to_trace = [ray]
        all_rays = []
        iteration = 0
        max_iterations = 1000
        while rays_to_trace and iteration < max_iterations:
            iteration += 1
            current_ray = rays_to_trace.pop(0)
            if not current_ray.active:
                all_rays.append(current_ray)
                continue
            if self.optical_system.is_outside_bounding_box(current_ray):
                current_ray.active = False
                current_ray.is_stray = True
                all_rays.append(current_ray)
                continue
            closest_info, point, t, _ = self.optical_system.find_closest_intersection(
                current_ray)
            if closest_info is None or point is None:
                current_ray.propagate(1000)
                current_ray.active = False
                current_ray.is_stray = True
                all_rays.append(current_ray)
                continue
            element = closest_info['element']
            current_ray.position = point.copy()
            current_ray.history.append((point.copy(), current_ray.direction.copy()))
            current_ray.optical_path += t
            if closest_info.get('is_detector', False):
                current_ray.final_position = point.copy()
                current_ray.active = False
                current_ray.elements_hit.append(element.name)
                self.detector_hits.append({
                    'position': point.copy(),
                    'intensity': current_ray.intensity,
                    'wavelength': current_ray.wavelength,
                    'bounce_count': current_ray.bounce_count,
                    'is_ghost': current_ray.is_ghost,
                    'is_stray': current_ray.is_stray
                })
                all_rays.append(current_ray)
                continue
            n1, n2 = self._get_refractive_indices(current_ray, element, closest_info)
            normal = element.get_normal_at(point[0], point[1])
            reflectivity = closest_info.get('reflectivity', 0.05)
            transmission = closest_info.get('transmission', 0.95)
            new_rays = current_ray.interact_with_surface(
                element, normal, n1, n2, reflectivity, transmission)
            if new_rays:
                for i, (int_type, new_ray) in enumerate(new_rays):
                    if i < max_rays_per_bounce:
                        rays_to_trace.append(new_ray)
            current_ray.elements_hit.append(f"{element.name}")
            all_rays.append(current_ray)
        return all_rays

    def _get_refractive_indices(self, ray, element, elem_info):
        if hasattr(element, 'side'):
            if element.side == 'first':
                n1 = refractive_index('air', ray.wavelength)
                n2 = refractive_index(element.material, ray.wavelength)
            else:
                n1 = refractive_index(element.material, ray.wavelength)
                n2 = refractive_index('air', ray.wavelength)
        else:
            n1 = refractive_index('air', ray.wavelength)
            n2 = refractive_index('air', ray.wavelength)
        return n1, n2

    def trace_rays(self, rays, max_rays_per_bounce=2):
        all_results = []
        for ray in rays:
            results = self.trace_ray(ray, max_rays_per_bounce)
            all_results.extend(results)
        self.traced_rays.extend(all_results)
        self.ghost_rays = [r for r in all_results if r.is_ghost]
        self.stray_rays = [r for r in all_results if r.is_stray]
        return all_results

    def get_ghost_ray_paths(self):
        return [r for r in self.ghost_rays if len(r.history) > 1]

    def get_stray_light_intensity(self):
        total_intensity = sum(h['intensity'] for h in self.detector_hits)
        ghost_intensity = sum(h['intensity'] for h in self.detector_hits if h['is_ghost'])
        stray_intensity = sum(h['intensity'] for h in self.detector_hits if h['is_stray'])
        return {
            'total': total_intensity,
            'ghost': ghost_intensity,
            'stray': stray_intensity,
            'ghost_fraction': ghost_intensity / total_intensity if total_intensity > 0 else 0,
            'stray_fraction': stray_intensity / total_intensity if total_intensity > 0 else 0
        }

    def analyze_ghosts(self):
        ghost_paths = self.get_ghost_ray_paths()
        ghost_types = {}
        for ray in ghost_paths:
            path_key = tuple(h['element'] for h in ray.interaction_history)
            if path_key not in ghost_types:
                ghost_types[path_key] = {
                    'count': 0,
                    'total_intensity': 0.0,
                    'rays': []
                }
            ghost_types[path_key]['count'] += 1
            ghost_types[path_key]['total_intensity'] += ray.intensity
            ghost_types[path_key]['rays'].append(ray)
        return ghost_types

    def clear(self):
        self.traced_rays = []
        self.ghost_rays = []
        self.stray_rays = []
        self.detector_hits = []


def create_point_source_nonsequential(position, num_rays=50,
                                       max_angle=0.5, wavelength=0.587,
                                       max_bounces=5):
    rays = []
    angles = np.linspace(-max_angle, max_angle, num_rays)
    for theta in angles:
        dir_ = np.array([np.sin(theta), 0, np.cos(theta)])
        ray = NonSequentialRay(position, dir_, wavelength=wavelength,
                               max_bounces=max_bounces)
        rays.append(ray)
    return rays


def create_collimated_nonsequential(position, num_rays=21,
                                     max_height=10.0, wavelength=0.587,
                                     max_bounces=5):
    rays = []
    heights = np.linspace(-max_height, max_height, num_rays)
    for h in heights:
        pos = np.array([h, 0, position[2]])
        dir_ = np.array([0, 0, 1.0])
        ray = NonSequentialRay(pos, dir_, wavelength=wavelength,
                               max_bounces=max_bounces)
        rays.append(ray)
    return rays


def setup_lens_system_for_stray_analysis():
    from lens import create_singlet_lens
    system = NonSequentialOpticalSystem('Stray_Analysis')
    lens = create_singlet_lens(focal_length=100, z_position=0, thickness=8,
                              material='BK7', aperture_radius=15.0)
    for i, surf in enumerate(lens.get_surfaces()):
        reflectivity = 0.04
        transmission = 0.96
        system.add_element(surf, reflectivity=reflectivity,
                          transmission=transmission)
    from optical_elements import ImagePlane
    detector = ImagePlane(100, size=20, name='Detector')
    system.add_detector(detector)
    return system
