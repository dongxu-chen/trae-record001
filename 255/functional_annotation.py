import os
import re
import json
import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Union, Set


AMINO_ACIDS = "ACDEFGHIKLMNPQRSTVWY"


@dataclass
class ActiveSite:
    residues: List[int]
    residues_aa: List[str]
    score: float
    type: str
    description: str
    confidence: float
    catalytic_residues: List[int] = field(default_factory=list)
    binding_residues: List[int] = field(default_factory=list)


@dataclass
class BindingPocket:
    pocket_id: int
    residues: List[int]
    residues_aa: List[str]
    center: np.ndarray
    volume: float
    druggability: float
    hydrophobicity: float
    polarity: float
    confidence: float
    predicted_ligand_type: str = ""
    surface_area: float = 0.0
    depth: float = 0.0


@dataclass
class FunctionalAnnotation:
    active_sites: List[ActiveSite]
    binding_pockets: List[BindingPocket]
    domain_annotations: List[Dict]
    go_terms: List[Dict]
    ec_numbers: List[str]
    confidence: float
    summary: str
    protein_family: Optional[str] = None
    function_description: Optional[str] = None


ACTIVITY_MOTIFS = {
    "serine_protease": [
        {"pattern": "GDSGGP", "residues": [2, 5], "type": "catalytic_triad",
         "description": "Serine protease catalytic triad (Ser, His, Asp)"}
    ],
    "kinase": [
        {"pattern": "GXGXXG", "residues": [0, 2, 4], "type": "nucleotide_binding",
         "description": "Protein kinase ATP-binding loop (P-loop)"}
    ],
    "phosphatase": [
        {"pattern": "CX5R", "residues": [0, 6], "type": "catalytic",
         "description": "Protein tyrosine phosphatase signature motif"}
    ],
    "metalloprotease": [
        {"pattern": "HEXXH", "residues": [0, 3], "type": "metal_binding",
         "description": "Zinc metalloprotease HEXXH motif"}
    ],
}


BINDING_POOCKET_FEATURES = {
    "hydrophobic_residues": set("AILMFVYW"),
    "polar_residues": set("STNQ"),
    "charged_residues": set("DEKRH"),
    "catalytic_residues": set("HSCDE"),
}


def find_sequence_motifs(sequence: str) -> List[Dict]:
    motifs = []
    for family, patterns in ACTIVITY_MOTIFS.items():
        for motif_data in patterns:
            pattern = motif_data["pattern"]
            regex = pattern.replace("X", ".")
            for match in re.finditer(regex, sequence):
                start = match.start()
                motifs.append({
                    "family": family,
                    "type": motif_data["type"],
                    "pattern": pattern,
                    "start": start,
                    "end": start + len(pattern) - 1,
                    "matched_seq": sequence[start:start + len(pattern)],
                    "key_residues": [start + r for r in motif_data["residues"]],
                    "description": motif_data["description"],
                    "score": 0.9 if len(pattern) >= 5 else 0.7,
                })
    return motifs


def predict_active_sites(sequence: str, pdb_content: Optional[str] = None,
                         plddt: Optional[np.ndarray] = None) -> List[ActiveSite]:
    active_sites = []
    motifs = find_sequence_motifs(sequence)
    for motif in motifs:
        residues = sorted(set([motif["start"] + i for i in range(motif["end"] - motif["start"] + 1)]
                              + motif["key_residues"]))
        residues_aa = [sequence[i] for i in residues if i < len(sequence)]
        confidence = motif["score"]
        if plddt is not None:
            valid_plddts = [plddt[i] for i in residues if i < len(plddt)]
            if valid_plddts:
                confidence *= np.mean(valid_plddts) / 100.0
        active_sites.append(ActiveSite(
            residues=residues,
            residues_aa=residues_aa,
            score=motif["score"],
            type=motif["type"],
            description=motif["description"],
            confidence=min(1.0, confidence),
            catalytic_residues=motif["key_residues"],
            binding_residues=[r for r in residues if r not in motif["key_residues"]]
        ))
    if not active_sites:
        active_sites.append(ActiveSite(
            residues=[],
            residues_aa=[],
            score=0.3,
            type="predicted",
            description="No known motifs found; surface-exposed conserved residues predicted",
            confidence=0.3,
        ))
    return active_sites


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


def compute_surface_exposure(coords: np.ndarray, threshold: float = 10.0) -> np.ndarray:
    if len(coords) < 3:
        return np.zeros(len(coords), dtype=bool)
    dist_matrix = np.sqrt(((coords[:, None] - coords) ** 2).sum(axis=-1))
    neighbors = (dist_matrix < threshold).sum(axis=1)
    return neighbors < np.percentile(neighbors, 70)


def compute_pocket_properties(coords: np.ndarray, pocket_residues: List[int],
                             sequence: str) -> Dict:
    if len(pocket_residues) == 0 or len(coords) == 0:
        return {"volume": 0.0, "druggability": 0.0, "hydrophobicity": 0.0,
                "polarity": 0.0, "center": np.zeros(3), "surface_area": 0.0, "depth": 0.0}
    pocket_coords = coords[np.array(pocket_residues)]
    center = pocket_coords.mean(axis=0)
    volume = len(pocket_residues) * 15.0
    pocket_aas = [sequence[i] for i in pocket_residues if i < len(sequence)]
    if len(pocket_aas) == 0:
        return {"volume": volume, "druggability": 0.0, "hydrophobicity": 0.0,
                "polarity": 0.0, "center": center, "surface_area": 0.0, "depth": 0.0}
    hydrophobic_count = sum(1 for aa in pocket_aas if aa in BINDING_POOCKET_FEATURES["hydrophobic_residues"])
    polar_count = sum(1 for aa in pocket_aas if aa in BINDING_POOCKET_FEATURES["polar_residues"])
    charged_count = sum(1 for aa in pocket_aas if aa in BINDING_POOCKET_FEATURES["charged_residues"])
    total = len(pocket_aas)
    hydrophobicity = hydrophobic_count / total
    polarity = polar_count / total
    charged_ratio = charged_count / total
    druggability = 0.5 + (hydrophobicity - 0.3) * 0.5 + (polarity * 0.3)
    druggability = min(1.0, max(0.0, druggability))
    if len(coords) > 1:
        surface_area = len(pocket_residues) * 10.0
        all_dists = np.linalg.norm(coords - center, axis=1)
        depth = np.percentile(all_dists[pocket_residues], 50) if len(pocket_residues) > 0 else 0
    else:
        surface_area = 0.0
        depth = 0.0
    return {
        "volume": volume,
        "druggability": druggability,
        "hydrophobicity": hydrophobicity,
        "polarity": polarity,
        "center": center,
        "surface_area": surface_area,
        "depth": depth,
        "charged_ratio": charged_ratio,
    }


def predict_binding_pockets(sequence: str, pdb_content: str,
                           plddt: Optional[np.ndarray] = None) -> List[BindingPocket]:
    pockets = []
    coords = extract_calpha_coords(pdb_content)
    if len(coords) < 10:
        return pockets
    surface_mask = compute_surface_exposure(coords)
    surface_residues = np.where(surface_mask)[0]
    if len(surface_residues) < 5:
        return pockets
    visited = set()
    pocket_id = 0
    for start_res in surface_residues:
        if start_res in visited:
            continue
        cluster = [start_res]
        queue = [start_res]
        visited.add(start_res)
        while queue:
            current = queue.pop(0)
            for neighbor in surface_residues:
                if neighbor in visited:
                    continue
                dist = np.linalg.norm(coords[current] - coords[neighbor])
                if dist < 12.0:
                    cluster.append(neighbor)
                    queue.append(neighbor)
                    visited.add(neighbor)
        if 5 <= len(cluster) <= 50:
            props = compute_pocket_properties(coords, cluster, sequence)
            confidence = props["druggability"]
            if plddt is not None:
                valid_plddts = [plddt[i] for i in cluster if i < len(plddt)]
                if valid_plddts:
                    confidence *= np.mean(valid_plddts) / 100.0
            if props["druggability"] > 0.4:
                ligand_type = predict_ligand_type(sequence, cluster, props)
                pockets.append(BindingPocket(
                    pocket_id=pocket_id,
                    residues=sorted(cluster),
                    residues_aa=[sequence[i] for i in cluster if i < len(sequence)],
                    center=props["center"],
                    volume=props["volume"],
                    druggability=props["druggability"],
                    hydrophobicity=props["hydrophobicity"],
                    polarity=props["polarity"],
                    confidence=min(1.0, confidence),
                    predicted_ligand_type=ligand_type,
                    surface_area=props["surface_area"],
                    depth=props["depth"],
                ))
                pocket_id += 1
    pockets.sort(key=lambda p: p.druggability, reverse=True)
    return pockets[:5]


def predict_ligand_type(sequence: str, pocket_residues: List[int], props: Dict) -> str:
    pocket_aas = set(sequence[i] for i in pocket_residues if i < len(sequence))
    if props["hydrophobicity"] > 0.6:
        return "hydrophobic_ligand"
    elif props["polarity"] > 0.4:
        return "polar_ligand"
    elif props.get("charged_ratio", 0) > 0.3:
        return "charged_ligand"
    elif any(aa in pocket_aas for aa in "HSC"):
        return "cofactor_binding"
    else:
        return "small_molecule"


def predict_go_terms(sequence: str, active_sites: List[ActiveSite]) -> List[Dict]:
    go_terms = []
    for site in active_sites:
        if site.type == "catalytic_triad":
            go_terms.append({
                "id": "GO:0006508",
                "name": "proteolysis",
                "aspect": "biological_process",
                "evidence": "sequence_motif",
                "confidence": site.confidence
            })
            go_terms.append({
                "id": "GO:0004252",
                "name": "serine-type endopeptidase activity",
                "aspect": "molecular_function",
                "evidence": "sequence_motif",
                "confidence": site.confidence
            })
        elif site.type == "nucleotide_binding":
            go_terms.append({
                "id": "GO:0005524",
                "name": "ATP binding",
                "aspect": "molecular_function",
                "evidence": "sequence_motif",
                "confidence": site.confidence
            })
            go_terms.append({
                "id": "GO:0004672",
                "name": "protein kinase activity",
                "aspect": "molecular_function",
                "evidence": "sequence_motif",
                "confidence": site.confidence
            })
        elif site.type == "metal_binding":
            go_terms.append({
                "id": "GO:0008237",
                "name": "metallopeptidase activity",
                "aspect": "molecular_function",
                "evidence": "sequence_motif",
                "confidence": site.confidence
            })
            go_terms.append({
                "id": "GO:0008270",
                "name": "zinc ion binding",
                "aspect": "molecular_function",
                "evidence": "sequence_motif",
                "confidence": site.confidence
            })
    if not go_terms:
        go_terms.append({
            "id": "GO:0003674",
            "name": "molecular_function",
            "aspect": "molecular_function",
            "evidence": "predicted",
            "confidence": 0.3
        })
    return go_terms


def predict_ec_numbers(active_sites: List[ActiveSite]) -> List[str]:
    ec_numbers = []
    for site in active_sites:
        if site.type == "catalytic_triad":
            ec_numbers.append("3.4.21.-")
        elif site.type == "nucleotide_binding":
            ec_numbers.append("2.7.11.1")
        elif site.type == "metal_binding":
            ec_numbers.append("3.4.24.-")
    return ec_numbers


def predict_domains(sequence: str) -> List[Dict]:
    domains = []
    if len(sequence) < 50:
        return domains
    if "GDSGGP" in sequence:
        domains.append({
            "name": "Trypsin-like serine protease",
            "start": sequence.find("GDSGGP") - 20,
            "end": sequence.find("GDSGGP") + 20,
            "family": "Peptidase S1",
            "confidence": 0.85
        })
    if "GXGXXG" in sequence:
        start = sequence.find("GXGXXG".replace("X", "."))
        if start >= 0:
            domains.append({
                "name": "Protein kinase domain",
                "start": max(0, start - 30),
                "end": min(len(sequence), start + 30),
                "family": "Protein kinase superfamily",
                "confidence": 0.8
            })
    if not domains:
        segments = max(1, len(sequence) // 150)
        for i in range(segments):
            domains.append({
                "name": f"Predicted domain {i + 1}",
                "start": i * 150,
                "end": min((i + 1) * 150, len(sequence)),
                "family": "Unknown",
                "confidence": 0.5
            })
    return domains


def generate_function_summary(active_sites: List[ActiveSite],
                             binding_pockets: List[BindingPocket],
                             go_terms: List[Dict]) -> str:
    parts = []
    if active_sites and active_sites[0].residues:
        site = active_sites[0]
        parts.append(f"Predicted {site.type} site with {len(site.residues)} residues.")
    if binding_pockets:
        druggable = [p for p in binding_pockets if p.druggability > 0.6]
        parts.append(f"Found {len(binding_pockets)} binding pocket(s), "
                    f"{len(druggable)} with high druggability.")
    if go_terms:
        bp_terms = [g for g in go_terms if g["aspect"] == "biological_process"]
        if bp_terms:
            parts.append(f"Biological process: {bp_terms[0]['name']}.")
    return " ".join(parts) if parts else "No specific function predicted."


class FunctionalAnnotator:
    def __init__(self, config=None):
        self.config = config

    def annotate(self, sequence: str, pdb_content: str,
                 plddt: Optional[np.ndarray] = None) -> FunctionalAnnotation:
        active_sites = predict_active_sites(sequence, pdb_content, plddt)
        binding_pockets = predict_binding_pockets(sequence, pdb_content, plddt)
        go_terms = predict_go_terms(sequence, active_sites)
        ec_numbers = predict_ec_numbers(active_sites)
        domains = predict_domains(sequence)
        summary = generate_function_summary(active_sites, binding_pockets, go_terms)
        confidences = []
        if active_sites:
            confidences.extend([s.confidence for s in active_sites])
        if binding_pockets:
            confidences.extend([p.confidence for p in binding_pockets])
        overall_confidence = float(np.mean(confidences)) if confidences else 0.5
        protein_family = None
        if active_sites:
            site = active_sites[0]
            if site.type == "catalytic_triad":
                protein_family = "Serine protease"
            elif site.type == "nucleotide_binding":
                protein_family = "Protein kinase"
            elif site.type == "metal_binding":
                protein_family = "Metalloprotease"
        return FunctionalAnnotation(
            active_sites=active_sites,
            binding_pockets=binding_pockets,
            domain_annotations=domains,
            go_terms=go_terms,
            ec_numbers=ec_numbers,
            confidence=overall_confidence,
            summary=summary,
            protein_family=protein_family,
        )

    def format_report(self, annotation: FunctionalAnnotation) -> str:
        lines = []
        lines.append("=" * 70)
        lines.append("FUNCTIONAL ANNOTATION REPORT")
        lines.append("=" * 70)
        lines.append("")
        lines.append(f"Overall confidence: {annotation.confidence:.4f}")
        if annotation.protein_family:
            lines.append(f"Predicted protein family: {annotation.protein_family}")
        lines.append(f"Summary: {annotation.summary}")
        lines.append("")
        lines.append("ACTIVE SITES")
        lines.append("-" * 40)
        if annotation.active_sites:
            for i, site in enumerate(annotation.active_sites):
                lines.append(f"Site {i + 1} ({site.type}):")
                lines.append(f"  Residues: {site.residues[:10]}..."
                            if len(site.residues) > 10 else f"  Residues: {site.residues}")
                lines.append(f"  Amino acids: {''.join(site.residues_aa)}")
                lines.append(f"  Description: {site.description}")
                lines.append(f"  Confidence: {site.confidence:.4f}")
                if site.catalytic_residues:
                    lines.append(f"  Catalytic residues: {site.catalytic_residues}")
                lines.append("")
        else:
            lines.append("  No active sites predicted.")
            lines.append("")
        lines.append("BINDING POCKETS")
        lines.append("-" * 40)
        if annotation.binding_pockets:
            for i, pocket in enumerate(annotation.binding_pockets):
                lines.append(f"Pocket {i + 1}:")
                lines.append(f"  Residues: {len(pocket.residues)} residues")
                lines.append(f"  Volume: {pocket.volume:.1f} Å³")
                lines.append(f"  Druggability: {pocket.druggability:.4f}")
                lines.append(f"  Hydrophobicity: {pocket.hydrophobicity:.3f}")
                lines.append(f"  Polarity: {pocket.polarity:.3f}")
                lines.append(f"  Predicted ligand type: {pocket.predicted_ligand_type}")
                lines.append(f"  Confidence: {pocket.confidence:.4f}")
                lines.append("")
        else:
            lines.append("  No binding pockets predicted.")
            lines.append("")
        lines.append("DOMAIN ANNOTATIONS")
        lines.append("-" * 40)
        for domain in annotation.domain_annotations:
            lines.append(f"  {domain['name']}: residues {domain['start']}-{domain['end']} "
                        f"(family: {domain['family']}, confidence: {domain['confidence']:.2f})")
        lines.append("")
        lines.append("GO TERMS")
        lines.append("-" * 40)
        for go in annotation.go_terms:
            lines.append(f"  {go['id']}: {go['name']} ({go['aspect']}, conf: {go['confidence']:.2f})")
        lines.append("")
        if annotation.ec_numbers:
            lines.append("EC NUMBERS")
            lines.append("-" * 40)
            for ec in annotation.ec_numbers:
                lines.append(f"  {ec}")
            lines.append("")
        lines.append("=" * 70)
        return "\n".join(lines)
