import sys
import time
import numpy as np

from PyQt5.QtWidgets import (QApplication, QMainWindow, QHBoxLayout, QWidget, 
                             QVBoxLayout, QLabel, QSlider, QPushButton, QComboBox,
                             QCheckBox, QGroupBox, QSpinBox, QTabWidget)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QMouseEvent, QWheelEvent
from PyQt5.QtWidgets import QOpenGLWidget

from OpenGL.GL import *

from fluid_simulator import FluidSimulator
from lbm_cpu import LBM_CPU
from lbm_cuda import LBM_CUDA
from renderer import FluidRenderer
from multiphase import MultiphaseLBM
from fluid_structure import RigidBody, FluidStructureCoupling
from particle_tracing import ParticleTracing


CUDA_AVAILABLE = False
try:
    import pycuda.autoinit
    CUDA_AVAILABLE = True
except ImportError:
    pass


class SimulationThread(QThread):
    simulation_complete = pyqtSignal()
    
    def __init__(self, simulator):
        super().__init__()
        self.simulator = simulator
        self.multiphase = None
        self.fsi = None
        self.particles = None
        self.obstacles = None
        
        self._running = False
        self._paused = False
        self._steps_per_frame = 1
        self._target_rate = 60
        
        self.enable_multiphase = False
        self.enable_fsi = False
        self.enable_particles = False
    
    def set_multiphase(self, multiphase):
        self.multiphase = multiphase
    
    def set_fsi(self, fsi):
        self.fsi = fsi
    
    def set_particles(self, particles):
        self.particles = particles
    
    def set_obstacles(self, obstacles):
        self.obstacles = obstacles
    
    def run(self):
        self._running = True
        interval = 1.0 / self._target_rate
        
        while self._running:
            start_time = time.time()
            
            if not self._paused:
                for _ in range(self._steps_per_frame):
                    self.simulator.step()
                    
                    if self.enable_multiphase and self.multiphase is not None:
                        if self.obstacles is not None:
                            self.multiphase.set_obstacles(self.obstacles)
                        self.multiphase.step()
                    
                    if self.enable_fsi and self.fsi is not None:
                        f = self.simulator.f if hasattr(self.simulator, 'f') else None
                        rho = self.simulator.rho if hasattr(self.simulator, 'rho') else None
                        u = self.simulator.u if hasattr(self.simulator, 'u') else None
                        tau = self.simulator.tau
                        
                        if f is not None and rho is not None and u is not None:
                            new_obstacles = self.fsi.step_coupling(f, rho, u, tau)
                            if self.obstacles is not None:
                                self.obstacles[:] = new_obstacles
                    
                    if self.enable_particles and self.particles is not None:
                        u_field = self.simulator.get_velocity()
                        self.particles.update(u_field, self.obstacles)
                
                self.simulation_complete.emit()
            
            elapsed = time.time() - start_time
            sleep_time = max(0, interval - elapsed)
            if sleep_time > 0:
                self.msleep(int(sleep_time * 1000))
    
    def stop(self):
        self._running = False
        self.wait()
    
    def pause(self, paused):
        self._paused = paused
    
    def set_steps_per_frame(self, steps):
        self._steps_per_frame = max(1, steps)
    
    def set_target_rate(self, rate):
        self._target_rate = max(1, rate)


class ControlPanel(QWidget):
    def __init__(self, simulator, gl_widget):
        super().__init__()
        self.simulator = simulator
        self.gl_widget = gl_widget
        
        self.display_mode = 0
        self.color_scale = 10.0
        self.tau = 0.6
        self.inflow_ux = 0.1
        self.inflow_uy = 0.0
        self.sim_running = True
        self.steps_per_frame = 1
        
        self.obstacle_mode = 0
        self.obstacle_radius = 20
        self.obstacle_size = 50
        
        self.show_phase = False
        self.show_particles = False
        self.show_streamlines = False
        self.show_bodies = False
        
        self.enable_multiphase = False
        self.enable_fsi = False
        self.enable_particles = False
        
        self.fps = 0.0
        self.sim_rate = 0.0
        
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(5)
        
        self.tabs = QTabWidget()
        self.tabs.addTab(self._create_basic_tab(), "基础")
        self.tabs.addTab(self._create_advanced_tab(), "高级")
        self.tabs.addTab(self._create_multiphase_tab(), "多相流")
        self.tabs.addTab(self._create_fsi_tab(), "流固耦合")
        self.tabs.addTab(self._create_particles_tab(), "粒子追踪")
        
        layout.addWidget(self.tabs)
    
    def _create_basic_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        
        sim_group = QGroupBox("模拟控制")
        sim_layout = QVBoxLayout()
        
        self.running_check = QCheckBox("运行模拟")
        self.running_check.setChecked(True)
        self.running_check.toggled.connect(self._toggle_running)
        sim_layout.addWidget(self.running_check)
        
        self.async_check = QCheckBox("异步模拟线程")
        self.async_check.setChecked(True)
        self.async_check.toggled.connect(self._toggle_async)
        sim_layout.addWidget(self.async_check)
        
        reset_btn = QPushButton("重置模拟")
        reset_btn.clicked.connect(self._reset_simulation)
        sim_layout.addWidget(reset_btn)
        
        sim_layout.addWidget(QLabel("每帧步数:"))
        self.steps_spin = QSpinBox()
        self.steps_spin.setRange(1, 50)
        self.steps_spin.setValue(1)
        self.steps_spin.valueChanged.connect(self._set_steps)
        sim_layout.addWidget(self.steps_spin)
        
        self.fps_label = QLabel("渲染FPS: 0.0")
        sim_layout.addWidget(self.fps_label)
        
        self.sim_rate_label = QLabel("模拟速率: 0 steps/s")
        sim_layout.addWidget(self.sim_rate_label)
        
        sim_group.setLayout(sim_layout)
        layout.addWidget(sim_group)
        
        display_group = QGroupBox("显示设置")
        display_layout = QVBoxLayout()
        
        display_layout.addWidget(QLabel("显示模式:"))
        self.display_combo = QComboBox()
        self.display_combo.addItems(["速度场 (HSV)", "压力场", "涡量场", "速率"])
        self.display_combo.currentIndexChanged.connect(self._set_display_mode)
        display_layout.addWidget(self.display_combo)
        
        display_layout.addWidget(QLabel("颜色缩放:"))
        self.color_scale_slider = QSlider(Qt.Horizontal)
        self.color_scale_slider.setRange(1, 100)
        self.color_scale_slider.setValue(20)
        self.color_scale_slider.valueChanged.connect(self._set_color_scale)
        display_layout.addWidget(self.color_scale_slider)
        
        display_group.setLayout(display_layout)
        layout.addWidget(display_group)
        
        help_group = QGroupBox("操作说明")
        help_layout = QVBoxLayout()
        help_layout.addWidget(QLabel("鼠标左键: 绘制障碍物"))
        help_layout.addWidget(QLabel("鼠标右键: 清除障碍物"))
        help_layout.addWidget(QLabel("滚轮: 调整绘制大小"))
        help_layout.addWidget(QLabel("空格: 暂停/继续"))
        help_layout.addWidget(QLabel("R: 重置模拟"))
        help_group.setLayout(help_layout)
        layout.addWidget(help_group)
        
        layout.addStretch()
        return widget
    
    def _create_advanced_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        
        param_group = QGroupBox("流体参数")
        param_layout = QVBoxLayout()
        
        self.mrt_check = QCheckBox("MRT碰撞模型")
        self.mrt_check.setChecked(True)
        self.mrt_check.toggled.connect(self._toggle_mrt)
        param_layout.addWidget(self.mrt_check)
        
        param_layout.addWidget(QLabel("粘度 (tau):"))
        self.tau_slider = QSlider(Qt.Horizontal)
        self.tau_slider.setRange(51, 500)
        self.tau_slider.setValue(60)
        self.tau_slider.valueChanged.connect(self._set_tau)
        param_layout.addWidget(self.tau_slider)
        
        param_layout.addWidget(QLabel("入流速度 X:"))
        self.ux_slider = QSlider(Qt.Horizontal)
        self.ux_slider.setRange(-50, 50)
        self.ux_slider.setValue(10)
        self.ux_slider.valueChanged.connect(self._set_inflow)
        param_layout.addWidget(self.ux_slider)
        
        param_layout.addWidget(QLabel("入流速度 Y:"))
        self.uy_slider = QSlider(Qt.Horizontal)
        self.uy_slider.setRange(-50, 50)
        self.uy_slider.setValue(0)
        self.uy_slider.valueChanged.connect(self._set_inflow)
        param_layout.addWidget(self.uy_slider)
        
        param_group.setLayout(param_layout)
        layout.addWidget(param_group)
        
        obstacle_group = QGroupBox("障碍物绘制")
        obstacle_layout = QVBoxLayout()
        
        self.subgrid_check = QCheckBox("亚网格边界")
        self.subgrid_check.setChecked(True)
        self.subgrid_check.toggled.connect(self._toggle_subgrid)
        obstacle_layout.addWidget(self.subgrid_check)
        
        obstacle_layout.addWidget(QLabel("绘制模式:"))
        self.obstacle_combo = QComboBox()
        self.obstacle_combo.addItems(["圆形", "矩形", "无"])
        self.obstacle_combo.currentIndexChanged.connect(self._set_obstacle_mode)
        obstacle_layout.addWidget(self.obstacle_combo)
        
        obstacle_layout.addWidget(QLabel("圆形半径:"))
        self.radius_slider = QSlider(Qt.Horizontal)
        self.radius_slider.setRange(5, 100)
        self.radius_slider.setValue(20)
        self.radius_slider.valueChanged.connect(self._set_radius)
        obstacle_layout.addWidget(self.radius_slider)
        
        obstacle_layout.addWidget(QLabel("矩形大小:"))
        self.size_slider = QSlider(Qt.Horizontal)
        self.size_slider.setRange(10, 200)
        self.size_slider.setValue(50)
        self.size_slider.valueChanged.connect(self._set_size)
        obstacle_layout.addWidget(self.size_slider)
        
        clear_obstacle_btn = QPushButton("清除障碍物")
        clear_obstacle_btn.clicked.connect(self.simulator.clear_obstacles)
        obstacle_layout.addWidget(clear_obstacle_btn)
        
        obstacle_group.setLayout(obstacle_layout)
        layout.addWidget(obstacle_group)
        
        stability_group = QGroupBox("数值稳定")
        stability_layout = QVBoxLayout()
        
        self.stabilization_check = QCheckBox("稳定化处理")
        self.stabilization_check.setChecked(True)
        self.stabilization_check.toggled.connect(self._toggle_stabilization)
        stability_layout.addWidget(self.stabilization_check)
        
        stability_layout.addWidget(QLabel("最大速度:"))
        self.max_vel_slider = QSlider(Qt.Horizontal)
        self.max_vel_slider.setRange(10, 100)
        self.max_vel_slider.setValue(50)
        self.max_vel_slider.valueChanged.connect(self._set_max_vel)
        stability_layout.addWidget(self.max_vel_slider)
        
        stability_group.setLayout(stability_layout)
        layout.addWidget(stability_group)
        
        preset_group = QGroupBox("预设场景")
        preset_layout = QHBoxLayout()
        
        cylinder_btn = QPushButton("圆柱绕流")
        cylinder_btn.clicked.connect(self._preset_cylinder)
        preset_layout.addWidget(cylinder_btn)
        
        lid_btn = QPushButton("空腔流")
        lid_btn.clicked.connect(self._preset_lid)
        preset_layout.addWidget(lid_btn)
        
        preset_group.setLayout(preset_layout)
        layout.addWidget(preset_group)
        
        layout.addStretch()
        return widget
    
    def _create_multiphase_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        
        mp_group = QGroupBox("多相流控制")
        mp_layout = QVBoxLayout()
        
        self.enable_multiphase_check = QCheckBox("启用多相流模拟")
        self.enable_multiphase_check.setChecked(False)
        self.enable_multiphase_check.toggled.connect(self._toggle_multiphase)
        mp_layout.addWidget(self.enable_multiphase_check)
        
        self.show_phase_check = QCheckBox("显示相界面")
        self.show_phase_check.setChecked(False)
        self.show_phase_check.toggled.connect(self._toggle_show_phase)
        mp_layout.addWidget(self.show_phase_check)
        
        mp_layout.addWidget(QLabel("表面张力系数:"))
        self.sigma_slider = QSlider(Qt.Horizontal)
        self.sigma_slider.setRange(1, 100)
        self.sigma_slider.setValue(10)
        self.sigma_slider.valueChanged.connect(self._set_sigma)
        mp_layout.addWidget(self.sigma_slider)
        
        mp_layout.addWidget(QLabel("密度比 (液/气):"))
        self.density_ratio_slider = QSlider(Qt.Horizontal)
        self.density_ratio_slider.setRange(2, 20)
        self.density_ratio_slider.setValue(10)
        self.density_ratio_slider.valueChanged.connect(self._set_density_ratio)
        mp_layout.addWidget(self.density_ratio_slider)
        
        mp_preset_layout = QHBoxLayout()
        
        droplet_btn = QPushButton("添加液滴")
        droplet_btn.clicked.connect(self._add_droplet)
        mp_preset_layout.addWidget(droplet_btn)
        
        column_btn = QPushButton("液柱")
        column_btn.clicked.connect(self._add_liquid_column)
        mp_preset_layout.addWidget(column_btn)
        
        reset_mp_btn = QPushButton("重置")
        reset_mp_btn.clicked.connect(self._reset_multiphase)
        mp_preset_layout.addWidget(reset_mp_btn)
        
        mp_layout.addLayout(mp_preset_layout)
        
        mp_group.setLayout(mp_layout)
        layout.addWidget(mp_group)
        
        layout.addStretch()
        return widget
    
    def _create_fsi_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        
        fsi_group = QGroupBox("流固耦合控制")
        fsi_layout = QVBoxLayout()
        
        self.enable_fsi_check = QCheckBox("启用流固耦合")
        self.enable_fsi_check.setChecked(False)
        self.enable_fsi_check.toggled.connect(self._toggle_fsi)
        fsi_layout.addWidget(self.enable_fsi_check)
        
        self.show_bodies_check = QCheckBox("显示刚体")
        self.show_bodies_check.setChecked(True)
        self.show_bodies_check.toggled.connect(self._toggle_show_bodies)
        fsi_layout.addWidget(self.show_bodies_check)
        
        fsi_layout.addWidget(QLabel("刚体密度:"))
        self.body_density_slider = QSlider(Qt.Horizontal)
        self.body_density_slider.setRange(10, 100)
        self.body_density_slider.setValue(20)
        fsi_layout.addWidget(self.body_density_slider)
        
        fsi_layout.addWidget(QLabel("刚体半径:"))
        self.body_radius_slider = QSlider(Qt.Horizontal)
        self.body_radius_slider.setRange(10, 50)
        self.body_radius_slider.setValue(25)
        fsi_layout.addWidget(self.body_radius_slider)
        
        fsi_preset_layout = QHBoxLayout()
        
        add_body_btn = QPushButton("添加可动刚体")
        add_body_btn.clicked.connect(self._add_floating_body)
        fsi_preset_layout.addWidget(add_body_btn)
        
        add_fixed_btn = QPushButton("添加固定刚体")
        add_fixed_btn.clicked.connect(self._add_fixed_body)
        fsi_preset_layout.addWidget(add_fixed_btn)
        
        clear_bodies_btn = QPushButton("清除刚体")
        clear_bodies_btn.clicked.connect(self._clear_bodies)
        fsi_preset_layout.addWidget(clear_bodies_btn)
        
        fsi_layout.addLayout(fsi_preset_layout)
        
        self.body_info_label = QLabel("刚体数量: 0")
        fsi_layout.addWidget(self.body_info_label)
        
        fsi_group.setLayout(fsi_layout)
        layout.addWidget(fsi_group)
        
        layout.addStretch()
        return widget
    
    def _create_particles_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        
        pt_group = QGroupBox("粒子追踪控制")
        pt_layout = QVBoxLayout()
        
        self.enable_particles_check = QCheckBox("启用粒子追踪")
        self.enable_particles_check.setChecked(False)
        self.enable_particles_check.toggled.connect(self._toggle_particles)
        pt_layout.addWidget(self.enable_particles_check)
        
        self.show_particles_check = QCheckBox("显示粒子")
        self.show_particles_check.setChecked(True)
        self.show_particles_check.toggled.connect(self._toggle_show_particles)
        pt_layout.addWidget(self.show_particles_check)
        
        self.show_streamlines_check = QCheckBox("显示流线")
        self.show_streamlines_check.setChecked(True)
        self.show_streamlines_check.toggled.connect(self._toggle_show_streamlines)
        pt_layout.addWidget(self.show_streamlines_check)
        
        pt_layout.addWidget(QLabel("粒子数量:"))
        self.particle_count_slider = QSlider(Qt.Horizontal)
        self.particle_count_slider.setRange(100, 5000)
        self.particle_count_slider.setValue(2000)
        self.particle_count_slider.valueChanged.connect(self._set_particle_count)
        pt_layout.addWidget(self.particle_count_slider)
        
        pt_layout.addWidget(QLabel("释放速率:"))
        self.release_rate_slider = QSlider(Qt.Horizontal)
        self.release_rate_slider.setRange(1, 50)
        self.release_rate_slider.setValue(10)
        self.release_rate_slider.valueChanged.connect(self._set_release_rate)
        pt_layout.addWidget(self.release_rate_slider)
        
        pt_layout.addWidget(QLabel("流线长度:"))
        self.trail_length_slider = QSlider(Qt.Horizontal)
        self.trail_length_slider.setRange(10, 500)
        self.trail_length_slider.setValue(100)
        self.trail_length_slider.valueChanged.connect(self._set_trail_length)
        pt_layout.addWidget(self.trail_length_slider)
        
        pt_preset_layout = QHBoxLayout()
        
        release_btn = QPushButton("大量释放")
        release_btn.clicked.connect(self._burst_release)
        pt_preset_layout.addWidget(release_btn)
        
        reset_pt_btn = QPushButton("重置粒子")
        reset_pt_btn.clicked.connect(self._reset_particles)
        pt_preset_layout.addWidget(reset_pt_btn)
        
        clear_pt_btn = QPushButton("清除粒子")
        clear_pt_btn.clicked.connect(self._clear_particles)
        pt_preset_layout.addWidget(clear_pt_btn)
        
        pt_layout.addLayout(pt_preset_layout)
        
        self.particle_info_label = QLabel("活跃粒子: 0")
        pt_layout.addWidget(self.particle_info_label)
        
        pt_group.setLayout(pt_layout)
        layout.addWidget(pt_group)
        
        layout.addStretch()
        return widget
    
    def _toggle_running(self, checked):
        self.sim_running = checked
        self.gl_widget.set_simulation_paused(not checked)
    
    def _toggle_async(self, checked):
        self.gl_widget.set_async_mode(checked)
    
    def _reset_simulation(self):
        self.simulator.clear_obstacles()
        self.simulator.initialize()
        self.simulator.set_inflow_velocity(self.inflow_ux, self.inflow_uy)
    
    def _set_steps(self, value):
        self.steps_per_frame = value
        self.gl_widget.set_steps_per_frame(value)
    
    def _set_display_mode(self, index):
        self.display_mode = index
        self.gl_widget.display_mode = index
    
    def _set_color_scale(self, value):
        self.color_scale = value / 2.0
        self.gl_widget.color_scale = self.color_scale
    
    def _set_tau(self, value):
        self.tau = value / 100.0
        self.simulator.set_tau(self.tau)
    
    def _set_inflow(self, _):
        self.inflow_ux = self.ux_slider.value() / 100.0
        self.inflow_uy = self.uy_slider.value() / 100.0
        self.simulator.set_inflow_velocity(self.inflow_ux, self.inflow_uy)
    
    def _set_obstacle_mode(self, index):
        self.obstacle_mode = index
        self.gl_widget.obstacle_mode = index
    
    def _set_radius(self, value):
        self.obstacle_radius = value
        self.gl_widget.obstacle_radius = value
    
    def _set_size(self, value):
        self.obstacle_size = value
        self.gl_widget.obstacle_size = value
    
    def _toggle_mrt(self, checked):
        self.simulator.use_mrt = checked
    
    def _toggle_subgrid(self, checked):
        self.simulator.enable_subgrid = checked
    
    def _toggle_stabilization(self, checked):
        self.simulator.enable_stabilization = checked
    
    def _set_max_vel(self, value):
        self.simulator.max_velocity = value / 100.0
    
    def _preset_cylinder(self):
        self.simulator.clear_obstacles()
        cx = self.simulator.width // 4
        cy = self.simulator.height // 2
        self.simulator.add_obstacle_circle(cx, cy, 25)
        self.inflow_ux = 0.1
        self.inflow_uy = 0.0
        self.ux_slider.setValue(10)
        self.uy_slider.setValue(0)
        self.simulator.set_inflow_velocity(0.1, 0.0)
    
    def _preset_lid(self):
        self.simulator.clear_obstacles()
        h, w = self.simulator.height, self.simulator.width
        self.simulator.add_obstacle_rect(0, 0, w, 10)
        self.simulator.add_obstacle_rect(0, h-10, w, h)
        self.simulator.add_obstacle_rect(0, 0, 10, h)
        self.simulator.add_obstacle_rect(w-10, 0, w, h)
        self.inflow_ux = 0.0
        self.inflow_uy = 0.0
        self.ux_slider.setValue(0)
        self.uy_slider.setValue(0)
    
    def _toggle_multiphase(self, checked):
        self.enable_multiphase = checked
        self.gl_widget.set_multiphase_enabled(checked)
    
    def _toggle_show_phase(self, checked):
        self.show_phase = checked
        self.gl_widget.show_phase = checked
    
    def _set_sigma(self, value):
        sigma = value / 1000.0
        if self.gl_widget.multiphase is not None:
            self.gl_widget.multiphase.sigma = sigma
    
    def _set_density_ratio(self, value):
        ratio = value
        if self.gl_widget.multiphase is not None:
            self.gl_widget.multiphase.rho2 = 1.0 / ratio
    
    def _add_droplet(self):
        if self.gl_widget.multiphase is not None:
            cx = self.simulator.width // 2
            cy = self.simulator.height // 2
            self.gl_widget.multiphase.set_droplet(cx, cy, 50)
    
    def _add_liquid_column(self):
        if self.gl_widget.multiphase is not None:
            self.gl_widget.multiphase.add_liquid_column(0, self.simulator.width // 2)
    
    def _reset_multiphase(self):
        if self.gl_widget.multiphase is not None:
            self.gl_widget.multiphase.reset()
    
    def _toggle_fsi(self, checked):
        self.enable_fsi = checked
        self.gl_widget.set_fsi_enabled(checked)
    
    def _toggle_show_bodies(self, checked):
        self.show_bodies = checked
        self.gl_widget.show_bodies = checked
    
    def _add_floating_body(self):
        if self.gl_widget.fsi is not None:
            density = self.body_density_slider.value() / 10.0
            radius = self.body_radius_slider.value()
            cx = self.simulator.width // 2
            cy = self.simulator.height // 2
            body = RigidBody(cx, cy, radius, density=density, fixed=False)
            self.gl_widget.fsi.add_body(body)
            self._update_body_info()
    
    def _add_fixed_body(self):
        if self.gl_widget.fsi is not None:
            radius = self.body_radius_slider.value()
            cx = self.simulator.width // 3
            cy = self.simulator.height // 2
            body = RigidBody(cx, cy, radius, density=1.0, fixed=True)
            self.gl_widget.fsi.add_body(body)
            self._update_body_info()
    
    def _clear_bodies(self):
        if self.gl_widget.fsi is not None:
            self.gl_widget.fsi.clear_bodies()
            self._update_body_info()
    
    def _update_body_info(self):
        if self.gl_widget.fsi is not None:
            count = len(self.gl_widget.fsi.bodies)
            self.body_info_label.setText(f"刚体数量: {count}")
    
    def _toggle_particles(self, checked):
        self.enable_particles = checked
        self.gl_widget.set_particles_enabled(checked)
    
    def _toggle_show_particles(self, checked):
        self.show_particles = checked
        self.gl_widget.show_particles = checked
    
    def _toggle_show_streamlines(self, checked):
        self.show_streamlines = checked
        self.gl_widget.show_streamlines = checked
    
    def _set_particle_count(self, value):
        if self.gl_widget.particles is not None:
            self.gl_widget.particles.max_particles = value
    
    def _set_release_rate(self, value):
        if self.gl_widget.particles is not None:
            self.gl_widget.particles.release_rate = value
    
    def _set_trail_length(self, value):
        if self.gl_widget.particles is not None:
            self.gl_widget.particles.trail_length = value
    
    def _burst_release(self):
        if self.gl_widget.particles is not None:
            self.gl_widget.particles.release_particles(500)
    
    def _reset_particles(self):
        if self.gl_widget.particles is not None:
            self.gl_widget.particles.reset()
    
    def _clear_particles(self):
        if self.gl_widget.particles is not None:
            self.gl_widget.particles.clear()
    
    def update_fps(self, fps):
        self.fps = fps
        self.fps_label.setText(f"渲染FPS: {fps:.1f}")
    
    def update_sim_rate(self, rate):
        self.sim_rate = rate
        self.sim_rate_label.setText(f"模拟速率: {rate:.0f} steps/s")
    
    def update_particle_info(self, count):
        self.particle_info_label.setText(f"活跃粒子: {count}")


class GLWidget(QOpenGLWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMinimumSize(512, 512)
        
        self.simulator = None
        self.renderer = None
        self.control_panel = None
        self.simulation_thread = None
        
        self.multiphase = None
        self.fsi = None
        self.particles = None
        
        self.sim_width = 512
        self.sim_height = 512
        
        self.frame_times = []
        self.last_time = time.time()
        
        self.use_cuda = CUDA_AVAILABLE
        self.use_async = True
        
        self.display_mode = 0
        self.color_scale = 10.0
        self.sim_running = True
        self.steps_per_frame = 1
        
        self.obstacle_mode = 0
        self.obstacle_radius = 20
        self.obstacle_size = 50
        
        self.is_drawing = False
        
        self._latest_data = None
        self._data_ready = False
        
        self.show_phase = False
        self.show_particles = False
        self.show_streamlines = False
        self.show_bodies = False
        
        self.enable_multiphase = False
        self.enable_fsi = False
        self.enable_particles = False
    
    def set_control_panel(self, panel):
        self.control_panel = panel
    
    def set_multiphase_enabled(self, enabled):
        self.enable_multiphase = enabled
        if self.simulation_thread:
            self.simulation_thread.enable_multiphase = enabled
        
        if enabled and self.multiphase is None:
            self.multiphase = MultiphaseLBM(self.sim_width, self.sim_height, self.simulator.tau)
            self.multiphase.set_obstacles(self.simulator.obstacles)
            if self.simulation_thread:
                self.simulation_thread.set_multiphase(self.multiphase)
                self.simulation_thread.set_obstacles(self.simulator.obstacles)
    
    def set_fsi_enabled(self, enabled):
        self.enable_fsi = enabled
        if self.simulation_thread:
            self.simulation_thread.enable_fsi = enabled
        
        if enabled and self.fsi is None:
            self.fsi = FluidStructureCoupling(self.sim_width, self.sim_height)
            if self.simulation_thread:
                self.simulation_thread.set_fsi(self.fsi)
                self.simulation_thread.set_obstacles(self.simulator.obstacles)
    
    def set_particles_enabled(self, enabled):
        self.enable_particles = enabled
        if self.simulation_thread:
            self.simulation_thread.enable_particles = enabled
        
        if enabled and self.particles is None:
            self.particles = ParticleTracing(self.sim_width, self.sim_height, max_particles=2000)
            self.particles.set_release_region(10, self.sim_height // 4, 3 * self.sim_height // 4)
            if self.simulation_thread:
                self.simulation_thread.set_particles(self.particles)
    
    def set_async_mode(self, enabled):
        self.use_async = enabled
        if enabled:
            self._start_async_simulation()
        else:
            self._stop_async_simulation()
    
    def set_simulation_paused(self, paused):
        self.sim_running = not paused
        if self.simulation_thread:
            self.simulation_thread.pause(paused)
    
    def set_steps_per_frame(self, steps):
        self.steps_per_frame = steps
        if self.simulation_thread:
            self.simulation_thread.set_steps_per_frame(steps)
    
    def _start_async_simulation(self):
        if self.simulator is None:
            return
        
        self._stop_async_simulation()
        self.simulation_thread = SimulationThread(self.simulator)
        self.simulation_thread.simulation_complete.connect(self._on_simulation_complete)
        
        if self.multiphase is not None:
            self.simulation_thread.set_multiphase(self.multiphase)
            self.simulation_thread.enable_multiphase = self.enable_multiphase
        if self.fsi is not None:
            self.simulation_thread.set_fsi(self.fsi)
            self.simulation_thread.enable_fsi = self.enable_fsi
        if self.particles is not None:
            self.simulation_thread.set_particles(self.particles)
            self.simulation_thread.enable_particles = self.enable_particles
        
        self.simulation_thread.set_obstacles(self.simulator.obstacles)
        self.simulation_thread.start()
    
    def _stop_async_simulation(self):
        if self.simulation_thread:
            self.simulation_thread.stop()
            self.simulation_thread = None
    
    def _on_simulation_complete(self):
        self._data_ready = True
    
    def initializeGL(self):
        glClearColor(0.1, 0.1, 0.1, 1.0)
        glEnable(GL_TEXTURE_2D)
        
        if self.use_cuda:
            print("使用 CUDA 加速")
            self.simulator = LBM_CUDA(self.sim_width, self.sim_height, tau=0.6)
        else:
            print("使用 CPU 模式")
            self.simulator = LBM_CPU(self.sim_width, self.sim_height, tau=0.6)
        
        self.simulator.set_inflow_velocity(0.1, 0.0)
        self.simulator.add_obstacle_circle(self.sim_width // 4, self.sim_height // 2, 25)
        
        self.renderer = FluidRenderer(self.sim_width, self.sim_height)
        
        if self.use_async:
            self._start_async_simulation()
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(16)
    
    def resizeGL(self, width, height):
        glViewport(0, 0, width, height)
    
    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT)
        
        if self.simulator is None or self.renderer is None:
            return
        
        if not self.use_async and self.sim_running:
            for _ in range(self.steps_per_frame):
                self.simulator.step()
                
                if self.enable_multiphase and self.multiphase is not None:
                    self.multiphase.set_obstacles(self.simulator.obstacles)
                    self.multiphase.step()
                
                if self.enable_fsi and self.fsi is not None:
                    f = self.simulator.f if hasattr(self.simulator, 'f') else None
                    rho = self.simulator.rho if hasattr(self.simulator, 'rho') else None
                    u = self.simulator.u if hasattr(self.simulator, 'u') else None
                    tau = self.simulator.tau
                    if f is not None and rho is not None and u is not None:
                        new_obstacles = self.fsi.step_coupling(f, rho, u, tau)
                        self.simulator.obstacles[:] = new_obstacles
                
                if self.enable_particles and self.particles is not None:
                    u_field = self.simulator.get_velocity()
                    self.particles.update(u_field, self.simulator.obstacles)
            
            self._data_ready = True
        
        if self._data_ready or self._latest_data is None:
            if self.display_mode == 0 or self.display_mode == 3:
                self._latest_data = self.simulator.get_velocity()
            elif self.display_mode == 1:
                self._latest_data = self.simulator.get_pressure()
            elif self.display_mode == 2:
                self._latest_data = self.simulator.get_vorticity()
            else:
                self._latest_data = self.simulator.get_velocity()
            self._data_ready = False
        
        if self._latest_data is not None:
            self.renderer.update_texture(self._latest_data)
        
        if self.enable_multiphase and self.multiphase is not None:
            phase = self.multiphase.get_phase()
            interface = self.multiphase.get_interface()
            self.renderer.update_phase_texture(phase, interface)
        
        if self.enable_particles and self.particles is not None:
            if self.show_particles:
                positions, colors = self.particles.get_active_particles()
                self.renderer.update_particles(positions, colors)
                if self.control_panel:
                    self.control_panel.update_particle_info(len(positions))
            
            if self.show_streamlines:
                lines, line_colors = self.particles.get_streamlines()
                self.renderer.update_streamlines(lines, line_colors)
        
        if self.enable_fsi and self.fsi is not None:
            body_states = self.fsi.get_body_states()
            self.renderer.update_bodies(body_states)
        
        self.renderer.render(
            self.display_mode, self.color_scale,
            show_phase=self.show_phase and self.enable_multiphase,
            show_particles=self.show_particles and self.enable_particles,
            show_streamlines=self.show_streamlines and self.enable_particles,
            show_bodies=self.show_bodies and self.enable_fsi
        )
        
        self._update_fps()
        if self.control_panel:
            fps = 1.0 / (np.mean(self.frame_times) + 1e-6)
            self.control_panel.update_fps(fps)
            self.control_panel.update_sim_rate(self.simulator.get_simulation_rate())
    
    def _update_fps(self):
        current_time = time.time()
        delta = current_time - self.last_time
        self.last_time = current_time
        
        self.frame_times.append(delta)
        if len(self.frame_times) > 30:
            self.frame_times.pop(0)
    
    def _get_sim_pos(self, x, y):
        sim_x = int(x / self.width() * self.sim_width)
        sim_y = int(y / self.height() * self.sim_height)
        sim_y = self.sim_height - sim_y
        return sim_x, sim_y
    
    def _draw_at_position(self, x, y):
        if self.obstacle_mode == 0:
            self.simulator.add_obstacle_circle(x, y, self.obstacle_radius)
        elif self.obstacle_mode == 1:
            half = self.obstacle_size // 2
            self.simulator.add_obstacle_rect(
                max(0, x - half), max(0, y - half),
                min(self.simulator.width, x + half),
                min(self.simulator.height, y + half)
            )
        
        if self.enable_multiphase and self.multiphase is not None:
            self.multiphase.set_obstacles(self.simulator.obstacles)
    
    def mousePressEvent(self, event: QMouseEvent):
        if self.simulator is None:
            return
        
        x, y = self._get_sim_pos(event.x(), event.y())
        
        if event.button() == Qt.LeftButton:
            self.is_drawing = True
            if self.obstacle_mode < 2:
                self._draw_at_position(x, y)
        elif event.button() == Qt.RightButton:
            self.simulator.clear_obstacles()
            if self.multiphase is not None:
                self.multiphase.set_obstacles(self.simulator.obstacles)
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.is_drawing = False
    
    def mouseMoveEvent(self, event: QMouseEvent):
        if not self.is_drawing or self.obstacle_mode >= 2:
            return
        
        x, y = self._get_sim_pos(event.x(), event.y())
        self._draw_at_position(x, y)
    
    def wheelEvent(self, event: QWheelEvent):
        delta = event.angleDelta().y() / 120.0
        
        if self.obstacle_mode == 0:
            self.obstacle_radius = max(5, min(100, self.obstacle_radius + int(delta * 5)))
            if self.control_panel:
                self.control_panel.radius_slider.setValue(self.obstacle_radius)
        elif self.obstacle_mode == 1:
            self.obstacle_size = max(10, min(200, self.obstacle_size + int(delta * 10)))
            if self.control_panel:
                self.control_panel.size_slider.setValue(self.obstacle_size)
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Space:
            self.sim_running = not self.sim_running
            if self.control_panel:
                self.control_panel.running_check.setChecked(self.sim_running)
            if self.simulation_thread:
                self.simulation_thread.pause(not self.sim_running)
        elif event.key() == Qt.Key_R:
            self.simulator.clear_obstacles()
            self.simulator.initialize()
            if self.multiphase is not None:
                self.multiphase.reset()
            if self.particles is not None:
                self.particles.reset()
    
    def cleanup(self):
        self._stop_async_simulation()
        if self.renderer:
            self.renderer.cleanup()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("格子玻尔兹曼流体模拟 (完整版)")
        self.resize(1400, 850)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QHBoxLayout(central_widget)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        self.gl_widget = GLWidget()
        self.control_panel = None
        
        layout.addWidget(self.gl_widget, stretch=3)
        
        QTimer.singleShot(100, self._init_control_panel)
    
    def _init_control_panel(self):
        self.control_panel = ControlPanel(self.gl_widget.simulator, self.gl_widget)
        self.gl_widget.set_control_panel(self.control_panel)
        self.centralWidget().layout().addWidget(self.control_panel, stretch=1)
    
    def closeEvent(self, event):
        self.gl_widget.cleanup()
        event.accept()


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
