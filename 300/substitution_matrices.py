import numpy as np

IUPAC_AMINO_ACIDS = ['A', 'R', 'N', 'D', 'C', 'Q', 'E', 'G', 'H', 'I', 'L', 'K', 'M', 'F', 'P', 'S', 'T', 'W', 'Y', 'V', 'B', 'Z', 'X', '*']
IUPAC_DNA_BASES = ['A', 'T', 'C', 'G', 'U', 'R', 'Y', 'K', 'M', 'S', 'W', 'B', 'D', 'H', 'V', 'N']

BLOSUM62_STANDARD = np.array([
    [4, -1, -2, -2, 0, -1, -1, 0, -2, -1, -1, -1, -1, -2, -1, 1, 0, -3, -2, 0],
    [-1, 5, 0, -2, -3, 1, 0, -2, 0, -3, -2, 2, -1, -3, -2, -1, -1, -3, -2, -3],
    [-2, 0, 6, 1, -3, 0, 0, 0, 1, -3, -3, 0, -2, -3, -2, 1, 0, -4, -2, -3],
    [-2, -2, 1, 6, -3, 0, 2, -1, -1, -3, -4, -1, -3, -3, -1, 0, -1, -4, -3, -3],
    [0, -3, -3, -3, 9, -3, -4, -3, -3, -1, -1, -3, -1, -2, -3, -1, -1, -2, -2, -1],
    [-1, 1, 0, 0, -3, 5, 2, -2, 0, -3, -2, 1, 0, -3, -1, 0, -1, -2, -1, -2],
    [-1, 0, 0, 2, -4, 2, 5, -2, 0, -3, -3, 1, -2, -3, -1, 0, -1, -3, -2, -2],
    [0, -2, 0, -1, -3, -2, -2, 6, -2, -4, -4, -2, -3, -3, -2, 0, -2, -2, -3, -3],
    [-2, 0, 1, -1, -3, 0, 0, -2, 8, -3, -3, -1, -2, -1, -2, -1, -2, -2, 2, -3],
    [-1, -3, -3, -3, -1, -3, -3, -4, -3, 4, 2, -3, 1, 0, -3, -2, -1, -3, -1, 3],
    [-1, -2, -3, -4, -1, -2, -3, -4, -3, 2, 4, -2, 2, 0, -3, -2, -1, -2, -1, 1],
    [-1, 2, 0, -1, -3, 1, 1, -2, -1, -3, -2, 5, -1, -3, -1, 0, -1, -3, -2, -2],
    [-1, -1, -2, -3, -1, 0, -2, -3, -2, 1, 2, -1, 5, 0, -2, -1, -1, -1, -1, 1],
    [-2, -3, -3, -3, -2, -3, -3, -3, -1, 0, 0, -3, 0, 6, -4, -2, -2, 1, 3, -1],
    [-1, -2, -2, -1, -3, -1, -1, -2, -2, -3, -3, -1, -2, -4, 7, -1, -1, -4, -3, -2],
    [1, -1, 1, 0, -1, 0, 0, 0, -1, -2, -2, 0, -1, -2, -1, 4, 1, -3, -2, -2],
    [0, -1, 0, -1, -1, -1, -1, -2, -2, -1, -1, -1, -1, -2, -1, 1, 5, -2, -2, 0],
    [-3, -3, -4, -4, -2, -2, -3, -2, -2, -3, -2, -3, -1, 1, -4, -3, -2, 11, 2, -3],
    [-2, -2, -2, -3, -2, -1, -2, -3, 2, -1, -1, -2, -1, 3, -3, -2, -2, 2, 7, -1],
    [0, -3, -3, -3, -1, -2, -2, -3, -3, 3, 1, -2, 1, -1, -2, -2, 0, -3, -1, 4]
], dtype=np.int32)

PAM250_STANDARD = np.array([
    [2, -2, 0, 0, -2, 0, 0, 1, -1, -1, -2, -1, -1, -3, 1, 1, 1, -6, -3, 0],
    [-2, 6, 0, -1, -4, 1, -1, -3, 2, -2, -3, 3, 0, -4, -1, 0, -1, 2, -4, -2],
    [0, 0, 2, 2, -4, 1, 1, 0, 2, -2, -3, 1, -2, -3, 0, 1, 0, -4, -2, -2],
    [0, -1, 2, 4, -5, 2, 3, 1, 1, -2, -4, 0, -3, -6, -1, 0, 0, -7, -4, -2],
    [-2, -4, -4, -5, 12, -5, -5, -3, -3, -2, -6, -5, -5, -4, -3, 0, -2, -8, 0, -2],
    [0, 1, 1, 2, -5, 4, 2, -1, 3, -2, -2, 1, -1, -5, 0, -1, -1, -5, -4, -2],
    [0, -1, 1, 3, -5, 2, 4, 0, 1, -2, -3, 0, -2, -5, -1, 0, 0, -7, -4, -2],
    [1, -3, 0, 1, -3, -1, 0, 5, -2, -3, -4, -2, -3, -4, 0, 1, 0, -7, -5, -1],
    [-1, 2, 2, 1, -3, 3, 1, -2, 6, -2, -2, 0, -2, -2, 0, -1, -1, -3, 0, -2],
    [-1, -2, -2, -2, -2, -2, -2, -3, -2, 5, 2, -2, 2, 1, -2, -1, 0, -5, -1, 4],
    [-2, -3, -3, -4, -6, -2, -3, -4, -2, 2, 6, -3, 4, 2, -3, -3, -2, -2, -1, 2],
    [-1, 3, 1, 0, -5, 1, 0, -2, 0, -2, -3, 5, 0, -5, -1, 0, 0, -3, -4, -2],
    [-1, 0, -2, -3, -5, -1, -2, -3, -2, 2, 4, 0, 6, 0, -2, -2, -1, -4, -2, 2],
    [-3, -4, -3, -6, -4, -5, -5, -4, -2, 1, 2, -5, 0, 9, -5, -3, -3, 0, 7, -1],
    [1, -1, 0, -1, -3, 0, -1, 0, 0, -2, -3, -1, -2, -5, 6, 1, 0, -6, -5, -1],
    [1, 0, 1, 0, 0, -1, 0, 1, -1, -1, -3, 0, -2, -3, 1, 2, 1, -2, -3, -1],
    [1, -1, 0, 0, -2, -1, 0, 0, -1, 0, -2, 0, -1, -3, 0, 1, 3, -5, -3, 0],
    [-6, 2, -4, -7, -8, -5, -7, -7, -3, -5, -2, -3, -4, 0, -6, -2, -5, 17, 0, -6],
    [-3, -4, -2, -4, 0, -4, -4, -5, 0, -1, -1, -4, -2, 7, -5, -3, -3, 0, 10, -2],
    [0, -2, -2, -2, -2, -2, -2, -1, -2, 4, 2, -2, 2, -1, -1, -1, 0, -6, -2, 4]
], dtype=np.int32)

def expand_protein_matrix(standard_matrix):
    n = len(IUPAC_AMINO_ACIDS)
    full_matrix = np.zeros((n, n), dtype=np.int32)
    n_std = standard_matrix.shape[0]
    
    full_matrix[:n_std, :n_std] = standard_matrix
    
    for i in range(n_std, n):
        for j in range(n_std):
            aa_i = IUPAC_AMINO_ACIDS[i]
            aa_j = IUPAC_AMINO_ACIDS[j]
            
            if aa_i == 'B':
                n_score = standard_matrix[2, j]
                d_score = standard_matrix[3, j]
                full_matrix[i, j] = min(n_score, d_score)
            elif aa_i == 'Z':
                q_score = standard_matrix[5, j]
                e_score = standard_matrix[6, j]
                full_matrix[i, j] = min(q_score, e_score)
            elif aa_i == 'X':
                full_matrix[i, j] = -1
            elif aa_i == '*':
                full_matrix[i, j] = -4
    
    for i in range(n):
        for j in range(n_std, n):
            full_matrix[i, j] = full_matrix[j, i]
    
    full_matrix[20, 20] = -1
    full_matrix[21, 21] = -1
    full_matrix[22, 22] = -1
    full_matrix[23, 23] = 1
    
    return full_matrix

BLOSUM62_MATRIX = expand_protein_matrix(BLOSUM62_STANDARD)
PAM250_MATRIX = expand_protein_matrix(PAM250_STANDARD)

def create_dna_matrix():
    n = len(IUPAC_DNA_BASES)
    matrix = np.full((n, n), -1, dtype=np.int32)
    
    for i in range(4):
        matrix[i, i] = 2
    
    for i in range(4, n):
        for j in range(4):
            base_i = IUPAC_DNA_BASES[i]
            base_j = IUPAC_DNA_BASES[j]
            
            matches = {
                'R': ['A', 'G'],
                'Y': ['C', 'T'],
                'K': ['G', 'T'],
                'M': ['A', 'C'],
                'S': ['C', 'G'],
                'W': ['A', 'T'],
                'B': ['C', 'G', 'T'],
                'D': ['A', 'G', 'T'],
                'H': ['A', 'C', 'T'],
                'V': ['A', 'C', 'G'],
                'N': ['A', 'T', 'C', 'G']
            }
            
            if base_j in matches.get(base_i, []):
                matrix[i, j] = 0
            else:
                matrix[i, j] = -1
    
    for i in range(n):
        for j in range(4, n):
            matrix[i, j] = matrix[j, i]
    
    for i in range(4, n):
        matrix[i, i] = 0
    
    matrix[15, :] = -1
    matrix[:, 15] = -1
    
    return matrix

DNA_MATRIX = create_dna_matrix()

class SubstitutionMatrix:
    def __init__(self, matrix_type='blosum62', seq_type='protein'):
        self.seq_type = seq_type.lower()
        self.matrix_type = matrix_type.lower()
        
        if self.seq_type == 'protein':
            self.alphabet = IUPAC_AMINO_ACIDS
            if self.matrix_type == 'blosum62':
                self.matrix = BLOSUM62_MATRIX
            elif self.matrix_type == 'pam250':
                self.matrix = PAM250_MATRIX
            else:
                raise ValueError(f"Unknown substitution matrix: {matrix_type}")
        elif self.seq_type == 'dna':
            self.alphabet = IUPAC_DNA_BASES
            self.matrix = DNA_MATRIX
        else:
            raise ValueError(f"Unknown sequence type: {seq_type}")
        
        self.index_map = {aa: i for i, aa in enumerate(self.alphabet)}
    
    def get_score(self, a, b):
        a = a.upper()
        b = b.upper()
        
        if a == 'U':
            a = 'T'
        if b == 'U':
            b = 'T'
        
        if a not in self.index_map or b not in self.index_map:
            return -1
        return self.matrix[self.index_map[a], self.index_map[b]]
    
    def __getitem__(self, key):
        return self.get_score(key[0], key[1])
    
    def get_alphabet(self):
        return self.alphabet
    
    def get_index(self, char):
        char = char.upper()
        return self.index_map.get(char, -1)
