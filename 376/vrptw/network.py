import math
import numpy as np
from typing import List, Tuple, Optional

from .models import ProblemData, Customer, Depot, TrafficFactor, CarbonConfig


class NetworkManager:
    def __init__(self, use_osm: bool = False, cache_dir: Optional[str] = None):
        self.use_osm = use_osm
        self.cache_dir = cache_dir
        self._osm_graph = None
        self._node_mapping = {}

    def build_matrices(
        self,
        depots: List[Depot],
        customers: List[Customer],
        travel_speed: float = 40.0,
        traffic_factor: Optional[TrafficFactor] = None,
    ) -> Tuple[List[List[float]], List[List[float]]]:
        all_nodes = depots + customers
        n = len(all_nodes)
        distance_matrix = [[0.0] * n for _ in range(n)]
        time_matrix = [[0.0] * n for _ in range(n)]

        if self.use_osm:
            osm_matrices = self._build_osm_matrices(all_nodes)
            if osm_matrices is not None:
                distance_matrix, raw_time_matrix = osm_matrices
                if traffic_factor:
                    tf = traffic_factor.get_factor()
                    time_matrix = [[t * tf for t in row] for row in raw_time_matrix]
                else:
                    time_matrix = raw_time_matrix
                return distance_matrix, time_matrix

        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                dx = all_nodes[i].x - all_nodes[j].x
                dy = all_nodes[i].y - all_nodes[j].y
                dist = math.sqrt(dx * dx + dy * dy)
                distance_matrix[i][j] = dist
                
                if traffic_factor:
                    tf = traffic_factor.get_factor()
                    time_matrix[i][j] = (dist / travel_speed) * tf
                else:
                    time_matrix[i][j] = dist / travel_speed

        return distance_matrix, time_matrix

    def _build_osm_matrices(self, all_nodes) -> Optional[Tuple[List[List[float]], List[List[float]]]]:
        try:
            import osmnx as ox
        except ImportError:
            print("Warning: OSMnx not installed, falling back to Euclidean distances")
            return None

        try:
            lats = [n.y for n in all_nodes]
            lons = [n.x for n in all_nodes]
            center_lat = (min(lats) + max(lats)) / 2
            center_lon = (min(lons) + max(lons)) / 2
            dist = max(
                max(lats) - min(lats),
                max(lons) - min(lons)
            ) * 111000 * 2

            G = ox.graph_from_point(
                (center_lat, center_lon),
                dist=dist,
                network_type="drive",
                simplify=True,
            )
            self._osm_graph = G

            nearest_nodes = []
            for node in all_nodes:
                nearest = ox.nearest_nodes(G, node.x, node.y)
                nearest_nodes.append(nearest)
                node.node_id = int(nearest)

            n = len(all_nodes)
            distance_matrix = [[0.0] * n for _ in range(n)]
            time_matrix = [[0.0] * n for _ in range(n)]

            for i in range(n):
                for j in range(n):
                    if i == j:
                        continue
                    try:
                        path = ox.shortest_path(G, nearest_nodes[i], nearest_nodes[j])
                        if path and len(path) > 1:
                            edge_lengths = ox.utils_graph.get_route_edge_attributes(G, path, "length")
                            total_length = sum(edge_lengths)
                            distance_matrix[i][j] = total_length / 1000.0
                            travel_time = total_length / 40000.0
                            time_matrix[i][j] = travel_time
                        else:
                            dx = all_nodes[i].x - all_nodes[j].x
                            dy = all_nodes[i].y - all_nodes[j].y
                            distance_matrix[i][j] = math.sqrt(dx * dx + dy * dy)
                            time_matrix[i][j] = distance_matrix[i][j] / 40.0
                    except Exception:
                        dx = all_nodes[i].x - all_nodes[j].x
                        dy = all_nodes[i].y - all_nodes[j].y
                        distance_matrix[i][j] = math.sqrt(dx * dx + dy * dy)
                        time_matrix[i][j] = distance_matrix[i][j] / 40.0

            return distance_matrix, time_matrix

        except Exception as e:
            print(f"Warning: OSMnx graph creation failed: {e}, falling back to Euclidean distances")
            return None

    def get_route_coordinates(
        self, node, all_nodes
    ) -> List[Tuple[float, float]]:
        if not self.use_osm or self._osm_graph is None:
            return [(node.x, node.y)]

        try:
            import osmnx as ox
            path = ox.shortest_path(
                self._osm_graph,
                all_nodes[0].node_id,
                node.node_id,
            )
            if path and len(path) > 1:
                coords = []
                for node_id in path:
                    node_data = self._osm_graph.nodes[node_id]
                    coords.append((node_data["y"], node_data["x"]))
                return coords
        except Exception:
            pass

        return [(node.x, node.y)]

    def calculate_carbon_emission(
        self,
        distance_km: float,
        load_factor: float = 0.5,
        carbon_config: Optional[CarbonConfig] = None,
    ) -> float:
        if carbon_config is None:
            carbon_config = CarbonConfig()
        
        base_emission = distance_km * carbon_config.emission_factor
        load_adjustment = 1.0 + (load_factor * 0.15)
        return base_emission * load_adjustment

    def create_problem_data(
        self,
        depots: List[Depot],
        customers: List[Customer],
        travel_speed: float = 40.0,
        traffic_factor: Optional[TrafficFactor] = None,
        carbon_config: Optional[CarbonConfig] = None,
    ) -> ProblemData:
        is_multi = len(depots) > 1
        
        if is_multi:
            distance_matrix, time_matrix = self._build_multi_depot_matrices(
                depots, customers, travel_speed, traffic_factor
            )
        else:
            distance_matrix, time_matrix = self.build_matrices(
                depots, customers, travel_speed, traffic_factor
            )

        return ProblemData(
            depots=depots,
            customers=customers,
            distance_matrix=distance_matrix,
            time_matrix=time_matrix,
            traffic_factor=traffic_factor,
            carbon_config=carbon_config,
            is_multi_depot=is_multi,
        )

    def _build_multi_depot_matrices(
        self,
        depots: List[Depot],
        customers: List[Customer],
        travel_speed: float,
        traffic_factor: Optional[TrafficFactor],
    ) -> Tuple[List[List[float]], List[List[float]]]:
        all_nodes = depots + customers
        n = len(all_nodes)
        num_depots = len(depots)
        
        distance_matrix = [[0.0] * n for _ in range(n)]
        time_matrix = [[0.0] * n for _ in range(n)]

        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                dx = all_nodes[i].x - all_nodes[j].x
                dy = all_nodes[i].y - all_nodes[j].y
                dist = math.sqrt(dx * dx + dy * dy)
                distance_matrix[i][j] = dist
                
                if traffic_factor:
                    tf = traffic_factor.get_factor()
                    time_matrix[i][j] = (dist / travel_speed) * tf
                else:
                    time_matrix[i][j] = dist / travel_speed

        return distance_matrix, time_matrix

    def assign_customers_to_depots(
        self,
        depots: List[Depot],
        customers: List[Customer],
    ) -> dict:
        assignments = {}
        for idx, depot in enumerate(depots):
            assignments[idx] = []

        for cust in customers:
            min_dist = float('inf')
            best_depot = 0
            
            for idx, depot in enumerate(depots):
                dx = cust.x - depot.x
                dy = cust.y - depot.y
                dist = math.sqrt(dx * dx + dy * dy)
                
                if dist < min_dist:
                    min_dist = dist
                    best_depot = idx
            
            cust.assigned_depot = best_depot
            assignments[best_depot].append(cust.id)

        return assignments

    @staticmethod
    def generate_sample_data(
        num_customers: int = 10,
        num_depots: int = 1,
        depot_lon: float = 116.407,
        depot_lat: float = 39.904,
        spread: float = 0.05,
    ) -> Tuple[List[Depot], List[Customer]]:
        np.random.seed(42)
        
        depots = []
        if num_depots == 1:
            depots.append(Depot(
                id=0,
                x=depot_lon,
                y=depot_lat,
                num_vehicles=5,
                vehicle_capacity=100,
            ))
        else:
            for i in range(num_depots):
                angle = i * (2 * np.pi / num_depots)
                lon = depot_lon + spread * 0.5 * np.cos(angle)
                lat = depot_lat + spread * 0.5 * np.sin(angle)
                depots.append(Depot(
                    id=i,
                    x=lon,
                    y=lat,
                    num_vehicles=5,
                    vehicle_capacity=100,
                ))

        customers = []
        for i in range(1, num_customers + 1):
            angle = (i - 1) * (2 * np.pi / num_customers)
            r = np.random.uniform(0.3, 1.0) * spread
            lon = depot_lon + r * np.cos(angle)
            lat = depot_lat + r * np.sin(angle)
            ready = np.random.uniform(0, 600)
            due = ready + np.random.uniform(120, 480)
            demand = np.random.uniform(10, 40)
            service = np.random.uniform(5, 20)
            customers.append(
                Customer(
                    id=i,
                    x=lon,
                    y=lat,
                    demand=demand,
                    ready_time=ready,
                    due_time=due,
                    service_time=service,
                )
            )

        return depots, customers

    @staticmethod
    def generate_traffic_factor(
        hour_of_day: int = 8,
        congestion_level: str = "normal",
        day_type: str = "weekday",
    ) -> TrafficFactor:
        return TrafficFactor(
            hour_of_day=hour_of_day,
            congestion_level=congestion_level,
        )

    @staticmethod
    def generate_carbon_config(
        emission_factor: float = 0.27,
        fuel_efficiency: float = 8.0,
        carbon_price_per_ton: float = 50.0,
    ) -> CarbonConfig:
        return CarbonConfig(
            emission_factor=emission_factor,
            fuel_efficiency=fuel_efficiency,
            carbon_price_per_ton=carbon_price_per_ton,
        )