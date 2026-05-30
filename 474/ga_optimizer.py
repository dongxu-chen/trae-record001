import random
import numpy as np
from typing import Dict, List, Tuple, Callable, Optional
from deap import base, creator, tools, algorithms
from warehouse import Warehouse, SeasonalityType, ABCClass


class WarehouseOptimizer:
    def __init__(self, warehouse: Warehouse,
                 weight_turnover: float = 0.4,
                 weight_correlation: float = 0.3,
                 weight_distance: float = 0.3,
                 weight_seasonality: float = 0.2,
                 weight_abc_zone: float = 0.3,
                 current_season: int = 1,
                 enforce_abc_constraints: bool = True):
        self.warehouse = warehouse
        self.weight_turnover = weight_turnover
        self.weight_correlation = weight_correlation
        self.weight_distance = weight_distance
        self.weight_seasonality = weight_seasonality
        self.weight_abc_zone = weight_abc_zone
        self.current_season = current_season
        self.enforce_abc_constraints = enforce_abc_constraints

        self.product_ids = list(warehouse.products.keys())
        self.location_ids = list(warehouse.locations.keys())
        self.num_products = len(self.product_ids)
        self.num_locations = len(self.location_ids)

        self.loc_to_idx = {loc_id: i for i, loc_id in enumerate(self.location_ids)}
        self.idx_to_loc = {i: loc_id for i, loc_id in enumerate(self.location_ids)}
        self.prod_to_idx = {prod_id: i for i, prod_id in enumerate(self.product_ids)}

        self.abc_results = {}
        self._perform_abc_analysis()

        self._setup_deap()

    def _setup_deap(self):
        creator.create("FitnessMax", base.Fitness, weights=(1.0,))
        creator.create("Individual", list, fitness=creator.FitnessMax)

        self.toolbox = base.Toolbox()
        self.toolbox.register("indices", random.sample, range(self.num_locations), self.num_products)
        self.toolbox.register("individual", tools.initIterate, creator.Individual, self.toolbox.indices)
        self.toolbox.register("population", tools.initRepeat, list, self.toolbox.individual)

        self.toolbox.register("evaluate", self.evaluate)
        self.toolbox.register("mate", self.crossover)
        self.toolbox.register("mutate", self.mutate)
        self.toolbox.register("select", tools.selTournament, tournsize=3)

    def evaluate(self, individual) -> Tuple[float]:
        assignment = {self.product_ids[i]: self.idx_to_loc[individual[i]]
                      for i in range(self.num_products)}

        score_turnover = self._score_turnover_placement(assignment)
        score_correlation = self._score_correlation(assignment)
        score_distance = self._score_picking_distance(assignment)
        score_seasonality = self._score_seasonality(assignment)
        score_abc_zone = self._score_abc_zone(assignment)

        total_weight = (self.weight_turnover + self.weight_correlation +
                       self.weight_distance + self.weight_seasonality +
                       self.weight_abc_zone)

        total_score = (self.weight_turnover * score_turnover +
                       self.weight_correlation * score_correlation +
                       self.weight_distance * score_distance +
                       self.weight_seasonality * score_seasonality +
                       self.weight_abc_zone * score_abc_zone) / total_weight

        if self.enforce_abc_constraints:
            penalty = self._calculate_abc_penalty(assignment)
            total_score *= (1 - penalty)

        return (total_score,)

    def _score_turnover_placement(self, assignment: Dict[str, str]) -> float:
        scores = []
        depot_x, depot_y, depot_z = -1.0, -1.0, 0.0

        for prod_id, loc_id in assignment.items():
            prod = self.warehouse.products[prod_id]
            loc = self.warehouse.locations[loc_id]

            distance_to_depot = np.sqrt(
                (loc.x - depot_x) ** 2 +
                (loc.y - depot_y) ** 2 +
                (loc.z - depot_z) ** 2
            )

            score = prod.turnover_rate / (distance_to_depot + 1)
            scores.append(score)

        return np.mean(scores) if scores else 0.0

    def _score_correlation(self, assignment: Dict[str, str]) -> float:
        if not self.warehouse.correlation_matrix:
            return 0.5

        total_corr = 0.0
        count = 0

        for i, p1 in enumerate(self.product_ids):
            for j, p2 in enumerate(self.product_ids):
                if i >= j:
                    continue

                corr = self.warehouse.correlation_matrix.get(p1, {}).get(p2, 0.0)
                if corr > 0.3:
                    loc1 = self.warehouse.locations[assignment[p1]]
                    loc2 = self.warehouse.locations[assignment[p2]]
                    dist = np.sqrt(
                        (loc1.x - loc2.x) ** 2 +
                        (loc1.y - loc2.y) ** 2 +
                        (loc1.z - loc2.z) ** 2
                    )
                    total_corr += corr / (dist + 1)
                    count += 1

        return total_corr / count if count > 0 else 0.0

    def _score_picking_distance(self, assignment: Dict[str, str]) -> float:
        sample_orders = self._generate_sample_orders(30)
        total_distance = 0.0

        for order in sample_orders:
            distance = self._calculate_order_distance(order, assignment)
            total_distance += distance

        avg_distance = total_distance / len(sample_orders) if sample_orders else 0
        return 1.0 / (avg_distance + 1)

    def _score_seasonality(self, assignment: Dict[str, str]) -> float:
        depot_x, depot_y, depot_z = -1.0, -1.0, 0.0
        scores = []

        for prod_id, loc_id in assignment.items():
            prod = self.warehouse.products.get(prod_id)
            loc = self.warehouse.locations.get(loc_id)
            if not prod or not loc:
                continue

            seasonal_weight = 1.0
            if prod.seasonal_pattern:
                if self.current_season in prod.seasonal_pattern.peak_seasons:
                    seasonal_weight = 1.0 + prod.seasonal_pattern.seasonality_strength
                else:
                    seasonal_weight = max(0.5, 1.0 - prod.seasonal_pattern.seasonality_strength * 0.5)

            distance_to_depot = np.sqrt(
                (loc.x - depot_x) ** 2 +
                (loc.y - depot_y) ** 2 +
                (loc.z - depot_z) ** 2
            )

            effective_turnover = prod.turnover_rate * seasonal_weight
            score = effective_turnover / (distance_to_depot + 1)
            scores.append(score)

        return np.mean(scores) if scores else 0.0

    def _perform_abc_analysis(self):
        self.warehouse.abc_analyzer.perform_abc_analysis()
        self.abc_results = self.warehouse.abc_analyzer.abc_results

    def _score_abc_zone(self, assignment: Dict[str, str]) -> float:
        if not self.abc_results:
            return 0.5

        scores = []
        zone_scores = {
            '黄金区': 1.0,
            '白银区': 0.7,
            '青铜区': 0.4,
            '存储区': 0.1
        }

        for prod_id, loc_id in assignment.items():
            abc_result = self.abc_results.get(prod_id)
            if not abc_result:
                continue

            loc = self.warehouse.locations[loc_id]
            zone_name = loc.zone.value
            zone_base_score = zone_scores.get(zone_name, 0.1)

            if abc_result.abc_class == ABCClass.A:
                if loc.zone.value == '黄金区':
                    match_score = 1.0
                elif loc.zone.value == '白银区':
                    match_score = 0.8
                elif loc.zone.value == '青铜区':
                    match_score = 0.5
                else:
                    match_score = 0.2
            elif abc_result.abc_class == ABCClass.B:
                if loc.zone.value in ['黄金区', '白银区']:
                    match_score = 1.0
                elif loc.zone.value == '青铜区':
                    match_score = 0.8
                else:
                    match_score = 0.5
            else:
                if loc.zone.value == '存储区':
                    match_score = 1.0
                elif loc.zone.value == '青铜区':
                    match_score = 0.9
                elif loc.zone.value == '白银区':
                    match_score = 0.6
                else:
                    match_score = 0.3

            final_score = zone_base_score * match_score
            scores.append(final_score)

        return np.mean(scores) if scores else 0.5

    def _calculate_abc_penalty(self, assignment: Dict[str, str]) -> float:
        if not self.abc_results:
            return 0.0

        violations = 0
        total = 0

        for prod_id, loc_id in assignment.items():
            total += 1
            abc_result = self.abc_results.get(prod_id)
            if not abc_result:
                continue

            loc = self.warehouse.locations[loc_id]
            if abc_result.abc_class not in loc.allowed_abc_classes:
                violations += 1

        return min(0.5, violations / total * 0.5) if total > 0 else 0.0

    def _generate_sample_orders(self, num_orders: int) -> List[List[str]]:
        orders = []
        for _ in range(num_orders):
            num_items = random.randint(2, 8)
            items = random.sample(self.product_ids, min(num_items, self.num_products))
            orders.append(items)
        return orders

    def _calculate_order_distance(self, order_items: List[str], assignment: Dict[str, str]) -> float:
        if len(order_items) < 2:
            return 0.0

        total_distance = 0.0
        depot_x, depot_y, depot_z = -1.0, -1.0, 0.0

        locations = []
        for item in order_items:
            if item in assignment:
                loc = self.warehouse.locations[assignment[item]]
                locations.append((loc.x, loc.y, loc.z))

        if not locations:
            return 0.0

        current_x, current_y, current_z = depot_x, depot_y, depot_z

        remaining = locations[:]
        while remaining:
            nearest_idx = 0
            nearest_dist = float('inf')
            for i, (x, y, z) in enumerate(remaining):
                dist = np.sqrt((x - current_x) ** 2 + (y - current_y) ** 2 + (z - current_z) ** 2)
                if dist < nearest_dist:
                    nearest_dist = dist
                    nearest_idx = i

            total_distance += nearest_dist
            current_x, current_y, current_z = remaining.pop(nearest_idx)

        total_distance += np.sqrt(
            (current_x - depot_x) ** 2 +
            (current_y - depot_y) ** 2 +
            (current_z - depot_z) ** 2
        )

        return total_distance

    def crossover(self, ind1, ind2):
        size = min(len(ind1), len(ind2))
        cxpoint1, cxpoint2 = sorted(random.sample(range(size), 2))

        temp1 = ind1[cxpoint1:cxpoint2]
        temp2 = ind2[cxpoint1:cxpoint2]

        ind1[cxpoint1:cxpoint2], ind2[cxpoint1:cxpoint2] = temp2, temp1

        self._fix_duplicates(ind1, cxpoint1, cxpoint2)
        self._fix_duplicates(ind2, cxpoint1, cxpoint2)

        return ind1, ind2

    def _fix_duplicates(self, individual, cx_start, cx_end):
        cx_segment = set(individual[cx_start:cx_end])

        all_indices = set(range(self.num_locations))
        unused = all_indices - set(individual)

        for i in range(len(individual)):
            if cx_start <= i < cx_end:
                continue

            while individual.count(individual[i]) > 1 and unused:
                new_val = unused.pop()
                individual[i] = new_val

        return individual

    def mutate(self, individual):
        if random.random() < 0.5:
            idx1, idx2 = random.sample(range(len(individual)), 2)
            individual[idx1], individual[idx2] = individual[idx2], individual[idx1]
        else:
            idx = random.randint(0, len(individual) - 1)
            used_locs = set(individual)
            available = [i for i in range(self.num_locations) if i not in used_locs]
            if available:
                individual[idx] = random.choice(available)

        return (individual,)

    def optimize(self, population_size: int = 50, generations: int = 100,
                 cxpb: float = 0.7, mutpb: float = 0.2, verbose: bool = True):
        pop = self.toolbox.population(n=population_size)
        hof = tools.HallOfFame(1)
        stats = tools.Statistics(lambda ind: ind.fitness.values)
        stats.register("avg", np.mean)
        stats.register("std", np.std)
        stats.register("min", np.min)
        stats.register("max", np.max)

        pop, logbook = algorithms.eaSimple(
            pop, self.toolbox, cxpb=cxpb, mutpb=mutpb,
            ngen=generations, stats=stats, halloffame=hof, verbose=verbose
        )

        best_ind = hof[0]
        best_assignment = {self.product_ids[i]: self.idx_to_loc[best_ind[i]]
                           for i in range(self.num_products)}

        return best_assignment, logbook, pop

    def apply_assignment(self, assignment: Dict[str, str]):
        self.warehouse.reset_assignments()
        for prod_id, loc_id in assignment.items():
            self.warehouse.assign_product(prod_id, loc_id)

    def generate_random_assignment(self) -> Dict[str, str]:
        locs = random.sample(self.location_ids, self.num_products)
        return {self.product_ids[i]: locs[i] for i in range(self.num_products)}

    def generate_turnover_based_assignment(self) -> Dict[str, str]:
        sorted_prods = sorted(self.product_ids,
                              key=lambda p: self.warehouse.products[p].turnover_rate,
                              reverse=True)

        depot_x, depot_y, depot_z = -1.0, -1.0, 0.0
        sorted_locs = sorted(self.location_ids,
                             key=lambda l: np.sqrt(
                                 (self.warehouse.locations[l].x - depot_x) ** 2 +
                                 (self.warehouse.locations[l].y - depot_y) ** 2 +
                                 (self.warehouse.locations[l].z - depot_z) ** 2
                             ))

        return {sorted_prods[i]: sorted_locs[i] for i in range(self.num_products)}
