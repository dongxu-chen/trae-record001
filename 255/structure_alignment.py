import os
import re
import json
import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Union
from enum import Enum


class AlignmentQuality(Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    MODERATE = "moderate"
    LOW = "low"
    POOR = "poor"


@dataclass
class StructureAlignmentResult:
    target_pdb_id: str
    target_name: str
    rmsd: float
    aligned_length: int
    sequence_identity: float
    structure_identity: float
    tm_score: float
    coverage: float
    quality: AlignmentQuality
    transformation: Optional[np.ndarray] = None
    aligned_residues: Optional[List[Tuple[int, int]]] = None
    target_sequence: Optional[str] = None
    target_organism: Optional[str] = None
    target_function: Optional[str] = None


@dataclass
class FoldSearchResult:
    query_length: int
    num_hits: int
    hits: List[StructureAlignmentResult]
    search_time: float
    fold_prediction: Optional[str] = None
    superfamily: Optional[str] = None


@dataclass
class StructuralFeature:
    feature_type: str
    values: np.ndarray
    description: str


PROTEIN_LIBRARY = [
    {
        "id": "1TGH",
        "name": "Trypsinogen",
        "sequence": "IVGGYTCGANTVPYQVSLNSGYHFCGGSLINSQWVVSAAHCYKSGIQVRLGEDNINVVEGNEQFISASKSIVHPSYNSNTLNNDIMLIKLKSAASLNSRVASISLPTSCASAGTQCLISGWGNTKSSGTSYPDVLKCLKAPILSDSSCKSAYPGQITSNMFCAGYLEGGKDSCQGDSGGPVVCNGQLQGVVSWGDGCAQKNKPGVYTKVCNYVSWIKQTIASN",
        "family": "Serine protease",
        "function": "Proteolysis, digestive enzyme",
        "organism": "Bos taurus",
        "fold": "Trypsin-like serine protease",
    },
    {
        "id": "2PKA",
        "name": "cAMP-dependent protein kinase",
        "sequence": "MAAAAALVRRRRGAISAEVTLSELMARKDSYGKTTGTPPDLSVVSALQNPKFAKFDDEISLEVYQVMEYVNGGELFDFVAKLFRGARIKKEDAAEVYAAKILRDVKGLRYIHPDLIDLYQKYMVSEYCIHCYNQKQIRVTDYGVPSQYMVLLQLVQGYVYLHGAPDYILDLKQTGQVFKPEIGDEVYGVFQEMLRAGKPFTELPDQVSHNIIQHLLDQPSKRITKEEALAHPYFSTFDFDQLSRAIVKFGSELKRDLAMKIILGYDVQGNRSIYYKVLDQNKQEFYQDIKELFTDLLRLIVDPAKRGIIRDLLHPEVIKAKYLLQPTEQQKLLDDLLTDPAKFYLHPNIVCRDYESQSSSGQSSSSSDDEEDE",
        "family": "Protein kinase",
        "function": "Protein phosphorylation, signal transduction",
        "organism": "Mus musculus",
        "fold": "Protein kinase",
    },
    {
        "id": "1AKE",
        "name": "Adenylate kinase",
        "sequence": "MQKIIVVGAPGSGKGTQARLLDRHGWKQISTGDMLRAAIRGDETIGEKAKQVLDEAGKPLVDDVRETAMEENLRKDADGVVLDGVPRTVSQEALRAAFSDADITVLVTEVEGREIIERRLKGRENRDTDSIAEDLKAKLEEYKLTPIYVYDADTQVVQRMVQDRKRLDAIEDYLHTLEELIVEYRKDKD",
        "family": "Nucleoside monophosphate kinase",
        "function": "Nucleotide metabolism",
        "organism": "Escherichia coli",
        "fold": "Alpha/beta plait",
    },
    {
        "id": "1PGB",
        "name": "Protein G B1 domain",
        "sequence": "MTYKLILNGKTLKGETTTEAVDAATAEKVFKQYANDNGVDGEWTYDDATKTFTVTE",
        "family": "Immunoglobulin-binding domain",
        "function": "Immunoglobulin binding",
        "organism": "Streptococcus",
        "fold": "Immunoglobulin-like beta-sandwich",
    },
    {
        "id": "1UBQ",
        "name": "Ubiquitin",
        "sequence": "MQIFVKTLTGKTITLEVEPSDTIENVKAKIQDKEGIPPDQQRLIFAGKQLEDGRTLSDYNIQKESTLHLVLRLRGG",
        "family": "Ubiquitin",
        "function": "Protein degradation signal",
        "organism": "Homo sapiens",
        "fold": "Ubiquitin-like",
    },
    {
        "id": "2HHB",
        "name": "Hemoglobin",
        "sequence": "VLSPADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHFDLSHGSAQVKGHGKKVADALTNAVAHVDDMPNALSALSDLHAHKLRVDPVNFKLLSHCLLVTLAAHLPAEFTPAVHASLDKFLASVSTVLTSKYR",
        "family": "Globin",
        "function": "Oxygen transport",
        "organism": "Homo sapiens",
        "fold": "Globin-like",
    },
]


def extract_calpha_coords(pdb_content: str) -> np.ndarray:
    coords = []
    for line in pdb_content.split('\n'):
        if line.startswith('ATOM') and 'CA' in line:
            try:
                x = float(line[30:38])
                y = float(line[38:46])
                z = float(line[46:54])
                coords.append([x, y, z])
            except:
                pass
    return np.array(coords, dtype=np.float32)


def compute_kabsch_rotation(P: np.ndarray, Q: np.ndarray) -> Tuple[np.ndarray, np.ndarray, float]:
    P = P.astype(np.float64)
    Q = Q.astype(np.float64)
    N = P.shape[0]
    P_centered = P - P.mean(axis=0)
    Q_centered = Q - Q.mean(axis=0)
    H = P_centered.T @ Q_centered
    U, S, Vt = np.linalg.svd(H)
    d = np.sign(np.linalg.det(Vt.T @ U.T))
    D = np.diag([1, 1, d])
    R = Vt.T @ D @ U.T
    P_rotated = P_centered @ R.T
    rmsd = np.sqrt(((P_rotated - Q_centered) ** 2).sum() / N)
    translation = Q.mean(axis=0) - P.mean(axis=0) @ R.T
    return R, translation, rmsd


def compute_tm_score(coords1: np.ndarray, coords2: np.ndarray,
                    L1: int, L2: int) -> float:
    if len(coords1) < 3 or len(coords2) < 3:
        return 0.0
    L = min(L1, L2)
    d0 = max(1.24 * np.cbrt(L - 15) - 1.8, 0.5)
    rmsd = np.sqrt(((coords1[:L] - coords2[:L]) ** 2).sum(axis=1))
    score = np.sum(1.0 / (1.0 + (rmsd / d0) ** 2))
    return float(score / L)


def compute_alignment_quality(rmsd: float, tm_score: float,
                            coverage: float) -> AlignmentQuality:
    if tm_score > 0.8 and rmsd < 2.0:
        return AlignmentQuality.EXCELLENT
    elif tm_score > 0.6 and rmsd < 4.0:
        return AlignmentQuality.GOOD
    elif tm_score > 0.4 and rmsd < 6.0:
        return AlignmentQuality.MODERATE
    elif tm_score > 0.2 and rmsd < 10.0:
        return AlignmentQuality.LOW
    else:
        return AlignmentQuality.POOR


def generate_backbone_from_sequence(sequence: str) -> np.ndarray:
    coords = []
    for i, aa in enumerate(sequence):
        x = i * 3.8
        y = np.sin(i * 0.5) * 2.0
        z = np.cos(i * 0.3) * 1.0
        coords.append([x, y, z])
    return np.array(coords, dtype=np.float32)


def sequence_identity(seq1: str, seq2: str, gap_penalty: float = -2.0) -> float:
    from Bio import pairwise2
    try:
        alignments = pairwise2.align.globalxx(seq1, seq2, score_only=True)
        if not alignments:
            return 0.0
        max_score = min(len(seq1), len(seq2))
        return min(1.0, alignments / max_score)
    except:
        matches = sum(1 for a, b in zip(seq1, seq2) if a == b)
        return matches / max(len(seq1), len(seq2))


def structure_identity(coords1: np.ndarray, coords2: np.ndarray,
                      threshold: float = 3.0) -> float:
    if len(coords1) != len(coords2) or len(coords1) == 0:
        return 0.0
    dists = np.sqrt(((coords1 - coords2) ** 2).sum(axis=1))
    return float((dists < threshold).mean())


class StructureAligner:
    def __init__(self, config=None):
        self.config = config
        self.library = PROTEIN_LIBRARY

    def align_structures(self, coords_query: np.ndarray, coords_target: np.ndarray,
                        seq_query: Optional[str] = None,
                        seq_target: Optional[str] = None) -> StructureAlignmentResult:
        if len(coords_query) < 3 or len(coords_target) < 3:
            return StructureAlignmentResult(
                target_pdb_id="", target_name="",
                rmsd=float('inf'), aligned_length=0,
                sequence_identity=0.0, structure_identity=0.0,
                tm_score=0.0, coverage=0.0,
                quality=AlignmentQuality.POOR,
            )
        min_len = min(len(coords_query), len(coords_target))
        coords_q = coords_query[:min_len]
        coords_t = coords_target[:min_len]
        try:
            R, translation, rmsd = compute_kabsch_rotation(coords_q, coords_t)
            coords_q_aligned = coords_q @ R.T + translation
        except:
            rmsd = np.sqrt(((coords_q - coords_t) ** 2).sum(axis=1).mean())
            coords_q_aligned = coords_q
        tm_score = compute_tm_score(coords_q_aligned, coords_t,
                                    len(coords_query), len(coords_target))
        struct_identity = structure_identity(coords_q_aligned, coords_t)
        seq_identity = 0.0
        if seq_query and seq_target:
            seq_identity = sequence_identity(seq_query, seq_target)
        coverage = min_len / max(len(coords_query), len(coords_target))
        quality = compute_alignment_quality(rmsd, tm_score, coverage)
        return StructureAlignmentResult(
            target_pdb_id="",
            target_name="",
            rmsd=float(rmsd),
            aligned_length=min_len,
            sequence_identity=float(seq_identity),
            structure_identity=struct_identity,
            tm_score=tm_score,
            coverage=float(coverage),
            quality=quality,
        )

    def search_fold(self, sequence: str, pdb_content: str,
                   top_k: int = 5) -> FoldSearchResult:
        import time
        start_time = time.time()
        coords_query = extract_calpha_coords(pdb_content)
        if len(coords_query) == 0:
            coords_query = generate_backbone_from_sequence(sequence)
        hits = []
        for entry in self.library:
            coords_target = generate_backbone_from_sequence(entry["sequence"])
            alignment = self.align_structures(
                coords_query, coords_target,
                sequence, entry["sequence"]
            )
            alignment.target_pdb_id = entry["id"]
            alignment.target_name = entry["name"]
            alignment.target_sequence = entry["sequence"]
            alignment.target_organism = entry["organism"]
            alignment.target_function = entry["function"]
            hits.append(alignment)
        hits.sort(key=lambda h: h.tm_score, reverse=True)
        top_hits = hits[:top_k]
        search_time = time.time() - start_time
        fold_prediction = None
        superfamily = None
        if top_hits and top_hits[0].tm_score > 0.5:
            best_hit = top_hits[0]
            best_entry = next(e for e in self.library if e["id"] == best_hit.target_pdb_id)
            fold_prediction = best_entry.get("fold")
            superfamily = best_entry.get("family")
        return FoldSearchResult(
            query_length=len(sequence),
            num_hits=len(top_hits),
            hits=top_hits,
            search_time=search_time,
            fold_prediction=fold_prediction,
            superfamily=superfamily,
        )

    def format_alignment_report(self, result: StructureAlignmentResult) -> str:
        lines = []
        lines.append("-" * 60)
        lines.append(f"Target: {result.target_pdb_id} - {result.target_name}")
        lines.append(f"  RMSD:            {result.rmsd:.3f} Å")
        lines.append(f"  TM-score:        {result.tm_score:.4f}")
        lines.append(f"  Aligned length:  {result.aligned_length} residues")
        lines.append(f"  Coverage:        {result.coverage * 100:.1f}%")
        lines.append(f"  Sequence ID:     {result.sequence_identity * 100:.1f}%")
        lines.append(f"  Structure ID:    {result.structure_identity * 100:.1f}%")
        lines.append(f"  Quality:         {result.quality.value}")
        if result.target_organism:
            lines.append(f"  Organism:        {result.target_organism}")
        if result.target_function:
            lines.append(f"  Function:        {result.target_function}")
        return "\n".join(lines)

    def format_search_report(self, search_result: FoldSearchResult) -> str:
        lines = []
        lines.append("=" * 70)
        lines.append("STRUCTURE FOLD SEARCH REPORT")
        lines.append("=" * 70)
        lines.append("")
        lines.append(f"Query length: {search_result.query_length} residues")
        lines.append(f"Search time:  {search_result.search_time:.3f} seconds")
        lines.append(f"Number of hits: {search_result.num_hits}")
        if search_result.fold_prediction:
            lines.append(f"Predicted fold: {search_result.fold_prediction}")
        if search_result.superfamily:
            lines.append(f"Predicted superfamily: {search_result.superfamily}")
        lines.append("")
        lines.append("TOP HITS:")
        lines.append("-" * 70)
        for i, hit in enumerate(search_result.hits):
            lines.append(f"\nHit {i + 1}:")
            lines.append(self.format_alignment_report(hit))
        lines.append("")
        lines.append("=" * 70)
        return "\n".join(lines)


def compute_structural_features(coords: np.ndarray) -> List[StructuralFeature]:
    features = []
    if len(coords) < 3:
        return features
    distances = np.sqrt(((coords[:, None] - coords) ** 2).sum(axis=-1))
    features.append(StructuralFeature(
        feature_type="distance_map",
        values=distances,
        description="Inter-residue C-alpha distance map"
    ))
    vectors = coords[1:] - coords[:-1]
    angles = np.zeros(len(vectors) - 1)
    for i in range(len(vectors) - 1):
        v1 = vectors[i]
        v2 = vectors[i + 1]
        cos_theta = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-8)
        angles[i] = np.arccos(np.clip(cos_theta, -1, 1))
    features.append(StructuralFeature(
        feature_type="backbone_angles",
        values=angles,
        description="Backbone pseudo-dihedral angles"
    ))
    radius = np.linalg.norm(coords - coords.mean(axis=0), axis=1)
    features.append(StructuralFeature(
        feature_type="radius_profile",
        values=radius,
        description="Distance from centroid for each residue"
    ))
    return features


def classify_fold(coords: np.ndarray) -> Optional[str]:
    if len(coords) < 10:
        return None
    centroid = coords.mean(axis=0)
    centered = coords - centroid
    u, s, vh = np.linalg.svd(centered)
    aspect_ratio = s[0] / max(s[-1], 1e-8)
    if aspect_ratio > 5.0:
        return "Elongated/filamentous"
    elif aspect_ratio < 1.5:
        return "Globular/compact"
    else:
        return "Intermediate"
