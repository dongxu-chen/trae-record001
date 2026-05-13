import random
import math
from typing import Dict, Optional, List

class Population:
    def __init__(self, size: int, min_size: int = 1, max_size: int = None, 
                 growth_rate: float = 0.0, carry_capacity: int = None,
                 migration_rate: float = 0.0, population_id: int = 0):
        if size <= 0:
            raise ValueError("Population size must be a positive integer")
        if min_size <= 0:
            raise ValueError("Minimum population size must be a positive integer")
        if max_size is not None and max_size < min_size:
            raise ValueError("Maximum size cannot be less than minimum size")
        if not (0.0 <= migration_rate <= 1.0):
            raise ValueError("Migration rate must be between 0.0 and 1.0")
        
        self._size = size
        self._min_size = min_size
        self._max_size = max_size if max_size is not None else size * 10
        self._growth_rate = max(0.0, growth_rate)
        self._carry_capacity = carry_capacity if carry_capacity is not None else self._max_size
        self._initial_size = size
        self._migration_rate = migration_rate
        self._population_id = population_id
    
    @property
    def size(self) -> int:
        return self._size
    
    @size.setter
    def size(self, value: int):
        if value <= 0:
            raise ValueError("Population size must be a positive integer")
        self._size = value
    
    @property
    def min_size(self) -> int:
        return self._min_size
    
    @property
    def max_size(self) -> int:
        return self._max_size
    
    @property
    def growth_rate(self) -> float:
        return self._growth_rate
    
    @property
    def carry_capacity(self) -> int:
        return self._carry_capacity
    
    @property
    def migration_rate(self) -> float:
        return self._migration_rate
    
    @migration_rate.setter
    def migration_rate(self, value: float):
        if not (0.0 <= value <= 1.0):
            raise ValueError("Migration rate must be between 0.0 and 1.0")
        self._migration_rate = value
    
    @property
    def population_id(self) -> int:
        return self._population_id
    
    def reproduce(self, model: str = 'constant') -> int:
        if model == 'constant':
            return self._size
        elif model == 'poisson':
            expected_offspring = self._size * (1 + self._growth_rate)
            next_size = int(random.gauss(expected_offspring, math.sqrt(expected_offspring)))
            next_size = max(self._min_size, min(self._max_size, next_size))
            return next_size
        elif model == 'logistic':
            r = self._growth_rate
            K = self._carry_capacity
            N = self._size
            expected_next = N + r * N * (1 - N / K)
            noise = random.gauss(0, math.sqrt(max(1, N * 0.1)))
            next_size = int(expected_next + noise)
            next_size = max(self._min_size, min(self._max_size, next_size))
            return next_size
        elif model == 'random_walk':
            step = random.randint(-max(1, int(self._size * 0.1)), max(1, int(self._size * 0.1)))
            next_size = self._size + step
            next_size = max(self._min_size, min(self._max_size, next_size))
            return next_size
        else:
            raise ValueError(f"Unknown reproduction model: {model}")
    
    def __repr__(self) -> str:
        return f"Population(id={self._population_id}, size={self._size}, min={self._min_size}, max={self._max_size}, m={self._migration_rate:.4f})"

class MetaPopulation:
    def __init__(self, populations: List[Population], migration_matrix: Optional[List[List[float]]] = None):
        if len(populations) < 1:
            raise ValueError("At least one population is required")
        
        self._populations = populations
        self._num_populations = len(populations)
        
        if migration_matrix is None:
            migration_matrix = [[0.0] * self._num_populations for _ in range(self._num_populations)]
        
        if len(migration_matrix) != self._num_populations:
            raise ValueError(f"Migration matrix must have {self._num_populations} rows")
        for row in migration_matrix:
            if len(row) != self._num_populations:
                raise ValueError(f"Each migration matrix row must have {self._num_populations} columns")
            for rate in row:
                if not (0.0 <= rate <= 1.0):
                    raise ValueError("All migration rates must be between 0.0 and 1.0")
        
        self._migration_matrix = migration_matrix
    
    @property
    def num_populations(self) -> int:
        return self._num_populations
    
    @property
    def populations(self) -> List[Population]:
        return self._populations.copy()
    
    def get_population(self, idx: int) -> Population:
        return self._populations[idx]
    
    def get_migration_rate(self, from_idx: int, to_idx: int) -> float:
        return self._migration_matrix[from_idx][to_idx]
    
    def set_migration_rate(self, from_idx: int, to_idx: int, rate: float):
        if not (0.0 <= rate <= 1.0):
            raise ValueError("Migration rate must be between 0.0 and 1.0")
        self._migration_matrix[from_idx][to_idx] = rate
    
    def get_total_size(self) -> int:
        return sum(p.size for p in self._populations)
    
    def __repr__(self) -> str:
        pop_info = ", ".join([f"Pop{i}({p.size})" for i, p in enumerate(self._populations)])
        return f"MetaPopulation(num={self._num_populations}, {pop_info})"
