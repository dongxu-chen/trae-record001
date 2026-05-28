import sys
import os
import numpy as np
import trimesh
import cv2
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QImage, QPixmap, QIcon

from gl_viewer import GLViewer3D
from uv_editor import UVEditor
from uv_unwrapper import UVUnwrapper
from texture_mapper import TextureMapper, export_textured_mesh
from advanced_texture import MultiTextureBlender, TextureBaker, TextureStyleTransfer


class TextureMappingApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("纹理映射工具 v3.0 - Texture Mapping Tool")
        self.resize(1800, 1000)

        self.mesh = None
        self.uv = None
        self.texture = None
        self.unwrapper = None
        self.mapper = None
        self.blender = None
        self.baker = None
        self.stylizer = TextureStyleTransfer()
        self.baked_maps = {}
        self.style_reference = None

        self.init_ui()
        self.connect_signals()
        self.create_sample_model()

    def init_ui(self):
        self.create_menu()
        self.create_toolbar()

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(5)

        viewer_control = QWidget()
        viewer_control_layout = QHBoxLayout(viewer_control)
        viewer_control_layout.setContentsMargins(5, 5, 5, 5)
        viewer_control_layout.setSpacing(10)

        self.selection_mode_btn = QPushButton("选择模式: 关闭")
        self.selection_mode_btn.setCheckable(True)
        self.selection_mode_btn.clicked.connect(self.toggle_selection_mode)
        self.selection_mode_btn.setStyleSheet("background-color: #666; color: white; padding: 8px 15px;")
        viewer_control_layout.addWidget(self.selection_mode_btn)

        self.sync_selection_btn = QPushButton("同步选择")
        self.sync_selection_btn.clicked.connect(self.sync_selection)
        viewer_control_layout.addWidget(self.sync_selection_btn)

        self.clear_selection_btn = QPushButton("清除选择")
        self.clear_selection_btn.clicked.connect(self.clear_all_selections)
        viewer_control_layout.addWidget(self.clear_selection_btn)

        viewer_control_layout.addStretch()

        self.info_label = QLabel("选择模式下: 点击3D模型选择顶点，UV编辑器同步高亮")
        self.info_label.setStyleSheet("color: #888; font-style: italic;")
        viewer_control_layout.addWidget(self.info_label)

        left_layout.addWidget(viewer_control)

        self.viewer_3d = GLViewer3D()
        self.viewer_3d.setMinimumSize(500, 500)
        left_layout.addWidget(self.viewer_3d, 1)

        self.view_info = QLabel("3D视图 | 左键: 旋转/选择 | 中键平移 | 滚轮缩放")
        self.view_info.setStyleSheet("background-color: #333; color: white; padding: 5px;")
        left_layout.addWidget(self.view_info)

        main_layout.addWidget(left_panel, 2)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(5)

        self.uv_editor = UVEditor()
        self.uv_editor.setMinimumSize(400, 400)
        right_layout.addWidget(self.uv_editor, 1)

        self.uv_info = QLabel("UV编辑器 | 左键选择/拖动 | Shift多选 | Ctrl+滚轮缩放 | 中键平移")
        self.uv_info.setStyleSheet("background-color: #333; color: white; padding: 5px;")
        right_layout.addWidget(self.uv_info)

        self.control_tab = QTabWidget()
        self.control_tab.setMinimumWidth(400)

        self.create_basic_tab()
        self.create_multi_texture_tab()
        self.create_baking_tab()
        self.create_style_tab()

        right_layout.addWidget(self.control_tab)

        main_layout.addWidget(right_panel, 1)

        self.status_bar = self.statusBar()
        self.status_bar.showMessage("就绪")

    def create_basic_tab(self):
        basic_widget = QWidget()
        basic_layout = QVBoxLayout(basic_widget)
        basic_layout.setContentsMargins(10, 10, 10, 10)
        basic_layout.setSpacing(8)

        unwrap_group = QGroupBox("UV展开 (ABF++ 优化)")
        unwrap_layout = QVBoxLayout(unwrap_group)

        method_layout = QHBoxLayout()
        method_layout.addWidget(QLabel("展开方法:"))
        self.method_combo = QComboBox()
        self.method_combo.addItems(["ABF++ (角度优先)", "LSCM (保角映射)"])
        method_layout.addWidget(self.method_combo)
        unwrap_layout.addLayout(method_layout)

        self.unwrap_btn = QPushButton("执行UV展开")
        self.unwrap_btn.setMinimumHeight(35)
        self.unwrap_btn.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")
        self.unwrap_btn.clicked.connect(self.unwrap_uv)
        unwrap_layout.addWidget(self.unwrap_btn)

        basic_layout.addWidget(unwrap_group)

        uv_edit_group = QGroupBox("UV编辑")
        uv_edit_layout = QGridLayout(uv_edit_group)

        self.select_all_btn = QPushButton("全选")
        self.select_all_btn.clicked.connect(self.uv_editor.select_all)
        uv_edit_layout.addWidget(self.select_all_btn, 0, 0)

        self.clear_sel_btn = QPushButton("清除选择")
        self.clear_sel_btn.clicked.connect(self.uv_editor.clear_selection)
        uv_edit_layout.addWidget(self.clear_sel_btn, 0, 1)

        self.pack_btn = QPushButton("UV打包")
        self.pack_btn.clicked.connect(self.pack_uv)
        uv_edit_layout.addWidget(self.pack_btn, 1, 0)

        self.apply_uv_btn = QPushButton("应用UV到3D视图")
        self.apply_uv_btn.setStyleSheet("background-color: #FF9800; color: white;")
        self.apply_uv_btn.clicked.connect(self.apply_uv_changes)
        uv_edit_layout.addWidget(self.apply_uv_btn, 1, 1)

        transform_layout = QHBoxLayout()
        self.rotate_left_btn = QPushButton("↺")
        self.rotate_left_btn.clicked.connect(lambda: self.uv_editor.rotate_uv(-15))
        transform_layout.addWidget(self.rotate_left_btn)

        self.rotate_right_btn = QPushButton("↻")
        self.rotate_right_btn.clicked.connect(lambda: self.uv_editor.rotate_uv(15))
        transform_layout.addWidget(self.rotate_right_btn)

        self.flip_h_btn = QPushButton("⇆")
        self.flip_h_btn.clicked.connect(lambda: self.uv_editor.flip_uv(True, False))
        transform_layout.addWidget(self.flip_h_btn)

        self.flip_v_btn = QPushButton("⇅")
        self.flip_v_btn.clicked.connect(lambda: self.uv_editor.flip_uv(False, True))
        transform_layout.addWidget(self.flip_v_btn)

        uv_edit_layout.addLayout(transform_layout, 2, 0, 1, 2)

        basic_layout.addWidget(uv_edit_group)

        texture_group = QGroupBox("纹理")
        texture_layout = QVBoxLayout(texture_group)

        tex_btns = QHBoxLayout()
        self.load_tex_btn = QPushButton("加载纹理")
        self.load_tex_btn.clicked.connect(self.load_texture)
        tex_btns.addWidget(self.load_tex_btn)

        self.checker_tex_btn = QPushButton("棋盘格")
        self.checker_tex_btn.clicked.connect(lambda: self.create_procedural_texture('checker'))
        tex_btns.addWidget(self.checker_tex_btn)

        self.gradient_tex_btn = QPushButton("渐变色")
        self.gradient_tex_btn.clicked.connect(lambda: self.create_procedural_texture('gradient'))
        tex_btns.addWidget(self.gradient_tex_btn)

        texture_layout.addLayout(tex_btns)

        basic_layout.addWidget(texture_group)

        seam_group = QGroupBox("接缝修复")
        seam_layout = QHBoxLayout(seam_group)

        self.fix_seam_copy_btn = QPushButton("边界复制")
        self.fix_seam_copy_btn.setStyleSheet("background-color: #E91E63; color: white;")
        self.fix_seam_copy_btn.clicked.connect(self.fix_seams_boundary_copy)
        seam_layout.addWidget(self.fix_seam_copy_btn)

        self.fix_seam_linear_btn = QPushButton("线性修复")
        self.fix_seam_linear_btn.clicked.connect(self.fix_seams_linear)
        seam_layout.addWidget(self.fix_seam_linear_btn)

        basic_layout.addWidget(seam_group)

        display_group = QGroupBox("显示模式")
        display_layout = QHBoxLayout(display_group)

        self.display_combo = QComboBox()
        self.display_combo.addItems(["实体", "线框", "点", "实体+线框"])
        self.display_combo.currentIndexChanged.connect(self.change_display_mode)
        display_layout.addWidget(self.display_combo)

        basic_layout.addWidget(display_group)

        export_group = QGroupBox("导出")
        export_layout = QHBoxLayout(export_group)

        self.export_btn = QPushButton("导出带纹理模型")
        self.export_btn.clicked.connect(self.export_model)
        self.export_btn.setMinimumHeight(40)
        self.export_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        export_layout.addWidget(self.export_btn)

        basic_layout.addWidget(export_group)

        basic_layout.addStretch()
        self.control_tab.addTab(basic_widget, "基础")

    def create_multi_texture_tab(self):
        multi_widget = QWidget()
        multi_layout = QVBoxLayout(multi_widget)
        multi_layout.setContentsMargins(10, 10, 10, 10)
        multi_layout.setSpacing(8)

        tex_list_group = QGroupBox("纹理列表")
        tex_list_layout = QVBoxLayout(tex_list_group)

        self.texture_list = QListWidget()
        self.texture_list.setMaximumHeight(100)
        tex_list_layout.addWidget(self.texture_list)

        tex_btns = QHBoxLayout()
        self.add_tex_btn = QPushButton("添加纹理")
        self.add_tex_btn.clicked.connect(self.add_multi_texture)
        tex_btns.addWidget(self.add_tex_btn)

        self.remove_tex_btn = QPushButton("移除")
        self.remove_tex_btn.clicked.connect(self.remove_multi_texture)
        tex_btns.addWidget(self.remove_tex_btn)

        tex_list_layout.addLayout(tex_btns)
        multi_layout.addWidget(tex_list_group)

        select_group = QGroupBox("区域选择")
        select_layout = QVBoxLayout(select_group)

        self.select_by_verts_btn = QPushButton("按选中顶点分配")
        self.select_by_verts_btn.clicked.connect(self.assign_texture_by_selected_vertices)
        select_layout.addWidget(self.select_by_verts_btn)

        normal_layout = QHBoxLayout()
        normal_layout.addWidget(QLabel("按法线方向:"))
        self.normal_dir_combo = QComboBox()
        self.normal_dir_combo.addItems(["+X", "-X", "+Y", "-Y", "+Z", "-Z"])
        normal_layout.addWidget(self.normal_dir_combo)
        select_layout.addLayout(normal_layout)

        self.select_by_normal_btn = QPushButton("按法线方向分配")
        self.select_by_normal_btn.clicked.connect(self.assign_texture_by_normal)
        select_layout.addWidget(self.select_by_normal_btn)

        multi_layout.addWidget(select_group)

        blend_group = QGroupBox("混合设置")
        blend_layout = QHBoxLayout(blend_group)
        blend_layout.addWidget(QLabel("混合宽度:"))
        self.blend_width_slider = QSlider(Qt.Horizontal)
        self.blend_width_slider.setRange(1, 20)
        self.blend_width_slider.setValue(5)
        blend_layout.addWidget(self.blend_width_slider)
        multi_layout.addWidget(blend_group)

        self.blend_textures_btn = QPushButton("混合纹理")
        self.blend_textures_btn.setStyleSheet("background-color: #9C27B0; color: white; font-weight: bold;")
        self.blend_textures_btn.clicked.connect(self.blend_all_textures)
        self.blend_textures_btn.setMinimumHeight(35)
        multi_layout.addWidget(self.blend_textures_btn)

        multi_layout.addStretch()
        self.control_tab.addTab(multi_widget, "多纹理混合")

    def create_baking_tab(self):
        baking_widget = QWidget()
        baking_layout = QVBoxLayout(baking_widget)
        baking_layout.setContentsMargins(10, 10, 10, 10)
        baking_layout.setSpacing(8)

        size_group = QGroupBox("烘焙尺寸")
        size_layout = QHBoxLayout(size_group)
        size_layout.addWidget(QLabel("分辨率:"))
        self.bake_size_combo = QComboBox()
        self.bake_size_combo.addItems(["512", "1024", "2048", "4096"])
        self.bake_size_combo.setCurrentIndex(1)
        size_layout.addWidget(self.bake_size_combo)
        baking_layout.addWidget(size_group)

        maps_group = QGroupBox("贴图类型")
        maps_layout = QVBoxLayout(maps_group)

        self.bake_normal_cb = QCheckBox("法线贴图 (Normal)")
        self.bake_normal_cb.setChecked(True)
        maps_layout.addWidget(self.bake_normal_cb)

        self.bake_specular_cb = QCheckBox("高光贴图 (Specular)")
        self.bake_specular_cb.setChecked(True)
        maps_layout.addWidget(self.bake_specular_cb)

        self.bake_roughness_cb = QCheckBox("粗糙度贴图 (Roughness)")
        self.bake_roughness_cb.setChecked(True)
        maps_layout.addWidget(self.bake_roughness_cb)

        self.bake_ao_cb = QCheckBox("环境光遮蔽 (AO)")
        self.bake_ao_cb.setChecked(True)
        maps_layout.addWidget(self.bake_ao_cb)

        baking_layout.addWidget(maps_group)

        params_group = QGroupBox("参数设置")
        params_layout = QGridLayout(params_group)

        params_layout.addWidget(QLabel("高光强度:"), 0, 0)
        self.shininess_slider = QSlider(Qt.Horizontal)
        self.shininess_slider.setRange(1, 100)
        self.shininess_slider.setValue(50)
        params_layout.addWidget(self.shininess_slider, 0, 1)

        params_layout.addWidget(QLabel("基础粗糙度:"), 1, 0)
        self.roughness_slider = QSlider(Qt.Horizontal)
        self.roughness_slider.setRange(0, 100)
        self.roughness_slider.setValue(30)
        params_layout.addWidget(self.roughness_slider, 1, 1)

        baking_layout.addWidget(params_group)

        self.bake_all_btn = QPushButton("烘焙所有贴图")
        self.bake_all_btn.setStyleSheet("background-color: #FF5722; color: white; font-weight: bold;")
        self.bake_all_btn.clicked.connect(self.bake_all_maps)
        self.bake_all_btn.setMinimumHeight(35)
        baking_layout.addWidget(self.bake_all_btn)

        self.preview_map_combo = QComboBox()
        self.preview_map_combo.addItems(["查看: 漫反射", "查看: 法线", "查看: 高光", "查看: 粗糙度", "查看: AO"])
        self.preview_map_combo.currentIndexChanged.connect(self.preview_baked_map)
        baking_layout.addWidget(self.preview_map_combo)

        baking_layout.addStretch()
        self.control_tab.addTab(baking_widget, "纹理烘焙")

    def create_style_tab(self):
        style_widget = QWidget()
        style_layout = QVBoxLayout(style_widget)
        style_layout.setContentsMargins(10, 10, 10, 10)
        style_layout.setSpacing(8)

        ref_group = QGroupBox("风格参考图")
        ref_layout = QVBoxLayout(ref_group)

        self.load_style_btn = QPushButton("加载风格参考图")
        self.load_style_btn.clicked.connect(self.load_style_reference)
        ref_layout.addWidget(self.load_style_btn)

        self.style_preview_label = QLabel("未加载参考图")
        self.style_preview_label.setAlignment(Qt.AlignCenter)
        self.style_preview_label.setMinimumHeight(100)
        self.style_preview_label.setStyleSheet("border: 1px solid #666;")
        ref_layout.addWidget(self.style_preview_label)

        style_layout.addWidget(ref_group)

        method_group = QGroupBox("风格迁移方法")
        method_layout = QVBoxLayout(method_group)

        self.style_method_combo = QComboBox()
        self.style_method_combo.addItems(["直方图匹配", "颜色迁移"])
        method_layout.addWidget(self.style_method_combo)

        style_layout.addWidget(method_group)

        adjust_group = QGroupBox("风格调整")
        adjust_layout = QGridLayout(adjust_group)

        adjust_layout.addWidget(QLabel("亮度:"), 0, 0)
        self.brightness_slider = QSlider(Qt.Horizontal)
        self.brightness_slider.setRange(-100, 100)
        self.brightness_slider.setValue(0)
        adjust_layout.addWidget(self.brightness_slider, 0, 1)

        adjust_layout.addWidget(QLabel("对比度:"), 1, 0)
        self.contrast_slider = QSlider(Qt.Horizontal)
        self.contrast_slider.setRange(-100, 100)
        self.contrast_slider.setValue(0)
        adjust_layout.addWidget(self.contrast_slider, 1, 1)

        adjust_layout.addWidget(QLabel("噪点强度:"), 2, 0)
        self.noise_slider = QSlider(Qt.Horizontal)
        self.noise_slider.setRange(0, 50)
        self.noise_slider.setValue(0)
        adjust_layout.addWidget(self.noise_slider, 2, 1)

        style_layout.addWidget(adjust_group)

        self.apply_style_btn = QPushButton("应用风格迁移")
        self.apply_style_btn.setStyleSheet("background-color: #00BCD4; color: white; font-weight: bold;")
        self.apply_style_btn.clicked.connect(self.apply_style_transfer)
        self.apply_style_btn.setMinimumHeight(35)
        style_layout.addWidget(self.apply_style_btn)

        self.apply_adjust_btn = QPushButton("应用调整")
        self.apply_adjust_btn.clicked.connect(self.apply_style_adjustments)
        style_layout.addWidget(self.apply_adjust_btn)

        style_layout.addStretch()
        self.control_tab.addTab(style_widget, "风格迁移")

    def connect_signals(self):
        self.uv_editor.vertices_selected.connect(self.on_uv_vertices_selected)
        self.uv_editor.vertices_highlighted.connect(self.on_uv_vertices_highlighted)
        self.viewer_3d.vertices_selected.connect(self.on_3d_vertices_selected)

    def create_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("文件")

        load_mesh_action = QAction("加载OBJ模型", self)
        load_mesh_action.setShortcut("Ctrl+O")
        load_mesh_action.triggered.connect(self.load_mesh)
        file_menu.addAction(load_mesh_action)

        load_tex_action = QAction("加载纹理", self)
        load_tex_action.triggered.connect(self.load_texture)
        file_menu.addAction(load_tex_action)

        file_menu.addSeparator()

        export_action = QAction("导出带纹理模型", self)
        export_action.setShortcut("Ctrl+S")
        export_action.triggered.connect(self.export_model)
        file_menu.addAction(export_action)

        file_menu.addSeparator()

        exit_action = QAction("退出", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        edit_menu = menubar.addMenu("编辑")

        unwrap_action = QAction("执行UV展开", self)
        unwrap_action.triggered.connect(self.unwrap_uv)
        edit_menu.addAction(unwrap_action)

        edit_menu.addSeparator()

        toggle_sel_action = QAction("切换选择模式", self)
        toggle_sel_action.triggered.connect(self.toggle_selection_mode)
        edit_menu.addAction(toggle_sel_action)

        help_menu = menubar.addMenu("帮助")

        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def create_toolbar(self):
        toolbar = QToolBar("主工具栏")
        toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(toolbar)

        load_action = QAction("加载模型", self)
        load_action.triggered.connect(self.load_mesh)
        toolbar.addAction(load_action)

        toolbar.addSeparator()

        unwrap_action = QAction("UV展开", self)
        unwrap_action.triggered.connect(self.unwrap_uv)
        toolbar.addAction(unwrap_action)

        toolbar.addSeparator()

        sel_mode_action = QAction("选择模式", self)
        sel_mode_action.setCheckable(True)
        sel_mode_action.triggered.connect(self.toggle_selection_mode)
        toolbar.addAction(sel_mode_action)

        toolbar.addSeparator()

        bake_action = QAction("烘焙贴图", self)
        bake_action.triggered.connect(self.bake_all_maps)
        toolbar.addAction(bake_action)

        toolbar.addSeparator()

        export_action = QAction("导出", self)
        export_action.triggered.connect(self.export_model)
        toolbar.addAction(export_action)

    def create_sample_model(self):
        self.status_bar.showMessage("正在创建示例模型...")
        mesh = trimesh.creation.icosphere(subdivisions=3, radius=1.0)
        self.set_mesh(mesh)
        self.status_bar.showMessage("已加载示例球体模型")

    def load_mesh(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择OBJ模型", "", "OBJ Files (*.obj)")
        if file_path:
            try:
                self.status_bar.showMessage(f"正在加载: {os.path.basename(file_path)}...")
                mesh = trimesh.load(file_path)
                if isinstance(mesh, trimesh.Scene):
                    mesh = mesh.to_mesh()
                self.set_mesh(mesh)
                self.status_bar.showMessage(f"已加载: {os.path.basename(file_path)}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"加载模型失败: {str(e)}")

    def set_mesh(self, mesh):
        self.mesh = mesh
        self.uv = None
        self.texture = None
        self.unwrapper = UVUnwrapper(mesh)
        self.mapper = None
        self.blender = None
        self.baker = None
        self.baked_maps = {}
        self.viewer_3d.set_mesh(mesh)
        self.viewer_3d.set_uv(None)
        self.viewer_3d.set_texture(None)
        self.uv_editor.set_uv(None, None)
        self.uv_editor.set_texture(None)
        self.texture_list.clear()

    def load_texture(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择纹理图像", "",
                                                    "Image Files (*.png *.jpg *.jpeg *.bmp *.tiff)")
        if file_path:
            try:
                texture = cv2.imread(file_path)
                texture = cv2.cvtColor(texture, cv2.COLOR_BGR2RGB)
                self.set_texture(texture)
                self.status_bar.showMessage(f"已加载纹理: {os.path.basename(file_path)}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"加载纹理失败: {str(e)}")

    def set_texture(self, texture):
        self.texture = texture
        self.viewer_3d.set_texture(texture)
        self.uv_editor.set_texture(texture)
        if self.mapper is not None:
            self.mapper.texture = texture
        if self.blender is not None:
            self.blender.base_texture = texture

    def create_procedural_texture(self, tex_type):
        if self.mapper is None and self.uv is not None:
            self.mapper = TextureMapper(self.mesh, self.uv)
        elif self.mapper is None:
            QMessageBox.warning(self, "提示", "请先执行UV展开")
            return

        if tex_type == 'checker':
            texture = self.mapper.create_checkerboard_texture(size=1024, square_size=64)
        elif tex_type == 'gradient':
            texture = self.mapper.create_gradient_texture(size=1024)

        self.set_texture(texture)
        self.status_bar.showMessage(f"已创建{tex_type}纹理")

    def unwrap_uv(self):
        if self.mesh is None:
            QMessageBox.warning(self, "提示", "请先加载模型")
            return

        method_idx = self.method_combo.currentIndex()
        method = 'abf++' if method_idx == 0 else 'lscm'
        method_name = self.method_combo.currentText()

        try:
            self.status_bar.showMessage(f"正在执行UV展开 ({method_name})...")
            QApplication.processEvents()

            self.uv = self.unwrapper.unwrap(method=method)

            if self.mapper is None:
                self.mapper = TextureMapper(self.mesh, self.uv)
            else:
                self.mapper.uv = self.uv

            self.blender = MultiTextureBlender(self.mesh, self.uv)
            self.baker = TextureBaker(self.mesh, self.uv)

            self.uv_editor.set_uv(self.uv, self.mesh.faces)
            self.viewer_3d.set_uv(self.uv)

            if self.texture is None:
                self.create_procedural_texture('checker')

            self.status_bar.showMessage(f"UV展开完成 ({method_name})")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"UV展开失败: {str(e)}")
            import traceback
            traceback.print_exc()

    def apply_uv_changes(self):
        if self.uv_editor.uv is not None:
            self.uv = self.uv_editor.get_uv()
            self.viewer_3d.set_uv(self.uv)
            if self.mapper is not None:
                self.mapper.uv = self.uv
            if self.blender is not None:
                self.blender.uv = self.uv
            if self.baker is not None:
                self.baker.uv = self.uv
            self.status_bar.showMessage("UV更改已应用到3D视图")

    def pack_uv(self):
        self.uv_editor.pack_uv(padding=0.02)
        self.apply_uv_changes()
        self.status_bar.showMessage("UV打包完成")

    def toggle_selection_mode(self):
        is_selected = self.selection_mode_btn.isChecked()
        self.viewer_3d.set_selection_mode(is_selected)

        if is_selected:
            self.selection_mode_btn.setText("选择模式: 开启")
            self.selection_mode_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 8px 15px;")
            self.view_info.setText("3D视图 | 选择模式 | 左键选择顶点 | 中键平移 | 滚轮缩放")
        else:
            self.selection_mode_btn.setText("选择模式: 关闭")
            self.selection_mode_btn.setStyleSheet("background-color: #666; color: white; padding: 8px 15px;")
            self.view_info.setText("3D视图 | 左键旋转 | 中键平移 | 滚轮缩放")

    def sync_selection(self):
        self.viewer_3d.set_highlighted_vertices(self.uv_editor.selected_vertices)
        self.status_bar.showMessage(f"已同步选择 {len(self.uv_editor.selected_vertices)} 个顶点")

    def clear_all_selections(self):
        self.uv_editor.clear_selection()
        self.viewer_3d.clear_selection()
        self.status_bar.showMessage("已清除所有选择")

    def on_uv_vertices_selected(self, vertices):
        self.viewer_3d.set_highlighted_vertices(vertices)
        if len(vertices) > 0:
            self.status_bar.showMessage(f"已选择 {len(vertices)} 个顶点")

    def on_uv_vertices_highlighted(self, vertices):
        self.viewer_3d.set_highlighted_vertices(vertices)

    def on_3d_vertices_selected(self, vertices):
        self.uv_editor.set_selected_vertices(vertices)
        if len(vertices) > 0:
            self.status_bar.showMessage(f"3D视图中选择了 {len(vertices)} 个顶点")

    def add_multi_texture(self):
        if self.blender is None:
            QMessageBox.warning(self, "提示", "请先执行UV展开")
            return

        file_path, _ = QFileDialog.getOpenFileName(self, "选择纹理图像", "",
                                                    "Image Files (*.png *.jpg *.jpeg *.bmp *.tiff)")
        if file_path:
            name = os.path.splitext(os.path.basename(file_path))[0]
            self.blender.add_texture(name, file_path)
            self.texture_list.addItem(name)
            self.status_bar.showMessage(f"已添加纹理: {name}")

    def remove_multi_texture(self):
        if self.blender is None:
            return

        current_item = self.texture_list.currentItem()
        if current_item:
            name = current_item.text()
            self.blender.remove_texture(name)
            self.texture_list.takeItem(self.texture_list.row(current_item))
            self.status_bar.showMessage(f"已移除纹理: {name}")

    def assign_texture_by_selected_vertices(self):
        if self.blender is None:
            QMessageBox.warning(self, "提示", "请先执行UV展开")
            return

        current_item = self.texture_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "提示", "请先选择一个纹理")
            return

        selected_vertices = self.uv_editor.selected_vertices
        if not selected_vertices:
            QMessageBox.warning(self, "提示", "请先在3D视图或UV编辑器中选择顶点")
            return

        name = current_item.text()
        face_indices = self.blender.select_faces_by_vertices(selected_vertices)
        blend_width = self.blend_width_slider.value()
        self.blender.assign_region(face_indices, name, blend_width)
        self.status_bar.showMessage(f"已分配纹理 {name} 到 {len(face_indices)} 个面")

    def assign_texture_by_normal(self):
        if self.blender is None:
            QMessageBox.warning(self, "提示", "请先执行UV展开")
            return

        current_item = self.texture_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "提示", "请先选择一个纹理")
            return

        dirs = {
            0: np.array([1, 0, 0]),
            1: np.array([-1, 0, 0]),
            2: np.array([0, 1, 0]),
            3: np.array([0, -1, 0]),
            4: np.array([0, 0, 1]),
            5: np.array([0, 0, -1]),
        }
        direction = dirs[self.normal_dir_combo.currentIndex()]

        name = current_item.text()
        face_indices = self.blender.select_faces_by_normal(direction, threshold=0.5)
        blend_width = self.blend_width_slider.value()
        self.blender.assign_region(face_indices, name, blend_width)
        self.status_bar.showMessage(f"已分配纹理 {name} 到 {len(face_indices)} 个面")

    def blend_all_textures(self):
        if self.blender is None or not self.blender.textures:
            QMessageBox.warning(self, "提示", "请先添加纹理并分配区域")
            return

        try:
            self.status_bar.showMessage("正在混合纹理...")
            QApplication.processEvents()

            size = 1024
            blended = self.blender.blend_textures(size)
            if blended is not None:
                self.set_texture(blended)
                self.status_bar.showMessage("纹理混合完成")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"纹理混合失败: {str(e)}")

    def bake_all_maps(self):
        if self.baker is None:
            QMessageBox.warning(self, "提示", "请先执行UV展开")
            return

        if self.texture is None:
            QMessageBox.warning(self, "提示", "请先加载纹理")
            return

        try:
            self.status_bar.showMessage("正在烘焙纹理贴图...")
            QApplication.processEvents()

            size = int(self.bake_size_combo.currentText())
            shininess = self.shininess_slider.value() / 100.0
            roughness = self.roughness_slider.value() / 100.0

            self.baked_maps = {}

            if self.bake_normal_cb.isChecked():
                self.status_bar.showMessage("烘焙法线贴图...")
                QApplication.processEvents()
                self.baked_maps['normal'] = self.baker.generate_normal_map(size)

            if self.bake_specular_cb.isChecked():
                self.status_bar.showMessage("烘焙高光贴图...")
                QApplication.processEvents()
                self.baked_maps['specular'] = self.baker.generate_specular_map(
                    self.texture, size, shininess
                )

            if self.bake_roughness_cb.isChecked():
                self.status_bar.showMessage("烘焙粗糙度贴图...")
                QApplication.processEvents()
                self.baked_maps['roughness'] = self.baker.generate_roughness_map(
                    self.texture, size, roughness
                )

            if self.bake_ao_cb.isChecked():
                self.status_bar.showMessage("烘焙AO贴图...")
                QApplication.processEvents()
                self.baked_maps['ao'] = self.baker.generate_ao_map(size // 2)
                self.baked_maps['ao'] = cv2.resize(self.baked_maps['ao'], (size, size))

            self.status_bar.showMessage(f"贴图烘焙完成，共生成 {len(self.baked_maps)} 张贴图")
            QMessageBox.information(self, "成功", f"已烘焙 {len(self.baked_maps)} 张贴图")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"烘焙失败: {str(e)}")
            import traceback
            traceback.print_exc()

    def preview_baked_map(self, index):
        if not self.baked_maps:
            return

        map_names = ['diffuse', 'normal', 'specular', 'roughness', 'ao']
        map_name = map_names[index]

        if map_name == 'diffuse':
            if self.texture is not None:
                self.set_texture(self.texture)
        elif map_name in self.baked_maps:
            self.viewer_3d.set_texture(self.baked_maps[map_name])
            self.uv_editor.set_texture(self.baked_maps[map_name])
            self.status_bar.showMessage(f"预览: {map_name} 贴图")

    def load_style_reference(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择风格参考图", "",
                                                    "Image Files (*.png *.jpg *.jpeg *.bmp *.tiff)")
        if file_path:
            try:
                self.style_reference = cv2.imread(file_path)
                self.style_reference = cv2.cvtColor(self.style_reference, cv2.COLOR_BGR2RGB)

                h, w = self.style_reference.shape[:2]
                max_size = 150
                if h > max_size or w > max_size:
                    scale = max_size / max(h, w)
                    preview = cv2.resize(self.style_reference, (int(w * scale), int(h * scale)))
                else:
                    preview = self.style_reference

                h, w = preview.shape[:2]
                qimg = QImage(preview.data, w, h, 3 * w, QImage.Format_RGB888)
                pixmap = QPixmap.fromImage(qimg)
                self.style_preview_label.setPixmap(pixmap)
                self.status_bar.showMessage(f"已加载风格参考图: {os.path.basename(file_path)}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"加载参考图失败: {str(e)}")

    def apply_style_transfer(self):
        if self.style_reference is None:
            QMessageBox.warning(self, "提示", "请先加载风格参考图")
            return

        if self.texture is None:
            QMessageBox.warning(self, "提示", "请先加载纹理")
            return

        try:
            self.status_bar.showMessage("正在应用风格迁移...")
            QApplication.processEvents()

            method = 'histogram' if self.style_method_combo.currentIndex() == 0 else 'color'
            styled = self.stylizer.stylize_texture(self.texture, self.style_reference, method)
            self.set_texture(styled)
            self.status_bar.showMessage("风格迁移完成")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"风格迁移失败: {str(e)}")

    def apply_style_adjustments(self):
        if self.texture is None:
            QMessageBox.warning(self, "提示", "请先加载纹理")
            return

        try:
            brightness = self.brightness_slider.value()
            contrast = self.contrast_slider.value()
            noise = self.noise_slider.value() / 100.0

            result = self.stylizer.adjust_brightness_contrast(self.texture, brightness, contrast)
            if noise > 0:
                result = self.stylizer.add_noise_style(result, noise)

            self.set_texture(result)
            self.status_bar.showMessage("风格调整已应用")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"调整失败: {str(e)}")

    def fix_seams_boundary_copy(self):
        if self.mapper is None or self.texture is None:
            QMessageBox.warning(self, "提示", "请先加载纹理并执行UV展开")
            return

        try:
            self.status_bar.showMessage("正在执行边界复制接缝修复...")
            QApplication.processEvents()

            fixed_texture = self.mapper.fix_seams_boundary_copy(blend_width=3)
            self.set_texture(fixed_texture)
            self.status_bar.showMessage("边界复制接缝修复完成")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"接缝修复失败: {str(e)}")

    def fix_seams_linear(self):
        if self.mapper is None or self.texture is None:
            QMessageBox.warning(self, "提示", "请先加载纹理并执行UV展开")
            return

        try:
            self.status_bar.showMessage("正在执行线性接缝修复...")
            QApplication.processEvents()

            fixed_texture = self.mapper.fix_seams_linear(blend_width=3)
            self.set_texture(fixed_texture)
            self.status_bar.showMessage("线性接缝修复完成")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"接缝修复失败: {str(e)}")

    def change_display_mode(self, index):
        modes = ['solid', 'wireframe', 'points', 'solid']
        mode = modes[index]
        self.viewer_3d.set_display_mode(mode)
        self.viewer_3d.toggle_wireframe(index == 3)

    def export_model(self):
        if self.mesh is None or self.uv is None:
            QMessageBox.warning(self, "提示", "请先加载模型并执行UV展开")
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "导出带纹理模型", "", "OBJ Files (*.obj)")
        if file_path:
            try:
                self.status_bar.showMessage("正在导出...")
                QApplication.processEvents()

                export_maps = self.baked_maps if self.baked_maps else None
                export_textured_mesh(self.mesh, self.uv, self.texture, file_path, export_maps)
                self.status_bar.showMessage(f"已导出到: {file_path}")

                msg = f"模型已成功导出到:\n{file_path}\n\n"
                if self.baked_maps:
                    msg += f"导出的贴图: {', '.join(self.baked_maps.keys())}"
                QMessageBox.information(self, "成功", msg)
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")
                import traceback
                traceback.print_exc()

    def show_about(self):
        QMessageBox.about(self, "关于",
                          "纹理映射工具 v3.0\n\n"
                          "核心功能:\n"
                          "- OBJ模型加载与3D可视化\n"
                          "- UV展开 (ABF++ / LSCM)\n"
                          "- 交互式UV坐标编辑\n"
                          "- 3D-UV双向顶点高亮联动\n"
                          "- 多纹理区域混合\n"
                          "- 纹理烘焙: 法线/高光/粗糙度/AO\n"
                          "- 风格迁移与风格调整\n"
                          "- 纹理接缝修复\n"
                          "- 带纹理模型导出\n\n"
                          "技术栈:\n"
                          "Python + PyQt5 + OpenGL + NumPy + Trimesh + OpenCV")


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    window = TextureMappingApp()
    window.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
