#!/usr/bin/env python3
"""
Example usage of Rust-accelerated sequence alignment.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 70)
print("RUST-ACCELERATED SEQUENCE ALIGNMENT EXAMPLE")
print("=" * 70)

try:
    import seqalign
    print(f"\nSeqAlign version: {seqalign.__version__}")
    print(f"Rust bindings available: {seqalign.has_rust()}")
except Exception as e:
    print(f"Error importing: {e}")
    sys.exit(1)

seq1 = "MVLSPADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHFDLSHGSAQVKGHG"
seq2 = "MVLSAADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHFDLSHGSAQVKGHG"

print(f"\nSequence 1: {seq1[:40]}...")
print(f"Sequence 2: {seq2[:40]}...")

if seqalign.has_rust():
    print("\n" + "-" * 70)
    print("1. Needleman-Wunsch Global Alignment (Rust)")
    print("-" * 70)
    
    nw = seqalign.NeedlemanWunschRust(
        match_score=2,
        mismatch_score=-1,
        gap_open=-5,
        gap_extend=-1,
        use_affine=True
    )
    result = nw.align(seq1, seq2)
    print(f"Alignment score: {result.score}")
    print(f"Aligned 1: {result.aligned_seq1}")
    print(f"Aligned 2: {result.aligned_seq2}")
    
    print("\n" + "-" * 70)
    print("2. Smith-Waterman Local Alignment (Rust)")
    print("-" * 70)
    
    sw = seqalign.SmithWatermanRust(
        match_score=2,
        mismatch_score=-1,
        gap_open=-5,
        gap_extend=-1,
        use_affine=True
    )
    result_sw = sw.align(seq1, seq2)
    print(f"Alignment score: {result_sw.score}")
    print(f"Position in seq1: {result_sw.start1}-{result_sw.end1}")
    print(f"Position in seq2: {result_sw.start2}-{result_sw.end2}")
    
    print("\n" + "-" * 70)
    print("3. Parallel Batch Alignment")
    print("-" * 70)
    
    sequences = [
        "MVLSPADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHFDLSHGSAQVKGHG",
        "MVLSAADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHFDLSHGSAQVKGHG",
        "MVLSPADKTNVKVVWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHFDLSHGSAQVKGHG",
        "MILSPADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHFDLSHGSAQVKGHG",
        "MVLSPADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHFDLSHGSAQVKGRA",
    ]
    reference = "MVLSPADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHFDLSHGSAQVKGHG"
    
    print(f"Aligning {len(sequences)} sequences against reference...")
    
    results = seqalign.parallel_align_all(
        sequences,
        reference,
        match_score=2,
        mismatch_score=-1,
        gap_open=-5,
        gap_extend=-1,
        use_affine=True,
        method="global"
    )
    
    for i, res in enumerate(results):
        print(f"  Seq{i}: score={res.score}")
    
    print("\n" + "-" * 70)
    print("4. Parallel Pairwise Similarity Matrix")
    print("-" * 70)
    
    matrix = seqalign.parallel_pairwise_scores(
        sequences[:4],
        match_score=2,
        mismatch_score=-1,
        gap_open=-5,
        gap_extend=-1,
        use_affine=True
    )
    
    print(f"Similarity matrix ({len(matrix)}x{len(matrix)}):")
    for i, row in enumerate(matrix):
        print(f"  Seq{i}: {row}")
    
    print("\n" + "=" * 70)
    print("All Rust operations completed successfully!")
    print("=" * 70)
    
else:
    print("\n" + "!" * 70)
    print("Rust bindings not available.")
    print("To build Rust extensions:")
    print("  1. Install Rust: https://rustup.rs/")
    print("  2. pip install maturin")
    print("  3. maturin develop --release")
    print("!" * 70)
