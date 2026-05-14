import numpy as np
from particle import Particle, AdaptiveParticle, calculate_inertia_weight


class PSO:
    def __init__(
        self,
        fitness_func,
        dim,
        bounds,
        n_particles=50,
        max_iter=100,
        w=0.7,
        c1=1.49,
        c2=1.49,
        w_decay=1.0,
        v_max=None,
        random_state=None,
        stagnation_threshold=1e-10,
        max_stagnant_iters=15,
        use_adaptive_w=False,
        w_strategy='linear',
        w_start=0.9,
        w_end=0.4,
        ineq_constraints=None,
        eq_constraints=None,
        penalty_type='static',
        penalty_factor=1e6,
        penalty_C=0.5,
        penalty_alpha=2
    ):
        self.fitness_func = fitness_func
        self.dim = dim
        self.bounds = bounds
        self.n_particles = n_particles
        self.max_iter = max_iter
        self.w = w
        self.c1 = c1
        self.c2 = c2
        self.w_decay = w_decay
        self.v_max = v_max
        self.stagnation_threshold = stagnation_threshold
        self.max_stagnant_iters = max_stagnant_iters
        self.use_adaptive_w = use_adaptive_w
        self.w_strategy = w_strategy
        self.w_start = w_start
        self.w_end = w_end
        self.ineq_constraints = ineq_constraints
        self.eq_constraints = eq_constraints
        self.penalty_type = penalty_type
        self.penalty_factor = penalty_factor
        self.penalty_C = penalty_C
        self.penalty_alpha = penalty_alpha

        if random_state is not None:
            np.random.seed(random_state)

        if self.use_adaptive_w:
            self.particles = [AdaptiveParticle(dim, bounds) for _ in range(n_particles)]
        else:
            self.particles = [Particle(dim, bounds) for _ in range(n_particles)]

        self.gbest_position = None
        self.gbest_fitness = float('inf')
        self.history = {
            'gbest_fitness': [],
            'gbest_position': [],
            'particles_position': [],
            'w_history': []
        }
        self._stagnant_count = 0
        self._previous_best = float('inf')
        self._penalty_factor_history = [penalty_factor]

    def _apply_penalty(self, x, fitness, iteration):
        if self.ineq_constraints is None and self.eq_constraints is None:
            return fitness

        ineq_vals = None
        eq_vals = None

        if self.ineq_constraints is not None:
            ineq_vals = self.ineq_constraints(x)

        if self.eq_constraints is not None:
            eq_vals = self.eq_constraints(x)

        if self.penalty_type == 'static':
            penalty = 0.0
            if ineq_vals is not None:
                for g in ineq_vals:
                    if g > 0:
                        penalty += self.penalty_factor * g ** 2
            if eq_vals is not None:
                for h in eq_vals:
                    if abs(h) > 1e-6:
                        penalty += self.penalty_factor * (h ** 2)
            return fitness + penalty

        elif self.penalty_type == 'dynamic':
            t = iteration + 1
            penalty = 0.0
            if ineq_vals is not None:
                for g in ineq_vals:
                    if g > 0:
                        penalty += (self.penalty_C * t) ** self.penalty_alpha * (g ** 2)
            if eq_vals is not None:
                for h in eq_vals:
                    if abs(h) > 1e-6:
                        penalty += (self.penalty_C * t) ** self.penalty_alpha * (h ** 2)
            return fitness + penalty

        elif self.penalty_type == 'adaptive':
            constraint_violation = 0.0
            if ineq_vals is not None:
                for g in ineq_vals:
                    if g > 0:
                        constraint_violation += g ** 2
            if eq_vals is not None:
                for h in eq_vals:
                    if abs(h) > 1e-6:
                        constraint_violation += h ** 2

            if constraint_violation > 0:
                current_factor = self._penalty_factor_history[-1]
                if fitness > self._previous_best:
                    current_factor *= 2.0
                else:
                    current_factor /= 2.0
                current_factor = max(1e3, min(current_factor, 1e9))
                self._penalty_factor_history.append(current_factor)
                return fitness + current_factor * constraint_violation
            else:
                self._penalty_factor_history.append(self._penalty_factor_history[-1])
                return fitness

        else:
            return fitness

    def _initialize(self):
        self.gbest_position = None
        self.gbest_fitness = float('inf')
        self.history = {
            'gbest_fitness': [],
            'gbest_position': [],
            'particles_position': [],
            'w_history': []
        }
        self._stagnant_count = 0
        self._previous_best = float('inf')
        self._penalty_factor_history = [self.penalty_factor]
        current_w = self.w

        for particle in self.particles:
            raw_fitness = particle.evaluate(self.fitness_func)
            penalized_fitness = self._apply_penalty(particle.position, raw_fitness, 0)
            particle.fitness = penalized_fitness
            particle.pbest_fitness = penalized_fitness

            if penalized_fitness < self.gbest_fitness:
                self.gbest_fitness = penalized_fitness
                self.gbest_position = particle.pbest_position.copy()

        self._previous_best = self.gbest_fitness
        self._record_history(current_w)
        return current_w

    def _record_history(self, current_w):
        self.history['gbest_fitness'].append(self.gbest_fitness)
        self.history['gbest_position'].append(self.gbest_position.copy())
        positions = np.array([p.position.copy() for p in self.particles])
        self.history['particles_position'].append(positions)
        self.history['w_history'].append(current_w)

    def _check_stagnation(self):
        improvement = abs(self._previous_best - self.gbest_fitness)
        if improvement < self.stagnation_threshold:
            self._stagnant_count += 1
        else:
            self._stagnant_count = 0
        self._previous_best = self.gbest_fitness
        return self._stagnant_count >= self.max_stagnant_iters

    def _reinitialize_stagnant_particles(self):
        for particle in self.particles:
            if np.random.random() < 0.3:
                particle.position = np.random.uniform(particle.low, particle.high, particle.dim)
                particle.velocity = np.zeros(particle.dim)
                particle.pbest_position = particle.position.copy()
                raw_fitness = self.fitness_func(particle.position)
                penalized_fitness = self._apply_penalty(particle.position, raw_fitness, 0)
                particle.pbest_fitness = penalized_fitness
                particle.fitness = penalized_fitness

    def optimize(self, verbose=False):
        current_w = self._initialize()

        for iteration in range(self.max_iter):
            if self.w_strategy != 'linear' or self.w_decay != 1.0:
                if self.w_decay != 1.0:
                    current_w *= self.w_decay
                else:
                    current_w = calculate_inertia_weight(
                        iteration,
                        self.max_iter,
                        self.w_start,
                        self.w_end,
                        self.w_strategy,
                        self.history['gbest_fitness'],
                        self.gbest_fitness
                    )

            for particle in self.particles:
                old_pbest = particle.pbest_fitness

                particle.update_velocity(
                    self.gbest_position,
                    current_w,
                    self.c1,
                    self.c2,
                    self.v_max
                )
                particle.update_position()

                raw_fitness = self.fitness_func(particle.position)
                penalized_fitness = self._apply_penalty(particle.position, raw_fitness, iteration)
                particle.fitness = penalized_fitness

                if penalized_fitness < particle.pbest_fitness:
                    particle.pbest_fitness = penalized_fitness
                    particle.pbest_position = particle.position.copy()
                    improved = True
                else:
                    improved = False

                if self.use_adaptive_w and isinstance(particle, AdaptiveParticle):
                    particle.record_outcome(improved)
                    current_w = particle.update_adaptive_w(
                        current_w,
                        w_min=self.w_end,
                        w_max=self.w_start
                    )

                if particle.pbest_fitness < self.gbest_fitness:
                    self.gbest_fitness = particle.pbest_fitness
                    self.gbest_position = particle.pbest_position.copy()

            self._record_history(current_w)

            if self._check_stagnation():
                if verbose:
                    print(f"Stagnation detected at iteration {iteration + 1}, reinitializing 30% of particles...")
                self._reinitialize_stagnant_particles()
                self._stagnant_count = 0

            if verbose:
                print(f"Iteration {iteration + 1}/{self.max_iter}, Best Fitness: {self.gbest_fitness:.6f}, w: {current_w:.4f}")

        return self.gbest_position, self.gbest_fitness

    def get_history(self):
        return self.history

    def reset(self):
        for particle in self.particles:
            particle.reset()
        self.gbest_position = None
        self.gbest_fitness = float('inf')
        self.history = {
            'gbest_fitness': [],
            'gbest_position': [],
            'particles_position': [],
            'w_history': []
        }
        self._stagnant_count = 0
        self._previous_best = float('inf')
        self._penalty_factor_history = [self.penalty_factor]


class ConstrainedPSO(PSO):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def check_feasibility(self, x):
        if self.ineq_constraints is None and self.eq_constraints is None:
            return True, 0.0

        violation = 0.0
        feasible = True

        if self.ineq_constraints is not None:
            ineq_vals = self.ineq_constraints(x)
            for g in ineq_vals:
                if g > 0:
                    violation += g ** 2
                    feasible = False

        if self.eq_constraints is not None:
            eq_vals = self.eq_constraints(x)
            for h in eq_vals:
                if abs(h) > 1e-6:
                    violation += h ** 2
                    feasible = False

        return feasible, violation


if __name__ == "__main__":
    from objective import TEST_FUNCTIONS

    func_name = 'sphere'
    func_info = TEST_FUNCTIONS[func_name]

    pso = PSO(
        fitness_func=func_info['function'],
        dim=2,
        bounds=func_info['bounds'],
        n_particles=30,
        max_iter=50,
        w=0.7,
        c1=1.49,
        c2=1.49,
        w_strategy='linear',
        w_start=0.9,
        w_end=0.4,
        random_state=42
    )

    best_position, best_fitness = pso.optimize(verbose=True)

    print(f"\nResults for {func_name}:")
    print(f"Best Position: {best_position}")
    print(f"Best Fitness: {best_fitness}")
    print(f"Optimal Position: {func_info['optimal_x']}")
    print(f"Optimal Fitness: {func_info['optimal']}")
