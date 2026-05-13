from typing import Dict, List, Optional, Tuple
import random
from collections import Counter
import copy

from population import Population, MetaPopulation
from allele import AllelePool
from selection import Fitness, SelectionModel

class WrightFisherSimulation:
    def __init__(self, population: Population, allele_pool: AllelePool, generations: int, runs: int = 1,
                 mutation_rate: float = 0.0, mutation_model: str = 'reciprocal',
                 reproduction_model: str = 'constant', allow_new_alleles: bool = False,
                 early_stop_on_fixation: bool = False,
                 selection_model: Optional[SelectionModel] = None):
        self.initial_population = population
        self.initial_allele_pool = allele_pool
        self.generations = generations
        self.runs = runs
        self.mutation_rate = max(0.0, min(1.0, mutation_rate))
        self.mutation_model = mutation_model
        self.reproduction_model = reproduction_model
        self.allow_new_alleles = allow_new_alleles
        self.early_stop_on_fixation = early_stop_on_fixation
        self.selection_model = selection_model
        self._results: List[List[Dict[str, float]]] = []
        self._population_history: List[List[int]] = []
        self._next_allele_id = 0
        self._is_meta_population = False
    
    def _apply_mutation(self, alleles: List[str]) -> List[str]:
        if self.mutation_rate <= 0.0:
            return alleles
        
        mutated_alleles = []
        allele_names = sorted(set(alleles))
        
        for allele in alleles:
            if random.random() < self.mutation_rate:
                if self.mutation_model == 'reciprocal':
                    other_alleles = [a for a in allele_names if a != allele]
                    if other_alleles:
                        mutated = random.choice(other_alleles)
                    else:
                        mutated = allele
                elif self.mutation_model == 'random':
                    if self.allow_new_alleles:
                        self._next_allele_id += 1
                        mutated = f'M{self._next_allele_id}'
                    else:
                        other_alleles = [a for a in allele_names if a != allele]
                        mutated = random.choice(other_alleles) if other_alleles else allele
                elif self.mutation_model == 'uniform':
                    all_alleles = allele_names
                    mutated = random.choice(all_alleles)
                else:
                    mutated = allele
                mutated_alleles.append(mutated)
            else:
                mutated_alleles.append(allele)
        
        return mutated_alleles
    
    def _apply_selection(self, frequencies: Dict[str, float]) -> Dict[str, float]:
        if self.selection_model is None:
            return frequencies
        return self.selection_model.apply_selection(frequencies)
    
    def _sample_next_generation(self, current_pool: AllelePool, population: Population) -> Dict[str, float]:
        current_freqs = {name: current_pool.get_frequency(name) for name in current_pool.get_allele_names()}
        
        selected_freqs = self._apply_selection(current_freqs)
        selected_pool = AllelePool(selected_freqs)
        
        next_size = population.reproduce(self.reproduction_model)
        
        sampled_alleles = []
        for _ in range(next_size):
            sampled_alleles.append(selected_pool.sample_allele())
        
        sampled_alleles = self._apply_mutation(sampled_alleles)
        
        count = Counter(sampled_alleles)
        total = len(sampled_alleles)
        
        all_alleles = set(current_pool.get_allele_names()) | set(count.keys())
        return {allele: count.get(allele, 0) / total for allele in all_alleles}, next_size
    
    def _is_fixed(self, frequencies: Dict[str, float]) -> bool:
        for freq in frequencies.values():
            if 0.0 < freq < 1.0:
                return False
        return True
    
    def _run_single_simulation(self) -> Tuple[List[Dict[str, float]], List[int]]:
        population = copy.deepcopy(self.initial_population)
        allele_names = self.initial_allele_pool.get_allele_names()
        current_frequencies = {name: self.initial_allele_pool.get_frequency(name) for name in allele_names}
        history = [current_frequencies.copy()]
        pop_size_history = [population.size]
        
        current_pool = AllelePool(current_frequencies)
        self._next_allele_id = 0
        
        for gen in range(self.generations):
            next_freq, next_size = self._sample_next_generation(current_pool, population)
            
            history.append(next_freq.copy())
            pop_size_history.append(next_size)
            
            population.size = next_size
            current_pool = AllelePool(next_freq)
            
            if self.early_stop_on_fixation and self._is_fixed(next_freq):
                while len(history) <= self.generations:
                    history.append(next_freq.copy())
                    pop_size_history.append(next_size)
                break
        
        return history, pop_size_history
    
    def run(self) -> List[List[Dict[str, float]]]:
        self._results = []
        self._population_history = []
        for _ in range(self.runs):
            history, pop_history = self._run_single_simulation()
            self._results.append(history)
            self._population_history.append(pop_history)
        return self._results
    
    def get_results(self) -> List[List[Dict[str, float]]]:
        return self._results
    
    def get_population_size_history(self) -> List[List[int]]:
        return self._population_history
    
    def get_allele_frequency_history(self, allele_name: str) -> List[List[float]]:
        if not self._results:
            raise RuntimeError("Simulation has not been run yet. Call run() first.")
        
        history = []
        for run in self._results:
            run_history = []
            for generation in run:
                run_history.append(generation.get(allele_name, 0.0))
            history.append(run_history)
        return history
    
    def get_average_frequency(self, allele_name: str) -> List[float]:
        if not self._results:
            raise RuntimeError("Simulation has not been run yet. Call run() first.")
        
        num_generations = len(self._results[0])
        avg_freq = []
        
        for gen in range(num_generations):
            total = sum(run[gen].get(allele_name, 0.0) for run in self._results)
            avg_freq.append(total / self.runs)
        
        return avg_freq
    
    def get_fixation_probability(self, allele_name: str) -> float:
        if not self._results:
            raise RuntimeError("Simulation has not been run yet. Call run() first.")
        
        fixed_count = 0
        for run in self._results:
            for gen in reversed(range(len(run))):
                freq = run[gen].get(allele_name, 0.0)
                if freq == 1.0:
                    fixed_count += 1
                    break
                elif freq < 1.0 and gen > 0:
                    break
        
        return fixed_count / self.runs
    
    def get_loss_probability(self, allele_name: str) -> float:
        if not self._results:
            raise RuntimeError("Simulation has not been run yet. Call run() first.")
        
        lost_count = 0
        for run in self._results:
            for gen in reversed(range(len(run))):
                freq = run[gen].get(allele_name, 0.0)
                if freq == 0.0:
                    lost_count += 1
                    break
                elif freq > 0.0 and gen > 0:
                    break
        
        return lost_count / self.runs
    
    def get_heterozygosity_history(self) -> List[List[float]]:
        if not self._results:
            raise RuntimeError("Simulation has not been run yet. Call run() first.")
        
        history = []
        for run in self._results:
            run_history = []
            for gen in run:
                het = 1.0 - sum(freq ** 2 for freq in gen.values())
                run_history.append(het)
            history.append(run_history)
        return history
    
    def get_time_to_fixation(self, allele_name: str) -> List[Optional[int]]:
        if not self._results:
            raise RuntimeError("Simulation has not been run yet. Call run() first.")
        
        times = []
        for run in self._results:
            fixed_gen = None
            for gen, freq_dict in enumerate(run):
                if freq_dict.get(allele_name, 0.0) == 1.0:
                    fixed_gen = gen
                    break
            times.append(fixed_gen)
        return times
    
    def get_time_to_loss(self, allele_name: str) -> List[Optional[int]]:
        if not self._results:
            raise RuntimeError("Simulation has not been run yet. Call run() first.")
        
        times = []
        for run in self._results:
            lost_gen = None
            for gen, freq_dict in enumerate(run):
                if freq_dict.get(allele_name, 0.0) == 0.0:
                    lost_gen = gen
                    break
            times.append(lost_gen)
        return times

class MetaPopulationSimulation:
    def __init__(self, meta_population: MetaPopulation, allele_pools: List[AllelePool], 
                 generations: int, runs: int = 1,
                 mutation_rate: float = 0.0, mutation_model: str = 'reciprocal',
                 reproduction_model: str = 'constant',
                 selection_models: Optional[List[SelectionModel]] = None,
                 migration_enabled: bool = True):
        if len(allele_pools) != meta_population.num_populations:
            raise ValueError(f"Number of allele pools ({len(allele_pools)}) must match number of populations ({meta_population.num_populations})")
        
        if selection_models is not None and len(selection_models) != meta_population.num_populations:
            raise ValueError(f"Number of selection models must match number of populations")
        
        self.meta_population = meta_population
        self.initial_allele_pools = allele_pools
        self.generations = generations
        self.runs = runs
        self.mutation_rate = max(0.0, min(1.0, mutation_rate))
        self.mutation_model = mutation_model
        self.reproduction_model = reproduction_model
        self.selection_models = selection_models or [None] * meta_population.num_populations
        self.migration_enabled = migration_enabled
        self._results: List[List[List[Dict[str, float]]]] = []
        self._population_history: List[List[List[int]]] = []
    
    def _apply_mutation(self, alleles: List[str]) -> List[str]:
        if self.mutation_rate <= 0.0:
            return alleles
        
        mutated_alleles = []
        allele_names = sorted(set(alleles))
        
        for allele in alleles:
            if random.random() < self.mutation_rate:
                if self.mutation_model == 'reciprocal':
                    other_alleles = [a for a in allele_names if a != allele]
                    mutated = random.choice(other_alleles) if other_alleles else allele
                elif self.mutation_model == 'uniform':
                    mutated = random.choice(allele_names)
                else:
                    mutated = allele
                mutated_alleles.append(mutated)
            else:
                mutated_alleles.append(allele)
        
        return mutated_alleles
    
    def _apply_migration(self, pop_frequencies: List[Dict[str, float]], 
                        pop_sizes: List[int]) -> List[Dict[str, float]]:
        if not self.migration_enabled:
            return pop_frequencies
        
        num_pops = self.meta_population.num_populations
        migrated_freqs = [dict(f) for f in pop_frequencies]
        
        all_alleles = set()
        for freq_dict in pop_frequencies:
            all_alleles.update(freq_dict.keys())
        
        for to_idx in range(num_pops):
            new_freqs = {allele: 0.0 for allele in all_alleles}
            
            for from_idx in range(num_pops):
                rate = self.meta_population.get_migration_rate(from_idx, to_idx)
                if rate <= 0.0 and from_idx != to_idx:
                    continue
                
                stay_rate = 1.0 - sum(
                    self.meta_population.get_migration_rate(to_idx, k) 
                    for k in range(num_pops) if k != to_idx
                ) if from_idx == to_idx else rate
                
                stay_rate = max(0.0, min(1.0, stay_rate))
                
                for allele in all_alleles:
                    freq = pop_frequencies[from_idx].get(allele, 0.0)
                    contribution = freq * (stay_rate if from_idx == to_idx else rate)
                    new_freqs[allele] += contribution
            
            total = sum(new_freqs.values())
            if total > 0:
                for allele in new_freqs:
                    new_freqs[allele] /= total
            
            migrated_freqs[to_idx] = new_freqs
        
        return migrated_freqs
    
    def _sample_population(self, frequencies: Dict[str, float], 
                          population: Population, 
                          selection_model: Optional[SelectionModel]) -> Tuple[Dict[str, float], int]:
        current_pool = AllelePool(frequencies)
        
        if selection_model is not None:
            selected_freqs = selection_model.apply_selection(frequencies)
            current_pool = AllelePool(selected_freqs)
        
        next_size = population.reproduce(self.reproduction_model)
        
        sampled_alleles = []
        for _ in range(next_size):
            sampled_alleles.append(current_pool.sample_allele())
        
        sampled_alleles = self._apply_mutation(sampled_alleles)
        
        count = Counter(sampled_alleles)
        total = len(sampled_alleles)
        
        all_alleles = set(frequencies.keys()) | set(count.keys())
        return {allele: count.get(allele, 0) / total for allele in all_alleles}, next_size
    
    def _run_single_simulation(self) -> Tuple[List[List[Dict[str, float]]], List[List[int]]]:
        num_pops = self.meta_population.num_populations
        
        populations = [copy.deepcopy(p) for p in self.meta_population.populations]
        
        current_freqs = []
        for pool in self.initial_allele_pools:
            freq_dict = {name: pool.get_frequency(name) for name in pool.get_allele_names()}
            current_freqs.append(freq_dict)
        
        history = [[dict(f) for f in current_freqs]]
        pop_size_history = [[p.size for p in populations]]
        
        for gen in range(self.generations):
            next_freqs = []
            next_sizes = []
            
            for idx in range(num_pops):
                freq, size = self._sample_population(
                    current_freqs[idx], 
                    populations[idx],
                    self.selection_models[idx]
                )
                next_freqs.append(freq)
                next_sizes.append(size)
                populations[idx].size = size
            
            if self.migration_enabled:
                next_freqs = self._apply_migration(next_freqs, next_sizes)
            
            history.append([dict(f) for f in next_freqs])
            pop_size_history.append(list(next_sizes))
            
            current_freqs = next_freqs
        
        return history, pop_size_history
    
    def run(self) -> List[List[List[Dict[str, float]]]]:
        self._results = []
        self._population_history = []
        for _ in range(self.runs):
            history, pop_history = self._run_single_simulation()
            self._results.append(history)
            self._population_history.append(pop_history)
        return self._results
    
    def get_results(self) -> List[List[List[Dict[str, float]]]]:
        return self._results
    
    def get_population_size_history(self) -> List[List[List[int]]]:
        return self._population_history
    
    def get_allele_frequency_history(self, allele_name: str, population_idx: int) -> List[List[float]]:
        if not self._results:
            raise RuntimeError("Simulation has not been run yet. Call run() first.")
        
        history = []
        for run in self._results:
            run_history = []
            for generation in run:
                run_history.append(generation[population_idx].get(allele_name, 0.0))
            history.append(run_history)
        return history
    
    def get_average_frequency(self, allele_name: str, population_idx: int) -> List[float]:
        if not self._results:
            raise RuntimeError("Simulation has not been run yet. Call run() first.")
        
        num_generations = len(self._results[0])
        avg_freq = []
        
        for gen in range(num_generations):
            total = sum(run[gen][population_idx].get(allele_name, 0.0) for run in self._results)
            avg_freq.append(total / self.runs)
        
        return avg_freq
    
    def get_global_frequency_history(self, allele_name: str) -> List[List[float]]:
        if not self._results:
            raise RuntimeError("Simulation has not been run yet. Call run() first.")
        
        num_pops = self.meta_population.num_populations
        history = []
        
        for run in self._results:
            run_history = []
            for generation in run:
                total_weighted = 0.0
                total_size = 0
                for idx in range(num_pops):
                    pop_size = generation[idx].get('_size', 0)
                    if pop_size == 0:
                        pop_size = 100
                    freq = generation[idx].get(allele_name, 0.0)
                    total_weighted += freq * pop_size
                    total_size += pop_size
                run_history.append(total_weighted / total_size if total_size > 0 else 0.0)
            history.append(run_history)
        
        return history
    
    def get_fst_history(self) -> List[List[float]]:
        if not self._results:
            raise RuntimeError("Simulation has not been run yet. Call run() first.")
        
        num_pops = self.meta_population.num_populations
        fst_history = []
        
        for run in self._results:
            run_fst = []
            for generation in run:
                all_alleles = set()
                for pop_freq in generation:
                    all_alleles.update(pop_freq.keys())
                
                if len(all_alleles) == 0:
                    run_fst.append(0.0)
                    continue
                
                global_freqs = {}
                for allele in all_alleles:
                    total = 0.0
                    for idx in range(num_pops):
                        total += generation[idx].get(allele, 0.0)
                    global_freqs[allele] = total / num_pops
                
                hs = 0.0
                ht = 0.0
                for allele in all_alleles:
                    p = global_freqs[allele]
                    ht += p * (1 - p)
                    within_pop = 0.0
                    for idx in range(num_pops):
                        pi = generation[idx].get(allele, 0.0)
                        within_pop += pi * (1 - pi)
                    hs += within_pop / num_pops
                
                fst = (ht - hs) / ht if ht > 0 else 0.0
                run_fst.append(fst)
            fst_history.append(run_fst)
        
        return fst_history
