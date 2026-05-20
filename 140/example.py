from seqalign import NeedlemanWunsch, SmithWaterman, SimilarityMatrix, AlignmentVisualizer


def example_global_alignment():
    print("=" * 60)
    print("Example 1: Needleman-Wunsch Global Alignment")
    print("=" * 60)
    
    seq1 = "HEAGAWGHEE"
    seq2 = "PAWHEAE"
    
    print(f"\nSequence 1: {seq1}")
    print(f"Sequence 2: {seq2}\n")
    
    nw = NeedlemanWunsch(match=1, mismatch=-1, gap=-2)
    aligned1, aligned2, score = nw.align(seq1, seq2)
    
    nw.print_alignment()
    
    return aligned1, aligned2, nw.get_score_matrix()


def example_local_alignment():
    print("\n" + "=" * 60)
    print("Example 2: Smith-Waterman Local Alignment")
    print("=" * 60)
    
    seq1 = "ACACACTA"
    seq2 = "AGCACACA"
    
    print(f"\nSequence 1: {seq1}")
    print(f"Sequence 2: {seq2}\n")
    
    sw = SmithWaterman(match=2, mismatch=-1, gap=-2)
    aligned1, aligned2, score = sw.align(seq1, seq2)
    
    sw.print_alignment()
    
    positions = sw.get_alignment_positions()
    print(f"Alignment positions: {positions}")
    
    return aligned1, aligned2, sw.get_score_matrix()


def example_similarity_matrix():
    print("\n" + "=" * 60)
    print("Example 3: Sequence Similarity Matrix")
    print("=" * 60)
    
    sequences = [
        "MVLSPADKTNVKAAW",
        "MVLSAADKTNVKAAW",
        "MVLSPADKTNVKVVW",
        "MILSPADKTNVKAAW"
    ]
    names = ["HemA", "HemB", "HemC", "HemD"]
    
    print("\nSequences:")
    for name, seq in zip(names, sequences):
        print(f"  {name}: {seq}")
    print()
    
    sim_matrix = SimilarityMatrix(alignment_method="global", match=1, mismatch=-1, gap=-2)
    matrix = sim_matrix.compute_matrix(sequences, names)
    
    print("Similarity Matrix:")
    sim_matrix.print_matrix()
    
    print("\nMost Similar Pairs:")
    pairs = sim_matrix.find_most_similar(threshold=0.5)
    for pair in pairs[:3]:
        print(f"  {pair['seq1']} - {pair['seq2']}: {pair['similarity']:.3f}")
    
    stats = sim_matrix.get_similarity_stats()
    print(f"\nStatistics:")
    print(f"  Mean: {stats['mean']:.3f}")
    print(f"  Median: {stats['median']:.3f}")
    print(f"  Min: {stats['min']:.3f}")
    print(f"  Max: {stats['max']:.3f}")
    
    return matrix, names


def example_protein_alignment():
    print("\n" + "=" * 60)
    print("Example 4: Protein Sequence Alignment with BLOSUM62")
    print("=" * 60)
    
    seq1 = "MKVLWAALLVTFLAGCQAKVEQAVETEPEPELRQQTEWQSGPEV"
    seq2 = "MKVLWAALLVTFLAGCQAKVEQAVETEPEPELRQQTEWQSGPAV"
    
    print(f"\nProtein 1: {seq1}")
    print(f"Protein 2: {seq2}\n")
    
    nw = NeedlemanWunsch()
    aligned1, aligned2, score = nw.align(seq1, seq2)
    
    nw.print_alignment(line_width=50)
    
    return aligned1, aligned2


def main():
    print("\n" + "#" * 60)
    print("#   Bioinformatics Sequence Alignment Toolkit")
    print("#   Using Biopython + NumPy")
    print("#" * 60 + "\n")
    
    aligned1, aligned2, score_matrix_nw = example_global_alignment()
    aligned1_sw, aligned2_sw, score_matrix_sw = example_local_alignment()
    sim_matrix, names = example_similarity_matrix()
    aligned1_prot, aligned2_prot = example_protein_alignment()
    
    print("\n" + "=" * 60)
    print("Visualization Examples (uncomment to run):")
    print("=" * 60)
    print("\n# Visualize alignment")
    print("visualizer = AlignmentVisualizer()")
    print("visualizer.plot_alignment(aligned1, aligned2, title='Global Alignment')")
    print("\n# Visualize score matrix")
    print("visualizer.plot_score_matrix(score_matrix_nw, 'HEAGAWGHEE', 'PAWHEAE')")
    print("\n# Visualize similarity matrix")
    print("visualizer.plot_similarity_matrix(sim_matrix, names)")
    print("\n# Visualize similarity histogram")
    print("visualizer.plot_similarity_histogram(sim_matrix)")
    
    print("\n" + "=" * 60)
    print("All examples completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
