import numpy as np
from abc import ABC, abstractmethod
from optical_constants import refractive_index


class OpticalElement(ABC):
    def __init__(self, z_position, aperture_radius=25.4, name=''):
        self.z_position = z_position
        self.aperture_radius = aperture_radius
        self.name = name
        self.element_type = 'generic'

    @abstractmethod
    def get_surface_height(self, r):
        pass

    @abstractmethod
    def get_surface_normal(self, r):
        pass

    def get_surface_sag(self, x, y):
        r = np.sqrt(x**2 + y**2)
        return self.get_surface_height(r)

    def get_normal_at(self, x, y):
        r = np.sqrt(x**2 + y**2)
        if r < 1e-12:
            return np.array([0.0, 0.0, -1.0])
        dr_dx = x / r
        dr_dy = y / r
        dz_dr = self.get_surface_normal(r)
        dz_dx = dz_dr * dr_dx
        dz_dy = dz_dr * dr_dy
        normal = np.array([-dz_dx, -dz_dy, 1.0])
        return normal / np.linalg.norm(normal)

    def intersect(self, ray):
        if not ray.active:
            return None
        pos = ray.position.copy()
        dir_ = ray.direction.copy()
        z_center = self.z_position

        if abs(dir_[2]) < 1e-12:
            return None

        t_to_vertex = (z_center - pos[2]) / dir_[2]
        if t_to_vertex < -1.0:
            return None

        t_search_min = max(0, t_to_vertex - 50)
        t_search_max = t_to_vertex + 50

        def f(t):
            if t < 0:
                return 1e10
            x = pos[0] + dir_[0] * t
            y = pos[1] + dir_[1] * t
            z = pos[2] + dir_[2] * t
            r = np.sqrt(x**2 + y**2)
            if r > self.aperture_radius * 1.5:
                return 1e10
            sag = self.get_surface_height(r)
            z_surface = z_center + sag
            return z - z_surface

        f_prev = None
        t_low = None
        t_high = None

        for t in np.linspace(t_search_min, t_search_max, 2000):
            f_curr = f(t)
            if abs(f_curr) < 1e10 and f_prev is not None:
                if f_prev * f_curr <= 0:
                    t_low = t - (t_search_max - t_search_min) / 2000
                    t_high = t
                    break
            f_prev = f_curr

        if t_low is not None and t_high is not None:
            for _ in range(200):
                t_mid = (t_low + t_high) / 2
                f_mid = f(t_mid)
                f_low = f(t_low)
                if abs(f_mid) < 1e-12:
                    t_low = t_high = t_mid
                    break
                if f_low * f_mid <= 0:
                    t_high = t_mid
                else:
                    t_low = t_mid
                if abs(t_high - t_low) < 1e-12:
                    break

            best_t = (t_low + t_high) / 2
            best_point = np.array([
                pos[0] + dir_[0] * best_t,
                pos[1] + dir_[1] * best_t,
                pos[2] + dir_[2] * best_t
            ])
            r_final = np.sqrt(best_point[0]**2 + best_point[1]**2)
            if r_final > self.aperture_radius:
                return None
            if best_t < 1e-6:
                return None
            return best_point, best_t

        return None

    @abstractmethod
    def interact(self, ray):
        pass

    def get_edges(self, num_points=100):
        r = np.linspace(-self.aperture_radius, self.aperture_radius, num_points)
        z = self.z_position + self.get_surface_height(np.abs(r))
        return r, z


class SphericalSurface(OpticalElement):
    def __init__(self, z_position, radius_of_curvature, aperture_radius=25.4,
                 material='air', side='first', thickness=0, name=''):
        super().__init__(z_position, aperture_radius, name)
        self.radius_of_curvature = radius_of_curvature
        self.material = material
        self.side = side
        self.thickness = thickness
        self.element_type = 'spherical_surface'
        self.is_reflective = False

    def get_surface_height(self, r):
        R = self.radius_of_curvature
        if abs(R) < 1e-12:
            return np.zeros_like(r)
        sign = 1 if R > 0 else -1
        R_abs = abs(R)
        if hasattr(r, '__len__'):
            r_clipped = np.clip(r, 0, R_abs * 0.999)
            return sign * (R_abs - np.sqrt(R_abs**2 - r_clipped**2))
        else:
            r_clipped = min(r, R_abs * 0.999)
            return sign * (R_abs - np.sqrt(R_abs**2 - r_clipped**2))

    def get_surface_normal(self, r):
        R = self.radius_of_curvature
        if abs(R) < 1e-12:
            return np.zeros_like(r)
        sign = 1 if R > 0 else -1
        R_abs = abs(R)
        if hasattr(r, '__len__'):
            r_clipped = np.clip(r, 0, R_abs * 0.999)
            return sign * r_clipped / np.sqrt(R_abs**2 - r_clipped**2)
        else:
            r_clipped = min(r, R_abs * 0.999)
            return sign * r_clipped / np.sqrt(R_abs**2 - r_clipped**2)

    def interact(self, ray):
        if not ray.active:
            return
        intersection = self.intersect(ray)
        if intersection is None:
            ray.active = False
            return
        point, t = intersection
        ray.position = point.copy()
        ray.history.append((point.copy(), ray.direction.copy()))
        normal = self.get_normal_at(point[0], point[1])
        if self.side == 'first':
            n1 = refractive_index('air', ray.wavelength)
            n2 = refractive_index(self.material, ray.wavelength)
        else:
            n1 = refractive_index(self.material, ray.wavelength)
            n2 = refractive_index('air', ray.wavelength)
        status = ray.refract(normal, n1, n2)
        ray.elements_hit.append(f"{self.name}({status})")


class AsphericalSurface(SphericalSurface):
    def __init__(self, z_position, curvature, conic_constant,
                 polynomial_coeffs=None, aperture_radius=25.4,
                 material='air', side='first', thickness=0, name=''):
        radius_of_curvature = 1.0 / curvature if abs(curvature) > 1e-12 else float('inf')
        super().__init__(z_position, radius_of_curvature, aperture_radius,
                         material, side, thickness, name)
        self.curvature = curvature
        self.conic_constant = conic_constant
        self.polynomial_coeffs = polynomial_coeffs if polynomial_coeffs is not None else []
        self.element_type = 'aspherical_surface'

    def get_surface_height(self, r):
        c = self.curvature
        k = self.conic_constant
        if abs(c) < 1e-12:
            base = np.zeros_like(r) if hasattr(r, '__len__') else 0.0
        else:
            if hasattr(r, '__len__'):
                denominator = 1 - (1 + k) * c**2 * r**2
                valid = denominator > 0
                base = np.zeros_like(r)
                base[valid] = c * r[valid]**2 / (1 + np.sqrt(denominator[valid]))
            else:
                denominator = 1 - (1 + k) * c**2 * r**2
                if denominator <= 0:
                    base = 0.0
                else:
                    base = c * r**2 / (1 + np.sqrt(denominator))
        poly_term = 0.0
        for i, coeff in enumerate(self.polynomial_coeffs):
            poly_term += coeff * r**(2 * (i + 2))
        return base + poly_term

    def get_surface_normal(self, r):
        c = self.curvature
        k = self.conic_constant
        if abs(c) < 1e-12:
            dz_dr_base = np.zeros_like(r) if hasattr(r, '__len__') else 0.0
        else:
            if hasattr(r, '__len__'):
                denominator = 1 - (1 + k) * c**2 * r**2
                valid = denominator > 0
                dz_dr_base = np.zeros_like(r)
                dz_dr_base[valid] = c * r[valid] / np.sqrt(denominator[valid])
            else:
                denominator = 1 - (1 + k) * c**2 * r**2
                if denominator <= 0:
                    dz_dr_base = 0.0
                else:
                    dz_dr_base = c * r / np.sqrt(denominator)
        poly_deriv = 0.0
        for i, coeff in enumerate(self.polynomial_coeffs):
            exp = 2 * (i + 2) - 1
            poly_deriv += exp * coeff * r**exp
        return dz_dr_base + poly_deriv


class ReflectiveSurface(OpticalElement):
    def __init__(self, z_position, radius_of_curvature, aperture_radius=25.4,
                 conic_constant=0, name=''):
        super().__init__(z_position, aperture_radius, name)
        self.radius_of_curvature = radius_of_curvature
        self.conic_constant = conic_constant
        self.element_type = 'reflective_surface'
        self.is_reflective = True

    def get_surface_height(self, r):
        R = self.radius_of_curvature
        k = self.conic_constant
        if abs(R) < 1e-12:
            return np.zeros_like(r) if hasattr(r, '__len__') else 0.0
        if hasattr(r, '__len__'):
            denominator = 1 + (1 + k) * (r / R)**2
            valid = denominator > 0
            z = np.zeros_like(r)
            z[valid] = R * (r[valid]**2) / (R**2 * (1 + np.sqrt(denominator[valid])))
            return z
        else:
            denominator = 1 + (1 + k) * (r / R)**2
            if denominator <= 0:
                return 0.0
            return R * r**2 / (R**2 * (1 + np.sqrt(denominator)))

    def get_surface_normal(self, r):
        R = self.radius_of_curvature
        k = self.conic_constant
        if abs(R) < 1e-12:
            return np.zeros_like(r) if hasattr(r, '__len__') else 0.0
        if hasattr(r, '__len__'):
            denominator = 1 + (1 + k) * (r / R)**2
            valid = denominator > 0
            dz_dr = np.zeros_like(r)
            dz_dr[valid] = (r[valid] / R) / np.sqrt(denominator[valid])
            return dz_dr
        else:
            denominator = 1 + (1 + k) * (r / R)**2
            if denominator <= 0:
                return 0.0
            return (r / R) / np.sqrt(denominator)

    def interact(self, ray):
        if not ray.active:
            return
        intersection = self.intersect(ray)
        if intersection is None:
            ray.active = False
            return
        point, t = intersection
        ray.position = point.copy()
        ray.history.append((point.copy(), ray.direction.copy()))
        normal = self.get_normal_at(point[0], point[1])
        if np.dot(ray.direction, normal) > 0:
            normal = -normal
        ray.reflect(normal)
        ray.elements_hit.append(self.name)


class ApertureStop(OpticalElement):
    def __init__(self, z_position, aperture_radius=25.4, name=''):
        super().__init__(z_position, aperture_radius, name)
        self.element_type = 'aperture_stop'

    def get_surface_height(self, r):
        return np.zeros_like(r) if hasattr(r, '__len__') else 0.0

    def get_surface_normal(self, r):
        return np.zeros_like(r) if hasattr(r, '__len__') else 0.0

    def intersect(self, ray):
        if not ray.active:
            return None
        t = ray.propagate_to_plane(self.z_position)
        if t is None:
            return None
        r = np.sqrt(ray.position[0]**2 + ray.position[1]**2)
        if r > self.aperture_radius:
            ray.active = False
            return None
        return ray.position.copy(), t

    def interact(self, ray):
        if not ray.active:
            return
        intersection = self.intersect(ray)
        if intersection is not None:
            ray.elements_hit.append(self.name)


class ImagePlane(OpticalElement):
    def __init__(self, z_position, size=50, name=''):
        super().__init__(z_position, size / 2, name)
        self.size = size
        self.element_type = 'image_plane'

    def get_surface_height(self, r):
        return np.zeros_like(r) if hasattr(r, '__len__') else 0.0

    def get_surface_normal(self, r):
        return np.zeros_like(r) if hasattr(r, '__len__') else 0.0

    def intersect(self, ray):
        if not ray.active:
            return None
        t = ray.propagate_to_plane(self.z_position)
        if t is None:
            return None
        return ray.position.copy(), t

    def interact(self, ray):
        if not ray.active:
            return
        intersection = self.intersect(ray)
        if intersection is not None:
            ray.final_position = intersection[0].copy()
            ray.elements_hit.append(self.name)


class ThinLens(OpticalElement):
    def __init__(self, z_position, focal_length, aperture_radius=25.4, name=''):
        super().__init__(z_position, aperture_radius, name)
        self.focal_length = focal_length
        self.element_type = 'thin_lens'

    def get_surface_height(self, r):
        return np.zeros_like(r) if hasattr(r, '__len__') else 0.0

    def get_surface_normal(self, r):
        return np.zeros_like(r) if hasattr(r, '__len__') else 0.0

    def intersect(self, ray):
        if not ray.active:
            return None
        t = ray.propagate_to_plane(self.z_position)
        if t is None:
            return None
        r = np.sqrt(ray.position[0]**2 + ray.position[1]**2)
        if r > self.aperture_radius:
            ray.active = False
            return None
        return ray.position.copy(), t

    def interact(self, ray):
        if not ray.active:
            return
        intersection = self.intersect(ray)
        if intersection is None:
            return
        point, t = intersection
        ray.history.append((point.copy(), ray.direction.copy()))
        n = refractive_index('air', ray.wavelength)
        h = np.sqrt(point[0]**2 + point[1]**2)
        if h > 0:
            radial_dir = np.array([point[0], point[1], 0]) / h
            slope = h / self.focal_length
            ray.direction[0] -= slope * radial_dir[0]
            ray.direction[1] -= slope * radial_dir[1]
            ray.direction = ray.direction / np.linalg.norm(ray.direction)
            ray.history.append((point.copy(), ray.direction.copy()))
        ray.elements_hit.append(self.name)
