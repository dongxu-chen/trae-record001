from abc import ABC, abstractmethod
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass


@dataclass
class Table:
    id: int
    capacity: int
    is_occupied: bool = False
    occupied_until: float = 0.0
    total_occupied_time: float = 0.0


class TableAssignmentStrategy(ABC):
    @abstractmethod
    def assign_table(
        self, group_size: int, tables: List[Table], current_time: float
    ) -> Optional[int]:
        pass

    @abstractmethod
    def get_name(self) -> str:
        pass


class FirstFitStrategy(TableAssignmentStrategy):
    def assign_table(
        self, group_size: int, tables: List[Table], current_time: float
    ) -> Optional[int]:
        for table in tables:
            if not table.is_occupied and table.capacity >= group_size:
                return table.id
        return None

    def get_name(self) -> str:
        return "首次匹配"


class BestFitStrategy(TableAssignmentStrategy):
    def assign_table(
        self, group_size: int, tables: List[Table], current_time: float
    ) -> Optional[int]:
        available_tables = [t for t in tables if not t.is_occupied and t.capacity >= group_size]

        if not available_tables:
            return None

        best_table = min(available_tables, key=lambda t: t.capacity - group_size)
        return best_table.id

    def get_name(self) -> str:
        return "最佳匹配"


class WorstFitStrategy(TableAssignmentStrategy):
    def assign_table(
        self, group_size: int, tables: List[Table], current_time: float
    ) -> Optional[int]:
        available_tables = [t for t in tables if not t.is_occupied and t.capacity >= group_size]

        if not available_tables:
            return None

        worst_table = max(available_tables, key=lambda t: t.capacity - group_size)
        return worst_table.id

    def get_name(self) -> str:
        return "最差匹配（大桌预留）"


class LoadBalancingStrategy(TableAssignmentStrategy):
    def assign_table(
        self, group_size: int, tables: List[Table], current_time: float
    ) -> Optional[int]:
        available_tables = [t for t in tables if not t.is_occupied and t.capacity >= group_size]

        if not available_tables:
            return None

        least_used = min(available_tables, key=lambda t: t.total_occupied_time)
        return least_used.id

    def get_name(self) -> str:
        return "负载均衡"


class TimeAwareStrategy(TableAssignmentStrategy):
    def __init__(self, look_ahead_minutes: float = 30):
        self.look_ahead_minutes = look_ahead_minutes

    def assign_table(
        self, group_size: int, tables: List[Table], current_time: float
    ) -> Optional[int]:
        soon_available = []
        for table in tables:
            if not table.is_occupied and table.capacity >= group_size:
                return table.id
            elif (
                table.is_occupied
                and table.capacity >= group_size
                and (table.occupied_until - current_time) <= self.look_ahead_minutes
            ):
                soon_available.append(table)

        return None

    def get_name(self) -> str:
        return "时间感知分配"


def create_tables(config) -> List[Table]:
    tables = []
    table_id = 1

    for _ in range(config.tables_2_seat):
        tables.append(Table(id=table_id, capacity=2))
        table_id += 1

    for _ in range(config.tables_4_seat):
        tables.append(Table(id=table_id, capacity=4))
        table_id += 1

    for _ in range(config.tables_6_seat):
        tables.append(Table(id=table_id, capacity=6))
        table_id += 1

    return tables


def get_available_tables(tables: List[Table]) -> List[Tuple[int, int]]:
    return [(t.id, t.capacity) for t in tables if not t.is_occupied]


def update_table_status(tables: List[Table], current_time: float) -> None:
    for table in tables:
        if table.is_occupied and table.occupied_until <= current_time:
            table.is_occupied = False


def get_table_by_id(tables: List[Table], table_id: int) -> Optional[Table]:
    for table in tables:
        if table.id == table_id:
            return table
    return None


def get_all_assignment_strategies() -> Dict[str, TableAssignmentStrategy]:
    return {
        "first_fit": FirstFitStrategy(),
        "best_fit": BestFitStrategy(),
        "worst_fit": WorstFitStrategy(),
        "load_balancing": LoadBalancingStrategy(),
        "time_aware": TimeAwareStrategy(),
    }
