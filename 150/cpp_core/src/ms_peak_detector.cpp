#include "ms_peak_detector.h"
#include <algorithm>
#include <cmath>
#include <numeric>
#include <thread>
#include <mutex>
#include <future>

namespace ms {
namespace core {

BaselineCorrector::BaselineCorrector(Method method) : method_(method) {}

BaselineCorrector::~BaselineCorrector() = default;

std::vector<double> BaselineCorrector::correct(const std::vector<double>& intensity,
                                                 double lam, double p, int niter) {
    switch (method_) {
        case Method::ROLLING_MIN:
            baseline_ = rolling_min(intensity, 51);
            break;
        case Method::ASLS:
            baseline_ = asls_impl(intensity, lam, p, niter);
            break;
        case Method::SEGMENTED_ASLS:
            baseline_ = correct_segmented(intensity, 1000, 200, lam, p, niter);
            break;
        default:
            baseline_ = rolling_min(intensity, 51);
    }

    std::vector<double> corrected(intensity.size());
    for (size_t i = 0; i < intensity.size(); ++i) {
        corrected[i] = intensity[i] - baseline_[i];
    }
    return corrected;
}

std::vector<double> BaselineCorrector::correct_segmented(const std::vector<double>& intensity,
                                                          size_t segment_size, size_t overlap,
                                                          double lam, double p, int niter) {
    const size_t n = intensity.size();
    if (n <= segment_size) {
        return sparse_asls(intensity, lam, p, niter);
    }

    std::vector<double> baseline(n, 0.0);
    std::vector<double> weights(n, 0.0);

    size_t num_segments = (n - overlap) / (segment_size - overlap) + 1;

    for (size_t seg = 0; seg < num_segments; ++seg) {
        size_t start = seg * (segment_size - overlap);
        size_t end = std::min(start + segment_size, n);
        size_t actual_size = end - start;

        std::vector<double> segment(actual_size);
        for (size_t i = 0; i < actual_size; ++i) {
            segment[i] = intensity[start + i];
        }

        std::vector<double> seg_baseline = sparse_asls(segment, lam, p, niter);

        std::vector<double> taper(actual_size, 1.0);
        if (seg > 0) {
            for (size_t i = 0; i < overlap && i < actual_size; ++i) {
                taper[i] = static_cast<double>(i) / overlap;
            }
        }
        if (seg < num_segments - 1) {
            size_t start_idx = (actual_size > overlap) ? (actual_size - overlap) : 0;
            for (size_t i = start_idx; i < actual_size; ++i) {
                taper[i] = static_cast<double>(actual_size - 1 - i) / overlap;
            }
        }

        for (size_t i = 0; i < actual_size; ++i) {
            baseline[start + i] += seg_baseline[i] * taper[i];
            weights[start + i] += taper[i];
        }
    }

    for (size_t i = 0; i < n; ++i) {
        if (weights[i] > 0) {
            baseline[i] /= weights[i];
        }
    }

    return baseline;
}

std::vector<double> BaselineCorrector::rolling_min(const std::vector<double>& intensity, size_t window_size) {
    const size_t n = intensity.size();
    std::vector<double> result(n);

    for (size_t i = 0; i < n; ++i) {
        size_t start = (i >= window_size / 2) ? (i - window_size / 2) : 0;
        size_t end = std::min(n, i + window_size / 2 + 1);

        double min_val = intensity[start];
        for (size_t j = start + 1; j < end; ++j) {
            if (intensity[j] < min_val) {
                min_val = intensity[j];
            }
        }
        result[i] = min_val;
    }

    for (size_t i = 0; i < n; ++i) {
        size_t start = (i >= window_size / 4) ? (i - window_size / 4) : 0;
        size_t end = std::min(n, i + window_size / 4 + 1);

        double max_val = result[start];
        for (size_t j = start + 1; j < end; ++j) {
            if (result[j] > max_val) {
                max_val = result[j];
            }
        }
        result[i] = max_val;
    }

    return result;
}

std::vector<double> BaselineCorrector::sparse_asls(const std::vector<double>& intensity,
                                                    double lam, double p, int niter) {
    const size_t n = intensity.size();
    std::vector<double> w(n, 1.0);
    std::vector<double> baseline(n, 0.0);

    for (int iter = 0; iter < niter; ++iter) {
        std::vector<double> a(n), b(n), c(n), d(n);

        for (size_t i = 0; i < n; ++i) {
            d[i] = w[i];
            if (i >= 2) d[i] += lam;
            if (i >= 1 && i < n - 1) d[i] += 2 * lam;
            if (i < n - 2) d[i] += lam;
        }

        for (size_t i = 1; i < n - 1; ++i) {
            b[i] = -2 * lam;
        }
        for (size_t i = 2; i < n; ++i) {
            c[i] = lam;
        }
        for (size_t i = 0; i < n; ++i) {
            a[i] = w[i] * intensity[i];
        }

        for (size_t i = 2; i < n; ++i) {
            double factor = b[i - 1] / d[i - 1];
            d[i] -= factor * b[i - 1];
            a[i] -= factor * a[i - 1];
            factor = c[i - 2] / d[i - 2];
            d[i] -= factor * c[i - 2];
        }

        baseline[n - 1] = a[n - 1] / d[n - 1];
        baseline[n - 2] = (a[n - 2] - b[n - 2] * baseline[n - 1]) / d[n - 2];
        for (int i = static_cast<int>(n) - 3; i >= 0; --i) {
            baseline[i] = (a[i] - b[i] * baseline[i + 1] - c[i] * baseline[i + 2]) / d[i];
        }

        for (size_t i = 0; i < n; ++i) {
            if (intensity[i] > baseline[i]) {
                w[i] = p;
            } else {
                w[i] = 1.0 - p;
            }
        }
    }

    return baseline;
}

std::vector<double> BaselineCorrector::asls_impl(const std::vector<double>& intensity,
                                                   double lam, double p, int niter) {
    return sparse_asls(intensity, lam, p, niter);
}

PeakDetector::PeakDetector(Method method) : method_(method) {}

PeakDetector::~PeakDetector() = default;

std::vector<Peak> PeakDetector::detect(const std::vector<double>& mz,
                                        const std::vector<double>& intensity,
                                        double merge_distance, double snr_threshold) {
    std::vector<Peak> peaks;

    switch (method_) {
        case Method::LOCAL_MAX:
            peaks = detect_local_max(mz, intensity);
            break;
        default:
            peaks = detect_local_max(mz, intensity);
    }

    if (merge_distance > 0) {
        peaks = merge_adjacent_peaks(peaks, mz, intensity);
    }

    std::vector<Peak> filtered;
    for (const auto& peak : peaks) {
        if (peak.snr >= snr_threshold) {
            filtered.push_back(peak);
        }
    }

    return filtered;
}

std::vector<Peak> PeakDetector::detect_local_max(const std::vector<double>& mz,
                                                   const std::vector<double>& intensity,
                                                   double threshold, size_t min_distance) {
    std::vector<Peak> peaks;
    const size_t n = intensity.size();
    if (n == 0) return peaks;

    double max_int = *std::max_element(intensity.begin(), intensity.end());
    double height = threshold * max_int;

    for (size_t i = 1; i < n - 1; ++i) {
        if (intensity[i] > height &&
            intensity[i] > intensity[i - 1] &&
            intensity[i] >= intensity[i + 1]) {

            bool too_close = false;
            for (auto it = peaks.rbegin(); it != peaks.rend(); ++it) {
                if (i - it->index < min_distance) {
                    too_close = true;
                    break;
                }
                if (i - it->index > 2 * min_distance) {
                    break;
                }
            }

            if (!too_close) {
                Peak p;
                p.mz = mz[i];
                p.intensity = intensity[i];
                p.index = i;
                p.left_index = i;
                p.right_index = i;

                double half_max = intensity[i] / 2.0;
                while (p.left_index > 0 && intensity[p.left_index] > half_max) {
                    p.left_index--;
                }
                while (p.right_index < n - 1 && intensity[p.right_index] > half_max) {
                    p.right_index++;
                }

                p.fwhm = mz[p.right_index] - mz[p.left_index];

                double area = 0.0;
                for (size_t j = p.left_index; j <= p.right_index; ++j) {
                    area += intensity[j] * (mz[j] - (j > 0 ? mz[j - 1] : mz[j]));
                }
                p.area = area;

                p.snr = calculate_snr(intensity, i, p.left_index, p.right_index);

                peaks.push_back(p);
            }
        }
    }

    return peaks;
}

std::vector<Peak> PeakDetector::merge_adjacent_peaks(const std::vector<Peak>& peaks,
                                                       const std::vector<double>& mz,
                                                       const std::vector<double>& intensity,
                                                       double merge_distance) {
    if (peaks.size() <= 1) return peaks;

    std::vector<Peak> sorted_peaks = peaks;
    std::sort(sorted_peaks.begin(), sorted_peaks.end(),
              [](const Peak& a, const Peak& b) { return a.mz < b.mz; });

    std::vector<Peak> merged;
    std::vector<Peak> current_group;
    current_group.push_back(sorted_peaks[0]);

    for (size_t i = 1; i < sorted_peaks.size(); ++i) {
        const Peak& prev = current_group.back();
        const Peak& curr = sorted_peaks[i];

        if (curr.mz - prev.mz <= merge_distance) {
            current_group.push_back(curr);
        } else {
            merged.push_back(merge_peak_group(current_group, mz, intensity));
            current_group.clear();
            current_group.push_back(curr);
        }
    }

    if (!current_group.empty()) {
        merged.push_back(merge_peak_group(current_group, mz, intensity));
    }

    return merged;
}

Peak PeakDetector::merge_peak_group(const std::vector<Peak>& peak_group,
                                      const std::vector<double>& mz,
                                      const std::vector<double>& intensity) {
    if (peak_group.size() == 1) {
        Peak result = peak_group[0];
        result.flags = 0;
        return result;
    }

    double total_intensity = 0.0;
    double weighted_mz = 0.0;
    size_t left_idx = SIZE_MAX;
    size_t right_idx = 0;

    for (const Peak& p : peak_group) {
        total_intensity += p.intensity;
        weighted_mz += p.mz * p.intensity;
        left_idx = std::min(left_idx, p.left_index);
        right_idx = std::max(right_idx, p.right_index);
    }

    Peak merged;
    merged.mz = weighted_mz / total_intensity;
    merged.intensity = total_intensity;
    merged.left_index = left_idx;
    merged.right_index = right_idx;
    merged.fwhm = mz[right_idx] - mz[left_idx];
    merged.flags = 1;

    size_t peak_idx = 0;
    while (peak_idx < mz.size() && mz[peak_idx] < merged.mz) {
        peak_idx++;
    }
    merged.index = peak_idx;

    double area = 0.0;
    for (size_t j = left_idx; j <= right_idx; ++j) {
        double delta_mz = (j > left_idx) ? (mz[j] - mz[j - 1]) : (mz[j + 1] - mz[j]);
        area += intensity[j] * delta_mz;
    }
    merged.area = area;

    merged.snr = calculate_snr(intensity, peak_idx, left_idx, right_idx);

    return merged;
}

double PeakDetector::calculate_snr(const std::vector<double>& intensity,
                                    size_t peak_idx, size_t left_idx, size_t right_idx,
                                    size_t window_size) {
    const size_t n = intensity.size();
    if (n == 0) return 0.0;

    std::vector<double> noise_samples;
    size_t start = (left_idx > window_size) ? (left_idx - window_size) : 0;
    size_t end = std::min(n, right_idx + window_size);

    for (size_t i = start; i < left_idx; ++i) {
        noise_samples.push_back(intensity[i]);
    }
    for (size_t i = right_idx + 1; i < end; ++i) {
        noise_samples.push_back(intensity[i]);
    }

    if (noise_samples.empty()) {
        start = (peak_idx > window_size) ? (peak_idx - window_size) : 0;
        end = std::min(n, peak_idx + window_size);
        for (size_t i = start; i < end; ++i) {
            if (i != peak_idx) {
                noise_samples.push_back(intensity[i]);
            }
        }
    }

    if (noise_samples.empty()) {
        return 100.0;
    }

    double sum = 0.0;
    for (double x : noise_samples) {
        sum += x;
    }
    double mean = sum / noise_samples.size();

    double variance = 0.0;
    for (double x : noise_samples) {
        variance += (x - mean) * (x - mean);
    }
    double stddev = std::sqrt(variance / noise_samples.size());

    double peak_int = intensity[peak_idx];
    return peak_int / (stddev + 1e-10);
}

ParallelProcessor::ParallelProcessor(size_t num_threads) {
    if (num_threads == 0) {
        num_threads_ = std::thread::hardware_concurrency();
        if (num_threads_ == 0) num_threads_ = 4;
    } else {
        num_threads_ = num_threads;
    }
}

ParallelProcessor::~ParallelProcessor() = default;

std::vector<std::vector<double>> ParallelProcessor::parallel_baseline_correction(
    const std::vector<std::vector<double>>& intensity_list,
    BaselineCorrector::Method method) {

    const size_t n = intensity_list.size();
    std::vector<std::vector<double>> results(n);

    auto process_chunk = [&](size_t start, size_t end) {
        BaselineCorrector corrector(method);
        for (size_t i = start; i < end; ++i) {
            results[i] = corrector.correct(intensity_list[i]);
        }
    };

    std::vector<std::future<void>> futures;
    size_t chunk_size = (n + num_threads_ - 1) / num_threads_;

    for (size_t t = 0; t < num_threads_; ++t) {
        size_t start = t * chunk_size;
        size_t end = std::min(n, start + chunk_size);
        if (start < end) {
            futures.push_back(std::async(std::launch::async, process_chunk, start, end));
        }
    }

    for (auto& f : futures) {
        f.wait();
    }

    return results;
}

std::vector<std::vector<Peak>> ParallelProcessor::parallel_peak_detection(
    const std::vector<std::vector<double>>& mz_list,
    const std::vector<std::vector<double>>& intensity_list,
    PeakDetector::Method method, double merge_distance) {

    const size_t n = mz_list.size();
    std::vector<std::vector<Peak>> results(n);

    auto process_chunk = [&](size_t start, size_t end) {
        PeakDetector detector(method);
        for (size_t i = start; i < end; ++i) {
            results[i] = detector.detect(mz_list[i], intensity_list[i], merge_distance);
        }
    };

    std::vector<std::future<void>> futures;
    size_t chunk_size = (n + num_threads_ - 1) / num_threads_;

    for (size_t t = 0; t < num_threads_; ++t) {
        size_t start = t * chunk_size;
        size_t end = std::min(n, start + chunk_size);
        if (start < end) {
            futures.push_back(std::async(std::launch::async, process_chunk, start, end));
        }
    }

    for (auto& f : futures) {
        f.wait();
    }

    return results;
}

std::vector<std::vector<double>> ParallelProcessor::parallel_process_pipeline(
    const std::vector<std::vector<double>>& mz_list,
    const std::vector<std::vector<double>>& intensity_list,
    std::vector<std::vector<Peak>>& detected_peaks) {

    auto corrected = parallel_baseline_correction(intensity_list,
                                                   BaselineCorrector::Method::SEGMENTED_ASLS);

    detected_peaks = parallel_peak_detection(mz_list, corrected,
                                              PeakDetector::Method::LOCAL_MAX, 0.5);

    return corrected;
}

} // namespace core
} // namespace ms

extern "C" {
    ms::core::BaselineCorrector* baseline_corrector_new(int method) {
        return new ms::core::BaselineCorrector(static_cast<ms::core::BaselineCorrector::Method>(method));
    }

    void baseline_corrector_delete(ms::core::BaselineCorrector* ptr) {
        delete ptr;
    }

    void baseline_corrector_correct(ms::core::BaselineCorrector* ptr,
                                     const double* intensity, size_t len,
                                     double* out_baseline, double* out_corrected) {
        if (!ptr || !intensity || !out_baseline || !out_corrected) return;

        std::vector<double> int_vec(intensity, intensity + len);
        std::vector<double> corrected = ptr->correct(int_vec);
        const std::vector<double>& baseline = ptr->get_baseline();

        for (size_t i = 0; i < len; ++i) {
            out_baseline[i] = baseline[i];
            out_corrected[i] = corrected[i];
        }
    }

    ms::core::PeakDetector* peak_detector_new(int method) {
        return new ms::core::PeakDetector(static_cast<ms::core::PeakDetector::Method>(method));
    }

    void peak_detector_delete(ms::core::PeakDetector* ptr) {
        delete ptr;
    }

    size_t peak_detector_detect(ms::core::PeakDetector* ptr,
                                 const double* mz, const double* intensity, size_t len,
                                 double merge_distance, double snr_threshold,
                                 ms::core::Peak* out_peaks, size_t max_peaks) {
        if (!ptr || !mz || !intensity || !out_peaks) return 0;

        std::vector<double> mz_vec(mz, mz + len);
        std::vector<double> int_vec(intensity, intensity + len);
        std::vector<ms::core::Peak> peaks = ptr->detect(mz_vec, int_vec, merge_distance, snr_threshold);

        size_t n_copy = std::min(peaks.size(), max_peaks);
        for (size_t i = 0; i < n_copy; ++i) {
            out_peaks[i] = peaks[i];
        }

        return peaks.size();
    }

    ms::core::ParallelProcessor* parallel_processor_new(size_t num_threads) {
        return new ms::core::ParallelProcessor(num_threads);
    }

    void parallel_processor_delete(ms::core::ParallelProcessor* ptr) {
        delete ptr;
    }
}
