use pyo3::prelude::*;
use std::fmt;

#[derive(Debug, Clone)]
pub struct AlignmentResult {
    pub aligned_seq1: String,
    pub aligned_seq2: String,
    pub score: i32,
    pub start1: usize,
    pub end1: usize,
    pub start2: usize,
    pub end2: usize,
}

impl Default for AlignmentResult {
    fn default() -> Self {
        Self {
            aligned_seq1: String::new(),
            aligned_seq2: String::new(),
            score: 0,
            start1: 0,
            end1: 0,
            start2: 0,
            end2: 0,
        }
    }
}

impl fmt::Display for AlignmentResult {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "AlignmentResult(score={}, len1={}, len2={})", 
               self.score, self.aligned_seq1.len(), self.aligned_seq2.len())
    }
}

#[pyclass(name = "AlignmentResult")]
#[derive(Debug, Clone)]
pub struct rust_AlignmentResult {
    #[pyo3(get)]
    pub aligned_seq1: String,
    #[pyo3(get)]
    pub aligned_seq2: String,
    #[pyo3(get)]
    pub score: i32,
    #[pyo3(get)]
    pub start1: usize,
    #[pyo3(get)]
    pub end1: usize,
    #[pyo3(get)]
    pub start2: usize,
    #[pyo3(get)]
    pub end2: usize,
}

#[pymethods]
impl rust_AlignmentResult {
    #[new]
    fn new() -> Self {
        Self {
            aligned_seq1: String::new(),
            aligned_seq2: String::new(),
            score: 0,
            start1: 0,
            end1: 0,
            start2: 0,
            end2: 0,
        }
    }

    fn __repr__(&self) -> String {
        format!(
            "AlignmentResult(score={}, aligned_length={})",
            self.score,
            self.aligned_seq1.len()
        )
    }
}

impl From<AlignmentResult> for rust_AlignmentResult {
    fn from(r: AlignmentResult) -> Self {
        Self {
            aligned_seq1: r.aligned_seq1,
            aligned_seq2: r.aligned_seq2,
            score: r.score,
            start1: r.start1,
            end1: r.end1,
            start2: r.start2,
            end2: r.end2,
        }
    }
}

#[derive(Debug, Clone, Copy)]
pub struct AlignmentParams {
    pub match_score: i32,
    pub mismatch_score: i32,
    pub gap_open: i32,
    pub gap_extend: i32,
    pub use_affine: bool,
}

impl Default for AlignmentParams {
    fn default() -> Self {
        Self {
            match_score: 2,
            mismatch_score: -1,
            gap_open: -5,
            gap_extend: -1,
            use_affine: true,
        }
    }
}
