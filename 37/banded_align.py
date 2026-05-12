from scoring import ScoringMatrix
from align import AlignmentResult, generate_cigar

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


def _in_band(i, j, k, shift=0):
    j_aligned = j - shift
    return -k <= (i - j_aligned) <= k


def banded_smith_waterman(query, ref, scoring=None, band_width=50, center_shift=0, use_gpu=None):
    if scoring is None:
        scoring = ScoringMatrix()
    
    if use_gpu is None:
        use_gpu = USE_CUPY
    
    if use_gpu and xp is not None:
        return _banded_sw_numpy_cupy(query, ref, scoring, band_width, center_shift)
    else:
        return _banded_sw_python(query, ref, scoring, band_width, center_shift)


def _banded_sw_python(query, ref, scoring, band_width, center_shift):
    m = len(query)
    n = len(ref)
    k = band_width
    
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
        j_start = max(1, i - k - center_shift)
        j_end = min(n + 1, i + k - center_shift + 1)
        
        for j in range(j_start, j_end):
            if not _in_band(i, j, k, center_shift):
                continue
            
            match = dp[i - 1][j - 1] + scoring.score(query[i - 1], ref[j - 1])
            
            if _in_band(i - 1, j, k, center_shift):
                delete = dp[i - 1][j] + scoring.gap_extend
            else:
                delete = float('-inf')
            
            if _in_band(i, j - 1, k, center_shift):
                insert = dp[i][j - 1] + scoring.gap_extend
            else:
                insert = float('-inf')
            
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
        
        if prev_i == 0 and prev_j == 0 and dp[i][j] != 0:
            break
        
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


def _banded_sw_numpy_cupy(query, ref, scoring, band_width, center_shift):
    m = len(query)
    n = len(ref)
    k = band_width
    
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
        j_start = max(1, i - k - center_shift)
        j_end = min(n + 1, i + k - center_shift + 1)
        
        for j in range(j_start, j_end):
            if not _in_band(i, j, k, center_shift):
                continue
            
            match = dp[i - 1, j - 1] + scoring.score(query[i - 1], ref[j - 1])
            
            if _in_band(i - 1, j, k, center_shift):
                delete = dp[i - 1, j] + scoring.gap_extend
            else:
                delete = -1000000
            
            if _in_band(i, j - 1, k, center_shift):
                insert = dp[i, j - 1] + scoring.gap_extend
            else:
                insert = -1000000
            
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
        
        if prev_i == 0 and prev_j == 0 and dp[i, j] != 0:
            break
        
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


def estimate_band_width(query_len, ref_len, expected_identity=0.8):
    max_len = max(query_len, ref_len)
    min_len = min(query_len, ref_len)
    divergence = 1.0 - expected_identity
    gaps = int(divergence * min_len) + 5
    return min(gaps, max_len // 4)


def long_read_alignment(query, ref, scoring=None, initial_band=100, use_gpu=None):
    if scoring is None:
        scoring = ScoringMatrix()
    
    result = banded_smith_waterman(
        query=query,
        ref=ref,
        scoring=scoring,
        band_width=initial_band,
        use_gpu=use_gpu
    )
    
    return result
