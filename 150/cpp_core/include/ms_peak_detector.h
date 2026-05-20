#ifndef MS_PEAK_DETECTOR_H
#define MS_PEAK_DETECTOR_H

#include <vector>
#include <cstddef>
#include <cstdint>

namespace ms {
namespace core {

struct Peak {
    double mz;
    double intensity;
    size_t index;
    size_t left_index;
    size_t right_index;
    double fwhm;
    double area;
    double snr;
    uint32_t flags;

    Peak() : mz(0.0), intensity(0.0), index(0), left_index(0), right_index(0),
             fwhm(0.0), area(0.0), snr(0.0), flags(0) {}
};

struct Spectrum {
    std::vector<double> mz;
    std::vector<double> intensity;
    size_t size() const { return mz.size(); }
};

class BaselineCorrector {
public:
    enum class Method {
        ROLLING_MIN,
        ASLS,
        SEGMENTED_ASLS,
        TOPHAT
    };

    BaselineCorrector(Method method = Method::SEGMENTED_ASLS);
    ~BaselineCorrector();

    std::vector<double> correct(const std::vector<double>& intensity,
                                 double lam = 1e5, double p = 0.001, int niter = 5);

    std::vector<double> correct_segmented(const std::vector<double>& intensity,
                                           size_t segment_size = 1000,
                                           size_t overlap = 200,
                                           double lam = 1e5, double p = 0.001, int niter = 5);

    const std::vector<double>& get_baseline() const { return baseline_; }

private:
    Method method_;
    std::vector<double> baseline_;

    std::vector<double> rolling_min(const std::vector<double>& intensity, size_t window_size);
    std::vector<double> asls_impl(const std::vector<double>& intensity, double lam, double p, int niter);
    std::vector<double> sparse_asls(const std::vector<double>& intensity, double lam, double p, int niter);
};

class PeakDetector {
public:
    enum class Method {
        LOCAL_MAX,
        CWT,
        CONTINUOUS_WAVELET
    };

    PeakDetector(Method method = Method::LOCAL_MAX);
    ~PeakDetector();

    std::vector<Peak> detect(const std::vector<double>& mz,
                              const std::vector<double>& intensity,
                              double merge_distance = 0.5,
                              double snr_threshold = 2.0);

    std::vector<Peak> detect_local_max(const std::vector<double>& mz,
                                        const std::vector<double>& intensity,
                                        double threshold = 0.01,
                                        size_t min_distance = 5);

private:
    Method method_;

    std::vector<Peak> merge_adjacent_peaks(const std::vector<Peak>& peaks,
                                            const std::vector<double>& mz,
                                            const std::vector<double>& intensity,
                                            double merge_distance);

    Peak merge_peak_group(const std::vector<Peak>& peak_group,
                           const std::vector<double>& mz,
                           const std::vector<double>& intensity);

    double calculate_snr(const std::vector<double>& intensity,
                          size_t peak_idx, size_t left_idx, size_t right_idx,
                          size_t window_size = 20);
};

class ParallelProcessor {
public:
    ParallelProcessor(size_t num_threads = 0);
    ~ParallelProcessor();

    std::vector<std::vector<double>> parallel_baseline_correction(
        const std::vector<std::vector<double>>& intensity_list,
        BaselineCorrector::Method method);

    std::vector<std::vector<Peak>> parallel_peak_detection(
        const std::vector<std::vector<double>>& mz_list,
        const std::vector<std::vector<double>>& intensity_list,
        PeakDetector::Method method,
        double merge_distance);

    std::vector<std::vector<double>> parallel_process_pipeline(
        const std::vector<std::vector<double>>& mz_list,
        const std::vector<std::vector<double>>& intensity_list,
        std::vector<std::vector<Peak>>& detected_peaks);

private:
    size_t num_threads_;
};

} // namespace core
} // namespace ms

extern "C" {
    ms::core::BaselineCorrector* baseline_corrector_new(int method);
    void baseline_corrector_delete(ms::core::BaselineCorrector* ptr);
    void baseline_corrector_correct(ms::core::BaselineCorrector* ptr,
                                     const double* intensity, size_t len,
                                     double* out_baseline, double* out_corrected);

    ms::core::PeakDetector* peak_detector_new(int method);
    void peak_detector_delete(ms::core::PeakDetector* ptr);
    size_t peak_detector_detect(ms::core::PeakDetector* ptr,
                                 const double* mz, const double* intensity, size_t len,
                                 double merge_distance, double snr_threshold,
                                 ms::core::Peak* out_peaks, size_t max_peaks);

    ms::core::ParallelProcessor* parallel_processor_new(size_t num_threads);
    void parallel_processor_delete(ms::core::ParallelProcessor* ptr);
}

#endif // MS_PEAK_DETECTOR_H
