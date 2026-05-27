import numpy as np
import cv2
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from typing import Optional
import sys
import time

from optical_flow.algorithms import LucasKanade, Farneback
from optical_flow.visualization import flow_to_hsv, flow_to_rgb, draw_vector_field, create_color_wheel
from optical_flow.metrics import compute_metrics, compute_epe, compute_aee

try:
    from optical_flow.algorithms import RAFT
    _HAS_RAFT = True
except ImportError:
    _HAS_RAFT = False


ALGORITHM_NAMES = {
    'lk_sparse': 'Lucas-Kanade (Sparse)',
    'lk_dense': 'Lucas-Kanade (Dense)',
    'farneback': 'Farneback',
    'raft': 'RAFT',
}


class SyntheticGenerator:
    """
    合成光流测试数据生成器

    生成已知运动的合成图像对和对应的真实光流,
    用于评估光流估计算法的精度。
    """

    @staticmethod
    def translate(size: int = 256, dx: float = 5.0, dy: float = 3.0, pattern: str = 'checker') -> tuple:
        """
        生成平移运动的图像对

        参数:
            size: 图像尺寸
            dx, dy: 平移量 (像素)
            pattern: 'checker' 棋盘格, 'noise' 随机噪声, 'gaussian' 高斯斑点

        返回:
            (frame1, frame2, gt_flow)
        """
        frame1 = SyntheticGenerator._generate_pattern(size, pattern)
        h, w = frame1.shape

        M = np.float32([[1, 0, dx], [0, 1, dy]])
        frame2 = cv2.warpAffine(frame1, M, (w, h))

        gt_flow = np.zeros((h, w, 2), dtype=np.float32)
        gt_flow[:, :, 0] = dx
        gt_flow[:, :, 1] = dy

        frame1_bgr = cv2.cvtColor(frame1, cv2.COLOR_GRAY2BGR)
        frame2_bgr = cv2.cvtColor(frame2, cv2.COLOR_GRAY2BGR)
        return frame1_bgr, frame2_bgr, gt_flow

    @staticmethod
    def rotate(size: int = 256, angle: float = 5.0, center: Optional[tuple] = None, pattern: str = 'gaussian') -> tuple:
        """
        生成旋转运动的图像对

        参数:
            size: 图像尺寸
            angle: 旋转角度 (度)
            center: 旋转中心, 若为 None 则使用图像中心
            pattern: 背景图案类型

        返回:
            (frame1, frame2, gt_flow)
        """
        frame1 = SyntheticGenerator._generate_pattern(size, pattern)
        h, w = frame1.shape

        if center is None:
            center = (w / 2, h / 2)

        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        frame2 = cv2.warpAffine(frame1, M, (w, w))

        gt_flow = SyntheticGenerator._compute_rotation_flow(h, w, center, np.radians(angle))

        frame1_bgr = cv2.cvtColor(frame1, cv2.COLOR_GRAY2BGR)
        frame2_bgr = cv2.cvtColor(frame2, cv2.COLOR_GRAY2BGR)
        return frame1_bgr, frame2_bgr, gt_flow

    @staticmethod
    def sinusoidal(size: int = 256, amp: float = 4.0, freq: float = 0.02, pattern: str = 'noise') -> tuple:
        """
        生成正弦运动的图像对

        参数:
            size: 图像尺寸
            amp: 运动幅度
            freq: 运动频率
            pattern: 背景图案类型

        返回:
            (frame1, frame2, gt_flow)
        """
        frame1 = SyntheticGenerator._generate_pattern(size, pattern)
        h, w = frame1.shape

        ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
        u = amp * np.sin(2 * np.pi * freq * xs)
        v = amp * np.cos(2 * np.pi * freq * ys)

        map_x = (xs + u).astype(np.float32)
        map_y = (ys + v).astype(np.float32)
        frame2 = cv2.remap(frame1, map_x, map_y, cv2.INTER_LINEAR)

        gt_flow = np.stack([u, v], axis=-1).astype(np.float32)

        frame1_bgr = cv2.cvtColor(frame1, cv2.COLOR_GRAY2BGR)
        frame2_bgr = cv2.cvtColor(frame2, cv2.COLOR_GRAY2BGR)
        return frame1_bgr, frame2_bgr, gt_flow

    @staticmethod
    def _generate_pattern(size: int, pattern: str) -> np.ndarray:
        """生成指定类型的背景图案"""
        if pattern == 'checker':
            img = np.zeros((size, size), dtype=np.uint8)
            block = size // 8
            for i in range(8):
                for j in range(8):
                    if (i + j) % 2 == 0:
                        img[i * block:(i + 1) * block, j * block:(j + 1) * block] = 255
            return img
        elif pattern == 'noise':
            return np.random.randint(0, 256, (size, size), dtype=np.uint8)
        elif pattern == 'gaussian':
            xx, yy = np.meshgrid(np.linspace(-1, 1, size), np.linspace(-1, 1, size))
            img = np.zeros((size, size), dtype=np.uint8)
            for _ in range(50):
                cx = np.random.uniform(-0.8, 0.8)
                cy = np.random.uniform(-0.8, 0.8)
                sigma = np.random.uniform(0.05, 0.2)
                g = np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * sigma ** 2))
                img = np.maximum(img, (g * 255).astype(np.uint8))
            return img
        else:
            return np.random.randint(0, 256, (size, size), dtype=np.uint8)

    @staticmethod
    def _compute_rotation_flow(h: int, w: int, center: tuple, angle_rad: float) -> np.ndarray:
        """计算旋转运动的真实光流"""
        ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
        cx, cy = center
        dx = xs - cx
        dy = ys - cy
        r = np.sqrt(dx ** 2 + dy ** 2)

        u = -r * np.sin(angle_rad) * np.cos(np.arctan2(dy, dx))
        v = r * np.cos(angle_rad) * np.sin(np.arctan2(dy, dx))

        u = dx * (np.cos(angle_rad) - 1) - dy * np.sin(angle_rad)
        v = dx * np.sin(angle_rad) + dy * (np.cos(angle_rad) - 1)

        return np.stack([u, v], axis=-1).astype(np.float32)


class OpticalFlowDemo:
    """
    光流估计交互演示

    功能:
        - 支持摄像头 / 视频文件 / 合成测试数据
        - 多种算法切换 (LK Sparse, LK Dense, Farneback, RAFT)
        - HSV 光流可视化
        - 矢量场显示
        - 评估指标计算 (AEE, EPE, Fl Error)
        - 参数实时调整
    """

    def __init__(self, source: str = 'camera', video_path: Optional[str] = None, synthetic_type: str = 'translate'):
        self.source = source
        self.video_path = video_path
        self.synthetic_type = synthetic_type

        self.algorithms: dict = {
            'lk_sparse': LucasKanade(mode='sparse'),
            'lk_dense': LucasKanade(mode='dense'),
            'farneback': Farneback(),
        }
        if _HAS_RAFT:
            self.algorithms['raft'] = RAFT(num_iters=6)
        self.current_alg = 'farneback'

        self.prev_frame = None
        self.gt_flow = None
        self.frame_count = 0

        self.win_name = 'Optical Flow Demo'
        self.show_vector = False
        self.show_gt = False
        self.median_filter = 0
        self.smooth_flow = False

        self.cap = None

    def __enter__(self):
        if self.source == 'camera':
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                raise RuntimeError('无法打开摄像头')
        elif self.source == 'video':
            if self.video_path is None:
                raise ValueError('视频文件路径未指定')
            self.cap = cv2.VideoCapture(self.video_path)
            if not self.cap.isOpened():
                raise RuntimeError(f'无法打开视频文件: {self.video_path}')
        return self

    def __exit__(self, *args):
        if self.cap is not None:
            self.cap.release()
        cv2.destroyAllWindows()

    def _get_frame(self) -> Optional[np.ndarray]:
        """获取下一帧图像"""
        if self.source == 'synthetic':
            if self.frame_count % 2 == 0:
                if self.synthetic_type == 'translate':
                    self.prev_frame, frame, self.gt_flow = SyntheticGenerator.translate()
                elif self.synthetic_type == 'rotate':
                    self.prev_frame, frame, self.gt_flow = SyntheticGenerator.rotate()
                elif self.synthetic_type == 'sinusoidal':
                    self.prev_frame, frame, self.gt_flow = SyntheticGenerator.sinusoidal()
                else:
                    self.prev_frame, frame, self.gt_flow = SyntheticGenerator.translate()
                self.frame_count += 1
                return frame
            else:
                self.frame_count += 1
                return self.prev_frame
        else:
            ret, frame = self.cap.read()
            if not ret:
                return None
            return frame

    def run(self):
        """运行交互演示"""
        alg_keys = list(self.algorithms.keys())
        alg_labels = [ALGORITHM_NAMES.get(k, k) for k in alg_keys]

        print('=' * 60)
        print('  光流估计交互演示')
        print('=' * 60)
        print('  控制键:')
        for i, (key, label) in enumerate(zip(alg_keys, alg_labels)):
            print(f'    {i+1}:   切换算法 ({label})')
        print('    v:   切换矢量场显示')
        print('    g:   切换真实光流显示 (仅合成数据)')
        print('    m:   切换中值滤波平滑 (0/3/5/7)')
        print('    s:   切换光流场预平滑')
        print('    r:   重置算法状态')
        print('    q/ESC: 退出')
        print('=' * 60)

        self._create_trackbars()

        while True:
            frame = self._get_frame()
            if frame is None:
                break

            alg = self.algorithms[self.current_alg]

            flow = alg.compute(frame, self.prev_frame)

            if self.prev_frame is not None:
                flow_vis = flow_to_hsv(
                    flow,
                    median_filter=self.median_filter,
                    smooth_flow=self.smooth_flow,
                )
            else:
                flow_vis = np.zeros_like(frame)

            self.prev_frame = frame

            display = self._create_display(frame, flow, flow_vis)

            cv2.imshow(self.win_name, display)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == 27:
                break
            elif ord('1') <= key < ord('1') + len(alg_keys):
                idx = key - ord('1')
                self.current_alg = alg_keys[idx]
                print(f'切换到: {ALGORITHM_NAMES.get(self.current_alg, self.current_alg)}')
            elif key == ord('v'):
                self.show_vector = not self.show_vector
                print(f'矢量场显示: {"开" if self.show_vector else "关"}')
            elif key == ord('g'):
                self.show_gt = not self.show_gt
                print(f'真实光流显示: {"开" if self.show_gt else "关"}')
            elif key == ord('m'):
                cycles = [0, 3, 5, 7]
                idx = cycles.index(self.median_filter) if self.median_filter in cycles else 0
                self.median_filter = cycles[(idx + 1) % len(cycles)]
                print(f'中值滤波核大小: {self.median_filter}')
            elif key == ord('s'):
                self.smooth_flow = not self.smooth_flow
                print(f'光流场预平滑: {"开" if self.smooth_flow else "关"}')
            elif key == ord('r'):
                for a in self.algorithms.values():
                    a.reset()
                print('算法状态已重置')

            self._read_trackbars()

        cv2.destroyAllWindows()

    def _create_trackbars(self):
        """创建参数调整的 trackbar"""
        cv2.namedWindow(self.win_name, cv2.WINDOW_NORMAL)

        fb_params = [
            ('pyr_scale', 1, 10),
            ('levels', 1, 8),
            ('winsize', 1, 30),
            ('iterations', 1, 10),
        ]

        for name, default, max_val in fb_params:
            cv2.createTrackbar(name, self.win_name, default, max_val, lambda x: None)

    def _read_trackbars(self):
        """读取 trackbar 值并更新参数"""
        try:
            pyr_scale = cv2.getTrackbarPos('pyr_scale', self.win_name) / 10.0
            levels = cv2.getTrackbarPos('levels', self.win_name)
            winsize = cv2.getTrackbarPos('winsize', self.win_name) * 2 + 1
            iterations = cv2.getTrackbarPos('iterations', self.win_name)

            self.algorithms['farneback'] = Farneback(
                pyr_scale=pyr_scale,
                levels=levels,
                winsize=winsize,
                iterations=iterations,
            )
        except Exception:
            pass

    def _create_display(self, frame: np.ndarray, flow: np.ndarray, flow_vis: np.ndarray) -> np.ndarray:
        """创建显示画面"""
        h, w = frame.shape[:2]

        info_bar = np.zeros((60, w, 3), dtype=np.uint8)
        info_bar[:] = (40, 40, 40)

        alg_name = ALGORITHM_NAMES[self.current_alg]
        cv2.putText(info_bar, f'Algorithm: {alg_name}', (10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

        mag = np.sqrt(flow[..., 0] ** 2 + flow[..., 1] ** 2)
        mean_mag = mag.mean() if mag.size > 0 else 0
        max_mag = mag.max() if mag.size > 0 else 0
        cv2.putText(info_bar, f'Mean Mag: {mean_mag:.2f}  Max Mag: {max_mag:.2f}',
                    (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

        if self.gt_flow is not None and self.prev_frame is not None:
            metrics = compute_metrics(flow, self.gt_flow)
            cv2.putText(info_bar, f'AEE: {metrics["AEE"]:.3f}  EPE: {metrics["EPE_mean"]:.3f}',
                        (w - 350, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 100), 1)
            cv2.putText(info_bar, f'Fl Error: {metrics["Fl_error"]:.3f}',
                        (w - 350, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 100), 1)

        filter_info = f'Median: {self.median_filter}  Smooth: {self.smooth_flow}'
        cv2.putText(info_bar, filter_info, (w - 280, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 200, 255), 1)

        display = np.vstack([frame, flow_vis])

        if self.show_vector and self.prev_frame is not None:
            vec_vis = self._render_vector_field(flow, frame.shape[:2])
            display = np.vstack([display, vec_vis])

        if self.show_gt and self.gt_flow is not None:
            gt_vis = flow_to_hsv(self.gt_flow)
            cv2.putText(gt_vis, 'Ground Truth', (10, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            display = np.hstack([display, np.vstack([frame, gt_vis])])

        display = np.vstack([info_bar, display])

        return display

    def _render_vector_field(self, flow: np.ndarray, shape: tuple) -> np.ndarray:
        """将矢量场渲染为图像"""
        h, w = shape
        vec_img = np.ones((h, w, 3), dtype=np.uint8) * 255

        step = max(h // 30, 16)
        for y in range(0, h, step):
            for x in range(0, w, step):
                u, v = flow[y, x]
                if abs(u) > 0.5 or abs(v) > 0.5:
                    end_x = int(x + u * 3)
                    end_y = int(y + v * 3)
                    cv2.arrowedLine(vec_img, (x, y), (end_x, end_y), (0, 0, 255), 1, tipLength=0.3)

        cv2.putText(vec_img, 'Vector Field', (10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 1)
        return vec_img

    def run_matplotlib_demo(self):
        """使用 Matplotlib 的完整演示 (含矢量场和色轮)"""
        print('生成合成测试数据...')

        fig = plt.figure(figsize=(18, 12))
        gs = GridSpec(3, 4, figure=fig, hspace=0.3, wspace=0.3)

        test_cases = {
            'Translate': SyntheticGenerator.translate(),
            'Rotate': SyntheticGenerator.rotate(),
            'Sinusoidal': SyntheticGenerator.sinusoidal(),
        }

        algs_to_show = ['lk_sparse', 'farneback']
        alg_labels = ['LK Sparse', 'Farneback']

        for row, (case_name, (f1, f2, gt)) in enumerate(test_cases.items()):
            ax = fig.add_subplot(gs[row, 0])
            ax.imshow(cv2.cvtColor(f2, cv2.COLOR_BGR2RGB))
            ax.set_title(f'{case_name}: Frame 2', fontsize=9)
            ax.axis('off')

            ax = fig.add_subplot(gs[row, 1])
            gt_rgb = flow_to_rgb(gt)
            ax.imshow(gt_rgb)
            ax.set_title('Ground Truth Flow', fontsize=9)
            ax.axis('off')

            for col, (alg_key, alg_label) in enumerate(zip(algs_to_show, alg_labels)):
                alg = self.algorithms[alg_key]
                alg.reset()
                flow = alg.compute(f2, f1)

                ax = fig.add_subplot(gs[row, col + 2])
                flow_rgb = flow_to_rgb(flow)
                ax.imshow(flow_rgb)

                metrics = compute_metrics(flow, gt)
                ax.set_title(f'{alg_label} (AEE: {metrics["AEE"]:.2f})', fontsize=9)
                ax.axis('off')

        fig.suptitle('Optical Flow Algorithm Comparison', fontsize=14, fontweight='bold')
        plt.tight_layout()
        plt.show()


def main():
    """主入口函数"""
    import argparse

    parser = argparse.ArgumentParser(description='光流估计交互演示')
    parser.add_argument('--source', type=str, default='camera',
                        choices=['camera', 'video', 'synthetic', 'matplotlib'],
                        help='输入源类型')
    parser.add_argument('--video', type=str, default=None, help='视频文件路径')
    parser.add_argument('--synthetic', type=str, default='translate',
                        choices=['translate', 'rotate', 'sinusoidal'],
                        help='合成数据类型')
    args = parser.parse_args()

    if args.source == 'matplotlib':
        demo = OpticalFlowDemo()
        demo.run_matplotlib_demo()
    else:
        with OpticalFlowDemo(
            source=args.source,
            video_path=args.video,
            synthetic_type=args.synthetic,
        ) as demo:
            demo.run()


if __name__ == '__main__':
    main()