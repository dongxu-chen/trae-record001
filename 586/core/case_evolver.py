import random
import re
import string
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field


@dataclass
class EvolvedTestCase:
    original_id: str
    evolved_id: str
    original_value: Any
    evolved_value: Any
    mutation_type: str
    generation: int
    parent_ids: List[str] = field(default_factory=list)
    fitness_score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'original_id': self.original_id,
            'evolved_id': self.evolved_id,
            'original_value': self.original_value,
            'evolved_value': self.evolved_value,
            'mutation_type': self.mutation_type,
            'generation': self.generation,
            'parent_ids': self.parent_ids,
            'fitness_score': self.fitness_score
        }


class TestCaseMutator:
    def __init__(self, seed: Optional[int] = None):
        if seed is not None:
            random.seed(seed)
        
        self.mutation_strategies = {
            'string': [
                self._mutate_string_insert,
                self._mutate_string_delete,
                self._mutate_string_replace,
                self._mutate_string_case,
                self._mutate_string_repeat,
                self._mutate_string_special
            ],
            'integer': [
                self._mutate_int_increment,
                self._mutate_int_decrement,
                self._mutate_int_multiply,
                self._mutate_int_boundary,
                self._mutate_int_random
            ],
            'number': [
                self._mutate_float_increment,
                self._mutate_float_multiply,
                self._mutate_float_precision,
                self._mutate_float_boundary
            ],
            'boolean': [
                self._mutate_bool_flip,
                self._mutate_bool_to_string
            ]
        }
    
    def mutate(self, value: Any, param_type: str = 'string') -> List[Dict[str, Any]]:
        mutations = []
        strategies = self.mutation_strategies.get(param_type, self.mutation_strategies['string'])
        
        for strategy in strategies:
            try:
                result = strategy(value)
                if result is not None and result != value:
                    mutations.append({
                        'value': result,
                        'type': strategy.__name__.replace('_mutate_', '')
                    })
            except Exception:
                continue
        
        return mutations
    
    def _mutate_string_insert(self, value: str) -> str:
        if not isinstance(value, str):
            value = str(value)
        if len(value) == 0:
            return 'X'
        pos = random.randint(0, len(value))
        char = random.choice(string.printable)
        return value[:pos] + char + value[pos:]
    
    def _mutate_string_delete(self, value: str) -> str:
        if not isinstance(value, str):
            value = str(value)
        if len(value) <= 1:
            return value
        pos = random.randint(0, len(value) - 1)
        return value[:pos] + value[pos + 1:]
    
    def _mutate_string_replace(self, value: str) -> str:
        if not isinstance(value, str):
            value = str(value)
        if len(value) == 0:
            return 'X'
        pos = random.randint(0, len(value) - 1)
        char = random.choice(string.printable)
        return value[:pos] + char + value[pos + 1:]
    
    def _mutate_string_case(self, value: str) -> str:
        if not isinstance(value, str):
            value = str(value)
        if random.random() > 0.5:
            return value.upper()
        return value.lower()
    
    def _mutate_string_repeat(self, value: str) -> str:
        if not isinstance(value, str):
            value = str(value)
        repeat_times = random.randint(2, 5)
        return value * repeat_times
    
    def _mutate_string_special(self, value: str) -> str:
        if not isinstance(value, str):
            value = str(value)
        special_chars = ['\x00', '\n', '\r', '\t', '\b', '\f', '\\', '"', "'", ';', '--', '#', '%00']
        if random.random() > 0.5:
            return value + random.choice(special_chars)
        return random.choice(special_chars) + value
    
    def _mutate_int_increment(self, value: Any) -> int:
        try:
            return int(value) + 1
        except (TypeError, ValueError):
            return 1
    
    def _mutate_int_decrement(self, value: Any) -> int:
        try:
            return int(value) - 1
        except (TypeError, ValueError):
            return -1
    
    def _mutate_int_multiply(self, value: Any) -> int:
        try:
            return int(value) * 2
        except (TypeError, ValueError):
            return 0
    
    def _mutate_int_boundary(self, value: Any) -> int:
        boundaries = [0, 1, -1, 2147483647, 2147483648, -2147483648]
        return random.choice(boundaries)
    
    def _mutate_int_random(self, value: Any) -> int:
        return random.randint(-1000000, 1000000)
    
    def _mutate_float_increment(self, value: Any) -> float:
        try:
            return float(value) + 0.1
        except (TypeError, ValueError):
            return 0.1
    
    def _mutate_float_multiply(self, value: Any) -> float:
        try:
            return float(value) * 10.0
        except (TypeError, ValueError):
            return 0.0
    
    def _mutate_float_precision(self, value: Any) -> float:
        try:
            return float(f"{float(value):.20f}")
        except (TypeError, ValueError):
            return 0.0000000001
    
    def _mutate_float_boundary(self, value: Any) -> float:
        boundaries = [0.0, float('inf'), float('-inf'), float('nan'), 1e308, -1e308]
        return random.choice(boundaries)
    
    def _mutate_bool_flip(self, value: Any) -> bool:
        return not bool(value)
    
    def _mutate_bool_to_string(self, value: Any) -> str:
        return str(not bool(value)).lower()


class CaseEvolver:
    def __init__(self, max_generations: int = 3, max_mutations_per_case: int = 5):
        self.max_generations = max_generations
        self.max_mutations_per_case = max_mutations_per_case
        self.mutator = TestCaseMutator()
        self.evolution_history: Dict[str, List[EvolvedTestCase]] = {}
        self.fitness_cache: Dict[str, float] = {}
    
    def evolve_failed_cases(
        self,
        failed_cases: List[Dict[str, Any]],
        generation: int = 1
    ) -> List[Dict[str, Any]]:
        if generation > self.max_generations:
            return []
        
        evolved_cases = []
        
        for failed_case in failed_cases:
            case_id = failed_case.get('test_id', f"case_{len(evolved_cases)}")
            tested_param = failed_case.get('tested_param', 'param')
            original_value = failed_case.get('test_value', '')
            param_type = self._detect_param_type(original_value)
            anomalies = failed_case.get('anomalies', [])
            
            fitness_score = self._calculate_fitness(anomalies)
            self.fitness_cache[case_id] = fitness_score
            
            if fitness_score >= 0.3:
                mutations = self.mutator.mutate(original_value, param_type)
                mutations = mutations[:self.max_mutations_per_case]
                
                for idx, mutation in enumerate(mutations):
                    evolved_id = f"{case_id}_g{generation}_m{idx}"
                    evolved_case = EvolvedTestCase(
                        original_id=case_id,
                        evolved_id=evolved_id,
                        original_value=original_value,
                        evolved_value=mutation['value'],
                        mutation_type=mutation['type'],
                        generation=generation,
                        parent_ids=[case_id],
                        fitness_score=fitness_score
                    )
                    
                    if case_id not in self.evolution_history:
                        self.evolution_history[case_id] = []
                    self.evolution_history[case_id].append(evolved_case)
                    
                    evolved_cases.append({
                        'evolved_id': evolved_id,
                        'tested_param': tested_param,
                        'test_value': mutation['value'],
                        'mutation_type': mutation['type'],
                        'value_type': f"evolved_{mutation['type']}",
                        'description': f"Evolved from {case_id} (gen {generation}): {mutation['type']}",
                        'original_case': failed_case,
                        'evolution': evolved_case.to_dict()
                    })
        
        return evolved_cases
    
    def _detect_param_type(self, value: Any) -> str:
        if isinstance(value, bool):
            return 'boolean'
        if isinstance(value, int):
            return 'integer'
        if isinstance(value, float):
            return 'number'
        if isinstance(value, str):
            return 'string'
        return 'string'
    
    def _calculate_fitness(self, anomalies: List[Dict[str, Any]]) -> float:
        if not anomalies:
            return 0.0
        
        score = 0.0
        severity_weights = {'high': 1.0, 'medium': 0.5, 'low': 0.2}
        
        for anomaly in anomalies:
            severity = anomaly.get('severity', 'low')
            score += severity_weights.get(severity, 0.1)
        
        return min(1.0, score / len(anomalies))
    
    def get_evolution_chain(self, case_id: str) -> List[Dict[str, Any]]:
        chain = []
        if case_id in self.evolution_history:
            for evolved in self.evolution_history[case_id]:
                chain.append(evolved.to_dict())
        return chain
    
    def get_evolution_summary(self) -> Dict[str, Any]:
        total_evolved = sum(len(cases) for cases in self.evolution_history.values())
        generations_used = set()
        mutation_types = {}
        
        for cases in self.evolution_history.values():
            for case in cases:
                generations_used.add(case.generation)
                mutation_types[case.mutation_type] = mutation_types.get(case.mutation_type, 0) + 1
        
        return {
            'total_original_cases': len(self.evolution_history),
            'total_evolved_cases': total_evolved,
            'generations_used': sorted(list(generations_used)),
            'mutation_type_distribution': mutation_types,
            'high_fitness_cases': [
                case_id for case_id, score in self.fitness_cache.items()
                if score >= 0.7
            ]
        }
    
    def clear(self) -> None:
        self.evolution_history.clear()
        self.fitness_cache.clear()


class EvolutionEngine:
    def __init__(self, max_generations: int = 3, max_mutations_per_case: int = 5):
        self.case_evolver = CaseEvolver(max_generations, max_mutations_per_case)
        self.current_generation = 0
    
    def run_evolution_cycle(
        self,
        failed_cases: List[Dict[str, Any]],
        run_test_func: Callable[[Dict[str, Any]], Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        all_results = []
        
        for generation in range(1, self.case_evolver.max_generations + 1):
            self.current_generation = generation
            
            evolved_cases = self.case_evolver.evolve_failed_cases(
                failed_cases,
                generation
            )
            
            if not evolved_cases:
                break
            
            generation_results = []
            new_failed_cases = []
            
            for evolved_case in evolved_cases:
                result = run_test_func(evolved_case)
                generation_results.append(result)
                
                if result.get('anomalies'):
                    new_failed_cases.append({
                        'test_id': evolved_case['evolved_id'],
                        'tested_param': evolved_case['tested_param'],
                        'test_value': evolved_case['test_value'],
                        'anomalies': result['anomalies']
                    })
            
            all_results.extend(generation_results)
            failed_cases = new_failed_cases
            
            if not failed_cases:
                break
        
        return all_results
    
    def get_summary(self) -> Dict[str, Any]:
        return {
            'max_generations': self.case_evolver.max_generations,
            'max_mutations_per_case': self.case_evolver.max_mutations_per_case,
            'generations_executed': self.current_generation,
            **self.case_evolver.get_evolution_summary()
        }
