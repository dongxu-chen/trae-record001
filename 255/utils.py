import os
import re
import gzip
import tempfile
import numpy as np
from typing import List, Tuple, Optional, Dict, Union
from Bio.PDB import PDBParser, PDBIO, Select, Structure, Model, Chain, Residue, Atom
from Bio.PDB.Polypeptide import PPBuilder, is_aa
from Bio.SeqUtils import molecular_weight, ProtParam


AMINO_ACIDS = "ACDEFGHIKLMNPQRSTVWY"
AA_THREE_TO_ONE = {
    'ALA': 'A', 'CYS': 'C', 'ASP': 'D', 'GLU': 'E', 'PHE': 'F',
    'GLY': 'G', 'HIS': 'H', 'ILE': 'I', 'LYS': 'K', 'LEU': 'L',
    'MET': 'M', 'ASN': 'N', 'PRO': 'P', 'GLN': 'Q', 'ARG': 'R',
    'SER': 'S', 'THR': 'T', 'VAL': 'V', 'TRP': 'W', 'TYR': 'Y',
    'SEC': 'U', 'PYL': 'O',
}
AA_ONE_TO_THREE = {v: k for k, v in AA_THREE_TO_ONE.items()}


def validate_amino_acid_sequence(sequence: str) -> Tuple[bool, str]:
    sequence = sequence.upper().strip()
    if not sequence:
        return False, "Sequence is empty"
    if len(sequence) < 5:
        return False, f"Sequence too short (minimum 5 residues, got {len(sequence)})"
    if len(sequence) > 2000:
        return False, f"Sequence too long (maximum 2000 residues, got {len(sequence)})"
    invalid_chars = set(sequence) - set(AMINO_ACIDS + "X")
    if invalid_chars:
        return False, f"Invalid characters: {invalid_chars}"
    return True, "Valid sequence"


def sequence_properties(sequence: str) -> Dict[str, Union[float, int, str]]:
    seq = sequence.upper().strip()
    analyser = ProtParam.ProteinAnalysis(seq)
    return {
        "length": len(seq),
        "molecular_weight": analyser.molecular_weight(),
        "aromaticity": analyser.aromaticity(),
        "instability_index": analyser.instability_index(),
        "isoelectric_point": analyser.isoelectric_point(),
        "charge_at_pH7": analyser.charge_at_pH(7.0),
        "gravy": analyser.gravy(),
        "amino_acid_count": analyser.count_amino_acids(),
        "amino_acid_percent": analyser.amino_acids_percent,
    }


def read_pdb(pdb_path: str, gzipped: bool = False) -> Structure.Structure:
    parser = PDBParser(QUIET=True)
    if gzipped or pdb_path.endswith('.gz'):
        with gzip.open(pdb_path, 'rt') as f:
            return parser.get_structure('structure', f)
    return parser.get_structure('structure', pdb_path)


def write_pdb(structure: Structure.Structure, output_path: str) -> str:
    io = PDBIO()
    io.set_structure(structure)
    io.save(output_path)
    return output_path


def extract_sequence_from_pdb(pdb_path: str, chain_id: str = 'A') -> str:
    structure = read_pdb(pdb_path)
    sequence = []
    for model in structure:
        for chain in model:
            if chain_id and chain.id != chain_id:
                continue
            for residue in chain:
                if is_aa(residue):
                    resname = residue.get_resname()
                    one_letter = AA_THREE_TO_ONE.get(resname, 'X')
                    sequence.append(one_letter)
    return ''.join(sequence)


def extract_coordinates_from_pdb(pdb_path: str, atom_type: str = 'CA',
                                chain_id: Optional[str] = 'A') -> np.ndarray:
    structure = read_pdb(pdb_path)
    coords = []
    for model in structure:
        for chain in model:
            if chain_id and chain.id != chain_id:
                continue
            for residue in chain:
                if is_aa(residue) and atom_type in residue:
                    coords.append(residue[atom_type].get_coord())
    return np.array(coords)


def compute_rmsd(coords1: np.ndarray, coords2: np.ndarray,
                align: bool = True) -> float:
    coords1 = np.asarray(coords1, dtype=np.float64)
    coords2 = np.asarray(coords2, dtype=np.float64)
    if coords1.shape != coords2.shape:
        raise ValueError(f"Coordinate arrays must have the same shape: "
                        f"{coords1.shape} vs {coords2.shape}")
    if align:
        coords1_centered = coords1 - coords1.mean(axis=0)
        coords2_centered = coords2 - coords2.mean(axis=0)
        H = coords1_centered.T @ coords2_centered
        U, S, Vt = np.linalg.svd(H)
        d = np.sign(np.linalg.det(Vt.T @ U.T))
        Vt[-1, :] *= d
        R = Vt.T @ U.T
        coords1_aligned = coords1_centered @ R.T
        diff = coords1_aligned - coords2_centered
    else:
        diff = coords1 - coords2
    return float(np.sqrt((diff ** 2).mean()))


def compute_contact_map(coords: np.ndarray, threshold: float = 8.0) -> np.ndarray:
    coords = np.asarray(coords)
    N = coords.shape[0]
    dist_matrix = np.sqrt(((coords[:, None] - coords) ** 2).sum(axis=-1))
    return (dist_matrix < threshold).astype(np.int8)


def compute_secondary_structure(sequence: str, method: str = 'simple') -> str:
    if method == 'simple':
        ss = []
        for i, aa in enumerate(sequence):
            if aa in 'AVLIMFYWR':
                ss.append('H')
            elif aa in 'EDNQST':
                ss.append('E')
            else:
                ss.append('C')
        return ''.join(ss)
    elif method == 'garnier':
        try:
            analyser = ProtParam.ProteinAnalysis(sequence)
            sec_struct = analyser.secondary_structure_fraction()
            helix, turn, sheet = sec_struct
            result = []
            for i, aa in enumerate(sequence):
                if i < len(sequence) * helix:
                    result.append('H')
                elif i < len(sequence) * (helix + sheet):
                    result.append('E')
                else:
                    result.append('C')
            return ''.join(result)
        except:
            return compute_secondary_structure(sequence, 'simple')
    else:
        raise ValueError(f"Unknown method: {method}")


def create_pdb_from_coords(coords: np.ndarray, sequence: str,
                          output_path: str, b_factors: Optional[np.ndarray] = None) -> str:
    coords = np.asarray(coords)
    if b_factors is None:
        b_factors = np.zeros(len(sequence))
    structure = Structure.Structure('prediction')
    model = Model.Model(0)
    chain = Chain.Chain('A')
    for i, (aa, coord, b_factor) in enumerate(zip(sequence, coords, b_factors)):
        res_id = (' ', i + 1, ' ')
        resname = AA_ONE_TO_THREE.get(aa, 'ALA')
        residue = Residue.Residue(res_id, resname, 0)
        n_atom = Atom.Atom('N', coord + np.array([-0.5, -1.2, 0.0]),
                          b_factor, 1.0, ' ', ' N ', 0, 'N')
        ca_atom = Atom.Atom('CA', coord, b_factor, 1.0, ' ', ' CA ', 1, 'C')
        c_atom = Atom.Atom('C', coord + np.array([1.5, 0.0, 0.0]),
                          b_factor, 1.0, ' ', ' C ', 2, 'C')
        o_atom = Atom.Atom('O', coord + np.array([2.2, 0.8, 0.0]),
                          b_factor, 1.0, ' ', ' O ', 3, 'O')
        residue.add(n_atom)
        residue.add(ca_atom)
        residue.add(c_atom)
        residue.add(o_atom)
        chain.add(residue)
    model.add(chain)
    structure.add(model)
    io = PDBIO()
    io.set_structure(structure)
    io.save(output_path)
    return output_path


def plddt_to_bfactor(plddt: np.ndarray, inverse: bool = True) -> np.ndarray:
    if inverse:
        return 100.0 - plddt
    return plddt


class PDBUtils:
    @staticmethod
    def load(pdb_path: str) -> Structure.Structure:
        return read_pdb(pdb_path)

    @staticmethod
    def save(structure: Structure.Structure, output_path: str) -> str:
        return write_pdb(structure, output_path)

    @staticmethod
    def get_sequence(pdb_path: str, chain_id: str = 'A') -> str:
        return extract_sequence_from_pdb(pdb_path, chain_id)

    @staticmethod
    def get_coords(pdb_path: str, atom_type: str = 'CA',
                  chain_id: Optional[str] = 'A') -> np.ndarray:
        return extract_coordinates_from_pdb(pdb_path, atom_type, chain_id)

    @staticmethod
    def from_coords(coords: np.ndarray, sequence: str,
                   output_path: str, b_factors: Optional[np.ndarray] = None) -> str:
        return create_pdb_from_coords(coords, sequence, output_path, b_factors)

    @staticmethod
    def rmsd(pdb1: str, pdb2: str, atom_type: str = 'CA',
            chain_id: Optional[str] = 'A', align: bool = True) -> float:
        coords1 = extract_coordinates_from_pdb(pdb1, atom_type, chain_id)
        coords2 = extract_coordinates_from_pdb(pdb2, atom_type, chain_id)
        return compute_rmsd(coords1, coords2, align)


class SequenceUtils:
    @staticmethod
    def validate(sequence: str) -> Tuple[bool, str]:
        return validate_amino_acid_sequence(sequence)

    @staticmethod
    def properties(sequence: str) -> Dict[str, Union[float, int, str]]:
        return sequence_properties(sequence)

    @staticmethod
    def from_fasta(fasta_path: str) -> List[str]:
        from Bio import SeqIO
        sequences = []
        for record in SeqIO.parse(fasta_path, 'fasta'):
            sequences.append(str(record.seq.upper()))
        return sequences

    @staticmethod
    def to_fasta(sequence: str, name: str = 'sequence',
                output_path: Optional[str] = None) -> Optional[str]:
        fasta_content = f">{name}\n{sequence}\n"
        if output_path:
            with open(output_path, 'w') as f:
                f.write(fasta_content)
            return output_path
        return None

    @staticmethod
    def save_fasta(sequences: List[str], names: List[str], output_path: str) -> str:
        with open(output_path, 'w') as f:
            for name, seq in zip(names, sequences):
                f.write(f">{name}\n{seq}\n")
        return output_path
