import math
from typing import Dict, Tuple
from scipy.stats import poisson
from .utils import RestaurantConfig


class QueueingModel:
    def __init__(self, config: RestaurantConfig):
        self.config = config
        self.total_tables = (
            config.tables_2_seat + config.tables_4_seat + config.tables_6_seat
        )
        self.operating_hours = config.close_hour - config.open_hour

    def calculate_mm_c_metrics(
        self, arrival_rate: float, service_rate: float, num_servers: int
    ) -> Dict[str, float]:
        rho = arrival_rate / (num_servers * service_rate)

        if rho >= 1:
            rho = 0.95

        sum_terms = sum(
            [
                (arrival_rate / service_rate) ** k / math.factorial(k)
                for k in range(num_servers)
            ]
        )
        last_term = (arrival_rate / service_rate) ** num_servers / (
            math.factorial(num_servers) * (1 - rho)
        )
        P0 = 1 / (sum_terms + last_term)

        Lq = (
            P0
            * ((arrival_rate / service_rate) ** num_servers)
            * rho
            / (math.factorial(num_servers) * ((1 - rho) ** 2))
        )

        Wq = Lq / arrival_rate if arrival_rate > 0 else 0
        W = Wq + 1 / service_rate
        L = arrival_rate * W

        return {
            "utilization": rho,
            "avg_queue_length": Lq,
            "avg_wait_time": Wq * 60,
            "avg_system_time": W * 60,
            "avg_customers_in_system": L,
            "probability_waiting": last_term * P0,
        }

    def get_baseline_metrics(self) -> Dict[str, Dict]:
        metrics = {}

        for hour in range(self.config.open_hour, self.config.close_hour):
            peak_factor = 1.0
            if hour in self.config.peak_hours:
                peak_factor = self.config.peak_multiplier

            hourly_arrival_rate = self.config.arrival_rate * peak_factor
            service_rate = 60.0 / self.config.avg_dining_time

            metrics[f"{hour}:00"] = self.calculate_mm_c_metrics(
                hourly_arrival_rate, service_rate, self.total_tables
            )

        return metrics

    def calculate_expected_turnover(self) -> Tuple[float, float, float]:
        total_expected_customers = 0
        weighted_wait_time = 0

        for hour in range(self.config.open_hour, self.config.close_hour):
            peak_factor = 1.0
            if hour in self.config.peak_hours:
                peak_factor = self.config.peak_multiplier

            hourly_arrival_rate = self.config.arrival_rate * peak_factor
            total_expected_customers += hourly_arrival_rate * 60

            service_rate = 60.0 / self.config.avg_dining_time
            metrics = self.calculate_mm_c_metrics(
                hourly_arrival_rate, service_rate, self.total_tables
            )
            weighted_wait_time += metrics["avg_wait_time"]

        avg_wait_time = weighted_wait_time / self.operating_hours
        expected_turnover = total_expected_customers / self.total_tables

        return total_expected_customers, expected_turnover, avg_wait_time

    def predict_improvement(
        self,
        new_arrival_rate: float = None,
        new_service_rate: float = None,
        new_num_tables: int = None,
    ) -> Dict[str, float]:
        arrival_rate = (
            new_arrival_rate if new_arrival_rate else self.config.arrival_rate
        )
        service_rate = (
            new_service_rate
            if new_service_rate
            else 60.0 / self.config.avg_dining_time
        )
        num_tables = new_num_tables if new_num_tables else self.total_tables

        baseline = self.calculate_mm_c_metrics(
            self.config.arrival_rate,
            60.0 / self.config.avg_dining_time,
            self.total_tables,
        )
        optimized = self.calculate_mm_c_metrics(
            arrival_rate, service_rate, num_tables
        )

        return {
            "baseline_utilization": baseline["utilization"],
            "optimized_utilization": optimized["utilization"],
            "utilization_change": optimized["utilization"] - baseline["utilization"],
            "baseline_wait_time": baseline["avg_wait_time"],
            "optimized_wait_time": optimized["avg_wait_time"],
            "wait_time_reduction": baseline["avg_wait_time"]
            - optimized["avg_wait_time"],
            "turnover_improvement": (
                (optimized["avg_customers_in_system"] / baseline["avg_customers_in_system"])
                - 1
            )
            * 100,
        }
