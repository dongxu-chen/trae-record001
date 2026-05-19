use pyo3::prelude::*;
use crate::alignment::{AlignmentResult, AlignmentParams, rust_AlignmentResult};

#[derive(Debug, Clone)]
pub struct SmithWaterman {
    params: AlignmentParams,
}

impl SmithWaterman {
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

        let mut dp = vec![vec![0i32; m + 1]; n + 1];
        let mut max_score = 0i32;
        let mut max_i = 0usize;
        let mut max_j = 0usize;

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
                
                dp[i][j] = 0.max(diagonal.max(up).max(left));

                if dp[i][j] > max_score {
                    max_score = dp[i][j];
                    max_i = i;
                    max_j = j;
                }
            }
        }

        let mut aligned1 = Vec::with_capacity(n + m);
        let mut aligned2 = Vec::with_capacity(n + m);
        let mut i = max_i;
        let mut j = max_j;

        while i > 0 && j > 0 && dp[i][j] > 0 {
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
            } else if dp[i][j] == dp[i - 1][j] + self.params.gap_open {
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
            score: max_score,
            start1: i,
            end1: max_i,
            start2: j,
            end2: max_j,
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

        let mut max_score = 0i32;
        let mut max_i = 0usize;
        let mut max_j = 0usize;
        let mut max_mat = 0u8;

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
                m_matrix[i][j] = 0.max(from_m.max(from_x).max(from_y));

                let open_from_m = m_matrix[i - 1][j] + gap_open;
                let extend_from_x = x_matrix[i - 1][j] + gap_extend;
                x_matrix[i][j] = 0.max(open_from_m.max(extend_from_x));

                let open_from_m_y = m_matrix[i][j - 1] + gap_open;
                let extend_from_y = y_matrix[i][j - 1] + gap_extend;
                y_matrix[i][j] = 0.max(open_from_m_y.max(extend_from_y));

                let curr_max = m_matrix[i][j].max(x_matrix[i][j]).max(y_matrix[i][j]);
                if curr_max > max_score {
                    max_score = curr_max;
                    max_i = i;
                    max_j = j;
                    max_mat = if curr_max == x_matrix[i][j] {
                        1
                    } else if curr_max == y_matrix[i][j] {
                        2
                    } else {
                        0
                    };
                }
            }
        }

        let mut aligned1 = Vec::with_capacity(n + m);
        let mut aligned2 = Vec::with_capacity(n + m);
        let mut i = max_i;
        let mut j = max_j;
        let mut current_matrix = max_mat;

        while i > 0 && j > 0 {
            let current_val = match current_matrix {
                0 => m_matrix[i][j],
                1 => x_matrix[i][j],
                2 => y_matrix[i][j],
                _ => 0,
            };

            if current_val <= 0 {
                break;
            }

            match current_matrix {
                0 => {
                    let s = if seq1_bytes[i - 1] == seq2_bytes[j - 1] {
                        self.params.match_score
                    } else {
                        self.params.mismatch_score
                    };
                    aligned1.push(seq1_bytes[i - 1]);
                    aligned2.push(seq2_bytes[j - 1]);
                    
                    if m_matrix[i - 1][j - 1] + s == m_matrix[i][j] {
                        current_matrix = 0;
                    } else if x_matrix[i - 1][j - 1] + s == m_matrix[i][j] {
                        current_matrix = 1;
                    } else {
                        current_matrix = 2;
                    }
                    i -= 1;
                    j -= 1;
                }
                1 => {
                    aligned1.push(seq1_bytes[i - 1]);
                    aligned2.push(b'-');
                    
                    if m_matrix[i - 1][j] + gap_open == x_matrix[i][j] {
                        current_matrix = 0;
                    } else {
                        current_matrix = 1;
                    }
                    i -= 1;
                }
                2 => {
                    aligned1.push(b'-');
                    aligned2.push(seq2_bytes[j - 1]);
                    
                    if m_matrix[i][j - 1] + gap_open == y_matrix[i][j] {
                        current_matrix = 0;
                    } else {
                        current_matrix = 2;
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
            score: max_score,
            start1: i,
            end1: max_i,
            start2: j,
            end2: max_j,
        }
    }
}

impl Default for SmithWaterman {
    fn default() -> Self {
        Self::new(2, -1, -5, -1, true)
    }
}

#[pyclass(name = "SmithWaterman")]
#[derive(Debug, Clone)]
pub struct rust_SmithWaterman {
    inner: SmithWaterman,
}

#[pymethods]
impl rust_SmithWaterman {
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
            inner: SmithWaterman::new(match_score, mismatch_score, gap_open, gap_extend, use_affine),
        }
    }

    pub fn align(&self, seq1: &str, seq2: &str) -> rust_AlignmentResult {
        self.inner.align(seq1, seq2).into()
    }
}
