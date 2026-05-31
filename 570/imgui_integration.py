import numpy as np
from imgui_bundle import imgui
from imgui_bundle.imgui import Vec2


class FluidGUI:
    def __init__(self, simulator):
        self.simulator = simulator
        
        self.display_mode = 0
        self.display_mode_names = ["Velocity (HSV)", "Pressure", "Vorticity", "Speed"]
        self.color_scale = 10.0
        
        self.tau = 0.6
        self.inflow_ux = 0.1
        self.inflow_uy = 0.0
        
        self.sim_running = True
        self.steps_per_frame = 1
        self.fps = 0.0
        
        self.obstacle_mode = 0
        self.obstacle_mode_names = ["Circle", "Rectangle", "None"]
        self.obstacle_radius = 20
        self.obstacle_size = 50
        
        self.mouse_pos = (0, 0)
        self.is_drawing = False
    
    def draw(self):
        imgui.set_next_window_pos(Vec2(10, 10), imgui.Cond_.once)
        imgui.set_next_window_size(Vec2(300, 450), imgui.Cond_.once)
        
        imgui.begin("控制面板")
        
        if imgui.collapsing_header("模拟控制", flags=imgui.TreeNodeFlags_.default_open):
            changed, self.sim_running = imgui.checkbox("运行模拟", self.sim_running)
            imgui.same_line()
            if imgui.button("重置"):
                self.reset_simulation()
            
            changed, self.steps_per_frame = imgui.slider_int("每帧步数", self.steps_per_frame, 1, 20)
            
            imgui.text(f"FPS: {self.fps:.1f}")
        
        imgui.spacing()
        
        if imgui.collapsing_header("显示设置", flags=imgui.TreeNodeFlags_.default_open):
            changed, self.display_mode = imgui.combo("显示模式", self.display_mode, self.display_mode_names)
            changed, self.color_scale = imgui.slider_float("颜色缩放", self.color_scale, 0.1, 50.0)
        
        imgui.spacing()
        
        if imgui.collapsing_header("流体参数", flags=imgui.TreeNodeFlags_.default_open):
            changed, self.tau = imgui.slider_float("粘度 (tau)", self.tau, 0.51, 2.0)
            if changed:
                self.simulator.set_tau(self.tau)
            
            changed, self.inflow_ux = imgui.slider_float("入流速度 X", self.inflow_ux, -0.5, 0.5)
            changed, self.inflow_uy = imgui.slider_float("入流速度 Y", self.inflow_uy, -0.5, 0.5)
            if changed:
                self.simulator.set_inflow_velocity(self.inflow_ux, self.inflow_uy)
        
        imgui.spacing()
        
        if imgui.collapsing_header("障碍物绘制", flags=imgui.TreeNodeFlags_.default_open):
            changed, self.obstacle_mode = imgui.combo("绘制模式", self.obstacle_mode, self.obstacle_mode_names)
            
            changed, self.obstacle_radius = imgui.slider_int("圆形半径", self.obstacle_radius, 5, 100)
            changed, self.obstacle_size = imgui.slider_int("矩形大小", self.obstacle_size, 10, 200)
            
            if imgui.button("清除障碍物"):
                self.simulator.clear_obstacles()
        
        imgui.spacing()
        
        if imgui.collapsing_header("预设场景"):
            if imgui.button("圆柱绕流"):
                self.load_preset_cylinder()
            imgui.same_line()
            if imgui.button("顶盖驱动"):
                self.load_preset_lid()
        
        imgui.end()
        
        self._draw_help_window()
    
    def _draw_help_window(self):
        imgui.set_next_window_pos(Vec2(10, 470), imgui.Cond_.once)
        imgui.set_next_window_size(Vec2(300, 150), imgui.Cond_.once)
        
        imgui.begin("操作说明")
        imgui.text("鼠标左键: 绘制障碍物")
        imgui.text("鼠标右键: 清除障碍物")
        imgui.text("滚轮: 调整绘制大小")
        imgui.text("空格: 暂停/继续")
        imgui.text("R: 重置模拟")
        imgui.end()
    
    def reset_simulation(self):
        self.simulator.clear_obstacles()
        self.simulator.initialize()
        self.simulator.set_inflow_velocity(self.inflow_ux, self.inflow_uy)
    
    def load_preset_cylinder(self):
        self.simulator.clear_obstacles()
        cx = self.simulator.width // 4
        cy = self.simulator.height // 2
        self.simulator.add_obstacle_circle(cx, cy, 25)
        self.inflow_ux = 0.1
        self.inflow_uy = 0.0
        self.simulator.set_inflow_velocity(0.1, 0.0)
    
    def load_preset_lid(self):
        self.simulator.clear_obstacles()
        h, w = self.simulator.height, self.simulator.width
        self.simulator.add_obstacle_rect(0, 0, w, 10)
        self.simulator.add_obstacle_rect(0, h-10, w, h)
        self.simulator.add_obstacle_rect(0, 0, 10, h)
        self.simulator.add_obstacle_rect(w-10, 0, w, h)
        self.inflow_ux = 0.0
        self.inflow_uy = 0.0
    
    def handle_mouse_input(self, x, y, button, action, window_width, window_height):
        sim_x = int(x / window_width * self.simulator.width)
        sim_y = int(y / window_height * self.simulator.height)
        sim_y = self.simulator.height - sim_y
        
        self.mouse_pos = (sim_x, sim_y)
        
        if button == 0:
            if action == 'press':
                self.is_drawing = True
                self._draw_at_position(sim_x, sim_y)
            elif action == 'release':
                self.is_drawing = False
        elif button == 1 and action == 'press':
            self.simulator.clear_obstacles()
    
    def handle_mouse_move(self, x, y, window_width, window_height):
        sim_x = int(x / window_width * self.simulator.width)
        sim_y = int(y / window_height * self.simulator.height)
        sim_y = self.simulator.height - sim_y
        
        self.mouse_pos = (sim_x, sim_y)
        
        if self.is_drawing and self.obstacle_mode < 2:
            self._draw_at_position(sim_x, sim_y)
    
    def handle_scroll(self, y_offset):
        if self.obstacle_mode == 0:
            self.obstacle_radius = max(5, min(100, self.obstacle_radius + int(y_offset * 5)))
        elif self.obstacle_mode == 1:
            self.obstacle_size = max(10, min(200, self.obstacle_size + int(y_offset * 10)))
    
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
