import sys
sys.path.insert(0, r'd:\Trae\project\record001\140')

print("Testing imports...")

try:
    from seqalign.needleman_wunsch import NeedlemanWunsch
    print("✓ NeedlemanWunsch imported successfully")
except Exception as e:
    print(f"✗ NeedlemanWunsch import failed: {e}")

try:
    from seqalign.smith_waterman import SmithWaterman
    print("✓ SmithWaterman imported successfully")
except Exception as e:
    print(f"✗ SmithWaterman import failed: {e}")

try:
    from seqalign.similarity_matrix import SimilarityMatrix
    print("✓ SimilarityMatrix imported successfully")
except Exception as e:
    print(f"✗ SimilarityMatrix import failed: {e}")

try:
    from seqalign.visualization import AlignmentVisualizer
    print("✓ AlignmentVisualizer imported successfully")
except Exception as e:
    print(f"✗ AlignmentVisualizer import failed: {e}")

print("\nTesting Needleman-Wunsch alignment...")
try:
    nw = NeedlemanWunsch(match=1, mismatch=-1, gap=-2)
    aligned1, aligned2, score = nw.align("HEAGAWGHEE", "PAWHEAE")
    print(f"✓ Alignment completed! Score: {score}")
    print(f"  Aligned 1: {aligned1}")
    print(f"  Aligned 2: {aligned2}")
except Exception as e:
    print(f"✗ Alignment failed: {e}")
    import traceback
    traceback.print_exc()

print("\nAll tests completed!")
