from typing import Dict, List
import random

class Allele:
    def __init__(self, name: str, initial_frequency: float):
        if not (0.0 <= initial_frequency <= 1.0):
            raise ValueError("Allele frequency must be between 0.0 and 1.0")
        self.name = name
        self._frequency = initial_frequency
    
    @property
    def frequency(self) -> float:
        return self._frequency
    
    @frequency.setter
    def frequency(self, value: float):
        if not (0.0 <= value <= 1.0):
            raise ValueError("Allele frequency must be between 0.0 and 1.0")
        self._frequency = value
    
    def __repr__(self) -> str:
        return f"Allele(name='{self.name}', frequency={self._frequency:.4f})"

class AllelePool:
    def __init__(self, alleles: Dict[str, float]):
        if not alleles:
            raise ValueError("At least one allele is required")
        
        total = sum(alleles.values())
        if not (0.999 <= total <= 1.001):
            raise ValueError(f"Allele frequencies must sum to 1.0 (current sum: {total})")
        
        self._alleles = {name: Allele(name, freq) for name, freq in alleles.items()}
    
    @property
    def alleles(self) -> Dict[str, Allele]:
        return self._alleles.copy()
    
    def get_frequency(self, allele_name: str) -> float:
        if allele_name not in self._alleles:
            raise KeyError(f"Allele '{allele_name}' not found")
        return self._alleles[allele_name].frequency
    
    def set_frequency(self, allele_name: str, frequency: float):
        if allele_name not in self._alleles:
            raise KeyError(f"Allele '{allele_name}' not found")
        self._alleles[allele_name].frequency = frequency
    
    def get_allele_names(self) -> List[str]:
        return list(self._alleles.keys())
    
    def sample_allele(self) -> str:
        alleles = list(self._alleles.keys())
        frequencies = [allele.frequency for allele in self._alleles.values()]
        return random.choices(alleles, weights=frequencies, k=1)[0]
    
    def __repr__(self) -> str:
        allele_info = ", ".join([f"{a.name}={a.frequency:.4f}" for a in self._alleles.values()])
        return f"AllelePool({allele_info})"
