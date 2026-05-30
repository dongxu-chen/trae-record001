import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button, RadioButtons, CheckButtons
from matplotlib.gridspec import GridSpec
from typing import Optional, Dict
import cv2

from lightfield import LightField
from depth_estimation import DepthEstimator
from fusion import MultiViewFusion
from evaluation import DepthEvaluator
from depth_effects import DepthOfFieldEffect, ApertureSynthesizer


class LightFieldDepthGUI:
    def __init__(self, light_field: LightField, ground_truth: Optional[np.ndarray] = None):
        self.lf = light_field
        self.ground_truth = ground_truth
        self.estimator = DepthEstimator(light_field)
        self.fusion = MultiViewFusion(light_field)
        self.evaluator = DepthEvaluator(ground_truth)
        self.dof_effect = DepthOfFieldEffect(light_field)
        self.aperture_synth = ApertureSynthesizer(light_field)
        
        self.current_depth = None
        self.current_confidence = None
        self.current_method = 'focus'
        self.gray_threshold = 0.3
        
        self.dof_focus_depth = 0.5
        self.dof_aperture = 0.3
        self.dof_enabled = False
        
        self._setup_gui()
        self._compute_initial_depth()
        
    def _setup_gui(self):
        self.fig = plt.figure(figsize=(18, 11))
        gs = GridSpec(3, 5, figure=self.fig, hspace=0.35, wspace=0.25)
        
        self.ax_center = self.fig.add_subplot(gs[0, 0])
        self.ax_center.set_title('中心视图 / 重聚焦')
        self.center_im = self.ax_center.imshow(
            self.lf.get_center_view(), 
            cmap='gray')
        
        self.ax_depth = self.fig.add_subplot(gs[0, 1])
        self.ax_depth.set_title('深度图 (低置信置灰)')
        self.depth_im = self.ax_depth.imshow(
            np.zeros((self.lf.height, self.lf.width)),
            cmap='jet')
        plt.colorbar(self.depth_im, ax=self.ax_depth, fraction=0.046, pad=0.04)
        
        self.ax_conf = self.fig.add_subplot(gs[0, 2])
        self.ax_conf.set_title('置信度图')
        self.conf_im = self.ax_conf.imshow(
            np.zeros((self.lf.height, self.lf.width)),
            cmap='viridis')
        plt.colorbar(self.conf_im, ax=self.ax_conf, fraction=0.046, pad=0.04)
        
        self.ax_dof = self.fig.add_subplot(gs[0, 3])
        self.ax_dof.set_title('景深效果预览')
        self.dof_im = self.ax_dof.imshow(
            self.lf.get_center_view(),
            cmap='gray')
        
        self.ax_density = self.fig.add_subplot(gs[0, 4])
        self.ax_density.set_title('梯度密度 / 低纹理掩码')
        grad_density, low_tex_mask = self.lf.compute_gradient_density()
        density_display = np.stack([
            grad_density,
            1.0 - low_tex_mask.astype(np.float32) * 0.6,
            grad_density
        ], axis=-1)
        self.density_im = self.ax_density.imshow(density_display)
        
        self.ax_epi = self.fig.add_subplot(gs[1, :3])
        self.ax_epi.set_title('EPI (极平面图像)')
        epi = self.lf.get_epi(self.lf.num_rows // 2, self.lf.height // 2)
        self.epi_im = self.ax_epi.imshow(epi, cmap='gray', aspect='auto')
        
        self.ax_eval = self.fig.add_subplot(gs[1, 3:])
        self.ax_eval.axis('off')
        self.eval_text = self.ax_eval.text(0.05, 0.95, '', 
                                          transform=self.ax_eval.transAxes,
                                          va='top', fontsize=10)
        
        self.ax_refocus_slider = plt.axes([0.1, 0.28, 0.45, 0.02])
        self.refocus_slider = Slider(
            ax=self.ax_refocus_slider,
            label='重聚焦平面 α',
            valmin=-2.0,
            valmax=2.0,
            valinit=0.0,
            valstep=0.1
        )
        self.refocus_slider.on_changed(self._on_refocus_change)
        
        self.ax_gray_slider = plt.axes([0.1, 0.24, 0.45, 0.02])
        self.gray_slider = Slider(
            ax=self.ax_gray_slider,
            label='置灰阈值',
            valmin=0.0,
            valmax=1.0,
            valinit=0.3,
            valstep=0.05
        )
        self.gray_slider.on_changed(self._on_gray_threshold_change)
        
        self.ax_dof_focus_slider = plt.axes([0.6, 0.28, 0.35, 0.02])
        self.dof_focus_slider = Slider(
            ax=self.ax_dof_focus_slider,
            label='对焦深度',
            valmin=0.0,
            valmax=1.0,
            valinit=0.5,
            valstep=0.05
        )
        self.dof_focus_slider.on_changed(self._on_dof_focus_change)
        
        self.ax_dof_aperture_slider = plt.axes([0.6, 0.24, 0.35, 0.02])
        self.dof_aperture_slider = Slider(
            ax=self.ax_dof_aperture_slider,
            label='光圈大小 (景深)',
            valmin=0.05,
            valmax=1.0,
            valinit=0.3,
            valstep=0.05
        )
        self.dof_aperture_slider.on_changed(self._on_dof_aperture_change)
        
        self.ax_method = plt.axes([0.02, 0.05, 0.12, 0.15])
        self.method_radio = RadioButtons(
            ax=self.ax_method,
            labels=['聚焦分析', '散焦分析', '视差估计', '多方法融合'],
            active=0
        )
        self.method_radio.on_clicked(self._on_method_change)
        
        self.ax_dof_check = plt.axes([0.16, 0.05, 0.1, 0.08])
        self.dof_check = CheckButtons(
            ax=self.ax_dof_check,
            labels=['启用DOF效果'],
            actives=[False]
        )
        self.dof_check.on_clicked(self._on_dof_toggle)
        
        self.ax_compute_btn = plt.axes([0.28, 0.05, 0.08, 0.05])
        self.compute_btn = Button(
            ax=self.ax_compute_btn,
            label='计算深度'
        )
        self.compute_btn.on_clicked(self._on_compute)
        
        self.ax_save_btn = plt.axes([0.38, 0.05, 0.08, 0.05])
        self.save_btn = Button(
            ax=self.ax_save_btn,
            label='保存结果'
        )
        self.save_btn.on_clicked(self._on_save)
        
        self.ax_refine_btn = plt.axes([0.48, 0.05, 0.08, 0.05])
        self.refine_btn = Button(
            ax=self.ax_refine_btn,
            label='优化深度'
        )
        self.refine_btn.on_clicked(self._on_refine)
        
        self.ax_apply_dof_btn = plt.axes([0.58, 0.05, 0.1, 0.05])
        self.apply_dof_btn = Button(
            ax=self.ax_apply_dof_btn,
            label='应用景深'
        )
        self.apply_dof_btn.on_clicked(self._on_apply_dof)
        
        self.ax_save_dof_btn = plt.axes([0.70, 0.05, 0.1, 0.05])
        self.save_dof_btn = Button(
            ax=self.ax_save_dof_btn,
            label='保存DOF图像'
        )
        self.save_dof_btn.on_clicked(self._on_save_dof)
        
        self.ax_benchmark_btn = plt.axes([0.82, 0.05, 0.12, 0.05])
        self.benchmark_btn = Button(
            ax=self.ax_benchmark_btn,
            label='性能基准测试'
        )
        self.benchmark_btn.on_clicked(self._on_benchmark)
    
    def _create_view_grid(self) -> np.ndarray:
        grid_h = self.lf.height
        grid_w = self.lf.width
        
        grid = np.zeros((grid_h * self.lf.num_rows, grid_w * self.lf.num_cols), dtype=np.float32)
        
        for r in range(self.lf.num_rows):
            for c in range(self.lf.num_cols):
                grid[r*grid_h:(r+1)*grid_h, c*grid_w:(c+1)*grid_w] = self.lf.images[r, c]
        
        return grid
    
    def _compute_initial_depth(self):
        self._on_method_change('聚焦分析')
        self._on_compute(None)
    
    def _on_refocus_change(self, val):
        alpha = self.refocus_slider.val
        refocused = self.estimator.refocus(alpha)
        self.center_im.set_data(refocused)
        self.fig.canvas.draw_idle()
    
    def _on_gray_threshold_change(self, val):
        self.gray_threshold = val
        self._update_display()
        self._update_evaluation()
    
    def _on_dof_focus_change(self, val):
        self.dof_focus_depth = val
        if self.dof_enabled and self.current_depth is not None:
            self._update_dof_preview()
    
    def _on_dof_aperture_change(self, val):
        self.dof_aperture = val
        if self.dof_enabled and self.current_depth is not None:
            self._update_dof_preview()
    
    def _on_dof_toggle(self, label):
        self.dof_enabled = self.dof_check.get_status()[0]
        if self.dof_enabled and self.current_depth is not None:
            self._update_dof_preview()
    
    def _on_method_change(self, label):
        method_map = {
            '聚焦分析': 'focus',
            '散焦分析': 'defocus',
            '视差估计': 'disparity',
            '多方法融合': 'fusion'
        }
        self.current_method = method_map.get(label, 'focus')
    
    def _on_compute(self, event):
        if self.current_method == 'focus':
            self.current_depth, self.current_confidence = self.estimator.estimate_depth_from_focus()
        elif self.current_method == 'defocus':
            self.current_depth, self.current_confidence = self.estimator.estimate_depth_from_defocus()
        elif self.current_method == 'disparity':
            self.current_depth, self.current_confidence = self.estimator.estimate_disparity()
        elif self.current_method == 'fusion':
            self.current_depth, self.current_confidence = self.fusion.multi_method_fusion()
        
        self._update_display()
        self._update_evaluation()
        if self.dof_enabled:
            self._update_dof_preview()
    
    def _on_refine(self, event):
        if self.current_depth is not None and self.current_confidence is not None:
            self.current_depth = self.fusion.refine_depth(
                self.current_depth, self.current_confidence)
            self._update_display()
            self._update_evaluation()
            if self.dof_enabled:
                self._update_dof_preview()
    
    def _on_apply_dof(self, event):
        if self.current_depth is not None:
            self._update_dof_preview()
    
    def _on_save_dof(self, event):
        if self.current_depth is not None:
            dof_image = self.dof_effect.apply_bokeh(
                self.current_depth,
                focus_depth=self.dof_focus_depth,
                aperture=self.dof_aperture,
                max_blur=15.0
            )
            dof_uint8 = (dof_image * 255).astype(np.uint8)
            cv2.imwrite('dof_result.png', dof_uint8)
            print("景深效果图像已保存: dof_result.png")
    
    def _on_benchmark(self, event):
        import time
        print("\n=== 性能基准测试 ===")
        
        lf_small = LightField.generate_synthetic(
            num_rows=5, num_cols=5, height=100, width=100, num_depths=2)
        
        est_cpu = DepthEstimator(lf_small, use_accelerated=False)
        est_accel = DepthEstimator(lf_small, use_accelerated=True)
        
        n_iter = 5
        
        t0 = time.time()
        for _ in range(n_iter):
            _, _ = est_cpu.estimate_depth_from_focus(adaptive=False, num_planes=10)
        cpu_time = (time.time() - t0) / n_iter
        
        t0 = time.time()
        for _ in range(n_iter):
            _, _ = est_accel.estimate_depth_from_focus(adaptive=True, num_planes=10)
        accel_time = (time.time() - t0) / n_iter
        
        speedup = cpu_time / max(accel_time, 1e-6)
        
        print(f"CPU (无加速): {cpu_time:.3f}s / 次")
        print(f"JIT加速版本:   {accel_time:.3f}s / 次")
        print(f"加速倍率:     {speedup:.1f}x")
        print("=" * 30)
        
        bench_text = (f"CPU: {cpu_time:.3f}s\n"
                     f"JIT: {accel_time:.3f}s\n"
                     f"加速: {speedup:.1f}x")
        self.eval_text.set_text(self.eval_text.get_text() + "\n\n性能基准:\n" + bench_text)
        self.fig.canvas.draw_idle()
    
    def _update_dof_preview(self):
        if self.current_depth is None:
            return
        
        dof_image = self.dof_effect.apply_bokeh(
            self.current_depth,
            focus_depth=self.dof_focus_depth,
            aperture=self.dof_aperture,
            max_blur=10.0
        )
        self.dof_im.set_data(dof_image)
        self.fig.canvas.draw_idle()
    
    def _on_save(self, event):
        if self.current_depth is not None:
            depth_norm = self.current_depth.copy()
            d_min, d_max = depth_norm.min(), depth_norm.max()
            if d_max - d_min > 1e-8:
                depth_norm = (depth_norm - d_min) / (d_max - d_min)
            else:
                depth_norm = np.zeros_like(depth_norm)
            
            depth_colored = cv2.applyColorMap(
                (depth_norm * 255).astype(np.uint8),
                cv2.COLORMAP_JET)

            if self.current_confidence is not None:
                low_conf_mask = self.current_confidence < self.gray_threshold
                depth_colored[low_conf_mask] = (depth_colored[low_conf_mask] * 0.3 + 128 * 0.7).astype(np.uint8)
            
            cv2.imwrite('depth_map.png', depth_colored)
            
            conf_colored = cv2.applyColorMap(
                (self.current_confidence * 255).astype(np.uint8),
                cv2.COLORMAP_VIRIDIS)
            cv2.imwrite('confidence_map.png', conf_colored)
            
            np.savez('depth_results.npz', 
                      depth=self.current_depth,
                      confidence=self.current_confidence)
            
            print("结果已保存: depth_map.png, confidence_map.png, depth_results.npz")
    
    def _update_display(self):
        if self.current_depth is not None:
            depth_norm = self.current_depth.copy()
            d_min, d_max = depth_norm.min(), depth_norm.max()
            if d_max - d_min > 1e-8:
                depth_norm = (depth_norm - d_min) / (d_max - d_min)
            else:
                depth_norm = np.zeros_like(depth_norm)

            cmap = plt.cm.jet
            depth_rgb = cmap(depth_norm)[:, :, :3]

            if self.current_confidence is not None:
                low_conf_mask = self.current_confidence < self.gray_threshold
                gray_val = np.array([0.5, 0.5, 0.5])
                depth_rgb[low_conf_mask] = depth_rgb[low_conf_mask] * 0.3 + gray_val * 0.7

            self.depth_im.set_data(depth_rgb)
            self.depth_im.set_clim(vmin=0, vmax=1)
        
        if self.current_confidence is not None:
            self.conf_im.set_data(self.current_confidence)
            self.conf_im.set_clim(vmin=0, vmax=1)
        
        self.fig.canvas.draw_idle()
    
    def _update_evaluation(self):
        if self.current_depth is not None and self.current_confidence is not None:
            results = self.evaluator.full_evaluation(
                self.current_depth, 
                self.current_confidence,
                self.ground_truth,
                self.lf.get_center_view(),
                texture_threshold=self.gray_threshold)
            
            eval_str = "深度评估 (高纹理区域):\n\n"
            
            if 'TextureCoverage' in results:
                eval_str += f"纹理覆盖率: {results['TextureCoverage']:.1%}\n"
            
            if 'MAE' in results:
                eval_str += f"MAE:  {results['MAE']:.4f}\n"
                eval_str += f"RMSE: {results['RMSE']:.4f}\n"
                eval_str += f"坏点率: {results['BadPixelRatio_0.07']:.2%}\n"
            
            eval_str += f"\n平滑度: {results['Smoothness']:.4f}\n"
            eval_str += f"平均置信度: {results['MeanConfidence']:.2%}\n"
            
            if 'MeanConfidence_HighTexture' in results:
                eval_str += f"高纹理置信度: {results['MeanConfidence_HighTexture']:.2%}\n"
                eval_str += f"低纹理置信度: {results['MeanConfidence_LowTexture']:.2%}\n"
            
            self.eval_text.set_text(eval_str)
    
    def run(self):
        plt.show()


class InteractiveDepthEstimator:
    @staticmethod
    def run_demo():
        print("生成合成光场数据...")
        lf = LightField.generate_synthetic(
            num_rows=5, num_cols=5,
            height=150, width=150,
            num_depths=3)
        
        print("启动交互界面...")
        gui = LightFieldDepthGUI(lf)
        gui.run()
