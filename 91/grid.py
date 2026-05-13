from abc import ABC, abstractmethod
from enum import Enum
from typing import Set, Tuple, Iterable


class Boundary(Enum):
    FIXED = "fixed"
    PERIODIC = "periodic"


class Grid(ABC):
    @abstractmethod
    def is_alive(self, x: int, y: int) -> bool:
        pass

    @abstractmethod
    def set_alive(self, x: int, y: int, alive: bool) -> None:
        pass

    @abstractmethod
    def get_live_cells(self) -> Set[Tuple[int, int]]:
        pass

    @abstractmethod
    def get_neighbors(self, x: int, y: int) -> Iterable[Tuple[int, int]]:
        pass

    @abstractmethod
    def clear(self) -> None:
        pass

    def toggle(self, x: int, y: int) -> None:
        self.set_alive(x, y, not self.is_alive(x, y))

    def add_pattern(self, pattern: Set[Tuple[int, int]], offset_x: int = 0, offset_y: int = 0) -> None:
        for x, y in pattern:
            self.set_alive(x + offset_x, y + offset_y, True)


class SparseGrid(Grid):
    def __init__(self) -> None:
        self._live_cells: Set[Tuple[int, int]] = set()

    def is_alive(self, x: int, y: int) -> bool:
        return (x, y) in self._live_cells

    def set_alive(self, x: int, y: int, alive: bool) -> None:
        if alive:
            self._live_cells.add((x, y))
        else:
            self._live_cells.discard((x, y))

    def get_live_cells(self) -> Set[Tuple[int, int]]:
        return set(self._live_cells)

    def get_neighbors(self, x: int, y: int) -> Iterable[Tuple[int, int]]:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                yield (x + dx, y + dy)

    def clear(self) -> None:
        self._live_cells.clear()

    def __repr__(self) -> str:
        return f"SparseGrid(live_cells={len(self._live_cells)})"


class DenseGrid(Grid):
    def __init__(
        self,
        width: int,
        height: int,
        boundary: Boundary = Boundary.FIXED
    ) -> None:
        self.width = width
        self.height = height
        self.boundary = boundary
        self._grid = [[False for _ in range(width)] for _ in range(height)]

    def _wrap(self, x: int, y: int) -> Tuple[int, int]:
        if self.boundary == Boundary.PERIODIC:
            return x % self.width, y % self.height
        return x, y

    def _in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def is_alive(self, x: int, y: int) -> bool:
        x, y = self._wrap(x, y)
        if not self._in_bounds(x, y):
            return False
        return self._grid[y][x]

    def set_alive(self, x: int, y: int, alive: bool) -> None:
        x, y = self._wrap(x, y)
        if self._in_bounds(x, y):
            self._grid[y][x] = alive

    def get_live_cells(self) -> Set[Tuple[int, int]]:
        cells = set()
        for y in range(self.height):
            for x in range(self.width):
                if self._grid[y][x]:
                    cells.add((x, y))
        return cells

    def get_neighbors(self, x: int, y: int) -> Iterable[Tuple[int, int]]:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                nx, ny = x + dx, y + dy
                nx, ny = self._wrap(nx, ny)
                if self._in_bounds(nx, ny):
                    yield (nx, ny)

    def clear(self) -> None:
        for y in range(self.height):
            for x in range(self.width):
                self._grid[y][x] = False

    def __repr__(self) -> str:
        return f"DenseGrid(width={self.width}, height={self.height}, boundary={self.boundary})"
