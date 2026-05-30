import sys
import os
import numpy as np
import cv2
import matplotlib
try:
    matplotlib.use("TkAgg")
except Exception:
    matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.widgets import Button, RadioButtons, Slider, CheckButtons
from matplotlib.gridspec import GridSpec

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fusion import (WaveletFusion, DLFusion, DynamicAligner, FusionQualityAssessor,
                     MultimodalFusion, VideoFusion, TemporalSmoother, WeightController)

DL_AVAILABLE = DLFusion is not None


class MultiFocusFusionApp:
    def __init__(self, image_paths=None):
        self.images = []
        self.aligned_images = []
        self.fused_result = None
        self.weight_map = None
        self.flow_vis = None
        self.motion_mask = None
        self.reliable_masks = None
        self.motion_masks = None
        self.flows = None
        self.metrics_results = None
        self.image_id = "fused_result"
        self.mos_weight = 0.4
        self.obj_weight = 0.6

        self.fusion_method = "wavelet"
        self.wavelet_name = "db2"
        self.wavelet_level = "auto"
        self.fusion_rule = "max"
        self.align_enabled = True
        self.align_method = "farneback"
        self.motion_aware_enabled = True
        self.show_metrics = True
        self.show_weight_map = True

        self.multimodal_method = "intensity_weighted"
        self.ir_weight = 0.5
        self.vis_weight = 0.5

        self.custom_weights = None
        self.weight_controller = None
        self.blend_mode = "weighted_average"

        self.temporal_mode = "iir"
        self.temporal_alpha = 0.3

        self.wavelet_fusion = WaveletFusion(wavelet=self.wavelet_name, level=self.wavelet_level, fusion_rule=self.fusion_rule)
        self.dl_fusion = DLFusion() if DL_AVAILABLE else None
        self.multimodal_fusion = MultimodalFusion(method=self.multimodal_method)
        self.aligner = DynamicAligner(method=self.align_method)
        self.assessor = FusionQualityAssessor()

        if image_paths:
            self.load_images(image_paths)

    def load_images(self, paths):
        self.images = []
        for p in paths:
            img = cv2.imread(p)
            if img is None:
                print(f"Warning: Cannot load {p}")
                continue
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            self.images.append(img)
        if len(self.images) < 2:
            print("Error: Need at least 2 images")
            return False
        h, w = self.images[0].shape[:2]
        self.images = [cv2.resize(img, (w, h)) for img in self.images]
        self.aligned_images = []
        self.fused_result = None
        n = len(self.images)
        self.custom_weights = [1.0 / n] * n
        self.weight_controller = WeightController(num_images=n)
        print(f"Loaded {len(self.images)} images ({w}x{h})")
        return True

    def load_from_directory(self, dir_path):
        exts = (".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff")
        files = sorted([os.path.join(dir_path, f) for f in os.listdir(dir_path)
                        if f.lower().endswith(exts)])
        if not files:
            print(f"No images found in {dir_path}")
            return False
        return self.load_images(files)

    def _do_align(self):
        if not self.align_enabled or len(self.images) < 2:
            self.aligned_images = [img.copy() for img in self.images]
            self.motion_masks = [None] * len(self.images)
            self.reliable_masks = [None] * len(self.images)
            self.flows = [None] * len(self.images)
            return
        images_bgr = [cv2.cvtColor(img, cv2.COLOR_RGB2BGR) for img in self.images]
        self.aligner.method = self.align_method
        if self.motion_aware_enabled:
            aligned_bgr, self.motion_masks, self.reliable_masks, self.flows = self.aligner.align_with_motion_aware(images_bgr, ref_idx=0)
        else:
            aligned_bgr = self.aligner.align(images_bgr, ref_idx=0)
            self.motion_masks = [None] * len(self.images)
            self.reliable_masks = [None] * len(self.images)
            self.flows = [None] * len(self.images)
        self.aligned_images = [cv2.cvtColor(img, cv2.COLOR_BGR2RGB) for img in aligned_bgr]
        if len(self.images) >= 2:
            if self.flows[1] is not None:
                self.flow_vis = cv2.cvtColor(self.aligner.visualize_flow(self.flows[1]), cv2.COLOR_BGR2RGB)
            else:
                flow = self.aligner._compute_optical_flow(images_bgr[0], images_bgr[1])
                self.flow_vis = cv2.cvtColor(self.aligner.visualize_flow(flow), cv2.COLOR_BGR2RGB)
            if self.motion_masks[1] is not None:
                self.motion_mask = self.motion_masks[1]
            else:
                self.motion_mask = self.aligner.detect_motion_mask(images_bgr[0], images_bgr[1])
        print("Alignment complete")

    def _do_fuse(self):
        sources = self.aligned_images if self.aligned_images else self.images
        if not sources:
            return
        if self.fusion_method == "wavelet":
            self.wavelet_fusion = WaveletFusion(
                wavelet=self.wavelet_name, level=self.wavelet_level, fusion_rule=self.fusion_rule
            )
            sources_bgr = [cv2.cvtColor(img, cv2.COLOR_RGB2BGR) for img in sources]
            masks_for_fusion = None
            if self.motion_aware_enabled and self.reliable_masks is not None:
                masks_for_fusion = [rm for rm in self.reliable_masks]
            result_bgr = self.wavelet_fusion.fuse(sources_bgr, masks_for_fusion)
            self.fused_result = cv2.cvtColor(result_bgr, cv2.COLOR_BGR2RGB)
            self.weight_map = None
            if self.wavelet_fusion._level == "auto":
                print(f"Auto wavelet level: {self.wavelet_fusion.level}")
        elif self.fusion_method == "deep_learning":
            if not DL_AVAILABLE or self.dl_fusion is None:
                print("Deep learning fusion unavailable (PyTorch not installed). Falling back to wavelet.")
                self.fusion_method = "wavelet"
                self._do_fuse()
                return
            sources_bgr = [cv2.cvtColor(img, cv2.COLOR_RGB2BGR) for img in sources]
            if len(sources_bgr) == 2:
                result_bgr, wmap = self.dl_fusion.fuse_pair(sources_bgr[0], sources_bgr[1])
                self.weight_map = cv2.cvtColor(wmap, cv2.COLOR_BGR2RGB)
            else:
                result_bgr = self.dl_fusion.fuse(sources_bgr)
                self.weight_map = None
            self.fused_result = cv2.cvtColor(result_bgr, cv2.COLOR_BGR2RGB)
        elif self.fusion_method == "multimodal":
            sources_bgr = [cv2.cvtColor(img, cv2.COLOR_RGB2BGR) for img in sources]
            self.multimodal_fusion.method = self.multimodal_method
            if self.multimodal_method == "intensity_weighted":
                result_bgr = self.multimodal_fusion.fuse(
                    sources_bgr[0], sources_bgr[1],
                    ir_weight=self.ir_weight, vis_weight=self.vis_weight
                )
            elif self.multimodal_method in ("wavelet", "laplacian_pyramid"):
                result_bgr = self.multimodal_fusion.fuse(sources_bgr[0], sources_bgr[1])
            else:
                result_bgr = self.multimodal_fusion.fuse(sources_bgr[0], sources_bgr[1])
            self.fused_result = cv2.cvtColor(result_bgr, cv2.COLOR_BGR2RGB)
            self.weight_map = None
        elif self.fusion_method == "custom_weight":
            sources_bgr = [cv2.cvtColor(img, cv2.COLOR_RGB2BGR) for img in sources]
            self.weight_controller.set_weights(self.custom_weights)
            self.weight_controller.blend_mode = self.blend_mode
            result_bgr = self.weight_controller.fuse(sources_bgr)
            self.fused_result = cv2.cvtColor(result_bgr, cv2.COLOR_BGR2RGB)
            self.weight_map = None
        print(f"Fusion complete ({self.fusion_method})")

    def _do_evaluate(self):
        sources = self.aligned_images if self.aligned_images else self.images
        if self.fused_result is None or not sources:
            return
        sources_bgr = [cv2.cvtColor(img, cv2.COLOR_RGB2BGR) for img in sources]
        fused_bgr = cv2.cvtColor(self.fused_result, cv2.COLOR_RGB2BGR)
        self.metrics_results = self.assessor.evaluate(
            fused_bgr, sources_bgr, image_id=self.image_id,
            mos_weight=self.mos_weight, obj_weight=self.obj_weight
        )
        print(self.assessor.format_results(self.metrics_results))

    def run_pipeline(self):
        self._do_align()
        self._do_fuse()
        self._do_evaluate()

    def run_gui(self):
        if not self.images:
            print("No images loaded.")
            return
        self.run_pipeline()
        fig = plt.figure(figsize=(22, 12), facecolor="#1a1a2e")
        fig.canvas.manager.set_window_title("Multi-Focus Image Fusion v3")
        gs = GridSpec(3, 4, figure=fig, hspace=0.38, wspace=0.25,
                      left=0.03, right=0.68, top=0.94, bottom=0.10)

        n_images = len(self.images)
        for i in range(min(n_images, 4)):
            ax = fig.add_subplot(gs[0, i])
            ax.imshow(self.images[i])
            ax.set_title(f"Source {i + 1}", color="white", fontsize=10)
            ax.axis("off")

        ax_aligned = fig.add_subplot(gs[1, 0])
        if self.aligned_images and len(self.aligned_images) > 1:
            ax_aligned.imshow(self.aligned_images[1])
            ax_aligned.set_title("Aligned (Img 2)", color="white", fontsize=9)
        else:
            ax_aligned.imshow(self.images[0])
            ax_aligned.set_title("No alignment", color="white", fontsize=9)
        ax_aligned.axis("off")

        ax_flow = fig.add_subplot(gs[1, 1])
        if self.flow_vis is not None:
            ax_flow.imshow(self.flow_vis)
        else:
            ax_flow.text(0.5, 0.5, "No Flow", ha="center", va="center", color="white")
        ax_flow.set_title("Optical Flow", color="white", fontsize=9)
        ax_flow.axis("off")

        ax_motion = fig.add_subplot(gs[1, 2])
        if self.motion_mask is not None:
            ax_motion.imshow(self.motion_mask, cmap="hot")
        else:
            ax_motion.text(0.5, 0.5, "No Mask", ha="center", va="center", color="white")
        ax_motion.set_title("Motion Mask", color="white", fontsize=9)
        ax_motion.axis("off")

        ax_reliable = fig.add_subplot(gs[1, 3])
        if self.reliable_masks is not None and len(self.reliable_masks) > 1 and self.reliable_masks[1] is not None:
            ax_reliable.imshow(self.reliable_masks[1], cmap="viridis", vmin=0, vmax=1)
        else:
            ax_reliable.text(0.5, 0.5, "N/A", ha="center", va="center", color="white")
        ax_reliable.set_title("Reliable Mask", color="white", fontsize=9)
        ax_reliable.axis("off")

        ax_fused = fig.add_subplot(gs[2, 0:2])
        if self.fused_result is not None:
            ax_fused.imshow(self.fused_result)
            level_text = ""
            if self.fusion_method == "wavelet" and self.wavelet_fusion._level == "auto":
                level_text = f"  [Auto={self.wavelet_fusion.level}]"
            ax_fused.set_title("Fused" + level_text, color="lime", fontsize=12, fontweight="bold")
        else:
            ax_fused.text(0.5, 0.5, "No Result", ha="center", va="center", color="white", fontsize=16)
        ax_fused.axis("off")

        ax_metrics = fig.add_subplot(gs[2, 2:4])
        ax_metrics.set_facecolor("#1a1a2e")
        if self.metrics_results:
            core_keys = ["NMI_avg", "Q_AB_avg", "FMI_avg", "Predicted_MOS", "Objective_Score"]
            if "Combined_Score" in self.metrics_results:
                core_keys += ["MOS", "Combined_Score"]
            display_keys = [k for k in core_keys if k in self.metrics_results]
            values = [self.metrics_results[k] for k in display_keys]
            colors = plt.cm.viridis(np.linspace(0.2, 0.8, len(values)))
            bars = ax_metrics.barh(range(len(display_keys)), values, color=colors)
            ax_metrics.set_yticks(range(len(display_keys)))
            ax_metrics.set_yticklabels(display_keys, fontsize=8, color="white")
            ax_metrics.set_title("Quality Metrics", color="white", fontsize=10)
            ax_metrics.tick_params(axis="x", colors="white", labelsize=7)
            for bar, val in zip(bars, values):
                ax_metrics.text(bar.get_width() + 0.01, bar.get_y() + bar.get_height() / 2,
                                f"{val:.3f}", va="center", color="white", fontsize=7)
            for spine in ax_metrics.spines.values():
                spine.set_color("#444")
        else:
            ax_metrics.text(0.5, 0.5, "No Metrics", ha="center", va="center", color="white")
        ax_metrics.axis("on")

        x0 = 0.70
        w0 = 0.14
        w1 = 0.27

        all_methods = ["wavelet", "multimodal", "custom_weight"]
        if DL_AVAILABLE:
            all_methods.insert(1, "deep_learning")
        ax_radio_method = fig.add_axes([x0, 0.86, w1, 0.12], facecolor="#2a2a4a")
        radio_method = RadioButtons(ax_radio_method, tuple(all_methods), active=0)
        for label in radio_method.labels:
            label.set_color("white")
            label.set_fontsize(8.5)
        ax_radio_method.set_title("Fusion Method", color="white", fontsize=9)

        ax_radio_rule = fig.add_axes([x0, 0.72, w1, 0.12], facecolor="#2a2a4a")
        radio_rule = RadioButtons(ax_radio_rule, ("max", "mean", "energy", "weighted"), active=0)
        for label in radio_rule.labels:
            label.set_color("white")
            label.set_fontsize(8.5)
        ax_radio_rule.set_title("Wavelet Rule", color="white", fontsize=9)

        ax_radio_mm = fig.add_axes([x0, 0.58, w1, 0.12], facecolor="#2a2a4a")
        mm_methods = ("intensity_wt", "gradient", "wavelet", "laplacian", "salience")
        radio_mm = RadioButtons(ax_radio_mm, mm_methods, active=0)
        for label in radio_mm.labels:
            label.set_color("white")
            label.set_fontsize(8)
        ax_radio_mm.set_title("Multimodal Method", color="white", fontsize=9)

        ax_radio_level = fig.add_axes([x0, 0.44, w1, 0.12], facecolor="#2a2a4a")
        radio_level = RadioButtons(ax_radio_level, ("auto", "1", "2", "3", "4", "5"), active=0)
        for label in radio_level.labels:
            label.set_color("white")
            label.set_fontsize(8)
        ax_radio_level.set_title("Wavelet Level", color="white", fontsize=9)

        ax_check = fig.add_axes([x0 + 0.005, 0.37, w1 - 0.01, 0.06], facecolor="#2a2a4a")
        check = CheckButtons(ax_check, ["Align", "Motion-aware"], [self.align_enabled, self.motion_aware_enabled])
        for label in check.labels:
            label.set_color("white")
            label.set_fontsize(7.5)

        ax_sl_w1 = fig.add_axes([x0 + 0.01, 0.32, w1 - 0.02, 0.025], facecolor="#2a2a4a")
        sl_w1 = Slider(ax_sl_w1, "W1", 0, 1, valinit=self.custom_weights[0] if self.custom_weights else 0.5, valstep=0.05)
        sl_w1.label.set_color("white")
        sl_w1.label.set_fontsize(7)
        sl_w1.valtext.set_color("white")
        sl_w1.valtext.set_fontsize(7)

        n_sliders = min(n_images, 4)
        weight_sliders = []
        for i in range(1, n_sliders):
            ax_sl = fig.add_axes([x0 + 0.01, 0.32 - i * 0.028, w1 - 0.02, 0.025], facecolor="#2a2a4a")
            init_v = self.custom_weights[i] if self.custom_weights and i < len(self.custom_weights) else 0.5
            sl = Slider(ax_sl, f"W{i + 1}", 0, 1, valinit=init_v, valstep=0.05)
            sl.label.set_color("white")
            sl.label.set_fontsize(7)
            sl.valtext.set_color("white")
            sl.valtext.set_fontsize(7)
            weight_sliders.append(sl)

        ax_sl_ir = fig.add_axes([x0 + 0.01, 0.32 - n_sliders * 0.028, w1 - 0.02, 0.025], facecolor="#2a2a4a")
        sl_ir = Slider(ax_sl_ir, "IR wt", 0, 1, valinit=self.ir_weight, valstep=0.05)
        sl_ir.label.set_color("white")
        sl_ir.label.set_fontsize(7)
        sl_ir.valtext.set_color("white")
        sl_ir.valtext.set_fontsize(7)

        ax_sl_tmp = fig.add_axes([x0 + 0.01, 0.32 - (n_sliders + 1) * 0.028, w1 - 0.02, 0.025], facecolor="#2a2a4a")
        sl_tmp = Slider(ax_sl_tmp, "Temporal", 0, 1, valinit=self.temporal_alpha, valstep=0.05)
        sl_tmp.label.set_color("white")
        sl_tmp.label.set_fontsize(7)
        sl_tmp.valtext.set_color("white")
        sl_tmp.valtext.set_fontsize(7)

        btn_y = 0.02
        btn_h = 0.045
        ax_btn_run = fig.add_axes([x0, btn_y + 5 * btn_h + 5 * 0.005, w0, btn_h])
        btn_run = Button(ax_btn_run, "Run Fusion", color="#4a90d9", hovercolor="#6ab0f9")
        btn_run.label.set_fontsize(8)

        ax_btn_wt = fig.add_axes([x0 + w0 + 0.01, btn_y + 5 * btn_h + 5 * 0.005, w0, btn_h])
        btn_wt = Button(ax_btn_wt, "Apply Wt", color="#a040d0", hovercolor="#c060f0")
        btn_wt.label.set_fontsize(8)

        ax_btn_mos = fig.add_axes([x0, btn_y + 4 * btn_h + 4 * 0.005, w0, btn_h])
        btn_mos = Button(ax_btn_mos, "Rate MOS", color="#d04060", hovercolor="#f06080")
        btn_mos.label.set_fontsize(8)

        ax_btn_save = fig.add_axes([x0 + w0 + 0.01, btn_y + 4 * btn_h + 4 * 0.005, w0, btn_h])
        btn_save = Button(ax_btn_save, "Save", color="#5cb85c", hovercolor="#7dd87d")
        btn_save.label.set_fontsize(8)

        ax_btn_met = fig.add_axes([x0, btn_y + 3 * btn_h + 3 * 0.005, w0, btn_h])
        btn_met = Button(ax_btn_met, "Metrics", color="#d9534f", hovercolor="#f97371")
        btn_met.label.set_fontsize(8)

        ax_btn_vid = fig.add_axes([x0 + w0 + 0.01, btn_y + 3 * btn_h + 3 * 0.005, w0, btn_h])
        btn_vid = Button(ax_btn_vid, "Video Fuse", color="#40a0a0", hovercolor="#60c0c0")
        btn_vid.label.set_fontsize(8)

        ax_btn_cls = fig.add_axes([x0, btn_y + 2 * btn_h + 2 * 0.005, w1, btn_h])
        btn_cls = Button(ax_btn_cls, "Close", color="#666666", hovercolor="#888888")
        btn_cls.label.set_fontsize(8)

        mm_method_map = {
            "intensity_wt": "intensity_weighted", "gradient": "gradient_guided",
            "wavelet": "wavelet", "laplacian": "laplacian_pyramid", "salience": "salience_weighted",
        }

        def on_method(label):
            self.fusion_method = label

        def on_rule(label):
            self.fusion_rule = label

        def on_mm(label):
            self.multimodal_method = mm_method_map.get(label, label)

        def on_level(label):
            self.wavelet_level = "auto" if label == "auto" else int(label)

        def on_check(label):
            if label == "Align":
                self.align_enabled = not self.align_enabled
            elif label == "Motion-aware":
                self.motion_aware_enabled = not self.motion_aware_enabled

        def on_w1(val):
            if self.custom_weights:
                self.custom_weights[0] = val

        def on_weight_slider(i):
            def handler(val):
                if self.custom_weights and i < len(self.custom_weights):
                    self.custom_weights[i] = val
            return handler

        def on_ir(val):
            self.ir_weight = val
            self.vis_weight = 1.0 - val

        def on_temporal(val):
            self.temporal_alpha = val

        def on_run(event):
            self.run_pipeline()
            plt.close(fig)
            self.run_gui()

        def on_apply_wt(event):
            self.fusion_method = "custom_weight"
            total = sum(self.custom_weights[:n_images])
            if total > 0:
                self.custom_weights = [w / total for w in self.custom_weights[:n_images]]
            self._do_fuse()
            plt.close(fig)
            self.run_gui()

        def on_save(event):
            if self.fused_result is not None:
                cv2.imwrite("fused_result.png", cv2.cvtColor(self.fused_result, cv2.COLOR_RGB2BGR))
                print("Saved: fused_result.png")

        def on_metrics(event):
            if self.metrics_results:
                print(self.assessor.format_results(self.metrics_results))

        def on_mos(event):
            self._show_mos_dialog()

        def on_video(event):
            self._show_video_dialog()

        def on_close(event):
            plt.close(fig)

        radio_method.on_clicked(on_method)
        radio_rule.on_clicked(on_rule)
        radio_mm.on_clicked(on_mm)
        radio_level.on_clicked(on_level)
        check.on_clicked(on_check)
        sl_w1.on_changed(on_w1)
        for i, sl in enumerate(weight_sliders):
            sl.on_changed(on_weight_slider(i + 1))
        sl_ir.on_changed(on_ir)
        sl_tmp.on_changed(on_temporal)
        btn_run.on_clicked(on_run)
        btn_wt.on_clicked(on_apply_wt)
        btn_mos.on_clicked(on_mos)
        btn_save.on_clicked(on_save)
        btn_met.on_clicked(on_metrics)
        btn_vid.on_clicked(on_video)
        btn_cls.on_clicked(on_close)

        fig.suptitle("Multi-Focus Image Fusion System v3", color="white", fontsize=14, fontweight="bold")
        plt.show()

    def _show_mos_dialog(self):
        if self.fused_result is None:
            print("No fused result to rate.")
            return
        fig = plt.figure(figsize=(7, 5), facecolor="#1a1a2e")
        fig.canvas.manager.set_window_title("MOS Rating")
        ax_img = fig.add_subplot(111)
        ax_img.imshow(self.fused_result)
        ax_img.set_title("Rate this fused image (1-5 scale)", color="white", fontsize=12)
        ax_img.axis("off")
        ax_slider = plt.axes([0.2, 0.15, 0.6, 0.06], facecolor="#2a2a4a")
        slider = Slider(ax_slider, "MOS", 1, 5, valinit=3, valstep=0.5)
        slider.label.set_color("white")
        slider.valtext.set_color("white")
        ax_btn = plt.axes([0.4, 0.05, 0.2, 0.06])
        btn = Button(ax_btn, "Submit", color="#5cb85c")
        btn.label.set_color("white")
        def on_submit(event):
            self.assessor.collect_mos(self.image_id, slider.val, observer_id="user")
            print(f"MOS score {slider.val}/5.0 recorded.")
            if self.metrics_results is not None:
                self.assessor.compute_combined_score(self.image_id, self.metrics_results,
                                                     self.mos_weight, self.obj_weight)
            plt.close(fig)
        btn.on_clicked(on_submit)
        plt.subplots_adjust(bottom=0.3)
        plt.show()

    def _show_video_dialog(self):
        fig = plt.figure(figsize=(6, 5), facecolor="#1a1a2e")
        fig.canvas.manager.set_window_title("Video Fusion")

        ax_info = fig.add_axes([0.1, 0.75, 0.8, 0.2], facecolor="#2a2a4a")
        ax_info.text(0.5, 0.5, "Video Fusion Mode\n\nFuse two video files frame-by-frame\nwith temporal consistency",
                     ha="center", va="center", color="white", fontsize=9, transform=ax_info.transAxes)
        ax_info.axis("off")

        ax_sl_alpha = fig.add_axes([0.2, 0.55, 0.6, 0.05], facecolor="#2a2a4a")
        sl_alpha = Slider(ax_sl_alpha, "Temporal α", 0.05, 0.95, valinit=self.temporal_alpha, valstep=0.05)
        sl_alpha.label.set_color("white")
        sl_alpha.valtext.set_color("white")

        ax_radio_tmp = fig.add_axes([0.15, 0.25, 0.7, 0.25], facecolor="#2a2a4a")
        radio_tmp = RadioButtons(ax_radio_tmp, ("iir", "moving_average", "flow_warp"), active=0)
        for label in radio_tmp.labels:
            label.set_color("white")
            label.set_fontsize(9)
        ax_radio_tmp.set_title("Temporal Consistency", color="white", fontsize=10)

        ax_btn = fig.add_axes([0.3, 0.08, 0.4, 0.08])
        btn = Button(ax_btn, "Start Video Fusion", color="#40a0a0", hovercolor="#60c0c0")
        btn.label.set_fontsize(10)

        selected_mode = [self.temporal_mode]

        def on_tmp(label):
            selected_mode[0] = label

        def on_start(event):
            print(f"\nVideo Fusion: temporal_mode={selected_mode[0]}, alpha={sl_alpha.val}")
            print("Usage: python main.py --video1 <path> --video2 <path> --temporal-mode <mode>")
            print("Example: python main.py --video1 ir.avi --video2 vis.avi --temporal-mode flow_warp --output fused.mp4")
            plt.close(fig)

        radio_tmp.on_clicked(on_tmp)
        btn.on_clicked(on_start)
        plt.show()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Multi-Focus Image Fusion")
    parser.add_argument("images", nargs="*", help="Input image paths")
    parser.add_argument("--dir", type=str, help="Directory containing input images")
    parser.add_argument("--method", choices=["wavelet", "deep_learning", "multimodal", "custom_weight"], default="wavelet")
    parser.add_argument("--wavelet", type=str, default="db2")
    parser.add_argument("--level", type=str, default="auto", help="Wavelet level (1-5 or 'auto')")
    parser.add_argument("--rule", choices=["max", "mean", "energy", "weighted"], default="max")
    parser.add_argument("--multimodal-method", choices=MultimodalFusion.get_available_methods(), default="intensity_weighted")
    parser.add_argument("--ir-weight", type=float, default=0.5, help="IR image weight for multimodal fusion")
    parser.add_argument("--weights", type=str, default=None, help="Custom weights e.g. '0.6,0.4'")
    parser.add_argument("--blend-mode", choices=WeightController.get_available_blend_modes(), default="weighted_average")
    parser.add_argument("--no-align", action="store_true")
    parser.add_argument("--no-motion-aware", action="store_true")
    parser.add_argument("--mos-score", type=float, default=None)
    parser.add_argument("--mos-weight", type=float, default=0.4)
    parser.add_argument("--obj-weight", type=float, default=0.6)
    parser.add_argument("--no-gui", action="store_true")
    parser.add_argument("--output", type=str, default="fused_result.png")
    parser.add_argument("--video1", type=str, help="First video file for video fusion")
    parser.add_argument("--video2", type=str, help="Second video file for video fusion")
    parser.add_argument("--temporal-mode", choices=VideoFusion.get_available_temporal_modes(), default="iir")
    parser.add_argument("--temporal-alpha", type=float, default=0.3)
    args = parser.parse_args()

    if args.video1 and args.video2:
        print(f"Video fusion: {args.video1} + {args.video2}")
        wf = WaveletFusion(wavelet=args.wavelet, level="auto" if args.level == "auto" else int(args.level), fusion_rule=args.rule)
        vf = VideoFusion(fusion_engine=wf, temporal_mode=args.temporal_mode, temporal_alpha=args.temporal_alpha)
        out = args.output if args.output.endswith(".mp4") else args.output.rsplit(".", 1)[0] + ".mp4"
        vf.process_video([args.video1, args.video2], out, show_progress=True)
        return

    app = MultiFocusFusionApp()
    app.fusion_method = args.method
    app.wavelet_name = args.wavelet
    if args.level.lower() == "auto":
        app.wavelet_level = "auto"
    else:
        try:
            app.wavelet_level = int(args.level)
        except ValueError:
            app.wavelet_level = "auto"
    app.fusion_rule = args.rule
    app.multimodal_method = args.multimodal_method
    app.ir_weight = args.ir_weight
    app.vis_weight = 1.0 - args.ir_weight
    app.blend_mode = args.blend_mode
    app.align_enabled = not args.no_align
    app.motion_aware_enabled = not args.no_motion_aware
    app.mos_weight = args.mos_weight
    app.obj_weight = args.obj_weight
    app.temporal_mode = args.temporal_mode
    app.temporal_alpha = args.temporal_alpha

    if args.weights:
        try:
            w = [float(x) for x in args.weights.split(",")]
            app.custom_weights = w
        except Exception:
            print(f"Warning: Invalid weights '{args.weights}'")

    if args.dir:
        app.load_from_directory(args.dir)
    elif args.images:
        app.load_images(args.images)
    else:
        print("No images specified. Generating test data...")
        script_dir = os.path.dirname(os.path.abspath(__file__))
        test_dir = os.path.join(script_dir, "test_data")
        os.makedirs(test_dir, exist_ok=True)
        gen_script = os.path.join(script_dir, "generate_test_data.py")
        if os.path.exists(gen_script):
            import subprocess
            subprocess.run([sys.executable, gen_script, "--output", test_dir], check=True)
        else:
            _generate_simple_test_data(test_dir)
        app.load_from_directory(test_dir)

    if not app.images:
        return

    if args.mos_score is not None and 1 <= args.mos_score <= 5:
        app.assessor.collect_mos(app.image_id, args.mos_score, observer_id="cli")
        print(f"MOS score {args.mos_score} recorded.")

    if args.no_gui:
        app.run_pipeline()
        if app.fused_result is not None:
            cv2.imwrite(args.output, cv2.cvtColor(app.fused_result, cv2.COLOR_RGB2BGR))
            print(f"Saved: {args.output}")
        if app.metrics_results:
            print(app.assessor.format_results(app.metrics_results))
    else:
        app.run_gui()


def _generate_simple_test_data(output_dir):
    h, w = 256, 256
    bg = np.ones((h, w, 3), dtype=np.uint8) * 200
    for c in range(3):
        bg[20:80, 20:80, c] = 50
        bg[20:80, 170:230, c] = 50
        bg[170:230, 20:80, c] = 50
        bg[170:230, 170:230, c] = 50
    img1 = bg.copy()
    for y in range(90, 160):
        for x in range(90, 160):
            dx, dy = x - 125, y - 125
            if dx * dx + dy * dy < 35 * 35:
                img1[y, x] = [220, 50, 50]
    img2 = bg.copy()
    for y in range(40, 110):
        for x in range(40, 110):
            img2[y, x] = [50, 50, 220]
    cv2.imwrite(os.path.join(output_dir, "focus_near.png"), cv2.cvtColor(img1, cv2.COLOR_RGB2BGR))
    cv2.imwrite(os.path.join(output_dir, "focus_far.png"), cv2.cvtColor(img2, cv2.COLOR_RGB2BGR))
    print(f"Generated test images in {output_dir}")


if __name__ == "__main__":
    main()
