#!/usr/bin/env python3
"""
Performance comparison between Python and Rust implementations.
Tests Needleman-Wunsch and Smith-Waterman algorithms with various sequence lengths.
"""

import sys
import os
import time
import random
import statistics

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def generate_random_sequence(length: int, alphabet: str = "ACDEFGHIKLMNPQRSTVWY") -> str:
    """Generate a random protein sequence."""
    return ''.join(random.choice(alphabet) for _ in range(length))

def generate_many_sequences(count: int, length: int) -> list:
    """Generate many random sequences."""
    return [generate_random_sequence(length) for _ in range(count)]

def test_single_alignment():
    """Test single pairwise alignment performance."""
    print("=" * 70)
    print("SINGLE PAIRWISE ALIGNMENT PERFORMANCE")
    print("=" * 70)
    
    seq_lengths = [50, 100, 200, 500]
    
    for seq_len in seq_lengths:
        seq1 = generate_random_sequence(seq_len)
        seq2 = generate_random_sequence(seq_len)
        
        print(f"\nSequence length: {seq_len}")
        
        # Test Python Needleman-Wunsch
        from seqalign import NeedlemanWunsch
        nw_py = NeedlemanWunsch(match=2, mismatch=-1, gap_open=-5, gap_extend=-1, use_affine=True)
        start = time.perf_counter()
        result_py = nw_py.align(seq1, seq2)
        time_py = time.perf_counter() - start
        print(f"  Python NW: {time_py*1000:.2f} ms, score={result_py.score}")
        
        # Test Rust Needleman-Wunsch (if available)
        try:
            from seqalign import NeedlemanWunschRust
            nw_rs = NeedlemanWunschRust(match_score=2, mismatch_score=-1, gap_open=-5, gap_extend=-1, use_affine=True)
            start = time.perf_counter()
            result_rs = nw_rs.align(seq1, seq2)
            time_rs = time.perf_counter() - start
            speedup = time_py / time_rs if time_rs > 0 else float('inf')
            print(f"  Rust   NW: {time_rs*1000:.2f} ms, score={result_rs.score}, speedup={speedup:.1f}x")
        except Exception as e:
            print(f"  Rust   NW: Not available ({e})")
        
        # Test Python Smith-Waterman
        from seqalign import SmithWaterman
        sw_py = SmithWaterman(match=2, mismatch=-1, gap_open=-5, gap_extend=-1, use_affine=True)
        start = time.perf_counter()
        result_sw_py = sw_py.align(seq1, seq2)
        time_sw_py = time.perf_counter() - start
        print(f"  Python SW: {time_sw_py*1000:.2f} ms, score={result_sw_py.score}")
        
        # Test Rust Smith-Waterman (if available)
        try:
            from seqalign import SmithWatermanRust
            sw_rs = SmithWatermanRust(match_score=2, mismatch_score=-1, gap_open=-5, gap_extend=-1, use_affine=True)
            start = time.perf_counter()
            result_sw_rs = sw_rs.align(seq1, seq2)
            time_sw_rs = time.perf_counter() - start
            speedup_sw = time_sw_py / time_sw_rs if time_sw_rs > 0 else float('inf')
            print(f"  Rust   SW: {time_sw_rs*1000:.2f} ms, score={result_sw_rs.score}, speedup={speedup_sw:.1f}x")
        except Exception as e:
            print(f"  Rust   SW: Not available ({e})")

def test_parallel_alignment():
    """Test parallel alignment performance."""
    print("\n" + "=" * 70)
    print("PARALLEL ALIGNMENT PERFORMANCE")
    print("=" * 70)
    
    seq_count = 50
    seq_length = 200
    reference = generate_random_sequence(seq_length)
    sequences = generate_many_sequences(seq_count, seq_length)
    
    print(f"\nAligning {seq_count} sequences of length {seq_length} against reference")
    
    # Sequential Python
    from seqalign import NeedlemanWunsch
    nw_py = NeedlemanWunsch(match=2, mismatch=-1, gap_open=-5, gap_extend=-1, use_affine=True)
    start = time.perf_counter()
    results_py = [nw_py.align(seq, reference) for seq in sequences]
    time_seq = time.perf_counter() - start
    scores_py = [r.score for r in results_py]
    print(f"  Sequential Python: {time_seq:.3f} s, avg_score={statistics.mean(scores_py):.1f}")
    
    # Parallel Rust (if available)
    try:
        from seqalign import parallel_align_all
        start = time.perf_counter()
        results_rs = parallel_align_all(sequences, reference, method="global")
        time_par = time.perf_counter() - start
        scores_rs = [r.score for r in results_rs]
        speedup = time_seq / time_par if time_par > 0 else float('inf')
        print(f"  Parallel Rust:    {time_par:.3f} s, avg_score={statistics.mean(scores_rs):.1f}, speedup={speedup:.1f}x")
    except Exception as e:
        print(f"  Parallel Rust:    Not available ({e})")

def test_pairwise_matrix():
    """Test pairwise similarity matrix computation."""
    print("\n" + "=" * 70)
    print("PAIRWISE SIMILARITY MATRIX")
    print("=" * 70)
    
    seq_count = 20
    seq_length = 150
    sequences = generate_many_sequences(seq_count, seq_length)
    
    print(f"\nComputing {seq_count}x{seq_count} pairwise matrix ({seq_count*seq_count} alignments)")
    
    # Sequential Python
    from seqalign import NeedlemanWunsch
    nw_py = NeedlemanWunsch(match=2, mismatch=-1, gap_open=-5, gap_extend=-1, use_affine=True)
    start = time.perf_counter()
    matrix_py = []
    for i in range(seq_count):
        row = []
        for j in range(seq_count):
            if i == j:
                row.append(0)
            else:
                row.append(nw_py.align(sequences[i], sequences[j]).score)
        matrix_py.append(row)
    time_seq = time.perf_counter() - start
    print(f"  Sequential Python: {time_seq:.3f} s")
    
    # Parallel Rust (if available)
    try:
        from seqalign import parallel_pairwise_scores
        start = time.perf_counter()
        matrix_rs = parallel_pairwise_scores(
            sequences, match_score=2, mismatch_score=-1, gap_open=-5, gap_extend=-1, use_affine=True
        )
        time_par = time.perf_counter() - start
        speedup = time_seq / time_par if time_par > 0 else float('inf')
        print(f"  Parallel Rust:    {time_par:.3f} s, speedup={speedup:.1f}x")
    except Exception as e:
        print(f"  Parallel Rust:    Not available ({e})")

def verify_correctness():
    """Verify that Rust and Python implementations produce the same results."""
    print("\n" + "=" * 70)
    print("CORRECTNESS VERIFICATION")
    print("=" * 70)
    
    print("\nGenerating test sequences...")
    
    test_cases = [
        ("MVLSPADKTNVKAAWGKVGA", "MVLSAADKTNVKAVWGKVGA"),
        ("ACGTACGTACGT", "ACGTTACGTAACGT"),
        ("AAAAA", "AAATAA"),
    ]
    
    all_ok = True
    
    for seq1, seq2 in test_cases:
        print(f"\nTesting: {seq1[:20]}... vs {seq2[:20]}...")
        
        # Needleman-Wunsch
        try:
            from seqalign import NeedlemanWunsch, NeedlemanWunschRust
            nw_py = NeedlemanWunsch(match=2, mismatch=-1, gap_open=-5, gap_extend=-1, use_affine=True)
            nw_rs = NeedlemanWunschRust(match_score=2, mismatch_score=-1, gap_open=-5, gap_extend=-1, use_affine=True)
            res_py = nw_py.align(seq1, seq2)
            res_rs = nw_rs.align(seq1, seq2)
            
            if res_py.score == res_rs.score:
                print(f"  NW Score match: {res_py.score} ✓")
            else:
                print(f"  NW Score mismatch: Python={res_py.score}, Rust={res_rs.score} ✗")
                all_ok = False
                
        except Exception as e:
            print(f"  NW Rust not available: {e}")
        
        # Smith-Waterman
        try:
            from seqalign import SmithWaterman, SmithWatermanRust
            sw_py = SmithWaterman(match=2, mismatch=-1, gap_open=-5, gap_extend=-1, use_affine=True)
            sw_rs = SmithWatermanRust(match_score=2, mismatch_score=-1, gap_open=-5, gap_extend=-1, use_affine=True)
            res_sw_py = sw_py.align(seq1, seq2)
            res_sw_rs = sw_rs.align(seq1, seq2)
            
            if res_sw_py.score == res_sw_rs.score:
                print(f"  SW Score match: {res_sw_py.score} ✓")
            else:
                print(f"  SW Score mismatch: Python={res_sw_py.score}, Rust={res_sw_rs.score} ✗")
                all_ok = False
                
        except Exception as e:
            print(f"  SW Rust not available: {e}")
    
    print(f"\nOverall correctness: {'PASSED' if all_ok else 'FAILED'}")
    return all_ok

def main():
    print("\n" + "#" * 70)
    print("#" + " " * 68 + "#")
    print("#" + " " * 10 + "SEQUENCE ALIGNMENT PERFORMANCE COMPARISON" + " " * 21 + "#")
    print("#" + " " * 15 + "Python vs Rust Implementations" + " " * 28 + "#")
    print("#" + " " * 68 + "#")
    print("#" * 70 + "\n")
    
    # Set random seed for reproducibility
    random.seed(42)
    
    # Run tests
    try:
        test_single_alignment()
        test_parallel_alignment()
        test_pairwise_matrix()
        verify_correctness()
        
        print("\n" + "=" * 70)
        print("ALL TESTS COMPLETED")
        print("=" * 70)
        
        print("\nTo build the Rust extension:")
        print("  1. Install Rust: https://rustup.rs/")
        print("  2. Install maturin: pip install maturin")
        print("  3. Build: maturin develop --release")
        
    except KeyboardInterrupt:
        print("\nTests interrupted by user.")
    except Exception as e:
        print(f"\nError during tests: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
