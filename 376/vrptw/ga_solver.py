import random
import math
import numpy as np
from typing import List, Tuple, Optional, Dict

from deap import base, creator, tools, algorithms

from .models import ProblemData, Solution, VehicleRoute, Customer, Depot, CarbonConfig


INF_PENALTY = 1e12


class VRPTWSolver:
    def __init__(self, data: ProblemData):
        self.data = data
        self.distance_matrix = data.distance_matrix
        self.time_matrix = data.time_matrix
        self.customers = data.customers
        self.depots = data.depots
        self.is_multi_depot = data.is_multi_depot
        self.carbon_config = data.carbon_config or CarbonConfig()
        self._validate_matrices()

    @property
    def num_depots(self) -> int:
        return len(self.depots)

    @property
    def total_vehicles(self) -> int:
        return sum(d.num_vehicles for d in self.depots)

    def _validate_matrices(self):
        n = len(self.depots) + len(self.customers)
        if self.distance_matrix is None or len(self.distance_matrix) < n:
            self.distance_matrix = [[0.0] * n for _ in range(n)]
            all_nodes = self.depots + self.customers
            for i in range(n):
                for j in range(n):
                    if i == j:
                        continue
                    dx = all_nodes[i].x - all_nodes[j].x
                    dy = all_nodes[i].y - all_nodes[j].y
                    self.distance_matrix[i][j] = math.sqrt(dx * dx + dy * dy)
        if self.time_matrix is None:
            self.time_matrix = [row[:] for row in self.distance_matrix]

    def _init_toolbox(self):
        if hasattr(creator, "FitnessMin"):
            del creator.FitnessMin
        if hasattr(creator, "Individual"):
            del creator.Individual

        creator.create("FitnessMin", base.Fitness, weights=(-1.0,))
        creator.create("Individual", list, fitness=creator.FitnessMin)

        self.toolbox = base.Toolbox()

        n = len(self.customers)
        self.toolbox.register("attr_int", random.randint, 0, n - 1)
        self.toolbox.register("individual_heuristic", self._create_heuristic_individual)
        self.toolbox.register("individual_random", tools.initRepeat, creator.Individual,
                              self.toolbox.attr_int, n)
        self.toolbox.register("population", self._create_population)

        self.toolbox.register("mate", tools.cxPartialyMatched)
        self.toolbox.register("mutate", tools.mutShuffleIndexes, indpb=0.05)
        self.toolbox.register("select", tools.selTournament, tournsize=3)
        self.toolbox.register("evaluate", self._evaluate)

    def _create_population(self, n: int):
        pop = []
        heuristic_count = max(1, n // 3)
        for _ in range(heuristic_count):
            ind = self._create_heuristic_individual()
            pop.append(creator.Individual(ind))
        for _ in range(n - heuristic_count):
            ind = random.sample(range(len(self.customers)), len(self.customers))
            pop.append(creator.Individual(ind))
        return pop

    def _create_heuristic_individual(self) -> list:
        n = len(self.customers)
        individual = []
        
        if self.is_multi_depot:
            depot_assignments = self._assign_customers_to_nearest_depot()
            for depot_id in range(self.num_depots):
                depot_customers = [i for i in range(n) if depot_assignments.get(i) == depot_id]
                sorted_by_ready = sorted(depot_customers, key=lambda i: self.customers[i].ready_time)
                individual.extend(self._build_feasible_sequence(sorted_by_ready, depot_id))
        else:
            sorted_by_ready = sorted(range(n), key=lambda i: self.customers[i].ready_time)
            individual = self._build_feasible_sequence(sorted_by_ready, 0)
        
        return individual

    def _assign_customers_to_nearest_depot(self) -> Dict[int, int]:
        assignments = {}
        for i, cust in enumerate(self.customers):
            min_dist = float('inf')
            best_depot = 0
            for j, depot in enumerate(self.depots):
                dx = cust.x - depot.x
                dy = cust.y - depot.y
                dist = math.sqrt(dx * dx + dy * dy)
                if dist < min_dist:
                    min_dist = dist
                    best_depot = j
            assignments[i] = best_depot
        return assignments

    def _build_feasible_sequence(self, customer_indices: list, depot_id: int) -> list:
        result = []
        unvisited = customer_indices[:]
        current_load = 0.0
        current_time = 0.0
        current_node = depot_id
        depot = self.depots[depot_id]

        while unvisited:
            feasible = []
            for cust_idx in unvisited:
                cust = self.customers[cust_idx]
                cust_node = self.num_depots + cust_idx
                travel_time = self.time_matrix[current_node][cust_node]
                arrival_time = current_time + travel_time

                if (arrival_time <= cust.due_time and 
                    current_load + cust.demand <= depot.vehicle_capacity):
                    feasible.append((cust_idx, arrival_time, cust.ready_time, travel_time))

            if feasible:
                best_idx = min(feasible, key=lambda x: max(x[1], x[2]) + x[3])[0]
                cust = self.customers[best_idx]
                cust_node = self.num_depots + best_idx
                travel_time = self.time_matrix[current_node][cust_node]
                arrival_time = max(current_time + travel_time, cust.ready_time)

                result.append(best_idx)
                current_load += cust.demand
                current_time = arrival_time + cust.service_time
                current_node = cust_node
                unvisited.remove(best_idx)
            else:
                if current_load > 0:
                    current_load = 0.0
                    current_time = 0.0
                    current_node = depot_id
                else:
                    best_idx = min(unvisited, key=lambda i: self.customers[i].ready_time)
                    cust = self.customers[best_idx]
                    cust_node = self.num_depots + best_idx

                    result.append(best_idx)
                    current_load = cust.demand
                    current_time = max(self.time_matrix[depot_id][cust_node], cust.ready_time) + cust.service_time
                    current_node = cust_node
                    unvisited.remove(best_idx)

        return result

    def _decode_individual(self, individual: list) -> List[Tuple[int, List[int]]]:
        routes = []
        
        if self.is_multi_depot:
            for depot_id in range(self.num_depots):
                depot = self.depots[depot_id]
                depot_customers = [i for i in individual if self._get_assigned_depot(i) == depot_id]
                
                current_route = []
                current_load = 0.0
                current_time = 0.0
                current_node = depot_id

                for cust_idx in depot_customers:
                    cust = self.customers[cust_idx]
                    cust_node = self.num_depots + cust_idx
                    travel_time = self.time_matrix[current_node][cust_node]
                    arrival_time = current_time + travel_time
                    arrival_time = max(arrival_time, cust.ready_time)

                    if (current_load + cust.demand > depot.vehicle_capacity or
                        arrival_time > cust.due_time):
                        if current_route:
                            routes.append((depot_id, current_route))
                        current_route = [cust_idx]
                        current_load = cust.demand
                        current_time = max(self.time_matrix[depot_id][cust_node], cust.ready_time) + cust.service_time
                        current_node = cust_node
                    else:
                        current_route.append(cust_idx)
                        current_load += cust.demand
                        current_time = arrival_time + cust.service_time
                        current_node = cust_node

                if current_route:
                    routes.append((depot_id, current_route))
        else:
            depot = self.depots[0]
            current_route = []
            current_load = 0.0
            current_time = 0.0
            current_node = 0

            for cust_idx in individual:
                cust = self.customers[cust_idx]
                cust_node = self.num_depots + cust_idx
                travel_time = self.time_matrix[current_node][cust_node]
                arrival_time = current_time + travel_time
                arrival_time = max(arrival_time, cust.ready_time)

                if (current_load + cust.demand > depot.vehicle_capacity or
                    arrival_time > cust.due_time):
                    if current_route:
                        routes.append((0, current_route))
                    current_route = [cust_idx]
                    current_load = cust.demand
                    current_time = max(self.time_matrix[0][cust_node], cust.ready_time) + cust.service_time
                    current_node = cust_node
                else:
                    current_route.append(cust_idx)
                    current_load += cust.demand
                    current_time = arrival_time + cust.service_time
                    current_node = cust_node

            if current_route:
                routes.append((0, current_route))

        return routes

    def _get_assigned_depot(self, cust_idx: int) -> int:
        cust = self.customers[cust_idx]
        if cust.assigned_depot is not None:
            return cust.assigned_depot
        
        min_dist = float('inf')
        best_depot = 0
        for j, depot in enumerate(self.depots):
            dx = cust.x - depot.x
            dy = cust.y - depot.y
            dist = math.sqrt(dx * dx + dy * dy)
            if dist < min_dist:
                min_dist = dist
                best_depot = j
        return best_depot

    def _get_depot_capacity(self, depot_id: int) -> float:
        return self.depots[depot_id].vehicle_capacity

    def _evaluate(self, individual) -> Tuple[float]:
        routes = self._decode_individual(individual)
        total_distance = 0.0
        total_carbon = 0.0
        total_penalty = 0.0

        depot_vehicle_count = {i: 0 for i in range(self.num_depots)}

        for depot_id, route in routes:
            if not route:
                continue
            
            depot = self.depots[depot_id]
            depot_vehicle_count[depot_id] += 1

            if depot_vehicle_count[depot_id] > depot.num_vehicles:
                total_penalty += (depot_vehicle_count[depot_id] - depot.num_vehicles) * 10000.0

            current_node = depot_id
            current_time = 0.0
            current_load = 0.0

            for cust_idx in route:
                cust = self.customers[cust_idx]
                cust_node = self.num_depots + cust_idx
                travel_time = self.time_matrix[current_node][cust_node]
                travel_dist = self.distance_matrix[current_node][cust_node]
                arrival_time = current_time + travel_time
                arrival_time = max(arrival_time, cust.ready_time)

                total_distance += travel_dist

                if arrival_time > cust.due_time:
                    total_penalty += (arrival_time - cust.due_time) * 100.0

                current_load += cust.demand
                current_time = arrival_time + cust.service_time
                current_node = cust_node

            total_distance += self.distance_matrix[current_node][depot_id]

            if current_load > depot.vehicle_capacity:
                total_penalty += (current_load - depot.vehicle_capacity) * 200.0

        total_carbon = total_distance * self.carbon_config.emission_factor
        fitness = total_distance + total_carbon * 0.1 + total_penalty
        return (fitness,)

    def _calculate_route_carbon(self, distance: float, load_factor: float) -> float:
        base_emission = distance * self.carbon_config.emission_factor
        load_adjustment = 1.0 + (load_factor * 0.15)
        return base_emission * load_adjustment

    def _build_solution(self, individual: list) -> Solution:
        raw_routes = self._decode_individual(individual)
        routes = []
        depot_assignments = {i: [] for i in range(self.num_depots)}

        vehicle_counter = 1
        for depot_id, raw_route in raw_routes:
            if not raw_route:
                continue
            
            depot = self.depots[depot_id]
            vr = VehicleRoute(vehicle_id=vehicle_counter, depot_id=depot_id)
            current_node = depot_id
            current_time = 0.0
            current_load = 0.0
            total_dist = 0.0
            total_wait = 0.0
            total_late = 0.0
            total_carbon = 0.0
            arrival_times = []
            departure_times = []
            distances = []
            travel_times = []

            for cust_idx in raw_route:
                cust = self.customers[cust_idx]
                cust_node = self.num_depots + cust_idx
                travel_dist = self.distance_matrix[current_node][cust_node]
                travel_time = self.time_matrix[current_node][cust_node]
                arrival_time = current_time + travel_time
                wait_time = max(0.0, cust.ready_time - arrival_time)
                arrival_time = max(arrival_time, cust.ready_time)
                departure_time = arrival_time + cust.service_time

                vr.customer_ids.append(cust.id)
                arrival_times.append(arrival_time)
                departure_times.append(departure_time)
                distances.append(travel_dist)
                travel_times.append(travel_time)

                load_factor = current_load / depot.vehicle_capacity if depot.vehicle_capacity > 0 else 0
                total_carbon += self._calculate_route_carbon(travel_dist, load_factor)

                total_dist += travel_dist
                total_wait += wait_time
                total_late += max(0.0, arrival_time - cust.due_time)
                current_load += cust.demand
                current_time = departure_time
                current_node = cust_node
                depot_assignments[depot_id].append(cust.id)

            return_dist = self.distance_matrix[current_node][depot_id]
            total_dist += return_dist
            distances.append(return_dist)
            travel_times.append(self.time_matrix[current_node][depot_id])
            
            return_carbon = self._calculate_route_carbon(return_dist, 0)
            total_carbon += return_carbon

            vr.total_distance = total_dist
            vr.total_demand = current_load
            vr.waiting_time = total_wait
            vr.lateness = total_late
            vr.carbon_emission = total_carbon
            vr.arrival_times = arrival_times
            vr.departure_times = departure_times
            vr.distances = distances
            vr.travel_times = travel_times
            vr._capacity = depot.vehicle_capacity
            routes.append(vr)
            vehicle_counter += 1

        total_distance = sum(r.total_distance for r in routes)
        total_wait = sum(r.waiting_time for r in routes)
        total_late = sum(r.lateness for r in routes)
        total_carbon = sum(r.carbon_emission for r in routes)
        
        avg_load = (
            sum(r.total_demand for r in routes) / 
            (len(routes) * self._get_depot_capacity(0)) if routes else 0.0
        )
        
        carbon_cost = (total_carbon / 1000.0) * self.carbon_config.carbon_price_per_ton

        return Solution(
            routes=routes,
            total_distance=total_distance,
            total_waiting_time=total_wait,
            total_lateness=total_late,
            used_vehicles=len(routes),
            avg_load_rate=avg_load,
            is_feasible=total_late <= 1e-8,
            total_carbon_emission=total_carbon,
            carbon_cost=carbon_cost,
            depot_assignments=depot_assignments,
        )

    def _swap_operator(self, individual: list, i: int, j: int) -> list:
        new_ind = individual[:]
        new_ind[i], new_ind[j] = new_ind[j], new_ind[i]
        return new_ind

    def _insert_operator(self, individual: list, i: int, j: int) -> list:
        new_ind = individual[:]
        cust = new_ind.pop(i)
        new_ind.insert(j, cust)
        return new_ind

    def _two_opt_operator(self, individual: list, i: int, j: int) -> list:
        new_ind = individual[:]
        if i > j:
            i, j = j, i
        new_ind[i:j+1] = new_ind[i:j+1][::-1]
        return new_ind

    def _local_search_combined(self, individual: list) -> list:
        best_ind = individual[:]
        best_fit = self._evaluate(best_ind)[0]
        improved = True
        max_iter = 30

        while improved and max_iter > 0:
            improved = False
            max_iter -= 1
            n = len(individual)

            for i in range(n):
                for j in range(i + 1, n):
                    operators = [
                        self._swap_operator(best_ind, i, j),
                        self._insert_operator(best_ind, i, j),
                        self._insert_operator(best_ind, j, i),
                        self._two_opt_operator(best_ind, i, j),
                    ]
                    
                    for new_ind in operators:
                        new_fit = self._evaluate(new_ind)[0]
                        if new_fit < best_fit - 1e-6:
                            best_ind = new_ind
                            best_fit = new_fit
                            improved = True
                            break
                    if improved:
                        break
                if improved:
                    break

        return best_ind

    def _relocate_search(self, individual: list) -> list:
        best_ind = individual[:]
        best_fit = self._evaluate(best_ind)[0]
        improved = True

        while improved:
            improved = False
            n = len(individual)

            for i in range(n):
                best_new_fit = best_fit
                best_new_ind = best_ind[:]
                best_pos = -1

                cust_to_move = best_ind[i]
                remaining = best_ind[:i] + best_ind[i+1:]

                for j in range(len(remaining) + 1):
                    new_ind = remaining[:j] + [cust_to_move] + remaining[j:]
                    new_fit = self._evaluate(new_ind)[0]
                    if new_fit < best_new_fit - 1e-6:
                        best_new_fit = new_fit
                        best_new_ind = new_ind
                        best_pos = j

                if best_pos >= 0:
                    best_ind = best_new_ind
                    best_fit = best_new_fit
                    improved = True

        return best_ind

    def _route_exchange_search(self, individual: list) -> list:
        routes = self._decode_individual(individual)
        if len(routes) < 2:
            return individual

        best_ind = individual[:]
        best_fit = self._evaluate(best_ind)[0]

        for i in range(len(routes)):
            for j in range(i + 1, len(routes)):
                for ci_idx, ci in enumerate(routes[i][1]):
                    for cj_idx, cj in enumerate(routes[j][1]):
                        new_ind = individual[:]
                        pos_i = individual.index(ci)
                        pos_j = individual.index(cj)
                        new_ind[pos_i], new_ind[pos_j] = new_ind[pos_j], new_ind[pos_i]
                        new_fit = self._evaluate(new_ind)[0]
                        if new_fit < best_fit - 1e-6:
                            best_ind = new_ind
                            best_fit = new_fit

        return best_ind

    def _depot_reassignment_search(self, individual: list) -> list:
        if not self.is_multi_depot:
            return individual

        best_ind = individual[:]
        best_fit = self._evaluate(best_ind)[0]
        improved = True

        while improved:
            improved = False
            for i, cust_idx in enumerate(individual):
                for new_depot in range(self.num_depots):
                    if self.customers[cust_idx].assigned_depot != new_depot:
                        old_depot = self.customers[cust_idx].assigned_depot
                        self.customers[cust_idx].assigned_depot = new_depot
                        new_fit = self._evaluate(best_ind)[0]
                        if new_fit < best_fit - 1e-6:
                            best_fit = new_fit
                            improved = True
                        else:
                            self.customers[cust_idx].assigned_depot = old_depot

        return best_ind

    def solve(
        self,
        population_size: int = 200,
        num_generations: int = 300,
        crossover_prob: float = 0.8,
        mutation_prob: float = 0.2,
        use_local_search: bool = True,
        verbose: bool = True,
    ) -> Solution:
        self._init_toolbox()
        random.seed(42)
        np.random.seed(42)

        pop = self.toolbox.population(n=population_size)

        best_ever = None
        best_fitness = float("inf")

        for gen in range(num_generations):
            offspring = algorithms.varAnd(pop, self.toolbox, cxpb=crossover_prob, mutpb=mutation_prob)

            fits = self.toolbox.map(self.toolbox.evaluate, offspring)
            for fit, ind in zip(fits, offspring):
                ind.fitness.values = fit

            pop = self.toolbox.select(offspring, k=len(pop))

            fits = self.toolbox.map(self.toolbox.evaluate, pop)
            best_gen = min(pop, key=lambda ind: ind.fitness.values[0])
            if best_gen.fitness.values[0] < best_fitness:
                best_fitness = best_gen.fitness.values[0]
                best_ever = best_gen[:]

            if verbose and (gen % 50 == 0 or gen == num_generations - 1):
                print(f"Generation {gen + 1}/{num_generations}, Best fitness: {best_fitness:.2f}")

        if use_local_search and best_ever is not None:
            if verbose:
                print("Running local search with combined operators...")
            best_ever = self._local_search_combined(best_ever)
            if verbose:
                print("Running relocate search...")
            best_ever = self._relocate_search(best_ever)
            if verbose:
                print("Running route exchange search...")
            best_ever = self._route_exchange_search(best_ever)
            if self.is_multi_depot and verbose:
                print("Running depot reassignment search...")
            if self.is_multi_depot:
                best_ever = self._depot_reassignment_search(best_ever)

        if best_ever is None:
            best_ever = pop[0][:]

        solution = self._build_solution(best_ever)
        return solution