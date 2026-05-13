from typing import Dict, List, Optional, Callable
import math

class Fitness:
    def __init__(self, values: Dict[str, float]):
        if not values:
            raise ValueError("At least one allele fitness value is required")
        
        for allele, w in values.items():
            if w < 0.0:
                raise ValueError(f"Fitness value for {allele} cannot be negative")
        
        self._values = dict(values)
        self._alleles = list(values.keys())
    
    @property
    def alleles(self) -> List[str]:
        return self._alleles.copy()
    
    def get_fitness(self, allele: str) -> float:
        if allele not in self._values:
            raise KeyError(f"Fitness not defined for allele '{allele}'")
        return self._values[allele]
    
    def set_fitness(self, allele: str, fitness: float):
        if fitness < 0.0:
            raise ValueError("Fitness value cannot be negative")
        self._values[allele] = fitness
        if allele not in self._alleles:
            self._alleles.append(allele)
    
    def get_normalized_fitnesses(self, frequencies: Dict[str, float]) -> Dict[str, float]:
        all_alleles = set(self._alleles) | set(frequencies.keys())
        
        weighted_sum = 0.0
        for allele in all_alleles:
            if allele in frequencies:
                freq = frequencies[allele]
            else:
                continue
            
            if allele in self._values:
                w = self._values[allele]
            else:
                w = 1.0
            weighted_sum += freq * w
        
        if weighted_sum <= 0.0:
            return {allele: 0.0 for allele in frequencies.keys()}
        
        result = {}
        for allele, freq in frequencies.items():
            if allele in self._values:
                w = self._values[allele]
            else:
                w = 1.0
            result[allele] = (w * freq) / weighted_sum
        
        return result
    
    def get_selection_coefficient(self, allele: str) -> float:
        if allele not in self._values:
            raise KeyError(f"Allele '{allele}' not found in fitness values")
        
        max_fitness = max(self._values.values())
        return 1.0 - (self._values[allele] / max_fitness) if max_fitness > 0 else 0.0
    
    def get_relative_fitness(self, allele: str) -> float:
        if allele not in self._values:
            raise KeyError(f"Allele '{allele}' not found in fitness values")
        
        max_fitness = max(self._values.values())
        return self._values[allele] / max_fitness if max_fitness > 0 else 0.0
    
    def __repr__(self) -> str:
        fitness_info = ", ".join([f"{a}={w:.4f}" for a, w in self._values.items()])
        return f"Fitness({fitness_info})"

class SelectionModel:
    def __init__(self, fitness: Optional[Fitness] = None, 
                 selection_strength: float = 0.0,
                 dominance: str = 'additive'):
        if not (0.0 <= selection_strength <= 1.0):
            raise ValueError("Selection strength must be between 0.0 and 1.0")
        if dominance not in ['additive', 'dominant', 'recessive', 'heterozygote_advantage']:
            raise ValueError("Dominance must be one of: 'additive', 'dominant', 'recessive', 'heterozygote_advantage'")
        
        self._fitness = fitness
        self._selection_strength = selection_strength
        self._dominance = dominance
    
    @property
    def fitness(self) -> Optional[Fitness]:
        return self._fitness
    
    @fitness.setter
    def fitness(self, value: Optional[Fitness]):
        self._fitness = value
    
    @property
    def selection_strength(self) -> float:
        return self._selection_strength
    
    @selection_strength.setter
    def selection_strength(self, value: float):
        if not (0.0 <= value <= 1.0):
            raise ValueError("Selection strength must be between 0.0 and 1.0")
        self._selection_strength = value
    
    @property
    def dominance(self) -> str:
        return self._dominance
    
    @dominance.setter
    def dominance(self, value: str):
        if value not in ['additive', 'dominant', 'recessive', 'heterozygote_advantage']:
            raise ValueError("Dominance must be one of: 'additive', 'dominant', 'recessive', 'heterozygote_advantage'")
        self._dominance = value
    
    def apply_selection(self, frequencies: Dict[str, float]) -> Dict[str, float]:
        if self._fitness is None and self._selection_strength <= 0.0:
            return frequencies.copy()
        
        if self._fitness is not None:
            return self._fitness.get_normalized_fitnesses(frequencies)
        
        if len(frequencies) < 2:
            return frequencies.copy()
        
        alleles = sorted(frequencies.keys())
        selected_allele = alleles[0]
        other_alleles = alleles[1:]
        
        s = self._selection_strength
        
        if self._dominance == 'additive':
            h = 0.5
        elif self._dominance == 'dominant':
            h = 1.0
        elif self._dominance == 'recessive':
            h = 0.0
        else:
            h = 0.5
        
        w_selected = 1.0 + s
        w_hetero = 1.0 + h * s
        w_other = 1.0
        
        p = frequencies[selected_allele]
        q = sum(frequencies[a] for a in other_alleles)
        
        if q <= 0:
            return frequencies.copy()
        
        w_bar = p * w_selected + q * w_other
        
        next_p = (p * w_selected) / w_bar if w_bar > 0 else p
        remaining = 1.0 - next_p
        
        result = {selected_allele: next_p}
        if other_alleles:
            share = remaining / len(other_alleles) if remaining > 0 else 0
            for allele in other_alleles:
                result[allele] = share
        
        return result
    
    def calculate_selection_response(self, allele_freq: float) -> float:
        if self._fitness is None:
            return 0.0
        
        w_allele = self._fitness.get_fitness(list(self._fitness.alleles)[0])
        w_avg = sum(self._fitness.get_fitness(a) for a in self._fitness.alleles) / len(self._fitness.alleles)
        
        if w_avg <= 0:
            return 0.0
        
        return allele_freq * (w_allele - w_avg) / w_avg
    
    def __repr__(self) -> str:
        if self._fitness is not None:
            return f"SelectionModel(fitness={self._fitness})"
        return f"SelectionModel(s={self._selection_strength:.4f}, dominance='{self._dominance}')"

def create_fitness_from_selection(alleles: List[str], 
                                 selected_allele: str,
                                 selection_coefficient: float,
                                 dominance: float = 0.5) -> Fitness:
    if not (0.0 <= selection_coefficient <= 1.0):
        raise ValueError("Selection coefficient must be between 0.0 and 1.0")
    
    if selected_allele not in alleles:
        raise ValueError(f"Selected allele '{selected_allele}' not in alleles list")
    
    fitness_values = {}
    w_selected = 1.0
    w_other = 1.0 - selection_coefficient
    
    for allele in alleles:
        if allele == selected_allele:
            fitness_values[allele] = w_selected
        else:
            fitness_values[allele] = w_other
    
    return Fitness(fitness_values)

def create_frequency_dependent_fitness(base_fitness: Fitness, 
                                      frequency_coefficient: float,
                                      positive: bool = True) -> Callable[[Dict[str, float]], Fitness]:
    def fitness_function(frequencies: Dict[str, float]) -> Fitness:
        values = {}
        for allele in base_fitness.alleles:
            w_base = base_fitness.get_fitness(allele)
            freq = frequencies.get(allele, 0.0)
            if positive:
                w = w_base + frequency_coefficient * freq
            else:
                w = w_base + frequency_coefficient * (1.0 - freq)
            values[allele] = max(0.0, w)
        return Fitness(values)
    
    return fitness_function
