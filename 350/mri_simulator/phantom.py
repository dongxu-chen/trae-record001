"""
数字体模模块 - 生成MRI模拟所需的体模数据
包含质子密度(PD)、T1弛豫时间、T2弛豫时间图
"""

import numpy as np
from scipy.ndimage import map_coordinates


class Phantom:
    """
    MRI数字体模类
    存储质子密度、T1、T2弛豫时间分布图
    """

    def __init__(self, size=(128, 128), fov=(0.256, 0.256)):
        """
        初始化体模
        
        Parameters:
            size: 矩阵大小 (Ny, Nx)
            fov: 视场大小 (米)
        """
        self.size = size
        self.fov = fov
        self.dx = fov[1] / size[1]
        self.dy = fov[0] / size[0]

        self.PD = np.zeros(size, dtype=np.float64)
        self.T1 = np.zeros(size, dtype=np.float64)
        self.T2 = np.zeros(size, dtype=np.float64)

        x = (np.arange(size[1]) - size[1] / 2) * self.dx
        y = (np.arange(size[0]) - size[0] / 2) * self.dy
        self.X, self.Y = np.meshgrid(x, y)

    def add_ellipse(self, center, radii, angle, pd, t1, t2):
        """
        添加椭圆组织区域
        
        Parameters:
            center: 中心坐标 (y, x) 米
            radii: 半径 (ry, rx) 米
            angle: 旋转角度 (弧度)
            pd: 质子密度
            t1: T1弛豫时间 (秒)
            t2: T2弛豫时间 (秒)
        """
        cy, cx = center
        ry, rx = radii

        cos_a = np.cos(angle)
        sin_a = np.sin(angle)

        x_rot = cos_a * (self.X - cx) + sin_a * (self.Y - cy)
        y_rot = -sin_a * (self.X - cx) + cos_a * (self.Y - cy)

        mask = (x_rot ** 2) / (rx ** 2) + (y_rot ** 2) / (ry ** 2) <= 1.0

        self.PD[mask] = pd
        self.T1[mask] = t1
        self.T2[mask] = t2

    def add_rectangle(self, center, size, angle, pd, t1, t2):
        """
        添加矩形组织区域
        
        Parameters:
            center: 中心坐标 (y, x) 米
            size: 大小 (height, width) 米
            angle: 旋转角度 (弧度)
            pd: 质子密度
            t1: T1弛豫时间 (秒)
            t2: T2弛豫时间 (秒)
        """
        cy, cx = center
        h, w = size

        cos_a = np.cos(angle)
        sin_a = np.sin(angle)

        x_rot = cos_a * (self.X - cx) + sin_a * (self.Y - cy)
        y_rot = -sin_a * (self.X - cx) + cos_a * (self.Y - cy)

        mask = (np.abs(x_rot) <= w / 2) & (np.abs(y_rot) <= h / 2)

        self.PD[mask] = pd
        self.T1[mask] = t1
        self.T2[mask] = t2

    def get_voxel_params(self):
        """
        获取所有体素的参数数组
        
        Returns:
            (PD, T1, T2) 数组，形状为 (N_voxels,)
        """
        return (
            self.PD.flatten().astype(np.float64),
            self.T1.flatten().astype(np.float64),
            self.T2.flatten().astype(np.float64),
        )

    def get_positions(self):
        """
        获取所有体素的空间坐标
        
        Returns:
            (x, y) 数组，形状为 (N_voxels,)
        """
        return self.X.flatten().astype(np.float64), self.Y.flatten().astype(np.float64)


def generate_shepp_logan(size=(128, 128), fov=(0.256, 0.256)):
    """
    生成Shepp-Logan体模，这是MRI模拟的标准测试体模
    
    Parameters:
        size: 图像大小 (Ny, Nx)
        fov: 视场大小 (米)
    
    Returns:
        Phantom对象，包含修改后的Shepp-Logan参数
    """
    phantom = Phantom(size, fov)

    ellipses = [
        {"center": (0.0, 0.0), "radii": (0.092, 0.069), "angle": 0.0, "pd": 1.0, "t1": 1.0, "t2": 0.1},
        {"center": (0.0, -0.0184), "radii": (0.0874, 0.06624), "angle": 0.0, "pd": 0.98, "t1": 1.2, "t2": 0.12},
        {"center": (0.022, 0.0), "radii": (0.031, 0.018), "angle": -0.31416, "pd": 0.8, "t1": 0.8, "t2": 0.08},
        {"center": (-0.022, 0.0), "radii": (0.041, 0.022), "angle": 0.31416, "pd": 0.7, "t1": 0.9, "t2": 0.07},
        {"center": (0.0, 0.035), "radii": (0.015, 0.015), "angle": 0.0, "pd": 0.6, "t1": 1.5, "t2": 0.15},
        {"center": (0.0, 0.01), "radii": (0.008, 0.008), "angle": 0.0, "pd": 0.5, "t1": 0.7, "t2": 0.06},
        {"center": (-0.04, -0.03), "radii": (0.012, 0.008), "angle": 0.0, "pd": 0.4, "t1": 0.6, "t2": 0.05},
        {"center": (0.0, -0.06), "radii": (0.016, 0.009), "angle": 0.0, "pd": 0.3, "t1": 1.1, "t2": 0.09},
        {"center": (0.04, -0.03), "radii": (0.01, 0.006), "angle": 0.0, "pd": 0.85, "t1": 1.3, "t2": 0.11},
        {"center": (-0.06, 0.0), "radii": (0.005, 0.005), "angle": 0.0, "pd": 0.2, "t1": 0.5, "t2": 0.04},
    ]

    for ellipse in ellipses:
        phantom.add_ellipse(
            ellipse["center"],
            ellipse["radii"],
            ellipse["angle"],
            ellipse["pd"],
            ellipse["t1"],
            ellipse["t2"],
        )

    return phantom


def generate_brain_phantom(size=(128, 128), fov=(0.256, 0.256)):
    """
    生成简化的脑体模
    
    Parameters:
        size: 图像大小 (Ny, Nx)
        fov: 视场大小 (米)
    
    Returns:
        Phantom对象
    """
    phantom = Phantom(size, fov)

    phantom.add_ellipse((0.0, 0.0), (0.10, 0.08), 0.0, 1.0, 0.9, 0.1)
    phantom.add_ellipse((0.03, 0.0), (0.035, 0.03), 0.0, 0.9, 1.1, 0.12)
    phantom.add_ellipse((-0.03, 0.0), (0.035, 0.03), 0.0, 0.9, 1.1, 0.12)
    phantom.add_ellipse((0.0, -0.04), (0.015, 0.02), 0.0, 0.7, 2.0, 0.25)
    phantom.add_ellipse((0.0, 0.05), (0.01, 0.015), 0.0, 0.8, 1.5, 0.08)
    phantom.add_rectangle((0.0, -0.08), (0.01, 0.04), 0.0, 0.6, 0.5, 0.05)

    return phantom
