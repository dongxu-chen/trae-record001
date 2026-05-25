import numpy as np
from substitution_matrices import SubstitutionMatrix

GAP = '-'
UP = 1
LEFT = 2
DIAG = 4
UP_LEFT = UP | LEFT
UP_DIAG = UP | DIAG
LEFT_DIAG = LEFT | DIAG
ALL_THREE = UP | LEFT | DIAG

class AlignmentResult:
    def __init__(self, aligned_seq1, aligned_seq2, score):
        self.aligned_seq1 = aligned_seq1
        self.aligned_seq2 = aligned_seq2
        self.score = score
    
    def __str__(self):
        return f"Score: {self.score}\nSeq1: {self.aligned_seq1}\nSeq2: {self.aligned_seq2}"
    
    def __eq__(self, other):
        return (self.aligned_seq1 == other.aligned_seq1 and 
                self.aligned_seq2 == other.aligned_seq2)
    
    def __hash__(self):
        return hash((self.aligned_seq1, self.aligned_seq2))

class NeedlemanWunsch:
    def __init__(self, seq1, seq2, gap_penalty=-2, matrix_type='blosum62', seq_type='protein', 
                 use_rolling=True, find_all_solutions=False, max_solutions=100):
        self.seq1 = seq1.upper()
        self.seq2 = seq2.upper()
        self.gap_penalty = gap_penalty
        self.sub_matrix = SubstitutionMatrix(matrix_type, seq_type)
        self.n = len(seq1)
        self.m = len(seq2)
        self.use_rolling = use_rolling
        self.find_all_solutions = find_all_solutions
        self.max_solutions = max_solutions
        
        self.score_matrix = None
        self.traceback_matrix = None
        self.alignment_results = []
        self.alignment_score = None
    
    def _compute_full_matrix(self):
        self.score_matrix = np.zeros((self.n + 1, self.m + 1), dtype=np.int32)
        self.traceback_matrix = np.zeros((self.n + 1, self.m + 1), dtype=np.int8)
        
        for i in range(1, self.n + 1):
            self.score_matrix[i, 0] = i * self.gap_penalty
            self.traceback_matrix[i, 0] = UP
        
        for j in range(1, self.m + 1):
            self.score_matrix[0, j] = j * self.gap_penalty
            self.traceback_matrix[0, j] = LEFT
        
        for i in range(1, self.n + 1):
            for j in range(1, self.m + 1):
                match_score = self.sub_matrix.get_score(self.seq1[i-1], self.seq2[j-1])
                diag = self.score_matrix[i-1, j-1] + match_score
                up = self.score_matrix[i-1, j] + self.gap_penalty
                left = self.score_matrix[i, j-1] + self.gap_penalty
                
                max_score = max(diag, up, left)
                self.score_matrix[i, j] = max_score
                
                directions = 0
                if diag == max_score:
                    directions |= DIAG
                if up == max_score:
                    directions |= UP
                if left == max_score:
                    directions |= LEFT
                
                self.traceback_matrix[i, j] = directions
        
        self.alignment_score = self.score_matrix[self.n, self.m]
    
    def _compute_rolling_matrix(self):
        prev_row = np.zeros(self.m + 1, dtype=np.int32)
        curr_row = np.zeros(self.m + 1, dtype=np.int32)
        
        self.traceback_matrix = np.zeros((self.n + 1, self.m + 1), dtype=np.int8)
        
        for j in range(1, self.m + 1):
            prev_row[j] = j * self.gap_penalty
            self.traceback_matrix[0, j] = LEFT
        
        for i in range(1, self.n + 1):
            curr_row[0] = i * self.gap_penalty
            self.traceback_matrix[i, 0] = UP
            
            for j in range(1, self.m + 1):
                match_score = self.sub_matrix.get_score(self.seq1[i-1], self.seq2[j-1])
                diag = prev_row[j-1] + match_score
                up = prev_row[j] + self.gap_penalty
                left = curr_row[j-1] + self.gap_penalty
                
                max_score = max(diag, up, left)
                curr_row[j] = max_score
                
                directions = 0
                if diag == max_score:
                    directions |= DIAG
                if up == max_score:
                    directions |= UP
                if left == max_score:
                    directions |= LEFT
                
                self.traceback_matrix[i, j] = directions
            
            prev_row, curr_row = curr_row, prev_row
        
        self.alignment_score = prev_row[self.m]
        self.score_matrix = None
    
    def _traceback_single(self, i, j):
        aligned1 = []
        aligned2 = []
        
        while i > 0 or j > 0:
            direction = self.traceback_matrix[i, j]
            
            if direction & DIAG:
                aligned1.append(self.seq1[i-1])
                aligned2.append(self.seq2[j-1])
                i -= 1
                j -= 1
            elif direction & UP:
                aligned1.append(self.seq1[i-1])
                aligned2.append(GAP)
                i -= 1
            elif direction & LEFT:
                aligned1.append(GAP)
                aligned2.append(self.seq2[j-1])
                j -= 1
            else:
                break
        
        return ''.join(reversed(aligned1)), ''.join(reversed(aligned2))
    
    def _traceback_all(self, i, j, current1, current2, solutions):
        if len(solutions) >= self.max_solutions:
            return
        
        if i == 0 and j == 0:
            aligned1 = ''.join(reversed(current1))
            aligned2 = ''.join(reversed(current2))
            result = AlignmentResult(aligned1, aligned2, self.alignment_score)
            solutions.add(result)
            return
        
        direction = self.traceback_matrix[i, j]
        
        if direction & DIAG:
            current1.append(self.seq1[i-1])
            current2.append(self.seq2[j-1])
            self._traceback_all(i-1, j-1, current1, current2, solutions)
            current1.pop()
            current2.pop()
        
        if direction & UP:
            current1.append(self.seq1[i-1])
            current2.append(GAP)
            self._traceback_all(i-1, j, current1, current2, solutions)
            current1.pop()
            current2.pop()
        
        if direction & LEFT:
            current1.append(GAP)
            current2.append(self.seq2[j-1])
            self._traceback_all(i, j-1, current1, current2, solutions)
            current1.pop()
            current2.pop()
    
    def align(self):
        if self.use_rolling:
            self._compute_rolling_matrix()
        else:
            self._compute_full_matrix()
        
        if self.find_all_solutions:
            solutions = set()
            self._traceback_all(self.n, self.m, [], [], solutions)
            self.alignment_results = list(solutions)
        else:
            aligned1, aligned2 = self._traceback_single(self.n, self.m)
            self.alignment_results = [AlignmentResult(aligned1, aligned2, self.alignment_score)]
        
        return self.alignment_results
    
    def get_match_line(self, result=None):
        if result is None:
            if not self.alignment_results:
                return ""
            result = self.alignment_results[0]
        
        match_line = []
        for a, b in zip(result.aligned_seq1, result.aligned_seq2):
            if a == b:
                match_line.append('|')
            elif a != GAP and b != GAP:
                if self.sub_matrix.get_score(a, b) > 0:
                    match_line.append(':')
                else:
                    match_line.append('.')
            else:
                match_line.append(' ')
        return ''.join(match_line)

class SmithWaterman:
    def __init__(self, seq1, seq2, gap_penalty=-2, matrix_type='blosum62', seq_type='protein',
                 use_rolling=True, find_all_solutions=False, max_solutions=100):
        self.seq1 = seq1.upper()
        self.seq2 = seq2.upper()
        self.gap_penalty = gap_penalty
        self.sub_matrix = SubstitutionMatrix(matrix_type, seq_type)
        self.n = len(seq1)
        self.m = len(seq2)
        self.use_rolling = use_rolling
        self.find_all_solutions = find_all_solutions
        self.max_solutions = max_solutions
        
        self.score_matrix = None
        self.traceback_matrix = None
        self.alignment_results = []
        self.alignment_score = None
        self.max_positions = []
    
    def _compute_full_matrix(self):
        self.score_matrix = np.zeros((self.n + 1, self.m + 1), dtype=np.int32)
        self.traceback_matrix = np.zeros((self.n + 1, self.m + 1), dtype=np.int8)
        
        for i in range(1, self.n + 1):
            for j in range(1, self.m + 1):
                match_score = self.sub_matrix.get_score(self.seq1[i-1], self.seq2[j-1])
                diag = self.score_matrix[i-1, j-1] + match_score
                up = self.score_matrix[i-1, j] + self.gap_penalty
                left = self.score_matrix[i, j-1] + self.gap_penalty
                
                max_score = max(0, diag, up, left)
                self.score_matrix[i, j] = max_score
                
                if max_score == 0:
                    continue
                
                directions = 0
                if diag == max_score:
                    directions |= DIAG
                if up == max_score:
                    directions |= UP
                if left == max_score:
                    directions |= LEFT
                
                self.traceback_matrix[i, j] = directions
        
        self.alignment_score = np.max(self.score_matrix)
        max_mask = (self.score_matrix == self.alignment_score)
        self.max_positions = list(zip(*np.where(max_mask)))
    
    def _compute_rolling_matrix(self):
        prev_row = np.zeros(self.m + 1, dtype=np.int32)
        curr_row = np.zeros(self.m + 1, dtype=np.int32)
        
        self.traceback_matrix = np.zeros((self.n + 1, self.m + 1), dtype=np.int8)
        self.alignment_score = 0
        self.max_positions = []
        
        for i in range(1, self.n + 1):
            for j in range(1, self.m + 1):
                match_score = self.sub_matrix.get_score(self.seq1[i-1], self.seq2[j-1])
                diag = prev_row[j-1] + match_score
                up = prev_row[j] + self.gap_penalty
                left = curr_row[j-1] + self.gap_penalty
                
                max_score = max(0, diag, up, left)
                curr_row[j] = max_score
                
                if max_score > self.alignment_score:
                    self.alignment_score = max_score
                    self.max_positions = [(i, j)]
                elif max_score == self.alignment_score and max_score > 0:
                    self.max_positions.append((i, j))
                
                if max_score == 0:
                    continue
                
                directions = 0
                if diag == max_score:
                    directions |= DIAG
                if up == max_score:
                    directions |= UP
                if left == max_score:
                    directions |= LEFT
                
                self.traceback_matrix[i, j] = directions
            
            prev_row, curr_row = curr_row, np.zeros(self.m + 1, dtype=np.int32)
        
        self.score_matrix = None
    
    def _traceback_single(self, i, j):
        aligned1 = []
        aligned2 = []
        start_i, start_j = i, j
        
        while (i > 0 or j > 0) and self.traceback_matrix[i, j] != 0:
            direction = self.traceback_matrix[i, j]
            
            if direction & DIAG:
                aligned1.append(self.seq1[i-1])
                aligned2.append(self.seq2[j-1])
                i -= 1
                j -= 1
            elif direction & UP:
                aligned1.append(self.seq1[i-1])
                aligned2.append(GAP)
                i -= 1
            elif direction & LEFT:
                aligned1.append(GAP)
                aligned2.append(self.seq2[j-1])
                j -= 1
            else:
                break
        
        return (''.join(reversed(aligned1)), ''.join(reversed(aligned2)),
                (i, j), (start_i, start_j))
    
    def _traceback_all_from_pos(self, i, j, current1, current2, solutions):
        if len(solutions) >= self.max_solutions:
            return
        
        if (i == 0 and j == 0) or self.traceback_matrix[i, j] == 0:
            aligned1 = ''.join(reversed(current1))
            aligned2 = ''.join(reversed(current2))
            result = AlignmentResult(aligned1, aligned2, self.alignment_score)
            solutions.add(result)
            return
        
        direction = self.traceback_matrix[i, j]
        
        if direction & DIAG:
            current1.append(self.seq1[i-1])
            current2.append(self.seq2[j-1])
            self._traceback_all_from_pos(i-1, j-1, current1, current2, solutions)
            current1.pop()
            current2.pop()
        
        if direction & UP:
            current1.append(self.seq1[i-1])
            current2.append(GAP)
            self._traceback_all_from_pos(i-1, j, current1, current2, solutions)
            current1.pop()
            current2.pop()
        
        if direction & LEFT:
            current1.append(GAP)
            current2.append(self.seq2[j-1])
            self._traceback_all_from_pos(i, j-1, current1, current2, solutions)
            current1.pop()
            current2.pop()
    
    def align(self):
        if self.use_rolling:
            self._compute_rolling_matrix()
        else:
            self._compute_full_matrix()
        
        if self.alignment_score == 0:
            self.alignment_results = []
            return self.alignment_results
        
        if self.find_all_solutions:
            solutions = set()
            for (i, j) in self.max_positions:
                self._traceback_all_from_pos(i, j, [], [], solutions)
                if len(solutions) >= self.max_solutions:
                    break
            self.alignment_results = list(solutions)
        else:
            if self.max_positions:
                i, j = self.max_positions[0]
                aligned1, aligned2, start_pos, end_pos = self._traceback_single(i, j)
                self.start_pos = start_pos
                self.end_pos = end_pos
                self.alignment_results = [AlignmentResult(aligned1, aligned2, self.alignment_score)]
        
        return self.alignment_results
    
    def get_match_line(self, result=None):
        if result is None:
            if not self.alignment_results:
                return ""
            result = self.alignment_results[0]
        
        match_line = []
        for a, b in zip(result.aligned_seq1, result.aligned_seq2):
            if a == b:
                match_line.append('|')
            elif a != GAP and b != GAP:
                if self.sub_matrix.get_score(a, b) > 0:
                    match_line.append(':')
                else:
                    match_line.append('.')
            else:
                match_line.append(' ')
        return ''.join(match_line)
