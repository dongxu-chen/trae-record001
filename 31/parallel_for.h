#ifndef PARALLEL_FOR_H
#define PARALLEL_FOR_H

#include <Eigen/Dense>
#include <Eigen/Sparse>
#include <functional>
#include <stdexcept>

#ifdef _OPENMP
#include <omp.h>
#endif

namespace matrix_lib {

struct ParallelConfig {
    int num_threads = -1;
    bool dynamic = true;
    int chunk_size = 1;

    static ParallelConfig default_config() {
        ParallelConfig config;
#ifdef _OPENMP
        config.num_threads = omp_get_max_threads();
#else
        config.num_threads = 1;
#endif
        return config;
    }
};

#ifdef _OPENMP
inline int get_max_threads() { return omp_get_max_threads(); }
inline int get_num_threads() { return omp_get_num_threads(); }
inline int get_thread_num() { return omp_get_thread_num(); }
#else
inline int get_max_threads() { return 1; }
inline int get_num_threads() { return 1; }
inline int get_thread_num() { return 0; }
#endif

template <typename Index, typename Func>
void parallel_for(Index begin, Index end, Func&& func,
                  const ParallelConfig& config = ParallelConfig::default_config()) {
#ifdef _OPENMP
    int original_threads = omp_get_max_threads();
    if (config.num_threads > 0) {
        omp_set_num_threads(config.num_threads);
    }

    if (config.dynamic) {
        #pragma omp parallel for schedule(dynamic, config.chunk_size)
        for (Index i = begin; i < end; ++i) {
            func(i);
        }
    } else {
        #pragma omp parallel for schedule(static, config.chunk_size)
        for (Index i = begin; i < end; ++i) {
            func(i);
        }
    }

    omp_set_num_threads(original_threads);
#else
    for (Index i = begin; i < end; ++i) {
        func(i);
    }
#endif
}

template <typename Index, typename Func>
void parallel_for(Index begin, Index end, Index step, Func&& func,
                  const ParallelConfig& config = ParallelConfig::default_config()) {
#ifdef _OPENMP
    int original_threads = omp_get_max_threads();
    if (config.num_threads > 0) {
        omp_set_num_threads(config.num_threads);
    }

    if (config.dynamic) {
        #pragma omp parallel for schedule(dynamic, config.chunk_size)
        for (Index i = begin; i < end; i += step) {
            func(i);
        }
    } else {
        #pragma omp parallel for schedule(static, config.chunk_size)
        for (Index i = begin; i < end; i += step) {
            func(i);
        }
    }

    omp_set_num_threads(original_threads);
#else
    for (Index i = begin; i < end; i += step) {
        func(i);
    }
#endif
}

template <typename Scalar>
Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic> parallel_add(
    const Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic>& A,
    const Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic>& B,
    const ParallelConfig& config = ParallelConfig::default_config()) {

    if (A.rows() != B.rows() || A.cols() != B.cols()) {
        throw std::invalid_argument("Matrix dimensions mismatch for addition");
    }

    Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic> C(A.rows(), A.cols());

    parallel_for(Eigen::Index(0), A.rows(), [&](Eigen::Index i) {
        for (Eigen::Index j = 0; j < A.cols(); ++j) {
            C(i, j) = A(i, j) + B(i, j);
        }
    }, config);

    return C;
}

template <typename Scalar>
Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic> parallel_multiply(
    const Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic>& A,
    const Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic>& B,
    const ParallelConfig& config = ParallelConfig::default_config()) {

    if (A.cols() != B.rows()) {
        throw std::invalid_argument("Matrix dimensions mismatch for multiplication");
    }

    Eigen::Index rowsA = A.rows();
    Eigen::Index colsA = A.cols();
    Eigen::Index colsB = B.cols();

    Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic> C(rowsA, colsB);
    C.setZero();

    constexpr Eigen::Index BLOCK_SIZE = 64;

    parallel_for(Eigen::Index(0), rowsA, BLOCK_SIZE, [&](Eigen::Index ii) {
        Eigen::Index i_max = (ii + BLOCK_SIZE < rowsA) ? (ii + BLOCK_SIZE) : rowsA;
        for (Eigen::Index jj = 0; jj < colsB; jj += BLOCK_SIZE) {
            Eigen::Index j_max = (jj + BLOCK_SIZE < colsB) ? (jj + BLOCK_SIZE) : colsB;
            for (Eigen::Index kk = 0; kk < colsA; kk += BLOCK_SIZE) {
                Eigen::Index k_max = (kk + BLOCK_SIZE < colsA) ? (kk + BLOCK_SIZE) : colsA;

                Eigen::Index block_rows = i_max - ii;
                Eigen::Index block_cols = j_max - jj;
                Eigen::Index block_k = k_max - kk;

                C.block(ii, jj, block_rows, block_cols).noalias() +=
                    A.block(ii, kk, block_rows, block_k) *
                    B.block(kk, jj, block_k, block_cols);
            }
        }
    }, config);

    return C;
}

template <typename Scalar>
Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic> parallel_transpose(
    const Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic>& A,
    const ParallelConfig& config = ParallelConfig::default_config()) {

    Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic> AT(A.cols(), A.rows());

    parallel_for(Eigen::Index(0), A.rows(), [&](Eigen::Index i) {
        for (Eigen::Index j = 0; j < A.cols(); ++j) {
            AT(j, i) = A(i, j);
        }
    }, config);

    return AT;
}

template <typename Scalar>
Eigen::Matrix<Scalar, Eigen::Dynamic, 1> parallel_sparse_multiply_vector(
    const Eigen::SparseMatrix<Scalar>& A,
    const Eigen::Matrix<Scalar, Eigen::Dynamic, 1>& x,
    const ParallelConfig& config = ParallelConfig::default_config()) {

    if (A.cols() != x.rows()) {
        throw std::invalid_argument("Matrix and vector dimensions mismatch");
    }

    Eigen::Matrix<Scalar, Eigen::Dynamic, 1> y(A.rows());
    y.setZero();

    parallel_for(Eigen::Index(0), A.outerSize(), [&](Eigen::Index k) {
        for (typename Eigen::SparseMatrix<Scalar>::InnerIterator it(A, k); it; ++it) {
#ifdef _OPENMP
            #pragma omp atomic
#endif
            y(it.row()) += it.value() * x(it.col());
        }
    }, config);

    return y;
}

template <typename Scalar>
void parallel_vector_apply(
    Eigen::Matrix<Scalar, Eigen::Dynamic, 1>& v,
    const std::function<Scalar(Scalar)>& func,
    const ParallelConfig& config = ParallelConfig::default_config()) {

    parallel_for(Eigen::Index(0), v.size(), [&](Eigen::Index i) {
        v(i) = func(v(i));
    }, config);
}

template <typename Scalar>
Scalar parallel_vector_reduce(
    const Eigen::Matrix<Scalar, Eigen::Dynamic, 1>& v,
    Scalar initial,
    const std::function<Scalar(Scalar, Scalar)>& reducer,
    const ParallelConfig& config = ParallelConfig::default_config()) {

    Scalar result = initial;

#ifdef _OPENMP
    int original_threads = omp_get_max_threads();
    if (config.num_threads > 0) {
        omp_set_num_threads(config.num_threads);
    }

    #pragma omp parallel for schedule(static) reduction(reduction:result)
    for (Eigen::Index i = 0; i < v.size(); ++i) {
        result = reducer(result, v(i));
    }

    omp_set_num_threads(original_threads);
#else
    for (Eigen::Index i = 0; i < v.size(); ++i) {
        result = reducer(result, v(i));
    }
#endif

    return result;
}

} 

#endif
