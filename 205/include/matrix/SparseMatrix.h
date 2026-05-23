#ifndef MATRIX_SPARSE_MATRIX_H
#define MATRIX_SPARSE_MATRIX_H

#include "Matrix.h"
#include <vector>
#include <cstddef>
#include <cassert>
#include <algorithm>
#include <tuple>

namespace matrix {

template <typename T>
class SparseMatrixCSR {
public:
    using value_type = T;
    using size_type = std::size_t;
    using index_type = std::int32_t;

    SparseMatrixCSR() : rows_(0), cols_(0), nnz_(0) {}

    SparseMatrixCSR(size_type rows, size_type cols, size_type nnz_hint = 0)
        : rows_(rows), cols_(cols), nnz_(0) {
        row_ptr_.resize(rows + 1, 0);
        if (nnz_hint > 0) {
            col_idx_.reserve(nnz_hint);
            values_.reserve(nnz_hint);
        }
    }

    static SparseMatrixCSR from_dense(const Matrix<T>& dense, T threshold = T{0}) {
        const size_type rows = dense.rows();
        const size_type cols = dense.cols();

        SparseMatrixCSR result(rows, cols);
        result.row_ptr_.resize(rows + 1);

        std::vector<size_type> nnz_per_row(rows, 0);
        for (size_type i = 0; i < rows; ++i) {
            for (size_type j = 0; j < cols; ++j) {
                if (std::abs(dense(i, j)) > threshold) {
                    ++nnz_per_row[i];
                }
            }
        }

        result.row_ptr_[0] = 0;
        for (size_type i = 0; i < rows; ++i) {
            result.row_ptr_[i + 1] = result.row_ptr_[i] + nnz_per_row[i];
        }

        result.nnz_ = result.row_ptr_[rows];
        result.col_idx_.resize(result.nnz_);
        result.values_.resize(result.nnz_);

        std::vector<size_type> current_pos = result.row_ptr_;
        for (size_type i = 0; i < rows; ++i) {
            for (size_type j = 0; j < cols; ++j) {
                const T val = dense(i, j);
                if (std::abs(val) > threshold) {
                    const size_type pos = current_pos[i]++;
                    result.col_idx_[pos] = static_cast<index_type>(j);
                    result.values_[pos] = val;
                }
            }
        }

        return result;
    }

    Matrix<T> to_dense() const {
        Matrix<T> result(rows_, cols_, T{0});
        for (size_type i = 0; i < rows_; ++i) {
            const size_type row_start = row_ptr_[i];
            const size_type row_end = row_ptr_[i + 1];
            for (size_type k = row_start; k < row_end; ++k) {
                result(i, col_idx_[k]) = values_[k];
            }
        }
        return result;
    }

    static double calculate_sparsity(const Matrix<T>& dense, T threshold = T{0}) {
        const size_type total = dense.rows() * dense.cols();
        size_type nnz = 0;
        for (size_type i = 0; i < dense.rows(); ++i) {
            for (size_type j = 0; j < dense.cols(); ++j) {
                if (std::abs(dense(i, j)) > threshold) {
                    ++nnz;
                }
            }
        }
        return 1.0 - static_cast<double>(nnz) / static_cast<double>(total);
    }

    size_type rows() const noexcept { return rows_; }
    size_type cols() const noexcept { return cols_; }
    size_type nnz() const noexcept { return nnz_; }
    double sparsity() const {
        return 1.0 - static_cast<double>(nnz_) / static_cast<double>(rows_ * cols_);
    }

    const std::vector<size_type>& row_ptr() const noexcept { return row_ptr_; }
    const std::vector<index_type>& col_idx() const noexcept { return col_idx_; }
    const std::vector<T>& values() const noexcept { return values_; }

    void insert(size_type row, size_type col, T value) {
        assert(row < rows_ && col < cols_);
        col_idx_.push_back(static_cast<index_type>(col));
        values_.push_back(value);
        ++nnz_;
    }

    void finalize() {
        row_ptr_.clear();
        row_ptr_.resize(rows_ + 1, 0);

        std::vector<std::vector<std::pair<index_type, T>>> row_data(rows_);
        for (size_type k = 0; k < nnz_; ++k) {
            size_type row = 0;
            size_type pos = k;
            for (size_type i = 0; i < rows_; ++i) {
                if (pos < row_data[i].size()) {
                    row = i;
                    break;
                }
                pos -= row_data[i].size();
            }
        }
    }

private:
    size_type rows_;
    size_type cols_;
    size_type nnz_;
    std::vector<size_type> row_ptr_;
    std::vector<index_type> col_idx_;
    std::vector<T> values_;
};

namespace sparse {

template <typename T>
Matrix<T> multiply_csr_dense(const SparseMatrixCSR<T>& A_sparse, const Matrix<T>& B) {
    const size_type M = A_sparse.rows();
    const size_type N = B.cols();
    assert(A_sparse.cols() == B.rows());

    const auto& row_ptr = A_sparse.row_ptr();
    const auto& col_idx = A_sparse.col_idx();
    const auto& values = A_sparse.values();

    Matrix<T> C(M, N, T{0});

    #pragma omp parallel for
    for (size_type i = 0; i < M; ++i) {
        const size_type row_start = row_ptr[i];
        const size_type row_end = row_ptr[i + 1];

        for (size_type k = row_start; k < row_end; ++k) {
            const size_type j_col = col_idx[k];
            const T a_val = values[k];

            for (size_type j = 0; j < N; ++j) {
                C(i, j) += a_val * B(j_col, j);
            }
        }
    }

    return C;
}

template <typename T>
SparseMatrixCSR<T> multiply_csr_csr(const SparseMatrixCSR<T>& A, const SparseMatrixCSR<T>& B) {
    const size_type M = A.rows();
    const size_type K = A.cols();
    const size_type N = B.cols();
    assert(K == B.rows());

    SparseMatrixCSR<T> C(M, N);
    std::vector<T> row_vals(N, T{0});
    std::vector<bool> row_mask(N, false);

    C.row_ptr().resize(M + 1, 0);
    size_type total_nnz = 0;

    for (size_type i = 0; i < M; ++i) {
        const size_type a_start = A.row_ptr()[i];
        const size_type a_end = A.row_ptr()[i + 1];

        for (size_type k_a = a_start; k_a < a_end; ++k_a) {
            const size_type k = A.col_idx()[k_a];
            const T a_val = A.values()[k_a];

            const size_type b_start = B.row_ptr()[k];
            const size_type b_end = B.row_ptr()[k + 1];

            for (size_type k_b = b_start; k_b < b_end; ++k_b) {
                const size_type j = B.col_idx()[k_b];
                const T b_val = B.values()[k_b];

                row_vals[j] += a_val * b_val;
                if (!row_mask[j]) {
                    row_mask[j] = true;
                    ++total_nnz;
                }
            }
        }

        C.row_ptr()[i + 1] = total_nnz;

        for (size_type j = 0; j < N; ++j) {
            if (row_mask[j]) {
                C.col_idx().push_back(static_cast<typename SparseMatrixCSR<T>::index_type>(j));
                C.values().push_back(row_vals[j]);
                row_vals[j] = T{0};
                row_mask[j] = false;
            }
        }
    }

    return C;
}

} // namespace sparse
} // namespace matrix

#endif // MATRIX_SPARSE_MATRIX_H
