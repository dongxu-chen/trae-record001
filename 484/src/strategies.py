from abc import ABC, abstractmethod
from typing import List, Tuple, Dict, Any
from dataclasses import dataclass


@dataclass
class CustomerGroup:
    id: int
    arrival_time: float
    size: int
    dining_time: float
    wait_time: float = 0.0
    table_id: int = -1
    is_reservation: bool = False
    dish_name: str = ""
    dish_price: float = 0.0
    retention_offered: bool = False
    retention_accepted: bool = False


class QueueStrategy(ABC):
    @abstractmethod
    def select_next_group(
        self, queue: List[CustomerGroup], available_tables: List[Tuple[int, int]]
    ) -> Tuple[CustomerGroup, int]:
        pass

    @abstractmethod
    def get_name(self) -> str:
        pass


class FIFOStrategy(QueueStrategy):
    def select_next_group(
        self, queue: List[CustomerGroup], available_tables: List[Tuple[int, int]]
    ) -> Tuple[CustomerGroup, int]:
        if not queue or not available_tables:
            return None, -1

        for group in queue:
            for table_id, table_capacity in available_tables:
                if group.size <= table_capacity:
                    return group, table_id

        return None, -1

    def get_name(self) -> str:
        return "先来先服务 (FIFO)"


class SizeMatchStrategy(QueueStrategy):
    def select_next_group(
        self, queue: List[CustomerGroup], available_tables: List[Tuple[int, int]]
    ) -> Tuple[CustomerGroup, int]:
        if not queue or not available_tables:
            return None, -1

        sorted_tables = sorted(available_tables, key=lambda x: x[1])

        for table_id, table_capacity in sorted_tables:
            matching_groups = [g for g in queue if g.size <= table_capacity]
            if matching_groups:
                best_group = min(
                    matching_groups, key=lambda g: (table_capacity - g.size, g.arrival_time)
                )
                return best_group, table_id

        return None, -1

    def get_name(self) -> str:
        return "大小匹配优先"


class DynamicPriorityStrategy(QueueStrategy):
    def __init__(self, wait_weight: float = 0.6, size_weight: float = 0.4):
        self.wait_weight = wait_weight
        self.size_weight = size_weight

    def select_next_group(
        self, queue: List[CustomerGroup], available_tables: List[Tuple[int, int]]
    ) -> Tuple[CustomerGroup, int]:
        if not queue or not available_tables:
            return None, -1

        current_time = max(g.arrival_time + g.wait_time for g in queue) if queue else 0
        max_wait = max(current_time - g.arrival_time for g in queue) if queue else 1
        max_size = max(g.size for g in queue) if queue else 1

        if max_wait == 0:
            max_wait = 1.0
        if max_size == 0:
            max_size = 1

        best_score = -1
        best_pair = (None, -1)

        for table_id, table_capacity in available_tables:
            for group in queue:
                if group.size <= table_capacity:
                    normalized_wait = (current_time - group.arrival_time) / max_wait
                    normalized_size = group.size / max_size
                    fit_score = 1 - (table_capacity - group.size) / 6

                    score = (
                        self.wait_weight * normalized_wait
                        + self.size_weight * normalized_size * fit_score
                    )

                    if score > best_score:
                        best_score = score
                        best_pair = (group, table_id)

        return best_pair

    def get_name(self) -> str:
        return "动态优先级策略"


class ShortestWaitFirstStrategy(QueueStrategy):
    def __init__(self, max_estimated_dining: float = 90):
        self.max_estimated_dining = max_estimated_dining

    def select_next_group(
        self, queue: List[CustomerGroup], available_tables: List[Tuple[int, int]]
    ) -> Tuple[CustomerGroup, int]:
        if not queue or not available_tables:
            return None, -1

        sorted_tables = sorted(available_tables, key=lambda x: x[1])
        sorted_queue = sorted(queue, key=lambda g: g.dining_time)

        for table_id, table_capacity in sorted_tables:
            for group in sorted_queue:
                if group.size <= table_capacity:
                    return group, table_id

        return None, -1

    def get_name(self) -> str:
        return "短用餐时间优先"


class SmartRetentionStrategy(QueueStrategy):
    def __init__(
        self,
        wait_threshold: float = 20.0,
        retention_success_rate: float = 0.65,
    ):
        self.wait_threshold = wait_threshold
        self.retention_success_rate = retention_success_rate
        self.retention_log: List[Dict] = []

    def select_next_group(
        self, queue: List[CustomerGroup], available_tables: List[Tuple[int, int]]
    ) -> Tuple[CustomerGroup, int]:
        if not queue or not available_tables:
            return None, -1

        for group in queue:
            wait = group.wait_time if group.wait_time > 0 else 0
            if wait >= self.wait_threshold and not group.retention_offered:
                group.retention_offered = True
                if np.random.random() < self.retention_success_rate:
                    group.retention_accepted = True
                    self.retention_log.append({
                        "group_id": group.id,
                        "wait_time": wait,
                        "accepted": True,
                    })
                else:
                    self.retention_log.append({
                        "group_id": group.id,
                        "wait_time": wait,
                        "accepted": False,
                    })

        sorted_tables = sorted(available_tables, key=lambda x: x[1])

        for table_id, table_capacity in sorted_tables:
            matching = [g for g in queue if g.size <= table_capacity]
            if matching:
                prioritized = sorted(
                    matching,
                    key=lambda g: (
                        -int(g.retention_accepted),
                        -int(g.is_reservation),
                        g.arrival_time,
                    ),
                )
                return prioritized[0], table_id

        return None, -1

    def get_name(self) -> str:
        return "智能挽留策略"


def get_all_strategies() -> Dict[str, QueueStrategy]:
    return {
        "fifo": FIFOStrategy(),
        "size_match": SizeMatchStrategy(),
        "dynamic": DynamicPriorityStrategy(),
        "shortest": ShortestWaitFirstStrategy(),
        "smart_retention": SmartRetentionStrategy(),
    }
