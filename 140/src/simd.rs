use std::arch::x86_64::*;

#[inline(always)]
pub fn score_match_mismatch_simd(a: u8, b: u8, match_score: i32, mismatch_score: i32) -> i32 {
    if a == b { match_score } else { mismatch_score }
}

pub unsafe fn compute_row_simd(
    seq1_bytes: &[u8],
    seq2_bytes: &[u8],
    row: &mut [i32],
    prev_row: &[i32],
    j: usize,
    match_score: i32,
    mismatch_score: i32,
    gap: i32,
) {
    let b = seq2_bytes[j - 1];
    let b_splat = _mm_set1_epi8(b as i8);
    let match_splat = _mm_set1_epi32(match_score);
    let mismatch_splat = _mm_set1_epi32(mismatch_score);
    let gap_splat = _mm_set1_epi32(gap);

    let n = seq1_bytes.len();
    let mut i = 1;
    while i <= n {
        if i + 15 <= n {
            let a_chunk = &seq1_bytes[i - 1..i + 15];
            let mut a_arr = [0u8; 16];
            a_arr.copy_from_slice(a_chunk);
            
            let a_vec = _mm_loadu_si128(a_arr.as_ptr() as *const _);
            let cmp = _mm_cmpeq_epi8(a_vec, b_splat);
            
            let mask = _mm_movemask_epi8(cmp) as u32;
            
            for k in 0..16 {
                let idx = i + k;
                if idx > n {
                    break;
                }
                let score = if (mask & (1 << k)) != 0 {
                    match_score
                } else {
                    mismatch_score
                };
                
                let diagonal = prev_row[idx - 1] + score;
                let up = prev_row[idx] + gap;
                let left = row[idx - 1] + gap;
                
                row[idx] = diagonal.max(up).max(left);
            }
            i += 16;
        } else {
            let a = seq1_bytes[i - 1];
            let score = if a == b { match_score } else { mismatch_score };
            
            let diagonal = prev_row[i - 1] + score;
            let up = prev_row[i] + gap;
            let left = row[i - 1] + gap;
            
            row[i] = diagonal.max(up).max(left);
            i += 1;
        }
    }
}

pub unsafe fn compute_row_affine_simd(
    seq1_bytes: &[u8],
    seq2_bytes: &[u8],
    m_row: &mut [i32],
    x_row: &mut [i32],
    y_row: &mut [i32],
    m_prev: &[i32],
    x_prev: &[i32],
    y_prev: &[i32],
    j: usize,
    match_score: i32,
    mismatch_score: i32,
    gap_open: i32,
    gap_extend: i32,
) {
    let b = seq2_bytes[j - 1];
    let n = seq1_bytes.len();
    let mut i = 1;
    
    while i <= n {
        if i + 7 <= n {
            for k in 0..8 {
                let idx = i + k;
                if idx > n {
                    break;
                }
                
                let a = seq1_bytes[idx - 1];
                let s = if a == b { match_score } else { mismatch_score };
                
                let m_prev_val = m_prev[idx - 1];
                let x_prev_val = x_prev[idx - 1];
                let y_prev_val = y_prev[idx - 1];
                
                let from_m = m_prev_val + s;
                let from_x = x_prev_val + s;
                let from_y = y_prev_val + s;
                m_row[idx] = from_m.max(from_x).max(from_y);
                
                let open_from_m = m_prev[idx] + gap_open;
                let extend_from_x = x_prev[idx] + gap_extend;
                x_row[idx] = open_from_m.max(extend_from_x);
                
                let open_from_m_y = m_row[idx - 1] + gap_open;
                let extend_from_y = y_row[idx - 1] + gap_extend;
                y_row[idx] = open_from_m_y.max(extend_from_y);
            }
            i += 8;
        } else {
            let a = seq1_bytes[i - 1];
            let s = if a == b { match_score } else { mismatch_score };
            
            let from_m = m_prev[i - 1] + s;
            let from_x = x_prev[i - 1] + s;
            let from_y = y_prev[i - 1] + s;
            m_row[i] = from_m.max(from_x).max(from_y);
            
            let open_from_m = m_prev[i] + gap_open;
            let extend_from_x = x_prev[i] + gap_extend;
            x_row[i] = open_from_m.max(extend_from_x);
            
            let open_from_m_y = m_row[i - 1] + gap_open;
            let extend_from_y = y_row[i - 1] + gap_extend;
            y_row[i] = open_from_m_y.max(extend_from_y);
            
            i += 1;
        }
    }
}
