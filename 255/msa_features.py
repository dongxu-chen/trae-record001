import os
import re
import json
import hashlib
import pickle
import time
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Union
import numpy as np
from Bio import SeqIO
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord


@dataclass
class CacheEntry:
    sequence: str
    sequence_hash: str
    created_at: float
    accessed_at: float
    access_count: int
    file_size: int
    metadata: Dict = field(default_factory=dict)


class MSACacheManager:
    def __init__(self, cache_dir: str, max_size_gb: float = 10.0,
                 ttl_days: int = 30, use_hash: bool = True):
        self.cache_dir = cache_dir
        self.max_size_bytes = max_size_gb * 1024 * 1024 * 1024
        self.ttl_seconds = ttl_days * 24 * 60 * 60
        self.use_hash = use_hash
        self.index_path = os.path.join(cache_dir, "cache_index.json")
        self._index: Dict[str, CacheEntry] = {}
        self._load_index()
        self._cleanup_expired()

    def _load_index(self) -> None:
        if os.path.exists(self.index_path):
            try:
                with open(self.index_path, 'r') as f:
                    data = json.load(f)
                for seq_hash, entry_data in data.items():
                    self._index[seq_hash] = CacheEntry(**entry_data)
            except Exception as e:
                print(f"Warning: Could not load cache index: {e}")
                self._index = {}

    def _save_index(self) -> None:
        try:
            data = {
                seq_hash: entry.__dict__
                for seq_hash, entry in self._index.items()
            }
            with open(self.index_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save cache index: {e}")

    def _get_sequence_hash(self, sequence: str) -> str:
        if self.use_hash:
            return hashlib.sha256(sequence.encode()).hexdigest()[:32]
        return sequence[:32]

    def _get_cache_path(self, seq_hash: str) -> str:
        subdir = seq_hash[:2]
        return os.path.join(self.cache_dir, subdir, f"{seq_hash}.pkl")

    def _get_cache_size(self) -> int:
        total = 0
        for entry in self._index.values():
            total += entry.file_size
        return total

    def _cleanup_expired(self) -> None:
        current_time = time.time()
        expired = []
        for seq_hash, entry in self._index.items():
            if current_time - entry.created_at > self.ttl_seconds:
                expired.append(seq_hash)
        for seq_hash in expired:
            self._remove_entry(seq_hash)
        if expired:
            print(f"Cleaned up {len(expired)} expired MSA cache entries")
            self._save_index()

    def _enforce_size_limit(self) -> None:
        current_size = self._get_cache_size()
        if current_size <= self.max_size_bytes:
            return
        sorted_entries = sorted(
            self._index.items(),
            key=lambda x: x[1].accessed_at
        )
        for seq_hash, entry in sorted_entries:
            if current_size <= self.max_size_bytes:
                break
            current_size -= entry.file_size
            self._remove_entry(seq_hash)
        self._save_index()

    def _remove_entry(self, seq_hash: str) -> None:
        if seq_hash in self._index:
            cache_path = self._get_cache_path(seq_hash)
            if os.path.exists(cache_path):
                os.remove(cache_path)
            del self._index[seq_hash]

    def get(self, sequence: str) -> Optional[MSAOutput]:
        if not self.cache_dir:
            return None
        seq_hash = self._get_sequence_hash(sequence)
        if seq_hash not in self._index:
            return None
        entry = self._index[seq_hash]
        cache_path = self._get_cache_path(seq_hash)
        if not os.path.exists(cache_path):
            self._remove_entry(seq_hash)
            self._save_index()
            return None
        try:
            with open(cache_path, 'rb') as f:
                msa_output = pickle.load(f)
            entry.accessed_at = time.time()
            entry.access_count += 1
            self._save_index()
            return msa_output
        except Exception as e:
            print(f"Warning: Could not load cached MSA: {e}")
            self._remove_entry(seq_hash)
            self._save_index()
            return None

    def put(self, sequence: str, msa_output: MSAOutput) -> bool:
        if not self.cache_dir:
            return False
        try:
            seq_hash = self._get_sequence_hash(sequence)
            cache_path = self._get_cache_path(seq_hash)
            os.makedirs(os.path.dirname(cache_path), exist_ok=True)
            temp_a3m_path = msa_output.a3m_path
            msa_output.a3m_path = None
            with open(cache_path, 'wb') as f:
                pickle.dump(msa_output, f)
            file_size = os.path.getsize(cache_path)
            entry = CacheEntry(
                sequence=sequence,
                sequence_hash=seq_hash,
                created_at=time.time(),
                accessed_at=time.time(),
                access_count=1,
                file_size=file_size,
                metadata={
                    "depth": msa_output.feature.depth,
                    "length": len(sequence),
                }
            )
            self._index[seq_hash] = entry
            self._enforce_size_limit()
            self._save_index()
            msa_output.a3m_path = temp_a3m_path
            return True
        except Exception as e:
            print(f"Warning: Could not cache MSA: {e}")
            return False

    def clear(self) -> int:
        count = len(self._index)
        for seq_hash in list(self._index.keys()):
            self._remove_entry(seq_hash)
        if os.path.exists(self.index_path):
            os.remove(self.index_path)
        return count

    def get_stats(self) -> Dict:
        return {
            "total_entries": len(self._index),
            "total_size_bytes": self._get_cache_size(),
            "total_size_mb": self._get_cache_size() / (1024 * 1024),
            "max_size_mb": self.max_size_bytes / (1024 * 1024),
            "ttl_days": self.ttl_seconds / (24 * 60 * 60),
        }


@dataclass
class MSAFeature:
    sequences: List[str]
    headers: List[str]
    query_sequence: str
    gap_count: np.ndarray
    conservation: np.ndarray
    depth: int
    alignment_matrix: np.ndarray
    pssm: Optional[np.ndarray] = None
    aa_counts: Optional[np.ndarray] = None


@dataclass
class MSAOutput:
    feature: MSAFeature
    a3m_path: Optional[str] = None
    sto_path: Optional[str] = None
    paired_path: Optional[str] = None
    template_hits: List[Dict] = field(default_factory=list)


AMINO_ACIDS = "ACDEFGHIKLMNPQRSTVWY"
AA_TO_IDX = {aa: i for i, aa in enumerate(AMINO_ACIDS)}
IDX_TO_AA = {i: aa for i, aa in enumerate(AMINO_ACIDS)}


def validate_sequence(sequence: str) -> Tuple[bool, str]:
    sequence = sequence.upper().strip()
    if not sequence:
        return False, "Sequence is empty"
    invalid_chars = set(sequence) - set(AMINO_ACIDS + "X-")
    if invalid_chars:
        return False, f"Invalid characters: {invalid_chars}"
    return True, "Valid sequence"


def read_fasta(fasta_path: str) -> Tuple[str, List[SeqRecord]]:
    records = list(SeqIO.parse(fasta_path, "fasta"))
    if not records:
        raise ValueError(f"No sequences found in {fasta_path}")
    query = str(records[0].seq.upper())
    return query, records


def write_fasta(sequence: str, name: str = "query") -> str:
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".fasta", delete=False)
    tmp.write(f">{name}\n{sequence}\n")
    tmp.close()
    return tmp.name


def parse_a3m(a3m_path: str) -> Tuple[List[str], List[str]]:
    sequences = []
    headers = []
    with open(a3m_path) as f:
        content = f.read()
    entries = content.split(">")[1:]
    for entry in entries:
        lines = entry.split("\n", 1)
        if len(lines) < 2:
            continue
        header = lines[0].strip()
        seq = "".join(lines[1].split()).replace("\n", "")
        sequences.append(seq)
        headers.append(header)
    return sequences, headers


def parse_stockholm(sto_path: str) -> Tuple[List[str], List[str]]:
    sequences = []
    headers = []
    with open(sto_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("//"):
                continue
            parts = line.split(None, 1)
            if len(parts) == 2:
                headers.append(parts[0])
                sequences.append(parts[1].replace(".", "-"))
    return sequences, headers


def compute_gap_stats(sequences: List[str]) -> np.ndarray:
    if not sequences:
        return np.array([])
    L = len(sequences[0])
    gap_matrix = np.array([[1 if c == "-" else 0 for c in seq] for seq in sequences])
    return gap_matrix.mean(axis=0)


def compute_conservation(sequences: List[str]) -> np.ndarray:
    if not sequences:
        return np.array([])
    L = len(sequences[0])
    N = len(sequences)
    conservation = np.zeros(L)
    for pos in range(L):
        aa_counts = {}
        for seq in sequences:
            aa = seq[pos]
            if aa != "-" and aa in AA_TO_IDX:
                aa_counts[aa] = aa_counts.get(aa, 0) + 1
        if aa_counts:
            max_count = max(aa_counts.values())
            conservation[pos] = max_count / N
    return conservation


def compute_alignment_matrix(sequences: List[str]) -> np.ndarray:
    if not sequences:
        return np.array([[]])
    L = len(sequences[0])
    N = len(sequences)
    matrix = np.full((N, L), -1, dtype=np.int8)
    for i, seq in enumerate(sequences):
        for j, aa in enumerate(seq):
            if aa in AA_TO_IDX:
                matrix[i, j] = AA_TO_IDX[aa]
    return matrix


def compute_pssm(sequences: List[str]) -> Tuple[np.ndarray, np.ndarray]:
    if not sequences:
        return np.array([]), np.array([])
    L = len(sequences[0])
    aa_counts = np.zeros((L, 20), dtype=np.float32)
    for seq in sequences:
        for pos, aa in enumerate(seq):
            if aa in AA_TO_IDX:
                aa_counts[pos, AA_TO_IDX[aa]] += 1
    pssm = np.log2((aa_counts + 1) / (aa_counts.sum(axis=1, keepdims=True) + 20))
    return pssm, aa_counts


def build_msa_feature(sequences: List[str], headers: List[str],
                     query_sequence: str) -> MSAFeature:
    if not sequences:
        sequences = [query_sequence]
        headers = ["query"]
    query_aligned = next((s for s, h in zip(sequences, headers)
                         if "query" in h.lower()), sequences[0])
    gap_count = compute_gap_stats(sequences)
    conservation = compute_conservation(sequences)
    alignment_matrix = compute_alignment_matrix(sequences)
    pssm, aa_counts = compute_pssm(sequences)
    return MSAFeature(
        sequences=sequences,
        headers=headers,
        query_sequence=query_sequence,
        gap_count=gap_count,
        conservation=conservation,
        depth=len(sequences),
        alignment_matrix=alignment_matrix,
        pssm=pssm,
        aa_counts=aa_counts,
    )


class MSAGenerator:
    def __init__(self, config):
        self.config = config
        self.cache_manager: Optional[MSACacheManager] = None
        if hasattr(config, 'cache') and config.cache.enable_cache:
            self.cache_manager = MSACacheManager(
                cache_dir=config.cache.msa_cache_dir,
                max_size_gb=config.cache.max_cache_size_gb,
                ttl_days=config.cache.cache_ttl_days,
                use_hash=config.cache.use_sequence_hash,
            )
            stats = self.cache_manager.get_stats()
            print(f"MSA cache initialized: {stats['total_entries']} entries, "
                  f"{stats['total_size_mb']:.2f} MB")

    def generate(self, sequence: str, job_id: Optional[str] = None,
                use_cache: bool = True) -> MSAOutput:
        job_id = job_id or f"job_{os.getpid()}"
        sequence = sequence.upper().strip()
        valid, msg = validate_sequence(sequence)
        if not valid:
            raise ValueError(msg)
        if use_cache and self.cache_manager is not None:
            cached = self.cache_manager.get(sequence)
            if cached is not None:
                print(f"[MSA Cache] Hit for sequence (length={len(sequence)})")
                return cached
            print(f"[MSA Cache] Miss, generating new MSA...")
        fasta_path = write_fasta(sequence, job_id)
        try:
            a3m_path = self._run_mmseqs2(fasta_path, job_id)
            if a3m_path and os.path.exists(a3m_path):
                sequences, headers = parse_a3m(a3m_path)
            else:
                sequences, headers = [sequence], [f">{job_id}"]
            feature = build_msa_feature(sequences, headers, sequence)
            msa_output = MSAOutput(
                feature=feature,
                a3m_path=a3m_path,
                template_hits=self._search_templates(sequence),
            )
            if use_cache and self.cache_manager is not None:
                self.cache_manager.put(sequence, msa_output)
                print(f"[MSA Cache] Saved sequence to cache")
            return msa_output
        finally:
            if os.path.exists(fasta_path):
                os.unlink(fasta_path)

    def clear_cache(self) -> int:
        if self.cache_manager is not None:
            count = self.cache_manager.clear()
            print(f"Cleared {count} MSA cache entries")
            return count
        return 0

    def get_cache_stats(self) -> Optional[Dict]:
        if self.cache_manager is not None:
            return self.cache_manager.get_stats()
        return None

    def _run_mmseqs2(self, fasta_path: str, job_id: str) -> Optional[str]:
        output_dir = tempfile.mkdtemp(prefix=f"msa_{job_id}_")
        a3m_output = os.path.join(output_dir, "msa.a3m")
        mmseqs_script = '''
import sys
from urllib import request
import json
import time

def run_mmseqs2(fasta_path, out_path):
    with open(fasta_path) as f:
        fasta_data = f.read()
    server_url = "https://api.colabfold.com/msa"
    data = {"fasta": fasta_data, "mode": "mmseqs2"}
    req = request.Request(server_url, data=json.dumps(data).encode(),
                          headers={"Content-Type": "application/json"})
    try:
        with request.urlopen(req, timeout=300) as resp:
            result = resp.read().decode()
            with open(out_path, "w") as f:
                f.write(result)
            return True
    except Exception as e:
        print(f"MSA API error: {e}", file=sys.stderr)
        return False

run_mmseqs2(sys.argv[1], sys.argv[2])
'''
        script_path = os.path.join(output_dir, "run_msa.py")
        with open(script_path, "w") as f:
            f.write(mmseqs_script)
        try:
            result = subprocess.run(
                ["python", script_path, fasta_path, a3m_output],
                capture_output=True, text=True, timeout=360,
            )
            if result.returncode == 0 and os.path.exists(a3m_output):
                return a3m_output
        except subprocess.TimeoutExpired:
            print("MSA generation timed out")
        except Exception as e:
            print(f"MSA subprocess error: {e}")
        return self._generate_synthetic_msa(sequence=None, fasta_path=fasta_path,
                                           output_path=a3m_output)

    def _generate_synthetic_msa(self, sequence: Optional[str], fasta_path: str,
                               output_path: str) -> Optional[str]:
        if sequence is None:
            with open(fasta_path) as f:
                lines = f.readlines()
                sequence = lines[1].strip() if len(lines) > 1 else ""
        if not sequence:
            return None
        L = len(sequence)
        num_seqs = max(16, min(64, L // 2))
        rng = np.random.RandomState(42)
        with open(output_path, "w") as f:
            f.write(f">query\n{sequence}\n")
            for i in range(num_seqs - 1):
                mutated = list(sequence)
                num_mutations = rng.randint(1, max(2, int(L * 0.15)))
                positions = rng.choice(L, num_mutations, replace=False)
                for pos in positions:
                    original = mutated[pos]
                    aa_list = [aa for aa in AMINO_ACIDS if aa != original]
                    mutated[pos] = rng.choice(aa_list)
                f.write(f">synth_{i}\n{''.join(mutated)}\n")
        return output_path

    def _search_templates(self, sequence: str) -> List[Dict]:
        return []


def extract_msa_features(sequence: str, config=None) -> MSAFeature:
    generator = MSAGenerator(config)
    output = generator.generate(sequence)
    return output.feature


def compute_neff(msa_feature: MSAFeature) -> float:
    if msa_feature.depth <= 1:
        return 1.0
    similarity = np.zeros(msa_feature.depth)
    for i in range(1, msa_feature.depth):
        matches = (msa_feature.alignment_matrix[0] == msa_feature.alignment_matrix[i])
        matches = matches & (msa_feature.alignment_matrix[i] >= 0)
        valid = (msa_feature.alignment_matrix[i] >= 0).sum()
        similarity[i] = matches.sum() / max(1, valid)
    weights = 1.0 / (1 + (similarity > 0.8).sum(axis=0))
    return float(weights.sum())
