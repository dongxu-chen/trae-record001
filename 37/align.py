from scoring import ScoringMatrix

try:
    import cupy as xp
    USE_CUPY = True
except ImportError:
    try:
        import numpy as xp
        USE_CUPY = False
    except ImportError:
        USE_CUPY = False
        xp = None


class AlignmentResult:
    def __init__(self, query_aligned, ref_aligned, score, start_query, end_query, start_ref, end_ref, cigar=None, aligned_using_gpu=False):
        self.query_aligned = query_aligned
        self.ref_aligned = ref_aligned
        self.score = score
        self.start_query = start_query
        self.end_query = end_query
        self.start_ref = start_ref
        self.end_ref = end_ref
        self.cigar = cigar
        self.aligned_using_gpu = aligned_using_gpu


def _smith_waterman_python(query, ref, scoring):
    m = len(query)
    n = len(ref)
    
    if m == 0 or n == 0:
        return AlignmentResult(
            query_aligned=query if query else '',
            ref_aligned=ref if ref else '',
            score=0,
            start_query=0,
            end_query=0,
            start_ref=0,
            end_ref=0,
            cigar='*',
            aligned_using_gpu=False
        )
    
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    traceback = [[(0, 0)] * (n + 1) for _ in range(m + 1)]
    
    max_score = 0
    max_pos = (0, 0)
    
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            match = dp[i - 1][j - 1] + scoring.score(query[i - 1], ref[j - 1])
            delete = dp[i - 1][j] + scoring.gap_extend
            insert = dp[i][j - 1] + scoring.gap_extend
            dp[i][j] = max(0, match, delete, insert)
            
            if dp[i][j] == 0:
                traceback[i][j] = (0, 0)
            elif dp[i][j] == match:
                traceback[i][j] = (i - 1, j - 1)
            elif dp[i][j] == delete:
                traceback[i][j] = (i - 1, j)
            else:
                traceback[i][j] = (i, j - 1)
            
            if dp[i][j] > max_score:
                max_score = dp[i][j]
                max_pos = (i, j)
    
    if max_score == 0:
        return AlignmentResult(
            query_aligned=query,
            ref_aligned='-' * len(query),
            score=0,
            start_query=0,
            end_query=0,
            start_ref=0,
            end_ref=0,
            cigar='*',
            aligned_using_gpu=False
        )
    
    aligned_query = []
    aligned_ref = []
    i, j = max_pos
    end_query, end_ref = i - 1, j - 1
    
    while i > 0 and j > 0 and dp[i][j] != 0:
        prev_i, prev_j = traceback[i][j]
        
        if prev_i == i - 1 and prev_j == j - 1:
            aligned_query.append(query[i - 1])
            aligned_ref.append(ref[j - 1])
        elif prev_i == i - 1 and prev_j == j:
            aligned_query.append(query[i - 1])
            aligned_ref.append('-')
        else:
            aligned_query.append('-')
            aligned_ref.append(ref[j - 1])
        
        i, j = prev_i, prev_j
    
    aligned_query = ''.join(reversed(aligned_query))
    aligned_ref = ''.join(reversed(aligned_ref))
    start_query, start_ref = i, j
    
    cigar = generate_cigar(aligned_query, aligned_ref)
    
    return AlignmentResult(
        query_aligned=aligned_query,
        ref_aligned=aligned_ref,
        score=max_score,
        start_query=start_query,
        end_query=end_query,
        start_ref=start_ref,
        end_ref=end_ref,
        cigar=cigar,
        aligned_using_gpu=False
    )


def _smith_waterman_numpy_cupy(query, ref, scoring):
    m = len(query)
    n = len(ref)
    
    if m == 0 or n == 0:
        return AlignmentResult(
            query_aligned=query if query else '',
            ref_aligned=ref if ref else '',
            score=0,
            start_query=0,
            end_query=0,
            start_ref=0,
            end_ref=0,
            cigar='*',
            aligned_using_gpu=USE_CUPY
        )
    
    dp = xp.zeros((m + 1, n + 1), dtype=xp.int32)
    traceback_i = xp.zeros((m + 1, n + 1), dtype=xp.int32)
    traceback_j = xp.zeros((m + 1, n + 1), dtype=xp.int32)
    
    max_score = 0
    max_i, max_j = 0, 0
    
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            match_score = scoring.score(query[i - 1], ref[j - 1])
            match = dp[i - 1, j - 1] + match_score
            delete = dp[i - 1, j] + scoring.gap_extend
            insert = dp[i, j - 1] + scoring.gap_extend
            current = max(0, match, delete, insert)
            dp[i, j] = current
            
            if current == 0:
                traceback_i[i, j] = 0
                traceback_j[i, j] = 0
            elif current == match:
                traceback_i[i, j] = i - 1
                traceback_j[i, j] = j - 1
            elif current == delete:
                traceback_i[i, j] = i - 1
                traceback_j[i, j] = j
            else:
                traceback_i[i, j] = i
                traceback_j[i, j] = j - 1
            
            if current > max_score:
                max_score = current
                max_i, max_j = i, j
    
    if max_score == 0:
        return AlignmentResult(
            query_aligned=query,
            ref_aligned='-' * len(query),
            score=0,
            start_query=0,
            end_query=0,
            start_ref=0,
            end_ref=0,
            cigar='*',
            aligned_using_gpu=USE_CUPY
        )
    
    aligned_query = []
    aligned_ref = []
    i, j = max_i, max_j
    end_query, end_ref = i - 1, j - 1
    
    while i > 0 and j > 0 and dp[i, j] != 0:
        prev_i = int(traceback_i[i, j])
        prev_j = int(traceback_j[i, j])
        
        if prev_i == i - 1 and prev_j == j - 1:
            aligned_query.append(query[i - 1])
            aligned_ref.append(ref[j - 1])
        elif prev_i == i - 1 and prev_j == j:
            aligned_query.append(query[i - 1])
            aligned_ref.append('-')
        else:
            aligned_query.append('-')
            aligned_ref.append(ref[j - 1])
        
        i, j = prev_i, prev_j
    
    aligned_query = ''.join(reversed(aligned_query))
    aligned_ref = ''.join(reversed(aligned_ref))
    start_query, start_ref = i, j
    
    cigar = generate_cigar(aligned_query, aligned_ref)
    
    return AlignmentResult(
        query_aligned=aligned_query,
        ref_aligned=aligned_ref,
        score=int(max_score),
        start_query=start_query,
        end_query=end_query,
        start_ref=start_ref,
        end_ref=end_ref,
        cigar=cigar,
        aligned_using_gpu=USE_CUPY
    )


def smith_waterman(query, ref, scoring=None, use_gpu=None):
    if scoring is None:
        scoring = ScoringMatrix()
    
    if use_gpu is None:
        use_gpu = USE_CUPY
    
    if use_gpu and xp is not None:
        return _smith_waterman_numpy_cupy(query, ref, scoring)
    else:
        return _smith_waterman_python(query, ref, scoring)


def generate_cigar(query_aligned, ref_aligned):
    if query_aligned == '' or ref_aligned == '':
        return '*'
    
    cigar_parts = []
    count = 0
    op = None
    
    for q_char, r_char in zip(query_aligned, ref_aligned):
        if q_char == '-':
            current_op = 'D'
        elif r_char == '-':
            current_op = 'I'
        elif q_char == r_char:
            current_op = 'M'
        else:
            current_op = 'M'
        
        if current_op == op:
            count += 1
        else:
            if op is not None:
                cigar_parts.append(f"{count}{op}")
            op = current_op
            count = 1
    
    if op is not None:
        cigar_parts.append(f"{count}{op}")
    
    return ''.join(cigar_parts)


def is_gpu_available():
    return USE_CUPY and xp is not None


def get_backend_info():
    if USE_CUPY:
        return 'Cupy (GPU)'
    elif xp is not None:
        return 'NumPy (CPU)'
    else:
        return 'Pure Python'
