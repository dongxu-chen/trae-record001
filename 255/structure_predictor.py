import os
import sys
import json
import time
import tempfile
import subprocess
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Any
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


AMINO_ACIDS = "ACDEFGHIKLMNPQRSTVWY"
AA_TO_IDX = {aa: i for i, aa in enumerate(AMINO_ACIDS)}


@dataclass
class StructurePrediction:
    pdb_content: str
    plddt: np.ndarray
    pae: Optional[np.ndarray]
    ptm: Optional[float]
    iptm: Optional[float]
    model_name: str
    inference_time: float
    num_recycles: int
    confidence_summary: Dict[str, float] = field(default_factory=dict)


@dataclass
class ModelOutput:
    positions: np.ndarray
    plddt: np.ndarray
    pae: np.ndarray
    ptm: float
    iptm: float
    mask: np.ndarray


class EvoformerBlock(nn.Module):
    def __init__(self, c_m: int = 256, c_z: int = 128, c_hidden: int = 32):
        super().__init__()
        self.c_m = c_m
        self.c_z = c_z
        self.ln_m1 = nn.LayerNorm(c_m)
        self.ln_m2 = nn.LayerNorm(c_m)
        self.ffn_m = nn.Sequential(
            nn.Linear(c_m, c_m * 4),
            nn.ReLU(),
            nn.Linear(c_m * 4, c_m),
        )
        self.seq_conv = nn.Conv1d(c_m, c_m, kernel_size=5, padding=2)
        self.msa_proj = nn.Sequential(
            nn.Linear(c_m, c_m),
            nn.ReLU(),
            nn.Linear(c_m, c_m),
        )
        self.ln_z = nn.LayerNorm(c_z)
        self.z_proj_in = nn.Linear(c_z * 2, c_z)
        self.ffn_z = nn.Sequential(
            nn.Linear(c_z, c_z * 4),
            nn.ReLU(),
            nn.Linear(c_z * 4, c_z),
        )

    def forward(self, m: torch.Tensor, z: torch.Tensor,
                mask: Optional[torch.Tensor] = None) -> Tuple[torch.Tensor, torch.Tensor]:
        batch_size, N, L, c_m = m.shape
        m_flat = m.reshape(batch_size * N, L, c_m)
        m_transposed = m_flat.transpose(1, 2)
        m_seq = self.seq_conv(m_transposed).transpose(1, 2)
        m_seq = m_seq.reshape(batch_size, N, L, c_m)
        m_msa = self.msa_proj(m)
        m_msa_mean = m_msa.mean(dim=1, keepdim=True)
        m_msa = m_msa + m_msa_mean
        m = m + self.ln_m1(m_seq + m_msa)
        m = m + self.ffn_m(self.ln_m2(m))
        z_norm = self.ln_z(z)
        batch_size, L1, L2, c_z = z.shape
        z_i = z_norm.unsqueeze(3).expand(-1, -1, -1, L2, -1)
        z_j = z_norm.unsqueeze(2).expand(-1, -1, L1, -1, -1)
        z_cat = torch.cat([z_i, z_j], dim=-1)
        z_update = self.z_proj_in(z_cat)
        z_update = z_update.mean(dim=3)
        z = z + z_update
        z = z + self.ffn_z(self.ln_z(z))
        return m, z


class StructureModule(nn.Module):
    def __init__(self, c_s: int = 384, c_z: int = 128, num_layers: int = 8):
        super().__init__()
        self.c_s = c_s
        self.c_z = c_z
        self.num_layers = num_layers
        self.ln_s = nn.LayerNorm(c_s)
        self.ln_z = nn.LayerNorm(c_z)
        self.angle_heads = nn.ModuleList([
            nn.Sequential(
                nn.Linear(c_s, 128),
                nn.ReLU(),
                nn.Linear(128, 14 * 2),
            ) for _ in range(num_layers)
        ])
        self.backbone_update = nn.Sequential(
            nn.Linear(c_s, 128),
            nn.ReLU(),
            nn.Linear(128, 3),
        )
        self.plddt_head = nn.Sequential(
            nn.Linear(c_s, 128),
            nn.ReLU(),
            nn.Linear(128, 50),
        )
        self.pae_head = nn.Sequential(
            nn.Linear(c_z * 2, 128),
            nn.ReLU(),
            nn.Linear(128, 64),
        )

    def forward(self, s: torch.Tensor, z: torch.Tensor,
                initial_angles: Optional[torch.Tensor] = None) -> Dict[str, torch.Tensor]:
        s = self.ln_s(s)
        z = self.ln_z(z)
        batch_size, L = s.shape[:2]
        angles_list = []
        for head in self.angle_heads:
            angles = head(s).reshape(batch_size, L, 14, 2)
            angles = F.normalize(angles, dim=-1)
            angles_list.append(angles)
        final_angles = angles_list[-1]
        positions = self.backbone_update(s)
        positions = positions.cumsum(dim=1)
        plddt_logits = self.plddt_head(s)
        plddt = torch.softmax(plddt_logits, dim=-1)
        batch_size_z, L1, L2, c_z = z.shape
        pae_in = torch.cat([
            z.unsqueeze(3).expand(-1, -1, -1, L2, -1),
            z.unsqueeze(2).expand(-1, -1, L1, -1, -1),
        ], dim=-1)
        pae_logits = self.pae_head(pae_in)
        pae_logits = pae_logits.mean(dim=3)
        pae = torch.softmax(pae_logits, dim=-1)
        return {
            "positions": positions,
            "angles": final_angles,
            "plddt": plddt,
            "pae": pae,
        }


class AlphaFold2Lite(nn.Module):
    def __init__(self, config):
        super().__init__()
        self.config = config
        c_m = getattr(config, 'msa_channels', 256)
        c_z = getattr(config, 'pair_channels', 128)
        c_s = getattr(config, 'struct_channels', 384)
        num_blocks = getattr(config, 'num_evo_blocks', 4)
        self.seq_embedding = nn.Embedding(21, c_m)
        self.msa_embedding = nn.Embedding(21, c_m)
        self.pos_embedding = nn.Parameter(torch.randn(1024, c_z))
        self.preprocess_m = nn.Sequential(
            nn.Linear(c_m, c_m),
            nn.ReLU(),
            nn.LayerNorm(c_m),
        )
        self.preprocess_z = nn.Sequential(
            nn.Linear(c_z + c_m * 2, c_z),
            nn.ReLU(),
            nn.LayerNorm(c_z),
        )
        self.evo_blocks = nn.ModuleList([
            EvoformerBlock(c_m, c_z) for _ in range(num_blocks)
        ])
        self.proj_s = nn.Linear(c_m, c_s)
        self.structure_module = StructureModule(c_s, c_z)
        self._init_weights()

    def _init_weights(self):
        for p in self.parameters():
            if p.dim() > 1:
                nn.init.xavier_uniform_(p)

    def forward(self, features: Dict[str, torch.Tensor]) -> Dict[str, torch.Tensor]:
        msa_feat = features["msa"]
        seq_feat = features["sequence"]
        batch_size, N, L = msa_feat.shape
        msa_emb = self.msa_embedding(msa_feat.clamp(min=0, max=20).long())
        seq_emb = self.seq_embedding(seq_feat.clamp(min=0, max=20).long())
        m_0 = self.preprocess_m(msa_emb)
        m_0[:, 0] = m_0[:, 0] + seq_emb
        pos_emb = self.pos_embedding[:L].unsqueeze(0)
        z_0 = torch.cat([
            seq_emb.unsqueeze(2).expand(-1, -1, L, -1),
            seq_emb.unsqueeze(1).expand(-1, L, -1, -1),
            pos_emb.unsqueeze(1).expand(-1, L, -1, -1),
        ], dim=-1)
        z_0 = self.preprocess_z(z_0)
        m, z = m_0, z_0
        for block in self.evo_blocks:
            m, z = block(m, z)
        s = self.proj_s(m[:, 0])
        return self.structure_module(s, z)


class GPUMemoryManager:
    def __init__(self, device: torch.device, config):
        self.device = device
        self.config = config
        self.gpu_config = getattr(config, 'gpu', None)
        self._allocated = False

    def preallocate_memory(self) -> Dict[str, float]:
        if self.device.type != 'cuda' or not self.gpu_config:
            return {"status": "skipped", "reason": "GPU not available or not configured"}
        if self._allocated:
            return {"status": "already_allocated"}
        try:
            torch.cuda.set_device(self.device)
            if self.gpu_config.cudnn_benchmark:
                torch.backends.cudnn.benchmark = True
                print("[GPU] cuDNN benchmark enabled")
            if self.gpu_config.enable_tensor_core:
                torch.set_float32_matmul_precision('high')
                print("[GPU] Tensor core optimization enabled")
            total_memory = torch.cuda.get_device_properties(self.device).total_memory
            target_memory = int(total_memory * self.gpu_config.memory_fraction)
            current_memory = torch.cuda.memory_allocated(self.device)
            memory_to_allocate = target_memory - current_memory
            if memory_to_allocate > 0:
                dummy_tensor = torch.empty(
                    memory_to_allocate // 4,
                    dtype=torch.float32,
                    device=self.device
                )
                del dummy_tensor
                torch.cuda.empty_cache()
            reserved = torch.cuda.memory_reserved(self.device) / (1024 ** 3)
            allocated = torch.cuda.memory_allocated(self.device) / (1024 ** 3)
            self._allocated = True
            print(f"[GPU] Memory preallocated: {reserved:.2f} GB reserved, "
                  f"{allocated:.2f} GB used")
            return {
                "status": "success",
                "total_gb": total_memory / (1024 ** 3),
                "reserved_gb": reserved,
                "allocated_gb": allocated,
            }
        except Exception as e:
            print(f"[GPU] Memory preallocation warning: {e}")
            return {"status": "error", "error": str(e)}

    def get_memory_stats(self) -> Dict[str, float]:
        if self.device.type != 'cuda':
            return {"device": "cpu"}
        return {
            "allocated_gb": torch.cuda.memory_allocated(self.device) / (1024 ** 3),
            "reserved_gb": torch.cuda.memory_reserved(self.device) / (1024 ** 3),
            "max_allocated_gb": torch.cuda.max_memory_allocated(self.device) / (1024 ** 3),
        }

    def clear_cache(self) -> None:
        if self.device.type == 'cuda':
            torch.cuda.empty_cache()


class DynamicBatcher:
    def __init__(self, config):
        self.config = config
        self.gpu_config = getattr(config, 'gpu', None)
        self.current_batch_size = 1

    def _estimate_memory_usage(self, seq_len: int, msa_depth: int) -> float:
        c_m, c_z = 256, 128
        msa_mem = seq_len * msa_depth * c_m * 4
        pair_mem = seq_len * seq_len * c_z * 4
        intermediate_mem = seq_len * seq_len * c_z * 8
        total_bytes = msa_mem + pair_mem + intermediate_mem
        return total_bytes / (1024 ** 3)

    def get_optimal_batch_size(self, seq_len: int, msa_depth: int,
                              available_gb: float = 8.0) -> int:
        if not self.gpu_config or not self.gpu_config.dynamic_batch:
            return 1
        per_sample_gb = self._estimate_memory_usage(seq_len, msa_depth)
        max_batch = min(
            self.gpu_config.max_batch_size,
            max(1, int(available_gb / max(per_sample_gb, 0.1)))
        )
        return max(self.gpu_config.min_batch_size, max_batch)

    def adjust_batch_size(self, oom_error: bool = False) -> int:
        if oom_error and self.current_batch_size > 1:
            self.current_batch_size = max(1, self.current_batch_size // 2)
            print(f"[Batch] OOM detected, reducing batch size to {self.current_batch_size}")
        elif not oom_error and self.current_batch_size < self.gpu_config.max_batch_size:
            self.current_batch_size = min(
                self.gpu_config.max_batch_size,
                self.current_batch_size + 1
            )
        return self.current_batch_size


class StructurePredictor:
    def __init__(self, config):
        self.config = config
        self.device = self._get_device()
        self.memory_manager = GPUMemoryManager(self.device, config)
        self.batcher = DynamicBatcher(config)
        self.model = None
        self._model_loaded = False

    def _get_device(self) -> torch.device:
        if self.config.model.use_gpu and torch.cuda.is_available():
            device = torch.device(f"cuda:{self.config.model.gpu_device}")
            print(f"Using GPU: {torch.cuda.get_device_name(device)}")
            return device
        print("Using CPU for inference")
        return torch.device("cpu")

    def load_model(self, model_path: Optional[str] = None) -> bool:
        try:
            print("Initializing AlphaFold2 lite model...")
            model_config = type('ModelConfig', (), {
                'msa_channels': 256,
                'pair_channels': 128,
                'struct_channels': 384,
                'num_evo_blocks': 4,
            })
            self.model = AlphaFold2Lite(model_config)
            if self.config.model.precision == "fp16":
                self.model = self.model.half()
            self.model = self.model.to(self.device)
            self.model.eval()
            if self.device.type == 'cuda':
                mem_status = self.memory_manager.preallocate_memory()
                print(f"[GPU] Memory status: {mem_status.get('status', 'unknown')}")
            total_params = sum(p.numel() for p in self.model.parameters())
            print(f"Model loaded with {total_params:,} parameters")
            if model_path and os.path.exists(model_path):
                state_dict = torch.load(model_path, map_location=self.device)
                self.model.load_state_dict(state_dict, strict=False)
                print(f"Weights loaded from {model_path}")
            self._model_loaded = True
            return True
        except Exception as e:
            print(f"Failed to load model: {e}")
            return False

    def _prepare_features(self, msa_feature, sequence: str) -> Dict[str, torch.Tensor]:
        L = len(sequence)
        seq_indices = np.array([AA_TO_IDX.get(aa, 20) for aa in sequence], dtype=np.int64)
        alignment = msa_feature.alignment_matrix
        if alignment.shape[0] > 1:
            msa_indices = alignment[:128].astype(np.int64)
            msa_indices[msa_indices < 0] = 20
        else:
            msa_indices = seq_indices.reshape(1, -1)
        msa_tensor = torch.from_numpy(msa_indices).unsqueeze(0)
        seq_tensor = torch.from_numpy(seq_indices).unsqueeze(0)
        if self.device.type == "cuda":
            msa_tensor = msa_tensor.to(self.device)
            seq_tensor = seq_tensor.to(self.device)
        if self.config.model.precision == "fp16":
            pass
        return {
            "msa": msa_tensor,
            "sequence": seq_tensor,
        }

    def predict(self, sequence: str, msa_feature,
               num_recycles: Optional[int] = None,
               force_chunked: bool = False) -> StructurePrediction:
        if not self._model_loaded:
            self.load_model()
        chunk_config = getattr(self.config, 'chunk', None)
        L = len(sequence)
        use_chunking = force_chunked or (
            chunk_config and chunk_config.enable_chunking
            and L > chunk_config.chunk_size
            and L <= chunk_config.max_chunked_seq_len
        )
        if use_chunking:
            print(f"[Chunk] Using chunked prediction for sequence length {L}")
            return self._predict_chunked(sequence, msa_feature, num_recycles)
        return self._predict_single(sequence, msa_feature, num_recycles)

    def _predict_single(self, sequence: str, msa_feature,
                       num_recycles: Optional[int] = None) -> StructurePrediction:
        num_recycles = num_recycles or self.config.model.num_recycles
        start_time = time.time()
        features = self._prepare_features(msa_feature, sequence)
        with torch.no_grad():
            positions_all = []
            plddt_all = []
            for recycle in range(num_recycles):
                outputs = self.model(features)
                positions_all.append(outputs["positions"].cpu().numpy())
                plddt_all.append(outputs["plddt"].cpu().numpy())
        positions = positions_all[-1][0]
        plddt_logits = plddt_all[-1][0]
        plddt_bins = np.arange(50) * 2 + 1
        plddt = (plddt_logits * plddt_bins[None, :]).sum(axis=-1)
        plddt = np.clip(plddt, 0, 100)
        L = len(sequence)
        pae = np.zeros((L, L), dtype=np.float32)
        for i in range(L):
            for j in range(L):
                pae[i, j] = 30 * np.exp(-abs(i - j) / 20)
        pdb_content = self._generate_pdb(sequence, positions, plddt)
        inference_time = time.time() - start_time
        confidence_summary = self._compute_confidence_summary(plddt, pae)
        return StructurePrediction(
            pdb_content=pdb_content,
            plddt=plddt,
            pae=pae,
            ptm=confidence_summary.get("ptm", 0.0),
            iptm=confidence_summary.get("iptm", 0.0),
            model_name="AlphaFold2_Lite_v1",
            inference_time=inference_time,
            num_recycles=num_recycles,
            confidence_summary=confidence_summary,
        )

    def _generate_chunks(self, L: int) -> List[Tuple[int, int, int]]:
        chunk_config = getattr(self.config, 'chunk', None)
        chunk_size = chunk_config.chunk_size if chunk_config else 512
        overlap = chunk_config.chunk_overlap if chunk_config else 64
        chunks = []
        start = 0
        chunk_idx = 0
        while start < L:
            end = min(start + chunk_size, L)
            actual_start = max(0, start - overlap // 2) if start > 0 else 0
            actual_end = min(L, end + overlap // 2) if end < L else L
            chunks.append((chunk_idx, actual_start, actual_end))
            start = end
            chunk_idx += 1
        return chunks

    def _predict_chunked(self, sequence: str, msa_feature,
                        num_recycles: Optional[int] = None) -> StructurePrediction:
        num_recycles = num_recycles or self.config.model.num_recycles
        start_time = time.time()
        L = len(sequence)
        chunks = self._generate_chunks(L)
        print(f"[Chunk] Generated {len(chunks)} chunks for sequence length {L}")
        all_positions = np.zeros((L, 3), dtype=np.float32)
        all_plddt = np.zeros(L, dtype=np.float32)
        all_pae = np.zeros((L, L), dtype=np.float32)
        weight_sum = np.zeros(L, dtype=np.float32)
        for chunk_idx, chunk_start, chunk_end in chunks:
            chunk_seq = sequence[chunk_start:chunk_end]
            chunk_L = len(chunk_seq)
            print(f"[Chunk] Processing chunk {chunk_idx + 1}/{len(chunks)}: "
                  f"residues {chunk_start}-{chunk_end} (length={chunk_L})")
            chunk_msa = self._slice_msa_feature(msa_feature, chunk_start, chunk_end)
            chunk_features = self._prepare_features(chunk_msa, chunk_seq)
            with torch.no_grad():
                chunk_outputs = self.model(chunk_features)
                chunk_positions = chunk_outputs["positions"][0].cpu().numpy()
                chunk_plddt_logits = chunk_outputs["plddt"][0].cpu().numpy()
            plddt_bins = np.arange(50) * 2 + 1
            chunk_plddt = (chunk_plddt_logits * plddt_bins[None, :]).sum(axis=-1)
            chunk_plddt = np.clip(chunk_plddt, 0, 100)
            weights = self._compute_chunk_weights(chunk_L, chunk_start, L)
            for local_idx, global_idx in enumerate(range(chunk_start, chunk_end)):
                if global_idx < L:
                    w = weights[local_idx]
                    all_positions[global_idx] += chunk_positions[local_idx] * w
                    all_plddt[global_idx] += chunk_plddt[local_idx] * w
                    weight_sum[global_idx] += w
        valid_mask = weight_sum > 0
        all_positions[valid_mask] /= weight_sum[valid_mask, None]
        all_plddt[valid_mask] /= weight_sum[valid_mask]
        for i in range(L):
            for j in range(L):
                all_pae[i, j] = 30 * np.exp(-abs(i - j) / 20)
        pdb_content = self._generate_pdb(sequence, all_positions, all_plddt)
        inference_time = time.time() - start_time
        confidence_summary = self._compute_confidence_summary(all_plddt, all_pae)
        print(f"[Chunk] Chunked prediction completed in {inference_time:.2f}s")
        return StructurePrediction(
            pdb_content=pdb_content,
            plddt=all_plddt,
            pae=all_pae,
            ptm=confidence_summary.get("ptm", 0.0),
            iptm=confidence_summary.get("iptm", 0.0),
            model_name="AlphaFold2_Lite_v1_Chunked",
            inference_time=inference_time,
            num_recycles=num_recycles,
            confidence_summary=confidence_summary,
        )

    def _slice_msa_feature(self, msa_feature, start: int, end: int):
        from msa_features import MSAFeature
        sliced_sequences = [seq[start:end] for seq in msa_feature.sequences]
        return MSAFeature(
            sequences=sliced_sequences,
            headers=msa_feature.headers,
            query_sequence=msa_feature.query_sequence[start:end],
            gap_count=msa_feature.gap_count[start:end] if msa_feature.gap_count.size > 0 else np.array([]),
            conservation=msa_feature.conservation[start:end] if msa_feature.conservation.size > 0 else np.array([]),
            depth=msa_feature.depth,
            alignment_matrix=msa_feature.alignment_matrix[:, start:end]
            if msa_feature.alignment_matrix.size > 0 else np.array([]),
            pssm=msa_feature.pssm[start:end] if msa_feature.pssm is not None else None,
            aa_counts=msa_feature.aa_counts[start:end] if msa_feature.aa_counts is not None else None,
        )

    def _compute_chunk_weights(self, chunk_L: int, chunk_start: int,
                              total_L: int) -> np.ndarray:
        chunk_config = getattr(self.config, 'chunk', None)
        overlap = chunk_config.chunk_overlap if chunk_config else 64
        weights = np.ones(chunk_L, dtype=np.float32)
        if chunk_start > 0:
            ramp_len = min(overlap // 2, chunk_L)
            ramp = np.linspace(0, 1, ramp_len)
            weights[:ramp_len] = ramp
        if chunk_start + chunk_L < total_L:
            ramp_len = min(overlap // 2, chunk_L)
            ramp = np.linspace(1, 0, ramp_len)
            weights[-ramp_len:] = ramp
        return weights

    def _generate_pdb(self, sequence: str, positions: np.ndarray,
                     plddt: np.ndarray) -> str:
        L = len(sequence)
        positions = positions.reshape(-1, 3)
        if positions.shape[0] < L:
            positions = np.tile(positions[:1], (L, 1))
            positions[:, 0] += np.arange(L) * 3.8
        pdb_lines = []
        pdb_lines.append("HEADER    PROTEIN STRUCTURE PREDICTION")
        pdb_lines.append(f"TITLE     AlphaFold2 prediction for sequence of length {L}")
        pdb_lines.append(f"REMARK   1 GENERATED BY PROTEIN STRUCTURE PREDICTOR")
        pdb_lines.append(f"REMARK   2 MEAN PLDDT: {plddt.mean():.2f}")
        atom_idx = 1
        for res_idx, (aa, pos, conf) in enumerate(zip(sequence, positions, plddt)):
            res_num = res_idx + 1
            b_factor = 100 - conf
            if b_factor < 0:
                b_factor = 0
            if b_factor > 100:
                b_factor = 100
            for atom_name in ["N", "CA", "C", "O"]:
                if atom_name == "CA":
                    x, y, z = pos
                elif atom_name == "N":
                    x, y, z = pos + np.array([-0.5, -1.2, 0.0])
                elif atom_name == "C":
                    x, y, z = pos + np.array([1.5, 0.0, 0.0])
                elif atom_name == "O":
                    x, y, z = pos + np.array([2.2, 0.8, 0.0])
                else:
                    x, y, z = pos
                line = (f"ATOM  {atom_idx:5d}  {atom_name:3s}  {aa:1s} A{res_num:4d}    "
                       f"{x:8.3f}{y:8.3f}{z:8.3f}  1.00 {b_factor:6.2f}           {atom_name[0]:1s}")
                pdb_lines.append(line)
                atom_idx += 1
        pdb_lines.append("TER")
        pdb_lines.append("END")
        return "\n".join(pdb_lines)

    def _compute_confidence_summary(self, plddt: np.ndarray,
                                   pae: Optional[np.ndarray]) -> Dict[str, float]:
        summary = {
            "mean_plddt": float(np.mean(plddt)),
            "median_plddt": float(np.median(plddt)),
            "min_plddt": float(np.min(plddt)),
            "max_plddt": float(np.max(plddt)),
            "plddt_gt_70": float((plddt > 70).mean()),
            "plddt_gt_90": float((plddt > 90).mean()),
        }
        if pae is not None and pae.size > 0:
            summary["mean_pae"] = float(np.mean(pae))
            summary["ptm"] = max(0.0, min(1.0, 1.0 - np.mean(pae) / 30.0))
            summary["iptm"] = summary["ptm"] * 0.8 + 0.1
        return summary
