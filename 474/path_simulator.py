import numpy as np
import random
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from warehouse import Warehouse, Location
from scipy.spatial.distance import cdist


@dataclass
class PickingPath:
    order_id: str
    items: List[str]
    locations: List[Tuple[str, float, float, float]]
    path: List[Tuple[float, float, float]]
    total_distance: float
    item_sequence: List[str]


class PathSimulator:
    def __init__(self, warehouse: Warehouse):
        self.warehouse = warehouse
        self.depot_position = (-1.0, -1.0, 0.0)

    def calculate_picking_distance(self, product_locations: Dict[str, str],
                                   order_items: List[str],
                                   method: str = 'nearest_neighbor') -> float:
        if len(order_items) < 2:
            return 0.0

        locations = []
        for item in order_items:
            if item in product_locations:
                loc_id = product_locations[item]
                loc = self.warehouse.locations[loc_id]
                locations.append((loc.x, loc.y, loc.z))

        if not locations:
            return 0.0

        if method == 'nearest_neighbor':
            return self._nearest_neighbor_distance(locations)
        elif method == 'tsp_2opt':
            return self._tsp_2opt_distance(locations)
        elif method == 's_shape':
            return self._s_shape_distance(locations)
        else:
            return self._nearest_neighbor_distance(locations)

    def _nearest_neighbor_distance(self, locations: List[Tuple[float, float, float]]) -> float:
        total_distance = 0.0
        current = self.depot_position
        remaining = locations[:]

        while remaining:
            nearest_idx = 0
            nearest_dist = float('inf')
            for i, loc in enumerate(remaining):
                dist = self._euclidean_distance(current, loc)
                if dist < nearest_dist:
                    nearest_dist = dist
                    nearest_idx = i

            total_distance += nearest_dist
            current = remaining.pop(nearest_idx)

        total_distance += self._euclidean_distance(current, self.depot_position)
        return total_distance

    def _tsp_2opt_distance(self, locations: List[Tuple[float, float, float]]) -> float:
        if len(locations) < 3:
            return self._nearest_neighbor_distance(locations)

        path = [self.depot_position] + locations + [self.depot_position]
        improved = True
        max_iterations = 100
        iteration = 0

        while improved and iteration < max_iterations:
            improved = False
            best_distance = self._calculate_path_length(path)

            for i in range(1, len(path) - 2):
                for j in range(i + 1, len(path) - 1):
                    new_path = path[:i] + path[i:j + 1][::-1] + path[j + 1:]
                    new_distance = self._calculate_path_length(new_path)

                    if new_distance < best_distance:
                        path = new_path
                        best_distance = new_distance
                        improved = True

            iteration += 1

        return self._calculate_path_length(path)

    def _s_shape_distance(self, locations: List[Tuple[float, float, float]]) -> float:
        if not locations:
            return 0.0

        sorted_by_x = sorted(locations, key=lambda l: (l[0], l[1]))

        total_distance = 0.0
        current = self.depot_position

        aisles = {}
        for loc in sorted_by_x:
            x_key = round(loc[0] / 5) * 5
            if x_key not in aisles:
                aisles[x_key] = []
            aisles[x_key].append(loc)

        aisle_order = sorted(aisles.keys())

        for i, aisle_key in enumerate(aisle_order):
            aisle_locs = aisles[aisle_key]

            if i % 2 == 0:
                sorted_aisle = sorted(aisle_locs, key=lambda l: l[1])
            else:
                sorted_aisle = sorted(aisle_locs, key=lambda l: l[1], reverse=True)

            for loc in sorted_aisle:
                total_distance += self._manhattan_distance(current, loc)
                current = loc

        total_distance += self._manhattan_distance(current, self.depot_position)
        return total_distance

    def _euclidean_distance(self, p1: Tuple[float, float, float],
                            p2: Tuple[float, float, float]) -> float:
        return np.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2 + (p1[2] - p2[2]) ** 2)

    def _manhattan_distance(self, p1: Tuple[float, float, float],
                            p2: Tuple[float, float, float]) -> float:
        return abs(p1[0] - p2[0]) + abs(p1[1] - p2[1]) + abs(p1[2] - p2[2])

    def _calculate_path_length(self, path: List[Tuple[float, float, float]]) -> float:
        total = 0.0
        for i in range(len(path) - 1):
            total += self._euclidean_distance(path[i], path[i + 1])
        return total

    def get_picking_path(self, product_locations: Dict[str, str],
                         order_items: List[str],
                         order_id: str = "ORDER_001",
                         method: str = 'nearest_neighbor') -> PickingPath:
        locations = []
        item_location_map = {}
        for item in order_items:
            if item in product_locations:
                loc_id = product_locations[item]
                loc = self.warehouse.locations[loc_id]
                locations.append((loc.x, loc.y, loc.z))
                item_location_map[(loc.x, loc.y, loc.z)] = item

        if not locations:
            return PickingPath(
                order_id=order_id,
                items=order_items,
                locations=[],
                path=[self.depot_position],
                total_distance=0.0,
                item_sequence=[]
            )

        path_coords, item_sequence = self._generate_path_with_sequence(
            locations, item_location_map, method
        )

        location_details = [
            (loc_id,
             self.warehouse.locations[product_locations[item]].x,
             self.warehouse.locations[product_locations[item]].y,
             self.warehouse.locations[product_locations[item]].z)
            for item, loc_id in [(item, product_locations[item]) for item in order_items if item in product_locations]
        ]

        total_distance = self._calculate_path_length(path_coords)

        return PickingPath(
            order_id=order_id,
            items=order_items,
            locations=location_details,
            path=path_coords,
            total_distance=total_distance,
            item_sequence=item_sequence
        )

    def _generate_path_with_sequence(self, locations: List[Tuple[float, float, float]],
                                     item_location_map: Dict[Tuple[float, float, float], str],
                                     method: str) -> Tuple[List[Tuple[float, float, float]], List[str]]:
        path = [self.depot_position]
        item_sequence = []
        current = self.depot_position
        remaining = locations[:]

        while remaining:
            nearest_idx = 0
            nearest_dist = float('inf')
            for i, loc in enumerate(remaining):
                dist = self._euclidean_distance(current, loc)
                if dist < nearest_dist:
                    nearest_dist = dist
                    nearest_idx = i

            current = remaining.pop(nearest_idx)
            path.append(current)
            item_sequence.append(item_location_map[current])

        path.append(self.depot_position)
        return path, item_sequence

    def compare_strategies(self, product_locations: Dict[str, str],
                           num_orders: int = 50) -> Dict[str, Dict]:
        orders = self._generate_test_orders(num_orders)
        strategies = ['nearest_neighbor', 'tsp_2opt', 's_shape']
        results = {}

        for strategy in strategies:
            distances = []
            for order_items in orders:
                dist = self.calculate_picking_distance(product_locations, order_items, strategy)
                distances.append(dist)

            results[strategy] = {
                'mean_distance': np.mean(distances),
                'std_distance': np.std(distances),
                'total_distance': np.sum(distances),
                'min_distance': np.min(distances),
                'max_distance': np.max(distances),
                'distances': distances
            }

        return results

    def compare_assignments(self, assignments: Dict[str, Dict[str, str]],
                            num_orders: int = 100,
                            strategy: str = 'nearest_neighbor') -> Dict[str, Dict]:
        orders = self._generate_test_orders(num_orders)
        results = {}

        for name, assignment in assignments.items():
            distances = []
            for order_items in orders:
                dist = self.calculate_picking_distance(assignment, order_items, strategy)
                distances.append(dist)

            results[name] = {
                'mean_distance': np.mean(distances),
                'std_distance': np.std(distances),
                'total_distance': np.sum(distances),
                'min_distance': np.min(distances),
                'max_distance': np.max(distances),
                'distances': distances
            }

        return results

    def _generate_test_orders(self, num_orders: int) -> List[List[str]]:
        product_ids = list(self.warehouse.products.keys())
        orders = []
        for _ in range(num_orders):
            num_items = random.randint(2, 10)
            items = random.sample(product_ids, min(num_items, len(product_ids)))
            orders.append(items)
        return orders

    def get_comparison_metrics(self, baseline: Dict, optimized: Dict) -> Dict:
        metrics = {}
        for key in ['mean_distance', 'total_distance', 'min_distance', 'max_distance']:
            baseline_val = baseline.get(key, 0)
            optimized_val = optimized.get(key, 0)
            reduction = baseline_val - optimized_val
            reduction_percent = (reduction / baseline_val * 100) if baseline_val > 0 else 0
            metrics[key] = {
                'baseline': baseline_val,
                'optimized': optimized_val,
                'reduction': reduction,
                'reduction_percent': reduction_percent
            }
        return metrics


@dataclass
class PeakTimeSlot:
    hour_of_day: int
    is_peak: bool
    order_intensity: float
    avg_items_per_order: int
    congestion_factor: float


class PeakHourSimulator:
    def __init__(self, warehouse: Warehouse):
        self.warehouse = warehouse
        self.base_simulator = PathSimulator(warehouse)
        self.hourly_pattern = self._generate_hourly_pattern()

    def _generate_hourly_pattern(self) -> Dict[int, PeakTimeSlot]:
        pattern = {}
        for hour in range(24):
            if 8 <= hour <= 11:
                is_peak = True
                intensity = 1.5
                avg_items = 8
                congestion = 1.3
            elif 14 <= hour <= 18:
                is_peak = True
                intensity = 2.0
                avg_items = 10
                congestion = 1.5
            elif 19 <= hour <= 21:
                is_peak = True
                intensity = 1.8
                avg_items = 9
                congestion = 1.4
            else:
                is_peak = False
                intensity = 0.5
                avg_items = 4
                congestion = 0.7

            pattern[hour] = PeakTimeSlot(
                hour_of_day=hour,
                is_peak=is_peak,
                order_intensity=intensity,
                avg_items_per_order=avg_items,
                congestion_factor=congestion
            )
        return pattern

    def simulate_peak_hour_orders(self, hour: int, num_orders: int = 50) -> List[List[str]]:
        time_slot = self.hourly_pattern.get(hour, self.hourly_pattern[10])
        product_ids = list(self.warehouse.products.keys())
        orders = []

        for _ in range(num_orders):
            num_items = max(2, int(random.gauss(time_slot.avg_items_per_order, 2)))
            items = random.sample(product_ids, min(num_items, len(product_ids)))
            orders.append(items)

        return orders

    def simulate_day_simulation(self, product_locations: Dict[str, str],
                           hours_to_simulate: List[int] = None,
                           orders_per_hour: int = 30) -> Dict[int, Dict]:
        if hours_to_simulate is None:
            hours_to_simulate = list(range(8, 22))

        hourly_results = {}

        for hour in hours_to_simulate:
            orders = self.simulate_peak_hour_orders(hour, orders_per_hour)
            distances = []

            for order_items in orders:
                dist = self.base_simulator.calculate_picking_distance(
                    product_locations, order_items, 'nearest_neighbor')
                distances.append(dist)

            time_slot = self.hourly_pattern[hour]

            hourly_results[hour] = {
                'hour': hour,
                'is_peak': time_slot.is_peak,
                'intensity': time_slot.order_intensity,
                'mean_distance': np.mean(distances),
                'std_distance': np.std(distances),
                'total_distance': np.sum(distances),
                'congestion_factor': time_slot.congestion_factor,
                'distances': distances
            }

        return hourly_results

    def compare_peak_vs_normal(self, product_locations: Dict[str, str],
                             orders_per_hour: int = 50) -> Dict:
        peak_hours = [h for h, ts in self.hourly_pattern.items() if ts.is_peak]
        normal_hours = [h for h, ts in self.hourly_pattern.items() if not ts.is_peak and 6 < h < 22]

        peak_results = []
        normal_results = []

        for hour in peak_hours[:3]:
            orders = self.simulate_peak_hour_orders(hour, orders_per_hour // 3)
            for order_items in orders:
                dist = self.base_simulator.calculate_picking_distance(
                    product_locations, order_items)
                peak_results.append(dist)

        for hour in normal_hours[:3]:
            orders = self.simulate_peak_hour_orders(hour, orders_per_hour // 3)
            for order_items in orders:
                dist = self.base_simulator.calculate_picking_distance(
                    product_locations, order_items)
                normal_results.append(dist)

        return {
            'peak': {
                'mean': np.mean(peak_results),
                'std': np.std(peak_results),
                'total': np.sum(peak_results),
                'count': len(peak_results)
            },
            'normal': {
                'mean': np.mean(normal_results),
                'std': np.std(normal_results),
                'total': np.sum(normal_results),
                'count': len(normal_results)
            },
            'peak_hours': peak_hours,
            'normal_hours': normal_hours
        }

    def compare_assignments_peak_hours(self, assignments: Dict[str, Dict[str, str]],
                                   orders_per_hour: int = 100) -> Dict[str, Dict]:
        results = {}

        for name, assignment in assignments.items():
            results[name] = self.compare_peak_vs_normal(assignment, orders_per_hour)

        return results

    def create_hourly_heatmap_data(self, assignment: Dict[str, str],
                              orders_per_hour: int = 30) -> pd.DataFrame:
        hours = list(range(8, 22))
        hourly_data = []

        for hour in hours:
            result = self.hourly_pattern[hour]
            orders = self.simulate_peak_hour_orders(hour, orders_per_hour // len(hours))
            distances = []
            for order_items in orders:
                dist = self.base_simulator.calculate_picking_distance(
                    assignment, order_items)
                distances.append(dist)

            hourly_data.append({
                'hour': hour,
                'is_peak': result.is_peak,
                'intensity': result.order_intensity,
                'mean_distance': np.mean(distances),
                'total_distance': np.sum(distances),
                'congestion_factor': result.congestion_factor
            })

        return pd.DataFrame(hourly_data)
