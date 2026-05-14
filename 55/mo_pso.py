import numpy as np
from particle import Particle, calculate_inertia_weight
from objective import dominates, get_pareto_front, crowding_distance


class MultiObjectiveParticle(Particle):
    def __init__(self, dim, bounds, n_obj, initial_position=None):
        super().__init__(dim, bounds, initial_position)
        self.n_obj = n_obj
        self.objective_values = np.zeros(n_obj)
        self.pbest_objective = np.zeros(n_obj)
        self.rank = 0
        self.crowding_distance = 0.0

    def evaluate_objectives(self, objective_func):
        self.objective_values = objective_func(self.position)
        if np.all(self.pbest_objective == 0):
            self.pbest_objective = self.objective_values.copy()
        elif dominates(self.objective_values, self.pbest_objective):
            self.pbest_objective = self.objective_values.copy()
            self.pbest_position = self.position.copy()
        return self.objective_values


class MOPSO:
    def __init__(
        self,
        objective_func,
        dim,
        bounds,
        n_obj,
        n_particles=50,
        max_iter=100,
        w_start=0.9,
        w_end=0.4,
        c1=1.49,
        c2=1.49,
        v_max=None,
        n_repository=100,
        random_state=None,
        w_strategy='linear'
    ):
        self.objective_func = objective_func
        self.dim = dim
        self.bounds = bounds
        self.n_obj = n_obj
        self.n_particles = n_particles
        self.max_iter = max_iter
        self.w_start = w_start
        self.w_end = w_end
        self.c1 = c1
        self.c2 = c2
        self.v_max = v_max
        self.n_repository = n_repository
        self.w_strategy = w_strategy

        if random_state is not None:
            np.random.seed(random_state)

        self.particles = [MultiObjectiveParticle(dim, bounds, n_obj) for _ in range(n_particles)]

        self.repository = []
        self.repository_positions = []
        self.history = {
            'repository_objectives': [],
            'repository_positions': []
        }

    def _initialize(self):
        self.repository = []
        self.repository_positions = []
        self.history = {
            'repository_objectives': [],
            'repository_positions': []
        }

        for particle in self.particles:
            particle.evaluate_objectives(self.objective_func)
            self._update_repository(particle.position.copy(), particle.objective_values.copy())

        self._record_history()

    def _update_repository(self, position, objectives):
        dominated = False

        for i in range(len(self.repository)):
            if dominates(self.repository[i], objectives):
                dominated = True
                break

        if not dominated:
            to_remove = []
            for i in range(len(self.repository)):
                if dominates(objectives, self.repository[i]):
                    to_remove.append(i)

            for i in reversed(to_remove):
                del self.repository[i]
                del self.repository_positions[i]

            self.repository.append(objectives.copy())
            self.repository_positions.append(position.copy())

            if len(self.repository) > self.n_repository:
                self._prune_repository()

    def _prune_repository(self):
        distances = crowding_distance(self.repository)
        n_remove = len(self.repository) - self.n_repository
        indices = np.argsort(distances)[:n_remove]

        for i in sorted(indices, reverse=True):
            del self.repository[i]
            del self.repository_positions[i]

    def _select_leader(self):
        if len(self.repository) == 0:
            return self.particles[0].pbest_position, self.particles[0].pbest_objective

        distances = crowding_distance(self.repository)
        max_cd = np.max(distances)
        candidates = [i for i, d in enumerate(distances) if d >= max_cd * 0.5]

        if len(candidates) == 0:
            candidates = list(range(len(self.repository)))

        selected = np.random.choice(candidates)
        return self.repository_positions[selected], self.repository[selected]

    def _record_history(self):
        self.history['repository_objectives'].append([obj.copy() for obj in self.repository])
        self.history['repository_positions'].append([pos.copy() for pos in self.repository_positions])

    def optimize(self, verbose=False):
        self._initialize()

        for iteration in range(self.max_iter):
            w = calculate_inertia_weight(
                iteration,
                self.max_iter,
                self.w_start,
                self.w_end,
                self.w_strategy
            )

            for particle in self.particles:
                leader_pos, leader_obj = self._select_leader()

                particle.update_velocity(
                    leader_pos,
                    w,
                    self.c1,
                    self.c2,
                    self.v_max
                )
                particle.update_position()

                particle.evaluate_objectives(self.objective_func)

                if len(self.repository) == 0 or dominates(particle.objective_values, leader_obj):
                    self._update_repository(particle.position.copy(), particle.objective_values.copy())

            self._record_history()

            if verbose:
                print(f"Iteration {iteration + 1}/{self.max_iter}, Repository size: {len(self.repository)}")

        return self.repository_positions, self.repository

    def get_history(self):
        return self.history

    def get_pareto_front(self):
        return np.array(self.repository_positions), np.array(self.repository)


class NSPSO(MOPSO):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _select_leader(self):
        if len(self.repository) == 0:
            return self.particles[0].pbest_position, self.particles[0].pbest_objective

        objectives = self.repository + [p.objective_values for p in self.particles]
        positions = self.repository_positions + [p.position for p in self.particles]

        pareto_indices = get_pareto_front(objectives)

        if len(pareto_indices) > 0:
            distances = crowding_distance([objectives[i] for i in pareto_indices])
            selected_idx = np.random.choice(len(pareto_indices), p=distances / np.sum(distances) if np.sum(distances) > 0 else None)
            return positions[pareto_indices[selected_idx]], objectives[pareto_indices[selected_idx]]

        return self.repository_positions[0], self.repository[0]


class OMOPSO(MOPSO):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _initialize(self):
        super()._initialize()

        for particle in self.particles:
            if len(self.repository) > 0:
                leader_idx = np.random.randint(len(self.repository))
                particle.gbest_position = self.repository_positions[leader_idx]
                particle.gbest_objective = self.repository[leader_idx]
            else:
                particle.gbest_position = particle.pbest_position
                particle.gbest_objective = particle.pbest_objective

    def optimize(self, verbose=False):
        self._initialize()

        for iteration in range(self.max_iter):
            w = calculate_inertia_weight(
                iteration,
                self.max_iter,
                self.w_start,
                self.w_end,
                self.w_strategy
            )

            for i, particle in enumerate(self.particles):
                if np.random.random() < 0.5:
                    if len(self.repository) > 0:
                        leader_idx = np.random.randint(len(self.repository))
                        leader_pos = self.repository_positions[leader_idx]
                    else:
                        leader_pos = particle.pbest_position
                else:
                    if len(self.repository) > 0:
                        distances = crowding_distance(self.repository)
                        leader_idx = np.argmax(distances)
                        leader_pos = self.repository_positions[leader_idx]
                    else:
                        leader_pos = particle.pbest_position

                particle.update_velocity(
                    leader_pos,
                    w,
                    self.c1,
                    self.c2,
                    self.v_max
                )

                if np.random.random() < 0.5:
                    mutation_idx = np.random.randint(self.dim)
                    mutation_rate = (self.max_iter - iteration) / self.max_iter
                    particle.velocity[mutation_idx] += mutation_rate * np.random.uniform(-1, 1)

                particle.update_position()

                particle.evaluate_objectives(self.objective_func)

                if len(self.repository) == 0 or np.any([dominates(particle.objective_values, obj) for obj in self.repository]):
                    self._update_repository(particle.position.copy(), particle.objective_values.copy())

            self._record_history()

            if verbose:
                print(f"Iteration {iteration + 1}/{self.max_iter}, Repository size: {len(self.repository)}")

        return self.repository_positions, self.repository


class SMPSO(MOPSO):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._mutation_rate = 0.1

    def _update_repository(self, position, objectives):
        dominated = False

        for i in range(len(self.repository)):
            if dominates(self.repository[i], objectives):
                dominated = True
                break

        if not dominated:
            to_remove = []
            for i in range(len(self.repository)):
                if dominates(objectives, self.repository[i]):
                    to_remove.append(i)

            for i in reversed(to_remove):
                del self.repository[i]
                del self.repository_positions[i]

            self.repository.append(objectives.copy())
            self.repository_positions.append(position.copy())

            if len(self.repository) > self.n_repository:
                distances = crowding_distance(self.repository)
                n_remove = len(self.repository) - self.n_repository
                indices = np.argsort(distances)[:n_remove]

                for i in sorted(indices, reverse=True):
                    del self.repository[i]
                    del self.repository_positions[i]

    def optimize(self, verbose=False):
        self._initialize()

        for iteration in range(self.max_iter):
            w = calculate_inertia_weight(
                iteration,
                self.max_iter,
                self.w_start,
                self.w_end,
                self.w_strategy
            )

            for particle in self.particles:
                if len(self.repository) > 0:
                    distances = crowding_distance(self.repository)
                    if np.sum(distances) > 0:
                        probs = distances / np.sum(distances)
                        probs[np.isnan(probs)] = 1 / len(distances)
                        probs = probs / np.sum(probs)
                    else:
                        probs = np.ones(len(distances)) / len(distances)
                    leader_idx = np.random.choice(len(self.repository), p=probs)
                    leader_pos = self.repository_positions[leader_idx]
                else:
                    leader_pos = particle.pbest_position

                particle.update_velocity(
                    leader_pos,
                    w,
                    self.c1,
                    self.c2,
                    self.v_max
                )

                if np.random.random() < self._mutation_rate:
                    mutation_idx = np.random.randint(self.dim)
                    low, high = self.bounds[mutation_idx]
                    particle.position[mutation_idx] = np.random.uniform(low, high)

                particle.update_position()

                particle.evaluate_objectives(self.objective_func)

                self._update_repository(particle.position.copy(), particle.objective_values.copy())

            self._record_history()

            if verbose:
                print(f"Iteration {iteration + 1}/{self.max_iter}, Repository size: {len(self.repository)}")

        return self.repository_positions, self.repository


if __name__ == "__main__":
    from objective import MULTI_OBJECTIVE_FUNCTIONS

    func_name = 'zdt1'
    func_info = MULTI_OBJECTIVE_FUNCTIONS[func_name]

    print(f"Running MOPSO on {func_name}...")
    mopso = MOPSO(
        objective_func=func_info['function'],
        dim=func_info['dim'],
        bounds=func_info['bounds'],
        n_obj=func_info['n_obj'],
        n_particles=100,
        max_iter=100,
        n_repository=100,
        random_state=42
    )

    positions, objectives = mopso.optimize(verbose=True)

    print(f"\nFinal Pareto Front size: {len(objectives)}")
    print(f"First 5 objective values:")
    for i in range(min(5, len(objectives))):
        print(f"  {objectives[i]}")
