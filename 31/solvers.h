#ifndef SOLVERS_H
#define SOLVERS_H

#include <Eigen/Dense>
#include <stdexcept>

namespace matrix_lib {

enum class SolverMethod {
    LU,
    QR,
    ColPivHouseholderQR,
    FullPivLU,
    JacobiSVD,
    LDLT,
    LLT
};

template <typename Scalar>
Eigen::Matrix<Scalar, Eigen::Dynamic, 1> solve_linear_system(
    const Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic>& A,
    const Eigen::Matrix<Scalar, Eigen::Dynamic, 1>& b,
    SolverMethod method = SolverMethod::ColPivHouseholderQR) {

    if (A.rows() != b.rows()) {
        throw std::invalid_argument("Matrix rows must match vector size");
    }

    Eigen::Matrix<Scalar, Eigen::Dynamic, 1> x;

    switch (method) {
        case SolverMethod::LU: {
            Eigen::PartialPivLU<Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic>> lu(A);
            x = lu.solve(b);
            break;
        }
        case SolverMethod::QR: {
            Eigen::HouseholderQR<Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic>> qr(A);
            x = qr.solve(b);
            break;
        }
        case SolverMethod::ColPivHouseholderQR: {
            Eigen::ColPivHouseholderQR<Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic>> cqr(A);
            x = cqr.solve(b);
            break;
        }
        case SolverMethod::FullPivLU: {
            Eigen::FullPivLU<Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic>> flu(A);
            x = flu.solve(b);
            break;
        }
        case SolverMethod::JacobiSVD: {
            Eigen::JacobiSVD<Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic>> svd(
                A, Eigen::ComputeThinU | Eigen::ComputeThinV);
            x = svd.solve(b);
            break;
        }
        case SolverMethod::LDLT: {
            Eigen::LDLT<Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic>> ldlt(A);
            x = ldlt.solve(b);
            break;
        }
        case SolverMethod::LLT: {
            Eigen::LLT<Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic>> llt(A);
            x = llt.solve(b);
            break;
        }
        default:
            throw std::invalid_argument("Unknown solver method");
    }

    return x;
}

template <typename Scalar>
Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic> solve_linear_system_matrix(
    const Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic>& A,
    const Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic>& B,
    SolverMethod method = SolverMethod::ColPivHouseholderQR) {

    if (A.rows() != B.rows()) {
        throw std::invalid_argument("Matrix rows must match right-hand side matrix rows");
    }

    Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic> X;

    switch (method) {
        case SolverMethod::LU: {
            Eigen::PartialPivLU<Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic>> lu(A);
            X = lu.solve(B);
            break;
        }
        case SolverMethod::QR: {
            Eigen::HouseholderQR<Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic>> qr(A);
            X = qr.solve(B);
            break;
        }
        case SolverMethod::ColPivHouseholderQR: {
            Eigen::ColPivHouseholderQR<Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic>> cqr(A);
            X = cqr.solve(B);
            break;
        }
        case SolverMethod::FullPivLU: {
            Eigen::FullPivLU<Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic>> flu(A);
            X = flu.solve(B);
            break;
        }
        case SolverMethod::JacobiSVD: {
            Eigen::JacobiSVD<Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic>> svd(
                A, Eigen::ComputeThinU | Eigen::ComputeThinV);
            X = svd.solve(B);
            break;
        }
        case SolverMethod::LDLT: {
            Eigen::LDLT<Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic>> ldlt(A);
            X = ldlt.solve(B);
            break;
        }
        case SolverMethod::LLT: {
            Eigen::LLT<Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic>> llt(A);
            X = llt.solve(B);
            break;
        }
        default:
            throw std::invalid_argument("Unknown solver method");
    }

    return X;
}

} 

#endif
