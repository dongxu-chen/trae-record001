import pygame
import numpy as np
import sys
from typing import List, Tuple, Dict, Optional
from map import GridMap
from obstacles import ObstacleManager, DynamicObstacle
from astar import AStar, HeuristicType
from rrt import RRT
from rrt_star import RRTStar
from replanner import IncrementalReplanner


class Button:
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


class PathPlannerVisualizer:
    def __init__(self, width: int = 1000, height: int = 700):
        pygame.init()
        self.width = width
        self.height = height
        self.sidebar_width = 250
        self.map_width = width - self.sidebar_width
        self.map_height = height

        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("机器人路径规划可视化")

        self.font_small = pygame.font.Font(None, 20)
        self.font_medium = pygame.font.Font(None, 24)
        self.font_large = pygame.font.Font(None, 32)

        self.grid_map = GridMap(self.map_width, self.map_height, resolution=5.0)
        self.obstacle_manager = ObstacleManager()

        self.start_pos: Optional[Tuple[float, float]] = None
        self.goal_pos: Optional[Tuple[float, float]] = None

        self.current_algorithm = 'astar'
        self.paths: Dict[str, List[Tuple[float, float]]] = {}
        self.path_colors = {
            'astar': (255, 0, 0),
            'rrt': (0, 255, 0),
            'rrt_star': (0, 0, 255)
        }

        self.statistics: Dict[str, dict] = {}

        self.rrt_tree_edges: List = []
        self.rrt_star_tree_edges: List = []
        self.show_tree = False

        self.planner_astar = AStar(self.grid_map, self.obstacle_manager)
        self.planner_rrt = RRT(self.grid_map, self.obstacle_manager)
        self.planner_rrt_star = RRTStar(self.grid_map, self.obstacle_manager, use_dynamic_radius=True)

        self.robot_radius = 8.0
        self.planner_astar.robot_radius = self.robot_radius
        self.planner_rrt.robot_radius = self.robot_radius
        self.planner_rrt_star.robot_radius = self.robot_radius

        self.setting_start = False
        self.setting_goal = False
        self.drawing_obstacle = False
        self.obstacle_start = None
        self.animation_running = False

        self.astar_heuristic = HeuristicType.OCTILE
        self.rrtstar_dynamic_radius = True

        self.use_incremental_replan = False
        self.incremental_replanner = IncrementalReplanner(self.grid_map, self.obstacle_manager)
        self.robot_position = None
        self.replan_count = 0

        self._init_buttons()
        self._init_sample_map()

    def _init_buttons(self) -> None:
        btn_y = 20
        btn_height = 32
        btn_width = self.sidebar_width - 40
        small_btn_width = (self.sidebar_width - 50) // 2
        btn_x = 10

        self.buttons = {
            'set_start': Button(btn_x, btn_y, btn_width, btn_height, "设置起点 (S)"),
            'set_goal': Button(btn_x, btn_y + 38, btn_width, btn_height, "设置终点 (G)"),
            'draw_obstacle': Button(btn_x, btn_y + 76, btn_width, btn_height, "绘制障碍物 (D)"),
            'clear_obstacles': Button(btn_x, btn_y + 114, btn_width, btn_height, "清除障碍物 (C)"),
        }

        algo_y = btn_y + 160
        self.buttons.update({
            'astar': Button(btn_x, algo_y, btn_width, btn_height, "A* 算法", color=(100, 50, 50)),
            'rrt': Button(btn_x, algo_y + 38, btn_width, btn_height, "RRT 算法", color=(50, 100, 50)),
            'rrt_star': Button(btn_x, algo_y + 76, btn_width, btn_height, "RRT* 算法", color=(50, 50, 100)),
        })

        heuristic_y = algo_y + 120
        self.buttons.update({
            'heuristic_label': Button(btn_x, heuristic_y, btn_width, btn_height, "A* 启发函数:", color=(60, 60, 60)),
            'heuristic_manhattan': Button(btn_x, heuristic_y + 38, small_btn_width, btn_height, "曼哈顿", color=(80, 60, 60)),
            'heuristic_euclidean': Button(btn_x + small_btn_width + 10, heuristic_y + 38, small_btn_width, btn_height, "欧氏", color=(80, 60, 60)),
            'heuristic_chebyshev': Button(btn_x, heuristic_y + 76, small_btn_width, btn_height, "切比雪夫", color=(80, 60, 60)),
            'heuristic_octile': Button(btn_x + small_btn_width + 10, heuristic_y + 76, small_btn_width, btn_height, "Octile", color=(80, 60, 60)),
        })

        feature_y = heuristic_y + 120
        self.buttons.update({
            'dynamic_radius': Button(btn_x, feature_y, btn_width, btn_height, "RRT*动态半径: 开", color=(60, 80, 60)),
            'incremental_replan': Button(btn_x, feature_y + 38, btn_width, btn_height, "增量重规划: 关", color=(60, 60, 80)),
        })

        plan_y = feature_y + 85
        self.buttons.update({
            'plan': Button(btn_x, plan_y, btn_width, btn_height, "开始规划 (P)", color=(50, 150, 50)),
            'compare': Button(btn_x, plan_y + 38, btn_width, btn_height, "对比所有算法", color=(100, 100, 50)),
            'toggle_tree': Button(btn_x, plan_y + 76, btn_width, btn_height, "显示/隐藏树 (T)"),
        })

        self.buttons.update({
            'add_dynamic': Button(btn_x, plan_y + 120, btn_width, btn_height, "添加动态障碍"),
            'toggle_animation': Button(btn_x, plan_y + 158, btn_width, btn_height, "开始/停止动画 (A)"),
            'clear_paths': Button(btn_x, plan_y + 196, btn_width, btn_height, "清除路径 (X)"),
        })

    def _init_sample_map(self) -> None:
        obstacles = [
            {'type': 'rectangle', 'x': 150, 'y': 100, 'width': 60, 'height': 200},
            {'type': 'rectangle', 'x': 350, 'y': 50, 'width': 50, 'height': 150},
            {'type': 'rectangle', 'x': 350, 'y': 300, 'width': 50, 'height': 200},
            {'type': 'rectangle', 'x': 500, 'y': 150, 'width': 80, 'height': 80},
            {'type': 'circle', 'x': 250, 'y': 450, 'radius': 40},
            {'type': 'polygon', 'vertices': [[600, 350], [650, 300], [700, 350], [680, 420], [620, 420]]},
        ]

        for obs in obstacles:
            if obs['type'] == 'rectangle':
                self.grid_map._add_rectangle_obstacle(obs)
            elif obs['type'] == 'circle':
                self.grid_map._add_circle_obstacle(obs)
            elif obs['type'] == 'polygon':
                self.grid_map._add_polygon_obstacle(obs)

        self.start_pos = (50.0, 50.0)
        self.goal_pos = (700.0, 500.0)

        dynamic_obs1 = self.obstacle_manager.add_dynamic_obstacle(
            'circle', x=300, y=250, radius=20
        )
        dynamic_obs1.set_waypoints([(300, 250), (300, 450), (200, 450), (200, 250)], speed=80)

        dynamic_obs2 = self.obstacle_manager.add_dynamic_obstacle(
            'rectangle', x=550, y=200, width=30, height=30
        )
        dynamic_obs2.set_waypoints([(550, 200), (550, 400), (450, 400), (450, 200)], speed=60)

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
                        self.start_pos = (float(x), float(y))
                        self.setting_start = False
                    elif self.setting_goal:
                        self.goal_pos = (float(x), float(y))
                        self.setting_goal = False
                    elif self.drawing_obstacle:
                        self.obstacle_start = (x, y)
                else:
                    for name, btn in self.buttons.items():
                        if btn.is_clicked(event.pos):
                            self._handle_button_click(name)

        if event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1 and self.drawing_obstacle and self.obstacle_start:
                x, y = event.pos
                if x < self.map_width:
                    x1, y1 = self.obstacle_start
                    x2, y2 = x, y
                    min_x, max_x = min(x1, x2), max(x1, x2)
                    min_y, max_y = min(y1, y2), max(y1, y2)
                    obs = {
                        'type': 'rectangle',
                        'x': min_x,
                        'y': min_y,
                        'width': max_x - min_x,
                        'height': max_y - min_y
                    }
                    self.grid_map._add_rectangle_obstacle(obs)
                self.obstacle_start = None

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_s:
                self.setting_start = True
                self.setting_goal = False
                self.drawing_obstacle = False
            elif event.key == pygame.K_g:
                self.setting_goal = True
                self.setting_start = False
                self.drawing_obstacle = False
            elif event.key == pygame.K_d:
                self.drawing_obstacle = True
                self.setting_start = False
                self.setting_goal = False
            elif event.key == pygame.K_c:
                self.grid_map = GridMap(self.map_width, self.map_height, resolution=5.0)
                self.planner_astar.grid_map = self.grid_map
                self.planner_rrt.grid_map = self.grid_map
                self.planner_rrt_star.grid_map = self.grid_map
            elif event.key == pygame.K_p:
                self.plan_path()
            elif event.key == pygame.K_a:
                self.animation_running = not self.animation_running
            elif event.key == pygame.K_t:
                self.show_tree = not self.show_tree
            elif event.key == pygame.K_x:
                self.paths = {}
                self.statistics = {}
                self.rrt_tree_edges = []
                self.rrt_star_tree_edges = []

        return True

    def _handle_button_click(self, name: str) -> None:
        if name == 'set_start':
            self.setting_start = True
            self.setting_goal = False
            self.drawing_obstacle = False
        elif name == 'set_goal':
            self.setting_goal = True
            self.setting_start = False
            self.drawing_obstacle = False
        elif name == 'draw_obstacle':
            self.drawing_obstacle = True
            self.setting_start = False
            self.setting_goal = False
        elif name == 'clear_obstacles':
            self.grid_map = GridMap(self.map_width, self.map_height, resolution=5.0)
            self.planner_astar.grid_map = self.grid_map
            self.planner_rrt.grid_map = self.grid_map
            self.planner_rrt_star.grid_map = self.grid_map
            self.incremental_replanner = IncrementalReplanner(self.grid_map, self.obstacle_manager)
        elif name == 'astar':
            self.current_algorithm = 'astar'
        elif name == 'rrt':
            self.current_algorithm = 'rrt'
        elif name == 'rrt_star':
            self.current_algorithm = 'rrt_star'
        elif name == 'heuristic_manhattan':
            self.astar_heuristic = HeuristicType.MANHATTAN
            self.planner_astar.set_heuristic(HeuristicType.MANHATTAN)
        elif name == 'heuristic_euclidean':
            self.astar_heuristic = HeuristicType.EUCLIDEAN
            self.planner_astar.set_heuristic(HeuristicType.EUCLIDEAN)
        elif name == 'heuristic_chebyshev':
            self.astar_heuristic = HeuristicType.CHEBYSHEV
            self.planner_astar.set_heuristic(HeuristicType.CHEBYSHEV)
        elif name == 'heuristic_octile':
            self.astar_heuristic = HeuristicType.OCTILE
            self.planner_astar.set_heuristic(HeuristicType.OCTILE)
        elif name == 'dynamic_radius':
            self.rrtstar_dynamic_radius = not self.rrtstar_dynamic_radius
            self.planner_rrt_star.use_dynamic_radius = self.rrtstar_dynamic_radius
            status = "开" if self.rrtstar_dynamic_radius else "关"
            self.buttons['dynamic_radius'].text = f"RRT*动态半径: {status}"
        elif name == 'incremental_replan':
            self.use_incremental_replan = not self.use_incremental_replan
            status = "开" if self.use_incremental_replan else "关"
            self.buttons['incremental_replan'].text = f"增量重规划: {status}"
            if self.use_incremental_replan and self.start_pos and self.goal_pos:
                self.incremental_replanner.set_active_algorithm(self.current_algorithm)
                self.incremental_replanner.plan_path(self.start_pos, self.goal_pos)
                self.robot_position = self.start_pos
        elif name == 'plan':
            self.plan_path()
        elif name == 'compare':
            self.compare_algorithms()
        elif name == 'toggle_tree':
            self.show_tree = not self.show_tree
        elif name == 'add_dynamic':
            obs = self.obstacle_manager.add_dynamic_obstacle(
                'circle', x=400, y=300, radius=15
            )
            obs.set_waypoints([(400, 300), (400, 500), (600, 500), (600, 300)], speed=70)
        elif name == 'toggle_animation':
            self.animation_running = not self.animation_running
        elif name == 'clear_paths':
            self.paths = {}
            self.statistics = {}
            self.rrt_tree_edges = []
            self.rrt_star_tree_edges = []
            self.replan_count = 0

    def plan_path(self) -> None:
        if self.start_pos is None or self.goal_pos is None:
            print("请先设置起点和终点!")
            return

        if self.use_incremental_replan:
            print(f"使用增量重规划 ({self.current_algorithm})...")
            self.incremental_replanner.set_active_algorithm(self.current_algorithm)
            path = self.incremental_replanner.plan_path(self.start_pos, self.goal_pos)
            self.robot_position = self.start_pos
            self.paths[self.current_algorithm] = path
            self.replan_count = 0
            if path:
                print(f"完成! 路径长度: {len(path)} 个点")
            return

        print(f"使用 {self.current_algorithm} 规划路径...")

        if self.current_algorithm == 'astar':
            path = self.planner_astar.plan(self.start_pos, self.goal_pos)
            if path:
                path = self.planner_astar.smooth_path(path)
            self.paths['astar'] = path
            self.statistics['astar'] = self.planner_astar.get_statistics()
        elif self.current_algorithm == 'rrt':
            path = self.planner_rrt.plan(self.start_pos, self.goal_pos)
            if path:
                path = self.planner_rrt.smooth_path(path)
            self.paths['rrt'] = path
            self.rrt_tree_edges = self.planner_rrt.get_tree_edges()
            self.statistics['rrt'] = self.planner_rrt.get_statistics()
        elif self.current_algorithm == 'rrt_star':
            path = self.planner_rrt_star.plan(self.start_pos, self.goal_pos)
            if path:
                path = self.planner_rrt_star.smooth_path(path)
            self.paths['rrt_star'] = path
            self.rrt_star_tree_edges = self.planner_rrt_star.get_tree_edges()
            self.statistics['rrt_star'] = self.planner_rrt_star.get_statistics()

        print(f"完成! 路径长度: {self.statistics.get(self.current_algorithm, {}).get('path_length', 0):.2f}")

    def compare_algorithms(self) -> None:
        if self.start_pos is None or self.goal_pos is None:
            print("请先设置起点和终点!")
            return

        print("对比所有算法...")
        self.paths = {}
        self.statistics = {}

        path_astar = self.planner_astar.plan(self.start_pos, self.goal_pos)
        if path_astar:
            path_astar = self.planner_astar.smooth_path(path_astar)
        self.paths['astar'] = path_astar
        self.statistics['astar'] = self.planner_astar.get_statistics()

        path_rrt = self.planner_rrt.plan(self.start_pos, self.goal_pos)
        if path_rrt:
            path_rrt = self.planner_rrt.smooth_path(path_rrt)
        self.paths['rrt'] = path_rrt
        self.rrt_tree_edges = self.planner_rrt.get_tree_edges()
        self.statistics['rrt'] = self.planner_rrt.get_statistics()

        path_rrt_star = self.planner_rrt_star.plan(self.start_pos, self.goal_pos)
        if path_rrt_star:
            path_rrt_star = self.planner_rrt_star.smooth_path(path_rrt_star)
        self.paths['rrt_star'] = path_rrt_star
        self.rrt_star_tree_edges = self.planner_rrt_star.get_tree_edges()
        self.statistics['rrt_star'] = self.planner_rrt_star.get_statistics()

        print("\n=== 算法对比结果 ===")
        for algo, stats in self.statistics.items():
            print(f"{algo}: 时间={stats['planning_time']*1000:.1f}ms, 长度={stats['path_length']:.1f}")

    def update(self, dt: float) -> None:
        if self.animation_running:
            self.obstacle_manager.update_all(dt)

        if self.use_incremental_replan and self.robot_position and self.animation_running:
            path, replanned = self.incremental_replanner.update(self.robot_position, dt)
            if path:
                self.paths[self.current_algorithm] = path
            if replanned:
                self.replan_count += 1
                print(f"增量重规划 #{self.replan_count} 完成")

            if path and len(path) > 1:
                self._simulate_robot_movement(dt)

    def _simulate_robot_movement(self, dt: float, speed: float = 80.0) -> None:
        path = self.incremental_replanner.get_path()
        if not path or len(path) < 2:
            return

        waypoint = self.incremental_replanner.replanners[self.current_algorithm].current_waypoint_index
        if waypoint >= len(path):
            return

        target_x, target_y = path[waypoint]
        dx = target_x - self.robot_position[0]
        dy = target_y - self.robot_position[1]
        dist = np.sqrt(dx * dx + dy * dy)

        if dist > 5.0:
            move_x = dx / dist * speed * dt
            move_y = dy / dist * speed * dt
            self.robot_position = (
                self.robot_position[0] + move_x,
                self.robot_position[1] + move_y
            )

    def draw(self) -> None:
        self.screen.fill((240, 240, 240))

        self._draw_grid()
        self._draw_obstacles()
        self._draw_dynamic_obstacles()

        if self.show_tree:
            self._draw_trees()

        self._draw_paths()
        self._draw_start_goal()

        if self.use_incremental_replan and self.robot_position:
            self._draw_robot()

        self._draw_sidebar()

        pygame.display.flip()

    def _draw_robot(self) -> None:
        pygame.draw.circle(self.screen, (100, 150, 255),
                           (int(self.robot_position[0]), int(self.robot_position[1])),
                           int(self.robot_radius))
        pygame.draw.circle(self.screen, (50, 100, 200),
                           (int(self.robot_position[0]), int(self.robot_position[1])),
                           int(self.robot_radius), 2)

    def _draw_grid(self) -> None:
        grid_surface = pygame.Surface((self.map_width, self.map_height), pygame.SRCALPHA)

        for y in range(self.grid_map.grid_height):
            for x in range(self.grid_map.grid_width):
                if self.grid_map.grid[y, x] == 1:
                    px = int(x * self.grid_map.resolution)
                    py = int(y * self.grid_map.resolution)
                    size = int(self.grid_map.resolution)
                    pygame.draw.rect(grid_surface, (80, 80, 80), (px, py, size, size))

        self.screen.blit(grid_surface, (0, 0))

    def _draw_obstacles(self) -> None:
        pass

    def _draw_dynamic_obstacles(self) -> None:
        for obs in self.obstacle_manager.dynamic_obstacles:
            if obs.shape == 'circle':
                pygame.draw.circle(self.screen, (255, 100, 100),
                                   (int(obs.position[0]), int(obs.position[1])),
                                   int(obs.radius))
                pygame.draw.circle(self.screen, (200, 50, 50),
                                   (int(obs.position[0]), int(obs.position[1])),
                                   int(obs.radius), 2)
            elif obs.shape == 'rectangle':
                rect = pygame.Rect(
                    int(obs.position[0] - obs.width / 2),
                    int(obs.position[1] - obs.height / 2),
                    int(obs.width),
                    int(obs.height)
                )
                pygame.draw.rect(self.screen, (255, 100, 100), rect)
                pygame.draw.rect(self.screen, (200, 50, 50), rect, 2)

    def _draw_trees(self) -> None:
        for edge in self.rrt_tree_edges:
            (x1, y1), (x2, y2) = edge
            pygame.draw.line(self.screen, (150, 255, 150), (int(x1), int(y1)), (int(x2), int(y2)), 1)

        for edge in self.rrt_star_tree_edges:
            (x1, y1), (x2, y2) = edge
            pygame.draw.line(self.screen, (150, 150, 255), (int(x1), int(y1)), (int(x2), int(y2)), 1)

    def _draw_paths(self) -> None:
        for algo, path in self.paths.items():
            if len(path) < 2:
                continue

            color = self.path_colors[algo]

            points = [(int(x), int(y)) for x, y in path]
            pygame.draw.lines(self.screen, color, False, points, 3)

            for i, (x, y) in enumerate(path):
                if i % 10 == 0:
                    pygame.draw.circle(self.screen, color, (int(x), int(y)), 4)

    def _draw_start_goal(self) -> None:
        if self.start_pos:
            pygame.draw.circle(self.screen, (0, 200, 0),
                               (int(self.start_pos[0]), int(self.start_pos[1])), 12)
            pygame.draw.circle(self.screen, (255, 255, 255),
                               (int(self.start_pos[0]), int(self.start_pos[1])), 6)
            text = self.font_small.render("S", True, (0, 0, 0))
            self.screen.blit(text, (self.start_pos[0] - 4, self.start_pos[1] - 8))

        if self.goal_pos:
            pygame.draw.circle(self.screen, (200, 0, 0),
                               (int(self.goal_pos[0]), int(self.goal_pos[1])), 12)
            pygame.draw.circle(self.screen, (255, 255, 255),
                               (int(self.goal_pos[0]), int(self.goal_pos[1])), 6)
            text = self.font_small.render("G", True, (0, 0, 0))
            self.screen.blit(text, (self.goal_pos[0] - 6, self.goal_pos[1] - 8))

    def _draw_sidebar(self) -> None:
        sidebar_rect = pygame.Rect(self.map_width, 0, self.sidebar_width, self.height)
        pygame.draw.rect(self.screen, (50, 50, 50), sidebar_rect)
        pygame.draw.line(self.screen, (100, 100, 100),
                         (self.map_width, 0), (self.map_width, self.height), 2)

        for btn in self.buttons.values():
            btn.draw(self.screen, self.font_small)

        info_y = 550
        text_color = (200, 200, 200)

        if self.setting_start:
            status = "点击地图设置起点"
        elif self.setting_goal:
            status = "点击地图设置终点"
        elif self.drawing_obstacle:
            status = "拖拽绘制矩形障碍"
        else:
            status = "就绪"

        status_text = self.font_small.render(f"状态: {status}", True, text_color)
        self.screen.blit(status_text, (self.map_width + 10, info_y))

        if self.use_incremental_replan:
            info_y += 25
            replan_text = self.font_small.render(f"重规划次数: {self.replan_count}", True, (100, 200, 255))
            self.screen.blit(replan_text, (self.map_width + 10, info_y))

        info_y += 30
        if self.statistics:
            title = self.font_medium.render("=== 统计信息 ===", True, (255, 200, 100))
            self.screen.blit(title, (self.map_width + 10, info_y))
            info_y += 25

            for algo, stats in self.statistics.items():
                if algo in self.paths and len(self.paths[algo]) > 0:
                    color = self.path_colors[algo]
                    algo_name = {'astar': 'A*', 'rrt': 'RRT', 'rrt_star': 'RRT*'}[algo]
                    text = self.font_small.render(
                        f"{algo_name}: {stats['path_length']:.1f}px, {stats['planning_time']*1000:.1f}ms",
                        True, color
                    )
                    self.screen.blit(text, (self.map_width + 10, info_y))
                    info_y += 20

        if self.current_algorithm == 'astar' and self.astar_heuristic:
            info_y += 10
            heuristic_name = {
                HeuristicType.MANHATTAN: '曼哈顿',
                HeuristicType.EUCLIDEAN: '欧氏',
                HeuristicType.CHEBYSHEV: '切比雪夫',
                HeuristicType.OCTILE: 'Octile'
            }.get(self.astar_heuristic, '未知')
            heur_text = self.font_small.render(f"启发函数: {heuristic_name}", True, (200, 200, 100))
            self.screen.blit(heur_text, (self.map_width + 10, info_y))

    def run(self) -> None:
        clock = pygame.time.Clock()
        running = True

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
