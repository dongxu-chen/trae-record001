import threading
from typing import Set, Tuple, Optional, Dict

import numpy as np

from grid import Grid, SparseGrid, DenseGrid, Boundary
from pattern import PATTERNS, center_pattern
from rule_parser import Rule, CONWAY, create_rule_from_string, VON_NEUMANN_NEIGHBORHOOD, DEFAULT_NEIGHBORHOOD

try:
    from numba import njit
    _NUMBA_AVAILABLE = True
except ImportError:
    _NUMBA_AVAILABLE = False
    def njit(*args, **kwargs):
        def decorator(func):
            return func
        return decorator


if _NUMBA_AVAILABLE:
    @njit
    def _step_numba(grid_in, grid_out, born_arr, survive_arr, is_periodic, width, height):
        for y in range(height):
            for x in range(width):
                count = 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        nx = x + dx
                        ny = y + dy
                        if is_periodic:
                            nx = nx % width
                            ny = ny % height
                        elif nx < 0 or nx >= width or ny < 0 or ny >= height:
                            continue
                        if grid_in[ny, nx]:
                            count += 1
                current = grid_in[y, x]
                if current:
                    grid_out[y, x] = count >= 0 and survive_arr[count]
                else:
                    grid_out[y, x] = count >= 0 and born_arr[count]


class GameOfLife:
    def __init__(
        self,
        grid: Optional[Grid] = None,
        rule: Optional[Rule] = None,
        use_numba: bool = False
    ) -> None:
        self.grid = grid if grid is not None else SparseGrid()
        self.rule = rule if rule is not None else CONWAY
        self.generation = 0
        self.use_numba = use_numba and _NUMBA_AVAILABLE
        self._step_lock = threading.Lock()
        self._worker_thread = None
        self._stop_flag = threading.Event()
        self._step_semaphore = threading.Semaphore(0)
        self._async_mode = False

    def enable_numba(self, enable: bool = True) -> None:
        self.use_numba = enable and _NUMBA_AVAILABLE

    @staticmethod
    def numba_available() -> bool:
        return _NUMBA_AVAILABLE

    def _build_rule_arrays(self) -> Tuple[np.ndarray, np.ndarray]:
        born = np.zeros(9, dtype=np.bool_)
        survive = np.zeros(9, dtype=np.bool_)
        for n in self.rule.born:
            if 0 <= n <= 8:
                born[n] = True
        for n in self.rule.survive:
            if 0 <= n <= 8:
                survive[n] = True
        return born, survive

    def _step_numba_fast(self) -> None:
        g = self.grid
        if not isinstance(g, DenseGrid):
            self._step_slow()
            return
        if self.rule.neighborhood != DEFAULT_NEIGHBORHOOD:
            self._step_slow()
            return
        if not _NUMBA_AVAILABLE or not self.use_numba:
            self._step_slow()
            return

        grid_arr = np.array(g._grid, dtype=np.bool_)
        out_arr = np.zeros_like(grid_arr)
        born_arr, survive_arr = self._build_rule_arrays()
        is_periodic = (g.boundary == Boundary.PERIODIC)

        _step_numba(
            grid_arr,
            out_arr,
            born_arr,
            survive_arr,
            is_periodic,
            g.width,
            g.height
        )

        for y in range(g.height):
            for x in range(g.width):
                g._grid[y][x] = bool(out_arr[y, x])
        self.generation += 1

    def _should_live(self, is_alive_now: bool, live_neighbors: int) -> bool:
        return self.rule.will_be_alive(is_alive_now, live_neighbors)

    def _step_slow(self) -> None:
        live_cells = self.grid.get_live_cells()
        neighbor_counts: Dict[Tuple[int, int], int] = {}

        for x, y in live_cells:
            for nx, ny in self.grid.get_neighbors(x, y):
                neighbor_counts[(nx, ny)] = neighbor_counts.get((nx, ny), 0) + 1

        changes = []

        for pos, count in neighbor_counts.items():
            is_alive_now = pos in live_cells
            next_alive = self._should_live(is_alive_now, count)
            if next_alive != is_alive_now:
                changes.append((pos[0], pos[1], next_alive))

        for x, y, alive in changes:
            self.grid.set_alive(x, y, alive)

        self.generation += 1

    def step(self) -> None:
        with self._step_lock:
            if self.use_numba and _NUMBA_AVAILABLE:
                try:
                    self._step_numba_fast()
                    return
                except Exception:
                    pass
            self._step_slow()

    def start_async(self) -> None:
        if self._async_mode:
            return
        self._async_mode = True
        self._stop_flag.clear()
        self._step_semaphore = threading.Semaphore(0)
        self._worker_thread = threading.Thread(target=self._async_worker, daemon=True)
        self._worker_thread.start()

    def stop_async(self) -> None:
        self._async_mode = False
        self._stop_flag.set()
        self._step_semaphore.release()
        if self._worker_thread is not None:
            self._worker_thread.join(timeout=1.0)
            self._worker_thread = None

    def queue_step(self) -> None:
        if self._async_mode:
            self._step_semaphore.release()

    def _async_worker(self) -> None:
        while not self._stop_flag.is_set():
            if self._step_semaphore.acquire(timeout=0.1):
                if self._stop_flag.is_set():
                    break
                self.step()

    def set_rule(self, rule: Rule) -> None:
        self.rule = rule

    def set_rule_from_string(self, rule_string: str) -> None:
        self.rule = create_rule_from_string(rule_string)

    def load_pattern(self, name: str, center_x: int = 0, center_y: int = 0) -> None:
        if name not in PATTERNS:
            raise ValueError(f"Unknown pattern: {name}")
        pattern = center_pattern(PATTERNS[name], center_x, center_y)
        self.grid.clear()
        self.grid.add_pattern(pattern)
        self.generation = 0

    def clear(self) -> None:
        self.grid.clear()
        self.generation = 0

    def get_live_cells(self) -> Set[Tuple[int, int]]:
        return self.grid.get_live_cells()

    def toggle_cell(self, x: int, y: int) -> None:
        self.grid.toggle(x, y)

    def to_numpy(self) -> Optional[np.ndarray]:
        g = self.grid
        if isinstance(g, DenseGrid):
            return np.array(g._grid, dtype=np.uint8) * 255
        return None

    def from_numpy(self, arr: np.ndarray) -> None:
        g = self.grid
        if isinstance(g, DenseGrid):
            if arr.shape != (g.height, g.width):
                raise ValueError(f"Array shape {arr.shape} does not match grid ({g.height}, {g.width})")
            for y in range(g.height):
                for x in range(g.width):
                    g._grid[y][x] = bool(arr[y, x])

    def __repr__(self) -> str:
        return (
            f"GameOfLife(generation={self.generation}, "
            f"live_cells={len(self.grid.get_live_cells())}, "
            f"rule={self.rule.to_string()})"
        )


def create_sparse_game(rule: Optional[Rule] = None) -> GameOfLife:
    return GameOfLife(SparseGrid(), rule=rule)


def create_dense_game(
    width: int,
    height: int,
    periodic: bool = False,
    rule: Optional[Rule] = None,
    use_numba: bool = True
) -> GameOfLife:
    boundary = Boundary.PERIODIC if periodic else Boundary.FIXED
    return GameOfLife(DenseGrid(width, height, boundary), rule=rule, use_numba=use_numba)
