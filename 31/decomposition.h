#ifndef DECOMPOSITION_H
#define DECOMPOSITION_H

#include <Eigen/Dense>
#include <Eigen/Sparse>
#include <Eigen/SparseLU>
#include <Eigen/SparseCholesky>
#include <stdexcept>
#include <tuple>
#include <limits>

namespace matrix_lib {

template <typename Scalar>
struct LUDecomposition {
    Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic> L;
    Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic> U;
    Eigen::MatrixXi P;
};

template <typename Scalar>
LUDecomposition<Scalar> lu_decomposition(
    const Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic>& A) {
    if (A.rows() != A.cols()) {
        throw std::invalid_argument("Matrix must be square for LU decomposition");
    }

    Eigen::PartialPivLU<Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic>> lu(A);

    LUDecomposition<Scalar> result;
    result.L = Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic>::Identity(A.rows(), A.rows());
    result.L.template triangularView<Eigen::StrictlyLower>() = lu.matrixLU();
    result.U = lu.matrixLU().template triangularView<Eigen::Upper>();
    result.P = lu.permutationP();

    return result;
}

template <typename Scalar>
struct QRDecomposition {
    Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic> Q;
    Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic> R;
    Eigen::PermutationMatrix<Eigen::Dynamic, Eigen::Dynamic> P;
    Scalar condition_number;
};

template <typename Scalar>
QRDecomposition<Scalar> qr_decomposition(
    const Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic>& A) {

    Eigen::ColPivHouseholderQR<Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic>> qr(A);

    QRDecomposition<Scalar> result;
    result.Q = qr.householderQ();
    result.R = qr.matrixQR().template triangularView<Eigen::Upper>();
    result.P = qr.colsPermutation();

    Eigen::VectorXd diag = qr.matrixQR().diagonal();
    if (diag.size() > 0) {
        Scalar max_diag = diag.array().abs().maxCoeff();
        Scalar min_diag = diag.array().abs().minCoeff();
        if (min_diag > static_cast<Scalar>(0)) {
            result.condition_number = max_diag / min_diag;
        } else {
            result.condition_number = std::numeric_limits<Scalar>::infinity();
        }
    } else {
        result.condition_number = static_cast<Scalar>(1);
    }

    return result;
}

template <typename Scalar>
struct CholeskyDecomposition {
    Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic> L;
};

template <typename Scalar>
CholeskyDecomposition<Scalar> cholesky_decomposition(
    const Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic>& A) {
    if (A.rows() != A.cols()) {
        throw std::invalid_argument("Matrix must be square for Cholesky decomposition");
    }

    Eigen::LLT<Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic>> llt(A);

    if (llt.info() != Eigen::Success) {
        throw std::runtime_error("Matrix is not positive definite for Cholesky decomposition");
    }

    CholeskyDecomposition<Scalar> result;
    result.L = llt.matrixL();

    return result;
}

template <typename Scalar, int Options>
struct SparseLUDecomposition {
    Eigen::SparseMatrix<Scalar, Options> L;
    Eigen::SparseMatrix<Scalar, Options> U;
    Eigen::PermutationMatrix<Eigen::Dynamic, Eigen::Dynamic> P;
    Eigen::PermutationMatrix<Eigen::Dynamic, Eigen::Dynamic> Q;
};

template <typename Scalar>
SparseLUDecomposition<Scalar, Eigen::ColMajor> sparse_lu_decomposition(
    const Eigen::SparseMatrix<Scalar, Eigen::ColMajor>& A) {

    if (A.rows() != A.cols()) {
        throw std::invalid_argument("Matrix must be square for sparse LU decomposition");
    }

    Eigen::SparseLU<Eigen::SparseMatrix<Scalar, Eigen::ColMajor>> lu;
    lu.analyzePattern(A);
    lu.factorize(A);

    if (lu.info() != Eigen::Success) {
        throw std::runtime_error("Sparse LU decomposition failed");
    }

    SparseLUDecomposition<Scalar, Eigen::ColMajor> result;
    result.L = lu.matrixL();
    result.U = lu.matrixU();
    result.P = lu.permutationP();
    result.Q = lu.permutationQ();

    return result;
}

template <typename Scalar, int Options>
struct SparseLLTDecomposition {
    Eigen::SparseMatrix<Scalar, Options> L;
};

template <typename Scalar>
SparseLLTDecomposition<Scalar, Eigen::ColMajor> sparse_cholesky_decomposition(
    const Eigen::SparseMatrix<Scalar, Eigen::ColMajor>& A) {

    if (A.rows() != A.cols()) {
        throw std::invalid_argument("Matrix must be square for sparse Cholesky decomposition");
    }

    Eigen::SimplicialLLT<Eigen::SparseMatrix<Scalar, Eigen::ColMajor>> llt;
    llt.analyzePattern(A);
    llt.factorize(A);

    if (llt.info() != Eigen::Success) {
        throw std::runtime_error("Matrix is not positive definite for sparse Cholesky decomposition");
    }

    SparseLLTDecomposition<Scalar, Eigen::ColMajor> result;
    result.L = llt.matrixL();

    return result;
}

template <typename Scalar>
struct SparseLDLTDecomposition {
    Eigen::SparseMatrix<Scalar, Eigen::ColMajor> L;
    Eigen::DiagonalMatrix<Scalar, Eigen::Dynamic> D;
    Eigen::PermutationMatrix<Eigen::Dynamic, Eigen::Dynamic> P;
};

template <typename Scalar>
SparseLDLTDecomposition<Scalar> sparse_ldlt_decomposition(
    const Eigen::SparseMatrix<Scalar, Eigen::ColMajor>& A) {

    if (A.rows() != A.cols()) {
        throw std::invalid_argument("Matrix must be square for sparse LDLT decomposition");
    }

    Eigen::SimplicialLDLT<Eigen::SparseMatrix<Scalar, Eigen::ColMajor>> ldlt;
    ldlt.analyzePattern(A);
    ldlt.factorize(A);

    if (ldlt.info() != Eigen::Success) {
        throw std::runtime_error("Sparse LDLT decomposition failed");
    }

    SparseLDLTDecomposition<Scalar> result;
    result.L = ldlt.matrixL();
    result.D = ldlt.vectorD().asDiagonal();
    result.P = ldlt.permutationP();

    return result;
}

template <typename Scalar>
struct SparseQRDecomposition {
    Eigen::SparseMatrix<Scalar, Eigen::ColMajor> R;
    Eigen::PermutationMatrix<Eigen::Dynamic, Eigen::Dynamic> P;
    int rank;
};

template <typename Scalar>
SparseQRDecomposition<Scalar> sparse_qr_decomposition(
    const Eigen::SparseMatrix<Scalar, Eigen::ColMajor>& A) {

    Eigen::SparseQR<Eigen::SparseMatrix<Scalar, Eigen::ColMajor>,
                    Eigen::COLAMDOrdering<int>> qr;
    qr.analyzePattern(A);
    qr.factorize(A);

    if (qr.info() != Eigen::Success) {
        throw std::runtime_error("Sparse QR decomposition failed");
    }

    SparseQRDecomposition<Scalar> result;
    result.R = qr.matrixR();
    result.P = qr.colsPermutation();
    result.rank = qr.rank();

    return result;
}

} 

#endif
