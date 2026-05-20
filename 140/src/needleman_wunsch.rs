use pyo3::prelude::*;
use crate::alignment::{AlignmentResult, AlignmentParams, rust_AlignmentResult};
use crate::simd;

#[derive(Debug, Clone)]
pub struct NeedlemanWunsch {
    params: AlignmentParams,
}

impl NeedlemanWunsch {
    pub fn new(
        match_score: i32,
        mismatch_score: i32,
        gap_open: i32,
        gap_extend: i32,
        use_affine: bool,
    ) -> Self {
        Self {
            params: AlignmentParams {
                match_score,
                mismatch_score,
                gap_open,
                gap_extend,
                use_affine,
            },
        }
    }

    pub fn align(&self, seq1: &str, seq2: &str) -> AlignmentResult {
        if self.params.use_affine {
            self.align_affine(seq1, seq2)
        } else {
            self.align_linear(seq1, seq2)
        }
    }

    fn align_linear(&self, seq1: &str, seq2: &str) -> AlignmentResult {
        let seq1_bytes = seq1.as_bytes();
        let seq2_bytes = seq2.as_bytes();
        let n = seq1_bytes.len();
        let m = seq2_bytes.len();

        let mut prev_row = vec![0i32; n + 1];
        let mut curr_row = vec![0i32; n + 1];

        for i in 0..=n {
            prev_row[i] = (i as i32) * self.params.gap_open;
        }

        for j in 1..=m {
            curr_row[0] = (j as i32) * self.params.gap_open;

            unsafe {
                simd::compute_row_simd(
                    seq1_bytes,
                    seq2_bytes,
                    &mut curr_row,
                    &prev_row,
                    j,
                    self.params.match_score,
                    self.params.mismatch_score,
                    self.params.gap_open,
                );
            }

            std::mem::swap(&mut prev_row, &mut curr_row);
        }

        let score = prev_row[n];
        let mut aligned1 = Vec::with_capacity(n + m);
        let mut aligned2 = Vec::with_capacity(n + m);
        let mut i = n;
        let mut j = m;

        let mut dp = vec![vec![0i32; m + 1]; n + 1];
        for i in 0..=n {
            dp[i][0] = (i as i32) * self.params.gap_open;
        }
        for j in 0..=m {
            dp[0][j] = (j as i32) * self.params.gap_open;
        }
        for j in 1..=m {
            for i in 1..=n {
                let s = if seq1_bytes[i - 1] == seq2_bytes[j - 1] {
                    self.params.match_score
                } else {
                    self.params.mismatch_score
                };
                let diagonal = dp[i - 1][j - 1] + s;
                let up = dp[i - 1][j] + self.params.gap_open;
                let left = dp[i][j - 1] + self.params.gap_open;
                dp[i][j] = diagonal.max(up).max(left);
            }
        }

        while i > 0 || j > 0 {
            if i > 0 && j > 0 {
                let s = if seq1_bytes[i - 1] == seq2_bytes[j - 1] {
                    self.params.match_score
                } else {
                    self.params.mismatch_score
                };
                if dp[i][j] == dp[i - 1][j - 1] + s {
                    aligned1.push(seq1_bytes[i - 1]);
                    aligned2.push(seq2_bytes[j - 1]);
                    i -= 1;
                    j -= 1;
                    continue;
                }
            }
            if i > 0 && dp[i][j] == dp[i - 1][j] + self.params.gap_open {
                aligned1.push(seq1_bytes[i - 1]);
                aligned2.push(b'-');
                i -= 1;
            } else {
                aligned1.push(b'-');
                aligned2.push(seq2_bytes[j - 1]);
                j -= 1;
            }
        }

        aligned1.reverse();
        aligned2.reverse();

        AlignmentResult {
            aligned_seq1: String::from_utf8(aligned1).unwrap_or_default(),
            aligned_seq2: String::from_utf8(aligned2).unwrap_or_default(),
            score,
            start1: 0,
            end1: n,
            start2: 0,
            end2: m,
        }
    }

    fn align_affine(&self, seq1: &str, seq2: &str) -> AlignmentResult {
        let seq1_bytes = seq1.as_bytes();
        let seq2_bytes = seq2.as_bytes();
        let n = seq1_bytes.len();
        let m = seq2_bytes.len();

        let mut m_matrix = vec![vec![0i32; m + 1]; n + 1];
        let mut x_matrix = vec![vec![0i32; m + 1]; n + 1];
        let mut y_matrix = vec![vec![0i32; m + 1]; n + 1];

        let gap_open = self.params.gap_open;
        let gap_extend = self.params.gap_extend;

        for i in 1..=n {
            x_matrix[i][0] = gap_open + (i as i32 - 1) * gap_extend;
            m_matrix[i][0] = i32::MIN / 2;
            y_matrix[i][0] = i32::MIN / 2;
        }
        for j in 1..=m {
            y_matrix[0][j] = gap_open + (j as i32 - 1) * gap_extend;
            m_matrix[0][j] = i32::MIN / 2;
            x_matrix[0][j] = i32::MIN / 2;
        }

        for j in 1..=m {
            for i in 1..=n {
                let s = if seq1_bytes[i - 1] == seq2_bytes[j - 1] {
                    self.params.match_score
                } else {
                    self.params.mismatch_score
                };

                let from_m = m_matrix[i - 1][j - 1] + s;
                let from_x = x_matrix[i - 1][j - 1] + s;
                let from_y = y_matrix[i - 1][j - 1] + s;
                m_matrix[i][j] = from_m.max(from_x).max(from_y);

                let open_from_m = m_matrix[i - 1][j] + gap_open;
                let extend_from_x = x_matrix[i - 1][j] + gap_extend;
                x_matrix[i][j] = open_from_m.max(extend_from_x);

                let open_from_m_y = m_matrix[i][j - 1] + gap_open;
                let extend_from_y = y_matrix[i][j - 1] + gap_extend;
                y_matrix[i][j] = open_from_m_y.max(extend_from_y);
            }
        }

        let score = m_matrix[n][m].max(x_matrix[n][m]).max(y_matrix[n][m]);

        let mut aligned1 = Vec::with_capacity(n + m);
        let mut aligned2 = Vec::with_capacity(n + m);
        let mut i = n;
        let mut j = m;

        let mut current_matrix = 0;
        if score == x_matrix[n][m] {
            current_matrix = 1;
        } else if score == y_matrix[n][m] {
            current_matrix = 2;
        }

        while i > 0 || j > 0 {
            match current_matrix {
                0 => {
                    let s = if i > 0 && j > 0 && seq1_bytes[i - 1] == seq2_bytes[j - 1] {
                        self.params.match_score
                    } else {
                        self.params.mismatch_score
                    };
                    aligned1.push(seq1_bytes[i - 1]);
                    aligned2.push(seq2_bytes[j - 1]);
                    if i > 1 && j > 1 {
                        if m_matrix[i - 1][j - 1] + s == m_matrix[i][j] {
                            current_matrix = 0;
                        } else if x_matrix[i - 1][j - 1] + s == m_matrix[i][j] {
                            current_matrix = 1;
                        } else {
                            current_matrix = 2;
                        }
                    }
                    i -= 1;
                    j -= 1;
                }
                1 => {
                    aligned1.push(seq1_bytes[i - 1]);
                    aligned2.push(b'-');
                    if i > 1 {
                        if m_matrix[i - 1][j] + gap_open == x_matrix[i][j] {
                            current_matrix = 0;
                        } else {
                            current_matrix = 1;
                        }
                    }
                    i -= 1;
                }
                2 => {
                    aligned1.push(b'-');
                    aligned2.push(seq2_bytes[j - 1]);
                    if j > 1 {
                        if m_matrix[i][j - 1] + gap_open == y_matrix[i][j] {
                            current_matrix = 0;
                        } else {
                            current_matrix = 2;
                        }
                    }
                    j -= 1;
                }
                _ => break,
            }
        }

        aligned1.reverse();
        aligned2.reverse();

        AlignmentResult {
            aligned_seq1: String::from_utf8(aligned1).unwrap_or_default(),
            aligned_seq2: String::from_utf8(aligned2).unwrap_or_default(),
            score,
            start1: 0,
            end1: n,
            start2: 0,
            end2: m,
        }
    }
}

impl Default for NeedlemanWunsch {
    fn default() -> Self {
        Self::new(2, -1, -5, -1, true)
    }
}

#[pyclass(name = "NeedlemanWunsch")]
#[derive(Debug, Clone)]
pub struct rust_NeedlemanWunsch {
    inner: NeedlemanWunsch,
}

#[pymethods]
impl rust_NeedlemanWunsch {
    #[new]
    #[pyo3(signature = (match_score=2, mismatch_score=-1, gap_open=-5, gap_extend=-1, use_affine=true))]
    fn new(
        match_score: i32,
        mismatch_score: i32,
        gap_open: i32,
        gap_extend: i32,
        use_affine: bool,
    ) -> Self {
        Self {
            inner: NeedlemanWunsch::new(match_score, mismatch_score, gap_open, gap_extend, use_affine),
        }
    }

    pub fn align(&self, seq1: &str, seq2: &str) -> rust_AlignmentResult {
        self.inner.align(seq1, seq2).into()
    }
}
