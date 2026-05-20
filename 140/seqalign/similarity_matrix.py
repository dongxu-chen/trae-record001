import numpy as np
from .needleman_wunsch import NeedlemanWunsch
from .smith_waterman import SmithWaterman


class SimilarityMatrix:
    def __init__(self, alignment_method="global", enforce_symmetric=True, **kwargs):
        self.alignment_method = alignment_method
        self.enforce_symmetric = enforce_symmetric
        self.kwargs = kwargs
        self.similarity_matrix = None
        self.sequences = None
        self.sequence_names = None

    def compute_pairwise_similarity(self, seq1, seq2):
        if self.alignment_method == "global":
            aligner = NeedlemanWunsch(**self.kwargs)
            aligned1, aligned2, score = aligner.align(seq1, seq2)
        else:
            aligner = SmithWaterman(**self.kwargs)
            aligned1, aligned2, score = aligner.align(seq1, seq2)
        
        if len(aligned1) == 0 or len(aligned2) == 0:
            return 0.0
        
        matches = sum(1 for a, b in zip(aligned1, aligned2) if a == b and a != "-")
        identity = matches / max(len(seq1), len(seq2))
        
        return identity

    def compute_matrix(self, sequences, names=None):
        self.sequences = sequences
        n = len(sequences)
        
        if names is None:
            self.sequence_names = [f"Seq{i+1}" for i in range(n)]
        else:
            self.sequence_names = names
        
        self.similarity_matrix = np.zeros((n, n))
        
        for i in range(n):
            self.similarity_matrix[i][i] = 1.0
        
        for i in range(n):
            for j in range(i + 1, n):
                sim_ij = self.compute_pairwise_similarity(sequences[i], sequences[j])
                sim_ji = self.compute_pairwise_similarity(sequences[j], sequences[i])
                
                if self.enforce_symmetric:
                    sim = max(sim_ij, sim_ji)
                    self.similarity_matrix[i][j] = sim
                    self.similarity_matrix[j][i] = sim
                else:
                    self.similarity_matrix[i][j] = sim_ij
                    self.similarity_matrix[j][i] = sim_ji
        
        return self.similarity_matrix

    def get_matrix(self):
        return self.similarity_matrix

    def get_sequence_names(self):
        return self.sequence_names

    def is_symmetric(self):
        if self.similarity_matrix is None:
            return False
        return np.allclose(self.similarity_matrix, self.similarity_matrix.T)

    def print_matrix(self, decimal_places=3):
        if self.similarity_matrix is None:
            print("No similarity matrix computed yet.")
            return
        
        n = len(self.sequence_names)
        max_name_len = max(len(name) for name in self.sequence_names)
        
        symmetric_status = "Symmetric" if self.is_symmetric() else "Asymmetric"
        print(f"Sequence Similarity Matrix ({symmetric_status})")
        print("-" * 50)
        
        header = " " * (max_name_len + 2)
        for name in self.sequence_names:
            header += f"{name:>{decimal_places + 4}} "
        print(header)
        
        for i in range(n):
            row = f"{self.sequence_names[i]:<{max_name_len}}  "
            for j in range(n):
                row += f"{self.similarity_matrix[i][j]:.{decimal_places}f}  "
            print(row)

    def find_most_similar(self, threshold=0.0):
        if self.similarity_matrix is None:
            return []
        
        n = self.similarity_matrix.shape[0]
        pairs = []
        
        for i in range(n):
            for j in range(i + 1, n):
                if self.similarity_matrix[i][j] >= threshold:
                    pairs.append({
                        "seq1": self.sequence_names[i],
                        "seq2": self.sequence_names[j],
                        "similarity": self.similarity_matrix[i][j],
                        "similarity_ji": self.similarity_matrix[j][i]
                    })
        
        pairs.sort(key=lambda x: x["similarity"], reverse=True)
        return pairs

    def get_similarity_stats(self):
        if self.similarity_matrix is None:
            return None
        
        upper_triangle = self.similarity_matrix[np.triu_indices_from(self.similarity_matrix, k=1)]
        
        if len(upper_triangle) == 0:
            return None
        
        return {
            "mean": np.mean(upper_triangle),
            "median": np.median(upper_triangle),
            "min": np.min(upper_triangle),
            "max": np.max(upper_triangle),
            "std": np.std(upper_triangle),
            "symmetric": self.is_symmetric()
        }

    def normalize_matrix(self):
        if self.similarity_matrix is None:
            return None
        
        max_val = np.max(self.similarity_matrix)
        if max_val > 0:
            self.similarity_matrix = self.similarity_matrix / max_val
        
        return self.similarity_matrix
