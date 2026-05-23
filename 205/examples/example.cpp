#include <iostream>
#include "matrix/Matrix.h"
#include "matrix/Multiply.h"

using namespace matrix;
using namespace matrix::multiply;

int main() {
    std::cout << "=== Matrix Multiplication Examples ===" << std::endl;

    const std::size_t N = 256;

    std::cout << "\n1. Creating random matrices..." << std::endl;
    Matrix<float> A = Matrix<float>::random(N, N);
    Matrix<float> B = Matrix<float>::random(N, N);

    std::cout << "   Matrix A: " << A.rows() << "x" << A.cols() << std::endl;
    std::cout << "   Matrix B: " << B.rows() << "x" << B.cols() << std::endl;

    std::cout << "\n2. Using different algorithms:" << std::endl;

    std::cout << "   Naive algorithm...   ";
    Matrix<float> C_naive = multiply(A, B, Algorithm::Naive);
    std::cout << "Done" << std::endl;

    std::cout << "   Blocked algorithm (block=64)...   ";
    Matrix<float> C_blocked = multiply(A, B, Algorithm::Blocked, 64);
    std::cout << "Done" << std::endl;

    std::cout << "   Strassen algorithm (threshold=128)...   ";
    Matrix<float> C_strassen = multiply(A, B, Algorithm::Strassen, 0, 128);
    std::cout << "Done" << std::endl;

    std::cout << "   Auto algorithm...   ";
    Matrix<float> C_auto = multiply(A, B);
    std::cout << "Done" << std::endl;

    std::cout << "\n3. Verifying correctness..." << std::endl;
    std::cout << "   Blocked matches Naive: " << (C_naive.isApprox(C_blocked) ? "YES" : "NO") << std::endl;
    std::cout << "   Strassen matches Naive: " << (C_naive.isApprox(C_strassen, 1e-3f) ? "YES" : "NO") << std::endl;

    std::cout << "\n4. Double precision example:" << std::endl;
    Matrix<double> D = Matrix<double>::random(128, 128);
    Matrix<double> E = Matrix<double>::random(128, 128);
    Matrix<double> F = multiply(D, E);
    std::cout << "   Double precision result: " << F.rows() << "x" << F.cols() << std::endl;

    std::cout << "\n=== All examples completed ===" << std::endl;
    return 0;
}
