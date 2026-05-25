import numpy as np
from optical_elements import (SphericalSurface, AsphericalSurface, ApertureStop,
                             ImagePlane, ReflectiveSurface)
from optical_constants import refractive_index


class ThickLens:
    def __init__(self, z_position, r1, r2, thickness, material='BK7',
                 aperture_radius=25.4, name='ThickLens'):
        self.z_position = z_position
        self.r1 = r1
        self.r2 = r2
        self.thickness = thickness
        self.material = material
        self.aperture_radius = aperture_radius
        self.name = name
        self.surface1 = SphericalSurface(z_position, r1, aperture_radius,
                                         material, side='first',
                                         thickness=thickness,
                                         name=name + '_front')
        self.surface2 = SphericalSurface(z_position + thickness, r2,
                                         aperture_radius, material,
                                         side='second', name=name + '_back')
        self.surfaces = [self.surface1, self.surface2]

    def get_surfaces(self):
        return self.surfaces

    def get_focal_length(self, wavelength=0.587):
        n = refractive_index(self.material, wavelength)
        R1 = self.r1
        R2 = self.r2
        d = self.thickness
        P1 = (n - 1) / R1 if abs(R1) > 1e-12 else 0
        P2 = (1 - n) / R2 if abs(R2) > 1e-12 else 0
        P = P1 + P2 - d * P1 * P2 / n
        return 1.0 / P if abs(P) > 1e-12 else float('inf')

    def get_principal_planes(self, wavelength=0.587):
        n = refractive_index(self.material, wavelength)
        R1 = self.r1
        R2 = self.r2
        d = self.thickness
        f = self.get_focal_length(wavelength)
        h1 = -f * (n - 1) * d / (n * R2) if abs(R2) > 1e-12 else 0
        h2 = -f * (n - 1) * d / (n * R1) if abs(R1) > 1e-12 else 0
        return (self.z_position + h1, self.z_position + self.thickness + h2)

    def get_back_focal_length(self, wavelength=0.587):
        f = self.get_focal_length(wavelength)
        _, h2 = self.get_principal_planes(wavelength)
        return f - (h2 - (self.z_position + self.thickness))


class DoubletLens:
    def __init__(self, z_position, r1, r2, r3, thickness1, thickness2,
                 material1='BK7', material2='SF11', aperture_radius=25.4,
                 name='Doublet'):
        self.z_position = z_position
        self.r1 = r1
        self.r2 = r2
        self.r3 = r3
        self.thickness1 = thickness1
        self.thickness2 = thickness2
        self.material1 = material1
        self.material2 = material2
        self.aperture_radius = aperture_radius
        self.name = name
        self.surface1 = SphericalSurface(z_position, r1, aperture_radius,
                                         material1, side='first',
                                         thickness=thickness1,
                                         name=name + '_s1')
        self.surface2 = SphericalSurface(z_position + thickness1, r2,
                                         aperture_radius, material2,
                                         side='first', thickness=thickness2,
                                         name=name + '_s2')
        self.surface3 = SphericalSurface(z_position + thickness1 + thickness2,
                                         r3, aperture_radius, material2,
                                         side='second', name=name + '_s3')
        self.surfaces = [self.surface1, self.surface2, self.surface3]

    def get_surfaces(self):
        return self.surfaces

    def get_focal_length(self, wavelength=0.587):
        n1 = refractive_index(self.material1, wavelength)
        n2 = refractive_index(self.material2, wavelength)
        R1, R2, R3 = self.r1, self.r2, self.r3
        d1, d2 = self.thickness1, self.thickness2
        P1 = (n1 - 1) / R1 if abs(R1) > 1e-12 else 0
        P2 = (n2 - n1) / R2 if abs(R2) > 1e-12 else 0
        P3 = (1 - n2) / R3 if abs(R3) > 1e-12 else 0
        M1 = np.array([[1, 0], [-P1, 1]])
        M2 = np.array([[1, d1 / n1], [0, 1]])
        M3 = np.array([[1, 0], [-P2, 1]])
        M4 = np.array([[1, d2 / n2], [0, 1]])
        M5 = np.array([[1, 0], [-P3, 1]])
        M = M5 @ M4 @ M3 @ M2 @ M1
        if abs(M[1, 0]) > 1e-12:
            return -1.0 / M[1, 0]
        return float('inf')


class AsphericalLens:
    def __init__(self, z_position, curvature1, curvature2, conic1, conic2,
                 thickness, material='BK7', aperture_radius=25.4,
                 poly_coeffs1=None, poly_coeffs2=None, name='AsphericLens'):
        self.z_position = z_position
        self.curvature1 = curvature1
        self.curvature2 = curvature2
        self.conic1 = conic1
        self.conic2 = conic2
        self.r1 = 1.0 / curvature1 if abs(curvature1) > 1e-12 else float('inf')
        self.r2 = 1.0 / curvature2 if abs(curvature2) > 1e-12 else float('inf')
        self.thickness = thickness
        self.material = material
        self.aperture_radius = aperture_radius
        self.name = name
        self.surface1 = AsphericalSurface(z_position, curvature1, conic1,
                                          poly_coeffs1, aperture_radius,
                                          material, side='first',
                                          thickness=thickness,
                                          name=name + '_front')
        self.surface2 = AsphericalSurface(z_position + thickness, curvature2,
                                          conic2, poly_coeffs2,
                                          aperture_radius, material,
                                          side='second', name=name + '_back')
        self.surfaces = [self.surface1, self.surface2]

    def get_surfaces(self):
        return self.surfaces


class LensSystem:
    def __init__(self, name='OpticalSystem'):
        self.name = name
        self.elements = []
        self.image_plane = None

    def add_element(self, element):
        self.elements.append(element)

    def add_thick_lens(self, z_position, r1, r2, thickness, material='BK7',
                       aperture_radius=25.4, name=''):
        if not name:
            name = f'Lens_{len(self.elements)}'
        lens = ThickLens(z_position, r1, r2, thickness, material,
                         aperture_radius, name)
        for surf in lens.get_surfaces():
            self.elements.append(surf)
        return lens

    def add_doublet(self, z_position, r1, r2, r3, thickness1, thickness2,
                    material1='BK7', material2='SF11', aperture_radius=25.4,
                    name=''):
        if not name:
            name = f'Doublet_{len(self.elements)}'
        doublet = DoubletLens(z_position, r1, r2, r3, thickness1, thickness2,
                              material1, material2, aperture_radius, name)
        for surf in doublet.get_surfaces():
            self.elements.append(surf)
        return doublet

    def add_aspheric_lens(self, z_position, curvature1, curvature2,
                          conic1, conic2, thickness,
                          material='BK7', aperture_radius=25.4,
                          poly_coeffs1=None, poly_coeffs2=None, name=''):
        if not name:
            name = f'Aspheric_{len(self.elements)}'
        lens = AsphericalLens(z_position, curvature1, curvature2,
                              conic1, conic2, thickness,
                              material, aperture_radius,
                              poly_coeffs1, poly_coeffs2, name)
        for surf in lens.get_surfaces():
            self.elements.append(surf)
        return lens

    def add_mirror(self, z_position, radius_of_curvature, aperture_radius=25.4,
                   conic_constant=0, name=''):
        if not name:
            name = f'Mirror_{len(self.elements)}'
        mirror = ReflectiveSurface(z_position, radius_of_curvature,
                                   aperture_radius, conic_constant, name)
        self.elements.append(mirror)
        return mirror

    def add_stop(self, z_position, aperture_radius, name=''):
        if not name:
            name = f'Stop_{len(self.elements)}'
        stop = ApertureStop(z_position, aperture_radius, name)
        self.elements.append(stop)
        return stop

    def set_image_plane(self, z_position, size=50, name='ImagePlane'):
        self.image_plane = ImagePlane(z_position, size, name)
        return self.image_plane

    def get_sorted_elements(self):
        all_elements = self.elements.copy()
        if self.image_plane is not None:
            all_elements.append(self.image_plane)
        has_reflective = any(hasattr(e, 'is_reflective') and e.is_reflective
                             for e in all_elements)
        if has_reflective:
            return all_elements
        return sorted(all_elements, key=lambda e: e.z_position)

    def get_z_extent(self):
        all_zs = [e.z_position for e in self.elements]
        if self.image_plane is not None:
            all_zs.append(self.image_plane.z_position)
        return min(all_zs), max(all_zs)


def create_singlet_lens(focal_length=100, z_position=0, thickness=10,
                        material='BK7', aperture_radius=25, biconvex=True):
    n = refractive_index(material, 0.587)
    if biconvex:
        R = 2 * (n - 1) * focal_length
        r1 = R
        r2 = -R
    else:
        R = (n - 1) * focal_length
        r1 = R
        r2 = float('inf')
    lens = ThickLens(z_position, r1, r2, thickness, material,
                     aperture_radius, name='Singlet')
    return lens


def create_achromatic_doublet(focal_length=100, z_position=0,
                              thickness1=8, thickness2=4,
                              material1='BK7', material2='SF11',
                              aperture_radius=25):
    n1_d = refractive_index(material1, 0.587)
    n2_d = refractive_index(material2, 0.587)
    n1_F = refractive_index(material1, 0.486)
    n2_F = refractive_index(material2, 0.486)
    n1_C = refractive_index(material1, 0.656)
    n2_C = refractive_index(material2, 0.656)
    V1 = (n1_d - 1) / (n1_F - n1_C)
    V2 = (n2_d - 1) / (n2_F - n2_C)
    P1 = V1 / (focal_length * (V1 - V2))
    P2 = -V2 / (focal_length * (V1 - V2))
    r1 = (n1_d - 1) / P1
    r2 = (n2_d - n1_d) / (P2 - (n1_d - 1) / r1)
    r3 = (1 - n2_d) / (P2 - (n2_d - n1_d) / r2)
    doublet = DoubletLens(z_position, r1, r2, r3, thickness1, thickness2,
                          material1, material2, aperture_radius,
                          name='Achromat')
    return doublet
