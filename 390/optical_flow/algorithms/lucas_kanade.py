import numpy as np
import cv2


class LucasKanade:
    """
    Lucas-Kanade 光流估计算法

    支持两种模式:
        - sparse: 稀疏光流, 基于 Shi-Tomasi 角点检测 + 金字塔 LK
        - dense: 稠密光流, 逐像素块匹配

    原理:
        基于光流约束方程: I_x * u + I_y * v + I_t = 0
        假设小运动窗口内速度场恒定, 通过最小二乘求解每个像素的 (u, v)

    参数:
        mode: 'sparse' 或 'dense'
        max_corners: 稀疏模式下跟踪的最大角点数量
        quality_level: 角点检测质量等级
        min_distance: 角点之间最小距离
        block_size: 计算导数的块大小
        win_size: LK 算法搜索窗口大小
        max_level: 金字塔层数
    """

    def __init__(
        self,
        mode: str = 'sparse',
        max_corners: int = 500,
        quality_level: float = 0.01,
        min_distance: int = 10,
        block_size: int = 7,
        win_size: int = 21,
        max_level: int = 3,
        adaptive_window: bool = False,
        win_min: int = 7,
        win_max: int = 31,
    ):
        self.mode = mode
        self.max_corners = max_corners
        self.quality_level = quality_level
        self.min_distance = min_distance
        self.block_size = block_size
        self.win_size = win_size
        self.max_level = max_level
        self.adaptive_window = adaptive_window
        self.win_min = win_min
        self.win_max = win_max

        self.prev_gray = None
        self.prev_pts = None

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

        if self.mode == 'sparse':
            flow = self._compute_sparse(prev_gray, gray)
        else:
            flow = self._compute_dense(prev_gray, gray)

        self.prev_gray = gray
        return flow

    def _compute_sparse(self, prev_gray: np.ndarray, gray: np.ndarray) -> np.ndarray:
        """
        稀疏光流: 跟踪角点, 插值到稠密光流场
        """
        h, w = gray.shape

        if self.prev_pts is None or len(self.prev_pts) < 10:
            self.prev_pts = cv2.goodFeaturesToTrack(
                prev_gray,
                maxCorners=self.max_corners,
                qualityLevel=self.quality_level,
                minDistance=self.min_distance,
                blockSize=self.block_size,
            )

        if self.prev_pts is None or len(self.prev_pts) == 0:
            return np.zeros((h, w, 2), dtype=np.float32)

        next_pts, status, _ = cv2.calcOpticalFlowPyrLK(
            prev_gray, gray,
            self.prev_pts, None,
            winSize=(self.win_size, self.win_size),
            maxLevel=self.max_level,
            criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01),
        )

        back_pts, status_back, _ = cv2.calcOpticalFlowPyrLK(
            gray, prev_gray,
            next_pts, None,
            winSize=(self.win_size, self.win_size),
            maxLevel=self.max_level,
            criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01),
        )

        good = (status.ravel() == 1) & (status_back.ravel() == 1)
        self.prev_pts = next_pts[good].reshape(-1, 1, 2)

        if len(self.prev_pts) == 0:
            self.prev_pts = cv2.goodFeaturesToTrack(
                prev_gray,
                maxCorners=self.max_corners,
                qualityLevel=self.quality_level,
                minDistance=self.min_distance,
                blockSize=self.block_size,
            )
            return np.zeros((h, w, 2), dtype=np.float32)

        flow = np.zeros((h, w, 2), dtype=np.float32)
        prev_pts_good = next_pts[good].reshape(-1, 2)
        curr_pts_good = back_pts[good].reshape(-1, 2)
        flow_vec = curr_pts_good - prev_pts_good

        for i, (pt, vec) in enumerate(zip(prev_pts_good, flow_vec)):
            x, y = int(pt[0]), int(pt[1])
            if 0 <= x < w and 0 <= y < h:
                flow[y, x] = vec

        mask = (flow[:, :, 0] != 0) | (flow[:, :, 1] != 0)
        if mask.any():
            flow = self._interpolate_flow(flow, mask)

        return flow

    @staticmethod
    def _interpolate_flow(flow: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """
        从稀疏光流点插值到稠密光流场 (距离加权平滑)
        """
        h, w = flow.shape[:2]
        ys, xs = np.where(mask)
        if len(xs) < 3:
            return flow

        u_vals = flow[ys, xs, 0]
        v_vals = flow[ys, xs, 1]

        u_img = np.zeros((h, w), dtype=np.float32)
        v_img = np.zeros((h, w), dtype=np.float32)
        weight = np.zeros((h, w), dtype=np.float32)

        for x, y, u, v in zip(xs, ys, u_vals, v_vals):
            u_img[y, x] = u
            v_img[y, x] = v
            weight[y, x] = 1.0

        kernel = np.ones((5, 5), dtype=np.float32) / 25.0
        for _ in range(10):
            u_img = cv2.filter2D(u_img, -1, kernel)
            v_img = cv2.filter2D(v_img, -1, kernel)
            weight = cv2.filter2D(weight, -1, kernel)

        weight = np.where(weight > 0, weight, 1.0)
        flow[:, :, 0] = u_img / weight
        flow[:, :, 1] = v_img / weight

        return flow

    def _compute_dense(self, prev_gray: np.ndarray, gray: np.ndarray) -> np.ndarray:
        """
        稠密光流: 逐像素应用 Lucas-Kanade 方法
        使用高斯-赛德尔迭代求解光流约束方程
        支持自适应窗口大小 (基于结构张量)
        """
        h, w = prev_gray.shape
        flow = np.zeros((h, w, 2), dtype=np.float32)

        prev_blur = cv2.GaussianBlur(prev_gray.astype(np.float32), (5, 5), 0)
        curr_blur = cv2.GaussianBlur(gray.astype(np.float32), (5, 5), 0)

        Ix = cv2.Sobel(prev_blur, cv2.CV_32F, 1, 0, ksize=3)
        Iy = cv2.Sobel(prev_blur, cv2.CV_32F, 0, 1, ksize=3)
        It = curr_blur - prev_blur

        kernel_small = np.ones((3, 3), dtype=np.float32) / 9.0

        Ix2 = Ix ** 2
        Iy2 = Iy ** 2
        Ixy = Ix * Iy
        Ixt = Ix * It
        Iyt = Iy * It

        u = np.zeros((h, w), dtype=np.float32)
        v = np.zeros((h, w), dtype=np.float32)

        if self.adaptive_window:
            win_sizes = self._compute_adaptive_windows(prev_gray)
            unique_wins = np.unique(win_sizes)
            u_list = []
            v_list = []
            for ws in unique_wins:
                if ws < 3:
                    ws = 3
                k = np.ones((ws, ws), dtype=np.float32) / (ws * ws)
                Ix2_w = cv2.filter2D(Ix2, -1, k)
                Iy2_w = cv2.filter2D(Iy2, -1, k)
                Ixy_w = cv2.filter2D(Ixy, -1, k)
                Ixt_w = cv2.filter2D(Ixt, -1, k)
                Iyt_w = cv2.filter2D(Iyt, -1, k)
                denom = Ix2_w * Iy2_w - Ixy_w ** 2 + 1e-6
                u_w = - (Iy2_w * Ixt_w - Ixy_w * Iyt_w) / denom
                v_w = - (Ix2_w * Iyt_w - Ixy_w * Ixt_w) / denom
                u_list.append(u_w)
                v_list.append(v_w)

            for idx, ws in enumerate(unique_wins):
                mask = (win_sizes == ws)
                u[mask] = u_list[idx][mask]
                v[mask] = v_list[idx][mask]
        else:
            kernel = np.ones((self.win_size, self.win_size), dtype=np.float32) / (self.win_size ** 2)
            for _ in range(5):
                u_avg = cv2.filter2D(u, -1, kernel_small)
                v_avg = cv2.filter2D(v, -1, kernel_small)

                Ix2_smooth = cv2.filter2D(Ix2, -1, kernel)
                Iy2_smooth = cv2.filter2D(Iy2, -1, kernel)
                Ixy_smooth = cv2.filter2D(Ixy, -1, kernel)
                Ixt_smooth = cv2.filter2D(Ixt, -1, kernel)
                Iyt_smooth = cv2.filter2D(Iyt, -1, kernel)

                denom = Ix2_smooth * Iy2_smooth - Ixy_smooth ** 2 + 1e-6

                u = u_avg - (Iy2_smooth * Ixt_smooth - Ixy_smooth * Iyt_smooth) / denom
                v = v_avg - (Ix2_smooth * Iyt_smooth - Ixy_smooth * Ixt_smooth) / denom

        flow[:, :, 0] = u
        flow[:, :, 1] = v
        return flow

    def _compute_adaptive_windows(self, gray: np.ndarray) -> np.ndarray:
        """
        根据结构张量计算自适应窗口大小

        结构张量: M = [[∑Ix², ∑IxIy], [∑IxIy, ∑Iy²]]
        计算特征值 λ1 ≥ λ2:
        - λ1, λ2 都大 → 角点 → 小窗口
        - λ1 大, λ2 小 → 边缘 → 中等窗口
        - λ1, λ2 都小 → 平坦 → 大窗口

        返回:
            每个像素的窗口大小 (H, W), 保证为奇数
        """
        h, w = gray.shape

        gray_f = gray.astype(np.float32)
        Ix = cv2.Sobel(gray_f, cv2.CV_32F, 1, 0, ksize=3)
        Iy = cv2.Sobel(gray_f, cv2.CV_32F, 0, 1, ksize=3)

        Ix2 = Ix ** 2
        Iy2 = Iy ** 2
        Ixy = Ix * Iy

        k = np.ones((5, 5), dtype=np.float32) / 25.0
        Ix2_s = cv2.filter2D(Ix2, -1, k)
        Iy2_s = cv2.filter2D(Iy2, -1, k)
        Ixy_s = cv2.filter2D(Ixy, -1, k)

        trace = Ix2_s + Iy2_s
        det = Ix2_s * Iy2_s - Ixy_s ** 2

        sqrt_term = np.sqrt(np.maximum(trace ** 2 / 4 - det, 0))
        lambda1 = trace / 2 + sqrt_term
        lambda2 = trace / 2 - sqrt_term

        lambda2 = np.maximum(lambda2, 0)

        corner_response = lambda2
        corner_norm = (corner_response - corner_response.min()) / (corner_response.max() - corner_response.min() + 1e-8)

        win_range = self.win_max - self.win_min
        win_sizes = self.win_max - (corner_norm * win_range).astype(np.int32)

        win_sizes = np.clip(win_sizes, self.win_min, self.win_max)
        win_sizes = (win_sizes // 2) * 2 + 1

        return win_sizes

    def reset(self):
        """重置内部状态"""
        self.prev_gray = None
        self.prev_pts = None