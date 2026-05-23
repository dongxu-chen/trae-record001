import random
import numpy as np
from deap import base, creator, tools, algorithms
from geopy.distance import geodesic
from typing import List, Dict, Tuple, Any, Optional


class VRPSolver:
    def __init__(self, locations: List[Dict], vehicle_capacity: float, num_vehicles: int, 
                 time_windows: Dict = None, forbidden_areas: List = None, 
                 locked_routes: List = None, traffic_data: Dict = None,
                 objective_weights: Dict = None):
        self.locations = locations
        self.vehicle_capacity = vehicle_capacity
        self.num_vehicles = num_vehicles
        self.time_windows = time_windows or {}
        self.forbidden_areas = forbidden_areas or []
        self.locked_routes = locked_routes or []
        self.traffic_data = traffic_data or {}
        self.objective_weights = objective_weights or {
            'distance': 1.0,
            'vehicles': 10.0,
            'time_window': 5.0,
            'fairness': 2.0
        }
        
        self.depot = locations[0] if locations else None
        self.customers = locations[1:] if len(locations) > 1 else []
        self.n_customers = len(self.customers)
        
        self.locked_customers = set()
        self._process_locked_routes()
        
        self.distance_matrix = self._compute_distance_matrix()
        self.traffic_matrix = self._compute_traffic_matrix()
        self.time_matrix = self._compute_time_matrix()
        self._setup_deap()
    
    def _process_locked_routes(self):
        for route_data in self.locked_routes:
            if 'locked' in route_data and route_data['locked']:
                for loc_idx in route_data.get('location_indices', []):
                    if loc_idx > 0:
                        self.locked_customers.add(loc_idx - 1)
    
    def _compute_distance_matrix(self):
        n = len(self.locations)
        matrix = np.zeros((n, n))
        for i in range(n):
            for j in range(n):
                if i != j:
                    coord1 = (self.locations[i]['lat'], self.locations[i]['lng'])
                    coord2 = (self.locations[j]['lat'], self.locations[j]['lng'])
                    matrix[i][j] = geodesic(coord1, coord2).kilometers
        return matrix
    
    def _compute_traffic_matrix(self):
        n = len(self.locations)
        matrix = np.ones((n, n))
        for i in range(n):
            for j in range(n):
                if i != j:
                    key = f"{i}-{j}"
                    if key in self.traffic_data:
                        matrix[i][j] = self.traffic_data[key]
                    else:
                        matrix[i][j] = 1.0 + random.uniform(-0.1, 0.3)
        return matrix
    
    def _compute_time_matrix(self):
        base_speed = 30.0
        return self.distance_matrix * self.traffic_matrix / base_speed
    
    def _is_point_in_forbidden_area(self, lat, lng):
        for area in self.forbidden_areas:
            if 'type' in area and area['type'] == 'circle':
                center_lat, center_lng = area['center']
                radius = area['radius'] / 1000
                dist = geodesic((lat, lng), (center_lat, center_lng)).kilometers
                if dist <= radius:
                    return True
        return False
    
    def _calculate_forbidden_penalty(self, from_idx, to_idx):
        lat1, lng1 = self.locations[from_idx]['lat'], self.locations[from_idx]['lng']
        lat2, lng2 = self.locations[to_idx]['lat'], self.locations[to_idx]['lng']
        
        base_penalty = 100.0
        segment_distance = self.distance_matrix[from_idx][to_idx]
        
        steps = 20
        forbidden_steps = 0
        max_depth = 0
        
        for i in range(steps + 1):
            t = i / steps
            lat = lat1 + t * (lat2 - lat1)
            lng = lng1 + t * (lng2 - lng1)
            
            for area in self.forbidden_areas:
                if 'type' in area and area['type'] == 'circle':
                    center_lat, center_lng = area['center']
                    radius = area['radius'] / 1000
                    dist = geodesic((lat, lng), (center_lat, center_lng)).kilometers
                    
                    if dist <= radius:
                        forbidden_steps += 1
                        depth = (radius - dist) / radius
                        if depth > max_depth:
                            max_depth = depth
                        break
        
        if forbidden_steps == 0:
            return 0.0
        
        penetration_ratio = forbidden_steps / (steps + 1)
        distance_penalty = segment_distance * penetration_ratio * 50
        depth_penalty = max_depth * 200
        count_penalty = base_penalty
        
        return count_penalty + distance_penalty + depth_penalty
    
    def _route_passes_through_forbidden(self, from_idx, to_idx):
        return self._calculate_forbidden_penalty(from_idx, to_idx) > 0
    
    def _get_time_window(self, loc_idx):
        if str(loc_idx) in self.time_windows:
            return self.time_windows[str(loc_idx)]
        if loc_idx in self.time_windows:
            return self.time_windows[loc_idx]
        return (8, 18)
    
    def _heuristic_insertion_with_time_window(self):
        unassigned = list(range(self.n_customers))
        routes = [[] for _ in range(self.num_vehicles)]
        current_loads = [0.0] * self.num_vehicles
        
        if self.time_windows:
            def get_tw_start(cust_idx):
                return self._get_time_window(cust_idx + 1)[0]
            unassigned.sort(key=get_tw_start)
        
        for customer_idx in unassigned:
            customer = self.customers[customer_idx]
            demand = customer.get('demand', 0)
            loc_idx = customer_idx + 1
            
            best_vehicle = -1
            best_position = -1
            best_cost = float('inf')
            
            for v in range(self.num_vehicles):
                if current_loads[v] + demand > self.vehicle_capacity:
                    continue
                
                route = routes[v]
                
                for pos in range(len(route) + 1):
                    test_route = route[:pos] + [loc_idx] + route[pos:]
                    
                    arrival_times = []
                    current_time = 8
                    prev_loc = 0
                    
                    feasible = True
                    for loc in test_route:
                        travel_time = self.time_matrix[prev_loc][loc]
                        arrival_time = current_time + travel_time
                        
                        tw_start, tw_end = self._get_time_window(loc)
                        
                        if arrival_time > tw_end:
                            feasible = False
                            break
                        
                        arrival_times.append(arrival_time)
                        current_time = max(arrival_time, tw_start) + 0.5
                        prev_loc = loc
                    
                    if not feasible:
                        continue
                    
                    added_distance = 0
                    if pos == 0:
                        if len(route) == 0:
                            added_distance = self.distance_matrix[0][loc_idx] + self.distance_matrix[loc_idx][0]
                        else:
                            added_distance = (self.distance_matrix[0][loc_idx] + 
                                            self.distance_matrix[loc_idx][route[0]] - 
                                            self.distance_matrix[0][route[0]])
                    elif pos == len(route):
                        added_distance = (self.distance_matrix[route[-1]][loc_idx] + 
                                        self.distance_matrix[loc_idx][0] - 
                                        self.distance_matrix[route[-1]][0])
                    else:
                        added_distance = (self.distance_matrix[route[pos-1]][loc_idx] + 
                                        self.distance_matrix[loc_idx][route[pos]] - 
                                        self.distance_matrix[route[pos-1]][route[pos]])
                    
                    cost = added_distance
                    
                    if cost < best_cost:
                        best_cost = cost
                        best_vehicle = v
                        best_position = pos
            
            if best_vehicle == -1:
                for v in range(self.num_vehicles):
                    if current_loads[v] + demand <= self.vehicle_capacity:
                        routes[v].append(loc_idx)
                        current_loads[v] += demand
                        break
            else:
                routes[best_vehicle].insert(best_position, loc_idx)
                current_loads[best_vehicle] += demand
        
        individual = []
        for route in routes:
            for loc_idx in route:
                individual.append(loc_idx - 1)
        
        if len(individual) < self.n_customers:
            remaining = [i for i in range(self.n_customers) if i not in individual]
            individual.extend(remaining)
        
        return individual[:self.n_customers]
    
    def _savings_heuristic(self):
        savings = []
        for i in range(self.n_customers):
            for j in range(i + 1, self.n_customers):
                saving = (self.distance_matrix[0][i + 1] + 
                         self.distance_matrix[0][j + 1] - 
                         self.distance_matrix[i + 1][j + 1])
                savings.append((saving, i, j))
        
        savings.sort(reverse=True)
        
        routes = []
        customer_route = {}
        
        for i in range(self.n_customers):
            if self.customers[i].get('demand', 0) <= self.vehicle_capacity:
                routes.append([i + 1])
                customer_route[i] = len(routes) - 1
        
        for saving, i, j in savings:
            if i not in customer_route or j not in customer_route:
                continue
            
            route_i_idx = customer_route[i]
            route_j_idx = customer_route[j]
            
            if route_i_idx == route_j_idx:
                continue
            
            route_i = routes[route_i_idx]
            route_j = routes[route_j_idx]
            
            load_i = sum(self.customers[c - 1].get('demand', 0) for c in route_i)
            load_j = sum(self.customers[c - 1].get('demand', 0) for c in route_j)
            
            if load_i + load_j > self.vehicle_capacity:
                continue
            
            if (route_i[-1] == i + 1 and route_j[0] == j + 1) or \
               (route_j[-1] == j + 1 and route_i[0] == i + 1):
                new_route = route_i + route_j
                routes.append(new_route)
                
                for c in new_route:
                    customer_route[c - 1] = len(routes) - 1
        
        individual = []
        used = set()
        
        for route in routes:
            for loc_idx in route:
                cust_idx = loc_idx - 1
                if cust_idx not in used:
                    individual.append(cust_idx)
                    used.add(cust_idx)
        
        for i in range(self.n_customers):
            if i not in used:
                individual.append(i)
        
        return individual[:self.n_customers]
    
    def _nearest_neighbor_heuristic(self):
        unvisited = set(range(self.n_customers))
        individual = []
        
        current = 0
        while unvisited:
            nearest = min(unvisited, key=lambda x: self.time_matrix[current][x + 1])
            individual.append(nearest)
            current = nearest + 1
            unvisited.remove(nearest)
        
        return individual
    
    def _generate_heuristic_individual(self):
        heuristics = [
            self._heuristic_insertion_with_time_window,
            self._savings_heuristic,
            self._nearest_neighbor_heuristic
        ]
        
        heuristic = random.choice(heuristics)
        individual = heuristic()
        
        if len(individual) != self.n_customers:
            individual = list(range(self.n_customers))
            random.shuffle(individual)
        
        return individual
    
    def _setup_deap(self):
        if hasattr(creator, 'FitnessMin'):
            del creator.FitnessMin
        if hasattr(creator, 'Individual'):
            del creator.Individual
            
        creator.create("FitnessMin", base.Fitness, weights=(-1.0, -1.0, -1.0, -1.0))
        creator.create("Individual", list, fitness=creator.FitnessMin)
        
        self.toolbox = base.Toolbox()
        self.toolbox.register("heuristic_ind", self._generate_heuristic_individual)
        
        def init_individual():
            ind = self.toolbox.heuristic_ind()
            return creator.Individual(ind)
        
        self.toolbox.register("individual", init_individual)
        self.toolbox.register("population", tools.initRepeat, list, self.toolbox.individual)
        self.toolbox.register("evaluate", self.evaluate_multi_objective)
        
        if self.locked_customers:
            self.toolbox.register("mate", self._mate_with_locked)
            self.toolbox.register("mutate", self._mutate_with_locked, indpb=0.05)
        else:
            self.toolbox.register("mate", tools.cxOrdered)
            self.toolbox.register("mutate", tools.mutShuffleIndexes, indpb=0.05)
        
        self.toolbox.register("select", tools.selTournament, tournsize=3)
    
    def _mate_with_locked(self, ind1, ind2):
        unlocked_positions = [i for i in range(len(ind1)) 
                             if ind1[i] not in self.locked_customers and 
                                ind2[i] not in self.locked_customers]
        
        if len(unlocked_positions) < 2:
            return ind1, ind2
        
        sub_ind1 = [ind1[i] for i in unlocked_positions]
        sub_ind2 = [ind2[i] for i in unlocked_positions]
        
        child1, child2 = tools.cxOrdered(sub_ind1, sub_ind2)
        
        for idx, pos in enumerate(unlocked_positions):
            ind1[pos] = child1[idx]
            ind2[pos] = child2[idx]
        
        return ind1, ind2
    
    def _mutate_with_locked(self, individual, indpb):
        unlocked_positions = [i for i in range(len(individual)) 
                             if individual[i] not in self.locked_customers]
        
        if len(unlocked_positions) < 2:
            return (individual,)
        
        for i in range(len(unlocked_positions)):
            if random.random() < indpb:
                j = random.randint(0, len(unlocked_positions) - 1)
                pos_i = unlocked_positions[i]
                pos_j = unlocked_positions[j]
                individual[pos_i], individual[pos_j] = individual[pos_j], individual[pos_i]
        
        return (individual,)
    
    def decode_route(self, individual: List[int]) -> List[List[int]]:
        routes = [[] for _ in range(self.num_vehicles)]
        current_loads = [0.0] * self.num_vehicles
        vehicle_idx = 0
        
        for customer_idx in individual:
            customer = self.customers[customer_idx]
            demand = customer.get('demand', 0)
            
            if current_loads[vehicle_idx] + demand <= self.vehicle_capacity:
                routes[vehicle_idx].append(customer_idx + 1)
                current_loads[vehicle_idx] += demand
            else:
                assigned = False
                for i in range(self.num_vehicles):
                    if i != vehicle_idx and current_loads[i] + demand <= self.vehicle_capacity:
                        routes[i].append(customer_idx + 1)
                        current_loads[i] += demand
                        assigned = True
                        break
                
                if not assigned:
                    routes[vehicle_idx].append(customer_idx + 1)
                    current_loads[vehicle_idx] += demand
            
            vehicle_idx = (vehicle_idx + 1) % self.num_vehicles
        
        return [route for route in routes if route]
    
    def evaluate_multi_objective(self, individual: List[int]) -> Tuple[float, float, float, float]:
        routes = self.decode_route(individual)
        
        total_distance = 0.0
        used_vehicles = len(routes)
        penalty = 0.0
        total_load = 0.0
        time_window_violations = 0.0
        route_distances = []
        satisfied_customers = 0
        
        for route in routes:
            if not route:
                continue
            
            route_distance = 0.0
            prev_idx = 0
            current_time = 8
            
            for loc_idx in route:
                forbid_penalty = self._calculate_forbidden_penalty(prev_idx, loc_idx)
                penalty += forbid_penalty
                
                travel_time = self.time_matrix[prev_idx][loc_idx]
                arrival_time = current_time + travel_time
                
                tw_start, tw_end = self._get_time_window(loc_idx)
                
                if arrival_time > tw_end:
                    time_window_violations += (arrival_time - tw_end)
                else:
                    satisfied_customers += 1
                
                route_distance += self.distance_matrix[prev_idx][loc_idx]
                current_time = max(arrival_time, tw_start) + 0.5
                prev_idx = loc_idx
            
            forbid_penalty = self._calculate_forbidden_penalty(prev_idx, 0)
            penalty += forbid_penalty
            route_distance += self.distance_matrix[prev_idx][0]
            
            total_distance += route_distance
            route_distances.append(route_distance)
            
            route_load = sum(self.customers[i-1].get('demand', 0) for i in route if i > 0)
            if route_load > self.vehicle_capacity:
                penalty += (route_load - self.vehicle_capacity) * 50
            total_load += route_load
        
        if len(route_distances) > 1:
            fairness = np.std(route_distances)
        else:
            fairness = 0
        
        time_window_satisfaction = time_window_violations
        
        return (
            (total_distance + penalty) * self.objective_weights['distance'],
            used_vehicles * self.objective_weights['vehicles'],
            time_window_satisfaction * self.objective_weights['time_window'],
            fairness * self.objective_weights['fairness']
        )
    
    def evaluate(self, individual: List[int]) -> Tuple[float, float, float]:
        obj = self.evaluate_multi_objective(individual)
        return (obj[0] + obj[1] + obj[2] + obj[3], obj[1], -sum(self.customers[i].get('demand', 0) for i in individual if i < len(self.customers)))
    
    def _insert_locked_routes(self, individual: List[int]) -> List[int]:
        if not self.locked_routes:
            return individual
        
        locked_segments = []
        unlocked_customers = set(range(self.n_customers))
        
        for route_data in self.locked_routes:
            if route_data.get('locked', False):
                segment = [i - 1 for i in route_data.get('location_indices', []) 
                          if i > 0 and (i - 1) < self.n_customers]
                if segment:
                    locked_segments.append(segment)
                    for cust_idx in segment:
                        if cust_idx in unlocked_customers:
                            unlocked_customers.remove(cust_idx)
        
        unlocked_list = [c for c in individual if c in unlocked_customers]
        
        result = []
        segment_idx = 0
        unlocked_idx = 0
        
        while unlocked_idx < len(unlocked_list) or segment_idx < len(locked_segments):
            if random.random() < 0.5 and segment_idx < len(locked_segments):
                result.extend(locked_segments[segment_idx])
                segment_idx += 1
            elif unlocked_idx < len(unlocked_list):
                result.append(unlocked_list[unlocked_idx])
                unlocked_idx += 1
            elif segment_idx < len(locked_segments):
                result.extend(locked_segments[segment_idx])
                segment_idx += 1
        
        return result[:self.n_customers]
    
    def analyze_capacity(self) -> Dict[str, Any]:
        total_demand = sum(c.get('demand', 0) for c in self.customers)
        total_capacity = self.vehicle_capacity * self.num_vehicles
        
        capacity_ratio = total_demand / total_capacity if total_capacity > 0 else 0
        
        suggestions = []
        outsourcing_needed = False
        outsourcing_customers = []
        
        if capacity_ratio > 1.0:
            outsourcing_needed = True
            excess_demand = total_demand - total_capacity
            
            sorted_customers = sorted(
                [(i + 1, self.customers[i].get('demand', 0), self.customers[i].get('name', f'配送点{i+1}')) 
                 for i in range(self.n_customers)],
                key=lambda x: (-x[1], x[0])
            )
            
            accumulated = 0
            for cust_idx, demand, name in sorted_customers:
                if accumulated >= excess_demand:
                    break
                outsourcing_customers.append({
                    'customer_id': cust_idx,
                    'name': name,
                    'demand': demand,
                    'reason': '超出运力'
                })
                accumulated += demand
            
            suggestions.append({
                'type': 'outsourcing',
                'priority': 'high',
                'message': f'总需求{total_demand}超出总运力{total_capacity}，建议外包{len(outsourcing_customers)}个配送点',
                'customers': outsourcing_customers
            })
            
            additional_vehicles = int(np.ceil(excess_demand / self.vehicle_capacity))
            suggestions.append({
                'type': 'vehicle',
                'priority': 'medium',
                'message': f'建议增加{additional_vehicles}辆车，或外包部分订单'
            })
        
        if len(self.customers) > self.num_vehicles * 5:
            suggestions.append({
                'type': 'workload',
                'priority': 'medium',
                'message': '每辆车平均配送点过多，建议增加车辆或减少配送点'
            })
        
        return {
            'total_demand': round(total_demand, 2),
            'total_capacity': round(total_capacity, 2),
            'capacity_ratio': round(capacity_ratio * 100, 1),
            'outsourcing_needed': outsourcing_needed,
            'outsourcing_customers': outsourcing_customers,
            'suggestions': suggestions
        }
    
    def analyze_fairness(self, routes: List[List[int]]) -> Dict[str, Any]:
        route_distances = []
        route_loads = []
        route_times = []
        
        for route in routes:
            if not route:
                continue
            
            distance = 0.0
            load = 0.0
            prev_idx = 0
            
            for loc_idx in route:
                distance += self.distance_matrix[prev_idx][loc_idx]
                load += self.customers[loc_idx - 1].get('demand', 0)
                prev_idx = loc_idx
            
            distance += self.distance_matrix[prev_idx][0]
            route_distances.append(distance)
            route_loads.append(load)
            route_times.append(distance / 30)
        
        if len(route_distances) == 0:
            return {'fairness_score': 100}
        
        distance_std = np.std(route_distances)
        distance_mean = np.mean(route_distances)
        distance_cv = distance_std / distance_mean if distance_mean > 0 else 0
        
        load_std = np.std(route_loads)
        load_mean = np.mean(route_loads)
        load_cv = load_std / load_mean if load_mean > 0 else 0
        
        fairness_score = max(0, 100 - (distance_cv * 50 + load_cv * 50) * 100)
        
        return {
            'fairness_score': round(fairness_score, 1),
            'distance_std': round(distance_std, 2),
            'distance_cv': round(distance_cv * 100, 1),
            'load_std': round(load_std, 2),
            'load_cv': round(load_cv * 100, 1),
            'route_distances': [round(d, 2) for d in route_distances],
            'route_loads': [round(l, 2) for l in route_loads]
        }
    
    def analyze_time_window_satisfaction(self, routes: List[List[int]]) -> Dict[str, Any]:
        total_customers = 0
        satisfied_customers = 0
        total_delay = 0.0
        
        for route in routes:
            if not route:
                continue
            
            prev_idx = 0
            current_time = 8
            
            for loc_idx in route:
                total_customers += 1
                travel_time = self.time_matrix[prev_idx][loc_idx]
                arrival_time = current_time + travel_time
                
                tw_start, tw_end = self._get_time_window(loc_idx)
                
                if arrival_time <= tw_end:
                    satisfied_customers += 1
                else:
                    total_delay += (arrival_time - tw_end)
                
                current_time = max(arrival_time, tw_start) + 0.5
                prev_idx = loc_idx
        
        satisfaction_rate = (satisfied_customers / total_customers * 100) if total_customers > 0 else 100
        
        return {
            'satisfaction_rate': round(satisfaction_rate, 1),
            'satisfied_customers': satisfied_customers,
            'total_customers': total_customers,
            'total_delay_hours': round(total_delay, 2)
        }
    
    def solve(self, population_size: int = 100, generations: int = 50, 
              cxpb: float = 0.7, mutpb: float = 0.2) -> Dict[str, Any]:
        if self.n_customers == 0:
            return {
                'routes': [],
                'total_distance': 0,
                'used_vehicles': 0,
                'total_load': 0,
                'load_rate': 0,
                'fairness': {'fairness_score': 100},
                'time_window': {'satisfaction_rate': 100},
                'capacity_analysis': self.analyze_capacity()
            }
        
        capacity_analysis = self.analyze_capacity()
        
        pop = []
        heuristic_count = min(population_size // 2, 20)
        
        for _ in range(heuristic_count):
            ind = self.toolbox.individual()
            pop.append(ind)
        
        while len(pop) < population_size:
            ind = self.toolbox.individual()
            pop.append(ind)
        
        hof = tools.HallOfFame(1)
        
        stats = tools.Statistics(lambda ind: ind.fitness.values)
        stats.register("avg", np.mean, axis=0)
        stats.register("min", np.min, axis=0)
        
        algorithms.eaSimple(pop, self.toolbox, cxpb, mutpb, generations, stats, halloffame=hof, verbose=False)
        
        best_individual = hof[0]
        routes = self.decode_route(best_individual)
        
        if self.locked_routes:
            routes = self._merge_locked_routes(routes)
        
        total_distance = 0.0
        used_vehicles = len(routes)
        total_load = 0.0
        
        route_details = []
        
        colors = ['#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6', '#1abc9c', '#e67e22', '#34495e']
        
        for idx, route in enumerate(routes):
            if not route:
                continue
            
            route_distance = 0.0
            prev_idx = 0
            route_points = [{'lat': self.depot['lat'], 'lng': self.depot['lng']}]
            
            for loc_idx in route:
                route_distance += self.distance_matrix[prev_idx][loc_idx]
                prev_idx = loc_idx
                route_points.append({'lat': self.locations[loc_idx]['lat'], 'lng': self.locations[loc_idx]['lng']})
            
            route_distance += self.distance_matrix[prev_idx][0]
            route_points.append({'lat': self.depot['lat'], 'lng': self.depot['lng']})
            
            route_load = sum(self.customers[i-1].get('demand', 0) for i in route if i > 0)
            total_distance += route_distance
            total_load += route_load
            
            is_locked = False
            for locked_route in self.locked_routes:
                if locked_route.get('locked', False) and locked_route.get('vehicle_id') == idx + 1:
                    is_locked = True
                    break
            
            route_details.append({
                'vehicle_id': idx + 1,
                'color': colors[idx % len(colors)],
                'route': route,
                'location_indices': [0] + route + [0],
                'points': route_points,
                'distance': round(route_distance, 2),
                'load': round(route_load, 2),
                'load_rate': round(route_load / self.vehicle_capacity * 100, 1),
                'locked': is_locked
            })
        
        total_capacity = self.vehicle_capacity * self.num_vehicles
        load_rate = round((total_load / total_capacity * 100) if total_capacity > 0 else 0, 1)
        
        fairness_analysis = self.analyze_fairness(routes)
        tw_analysis = self.analyze_time_window_satisfaction(routes)
        
        return {
            'routes': route_details,
            'total_distance': round(total_distance, 2),
            'used_vehicles': used_vehicles,
            'total_load': round(total_load, 2),
            'load_rate': load_rate,
            'depot': {'lat': self.depot['lat'], 'lng': self.depot['lng']},
            'fairness': fairness_analysis,
            'time_window': tw_analysis,
            'capacity_analysis': capacity_analysis
        }
    
    def _merge_locked_routes(self, optimized_routes: List[List[int]]) -> List[List[int]]:
        result = []
        
        for locked_route in self.locked_routes:
            if locked_route.get('locked', False):
                locked_segment = [i for i in locked_route.get('location_indices', []) if i > 0]
                if locked_segment:
                    result.append(locked_segment)
        
        used_customers = set()
        for route in result:
            for loc_idx in route:
                used_customers.add(loc_idx)
        
        for route in optimized_routes:
            filtered = [loc_idx for loc_idx in route if loc_idx not in used_customers]
            if filtered:
                result.append(filtered)
                for loc_idx in filtered:
                    used_customers.add(loc_idx)
        
        return result
