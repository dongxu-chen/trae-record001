import sys
import numpy as np
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QSpinBox, QComboBox, QFileDialog,
    QGroupBox, QFormLayout, QMessageBox, QSplitter, QCheckBox,
    QSlider, QDoubleSpinBox, QTabWidget
)
from PyQt5.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from matplotlib import cm

import openmesh as om
from subdivision import (LoopSubdivision, CatmullClarkSubdivision,
                         MeshUtils, ViewDependentSubdivision,
                         MultiResolutionMesh)


class MeshViewer(FigureCanvas):
    def __init__(self, parent=None):
        self.fig = Figure(figsize=(8, 6), dpi=100)
        self.ax = self.fig.add_subplot(111, projection='3d')
        super().__init__(self.fig)
        self.setParent(parent)

        self.mesh = None
        self.uv_coords = None
        self.show_wireframe = True
        self.show_solid = True
        self.show_normals = False
        self.show_uv = False
        self.camera_position = np.array([0, 0, 5])

    def set_mesh(self, mesh, uv_coords=None):
        self.mesh = mesh
        self.uv_coords = uv_coords
        self.update_plot()

    def update_plot(self):
        self.ax.clear()

        if self.mesh is None:
            self.ax.text(0.5, 0.5, 0.5, 'No mesh loaded',
                         ha='center', va='center', transform=self.ax.transAxes)
            self.draw()
            return

        vertices = np.array([self.mesh.point(vh) for vh in self.mesh.vertices()])

        faces = []
        face_indices = []
        for fh in self.mesh.faces():
            face = []
            for vh in self.mesh.fv(fh):
                face.append(vertices[vh.idx()])
            faces.append(face)
            face_indices.append([vh.idx() for vh in self.mesh.fv(fh)])

        facecolors = None
        if self.show_uv and self.uv_coords is not None and len(self.uv_coords) == len(vertices):
            try:
                u = self.uv_coords[:, 0]
                v = self.uv_coords[:, 1]
                colors = cm.viridis((u + v) * 0.5 % 1.0)

                facecolors = []
                for face_idx in face_indices:
                    face_color = colors[face_idx].mean(axis=0)
                    facecolors.append(face_color)
            except Exception:
                facecolors = None

        if self.show_solid and faces:
            if facecolors is not None:
                poly = Poly3DCollection(faces, alpha=0.7, facecolors=facecolors,
                                        edgecolor='none' if not self.show_wireframe else 'gray')
            else:
                poly = Poly3DCollection(faces, alpha=0.7, facecolor='lightblue',
                                        edgecolor='none' if not self.show_wireframe else 'gray')
            self.ax.add_collection3d(poly)

        if self.show_wireframe and not self.show_solid:
            for face in faces:
                face_np = np.array(face)
                self.ax.plot(face_np[:, 0], face_np[:, 1], face_np[:, 2],
                             color='gray', linewidth=0.5)

        if self.show_normals:
            normals = MeshUtils.compute_vertex_normals(self.mesh)
            for i, v in enumerate(vertices):
                n = normals[i] * 0.1
                self.ax.quiver(v[0], v[1], v[2], n[0], n[1], n[2],
                               color='red', linewidth=1, length=0.1)

        self.ax.scatter(vertices[:, 0], vertices[:, 1], vertices[:, 2],
                        color='darkblue', s=5, alpha=0.5)

        self.ax.set_xlabel('X')
        self.ax.set_ylabel('Y')
        self.ax.set_zlabel('Z')

        max_range = np.array([vertices[:, 0].max() - vertices[:, 0].min(),
                              vertices[:, 1].max() - vertices[:, 1].min(),
                              vertices[:, 2].max() - vertices[:, 2].min()]).max() / 2.0
        max_range = max(max_range, 0.1)

        mid_x = (vertices[:, 0].max() + vertices[:, 0].min()) * 0.5
        mid_y = (vertices[:, 1].max() + vertices[:, 1].min()) * 0.5
        mid_z = (vertices[:, 2].max() + vertices[:, 2].min()) * 0.5

        self.ax.set_xlim(mid_x - max_range, mid_x + max_range)
        self.ax.set_ylim(mid_y - max_range, mid_y + max_range)
        self.ax.set_zlim(mid_z - max_range, mid_z + max_range)

        self.ax.set_box_aspect([1, 1, 1])
        self.fig.tight_layout()
        self.draw()

    def toggle_wireframe(self, checked):
        self.show_wireframe = checked
        self.update_plot()

    def toggle_solid(self, checked):
        self.show_solid = checked
        self.update_plot()

    def toggle_normals(self, checked):
        self.show_normals = checked
        self.update_plot()

    def toggle_uv(self, checked):
        self.show_uv = checked
        self.update_plot()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Mesh Subdivision Tool')
        self.setGeometry(100, 100, 1400, 900)

        self.original_mesh = None
        self.original_uv = None
        self.current_mesh = None
        self.current_uv = None
        self.subdivision_level = 0
        self.max_subdivision_level = 4
        self.multi_res = None

        self.init_ui()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)

        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        control_panel = self.create_control_panel()
        splitter.addWidget(control_panel)

        self.viewer = MeshViewer()
        splitter.addWidget(self.viewer)

        splitter.setSizes([350, 1050])

    def create_control_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)

        tabs = QTabWidget()
        layout.addWidget(tabs)

        basic_tab = self._create_basic_tab()
        tabs.addTab(basic_tab, "Basic")

        advanced_tab = self._create_advanced_tab()
        tabs.addTab(advanced_tab, "Advanced")

        multires_tab = self._create_multires_tab()
        tabs.addTab(multires_tab, "Multi-Res")

        view_group = QGroupBox('View Options')
        view_layout = QVBoxLayout(view_group)

        self.wireframe_check = QCheckBox('Show Wireframe')
        self.wireframe_check.setChecked(True)
        self.wireframe_check.toggled.connect(self.viewer.toggle_wireframe)
        view_layout.addWidget(self.wireframe_check)

        self.solid_check = QCheckBox('Show Solid')
        self.solid_check.setChecked(True)
        self.solid_check.toggled.connect(self.viewer.toggle_solid)
        view_layout.addWidget(self.solid_check)

        self.normals_check = QCheckBox('Show Normals')
        self.normals_check.setChecked(False)
        self.normals_check.toggled.connect(self.viewer.toggle_normals)
        view_layout.addWidget(self.normals_check)

        self.uv_check = QCheckBox('Show UV Coloring')
        self.uv_check.setChecked(False)
        self.uv_check.toggled.connect(self.viewer.toggle_uv)
        view_layout.addWidget(self.uv_check)

        layout.addWidget(view_group)

        info_group = QGroupBox('Mesh Info')
        self.info_label = QLabel('No mesh loaded')
        info_layout = QVBoxLayout(info_group)
        info_layout.addWidget(self.info_label)
        layout.addWidget(info_group)

        return panel

    def _create_basic_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        file_group = QGroupBox('File Operations')
        file_layout = QFormLayout(file_group)

        self.load_btn = QPushButton('Load Mesh')
        self.load_btn.clicked.connect(self.load_mesh)
        file_layout.addRow(self.load_btn)

        self.load_uv_btn = QPushButton('Load Mesh + UV')
        self.load_uv_btn.clicked.connect(self.load_mesh_with_uv)
        file_layout.addRow(self.load_uv_btn)

        self.export_btn = QPushButton('Export Mesh')
        self.export_btn.clicked.connect(self.export_mesh)
        self.export_btn.setEnabled(False)
        file_layout.addRow(self.export_btn)

        layout.addWidget(file_group)

        primitive_group = QGroupBox('Primitive Meshes')
        primitive_layout = QVBoxLayout(primitive_group)

        self.tetra_btn = QPushButton('Create Tetrahedron')
        self.tetra_btn.clicked.connect(lambda: self.create_primitive('tetrahedron'))
        primitive_layout.addWidget(self.tetra_btn)

        self.cube_btn = QPushButton('Create Cube')
        self.cube_btn.clicked.connect(lambda: self.create_primitive('cube'))
        primitive_layout.addWidget(self.cube_btn)

        self.octa_btn = QPushButton('Create Octahedron')
        self.octa_btn.clicked.connect(lambda: self.create_primitive('octahedron'))
        primitive_layout.addWidget(self.octa_btn)

        layout.addWidget(primitive_group)

        subdiv_group = QGroupBox('Subdivision')
        subdiv_layout = QFormLayout(subdiv_group)

        self.algorithm_combo = QComboBox()
        self.algorithm_combo.addItems(['Loop Subdivision', 'Catmull-Clark Subdivision'])
        subdiv_layout.addRow('Algorithm:', self.algorithm_combo)

        self.level_spin = QSpinBox()
        self.level_spin.setRange(0, self.max_subdivision_level)
        subdiv_layout.addRow('Level:', self.level_spin)

        self.subdiv_btn = QPushButton('Apply Subdivision')
        self.subdiv_btn.clicked.connect(self.apply_subdivision)
        self.subdiv_btn.setEnabled(False)
        subdiv_layout.addRow(self.subdiv_btn)

        self.reset_btn = QPushButton('Reset to Original')
        self.reset_btn.clicked.connect(self.reset_mesh)
        self.reset_btn.setEnabled(False)
        subdiv_layout.addRow(self.reset_btn)

        layout.addWidget(subdiv_group)
        layout.addStretch()

        return tab

    def _create_advanced_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        uv_group = QGroupBox('Texture Mapping')
        uv_layout = QFormLayout(uv_group)

        self.uv_method_combo = QComboBox()
        self.uv_method_combo.addItems(['Spherical', 'Planar', 'Cylindrical'])
        uv_layout.addRow('UV Method:', self.uv_method_combo)

        self.gen_uv_btn = QPushButton('Generate UV')
        self.gen_uv_btn.clicked.connect(self.generate_uv)
        self.gen_uv_btn.setEnabled(False)
        uv_layout.addRow(self.gen_uv_btn)

        layout.addWidget(uv_group)

        vd_group = QGroupBox('View-Dependent Subdivision')
        vd_layout = QFormLayout(vd_group)

        self.cam_x_spin = QDoubleSpinBox()
        self.cam_x_spin.setRange(-100, 100)
        self.cam_x_spin.setValue(0)
        vd_layout.addRow('Camera X:', self.cam_x_spin)

        self.cam_y_spin = QDoubleSpinBox()
        self.cam_y_spin.setRange(-100, 100)
        self.cam_y_spin.setValue(0)
        vd_layout.addRow('Camera Y:', self.cam_y_spin)

        self.cam_z_spin = QDoubleSpinBox()
        self.cam_z_spin.setRange(-100, 100)
        self.cam_z_spin.setValue(5)
        vd_layout.addRow('Camera Z:', self.cam_z_spin)

        self.near_spin = QDoubleSpinBox()
        self.near_spin.setRange(0.1, 100)
        self.near_spin.setValue(1.5)
        self.near_spin.setSingleStep(0.5)
        vd_layout.addRow('Near Threshold:', self.near_spin)

        self.far_spin = QDoubleSpinBox()
        self.far_spin.setRange(0.5, 200)
        self.far_spin.setValue(4.0)
        self.far_spin.setSingleStep(0.5)
        vd_layout.addRow('Far Threshold:', self.far_spin)

        self.vd_max_level_spin = QSpinBox()
        self.vd_max_level_spin.setRange(1, 5)
        self.vd_max_level_spin.setValue(3)
        vd_layout.addRow('Max Level:', self.vd_max_level_spin)

        self.vd_subdiv_btn = QPushButton('View-Dependent Subdivide')
        self.vd_subdiv_btn.clicked.connect(self.apply_view_dependent)
        self.vd_subdiv_btn.setEnabled(False)
        vd_layout.addRow(self.vd_subdiv_btn)

        layout.addWidget(vd_group)
        layout.addStretch()

        return tab

    def _create_multires_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        mr_group = QGroupBox('Multi-Resolution')
        mr_layout = QFormLayout(mr_group)

        self.mr_max_level_spin = QSpinBox()
        self.mr_max_level_spin.setRange(1, 5)
        self.mr_max_level_spin.setValue(4)
        mr_layout.addRow('Max Levels:', self.mr_max_level_spin)

        self.build_mr_btn = QPushButton('Build Multi-Res Hierarchy')
        self.build_mr_btn.clicked.connect(self.build_multires)
        self.build_mr_btn.setEnabled(False)
        mr_layout.addRow(self.build_mr_btn)

        self.mr_level_slider = QSlider(Qt.Horizontal)
        self.mr_level_slider.setRange(0, 4)
        self.mr_level_slider.setValue(0)
        self.mr_level_slider.setEnabled(False)
        self.mr_level_slider.valueChanged.connect(self.on_multires_level_changed)
        mr_layout.addRow('Level:', self.mr_level_slider)

        self.mr_level_label = QLabel('Level: 0')
        mr_layout.addRow(self.mr_level_label)

        refine_coarsen_layout = QHBoxLayout()
        self.coarsen_btn = QPushButton('<< Coarsen')
        self.coarsen_btn.clicked.connect(self.coarsen_mesh)
        self.coarsen_btn.setEnabled(False)
        refine_coarsen_layout.addWidget(self.coarsen_btn)

        self.refine_btn = QPushButton('Refine >>')
        self.refine_btn.clicked.connect(self.refine_mesh)
        self.refine_btn.setEnabled(False)
        refine_coarsen_layout.addWidget(self.refine_btn)

        mr_layout.addRow(refine_coarsen_layout)

        layout.addWidget(mr_group)

        interp_group = QGroupBox('Continuous Level')
        interp_layout = QFormLayout(interp_group)

        self.interp_slider = QSlider(Qt.Horizontal)
        self.interp_slider.setRange(0, 100)
        self.interp_slider.setValue(0)
        self.interp_slider.setEnabled(False)
        self.interp_slider.valueChanged.connect(self.on_interp_changed)
        interp_layout.addRow('Interpolation:', self.interp_slider)

        self.interp_label = QLabel('t = 0.00')
        interp_layout.addRow(self.interp_label)

        layout.addWidget(interp_group)
        layout.addStretch()

        return tab

    def load_mesh(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, 'Load Mesh', '',
            'Mesh Files (*.obj *.off *.ply);;All Files (*)'
        )
        if filepath:
            try:
                self.original_mesh = MeshUtils.import_mesh(filepath)
                self.original_uv = None
                self.current_mesh = self._copy_mesh(self.original_mesh)
                self.current_uv = None
                self.subdivision_level = 0
                self.level_spin.setValue(0)
                self.update_mesh_view()
                self.enable_controls(True)
            except Exception as e:
                QMessageBox.critical(self, 'Error', f'Failed to load mesh: {str(e)}')

    def load_mesh_with_uv(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, 'Load Mesh with UV', '',
            'OBJ Files (*.obj);;All Files (*)'
        )
        if filepath:
            try:
                mesh, uv = MeshUtils.import_obj_with_uv(filepath)
                self.original_mesh = mesh
                self.original_uv = uv
                self.current_mesh = self._copy_mesh(self.original_mesh)
                self.current_uv = uv.copy() if uv is not None else None
                self.subdivision_level = 0
                self.level_spin.setValue(0)
                self.update_mesh_view()
                self.enable_controls(True)
            except Exception as e:
                QMessageBox.critical(self, 'Error', f'Failed to load mesh: {str(e)}')

    def create_primitive(self, primitive_type):
        try:
            if primitive_type == 'tetrahedron':
                self.original_mesh, self.original_uv = MeshUtils.create_tetrahedron()
            elif primitive_type == 'cube':
                self.original_mesh, self.original_uv = MeshUtils.create_cube()
            elif primitive_type == 'octahedron':
                self.original_mesh, self.original_uv = MeshUtils.create_octahedron()

            self.current_mesh = self._copy_mesh(self.original_mesh)
            self.current_uv = self.original_uv.copy() if self.original_uv is not None else None
            self.subdivision_level = 0
            self.level_spin.setValue(0)
            self.update_mesh_view()
            self.enable_controls(True)
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Failed to create primitive: {str(e)}')

    def generate_uv(self):
        if self.current_mesh is None:
            return

        method = self.uv_method_combo.currentText()
        try:
            if method == 'Spherical':
                self.current_uv = MeshUtils.generate_spherical_uv(self.current_mesh)
            elif method == 'Planar':
                self.current_uv = MeshUtils.generate_planar_uv(self.current_mesh)
            elif method == 'Cylindrical':
                self.current_uv = MeshUtils.generate_cylindrical_uv(self.current_mesh)

            self.original_uv = self.current_uv.copy()
            self.viewer.set_mesh(self.current_mesh, self.current_uv)
            self.update_info()
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Failed to generate UV: {str(e)}')

    def _copy_mesh(self, mesh):
        if isinstance(mesh, om.TriMesh):
            new_mesh = om.TriMesh()
        else:
            new_mesh = om.PolyMesh()

        vertex_map = {}
        for vh in mesh.vertices():
            new_vh = new_mesh.add_vertex(mesh.point(vh))
            vertex_map[vh.idx()] = new_vh

        for fh in mesh.faces():
            face_vertices = [vertex_map[vh.idx()] for vh in mesh.fv(fh)]
            new_mesh.add_face(face_vertices)

        return new_mesh

    def apply_subdivision(self):
        if self.original_mesh is None:
            return

        target_level = self.level_spin.value()

        try:
            self.current_mesh = self._copy_mesh(self.original_mesh)

            if target_level > 0:
                algorithm = self.algorithm_combo.currentText()

                if algorithm == 'Loop Subdivision':
                    if not isinstance(self.current_mesh, om.TriMesh):
                        QMessageBox.warning(self, 'Warning',
                                            'Loop subdivision requires a triangular mesh. '
                                            'Converting to triangular mesh.')
                        self.current_mesh = self._to_triangular(self.current_mesh)
                        self.original_uv = None

                    subdiv = LoopSubdivision(self.current_mesh, self.original_uv)
                    self.current_mesh = subdiv.subdivide(target_level)
                    self.current_uv = subdiv.get_uv_coords()
                else:
                    subdiv = CatmullClarkSubdivision(self.current_mesh, self.original_uv)
                    self.current_mesh = subdiv.subdivide(target_level)
                    self.current_uv = subdiv.get_uv_coords()

            self.subdivision_level = target_level
            self.update_mesh_view()
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Subdivision failed: {str(e)}')

    def apply_view_dependent(self):
        if self.original_mesh is None:
            return

        try:
            camera_pos = np.array([self.cam_x_spin.value(),
                                   self.cam_y_spin.value(),
                                   self.cam_z_spin.value()])

            algorithm = 'loop' if self.algorithm_combo.currentText() == 'Loop Subdivision' else 'catmull_clark'

            vd = ViewDependentSubdivision(
                self._copy_mesh(self.original_mesh),
                camera_position=camera_pos,
                algorithm=algorithm,
                uv_coords=self.original_uv
            )
            vd.set_thresholds(self.near_spin.value(), self.far_spin.value())
            vd.max_level = self.vd_max_level_spin.value()

            self.current_mesh, self.current_uv = vd.subdivide_view_dependent()

            self.viewer.camera_position = camera_pos
            self.update_mesh_view()
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'View-dependent subdivision failed: {str(e)}')

    def build_multires(self):
        if self.original_mesh is None:
            return

        try:
            algorithm = 'loop' if self.algorithm_combo.currentText() == 'Loop Subdivision' else 'catmull_clark'
            max_levels = self.mr_max_level_spin.value()

            self.multi_res = MultiResolutionMesh(
                self._copy_mesh(self.original_mesh),
                algorithm=algorithm,
                max_levels=max_levels,
                uv_coords=self.original_uv
            )

            self.mr_level_slider.setRange(0, max_levels)
            self.mr_level_slider.setValue(0)
            self.mr_level_slider.setEnabled(True)
            self.interp_slider.setRange(0, max_levels * 100)
            self.interp_slider.setValue(0)
            self.interp_slider.setEnabled(True)

            self.coarsen_btn.setEnabled(True)
            self.refine_btn.setEnabled(True)

            mesh, uv = self.multi_res.get_current()
            self.current_mesh = mesh
            self.current_uv = uv
            self.subdivision_level = 0
            self.update_mesh_view()

            QMessageBox.information(self, 'Success',
                                    f'Multi-resolution hierarchy built ({max_levels + 1} levels)')
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Failed to build multi-res: {str(e)}')

    def on_multires_level_changed(self, value):
        if self.multi_res is None:
            return

        self.multi_res.set_current_level(value)
        mesh, uv = self.multi_res.get_current()
        self.current_mesh = mesh
        self.current_uv = uv
        self.subdivision_level = value
        self.mr_level_label.setText(f'Level: {value}')
        self.update_mesh_view()

    def on_interp_changed(self, value):
        if self.multi_res is None:
            return

        t = value / (self.multi_res.max_levels * 100)
        self.interp_label.setText(f't = {t:.2f}')

        mesh, uv = self.multi_res.interpolate_level(t)
        self.current_mesh = mesh
        self.current_uv = uv
        self.viewer.set_mesh(mesh, uv)
        self.update_info()

    def refine_mesh(self):
        if self.multi_res is None:
            return

        if self.multi_res.refine():
            level = self.multi_res.current_level
            self.mr_level_slider.setValue(level)
            mesh, uv = self.multi_res.get_current()
            self.current_mesh = mesh
            self.current_uv = uv
            self.subdivision_level = level
            self.update_mesh_view()

    def coarsen_mesh(self):
        if self.multi_res is None:
            return

        if self.multi_res.coarsen():
            level = self.multi_res.current_level
            self.mr_level_slider.setValue(level)
            mesh, uv = self.multi_res.get_current()
            self.current_mesh = mesh
            self.current_uv = uv
            self.subdivision_level = level
            self.update_mesh_view()

    def _to_triangular(self, mesh):
        tri_mesh = om.TriMesh()

        vertex_map = {}
        for vh in mesh.vertices():
            new_vh = tri_mesh.add_vertex(mesh.point(vh))
            vertex_map[vh.idx()] = new_vh

        for fh in mesh.faces():
            face_vertices = list(mesh.fv(fh))
            if len(face_vertices) == 3:
                v0 = vertex_map[face_vertices[0].idx()]
                v1 = vertex_map[face_vertices[1].idx()]
                v2 = vertex_map[face_vertices[2].idx()]
                tri_mesh.add_face(v0, v1, v2)
            elif len(face_vertices) >= 4:
                v0 = vertex_map[face_vertices[0].idx()]
                for i in range(1, len(face_vertices) - 1):
                    v1 = vertex_map[face_vertices[i].idx()]
                    v2 = vertex_map[face_vertices[i + 1].idx()]
                    tri_mesh.add_face(v0, v1, v2)

        return tri_mesh

    def reset_mesh(self):
        if self.original_mesh is not None:
            self.current_mesh = self._copy_mesh(self.original_mesh)
            self.current_uv = self.original_uv.copy() if self.original_uv is not None else None
            self.subdivision_level = 0
            self.level_spin.setValue(0)
            self.multi_res = None
            self.mr_level_slider.setEnabled(False)
            self.interp_slider.setEnabled(False)
            self.coarsen_btn.setEnabled(False)
            self.refine_btn.setEnabled(False)
            self.update_mesh_view()

    def export_mesh(self):
        if self.current_mesh is None:
            return

        filepath, filter = QFileDialog.getSaveFileName(
            self, 'Export Mesh', '',
            'OBJ File (*.obj);;OFF File (*.off);;PLY File (*.ply)'
        )
        if filepath:
            try:
                if 'OBJ' in filter:
                    if not filepath.endswith('.obj'):
                        filepath += '.obj'
                    MeshUtils.export_obj(self.current_mesh, filepath, self.current_uv)
                elif 'OFF' in filter:
                    if not filepath.endswith('.off'):
                        filepath += '.off'
                    MeshUtils.export_off(self.current_mesh, filepath)
                elif 'PLY' in filter:
                    if not filepath.endswith('.ply'):
                        filepath += '.ply'
                    MeshUtils.export_ply(self.current_mesh, filepath, self.current_uv)

                QMessageBox.information(self, 'Success', f'Mesh exported to: {filepath}')
            except Exception as e:
                QMessageBox.critical(self, 'Error', f'Export failed: {str(e)}')

    def update_mesh_view(self):
        self.viewer.set_mesh(self.current_mesh, self.current_uv)
        self.update_info()

    def update_info(self):
        if self.current_mesh is None:
            self.info_label.setText('No mesh loaded')
            return

        info = MeshUtils.get_mesh_info(self.current_mesh)
        has_uv = self.current_uv is not None
        info_text = (
            f"Vertices: {info['n_vertices']}\n"
            f"Edges: {info['n_edges']}\n"
            f"Faces: {info['n_faces']}\n"
            f"Subdivision Level: {self.subdivision_level}\n"
            f"UV Mapping: {'Yes' if has_uv else 'No'}"
        )
        self.info_label.setText(info_text)

    def enable_controls(self, enabled):
        self.export_btn.setEnabled(enabled)
        self.subdiv_btn.setEnabled(enabled)
        self.reset_btn.setEnabled(enabled)
        self.gen_uv_btn.setEnabled(enabled)
        self.vd_subdiv_btn.setEnabled(enabled)
        self.build_mr_btn.setEnabled(enabled)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
