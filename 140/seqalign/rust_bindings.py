"""
Rust-accelerated sequence alignment bindings.
Provides high-performance implementations of Needleman-Wunsch and Smith-Waterman algorithms
with SIMD optimizations and parallel processing.
"""

import sys
import os
from typing import List, Tuple, Optional

try:
    from . import seqalign_rs
except ImportError:
    try:
        import seqalign_rs
    except ImportError:
        seqalign_rs = None
        print("Warning: Rust bindings not available. Falling back to Python implementation.")


def has_rust() -> bool:
    """Check if Rust bindings are available."""
    return seqalign_rs is not None


class NeedlemanWunschRust:
    """
    Needleman-Wunsch global alignment (Rust implementation).
    
    Args:
        match_score: Score for matching characters (default: 2)
        mismatch_score: Score for mismatching characters (default: -1)
        gap_open: Penalty for opening a gap (default: -5)
        gap_extend: Penalty for extending a gap (default: -1)
        use_affine: Use affine gap penalty (default: True)
    
    Example:
        >>> nw = NeedlemanWunschRust(match_score=2, mismatch_score=-1, gap_open=-5)
        >>> result = nw.align("MVLSPADKTNVKAA", "MVSAPDKTNVKAA")
        >>> print(result.aligned_seq1, result.aligned_seq2, result.score)
    """
    
    def __init__(
        self,
        match_score: int = 2,
        mismatch_score: int = -1,
        gap_open: int = -5,
        gap_extend: int = -1,
        use_affine: bool = True,
    ):
        if seqalign_rs is None:
            raise ImportError("Rust bindings are not available. Please compile the Rust extension.")
        
        self._aligner = seqalign_rs.NeedlemanWunsch(
            match_score=match_score,
            mismatch_score=mismatch_score,
            gap_open=gap_open,
            gap_extend=gap_extend,
            use_affine=use_affine,
        )
    
    def align(self, seq1: str, seq2: str) -> 'AlignmentResult':
        """
        Perform global alignment between two sequences.
        
        Args:
            seq1: First sequence
            seq2: Second sequence
            
        Returns:
            AlignmentResult with aligned sequences and score
        """
        return self._aligner.align(seq1, seq2)


class SmithWatermanRust:
    """
    Smith-Waterman local alignment (Rust implementation).
    
    Args:
        match_score: Score for matching characters (default: 2)
        mismatch_score: Score for mismatching characters (default: -1)
        gap_open: Penalty for opening a gap (default: -5)
        gap_extend: Penalty for extending a gap (default: -1)
        use_affine: Use affine gap penalty (default: True)
    
    Example:
        >>> sw = SmithWatermanRust(match_score=2, mismatch_score=-1, gap_open=-5)
        >>> result = sw.align("MVLSPADKTNVKAA", "MVSAPDKTNVKAA")
        >>> print(result.aligned_seq1, result.aligned_seq2, result.score)
    """
    
    def __init__(
        self,
        match_score: int = 2,
        mismatch_score: int = -1,
        gap_open: int = -5,
        gap_extend: int = -1,
        use_affine: bool = True,
    ):
        if seqalign_rs is None:
            raise ImportError("Rust bindings are not available. Please compile the Rust extension.")
        
        self._aligner = seqalign_rs.SmithWaterman(
            match_score=match_score,
            mismatch_score=mismatch_score,
            gap_open=gap_open,
            gap_extend=gap_extend,
            use_affine=use_affine,
        )
    
    def align(self, seq1: str, seq2: str) -> 'AlignmentResult':
        """
        Perform local alignment between two sequences.
        
        Args:
            seq1: First sequence
            seq2: Second sequence
            
        Returns:
            AlignmentResult with aligned sequences and score
        """
        return self._aligner.align(seq1, seq2)


def parallel_align_all(
    sequences: List[str],
    reference: str,
    match_score: int = 2,
    mismatch_score: int = -1,
    gap_open: int = -5,
    gap_extend: int = -1,
    use_affine: bool = True,
    method: str = "global",
) -> List['AlignmentResult']:
    """
    Align multiple sequences against a reference in parallel using Rust.
    
    Args:
        sequences: List of query sequences
        reference: Reference sequence to align against
        match_score: Score for matching characters (default: 2)
        mismatch_score: Score for mismatching characters (default: -1)
        gap_open: Penalty for opening a gap (default: -5)
        gap_extend: Penalty for extending a gap (default: -1)
        use_affine: Use affine gap penalty (default: True)
        method: "global" for Needleman-Wunsch or "local" for Smith-Waterman (default: "global")
        
    Returns:
        List of AlignmentResult objects
        
    Example:
        >>> seqs = ["MVLSPADK", "MVSAPDUK", "MVLSPADT"]
        >>> results = parallel_align_all(seqs, "MVLSPADKT")
        >>> for res in results:
        ...     print(f"Score: {res.score}")
    """
    if seqalign_rs is None:
        raise ImportError("Rust bindings are not available. Please compile the Rust extension.")
    
    return seqalign_rs.rust_parallel_align_all(
        sequences,
        reference,
        match_score=match_score,
        mismatch_score=mismatch_score,
        gap_open=gap_open,
        gap_extend=gap_extend,
        use_affine=use_affine,
        method=method,
    )


def parallel_pairwise_scores(
    sequences: List[str],
    match_score: int = 2,
    mismatch_score: int = -1,
    gap_open: int = -5,
    gap_extend: int = -1,
    use_affine: bool = True,
) -> List[List[int]]:
    """
    Compute pairwise alignment scores for all sequence pairs in parallel.
    
    Args:
        sequences: List of sequences to compare
        match_score: Score for matching characters (default: 2)
        mismatch_score: Score for mismatching characters (default: -1)
        gap_open: Penalty for opening a gap (default: -5)
        gap_extend: Penalty for extending a gap (default: -1)
        use_affine: Use affine gap penalty (default: True)
        
    Returns:
        2D matrix of alignment scores
        
    Example:
        >>> seqs = ["MVLSPADK", "MVSAPDUK", "MVLSPADT"]
        >>> matrix = parallel_pairwise_scores(seqs)
        >>> for i, row in enumerate(matrix):
        ...     for j, score in enumerate(row):
        ...         print(f"Seq{i} vs Seq{j}: {score}")
    """
    if seqalign_rs is None:
        raise ImportError("Rust bindings are not available. Please compile the Rust extension.")
    
    return seqalign_rs.rust_parallel_pairwise_scores(
        sequences,
        match_score=match_score,
        mismatch_score=mismatch_score,
        gap_open=gap_open,
        gap_extend=gap_extend,
        use_affine=use_affine,
    )


class AlignmentResult:
    """
    Wrapper for alignment results (compatible with both Python and Rust implementations).
    
    Attributes:
        aligned_seq1: Aligned first sequence (with gaps)
        aligned_seq2: Aligned second sequence (with gaps)
        score: Alignment score
        start1: Start position in first sequence (0-based)
        end1: End position in first sequence (0-based, exclusive)
        start2: Start position in second sequence (0-based)
        end2: End position in second sequence (0-based, exclusive)
    """
    
    def __init__(
        self,
        aligned_seq1: str,
        aligned_seq2: str,
        score: int,
        start1: int = 0,
        end1: int = 0,
        start2: int = 0,
        end2: int = 0,
    ):
        self.aligned_seq1 = aligned_seq1
        self.aligned_seq2 = aligned_seq2
        self.score = score
        self.start1 = start1
        self.end1 = end1
        self.start2 = start2
        self.end2 = end2
    
    def __repr__(self) -> str:
        return f"AlignmentResult(score={self.score}, len={len(self.aligned_seq1)})"
    
    def print_alignment(self, line_width: int = 60) -> None:
        """Print alignment in formatted blocks."""
        n = len(self.aligned_seq1)
        for i in range(0, n, line_width):
            end = min(i + line_width, n)
            print(f"Seq1: {self.aligned_seq1[i:end]}")
            print(f"Seq2: {self.aligned_seq2[i:end]}")
            print()


__all__ = [
    'has_rust',
    'NeedlemanWunschRust',
    'SmithWatermanRust',
    'parallel_align_all',
    'parallel_pairwise_scores',
    'AlignmentResult',
]
