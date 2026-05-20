use pyo3::prelude::*;
use rayon::prelude::*;
use crate::needleman_wunsch::NeedlemanWunsch;
use crate::smith_waterman::SmithWaterman;
use crate::alignment::{AlignmentResult, rust_AlignmentResult};
use std::sync::Arc;

pub fn parallel_align_all_nw(
    sequences: &[String], reference: &str,
    match_score: i32,
    mismatch_score: i32,
    gap_open: i32,
    gap_extend: i32,
    use_affine: bool,
) -> Vec<AlignmentResult> {
    let aligner = Arc::new(NeedlemanWunsch::new(
        match_score,
        mismatch_score,
        gap_open,
        gap_extend,
        use_affine,
    ));

    sequences
        .par_iter()
        .map(|seq| {
            aligner.align(seq, reference)
        })
        .collect()
}

pub fn parallel_align_all_sw(
    sequences: &[String],
    reference: &str,
    match_score: i32,
    mismatch_score: i32,
    gap_open: i32,
    gap_extend: i32,
    use_affine: bool,
) -> Vec<AlignmentResult> {
    let aligner = Arc::new(SmithWaterman::new(
        match_score,
        mismatch_score,
        gap_open,
        gap_extend,
        use_affine,
    ));

    sequences
        .par_iter()
        .map(|seq| {
            aligner.align(seq, reference)
        })
        .collect()
}

pub fn parallel_pairwise_scores(
    sequences: &[String],
    match_score: i32,
    mismatch_score: i32,
    gap_open: i32,
    gap_extend: i32,
    use_affine: bool,
) -> Vec<Vec<i32>> {
    let n = sequences.len();
    let aligner = Arc::new(NeedlemanWunsch::new(
        match_score,
        mismatch_score,
        gap_open,
        gap_extend,
        use_affine,
    ));

    (0..n)
        .into_par_iter()
        .map(|i| {
            let mut row = vec![0i32; n];
            for j in 0..n {
                if i == j {
                    row[j] = 0;
                } else {
                    let result = aligner.align(&sequences[i], &sequences[j]);
                    row[j] = result.score;
                }
            }
            row
        })
        .collect()
}

#[pyfunction]
#[pyo3(signature = (sequences, reference, match_score=2, mismatch_score=-1, gap_open=-5, gap_extend=-1, use_affine=true, method="global"))]
pub fn rust_parallel_align_all(
    sequences: Vec<String>,
    reference: &str,
    match_score: i32,
    mismatch_score: i32,
    gap_open: i32,
    gap_extend: i32,
    use_affine: bool,
    method: &str,
) -> PyResult<Vec<rust_AlignmentResult>> {
    let results = if method == "local" {
        parallel_align_all_sw(
            &sequences,
            reference,
            match_score,
            mismatch_score,
            gap_open,
            gap_extend,
            use_affine,
        )
    } else {
        parallel_align_all_nw(
            &sequences,
            reference,
            match_score,
            mismatch_score,
            gap_open,
            gap_extend,
            use_affine,
        )
    };

    Ok(results.into_iter().map(|r| r.into()).collect())
}

#[pyfunction]
pub fn rust_parallel_pairwise_scores(
    sequences: Vec<String>,
    match_score: i32,
    mismatch_score: i32,
    gap_open: i32,
    gap_extend: i32,
    use_affine: bool,
) -> PyResult<Vec<Vec<i32>>> {
    Ok(parallel_pairwise_scores(
        &sequences,
        match_score,
        mismatch_score,
        gap_open,
        gap_extend,
        use_affine,
    ))
}
