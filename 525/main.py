import numpy as np
import cv2
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button
import warnings
import argparse

from lf_decoder import LightFieldDecoder, create_synthetic_lightfield, create_gradient_lightfield
from lf_refocus import (LightFieldRefocus, auto_focus, evaluate_sharpness,
                          FocusTracker, AllInFocusSynthesizer, DepthOfFieldExtender)
from depth_estimation import DepthEstimator, depth_to_pointcloud, save_pointcloud_ply
from gpu_accelerator import GPULightFieldRefocus, check_gpu_available, benchmark_refocus

warnings.filterwarnings('ignore')


class LightFieldGUI:
    def __init__(self, lf_data: np.ndarray):
        self.lf_data = lf_data
        self.refocus = LightFieldRefocus(lf_data)
        self.depth_estimator = DepthEstimator(lf_data)
        self.all_focus_synth = AllInFocusSynthesizer(self.refocus)
        self.dof_extender = DepthOfFieldExtender(self.refocus)
        self.focus_tracker = None
        
        self.current_alpha = 0.0
        self.current_aperture = 1.0
        self.depth_map = None
        
        self.use_gpu = False
        self.gpu_refocus = None
        
        self.fig, self.axes = plt.subplots(2, 3, figsize=(15, 10))
        self.fig.suptitle('光场相机数字重聚焦系统', fontsize=16)
        
        self._setup_widgets()
        self._initialize_views()
        
    def _setup_widgets(self):
        self.fig.subplots_adjust(bottom=0.30)
        
        ax_alpha = plt.axes([0.15, 0.20, 0.7, 0.03])
        ax_aperture = plt.axes([0.15, 0.15, 0.7, 0.03])
        
        self.slider_alpha = Slider(
            ax=ax_alpha,
            label='焦深 (Alpha)',
            valmin=self.refocus.focal_depth_range[0],
            valmax=self.refocus.focal_depth_range[1],
            valinit=0.0,
            valstep=0.1
        )
        
        self.slider_aperture = Slider(
            ax=ax_aperture,
            label='光圈大小',
            valmin=0.1,
            valmax=1.0,
            valinit=1.0,
            valstep=0.1
        )
        
        self.slider_alpha.on_changed(self._update_refocus)
        self.slider_aperture.on_changed(self._update_refocus)
        
        ax_auto_focus = plt.axes([0.04, 0.08, 0.13, 0.04])
        ax_all_focus = plt.axes([0.18, 0.08, 0.13, 0.04])
        ax_depth = plt.axes([0.32, 0.08, 0.13, 0.04])
        ax_dof_ext = plt.axes([0.46, 0.08, 0.13, 0.04])
        ax_bokeh = plt.axes([0.60, 0.08, 0.13, 0.04])
        ax_track = plt.axes([0.74, 0.08, 0.13, 0.04])
        ax_lap = plt.axes([0.04, 0.03, 0.13, 0.04])
        ax_save = plt.axes([0.18, 0.03, 0.13, 0.04])
        
        self.btn_auto_focus = Button(ax_auto_focus, '自动对焦')
        self.btn_all_focus = Button(ax_all_focus, '全焦合成')
        self.btn_depth = Button(ax_depth, '估计深度')
        self.btn_dof_ext = Button(ax_dof_ext, '景深扩展')
        self.btn_bokeh = Button(ax_bokeh, '散景渲染')
        self.btn_track = Button(ax_track, '焦点跟踪')
        self.btn_lap = Button(ax_lap, '拉普拉斯融合')
        self.btn_save = Button(ax_save, '保存结果')
        
        self.btn_auto_focus.on_clicked(self._on_auto_focus)
        self.btn_all_focus.on_clicked(self._on_all_focus)
        self.btn_depth.on_clicked(self._on_estimate_depth)
        self.btn_dof_ext.on_clicked(self._on_dof_extend)
        self.btn_bokeh.on_clicked(self._on_bokeh)
        self.btn_track.on_clicked(self._on_track_focus)
        self.btn_lap.on_clicked(self._on_laplacian_blend)
        self.btn_save.on_clicked(self._on_save)
        
    def _initialize_views(self):
        center_view = self.lf_data[self.refocus.center_vy, self.refocus.center_vx]
        
        self.axes[0, 0].imshow(cv2.cvtColor(center_view, cv2.COLOR_BGR2RGB))
        self.axes[0, 0].set_title('中心视角')
        self.axes[0, 0].axis('off')
        
        refocused = self.refocus.refocus_fast(0.0, 1.0)
        self.im_refocus = self.axes[0, 1].imshow(cv2.cvtColor(refocused, cv2.COLOR_BGR2RGB))
        self.axes[0, 1].set_title('重聚焦结果')
        self.axes[0, 1].axis('off')
        
        grid_view = self._create_view_grid()
        self.axes[0, 2].imshow(cv2.cvtColor(grid_view, cv2.COLOR_BGR2RGB))
        self.axes[0, 2].set_title('视角阵列')
        self.axes[0, 2].axis('off')
        
        epi_image = self._create_epipolar_image()
        self.axes[1, 0].imshow(cv2.cvtColor(epi_image, cv2.COLOR_BGR2RGB))
        self.axes[1, 0].set_title('极平面图像 (EPI)')
        self.axes[1, 0].axis('off')
        
        self.im_depth = self.axes[1, 1].imshow(np.zeros((self.refocus.img_h, self.refocus.img_w)), 
                                                cmap='jet', vmin=0, vmax=1)
        self.axes[1, 1].set_title('深度图')
        self.axes[1, 1].axis('off')
        
        sharpness_img = self._compute_sharpness_map(refocused)
        self.im_sharpness = self.axes[1, 2].imshow(sharpness_img, cmap='hot')
        self.axes[1, 2].set_title('清晰度分布')
        self.axes[1, 2].axis('off')
        
    def _create_view_grid(self) -> np.ndarray:
        num_views_y, num_views_x = self.lf_data.shape[:2]
        h, w = self.lf_data.shape[2:4]
        
        grid_size = 3
        step_x = max(1, num_views_x // grid_size)
        step_y = max(1, num_views_y // grid_size)
        
        grid = np.zeros((h * grid_size, w * grid_size, 3), dtype=np.uint8)
        
        for i, vy in enumerate(range(0, num_views_y, step_y)[:grid_size]):
            for j, vx in enumerate(range(0, num_views_x, step_x)[:grid_size]):
                grid[i*h:(i+1)*h, j*w:(j+1)*w] = self.lf_data[vy, vx]
        
        return grid
    
    def _create_epipolar_image(self) -> np.ndarray:
        y_mid = self.refocus.img_h // 2
        epi = self.lf_data[self.refocus.center_vy, :, y_mid, :, :]
        epi = np.transpose(epi, (1, 0, 2))
        return epi
    
    def _compute_sharpness_map(self, image: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        laplacian = cv2.Laplacian(gray, cv2.CV_32F)
        sharpness = np.abs(laplacian)
        sharpness = cv2.normalize(sharpness, None, 0, 1, cv2.NORM_MINMAX)
        return sharpness
    
    def _update_refocus(self, val):
        self.current_alpha = self.slider_alpha.val
        self.current_aperture = self.slider_aperture.val
        
        refocused = self.refocus.refocus_fast(self.current_alpha, self.current_aperture)
        
        self.im_refocus.set_data(cv2.cvtColor(refocused, cv2.COLOR_BGR2RGB))
        
        sharpness = self._compute_sharpness_map(refocused)
        self.im_sharpness.set_data(sharpness)
        
        self.fig.canvas.draw_idle()
    
    def _on_auto_focus(self, event):
        best_alpha, best_image = auto_focus(self.refocus)
        self.slider_alpha.set_val(best_alpha)
        print(f"自动对焦完成，最佳Alpha值: {best_alpha:.2f}")
    
    def _on_all_focus(self, event):
        print("正在执行全焦图像合成（多焦平面软融合）...")
        all_focus, depth_map = self.all_focus_synth.synthesize(
            num_planes=15, blend_sigma=2.0, edge_aware=True
        )
        self.im_refocus.set_data(cv2.cvtColor(all_focus, cv2.COLOR_BGR2RGB))
        self.im_depth.set_data(depth_map)
        self.depth_map = depth_map
        self.dof_extender.depth_map = depth_map
        self.fig.canvas.draw_idle()
        print("全焦合成完成（边缘感知软融合）")
    
    def _on_estimate_depth(self, event):
        print("正在估计深度...")
        self.depth_map = self.depth_estimator.estimate_depth_focus_stack(num_planes=10)
        self.im_depth.set_data(self.depth_map)
        self.dof_extender.depth_map = self.depth_map
        self.fig.canvas.draw_idle()
        print("深度估计完成")
    
    def _on_dof_extend(self, event):
        print("正在执行景深扩展...")
        result = self.dof_extender.extend_dof(
            target_alpha=self.current_alpha,
            depth_range=0.3,
            aperture_size=self.current_aperture,
            num_layers=7
        )
        self.im_refocus.set_data(cv2.cvtColor(result, cv2.COLOR_BGR2RGB))
        self.fig.canvas.draw_idle()
        print(f"景深扩展完成 (alpha={self.current_alpha:.1f}, 深度范围=0.3)")
    
    def _on_bokeh(self, event):
        print("正在渲染散景效果...")
        result = self.dof_extender.bokeh_render(
            focus_depth=0.5,
            dof_width=0.05,
            aperture_shape='circular',
            aperture_size=self.current_aperture,
            highlight_boost=1.5
        )
        self.im_refocus.set_data(cv2.cvtColor(result, cv2.COLOR_BGR2RGB))
        self.fig.canvas.draw_idle()
        print("散景渲染完成（圆形光圈 + 高光增强）")
    
    def _on_track_focus(self, event):
        print("正在初始化焦点跟踪...")
        if self.focus_tracker is None:
            self.focus_tracker = FocusTracker(self.refocus, self.depth_map)
            cx = self.refocus.img_w // 2
            cy = self.refocus.img_h // 2
            tid = self.focus_tracker.add_target_point((cx, cy), window=30, tracker_type='csrt')
            print(f"已添加跟踪目标 #{tid}，中心 ({cx}, {cy})")
        
        result, tracking = self.focus_tracker.refocus_tracked(aperture_size=self.current_aperture)
        self.im_refocus.set_data(cv2.cvtColor(result, cv2.COLOR_BGR2RGB))
        
        vis = self.focus_tracker.draw_trajectories(
            self.lf_data[self.refocus.center_vy, self.refocus.center_vx]
        )
        self.axes[0, 0].imshow(cv2.cvtColor(vis, cv2.COLOR_BGR2RGB))
        
        for tid, info in tracking.items():
            if info.get('active', False):
                print(f"  目标 #{tid}: 中心=({info['center'][0]:.0f}, {info['center'][1]:.0f}), "
                      f"alpha={info['alpha']:.2f}")
        
        self.fig.canvas.draw_idle()
        print("焦点跟踪完成")
    
    def _on_laplacian_blend(self, event):
        print("正在执行拉普拉斯金字塔融合...")
        all_focus, depth_map = self.all_focus_synth.synthesize_laplacian(
            num_planes=10, levels=3
        )
        self.im_refocus.set_data(cv2.cvtColor(all_focus, cv2.COLOR_BGR2RGB))
        self.im_depth.set_data(depth_map)
        self.depth_map = depth_map
        self.dof_extender.depth_map = depth_map
        self.fig.canvas.draw_idle()
        print("拉普拉斯金字塔融合完成")
    
    def _on_save(self, event):
        refocused = self.refocus.refocus_fast(self.current_alpha, self.current_aperture)
        cv2.imwrite('refocused_result.png', refocused)
        print("重聚焦结果已保存到 refocused_result.png")
        
        if self.depth_map is not None:
            depth_colored = cv2.applyColorMap((self.depth_map * 255).astype(np.uint8), cv2.COLORMAP_JET)
            cv2.imwrite('depth_map.png', depth_colored)
            print("深度图已保存到 depth_map.png")
            
            center_view = self.lf_data[self.refocus.center_vy, self.refocus.center_vx]
            points, colors = depth_to_pointcloud(self.depth_map, center_view)
            save_pointcloud_ply('pointcloud.ply', points, colors)
            print("点云已保存到 pointcloud.ply")
    
    def run(self):
        plt.tight_layout(rect=[0, 0.2, 1, 1])
        plt.show()


def generate_test_scene() -> np.ndarray:
    h, w = 256, 256
    num_views = 9
    lf_data = np.zeros((num_views, num_views, h, w, 3), dtype=np.uint8)
    
    half_v = num_views // 2
    
    for vy in range(num_views):
        for vx in range(num_views):
            du = vx - half_v
            dv = vy - half_v
            
            img = np.zeros((h, w, 3), dtype=np.uint8)
            
            cv2.circle(img, (w // 4 + du * 3, h // 4 + dv * 3), 25, (255, 0, 0), -1)
            
            cv2.circle(img, (w // 2 + du * 6, h // 2 + dv * 6), 30, (0, 255, 0), -1)
            
            cv2.rectangle(img, 
                        (3 * w // 4 + du * 9 - 25, 3 * h // 4 + dv * 9 - 25),
                        (3 * w // 4 + du * 9 + 25, 3 * h // 4 + dv * 9 + 25),
                        (0, 0, 255), -1)
            
            for i in range(5):
                x = np.random.randint(50, w - 50)
                y = np.random.randint(50, h - 50)
                cv2.circle(img, (x + du * 12, y + dv * 12), 5, (255, 255, 255), -1)
            
            lf_data[vy, vx] = img
    
    return lf_data


def demo_basic_refocus():
    print("=" * 50)
    print("光场相机重聚焦演示")
    print("=" * 50)
    
    print("\n1. 生成测试光场数据...")
    lf_data = generate_test_scene()
    print(f"   光场数据维度: {lf_data.shape}")
    
    print("\n2. 初始化重聚焦引擎...")
    refocus = LightFieldRefocus(lf_data, focal_depth_range=(-5.0, 5.0))
    
    print("\n3. 执行不同焦深的重聚焦...")
    alphas = [-3.0, -1.5, 0.0, 1.5, 3.0]
    
    fig, axes = plt.subplots(1, len(alphas), figsize=(15, 4))
    for i, alpha in enumerate(alphas):
        result = refocus.refocus_fast(alpha)
        sharpness = evaluate_sharpness(result)
        axes[i].imshow(cv2.cvtColor(result, cv2.COLOR_BGR2RGB))
        axes[i].set_title(f'α = {alpha:.1f}\n清晰度: {sharpness:.1f}')
        axes[i].axis('off')
    
    plt.suptitle('不同焦深的重聚焦效果')
    plt.tight_layout()
    plt.savefig('refocus_demo.png')
    print("   结果已保存到 refocus_demo.png")
    
    print("\n4. 估计深度图...")
    depth_estimator = DepthEstimator(lf_data)
    depth_map = depth_estimator.estimate_depth_focus_stack(num_planes=15)
    
    fig, axes = plt.subplots(1, 2, figsize=(10, 5))
    center_vy = lf_data.shape[0] // 2
    center_vx = lf_data.shape[1] // 2
    axes[0].imshow(cv2.cvtColor(lf_data[center_vy, center_vx], cv2.COLOR_BGR2RGB))
    axes[0].set_title('中心视角')
    axes[0].axis('off')
    
    im = axes[1].imshow(depth_map, cmap='jet')
    axes[1].set_title('估计深度图')
    axes[1].axis('off')
    plt.colorbar(im, ax=axes[1])
    plt.tight_layout()
    plt.savefig('depth_demo.png')
    print("   深度图已保存到 depth_demo.png")
    
    print("\n5. 全焦图像合成（多焦平面软融合）...")
    all_focus_synth = AllInFocusSynthesizer(refocus)
    all_focus, depth_from_synth = all_focus_synth.synthesize(
        num_planes=15, blend_sigma=2.0, edge_aware=True
    )
    cv2.imwrite('all_in_focus_soft.png', all_focus)
    print("   全焦图像已保存到 all_in_focus_soft.png")
    
    print("\n6. 拉普拉斯金字塔融合...")
    all_focus_lap, depth_lap = all_focus_synth.synthesize_laplacian(num_planes=10, levels=3)
    cv2.imwrite('all_in_focus_laplacian.png', all_focus_lap)
    print("   拉普拉斯融合结果已保存到 all_in_focus_laplacian.png")
    
    print("\n7. 景深扩展...")
    dof_ext = DepthOfFieldExtender(refocus, depth_map)
    dof_result = dof_ext.extend_dof(target_alpha=0.0, depth_range=0.3, num_layers=5)
    cv2.imwrite('dof_extended.png', dof_result)
    print("   景深扩展结果已保存到 dof_extended.png")
    
    print("\n8. 散景渲染...")
    bokeh_result = dof_ext.bokeh_render(
        focus_depth=0.5, dof_width=0.05,
        aperture_shape='circular', highlight_boost=1.5
    )
    cv2.imwrite('bokeh_result.png', bokeh_result)
    print("   散景渲染结果已保存到 bokeh_result.png")
    
    plt.show()


def demo_gui():
    print("启动光场重聚焦GUI界面...")
    lf_data = generate_test_scene()
    gui = LightFieldGUI(lf_data)
    gui.run()


def demo_gpu_acceleration():
    print("\n检查GPU加速能力...")
    gpu_info = check_gpu_available()
    print(f"CuPy可用: {gpu_info['cupy_available']}")
    print(f"Numba可用: {gpu_info['numba_available']}")
    if 'cuda_available' in gpu_info:
        print(f"CUDA可用: {gpu_info['cuda_available']}")
    if 'gpu_count' in gpu_info and gpu_info['gpu_count'] > 0:
        print(f"GPU数量: {gpu_info['gpu_count']}")
        if 'gpu_name' in gpu_info:
            print(f"GPU名称: {gpu_info['gpu_name']}")
    
    print("\n生成测试数据并进行性能测试...")
    lf_data = generate_test_scene()
    
    try:
        results = benchmark_refocus(lf_data, alpha=0.0)
        print(f"\n性能测试结果:")
        print(f"CPU 时间: {results['cpu_time']:.3f} 秒")
        if 'cupy_time' in results:
            print(f"CuPy 时间: {results['cupy_time']:.3f} 秒 (加速 {results['cupy_speedup']:.1f}x)")
        if 'numba_time' in results:
            print(f"Numba 时间: {results['numba_time']:.3f} 秒 (加速 {results['numba_speedup']:.1f}x)")
    except Exception as e:
        print(f"性能测试跳过: {e}")


def main():
    parser = argparse.ArgumentParser(description='光场相机数字重聚焦系统')
    parser.add_argument('--mode', type=str, default='gui', 
                       choices=['gui', 'demo', 'gpu', 'benchmark'],
                       help='运行模式')
    parser.add_argument('--image', type=str, default=None,
                       help='输入图像路径（用于生成合成光场）')
    
    args = parser.parse_args()
    
    if args.mode == 'gui':
        demo_gui()
    elif args.mode == 'demo':
        demo_basic_refocus()
    elif args.mode == 'gpu':
        demo_gpu_acceleration()
    elif args.mode == 'benchmark':
        demo_gpu_acceleration()


if __name__ == '__main__':
    main()
