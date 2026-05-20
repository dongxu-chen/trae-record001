import numpy as np
from Bio.Align import substitution_matrices


class SmithWaterman:
    def __init__(self, match=2, mismatch=-1, gap_open=-2, gap_extend=-1,
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
        self.start_pos1 = None
        self.start_pos2 = None
        self.end_pos1 = None
        self.end_pos2 = None

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
        
        max_score = 0
        max_i, max_j = 0, 0
        
        for i in range(1, n + 1):
            for j in range(1, m + 1):
                match_score = self._get_match_score(seq1[i-1], seq2[j-1])
                
                diagonal = self.score_matrix[i-1][j-1] + match_score
                up = self.score_matrix[i-1][j] + self.gap_open
                left = self.score_matrix[i][j-1] + self.gap_open
                
                current_max = max(diagonal, up, left, 0)
                self.score_matrix[i][j] = current_max
                
                if current_max == diagonal:
                    self.traceback_matrix[i][j] = 0
                elif current_max == up:
                    self.traceback_matrix[i][j] = 1
                elif current_max == left:
                    self.traceback_matrix[i][j] = 2
                else:
                    self.traceback_matrix[i][j] = 3
                
                if current_max > max_score:
                    max_score = current_max
                    max_i, max_j = i, j
        
        if max_score > 0:
            self._traceback_linear(max_i, max_j)
            self.end_pos1, self.end_pos2 = max_i, max_j
        else:
            self.aligned_seq1 = ""
            self.aligned_seq2 = ""
        
        self.alignment_score = max_score
        
        return self.aligned_seq1, self.aligned_seq2, self.alignment_score

    def _affine_align(self, seq1, seq2):
        n, m = len(seq1), len(seq2)
        
        self.score_matrix = np.zeros((n + 1, m + 1))
        self.Ix_matrix = np.zeros((n + 1, m + 1))
        self.Iy_matrix = np.zeros((n + 1, m + 1))
        self.traceback_matrix = np.zeros((n + 1, m + 1), dtype=int)
        
        max_score = 0
        max_i, max_j = 0, 0
        
        for i in range(1, n + 1):
            for j in range(1, m + 1):
                match_score = self._get_match_score(seq1[i-1], seq2[j-1])
                
                self.Ix_matrix[i][j] = max(
                    self.score_matrix[i-1][j] + self.gap_open,
                    self.Ix_matrix[i-1][j] + self.gap_extend,
                    0
                )
                
                self.Iy_matrix[i][j] = max(
                    self.score_matrix[i][j-1] + self.gap_open,
                    self.Iy_matrix[i][j-1] + self.gap_extend,
                    0
                )
                
                match = self.score_matrix[i-1][j-1] + match_score
                self.score_matrix[i][j] = max(match, self.Ix_matrix[i][j], self.Iy_matrix[i][j], 0)
                
                if self.score_matrix[i][j] == match:
                    self.traceback_matrix[i][j] = 0
                elif self.score_matrix[i][j] == self.Ix_matrix[i][j]:
                    self.traceback_matrix[i][j] = 1
                elif self.score_matrix[i][j] == self.Iy_matrix[i][j]:
                    self.traceback_matrix[i][j] = 2
                else:
                    self.traceback_matrix[i][j] = 3
                
                if self.score_matrix[i][j] > max_score:
                    max_score = self.score_matrix[i][j]
                    max_i, max_j = i, j
        
        if max_score > 0:
            self._traceback_affine(max_i, max_j)
            self.end_pos1, self.end_pos2 = max_i, max_j
        else:
            self.aligned_seq1 = ""
            self.aligned_seq2 = ""
        
        self.alignment_score = max_score
        
        return self.aligned_seq1, self.aligned_seq2, self.alignment_score

    def _banded_align(self, seq1, seq2):
        n, m = len(seq1), len(seq2)
        k = self.band_width
        
        if abs(n - m) > k:
            raise ValueError(f"Sequence length difference ({abs(n - m)}) exceeds band width ({k})")
        
        self.score_matrix = np.zeros((n + 1, m + 1))
        self.traceback_matrix = np.zeros((n + 1, m + 1), dtype=int)
        
        max_score = 0
        max_i, max_j = 0, 0
        
        for i in range(1, n + 1):
            j_start = max(1, i - k)
            j_end = min(m, i + k)
            
            for j in range(j_start, j_end + 1):
                match_score = self._get_match_score(seq1[i-1], seq2[j-1])
                
                diagonal = self.score_matrix[i-1][j-1] + match_score
                up = self.score_matrix[i-1][j] + self.gap_open
                left = self.score_matrix[i][j-1] + self.gap_open
                
                current_max = max(diagonal, up, left, 0)
                self.score_matrix[i][j] = current_max
                
                if current_max == diagonal:
                    self.traceback_matrix[i][j] = 0
                elif current_max == up:
                    self.traceback_matrix[i][j] = 1
                elif current_max == left:
                    self.traceback_matrix[i][j] = 2
                else:
                    self.traceback_matrix[i][j] = 3
                
                if current_max > max_score:
                    max_score = current_max
                    max_i, max_j = i, j
        
        if max_score > 0:
            self._traceback_linear(max_i, max_j)
            self.end_pos1, self.end_pos2 = max_i, max_j
        else:
            self.aligned_seq1 = ""
            self.aligned_seq2 = ""
        
        self.alignment_score = max_score
        
        return self.aligned_seq1, self.aligned_seq2, self.alignment_score

    def _traceback_linear(self, i, j):
        aligned1, aligned2 = [], []
        
        while self.score_matrix[i][j] > 0:
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
            elif direction == 2:
                aligned1.append("-")
                aligned2.append(self.seq2[j - 1])
                j -= 1
            else:
                break
        
        self.start_pos1 = i
        self.start_pos2 = j
        self.aligned_seq1 = "".join(reversed(aligned1))
        self.aligned_seq2 = "".join(reversed(aligned2))

    def _traceback_affine(self, i, j):
        aligned1, aligned2 = [], []
        current_state = 'M'
        
        while self.score_matrix[i][j] > 0:
            if current_state == 'M':
                direction = self.traceback_matrix[i][j]
                if direction == 0:
                    aligned1.append(self.seq1[i - 1])
                    aligned2.append(self.seq2[j - 1])
                    i -= 1
                    j -= 1
                elif direction == 1:
                    current_state = 'Ix'
                elif direction == 2:
                    current_state = 'Iy'
                else:
                    break
            elif current_state == 'Ix':
                aligned1.append(self.seq1[i - 1])
                aligned2.append("-")
                i -= 1
                if self.score_matrix[i][j] >= self.Ix_matrix[i][j]:
                    current_state = 'M'
            else:
                aligned1.append("-")
                aligned2.append(self.seq2[j - 1])
                j -= 1
                if self.score_matrix[i][j] >= self.Iy_matrix[i][j]:
                    current_state = 'M'
        
        self.start_pos1 = i
        self.start_pos2 = j
        self.aligned_seq1 = "".join(reversed(aligned1))
        self.aligned_seq2 = "".join(reversed(aligned2))

    def get_score_matrix(self):
        return self.score_matrix

    def get_alignment_positions(self):
        return {
            "start1": self.start_pos1,
            "start2": self.start_pos2,
            "end1": self.end_pos1,
            "end2": self.end_pos2
        }

    def print_alignment(self, line_width=60):
        if self.aligned_seq1 is None or self.aligned_seq2 is None:
            print("No alignment performed yet.")
            return
        
        if len(self.aligned_seq1) == 0:
            print("No significant local alignment found.")
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
        print(f"Smith-Waterman Local Alignment ({method})")
        print(f"Local Alignment Score: {self.alignment_score}")
        print(f"Position in Seq1: {self.start_pos1 + 1}-{self.end_pos1}")
        print(f"Position in Seq2: {self.start_pos2 + 1}-{self.end_pos2}")
        print("-" * 50)
        
        for i in range(0, len(self.aligned_seq1), line_width):
            end = min(i + line_width, len(self.aligned_seq1))
            print(f"Seq1: {self.aligned_seq1[i:end]}")
            print(f"      {match_str[i:end]}")
            print(f"Seq2: {self.aligned_seq2[i:end]}")
            print()
