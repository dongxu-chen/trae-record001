import numpy as np


class Particle:
    def __init__(self, dim, bounds, initial_position=None):
        self.dim = dim
        self.bounds = bounds
        self.low = np.array([b[0] for b in bounds])
        self.high = np.array([b[1] for b in bounds])

        if initial_position is not None:
            self.position = np.clip(np.array(initial_position), self.low, self.high)
        else:
            self.position = np.random.uniform(self.low, self.high, dim)

        self.velocity = np.zeros(dim)
        self.pbest_position = self.position.copy()
        self.pbest_fitness = float('inf')
        self.fitness = float('inf')

    def update_velocity(self, gbest_position, w, c1, c2, v_max=None):
        r1 = np.random.uniform(0, 1, self.dim)
        r2 = np.random.uniform(0, 1, self.dim)

        cognitive = c1 * r1 * (self.pbest_position - self.position)
        social = c2 * r2 * (gbest_position - self.position)
        self.velocity = w * self.velocity + cognitive + social

        if v_max is not None:
            v_max = np.asarray(v_max)
            if v_max.ndim == 0:
                v_max = np.full(self.dim, v_max)
            elif v_max.shape[0] != self.dim:
                raise ValueError(f"v_max length ({v_max.shape[0]}) must match dimensions ({self.dim})")
            self.velocity = np.clip(self.velocity, -v_max, v_max)

    def update_position(self):
        self.position = self.position + self.velocity
        self.position = np.clip(self.position, self.low, self.high)

    def evaluate(self, fitness_func):
        self.fitness = fitness_func(self.position)
        if self.fitness < self.pbest_fitness:
            self.pbest_fitness = self.fitness
            self.pbest_position = self.position.copy()
        return self.fitness

    def reset(self):
        self.position = np.random.uniform(self.low, self.high, self.dim)
        self.velocity = np.zeros(self.dim)
        self.pbest_position = self.position.copy()
        self.pbest_fitness = float('inf')
        self.fitness = float('inf')


class AdaptiveParticle(Particle):
    def __init__(self, dim, bounds, initial_position=None):
        super().__init__(dim, bounds, initial_position)
        self.success_count = 0
        self.failure_count = 0

    def update_adaptive_w(self, current_w, w_min=0.4, w_max=0.9, success_threshold=5):
        if self.success_count >= success_threshold:
            new_w = min(current_w * 1.2, w_max)
            self.success_count = 0
        elif self.failure_count >= success_threshold:
            new_w = max(current_w * 0.8, w_min)
            self.failure_count = 0
        else:
            new_w = current_w
        return new_w

    def record_outcome(self, improved):
        if improved:
            self.success_count += 1
            self.failure_count = 0
        else:
            self.failure_count += 1
            self.success_count = 0


def calculate_inertia_weight(
    iteration,
    max_iter,
    w_start=0.9,
    w_end=0.4,
    strategy='linear',
    fitness_history=None,
    current_fitness=None
):
    if strategy == 'linear':
        return w_start - (w_start - w_end) * (iteration / max_iter)

    elif strategy == 'exponential':
        return w_end * (w_start / w_end) ** (-iteration / max_iter)

    elif strategy == 'sigmoid':
        midpoint = max_iter / 2
        steepness = 4 / max_iter
        return w_end + (w_start - w_end) / (1 + np.exp(steepness * (iteration - midpoint)))

    elif strategy == 'random':
        return 0.5 + np.random.random() * 0.5

    elif strategy == 'adaptive' and fitness_history is not None and len(fitness_history) > 1:
        if current_fitness is not None:
            improvement = fitness_history[-2] - current_fitness
            if improvement > 0:
                return w_start
            else:
                return w_end
        return w_start

    else:
        return w_start - (w_start - w_end) * (iteration / max_iter)


class ConstrictionParticle(Particle):
    def __init__(self, dim, bounds, initial_position=None):
        super().__init__(dim, bounds, initial_position)

    def update_velocity_constriction(self, gbest_position, phi1=2.05, phi2=2.05, v_max=None):
        phi = phi1 + phi2
        K = 2 / abs(2 - phi - np.sqrt(phi ** 2 - 4 * phi))

        r1 = np.random.uniform(0, 1, self.dim)
        r2 = np.random.uniform(0, 1, self.dim)

        cognitive = phi1 * r1 * (self.pbest_position - self.position)
        social = phi2 * r2 * (gbest_position - self.position)
        self.velocity = K * (self.velocity + cognitive + social)

        if v_max is not None:
            v_max = np.asarray(v_max)
            if v_max.ndim == 0:
                v_max = np.full(self.dim, v_max)
            elif v_max.shape[0] != self.dim:
                raise ValueError(f"v_max length ({v_max.shape[0]}) must match dimensions ({self.dim})")
            self.velocity = np.clip(self.velocity, -v_max, v_max)
