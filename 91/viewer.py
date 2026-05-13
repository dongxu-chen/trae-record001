import os
import threading
from enum import Enum

import pygame

from game import (
    GameOfLife,
    create_sparse_game,
    create_dense_game
)
from pattern import list_patterns
from grid import DenseGrid, SparseGrid
from rule_parser import (
    Rule,
    CONWAY,
    list_builtin_rules,
    get_builtin_rule,
    parse_rule,
    is_valid_rule_string
)
from gif_exporter import pil_available


class Tool(Enum):
    PEN = "pen"
    ERASER = "eraser"
    LINE = "line"
    RECT = "rect"
    ELLIPSE = "ellipse"
    FLOOD = "flood"


class Viewer:
    def __init__(
        self,
        game: GameOfLife = None,
        width: int = 1200,
        height: int = 800,
        cell_size: int = 8,
        fps: int = 30
    ) -> None:
        pygame.init()
        self.game = game if game is not None else create_dense_game(
            width // cell_size,
            height // cell_size,
            periodic=True,
            use_numba=True
        )
        self.width = width
        self.height = height
        self.cell_size = cell_size
        self.fps = fps
        self.running = True
        self.paused = True
        self.grid_width = width // cell_size
        self.grid_height = height // cell_size
        self.offset_x = 0
        self.offset_y = 0
        self.dragging = False
        self.drag_state = None
        self.show_grid = True
        self.use_numba = True
        self.tool = Tool.PEN

        self.panning = False
        self.pan_start = None
        self.drag_start = None
        self.temp_line_pos = None

        self.rule_text = "B3/S23"
        self.rule_error = False
        self.editing_rule = False
        self._rule_input_buffer = ""

        self.exporting = False
        self.export_progress = 0.0
        self.export_thread = None

        self.BG_COLOR = (10, 10, 20)
        self.CELL_COLOR = (0, 255, 136)
        self.GRID_COLOR = (30, 30, 50)
        self.TEXT_COLOR = (200, 200, 200)
        self.TITLE_COLOR = (255, 255, 255)
        self.PANEL_COLOR = (20, 20, 40)
        self.PANEL_BORDER = (60, 60, 90)
        self.BUTTON_COLOR = (40, 40, 70)
        self.BUTTON_HOVER = (60, 60, 100)
        self.ACTIVE_COLOR = (0, 200, 100)

        self.panel_width = 300
        self.main_width = width - self.panel_width

        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Conway's Game of Life - Extended")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Consolas", 12)
        self.title_font = pygame.font.SysFont("Consolas", 18, bold=True)
        self.small_font = pygame.font.SysFont("Consolas", 10)

        self._init_ui_state()

    def _init_ui_state(self):
        self._builtin_rule_index = 0
        self._tool_buttons = [
            ("Pen", Tool.PEN, pygame.K_1),
            ("Eraser", Tool.ERASER, pygame.K_2),
            ("Line", Tool.LINE, pygame.K_3),
            ("Rect", Tool.RECT, pygame.K_4),
            ("Ellipse", Tool.ELLIPSE, pygame.K_5),
            ("Flood", Tool.FLOOD, pygame.K_6),
        ]

    def screen_to_grid(self, screen_x: int, screen_y: int):
        grid_x = screen_x // self.cell_size - self.offset_x
        grid_y = screen_y // self.cell_size - self.offset_y
        return grid_x, grid_y

    def grid_to_screen(self, grid_x: int, grid_y: int):
        screen_x = (grid_x + self.offset_x) * self.cell_size
        screen_y = (grid_y + self.offset_y) * self.cell_size
        return screen_x, screen_y

    def _paint_cell(self, grid_x: int, grid_y: int, alive: bool):
        self.game.grid.set_alive(grid_x, grid_y, alive)

    def _flood_fill(self, start_x: int, start_y: int, target_alive: bool):
        g = self.game.grid
        if isinstance(g, SparseGrid):
            return
        width, height = g.width, g.height
        start_state = g.is_alive(start_x, start_y)
        if start_state == target_alive:
            return
        stack = [(start_x, start_y)]
        while stack:
            x, y = stack.pop()
            if 0 <= x < width and 0 <= y < height:
                if g.is_alive(x, y) == start_state:
                    g.set_alive(x, y, target_alive)
                    stack.append((x + 1, y))
                    stack.append((x - 1, y))
                    stack.append((x, y + 1))
                    stack.append((x, y - 1))

    def _draw_line(self, x0: int, y0: int, x1: int, y1: int, alive: bool):
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            self._paint_cell(x0, y0, alive)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def _draw_rect(self, x0: int, y0: int, x1: int, y1: int, alive: bool, fill: bool = False):
        min_x, max_x = min(x0, x1), max(x0, x1)
        min_y, max_y = min(y0, y1), max(y0, y1)
        if fill:
            for y in range(min_y, max_y + 1):
                for x in range(min_x, max_x + 1):
                    self._paint_cell(x, y, alive)
        else:
            self._draw_line(min_x, min_y, max_x, min_y, alive)
            self._draw_line(min_x, max_y, max_x, max_y, alive)
            self._draw_line(min_x, min_y, min_x, max_y, alive)
            self._draw_line(max_x, min_y, max_x, max_y, alive)

    def _draw_ellipse(self, x0: int, y0: int, x1: int, y1: int, alive: bool):
        cx = (x0 + x1) // 2
        cy = (y0 + y1) // 2
        rx = abs(x1 - x0) // 2
        ry = abs(y1 - y0) // 2
        if rx == 0 and ry == 0:
            self._paint_cell(cx, cy, alive)
            return
        rx2 = rx * rx
        ry2 = ry * ry
        x, y = 0, ry
        p = ry2 - rx2 * ry + (rx2 // 4)
        while 2 * ry2 * x <= 2 * rx2 * y:
            self._paint_symmetric(cx, cy, x, y, alive)
            if p < 0:
                x += 1
                p += 2 * ry2 * x + ry2
            else:
                x += 1
                y -= 1
                p += 2 * ry2 * x + ry2 - 2 * rx2 * y
        p = ry2 * (x + 0.5) * (x + 0.5) + rx2 * (y - 1) * (y - 1) - rx2 * ry2
        while y >= 0:
            self._paint_symmetric(cx, cy, x, y, alive)
            if p > 0:
                y -= 1
                p -= 2 * rx2 * y + rx2
            else:
                y -= 1
                x += 1
                p += 2 * ry2 * x - 2 * rx2 * y + rx2

    def _paint_symmetric(self, cx: int, cy: int, x: int, y: int, alive: bool):
        self._paint_cell(cx + x, cy + y, alive)
        self._paint_cell(cx - x, cy + y, alive)
        self._paint_cell(cx + x, cy - y, alive)
        self._paint_cell(cx - x, cy - y, alive)

    def draw_grid(self):
        if not self.show_grid:
            return
        for x in range(0, self.main_width, self.cell_size):
            pygame.draw.line(self.screen, self.GRID_COLOR, (x, 0), (x, self.height))
        for y in range(0, self.height, self.cell_size):
            pygame.draw.line(self.screen, self.GRID_COLOR, (0, y), (self.main_width, y))

    def draw_cells(self):
        live_cells = self.game.get_live_cells()
        for x, y in live_cells:
            screen_x, screen_y = self.grid_to_screen(x, y)
            if 0 <= screen_x < self.main_width and 0 <= screen_y < self.height:
                rect = pygame.Rect(
                    screen_x + 1,
                    screen_y + 1,
                    self.cell_size - 2,
                    self.cell_size - 2
                )
                pygame.draw.rect(self.screen, self.CELL_COLOR, rect)

    def _get_boundary_text(self):
        g = self.game.grid
        if isinstance(g, DenseGrid):
            return f"{g.boundary.value}"
        return "infinite"

    def _text(self, text: str, x: int, y: int, color=None, font=None):
        if font is None:
            font = self.font
        if color is None:
            color = self.TEXT_COLOR
        surface = font.render(text, True, color)
        self.screen.blit(surface, (x, y))
        return surface.get_width()

    def _button(self, rect, label: str, active: bool = False):
        mouse = pygame.mouse.get_pos()
        hover = rect.collidepoint(mouse)
        color = self.ACTIVE_COLOR if active else (self.BUTTON_HOVER if hover else self.BUTTON_COLOR)
        pygame.draw.rect(self.screen, color, rect)
        pygame.draw.rect(self.screen, self.PANEL_BORDER, rect, 1)
        text_surf = self.small_font.render(label, True, self.TITLE_COLOR)
        tx = rect.x + (rect.width - text_surf.get_width()) // 2
        ty = rect.y + (rect.height - text_surf.get_height()) // 2
        self.screen.blit(text_surf, (tx, ty))
        return hover and pygame.mouse.get_pressed()[0]

    def draw_panel(self):
        px = self.main_width
        pygame.draw.rect(self.screen, self.PANEL_COLOR, (px, 0, self.panel_width, self.height))
        pygame.draw.line(self.screen, self.PANEL_BORDER, (px, 0), (px, self.height), 2)

        y = 10
        self._text("Game of Life", px + 10, y, color=self.TITLE_COLOR, font=self.title_font)
        y += 25

        status = "PAUSED" if self.paused else "RUNNING"
        status_color = (255, 200, 0) if self.paused else (0, 255, 100)
        self._text(status, px + 10, y, color=status_color)
        y += 20

        info_lines = [
            f"Gen: {self.game.generation}",
            f"Live: {len(self.game.get_live_cells())}",
            f"FPS: {int(self.clock.get_fps())}",
            f"Zoom: {self.cell_size}x",
            f"Grid: {'Dense' if isinstance(self.game.grid, DenseGrid) else 'Sparse'}",
            f"Boundary: {self._get_boundary_text()}",
            f"Numba: {'ON' if self.use_numba and self.game.numba_available() else 'OFF'}",
        ]
        for line in info_lines:
            self._text(line, px + 10, y)
            y += 16

        y += 10
        self._text("Control Buttons", px + 10, y, color=self.TITLE_COLOR)
        y += 18

        btn_w = 90
        btn_h = 26
        buttons_row1 = [
            ("Play/Stop", self._toggle_play),
            ("Step (.)", self._do_step),
            ("Clear", self.game.clear),
        ]
        buttons_row2 = [
            ("Random (R)", self.randomize),
            ("Grid (G)", self._toggle_grid),
            ("Numba (N)", self._toggle_numba),
        ]
        for i, (label, _) in enumerate(buttons_row1):
            rect = pygame.Rect(px + 10 + i * (btn_w + 4), y, btn_w, btn_h)
            if self._button(rect, label, active=self._button_active_for(label)):
                pass
        y += btn_h + 6
        for i, (label, _) in enumerate(buttons_row2):
            rect = pygame.Rect(px + 10 + i * (btn_w + 4), y, btn_w, btn_h)
            self._button(rect, label)
        y += btn_h + 12

        self._text("Drawing Tools", px + 10, y, color=self.TITLE_COLOR)
        y += 18
        tool_btn_w = 46
        tool_btn_h = 26
        for i, (label, tool, _) in enumerate(self._tool_buttons):
            col = i % 3
            row = i // 3
            bx = px + 10 + col * (tool_btn_w + 4)
            by = y + row * (tool_btn_h + 4)
            rect = pygame.Rect(bx, by, tool_btn_w, tool_btn_h)
            self._button(rect, label, active=(self.tool == tool))
        y += (tool_btn_h + 4) * 2 + 8

        self._text("Rules", px + 10, y, color=self.TITLE_COLOR)
        y += 18
        self._text("Built-in (Alt+Left/Right):", px + 10, y)
        y += 16
        rules = list_builtin_rules()
        idx = self._builtin_rule_index % len(rules)
        selected_rule_name = rules[idx]
        self._text(f"  {selected_rule_name}", px + 10, y, color=self.ACTIVE_COLOR)
        y += 18

        self._text("Custom (Bx/Sy) (U: apply):", px + 10, y)
        y += 16
        rule_rect = pygame.Rect(px + 10, y, self.panel_width - 20, 24)
        rule_color = (255, 80, 80) if self.rule_error else (255, 255, 255)
        if self.editing_rule:
            rule_color = (255, 220, 100)
        pygame.draw.rect(self.screen, (50, 50, 80), rule_rect)
        pygame.draw.rect(self.screen, self.PANEL_BORDER, rule_rect, 1)
        display_text = self._rule_input_buffer if self.editing_rule else self.rule_text
        self._text(display_text, px + 14, y + 5, color=rule_color)
        y += 30

        self._text(f"Current: {self.game.rule.to_string()}", px + 10, y)
        y += 20

        self._text("Grid Type", px + 10, y, color=self.TITLE_COLOR)
        y += 18
        grid_buttons = [
            ("Sparse (Tab)", lambda: self._switch_to_sparse()),
            ("Dense Fix (Q)", lambda: self._switch_to_dense(False)),
            ("Dense Per (E)", lambda: self._switch_to_dense(True)),
        ]
        small_btn_w = 90
        for i, (label, _) in enumerate(grid_buttons):
            rect = pygame.Rect(px + 10 + i * (small_btn_w + 4), y, small_btn_w, 24)
            self._button(rect, label)
        y += 34

        if pil_available():
            self._text("GIF Export (V)", px + 10, y, color=self.TITLE_COLOR)
            y += 18
            if self.exporting:
                pct = int(self.export_progress * 100)
                bar_w = self.panel_width - 20
                bar_rect = pygame.Rect(px + 10, y, bar_w, 18)
                pygame.draw.rect(self.screen, (50, 50, 80), bar_rect)
                fill = int(bar_w * self.export_progress)
                pygame.draw.rect(self.screen, self.ACTIVE_COLOR, (px + 10, y, fill, 18))
                pygame.draw.rect(self.screen, self.PANEL_BORDER, bar_rect, 1)
                self._text(f"Exporting... {pct}%", px + 14, y + 3)
                y += 24
            else:
                btn = pygame.Rect(px + 10, y, self.panel_width - 20, 28)
                self._button(btn, "Export 200-frame GIF")
        else:
            self._text("GIF Export:", px + 10, y, color=self.TITLE_COLOR)
            y += 18
            self._text("  pip install Pillow", px + 10, y, color=(255, 120, 120))
            y += 16

    def _button_active_for(self, label: str) -> bool:
        if "Play" in label:
            return not self.paused
        return False

    def _toggle_play(self):
        self.paused = not self.paused

    def _do_step(self):
        if self.paused:
            self.game.step()

    def _toggle_grid(self):
        self.show_grid = not self.show_grid

    def _toggle_numba(self):
        self.use_numba = not self.use_numba
        self.game.enable_numba(self.use_numba)

    def _switch_to_dense(self, periodic: bool):
        g = self.game.grid
        current_cells = g.get_live_cells()
        gw = self.grid_width
        gh = self.grid_height
        new_game = create_dense_game(gw, gh, periodic=periodic, use_numba=self.use_numba)
        new_game.set_rule(self.game.rule)
        offset_x = gw // 2
        offset_y = gh // 2
        for x, y in current_cells:
            new_game.grid.set_alive(x + offset_x, y + offset_y, True)
        self.game = new_game
        self.offset_x = 0
        self.offset_y = 0

    def _switch_to_sparse(self):
        g = self.game.grid
        if isinstance(g, SparseGrid):
            return
        current_cells = g.get_live_cells()
        new_game = create_sparse_game(rule=self.game.rule)
        offset_x = g.width // 2
        offset_y = g.height // 2
        for x, y in current_cells:
            new_game.grid.set_alive(x - offset_x, y - offset_y, True)
        self.game = new_game
        self.offset_x = self.grid_width // 2
        self.offset_y = self.grid_height // 2

    def randomize(self):
        import random
        self.game.clear()
        density = 0.2
        g = self.game.grid
        if isinstance(g, DenseGrid):
            for y in range(g.height):
                for x in range(g.width):
                    if random.random() < density:
                        self.game.toggle_cell(x, y)
        else:
            for x in range(-self.grid_width // 2, self.grid_width // 2):
                for y in range(-self.grid_height // 2, self.grid_height // 2):
                    if random.random() < density:
                        self.game.toggle_cell(x, y)

    def load_pattern_by_index(self, index: int):
        patterns = list_patterns()
        if 0 <= index < len(patterns):
            self.game.load_pattern(patterns[index], self.grid_width // 2, self.grid_height // 2)

    def _apply_rule_string(self):
        if is_valid_rule_string(self._rule_input_buffer):
            self.rule_text = self._rule_input_buffer.upper()
            self.rule_error = False
            self.game.set_rule(parse_rule(self.rule_text))
        else:
            self.rule_error = True
        self.editing_rule = False

    def _select_builtin_rule(self, index: int):
        rules = list_builtin_rules()
        idx = index % len(rules)
        rule = get_builtin_rule(rules[idx])
        self.game.set_rule(rule)
        self.rule_text = rule.to_string()
        self._rule_input_buffer = self.rule_text
        self._builtin_rule_index = idx
        self.rule_error = False

    def _start_gif_export(self):
        if not pil_available() or self.exporting:
            return
        if not isinstance(self.game.grid, DenseGrid):
            return

        self.exporting = True
        self.export_progress = 0.0
        saved_state = (self.paused, list(self.game.get_live_cells()), self.game.generation)
        output_path = os.path.join(os.getcwd(), "game_of_life.gif")

        def worker():
            try:
                from gif_exporter import GifExporter
                steps = 200
                exporter = GifExporter(output_path, fps=15, scale=2)
                self.export_progress = 0.01
                for i in range(steps):
                    frame = self.game.to_numpy()
                    if frame is not None:
                        exporter.add_frame_from_grid(frame)
                    self.game.step()
                    self.export_progress = (i + 1) / steps
                exporter.save()
            except Exception:
                pass
            finally:
                self.exporting = False
                self.export_progress = 0.0
                self.paused = saved_state[0]

        self.export_thread = threading.Thread(target=worker, daemon=True)
        self.export_thread.start()

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            self.running = False

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSPACE:
                if self.editing_rule:
                    self._rule_input_buffer = self._rule_input_buffer[:-1]
                return

            if event.key == pygame.K_ESCAPE:
                if self.editing_rule:
                    self.editing_rule = False
                    self._rule_input_buffer = self.rule_text
                    self.rule_error = False
                return

            if event.key == pygame.K_RETURN:
                if self.editing_rule:
                    self._apply_rule_string()
                return

            if self.editing_rule:
                c = event.unicode
                if c and c.upper() in "B/S0123456789":
                    self._rule_input_buffer += c.upper()
                return

            if event.key == pygame.K_SPACE:
                self.paused = not self.paused
            elif event.key == pygame.K_PERIOD:
                if self.paused:
                    self.game.step()
            elif event.key == pygame.K_c:
                self.game.clear()
            elif event.key == pygame.K_r:
                self.randomize()
            elif event.key == pygame.K_g:
                self.show_grid = not self.show_grid
            elif event.key == pygame.K_n:
                self._toggle_numba()
            elif event.key == pygame.K_w:
                self.offset_y += 5
            elif event.key == pygame.K_s:
                self.offset_y -= 5
            elif event.key == pygame.K_a:
                self.offset_x += 5
            elif event.key == pygame.K_d:
                self.offset_x -= 5
            elif event.key in (pygame.K_EQUALS, pygame.K_KP_PLUS):
                self.cell_size = min(self.cell_size + 1, 32)
                self.grid_width = self.main_width // self.cell_size
                self.grid_height = self.height // self.cell_size
            elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                self.cell_size = max(self.cell_size - 1, 2)
                self.grid_width = self.main_width // self.cell_size
                self.grid_height = self.height // self.cell_size
            elif pygame.K_0 <= event.key <= pygame.K_9:
                self.load_pattern_by_index(event.key - pygame.K_0)
            elif event.key == pygame.K_q:
                self._switch_to_dense(periodic=False)
            elif event.key == pygame.K_e:
                self._switch_to_dense(periodic=True)
            elif event.key == pygame.K_TAB:
                self._switch_to_sparse()
            elif event.key == pygame.K_1:
                self.tool = Tool.PEN
            elif event.key == pygame.K_2:
                self.tool = Tool.ERASER
            elif event.key == pygame.K_3:
                self.tool = Tool.LINE
            elif event.key == pygame.K_4:
                self.tool = Tool.RECT
            elif event.key == pygame.K_5:
                self.tool = Tool.ELLIPSE
            elif event.key == pygame.K_6:
                self.tool = Tool.FLOOD
            elif event.key == pygame.K_u:
                if is_valid_rule_string(self.rule_text):
                    self.game.set_rule(parse_rule(self.rule_text))
            elif event.key == pygame.K_LEFT and pygame.key.get_mods() & pygame.KMOD_ALT:
                self._select_builtin_rule(self._builtin_rule_index - 1)
            elif event.key == pygame.K_RIGHT and pygame.key.get_mods() & pygame.KMOD_ALT:
                self._select_builtin_rule(self._builtin_rule_index + 1)
            elif event.key == pygame.K_v:
                self._start_gif_export()

        elif event.type == pygame.MOUSEBUTTONDOWN:
            x, y = event.pos

            if x >= self.main_width:
                self._handle_panel_click(event)
                return

            if event.button == 1:
                gx, gy = self.screen_to_grid(x, y)
                if self.tool == Tool.PEN:
                    self.dragging = True
                    original = self.game.grid.is_alive(gx, gy)
                    self.drag_state = not original
                    self.game.toggle_cell(gx, gy)
                elif self.tool == Tool.ERASER:
                    self.dragging = True
                    self.drag_state = False
                    self._paint_cell(gx, gy, False)
                elif self.tool in (Tool.LINE, Tool.RECT, Tool.ELLIPSE):
                    self.drag_start = (gx, gy)
                    self.temp_line_pos = (gx, gy)
                elif self.tool == Tool.FLOOD:
                    self._flood_fill(gx, gy, True)
            elif event.button == 3:
                self.panning = True
                self.pan_start = (x, y, self.offset_x, self.offset_y)
            elif event.button == 4:
                self.cell_size = min(self.cell_size + 1, 32)
                self.grid_width = self.main_width // self.cell_size
                self.grid_height = self.height // self.cell_size
            elif event.button == 5:
                self.cell_size = max(self.cell_size - 1, 2)
                self.grid_width = self.main_width // self.cell_size
                self.grid_height = self.height // self.cell_size

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                if self.drag_start is not None and self.temp_line_pos is not None:
                    x0, y0 = self.drag_start
                    x1, y1 = self.temp_line_pos
                    alive = True
                    if self.tool == Tool.LINE:
                        self._draw_line(x0, y0, x1, y1, alive)
                    elif self.tool == Tool.RECT:
                        keys = pygame.key.get_pressed()
                        self._draw_rect(x0, y0, x1, y1, alive, fill=keys[pygame.K_LSHIFT])
                    elif self.tool == Tool.ELLIPSE:
                        self._draw_ellipse(x0, y0, x1, y1, alive)
                self.drag_start = None
                self.temp_line_pos = None
                self.dragging = False
                self.drag_state = None
            elif event.button == 3:
                self.panning = False
                self.pan_start = None

        elif event.type == pygame.MOUSEMOTION:
            x, y = event.pos
            if x >= self.main_width:
                return
            if self.panning and self.pan_start is not None:
                sx, sy, ox, oy = self.pan_start
                self.offset_x = ox + (x - sx) // self.cell_size
                self.offset_y = oy + (y - sy) // self.cell_size
            elif self.dragging and self.drag_state is not None:
                gx, gy = self.screen_to_grid(x, y)
                self._paint_cell(gx, gy, self.drag_state)
            elif self.drag_start is not None:
                self.temp_line_pos = self.screen_to_grid(x, y)

    def _handle_panel_click(self, event):
        px = self.main_width
        x, y = event.pos
        bx = x - px

        btn_w = 90
        btn_h = 26
        button_rows = [
            [("Play/Stop", self._toggle_play), ("Step (.)", self._do_step), ("Clear", self.game.clear)],
            [("Random (R)", self.randomize), ("Grid (G)", self._toggle_grid), ("Numba (N)", self._toggle_numba)],
        ]
        base_y = 170
        for row_idx, row in enumerate(button_rows):
            for col_idx, (label, action) in enumerate(row):
                rx = 10 + col_idx * (btn_w + 4)
                ry = base_y + row_idx * (btn_h + 6)
                rect = pygame.Rect(rx, ry, btn_w, btn_h)
                if rect.collidepoint((bx, y)):
                    action()
                    return

        tool_btn_w = 46
        tool_btn_h = 26
        tool_base_y = 272
        for i, (_, tool, _) in enumerate(self._tool_buttons):
            col = i % 3
            row = i // 3
            rx = 10 + col * (tool_btn_w + 4)
            ry = tool_base_y + row * (tool_btn_h + 4)
            rect = pygame.Rect(rx, ry, tool_btn_w, tool_btn_h)
            if rect.collidepoint((bx, y)):
                self.tool = tool
                return

        rule_rect = pygame.Rect(10, 368, self.panel_width - 20, 24)
        if rule_rect.collidepoint((bx, y)):
            self.editing_rule = True
            self._rule_input_buffer = self.rule_text
            self.rule_error = False
            return

        small_btn_w = 90
        grid_base_y = 456
        grid_actions = [
            ("Sparse (Tab)", lambda: self._switch_to_sparse()),
            ("Dense Fix (Q)", lambda: self._switch_to_dense(False)),
            ("Dense Per (E)", lambda: self._switch_to_dense(True)),
        ]
        for i, (_, action) in enumerate(grid_actions):
            rx = 10 + i * (small_btn_w + 4)
            rect = pygame.Rect(rx, grid_base_y, small_btn_w, 24)
            if rect.collidepoint((bx, y)):
                action()
                return

        if pil_available() and not self.exporting:
            export_btn = pygame.Rect(10, 516, self.panel_width - 20, 28)
            if export_btn.collidepoint((bx, y)):
                self._start_gif_export()

    def run(self):
        while self.running:
            for event in pygame.event.get():
                self.handle_event(event)

            if not self.paused:
                self.game.step()

            self.screen.fill(self.BG_COLOR)
            self.draw_grid()
            self.draw_cells()
            self._draw_preview()
            self.draw_panel()
            pygame.display.flip()
            self.clock.tick(self.fps)

        pygame.quit()

    def _draw_preview(self):
        if self.drag_start is None or self.temp_line_pos is None:
            return
        if self.tool not in (Tool.LINE, Tool.RECT, Tool.ELLIPSE):
            return
        x0, y0 = self.grid_to_screen(self.drag_start[0], self.drag_start[1])
        x1, y1 = self.grid_to_screen(self.temp_line_pos[0], self.temp_line_pos[1])
        color = (255, 255, 100)
        if self.tool == Tool.LINE:
            pygame.draw.line(self.screen, color, (x0, y0), (x1, y1), 2)
        elif self.tool == Tool.RECT:
            keys = pygame.key.get_pressed()
            rx = min(x0, x1)
            ry = min(y0, y1)
            rw = abs(x1 - x0) + self.cell_size
            rh = abs(y1 - y0) + self.cell_size
            if keys[pygame.K_LSHIFT]:
                pygame.draw.rect(self.screen, (*color, 100), (rx, ry, rw, rh), 0)
            pygame.draw.rect(self.screen, color, (rx, ry, rw, rh), 2)
        elif self.tool == Tool.ELLIPSE:
            rx = min(x0, x1)
            ry = min(y0, y1)
            rw = abs(x1 - x0) + self.cell_size
            rh = abs(y1 - y0) + self.cell_size
            pygame.draw.ellipse(self.screen, color, (rx, ry, rw, rh), 2)


def main():
    viewer = Viewer()
    viewer.run()


if __name__ == "__main__":
    main()
