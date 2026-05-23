#ifndef MATRIX_MULTIPLY_H
#define MATRIX_MULTIPLY_H

#include "Matrix.h"
#include <algorithm>
#include <cmath>
#include <cstddef>
#include <vector>
#include <memory>

#ifdef _OPENMP
#include <omp.h>
#endif

namespace matrix {
namespace multiply {

enum class Algorithm {
    Naive,
    Blocked,
    Strassen,
    Auto
};

namespace detail {

constexpr std::size_t MIN_BLOCK_SIZE = 32;
constexpr std::size_t MAX_BLOCK_SIZE = 256;
constexpr std::size_t STRASSEN_NAIVE_THRESHOLD = 64;

inline std::size_t calculate_optimal_block_size(std::size_t M, std::size_t K, std::size_t N) {
    const std::size_t avg_dim = (M + K + N) / 3;
    
    if (avg_dim < 64) {
        return 0;
    }
    
    std::size_t block_size = avg_dim / 8;
    block_size = std::max(MIN_BLOCK_SIZE, std::min(MAX_BLOCK_SIZE, block_size));
    
    while (block_size > MIN_BLOCK_SIZE && avg_dim % block_size != 0) {
        --block_size;
    }
    
    return block_size;
}

template <typename T>
class TemporaryMatrixPool {
public:
    static TemporaryMatrixPool& instance() {
        static TemporaryMatrixPool pool;
        return pool;
    }

    std::shared_ptr<Matrix<T>> acquire(std::size_t rows, std::size_t cols) {
        #pragma omp critical(pool_access)
        {
            for (auto it = pool_.begin(); it != pool_.end(); ++it) {
                if ((*it)->rows() == rows && (*it)->cols() == cols) {
                    auto mat = *it;
                    pool_.erase(it);
                    std::fill(mat->vector().begin(), mat->vector().end(), T{0});
                    return mat;
                }
            }
        }
        return std::make_shared<Matrix<T>>(rows, cols, T{0});
    }

    void release(std::shared_ptr<Matrix<T>> mat) {
        #pragma omp critical(pool_access)
        {
            if (pool_.size() < max_pool_size_) {
                pool_.push_back(mat);
            }
        }
    }

private:
    TemporaryMatrixPool() = default;
    std::vector<std::shared_ptr<Matrix<T>>> pool_;
    const std::size_t max_pool_size_ = 16;
};

} // namespace detail

template <typename T>
Matrix<T> naive(const Matrix<T>& A, const Matrix<T>& B) {
    const std::size_t M = A.rows();
    const std::size_t K = A.cols();
    const std::size_t N = B.cols();
    assert(K == B.rows());

    Matrix<T> C(M, N, T{0});

    #pragma omp parallel for
    for (std::size_t i = 0; i < M; ++i) {
        for (std::size_t k = 0; k < K; ++k) {
            const T a_ik = A(i, k);
            for (std::size_t j = 0; j < N; ++j) {
                C(i, j) += a_ik * B(k, j);
            }
        }
    }
    return C;
}

template <typename T>
Matrix<T> blocked(const Matrix<T>& A, const Matrix<T>& B, std::size_t block_size = 0) {
    const std::size_t M = A.rows();
    const std::size_t K = A.cols();
    const std::size_t N = B.cols();
    assert(K == B.rows());

    if (block_size == 0) {
        block_size = detail::calculate_optimal_block_size(M, K, N);
    }

    if (block_size < detail::MIN_BLOCK_SIZE || std::min({M, K, N}) <= block_size) {
        return naive(A, B);
    }

    Matrix<T> C(M, N, T{0});

    #pragma omp parallel for
    for (std::size_t i0 = 0; i0 < M; i0 += block_size) {
        const std::size_t i_end = std::min(i0 + block_size, M);
        for (std::size_t k0 = 0; k0 < K; k0 += block_size) {
            const std::size_t k_end = std::min(k0 + block_size, K);
            for (std::size_t j0 = 0; j0 < N; j0 += block_size) {
                const std::size_t j_end = std::min(j0 + block_size, N);

                for (std::size_t i = i0; i < i_end; ++i) {
                    for (std::size_t k = k0; k < k_end; ++k) {
                        const T a_ik = A(i, k);
                        for (std::size_t j = j0; j < j_end; ++j) {
                            C(i, j) += a_ik * B(k, j);
                        }
                    }
                }
            }
        }
    }
    return C;
}

namespace detail {

template <typename T>
void add_blocks(const T* A, const T* B, T* C, std::size_t n, std::size_t lda, std::size_t ldb, std::size_t ldc) {
    for (std::size_t i = 0; i < n; ++i) {
        for (std::size_t j = 0; j < n; ++j) {
            C[i * ldc + j] = A[i * lda + j] + B[i * ldb + j];
        }
    }
}

template <typename T>
void sub_blocks(const T* A, const T* B, T* C, std::size_t n, std::size_t lda, std::size_t ldb, std::size_t ldc) {
    for (std::size_t i = 0; i < n; ++i) {
        for (std::size_t j = 0; j < n; ++j) {
            C[i * ldc + j] = A[i * lda + j] - B[i * ldb + j];
        }
    }
}

template <typename T>
void strassen_recursive_inplace(const T* A, const T* B, T* C, std::size_t n,
                                std::size_t lda, std::size_t ldb, std::size_t ldc,
                                std::size_t threshold,
                                Matrix<T>& tmp1, Matrix<T>& tmp2,
                                Matrix<T>& tmp3, Matrix<T>& tmp4) {
    if (n <= threshold) {
        if (n < STRASSEN_NAIVE_THRESHOLD) {
            for (std::size_t i = 0; i < n; ++i) {
                for (std::size_t k = 0; k < n; ++k) {
                    const T a_ik = A[i * lda + k];
                    for (std::size_t j = 0; j < n; ++j) {
                        C[i * ldc + j] += a_ik * B[k * ldb + j];
                    }
                }
            }
        } else {
            const std::size_t block = 32;
            for (std::size_t i0 = 0; i0 < n; i0 += block) {
                const std::size_t i_end = std::min(i0 + block, n);
                for (std::size_t k0 = 0; k0 < n; k0 += block) {
                    const std::size_t k_end = std::min(k0 + block, n);
                    for (std::size_t j0 = 0; j0 < n; j0 += block) {
                        const std::size_t j_end = std::min(j0 + block, n);
                        for (std::size_t i = i0; i < i_end; ++i) {
                            for (std::size_t k = k0; k < k_end; ++k) {
                                const T a_ik = A[i * lda + k];
                                for (std::size_t j = j0; j < j_end; ++j) {
                                    C[i * ldc + j] += a_ik * B[k * ldb + j];
                                }
                            }
                        }
                    }
                }
            }
        }
        return;
    }

    const std::size_t new_n = n / 2;

    const T* a11 = A;
    const T* a12 = A + new_n;
    const T* a21 = A + new_n * lda;
    const T* a22 = A + new_n * lda + new_n;

    const T* b11 = B;
    const T* b12 = B + new_n;
    const T* b21 = B + new_n * ldb;
    const T* b22 = B + new_n * ldb + new_n;

    T* c11 = C;
    T* c12 = C + new_n;
    T* c21 = C + new_n * ldc;
    T* c22 = C + new_n * ldc + new_n;

    T* t1_ptr = tmp1.data();
    T* t2_ptr = tmp2.data();
    T* t3_ptr = tmp3.data();
    T* t4_ptr = tmp4.data();

    Matrix<T> m1_ptr(new_n, new_n);
    Matrix<T> m2_ptr(new_n, new_n);
    Matrix<T> m3_ptr(new_n, new_n);
    Matrix<T> m4_ptr(new_n, new_n);
    Matrix<T> m5_ptr(new_n, new_n);
    Matrix<T> m6_ptr(new_n, new_n);
    Matrix<T> m7_ptr(new_n, new_n);

    T* m1 = m1_ptr.data();
    T* m2 = m2_ptr.data();
    T* m3 = m3_ptr.data();
    T* m4 = m4_ptr.data();
    T* m5 = m5_ptr.data();
    T* m6 = m6_ptr.data();
    T* m7 = m7_ptr.data();

    #pragma omp parallel sections private(t1_ptr, t2_ptr, t3_ptr, t4_ptr)
    {
        #pragma omp section
        {
            add_blocks(a11, a22, t1_ptr, new_n, lda, lda, new_n);
            add_blocks(b11, b22, t2_ptr, new_n, ldb, ldb, new_n);
            std::fill(m1, m1 + new_n * new_n, T{0});
            strassen_recursive_inplace(t1_ptr, t2_ptr, m1, new_n, new_n, new_n, new_n, threshold, tmp1, tmp2, tmp3, tmp4);
        }

        #pragma omp section
        {
            add_blocks(a21, a22, t1_ptr, new_n, lda, lda, new_n);
            std::fill(m2, m2 + new_n * new_n, T{0});
            strassen_recursive_inplace(t1_ptr, b11, m2, new_n, new_n, ldb, new_n, threshold, tmp1, tmp2, tmp3, tmp4);
        }

        #pragma omp section
        {
            sub_blocks(b12, b22, t1_ptr, new_n, ldb, ldb, new_n);
            std::fill(m3, m3 + new_n * new_n, T{0});
            strassen_recursive_inplace(a11, t1_ptr, m3, new_n, lda, new_n, new_n, threshold, tmp1, tmp2, tmp3, tmp4);
        }

        #pragma omp section
        {
            sub_blocks(b21, b11, t1_ptr, new_n, ldb, ldb, new_n);
            std::fill(m4, m4 + new_n * new_n, T{0});
            strassen_recursive_inplace(a22, t1_ptr, m4, new_n, lda, new_n, new_n, threshold, tmp1, tmp2, tmp3, tmp4);
        }

        #pragma omp section
        {
            add_blocks(a11, a12, t1_ptr, new_n, lda, lda, new_n);
            std::fill(m5, m5 + new_n * new_n, T{0});
            strassen_recursive_inplace(t1_ptr, b22, m5, new_n, new_n, ldb, new_n, threshold, tmp1, tmp2, tmp3, tmp4);
        }

        #pragma omp section
        {
            sub_blocks(a21, a11, t1_ptr, new_n, lda, lda, new_n);
            add_blocks(b11, b12, t2_ptr, new_n, ldb, ldb, new_n);
            std::fill(m6, m6 + new_n * new_n, T{0});
            strassen_recursive_inplace(t1_ptr, t2_ptr, m6, new_n, new_n, new_n, new_n, threshold, tmp1, tmp2, tmp3, tmp4);
        }

        #pragma omp section
        {
            sub_blocks(a12, a22, t1_ptr, new_n, lda, lda, new_n);
            add_blocks(b21, b22, t2_ptr, new_n, ldb, ldb, new_n);
            std::fill(m7, m7 + new_n * new_n, T{0});
            strassen_recursive_inplace(t1_ptr, t2_ptr, m7, new_n, new_n, new_n, new_n, threshold, tmp1, tmp2, tmp3, tmp4);
        }
    }

    for (std::size_t i = 0; i < new_n; ++i) {
        const std::size_t i_c11 = i * ldc;
        const std::size_t i_c21 = (i + new_n) * ldc;
        const std::size_t i_m = i * new_n;
        for (std::size_t j = 0; j < new_n; ++j) {
            const T m1v = m1[i_m + j];
            const T m2v = m2[i_m + j];
            const T m3v = m3[i_m + j];
            const T m4v = m4[i_m + j];
            const T m5v = m5[i_m + j];
            const T m6v = m6[i_m + j];
            const T m7v = m7[i_m + j];

            c11[i_c11 + j] = m1v + m4v - m5v + m7v;
            c12[i_c11 + j + new_n] = m3v + m5v;
            c21[i_c21 + j] = m2v + m4v;
            c22[i_c21 + j + new_n] = m1v - m2v + m3v + m6v;
        }
    }
}

template <typename T>
std::size_t next_power_of_two(std::size_t n) {
    std::size_t result = 1;
    while (result < n) {
        result <<= 1;
    }
    return result;
}

} // namespace detail

template <typename T>
Matrix<T> strassen(const Matrix<T>& A, const Matrix<T>& B,
                   std::size_t threshold = 128) {
    const std::size_t M = A.rows();
    const std::size_t K = A.cols();
    const std::size_t N = B.cols();
    assert(K == B.rows());

    if (std::min({M, K, N}) < detail::STRASSEN_NAIVE_THRESHOLD * 2) {
        return blocked(A, B);
    }

    const std::size_t max_dim = std::max({M, K, N});
    const std::size_t padded_size = detail::next_power_of_two(max_dim);

    Matrix<T> A_padded = Matrix<T>::zero(padded_size, padded_size);
    Matrix<T> B_padded = Matrix<T>::zero(padded_size, padded_size);

    for (std::size_t i = 0; i < M; ++i) {
        for (std::size_t j = 0; j < K; ++j) {
            A_padded(i, j) = A(i, j);
        }
    }

    for (std::size_t i = 0; i < K; ++i) {
        for (std::size_t j = 0; j < N; ++j) {
            B_padded(i, j) = B(i, j);
        }
    }

    const std::size_t tmp_size = padded_size / 2;
    Matrix<T> tmp1(tmp_size, tmp_size);
    Matrix<T> tmp2(tmp_size, tmp_size);
    Matrix<T> tmp3(tmp_size, tmp_size);
    Matrix<T> tmp4(tmp_size, tmp_size);

    Matrix<T> C_padded(padded_size, padded_size, T{0});

    detail::strassen_recursive_inplace(
        A_padded.data(), B_padded.data(), C_padded.data(),
        padded_size, padded_size, padded_size, padded_size,
        threshold, tmp1, tmp2, tmp3, tmp4
    );

    Matrix<T> C(M, N);
    for (std::size_t i = 0; i < M; ++i) {
        for (std::size_t j = 0; j < N; ++j) {
            C(i, j) = C_padded(i, j);
        }
    }

    return C;
}

namespace detail {

template <typename T>
struct AlgorithmSelector {
    static Algorithm select(std::size_t M, std::size_t K, std::size_t N) {
        const std::size_t min_dim = std::min({M, K, N});
        const std::size_t avg_dim = (M + K + N) / 3;

        if (min_dim < 64) {
            return Algorithm::Naive;
        } else if (avg_dim < 256) {
            return Algorithm::Blocked;
        } else if (avg_dim < 512) {
            return Algorithm::Blocked;
        } else {
            return Algorithm::Strassen;
        }
    }
};

} // namespace detail

template <typename T>
Matrix<T> multiply(const Matrix<T>& A, const Matrix<T>& B,
                   Algorithm algo = Algorithm::Auto,
                   std::size_t block_size = 0,
                   std::size_t strassen_threshold = 128) {
    if (algo == Algorithm::Auto) {
        algo = detail::AlgorithmSelector<T>::select(A.rows(), A.cols(), B.cols());
    }

    switch (algo) {
        case Algorithm::Naive:
            return naive(A, B);
        case Algorithm::Blocked:
            return blocked(A, B, block_size);
        case Algorithm::Strassen:
            return strassen(A, B, strassen_threshold);
        default:
            return blocked(A, B, block_size);
    }
}

} // namespace multiply
} // namespace matrix

#endif // MATRIX_MULTIPLY_H
