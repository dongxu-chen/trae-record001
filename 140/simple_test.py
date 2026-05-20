import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("Testing imports...")

try:
    from seqalign.needleman_wunsch import NeedlemanWunsch
    print("✓ NeedlemanWunsch imported successfully")
except Exception as e:
    print(f"✗ NeedlemanWunsch import failed: {e}")
    import traceback
    traceback.print_exc()

try:
    from seqalign.smith_waterman import SmithWaterman
    print("✓ SmithWaterman imported successfully")
except Exception as e:
    print(f"✗ SmithWaterman import failed: {e}")
    import traceback
    traceback.print_exc()

try:
    from seqalign.similarity_matrix import SimilarityMatrix
    print("✓ SimilarityMatrix imported successfully")
except Exception as e:
    print(f"✗ SimilarityMatrix import failed: {e}")
    import traceback
    traceback.print_exc()

try:
    from seqalign.visualization import AlignmentVisualizer
    print("✓ AlignmentVisualizer imported successfully")
except Exception as e:
    print(f"✗ AlignmentVisualizer import failed: {e}")
    import traceback
    traceback.print_exc()

print("\nTesting alignment algorithms...")

try:
    nw = NeedlemanWunsch(match=2, mismatch=-1, gap_open=-2, use_affine=True, gap_extend=-0.5)
    aligned1, aligned2, score = nw.align("HEAGAWGHEE", "PAWHEAE")
    print(f"✓ Affine Needleman-Wunsch completed successfully")
    print(f"  Score: {score}")
    print(f"  Aligned: {aligned1} / {aligned2}")
except Exception as e:
    print(f"✗ Affine Needleman-Wunsch failed: {e}")
    import traceback
    traceback.print_exc()

try:
    nw_banded = NeedlemanWunsch(match=2, mismatch=-1, gap_open=-2, band_width=5)
    aligned1, aligned2, score = nw_banded.align("HEAGAWGHEE", "PAWHEAE")
    print(f"✓ Banded Needleman-Wunsch completed successfully")
    print(f"  Score: {score}")
    print(f"  Aligned: {aligned1} / {aligned2}")
except Exception as e:
    print(f"✗ Banded Needleman-Wunsch failed: {e}")
    import traceback
    traceback.print_exc()

try:
    sw = SmithWaterman(match=2, mismatch=-1, gap_open=-2, use_affine=True, gap_extend=-0.5)
    aligned1, aligned2, score = sw.align("HEAGAWGHEE", "PAWHEAE")
    print(f"✓ Affine Smith-Waterman completed successfully")
    print(f"  Score: {score}")
    print(f"  Aligned: {aligned1} / {aligned2}")
except Exception as e:
    print(f"✗ Affine Smith-Waterman failed: {e}")
    import traceback
    traceback.print_exc()

try:
    sw_banded = SmithWaterman(match=2, mismatch=-1, gap_open=-2, band_width=5)
    aligned1, aligned2, score = sw_banded.align("HEAGAWGHEE", "PAWHEAE")
    print(f"✓ Banded Smith-Waterman completed successfully")
    print(f"  Score: {score}")
    print(f"  Aligned: {aligned1} / {aligned2}")
except Exception as e:
    print(f"✗ Banded Smith-Waterman failed: {e}")
    import traceback
    traceback.print_exc()

print("\nTesting similarity matrix symmetry...")

try:
    sequences = ["MVLSPADKTNVKAAW", "MVLSAADKTNVKAAW", "MVLSPADKTNVKVVW"]
    sim = SimilarityMatrix(alignment_method="global", enforce_symmetric=True,
                            match=1, mismatch=-1, gap_open=-2)
    matrix = sim.compute_matrix(sequences)
    print(f"✓ Symmetric similarity matrix computed")
    print(f"  Is symmetric: {sim.is_symmetric()}")
    print(f"  Matrix shape: {matrix.shape}")
except Exception as e:
    print(f"✗ Symmetric similarity matrix failed: {e}")
    import traceback
    traceback.print_exc()

print("\nAll tests completed!")
