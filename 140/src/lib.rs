use pyo3::prelude::*;

mod alignment;
mod needleman_wunsch;
mod smith_waterman;
mod parallel;
mod simd;

pub use alignment::*;
pub use needleman_wunsch::*;
pub use smith_waterman::*;
pub use parallel::*;

#[pymodule]
fn seqalign_rs(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<rust_AlignmentResult>()?;
    m.add_class::<rust_NeedlemanWunsch>()?;
    m.add_class::<rust_SmithWaterman>()?;
    m.add_function(wrap_pyfunction!(rust_parallel_align_all, m)?)?;
    m.add_function(wrap_pyfunction!(rust_parallel_pairwise_scores, m)?)?;
    Ok(())
}
