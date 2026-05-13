from typing import List, Dict, Optional, Union
import matplotlib.pyplot as plt
import numpy as np

from drift import WrightFisherSimulation, MetaPopulationSimulation
from parallel_replicates import ParallelReplicates

class FrequencyPlotter:
    def __init__(self, simulation: Union[WrightFisherSimulation, ParallelReplicates]):
        self.simulation = simulation
        self._is_parallel = isinstance(simulation, ParallelReplicates)
    
    def _get_ylim(self, all_frequencies: List[float], auto_scale: bool = False) -> tuple:
        if auto_scale:
            min_freq = min(all_frequencies)
            max_freq = max(all_frequencies)
            range_freq = max_freq - min_freq
            
            if range_freq == 0:
                margin = 0.1
            else:
                margin = max(0.05, range_freq * 0.1)
            
            y_min = max(0.0, min_freq - margin)
            y_max = min(1.0, max_freq + margin)
            return (y_min, y_max)
        else:
            return (0.0, 1.05)
    
    def plot_single_run(self, run_index: int = 0, save_path: Optional[str] = None, show: bool = True, auto_ylim: bool = False):
        results = self.simulation.get_results()
        if not results:
            raise RuntimeError("Simulation has not been run yet. Call run() first.")
        
        if run_index >= len(results):
            raise ValueError(f"Run index {run_index} out of range (total runs: {len(results)})")
        
        run_data = results[run_index]
        all_alleles = set()
        for gen in run_data:
            all_alleles.update(gen.keys())
        allele_names = sorted(all_alleles)
        generations = list(range(len(run_data)))
        
        plt.figure(figsize=(10, 6))
        
        all_frequencies = []
        for allele in allele_names:
            frequencies = [gen.get(allele, 0.0) for gen in run_data]
            all_frequencies.extend(frequencies)
            plt.plot(generations, frequencies, label=f'Allele {allele}', linewidth=2)
        
        plt.xlabel('Generation')
        plt.ylabel('Allele Frequency')
        plt.title(f'Genetic Drift - Run {run_index + 1}')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.ylim(self._get_ylim(all_frequencies, auto_ylim))
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        if show:
            plt.show()
        else:
            plt.close()
    
    def plot_all_runs(self, allele_name: str, save_path: Optional[str] = None, show: bool = True, 
                      alpha: float = 0.3, auto_ylim: bool = False):
        if not self.simulation.get_results():
            raise RuntimeError("Simulation has not been run yet. Call run() first.")
        
        history = self.simulation.get_allele_frequency_history(allele_name)
        num_generations = len(history[0])
        generations = list(range(num_generations))
        
        plt.figure(figsize=(10, 6))
        
        all_frequencies = []
        for run_idx, run_history in enumerate(history):
            all_frequencies.extend(run_history)
            plt.plot(generations, run_history, alpha=alpha, linewidth=1.5)
        
        avg_freq = self.simulation.get_average_frequency(allele_name)
        all_frequencies.extend(avg_freq)
        plt.plot(generations, avg_freq, color='red', linewidth=2, label='Average')
        
        plt.xlabel('Generation')
        plt.ylabel(f'Frequency of Allele {allele_name}')
        plt.title(f'Genetic Drift - {self.simulation.runs} Simulations (Allele {allele_name})')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.ylim(self._get_ylim(all_frequencies, auto_ylim))
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        if show:
            plt.show()
        else:
            plt.close()
    
    def plot_all_alleles(self, save_path: Optional[str] = None, show: bool = True, 
                         alpha: float = 0.3, auto_ylim: bool = False):
        if not self.simulation.get_results():
            raise RuntimeError("Simulation has not been run yet. Call run() first.")
        
        all_alleles = set()
        for run in self.simulation.get_results():
            for gen in run:
                all_alleles.update(gen.keys())
        allele_names = sorted(all_alleles)
        num_generations = len(self.simulation.get_results()[0])
        generations = list(range(num_generations))
        
        colors = plt.cm.tab10(np.linspace(0, 1, max(1, len(allele_names))))
        
        plt.figure(figsize=(10, 6))
        
        all_frequencies = []
        for idx, allele in enumerate(allele_names):
            history = self.simulation.get_allele_frequency_history(allele)
            for run_history in history:
                all_frequencies.extend(run_history)
                plt.plot(generations, run_history, color=colors[idx], alpha=alpha, linewidth=1)
            
            avg_freq = self.simulation.get_average_frequency(allele)
            all_frequencies.extend(avg_freq)
            plt.plot(generations, avg_freq, color=colors[idx], linewidth=2.5, 
                     label=f'{allele} (avg)')
        
        plt.xlabel('Generation')
        plt.ylabel('Allele Frequency')
        plt.title(f'Genetic Drift - All Alleles ({self.simulation.runs} Simulations)')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.ylim(self._get_ylim(all_frequencies, auto_ylim))
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        if show:
            plt.show()
        else:
            plt.close()
    
    def plot_heterozygosity(self, save_path: Optional[str] = None, show: bool = True, 
                            alpha: float = 0.3, auto_ylim: bool = False):
        if not self.simulation.get_results():
            raise RuntimeError("Simulation has not been run yet. Call run() first.")
        
        het_history = self.simulation.get_heterozygosity_history()
        num_generations = len(het_history[0])
        generations = list(range(num_generations))
        
        plt.figure(figsize=(10, 6))
        
        all_het = []
        for run_het in het_history:
            all_het.extend(run_het)
            plt.plot(generations, run_het, alpha=alpha, linewidth=1.5)
        
        avg_het = [sum(gen) / self.simulation.runs for gen in zip(*het_history)]
        all_het.extend(avg_het)
        plt.plot(generations, avg_het, color='red', linewidth=2, label='Average')
        
        plt.xlabel('Generation')
        plt.ylabel('Heterozygosity (H)')
        plt.title(f'Heterozygosity Over Time ({self.simulation.runs} Simulations)')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.ylim(self._get_ylim(all_het, auto_ylim))
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        if show:
            plt.show()
        else:
            plt.close()
    
    def plot_population_size(self, save_path: Optional[str] = None, show: bool = True, 
                             alpha: float = 0.3, auto_ylim: bool = True):
        if not self.simulation.get_results():
            raise RuntimeError("Simulation has not been run yet. Call run() first.")
        
        pop_history = self.simulation.get_population_size_history()
        if not pop_history:
            raise RuntimeError("No population size history available. Use variable size model.")
        
        num_generations = len(pop_history[0])
        generations = list(range(num_generations))
        
        plt.figure(figsize=(10, 6))
        
        all_sizes = []
        for run_sizes in pop_history:
            all_sizes.extend(run_sizes)
            plt.plot(generations, run_sizes, alpha=alpha, linewidth=1.5)
        
        avg_sizes = [sum(gen) / self.simulation.runs for gen in zip(*pop_history)]
        all_sizes.extend(avg_sizes)
        plt.plot(generations, avg_sizes, color='red', linewidth=2, label='Average')
        
        plt.xlabel('Generation')
        plt.ylabel('Population Size (N)')
        plt.title(f'Population Size Over Time ({self.simulation.runs} Simulations)')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        if auto_ylim:
            min_size = min(all_sizes)
            max_size = max(all_sizes)
            margin = max(1, int((max_size - min_size) * 0.1)) if max_size > min_size else 1
            plt.ylim(max(0, min_size - margin), max_size + margin)
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        if show:
            plt.show()
        else:
            plt.close()
    
    def plot_statistics(self, save_path: Optional[str] = None, show: bool = True):
        if not self.simulation.get_results():
            raise RuntimeError("Simulation has not been run yet. Call run() first.")
        
        all_alleles = set()
        for run in self.simulation.get_results():
            for gen in run:
                all_alleles.update(gen.keys())
        allele_names = sorted(all_alleles)
        
        fixation_probs = [self.simulation.get_fixation_probability(a) for a in allele_names]
        loss_probs = [self.simulation.get_loss_probability(a) for a in allele_names]
        
        x = np.arange(len(allele_names))
        width = 0.35
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        bars1 = ax.bar(x - width/2, fixation_probs, width, label='Fixation Probability', color='green', alpha=0.7)
        bars2 = ax.bar(x + width/2, loss_probs, width, label='Loss Probability', color='red', alpha=0.7)
        
        ax.set_xlabel('Allele')
        ax.set_ylabel('Probability')
        initial_pop_size = self.simulation.initial_population.size
        ax.set_title(f'Fixation and Loss Probabilities (N0={initial_pop_size}, {self.simulation.runs} runs)')
        ax.set_xticks(x)
        ax.set_xticklabels(allele_names)
        ax.legend()
        ax.grid(True, alpha=0.3, axis='y')
        ax.set_ylim(0, max(max(fixation_probs), max(loss_probs)) * 1.1 if (fixation_probs or loss_probs) else 1.1)
        
        for bar in bars1:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.2f}',
                    ha='center', va='bottom')
        
        for bar in bars2:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.2f}',
                    ha='center', va='bottom')
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        if show:
            plt.show()
        else:
            plt.close()

class MetaPopulationPlotter:
    def __init__(self, simulation: MetaPopulationSimulation):
        self.simulation = simulation
    
    def _get_ylim(self, all_frequencies: List[float], auto_scale: bool = False) -> tuple:
        if auto_scale:
            min_freq = min(all_frequencies)
            max_freq = max(all_frequencies)
            range_freq = max_freq - min_freq
            
            if range_freq == 0:
                margin = 0.1
            else:
                margin = max(0.05, range_freq * 0.1)
            
            y_min = max(0.0, min_freq - margin)
            y_max = min(1.0, max_freq + margin)
            return (y_min, y_max)
        else:
            return (0.0, 1.05)
    
    def plot_population_frequency(self, allele_name: str, population_idx: int,
                                   save_path: Optional[str] = None, show: bool = True,
                                   alpha: float = 0.3, auto_ylim: bool = False):
        if not self.simulation.get_results():
            raise RuntimeError("Simulation has not been run yet. Call run() first.")
        
        history = self.simulation.get_allele_frequency_history(allele_name, population_idx)
        num_generations = len(history[0])
        generations = list(range(num_generations))
        
        plt.figure(figsize=(10, 6))
        
        all_frequencies = []
        for run_history in history:
            all_frequencies.extend(run_history)
            plt.plot(generations, run_history, alpha=alpha, linewidth=1.5)
        
        avg_freq = self.simulation.get_average_frequency(allele_name, population_idx)
        all_frequencies.extend(avg_freq)
        plt.plot(generations, avg_freq, color='red', linewidth=2, label='Average')
        
        plt.xlabel('Generation')
        plt.ylabel(f'Frequency of Allele {allele_name}')
        plt.title(f'Population {population_idx + 1} - {self.simulation.runs} Simulations')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.ylim(self._get_ylim(all_frequencies, auto_ylim))
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        if show:
            plt.show()
        else:
            plt.close()
    
    def plot_all_populations(self, allele_name: str,
                              save_path: Optional[str] = None, show: bool = True,
                              auto_ylim: bool = False):
        if not self.simulation.get_results():
            raise RuntimeError("Simulation has not been run yet. Call run() first.")
        
        num_pops = self.simulation.meta_population.num_populations
        colors = plt.cm.tab10(np.linspace(0, 1, max(1, num_pops)))
        
        plt.figure(figsize=(12, 7))
        
        all_frequencies = []
        for pop_idx in range(num_pops):
            avg_freq = self.simulation.get_average_frequency(allele_name, pop_idx)
            generations = list(range(len(avg_freq)))
            all_frequencies.extend(avg_freq)
            plt.plot(generations, avg_freq, color=colors[pop_idx], 
                    linewidth=2.5, label=f'Population {pop_idx + 1}')
        
        plt.xlabel('Generation')
        plt.ylabel(f'Average Frequency of Allele {allele_name}')
        plt.title(f'Allele Frequency Across {num_pops} Populations ({self.simulation.runs} runs each)')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.ylim(self._get_ylim(all_frequencies, auto_ylim))
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        if show:
            plt.show()
        else:
            plt.close()
    
    def plot_population_sizes(self, save_path: Optional[str] = None, show: bool = True,
                               alpha: float = 0.3, auto_ylim: bool = True):
        if not self.simulation.get_results():
            raise RuntimeError("Simulation has not been run yet. Call run() first.")
        
        num_pops = self.simulation.meta_population.num_populations
        colors = plt.cm.tab10(np.linspace(0, 1, max(1, num_pops)))
        pop_history = self.simulation.get_population_size_history()
        
        plt.figure(figsize=(12, 7))
        
        all_sizes = []
        for pop_idx in range(num_pops):
            avg_sizes = []
            for gen in range(len(pop_history[0])):
                total = sum(run[gen][pop_idx] for run in pop_history)
                avg_sizes.append(total / len(pop_history))
            
            generations = list(range(len(avg_sizes)))
            all_sizes.extend(avg_sizes)
            plt.plot(generations, avg_sizes, color=colors[pop_idx], 
                    linewidth=2.5, label=f'Population {pop_idx + 1}')
            
            for run in pop_history:
                pop_sizes = [gen[pop_idx] for gen in run]
                all_sizes.extend(pop_sizes)
                plt.plot(generations, pop_sizes, color=colors[pop_idx], 
                        alpha=alpha, linewidth=0.8)
        
        plt.xlabel('Generation')
        plt.ylabel('Population Size (N)')
        plt.title(f'Population Sizes Over Time')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        if auto_ylim:
            min_size = min(all_sizes)
            max_size = max(all_sizes)
            margin = max(1, int((max_size - min_size) * 0.1)) if max_size > min_size else 1
            plt.ylim(max(0, min_size - margin), max_size + margin)
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        if show:
            plt.show()
        else:
            plt.close()
    
    def plot_fst(self, save_path: Optional[str] = None, show: bool = True,
                  alpha: float = 0.3, auto_ylim: bool = False):
        if not self.simulation.get_results():
            raise RuntimeError("Simulation has not been run yet. Call run() first.")
        
        fst_history = self.simulation.get_fst_history()
        num_generations = len(fst_history[0])
        generations = list(range(num_generations))
        
        plt.figure(figsize=(10, 6))
        
        all_fst = []
        for run_fst in fst_history:
            all_fst.extend(run_fst)
            plt.plot(generations, run_fst, alpha=alpha, linewidth=1.5)
        
        avg_fst = [sum(gen) / len(fst_history) for gen in zip(*fst_history)]
        all_fst.extend(avg_fst)
        plt.plot(generations, avg_fst, color='red', linewidth=2, label='Average Fst')
        
        plt.xlabel('Generation')
        plt.ylabel('Fst')
        plt.title(f'Population Differentiation (Fst) Over Time')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        if auto_ylim:
            min_fst = min(all_fst)
            max_fst = max(all_fst)
            range_fst = max_fst - min_fst
            margin = max(0.02, range_fst * 0.1) if range_fst > 0 else 0.02
            plt.ylim(max(0.0, min_fst - margin), min(1.0, max_fst + margin))
        else:
            plt.ylim(0.0, 1.05)
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        if show:
            plt.show()
        else:
            plt.close()
    
    def plot_statistics_comparison(self, allele_name: str,
                                    save_path: Optional[str] = None, show: bool = True):
        if not self.simulation.get_results():
            raise RuntimeError("Simulation has not been run yet. Call run() first.")
        
        num_pops = self.simulation.meta_population.num_populations
        
        fix_probs = []
        loss_probs = []
        pop_labels = []
        
        for pop_idx in range(num_pops):
            fix_count = 0
            loss_count = 0
            for run in self.simulation.get_results():
                for gen in reversed(range(len(run))):
                    freq = run[gen][pop_idx].get(allele_name, 0.0)
                    if freq == 1.0:
                        fix_count += 1
                        break
                    elif freq == 0.0:
                        loss_count += 1
                        break
                    elif 0.0 < freq < 1.0:
                        break
            
            fix_probs.append(fix_count / self.simulation.runs)
            loss_probs.append(loss_count / self.simulation.runs)
            pop_labels.append(f'Pop {pop_idx + 1}')
        
        x = np.arange(num_pops)
        width = 0.35
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        bars1 = ax.bar(x - width/2, fix_probs, width, 
                       label='Fixation Probability', color='green', alpha=0.7)
        bars2 = ax.bar(x + width/2, loss_probs, width, 
                       label='Loss Probability', color='red', alpha=0.7)
        
        ax.set_xlabel('Population')
        ax.set_ylabel('Probability')
        ax.set_title(f'Fixation/Loss Probability by Population (Allele {allele_name})')
        ax.set_xticks(x)
        ax.set_xticklabels(pop_labels)
        ax.legend()
        ax.grid(True, alpha=0.3, axis='y')
        
        max_val = max(max(fix_probs), max(loss_probs), 0.1)
        ax.set_ylim(0, max_val * 1.1)
        
        for bar in bars1:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.2f}', ha='center', va='bottom')
        
        for bar in bars2:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.2f}', ha='center', va='bottom')
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        if show:
            plt.show()
        else:
            plt.close()
