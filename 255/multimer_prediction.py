import os
import re
import json
import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Union
from enum import Enum


class StoichiometryType(Enum):
    MONOMER = "1"
    DIMER = "2"
    TRIMER = "3"
    TETRAMER = "4"
    PENTAMER = "5"
    HEXAMER = "6"
    HETEROMER = "hetero"


@dataclass
class ChainInfo:
    chain_id: str
    sequence: str
    sequence_length: int
    is_homomer: bool
    copy_number: int = 1


@dataclass
class InterfaceInfo:
    chain1: str
    chain2: str
    num_residues: int
    interface_area: float
    hydrogen_bonds: int
    salt_bridges: int
    hydrophobic_interactions: int
    binding_affinity: float
    confidence: float


@dataclass
class MultimerPrediction:
    chains: List[ChainInfo]
    stoichiometry: str
    num_chains: int
    interfaces: List[InterfaceInfo]
    pdb_content: str
    assembly_confidence: float
    interface_confidences: Dict[str, float]
    is_homomeric: bool
    plddt_by_chain: Dict[str, np.ndarray]
    pae_by_chain: Optional[Dict[str, np.ndarray]] = None


@dataclass
class AssemblyResult:
    success: bool
    multimer: MultimerPrediction
    output_path: Optional[str] = None
    error_message: Optional[str] = None


def parse_complex_sequence(complex_input: Union[str, List[str], Dict[str, str]]) -> List[ChainInfo]:
    if isinstance(complex_input, str):
        if ":" in complex_input:
            parts = complex_input.split(":")
        elif "," in complex_input:
            parts = complex_input.split(",")
        else:
            parts = [complex_input]
        chains = []
        for i, seq in enumerate(parts):
            chain_id = chr(65 + i)
            chains.append(ChainInfo(
                chain_id=chain_id, sequence=seq.strip(),
                sequence_length=len(seq.strip()), is_homomer=True
            ))
        return chains
    elif isinstance(complex_input, list):
        chains = []
        for i, seq in enumerate(complex_input):
            chain_id = chr(65 + i)
            chains.append(ChainInfo(
                chain_id=chain_id, sequence=seq.strip(),
                sequence_length=len(seq.strip()), is_homomer=True
            ))
        return chains
    elif isinstance(complex_input, dict):
        chains = []
        for chain_id, seq in complex_input.items():
            chains.append(ChainInfo(
                chain_id=chain_id, sequence=seq.strip(),
                sequence_length=len(seq.strip()),
                is_homomer=len(set(complex_input.values())) == 1
            ))
        return chains
    else:
        raise ValueError(f"Unsupported input type: {type(complex_input)}")


def detect_homology(sequences: List[str]) -> Tuple[bool, float]:
    if len(sequences) < 2:
        return True, 1.0
    seq1 = sequences[0]
    identity = 1.0
    for seq in sequences[1:]:
        matches = sum(1 for a, b in zip(seq1, seq) if a == b)
        identity = min(identity, matches / max(len(seq1), len(seq)))
    return identity > 0.9, float(identity)


def generate_homomer_positions(base_positions: np.ndarray, num_copies: int,
                               rotation_angle: float = 72.0) -> np.ndarray:
    all_positions = [base_positions]
    center = base_positions.mean(axis=0)
    for copy_idx in range(1, num_copies):
        angle = np.radians(rotation_angle * copy_idx)
        rotation_matrix = np.array([
            [np.cos(angle), -np.sin(angle), 0],
            [np.sin(angle), np.cos(angle), 0],
            [0, 0, 1]
        ])
        translated = base_positions - center
        rotated = translated @ rotation_matrix.T
        translated_back = rotated + center + np.array([5.0 * copy_idx, 0, 0])
        all_positions.append(translated_back)
    return np.vstack(all_positions)


def generate_heteromer_positions(chain_positions: List[np.ndarray]) -> np.ndarray:
    all_positions = []
    offset = 0.0
    for positions in chain_positions:
        translated = positions + np.array([offset, 0, 0])
        all_positions.append(translated)
        offset += positions.shape[0] * 3.8 + 20.0
    return np.vstack(all_positions)


def compute_interface_info(positions1: np.ndarray, positions2: np.ndarray,
                          threshold: float = 8.0) -> InterfaceInfo:
    if positions1.ndim == 3:
        positions1 = positions1.reshape(-1, 3)
    if positions2.ndim == 3:
        positions2 = positions2.reshape(-1, 3)
    dist_matrix = np.sqrt(((positions1[:, None] - positions2) ** 2).sum(axis=-1))
    contacts = (dist_matrix < threshold).sum()
    interface_residues = int((dist_matrix < threshold).any(axis=1).sum() +
                            (dist_matrix < threshold).any(axis=0).sum())
    interface_area = interface_residues * 15.0
    confidence = min(1.0, contacts / 100.0)
    return InterfaceInfo(
        chain1="A", chain2="B",
        num_residues=interface_residues,
        interface_area=interface_area,
        hydrogen_bonds=int(contacts // 3),
        salt_bridges=int(contacts // 5),
        hydrophobic_interactions=int(contacts // 2),
        binding_affinity=float(-np.log(max(1e-6, confidence)) * 2.0),
        confidence=confidence
    )


class MultimerPredictor:
    def __init__(self, config):
        self.config = config

    def predict_multimer(self, sequences: Union[str, List[str], Dict[str, str]],
                       stoichiometry: Optional[str] = None,
                       homomer_copies: int = 2) -> AssemblyResult:
        try:
            chains = parse_complex_sequence(sequences)
            seq_list = [c.sequence for c in chains]
            if stoichiometry is None:
                is_homomeric, avg_identity = detect_homology(seq_list)
                if is_homomeric and len(chains) == 1:
                    stoichiometry = f"{homomer_copies}"
                else:
                    stoichiometry = f"{len(chains)}"
            multimer = self._assemble_multimer(chains, stoichiometry)
            return AssemblyResult(success=True, multimer=multimer)
        except Exception as e:
            import traceback
            traceback.print_exc()
            empty_multimer = MultimerPrediction(
                chains=[], stoichiometry="", num_chains=0,
                interfaces=[], pdb_content="",
                assembly_confidence=0.0,
                interface_confidences={},
                is_homomeric=False,
                plddt_by_chain={}
            )
            return AssemblyResult(success=False, multimer=empty_multimer,
                                error_message=str(e))

    def _assemble_multimer(self, chains: List[ChainInfo],
                          stoichiometry: str) -> MultimerPrediction:
        sequences = [c.sequence for c in chains]
        num_chains = len(chains)
        is_homomeric = all(s == sequences[0] for s in sequences)
        all_chain_positions = []
        all_chain_plddt = []
        from structure_predictor import StructurePredictor
        predictor = StructurePredictor(self.config)
        predictor.load_model()
        from msa_features import MSAGenerator
        msa_gen = MSAGenerator(self.config)
        for chain in chains:
            msa_output = msa_gen.generate(chain.sequence)
            struct_pred = predictor.predict(chain.sequence, msa_output.feature)
            chain_positions = self._extract_backbone_positions(struct_pred.pdb_content)
            all_chain_positions.append(chain_positions)
            all_chain_plddt.append(struct_pred.plddt)
        interfaces = []
        for i in range(len(chains)):
            for j in range(i + 1, len(chains)):
                interface = compute_interface_info(
                    all_chain_positions[i],
                    all_chain_positions[j]
                )
                interface.chain1 = chains[i].chain_id
                interface.chain2 = chains[j].chain_id
                interfaces.append(interface)
        pdb_content = self._build_multimer_pdb(chains, all_chain_positions, all_chain_plddt)
        interface_confidences = {
            f"{iface.chain1}_{iface.chain2}": iface.confidence
            for iface in interfaces
        }
        assembly_confidence = float(np.mean([iface.confidence for iface in interfaces])) \
            if interfaces else 0.5
        plddt_by_chain = {
            chain.chain_id: plddt
            for chain, plddt in zip(chains, all_chain_plddt)
        }
        return MultimerPrediction(
            chains=chains,
            stoichiometry=stoichiometry,
            num_chains=num_chains,
            interfaces=interfaces,
            pdb_content=pdb_content,
            assembly_confidence=assembly_confidence,
            interface_confidences=interface_confidences,
            is_homomeric=is_homomeric,
            plddt_by_chain=plddt_by_chain,
        )

    def _extract_backbone_positions(self, pdb_content: str) -> np.ndarray:
        positions = []
        for line in pdb_content.split('\n'):
            if line.startswith('ATOM') and 'CA' in line:
                try:
                    x = float(line[30:38])
                    y = float(line[38:46])
                    z = float(line[46:54])
                    positions.append([x, y, z])
                except:
                    pass
        return np.array(positions, dtype=np.float32)

    def _arrange_chains(self, chain_positions: List[np.ndarray],
                        is_homomeric: bool) -> np.ndarray:
        if is_homomeric and len(chain_positions) == 1:
            return chain_positions[0]
        return np.vstack(chain_positions)

    def _build_multimer_pdb(self, chains: List[ChainInfo],
                          chain_positions: List[np.ndarray],
                          chain_plddts: List[np.ndarray]) -> str:
        pdb_lines = []
        pdb_lines.append("HEADER    PROTEIN COMPLEX STRUCTURE PREDICTION")
        pdb_lines.append(f"TITLE     Multimer prediction")
        pdb_lines.append(f"REMARK   1 COMPLEX WITH {len(chains)} CHAINS")
        atom_idx = 1
        for chain_idx, chain in enumerate(chains):
            positions = chain_positions[chain_idx]
            plddt = chain_plddts[chain_idx]
            for res_idx, (aa, pos, conf) in enumerate(zip(chain.sequence,
                                                           positions, plddt)):
                res_num = res_idx + 1
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
                    line = (f"ATOM  {atom_idx:5d}  {atom_name:3s}  {aa:1s} {chain.chain_id:1s}{res_num:4d}    "
                           f"{x:8.3f}{y:8.3f}{z:8.3f}  1.00 {100 - conf:6.2f}           {atom_name[0]:1s}")
                    pdb_lines.append(line)
                    atom_idx += 1
            pdb_lines.append(f"TER   {atom_idx:5d}      {chain.chain_id:1s}")
            atom_idx += 1
        pdb_lines.append("END")
        return "\n".join(pdb_lines)

    def predict_homomer(self, sequence: str, num_copies: int = 2) -> AssemblyResult:
        chains = []
        for i in range(num_copies):
            chains.append(ChainInfo(
                chain_id=chr(65 + i),
                sequence=sequence,
                sequence_length=len(sequence),
                is_homomer=True
            ))
        return self._assemble_multimer(chains, stoichiometry=str(num_copies))

    def predict_heteromer(self, sequences: Dict[str, str]) -> AssemblyResult:
        chains = parse_complex_sequence(sequences)
        return self._assemble_multimer(chains, stoichiometry=f"{len(chains)}")


def format_multimer_report(multimer: MultimerPrediction) -> str:
    lines = []
    lines.append("=" * 60)
    lines.append("MULTIMER STRUCTURE PREDICTION REPORT")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"Stoichiometry: {multimer.stoichiometry}")
    lines.append(f"Number of chains: {multimer.num_chains}")
    lines.append(f"Homomeric: {multimer.is_homomeric}")
    lines.append(f"Assembly confidence: {multimer.assembly_confidence:.4f}")
    lines.append("")
    lines.append("Chains:")
    for chain in multimer.chains:
        lines.append(f"  Chain {chain.chain_id}: length={chain.sequence_length} residues")
    lines.append("")
    if multimer.interfaces:
        lines.append("Interfaces:")
        for iface in multimer.interfaces:
            lines.append(f"  {iface.chain1}-{iface.chain2}:")
            lines.append(f"    Interface residues: {iface.num_residues}")
            lines.append(f"    Interface area: {iface.interface_area:.1f} Å²")
            lines.append(f"    Hydrogen bonds: {iface.hydrogen_bonds}")
            lines.append(f"    Confidence: {iface.confidence:.4f}")
            lines.append(f"    Predicted binding affinity: {iface.binding_affinity:.2f} kcal/mol")
    lines.append("")
    lines.append("=" * 60)
    return "\n".join(lines)
