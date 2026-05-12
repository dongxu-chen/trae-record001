from seq_io import Sequence, write_fasta, read_fasta
from scoring import ScoringMatrix
from align import smith_waterman, is_gpu_available, get_backend_info
from output import alignment_to_sam, generate_sam_header, print_alignment
import tempfile
import os
import gzip


def test_basic_alignment():
    query = "HEAGAWGHEE"
    ref = "PAWHEAE"
    
    scoring = ScoringMatrix(gap_open=-10, gap_extend=-1)
    result = smith_waterman(query, ref, scoring)
    
    print("Testing basic alignment...")
    print(f"Query: {query}")
    print(f"Reference: {ref}")
    print(f"Score: {result.score}")
    print(f"CIGAR: {result.cigar}")
    print()
    
    assert result.score > 0, "Alignment should have positive score"
    assert result.cigar != '*', "CIGAR should not be '*' for valid alignment"
    print("OK - Basic alignment test passed")
    return result


def test_sam_output():
    query = Sequence(
        identifier="query1",
        sequence="HEAGAWGHEE",
        quality="IIIIIIIIII"
    )
    ref = Sequence(
        identifier="ref1",
        sequence="PAWHEAE"
    )
    
    scoring = ScoringMatrix()
    result = smith_waterman(query.seq, ref.seq, scoring)
    
    sam_line = alignment_to_sam(
        query_id=query.id,
        query_seq=query.seq,
        query_qual=query.quality,
        alignment_result=result,
        reference_id=ref.id
    )
    
    print("\nTesting SAM output (mapped)...")
    print(f"SAM line: {sam_line}")
    
    fields = sam_line.split('\t')
    assert len(fields) >= 11, "SAM line should have at least 11 fields"
    assert fields[1] == '0', "Flag should be 0 for mapped"
    assert fields[2] == 'ref1', "RNAME should be ref1"
    assert fields[5] != '*', "CIGAR should not be '*'"
    print("OK - SAM mapped output test passed")
    
    from align import AlignmentResult
    unmapped_result = AlignmentResult(
        query_aligned="ATCG",
        ref_aligned="----",
        score=0,
        start_query=0,
        end_query=0,
        start_ref=0,
        end_ref=0,
        cigar='*'
    )
    
    sam_unmapped = alignment_to_sam(
        query_id="unmapped1",
        query_seq="ATCG",
        query_qual="IIII",
        alignment_result=unmapped_result,
        reference_id="ref1"
    )
    
    print("\nTesting SAM output (unmapped)...")
    print(f"SAM line: {sam_unmapped}")
    
    fields2 = sam_unmapped.split('\t')
    assert fields2[1] == '4', "Flag should be 4 for unmapped"
    assert fields2[2] == '*', "RNAME should be '*' for unmapped"
    assert fields2[3] == '0', "POS should be 0 for unmapped"
    assert fields2[5] == '*', "CIGAR should be '*' for unmapped"
    print("OK - SAM unmapped output test passed")


def test_boundary_cases():
    query = "A"
    ref = "A"
    scoring = ScoringMatrix()
    result = smith_waterman(query, ref, scoring)
    
    print("\nTesting single match case...")
    print(f"Score: {result.score}")
    print(f"CIGAR: {result.cigar}")
    
    assert result.score == 4, "Single A-A match should score 4 (BLOSUM62)"
    assert result.cigar == '1M', "CIGAR should be '1M'"
    print("OK - Single match test passed")
    
    query_empty = ""
    ref_empty = ""
    result2 = smith_waterman(query_empty, ref_empty, scoring)
    print("\nTesting empty sequences...")
    print(f"Score: {result2.score}")
    print(f"CIGAR: {result2.cigar}")
    
    assert result2.score == 0, "Empty sequences should have score 0"
    print("OK - Empty sequences test passed")
    
    query_single = "A"
    ref_long = "AAAAA"
    result3 = smith_waterman(query_single, ref_long, scoring)
    print("\nTesting single char vs long ref...")
    print(f"Score: {result3.score}")
    print(f"CIGAR: {result3.cigar}")
    assert result3.score == 4, "Single match should score 4"
    print("OK - Single char vs long ref test passed")


def test_gzip_support():
    print("\nTesting gzip support...")
    
    sequences = [
        Sequence(identifier="seq1", sequence="HEAGAWGHEE", description="Test sequence 1"),
        Sequence(identifier="seq2", sequence="PAWHEAE", description="Test sequence 2"),
    ]
    
    with tempfile.TemporaryDirectory() as tmpdir:
        fasta_gz = os.path.join(tmpdir, "test.fasta.gz")
        write_fasta(fasta_gz, sequences)
        
        assert os.path.exists(fasta_gz), "Gzip file should be created"
        
        read_seqs = read_fasta(fasta_gz)
        assert len(read_seqs) == 2, "Should read 2 sequences"
        assert read_seqs[0].id == "seq1", "First sequence ID should match"
        assert read_seqs[0].seq == "HEAGAWGHEE", "Sequence content should match"
        assert read_seqs[1].id == "seq2", "Second sequence ID should match"
        assert read_seqs[1].seq == "PAWHEAE", "Sequence content should match"
    
    print("OK - gzip support test passed")


def test_banded_alignment():
    print("\nTesting banded Smith-Waterman (long reads)...")
    
    from banded_align import banded_smith_waterman, estimate_band_width
    
    query = "HEAGAWGHEE"
    ref = "PAWHEAE"
    
    scoring = ScoringMatrix(gap_open=-10, gap_extend=-1)
    
    result_full = smith_waterman(query, ref, scoring)
    result_banded = banded_smith_waterman(query, ref, scoring, band_width=50)
    
    print(f"Full SW score: {result_full.score}, CIGAR: {result_full.cigar}")
    print(f"Banded SW score: {result_banded.score}, CIGAR: {result_banded.cigar}")
    
    assert result_banded.score == result_full.score, "Banded should give same score for small sequences"
    print("OK - Banded alignment test passed")
    
    estimated = estimate_band_width(1000, 1000, expected_identity=0.9)
    print(f"Estimated band width for 90% identity: {estimated}")
    assert estimated > 0, "Estimated bandwidth should be positive"


def test_backend_info():
    print("\nTesting backend detection...")
    
    backend = get_backend_info()
    gpu_avail = is_gpu_available()
    
    print(f"Backend: {backend}")
    print(f"GPU available: {gpu_avail}")
    
    assert backend in ['Cupy (GPU)', 'NumPy (CPU)', 'Pure Python'], "Backend should be one of the expected types"
    print("OK - Backend detection test passed")


def test_batch_alignment():
    print("\nTesting batch alignment...")
    
    from batch_align import batch_align, get_optimal_workers
    
    queries = [
        "HEAGAWGHEE",
        "PAWHEAE",
        "AAAAA",
    ]
    ref = "HEAGAWGHEEPAWHEAE"
    
    scoring = ScoringMatrix()
    
    workers = get_optimal_workers()
    print(f"Optimal workers: {workers}")
    
    results = batch_align(queries, ref, num_workers=1)
    
    assert len(results) == 3, "Should have 3 results"
    
    for i, result in enumerate(results):
        print(f"Query {i} score: {result.score}, CIGAR: {result.cigar}")
        assert result.score >= 0, "Score should be non-negative"
    
    print("OK - Batch alignment test passed")


def test_affine_vs_linear():
    query = "AAA"
    ref = "AA"
    
    affine = ScoringMatrix(gap_open=-10, gap_extend=-1, use_affine=True)
    linear = ScoringMatrix(gap_open=-10, gap_extend=-1, use_affine=False)
    
    result_affine = smith_waterman(query, ref, affine)
    result_linear = smith_waterman(query, ref, linear)
    
    print("\nTesting affine vs linear gap penalty...")
    print(f"Affine score: {result_affine.score}")
    print(f"Linear score: {result_linear.score}")
    
    assert affine.use_affine == True, "Affine should use_affine=True"
    assert linear.use_affine == False, "Linear should use_affine=False"
    print("OK - Affine/Linear mode test passed")


if __name__ == "__main__":
    test_backend_info()
    test_basic_alignment()
    test_sam_output()
    test_boundary_cases()
    test_gzip_support()
    test_banded_alignment()
    test_batch_alignment()
    test_affine_vs_linear()
    print("\n=== All tests passed! ===")
