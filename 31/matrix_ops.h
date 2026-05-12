#ifndef MATRIX_OPS_H
#define MATRIX_OPS_H

#include <Eigen/Dense>
#include <Eigen/Sparse>
#include <stdexcept>

namespace matrix_lib {

template <typename Scalar, int Rows, int Cols>
Eigen::Matrix<Scalar, Rows, Cols> add(
    const Eigen::Matrix<Scalar, Rows, Cols>& A,
    const Eigen::Matrix<Scalar, Rows, Cols>& B) {
    return A + B;
}

template <typename Scalar>
Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic> add_dynamic(
    const Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic>& A,
    const Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic>& B) {
    if (A.rows() != B.rows() || A.cols() != B.cols()) {
        throw std::invalid_argument("Matrix dimensions mismatch for addition");
    }
    return A + B;
}

template <typename Scalar, int RowsA, int ColsA, int ColsB>
Eigen::Matrix<Scalar, RowsA, ColsB> multiply(
    const Eigen::Matrix<Scalar, RowsA, ColsA>& A,
    const Eigen::Matrix<Scalar, ColsA, ColsB>& B) {
    Eigen::Matrix<Scalar, RowsA, ColsB> C;
    C.noalias() = A * B;
    return C;
}

template <typename Scalar>
Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic> multiply_dynamic(
    const Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic>& A,
    const Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic>& B) {
    if (A.cols() != B.rows()) {
        throw std::invalid_argument("Matrix dimensions mismatch for multiplication");
    }

    Eigen::Index rowsA = A.rows();
    Eigen::Index colsA = A.cols();
    Eigen::Index colsB = B.cols();

    Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic> C(rowsA, colsB);
    C.setZero();

    constexpr Eigen::Index BLOCK_SIZE = 64;

    for (Eigen::Index ii = 0; ii < rowsA; ii += BLOCK_SIZE) {
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
    }

    return C;
}

template <typename Scalar, int N>
Eigen::Matrix<Scalar, N, N> inverse(const Eigen::Matrix<Scalar, N, N>& A) {
    Eigen::Matrix<Scalar, N, N> inv = A.inverse();
    if (inv.rows() == 0 || inv.cols() == 0) {
        throw std::runtime_error("Matrix is singular and cannot be inverted");
    }
    return inv;
}

template <typename Scalar>
Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic> inverse_dynamic(
    const Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic>& A) {
    if (A.rows() != A.cols()) {
        throw std::invalid_argument("Matrix must be square to compute inverse");
    }
    Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic> inv = A.inverse();
    if (inv.rows() == 0 || inv.cols() == 0) {
        throw std::runtime_error("Matrix is singular and cannot be inverted");
    }
    return inv;
}

template <typename Scalar, int Rows, int Cols>
Scalar determinant(const Eigen::Matrix<Scalar, Rows, Cols>& A) {
    static_assert(Rows == Cols, "Matrix must be square for determinant");
    return A.determinant();
}

template <typename Scalar>
Scalar determinant_dynamic(
    const Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic>& A) {
    if (A.rows() != A.cols()) {
        throw std::invalid_argument("Matrix must be square for determinant");
    }
    return A.determinant();
}

template <typename Scalar, int Rows, int Cols>
Eigen::Matrix<Scalar, Cols, Rows> transpose(const Eigen::Matrix<Scalar, Rows, Cols>& A) {
    return A.transpose();
}

template <typename Scalar>
Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic> transpose_dynamic(
    const Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic>& A) {
    return A.transpose();
}

enum class StorageFormat {
    CSC,
    CSR,
    COO
};

template <typename Scalar>
Eigen::SparseMatrix<Scalar, Eigen::ColMajor> dense_to_sparse_csc(
    const Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic>& dense,
    Scalar tolerance = static_cast<Scalar>(1e-10)) {

    Eigen::SparseMatrix<Scalar, Eigen::ColMajor> sparse(dense.rows(), dense.cols());

    std::vector<Eigen::Triplet<Scalar>> triplets;
    triplets.reserve(dense.size() / 10);

    for (Eigen::Index j = 0; j < dense.cols(); ++j) {
        for (Eigen::Index i = 0; i < dense.rows(); ++i) {
            if (std::abs(dense(i, j)) > tolerance) {
                triplets.emplace_back(i, j, dense(i, j));
            }
        }
    }

    sparse.setFromTriplets(triplets.begin(), triplets.end());
    return sparse;
}

template <typename Scalar>
Eigen::SparseMatrix<Scalar, Eigen::RowMajor> dense_to_sparse_csr(
    const Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic>& dense,
    Scalar tolerance = static_cast<Scalar>(1e-10)) {

    Eigen::SparseMatrix<Scalar, Eigen::RowMajor> sparse(dense.rows(), dense.cols());

    std::vector<Eigen::Triplet<Scalar>> triplets;
    triplets.reserve(dense.size() / 10);

    for (Eigen::Index i = 0; i < dense.rows(); ++i) {
        for (Eigen::Index j = 0; j < dense.cols(); ++j) {
            if (std::abs(dense(i, j)) > tolerance) {
                triplets.emplace_back(i, j, dense(i, j));
            }
        }
    }

    sparse.setFromTriplets(triplets.begin(), triplets.end());
    return sparse;
}

template <typename Scalar>
Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic> sparse_to_dense(
    const Eigen::SparseMatrix<Scalar>& sparse) {
    return Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic>(sparse);
}

template <typename Scalar, int Options>
Eigen::SparseMatrix<Scalar, Options> sparse_add(
    const Eigen::SparseMatrix<Scalar, Options>& A,
    const Eigen::SparseMatrix<Scalar, Options>& B) {

    if (A.rows() != B.rows() || A.cols() != B.cols()) {
        throw std::invalid_argument("Matrix dimensions mismatch for sparse addition");
    }
    return A + B;
}

template <typename Scalar, int Options>
Eigen::SparseMatrix<Scalar, Options> sparse_multiply(
    const Eigen::SparseMatrix<Scalar, Options>& A,
    const Eigen::SparseMatrix<Scalar, Options>& B) {

    if (A.cols() != B.rows()) {
        throw std::invalid_argument("Matrix dimensions mismatch for sparse multiplication");
    }
    return A * B;
}

template <typename Scalar, int Options>
Eigen::Matrix<Scalar, Eigen::Dynamic, 1> sparse_multiply_dense_vector(
    const Eigen::SparseMatrix<Scalar, Options>& A,
    const Eigen::Matrix<Scalar, Eigen::Dynamic, 1>& x) {

    if (A.cols() != x.rows()) {
        throw std::invalid_argument("Matrix and vector dimensions mismatch");
    }
    return A * x;
}

template <typename Scalar, int Options>
Eigen::SparseMatrix<Scalar, Options> sparse_transpose(
    const Eigen::SparseMatrix<Scalar, Options>& A) {
    return A.transpose();
}

template <typename Scalar, int Options>
Eigen::Index sparse_nnz(const Eigen::SparseMatrix<Scalar, Options>& A) {
    return A.nonZeros();
}

template <typename Scalar, int Options>
double sparse_density(const Eigen::SparseMatrix<Scalar, Options>& A) {
    double total = static_cast<double>(A.rows()) * A.cols();
    return static_cast<double>(A.nonZeros()) / total;
}

template <typename Scalar, int Options>
void sparse_prune(Eigen::SparseMatrix<Scalar, Options>& A, Scalar tolerance) {
    A.prune(tolerance);
}

template <typename Scalar, int Options>
Eigen::SparseMatrix<Scalar, Options> sparse_identity(Eigen::Index size) {
    Eigen::SparseMatrix<Scalar, Options> I(size, size);
    I.setIdentity();
    return I;
}

template <typename Scalar, int Options>
void sparse_set_from_triplets(
    Eigen::SparseMatrix<Scalar, Options>& sparse,
    const std::vector<Eigen::Triplet<Scalar>>& triplets,
    bool sorted = false) {

    if (sorted) {
        sparse.setFromTriplets(triplets.begin(), triplets.end(),
            [](const Scalar& a, const Scalar& b) { return a + b; });
    } else {
        sparse.setFromTriplets(triplets.begin(), triplets.end());
    }
}

} 

#endif
