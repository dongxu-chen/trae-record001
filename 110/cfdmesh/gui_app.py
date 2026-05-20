import sys
import os
import numpy as np
from pathlib import Path

try:
    from PyQt5.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QLabel, QSlider, QPushButton, QTextEdit, QFileDialog,
        QGroupBox, QSplitter, QDockWidget, QCheckBox, QProgressBar
    )
    from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QMimeData
    from PyQt5.QtGui import QFont, QColor, QDragEnterEvent, QDropEvent
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False

try:
    import pyvista as pv
    from pyvistaqt import BackgroundPlotter
    PYVISTA_AVAILABLE = True
except ImportError:
    PYVISTA_AVAILABLE = False

try:
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

import meshio
from .fast_quality import FastMeshQuality


class QualityHistogramWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)

        self.figure = Figure(figsize=(4, 3), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.layout.addWidget(self.canvas)

        self.axes = self.figure.subplots(2, 2)
        self.figure.tight_layout(pad=2.0)

    def update_histograms(self, quality_data: dict):
        for ax in self.axes.flat:
            ax.clear()

        all_non_orth = []
        all_aspect = []
        all_size = []

        for cell_type, metrics in quality_data.items():
            if 'non_orthogonality' in metrics:
                all_non_orth.extend(metrics['non_orthogonality'])
            if 'aspect_ratio' in metrics:
                all_aspect.extend(metrics['aspect_ratio'])
            if 'area' in metrics:
                all_size.extend(metrics['area'])
            elif 'volume' in metrics:
                all_size.extend(metrics['volume'])

        colors = ['#3498db', '#e74c3c', '#2ecc71', '#f39c12']
        titles = ['非正交度 (°)', '长宽比', '单元尺寸']

        data_list = [all_non_orth, all_aspect, all_size]
        ax_list = [self.axes[0, 0], self.axes[0, 1], self.axes[1, 0]]

        for ax, data, title, color in zip(ax_list, data_list, titles, colors):
            if len(data) > 0:
                data = np.array(data)
                data = data[np.isfinite(data)]
                if len(data) > 0:
                    ax.hist(data, bins=20, color=color, alpha=0.7, edgecolor='black')
                    ax.axvline(np.mean(data), color='red', linestyle='dashed', linewidth=1)
                    ax.set_title(title, fontsize=9)
                    ax.tick_params(axis='both', labelsize=7)

        self.axes[1, 1].axis('off')
        if len(all_non_orth) > 0:
            bad_cells = sum(1 for x in all_non_orth if x > 70)
            total = len(all_non_orth)
            quality_text = f"""
            质量统计:
            ------------
            单元总数: {total}
            坏单元数: {bad_cells}
            坏单元率: {bad_cells/total*100:.1f}%
            平均非正交: {np.mean(all_non_orth):.1f}°

            质量评级: {"优秀" if bad_cells/total < 0.01 else "良好" if bad_cells/total < 0.05 else "合格" if bad_cells/total < 0.15 else "较差"}
            """
            self.axes[1, 1].text(0.1, 0.5, quality_text, fontsize=8, verticalalignment='center')

        self.canvas.draw()


class DraggablePlotter(QWidget):
    fileDropped = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.layout = QVBoxLayout(self)

        if PYVISTA_AVAILABLE:
            self.plotter = BackgroundPlotter(show=False, window_size=(800, 600))
            self.layout.addWidget(self.plotter)
            self._show_welcome()

        self.setMinimumSize(600, 400)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        for url in event.mimeData().urls():
            if url.isLocalFile():
                file_path = url.toLocalFile()
                if file_path.endswith(('.vtk', '.vtu', '.stl', '.msh', '.obj', '.ply')):
                    self.fileDropped.emit(file_path)
                    event.acceptProposedAction()
                    break

    def _show_welcome(self):
        self.plotter.add_text(
            "拖拽网格文件到此处\n或点击左侧按钮加载",
            position='center',
            font_size=16,
            color='gray'
        )
        self.plotter.show_grid()

    def load_mesh(self, mesh_data):
        self.plotter.clear()

        if isinstance(mesh_data, pv.UnstructuredGrid):
            self.plotter.add_mesh(
                mesh_data,
                show_edges=True,
                edge_color='white',
                line_width=0.5,
                cmap='viridis',
                opacity=0.9
            )
        else:
            self.plotter.add_mesh(
                mesh_data,
                style='surface',
                show_edges=True,
                edge_color='white'
            )

        self.plotter.view_isometric()
        self.plotter.camera.zoom(0.8)

    def update_mesh_points(self, points):
        if hasattr(self, '_current_mesh'):
            self._current_mesh.points = points
            self.plotter.update()

    def color_by_quality(self, quality_array, scalar_name='Non-Orthogonality'):
        if hasattr(self, '_current_mesh'):
            self._current_mesh.cell_data[scalar_name] = quality_array
            self.plotter.add_mesh(
                self._current_mesh,
                scalars=scalar_name,
                show_edges=True,
                edge_color='white',
                cmap='RdYlGn_r',
                clim=[0, 70],
                opacity=0.9
            )


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CFD 网格前处理工具 - 交互式版")
        self.setGeometry(100, 100, 1400, 900)

        self.current_mesh = None
        self.original_points = None
        self.mesh_cells = None
        self.quality_calculator = None

        self._setup_ui()
        self._setup_connections()

    def _setup_ui(self):
        central_widget = QWidget()
        main_layout = QHBoxLayout(central_widget)
        self.setCentralWidget(central_widget)

        splitter = QSplitter(Qt.Horizontal)

        left_panel = self._create_left_panel()
        right_panel = self._create_right_panel()

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)

        main_layout.addWidget(splitter)

    def _create_left_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)

        file_group = QGroupBox("文件操作")
        file_layout = QVBoxLayout()

        self.load_btn = QPushButton("加载网格文件")
        self.load_btn.setStyleSheet("font-size: 12px; padding: 8px;")
        file_layout.addWidget(self.load_btn)

        self.file_label = QLabel("拖拽文件到3D视图或点击按钮加载")
        self.file_label.setWordWrap(True)
        file_layout.addWidget(self.file_label)

        file_group.setLayout(file_layout)
        layout.addWidget(file_group)

        smooth_group = QGroupBox("Laplacian 平滑")
        smooth_layout = QVBoxLayout()

        smooth_layout.addWidget(QLabel("迭代次数:"))
        self.iter_slider = QSlider(Qt.Horizontal)
        self.iter_slider.setRange(1, 100)
        self.iter_slider.setValue(20)
        self.iter_label = QLabel("20")
        iter_hbox = QHBoxLayout()
        iter_hbox.addWidget(self.iter_slider)
        iter_hbox.addWidget(self.iter_label)
        smooth_layout.addLayout(iter_hbox)

        smooth_layout.addWidget(QLabel("松弛因子:"))
        self.relax_slider = QSlider(Qt.Horizontal)
        self.relax_slider.setRange(1, 100)
        self.relax_slider.setValue(50)
        self.relax_label = QLabel("0.50")
        relax_hbox = QHBoxLayout()
        relax_hbox.addWidget(self.relax_slider)
        relax_hbox.addWidget(self.relax_label)
        smooth_layout.addLayout(relax_hbox)

        self.fixed_boundary_cb = QCheckBox("固定边界节点")
        self.fixed_boundary_cb.setChecked(True)
        smooth_layout.addWidget(self.fixed_boundary_cb)

        self.live_preview_cb = QCheckBox("实时预览 (拖动滑块时)")
        self.live_preview_cb.setChecked(True)
        smooth_layout.addWidget(self.live_preview_cb)

        self.apply_smooth_btn = QPushButton("应用平滑")
        self.apply_smooth_btn.setStyleSheet("background-color: #3498db; color: white; padding: 8px;")
        smooth_layout.addWidget(self.apply_smooth_btn)

        self.reset_btn = QPushButton("重置网格")
        self.reset_btn.setStyleSheet("background-color: #e74c3c; color: white; padding: 8px;")
        smooth_layout.addWidget(self.reset_btn)

        smooth_group.setLayout(smooth_layout)
        layout.addWidget(smooth_group)

        viz_group = QGroupBox("可视化选项")
        viz_layout = QVBoxLayout()

        self.show_edges_cb = QCheckBox("显示单元边线")
        self.show_edges_cb.setChecked(True)
        viz_layout.addWidget(self.show_edges_cb)

        self.color_by_quality_cb = QCheckBox("按非正交度着色")
        self.color_by_quality_cb.setChecked(False)
        viz_layout.addWidget(self.color_by_quality_cb)

        viz_group.setLayout(viz_layout)
        layout.addWidget(viz_group)

        layout.addWidget(QLabel("计算进度:"))
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)

        layout.addStretch()

        return panel

    def _create_right_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)

        self.plotter_widget = DraggablePlotter()
        layout.addWidget(self.plotter_widget)

        if MATPLOTLIB_AVAILABLE:
            self.histogram_widget = QualityHistogramWidget()
            layout.addWidget(self.histogram_widget)

        self.report_text = QTextEdit()
        self.report_text.setReadOnly(True)
        self.report_text.setMaximumHeight(200)
        self.report_text.setFont(QFont("Consolas", 9))
        layout.addWidget(self.report_text)

        return panel

    def _setup_connections(self):
        self.load_btn.clicked.connect(self._load_file_dialog)
        self.plotter_widget.fileDropped.connect(self._load_mesh_file)

        self.iter_slider.valueChanged.connect(self._on_iter_changed)
        self.relax_slider.valueChanged.connect(self._on_relax_changed)

        self.iter_slider.sliderReleased.connect(self._on_slider_released)
        self.relax_slider.sliderReleased.connect(self._on_slider_released)

        self.apply_smooth_btn.clicked.connect(self._apply_smoothing)
        self.reset_btn.clicked.connect(self._reset_mesh)

        self.show_edges_cb.toggled.connect(self._update_visualization)
        self.color_by_quality_cb.toggled.connect(self._update_coloring)

    def _load_file_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择网格文件",
            "",
            "网格文件 (*.vtk *.vtu *.stl *.msh *.obj *.ply);;所有文件 (*.*)"
        )
        if file_path:
            self._load_mesh_file(file_path)

    def _load_mesh_file(self, file_path: str):
        self.progress_bar.setValue(10)

        try:
            mesh = meshio.read(file_path)
            self.progress_bar.setValue(30)

            self.original_points = mesh.points.copy()
            if self.original_points.shape[1] == 2:
                self.original_points = np.hstack([self.original_points, np.zeros((len(self.original_points), 1))])

            self.mesh_cells = {}
            for cell_block in mesh.cells:
                self.mesh_cells[cell_block.type] = cell_block.data.tolist()

            self.progress_bar.setValue(50)

            self.quality_calculator = FastMeshQuality(self.original_points, self.mesh_cells)

            self.progress_bar.setValue(70)

            pv_cells = []
            pv_cell_types = []
            cell_offset = 0

            for cell_type, cell_data in self.mesh_cells.items():
                for cell in cell_data:
                    pv_cells.extend([len(cell)] + list(cell))
                    pv_cell_types.append(self._get_vtk_cell_type(cell_type))

            pv_cells = np.array(pv_cells)
            pv_cell_types = np.array(pv_cell_types)

            pv_mesh = pv.UnstructuredGrid(pv_cells, pv_cell_types, self.original_points)
            self.plotter_widget._current_mesh = pv_mesh
            self.plotter_widget.load_mesh(pv_mesh)

            self.progress_bar.setValue(90)

            self._compute_and_display_quality()

            self.file_label.setText(f"已加载: {Path(file_path).name}\n"
                                   f"节点数: {len(self.original_points)}\n"
                                   f"单元数: {sum(len(c) for c in self.mesh_cells.values())}")

            self.progress_bar.setValue(100)

        except Exception as e:
            self.report_text.append(f"加载失败: {str(e)}")
            self.progress_bar.setValue(0)

    def _get_vtk_cell_type(self, cell_type: str) -> int:
        type_map = {
            'triangle': 5,
            'quad': 9,
            'tetra': 10,
            'hexahedron': 12,
            'wedge': 13,
            'pyramid': 14
        }
        return type_map.get(cell_type, 0)

    def _on_iter_changed(self, value):
        self.iter_label.setText(str(value))

    def _on_relax_changed(self, value):
        relax = value / 100.0
        self.relax_label.setText(f"{relax:.2f}")

    def _on_slider_released(self):
        if self.live_preview_cb.isChecked() and self.quality_calculator:
            self._apply_smoothing()

    def _apply_smoothing(self):
        if self.quality_calculator is None:
            return

        iterations = self.iter_slider.value()
        relaxation = self.relax_slider.value() / 100.0
        fixed_boundary = self.fixed_boundary_cb.isChecked()

        self.progress_bar.setValue(20)

        new_points = self.quality_calculator.laplacian_smooth(
            iterations=iterations,
            relaxation=relaxation,
            fixed_boundary=fixed_boundary
        )

        self.progress_bar.setValue(60)

        self.quality_calculator.points = new_points
        self.plotter_widget.update_mesh_points(new_points)

        self._compute_and_display_quality()

        self.progress_bar.setValue(100)

    def _reset_mesh(self):
        if self.quality_calculator is None:
            return

        self.quality_calculator.points = self.original_points.copy()
        self.plotter_widget.update_mesh_points(self.original_points)
        self._compute_and_display_quality()

    def _compute_and_display_quality(self):
        if self.quality_calculator is None:
            return

        quality_data = self.quality_calculator.compute_all()

        report_lines = []
        report_lines.append("=" * 50)
        report_lines.append("网格质量报告")
        report_lines.append("=" * 50)

        all_non_orth = []
        for cell_type, metrics in quality_data.items():
            report_lines.append(f"\n单元类型: {cell_type}")
            report_lines.append(f"单元数量: {len(list(metrics.values())[0])}")

            if 'non_orthogonality' in metrics:
                non_orth = metrics['non_orthogonality']
                all_non_orth.extend(non_orth)
                report_lines.append(f"非正交度: {np.mean(non_orth):.2f}° (avg), {np.max(non_orth):.2f}° (max)")

            if 'aspect_ratio' in metrics:
                aspect = metrics['aspect_ratio']
                report_lines.append(f"长宽比: {np.mean(aspect):.2f} (avg), {np.max(aspect):.2f} (max)")

            if 'area' in metrics:
                area = metrics['area']
                report_lines.append(f"总面积: {np.sum(area):.4f}")

            if 'volume' in metrics:
                volume = metrics['volume']
                report_lines.append(f"总体积: {np.sum(volume):.4f}")

        if len(all_non_orth) > 0:
            bad_cells = sum(1 for x in all_non_orth if x > 70)
            bad_ratio = bad_cells / len(all_non_orth) * 100
            report_lines.append(f"\n坏单元统计 (非正交度>70°): {bad_cells} 个 ({bad_ratio:.1f}%)")

            if bad_ratio < 1:
                report_lines.append("质量评级: ★★★★★ 优秀")
            elif bad_ratio < 5:
                report_lines.append("质量评级: ★★★★☆ 良好")
            elif bad_ratio < 15:
                report_lines.append("质量评级: ★★★☆☆ 合格")
            else:
                report_lines.append("质量评级: ★★☆☆☆ 较差")

        self.report_text.setText("\n".join(report_lines))

        if MATPLOTLIB_AVAILABLE:
            self.histogram_widget.update_histograms(quality_data)

        if self.color_by_quality_cb.isChecked() and len(all_non_orth) > 0:
            self.plotter_widget.color_by_quality(np.array(all_non_orth))

    def _update_visualization(self):
        pass

    def _update_coloring(self):
        if self.color_by_quality_cb.isChecked():
            self._compute_and_display_quality()


def main():
    if not PYQT_AVAILABLE:
        print("错误: PyQt5 未安装，请运行: pip install PyQt5")
        return

    if not PYVISTA_AVAILABLE:
        print("错误: pyvista 未安装，请运行: pip install pyvista pyvistaqt")
        return

    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
