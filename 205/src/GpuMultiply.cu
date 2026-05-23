#include "matrix/GpuMultiply.h"
#include "matrix/Matrix.h"
#include <cuda_runtime.h>
#include <stdexcept>

namespace matrix {
namespace gpu {

#define CUDA_CHECK(err) \
    if (err != cudaSuccess) { \
        throw std::runtime_error("CUDA error: " + std::string(cudaGetErrorString(err))); \
    }

__global__ void matmul_kernel(float* C, const float* A, const float* B,
                               int M, int K, int N) {
    int row = blockIdx.y * blockDim.y + threadIdx.y;
    int col = blockIdx.x * blockDim.x + threadIdx.x;

    if (row < M && col < N) {
        float sum = 0.0f;
        for (int k = 0; k < K; ++k) {
            sum += A[row * K + k] * B[k * N + col];
        }
        C[row * N + col] = sum;
    }
}

__global__ void matmul_kernel(double* C, const double* A, const double* B,
                               int M, int K, int N) {
    int row = blockIdx.y * blockDim.y + threadIdx.y;
    int col = blockIdx.x * blockDim.x + threadIdx.x;

    if (row < M && col < N) {
        double sum = 0.0;
        for (int k = 0; k < K; ++k) {
            sum += A[row * K + k] * B[k * N + col];
        }
        C[row * N + col] = sum;
    }
}

__global__ void matmul_tiled_kernel(float* C, const float* A, const float* B,
                                     int M, int K, int N, int tile_size) {
    extern __shared__ float shared[];
    float* sA = shared;
    float* sB = shared + tile_size * tile_size;

    int tx = threadIdx.x;
    int ty = threadIdx.y;
    int bx = blockIdx.x;
    int by = blockIdx.y;

    int row = by * tile_size + ty;
    int col = bx * tile_size + tx;

    float sum = 0.0f;

    for (int t = 0; t < (K + tile_size - 1) / tile_size; ++t) {
        if (row < M && t * tile_size + tx < K) {
            sA[ty * tile_size + tx] = A[row * K + t * tile_size + tx];
        } else {
            sA[ty * tile_size + tx] = 0.0f;
        }

        if (col < N && t * tile_size + ty < K) {
            sB[ty * tile_size + tx] = B[(t * tile_size + ty) * N + col];
        } else {
            sB[ty * tile_size + tx] = 0.0f;
        }

        __syncthreads();

        for (int k = 0; k < tile_size; ++k) {
            sum += sA[ty * tile_size + k] * sB[k * tile_size + tx];
        }

        __syncthreads();
    }

    if (row < M && col < N) {
        C[row * N + col] = sum;
    }
}

bool is_cuda_available() {
    int deviceCount;
    cudaError_t err = cudaGetDeviceCount(&deviceCount);
    return (err == cudaSuccess && deviceCount > 0);
}

std::string get_cuda_version() {
    if (!is_cuda_available()) {
        return "No CUDA devices found";
    }
    
    int device;
    cudaGetDevice(&device);
    
    cudaDeviceProp prop;
    cudaGetDeviceProperties(&prop, device);
    
    return std::string("CUDA ") + prop.name + 
           " (Compute Capability " + 
           std::to_string(prop.major) + "." + std::to_string(prop.minor) + ")";
}

template <typename T>
Matrix<T> multiply_gpu(const Matrix<T>& A, const Matrix<T>& B) {
    const std::size_t M = A.rows();
    const std::size_t K = A.cols();
    const std::size_t N = B.cols();
    assert(K == B.rows());

    if (!is_cuda_available()) {
        throw std::runtime_error("No CUDA devices available");
    }

    T* d_A;
    T* d_B;
    T* d_C;

    CUDA_CHECK(cudaMalloc(&d_A, M * K * sizeof(T)));
    CUDA_CHECK(cudaMalloc(&d_B, K * N * sizeof(T)));
    CUDA_CHECK(cudaMalloc(&d_C, M * N * sizeof(T)));

    CUDA_CHECK(cudaMemcpy(d_A, A.data(), M * K * sizeof(T), cudaMemcpyHostToDevice));
    CUDA_CHECK(cudaMemcpy(d_B, B.data(), K * N * sizeof(T), cudaMemcpyHostToDevice));

    dim3 blockDim(16, 16);
    dim3 gridDim((N + blockDim.x - 1) / blockDim.x,
                 (M + blockDim.y - 1) / blockDim.y);

    matmul_kernel<<<gridDim, blockDim>>>(d_C, d_A, d_B,
                                         static_cast<int>(M),
                                         static_cast<int>(K),
                                         static_cast<int>(N));

    CUDA_CHECK(cudaGetLastError());
    CUDA_CHECK(cudaDeviceSynchronize());

    Matrix<T> C(M, N);
    CUDA_CHECK(cudaMemcpy(C.data(), d_C, M * N * sizeof(T), cudaMemcpyDeviceToHost));

    CUDA_CHECK(cudaFree(d_A));
    CUDA_CHECK(cudaFree(d_B));
    CUDA_CHECK(cudaFree(d_C));

    return C;
}

template <typename T>
Matrix<T> multiply_gpu_blocked(const Matrix<T>& A, const Matrix<T>& B,
                               std::size_t tile_size) {
    const std::size_t M = A.rows();
    const std::size_t K = A.cols();
    const std::size_t N = B.cols();
    assert(K == B.rows());

    if (!is_cuda_available()) {
        throw std::runtime_error("No CUDA devices available");
    }

    T* d_A;
    T* d_B;
    T* d_C;

    CUDA_CHECK(cudaMalloc(&d_A, M * K * sizeof(T)));
    CUDA_CHECK(cudaMalloc(&d_B, K * N * sizeof(T)));
    CUDA_CHECK(cudaMalloc(&d_C, M * N * sizeof(T)));

    CUDA_CHECK(cudaMemcpy(d_A, A.data(), M * K * sizeof(T), cudaMemcpyHostToDevice));
    CUDA_CHECK(cudaMemcpy(d_B, B.data(), K * N * sizeof(T), cudaMemcpyHostToDevice));

    dim3 blockDim(static_cast<unsigned int>(tile_size), 
                  static_cast<unsigned int>(tile_size));
    dim3 gridDim((N + tile_size - 1) / tile_size,
                 (M + tile_size - 1) / tile_size);
    size_t shared_size = 2 * tile_size * tile_size * sizeof(float);

    matmul_tiled_kernel<<<gridDim, blockDim, shared_size>>>(
        d_C, d_A, d_B,
        static_cast<int>(M),
        static_cast<int>(K),
        static_cast<int>(N),
        static_cast<int>(tile_size));

    CUDA_CHECK(cudaGetLastError());
    CUDA_CHECK(cudaDeviceSynchronize());

    Matrix<T> C(M, N);
    CUDA_CHECK(cudaMemcpy(C.data(), d_C, M * N * sizeof(T), cudaMemcpyDeviceToHost));

    CUDA_CHECK(cudaFree(d_A));
    CUDA_CHECK(cudaFree(d_B));
    CUDA_CHECK(cudaFree(d_C));

    return C;
}

template Matrix<float> multiply_gpu<float>(const Matrix<float>&, const Matrix<float>&);
template Matrix<double> multiply_gpu<double>(const Matrix<double>&, const Matrix<double>&);
template Matrix<float> multiply_gpu_blocked<float>(const Matrix<float>&, const Matrix<float>&, std::size_t);

} // namespace gpu
} // namespace matrix
