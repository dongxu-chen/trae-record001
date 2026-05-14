import numpy as np
from multiprocessing import Pool, cpu_count, Manager
from particle import Particle, calculate_inertia_weight
from pso import PSO


def evaluate_single(args):
    position, fitness_func = args
    return fitness_func(position)


def evaluate_batch(args):
    positions, fitness_func = args
    return [fitness_func(pos) for pos in positions]


class ParallelPSO(PSO):
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
        penalty_alpha=2,
        n_processes=None,
        batch_size=1,
        strategy='island'
    ):
        super().__init__(
            fitness_func=fitness_func,
            dim=dim,
            bounds=bounds,
            n_particles=n_particles,
            max_iter=max_iter,
            w=w,
            c1=c1,
            c2=c2,
            w_decay=w_decay,
            v_max=v_max,
            random_state=random_state,
            stagnation_threshold=stagnation_threshold,
            max_stagnant_iters=max_stagnant_iters,
            use_adaptive_w=use_adaptive_w,
            w_strategy=w_strategy,
            w_start=w_start,
            w_end=w_end,
            ineq_constraints=ineq_constraints,
            eq_constraints=eq_constraints,
            penalty_type=penalty_type,
            penalty_factor=penalty_factor,
            penalty_C=penalty_C,
            penalty_alpha=penalty_alpha
        )

        if n_processes is None:
            self.n_processes = max(1, cpu_count() - 1)
        else:
            self.n_processes = n_processes

        self.batch_size = batch_size
        self.strategy = strategy

    def _evaluate_parallel_single(self, positions):
        args = [(pos, self.fitness_func) for pos in positions]
        with Pool(processes=self.n_processes) as pool:
            return pool.map(evaluate_single, args)

    def _evaluate_parallel_batch(self, positions):
        n = len(positions)
        batch_size = max(1, n // self.n_processes)
        batches = [positions[i:i + batch_size] for i in range(0, n, batch_size)]
        args = [(batch, self.fitness_func) for batch in batches]
        with Pool(processes=self.n_processes) as pool:
            results = pool.map(evaluate_batch, args)
        return [fit for batch in results for fit in batch]

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
                particle.update_velocity(
                    self.gbest_position,
                    current_w,
                    self.c1,
                    self.c2,
                    self.v_max
                )
                particle.update_position()

            positions = [p.position.copy() for p in self.particles]

            if self.batch_size == 1:
                raw_fitnesses = self._evaluate_parallel_single(positions)
            else:
                raw_fitnesses = self._evaluate_parallel_batch(positions)

            for i, (particle, raw_fitness) in enumerate(zip(self.particles, raw_fitnesses)):
                penalized_fitness = self._apply_penalty(particle.position, raw_fitness, iteration)
                particle.fitness = penalized_fitness

                if penalized_fitness < particle.pbest_fitness:
                    particle.pbest_fitness = penalized_fitness
                    particle.pbest_position = particle.position.copy()
                    improved = True
                else:
                    improved = False

                if self.use_adaptive_w and hasattr(particle, 'record_outcome'):
                    particle.record_outcome(improved)
                    if hasattr(particle, 'update_adaptive_w'):
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


def run_island_pso(
    fitness_func,
    dim,
    bounds,
    n_particles=50,
    max_iter=100,
    n_islands=None,
    migration_interval=10,
    migration_rate=0.1,
    n_processes=None,
    **kwargs
):
    if n_islands is None:
        n_islands = max(1, cpu_count() - 1)

    if n_processes is None:
        n_processes = n_islands

    islands = []
    for i in range(n_islands):
        pso = PSO(
            fitness_func=fitness_func,
            dim=dim,
            bounds=bounds,
            n_particles=n_particles,
            max_iter=max_iter,
            **kwargs
        )
        islands.append(pso)

    def run_island_iteration(args):
        pso, current_iter, max_iterations = args
        pso.max_iter = 1
        pso.optimize(verbose=False)
        return {
            'particles': [(p.position.copy(), p.pbest_fitness, p.pbest_position.copy()) for p in pso.particles],
            'gbest': (pso.gbest_position.copy(), pso.gbest_fitness),
            'history': pso.history
        }

    best_overall = float('inf')
    best_position = None

    for iteration in range(0, max_iter, migration_interval):
        current_max_iter = min(migration_interval, max_iter - iteration)

        args_list = [(island, iteration, current_max_iter) for island in islands]

        with Pool(processes=n_processes) as pool:
            results = pool.map(run_island_iteration, args_list)

        for idx, result in enumerate(results):
            island = islands[idx]
            for i, (pos, pbest_fit, pbest_pos) in enumerate(result['particles']):
                island.particles[i].position = pos.copy()
                island.particles[i].pbest_fitness = pbest_fit
                island.particles[i].pbest_position = pbest_pos.copy()
            island.gbest_position = result['gbest'][0].copy()
            island.gbest_fitness = result['gbest'][1]

            if island.gbest_fitness < best_overall:
                best_overall = island.gbest_fitness
                best_position = island.gbest_position.copy()

        if iteration + migration_interval < max_iter:
            all_particles = []
            for island in islands:
                all_particles.extend([(p.pbest_position.copy(), p.pbest_fitness) for p in island.particles])

            all_particles.sort(key=lambda x: x[1])
            n_migrate = max(1, int(len(all_particles) * migration_rate / n_islands))
            best_particles = all_particles[:n_migrate]

            for island in islands:
                island_indices = np.random.choice(len(island.particles), size=min(n_migrate, len(island.particles)), replace=False)
                for i, idx in enumerate(island_indices):
                    if i < len(best_particles):
                        island.particles[idx].position = best_particles[i][0].copy()
                        island.particles[idx].pbest_position = best_particles[i][0].copy()
                        island.particles[idx].pbest_fitness = best_particles[i][1]

    return best_position, best_overall, islands


if __name__ == "__main__":
    from objective import TEST_FUNCTIONS
    import time

    func_name = 'rastrigin'
    func_info = TEST_FUNCTIONS[func_name]

    print(f"Testing Parallel PSO on {func_name}...")
    print(f"CPU Cores: {cpu_count()}")

    print("\n1. Sequential PSO:")
    start_time = time.time()
    pso_seq = PSO(
        fitness_func=func_info['function'],
        dim=10,
        bounds=func_info['bounds'] * 5,
        n_particles=100,
        max_iter=50,
        w_strategy='linear',
        random_state=42
    )
    best_pos_seq, best_fit_seq = pso_seq.optimize(verbose=False)
    seq_time = time.time() - start_time
    print(f"  Best Fitness: {best_fit_seq:.6f}")
    print(f"  Time: {seq_time:.2f}s")

    print("\n2. Parallel PSO (single evaluation):")
    start_time = time.time()
    pso_par = ParallelPSO(
        fitness_func=func_info['function'],
        dim=10,
        bounds=func_info['bounds'] * 5,
        n_particles=100,
        max_iter=50,
        w_strategy='linear',
        random_state=42,
        batch_size=1
    )
    best_pos_par, best_fit_par = pso_par.optimize(verbose=False)
    par_time = time.time() - start_time
    print(f"  Best Fitness: {best_fit_par:.6f}")
    print(f"  Time: {par_time:.2f}s")
    print(f"  Speedup: {seq_time/par_time:.2f}x")

    print("\n3. Parallel PSO (batch evaluation):")
    start_time = time.time()
    pso_batch = ParallelPSO(
        fitness_func=func_info['function'],
        dim=10,
        bounds=func_info['bounds'] * 5,
        n_particles=100,
        max_iter=50,
        w_strategy='linear',
        random_state=42,
        batch_size=10
    )
    best_pos_batch, best_fit_batch = pso_batch.optimize(verbose=False)
    batch_time = time.time() - start_time
    print(f"  Best Fitness: {best_fit_batch:.6f}")
    print(f"  Time: {batch_time:.2f}s")
    print(f"  Speedup: {seq_time/batch_time:.2f}x")
