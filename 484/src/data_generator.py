import numpy as np
import pandas as pd
from typing import List, Dict, Tuple
from .utils import (
    RestaurantConfig,
    generate_group_size,
    generate_dining_time,
    select_dish_combination,
    adjust_dining_time_by_dish,
)


class RestaurantDataGenerator:
    def __init__(self, config: RestaurantConfig):
        self.config = config
        np.random.seed(42)

    def generate_daily_arrivals(self) -> List[Tuple[float, int, float, str, float]]:
        arrivals = []
        current_time = self.config.open_hour * 60
        end_time = self.config.close_hour * 60

        while current_time < end_time:
            current_hour = int(current_time // 60)
            peak_factor = 1.0
            if current_hour in self.config.peak_hours:
                peak_factor = self.config.peak_multiplier

            inter_arrival_time = np.random.exponential(
                60.0 / (self.config.arrival_rate * peak_factor)
            )
            current_time += inter_arrival_time

            if current_time >= end_time:
                break

            group_size = generate_group_size()
            base_dining_time = generate_dining_time(self.config)

            dish_name, dish_time, dish_price = select_dish_combination(self.config)
            dining_time = adjust_dining_time_by_dish(
                base_dining_time, dish_name, self.config
            )

            is_reservation = np.random.random() < self.config.reservation_config.reservation_rate

            arrivals.append(
                (current_time, group_size, dining_time, dish_name, dish_price, is_reservation)
            )

        return arrivals

    def generate_reservations(self) -> List[Dict]:
        res_config = self.config.reservation_config
        reservations = []
        res_id = 0

        for hour in range(self.config.open_hour, self.config.close_hour):
            peak_factor = 1.0
            if hour in self.config.peak_hours:
                peak_factor = self.config.peak_multiplier

            num_reservations = np.random.poisson(
                self.config.arrival_rate * peak_factor * res_config.reservation_rate
            )

            for _ in range(num_reservations):
                minute_offset = np.random.randint(0, 60)
                reserved_time = hour * 60 + minute_offset
                group_size = generate_group_size()
                dish_name, _, dish_price = select_dish_combination(self.config)

                is_no_show = np.random.random() < res_config.no_show_rate
                is_late = (not is_no_show) and (
                    np.random.random() < res_config.late_arrival_rate
                )

                actual_arrival = None
                if not is_no_show:
                    if is_late:
                        late_minutes = np.random.exponential(10)
                        actual_arrival = reserved_time + late_minutes
                    else:
                        actual_arrival = reserved_time + np.random.normal(0, 3)

                reservations.append(
                    {
                        "id": res_id,
                        "reserved_time": reserved_time,
                        "group_size": group_size,
                        "is_no_show": is_no_show,
                        "is_late": is_late,
                        "actual_arrival": actual_arrival,
                        "dish_name": dish_name,
                        "dish_price": dish_price,
                    }
                )
                res_id += 1

        return reservations

    def generate_dish_analysis_data(self, days: int = 7) -> pd.DataFrame:
        all_data = []

        for day in range(days):
            daily = self.generate_daily_arrivals()
            for arr_time, group_size, dining_time, dish_name, dish_price, is_res in daily:
                hour = int(arr_time // 60)
                all_data.append(
                    {
                        "day": day + 1,
                        "arrival_time": arr_time,
                        "hour": hour,
                        "group_size": group_size,
                        "dining_time": dining_time,
                        "dish_name": dish_name,
                        "dish_price": dish_price,
                        "is_reservation": is_res,
                        "is_peak": hour in self.config.peak_hours,
                    }
                )

        return pd.DataFrame(all_data)

    def generate_historical_data(self, days: int = 7) -> pd.DataFrame:
        all_data = []

        for day in range(days):
            daily_arrivals = self.generate_daily_arrivals()

            for idx, item in enumerate(daily_arrivals):
                arr_time, group_size, dining_time, dish_name, dish_price, is_res = item
                hour = int(arr_time // 60)
                all_data.append(
                    {
                        "day": day + 1,
                        "arrival_time_minutes": arr_time,
                        "arrival_hour": hour,
                        "group_size": group_size,
                        "dining_time_minutes": dining_time,
                        "dish_name": dish_name,
                        "dish_price": dish_price,
                        "is_reservation": is_res,
                        "is_peak_hour": hour in self.config.peak_hours,
                    }
                )

        return pd.DataFrame(all_data)

    def generate_hourly_statistics(self, days: int = 7) -> Dict[str, List]:
        df = self.generate_historical_data(days)

        hourly_stats = {
            "hour": [],
            "avg_arrivals": [],
            "avg_group_size": [],
            "avg_dining_time": [],
            "total_groups": [],
        }

        for hour in range(self.config.open_hour, self.config.close_hour):
            hour_data = df[df["arrival_hour"] == hour]

            hourly_stats["hour"].append(hour)
            hourly_stats["avg_arrivals"].append(
                round(len(hour_data) / days, 2) if len(hour_data) > 0 else 0
            )
            hourly_stats["avg_group_size"].append(
                round(hour_data["group_size"].mean(), 2)
                if len(hour_data) > 0
                else 0
            )
            hourly_stats["avg_dining_time"].append(
                round(hour_data["dining_time_minutes"].mean(), 2)
                if len(hour_data) > 0
                else 0
            )
            hourly_stats["total_groups"].append(len(hour_data))

        return hourly_stats

    def get_summary_statistics(self, days: int = 7) -> Dict:
        df = self.generate_historical_data(days)

        return {
            "total_groups": len(df),
            "avg_daily_groups": round(len(df) / days, 1),
            "avg_group_size": round(df["group_size"].mean(), 2),
            "avg_dining_time": round(df["dining_time_minutes"].mean(), 2),
            "peak_hour_groups": len(df[df["is_peak_hour"]]),
            "non_peak_hour_groups": len(df[~df["is_peak_hour"]]),
            "reservation_ratio": round(df["is_reservation"].mean(), 2),
        }
