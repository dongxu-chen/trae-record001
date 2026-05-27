import numpy as np
import cv2
import matplotlib.pyplot as plt
from typing import Optional


def flow_to_hsv(
    flow: np.ndarray,
    max_flow: Optional[float] = None,
    median_filter: int = 0,
    smooth_flow: bool = False,
) -> np.ndarray:
    """
    将光流场转换为 HSV 彩色编码图

    原理:
        - 色相 (Hue): 表示运动方向, 0-360° 映射到 0-180 (OpenCV HSV 范围)
        - 饱和度 (Saturation): 恒为最大值
        - 明度 (Value): 表示运动幅度

    参数:
        flow: 光流场 (H, W, 2), 通道为 (u, v)
        max_flow: 最大光流幅度归一化值, 若为 None 则自动计算
        median_filter: 对最终 HSV 图像应用中值滤波的核大小 (0 表示不应用)
        smooth_flow: 是否先对光流场进行中值滤波平滑 (减少边缘噪声)

    返回:
        HSV 编码的 BGR 图像 (H, W, 3)
    """
    h, w = flow.shape[:2]

    if smooth_flow:
        u_smooth = cv2.medianBlur(flow[:, :, 0].astype(np.float32), 3)
        v_smooth = cv2.medianBlur(flow[:, :, 1].astype(np.float32), 3)
        u = u_smooth
        v = v_smooth
    else:
        u = flow[:, :, 0]
        v = flow[:, :, 1]

    magnitude = np.sqrt(u ** 2 + v ** 2)
    angle = np.arctan2(v, u)

    if max_flow is None:
        max_flow = magnitude.max() if magnitude.max() > 0 else 1.0

    hsv = np.zeros((h, w, 3), dtype=np.uint8)
    hsv[:, :, 0] = (angle * 180 / np.pi / 2).astype(np.uint8)
    hsv[:, :, 1] = 255
    hsv[:, :, 2] = np.clip(magnitude / max_flow * 255, 0, 255).astype(np.uint8)

    bgr = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)

    if median_filter > 0:
        median_filter = median_filter if median_filter % 2 == 1 else median_filter + 1
        bgr = cv2.medianBlur(bgr, median_filter)

    return bgr


def flow_to_rgb(
    flow: np.ndarray,
    max_flow: Optional[float] = None,
    median_filter: int = 0,
    smooth_flow: bool = False,
) -> np.ndarray:
    """
    将光流场转换为 RGB 图 (用于 Matplotlib 显示)

    参数:
        flow: 光流场 (H, W, 2)
        max_flow: 最大光流幅度归一化值
        median_filter: 中值滤波核大小 (0 表示不应用)
        smooth_flow: 是否先对光流场进行中值滤波

    返回:
        RGB 图像 (H, W, 3)
    """
    hsv = flow_to_hsv(flow, max_flow, median_filter, smooth_flow)
    rgb = cv2.cvtColor(hsv, cv2.COLOR_BGR2RGB)
    return rgb


def visualize_flow(
    flow: np.ndarray,
    ax: Optional[plt.Axes] = None,
    title: str = 'Optical Flow',
    max_flow: Optional[float] = None,
    show_axis: bool = False,
    median_filter: int = 0,
    smooth_flow: bool = False,
) -> plt.Axes:
    """
    使用 Matplotlib 可视化光流场

    参数:
        flow: 光流场 (H, W, 2)
        ax: Matplotlib 坐标轴, 若为 None 则创建新图
        title: 图标题
        max_flow: 最大光流幅度
        show_axis: 是否显示坐标轴
        median_filter: 中值滤波核大小 (0 表示不应用)
        smooth_flow: 是否先对光流场进行中值滤波

    返回:
        Matplotlib 坐标轴对象
    """
    rgb = flow_to_rgb(flow, max_flow, median_filter, smooth_flow)

    if ax is None:
        _, ax = plt.subplots(1, 1, figsize=(8, 6))

    ax.imshow(rgb)
    ax.set_title(title)
    if not show_axis:
        ax.axis('off')

    return ax


def draw_vector_field(
    flow: np.ndarray,
    step: int = 16,
    ax: Optional[plt.Axes] = None,
    title: str = 'Vector Field',
    max_flow: Optional[float] = None,
) -> plt.Axes:
    """
    绘制光流矢量场 (quiver plot

    简化版, 每隔 step 像素绘制一个箭头

    参数:
        flow: 光流场 (H, W, 2)
        step: 采样步长
        ax: Matplotlib 坐标轴
        title: 图标题
        max_flow: 最大光流幅度

    返回:
        Matplotlib 坐标轴
    """
    h, w = flow.shape[:2]

    y, x = np.mgrid[0:h:step, 0:w:step]
    u = flow[::step, ::step, 0]
    v = flow[::step, ::step, 1]

    magnitude = np.sqrt(u ** 2 + v ** 2)
    if max_flow is None:
        max_flow = magnitude.max() if magnitude.max() > 0 else 1.0

    if ax is None:
        _, ax = plt.subplots(1, 1, figsize=(8, 6))

    ax.quiver(
        x, y, u, v,
        magnitude,
        angles='xy',
        scale_units='xy',
        scale=1,
        cmap='hsv',
        clim=[0, max_flow],
    )
    ax.set_title(title)
    ax.set_aspect('equal')
    ax.invert_yaxis()

    return ax


def create_color_wheel(size: int = 256, ax: Optional[plt.Axes] = None) -> plt.Axes:
    """
    创建光流颜色编码的色轮参考图

    参数:
        size: 色轮大小
        ax: Matplotlib 坐标轴

    返回:
        Matplotlib 坐标轴
    """
    xx, yy = np.meshgrid(
        np.linspace(-1, 1, size),
        np.linspace(-1, 1, size),
    )

    flow = np.stack([xx, yy], axis=-1)
    magnitude = np.sqrt(xx ** 2 + yy ** 2)
    mask = magnitude <= 1.0

    flow[~mask] = 0

    rgb = flow_to_rgb(flow, max_flow=1.0)

    if ax is None:
        _, ax = plt.subplots(1, 1, figsize=(6, 6))

    ax.imshow(rgb)
    ax.set_title('Color Wheel (HSV Encoding')
    ax.set_xlabel('u')
    ax.set_ylabel('v')

    return ax