import numpy as np
from optical_constants import WAVELENGTH_COLORS, WAVELENGTH_NAMES


class Ray:
    def __init__(self, position, direction, wavelength=0.587, intensity=1.0, origin=None):
        self.position = np.array(position, dtype=float).reshape(3)
        direction = np.array(direction, dtype=float).reshape(3)
        self.direction = direction / np.linalg.norm(direction)
        self.wavelength = wavelength
        self.intensity = intensity
        self.origin = origin
        self.history = [(self.position.copy(), self.direction.copy())]
        self.active = True
        self.elements_hit = []
        self.final_position = None
        self.total_internal_reflection = False
        self.reflection_events = []

    def copy(self):
        new_ray = Ray(self.position.copy(), self.direction.copy(),
                      self.wavelength, self.intensity, self.origin)
        new_ray.history = [(p.copy(), d.copy()) for p, d in self.history]
        new_ray.active = self.active
        new_ray.elements_hit = self.elements_hit.copy()
        new_ray.final_position = self.final_position.copy() if self.final_position is not None else None
        new_ray.total_internal_reflection = self.total_internal_reflection
        new_ray.reflection_events = self.reflection_events.copy()
        return new_ray

    def propagate(self, distance):
        if not self.active:
            return
        new_pos = self.position + self.direction * distance
        self.position = new_pos
        self.history.append((new_pos.copy(), self.direction.copy()))

    def propagate_to_plane(self, z_position):
        if not self.active:
            return None
        if abs(self.direction[2]) < 1e-12:
            self.active = False
            return None
        distance = (z_position - self.position[2]) / self.direction[2]
        if distance < 0:
            self.active = False
            return None
        self.propagate(distance)
        return distance

    def reflect(self, normal):
        if not self.active:
            return
        normal = np.array(normal, dtype=float)
        normal = normal / np.linalg.norm(normal)
        self.direction = self.direction - 2 * np.dot(self.direction, normal) * normal
        self.history.append((self.position.copy(), self.direction.copy()))

    def refract(self, normal, n1, n2):
        if not self.active:
            return 'inactive'
        normal = np.array(normal, dtype=float)
        normal = normal / np.linalg.norm(normal)
        if np.dot(self.direction, normal) > 0:
            normal = -normal
        cos_theta1 = -np.dot(self.direction, normal)
        cos_theta1 = np.clip(cos_theta1, 0.0, 1.0)
        sin_theta1_sq = max(0.0, 1 - cos_theta1 ** 2)
        n_ratio = n1 / n2
        sin_theta2_sq = n_ratio ** 2 * sin_theta1_sq
        if sin_theta2_sq >= 1.0 - 1e-10:
            self.total_internal_reflection = True
            self.reflection_events.append({
                'position': self.position.copy(),
                'wavelength': self.wavelength,
                'type': 'total_internal_reflection',
                'n1': float(n1),
                'n2': float(n2),
                'incident_angle': float(np.arcsin(np.sqrt(float(sin_theta1_sq))) * 180 / np.pi)
            })
            self.reflect(normal)
            return 'total_internal_reflection'
        sin_theta2_sq = min(sin_theta2_sq, 1.0 - 1e-12)
        cos_theta2 = np.sqrt(1.0 - sin_theta2_sq)
        self.direction = n_ratio * self.direction + (n_ratio * cos_theta1 - cos_theta2) * normal
        dir_norm = np.linalg.norm(self.direction)
        if dir_norm < 1e-12:
            self.direction = np.array([0.0, 0.0, 1.0])
        else:
            self.direction = self.direction / dir_norm
        self.history.append((self.position.copy(), self.direction.copy()))
        return 'refracted'

    def get_color(self):
        wls = sorted(WAVELENGTH_COLORS.keys())
        closest_wl = min(wls, key=lambda w: abs(w - self.wavelength))
        return WAVELENGTH_COLORS[closest_wl]

    def get_wavelength_name(self):
        wls = sorted(WAVELENGTH_NAMES.keys())
        closest_wl = min(wls, key=lambda w: abs(w - self.wavelength))
        return WAVELENGTH_NAMES[closest_wl]

    def get_path_length(self):
        total = 0.0
        for i in range(1, len(self.history)):
            total += np.linalg.norm(self.history[i][0] - self.history[i-1][0])
        return total

    def get_xy_at_z(self, z):
        if not self.active or len(self.history) < 2:
            return None
        for i in range(len(self.history) - 1):
            p1, _ = self.history[i]
            p2, _ = self.history[i+1]
            if (p1[2] <= z <= p2[2]) or (p2[2] <= z <= p1[2]):
                if abs(p2[2] - p1[2]) < 1e-12:
                    continue
                t = (z - p1[2]) / (p2[2] - p1[2])
                x = p1[0] + t * (p2[0] - p1[0])
                y = p1[1] + t * (p2[1] - p1[1])
                return np.array([x, y, z])
        return None


def create_ray_bundle(object_height=0.0, angle=0.0, num_rays=11, max_height=10.0,
                      wavelength=0.587, initial_z=-50.0, distribution='radial'):
    rays = []
    if distribution == 'ring':
        angles = np.linspace(0, 2 * np.pi, num_rays, endpoint=False)
        for theta in angles:
            x = max_height * np.cos(theta)
            y = max_height * np.sin(theta)
            pos = np.array([x + object_height, y, initial_z])
            dir_ = np.array([angle, 0, 1.0])
            dir_ = dir_ / np.linalg.norm(dir_)
            rays.append(Ray(pos, dir_, wavelength=wavelength))
    elif distribution == 'grid':
        grid_size = int(np.ceil(np.sqrt(num_rays)))
        xs = np.linspace(-max_height, max_height, grid_size)
        ys = np.linspace(-max_height, max_height, grid_size)
        for x in xs:
            for y in ys:
                pos = np.array([x + object_height, y, initial_z])
                dir_ = np.array([angle, 0, 1.0])
                dir_ = dir_ / np.linalg.norm(dir_)
                rays.append(Ray(pos, dir_, wavelength=wavelength))
    elif distribution == 'radial':
        rings = int(np.ceil(np.sqrt(num_rays / 6)))
        for r_idx in range(rings):
            r = max_height * (r_idx + 1) / rings
            n_angles = 6 * (r_idx + 1) if r_idx > 0 else 1
            angles = np.linspace(0, 2 * np.pi, n_angles, endpoint=False)
            for theta in angles:
                x = r * np.cos(theta)
                y = r * np.sin(theta)
                pos = np.array([x + object_height, y, initial_z])
                dir_ = np.array([angle, 0, 1.0])
                dir_ = dir_ / np.linalg.norm(dir_)
                rays.append(Ray(pos, dir_, wavelength=wavelength))
    elif distribution == 'meridional':
        heights = np.linspace(-max_height, max_height, num_rays)
        for h in heights:
            pos = np.array([h + object_height, 0, initial_z])
            dir_ = np.array([angle, 0, 1.0])
            dir_ = dir_ / np.linalg.norm(dir_)
            rays.append(Ray(pos, dir_, wavelength=wavelength))
    else:
        heights = np.linspace(-max_height, max_height, num_rays)
        for h in heights:
            pos = np.array([h + object_height, 0, initial_z])
            dir_ = np.array([angle, 0, 1.0])
            dir_ = dir_ / np.linalg.norm(dir_)
            rays.append(Ray(pos, dir_, wavelength=wavelength))
    return rays


def create_point_source_rays(object_height=0.0, num_rays=50, max_angle=0.3,
                              wavelength=0.587, initial_z=-50.0):
    rays = []
    angles = np.linspace(-max_angle, max_angle, num_rays)
    for theta in angles:
        pos = np.array([object_height, 0, initial_z])
        dir_ = np.array([np.sin(theta), 0, np.cos(theta)])
        rays.append(Ray(pos, dir_, wavelength=wavelength))
    return rays


def create_collimated_rays(object_height=0.0, num_rays=21, max_height=10.0,
                            wavelength=0.587, initial_z=-50.0):
    return create_ray_bundle(object_height=object_height, angle=0.0,
                              num_rays=num_rays, max_height=max_height,
                              wavelength=wavelength, initial_z=initial_z,
                              distribution='meridional')
