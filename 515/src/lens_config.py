import os
import json
import numpy as np
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, asdict, field
from .distortion_models import (
    FisheyeProjectionType,
    create_projection_model,
    FisheyeDistortionModel,
)


@dataclass
class LensConfig:
    name: str
    projection_type: FisheyeProjectionType
    focal_length: float
    center: Tuple[float, float]
    fov_degrees: float = 180.0
    sensor_size: Optional[Tuple[float, float]] = None
    distortion_coeffs: Optional[List[float]] = None
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["projection_type"] = self.projection_type.value
        data["center"] = list(self.center)
        if self.sensor_size is not None:
            data["sensor_size"] = list(self.sensor_size)
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LensConfig":
        projection_type = FisheyeProjectionType(data.get("projection_type", "equisolid"))
        center = tuple(data.get("center", [0.0, 0.0]))
        return cls(
            name=data.get("name", "unknown"),
            projection_type=projection_type,
            focal_length=float(data.get("focal_length", 0.0)),
            center=center,
            fov_degrees=float(data.get("fov_degrees", 180.0)),
            sensor_size=tuple(data.get("sensor_size")) if data.get("sensor_size") else None,
            distortion_coeffs=list(data.get("distortion_coeffs")) if data.get("distortion_coeffs") else None,
            description=data.get("description", ""),
            metadata=data.get("metadata", {}),
        )

    def get_model(self) -> FisheyeDistortionModel:
        return create_projection_model(
            self.projection_type, self.focal_length, self.center
        )


class LensConfigManager:
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file
        self.lenses: Dict[str, LensConfig] = {}
        self.active_lens: Optional[str] = None

        if config_file and os.path.exists(config_file):
            self.load(config_file)

    def add_lens(self, config: LensConfig) -> None:
        self.lenses[config.name] = config

    def remove_lens(self, name: str) -> None:
        if name in self.lenses:
            del self.lenses[name]
            if self.active_lens == name:
                self.active_lens = None

    def get_lens(self, name: str) -> Optional[LensConfig]:
        return self.lenses.get(name)

    def set_active_lens(self, name: str) -> None:
        if name not in self.lenses:
            raise ValueError(f"Lens '{name}' not found in configuration")
        self.active_lens = name

    def get_active_lens(self) -> Optional[LensConfig]:
        if self.active_lens is None:
            return None
        return self.lenses.get(self.active_lens)

    def get_active_model(self) -> Optional[FisheyeDistortionModel]:
        lens = self.get_active_lens()
        if lens is None:
            return None
        return lens.get_model()

    def list_lenses(self) -> List[str]:
        return sorted(self.lenses.keys())

    def get_lens_info(self, name: str) -> Optional[Dict[str, Any]]:
        lens = self.get_lens(name)
        if lens is None:
            return None

        return {
            "name": lens.name,
            "projection_type": lens.projection_type.value,
            "focal_length": lens.focal_length,
            "center": lens.center,
            "fov_degrees": lens.fov_degrees,
            "sensor_size": lens.sensor_size,
            "description": lens.description,
            "is_active": self.active_lens == name,
        }

    def get_all_lenses_info(self) -> List[Dict[str, Any]]:
        return [self.get_lens_info(name) for name in self.list_lenses()]

    def save(self, filepath: Optional[str] = None) -> None:
        save_path = filepath or self.config_file
        if save_path is None:
            raise ValueError("No filepath specified and no config_file set")

        data = {
            "active_lens": self.active_lens,
            "lenses": {name: config.to_dict() for name, config in self.lenses.items()},
            "version": "1.0",
        }

        os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
        with open(save_path, "w") as f:
            json.dump(data, f, indent=2)

        self.config_file = save_path

    def load(self, filepath: str) -> None:
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Config file not found: {filepath}")

        with open(filepath, "r") as f:
            data = json.load(f)

        self.lenses = {}
        for name, lens_data in data.get("lenses", {}).items():
            self.lenses[name] = LensConfig.from_dict(lens_data)

        self.active_lens = data.get("active_lens")
        self.config_file = filepath

    def create_lens_from_params(
        self,
        name: str,
        params: Dict[str, Any],
        description: str = "",
        set_active: bool = True,
    ) -> LensConfig:
        if "projection_type" in params and isinstance(params["projection_type"], str):
            params["projection_type"] = FisheyeProjectionType(params["projection_type"])

        lens = LensConfig(
            name=name,
            projection_type=params.get("projection_type", FisheyeProjectionType.EQUISOLID),
            focal_length=float(params.get("focal_length", 0.0)),
            center=tuple(params.get("center", (0.0, 0.0))),
            fov_degrees=float(params.get("fov_degrees", 180.0)),
            description=description,
        )

        self.add_lens(lens)
        if set_active:
            self.set_active_lens(name)

        return lens

    def calibrate_lens_from_image(
        self,
        name: str,
        image: np.ndarray,
        description: str = "",
        use_line_calibration: bool = True,
        set_active: bool = True,
    ) -> LensConfig:
        if use_line_calibration:
            from .self_calibration import self_calibrate_from_lines

            params = self_calibrate_from_lines(image)
        else:
            from .calibration import estimate_fisheye_params_auto

            params = estimate_fisheye_params_auto(image)

        return self.create_lens_from_params(
            name=name,
            params=params,
            description=description,
            set_active=set_active,
        )

    def calibrate_lens_from_images(
        self,
        name: str,
        image_paths: List[str],
        description: str = "",
        use_line_calibration: bool = True,
        set_active: bool = True,
    ) -> LensConfig:
        if use_line_calibration:
            from .self_calibration import self_calibrate_from_multiple_images

            params = self_calibrate_from_multiple_images(image_paths)
        else:
            from .calibration import estimate_params_from_multiple_images

            params = estimate_params_from_multiple_images(image_paths)

        return self.create_lens_from_params(
            name=name,
            params=params,
            description=description,
            set_active=set_active,
        )

    def get_lens_for_image(
        self,
        image_path: str,
    ) -> Optional[LensConfig]:
        filename = os.path.basename(image_path).lower()

        for lens_name in self.lenses:
            if lens_name.lower() in filename:
                return self.lenses[lens_name]

        return None

    def batch_config_from_directory(
        self,
        input_dir: str,
        lens_name_patterns: Optional[Dict[str, str]] = None,
        output_config_file: Optional[str] = None,
    ) -> Dict[str, List[str]]:
        import glob

        image_files = set()
        for ext in ["*.jpg", "*.jpeg", "*.png", "*.bmp"]:
            for f in glob.glob(os.path.join(input_dir, ext)):
                image_files.add(os.path.normpath(os.path.abspath(f)))
            for f in glob.glob(os.path.join(input_dir, ext.upper())):
                image_files.add(os.path.normpath(os.path.abspath(f)))
        image_files = sorted(image_files)

        if lens_name_patterns is None or len(lens_name_patterns) == 0:
            lens_name_patterns = {name: name for name in self.lenses.keys()}

        lens_groups: Dict[str, List[str]] = {name: [] for name in lens_name_patterns}

        for image_path in image_files:
            filename = os.path.basename(image_path).lower()
            matched = False

            for lens_name, pattern in lens_name_patterns.items():
                if pattern.lower() in filename:
                    lens_groups[lens_name].append(image_path)
                    matched = True
                    break

            if not matched:
                if "default" not in lens_groups:
                    lens_groups["default"] = []
                lens_groups["default"].append(image_path)

        if output_config_file:
            self.save(output_config_file)

        return lens_groups

    def print_summary(self) -> None:
        print("=" * 60)
        print("Lens Configuration Summary")
        print("=" * 60)
        print(f"Total lenses: {len(self.lenses)}")
        print(f"Active lens: {self.active_lens or 'None'}")
        print()

        for name in self.list_lenses():
            info = self.get_lens_info(name)
            marker = " *" if info["is_active"] else "  "
            print(f"{marker}{name}")
            print(f"    Projection: {info['projection_type']}")
            print(f"    Focal length: {info['focal_length']:.1f}")
            print(f"    Center: ({info['center'][0]:.1f}, {info['center'][1]:.1f})")
            print(f"    FOV: {info['fov_degrees']:.1f}°")
            if info["description"]:
                print(f"    Description: {info['description']}")
            print()


def create_default_lens_config() -> LensConfigManager:
    manager = LensConfigManager()

    manager.add_lens(LensConfig(
        name="lens_a_180",
        projection_type=FisheyeProjectionType.EQUISOLID,
        focal_length=500.0,
        center=(640.0, 480.0),
        fov_degrees=180.0,
        description="180° equisolid angle fisheye lens",
    ))

    manager.add_lens(LensConfig(
        name="lens_b_220",
        projection_type=FisheyeProjectionType.STEREOGRAPHIC,
        focal_length=400.0,
        center=(640.0, 480.0),
        fov_degrees=220.0,
        description="220° super wide angle lens",
    ))

    manager.add_lens(LensConfig(
        name="lens_c_120",
        projection_type=FisheyeProjectionType.ORTHOGRAPHIC,
        focal_length=800.0,
        center=(640.0, 480.0),
        fov_degrees=120.0,
        description="120° wide angle lens",
    ))

    manager.set_active_lens("lens_a_180")

    return manager
