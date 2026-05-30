import sys
import numpy as np
import cv2
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button, RadioButtons, CheckButtons, TextBox
from matplotlib.gridspec import GridSpec
from superpixel_core import SuperpixelSegmenter, COMPACTNESS_PRESETS, SuperpixelClassifier
from superpixel_video import VideoSuperpixel, SuperpixelTracker


class SuperpixelApp:

    def __init__(self, initial_path=None):
        self.mode = "image"
        self.image = self._create_demo_image()
        self.segmenter = SuperpixelSegmenter(self.image)
        self.current_segments = None
        self.vis_mode = "boundaries"
        self.show_edge_map = False

        self.video_processor = None
        self.video_frame_idx = 0
        self.video_playing = False
        self.video_timer = None
        self.show_tracks = False
        self.show_classification = False

        self.class_label_input = 0
        self.class_name_input = "object"
        self.selected_seg_id = None

        if initial_path:
            self._try_load_path(initial_path)

        self._build_gui()

    def _create_demo_image(self):
        h, w = 300, 400
        img = np.zeros((h, w, 3), dtype=np.uint8)
        img[: h // 2, : w // 2] = [220, 80, 60]
        img[: h // 2, w // 2 :] = [60, 180, 75]
        img[h // 2 :, : w // 2] = [60, 100, 220]
        img[h // 2 :, w // 2 :] = [220, 200, 60]
        for cx, cy, r, c in [
            (100, 75, 40, [255, 255, 255]),
            (300, 75, 40, [255, 200, 150]),
            (100, 225, 40, [150, 200, 255]),
            (300, 225, 40, [200, 150, 255]),
        ]:
            yy, xx = np.ogrid[:h, :w]
            mask = (xx - cx) ** 2 + (yy - cy) ** 2 <= r ** 2
            img[mask] = c
        for i in range(0, w, 30):
            img[:, i : i + 2] = (img[:, i : i + 2].astype(int) * 0.7).astype(np.uint8)
        noise = np.random.randint(0, 15, img.shape, dtype=np.uint8)
        img = cv2.add(img, noise)
        return img

    def _try_load_path(self, path):
        ext = path.lower().split(".")[-1] if "." in path else ""
        video_exts = {"mp4", "avi", "mov", "mkv", "webm", "flv", "wmv", "m4v"}
        image_exts = {"png", "jpg", "jpeg", "bmp", "tiff", "tif", "webp"}
        if ext in video_exts:
            self._load_video(path)
        elif ext in image_exts:
            self._load_image(path)

    def _build_gui(self):
        self.fig = plt.figure(figsize=(18, 12), facecolor="#f0f0f0")
        self.fig.canvas.manager.set_window_title("Superpixel Segmentation Tool v3")

        gs = GridSpec(16, 8, figure=self.fig, hspace=1.2, wspace=0.4,
                      left=0.04, right=0.72, top=0.96, bottom=0.03)

        self.ax_original = self.fig.add_subplot(gs[0:4, 0:4])
        self.ax_result = self.fig.add_subplot(gs[0:4, 4:8])
        self.ax_info = self.fig.add_subplot(gs[4:6, 0:8])
        self.ax_info.axis("off")

        self.ax_original.set_title("Original Image", fontsize=12, fontweight="bold")
        self.ax_result.set_title("Segmentation Result", fontsize=12, fontweight="bold")
        self.ax_original.imshow(self.image)
        self.ax_result.imshow(self.image)
        for ax in [self.ax_original, self.ax_result]:
            ax.set_xticks([])
            ax.set_yticks([])

        self.fig.canvas.mpl_connect("button_press_event", self._on_canvas_click)

        ctrl_left = 0.75
        ctrl_width = 0.22
        y = 0.96

        ax_mode = self.fig.add_axes([ctrl_left, y - 0.06, ctrl_width, 0.05],
                                    facecolor="#e8e8e8")
        ax_mode.set_title("Mode", fontsize=10, fontweight="bold", pad=2)
        self.radio_mode = RadioButtons(ax_mode, ("Image", "Video"), active=0)
        self.radio_mode.on_clicked(self._on_mode_change)
        y -= 0.08

        ax_algo = self.fig.add_axes([ctrl_left, y - 0.07, ctrl_width, 0.06],
                                    facecolor="#e8e8e8")
        ax_algo.set_title("Algorithm", fontsize=10, fontweight="bold", pad=2)
        self.radio_algo = RadioButtons(ax_algo, ("SLIC", "Felzenszwalb"), active=0)
        self.radio_algo.on_clicked(self._on_algo_change)
        y -= 0.09

        ax_compact = self.fig.add_axes([ctrl_left, y - 0.08, ctrl_width, 0.07],
                                       facecolor="#e8e8e8")
        ax_compact.set_title("Compactness Preset", fontsize=9, fontweight="bold", pad=2)
        self.radio_compact = RadioButtons(
            ax_compact, ("Auto", "Flat", "Balanced", "Texture", "Custom"), active=0
        )
        self.radio_compact.on_clicked(self._on_compact_change)
        y -= 0.10

        ax_slic_n = self.fig.add_axes([ctrl_left, y - 0.025, ctrl_width, 0.025])
        self.slider_slic_n = Slider(ax_slic_n, "Segments", 10, 500,
                                    valinit=100, valstep=10, color="#4CAF50")
        y -= 0.045

        ax_slic_c = self.fig.add_axes([ctrl_left, y - 0.025, ctrl_width, 0.025])
        self.slider_slic_c = Slider(ax_slic_c, "Custom Compact", 1, 50,
                                    valinit=10, valstep=1, color="#4CAF50")
        self.slider_slic_c.ax.set_visible(False)
        y -= 0.045

        ax_slic_s = self.fig.add_axes([ctrl_left, y - 0.025, ctrl_width, 0.025])
        self.slider_slic_s = Slider(ax_slic_s, "Sigma", 0.1, 5.0,
                                    valinit=1.0, valstep=0.1, color="#4CAF50")
        y -= 0.045

        self.slic_sliders = [
            self.slider_slic_n, self.slider_slic_c, self.slider_slic_s
        ]

        ax_fz_scale = self.fig.add_axes([ctrl_left, 0.82 - 0.025, ctrl_width, 0.025])
        self.slider_fz_scale = Slider(ax_fz_scale, "Scale", 10, 500,
                                      valinit=100, valstep=10, color="#2196F3")
        ax_fz_sigma = self.fig.add_axes([ctrl_left, 0.775 - 0.025, ctrl_width, 0.025])
        self.slider_fz_sigma = Slider(ax_fz_sigma, "Sigma", 0.1, 5.0,
                                      valinit=0.5, valstep=0.1, color="#2196F3")
        ax_fz_minsize = self.fig.add_axes([ctrl_left, 0.73 - 0.025, ctrl_width, 0.025])
        self.slider_fz_minsize = Slider(ax_fz_minsize, "Min Size", 10, 500,
                                        valinit=50, valstep=10, color="#2196F3")
        self.fz_sliders = [
            self.slider_fz_scale, self.slider_fz_sigma, self.slider_fz_minsize
        ]
        for sl in self.fz_sliders:
            sl.ax.set_visible(False)

        ax_temporal = self.fig.add_axes([ctrl_left, y - 0.025, ctrl_width, 0.025])
        self.slider_temporal = Slider(ax_temporal, "Temporal Weight", 0.0, 1.0,
                                      valinit=0.5, valstep=0.05, color="#607D8B")
        ax_temporal.set_visible(False)
        self.ax_temporal_title = ax_temporal
        y -= 0.045

        ax_edge_check = self.fig.add_axes([ctrl_left, y - 0.035, ctrl_width, 0.035],
                                          facecolor="#e8e8e8")
        self.check_edge = CheckButtons(ax_edge_check, ("Edge-Guided Segmentation",),
                                       actives=(False,))
        self.check_edge.on_clicked(self._on_edge_toggle)
        y -= 0.055

        ax_edge_method = self.fig.add_axes([ctrl_left, y - 0.055, ctrl_width, 0.05],
                                           facecolor="#e8e8e8")
        ax_edge_method.set_title("Edge Detector", fontsize=8, fontweight="bold", pad=1)
        self.radio_edge_method = RadioButtons(
            ax_edge_method, ("Canny", "Sobel", "Laplacian"), active=0
        )
        self.radio_edge_method.ax.set_visible(False)
        y -= 0.075

        ax_edge_low = self.fig.add_axes([ctrl_left, y - 0.025, ctrl_width, 0.025])
        self.slider_edge_low = Slider(ax_edge_low, "Edge Low", 10, 100,
                                      valinit=50, valstep=5, color="#9C27B0")
        ax_edge_low.set_visible(False)
        y -= 0.045

        ax_edge_high = self.fig.add_axes([ctrl_left, y - 0.025, ctrl_width, 0.025])
        self.slider_edge_high = Slider(ax_edge_high, "Edge High", 50, 250,
                                       valinit=150, valstep=5, color="#9C27B0")
        ax_edge_high.set_visible(False)
        y -= 0.045

        self.edge_sliders = [self.slider_edge_low, self.slider_edge_high]
        for sl in self.edge_sliders:
            sl.ax.set_visible(False)

        ax_show_edge = self.fig.add_axes([ctrl_left, y - 0.035, ctrl_width, 0.035],
                                         facecolor="#e8e8e8")
        self.check_show_edge = CheckButtons(
            ax_show_edge, ("Show Edge Map",), actives=(False,)
        )
        self.check_show_edge.on_clicked(self._on_show_edge_toggle)
        self.check_show_edge.ax.set_visible(False)
        y -= 0.055

        ax_tracking_check = self.fig.add_axes([ctrl_left, y - 0.035, ctrl_width, 0.035],
                                              facecolor="#e8e8e8")
        self.check_tracking = CheckButtons(
            ax_tracking_check, ("Enable Tracking", "Show Tracks"),
            actives=(True, False)
        )
        self.check_tracking.on_clicked(self._on_tracking_toggle)
        self.check_tracking.ax.set_visible(False)
        y -= 0.055

        ax_merge_min = self.fig.add_axes([ctrl_left, y - 0.025, ctrl_width, 0.025])
        self.slider_merge_min = Slider(ax_merge_min, "Merge MinSize", 0, 500,
                                       valinit=0, valstep=10, color="#FF9800")
        y -= 0.045

        ax_merge_thresh = self.fig.add_axes([ctrl_left, y - 0.025, ctrl_width, 0.025])
        self.slider_merge_thresh = Slider(ax_merge_thresh, "Base Threshold", 0, 30,
                                          valinit=5.0, valstep=0.5, color="#FF9800")
        y -= 0.045

        ax_adaptive_check = self.fig.add_axes([ctrl_left, y - 0.035, ctrl_width, 0.035],
                                              facecolor="#e8e8e8")
        self.check_adaptive = CheckButtons(
            ax_adaptive_check, ("Adaptive Threshold",), actives=(True,)
        )
        self.check_adaptive.on_clicked(self._on_adaptive_toggle)
        y -= 0.055

        ax_adaptive_sens = self.fig.add_axes([ctrl_left, y - 0.025, ctrl_width, 0.025])
        self.slider_adaptive_sens = Slider(ax_adaptive_sens, "Sensitivity", 0.1, 3.0,
                                           valinit=1.0, valstep=0.1, color="#FF5722")
        y -= 0.045

        ax_vis = self.fig.add_axes([ctrl_left, y - 0.07, ctrl_width, 0.06],
                                   facecolor="#e8e8e8")
        ax_vis.set_title("Visualization", fontsize=9, fontweight="bold", pad=2)
        self.radio_vis = RadioButtons(ax_vis,
                                      ("Boundaries", "Mean Color", "Random Color"),
                                      active=0)
        self.radio_vis.on_clicked(self._on_vis_change)
        y -= 0.09

        ax_class_label = self.fig.add_axes([ctrl_left, y - 0.025, ctrl_width * 0.45, 0.025])
        self.text_class_label = TextBox(ax_class_label, "Label: ", textalignment="center")
        self.text_class_label.set_val("0")
        self.text_class_label.on_submit(self._on_class_label_change)

        ax_class_name = self.fig.add_axes(
            [ctrl_left + ctrl_width * 0.48, y - 0.025, ctrl_width * 0.52, 0.025]
        )
        self.text_class_name = TextBox(ax_class_name, "Name: ", textalignment="center")
        self.text_class_name.set_val("object")
        self.text_class_name.on_submit(self._on_class_name_change)
        y -= 0.045

        ax_class_sample = self.fig.add_axes([ctrl_left, y - 0.04, 0.10, 0.035])
        self.btn_add_sample = Button(ax_class_sample, "+Sample",
                                     color="#3F51B5", hovercolor="#5C6BC0")
        self.btn_add_sample.on_clicked(self._on_add_sample)

        ax_class_train = self.fig.add_axes([ctrl_left + 0.12, y - 0.04, 0.10, 0.035])
        self.btn_train = Button(ax_class_train, "Train",
                                color="#3F51B5", hovercolor="#5C6BC0")
        self.btn_train.on_clicked(self._on_train)

        ax_classify_check = self.fig.add_axes(
            [ctrl_left, y - 0.08, ctrl_width, 0.035], facecolor="#e8e8e8"
        )
        self.check_classify = CheckButtons(
            ax_classify_check, ("Show Classification",), actives=(False,)
        )
        self.check_classify.on_clicked(self._on_classify_toggle)
        y -= 0.09

        ax_run = self.fig.add_axes([ctrl_left, y - 0.04, 0.10, 0.04])
        self.btn_run = Button(ax_run, "Run", color="#4CAF50", hovercolor="#66BB6A")
        self.btn_run.label.set_fontweight("bold")
        self.btn_run.on_clicked(self._on_run)

        ax_save = self.fig.add_axes([ctrl_left + 0.12, y - 0.04, 0.10, 0.04])
        self.btn_save = Button(ax_save, "Save", color="#2196F3", hovercolor="#42A5F5")
        self.btn_save.on_clicked(self._on_save)
        y -= 0.06

        ax_reset = self.fig.add_axes([ctrl_left, y - 0.04, 0.10, 0.04])
        self.btn_reset = Button(ax_reset, "Reset", color="#f44336", hovercolor="#ef5350")
        self.btn_reset.on_clicked(self._on_reset)

        ax_load = self.fig.add_axes([ctrl_left + 0.12, y - 0.04, 0.10, 0.04])
        self.btn_load = Button(ax_load, "Load File", color="#9C27B0", hovercolor="#AB47BC")
        self.btn_load.on_clicked(self._on_load)
        y -= 0.06

        ax_frame_slider = self.fig.add_axes([0.06, y + 0.01, 0.56, 0.03])
        self.slider_frame = Slider(ax_frame_slider, "Frame", 0, 100,
                                   valinit=0, valstep=1, color="#607D8B")
        self.slider_frame.on_changed(self._on_frame_slider_change)
        ax_frame_slider.set_visible(False)
        self.ax_frame_slider = ax_frame_slider

        ax_prev = self.fig.add_axes([0.06, y - 0.03, 0.08, 0.03])
        self.btn_prev = Button(ax_prev, "< Prev", color="#78909C", hovercolor="#90A4AE")
        self.btn_prev.on_clicked(self._on_prev_frame)
        ax_prev.set_visible(False)
        self.ax_prev = ax_prev

        ax_play = self.fig.add_axes([0.15, y - 0.03, 0.08, 0.03])
        self.btn_play = Button(ax_play, "Play", color="#78909C", hovercolor="#90A4AE")
        self.btn_play.on_clicked(self._on_play_toggle)
        ax_play.set_visible(False)
        self.ax_play = ax_play

        ax_next = self.fig.add_axes([0.24, y - 0.03, 0.08, 0.03])
        self.btn_next = Button(ax_next, "Next >", color="#78909C", hovercolor="#90A4AE")
        self.btn_next.on_clicked(self._on_next_frame)
        ax_next.set_visible(False)
        self.ax_next = ax_next

        ax_process_video = self.fig.add_axes([0.33, y - 0.03, 0.10, 0.03])
        self.btn_process_video = Button(ax_process_video, "Process All",
                                        color="#4CAF50", hovercolor="#66BB6A")
        self.btn_process_video.on_clicked(self._on_process_video)
        ax_process_video.set_visible(False)
        self.ax_process_video = ax_process_video

        self.current_algo = "SLIC"
        self.edge_guided = False
        self.adaptive_merge = True
        self.enable_tracking = True
        self._update_info(
            "Ready. Select mode (Image/Video), algorithm, adjust parameters, and click Run.\n"
            "Features: Image/Video, Compactness presets, Edge guidance, Adaptive merge, "
            "Tracking, Classification"
        )

    def _on_mode_change(self, label):
        self.mode = label.lower()
        is_video = self.mode == "video"
        self.ax_temporal_title.set_visible(is_video)
        self.slider_temporal.ax.set_visible(is_video)
        self.check_tracking.ax.set_visible(is_video)
        self.ax_frame_slider.set_visible(is_video)
        self.ax_prev.set_visible(is_video)
        self.ax_play.set_visible(is_video)
        self.ax_next.set_visible(is_video)
        self.ax_process_video.set_visible(is_video)
        if is_video and self.video_processor is None:
            self._update_info("Video mode. Click 'Load File' to open a video.")
        self.fig.canvas.draw_idle()

    def _on_algo_change(self, label):
        self.current_algo = label
        if label == "SLIC":
            for sl in self.slic_sliders:
                sl.ax.set_visible(True)
            for sl in self.fz_sliders:
                sl.ax.set_visible(False)
            self.radio_compact.ax.set_visible(True)
        else:
            for sl in self.slic_sliders:
                sl.ax.set_visible(False)
            for sl in self.fz_sliders:
                sl.ax.set_visible(True)
            self.radio_compact.ax.set_visible(False)
            self.slider_slic_c.ax.set_visible(False)
        self.fig.canvas.draw_idle()

    def _on_compact_change(self, label):
        if label == "Custom":
            self.slider_slic_c.ax.set_visible(True)
        else:
            self.slider_slic_c.ax.set_visible(False)
        self.fig.canvas.draw_idle()

    def _on_edge_toggle(self, label):
        self.edge_guided = not self.edge_guided
        for sl in self.edge_sliders:
            sl.ax.set_visible(self.edge_guided)
        self.radio_edge_method.ax.set_visible(self.edge_guided)
        self.check_show_edge.ax.set_visible(self.edge_guided)
        self.fig.canvas.draw_idle()

    def _on_show_edge_toggle(self, label):
        self.show_edge_map = not self.show_edge_map
        self._refresh_display()
        self.fig.canvas.draw_idle()

    def _on_adaptive_toggle(self, label):
        self.adaptive_merge = not self.adaptive_merge
        self.slider_adaptive_sens.ax.set_visible(self.adaptive_merge)
        self.fig.canvas.draw_idle()

    def _on_tracking_toggle(self, label):
        if label == "Enable Tracking":
            self.enable_tracking = not self.enable_tracking
        elif label == "Show Tracks":
            self.show_tracks = not self.show_tracks
            self._refresh_display()
        self.fig.canvas.draw_idle()

    def _on_classify_toggle(self, label):
        self.show_classification = not self.show_classification
        self._refresh_display()
        self.fig.canvas.draw_idle()

    def _on_vis_change(self, label):
        self.vis_mode = {
            "Boundaries": "boundaries",
            "Mean Color": "mean_color",
            "Random Color": "random_color",
        }[label]
        self._refresh_display()
        self.fig.canvas.draw_idle()

    def _on_class_label_change(self, text):
        try:
            self.class_label_input = int(text)
        except ValueError:
            pass

    def _on_class_name_change(self, text):
        self.class_name_input = text if text else "object"

    def _on_canvas_click(self, event):
        if event.inaxes != self.ax_result:
            return
        if event.xdata is None or event.ydata is None:
            return
        x, y = int(event.xdata), int(event.ydata)
        if self.mode == "image" and self.current_segments is not None:
            if 0 <= y < self.current_segments.shape[0] and 0 <= x < self.current_segments.shape[1]:
                self.selected_seg_id = int(self.current_segments[y, x])
                self._update_info(
                    f"Selected superpixel ID={self.selected_seg_id}. "
                    f"Set label/name and click '+Sample' to add training sample."
                )
                self.fig.canvas.draw_idle()
        elif self.mode == "video" and self.video_processor is not None:
            if len(self.video_processor.segmentations) > 0:
                segs = self.video_processor.segmentations[-1]
                if 0 <= y < segs.shape[0] and 0 <= x < segs.shape[1]:
                    self.selected_seg_id = int(segs[y, x])
                    self._update_info(
                        f"Selected superpixel ID={self.selected_seg_id}. "
                        f"Set label/name and click '+Sample' to add training sample."
                    )
                    self.fig.canvas.draw_idle()

    def _on_add_sample(self, event):
        if self.selected_seg_id is None:
            self._update_info("Click on a superpixel first to select it.")
            self.fig.canvas.draw_idle()
            return
        if self.mode == "image":
            ok = self.segmenter.classifier.add_training_sample(
                self.image, self.current_segments, self.selected_seg_id,
                self.class_label_input, self.class_name_input
            )
        else:
            if self.video_processor is None or len(self.video_processor.frames_buffer) == 0:
                self._update_info("No video loaded.")
                self.fig.canvas.draw_idle()
                return
            ok = self.video_processor.add_classification_sample(
                len(self.video_processor.frames_buffer) - 1,
                self.selected_seg_id,
                self.class_label_input, self.class_name_input
            )
        if ok:
            n_samples = len(self.video_processor.classifier.training_data) if self.mode == "video" \
                else len(self.segmenter.classifier.training_data) \
                if hasattr(self.segmenter, 'classifier') else len(self.video_processor.classifier.training_data)
            self._update_info(
                f"Added training sample: label={self.class_label_input} "
                f"({self.class_name_input}), ID={self.selected_seg_id}. "
                f"Total samples: {n_samples}"
            )
        else:
            self._update_info("Failed to add training sample.")
        self.fig.canvas.draw_idle()

    def _on_train(self, event):
        if self.mode == "image":
            if not hasattr(self.segmenter, 'classifier'):
                self.segmenter.classifier = SuperpixelClassifier()
            ok = self.segmenter.classifier.train()
            n = len(self.segmenter.classifier.training_data)
        else:
            if self.video_processor is None:
                self._update_info("No video loaded.")
                self.fig.canvas.draw_idle()
                return
            ok = self.video_processor.train_classifier()
            n = len(self.video_processor.classifier.training_data)
        if ok:
            self._update_info(f"Classifier trained with {n} samples.")
        else:
            self._update_info(f"Need at least 2 training samples (have {n}).")
        self.fig.canvas.draw_idle()

    def _on_frame_slider_change(self, val):
        if self.video_processor is None:
            return
        target = int(val)
        if target < len(self.video_processor.segmentations):
            self.video_frame_idx = target
            self._refresh_display()
            self.fig.canvas.draw_idle()

    def _on_prev_frame(self, event):
        if self.video_processor is None:
            return
        self.video_frame_idx = max(0, self.video_frame_idx - 1)
        self.slider_frame.set_val(self.video_frame_idx)

    def _on_next_frame(self, event):
        if self.video_processor is None:
            return
        self.video_frame_idx += 1
        if self.video_frame_idx >= len(self.video_processor.segmentations):
            frame = self.video_processor.read_frame()
            if frame is not None:
                self._process_single_frame(frame)
            else:
                self.video_frame_idx -= 1
                self._update_info("End of video.")
                self.fig.canvas.draw_idle()
                return
        self.slider_frame.set_val(self.video_frame_idx)

    def _on_play_toggle(self, event):
        self.video_playing = not self.video_playing
        self.btn_play.label.set_text("Pause" if self.video_playing else "Play")
        if self.video_playing:
            self._start_playback()
        else:
            self._stop_playback()
        self.fig.canvas.draw_idle()

    def _start_playback(self):
        if self.video_timer is None:
            interval = 1000 / max(self.video_processor.fps, 1) if self.video_processor else 50
            self.video_timer = self.fig.canvas.new_timer(interval=int(interval))
            self.video_timer.add_callback(self._playback_step)
        self.video_timer.start()

    def _stop_playback(self):
        if self.video_timer is not None:
            self.video_timer.stop()

    def _playback_step(self):
        if not self.video_playing:
            return
        if self.video_processor is None:
            self.video_playing = False
            self.btn_play.label.set_text("Play")
            return
        self.video_frame_idx += 1
        if self.video_frame_idx >= len(self.video_processor.segmentations):
            frame = self.video_processor.read_frame()
            if frame is None:
                self.video_playing = False
                self.btn_play.label.set_text("Play")
                self._update_info("End of video.")
                self.fig.canvas.draw_idle()
                return
            self._process_single_frame(frame)
        self.slider_frame.set_val(self.video_frame_idx)

    def _on_process_video(self, event):
        if self.video_processor is None:
            self._update_info("Load a video first.")
            self.fig.canvas.draw_idle()
            return
        self._update_info("Processing video...")
        self.fig.canvas.draw_idle()
        try:
            self.video_processor.process_video(
                progress_callback=lambda i, t: self._update_info(
                    f"Processing frame {i}/{t}..."
                )
            )
        except Exception as e:
            self._update_info(f"Error: {e}")
            self.fig.canvas.draw_idle()
            return
        max_frame = max(0, len(self.video_processor.segmentations) - 1)
        self.slider_frame.valmax = max_frame
        self.slider_frame.ax.set_xlim(0, max_frame)
        self._update_info(f"Video processed. {len(self.video_processor.segmentations)} frames.")
        self.fig.canvas.draw_idle()

    def _process_single_frame(self, frame):
        edge_kwargs = {
            "edge_guided": self.edge_guided,
            "edge_method": self.radio_edge_method.value_selected.lower(),
            "edge_low": int(self.slider_edge_low.val),
            "edge_high": int(self.slider_edge_high.val),
        } if self.edge_guided else {}

        if self.current_algo == "Felzenszwalb":
            fz_kwargs = {
                "scale": int(self.slider_fz_scale.val),
                "sigma": float(self.slider_fz_sigma.val),
                "min_size": int(self.slider_fz_minsize.val),
            }
            edge_kwargs.update(fz_kwargs)

        self.video_processor.algorithm = self.current_algo
        self.video_processor.n_segments = int(self.slider_slic_n.val)
        preset_map = {
            "Auto": "auto", "Flat": "flat", "Balanced": "balanced",
            "Texture": "texture", "Custom": float(self.slider_slic_c.val),
        }
        self.video_processor.compactness_mode = preset_map[self.radio_compact.value_selected]
        self.video_processor.edge_guided = self.edge_guided
        self.video_processor.temporal_weight = float(self.slider_temporal.val)

        segments, _ = self.video_processor.process_frame(
            frame, use_tracking=self.enable_tracking, **edge_kwargs
        )

        merge_min = int(self.slider_merge_min.val)
        base_thresh = float(self.slider_merge_thresh.val)
        if merge_min > 0:
            self.video_processor.segmentations[-1] = segments
            temp_seg = SuperpixelSegmenter(frame)
            temp_seg.segments = segments
            temp_seg.merge_small_segments(min_size=merge_min)
            segments = temp_seg.segments
            self.video_processor.segmentations[-1] = segments
        if base_thresh > 0:
            temp_seg = SuperpixelSegmenter(frame)
            temp_seg.segments = segments
            temp_seg.merge_by_color_similarity(
                base_threshold=base_thresh,
                adaptive=self.adaptive_merge,
                sensitivity=float(self.slider_adaptive_sens.val),
            )
            segments = temp_seg.segments
            self.video_processor.segmentations[-1] = segments

        return segments

    def _on_run(self, event):
        if self.mode == "image":
            self._run_image_mode()
        else:
            self._run_video_mode_first_frame()

    def _run_image_mode(self):
        self.segmenter = SuperpixelSegmenter(self.image)

        edge_kwargs = {
            "edge_guided": self.edge_guided,
            "edge_method": self.radio_edge_method.value_selected.lower(),
            "edge_low": int(self.slider_edge_low.val),
            "edge_high": int(self.slider_edge_high.val),
        } if self.edge_guided else {}

        if self.current_algo == "SLIC":
            preset_map = {
                "Auto": "auto", "Flat": "flat",
                "Balanced": "balanced", "Texture": "texture",
                "Custom": float(self.slider_slic_c.val),
            }
            compact_mode = preset_map[self.radio_compact.value_selected]
            segments = self.segmenter.run_slic(
                n_segments=int(self.slider_slic_n.val),
                compactness_mode=compact_mode,
                sigma=float(self.slider_slic_s.val),
                **edge_kwargs,
            )
        else:
            segments = self.segmenter.run_felzenszwalb(
                scale=int(self.slider_fz_scale.val),
                sigma=float(self.slider_fz_sigma.val),
                min_size=int(self.slider_fz_minsize.val),
                **edge_kwargs,
            )

        merge_min = int(self.slider_merge_min.val)
        base_thresh = float(self.slider_merge_thresh.val)
        if merge_min > 0:
            self.segmenter.merge_small_segments(min_size=merge_min)
        if base_thresh > 0:
            self.segmenter.merge_by_color_similarity(
                base_threshold=base_thresh,
                adaptive=self.adaptive_merge,
                sensitivity=float(self.slider_adaptive_sens.val),
            )

        self.current_segments = self.segmenter.segments
        self.selected_seg_id = None

        if self.edge_guided and self.segmenter.edge_map is not None and self.show_edge_map:
            self.ax_original.clear()
            self.ax_original.imshow(self.segmenter.edge_map, cmap="gray")
            self.ax_original.set_title("Edge Map", fontsize=12, fontweight="bold")
        else:
            self.ax_original.clear()
            self.ax_original.imshow(self.image)
            self.ax_original.set_title("Original Image", fontsize=12, fontweight="bold")
        self.ax_original.set_xticks([])
        self.ax_original.set_yticks([])

        self._refresh_display()
        n_seg = self.segmenter.get_num_segments()
        compact_info = ""
        if self.current_algo == "SLIC" and self.segmenter.compactness_preset:
            compact_val = self.segmenter.resolve_compactness(
                self.radio_compact.value_selected.lower()
                if self.radio_compact.value_selected != "Custom"
                else self.slider_slic_c.val
            )
            compact_info = (
                f" | Compactness: {self.segmenter.compactness_preset} ({compact_val:.1f})"
            )
        edge_info = " | Edge-Guided" if self.edge_guided else ""
        merge_info = " | Adaptive Merge" if self.adaptive_merge else ""
        texture_info = ""
        if self.current_algo == "SLIC" and self.radio_compact.value_selected == "Auto":
            texture_info = f" | Detected: {self.segmenter.detect_texture_level()}"

        self._update_info(
            f"Algorithm: {self.current_algo} | Segments: {n_seg} | "
            f"Image: {self.image.shape[1]}x{self.image.shape[0]}"
            f"{compact_info}{edge_info}{merge_info}{texture_info}"
        )
        self.fig.canvas.draw_idle()

    def _run_video_mode_first_frame(self):
        if self.video_processor is None or len(self.video_processor.frames_buffer) == 0:
            self._update_info("Load a video first (Load File -> select video).")
            self.fig.canvas.draw_idle()
            return
        self.video_processor.tracker.reset()
        self.video_processor.segmentations = []
        self.video_processor.prediction_history = []
        self.video_processor.frames_buffer = []
        self.video_processor.classifier.reset()
        self.video_processor.current_frame_idx = 0
        self.video_processor.video_capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
        frame = self.video_processor.read_frame()
        if frame is None:
            self._update_info("Failed to read video.")
            self.fig.canvas.draw_idle()
            return
        self._process_single_frame(frame)
        self.video_frame_idx = 0
        max_frame = max(0, self.video_processor.frame_count - 1)
        self.slider_frame.valmax = max_frame
        self.slider_frame.ax.set_xlim(0, max_frame)
        self.slider_frame.set_val(0)
        self._refresh_display()
        self._update_info(
            f"Video ready. {self.video_processor.frame_count} frames @ "
            f"{self.video_processor.fps:.1f} FPS. Use Play or Process All."
        )
        self.fig.canvas.draw_idle()

    def _refresh_display(self):
        if self.mode == "image":
            if self.current_segments is None:
                self.ax_result.clear()
                self.ax_result.imshow(self.image)
            else:
                if self.vis_mode == "boundaries":
                    result = self.segmenter.visualize_boundaries()
                elif self.vis_mode == "mean_color":
                    result = self.segmenter.visualize_mean_color()
                else:
                    result = self.segmenter.visualize_random_color()
                if self.show_classification and self.segmenter.classifier.model is not None:
                    pred_mask, preds = self.segmenter.classifier.classify_image(
                        self.image, self.current_segments
                    )
                    result = cv2.addWeighted(result, 0.6, pred_mask, 0.4, 0)
                self.ax_result.clear()
                self.ax_result.imshow(result)
            self.ax_result.set_title("Segmentation Result", fontsize=12, fontweight="bold")
            self.ax_result.set_xticks([])
            self.ax_result.set_yticks([])
        else:
            if self.video_processor is None or len(self.video_processor.segmentations) == 0:
                self.ax_result.clear()
                self.ax_result.imshow(self.image)
            else:
                vis = self.video_processor.get_visualization(
                    self.video_frame_idx,
                    mode=self.vis_mode,
                    show_tracks=self.show_tracks,
                    show_classification=self.show_classification,
                )
                if vis is not None:
                    self.ax_result.clear()
                    self.ax_result.imshow(vis)
                    self.ax_result.set_title(
                        f"Frame {self.video_frame_idx}/{len(self.video_processor.segmentations) - 1}",
                        fontsize=12, fontweight="bold"
                    )
                    if len(self.video_processor.frames_buffer) > self.video_frame_idx:
                        frame = self.video_processor.frames_buffer[self.video_frame_idx]
                        if self.show_edge_map and self.video_processor.tracker.prev_image is not None:
                            pass
                        else:
                            self.ax_original.clear()
                            self.ax_original.imshow(frame)
                            self.ax_original.set_title(
                                f"Frame {self.video_frame_idx}",
                                fontsize=12, fontweight="bold"
                            )
                        self.ax_original.set_xticks([])
                        self.ax_original.set_yticks([])
            self.ax_result.set_xticks([])
            self.ax_result.set_yticks([])

    def _update_info(self, text):
        self.ax_info.clear()
        self.ax_info.axis("off")
        self.ax_info.text(0.5, 0.5, text, transform=self.ax_info.transAxes,
                          fontsize=9, ha="center", va="center",
                          bbox=dict(boxstyle="round,pad=0.5", facecolor="wheat", alpha=0.8))

    def _on_save(self, event):
        if self.mode == "image":
            if self.current_segments is None:
                self._update_info("No result to save. Run first!")
                self.fig.canvas.draw_idle()
                return
            result = self.segmenter.visualize_boundaries()
            result_bgr = cv2.cvtColor(result, cv2.COLOR_RGB2BGR)
            filename = f"superpixel_{self.current_algo.lower()}_result.png"
            cv2.imwrite(filename, result_bgr)
            self._update_info(f"Saved: {filename}")
        else:
            if self.video_processor is None or len(self.video_processor.segmentations) == 0:
                self._update_info("Process video first!")
                self.fig.canvas.draw_idle()
                return
            filename = f"superpixel_{self.current_algo.lower()}_video.mp4"
            ok = self.video_processor.save_output_video(
                filename,
                mode=self.vis_mode,
                show_tracks=self.show_tracks,
                show_classification=self.show_classification,
            )
            if ok:
                self._update_info(f"Saved: {filename}")
            else:
                self._update_info("Failed to save video.")
        self.fig.canvas.draw_idle()

    def _on_reset(self, event):
        if self.mode == "image":
            self.segmenter = SuperpixelSegmenter(self.image)
            self.current_segments = None
            self.selected_seg_id = None
            self.show_edge_map = False
            self.check_show_edge.set_active(0)
            self.ax_result.clear()
            self.ax_result.imshow(self.image)
            self.ax_result.set_title("Segmentation Result", fontsize=12, fontweight="bold")
            self.ax_result.set_xticks([])
            self.ax_result.set_yticks([])
            self.ax_original.clear()
            self.ax_original.imshow(self.image)
            self.ax_original.set_title("Original Image", fontsize=12, fontweight="bold")
            self.ax_original.set_xticks([])
            self.ax_original.set_yticks([])
            self.slider_merge_min.set_val(0)
            self.slider_merge_thresh.set_val(5.0)
            self._update_info("Reset. Ready to run again.")
        else:
            if self.video_processor is not None:
                self.video_processor.tracker.reset()
                self.video_processor.segmentations = []
                self.video_processor.prediction_history = []
                self.video_playing = False
                self.btn_play.label.set_text("Play")
                self._stop_playback()
            self.video_frame_idx = 0
            self.ax_result.clear()
            self.ax_result.imshow(self.image)
            self.ax_result.set_title("Segmentation Result", fontsize=12, fontweight="bold")
            self.ax_result.set_xticks([])
            self.ax_result.set_yticks([])
            self._update_info("Video reset. Load a new video or run again.")
        self.fig.canvas.draw_idle()

    def _on_load(self, event):
        from tkinter import Tk, filedialog
        root = Tk()
        root.withdraw()
        file_path = filedialog.askopenfilename(
            title="Select Image or Video",
            filetypes=[
                ("All files", "*.*"),
                ("Image files", "*.png *.jpg *.jpeg *.bmp *.tiff *.tif *.webp"),
                ("Video files", "*.mp4 *.avi *.mov *.mkv *.webm *.flv *.wmv *.m4v"),
            ]
        )
        root.destroy()
        if not file_path:
            return
        self._try_load_path(file_path)

    def _load_image(self, file_path):
        img = cv2.imread(file_path)
        if img is None:
            self._update_info(f"Failed to load: {file_path}")
            self.fig.canvas.draw_idle()
            return
        self.image = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        self.segmenter = SuperpixelSegmenter(self.image)
        self.current_segments = None
        self.show_edge_map = False
        self.mode = "image"
        self.radio_mode.set_active(0)
        self.ax_original.clear()
        self.ax_original.imshow(self.image)
        self.ax_original.set_title("Original Image", fontsize=12, fontweight="bold")
        self.ax_original.set_xticks([])
        self.ax_original.set_yticks([])
        self.ax_result.clear()
        self.ax_result.imshow(self.image)
        self.ax_result.set_title("Segmentation Result", fontsize=12, fontweight="bold")
        self.ax_result.set_xticks([])
        self.ax_result.set_yticks([])
        self._update_info(f"Loaded image: {file_path} ({self.image.shape[1]}x{self.image.shape[0]})")
        self.fig.canvas.draw_idle()

    def _load_video(self, file_path):
        try:
            if self.video_processor is None:
                self.video_processor = VideoSuperpixel()
            self.video_processor.open_video(file_path)
            self.video_processor.tracker.reset()
            self.video_processor.segmentations = []
            self.video_processor.prediction_history = []
            self.video_processor.frames_buffer = []
            self.video_processor.classifier.reset()
            self.mode = "video"
            self.radio_mode.set_active(1)
            self.video_frame_idx = 0
            self.video_playing = False
            self.btn_play.label.set_text("Play")
            self._stop_playback()
            max_frame = max(0, self.video_processor.frame_count - 1)
            self.slider_frame.valmax = max_frame
            self.slider_frame.ax.set_xlim(0, max_frame)
            self.slider_frame.set_val(0)
            frame = self.video_processor.read_frame()
            if frame is not None:
                self.video_processor.frames_buffer = [frame]
                self.ax_original.clear()
                self.ax_original.imshow(frame)
                self.ax_original.set_title("Frame 0", fontsize=12, fontweight="bold")
                self.ax_original.set_xticks([])
                self.ax_original.set_yticks([])
                self.ax_result.clear()
                self.ax_result.imshow(frame)
                self.ax_result.set_title("Segmentation Result", fontsize=12, fontweight="bold")
                self.ax_result.set_xticks([])
                self.ax_result.set_yticks([])
            self._update_info(
                f"Loaded video: {file_path}\n"
                f"{self.video_processor.frame_count} frames @ "
                f"{self.video_processor.fps:.1f} FPS, "
                f"{self.video_processor.frame_width}x{self.video_processor.frame_height}"
            )
            self.fig.canvas.draw_idle()
        except Exception as e:
            self._update_info(f"Failed to load video: {e}")
            self.fig.canvas.draw_idle()

    def run(self):
        plt.show()
        self._stop_playback()
        if self.video_processor is not None:
            self.video_processor.close_video()


def main():
    initial_path = sys.argv[1] if len(sys.argv) > 1 else None
    app = SuperpixelApp(initial_path=initial_path)
    app.run()


if __name__ == "__main__":
    main()
