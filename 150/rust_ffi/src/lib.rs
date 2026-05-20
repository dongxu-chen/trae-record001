use std::ffi::c_void;
use std::marker::PhantomData;
use pyo3::prelude::*;
use pyo3::types::PyList;
use numpy::PyReadonlyArray1;

#[repr(C)]
#[derive(Debug, Clone, Copy)]
pub struct PeakFFI {
    pub mz: f64,
    pub intensity: f64,
    pub index: usize,
    pub left_index: usize,
    pub right_index: usize,
    pub fwhm: f64,
    pub area: f64,
    pub snr: f64,
    pub flags: u32,
}

unsafe impl Send for PeakFFI {}
unsafe impl Sync for PeakFFI {}

#[repr(C)]
#[derive(Debug, Clone, Copy)]
pub enum BaselineMethodFFI {
    RollingMin = 0,
    ASLS = 1,
    SegmentedASLS = 2,
    TopHat = 3,
}

#[repr(C)]
#[derive(Debug, Clone, Copy)]
pub enum PeakMethodFFI {
    LocalMax = 0,
    CWT = 1,
    ContinuousWavelet = 2,
}

extern "C" {
    fn baseline_corrector_new(method: i32) -> *mut c_void;
    fn baseline_corrector_delete(ptr: *mut c_void);
    fn baseline_corrector_correct(
        ptr: *mut c_void,
        intensity: *const f64,
        len: usize,
        out_baseline: *mut f64,
        out_corrected: *mut f64,
    );

    fn peak_detector_new(method: i32) -> *mut c_void;
    fn peak_detector_delete(ptr: *mut c_void);
    fn peak_detector_detect(
        ptr: *mut c_void,
        mz: *const f64,
        intensity: *const f64,
        len: usize,
        merge_distance: f64,
        snr_threshold: f64,
        out_peaks: *mut PeakFFI,
        max_peaks: usize,
    ) -> usize;

    fn parallel_processor_new(num_threads: usize) -> *mut c_void;
    fn parallel_processor_delete(ptr: *mut c_void);
}

pub struct BaselineCorrector {
    ptr: *mut c_void,
    _marker: PhantomData<*const ()>,
}

unsafe impl Send for BaselineCorrector {}
unsafe impl Sync for BaselineCorrector {}

impl BaselineCorrector {
    pub fn new(method: BaselineMethodFFI) -> Self {
        let ptr = unsafe { baseline_corrector_new(method as i32) };
        BaselineCorrector {
            ptr,
            _marker: PhantomData,
        }
    }

    pub fn correct(&self, intensity: &[f64]) -> (Vec<f64>, Vec<f64>) {
        let n = intensity.len();
        let mut baseline = vec![0.0; n];
        let mut corrected = vec![0.0; n];

        unsafe {
            baseline_corrector_correct(
                self.ptr,
                intensity.as_ptr(),
                n,
                baseline.as_mut_ptr(),
                corrected.as_mut_ptr(),
            );
        }

        (baseline, corrected)
    }
}

impl Drop for BaselineCorrector {
    fn drop(&mut self) {
        unsafe {
            baseline_corrector_delete(self.ptr);
        }
    }
}

pub struct PeakDetector {
    ptr: *mut c_void,
    _marker: PhantomData<*const ()>,
}

unsafe impl Send for PeakDetector {}
unsafe impl Sync for PeakDetector {}

impl PeakDetector {
    pub fn new(method: PeakMethodFFI) -> Self {
        let ptr = unsafe { peak_detector_new(method as i32) };
        PeakDetector {
            ptr,
            _marker: PhantomData,
        }
    }

    pub fn detect(&self, mz: &[f64], intensity: &[f64], merge_distance: f64, snr_threshold: f64) -> Vec<PeakFFI> {
        let n = std::cmp::min(mz.len(), intensity.len());
        let mut peaks = Vec::with_capacity(n);

        let peak_count = unsafe {
            peak_detector_detect(
                self.ptr,
                mz.as_ptr(),
                intensity.as_ptr(),
                n,
                merge_distance,
                snr_threshold,
                peaks.as_mut_ptr(),
                n,
            )
        };

        unsafe {
            peaks.set_len(peak_count);
        }

        peaks
    }
}

impl Drop for PeakDetector {
    fn drop(&mut self) {
        unsafe {
            peak_detector_delete(self.ptr);
        }
    }
}

pub struct ParallelProcessor {
    ptr: *mut c_void,
    _marker: PhantomData<*const ()>,
}

unsafe impl Send for ParallelProcessor {}
unsafe impl Sync for ParallelProcessor {}

impl ParallelProcessor {
    pub fn new(num_threads: usize) -> Self {
        let ptr = unsafe { parallel_processor_new(num_threads) };
        ParallelProcessor {
            ptr,
            _marker: PhantomData,
        }
    }

    pub fn parallel_baseline_correction(
        &self,
        intensity_list: &[Vec<f64>],
        _method: BaselineMethodFFI,
    ) -> Vec<Vec<f64>> {
        use rayon::prelude::*;

        intensity_list
            .par_iter()
            .map(|intensity| {
                let corrector = BaselineCorrector::new(BaselineMethodFFI::SegmentedASLS);
                let (_, corrected) = corrector.correct(intensity);
                corrected
            })
            .collect()
    }

    pub fn parallel_peak_detection(
        &self,
        mz_list: &[Vec<f64>],
        intensity_list: &[Vec<f64>],
        _method: PeakMethodFFI,
        merge_distance: f64,
        snr_threshold: f64,
    ) -> Vec<Vec<PeakFFI>> {
        use rayon::prelude::*;

        mz_list
            .par_iter()
            .zip(intensity_list.par_iter())
            .map(|(mz, intensity)| {
                let detector = PeakDetector::new(PeakMethodFFI::LocalMax);
                detector.detect(mz, intensity, merge_distance, snr_threshold)
            })
            .collect()
    }

    pub fn parallel_process_pipeline(
        &self,
        mz_list: &[Vec<f64>],
        intensity_list: &[Vec<f64>],
        merge_distance: f64,
        snr_threshold: f64,
    ) -> (Vec<Vec<f64>>, Vec<Vec<PeakFFI>>) {
        let corrected = self.parallel_baseline_correction(intensity_list, BaselineMethodFFI::SegmentedASLS);
        let peaks = self.parallel_peak_detection(mz_list, &corrected, PeakMethodFFI::LocalMax, merge_distance, snr_threshold);
        (corrected, peaks)
    }
}

impl Drop for ParallelProcessor {
    fn drop(&mut self) {
        unsafe {
            parallel_processor_delete(self.ptr);
        }
    }
}

#[derive(Debug, Clone)]
#[pyclass(name = "Peak")]
pub struct PyPeak {
    #[pyo3(get)]
    pub mz: f64,
    #[pyo3(get)]
    pub intensity: f64,
    #[pyo3(get)]
    pub index: usize,
    #[pyo3(get)]
    pub left_index: usize,
    #[pyo3(get)]
    pub right_index: usize,
    #[pyo3(get)]
    pub fwhm: f64,
    #[pyo3(get)]
    pub area: f64,
    #[pyo3(get)]
    pub snr: f64,
    #[pyo3(get)]
    pub is_merged: bool,
}

#[pymethods]
impl PyPeak {
    fn __repr__(&self) -> String {
        format!(
            "Peak(mz={:.4}, intensity={:.2}, snr={:.1}, merged={})",
            self.mz, self.intensity, self.snr, self.is_merged
        )
    }
}

#[pyclass(name = "BaselineCorrector")]
pub struct PyBaselineCorrector {
    corrector: BaselineCorrector,
}

#[pymethods]
impl PyBaselineCorrector {
    #[new]
    #[pyo3(signature = (method = "segmented_asls"))]
    fn new(method: &str) -> Self {
        let method_ffi = match method.to_lowercase().as_str() {
            "rolling_min" | "rolling" => BaselineMethodFFI::RollingMin,
            "asls" => BaselineMethodFFI::ASLS,
            "segmented_asls" | "segmented" => BaselineMethodFFI::SegmentedASLS,
            "tophat" => BaselineMethodFFI::TopHat,
            _ => BaselineMethodFFI::SegmentedASLS,
        };
        PyBaselineCorrector {
            corrector: BaselineCorrector::new(method_ffi),
        }
    }

    fn correct(&self, intensity: Vec<f64>) -> (Vec<f64>, Vec<f64>) {
        self.corrector.correct(&intensity)
    }
}

#[pyclass(name = "PeakDetector")]
pub struct PyPeakDetector {
    detector: PeakDetector,
}

#[pymethods]
impl PyPeakDetector {
    #[new]
    #[pyo3(signature = (method = "local_max"))]
    fn new(method: &str) -> Self {
        let method_ffi = match method.to_lowercase().as_str() {
            "local_max" | "localmax" => PeakMethodFFI::LocalMax,
            "cwt" | "wavelet" => PeakMethodFFI::CWT,
            _ => PeakMethodFFI::LocalMax,
        };
        PyPeakDetector {
            detector: PeakDetector::new(method_ffi),
        }
    }

    #[pyo3(signature = (mz, intensity, merge_distance = 0.5, snr_threshold = 2.0))]
    fn detect(&self, mz: Vec<f64>, intensity: Vec<f64>, merge_distance: f64, snr_threshold: f64) -> Vec<PyPeak> {
        let peaks = self.detector.detect(&mz, &intensity, merge_distance, snr_threshold);
        peaks
            .into_iter()
            .map(|p| PyPeak {
                mz: p.mz,
                intensity: p.intensity,
                index: p.index,
                left_index: p.left_index,
                right_index: p.right_index,
                fwhm: p.fwhm,
                area: p.area,
                snr: p.snr,
                is_merged: (p.flags & 1) != 0,
            })
            .collect()
    }
}

#[pyclass(name = "ParallelProcessor")]
pub struct PyParallelProcessor {
    processor: ParallelProcessor,
}

#[pymethods]
impl PyParallelProcessor {
    #[new]
    #[pyo3(signature = (num_threads = 0))]
    fn new(num_threads: usize) -> Self {
        PyParallelProcessor {
            processor: ParallelProcessor::new(num_threads),
        }
    }

    #[pyo3(signature = (intensity_list, method = "segmented_asls"))]
    fn parallel_baseline_correction(&self, intensity_list: Vec<Vec<f64>>, method: &str) -> Vec<Vec<f64>> {
        let method_ffi = match method.to_lowercase().as_str() {
            "rolling_min" | "rolling" => BaselineMethodFFI::RollingMin,
            "asls" => BaselineMethodFFI::ASLS,
            "segmented_asls" | "segmented" => BaselineMethodFFI::SegmentedASLS,
            "tophat" => BaselineMethodFFI::TopHat,
            _ => BaselineMethodFFI::SegmentedASLS,
        };
        self.processor.parallel_baseline_correction(&intensity_list, method_ffi)
    }

    #[pyo3(signature = (mz_list, intensity_list, method = "local_max", merge_distance = 0.5, snr_threshold = 2.0))]
    fn parallel_peak_detection(
        &self,
        mz_list: Vec<Vec<f64>>,
        intensity_list: Vec<Vec<f64>>,
        method: &str,
        merge_distance: f64,
        snr_threshold: f64,
    ) -> Vec<Vec<PyPeak>> {
        let method_ffi = match method.to_lowercase().as_str() {
            "local_max" | "localmax" => PeakMethodFFI::LocalMax,
            "cwt" | "wavelet" => PeakMethodFFI::CWT,
            _ => PeakMethodFFI::LocalMax,
        };

        let peaks_list = self.processor.parallel_peak_detection(
            &mz_list,
            &intensity_list,
            method_ffi,
            merge_distance,
            snr_threshold,
        );

        peaks_list
            .into_iter()
            .map(|peaks| {
                peaks
                    .into_iter()
                    .map(|p| PyPeak {
                        mz: p.mz,
                        intensity: p.intensity,
                        index: p.index,
                        left_index: p.left_index,
                        right_index: p.right_index,
                        fwhm: p.fwhm,
                        area: p.area,
                        snr: p.snr,
                        is_merged: (p.flags & 1) != 0,
                    })
                    .collect()
            })
            .collect()
    }

    #[pyo3(signature = (mz_list, intensity_list, merge_distance = 0.5, snr_threshold = 2.0))]
    fn process_pipeline(
        &self,
        mz_list: Vec<Vec<f64>>,
        intensity_list: Vec<Vec<f64>>,
        merge_distance: f64,
        snr_threshold: f64,
    ) -> (Vec<Vec<f64>>, Vec<Vec<PyPeak>>) {
        let (corrected, peaks) =
            self.processor
                .parallel_process_pipeline(&mz_list, &intensity_list, merge_distance, snr_threshold);

        let peaks_py = peaks
            .into_iter()
            .map(|peaks| {
                peaks
                    .into_iter()
                    .map(|p| PyPeak {
                        mz: p.mz,
                        intensity: p.intensity,
                        index: p.index,
                        left_index: p.left_index,
                        right_index: p.right_index,
                        fwhm: p.fwhm,
                        area: p.area,
                        snr: p.snr,
                        is_merged: (p.flags & 1) != 0,
                    })
                    .collect()
            })
            .collect();

        (corrected, peaks_py)
    }
}

#[pymodule]
fn ms_peak_detector_core(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<PyPeak>()?;
    m.add_class::<PyBaselineCorrector>()?;
    m.add_class::<PyPeakDetector>()?;
    m.add_class::<PyParallelProcessor>()?;
    m.add("__version__", "0.2.0")?;
    Ok(())
}
