import numpy as np
from Bio.Align import substitution_matrices


class NeedlemanWunsch:
    def __init__(self, match=1, mismatch=-1, gap_open=-2, gap_extend=-1, 
                 use_affine=False, substitution_matrix=None, band_width=None):
        self.match = match
        self.mismatch = mismatch
        self.gap_open = gap_open
        self.gap_extend = gap_extend
        self.use_affine = use_affine
        self.substitution_matrix = substitution_matrix
        self.band_width = band_width
        
        if substitution_matrix is None:
            self.substitution_matrix = substitution_matrices.load("BLOSUM62")
        
        self.score_matrix = None
        self.traceback_matrix = None
        self.Ix_matrix = None
        self.Iy_matrix = None
        self.seq1 = None
        self.seq2 = None
        self.aligned_seq1 = None
        self.aligned_seq2 = None
        self.alignment_score = None

    def _get_match_score(self, aa1, aa2):
        if (aa1, aa2) in self.substitution_matrix:
            return self.substitution_matrix[(aa1, aa2)]
        elif (aa2, aa1) in self.substitution_matrix:
            return self.substitution_matrix[(aa2, aa1)]
        else:
            return self.match if aa1 == aa2 else self.mismatch

    def align(self, seq1, seq2):
        self.seq1 = seq1
        self.seq2 = seq2
        n, m = len(seq1), len(seq2)
        
        if self.band_width is not None:
            return self._banded_align(seq1, seq2)
        
        if self.use_affine:
            return self._affine_align(seq1, seq2)
        else:
            return self._linear_align(seq1, seq2)

    def _linear_align(self, seq1, seq2):
        n, m = len(seq1), len(seq2)
        
        self.score_matrix = np.zeros((n + 1, m + 1))
        self.traceback_matrix = np.zeros((n + 1, m + 1), dtype=int)
        
        for i in range(1, n + 1):
            self.score_matrix[i][0] = self.gap_open * i
            self.traceback_matrix[i][0] = 1
        
        for j in range(1, m + 1):
            self.score_matrix[0][j] = self.gap_open * j
            self.traceback_matrix[0][j] = 2
        
        for i in range(1, n + 1):
            for j in range(1, m + 1):
                match_score = self._get_match_score(seq1[i-1], seq2[j-1])
                
                diagonal = self.score_matrix[i-1][j-1] + match_score
                up = self.score_matrix[i-1][j] + self.gap_open
                left = self.score_matrix[i][j-1] + self.gap_open
                
                max_score = max(diagonal, up, left)
                self.score_matrix[i][j] = max_score
                
                if max_score == diagonal:
                    self.traceback_matrix[i][j] = 0
                elif max_score == up:
                    self.traceback_matrix[i][j] = 1
                else:
                    self.traceback_matrix[i][j] = 2
        
        self._traceback_linear(n, m)
        self.alignment_score = self.score_matrix[n][m]
        
        return self.aligned_seq1, self.aligned_seq2, self.alignment_score

    def _affine_align(self, seq1, seq2):
        n, m = len(seq1), len(seq2)
        
        self.score_matrix = np.zeros((n + 1, m + 1))
        self.Ix_matrix = np.zeros((n + 1, m + 1))
        self.Iy_matrix = np.zeros((n + 1, m + 1))
        self.traceback_matrix = np.zeros((n + 1, m + 1), dtype=int)
        
        for i in range(1, n + 1):
            self.score_matrix[i][0] = self.gap_open + (i - 1) * self.gap_extend
            self.Ix_matrix[i][0] = self.gap_open + (i - 1) * self.gap_extend
            self.Iy_matrix[i][0] = -np.inf
            self.traceback_matrix[i][0] = 1
        
        for j in range(1, m + 1):
            self.score_matrix[0][j] = self.gap_open + (j - 1) * self.gap_extend
            self.Ix_matrix[0][j] = -np.inf
            self.Iy_matrix[0][j] = self.gap_open + (j - 1) * self.gap_extend
            self.traceback_matrix[0][j] = 2
        
        for i in range(1, n + 1):
            for j in range(1, m + 1):
                match_score = self._get_match_score(seq1[i-1], seq2[j-1])
                
                self.Ix_matrix[i][j] = max(
                    self.score_matrix[i-1][j] + self.gap_open,
                    self.Ix_matrix[i-1][j] + self.gap_extend
                )
                
                self.Iy_matrix[i][j] = max(
                    self.score_matrix[i][j-1] + self.gap_open,
                    self.Iy_matrix[i][j-1] + self.gap_extend
                )
                
                match = self.score_matrix[i-1][j-1] + match_score
                self.score_matrix[i][j] = max(match, self.Ix_matrix[i][j], self.Iy_matrix[i][j])
                
                if self.score_matrix[i][j] == match:
                    self.traceback_matrix[i][j] = 0
                elif self.score_matrix[i][j] == self.Ix_matrix[i][j]:
                    self.traceback_matrix[i][j] = 1
                else:
                    self.traceback_matrix[i][j] = 2
        
        self._traceback_affine(n, m)
        self.alignment_score = self.score_matrix[n][m]
        
        return self.aligned_seq1, self.aligned_seq2, self.alignment_score

    def _banded_align(self, seq1, seq2):
        n, m = len(seq1), len(seq2)
        k = self.band_width
        
        if abs(n - m) > k:
            raise ValueError(f"Sequence length difference ({abs(n - m)}) exceeds band width ({k})")
        
        self.score_matrix = np.full((n + 1, m + 1), -np.inf)
        self.traceback_matrix = np.zeros((n + 1, m + 1), dtype=int)
        
        self.score_matrix[0][0] = 0
        
        for i in range(1, min(n, k) + 1):
            self.score_matrix[i][0] = self.gap_open * i
            self.traceback_matrix[i][0] = 1
        
        for j in range(1, min(m, k) + 1):
            self.score_matrix[0][j] = self.gap_open * j
            self.traceback_matrix[0][j] = 2
        
        for i in range(1, n + 1):
            j_start = max(1, i - k)
            j_end = min(m, i + k)
            
            for j in range(j_start, j_end + 1):
                match_score = self._get_match_score(seq1[i-1], seq2[j-1])
                
                diagonal = self.score_matrix[i-1][j-1] + match_score if self.score_matrix[i-1][j-1] != -np.inf else -np.inf
                up = self.score_matrix[i-1][j] + self.gap_open if self.score_matrix[i-1][j] != -np.inf else -np.inf
                left = self.score_matrix[i][j-1] + self.gap_open if self.score_matrix[i][j-1] != -np.inf else -np.inf
                
                max_score = max(diagonal, up, left)
                if max_score != -np.inf:
                    self.score_matrix[i][j] = max_score
                    
                    if max_score == diagonal:
                        self.traceback_matrix[i][j] = 0
                    elif max_score == up:
                        self.traceback_matrix[i][j] = 1
                    else:
                        self.traceback_matrix[i][j] = 2
        
        self._traceback_linear(n, m)
        self.alignment_score = self.score_matrix[n][m]
        
        return self.aligned_seq1, self.aligned_seq2, self.alignment_score

    def _traceback_linear(self, i, j):
        aligned1, aligned2 = [], []
        
        while i > 0 or j > 0:
            direction = self.traceback_matrix[i][j]
            
            if direction == 0:
                aligned1.append(self.seq1[i - 1])
                aligned2.append(self.seq2[j - 1])
                i -= 1
                j -= 1
            elif direction == 1:
                aligned1.append(self.seq1[i - 1])
                aligned2.append("-")
                i -= 1
            else:
                aligned1.append("-")
                aligned2.append(self.seq2[j - 1])
                j -= 1
        
        self.aligned_seq1 = "".join(reversed(aligned1))
        self.aligned_seq2 = "".join(reversed(aligned2))

    def _traceback_affine(self, i, j):
        aligned1, aligned2 = [], []
        current_state = 'M'
        
        while i > 0 or j > 0:
            if current_state == 'M':
                direction = self.traceback_matrix[i][j]
                if direction == 0:
                    aligned1.append(self.seq1[i - 1])
                    aligned2.append(self.seq2[j - 1])
                    i -= 1
                    j -= 1
                elif direction == 1:
                    current_state = 'Ix'
                else:
                    current_state = 'Iy'
            elif current_state == 'Ix':
                aligned1.append(self.seq1[i - 1])
                aligned2.append("-")
                i -= 1
                if self.score_matrix[i][j] > self.Ix_matrix[i][j]:
                    current_state = 'M'
            else:
                aligned1.append("-")
                aligned2.append(self.seq2[j - 1])
                j -= 1
                if self.score_matrix[i][j] > self.Iy_matrix[i][j]:
                    current_state = 'M'
        
        self.aligned_seq1 = "".join(reversed(aligned1))
        self.aligned_seq2 = "".join(reversed(aligned2))

    def get_score_matrix(self):
        return self.score_matrix

    def print_alignment(self, line_width=60):
        if self.aligned_seq1 is None or self.aligned_seq2 is None:
            print("No alignment performed yet.")
            return
        
        match_line = []
        for a, b in zip(self.aligned_seq1, self.aligned_seq2):
            if a == b:
                match_line.append("|")
            elif a != "-" and b != "-":
                match_line.append(".")
            else:
                match_line.append(" ")
        
        match_str = "".join(match_line)
        
        method = "Banded" if self.band_width else ("Affine" if self.use_affine else "Linear")
        print(f"Needleman-Wunsch Global Alignment ({method})")
        print(f"Alignment Score: {self.alignment_score}")
        print("-" * 50)
        
        for i in range(0, len(self.aligned_seq1), line_width):
            end = min(i + line_width, len(self.aligned_seq1))
            print(f"Seq1: {self.aligned_seq1[i:end]}")
            print(f"      {match_str[i:end]}")
            print(f"Seq2: {self.aligned_seq2[i:end]}")
            print()
