from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
import numpy as np


@dataclass
class DishCategory:
    name: str
    avg_cook_time: float
    avg_eat_time: float
    price: float
    popularity: float


DEFAULT_DISHES = [
    DishCategory("快餐简餐", 8, 20, 35, 0.30),
    DishCategory("家常炒菜", 15, 35, 55, 0.25),
    DishCategory("火锅烧烤", 10, 60, 80, 0.15),
    DishCategory("宴席套餐", 25, 50, 120, 0.10),
    DishCategory("甜品饮品", 5, 15, 25, 0.20),
]


@dataclass
class ReservationConfig:
    reservation_rate: float = 0.25
    no_show_rate: float = 0.15
    late_arrival_rate: float = 0.20
    late_tolerance_minutes: float = 15.0


@dataclass
class RetentionConfig:
    wait_threshold: float = 20.0
    discount_rate: float = 0.10
    retention_success_rate: float = 0.65
    max_discounts_per_hour: int = 5


@dataclass
class RestaurantConfig:
    tables_2_seat: int = 10
    tables_4_seat: int = 8
    tables_6_seat: int = 4
    arrival_rate: float = 3.0
    avg_dining_time: float = 60.0
    std_dining_time: float = 15.0
    lognormal_weight: float = 0.7
    lognormal_mu: float = 4.0
    lognormal_sigma: float = 0.35
    exponential_scale: float = 30.0
    satisfaction_threshold: float = 15.0
    satisfaction_decay_rate: float = 0.05
    peak_hours: List[int] = field(default_factory=lambda: [11, 12, 13, 18, 19, 20])
    peak_multiplier: float = 2.0
    open_hour: int = 10
    close_hour: int = 22
    avg_spend_per_person: float = 80.0
    reservation_config: ReservationConfig = field(default_factory=ReservationConfig)
    retention_config: RetentionConfig = field(default_factory=RetentionConfig)
    dishes: List[DishCategory] = field(default_factory=lambda: list(DEFAULT_DISHES))


@dataclass
class SimulationResult:
    total_arrivals: int = 0
    total_served: int = 0
    total_lost: int = 0
    average_wait_time: float = 0.0
    median_wait_time: float = 0.0
    average_dining_time: float = 0.0
    table_turnover_rate: float = 0.0
    overall_utilization: float = 0.0
    table_utilization: Dict[int, List[float]] = field(default_factory=dict)
    hourly_arrivals: List[int] = field(default_factory=list)
    hourly_served: List[int] = field(default_factory=list)
    queue_length_history: List[Tuple[float, int]] = field(default_factory=list)
    wait_times: List[float] = field(default_factory=list)
    revenue: float = 0.0
    table_occupancy_timeline: Dict[int, List[Tuple[float, float, int]]] = field(
        default_factory=dict
    )
    strategy_name: str = ""
    satisfaction_score: float = 0.0
    satisfaction_scores: List[float] = field(default_factory=list)
    wait_time_penalty: float = 0.0
    net_benefit: float = 0.0
    hourly_satisfaction: List[float] = field(default_factory=list)
    state_change_events: List[Dict] = field(default_factory=list)
    total_reservations: int = 0
    reservation_no_shows: int = 0
    reservation_late_arrivals: int = 0
    reservation_show_rate: float = 0.0
    no_show_wasted_minutes: float = 0.0
    hourly_reservations: List[int] = field(default_factory=list)
    hourly_no_shows: List[int] = field(default_factory=list)
    retention_offers_sent: int = 0
    retention_offers_accepted: int = 0
    retention_success_rate: float = 0.0
    retention_revenue_saved: float = 0.0
    retention_discount_cost: float = 0.0
    dish_combination_impact: Dict[str, Dict] = field(default_factory=dict)
    dish_dining_time_correlation: List[Dict] = field(default_factory=list)
    no_show_impact_on_turnover: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "total_arrivals": self.total_arrivals,
            "total_served": self.total_served,
            "total_lost": self.total_lost,
            "average_wait_time": round(self.average_wait_time, 2),
            "median_wait_time": round(self.median_wait_time, 2),
            "average_dining_time": round(self.average_dining_time, 2),
            "table_turnover_rate": round(self.table_turnover_rate, 2),
            "overall_utilization": round(self.overall_utilization, 2),
            "revenue": round(self.revenue, 2),
            "satisfaction_score": round(self.satisfaction_score, 2),
            "wait_time_penalty": round(self.wait_time_penalty, 2),
            "net_benefit": round(self.net_benefit, 2),
            "strategy_name": self.strategy_name,
            "reservation_show_rate": round(self.reservation_show_rate, 2),
            "no_show_wasted_minutes": round(self.no_show_wasted_minutes, 1),
            "retention_success_rate": round(self.retention_success_rate, 2),
            "no_show_impact_on_turnover": round(self.no_show_impact_on_turnover, 2),
        }


def format_time(minutes: float) -> str:
    hours = int(minutes // 60)
    mins = int(minutes % 60)
    return f"{hours:02d}:{mins:02d}"


def calculate_turnover_rate(
    total_served: int, total_tables: int, operating_hours: float
) -> float:
    if total_tables == 0 or operating_hours == 0:
        return 0.0
    return total_served / (total_tables * operating_hours)


def get_peak_factor(current_hour: int, config: RestaurantConfig) -> float:
    if current_hour in config.peak_hours:
        return config.peak_multiplier
    return 1.0


def generate_group_size() -> int:
    sizes = [1, 2, 3, 4, 5, 6]
    probabilities = [0.15, 0.35, 0.25, 0.15, 0.07, 0.03]
    return np.random.choice(sizes, p=probabilities)


def generate_dining_time(config: RestaurantConfig) -> float:
    if np.random.random() < config.lognormal_weight:
        sample = np.random.lognormal(config.lognormal_mu, config.lognormal_sigma)
    else:
        sample = np.random.exponential(config.exponential_scale)
    return max(15.0, min(180.0, sample))


def calculate_satisfaction(wait_time: float, config: RestaurantConfig) -> float:
    if wait_time <= config.satisfaction_threshold:
        return 1.0
    excess = wait_time - config.satisfaction_threshold
    return max(0.0, 1.0 - config.satisfaction_decay_rate * excess)


def select_dish_combination(config: RestaurantConfig) -> Tuple[str, float, float]:
    dishes = config.dishes
    probs = [d.popularity for d in dishes]
    total = sum(probs)
    probs = [p / total for p in probs]

    idx = np.random.choice(len(dishes), p=probs)
    dish = dishes[idx]

    cook_var = np.random.normal(0, dish.avg_cook_time * 0.15)
    eat_var = np.random.normal(0, dish.avg_eat_time * 0.2)

    total_time = max(15.0, dish.avg_cook_time + cook_var + dish.avg_eat_time + eat_var)
    total_time = min(180.0, total_time)

    return dish.name, total_time, dish.price


def adjust_dining_time_by_dish(
    base_dining_time: float, dish_name: str, config: RestaurantConfig
) -> float:
    dish = None
    for d in config.dishes:
        if d.name == dish_name:
            dish = d
            break
    if dish is None:
        return base_dining_time

    dish_time_ratio = (dish.avg_cook_time + dish.avg_eat_time) / 55.0
    adjusted = base_dining_time * (0.4 + 0.6 * dish_time_ratio)
    return max(15.0, min(180.0, adjusted))
