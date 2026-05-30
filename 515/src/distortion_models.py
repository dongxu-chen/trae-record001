from abc import ABC, abstractmethod
from enum import Enum
import numpy as np


class FisheyeProjectionType(Enum):
    EQUIDISTANT = "equidistant"
    EQUISOLID = "equisolid"
    ORTHOGRAPHIC = "orthographic"
    STEREOGRAPHIC = "stereographic"


class FisheyeDistortionModel(ABC):
    def __init__(self, focal_length: float, center: tuple[float, float]):
        self.focal_length = focal_length
        self.center = np.array(center, dtype=np.float64)

    @abstractmethod
    def project(self, theta: np.ndarray) -> np.ndarray:
        pass

    @abstractmethod
    def unproject(self, r: np.ndarray) -> np.ndarray:
        pass

    def pixel_to_angle(self, pixel_coords: np.ndarray) -> np.ndarray:
        centered = pixel_coords - self.center
        r = np.sqrt(centered[..., 0] ** 2 + centered[..., 1] ** 2)
        theta = self.unproject(r)
        phi = np.arctan2(centered[..., 1], centered[..., 0])
        return np.stack([theta, phi], axis=-1)

    def angle_to_pixel(self, angles: np.ndarray) -> np.ndarray:
        theta = angles[..., 0]
        phi = angles[..., 1]
        r = self.project(theta)
        x = r * np.cos(phi) + self.center[0]
        y = r * np.sin(phi) + self.center[1]
        return np.stack([x, y], axis=-1)

    def pixel_to_cartesian(self, pixel_coords: np.ndarray) -> np.ndarray:
        angles = self.pixel_to_angle(pixel_coords)
        theta = angles[..., 0]
        phi = angles[..., 1]
        x = np.sin(theta) * np.cos(phi)
        y = np.sin(theta) * np.sin(phi)
        z = np.cos(theta)
        return np.stack([x, y, z], axis=-1)

    def cartesian_to_pixel(self, cartesian: np.ndarray) -> np.ndarray:
        x = cartesian[..., 0]
        y = cartesian[..., 1]
        z = cartesian[..., 2]
        theta = np.arccos(np.clip(z, -1.0, 1.0))
        phi = np.arctan2(y, x)
        return self.angle_to_pixel(np.stack([theta, phi], axis=-1))


class EquidistantProjection(FisheyeDistortionModel):
    def project(self, theta: np.ndarray) -> np.ndarray:
        return self.focal_length * theta

    def unproject(self, r: np.ndarray) -> np.ndarray:
        return r / self.focal_length


class EquisolidProjection(FisheyeDistortionModel):
    def project(self, theta: np.ndarray) -> np.ndarray:
        return 2.0 * self.focal_length * np.sin(theta / 2.0)

    def unproject(self, r: np.ndarray) -> np.ndarray:
        return 2.0 * np.arcsin(np.clip(r / (2.0 * self.focal_length), -1.0, 1.0))


class OrthographicProjection(FisheyeDistortionModel):
    def project(self, theta: np.ndarray) -> np.ndarray:
        return self.focal_length * np.sin(theta)

    def unproject(self, r: np.ndarray) -> np.ndarray:
        return np.arcsin(np.clip(r / self.focal_length, -1.0, 1.0))


class StereographicProjection(FisheyeDistortionModel):
    def project(self, theta: np.ndarray) -> np.ndarray:
        return 2.0 * self.focal_length * np.tan(theta / 2.0)

    def unproject(self, r: np.ndarray) -> np.ndarray:
        return 2.0 * np.arctan(r / (2.0 * self.focal_length))


PROJECTION_MAP = {
    FisheyeProjectionType.EQUIDISTANT: EquidistantProjection,
    FisheyeProjectionType.EQUISOLID: EquisolidProjection,
    FisheyeProjectionType.ORTHOGRAPHIC: OrthographicProjection,
    FisheyeProjectionType.STEREOGRAPHIC: StereographicProjection,
}


def create_projection_model(
    projection_type: FisheyeProjectionType,
    focal_length: float,
    center: tuple[float, float],
) -> FisheyeDistortionModel:
    model_class = PROJECTION_MAP.get(projection_type)
    if model_class is None:
        raise ValueError(f"Unknown projection type: {projection_type}")
    return model_class(focal_length, center)


def estimate_projection_type_from_fov(fov_degrees: float) -> FisheyeProjectionType:
    fov = np.radians(fov_degrees)
    if fov <= np.pi / 2:
        return FisheyeProjectionType.ORTHOGRAPHIC
    elif fov <= 2.0 * np.pi / 3:
        return FisheyeProjectionType.EQUISOLID
    elif fov <= 5.0 * np.pi / 6:
        return FisheyeProjectionType.EQUIDISTANT
    else:
        return FisheyeProjectionType.STEREOGRAPHIC
