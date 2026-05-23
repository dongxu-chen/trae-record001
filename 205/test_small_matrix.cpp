#include <iostream>
#include <iomanip>
#include "matrix/Matrix.h"
#include "matrix/Multiply.h"

using namespace matrix;
using namespace matrix::multiply;

int main() {
    std::cout << "=== Small Matrix Performance Test ===" << std::endl;
    
    std::cout << "\nTesting dynamic block size calculation:" << std::endl;
    for (std::size_t n : {16, 32, 64, 128, 256, 512, 1024}) {
        std::size_t block = detail::calculate_optimal_block_size(n, n, n);
        std::cout << "  " << std::setw(4) << n << "x" << std::setw(4) << n 
                  << " -> block size: " << block << std::endl;
    }

    std::cout << "\nTesting small matrix multiplication correctness:" << std::endl;
    
    for (std::size_t n : {16, 32, 64}) {
        std::cout << "\n  " << n << "x" << n << ":" << std::endl;
        
        Matrix<float> A = Matrix<float>::random(n, n, 0.0f, 1.0f);
        Matrix<float> B = Matrix<float>::random(n, n, 0.0f, 1.0f);
        
        Matrix<float> C_naive = multiply(A, B, Algorithm::Naive);
        Matrix<float> C_blocked = multiply(A, B, Algorithm::Blocked);
        Matrix<float> C_strassen = multiply(A, B, Algorithm::Strassen);
        Matrix<float> C_auto = multiply(A, B, Algorithm::Auto);
        
        std::cout << "    Blocked vs Naive: " << (C_naive.isApprox(C_blocked, 1e-5f) ? "PASS" : "FAIL") << std::endl;
        std::cout << "    Strassen vs Naive: " << (C_naive.isApprox(C_strassen, 1e-3f) ? "PASS" : "FAIL") << std::endl;
        std::cout << "    Auto vs Naive: " << (C_naive.isApprox(C_auto, 1e-3f) ? "PASS" : "FAIL") << std::endl;
    }

    std::cout << "\n=== Test Complete ===" << std::endl;
    return 0;
}
