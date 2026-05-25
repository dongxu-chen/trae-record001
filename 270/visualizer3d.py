import pygame
import numpy as np
import sys
from typing import List, Tuple, Dict, Optional
from map3d import Map3D
from astar3d import AStar3D
from multi_robot import MultiRobotCoordinator
from robot_sim import RobotSimulationManager


class Button3D:
    def __init__(self, x: int, y: int, width: int, height: int, text: str,
                 color: Tuple[int, int, int] = (70, 70, 70),
                 hover_color: Tuple[int, int, int] = (100, 100, 100),
                 text_color: Tuple[int, int, int] = (255, 255, 255)):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.color = color
        self.hover_color = hover_color
        self.text_color = text_color
        self.is_hovered = False

    def draw(self, screen: pygame.Surface, font: pygame.font.Font) -> None:
        color = self.hover_color if self.is_hovered else self.color
        pygame.draw.rect(screen, color, self.rect)
        pygame.draw.rect(screen, (150, 150, 150), self.rect, 2)

        text_surf = font.render(self.text, True, self.text_color)
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)

    def check_hover(self, mouse_pos: Tuple[int, int]) -> None:
        self.is_hovered = self.rect.collidepoint(mouse_pos)

    def is_clicked(self, mouse_pos: Tuple[int, int]) -> bool:
        return self.rect.collidepoint(mouse_pos)


class PathPlanner3DVisualizer:
    def __init__(self, width: int = 1200, height: int = 750):
        pygame.init()
        self.width = width
        self.height = height
        self.sidebar_width = 220
        self.map_width = width - self.sidebar_width
        self.map_height = height

        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("3D多机器人路径规划可视化")

        self.font_small = pygame.font.Font(None, 18)
        self.font_medium = pygame.font.Font(None, 22)
        self.font_large = pygame.font.Font(None, 28)

        self.map3d = Map3D(floor_width=750, floor_height=700, resolution=5.0)
        self.astar3d = AStar3D(self.map3d)
        self.multi_robot_coordinator = MultiRobotCoordinator(map3d=self.map3d)
        self.robot_sim_manager = RobotSimulationManager()

        self.current_floor = 0
        self.start_pos_3d: Optional[Tuple[float, float, int]] = None
        self.goal_pos_3d: Optional[Tuple[float, float, int]] = None
        self.path_3d: List[Tuple[float, float, int]] = []

        self.multi_robot_mode = False
        self.animation_running = False
        self.setting_start = False
        self.setting_goal = False

        self.floor_colors = [
            (240, 240, 255),
            (240, 255, 240),
            (255, 255, 240),
            (255, 240, 255),
        ]

        self._init_sample_3d_map()
        self._init_buttons()

    def _init_sample_3d_map(self) -> None:
        floor0 = self.map3d.add_floor(0, "1F - 大厅")
        floor1 = self.map3d.add_floor(1, "2F - 办公区")
        floor2 = self.map3d.add_floor(2, "3F - 会议室")

        obstacles_f0 = [
            {'type': 'rectangle', 'x': 200, 'y': 100, 'width': 100, 'height': 150},
            {'type': 'rectangle', 'x': 450, 'y': 150, 'width': 80, 'height': 200},
            {'type': 'circle', 'x': 600, 'y': 450, 'radius': 40},
        ]
        for obs in obstacles_f0:
            if obs['type'] == 'rectangle':
                floor0.grid_map._add_rectangle_obstacle(obs)
            elif obs['type'] == 'circle':
                floor0.grid_map._add_circle_obstacle(obs)

        obstacles_f1 = [
            {'type': 'rectangle', 'x': 100, 'y': 100, 'width': 120, 'height': 100},
            {'type': 'rectangle', 'x': 300, 'y': 200, 'width': 150, 'height': 80},
            {'type': 'rectangle', 'x': 500, 'y': 350, 'width': 100, 'height': 150},
            {'type': 'polygon', 'vertices': [[200, 400], [280, 350], [350, 420], [250, 480]]},
        ]
        for obs in obstacles_f1:
            if obs['type'] == 'rectangle':
                floor1.grid_map._add_rectangle_obstacle(obs)
            elif obs['type'] == 'circle':
                floor1.grid_map._add_circle_obstacle(obs)
            elif obs['type'] == 'polygon':
                floor1.grid_map._add_polygon_obstacle(obs)

        obstacles_f2 = [
            {'type': 'rectangle', 'x': 150, 'y': 150, 'width': 200, 'height': 150},
            {'type': 'rectangle', 'x': 500, 'y': 100, 'width': 80, 'height': 250},
            {'type': 'circle', 'x': 350, 'y': 500, 'radius': 50},
        ]
        for obs in obstacles_f2:
            if obs['type'] == 'rectangle':
                floor2.grid_map._add_rectangle_obstacle(obs)
            elif obs['type'] == 'circle':
                floor2.grid_map._add_circle_obstacle(obs)

        self.map3d.add_connection('elevator', 0, 1, (700, 100), (700, 100), speed=2.0)
        self.map3d.add_connection('stairs', 1, 2, (100, 600), (100, 600), speed=1.0)
        self.map3d.add_connection('elevator', 0, 2, (50, 300), (50, 300), speed=2.0)

        self.start_pos_3d = (50.0, 50.0, 0)
        self.goal_pos_3d = (650.0, 550.0, 2)

    def _init_buttons(self) -> None:
        btn_y = 20
        btn_height = 30
        btn_width = self.sidebar_width - 30
        small_btn_width = (self.sidebar_width - 40) // 3
        btn_x = 15

        self.buttons = {
            'floor_label': Button3D(btn_x, btn_y, btn_width, btn_height, "楼层选择:", color=(60, 60, 60)),
            'floor_0': Button3D(btn_x, btn_y + 35, small_btn_width, btn_height, "1F", color=(80, 80, 100)),
            'floor_1': Button3D(btn_x + small_btn_width + 5, btn_y + 35, small_btn_width, btn_height, "2F", color=(80, 80, 100)),
            'floor_2': Button3D(btn_x + 2 * (small_btn_width + 5), btn_y + 35, small_btn_width, btn_height, "3F", color=(80, 80, 100)),
        }

        mode_y = btn_y + 90
        self.buttons.update({
            'mode_3d': Button3D(btn_x, mode_y, btn_width, btn_height, "3D路径规划模式", color=(100, 60, 60)),
            'mode_multi': Button3D(btn_x, mode_y + 35, btn_width, btn_height, "多机器人协同模式", color=(60, 100, 60)),
        })

        action_y = mode_y + 90
        self.buttons.update({
            'set_start': Button3D(btn_x, action_y, btn_width, btn_height, "设置起点 (S)"),
            'set_goal': Button3D(btn_x, action_y + 35, btn_width, btn_height, "设置终点 (G)"),
            'plan': Button3D(btn_x, action_y + 70, btn_width, btn_height, "开始规划 (P)", color=(50, 120, 50)),
        })

        robot_y = action_y + 130
        self.buttons.update({
            'add_robot': Button3D(btn_x, robot_y, btn_width, btn_height, "添加机器人"),
            'start_sim': Button3D(btn_x, robot_y + 35, btn_width, btn_height, "开始/停止仿真 (A)", color=(60, 60, 100)),
            'clear_robots': Button3D(btn_x, robot_y + 70, btn_width, btn_height, "清除所有机器人"),
        })

        info_y = robot_y + 130
        self.buttons.update({
            'info_label': Button3D(btn_x, info_y, btn_width, btn_height, "=== 信息面板 ===", color=(60, 60, 60)),
        })

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.QUIT:
            return False

        if event.type == pygame.MOUSEMOTION:
            for btn in self.buttons.values():
                btn.check_hover(event.pos)

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                x, y = event.pos

                if x < self.map_width:
                    if self.setting_start:
                        self.start_pos_3d = (float(x), float(y), self.current_floor)
                        self.setting_start = False
                    elif self.setting_goal:
                        self.goal_pos_3d = (float(x), float(y), self.current_floor)
                        self.setting_goal = False
                    elif self.multi_robot_mode:
                        robot = self.multi_robot_coordinator.add_robot(float(x), float(y), self.current_floor)
                        self.robot_sim_manager.add_robot(float(x), float(y), self.current_floor)
                        print(f"添加机器人 #{robot.robot_id} 于 ({x:.0f}, {y:.0f}) F{self.current_floor}")
                else:
                    for name, btn in self.buttons.items():
                        if btn.is_clicked(event.pos):
                            self._handle_button_click(name)

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_s:
                self.setting_start = True
                self.setting_goal = False
            elif event.key == pygame.K_g:
                self.setting_goal = True
                self.setting_start = False
            elif event.key == pygame.K_p:
                self.plan_path_3d()
            elif event.key == pygame.K_a:
                self.animation_running = not self.animation_running

        return True

    def _handle_button_click(self, name: str) -> None:
        if name == 'floor_0':
            self.current_floor = 0
        elif name == 'floor_1':
            self.current_floor = 1
        elif name == 'floor_2':
            self.current_floor = 2
        elif name == 'mode_3d':
            self.multi_robot_mode = False
        elif name == 'mode_multi':
            self.multi_robot_mode = True
        elif name == 'set_start':
            self.setting_start = True
            self.setting_goal = False
        elif name == 'set_goal':
            self.setting_goal = True
            self.setting_start = False
        elif name == 'plan':
            if self.multi_robot_mode:
                self.plan_multi_robot()
            else:
                self.plan_path_3d()
        elif name == 'add_robot':
            x, y = 100 + np.random.randint(0, 200), 100 + np.random.randint(0, 200)
            robot = self.multi_robot_coordinator.add_robot(float(x), float(y), self.current_floor)
            self.robot_sim_manager.add_robot(float(x), float(y), self.current_floor)
            print(f"添加机器人 #{robot.robot_id} 于 ({x:.0f}, {y:.0f}) F{self.current_floor}")
        elif name == 'start_sim':
            self.animation_running = not self.animation_running
        elif name == 'clear_robots':
            self.multi_robot_coordinator = MultiRobotCoordinator(map3d=self.map3d)
            self.robot_sim_manager = RobotSimulationManager()
            print("清除所有机器人")

    def plan_path_3d(self) -> None:
        if self.start_pos_3d is None or self.goal_pos_3d is None:
            print("请先设置起点和终点!")
            return

        print(f"规划3D路径: F{self.start_pos_3d[2]}({self.start_pos_3d[0]:.0f}, {self.start_pos_3d[1]:.0f}) -> F{self.goal_pos_3d[2]}({self.goal_pos_3d[0]:.0f}, {self.goal_pos_3d[1]:.0f})")

        self.path_3d = self.astar3d.plan(self.start_pos_3d, self.goal_pos_3d)

        if self.path_3d:
            stats = self.astar3d.get_statistics()
            print(f"规划完成! 路径长度: {stats['path_length']:.1f}, 时间: {stats['planning_time']*1000:.1f}ms, 节点: {stats['nodes_expanded']}")

            floor_changes = []
            for i in range(1, len(self.path_3d)):
                if self.path_3d[i][2] != self.path_3d[i-1][2]:
                    floor_changes.append((self.path_3d[i-1][2], self.path_3d[i][2]))
            if floor_changes:
                print(f"楼层变化: {floor_changes}")
        else:
            print("未找到有效路径!")

    def plan_multi_robot(self) -> None:
        robots = self.multi_robot_coordinator.get_robot_states()
        if len(robots) < 1:
            print("请先添加机器人!")
            return

        goals = [
            (650.0, 550.0, 0),
            (100.0, 500.0, 1),
            (400.0, 300.0, 2),
        ]

        for i, robot in enumerate(robots):
            if i < len(goals):
                goal = goals[i]
                start = (robot.x, robot.y, robot.floor)
                path = self.astar3d.plan(start, goal)
                if path:
                    self.multi_robot_coordinator.set_robot_path(robot.robot_id, path)
                    sim_robot = self.robot_sim_manager.get_robot(robot.robot_id)
                    if sim_robot:
                        sim_robot.set_path(path)
                    print(f"机器人 #{robot.robot_id}: 规划路径完成, {len(path)} 个点")

        print(f"多机器人路径规划完成，共 {len(robots)} 个机器人")

    def update(self, dt: float) -> None:
        if self.animation_running:
            if self.multi_robot_mode:
                self.multi_robot_coordinator.update(dt)

                for robot_id, robot in self.multi_robot_coordinator.robots.items():
                    sim_robot = self.robot_sim_manager.get_robot(robot_id)
                    if sim_robot:
                        sim_robot.drive.set_pose(robot.x, robot.y, robot.theta)
                        sim_robot.floor = robot.floor

    def draw(self) -> None:
        floor_color = self.floor_colors[self.current_floor % len(self.floor_colors)]
        self.screen.fill(floor_color)

        self._draw_floor_grid()
        self._draw_obstacles()
        self._draw_connections()
        self._draw_3d_path()

        if self.multi_robot_mode:
            self._draw_multi_robots()
        else:
            self._draw_start_goal_3d()

        self._draw_sidebar()
        self._draw_floor_info()

        pygame.display.flip()

    def _draw_floor_grid(self) -> None:
        floor = self.map3d.get_floor(self.current_floor)
        if not floor:
            return

        for y_grid in range(floor.grid_map.grid_height):
            for x_grid in range(floor.grid_map.grid_width):
                if floor.grid_map.grid[y_grid, x_grid] == 1:
                    px = int(x_grid * floor.grid_map.resolution)
                    py = int(y_grid * floor.grid_map.resolution)
                    size = int(floor.grid_map.resolution)
                    pygame.draw.rect(self.screen, (80, 80, 80), (px, py, size, size))

    def _draw_obstacles(self) -> None:
        pass

    def _draw_connections(self) -> None:
        connections = self.map3d.get_connections_from_floor(self.current_floor)
        for conn in connections:
            if conn.floor1 == self.current_floor:
                pos = conn.pos1
            else:
                pos = conn.pos2

            target_floor = conn.floor2 if conn.floor1 == self.current_floor else conn.floor1

            color = (100, 200, 255) if conn.type == 'elevator' else (200, 150, 100)
            pygame.draw.circle(self.screen, color, (int(pos[0]), int(pos[1])), 20)
            pygame.draw.circle(self.screen, (50, 50, 50), (int(pos[0]), int(pos[1])), 20, 2)

            label = f"→F{target_floor}"
            text = self.font_small.render(label, True, (0, 0, 0))
            self.screen.blit(text, (pos[0] - 15, pos[1] - 8))

    def _draw_3d_path(self) -> None:
        if not self.path_3d:
            return

        path_on_floor = [(x, y) for x, y, f in self.path_3d if f == self.current_floor]

        if len(path_on_floor) >= 2:
            points = [(int(x), int(y)) for x, y in path_on_floor]
            pygame.draw.lines(self.screen, (255, 100, 50), False, points, 4)

            for i, (x, y) in enumerate(path_on_floor):
                if i % 5 == 0:
                    pygame.draw.circle(self.screen, (255, 100, 50), (int(x), int(y)), 5)

    def _draw_start_goal_3d(self) -> None:
        if self.start_pos_3d and self.start_pos_3d[2] == self.current_floor:
            x, y, _ = self.start_pos_3d
            pygame.draw.circle(self.screen, (0, 200, 0), (int(x), int(y)), 15)
            pygame.draw.circle(self.screen, (255, 255, 255), (int(x), int(y)), 8)
            text = self.font_small.render("S", True, (0, 0, 0))
            self.screen.blit(text, (x - 5, y - 10))

        if self.goal_pos_3d and self.goal_pos_3d[2] == self.current_floor:
            x, y, _ = self.goal_pos_3d
            pygame.draw.circle(self.screen, (200, 0, 0), (int(x), int(y)), 15)
            pygame.draw.circle(self.screen, (255, 255, 255), (int(x), int(y)), 8)
            text = self.font_small.render("G", True, (0, 0, 0))
            self.screen.blit(text, (x - 7, y - 10))

    def _draw_multi_robots(self) -> None:
        robots = self.multi_robot_coordinator.get_robot_states()

        for robot in robots:
            if robot.floor != self.current_floor:
                continue

            color = robot.color

            for i in range(robot.path_index, min(robot.path_index + 20, len(robot.path))):
                px, py, pf = robot.path[i]
                if pf == self.current_floor:
                    alpha = 255 - (i - robot.path_index) * 10
                    c = (min(255, color[0]), min(255, color[1]), min(255, color[2]))
                    pygame.draw.circle(self.screen, c, (int(px), int(py)), 4)

            pygame.draw.circle(self.screen, color, (int(robot.x), int(robot.y)), int(robot.radius))
            pygame.draw.circle(self.screen, (50, 50, 50), (int(robot.x), int(robot.y)), int(robot.radius), 2)

            dir_x = robot.x + np.cos(robot.theta) * robot.radius
            dir_y = robot.y + np.sin(robot.theta) * robot.radius
            pygame.draw.line(self.screen, (0, 0, 0),
                             (int(robot.x), int(robot.y)),
                             (int(dir_x), int(dir_y)), 3)

            id_text = self.font_small.render(f"#{robot.robot_id}", True, (0, 0, 0))
            self.screen.blit(id_text, (robot.x - 10, robot.y - 30))

            if robot.goal_reached:
                done_text = self.font_small.render("✓", True, (0, 150, 0))
                self.screen.blit(done_text, (robot.x + 15, robot.y - 10))

    def _draw_sidebar(self) -> None:
        sidebar_rect = pygame.Rect(self.map_width, 0, self.sidebar_width, self.height)
        pygame.draw.rect(self.screen, (50, 50, 50), sidebar_rect)
        pygame.draw.line(self.screen, (100, 100, 100),
                         (self.map_width, 0), (self.map_width, self.height), 2)

        for btn in self.buttons.values():
            btn.draw(self.screen, self.font_small)

        info_y = 450
        text_color = (200, 200, 200)

        status = "设置起点..." if self.setting_start else \
                 "设置终点..." if self.setting_goal else \
                 "就绪"
        status_text = self.font_small.render(f"状态: {status}", True, text_color)
        self.screen.blit(status_text, (self.map_width + 15, info_y))

        info_y += 30
        mode_text = "多机器人模式" if self.multi_robot_mode else "3D路径规划模式"
        mode_display = self.font_small.render(f"模式: {mode_text}", True, (150, 200, 255))
        self.screen.blit(mode_display, (self.map_width + 15, info_y))

        info_y += 30
        if self.multi_robot_mode:
            robot_count = len(self.multi_robot_coordinator.get_robot_states())
            count_text = self.font_small.render(f"机器人数量: {robot_count}", True, text_color)
            self.screen.blit(count_text, (self.map_width + 15, info_y))

            info_y += 25
            sim_status = "运行中" if self.animation_running else "已停止"
            sim_text = self.font_small.render(f"仿真: {sim_status}", True, (200, 150, 100))
            self.screen.blit(sim_text, (self.map_width + 15, info_y))
        elif self.path_3d:
            length = self.astar3d.path_length
            stats = self.astar3d.get_statistics()
            len_text = self.font_small.render(f"路径长度: {length:.1f}", True, (255, 200, 100))
            time_text = self.font_small.render(f"规划时间: {stats['planning_time']*1000:.1f}ms", True, (255, 200, 100))
            self.screen.blit(len_text, (self.map_width + 15, info_y))
            self.screen.blit(time_text, (self.map_width + 15, info_y + 25))

    def _draw_floor_info(self) -> None:
        floor = self.map3d.get_floor(self.current_floor)
        if floor:
            info_bg = pygame.Rect(10, 10, 150, 35)
            pygame.draw.rect(self.screen, (255, 255, 255, 200), info_bg)
            pygame.draw.rect(self.screen, (100, 100, 100), info_bg, 2)

            floor_text = self.font_medium.render(f" {floor.name}", True, (0, 0, 0))
            self.screen.blit(floor_text, (15, 15))

    def run(self) -> None:
        clock = pygame.time.Clock()
        running = True

        print("\n" + "=" * 50)
        print("3D多机器人路径规划可视化系统")
        print("=" * 50)
        print("快捷键:")
        print("  S - 设置起点")
        print("  G - 设置终点")
        print("  P - 开始规划")
        print("  A - 开始/停止仿真")
        print("  楼层按钮 - 切换楼层")
        print("=" * 50)

        while running:
            dt = clock.tick(60) / 1000.0

            for event in pygame.event.get():
                running = self.handle_event(event)
                if not running:
                    break

            self.update(dt)
            self.draw()

        pygame.quit()
        sys.exit()
