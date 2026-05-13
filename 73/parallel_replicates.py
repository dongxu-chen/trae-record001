import random
import copy
from typing import Dict, List, Optional, Tuple, Callable, Any
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
import multiprocessing as mp
from functools import partial

from population import Population, MetaPopulation
from allele import AllelePool
from selection import SelectionModel
from drift import WrightFisherSimulation, MetaPopulationSimulation

def _run_single_replicate(sim_config: Dict[str, Any], 
                         random_seed: Optional[int] = None,
                         sim_type: str = 'single') -> Dict[str, Any]:
    if random_seed is not None:
        random.seed(random_seed)
    
    if sim_type == 'single':
        simulation = WrightFisherSimulation(
            population=sim_config['population'],
            allele_pool=sim_config['allele_pool'],
            generations=sim_config['generations'],
            runs=1,
            mutation_rate=sim_config.get('mutation_rate', 0.0),
            mutation_model=sim_config.get('mutation_model', 'reciprocal'),
            reproduction_model=sim_config.get('reproduction_model', 'constant'),
            allow_new_alleles=sim_config.get('allow_new_alleles', False),
            early_stop_on_fixation=sim_config.get('early_stop_on_fixation', False),
            selection_model=sim_config.get('selection_model', None)
        )
        simulation.run()
        
        return {
            'frequencies': simulation.get_results()[0],
            'population_size': simulation.get_population_size_history()[0]
        }
    
    elif sim_type == 'meta':
        simulation = MetaPopulationSimulation(
            meta_population=sim_config['meta_population'],
            allele_pools=sim_config['allele_pools'],
            generations=sim_config['generations'],
            runs=1,
            mutation_rate=sim_config.get('mutation_rate', 0.0),
            mutation_model=sim_config.get('mutation_model', 'reciprocal'),
            reproduction_model=sim_config.get('reproduction_model', 'constant'),
            selection_models=sim_config.get('selection_models', None),
            migration_enabled=sim_config.get('migration_enabled', True)
        )
        simulation.run()
        
        return {
            'frequencies': simulation.get_results()[0],
            'population_size': simulation.get_population_size_history()[0]
        }

class ParallelReplicates:
    def __init__(self, num_replicates: int = 10, 
                 num_workers: Optional[int] = None,
                 use_processes: bool = True):
        self.num_replicates = num_replicates
        self.num_workers = num_workers if num_workers is not None else mp.cpu_count()
        self.use_processes = use_processes
        self._results: List[Dict[str, Any]] = []
        self._sim_type: str = 'single'
    
    def run_single_population(self,
                             population: Population,
                             allele_pool: AllelePool,
                             generations: int,
                             mutation_rate: float = 0.0,
                             mutation_model: str = 'reciprocal',
                             reproduction_model: str = 'constant',
                             allow_new_alleles: bool = False,
                             early_stop_on_fixation: bool = False,
                             selection_model: Optional[SelectionModel] = None,
                             base_seed: Optional[int] = None) -> List[Dict[str, Any]]:
        
        self._sim_type = 'single'
        
        sim_config = {
            'population': population,
            'allele_pool': allele_pool,
            'generations': generations,
            'mutation_rate': mutation_rate,
            'mutation_model': mutation_model,
            'reproduction_model': reproduction_model,
            'allow_new_alleles': allow_new_alleles,
            'early_stop_on_fixation': early_stop_on_fixation,
            'selection_model': selection_model
        }
        
        seeds = [base_seed + i if base_seed is not None else None 
                 for i in range(self.num_replicates)]
        
        results = []
        
        if self.use_processes and self.num_workers > 1:
            with ProcessPoolExecutor(max_workers=self.num_workers) as executor:
                futures = [
                    executor.submit(_run_single_replicate, 
                                   copy.deepcopy(sim_config), 
                                   seed, 
                                   'single')
                    for seed in seeds
                ]
                for future in as_completed(futures):
                    results.append(future.result())
        else:
            for seed in seeds:
                results.append(_run_single_replicate(
                    copy.deepcopy(sim_config), seed, 'single'
                ))
        
        self._results = results
        return results
    
    def run_meta_population(self,
                           meta_population: MetaPopulation,
                           allele_pools: List[AllelePool],
                           generations: int,
                           mutation_rate: float = 0.0,
                           mutation_model: str = 'reciprocal',
                           reproduction_model: str = 'constant',
                           selection_models: Optional[List[SelectionModel]] = None,
                           migration_enabled: bool = True,
                           base_seed: Optional[int] = None) -> List[Dict[str, Any]]:
        
        self._sim_type = 'meta'
        
        sim_config = {
            'meta_population': meta_population,
            'allele_pools': allele_pools,
            'generations': generations,
            'mutation_rate': mutation_rate,
            'mutation_model': mutation_model,
            'reproduction_model': reproduction_model,
            'selection_models': selection_models,
            'migration_enabled': migration_enabled
        }
        
        seeds = [base_seed + i if base_seed is not None else None 
                 for i in range(self.num_replicates)]
        
        results = []
        
        if self.use_processes and self.num_workers > 1:
            with ProcessPoolExecutor(max_workers=self.num_workers) as executor:
                futures = [
                    executor.submit(_run_single_replicate, 
                                   copy.deepcopy(sim_config), 
                                   seed, 
                                   'meta')
                    for seed in seeds
                ]
                for future in as_completed(futures):
                    results.append(future.result())
        else:
            for seed in seeds:
                results.append(_run_single_replicate(
                    copy.deepcopy(sim_config), seed, 'meta'
                ))
        
        self._results = results
        return results
    
    def get_results(self) -> List[Dict[str, Any]]:
        return self._results
    
    def get_allele_frequency_history(self, allele_name: str,
                                    population_idx: Optional[int] = None) -> List[List[float]]:
        if not self._results:
            raise RuntimeError("No results available. Run simulation first.")
        
        history = []
        for result in self._results:
            if self._sim_type == 'single':
                run_history = []
                for gen in result['frequencies']:
                    run_history.append(gen.get(allele_name, 0.0))
                history.append(run_history)
            else:
                if population_idx is None:
                    raise ValueError("population_idx is required for meta-population results")
                run_history = []
                for gen in result['frequencies']:
                    run_history.append(gen[population_idx].get(allele_name, 0.0))
                history.append(run_history)
        
        return history
    
    def get_average_frequency(self, allele_name: str,
                             population_idx: Optional[int] = None) -> List[float]:
        history = self.get_allele_frequency_history(allele_name, population_idx)
        if not history:
            return []
        
        num_generations = len(history[0])
        avg_freq = []
        
        for gen in range(num_generations):
            total = sum(run[gen] for run in history)
            avg_freq.append(total / len(history))
        
        return avg_freq
    
    def get_fixation_probability(self, allele_name: str,
                                population_idx: Optional[int] = None) -> float:
        history = self.get_allele_frequency_history(allele_name, population_idx)
        if not history:
            return 0.0
        
        fixed_count = 0
        for run_history in history:
            for freq in reversed(run_history):
                if freq == 1.0:
                    fixed_count += 1
                    break
                elif freq < 1.0:
                    break
        
        return fixed_count / len(history)
    
    def get_loss_probability(self, allele_name: str,
                            population_idx: Optional[int] = None) -> float:
        history = self.get_allele_frequency_history(allele_name, population_idx)
        if not history:
            return 0.0
        
        lost_count = 0
        for run_history in history:
            for freq in reversed(run_history):
                if freq == 0.0:
                    lost_count += 1
                    break
                elif freq > 0.0:
                    break
        
        return lost_count / len(history)
    
    def get_heterozygosity_history(self,
                                   population_idx: Optional[int] = None) -> List[List[float]]:
        if not self._results:
            raise RuntimeError("No results available. Run simulation first.")
        
        history = []
        for result in self._results:
            if self._sim_type == 'single':
                run_history = []
                for gen in result['frequencies']:
                    het = 1.0 - sum(freq ** 2 for freq in gen.values())
                    run_history.append(het)
                history.append(run_history)
            else:
                if population_idx is None:
                    raise ValueError("population_idx is required for meta-population results")
                run_history = []
                for gen in result['frequencies']:
                    het = 1.0 - sum(freq ** 2 for freq in gen[population_idx].values())
                    run_history.append(het)
                history.append(run_history)
        
        return history
    
    def get_population_size_history(self,
                                    population_idx: Optional[int] = None) -> List[List[int]]:
        if not self._results:
            raise RuntimeError("No results available. Run simulation first.")
        
        history = []
        for result in self._results:
            if self._sim_type == 'single':
                history.append(result['population_size'])
            else:
                if population_idx is None:
                    raise ValueError("population_idx is required for meta-population results")
                pop_history = []
                for gen in result['population_size']:
                    pop_history.append(gen[population_idx])
                history.append(pop_history)
        
        return history
    
    def get_summary_statistics(self, allele_name: str,
                               population_idx: Optional[int] = None) -> Dict[str, Any]:
        history = self.get_allele_frequency_history(allele_name, population_idx)
        if not history:
            return {}
        
        avg_freq = self.get_average_frequency(allele_name, population_idx)
        fix_prob = self.get_fixation_probability(allele_name, population_idx)
        loss_prob = self.get_loss_probability(allele_name, population_idx)
        
        final_freqs = [run[-1] for run in history]
        mean_final = sum(final_freqs) / len(final_freqs)
        variance_final = sum((f - mean_final) ** 2 for f in final_freqs) / len(final_freqs)
        
        return {
            'num_replicates': len(history),
            'initial_frequency': history[0][0],
            'final_frequency_mean': mean_final,
            'final_frequency_variance': variance_final,
            'fixation_probability': fix_prob,
            'loss_probability': loss_prob,
            'average_frequency_history': avg_freq,
            'num_generations': len(avg_freq)
        }
