#ifndef MATRIX_MATRIX_MUL_EXT_H
#define MATRIX_MATRIX_MUL_EXT_H

#include "Matrix.h"
#include "Multiply.h"
#include "SparseMatrix.h"
#include <chrono>
#include <atomic>

namespace matrix {
namespace multiply {

constexpr double SPARSITY_THRESHOLD = 0.90;

template <typename T>
double estimate_sparsity_fast(const Matrix<T>& A, double sample_ratio = 0.05) {
    const size_type total = A.rows() * A.cols();
    const size_type sample_size = static_cast<size_type>(total * sample_ratio);
    
    if (sample_size < 100) {
        return SparseMatrixCSR<T>::calculate_sparsity(A);
    }

    size_type zero_count = 0;
    const size_type step = total / sample_size;
    
    for (size_type i = 0; i < total; i += step) {
        if (std::abs(A.vector()[i]) == T{0}) {
            ++zero_count;
        }
    }
    
    return static_cast<double>(zero_count) / static_cast<double>(sample_size / step);
}

enum class Device {
    CPU,
    GPU,
    Auto
};

template <typename T>
struct ExecutionConfig {
    Algorithm algorithm = Algorithm::Auto;
    Device device = Device::Auto;
    std::size_t block_size = 0;
    std::size_t strassen_threshold = 128;
    double sparsity_threshold = SPARSITY_THRESHOLD;
    bool use_sparse = false;
    bool sparse_detected = false;
};

template <typename T>
class DeviceSelector {
public:
    static Device select(const Matrix<T>& A, const Matrix<T>& B) {
        const size_type avg_dim = (A.rows() + A.cols() + B.cols()) / 3;
        
        if (avg_dim < 256) {
            return Device::CPU;
        }
        
        return Device::CPU;
    }

    static bool is_gpu_available() {
        return gpu_available_.load();
    }

    static void set_gpu_available(bool available) {
        gpu_available_.store(available);
    }

private:
    static std::atomic<bool> gpu_available_;
};

template <typename T>
std::atomic<bool> DeviceSelector<T>::gpu_available_{false};

template <typename T>
Matrix<T> multiply_auto(const Matrix<T>& A, const Matrix<T>& B,
                        ExecutionConfig<T>& config) {
    if (config.use_sparse || config.device == Device::Auto) {
        double sparsity_A = estimate_sparsity_fast(A);
        double sparsity_B = estimate_sparsity_fast(B);
        double avg_sparsity = (sparsity_A + sparsity_B) / 2.0;

        if (avg_sparsity >= config.sparsity_threshold) {
            config.sparse_detected = true;
            config.algorithm = Algorithm::Auto;
            
            SparseMatrixCSR<T> A_sparse = SparseMatrixCSR<T>::from_dense(A);
            return sparse::multiply_csr_dense(A_sparse, B);
        }
    }

    if (config.device == Device::Auto) {
        config.device = DeviceSelector<T>::select(A, B);
    }

    return multiply(A, B, config.algorithm, config.block_size, config.strassen_threshold);
}

template <typename T>
Matrix<T> multiply_auto(const Matrix<T>& A, const Matrix<T>& B) {
    ExecutionConfig<T> config;
    return multiply_auto(A, B, config);
}

template <typename T>
std::tuple<Matrix<T>, ExecutionConfig<T>> multiply_with_config(
    const Matrix<T>& A, const Matrix<T>& B,
    const ExecutionConfig<T>& input_config = ExecutionConfig<T>{}) {
    
    ExecutionConfig<T> config = input_config;
    Matrix<T> result = multiply_auto(A, B, config);
    return {result, config};
}

} // namespace multiply
} // namespace matrix

#endif // MATRIX_MATRIX_MUL_EXT_H
