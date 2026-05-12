#ifndef SPARSE_SOLVERS_H
#define SPARSE_SOLVERS_H

#include <Eigen/Dense>
#include <Eigen/Sparse>
#include <Eigen/SparseLU>
#include <Eigen/SparseCholesky>
#include <Eigen/SparseQR>
#include <Eigen/IterativeLinearSolvers>
#include <stdexcept>
#include <string>
#include <chrono>

#ifdef EIGEN_USE_MKL_ALL
#include <Eigen/PardisoSupport>
#endif

#ifdef EIGEN_USE_SUPERLU
#include <Eigen/SuperLUSupport>
#endif

namespace matrix_lib {

enum class SparseSolverType {
    SparseLU,
    SparseLLT,
    SparseLDLT,
    SparseQR,
    BiCGSTAB,
    ConjugateGradient,
    LeastSquaresConjugateGradient,
    MINRES,
#ifdef EIGEN_USE_SUPERLU
    SuperLU,
    SuperLU_MT,
#endif
#ifdef EIGEN_USE_MKL_ALL
    PardisoLU,
    PardisoLLT,
    PardisoLDLT,
#endif
};

template <typename Scalar>
struct SparseSolverResult {
    Eigen::Matrix<Scalar, Eigen::Dynamic, 1> solution;
    bool success;
    std::string error_message;
    int iterations;
    Scalar relative_error;
    double elapsed_ms;
};

template <typename Scalar>
SparseSolverResult<Scalar> solve_sparse_system(
    const Eigen::SparseMatrix<Scalar, Eigen::ColMajor>& A,
    const Eigen::Matrix<Scalar, Eigen::Dynamic, 1>& b,
    SparseSolverType solver_type = SparseSolverType::SparseLU,
    Scalar tolerance = static_cast<Scalar>(1e-10),
    int max_iterations = 1000) {

    SparseSolverResult<Scalar> result;
    result.success = false;
    result.iterations = 0;
    result.relative_error = static_cast<Scalar>(0);
    result.elapsed_ms = 0.0;

    if (A.rows() != b.rows()) {
        result.error_message = "Matrix rows must match vector size";
        return result;
    }

#ifdef _OPENMP
    auto start = omp_get_wtime();
#else
    auto start = std::chrono::high_resolution_clock::now();
#endif

    try {
        switch (solver_type) {
            case SparseSolverType::SparseLU: {
                Eigen::SparseLU<Eigen::SparseMatrix<Scalar, Eigen::ColMajor>> solver;
                solver.analyzePattern(A);
                solver.factorize(A);
                if (solver.info() != Eigen::Success) {
                    result.error_message = "SparseLU factorization failed";
                    break;
                }
                result.solution = solver.solve(b);
                result.success = (solver.info() == Eigen::Success);
                result.iterations = 1;
                break;
            }

            case SparseSolverType::SparseLLT: {
                Eigen::SimplicialLLT<Eigen::SparseMatrix<Scalar, Eigen::ColMajor>> solver;
                solver.analyzePattern(A);
                solver.factorize(A);
                if (solver.info() != Eigen::Success) {
                    result.error_message = "SparseLLT factorization failed (matrix may not be positive definite)";
                    break;
                }
                result.solution = solver.solve(b);
                result.success = (solver.info() == Eigen::Success);
                result.iterations = 1;
                break;
            }

            case SparseSolverType::SparseLDLT: {
                Eigen::SimplicialLDLT<Eigen::SparseMatrix<Scalar, Eigen::ColMajor>> solver;
                solver.analyzePattern(A);
                solver.factorize(A);
                if (solver.info() != Eigen::Success) {
                    result.error_message = "SparseLDLT factorization failed";
                    break;
                }
                result.solution = solver.solve(b);
                result.success = (solver.info() == Eigen::Success);
                result.iterations = 1;
                break;
            }

            case SparseSolverType::SparseQR: {
                Eigen::SparseQR<Eigen::SparseMatrix<Scalar, Eigen::ColMajor>,
                                Eigen::COLAMDOrdering<int>> solver;
                solver.analyzePattern(A);
                solver.factorize(A);
                if (solver.info() != Eigen::Success) {
                    result.error_message = "SparseQR factorization failed";
                    break;
                }
                result.solution = solver.solve(b);
                result.success = (solver.info() == Eigen::Success);
                result.iterations = 1;
                break;
            }

            case SparseSolverType::BiCGSTAB: {
                Eigen::BiCGSTAB<Eigen::SparseMatrix<Scalar, Eigen::ColMajor>> solver;
                solver.setTolerance(tolerance);
                solver.setMaxIterations(max_iterations);
                solver.compute(A);
                result.solution = solver.solve(b);
                result.success = solver.info() == Eigen::Success;
                result.iterations = solver.iterations();
                result.relative_error = solver.error();
                if (!result.success) {
                    result.error_message = "BiCGSTAB did not converge";
                }
                break;
            }

            case SparseSolverType::ConjugateGradient: {
                Eigen::ConjugateGradient<Eigen::SparseMatrix<Scalar, Eigen::ColMajor>> solver;
                solver.setTolerance(tolerance);
                solver.setMaxIterations(max_iterations);
                solver.compute(A);
                result.solution = solver.solve(b);
                result.success = solver.info() == Eigen::Success;
                result.iterations = solver.iterations();
                result.relative_error = solver.error();
                if (!result.success) {
                    result.error_message = "ConjugateGradient did not converge";
                }
                break;
            }

            case SparseSolverType::LeastSquaresConjugateGradient: {
                Eigen::LeastSquaresConjugateGradient<Eigen::SparseMatrix<Scalar, Eigen::ColMajor>> solver;
                solver.setTolerance(tolerance);
                solver.setMaxIterations(max_iterations);
                solver.compute(A);
                result.solution = solver.solve(b);
                result.success = solver.info() == Eigen::Success;
                result.iterations = solver.iterations();
                result.relative_error = solver.error();
                if (!result.success) {
                    result.error_message = "LeastSquaresConjugateGradient did not converge";
                }
                break;
            }

            case SparseSolverType::MINRES: {
                Eigen::MINRES<Eigen::SparseMatrix<Scalar, Eigen::ColMajor>> solver;
                solver.setTolerance(tolerance);
                solver.setMaxIterations(max_iterations);
                solver.compute(A);
                result.solution = solver.solve(b);
                result.success = solver.info() == Eigen::Success;
                result.iterations = solver.iterations();
                result.relative_error = solver.error();
                if (!result.success) {
                    result.error_message = "MINRES did not converge";
                }
                break;
            }

#ifdef EIGEN_USE_SUPERLU
            case SparseSolverType::SuperLU: {
                Eigen::SuperLU<Eigen::SparseMatrix<Scalar, Eigen::ColMajor>> solver;
                solver.analyzePattern(A);
                solver.factorize(A);
                if (solver.info() != Eigen::Success) {
                    result.error_message = "SuperLU factorization failed";
                    break;
                }
                result.solution = solver.solve(b);
                result.success = (solver.info() == Eigen::Success);
                result.iterations = 1;
                break;
            }

            case SparseSolverType::SuperLU_MT: {
                Eigen::SuperLUMT<Eigen::SparseMatrix<Scalar, Eigen::ColMajor>> solver;
                solver.analyzePattern(A);
                solver.factorize(A);
                if (solver.info() != Eigen::Success) {
                    result.error_message = "SuperLU_MT factorization failed";
                    break;
                }
                result.solution = solver.solve(b);
                result.success = (solver.info() == Eigen::Success);
                result.iterations = 1;
                break;
            }
#endif

#ifdef EIGEN_USE_MKL_ALL
            case SparseSolverType::PardisoLU: {
                Eigen::PardisoLU<Eigen::SparseMatrix<Scalar, Eigen::ColMajor>> solver;
                solver.analyzePattern(A);
                solver.factorize(A);
                if (solver.info() != Eigen::Success) {
                    result.error_message = "PardisoLU factorization failed";
                    break;
                }
                result.solution = solver.solve(b);
                result.success = (solver.info() == Eigen::Success);
                result.iterations = 1;
                break;
            }

            case SparseSolverType::PardisoLLT: {
                Eigen::PardisoLLT<Eigen::SparseMatrix<Scalar, Eigen::ColMajor>> solver;
                solver.analyzePattern(A);
                solver.factorize(A);
                if (solver.info() != Eigen::Success) {
                    result.error_message = "PardisoLLT factorization failed";
                    break;
                }
                result.solution = solver.solve(b);
                result.success = (solver.info() == Eigen::Success);
                result.iterations = 1;
                break;
            }

            case SparseSolverType::PardisoLDLT: {
                Eigen::PardisoLDLT<Eigen::SparseMatrix<Scalar, Eigen::ColMajor>> solver;
                solver.analyzePattern(A);
                solver.factorize(A);
                if (solver.info() != Eigen::Success) {
                    result.error_message = "PardisoLDLT factorization failed";
                    break;
                }
                result.solution = solver.solve(b);
                result.success = (solver.info() == Eigen::Success);
                result.iterations = 1;
                break;
            }
#endif

            default:
                result.error_message = "Unknown solver type";
        }
    } catch (const std::exception& e) {
        result.error_message = std::string("Exception: ") + e.what();
        result.success = false;
    }

#ifdef _OPENMP
    auto end = omp_get_wtime();
    result.elapsed_ms = (end - start) * 1000.0;
#else
    auto end = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::microseconds>(end - start);
    result.elapsed_ms = duration.count() / 1000.0;
#endif

    return result;
}

template <typename Scalar>
SparseSolverResult<Scalar> solve_sparse_system_matrix(
    const Eigen::SparseMatrix<Scalar, Eigen::ColMajor>& A,
    const Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic>& B,
    SparseSolverType solver_type = SparseSolverType::SparseLU) {

    SparseSolverResult<Scalar> result;
    result.success = false;
    result.iterations = 0;
    result.relative_error = static_cast<Scalar>(0);
    result.elapsed_ms = 0.0;

    if (A.rows() != B.rows()) {
        result.error_message = "Matrix rows must match right-hand side matrix rows";
        return result;
    }

#ifdef _OPENMP
    auto start = omp_get_wtime();
#else
    auto start = std::chrono::high_resolution_clock::now();
#endif

    try {
        switch (solver_type) {
            case SparseSolverType::SparseLU: {
                Eigen::SparseLU<Eigen::SparseMatrix<Scalar, Eigen::ColMajor>> solver;
                solver.analyzePattern(A);
                solver.factorize(A);
                if (solver.info() != Eigen::Success) {
                    result.error_message = "SparseLU factorization failed";
                    break;
                }
                Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic> X = solver.solve(B);
                result.solution = X.reshaped();
                result.success = (solver.info() == Eigen::Success);
                result.iterations = 1;
                break;
            }

            case SparseSolverType::SparseLLT: {
                Eigen::SimplicialLLT<Eigen::SparseMatrix<Scalar, Eigen::ColMajor>> solver;
                solver.analyzePattern(A);
                solver.factorize(A);
                if (solver.info() != Eigen::Success) {
                    result.error_message = "SparseLLT factorization failed";
                    break;
                }
                Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic> X = solver.solve(B);
                result.solution = X.reshaped();
                result.success = (solver.info() == Eigen::Success);
                result.iterations = 1;
                break;
            }

            case SparseSolverType::SparseLDLT: {
                Eigen::SimplicialLDLT<Eigen::SparseMatrix<Scalar, Eigen::ColMajor>> solver;
                solver.analyzePattern(A);
                solver.factorize(A);
                if (solver.info() != Eigen::Success) {
                    result.error_message = "SparseLDLT factorization failed";
                    break;
                }
                Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic> X = solver.solve(B);
                result.solution = X.reshaped();
                result.success = (solver.info() == Eigen::Success);
                result.iterations = 1;
                break;
            }

            case SparseSolverType::SparseQR: {
                Eigen::SparseQR<Eigen::SparseMatrix<Scalar, Eigen::ColMajor>,
                                Eigen::COLAMDOrdering<int>> solver;
                solver.analyzePattern(A);
                solver.factorize(A);
                if (solver.info() != Eigen::Success) {
                    result.error_message = "SparseQR factorization failed";
                    break;
                }
                Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic> X = solver.solve(B);
                result.solution = X.reshaped();
                result.success = (solver.info() == Eigen::Success);
                result.iterations = 1;
                break;
            }

#ifdef EIGEN_USE_SUPERLU
            case SparseSolverType::SuperLU: {
                Eigen::SuperLU<Eigen::SparseMatrix<Scalar, Eigen::ColMajor>> solver;
                solver.analyzePattern(A);
                solver.factorize(A);
                if (solver.info() != Eigen::Success) {
                    result.error_message = "SuperLU factorization failed";
                    break;
                }
                Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic> X = solver.solve(B);
                result.solution = X.reshaped();
                result.success = (solver.info() == Eigen::Success);
                result.iterations = 1;
                break;
            }

            case SparseSolverType::SuperLU_MT: {
                Eigen::SuperLUMT<Eigen::SparseMatrix<Scalar, Eigen::ColMajor>> solver;
                solver.analyzePattern(A);
                solver.factorize(A);
                if (solver.info() != Eigen::Success) {
                    result.error_message = "SuperLU_MT factorization failed";
                    break;
                }
                Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic> X = solver.solve(B);
                result.solution = X.reshaped();
                result.success = (solver.info() == Eigen::Success);
                result.iterations = 1;
                break;
            }
#endif

#ifdef EIGEN_USE_MKL_ALL
            case SparseSolverType::PardisoLU: {
                Eigen::PardisoLU<Eigen::SparseMatrix<Scalar, Eigen::ColMajor>> solver;
                solver.analyzePattern(A);
                solver.factorize(A);
                if (solver.info() != Eigen::Success) {
                    result.error_message = "PardisoLU factorization failed";
                    break;
                }
                Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic> X = solver.solve(B);
                result.solution = X.reshaped();
                result.success = (solver.info() == Eigen::Success);
                result.iterations = 1;
                break;
            }
#endif

            default:
                result.error_message = "This solver type does not support matrix RHS";
        }
    } catch (const std::exception& e) {
        result.error_message = std::string("Exception: ") + e.what();
        result.success = false;
    }

#ifdef _OPENMP
    auto end = omp_get_wtime();
    result.elapsed_ms = (end - start) * 1000.0;
#else
    auto end = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::microseconds>(end - start);
    result.elapsed_ms = duration.count() / 1000.0;
#endif

    return result;
}

} 

#endif
