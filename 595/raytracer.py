import numpy as np
import cv2
import time
import sys
import math
import random
import os
import multiprocessing
from dataclasses import dataclass, field
from typing import Optional, List, Tuple
from abc import ABC, abstractmethod
from concurrent.futures import ProcessPoolExecutor, as_completed

EPSILON = 1e-6
INF = float('inf')
SCENE_SEED = 42


class Vec3:
    __slots__ = ('x', 'y', 'z', '_data')

    def __init__(self, x=0.0, y=0.0, z=0.0):
        if isinstance(x, np.ndarray):
            self._data = x.astype(np.float64)
            self.x = float(self._data[0])
            self.y = float(self._data[1])
            self.z = float(self._data[2])
        else:
            self.x = float(x)
            self.y = float(y)
            self.z = float(z)
            self._data = None

    def _get_data(self):
        if self._data is None:
            self._data = np.array([self.x, self.y, self.z], dtype=np.float64)
        return self._data

    def __add__(self, other):
        if isinstance(other, Vec3):
            return Vec3(self.x + other.x, self.y + other.y, self.z + other.z)
        return Vec3(self.x + other, self.y + other, self.z + other)

    def __sub__(self, other):
        if isinstance(other, Vec3):
            return Vec3(self.x - other.x, self.y - other.y, self.z - other.z)
        return Vec3(self.x - other, self.y - other, self.z - other)

    def __mul__(self, other):
        if isinstance(other, Vec3):
            return Vec3(self.x * other.x, self.y * other.y, self.z * other.z)
        return Vec3(self.x * other, self.y * other, self.z * other)

    def __rmul__(self, other):
        return self.__mul__(other)

    def __neg__(self):
        return Vec3(-self.x, -self.y, -self.z)

    def __truediv__(self, other):
        if isinstance(other, Vec3):
            return Vec3(self.x / other.x, self.y / other.y, self.z / other.z)
        return Vec3(self.x / other, self.y / other, self.z / other)

    def dot(self, other):
        return self.x * other.x + self.y * other.y + self.z * other.z

    def cross(self, other):
        return Vec3(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x,
        )

    def length_squared(self):
        return self.x * self.x + self.y * self.y + self.z * self.z

    def length(self):
        return math.sqrt(self.length_squared())

    def normalized(self):
        l = self.length()
        if l < EPSILON:
            return Vec3(0, 0, 0)
        inv = 1.0 / l
        return Vec3(self.x * inv, self.y * inv, self.z * inv)

    def __repr__(self):
        return f"Vec3({self.x:.4f}, {self.y:.4f}, {self.z:.4f})"


def reflect(v: Vec3, n: Vec3) -> Vec3:
    d = 2.0 * (v.x * n.x + v.y * n.y + v.z * n.z)
    return Vec3(v.x - d * n.x, v.y - d * n.y, v.z - d * n.z)


def refract(v: Vec3, n: Vec3, etai_over_etat: float) -> Vec3:
    cos_theta = min(-(v.x * n.x + v.y * n.y + v.z * n.z), 1.0)
    rx = etai_over_etat * (v.x + cos_theta * n.x)
    ry = etai_over_etat * (v.y + cos_theta * n.y)
    rz = etai_over_etat * (v.z + cos_theta * n.z)
    r_perp_len_sq = rx * rx + ry * ry + rz * rz
    k = -math.sqrt(abs(1.0 - r_perp_len_sq))
    return Vec3(rx + k * n.x, ry + k * n.y, rz + k * n.z)


def schlick(cosine: float, ref_idx: float) -> float:
    r0 = ((1 - ref_idx) / (1 + ref_idx)) ** 2
    return r0 + (1 - r0) * ((1 - cosine) ** 5)


def random_in_unit_sphere(rng: random.Random) -> Vec3:
    while True:
        x = rng.uniform(-1, 1)
        y = rng.uniform(-1, 1)
        z = rng.uniform(-1, 1)
        if x * x + y * y + z * z < 1.0:
            return Vec3(x, y, z)


def random_unit_vector(rng: random.Random) -> Vec3:
    v = random_in_unit_sphere(rng)
    l = math.sqrt(v.x * v.x + v.y * v.y + v.z * v.z)
    if l < EPSILON:
        return Vec3(0, 1, 0)
    inv = 1.0 / l
    return Vec3(v.x * inv, v.y * inv, v.z * inv)


class Texture(ABC):
    @abstractmethod
    def value(self, u: float, v: float, point: Vec3) -> Vec3:
        pass


class SolidColor(Texture):
    __slots__ = ('color',)

    def __init__(self, color: Vec3):
        self.color = color

    def value(self, u: float, v: float, point: Vec3) -> Vec3:
        return self.color


class CheckerTexture(Texture):
    __slots__ = ('odd', 'even', 'scale')

    def __init__(self, odd: Texture, even: Texture, scale: float = 10.0):
        self.odd = odd
        self.even = even
        self.scale = scale

    def value(self, u: float, v: float, point: Vec3) -> Vec3:
        sines = math.sin(self.scale * point.x) * math.sin(self.scale * point.y) * math.sin(self.scale * point.z)
        if sines < 0:
            return self.odd.value(u, v, point)
        return self.even.value(u, v, point)


class ImageTexture(Texture):
    __slots__ = ('data', 'width', 'height')

    def __init__(self, path: str):
        img = cv2.imread(path, cv2.IMREAD_COLOR)
        if img is None:
            raise FileNotFoundError(f"Cannot load texture: {path}")
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        self.data = img.astype(np.float64) / 255.0
        self.height, self.width = img.shape[:2]

    def value(self, u: float, v: float, point: Vec3) -> Vec3:
        u = u - math.floor(u)
        v = v - math.floor(v)
        x = u * (self.width - 1)
        y = (1.0 - v) * (self.height - 1)
        x0 = int(x)
        y0 = int(y)
        x1 = min(x0 + 1, self.width - 1)
        y1 = min(y0 + 1, self.height - 1)
        fx = x - x0
        fy = y - y0
        c00 = self.data[y0, x0]
        c01 = self.data[y0, x1]
        c10 = self.data[y1, x0]
        c11 = self.data[y1, x1]
        c0 = c00 * (1 - fx) + c01 * fx
        c1 = c10 * (1 - fx) + c11 * fx
        c = c0 * (1 - fy) + c1 * fy
        return Vec3(float(c[0]), float(c[1]), float(c[2]))


@dataclass
class Ray:
    origin: Vec3
    direction: Vec3

    def at(self, t: float) -> Vec3:
        return Vec3(
            self.origin.x + t * self.direction.x,
            self.origin.y + t * self.direction.y,
            self.origin.z + t * self.direction.z,
        )


@dataclass
class HitRecord:
    t: float = INF
    point: Vec3 = field(default_factory=lambda: Vec3())
    normal: Vec3 = field(default_factory=lambda: Vec3())
    front_face: bool = True
    material: Optional['Material'] = None
    u: float = 0.0
    v: float = 0.0

    def set_face_normal(self, ray: Ray, outward_normal: Vec3):
        self.front_face = ray.direction.dot(outward_normal) < 0
        if self.front_face:
            self.normal = outward_normal
        else:
            self.normal = -outward_normal


class Material(ABC):
    @abstractmethod
    def scatter(self, ray: Ray, hit: HitRecord, rng: random.Random) -> Tuple[bool, Vec3, Ray]:
        pass

    @abstractmethod
    def emitted(self) -> Vec3:
        pass


class Lambertian(Material):
    __slots__ = ('albedo',)

    def __init__(self, albedo):
        if isinstance(albedo, Vec3):
            self.albedo = SolidColor(albedo)
        elif isinstance(albedo, Texture):
            self.albedo = albedo
        else:
            self.albedo = SolidColor(Vec3(0.5, 0.5, 0.5))

    def scatter(self, ray: Ray, hit: HitRecord, rng: random.Random) -> Tuple[bool, Vec3, Ray]:
        ruv = random_unit_vector(rng)
        scatter_dir = Vec3(
            hit.normal.x + ruv.x,
            hit.normal.y + ruv.y,
            hit.normal.z + ruv.z,
        )
        if scatter_dir.length_squared() < EPSILON:
            scatter_dir = hit.normal
        albedo_color = self.albedo.value(hit.u, hit.v, hit.point)
        return True, albedo_color, Ray(hit.point, scatter_dir)

    def emitted(self) -> Vec3:
        return Vec3(0, 0, 0)


class Metal(Material):
    __slots__ = ('albedo', 'fuzz')

    def __init__(self, albedo: Vec3, fuzz: float = 0.0):
        self.albedo = albedo
        self.fuzz = min(fuzz, 1.0)

    def scatter(self, ray: Ray, hit: HitRecord, rng: random.Random) -> Tuple[bool, Vec3, Ray]:
        reflected = reflect(ray.direction.normalized(), hit.normal)
        fuzz_vec = random_in_unit_sphere(rng)
        scattered = Ray(
            hit.point,
            Vec3(
                reflected.x + self.fuzz * fuzz_vec.x,
                reflected.y + self.fuzz * fuzz_vec.y,
                reflected.z + self.fuzz * fuzz_vec.z,
            ),
        )
        absorbed = scattered.direction.dot(hit.normal) < 0
        return (not absorbed), self.albedo, scattered

    def emitted(self) -> Vec3:
        return Vec3(0, 0, 0)


class Dielectric(Material):
    __slots__ = ('ref_idx',)

    def __init__(self, ref_idx: float):
        self.ref_idx = ref_idx

    def scatter(self, ray: Ray, hit: HitRecord, rng: random.Random) -> Tuple[bool, Vec3, Ray]:
        albedo = Vec3(1.0, 1.0, 1.0)
        if hit.front_face:
            etai_over_etat = 1.0 / self.ref_idx
        else:
            etai_over_etat = self.ref_idx

        unit_dir = ray.direction.normalized()
        cos_theta = min((-unit_dir).dot(hit.normal), 1.0)
        sin_theta = math.sqrt(1.0 - cos_theta * cos_theta)

        cannot_refract = etai_over_etat * sin_theta > 1.0

        if cannot_refract:
            reflected_dir = reflect(unit_dir, hit.normal)
            return True, albedo, Ray(hit.point, reflected_dir)

        critical_angle = math.asin(min(1.0 / max(etai_over_etat, EPSILON), 1.0))
        incident_angle = math.asin(min(sin_theta, 1.0))

        if incident_angle > critical_angle:
            reflected_dir = reflect(unit_dir, hit.normal)
            return True, albedo, Ray(hit.point, reflected_dir)

        reflect_prob = schlick(cos_theta, etai_over_etat)
        if rng.random() < reflect_prob:
            reflected_dir = reflect(unit_dir, hit.normal)
            return True, albedo, Ray(hit.point, reflected_dir)

        refracted_dir = refract(unit_dir, hit.normal, etai_over_etat)
        return True, albedo, Ray(hit.point, refracted_dir)

    def emitted(self) -> Vec3:
        return Vec3(0, 0, 0)


class Emissive(Material):
    __slots__ = ('color', 'intensity')

    def __init__(self, color: Vec3, intensity: float = 1.0):
        self.color = color
        self.intensity = intensity

    def scatter(self, ray: Ray, hit: HitRecord, rng: random.Random) -> Tuple[bool, Vec3, Ray]:
        return False, Vec3(0, 0, 0), Ray(Vec3(), Vec3())

    def emitted(self) -> Vec3:
        return Vec3(
            self.color.x * self.intensity,
            self.color.y * self.intensity,
            self.color.z * self.intensity,
        )


class AABB:
    __slots__ = ('min_x', 'min_y', 'min_z', 'max_x', 'max_y', 'max_z')

    def __init__(self, minimum: Vec3 = None, maximum: Vec3 = None):
        if minimum is None:
            self.min_x = INF
            self.min_y = INF
            self.min_z = INF
            self.max_x = -INF
            self.max_y = -INF
            self.max_z = -INF
        else:
            self.min_x = minimum.x
            self.min_y = minimum.y
            self.min_z = minimum.z
            self.max_x = maximum.x
            self.max_y = maximum.y
            self.max_z = maximum.z

    def hit(self, ray: Ray, t_min: float, t_max: float) -> bool:
        ox, oy, oz = ray.origin.x, ray.origin.y, ray.origin.z
        dx, dy, dz = ray.direction.x, ray.direction.y, ray.direction.z

        for d, o, mn, mx in ((dx, ox, self.min_x, self.max_x),
                              (dy, oy, self.min_y, self.max_y),
                              (dz, oz, self.min_z, self.max_z)):
            if abs(d) < EPSILON:
                if o < mn or o > mx:
                    return False
                continue
            inv_d = 1.0 / d
            t0 = (mn - o) * inv_d
            t1 = (mx - o) * inv_d
            if inv_d < 0:
                t0, t1 = t1, t0
            t_min = max(t_min, t0)
            t_max = min(t_max, t1)
            if t_max <= t_min:
                return False
        return True

    def surface_area(self) -> float:
        dx = self.max_x - self.min_x
        dy = self.max_y - self.min_y
        dz = self.max_z - self.min_z
        return 2.0 * (dx * dy + dy * dz + dz * dx)

    @staticmethod
    def surrounding_box(box0: 'AABB', box1: 'AABB') -> 'AABB':
        return AABB(
            Vec3(
                min(box0.min_x, box1.min_x),
                min(box0.min_y, box1.min_y),
                min(box0.min_z, box1.min_z),
            ),
            Vec3(
                max(box0.max_x, box1.max_x),
                max(box0.max_y, box1.max_y),
                max(box0.max_z, box1.max_z),
            ),
        )


class Hittable(ABC):
    @abstractmethod
    def hit(self, ray: Ray, t_min: float, t_max: float) -> Optional[HitRecord]:
        pass

    @abstractmethod
    def bounding_box(self) -> AABB:
        pass


class Sphere(Hittable):
    __slots__ = ('center', 'radius', 'material', '_box')

    def __init__(self, center: Vec3, radius: float, material: Material):
        self.center = center
        self.radius = radius
        self.material = material
        r = abs(radius)
        self._box = AABB(center - Vec3(r, r, r), center + Vec3(r, r, r))

    def hit(self, ray: Ray, t_min: float, t_max: float) -> Optional[HitRecord]:
        cx, cy, cz = self.center.x, self.center.y, self.center.z
        ox, oy, oz = ray.origin.x - cx, ray.origin.y - cy, ray.origin.z - cz
        dx, dy, dz = ray.direction.x, ray.direction.y, ray.direction.z

        a = dx * dx + dy * dy + dz * dz
        half_b = ox * dx + oy * dy + oz * dz
        c = ox * ox + oy * oy + oz * oz - self.radius * self.radius
        discriminant = half_b * half_b - a * c

        if discriminant < 0:
            return None

        sqrt_d = math.sqrt(discriminant)
        inv_a = 1.0 / a
        root = (-half_b - sqrt_d) * inv_a
        if root < t_min or root > t_max:
            root = (-half_b + sqrt_d) * inv_a
            if root < t_min or root > t_max:
                return None

        px = ray.origin.x + root * dx
        py = ray.origin.y + root * dy
        pz = ray.origin.z + root * dz
        inv_r = 1.0 / self.radius
        nx = (px - cx) * inv_r
        ny = (py - cy) * inv_r
        nz = (pz - cz) * inv_r

        hit_rec = HitRecord()
        hit_rec.t = root
        hit_rec.point = Vec3(px, py, pz)
        outward_normal = Vec3(nx, ny, nz)
        hit_rec.set_face_normal(ray, outward_normal)
        hit_rec.material = self.material
        theta = math.acos(min(max(-ny, -1.0), 1.0))
        phi = math.atan2(-nz, nx) + math.pi
        hit_rec.u = phi / (2.0 * math.pi)
        hit_rec.v = theta / math.pi
        return hit_rec

    def bounding_box(self) -> AABB:
        return self._box


class Triangle(Hittable):
    __slots__ = ('v0', 'v1', 'v2', 'material', 'normal', '_box')

    def __init__(self, v0: Vec3, v1: Vec3, v2: Vec3, material: Material):
        self.v0 = v0
        self.v1 = v1
        self.v2 = v2
        self.material = material
        edge1 = v1 - v0
        edge2 = v2 - v0
        self.normal = edge1.cross(edge2).normalized()
        pad = 0.0001
        self._box = AABB(
            Vec3(
                min(v0.x, v1.x, v2.x) - pad,
                min(v0.y, v1.y, v2.y) - pad,
                min(v0.z, v1.z, v2.z) - pad,
            ),
            Vec3(
                max(v0.x, v1.x, v2.x) + pad,
                max(v0.y, v1.y, v2.y) + pad,
                max(v0.z, v1.z, v2.z) + pad,
            ),
        )

    def hit(self, ray: Ray, t_min: float, t_max: float) -> Optional[HitRecord]:
        e1x = self.v1.x - self.v0.x
        e1y = self.v1.y - self.v0.y
        e1z = self.v1.z - self.v0.z
        e2x = self.v2.x - self.v0.x
        e2y = self.v2.y - self.v0.y
        e2z = self.v2.z - self.v0.z

        dx, dy, dz = ray.direction.x, ray.direction.y, ray.direction.z
        hx = dy * e2z - dz * e2y
        hy = dz * e2x - dx * e2z
        hz = dx * e2y - dy * e2x

        a = e1x * hx + e1y * hy + e1z * hz
        if abs(a) < EPSILON:
            return None

        f = 1.0 / a
        sx = ray.origin.x - self.v0.x
        sy = ray.origin.y - self.v0.y
        sz = ray.origin.z - self.v0.z

        u = f * (sx * hx + sy * hy + sz * hz)
        if u < 0.0 or u > 1.0:
            return None

        qx = sy * e1z - sz * e1y
        qy = sz * e1x - sx * e1z
        qz = sx * e1y - sy * e1x

        v = f * (dx * qx + dy * qy + dz * qz)
        if v < 0.0 or u + v > 1.0:
            return None

        t = f * (e2x * qx + e2y * qy + e2z * qz)
        if t < t_min or t > t_max:
            return None

        hit_rec = HitRecord()
        hit_rec.t = t
        hit_rec.point = ray.at(t)
        hit_rec.set_face_normal(ray, self.normal)
        hit_rec.material = self.material
        hit_rec.u = u
        hit_rec.v = v
        return hit_rec

    def bounding_box(self) -> AABB:
        return self._box


class BVHNode(Hittable):
    __slots__ = ('left', 'right', '_box')

    def __init__(self, objects: List[Hittable], start: int, end: int):
        object_span = end - start

        if object_span == 1:
            self.left = objects[start]
            self.right = objects[start]
            self._box = self.left.bounding_box()
            return
        elif object_span == 2:
            self.left = objects[start]
            self.right = objects[start + 1]
            self._box = AABB.surrounding_box(self.left.bounding_box(), self.right.bounding_box())
            return

        parent_box = objects[start].bounding_box()
        for i in range(start + 1, end):
            parent_box = AABB.surrounding_box(parent_box, objects[i].bounding_box())
        parent_area = parent_box.surface_area()
        if parent_area < EPSILON:
            mid = start + object_span // 2
            self.left = BVHNode(objects, start, mid)
            self.right = BVHNode(objects, mid, end)
            self._box = parent_box
            return

        best_cost = float('inf')
        best_axis = 0
        best_mid = start + object_span // 2

        for axis in range(3):
            key_func = lambda obj: (obj.bounding_box().min_x if axis == 0 else
                                   (obj.bounding_box().min_y if axis == 1 else
                                    obj.bounding_box().min_z))

            sorted_objs = sorted(objects[start:end], key=key_func)
            for i in range(start, end):
                objects[i] = sorted_objs[i - start]

            left_boxes = []
            right_boxes = []

            current_box = objects[start].bounding_box()
            left_boxes.append(current_box)
            for i in range(start + 1, end - 1):
                current_box = AABB.surrounding_box(current_box, objects[i].bounding_box())
                left_boxes.append(current_box)

            current_box = objects[end - 1].bounding_box()
            right_boxes.append(current_box)
            for i in range(end - 2, start, -1):
                current_box = AABB.surrounding_box(current_box, objects[i].bounding_box())
                right_boxes.append(current_box)
            right_boxes.reverse()

            for split in range(0, len(left_boxes)):
                left_count = split + 1
                right_count = object_span - left_count
                if left_count == 0 or right_count == 0:
                    continue

                left_area = left_boxes[split].surface_area()
                right_area = right_boxes[split].surface_area()

                cost = (left_count * left_area + right_count * right_area) / parent_area

                if cost < best_cost:
                    best_cost = cost
                    best_axis = axis
                    best_mid = start + left_count

        if best_cost >= object_span:
            mid = start + object_span // 2
            self.left = BVHNode(objects, start, mid)
            self.right = BVHNode(objects, mid, end)
            self._box = parent_box
            return

        key_func = lambda obj: (obj.bounding_box().min_x if best_axis == 0 else
                               (obj.bounding_box().min_y if best_axis == 1 else
                                obj.bounding_box().min_z))
        sorted_objs = sorted(objects[start:end], key=key_func)
        for i in range(start, end):
            objects[i] = sorted_objs[i - start]

        self.left = BVHNode(objects, start, best_mid)
        self.right = BVHNode(objects, best_mid, end)
        self._box = AABB.surrounding_box(self.left.bounding_box(), self.right.bounding_box())

    def hit(self, ray: Ray, t_min: float, t_max: float) -> Optional[HitRecord]:
        if not self._box.hit(ray, t_min, t_max):
            return None

        hit_left = self.left.hit(ray, t_min, t_max)
        if hit_left is not None:
            hit_right = self.right.hit(ray, t_min, hit_left.t)
        else:
            hit_right = self.right.hit(ray, t_min, t_max)

        if hit_right is not None:
            return hit_right
        return hit_left

    def bounding_box(self) -> AABB:
        return self._box


@dataclass
class PointLight:
    position: Vec3
    color: Vec3
    intensity: float = 1.0


@dataclass
class DirectionalLight:
    direction: Vec3
    color: Vec3
    intensity: float = 1.0


class Scene:
    __slots__ = ('objects', 'lights', 'bvh', 'photon_map', 'caustic_photon_map')

    def __init__(self):
        self.objects: List[Hittable] = []
        self.lights: List = []
        self.bvh: Optional[BVHNode] = None
        self.photon_map: Optional['PhotonMap'] = None
        self.caustic_photon_map: Optional['PhotonMap'] = None

    def add_object(self, obj: Hittable):
        self.objects.append(obj)

    def add_light(self, light):
        self.lights.append(light)

    def build_bvh(self):
        if self.objects:
            objs = self.objects[:]
            self.bvh = BVHNode(objs, 0, len(objs))

    def hit(self, ray: Ray, t_min: float, t_max: float) -> Optional[HitRecord]:
        if self.bvh is not None:
            return self.bvh.hit(ray, t_min, t_max)
        closest = t_max
        result = None
        for obj in self.objects:
            hit_rec = obj.hit(ray, t_min, closest)
            if hit_rec is not None:
                closest = hit_rec.t
                result = hit_rec
        return result

    def is_shadowed(self, point: Vec3, light_dir: Vec3, distance: float) -> bool:
        shadow_ray = Ray(point, light_dir)
        hit_rec = self.hit(shadow_ray, EPSILON, distance)
        return hit_rec is not None

    def build_photon_map(self, num_photons=50000, max_depth=6, seed=None):
        if seed is None:
            seed = SCENE_SEED + 777
        all_photons = _emit_photons(self, num_photons, max_depth, seed)
        caustic_photons = [p for p in all_photons if p.flag == 2]
        global_photons = [p for p in all_photons if p.flag != 2]
        if global_photons:
            self.photon_map = PhotonMap(global_photons)
        if caustic_photons:
            self.caustic_photon_map = PhotonMap(caustic_photons)


@dataclass
class Photon:
    position: Vec3 = field(default_factory=lambda: Vec3())
    direction: Vec3 = field(default_factory=lambda: Vec3())
    power: Vec3 = field(default_factory=lambda: Vec3())
    flag: int = 0


class _KDNode:
    __slots__ = ('photon', 'left', 'right', 'axis')

    def __init__(self):
        self.photon = None
        self.left = None
        self.right = None
        self.axis = 0


class PhotonMap:
    def __init__(self, photons: List[Photon]):
        self.photons = photons[:]
        self.root = self._build(0, len(self.photons), 0)

    def _build(self, start: int, end: int, depth: int):
        if start >= end:
            return None
        axis = depth % 3
        get_coord = (lambda p: p.position.x, lambda p: p.position.y, lambda p: p.position.z)[axis]
        self.photons[start:end] = sorted(self.photons[start:end], key=get_coord)
        mid = (start + end) // 2
        node = _KDNode()
        node.photon = self.photons[mid]
        node.axis = axis
        node.left = self._build(start, mid, depth + 1)
        node.right = self._build(mid + 1, end, depth + 1)
        return node

    def gather(self, point: Vec3, max_dist_sq: float, max_count: int):
        result = []
        self._gather_impl(self.root, point, max_dist_sq, max_count, result)
        result.sort(key=lambda x: x[0])
        return result[:max_count]

    def _gather_impl(self, node, point, max_dist_sq, max_count, result):
        if node is None:
            return
        px, py, pz = node.photon.position.x, node.photon.position.y, node.photon.position.z
        dx = px - point.x
        dy = py - point.y
        dz = pz - point.z
        dist_sq = dx * dx + dy * dy + dz * dz

        if dist_sq < max_dist_sq:
            result.append((dist_sq, node.photon))

        axis = node.axis
        diff = (point.x, point.y, point.z)[axis] - (px, py, pz)[axis]
        diff_sq = diff * diff

        if diff < 0:
            first, second = node.left, node.right
        else:
            first, second = node.right, node.left

        self._gather_impl(first, point, max_dist_sq, max_count, result)
        if diff_sq < max_dist_sq:
            self._gather_impl(second, point, max_dist_sq, max_count, result)


def _emit_photons(scene: Scene, num_photons: int, max_depth: int, seed: int) -> List[Photon]:
    rng = random.Random(seed)
    photons = []

    total_power = 0.0
    for light in scene.lights:
        if isinstance(light, PointLight):
            total_power += (light.color.x + light.color.y + light.color.z) * light.intensity
        elif isinstance(light, DirectionalLight):
            total_power += (light.color.x + light.color.y + light.color.z) * light.intensity

    if total_power < EPSILON:
        return photons

    for light in scene.lights:
        if isinstance(light, PointLight):
            light_power = (light.color.x + light.color.y + light.color.z) * light.intensity
            n_light = max(1, int(num_photons * light_power / total_power))
            power_per_photon = Vec3(
                light.color.x * light.intensity / n_light,
                light.color.y * light.intensity / n_light,
                light.color.z * light.intensity / n_light,
            )
            for _ in range(n_light):
                direction = random_unit_vector(rng)
                ray = Ray(light.position, direction)
                _trace_photon(ray, scene, power_per_photon, 0, max_depth, rng, photons, False)

        elif isinstance(light, DirectionalLight):
            light_power = (light.color.x + light.color.y + light.color.z) * light.intensity
            n_light = max(1, int(num_photons * light_power / total_power))
            power_per_photon = Vec3(
                light.color.x * light.intensity / n_light,
                light.color.y * light.intensity / n_light,
                light.color.z * light.intensity / n_light,
            )
            ldx, ldy, ldz = -light.direction.x, -light.direction.y, -light.direction.z
            for _ in range(n_light):
                origin = Vec3(
                    rng.uniform(-10, 10),
                    rng.uniform(0.01, 0.02),
                    rng.uniform(-10, 10),
                )
                ray = Ray(origin, Vec3(ldx, ldy, ldz))
                _trace_photon(ray, scene, power_per_photon, 0, max_depth, rng, photons, False)

    return photons


def _trace_photon(ray: Ray, scene: Scene, power: Vec3, depth: int, max_depth: int,
                  rng: random.Random, photons: List[Photon], is_caustic: bool):
    if depth >= max_depth:
        return

    hit_rec = scene.hit(ray, EPSILON, INF)
    if hit_rec is None:
        return

    is_specular = isinstance(hit_rec.material, (Metal, Dielectric))

    if depth > 0 and not is_specular:
        flag = 2 if is_caustic else 1
        photons.append(Photon(hit_rec.point, ray.direction, power, flag))

    scattered_result = hit_rec.material.scatter(ray, hit_rec, rng)
    if not scattered_result[0]:
        if isinstance(hit_rec.material, Emissive):
            return
        return

    _, attenuation, scattered = scattered_result

    p = max(attenuation.x, attenuation.y, attenuation.z)
    if p < EPSILON:
        return
    if depth > 1 and rng.random() > p:
        return

    new_power = Vec3(
        power.x * attenuation.x / p,
        power.y * attenuation.y / p,
        power.z * attenuation.z / p,
    )

    new_caustic = is_caustic or is_specular
    _trace_photon(scattered, scene, new_power, depth + 1, max_depth, rng, photons, new_caustic)


class Camera:
    __slots__ = ('origin', 'horizontal', 'vertical', 'lower_left_corner', 'u', 'v', 'w', 'lens_radius')

    def __init__(
        self,
        lookfrom: Vec3,
        lookat: Vec3,
        vup: Vec3,
        vfov: float,
        aspect_ratio: float,
        aperture: float = 0.0,
        focus_dist: float = None,
    ):
        theta = math.radians(vfov)
        h = math.tan(theta / 2.0)
        viewport_height = 2.0 * h
        viewport_width = aspect_ratio * viewport_height

        self.w = (lookfrom - lookat).normalized()
        self.u = vup.cross(self.w).normalized()
        self.v = self.w.cross(self.u)

        self.origin = lookfrom
        self.horizontal = focus_dist * viewport_width * self.u
        self.vertical = focus_dist * viewport_height * self.v
        self.lower_left_corner = (
            self.origin
            - self.horizontal * 0.5
            - self.vertical * 0.5
            - focus_dist * self.w
        )
        self.lens_radius = aperture / 2.0

    def get_ray(self, s: float, t: float, rng: random.Random) -> Ray:
        if self.lens_radius > 0:
            rd = random_in_unit_sphere(rng)
            offset = Vec3(
                self.u.x * rd.x * self.lens_radius + self.v.x * rd.y * self.lens_radius,
                self.u.y * rd.x * self.lens_radius + self.v.y * rd.y * self.lens_radius,
                self.u.z * rd.x * self.lens_radius + self.v.z * rd.y * self.lens_radius,
            )
        else:
            offset = Vec3(0, 0, 0)

        llc = self.lower_left_corner
        h = self.horizontal
        v = self.vertical
        o = self.origin

        direction = Vec3(
            llc.x + s * h.x + t * v.x - o.x - offset.x,
            llc.y + s * h.y + t * v.y - o.y - offset.y,
            llc.z + s * h.z + t * v.z - o.z - offset.z,
        )
        origin = Vec3(o.x + offset.x, o.y + offset.y, o.z + offset.z)
        return Ray(origin, direction)


def ray_color(ray: Ray, scene: Scene, depth: int, max_depth: int, rng: random.Random) -> Vec3:
    if depth <= 0:
        return Vec3(0, 0, 0)

    hit_rec = scene.hit(ray, EPSILON, INF)
    if hit_rec is None:
        dx, dy, dz = ray.direction.x, ray.direction.y, ray.direction.z
        l = math.sqrt(dx * dx + dy * dy + dz * dz)
        t = 0.5 * (dy / l + 1.0)
        inv = 1.0 - t
        return Vec3(inv + 0.5 * t, inv + 0.2 * t, inv * 1.0 + t)

    emitted = hit_rec.material.emitted()

    scattered_result = hit_rec.material.scatter(ray, hit_rec, rng)
    if not scattered_result[0]:
        return emitted

    _, attenuation, scattered = scattered_result

    direct_r = direct_g = direct_b = 0.0
    ar, ag, ab = attenuation.x, attenuation.y, attenuation.z
    nx, ny, nz = hit_rec.normal.x, hit_rec.normal.y, hit_rec.normal.z

    for light in scene.lights:
        if isinstance(light, PointLight):
            lx = light.position.x - hit_rec.point.x
            ly = light.position.y - hit_rec.point.y
            lz = light.position.z - hit_rec.point.z
            dist = math.sqrt(lx * lx + ly * ly + lz * lz)
            if dist < EPSILON:
                continue
            inv_dist = 1.0 / dist
            ldx, ldy, ldz = lx * inv_dist, ly * inv_dist, lz * inv_dist

            light_dir = Vec3(ldx, ldy, ldz)
            if scene.is_shadowed(hit_rec.point, light_dir, dist):
                continue

            ndotl = max(0.0, nx * ldx + ny * ldy + nz * ldz)

            vx = -ray.direction.x
            vy = -ray.direction.y
            vz = -ray.direction.z
            vl = math.sqrt(vx * vx + vy * vy + vz * vz)
            if vl > EPSILON:
                inv_vl = 1.0 / vl
                vx *= inv_vl
                vy *= inv_vl
                vz *= inv_vl

            hx_ = ldx + vx
            hy_ = ldy + vy
            hz_ = ldz + vz
            hl = math.sqrt(hx_ * hx_ + hy_ * hy_ + hz_ * hz_)
            if hl > EPSILON:
                inv_hl = 1.0 / hl
                hx_ *= inv_hl
                hy_ *= inv_hl
                hz_ *= inv_hl

            ndoth = max(0.0, nx * hx_ + ny * hy_ + nz * hz_)
            spec = ndoth ** 32.0

            li = light.intensity
            lcr, lcg, lcb = light.color.x * li, light.color.y * li, light.color.z * li

            direct_r += (ar * lcr * ndotl + lcr * spec * 0.3)
            direct_g += (ag * lcg * ndotl + lcg * spec * 0.3)
            direct_b += (ab * lcb * ndotl + lcb * spec * 0.3)

        elif isinstance(light, DirectionalLight):
            ldx, ldy, ldz = -light.direction.x, -light.direction.y, -light.direction.z

            light_dir = Vec3(ldx, ldy, ldz)
            if scene.is_shadowed(hit_rec.point, light_dir, INF):
                continue

            ndotl = max(0.0, nx * ldx + ny * ldy + nz * ldz)

            vx = -ray.direction.x
            vy = -ray.direction.y
            vz = -ray.direction.z
            vl = math.sqrt(vx * vx + vy * vy + vz * vz)
            if vl > EPSILON:
                inv_vl = 1.0 / vl
                vx *= inv_vl
                vy *= inv_vl
                vz *= inv_vl

            hx_ = ldx + vx
            hy_ = ldy + vy
            hz_ = ldz + vz
            hl = math.sqrt(hx_ * hx_ + hy_ * hy_ + hz_ * hz_)
            if hl > EPSILON:
                inv_hl = 1.0 / hl
                hx_ *= inv_hl
                hy_ *= inv_hl
                hz_ *= inv_hl

            ndoth = max(0.0, nx * hx_ + ny * hy_ + nz * hz_)
            spec = ndoth ** 32.0

            li = light.intensity
            lcr, lcg, lcb = light.color.x * li, light.color.y * li, light.color.z * li

            direct_r += (ar * lcr * ndotl + lcr * spec * 0.3)
            direct_g += (ag * lcg * ndotl + lcg * spec * 0.3)
            direct_b += (ab * lcb * ndotl + lcb * spec * 0.3)

    caustic_r = caustic_g = caustic_b = 0.0
    if scene.caustic_photon_map is not None and not isinstance(hit_rec.material, (Metal, Dielectric)):
        gathered = scene.caustic_photon_map.gather(hit_rec.point, max_dist_sq=2.0, max_count=50)
        if gathered:
            r_sq = gathered[-1][0]
            if r_sq > EPSILON:
                area = math.pi * r_sq
                for dist_sq, photon in gathered:
                    ndotl = max(0.0, nx * (-photon.direction.x) +
                                        ny * (-photon.direction.y) +
                                        nz * (-photon.direction.z))
                    caustic_r += photon.power.x * ndotl
                    caustic_g += photon.power.y * ndotl
                    caustic_b += photon.power.z * ndotl
                inv_area = 1.0 / area
                caustic_r *= inv_area
                caustic_g *= inv_area
                caustic_b *= inv_area

    p = max(ar, ag, ab)
    if depth < max_depth - 2:
        if rng.random() > p:
            return Vec3(
                emitted.x + direct_r * 0.7 + caustic_r,
                emitted.y + direct_g * 0.7 + caustic_g,
                emitted.z + direct_b * 0.7 + caustic_b,
            )
        inv_p = 1.0 / p
    else:
        inv_p = 1.0

    indirect = ray_color(scattered, scene, depth - 1, max_depth, rng)

    return Vec3(
        emitted.x + direct_r * 0.7 + attenuation.x * indirect.x * 0.3 * inv_p + caustic_r,
        emitted.y + direct_g * 0.7 + attenuation.y * indirect.y * 0.3 * inv_p + caustic_g,
        emitted.z + direct_b * 0.7 + attenuation.z * indirect.z * 0.3 * inv_p + caustic_b,
    )


def create_demo_scene(seed: int = SCENE_SEED, use_photon_map: bool = False) -> Scene:
    rng = random.Random(seed)
    scene = Scene()

    checker = CheckerTexture(
        SolidColor(Vec3(0.2, 0.2, 0.2)),
        SolidColor(Vec3(0.6, 0.6, 0.6)),
        scale=2.0,
    )
    ground_mat = Lambertian(checker)
    scene.add_object(Sphere(Vec3(0, -1000, 0), 1000, ground_mat))

    mat1 = Lambertian(Vec3(0.7, 0.1, 0.1))
    scene.add_object(Sphere(Vec3(-3, 1, 0), 1.0, mat1))

    mat2 = Metal(Vec3(0.8, 0.85, 0.9), 0.02)
    scene.add_object(Sphere(Vec3(0, 1, 0), 1.0, mat2))

    mat3 = Dielectric(1.5)
    scene.add_object(Sphere(Vec3(3, 1, 0), 1.0, mat3))
    scene.add_object(Sphere(Vec3(3, 1, 0), -0.8, mat3))

    mat_emissive = Emissive(Vec3(1, 0.9, 0.7), 5.0)
    scene.add_object(Sphere(Vec3(-1, 4, -3), 1.5, mat_emissive))

    tri_mat = Lambertian(Vec3(0.2, 0.6, 0.3))
    scene.add_object(
        Triangle(
            Vec3(-6, 0, -3),
            Vec3(-3, 3, -5),
            Vec3(0, 0, -3),
            tri_mat,
        )
    )

    for i in range(5):
        center = Vec3(
            rng.uniform(-8, 8),
            0.2,
            rng.uniform(-6, 2),
        )
        choose_mat = rng.random()
        if choose_mat < 0.6:
            mat = Lambertian(Vec3(
                rng.uniform(0.2, 0.8),
                rng.uniform(0.2, 0.8),
                rng.uniform(0.2, 0.8),
            ))
        elif choose_mat < 0.85:
            mat = Metal(Vec3(
                rng.uniform(0.4, 0.9),
                rng.uniform(0.4, 0.9),
                rng.uniform(0.4, 0.9),
            ), rng.uniform(0, 0.3))
        else:
            mat = Dielectric(1.5)
        scene.add_object(Sphere(center, 0.2, mat))

    wall_mat = Lambertian(Vec3(0.6, 0.6, 0.5))
    scene.add_object(
        Triangle(
            Vec3(-10, 0, -8),
            Vec3(10, 0, -8),
            Vec3(10, 8, -8),
            wall_mat,
        )
    )
    scene.add_object(
        Triangle(
            Vec3(-10, 0, -8),
            Vec3(10, 8, -8),
            Vec3(-10, 8, -8),
            wall_mat,
        )
    )

    scene.add_light(PointLight(Vec3(-1, 4, -3), Vec3(1, 0.9, 0.7), 1.0))
    scene.add_light(PointLight(Vec3(5, 5, 5), Vec3(0.8, 0.8, 1.0), 0.6))
    scene.add_light(DirectionalLight(Vec3(-0.5, -1, -0.3), Vec3(0.6, 0.6, 0.5), 0.4))

    scene.build_bvh()

    if use_photon_map:
        scene.build_photon_map(num_photons=50000, max_depth=6, seed=seed + 777)

    return scene


def create_textured_scene(seed: int = SCENE_SEED, texture_path: str = None, use_photon_map: bool = False) -> Scene:
    scene = Scene()

    checker = CheckerTexture(
        SolidColor(Vec3(0.1, 0.1, 0.1)),
        SolidColor(Vec3(0.7, 0.7, 0.7)),
        scale=1.0,
    )
    ground_mat = Lambertian(checker)
    scene.add_object(Sphere(Vec3(0, -1000, 0), 1000, ground_mat))

    if texture_path and os.path.exists(texture_path):
        tex = ImageTexture(texture_path)
        mat_textured = Lambertian(tex)
    else:
        mat_textured = Lambertian(CheckerTexture(
            SolidColor(Vec3(0.9, 0.2, 0.2)),
            SolidColor(Vec3(0.2, 0.2, 0.9)),
            scale=5.0,
        ))
    scene.add_object(Sphere(Vec3(-3, 1.5, 0), 1.5, mat_textured))

    caustic_glass = Dielectric(1.5)
    scene.add_object(Sphere(Vec3(3, 1.5, 2), 1.5, caustic_glass))

    mat_metal = Metal(Vec3(0.9, 0.85, 0.8), 0.01)
    scene.add_object(Sphere(Vec3(0, 1.5, -3), 1.5, mat_metal))

    mat_emissive = Emissive(Vec3(1, 0.95, 0.8), 8.0)
    scene.add_object(Sphere(Vec3(0, 5, 0), 0.5, mat_emissive))

    scene.add_light(PointLight(Vec3(0, 5, 0), Vec3(1, 0.95, 0.8), 2.0))
    scene.add_light(PointLight(Vec3(-5, 4, 3), Vec3(0.7, 0.7, 1.0), 0.8))
    scene.add_light(DirectionalLight(Vec3(-0.3, -1, -0.5), Vec3(0.5, 0.5, 0.4), 0.3))

    scene.build_bvh()

    if use_photon_map:
        scene.build_photon_map(num_photons=80000, max_depth=8, seed=seed + 999)

    return scene


def _render_tile_worker(args):
    (
        y_start, y_end, width, height,
        origin, lower_left, horiz, vert,
        cam_u, cam_v, lens_radius,
        max_depth, base_samples, adaptive_threshold, adaptive_max_samples,
        seed, scene_seed,
    ) = args

    rng = random.Random(seed)
    scene = create_demo_scene(scene_seed)

    camera = Camera.__new__(Camera)
    camera.origin = Vec3(origin)
    camera.lower_left_corner = Vec3(lower_left)
    camera.horizontal = Vec3(horiz)
    camera.vertical = Vec3(vert)
    camera.u = Vec3(cam_u)
    camera.v = Vec3(cam_v)
    camera.w = Vec3(0, 0, 0)
    camera.lens_radius = lens_radius

    tile_h = y_end - y_start
    pixels = np.zeros((tile_h, width, 3), dtype=np.float64)
    sample_counts = np.ones((tile_h, width), dtype=np.int32) * base_samples

    inv_w = 1.0 / max(width - 1, 1)
    inv_h = 1.0 / max(height - 1, 1)

    def trace_pixel(i, y, num_samples):
        cr, cg, cb = 0.0, 0.0, 0.0
        pixel_y = height - 1 - y
        for _ in range(num_samples):
            u = (i + rng.random()) * inv_w
            v = (pixel_y + rng.random()) * inv_h
            ray = camera.get_ray(u, v, rng)
            color = ray_color(ray, scene, max_depth, max_depth, rng)
            cr += color.x
            cg += color.y
            cb += color.z
        return cr, cg, cb

    for j in range(tile_h):
        y = y_start + j
        for i in range(width):
            cr, cg, cb = trace_pixel(i, y, base_samples)
            pixels[j, i, 0] = cr
            pixels[j, i, 1] = cg
            pixels[j, i, 2] = cb

    if adaptive_max_samples > base_samples:
        for j in range(tile_h):
            y = y_start + j
            for i in range(width):
                need_more = False
                neighbors = []
                if i > 0:
                    neighbors.append(pixels[j, i - 1])
                if i < width - 1:
                    neighbors.append(pixels[j, i + 1])
                if j > 0:
                    neighbors.append(pixels[j - 1, i])
                if j < tile_h - 1:
                    neighbors.append(pixels[j + 1, i])

                if neighbors:
                    curr = pixels[j, i]
                    max_diff = 0.0
                    for n in neighbors:
                        diff_r = abs(curr[0] - n[0]) / max(base_samples, 1)
                        diff_g = abs(curr[1] - n[1]) / max(base_samples, 1)
                        diff_b = abs(curr[2] - n[2]) / max(base_samples, 1)
                        max_diff = max(max_diff, diff_r, diff_g, diff_b)

                    if max_diff > adaptive_threshold:
                        need_more = True

                if need_more:
                    extra_samples = adaptive_max_samples - base_samples
                    cr, cg, cb = trace_pixel(i, y, extra_samples)
                    pixels[j, i, 0] += cr
                    pixels[j, i, 1] += cg
                    pixels[j, i, 2] += cb
                    sample_counts[j, i] = adaptive_max_samples

    for j in range(tile_h):
        for i in range(width):
            inv_s = 1.0 / sample_counts[j, i]
            pixels[j, i, 0] *= inv_s
            pixels[j, i, 1] *= inv_s
            pixels[j, i, 2] *= inv_s

    return y_start, pixels


def render(
    scene: Scene,
    width: int = 800,
    height: int = 600,
    samples_per_pixel: int = 100,
    max_depth: int = 8,
    num_workers: int = 4,
    lookfrom: Vec3 = None,
    lookat: Vec3 = None,
    output_path: str = 'output.png',
    scene_seed: int = SCENE_SEED,
    adaptive_threshold: float = 0.1,
    adaptive_max_samples: int = 0,
):
    if lookfrom is None:
        lookfrom = Vec3(8, 3, 6)
    if lookat is None:
        lookat = Vec3(0, 1, 0)

    if adaptive_max_samples <= samples_per_pixel:
        adaptive_max_samples = samples_per_pixel
        base_samples = samples_per_pixel
    else:
        base_samples = samples_per_pixel

    aspect_ratio = width / height
    camera = Camera(
        lookfrom=lookfrom,
        lookat=lookat,
        vup=Vec3(0, 1, 0),
        vfov=35,
        aspect_ratio=aspect_ratio,
        aperture=0.05,
        focus_dist=(lookfrom - lookat).length(),
    )

    cam_data = (
        camera.origin._get_data().copy(),
        camera.lower_left_corner._get_data().copy(),
        camera.horizontal._get_data().copy(),
        camera.vertical._get_data().copy(),
        camera.u._get_data().copy(),
        camera.v._get_data().copy(),
        camera.lens_radius,
    )

    num_tiles = num_workers * 2
    tile_size = max(1, height // num_tiles)
    tiles = []
    base_rng = random.Random(scene_seed + 1000)

    for y_start in range(0, height, tile_size):
        y_end = min(y_start + tile_size, height)
        tiles.append((
            y_start, y_end, width, height,
            cam_data[0], cam_data[1], cam_data[2], cam_data[3],
            cam_data[4], cam_data[5], cam_data[6],
            max_depth, base_samples, adaptive_threshold, adaptive_max_samples,
            int(base_rng.randint(0, 2**31)),
            scene_seed,
        ))

    image = np.zeros((height, width, 3), dtype=np.float64)
    start_time = time.time()

    print(f"Scene: {len(scene.objects)} objects, {len(scene.lights)} lights", flush=True)
    if adaptive_max_samples > base_samples:
        print(f"Adaptive sampling: {base_samples} base, up to {adaptive_max_samples} on edges (threshold={adaptive_threshold})", flush=True)
        print(f"Rendering {width}x{height}, depth {max_depth}", flush=True)
        est_rays_min = width * height * base_samples
        est_rays_max = width * height * adaptive_max_samples
        print(f"Estimated rays: {est_rays_min:,} ~ {est_rays_max:,}", flush=True)
    else:
        print(f"Rendering {width}x{height}, {samples_per_pixel} samples, depth {max_depth}", flush=True)
        est_rays = width * height * samples_per_pixel
        print(f"Estimated total rays: {est_rays:,}", flush=True)

    progress_log = open('render_progress.log', 'w')
    progress_log.write(f"[{time.strftime('%H:%M:%S')}] Scene: {len(scene.objects)} objects, {len(scene.lights)} lights\n")
    if adaptive_max_samples > base_samples:
        progress_log.write(f"[{time.strftime('%H:%M:%S')}] Adaptive: {base_samples} base → {adaptive_max_samples} max (thresh={adaptive_threshold})\n")
        progress_log.write(f"[{time.strftime('%H:%M:%S')}] Rendering {width}x{height}, depth {max_depth}\n")
    else:
        progress_log.write(f"[{time.strftime('%H:%M:%S')}] Rendering {width}x{height}, {samples_per_pixel} samples, depth {max_depth}\n")
    progress_log.flush()

    try:
        with ProcessPoolExecutor(max_workers=num_workers) as executor:
            futures = {executor.submit(_render_tile_worker, tile): tile for tile in tiles}
            completed = 0
            for future in as_completed(futures):
                try:
                    tile_y_start, tile_pixels = future.result()
                    tile_h = tile_pixels.shape[0]
                    image[tile_y_start:tile_y_start + tile_h] = tile_pixels
                    completed += 1
                    elapsed = time.time() - start_time
                    progress = completed / len(tiles) * 100
                    eta = elapsed / completed * (len(tiles) - completed)
                    print(f"[{time.strftime('%H:%M:%S')}] Tile {completed}/{len(tiles)} ({progress:.0f}%) - {elapsed:.1f}s, ETA: {eta:.1f}s", flush=True)
                    progress_log.write(f"[{time.strftime('%H:%M:%S')}] Tile {completed}/{len(tiles)} ({progress:.0f}%) - {elapsed:.1f}s, ETA {eta:.1f}s\n")
                    progress_log.flush()
                except Exception as e:
                    print(f"  Tile failed: {e}", flush=True)
    except Exception as e:
        print(f"Multi-process failed ({e}), falling back to single thread...", flush=True)
        rng = random.Random(scene_seed + 1)
        inv_w = 1.0 / max(width - 1, 1)
        inv_h = 1.0 / max(height - 1, 1)

        def trace_pixel(i, pixel_y, num_samples):
            cr, cg, cb = 0.0, 0.0, 0.0
            for _ in range(num_samples):
                u = (i + rng.random()) * inv_w
                v = (pixel_y + rng.random()) * inv_h
                ray = camera.get_ray(u, v, rng)
                color = ray_color(ray, scene, max_depth, max_depth, rng)
                cr += color.x
                cg += color.y
                cb += color.z
            return cr, cg, cb

        pixels_accum = np.zeros((height, width, 3), dtype=np.float64)
        sample_counts = np.ones((height, width), dtype=np.int32) * base_samples

        for j in range(height):
            pixel_y = height - 1 - j
            for i in range(width):
                cr, cg, cb = trace_pixel(i, pixel_y, base_samples)
                pixels_accum[j, i, 0] = cr
                pixels_accum[j, i, 1] = cg
                pixels_accum[j, i, 2] = cb

        if adaptive_max_samples > base_samples:
            for j in range(height):
                for i in range(width):
                    need_more = False
                    neighbors = []
                    if i > 0:
                        neighbors.append(pixels_accum[j, i - 1])
                    if i < width - 1:
                        neighbors.append(pixels_accum[j, i + 1])
                    if j > 0:
                        neighbors.append(pixels_accum[j - 1, i])
                    if j < height - 1:
                        neighbors.append(pixels_accum[j + 1, i])

                    if neighbors:
                        curr = pixels_accum[j, i]
                        max_diff = 0.0
                        for n in neighbors:
                            diff_r = abs(curr[0] - n[0]) / max(base_samples, 1)
                            diff_g = abs(curr[1] - n[1]) / max(base_samples, 1)
                            diff_b = abs(curr[2] - n[2]) / max(base_samples, 1)
                            max_diff = max(max_diff, diff_r, diff_g, diff_b)

                        if max_diff > adaptive_threshold:
                            need_more = True

                    if need_more:
                        pixel_y = height - 1 - j
                        extra_samples = adaptive_max_samples - base_samples
                        cr, cg, cb = trace_pixel(i, pixel_y, extra_samples)
                        pixels_accum[j, i, 0] += cr
                        pixels_accum[j, i, 1] += cg
                        pixels_accum[j, i, 2] += cb
                        sample_counts[j, i] = adaptive_max_samples

        for j in range(height):
            for i in range(width):
                inv_s = 1.0 / sample_counts[j, i]
                image[j, i, 0] = pixels_accum[j, i, 0] * inv_s
                image[j, i, 1] = pixels_accum[j, i, 1] * inv_s
                image[j, i, 2] = pixels_accum[j, i, 2] * inv_s

            if (j + 1) % 10 == 0 or j == height - 1:
                elapsed = time.time() - start_time
                progress = (j + 1) / height * 100
                eta = elapsed / (j + 1) * (height - j - 1)
                print(f"[{time.strftime('%H:%M:%S')}] Row {j+1}/{height} ({progress:.0f}%) - {elapsed:.1f}s, ETA: {eta:.1f}s", flush=True)
                progress_log.write(f"[{time.strftime('%H:%M:%S')}] Row {j+1}/{height} ({progress:.0f}%) - {elapsed:.1f}s, ETA {eta:.1f}s\n")
                progress_log.flush()

    progress_log.close()

    image = np.clip(image, 0, None)
    image = np.sqrt(image)
    image = np.clip(image * 255, 0, 255).astype(np.uint8)
    image_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
    cv2.imwrite(output_path, image_bgr)

    total_time = time.time() - start_time
    print(f"\nRender complete in {total_time:.2f}s", flush=True)
    print(f"Output: {output_path}", flush=True)

    with open('render_log.txt', 'w') as f:
        f.write(f"Render time: {total_time:.2f}s\n")
        f.write(f"Resolution: {width}x{height}\n")
        f.write(f"Base samples: {base_samples}\n")
        f.write(f"Adaptive max samples: {adaptive_max_samples}\n")
        f.write(f"Adaptive threshold: {adaptive_threshold}\n")
        f.write(f"Max depth: {max_depth}\n")
        f.write(f"Workers: {num_workers}\n")
        f.write(f"Output: {output_path}\n")

    return image


@dataclass
class AnimKeyframe:
    time: float
    lookfrom: Vec3
    lookat: Vec3
    vfov: float = 35.0


def _catmull_rom_vec3(t: float, p0: Vec3, p1: Vec3, p2: Vec3, p3: Vec3) -> Vec3:
    t2 = t * t
    t3 = t2 * t
    c0 = 2.0 * p1
    c1 = -p0 + p2
    c2 = 2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3
    c3 = -p0 + 3.0 * p1 - 3.0 * p2 + p3
    result = (c0 + c1 * t + c2 * t2 + c3 * t3) * 0.5
    return result


def _catmull_rom_float(t: float, p0: float, p1: float, p2: float, p3: float) -> float:
    t2 = t * t
    t3 = t2 * t
    c0 = 2.0 * p1
    c1 = -p0 + p2
    c2 = 2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3
    c3 = -p0 + 3.0 * p1 - 3.0 * p2 + p3
    return (c0 + c1 * t + c2 * t2 + c3 * t3) * 0.5


def interpolate_keyframes(keyframes: List[AnimKeyframe], t: float):
    if len(keyframes) == 0:
        return Vec3(8, 3, 6), Vec3(0, 1, 0), 35.0
    if len(keyframes) == 1:
        kf = keyframes[0]
        return kf.lookfrom, kf.lookat, kf.vfov

    t = max(0.0, min(1.0, t))

    for i in range(len(keyframes) - 1):
        if keyframes[i].time <= t <= keyframes[i + 1].time:
            dt = keyframes[i + 1].time - keyframes[i].time
            if dt < EPSILON:
                kf = keyframes[i]
                return kf.lookfrom, kf.lookat, kf.vfov
            local_t = (t - keyframes[i].time) / dt

            i0 = max(0, i - 1)
            i1 = i
            i2 = i + 1
            i3 = min(len(keyframes) - 1, i + 2)

            lookfrom = _catmull_rom_vec3(local_t,
                keyframes[i0].lookfrom, keyframes[i1].lookfrom,
                keyframes[i2].lookfrom, keyframes[i3].lookfrom)
            lookat = _catmull_rom_vec3(local_t,
                keyframes[i0].lookat, keyframes[i1].lookat,
                keyframes[i2].lookat, keyframes[i3].lookat)
            vfov = _catmull_rom_float(local_t,
                keyframes[i0].vfov, keyframes[i1].vfov,
                keyframes[i2].vfov, keyframes[i3].vfov)

            return lookfrom, lookat, vfov

    kf = keyframes[-1]
    return kf.lookfrom, kf.lookat, kf.vfov


def render_animation(
    scene_builder,
    keyframes: List[AnimKeyframe],
    width: int = 320,
    height: int = 240,
    samples_per_pixel: int = 8,
    max_depth: int = 5,
    num_frames: int = 30,
    output_dir: str = 'frames',
    fps: int = 24,
    adaptive_threshold: float = 0.1,
    adaptive_max_samples: int = 0,
    scene_seed: int = SCENE_SEED,
):
    os.makedirs(output_dir, exist_ok=True)

    total_start = time.time()

    for frame_idx in range(num_frames):
        frame_t = frame_idx / max(num_frames - 1, 1)
        lookfrom, lookat, vfov = interpolate_keyframes(keyframes, frame_t)

        scene = scene_builder(scene_seed)

        aspect_ratio = width / height
        focus_dist = (lookfrom - lookat).length()
        camera = Camera(
            lookfrom=lookfrom,
            lookat=lookat,
            vup=Vec3(0, 1, 0),
            vfov=vfov,
            aspect_ratio=aspect_ratio,
            aperture=0.05,
            focus_dist=focus_dist,
        )

        output_path = os.path.join(output_dir, f'frame_{frame_idx:04d}.png')

        if adaptive_max_samples <= samples_per_pixel:
            adaptive_max_samples = samples_per_pixel
            base_samples = samples_per_pixel
        else:
            base_samples = samples_per_pixel

        rng = random.Random(scene_seed + frame_idx + 1)
        inv_w = 1.0 / max(width - 1, 1)
        inv_h = 1.0 / max(height - 1, 1)

        def trace_pixel(i, pixel_y, num_samples):
            cr, cg, cb = 0.0, 0.0, 0.0
            for _ in range(num_samples):
                u = (i + rng.random()) * inv_w
                v = (pixel_y + rng.random()) * inv_h
                ray = camera.get_ray(u, v, rng)
                color = ray_color(ray, scene, max_depth, max_depth, rng)
                cr += color.x
                cg += color.y
                cb += color.z
            return cr, cg, cb

        pixels_accum = np.zeros((height, width, 3), dtype=np.float64)
        sample_counts = np.ones((height, width), dtype=np.int32) * base_samples

        frame_start = time.time()
        for j in range(height):
            pixel_y = height - 1 - j
            for i in range(width):
                cr, cg, cb = trace_pixel(i, pixel_y, base_samples)
                pixels_accum[j, i, 0] = cr
                pixels_accum[j, i, 1] = cg
                pixels_accum[j, i, 2] = cb

        edge_count = 0
        if adaptive_max_samples > base_samples:
            for j in range(height):
                for i in range(width):
                    need_more = False
                    neighbors = []
                    if i > 0:
                        neighbors.append(pixels_accum[j, i - 1])
                    if i < width - 1:
                        neighbors.append(pixels_accum[j, i + 1])
                    if j > 0:
                        neighbors.append(pixels_accum[j - 1, i])
                    if j < height - 1:
                        neighbors.append(pixels_accum[j + 1, i])

                    if neighbors:
                        curr = pixels_accum[j, i]
                        max_diff = 0.0
                        for n in neighbors:
                            diff_r = abs(curr[0] - n[0]) / max(base_samples, 1)
                            diff_g = abs(curr[1] - n[1]) / max(base_samples, 1)
                            diff_b = abs(curr[2] - n[2]) / max(base_samples, 1)
                            max_diff = max(max_diff, diff_r, diff_g, diff_b)

                        if max_diff > adaptive_threshold:
                            need_more = True

                    if need_more:
                        edge_count += 1
                        pixel_y = height - 1 - j
                        extra_samples = adaptive_max_samples - base_samples
                        cr, cg, cb = trace_pixel(i, pixel_y, extra_samples)
                        pixels_accum[j, i, 0] += cr
                        pixels_accum[j, i, 1] += cg
                        pixels_accum[j, i, 2] += cb
                        sample_counts[j, i] = adaptive_max_samples

        image = np.zeros((height, width, 3), dtype=np.float64)
        for j in range(height):
            for i in range(width):
                inv_s = 1.0 / sample_counts[j, i]
                image[j, i, 0] = pixels_accum[j, i, 0] * inv_s
                image[j, i, 1] = pixels_accum[j, i, 1] * inv_s
                image[j, i, 2] = pixels_accum[j, i, 2] * inv_s

        image = np.clip(image, 0, None)
        image = np.sqrt(image)
        image = np.clip(image * 255, 0, 255).astype(np.uint8)
        image_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        cv2.imwrite(output_path, image_bgr)

        frame_time = time.time() - frame_start
        elapsed = time.time() - total_start
        eta = elapsed / (frame_idx + 1) * (num_frames - frame_idx - 1)
        print(f"Frame {frame_idx+1}/{num_frames} ({frame_t:.2f}) - {frame_time:.1f}s, Total: {elapsed:.1f}s, ETA: {eta:.1f}s", flush=True)

    total_time = time.time() - total_start
    print(f"\nAnimation complete: {num_frames} frames in {total_time:.1f}s", flush=True)
    print(f"Frames saved to: {output_dir}/", flush=True)

    video_path = os.path.join(output_dir, 'animation.avi')
    try:
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        out = cv2.VideoWriter(video_path, fourcc, fps, (width, height))
        for frame_idx in range(num_frames):
            frame_path = os.path.join(output_dir, f'frame_{frame_idx:04d}.png')
            frame_img = cv2.imread(frame_path)
            if frame_img is not None:
                out.write(frame_img)
        out.release()
        print(f"Video saved to: {video_path}", flush=True)
    except Exception as e:
        print(f"Video creation failed: {e}", flush=True)

    return total_time


if __name__ == '__main__':
    multiprocessing.freeze_support()

    num_workers = max(1, multiprocessing.cpu_count() - 1)

    width = 800
    height = 600
    samples = 64
    max_depth = 6
    adaptive_threshold = 0.1
    adaptive_max_samples = 0

    if len(sys.argv) > 1:
        width = int(sys.argv[1])
    if len(sys.argv) > 2:
        height = int(sys.argv[2])
    if len(sys.argv) > 3:
        samples = int(sys.argv[3])
    if len(sys.argv) > 4:
        max_depth = int(sys.argv[4])
    if len(sys.argv) > 5:
        num_workers = int(sys.argv[5])
    if len(sys.argv) > 6:
        adaptive_max_samples = int(sys.argv[6])
    if len(sys.argv) > 7:
        adaptive_threshold = float(sys.argv[7])

    scene = create_demo_scene()
    render(
        scene,
        width=width,
        height=height,
        samples_per_pixel=samples,
        max_depth=max_depth,
        num_workers=num_workers,
        output_path='output.png',
        adaptive_threshold=adaptive_threshold,
        adaptive_max_samples=adaptive_max_samples,
    )
