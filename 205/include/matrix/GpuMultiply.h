#ifndef MATRIX_GPU_MULTIPLY_H
#define MATRIX_GPU_MULTIPLY_H

#include "Matrix.h"
#include <stdexcept>
#include <string>

namespace matrix {
namespace gpu {

inline bool is_cuda_available() {
    return false;
}

inline std::string get_cuda_version() {
    return "CUDA not available (built without GPU support)";
}

template <typename T>
Matrix<T> multiply_gpu(const Matrix<T>& A, const Matrix<T>& B) {
    throw std::runtime_error("GPU multiplication not available. "
                             "Build with CUDA support to enable GPU acceleration.");
}

template <typename T>
Matrix<T> multiply_gpu_blocked(const Matrix<T>& A, const Matrix<T>& B,
                               std::size_t block_size = 32) {
    throw std::runtime_error("GPU multiplication not available. "
                             "Build with CUDA support to enable GPU acceleration.");
}

} // namespace gpu
} // namespace matrix

#endif // MATRIX_GPU_MULTIPLY_H
