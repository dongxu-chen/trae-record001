mod pqlx;
mod steim2;
mod parallel;

use pyo3::prelude::*;
use std::collections::HashMap;

use crate::steim2::{Steim2Decoder, Steim2Frame};
use crate::pqlx::{PQLXAnalyzer, PQLXMetrics, MultiChannelMetrics};
use crate::parallel::ParallelProcessor;

#[pyclass(name = "Steim2Frame")]
struct PySteim2Frame {
    inner: Steim2Frame,
}

#[pymethods]
impl PySteim2Frame {
    #[new]
    fn new(data: &[u8]) -> PyResult<Self> {
        match Steim2Frame::new(data) {
            Ok(frame) => Ok(Self { inner: frame }),
            Err(e) => Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("{}", e))),
        }
    }

    fn decode(&self) -> Vec<i32> {
        self.inner.decode()
    }
}

#[pyclass(name = "Steim2Decoder")]
struct PySteim2Decoder {
    inner: Steim2Decoder,
}

#[pymethods]
impl PySteim2Decoder {
    #[new]
    fn new() -> Self {
        Self { inner: Steim2Decoder::new() }
    }

    fn add_frame(&mut self, frame_data: &[u8]) -> PyResult<()> {
        match self.inner.add_frame(frame_data) {
            Ok(_) => Ok(()),
            Err(e) => Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("{}", e))),
        }
    }

    fn add_frames(&mut self, frames_data: &[u8]) -> PyResult<()> {
        match self.inner.add_frames(frames_data) {
            Ok(_) => Ok(()),
            Err(e) => Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("{}", e))),
        }
    }

    fn decode_all(&self) -> Vec<i32> {
        self.inner.decode_all()
    }

    #[staticmethod]
    fn validate_alignment(data: &[u8]) -> Vec<u8> {
        Steim2Decoder::validate_alignment(data)
    }
}

#[pyclass(name = "PQLXMetrics")]
#[derive(Clone)]
struct PyPQLXMetrics {
    #[pyo3(get)]
    mean: f64,
    #[pyo3(get)]
    std_dev: f64,
    #[pyo3(get)]
    min: i32,
    #[pyo3(get)]
    max: i32,
    #[pyo3(get)]
    peak_to_peak: i32,
    #[pyo3(get)]
    rms: f64,
    #[pyo3(get)]
    skewness: f64,
    #[pyo3(get)]
    kurtosis: f64,
    #[pyo3(get)]
    num_samples: usize,
    #[pyo3(get)]
    num_gaps: usize,
    #[pyo3(get)]
    gap_percentage: f64,
    #[pyo3(get)]
    dc_offset: f64,
    #[pyo3(get)]
    cross_correlation: Option<f64>,
}

#[pymethods]
impl PyPQLXMetrics {
    fn __repr__(&self) -> String {
        format!(
            "PQLXMetrics(mean={:.2}, std={:.2}, min={}, max={}, p2p={}, rms={:.2}, \
            skew={:.2}, kurt={:.2}, samples={}, gaps={}, gap_pct={:.2}%, dc_offset={:.2})",
            self.mean, self.std_dev, self.min, self.max, self.peak_to_peak,
            self.rms, self.skewness, self.kurtosis, self.num_samples,
            self.num_gaps, self.gap_percentage, self.dc_offset
        )
    }
}

impl From<PQLXMetrics> for PyPQLXMetrics {
    fn from(m: PQLXMetrics) -> Self {
        Self {
            mean: m.mean,
            std_dev: m.std_dev,
            min: m.min,
            max: m.max,
            peak_to_peak: m.peak_to_peak,
            rms: m.rms,
            skewness: m.skewness,
            kurtosis: m.kurtosis,
            num_samples: m.num_samples,
            num_gaps: m.num_gaps,
            gap_percentage: m.gap_percentage,
            dc_offset: m.dc_offset,
            cross_correlation: m.cross_correlation,
        }
    }
}

#[pyclass(name = "PQLXAnalyzer")]
struct PyPQLXAnalyzer;

#[pymethods]
impl PyPQLXAnalyzer {
    #[staticmethod]
    fn analyze(samples: Vec<i32>, gap_threshold: i32) -> PyPQLXMetrics {
        let metrics = PQLXAnalyzer::analyze(&samples, gap_threshold);
        metrics.into()
    }

    #[staticmethod]
    fn cross_correlate(a: Vec<i32>, b: Vec<i32>) -> f64 {
        PQLXAnalyzer::cross_correlate(&a, &b)
    }

    #[staticmethod]
    fn snr_estimate(samples: Vec<i32>, noise_window: usize) -> f64 {
        PQLXAnalyzer::snr_estimate(&samples, noise_window)
    }

    #[staticmethod]
    fn quality_score(metrics: &PyPQLXMetrics) -> f64 {
        let m = PQLXMetrics {
            mean: metrics.mean,
            std_dev: metrics.std_dev,
            min: metrics.min,
            max: metrics.max,
            peak_to_peak: metrics.peak_to_peak,
            rms: metrics.rms,
            skewness: metrics.skewness,
            kurtosis: metrics.kurtosis,
            num_samples: metrics.num_samples,
            num_gaps: metrics.num_gaps,
            gap_percentage: metrics.gap_percentage,
            dc_offset: metrics.dc_offset,
            cross_correlation: metrics.cross_correlation,
        };
        PQLXAnalyzer::quality_score(&m)
    }
}

#[pyclass(name = "ParallelProcessor")]
struct PyParallelProcessor {
    inner: ParallelProcessor,
}

#[pymethods]
impl PyParallelProcessor {
    #[new]
    #[pyo3(signature = (num_threads=None))]
    fn new(num_threads: Option<usize>) -> Self {
        Self { inner: ParallelProcessor::new(num_threads) }
    }

    fn decode_many_stations(&self, station_data: HashMap<String, Vec<u8>>) -> HashMap<String, PyObject> {
        Python::with_gil(|py| {
            let results = self.inner.decode_many_stations(&station_data);
            results.into_iter()
                .map(|(k, v)| {
                    let obj = match v {
                        Ok(samples) => samples.into_pyobject(py).unwrap().into_any(),
                        Err(e) => e.into_pyobject(py).unwrap().into_any(),
                    };
                    (k, obj)
                })
                .collect()
        })
    }

    fn analyze_many_stations(&self, station_samples: HashMap<String, Vec<i32>>, gap_threshold: i32) -> HashMap<String, PyPQLXMetrics> {
        let results = self.inner.analyze_many_stations(&station_samples, gap_threshold);
        results.into_iter()
            .map(|(k, v)| (k, v.into()))
            .collect()
    }

    fn decode_and_analyze(&self, station_data: HashMap<String, Vec<u8>>, gap_threshold: i32) -> HashMap<String, (PyObject, Option<PyPQLXMetrics>)> {
        Python::with_gil(|py| {
            let results = self.inner.decode_and_analyze(&station_data, gap_threshold);
            results.into_iter()
                .map(|(k, (samples, metrics))| {
                    let samples_obj = match samples {
                        Ok(s) => s.into_pyobject(py).unwrap().into_any(),
                        Err(e) => e.into_pyobject(py).unwrap().into_any(),
                    };
                    (k, (samples_obj, metrics.map(|m| m.into())))
                })
                .collect()
        })
    }

    fn parallel_quality_filter(&self, station_samples: HashMap<String, Vec<i32>>, min_quality_score: f64, gap_threshold: i32) -> HashMap<String, (Vec<i32>, PyPQLXMetrics)> {
        let results = self.inner.parallel_quality_filter(&station_samples, min_quality_score, gap_threshold);
        results.into_iter()
            .map(|(k, (samples, metrics))| (k, (samples, metrics.into())))
            .collect()
    }
}

#[pymodule]
fn seis_rs(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<PySteim2Frame>()?;
    m.add_class::<PySteim2Decoder>()?;
    m.add_class::<PyPQLXMetrics>()?;
    m.add_class::<PyPQLXAnalyzer>()?;
    m.add_class::<PyParallelProcessor>()?;
    
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    
    Ok(())
}
