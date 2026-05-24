import os
import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


@dataclass
class ResidueConfidence:
    index: int
    amino_acid: str
    plddt: float
    quality: str
    pae_local: Optional[float] = None


@dataclass
class ConfidenceReport:
    mean_plddt: float
    median_plddt: float
    min_plddt: float
    max_plddt: float
    plddt_by_residue: np.ndarray
    quality_regions: List[Dict[str, int]]
    overall_quality: str
    plddt_distribution: Dict[str, float]
    residue_confidence: List[ResidueConfidence] = field(default_factory=list)
    sequence: Optional[str] = None
    pae_stats: Optional[Dict[str, float]] = None
    ptm_score: Optional[float] = None
    iptm_score: Optional[float] = None


class ConfidenceEvaluator:
    def __init__(self, config=None):
        self.config = config
        self._quality_thresholds = {
            "very_high": 90,
            "high": 70,
            "moderate": 50,
            "low": 0,
        }

    def evaluate(self, plddt: np.ndarray, pae: Optional[np.ndarray] = None,
                ptm: Optional[float] = None, iptm: Optional[float] = None,
                sequence: Optional[str] = None) -> ConfidenceReport:
        plddt = np.asarray(plddt).flatten()
        if plddt.size == 0:
            raise ValueError("pLDDT array is empty")
        L = len(plddt)
        if sequence is not None:
            sequence = sequence.upper()
            if len(sequence) < L:
                sequence = sequence + 'X' * (L - len(sequence))
            sequence = sequence[:L]
        stats = self._compute_basic_stats(plddt)
        distribution = self._compute_distribution(plddt)
        regions = self._find_quality_regions(plddt)
        overall_quality = self._rate_overall_quality(stats["mean"])
        pae_stats = self._compute_pae_stats(pae) if pae is not None else None
        residue_confidence = self._build_residue_confidence(plddt, pae, sequence)
        return ConfidenceReport(
            mean_plddt=stats["mean"],
            median_plddt=stats["median"],
            min_plddt=stats["min"],
            max_plddt=stats["max"],
            plddt_by_residue=plddt,
            quality_regions=regions,
            overall_quality=overall_quality,
            plddt_distribution=distribution,
            residue_confidence=residue_confidence,
            sequence=sequence,
            pae_stats=pae_stats,
            ptm_score=ptm,
            iptm_score=iptm,
        )

    def _build_residue_confidence(self, plddt: np.ndarray, pae: Optional[np.ndarray],
                                 sequence: Optional[str]) -> List[ResidueConfidence]:
        residues = []
        L = len(plddt)
        for i in range(L):
            aa = sequence[i] if sequence and i < len(sequence) else 'X'
            quality = self._get_quality_label(plddt[i])
            pae_local = None
            if pae is not None and pae.ndim == 2 and i < pae.shape[0]:
                pae_local = float(pae[i, i]) if i < pae.shape[1] else None
            residues.append(ResidueConfidence(
                index=i,
                amino_acid=aa,
                plddt=float(plddt[i]),
                quality=quality,
                pae_local=pae_local,
            ))
        return residues

    def format_residue_table(self, report: ConfidenceReport,
                            max_rows: Optional[int] = 100) -> str:
        if not report.residue_confidence:
            return "No residue-level confidence data available."
        residues = report.residue_confidence
        if max_rows and len(residues) > max_rows:
            residues = residues[:max_rows]
            note = f"\n... (showing first {max_rows} of {len(report.residue_confidence)} residues)"
        else:
            note = ""
        lines = []
        lines.append("=" * 80)
        lines.append(f"{'Idx':>5} {'AA':>3} {'pLDDT':>8} {'Quality':>12} {'Local PAE':>12}")
        lines.append("-" * 80)
        for res in residues:
            pae_str = f"{res.pae_local:>12.2f}" if res.pae_local is not None else "         N/A"
            lines.append(f"{res.index:>5d} {res.amino_acid:>3} {res.plddt:>8.2f} {res.quality:>12} {pae_str}")
        lines.append("=" * 80)
        return "\n".join(lines) + note

    def get_low_confidence_residues(self, report: ConfidenceReport,
                                   threshold: float = 70.0) -> List[ResidueConfidence]:
        return [r for r in report.residue_confidence if r.plddt < threshold]

    def get_high_confidence_residues(self, report: ConfidenceReport,
                                    threshold: float = 90.0) -> List[ResidueConfidence]:
        return [r for r in report.residue_confidence if r.plddt >= threshold]

    def format_quality_summary(self, report: ConfidenceReport) -> str:
        lines = []
        lines.append("\n" + "=" * 60)
        lines.append("RESIDUE-LEVEL CONFIDENCE SUMMARY")
        lines.append("=" * 60)
        lines.append(f"\nSequence length: {len(report.plddt_by_residue)} residues")
        lines.append(f"Mean pLDDT: {report.mean_plddt:.2f}")
        lines.append(f"Overall quality: {report.overall_quality}")
        lines.append("\npLDDT Distribution:")
        for key, value in report.plddt_distribution.items():
            count = int(value * len(report.plddt_by_residue))
            lines.append(f"  {key:12s}: {count:>5d} residues ({value * 100:6.2f}%)")
        low_conf = self.get_low_confidence_residues(report, 70.0)
        if low_conf:
            lines.append(f"\nLow confidence regions (<70 pLDDT): {len(low_conf)} residues")
            if len(low_conf) <= 20:
                for res in low_conf:
                    lines.append(f"  - {res.amino_acid}{res.index + 1}: pLDDT={res.plddt:.2f}")
            else:
                lines.append(f"  (too many to list, use get_low_confidence_residues())")
        high_conf = self.get_high_confidence_residues(report, 90.0)
        if high_conf:
            lines.append(f"\nHigh confidence regions (≥90 pLDDT): {len(high_conf)} residues")
        return "\n".join(lines)

    def _compute_basic_stats(self, plddt: np.ndarray) -> Dict[str, float]:
        return {
            "mean": float(np.mean(plddt)),
            "median": float(np.median(plddt)),
            "min": float(np.min(plddt)),
            "max": float(np.max(plddt)),
            "std": float(np.std(plddt)),
        }

    def _compute_distribution(self, plddt: np.ndarray) -> Dict[str, float]:
        total = len(plddt)
        if total == 0:
            return {k: 0.0 for k in self._quality_thresholds}
        dist = {}
        dist["very_high"] = float((plddt >= 90).sum() / total)
        dist["high"] = float(((plddt >= 70) & (plddt < 90)).sum() / total)
        dist["moderate"] = float(((plddt >= 50) & (plddt < 70)).sum() / total)
        dist["low"] = float((plddt < 50).sum() / total)
        return dist

    def _find_quality_regions(self, plddt: np.ndarray) -> List[Dict[str, int]]:
        regions = []
        L = len(plddt)
        if L == 0:
            return regions
        current_quality = self._get_quality_label(plddt[0])
        start = 0
        for i in range(1, L):
            quality = self._get_quality_label(plddt[i])
            if quality != current_quality:
                regions.append({
                    "start": start,
                    "end": i - 1,
                    "length": i - start,
                    "quality": current_quality,
                    "mean_plddt": float(np.mean(plddt[start:i])),
                })
                current_quality = quality
                start = i
        regions.append({
            "start": start,
            "end": L - 1,
            "length": L - start,
            "quality": current_quality,
            "mean_plddt": float(np.mean(plddt[start:])),
        })
        return regions

    def _get_quality_label(self, plddt_value: float) -> str:
        if plddt_value >= 90:
            return "very_high"
        elif plddt_value >= 70:
            return "high"
        elif plddt_value >= 50:
            return "moderate"
        else:
            return "low"

    def _rate_overall_quality(self, mean_plddt: float) -> str:
        if mean_plddt >= 90:
            return "Very High"
        elif mean_plddt >= 70:
            return "High"
        elif mean_plddt >= 50:
            return "Moderate"
        else:
            return "Low"

    def _compute_pae_stats(self, pae: np.ndarray) -> Dict[str, float]:
        pae = np.asarray(pae)
        if pae.ndim == 1:
            pae = pae.reshape(int(np.sqrt(len(pae))), -1)
        L = pae.shape[0]
        diag = np.diag(pae)
        upper_tri = pae[np.triu_indices(L, k=1)]
        lower_tri = pae[np.tril_indices(L, k=-1)]
        return {
            "mean": float(np.mean(pae)),
            "median": float(np.median(pae)),
            "min": float(np.min(pae)),
            "max": float(np.max(pae)),
            "std": float(np.std(pae)),
            "diag_mean": float(np.mean(diag)),
            "off_diag_mean": float(np.mean(np.concatenate([upper_tri, lower_tri]))),
        }

    def plot_plddt(self, report: ConfidenceReport, output_path: str,
                  sequence: Optional[str] = None) -> str:
        fig, axes = plt.subplots(2, 1, figsize=(12, 8),
                                gridspec_kw={'height_ratios': [3, 1]})
        plddt = report.plddt_by_residue
        x = np.arange(len(plddt))
        ax1 = axes[0]
        colors = []
        for val in plddt:
            if val >= 90:
                colors.append('#0053D6')
            elif val >= 70:
                colors.append('#65CBF3')
            elif val >= 50:
                colors.append('#FFDB13')
            else:
                colors.append('#FF7D45')
        ax1.bar(x, plddt, color=colors, width=1.0, edgecolor='none')
        ax1.axhline(y=90, color='gray', linestyle='--', alpha=0.7, label='pLDDT ≥ 90')
        ax1.axhline(y=70, color='gray', linestyle=':', alpha=0.7, label='pLDDT ≥ 70')
        ax1.set_xlabel('Residue Index', fontsize=12)
        ax1.set_ylabel('pLDDT Score', fontsize=12)
        ax1.set_title(f'Per-Residue Confidence (Mean pLDDT: {report.mean_plddt:.2f})',
                     fontsize=14, fontweight='bold')
        ax1.set_ylim(0, 100)
        ax1.legend(loc='upper right')
        ax1.grid(axis='y', alpha=0.3)
        ax2 = axes[1]
        quality_colors = {
            'very_high': '#0053D6',
            'high': '#65CBF3',
            'moderate': '#FFDB13',
            'low': '#FF7D45',
        }
        current_pos = 0
        for region in report.quality_regions:
            ax2.barh(0, region['length'], left=current_pos,
                    color=quality_colors[region['quality']], edgecolor='white')
            current_pos += region['length']
        ax2.set_xlim(0, len(plddt))
        ax2.set_yticks([])
        ax2.set_xlabel('Quality Regions', fontsize=12)
        legend_elements = [
            plt.Rectangle((0, 0), 1, 1, color='#0053D6', label='Very High (≥90)'),
            plt.Rectangle((0, 0), 1, 1, color='#65CBF3', label='High (70-90)'),
            plt.Rectangle((0, 0), 1, 1, color='#FFDB13', label='Moderate (50-70)'),
            plt.Rectangle((0, 0), 1, 1, color='#FF7D45', label='Low (<50)'),
        ]
        ax2.legend(handles=legend_elements, loc='upper center',
                  bbox_to_anchor=(0.5, -0.2), ncol=4)
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close(fig)
        return output_path

    def plot_pae(self, pae: np.ndarray, output_path: str) -> str:
        fig, ax = plt.subplots(figsize=(10, 8))
        pae = np.asarray(pae)
        if pae.ndim == 1:
            pae = pae.reshape(int(np.sqrt(len(pae))), -1)
        im = ax.imshow(pae, cmap='viridis_r', vmin=0, vmax=30,
                      interpolation='nearest')
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label('Predicted Aligned Error (Å)', fontsize=12)
        ax.set_xlabel('Residue Index', fontsize=12)
        ax.set_ylabel('Residue Index', fontsize=12)
        ax.set_title('Predicted Aligned Error (PAE) Matrix', fontsize=14, fontweight='bold')
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close(fig)
        return output_path

    def generate_report(self, report: ConfidenceReport, output_path: str,
                       include_residue_table: bool = True,
                       max_residue_rows: int = 50) -> str:
        lines = []
        lines.append("=" * 80)
        lines.append("PROTEIN STRUCTURE CONFIDENCE REPORT")
        lines.append("=" * 80)
        lines.append("")
        lines.append("OVERALL METRICS")
        lines.append("-" * 40)
        lines.append(f"Overall Quality: {report.overall_quality}")
        lines.append(f"Mean pLDDT:     {report.mean_plddt:.2f}")
        lines.append(f"Median pLDDT:   {report.median_plddt:.2f}")
        lines.append(f"Min pLDDT:      {report.min_plddt:.2f}")
        lines.append(f"Max pLDDT:      {report.max_plddt:.2f}")
        lines.append("")
        lines.append("pLDDT DISTRIBUTION")
        lines.append("-" * 40)
        for key, value in report.plddt_distribution.items():
            count = int(value * len(report.plddt_by_residue))
            lines.append(f"  {key:12s}: {count:>5d} residues ({value * 100:6.2f}%)")
        lines.append("")
        if report.ptm_score is not None:
            lines.append(f"pTM Score:      {report.ptm_score:.4f}")
        if report.iptm_score is not None:
            lines.append(f"ipTM Score:     {report.iptm_score:.4f}")
        lines.append("")
        lines.append("QUALITY REGIONS")
        lines.append("-" * 40)
        for i, region in enumerate(report.quality_regions):
            lines.append(f"  Region {i + 1:2d}: residues {region['start']:>4d}-{region['end']:>4d} "
                        f"(length {region['length']:>4d}), "
                        f"quality={region['quality']:10s}, "
                        f"mean_pLDDT={region['mean_plddt']:.2f}")
        lines.append("")
        if report.pae_stats is not None:
            lines.append("PAE STATISTICS")
            lines.append("-" * 40)
            for key, value in report.pae_stats.items():
                lines.append(f"  {key:15s}: {value:.4f}")
            lines.append("")
        if include_residue_table and report.residue_confidence:
            lines.append("RESIDUE-LEVEL CONFIDENCE")
            lines.append("-" * 80)
            lines.append(self.format_residue_table(report, max_rows=max_residue_rows))
            lines.append("")
            low_conf = self.get_low_confidence_residues(report, 70.0)
            if low_conf:
                lines.append(f"LOW CONFIDENCE RESIDUES (<70 pLDDT): {len(low_conf)} total")
                lines.append("-" * 40)
                for res in low_conf[:20]:
                    lines.append(f"  {res.amino_acid}{res.index + 1:>4d}: pLDDT={res.plddt:.2f}")
                if len(low_conf) > 20:
                    lines.append(f"  ... and {len(low_conf) - 20} more")
                lines.append("")
        lines.append("=" * 80)
        with open(output_path, 'w') as f:
            f.write("\n".join(lines))
        return output_path


def compute_plddt_stats(plddt: np.ndarray) -> Dict[str, float]:
    return {
        "mean": float(np.mean(plddt)),
        "median": float(np.median(plddt)),
        "min": float(np.min(plddt)),
        "max": float(np.max(plddt)),
        "std": float(np.std(plddt)),
        "pct_gt_70": float((plddt > 70).mean() * 100),
        "pct_gt_90": float((plddt > 90).mean() * 100),
    }


def interpret_plddt(mean_plddt: float) -> Dict[str, str]:
    if mean_plddt >= 90:
        quality = "Very high"
        description = "Model backbone is highly accurate. Good for docking studies."
    elif mean_plddt >= 70:
        quality = "High"
        description = "Model backbone is generally accurate. Good for most analyses."
    elif mean_plddt >= 50:
        quality = "Moderate"
        description = "Model has some errors. Use with caution for detailed analysis."
    else:
        quality = "Low"
        description = "Model quality is low. Should be interpreted with great caution."
    return {"quality": quality, "description": description}
