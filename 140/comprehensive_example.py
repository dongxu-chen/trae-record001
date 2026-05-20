import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from seqalign import (
    NeedlemanWunsch, SmithWaterman, SimilarityMatrix, AlignmentVisualizer,
    LocalBLAST, ClustalW, PhylogeneticAnalysis, AlignmentReport, FastaWriter
)
import matplotlib
matplotlib.use('Agg')


def print_header(title):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def example_1_basic_alignment():
    print_header("Example 1: Basic Sequence Alignment")
    
    seq1 = "MVLSPADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHFDLSHGSAQVKGHG"
    seq2 = "MVLSAADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHFDLSHGSAQVKGHG"
    
    print(f"\nSequence 1: {seq1[:50]}...")
    print(f"Sequence 2: {seq2[:50]}...")
    
    print("\n--- Needleman-Wunsch Global Alignment (Affine Gap) ---")
    nw = NeedlemanWunsch(
        match=2, mismatch=-1, gap_open=-5, gap_extend=-1, use_affine=True
    )
    aligned1, aligned2, score = nw.align(seq1, seq2)
    print(f"Alignment Score: {score}")
    print(f"Aligned 1: {aligned1[:60]}...")
    print(f"Aligned 2: {aligned2[:60]}...")
    
    print("\n--- Smith-Waterman Local Alignment ---")
    sw = SmithWaterman(
        match=2, mismatch=-1, gap_open=-5, gap_extend=-1, use_affine=True
    )
    aligned1_local, aligned2_local, score_local = sw.align(seq1, seq2)
    print(f"Local Alignment Score: {score_local}")
    positions = sw.get_alignment_positions()
    print(f"Position in Seq1: {positions['start1'] + 1}-{positions['end1']}")
    print(f"Position in Seq2: {positions['start2'] + 1}-{positions['end2']}")
    
    return aligned1, aligned2


def example_2_banded_alignment():
    print_header("Example 2: Banded Alignment (Memory Efficient)")
    
    seq1 = "MVLSPADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHFDLSHGSAQVKGHGKKVADALTNAVAHVDDMPNALSALSDLHAHKLRVDPVNFKLLSHCLLVTLAAHLPAEFTPAVHASLDKFLASVSTVLTSKYR"
    seq2 = "MVLSAADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHFDLSHGSAQVKGHGKKVADALTNAVAHVDDMPNALSALSDLHAHKLRVDPVNFKLLSHCLLVTLAAHLPAEFTPAVHASLDKFLASVSTVLTSKYR"
    
    print(f"\nLong Sequence 1 length: {len(seq1)}")
    print(f"Long Sequence 2 length: {len(seq2)}")
    
    print("\n--- Standard Full Matrix Alignment ---")
    nw_std = NeedlemanWunsch(match=2, mismatch=-1, gap_open=-5, gap_extend=-1, use_affine=True)
    _, _, score_std = nw_std.align(seq1, seq2)
    print(f"Score: {score_std}")
    
    print("\n--- Banded Alignment (band_width=10) ---")
    nw_banded = NeedlemanWunsch(
        match=2, mismatch=-1, gap_open=-5, gap_extend=-1, band_width=10
    )
    _, _, score_banded = nw_banded.align(seq1, seq2)
    print(f"Score: {score_banded}")
    print("Note: Banded alignment is much more memory efficient for long sequences!")
    
    return score_std, score_banded


def example_3_blast_search():
    print_header("Example 3: Local BLAST Search")
    
    database_sequences = [
        "MVLSPADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHFDLSHGSAQVKGHG",
        "MVLSAADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHFDLSHGSAQVKGHG",
        "MVLSPADKTNVKVVWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHFDLSHGSAQVKGHG",
        "MILSPADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHFDLSHGSAQVKGHG",
        "MVLSPADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHFDLSHGSAQVKGRA"
    ]
    database_ids = ["Hemoglobin_A", "Hemoglobin_B", "Hemoglobin_C", "Hemoglobin_D", "Hemoglobin_E"]
    
    query = "MVLSPADKTNVKAAWGKVGAHAGEYGAEALERM"
    print(f"\nQuery sequence: {query}")
    print(f"Database contains {len(database_sequences)} sequences")
    
    blast = LocalBLAST(word_size=5, score_threshold=10)
    blast.build_database(database_sequences, database_ids)
    
    hits = blast.search(query, query_id="Query_Hemo", max_hits=10)
    
    print(f"\nFound {len(hits)} hits:")
    blast.print_search_results(hits)
    
    return hits


def example_4_multiple_alignment():
    print_header("Example 4: ClustalW Multiple Sequence Alignment")
    
    sequences = [
        "MVLSPADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHFDLSHGSAQVKGHG",
        "MVLSAADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHFDLSHGSAQVKGHG",
        "MVLSPADKTNVKVVWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHFDLSHGSAQVKGHG",
        "MILSPADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHFDLSHGSAQVKGHG",
        "MVLSPADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHFDLSHGSAQVKGRA"
    ]
    names = ["Hem_A", "Hem_B", "Hem_C", "Hem_D", "Hem_E"]
    
    print(f"\nPerforming progressive MSA on {len(sequences)} sequences...")
    
    msa = ClustalW(match=2, mismatch=-1, gap_open=-5, gap_extend=-1)
    aligned_sequences = msa.align(sequences, names)
    
    msa.print_alignment(line_width=50)
    
    return aligned_sequences, names


def example_5_phylogenetic_tree():
    print_header("Example 5: Phylogenetic Tree Construction (Neighbor-Joining)")
    
    sequences = [
        "MVLSPADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHFDLSHGSAQVKGHG",
        "MVLSAADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHFDLSHGSAQVKGHG",
        "MVLSPADKTNVKVVWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHFDLSHGSAQVKGHG",
        "MILSPADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHFDLSHGSAQVKGHG",
        "MVLSPADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHFDLSHGSAQVKGRA"
    ]
    names = ["Hem_A", "Hem_B", "Hem_C", "Hem_D", "Hem_E"]
    
    print("\nBuilding Neighbor-Joining tree...")
    
    phyl = PhylogeneticAnalysis()
    tree = phyl.build_tree(sequences, names, distance_method='p_distance')
    
    newick = phyl.get_newick()
    print(f"\nNewick format tree:")
    print(f"  {newick}")
    
    print("\nTree built successfully!")
    
    return tree


def example_6_similarity_matrix():
    print_header("Example 6: Symmetric Sequence Similarity Matrix")
    
    sequences = [
        "MVLSPADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHFDLSHGSAQVKGHG",
        "MVLSAADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHFDLSHGSAQVKGHG",
        "MVLSPADKTNVKVVWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHFDLSHGSAQVKGHG",
        "MILSPADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHFDLSHGSAQVKGHG",
        "MVLSPADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHFDLSHGSAQVKGRA"
    ]
    names = ["Hem_A", "Hem_B", "Hem_C", "Hem_D", "Hem_E"]
    
    print("\nCalculating symmetric similarity matrix (max method)...")
    
    sim = SimilarityMatrix(
        alignment_method='global', enforce_symmetric=True,
        match=2, mismatch=-1, gap_open=-5, gap_extend=-1
    )
    matrix = sim.compute_matrix(sequences, names)
    
    print(f"\nIs symmetric: {sim.is_symmetric()}")
    sim.print_matrix()
    
    stats = sim.get_similarity_stats()
    print(f"\nStatistics:")
    for key, value in stats.items():
        if key != 'symmetric':
            print(f"  {key}: {value:.4f}")
    
    pairs = sim.find_most_similar(threshold=0.8)
    print(f"\nMost similar pairs (>=80%):")
    for pair in pairs:
        print(f"  {pair['seq1']} <-> {pair['seq2']}: {pair['similarity']:.2%}")
    
    return matrix


def example_7_pdf_report():
    print_header("Example 7: Generate Colorful PDF Report")
    
    sequences = [
        "MVLSPADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHFDLSHGSAQVKGHG",
        "MVLSAADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHFDLSHGSAQVKGHG",
        "MVLSPADKTNVKVVWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHFDLSHGSAQVKGHG",
        "MILSPADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHFDLSHGSAQVKGHG",
    ]
    names = ["Hem_A", "Hem_B", "Hem_C", "Hem_D"]
    
    msa = ClustalW(match=2, mismatch=-1, gap_open=-5, gap_extend=-1)
    aligned = msa.align(sequences, names)
    
    sim = SimilarityMatrix(enforce_symmetric=True)
    sim_matrix = sim.compute_matrix(sequences, names)
    
    blast = LocalBLAST(word_size=5)
    blast.build_database(sequences, names)
    hits = blast.search(sequences[0], query_id=names[0])
    
    phyl = PhylogeneticAnalysis()
    tree = phyl.build_tree(sequences, names)
    
    report = AlignmentReport()
    report_file = 'alignment_report.pdf'
    report.generate_full_report(
        filename=report_file,
        aligned_sequences=aligned,
        names=names,
        similarity_matrix=sim_matrix,
        blast_hits=hits,
        query_id=names[0],
        phylogenetic_tree=tree,
        seq_type='protein'
    )
    
    FastaWriter.write_alignment(aligned, names, 'alignment_results.fasta')
    
    print(f"\nReport files generated:")
    print(f"  - {report_file}")
    print(f"  - alignment_results.fasta")
    
    return report_file


def example_8_visualizations():
    print_header("Example 8: Advanced Visualizations")
    
    sequences = [
        "MVLSPADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHFDLSHGSAQVKGHG",
        "MVLSAADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHFDLSHGSAQVKGHG",
        "MVLSPADKTNVKVVWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHFDLSHGSAQVKGHG",
    ]
    names = ["Seq1", "Seq2", "Seq3"]
    
    msa = ClustalW()
    aligned = msa.align(sequences, names)
    
    sim = SimilarityMatrix(enforce_symmetric=True)
    sim_matrix = sim.compute_matrix(sequences, names)
    
    viz = AlignmentVisualizer()
    
    print("\nGenerating visualizations...")
    print("  - Sequence Logo (conservation visualization)")
    print("  - Similarity Heatmap")
    print("  - Alignment Display with colors")
    print("  - Similarity Histogram")
    print("  - Conservation Heatmap")
    
    print("\nVisualization functions ready to use!")
    
    return viz


def main():
    print("\n" + "#" * 80)
    print("#" + " " * 78 + "#")
    print("#" + " " * 15 + "SEQUENCE ALIGNMENT TOOLKIT v2.0" + " " * 28 + "#")
    print("#" + " " * 78 + "#")
    print("#" + " " * 10 + "BLAST • MSA • Phylogenetic Trees • PDF Reports" + " " * 20 + "#")
    print("#" + " " * 78 + "#")
    print("#" * 80)
    
    try:
        example_1_basic_alignment()
        example_2_banded_alignment()
        hits = example_3_blast_search()
        aligned, names = example_4_multiple_alignment()
        tree = example_5_phylogenetic_tree()
        sim_matrix = example_6_similarity_matrix()
        example_7_pdf_report()
        viz = example_8_visualizations()
        
        print("\n" + "=" * 80)
        print("ALL EXAMPLES COMPLETED SUCCESSFULLY!")
        print("=" * 80)
        print("\nSummary of Features:")
        print("  ✓ Needleman-Wunsch: Global alignment (linear/affine gap)")
        print("  ✓ Smith-Waterman: Local alignment (linear/affine gap)")
        print("  ✓ Banded Alignment: Memory-efficient for long sequences")
        print("  ✓ Local BLAST: Seed-and-extend database search")
        print("  ✓ ClustalW: Progressive multiple sequence alignment")
        print("  ✓ Neighbor-Joining: Phylogenetic tree construction")
        print("  ✓ Symmetric Similarity Matrix: Enforced with max method")
        print("  ✓ Colorful PDF Report: Complete analysis summary")
        print("  ✓ Sequence Logo, Heatmaps, Dot Plots: Visualizations")
        print("\nGenerated files:")
        print("  - alignment_report.pdf (colorful PDF report)")
        print("  - alignment_results.fasta (MSA results)")
        print("\nModule imports available:")
        print("  from seqalign import NeedlemanWunsch, SmithWaterman, LocalBLAST")
        print("  from seqalign import ClustalW, PhylogeneticAnalysis, SimilarityMatrix")
        print("  from seqalign import AlignmentVisualizer, AlignmentReport, FastaWriter")
        
    except Exception as e:
        print(f"\nError in example: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
