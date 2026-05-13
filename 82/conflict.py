import os
from collections import defaultdict
from typing import Dict, List


class ConflictResolver:
    def __init__(self, strategy: str = 'suffix', start_count: int = 1):
        self.strategy = strategy
        self.start_count = start_count
        self._used_names: set = set()
        self._base_name_counters: Dict[str, int] = defaultdict(lambda: start_count)

    def register(self, file_path: str):
        self._used_names.add(os.path.basename(file_path).lower())

    def register_batch(self, file_paths: List[str]):
        for fp in file_paths:
            self.register(fp)

    def _exists(self, target_dir: str, filename: str) -> bool:
        if filename.lower() in self._used_names:
            return True
        return os.path.exists(os.path.join(target_dir, filename))

    def _get_counter(self, base_name_lower: str) -> int:
        counter = self._base_name_counters[base_name_lower]
        self._base_name_counters[base_name_lower] += 1
        return counter

    def resolve(self, target_dir: str, filename: str, extension: str) -> str:
        base_name = filename
        base_name_lower = base_name.lower()
        extension_lower = extension.lower()

        candidate = f"{base_name}{extension}"

        if not self._exists(target_dir, candidate):
            self._used_names.add(candidate.lower())
            return candidate

        while True:
            counter = self._get_counter(base_name_lower)
            if self.strategy == 'suffix':
                candidate = f"{base_name} ({counter}){extension}"
            elif self.strategy == 'prefix':
                candidate = f"{counter:02d}-{base_name}{extension}"
            else:
                raise ValueError(f"Unknown conflict strategy: {self.strategy}")

            if not self._exists(target_dir, candidate):
                self._used_names.add(candidate.lower())
                return candidate

    @staticmethod
    def get_strategies() -> list:
        return ['suffix', 'prefix']
