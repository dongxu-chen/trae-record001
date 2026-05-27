import numpy as np
from itertools import product
from collections import defaultdict
from .signal_controller import DiscreteEventSimulator
from .traffic_model import TrafficModel


class MultiParamSignalOptimizer:
    def __init__(self, network_config, base_signal_config, od_matrix):
        self.network_config = network_config
        self.base_signal_config = base_signal_config
        self.od_matrix = od_matrix
        self.best_config = None
        self.best_score = float('inf')
        self.optimization_history = []
        self.optimization_type = 'full'

    def evaluate_config(self, signal_config, simulation_steps=200, method='ca'):
        try:
            if method == 'des':
                simulator = DiscreteEventSimulator(
                    self.network_config,
                    signal_config,
                    self.od_matrix
                )
                results = simulator.run(duration=simulation_steps)

                avg_queue = results.get('overall_avg_queue', 0)
                max_queue = results.get('overall_max_queue', 0)
                avg_travel_time = results.get('average_travel_time', 0)
                throughput = results.get('total_completed', 0)
            else:
                model = TrafficModel(
                    self.network_config,
                    signal_config,
                    self.od_matrix,
                    sim_config={"max_speed": 14, "generation_rate": 0.3, "use_parallel": True}
                )
                results = model.run_model(steps=simulation_steps)

                queues = results.get('queue_lengths', {})
                avg_queue = float(np.mean(list(queues.values()))) if queues else 0
                max_queue = float(np.max(list(queues.values()))) if queues else 0
                avg_travel_time = 0
                if results.get('metrics'):
                    speeds = [m.get('AvgSpeed', 0) for m in results['metrics']]
                    avg_speed = float(np.mean(speeds)) if speeds else 0
                    avg_travel_time = 100 / max(0.1, avg_speed)
                throughput = results.get('total_completed', 0)

            green_ratio = self._calculate_green_ratio(signal_config)
            cycle_efficiency = self._calculate_cycle_efficiency(signal_config)

            score = self._calculate_multi_objective_score(
                avg_queue, max_queue, avg_travel_time, throughput, green_ratio, cycle_efficiency
            )

            return {
                'score': score,
                'avg_queue': avg_queue,
                'max_queue': max_queue,
                'avg_travel_time': avg_travel_time,
                'throughput': throughput,
                'green_ratio': green_ratio,
                'cycle_efficiency': cycle_efficiency,
                'signal_config': signal_config
            }
        except Exception as e:
            return {
                'score': float('inf'),
                'avg_queue': 0,
                'max_queue': 0,
                'avg_travel_time': 0,
                'throughput': 0,
                'green_ratio': 0,
                'cycle_efficiency': 0,
                'signal_config': signal_config,
                'error': str(e)
            }

    def _calculate_multi_objective_score(self, avg_queue, max_queue, avg_travel_time, throughput, green_ratio, cycle_efficiency):
        w_queue = 0.25
        w_max_queue = 0.20
        w_travel = 0.20
        w_throughput = 0.15
        w_green = 0.10
        w_cycle = 0.10

        max_possible_queue = 50
        max_possible_travel_time = 100
        max_throughput = 200

        normalized_queue = min(1.0, avg_queue / max_possible_queue)
        normalized_max_queue = min(1.0, max_queue / max_possible_queue)
        normalized_travel = min(1.0, avg_travel_time / max_possible_travel_time)
        normalized_throughput = max(0, 1 - min(1.0, throughput / max_throughput))
        normalized_green = 1 - green_ratio if green_ratio > 0.7 else green_ratio
        normalized_cycle = 1 - cycle_efficiency if cycle_efficiency > 0.9 else cycle_efficiency

        score = (w_queue * normalized_queue +
                 w_max_queue * normalized_max_queue +
                 w_travel * normalized_travel +
                 w_throughput * normalized_throughput +
                 w_green * normalized_green +
                 w_cycle * normalized_cycle)

        return score

    def _calculate_green_ratio(self, signal_config):
        total_green = 0
        total_cycle = 0

        for signal in signal_config.get('signals', []):
            phases = signal.get('phases', [])
            for phase in phases:
                duration = phase.get('duration', 0)
                total_cycle += duration
                directions = phase.get('directions', {})
                if 'green' in directions:
                    total_green += duration

        return total_green / max(1, total_cycle)

    def _calculate_cycle_efficiency(self, signal_config):
        efficiencies = []

        for signal in signal_config.get('signals', []):
            phases = signal.get('phases', [])
            if len(phases) < 2:
                continue

            cycle_length = sum(p.get('duration', 0) for p in phases)
            if cycle_length == 0:
                continue

            green_times = []
            for phase in phases:
                directions = phase.get('directions', {})
                if 'green' in directions:
                    green_times.append(phase.get('duration', 0))

            if green_times:
                balance = min(green_times) / max(green_times) if max(green_times) > 0 else 0
                efficiencies.append(balance)

        return float(np.mean(efficiencies)) if efficiencies else 0.5

    def grid_search_optimize(self, min_duration=10, max_duration=60, step=10,
                             include_offset=False, method='ca'):
        signals = self.base_signal_config.get('signals', [])
        if not signals:
            return None

        signal_id = signals[0]['id']
        original_phases = signals[0]['phases']
        original_offset = signals[0].get('phase_offset', 0)

        best_results = None
        all_results = []

        durations = list(range(min_duration, max_duration + 1, step))

        if include_offset:
            offsets = list(range(0, 60, step))
        else:
            offsets = [original_offset]

        phase_combinations = list(product(durations, repeat=len(original_phases)))

        for combo in phase_combinations:
            for offset in offsets:
                new_signal_config = self._create_full_signal_config(
                    signal_id, original_phases, combo, offset
                )
                result = self.evaluate_config(new_signal_config, method=method)

                all_results.append({
                    'durations': combo,
                    'offset': offset,
                    'score': result['score'],
                    'avg_queue': result['avg_queue'],
                    'max_queue': result['max_queue'],
                    'throughput': result['throughput'],
                    'green_ratio': result['green_ratio'],
                    'cycle_efficiency': result['cycle_efficiency']
                })

                if result['score'] < self.best_score:
                    self.best_score = result['score']
                    self.best_config = new_signal_config
                    best_results = result

        self.optimization_history = sorted(all_results, key=lambda x: x['score'])[:20]
        return {
            'best_config': self.best_config,
            'best_score': self.best_score,
            'best_metrics': best_results,
            'history': self.optimization_history,
            'type': 'grid_search',
            'params_optimized': ['duration', 'offset'] if include_offset else ['duration']
        }

    def hill_climb_optimize(self, iterations=20, step_size=5, include_offset=False, method='ca'):
        signals = self.base_signal_config.get('signals', [])
        if not signals:
            return None

        signal_id = signals[0]['id']
        original_phases = signals[0]['phases']
        original_offset = signals[0].get('phase_offset', 0)

        current_durations = [phase['duration'] for phase in original_phases]
        current_offset = original_offset

        current_config = self._create_full_signal_config(
            signal_id, original_phases, current_durations, current_offset
        )
        current_result = self.evaluate_config(current_config, method=method)
        current_score = current_result['score']

        self.best_score = current_score
        self.best_config = current_config
        self.optimization_history.append({
            'iteration': 0,
            'durations': tuple(current_durations),
            'offset': current_offset,
            'score': current_score,
            'avg_queue': current_result['avg_queue'],
            'green_ratio': current_result['green_ratio']
        })

        for i in range(1, iterations + 1):
            improved = False
            neighbors = self._get_multi_param_neighbors(
                current_durations, current_offset, step_size, include_offset
            )

            for neighbor_durations, neighbor_offset in neighbors:
                neighbor_config = self._create_full_signal_config(
                    signal_id, original_phases, neighbor_durations, neighbor_offset
                )
                neighbor_result = self.evaluate_config(neighbor_config, method=method)

                if neighbor_result['score'] < current_score:
                    current_durations = list(neighbor_durations)
                    current_offset = neighbor_offset
                    current_score = neighbor_result['score']
                    current_result = neighbor_result
                    improved = True

                    if current_score < self.best_score:
                        self.best_score = current_score
                        self.best_config = neighbor_config

            self.optimization_history.append({
                'iteration': i,
                'durations': tuple(current_durations),
                'offset': current_offset,
                'score': current_score,
                'avg_queue': current_result['avg_queue'],
                'green_ratio': current_result.get('green_ratio', 0)
            })

            if not improved:
                break

        return {
            'best_config': self.best_config,
            'best_score': self.best_score,
            'final_durations': current_durations,
            'final_offset': current_offset,
            'history': self.optimization_history,
            'type': 'hill_climb',
            'params_optimized': ['duration', 'offset'] if include_offset else ['duration']
        }

    def genetic_algorithm_optimize(self, population_size=20, generations=10,
                                    mutation_rate=0.2, include_offset=False, method='ca'):
        signals = self.base_signal_config.get('signals', [])
        if not signals:
            return None

        signal_id = signals[0]['id']
        original_phases = signals[0]['phases']
        num_phases = len(original_phases)

        min_dur, max_dur = 10, 60
        min_offset, max_offset = 0, 59

        def create_individual():
            durations = [np.random.randint(min_dur, max_dur + 1) for _ in range(num_phases)]
            offset = np.random.randint(min_offset, max_offset + 1) if include_offset else 0
            return (durations, offset)

        def fitness(individual):
            durations, offset = individual
            config = self._create_full_signal_config(signal_id, original_phases, durations, offset)
            result = self.evaluate_config(config, method=method)
            return result['score'], result

        population = [create_individual() for _ in range(population_size)]

        for gen in range(generations):
            fitness_results = []
            for ind in population:
                score, metrics = fitness(ind)
                fitness_results.append((score, ind, metrics))

            fitness_results.sort(key=lambda x: x[0])

            best_score, best_ind, best_metrics = fitness_results[0]
            if best_score < self.best_score:
                self.best_score = best_score
                best_durations, best_offset = best_ind
                self.best_config = self._create_full_signal_config(
                    signal_id, original_phases, best_durations, best_offset
                )

            self.optimization_history.append({
                'generation': gen,
                'best_score': best_score,
                'best_durations': tuple(best_ind[0]),
                'best_offset': best_ind[1],
                'avg_queue': best_metrics['avg_queue'],
                'throughput': best_metrics['throughput'],
                'green_ratio': best_metrics.get('green_ratio', 0)
            })

            new_population = [best_ind]

            while len(new_population) < population_size:
                parents = self._tournament_selection(fitness_results)
                child = self._crossover(parents[0], parents[1], include_offset)
                child = self._mutate(child, mutation_rate, min_dur, max_dur, min_offset, max_offset, include_offset)
                new_population.append(child)

            population = new_population

        return {
            'best_config': self.best_config,
            'best_score': self.best_score,
            'history': self.optimization_history,
            'type': 'genetic',
            'params_optimized': ['duration', 'offset'] if include_offset else ['duration']
        }

    def _get_multi_param_neighbors(self, durations, offset, step_size, include_offset):
        neighbors = []

        for i in range(len(durations)):
            for delta in [-step_size, step_size]:
                new_dur = durations[i] + delta
                if 10 <= new_dur <= 60:
                    new_durations = list(durations)
                    new_durations[i] = new_dur
                    neighbors.append((new_durations, offset))

        if include_offset:
            for delta in [-step_size, step_size]:
                new_offset = (offset + delta) % 60
                neighbors.append((list(durations), new_offset))

        return neighbors

    def _tournament_selection(self, fitness_results, tournament_size=3):
        selected = []
        for _ in range(2):
            tournament = np.random.choice(len(fitness_results), tournament_size, replace=False)
            winner_idx = min(tournament, key=lambda i: fitness_results[i][0])
            selected.append(fitness_results[winner_idx][1])
        return selected

    def _crossover(self, parent1, parent2, include_offset):
        durations1, offset1 = parent1
        durations2, offset2 = parent2

        if len(durations1) >= 2:
            point = np.random.randint(1, len(durations1))
            child_durations = durations1[:point] + durations2[point:]
        else:
            child_durations = durations1

        child_offset = offset1 if np.random.random() < 0.5 else offset2
        return (child_durations, child_offset)

    def _mutate(self, individual, mutation_rate, min_dur, max_dur, min_offset, max_offset, include_offset):
        durations, offset = individual
        mutated_durations = list(durations)

        for i in range(len(mutated_durations)):
            if np.random.random() < mutation_rate:
                mutated_durations[i] = np.random.randint(min_dur, max_dur + 1)

        mutated_offset = offset
        if include_offset and np.random.random() < mutation_rate:
            mutated_offset = np.random.randint(min_offset, max_offset + 1)

        return (mutated_durations, mutated_offset)

    def _create_full_signal_config(self, signal_id, original_phases, durations, offset=0):
        new_phases = []
        for i, phase in enumerate(original_phases):
            new_phase = dict(phase)
            new_phase['duration'] = int(durations[i])
            new_phases.append(new_phase)

        new_signals = []
        for signal in self.base_signal_config.get('signals', []):
            if signal['id'] == signal_id:
                new_signal = dict(signal)
                new_signal['phases'] = new_phases
                new_signal['phase_offset'] = offset
                new_signals.append(new_signal)
            else:
                new_signals.append(dict(signal))

        return {'signals': new_signals}

    def get_optimization_report(self):
        if not self.best_config:
            return {'status': 'No optimization performed'}

        signals = self.best_config.get('signals', [])
        signal_details = []
        for signal in signals:
            phases = signal.get('phases', [])
            signal_details.append({
                'id': signal['id'],
                'offset': signal.get('phase_offset', 0),
                'durations': [phase.get('duration') for phase in phases],
                'green_ratio': self._calculate_green_ratio({'signals': [signal]})
            })

        return {
            'status': 'Optimization complete',
            'best_score': self.best_score,
            'signal_details': signal_details,
            'total_iterations': len(self.optimization_history),
            'history': self.optimization_history,
            'recommended_config': self.best_config
        }

    def compare_configurations(self, config1, config2, simulation_steps=200, method='ca'):
        result1 = self.evaluate_config(config1, simulation_steps, method)
        result2 = self.evaluate_config(config2, simulation_steps, method)

        improvement = ((result1['score'] - result2['score']) / max(0.001, result1['score'])) * 100

        return {
            'original': result1,
            'optimized': result2,
            'improvement_percent': improvement,
            'is_better': result2['score'] < result1['score'],
            'green_ratio_change': result2.get('green_ratio', 0) - result1.get('green_ratio', 0),
            'cycle_efficiency_change': result2.get('cycle_efficiency', 0) - result1.get('cycle_efficiency', 0)
        }


SignalOptimizer = MultiParamSignalOptimizer
