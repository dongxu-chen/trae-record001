import os
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class CacheConfig:
    enable_cache: bool = True
    cache_dir: str = field(default_factory=lambda: os.path.join(os.getcwd(), "cache"))
    msa_cache_dir: str = field(default_factory=lambda: os.path.join(os.getcwd(), "cache", "msa"))
    max_cache_size_gb: float = 10.0
    cache_ttl_days: int = 30
    use_sequence_hash: bool = True


@dataclass
class GPUConfig:
    preallocate_memory: bool = True
    memory_fraction: float = 0.8
    dynamic_batch: bool = True
    max_batch_size: int = 8
    min_batch_size: int = 1
    auto_batch_tuning: bool = True
    enable_tensor_core: bool = True
    cudnn_benchmark: bool = True


@dataclass
class ChunkConfig:
    enable_chunking: bool = True
    chunk_size: int = 512
    chunk_overlap: int = 64
    max_chunked_seq_len: int = 4096
    merge_strategy: str = "weighted_average"
    num_chunks: Optional[int] = None


@dataclass
class ModelConfig:
    model_dir: str = field(default_factory=lambda: os.path.join(os.getcwd(), "models"))
    use_gpu: bool = True
    gpu_device: int = 0
    precision: str = "fp16"
    max_seq_len: int = 2000
    num_recycles: int = 3
    num_models: int = 5


@dataclass
class MSAConfig:
    use_bfd: bool = False
    use_small_bfd: bool = True
    use_uniref90: bool = True
    use_uniprot: bool = False
    msa_mode: str = "MMseqs2"
    max_msa_seqs: int = 512
    min_msa_seqs: int = 8
    e_value: float = 0.001
    max_hits: int = 10000


@dataclass
class PredictionConfig:
    output_dir: str = field(default_factory=lambda: os.path.join(os.getcwd(), "output"))
    save_pdb: bool = True
    save_msa: bool = False
    save_features: bool = False
    relax_structure: bool = True
    use_amber: bool = False
    num_relax_iterations: int = 200
    show_residue_plddt: bool = True
    verbose_plddt: bool = True


@dataclass
class APIConfig:
    host: str = "0.0.0.0"
    port: int = 8000
    max_requests: int = 10
    timeout: int = 600
    enable_cors: bool = True


class Config:
    def __init__(self):
        self.model = ModelConfig()
        self.msa = MSAConfig()
        self.cache = CacheConfig()
        self.gpu = GPUConfig()
        self.chunk = ChunkConfig()
        self.prediction = PredictionConfig()
        self.api = APIConfig()
        self._create_dirs()

    def _create_dirs(self):
        os.makedirs(self.model.model_dir, exist_ok=True)
        os.makedirs(self.prediction.output_dir, exist_ok=True)
        if self.cache.enable_cache:
            os.makedirs(self.cache.cache_dir, exist_ok=True)
            os.makedirs(self.cache.msa_cache_dir, exist_ok=True)

    def to_dict(self) -> dict:
        return {
            "model": self.model.__dict__,
            "msa": self.msa.__dict__,
            "cache": self.cache.__dict__,
            "gpu": self.gpu.__dict__,
            "chunk": self.chunk.__dict__,
            "prediction": self.prediction.__dict__,
            "api": self.api.__dict__,
        }
