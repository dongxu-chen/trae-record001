import hashlib
import json
import time
from typing import Dict, Any, Optional, Callable, Tuple
from dataclasses import dataclass, field
from threading import Lock


@dataclass
class CacheEntry:
    data: Any
    timestamp: float
    ttl: float = 3600
    hit_count: int = 0


class CacheManager:
    _instance = None
    _lock = Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = Lock()
        self._stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0
        }
    
    def _generate_key(self, prefix: str, graph_hash: str, **params) -> str:
        sorted_params = json.dumps(params, sort_keys=True)
        raw_key = f"{prefix}:{graph_hash}:{sorted_params}"
        return hashlib.md5(raw_key.encode()).hexdigest()
    
    def _compute_graph_hash(self, nodes: list, edges: list) -> str:
        sorted_nodes = sorted(nodes)
        sorted_edges = sorted(
            (min(e[0], e[1]), max(e[0], e[1]), e[2]) for e in edges
        )
        raw = json.dumps([sorted_nodes, sorted_edges], sort_keys=True)
        return hashlib.md5(raw.encode()).hexdigest()
    
    def get(self, key: str) -> Tuple[Optional[Any], bool]:
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                self._stats['misses'] += 1
                return None, False
            
            if time.time() - entry.timestamp > entry.ttl:
                del self._cache[key]
                self._stats['evictions'] += 1
                self._stats['misses'] += 1
                return None, False
            
            entry.hit_count += 1
            self._stats['hits'] += 1
            return entry.data, True
    
    def set(self, key: str, data: Any, ttl: float = 3600) -> None:
        with self._lock:
            self._cache[key] = CacheEntry(
                data=data,
                timestamp=time.time(),
                ttl=ttl,
                hit_count=0
            )
    
    def get_or_compute(self, key: str, compute_func: Callable, 
                       ttl: float = 3600, **kwargs) -> Tuple[Any, bool]:
        data, hit = self.get(key)
        if hit:
            return data, True
        
        data = compute_func(**kwargs)
        self.set(key, data, ttl)
        return data, False
    
    def invalidate(self, key: str) -> bool:
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    def invalidate_prefix(self, prefix: str) -> int:
        with self._lock:
            keys_to_remove = [k for k in self._cache.keys() if k.startswith(prefix)]
            for k in keys_to_remove:
                del self._cache[k]
                self._stats['evictions'] += 1
            return len(keys_to_remove)
    
    def clear(self) -> int:
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self._stats['evictions'] += count
            return count
    
    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            total_requests = self._stats['hits'] + self._stats['misses']
            hit_rate = self._stats['hits'] / total_requests if total_requests > 0 else 0
            
            cache_entries = []
            for key, entry in self._cache.items():
                cache_entries.append({
                    'key': key,
                    'size': len(json.dumps(entry.data).encode()),
                    'age': time.time() - entry.timestamp,
                    'ttl': entry.ttl,
                    'hit_count': entry.hit_count
                })
            
            return {
                'hits': self._stats['hits'],
                'misses': self._stats['misses'],
                'evictions': self._stats['evictions'],
                'hit_rate': hit_rate,
                'total_entries': len(self._cache),
                'total_size_bytes': sum(e['size'] for e in cache_entries),
                'entries': cache_entries
            }
    
    def get_temporal_key(self, graph_hash: str, time_windows: int, 
                        relationship_types: Optional[list] = None) -> str:
        return self._generate_key(
            'temporal', graph_hash, 
            time_windows=time_windows,
            relationship_types=sorted(relationship_types) if relationship_types else None
        )
    
    def get_community_key(self, graph_hash: str, 
                          relationship_types: Optional[list] = None) -> str:
        return self._generate_key(
            'community', graph_hash,
            relationship_types=sorted(relationship_types) if relationship_types else None
        )
    
    def get_influence_key(self, graph_hash: str, method: str,
                          relationship_types: Optional[list] = None) -> str:
        return self._generate_key(
            f'influence:{method}', graph_hash,
            relationship_types=sorted(relationship_types) if relationship_types else None
        )


_cache_manager = CacheManager()


def get_cache_manager() -> CacheManager:
    return _cache_manager
