import numpy as np
import cv2


class Farneback:
    """
    Gunnar Farneback 光流估计算法

    原理:
        基于多项式展开 (Polynomial Expansion) 的稠密光流算法。
        将每个像素邻域用二次多项式近似: f(x) ≈ x^T A x + b^T x + c
        通过极小化两帧多项式系数的差异来求解位移场。

    参数:
        pyr_scale: 金字塔缩放比例 (0 < pyr_scale < 1)
        levels: 金字塔层数
        winsize: 平均窗口大小, 越大越鲁棒但越模糊
        iterations: 每层金字塔迭代次数
        poly_n: 多项式展开邻域大小
        poly_sigma: 多项式展开的高斯标准差
        flags: 额外标志 (OPTFLOW_USE_INITIAL_FLOW, OPTFLOW_FARNEBACK_GAUSSIAN)
    """

    def __init__(
        self,
        pyr_scale: float = 0.5,
        levels: int = 3,
        winsize: int = 15,
        iterations: int = 3,
        poly_n: int = 7,
        poly_sigma: float = 1.5,
        flags: int = 0,
    ):
        self.pyr_scale = pyr_scale
        self.levels = levels
        self.winsize = winsize
        self.iterations = iterations
        self.poly_n = poly_n
        self.poly_sigma = poly_sigma
        self.flags = flags

        self.prev_gray = None

    def compute(self, frame: np.ndarray, prev_frame: np.ndarray | None = None) -> np.ndarray:
        """
        计算两帧之间的光流

        参数:
            frame: 当前帧 (BGR 或灰度)
            prev_frame: 上一帧, 若为 None 则使用内部缓存

        返回:
            光流场, 形状为 (H, W, 2), 通道为 (u, v)
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame

        if prev_frame is not None:
            prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY) if len(prev_frame.shape) == 3 else prev_frame
        elif self.prev_gray is not None:
            prev_gray = self.prev_gray
        else:
            self.prev_gray = gray
            h, w = gray.shape
            return np.zeros((h, w, 2), dtype=np.float32)

        flow = cv2.calcOpticalFlowFarneback(
            prev_gray, gray, None,
            pyr_scale=self.pyr_scale,
            levels=self.levels,
            winsize=self.winsize,
            iterations=self.iterations,
            poly_n=self.poly_n,
            poly_sigma=self.poly_sigma,
            flags=self.flags,
        )

        self.prev_gray = gray
        self.flags = cv2.OPTFLOW_USE_INITIAL_FLOW

        return flow

    def reset(self):
        """重置内部状态"""
        self.prev_gray = None
        self.flags = 0