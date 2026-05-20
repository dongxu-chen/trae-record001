"""
Sequence Alignment Toolkit v3.0
Biological sequence alignment with Python and Rust acceleration.

Features:
- Needleman-Wunsch global alignment (Python + Rust implementations)
- Smith-Waterman local alignment (Python + Rust implementations)
- SIMD-accelerated alignment computation (Rust)
- Multi-threaded parallel sequence alignment (Rust)
- Similarity matrix computation (enforced symmetry)
- Sequence Logo and heatmap visualization
- BLAST database search with seed extension
- ClustalW progressive multiple alignment
- Neighbor-Joining phylogenetic tree construction
- Colorful PDF report generation
"""

from .needleman_wunsch import NeedlemanWunsch
from .smith_waterman import SmithWaterman
from .similarity_matrix import SimilarityMatrix
from .visualization import AlignmentVisualizer
from .blast import LocalBLAST
from .multiple_alignment import ClustalW, ProgressiveMSA
from .phylogenetic_tree import PhylogeneticTree, DistanceCalculator, PhylogeneticAnalysis
from .report_generator import AlignmentReport, FastaWriter

from .rust_bindings import (
    has_rust,
    NeedlemanWunschRust,
    SmithWatermanRust,
    parallel_align_all,
    parallel_pairwise_scores,
)

__version__ = "3.0.0"
__all__ = [
    "NeedlemanWunsch", 
    "SmithWaterman", 
    "SimilarityMatrix", 
    "AlignmentVisualizer",
    "LocalBLAST",
    "ClustalW",
    "ProgressiveMSA",
    "PhylogeneticTree",
    "DistanceCalculator",
    "PhylogeneticAnalysis",
    "AlignmentReport",
    "FastaWriter",
    "has_rust",
    "NeedlemanWunschRust",
    "SmithWatermanRust",
    "parallel_align_all",
    "parallel_pairwise_scores",
]
