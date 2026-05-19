import meshio
import numpy as np
from pathlib import Path


class MeshReader:
    SUPPORTED_FORMATS = [".msh", ".vtk", ".vtu", ".stl", ".obj", ".ply"]

    def __init__(self):
        self.mesh = None
        self.file_path = None

    def read(self, file_path):
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        suffix = self.file_path.suffix.lower()
        if suffix not in self.SUPPORTED_FORMATS:
            raise ValueError(f"不支持的格式: {suffix}. 支持的格式: {self.SUPPORTED_FORMATS}")

        self.mesh = meshio.read(file_path)
        return self.mesh

    def get_points(self):
        if self.mesh is None:
            raise ValueError("未读取网格文件")
        return self.mesh.points

    def get_cells(self):
        if self.mesh is None:
            raise ValueError("未读取网格文件")
        return self.mesh.cells

    def get_cell_data(self):
        if self.mesh is None:
            raise ValueError("未读取网格文件")
        return self.mesh.cell_data

    def get_point_data(self):
        if self.mesh is None:
            raise ValueError("未读取网格文件")
        return self.mesh.point_data

    def get_mesh_info(self):
        if self.mesh is None:
            raise ValueError("未读取网格文件")

        info = {
            "file_path": str(self.file_path),
            "num_points": len(self.mesh.points),
            "cell_types": {},
            "total_cells": 0
        }

        for cell_block in self.mesh.cells:
            cell_type = cell_block.type
            num_cells = len(cell_block.data)
            info["cell_types"][cell_type] = num_cells
            info["total_cells"] += num_cells

        return info

    @staticmethod
    def list_supported_formats():
        return MeshReader.SUPPORTED_FORMATS
