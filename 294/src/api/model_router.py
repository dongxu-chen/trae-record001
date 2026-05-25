import os
import random
import hashlib
import threading
import config
from src.models.deepfm import load_model


class ModelVersion:
    def __init__(self, version, path, traffic_ratio=1.0, default=False):
        self.version = version
        self.path = path
        self.traffic_ratio = traffic_ratio
        self.default = default
        self.model = None
        self.processors = None
        self.cold_start_handler = None
        self.loaded = False
    
    def load(self):
        try:
            import pickle
            
            self.model = load_model(self.path)
            
            processor_path = os.path.join(self.path, 'processors.pkl')
            if os.path.exists(processor_path):
                with open(processor_path, 'rb') as f:
                    self.processors = pickle.load(f)
            
            cold_start_path = os.path.join(self.path, 'cold_start.pkl')
            if os.path.exists(cold_start_path):
                from src.data.cold_start import ColdStartHandler
                self.cold_start_handler = ColdStartHandler()
                self.cold_start_handler.load(cold_start_path)
            
            self.loaded = True
            print(f"Model version {self.version} loaded successfully")
            return True
        except Exception as e:
            print(f"Failed to load model version {self.version}: {e}")
            return False


class ModelRouter:
    def __init__(self):
        self.models = {}
        self.default_version = None
        self.routing_strategy = config.ROUTING_STRATEGY
        self.grayscale_enabled = config.GRAYSCALE_ENABLED
        self._lock = threading.Lock()
        self.request_count = {}
        self._load_models_from_config()
    
    def _load_models_from_config(self):
        for version, config_info in config.MODEL_VERSIONS.items():
            model_version = ModelVersion(
                version=version,
                path=config_info['path'],
                traffic_ratio=config_info.get('traffic_ratio', 0.0),
                default=config_info.get('default', False)
            )
            
            if os.path.exists(config_info['path']):
                model_version.load()
            
            self.models[version] = model_version
            self.request_count[version] = 0
            
            if model_version.default:
                self.default_version = version
        
        if not self.default_version and self.models:
            self.default_version = list(self.models.keys())[0]
        
        print(f"ModelRouter initialized with {len(self.models)} versions")
        print(f"Default version: {self.default_version}")
        for v, m in self.models.items():
            print(f"  {v}: ratio={m.traffic_ratio}, loaded={m.loaded}")
    
    def get_model_by_version(self, version):
        with self._lock:
            if version in self.models and self.models[version].loaded:
                self.request_count[version] += 1
                return self.models[version]
        return None
    
    def get_default_model(self):
        return self.get_model_by_version(self.default_version)
    
    def route_by_ratio(self, user_id=None):
        if not self.grayscale_enabled:
            return self.get_default_model()
        
        if user_id:
            hash_val = int(hashlib.md5(str(user_id).encode()).hexdigest(), 16) % 100 / 100.0
        else:
            hash_val = random.random()
        
        cumulative_ratio = 0.0
        sorted_versions = sorted(
            self.models.items(),
            key=lambda x: (not x[1].default, -x[1].traffic_ratio)
        )
        
        for version, model_version in sorted_versions:
            if not model_version.loaded:
                continue
            
            cumulative_ratio += model_version.traffic_ratio
            if hash_val < cumulative_ratio:
                return self.get_model_by_version(version)
        
        return self.get_default_model()
    
    def route_by_user_hash(self, user_id, versions=None):
        if not versions:
            versions = list(self.models.keys())
        
        hash_val = int(hashlib.md5(str(user_id).encode()).hexdigest(), 16)
        selected_idx = hash_val % len(versions)
        return self.get_model_by_version(versions[selected_idx])
    
    def route(self, user_id=None, requested_version=None):
        if requested_version:
            return self.get_model_by_version(requested_version)
        
        if self.routing_strategy == 'ratio':
            return self.route_by_ratio(user_id)
        elif self.routing_strategy == 'user_hash':
            return self.route_by_user_hash(user_id)
        else:
            return self.get_default_model()
    
    def update_traffic_ratio(self, version, new_ratio):
        with self._lock:
            if version in self.models:
                self.models[version].traffic_ratio = new_ratio
                print(f"Updated {version} traffic ratio to {new_ratio}")
                return True
        return False
    
    def add_model_version(self, version, path, traffic_ratio=0.0, default=False, load_now=True):
        with self._lock:
            model_version = ModelVersion(version, path, traffic_ratio, default)
            
            if load_now:
                model_version.load()
            
            self.models[version] = model_version
            self.request_count[version] = 0
            
            if default:
                self.default_version = version
            
            print(f"Added model version: {version}")
            return model_version
    
    def get_routing_stats(self):
        total_requests = sum(self.request_count.values())
        stats = {
            'total_requests': total_requests,
            'default_version': self.default_version,
            'routing_strategy': self.routing_strategy,
            'versions': {}
        }
        
        for version, count in self.request_count.items():
            model_version = self.models[version]
            stats['versions'][version] = {
                'requests': count,
                'traffic_ratio_configured': model_version.traffic_ratio,
                'traffic_ratio_actual': count / total_requests if total_requests > 0 else 0,
                'loaded': model_version.loaded,
                'default': model_version.default
            }
        
        return stats
    
    def reset_stats(self):
        with self._lock:
            for version in self.request_count:
                self.request_count[version] = 0


_global_router = None


def get_model_router():
    global _global_router
    if _global_router is None:
        _global_router = ModelRouter()
    return _global_router
