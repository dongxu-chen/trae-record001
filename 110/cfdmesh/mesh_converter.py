import meshio
import numpy as np
from pathlib import Path
from typing import Optional


class MeshConverter:
    SUPPORTED_INPUT_FORMATS = [".msh", ".vtk", ".vtu", ".stl", ".obj", ".ply", ".mesh"]
    SUPPORTED_OUTPUT_FORMATS = [".msh", ".vtk", ".vtu", ".stl", ".obj", ".ply", ".mesh", ".vtk"]

    def __init__(self):
        self.mesh = None
        self.input_format = None

    def load_mesh(self, file_path: str):
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        self.input_format = path.suffix.lower()
        if self.input_format not in self.SUPPORTED_INPUT_FORMATS:
            raise ValueError(f"不支持的输入格式: {self.input_format}")

        self.mesh = meshio.read(file_path)
        return self.mesh

    def save_mesh(self, output_path: str, format: Optional[str] = None):
        if self.mesh is None:
            raise ValueError("未加载网格，请先调用 load_mesh()")

        output_path = Path(output_path)
        output_format = format.lower() if format else output_path.suffix.lower()

        if output_format not in self.SUPPORTED_OUTPUT_FORMATS:
            raise ValueError(f"不支持的输出格式: {output_format}")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        meshio.write(output_path, self.mesh)
        return str(output_path)

    def convert(self, input_path: str, output_path: str):
        self.load_mesh(input_path)
        return self.save_mesh(output_path)

    @staticmethod
    def list_input_formats():
        return MeshConverter.SUPPORTED_INPUT_FORMATS

    @staticmethod
    def list_output_formats():
        return MeshConverter.SUPPORTED_OUTPUT_FORMATS

    def get_format_info(self):
        info = {
            "input_format": self.input_format,
            "supported_input": self.SUPPORTED_INPUT_FORMATS,
            "supported_output": self.SUPPORTED_OUTPUT_FORMATS
        }
        return info

    def scale_mesh(self, scale_factor: float):
        if self.mesh is None:
            raise ValueError("未加载网格")
        self.mesh.points *= scale_factor

    def translate_mesh(self, translation: np.ndarray):
        if self.mesh is None:
            raise ValueError("未加载网格")
        self.mesh.points += translation

    def rotate_mesh(self, angle_deg: float, axis: str = 'z'):
        if self.mesh is None:
            raise ValueError("未加载网格")

        angle_rad = np.radians(angle_deg)
        cos_a = np.cos(angle_rad)
        sin_a = np.sin(angle_rad)

        if axis.lower() == 'x':
            rotation_matrix = np.array([
                [1, 0, 0],
                [0, cos_a, -sin_a],
                [0, sin_a, cos_a]
            ])
        elif axis.lower() == 'y':
            rotation_matrix = np.array([
                [cos_a, 0, sin_a],
                [0, 1, 0],
                [-sin_a, 0, cos_a]
            ])
        elif axis.lower() == 'z':
            rotation_matrix = np.array([
                [cos_a, -sin_a, 0],
                [sin_a, cos_a, 0],
                [0, 0, 1]
            ])
        else:
            raise ValueError("不支持的旋转轴，请使用 'x', 'y', 或 'z'")

        self.mesh.points = self.mesh.points @ rotation_matrix.T
