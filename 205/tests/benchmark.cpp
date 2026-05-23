#include <chrono>
#include <iomanip>
#include <iostream>
#include <vector>
#include <string>

#include "matrix/Matrix.h"
#include "matrix/Multiply.h"

#ifdef _OPENMP
#include <omp.h>
#endif

using namespace matrix;
using namespace matrix::multiply;

template <typename T>
struct BenchmarkResult {
    std::string precision;
    std::size_t size;
    double naive_time;
    double blocked_time;
    double strassen_time;
    double auto_time;
    std::string auto_algo;
};

template <typename T>
double measure_time(const Matrix<T>& A, const Matrix<T>& B,
                    Algorithm algo, std::size_t iterations = 3) {
    double total_time = 0.0;
    for (std::size_t i = 0; i < iterations; ++i) {
        auto start = std::chrono::high_resolution_clock::now();
        Matrix<T> C = multiply(A, B, algo);
        auto end = std::chrono::high_resolution_clock::now();
        std::chrono::duration<double, std::milli> duration = end - start;
        total_time += duration.count();
    }
    return total_time / iterations;
}

template <typename T>
double calculate_gflops(std::size_t N, double time_ms) {
    if (time_ms <= 0) return 0.0;
    double operations = 2.0 * static_cast<double>(N) * N * N;
    double time_seconds = time_ms / 1000.0;
    return operations / time_seconds / 1e9;
}

std::string get_precision_name(float) { return "float"; }
std::string get_precision_name(double) { return "double"; }

std::string get_auto_algo_name(std::size_t N) {
    if (N < 64) {
        return "Naive";
    } else if (N < 512) {
        return "Blocked";
    } else {
        return "Strassen";
    }
}

template <typename T>
BenchmarkResult<T> run_benchmark(std::size_t N, std::size_t iterations = 3) {
    Matrix<T> A = Matrix<T>::random(N, N, T{0}, T{1});
    Matrix<T> B = Matrix<T>::random(N, N, T{0}, T{1});

    BenchmarkResult<T> result;
    result.precision = get_precision_name(T{});
    result.size = N;

    std::cout << "  Testing " << result.precision << " " << N << "x" << N << "..." << std::endl;

    std::size_t naive_iter = (N < 128) ? iterations * 10 : iterations;
    result.naive_time = measure_time(A, B, Algorithm::Naive, naive_iter);

    result.blocked_time = measure_time(A, B, Algorithm::Blocked, iterations);
    result.strassen_time = measure_time(A, B, Algorithm::Strassen, iterations);

    {
        auto start = std::chrono::high_resolution_clock::now();
        Matrix<T> C = multiply(A, B, Algorithm::Auto);
        auto end = std::chrono::high_resolution_clock::now();
        std::chrono::duration<double, std::milli> duration = end - start;
        result.auto_time = duration.count();
        result.auto_algo = get_auto_algo_name(N);
    }

    return result;
}

template <typename T>
void verify_correctness() {
    std::cout << "\n=== Verifying Correctness ===" << std::endl;

    const std::size_t N = 128;
    Matrix<T> A = Matrix<T>::random(N, N, T{0}, T{1});
    Matrix<T> B = Matrix<T>::random(N, N, T{0}, T{1});

    Matrix<T> C_naive = multiply(A, B, Algorithm::Naive);
    Matrix<T> C_blocked = multiply(A, B, Algorithm::Blocked);
    Matrix<T> C_strassen = multiply(A, B, Algorithm::Strassen);
    Matrix<T> C_auto = multiply(A, B, Algorithm::Auto);

    std::cout << "  Precision: " << get_precision_name(T{}) << std::endl;
    std::cout << "  Blocked matches Naive: " << (C_naive.isApprox(C_blocked, T{1e-4}) ? "YES" : "NO") << std::endl;
    std::cout << "  Strassen matches Naive: " << (C_naive.isApprox(C_strassen, T{1e-3}) ? "YES" : "NO") << std::endl;
    std::cout << "  Auto matches Naive: " << (C_naive.isApprox(C_auto, T{1e-3}) ? "YES" : "NO") << std::endl;
}

void print_separator(int total_width = 100) {
    std::cout << std::string(total_width, '-') << std::endl;
}

template <typename T>
void print_results_table(const std::vector<BenchmarkResult<T>>& results) {
    if (results.empty()) return;

    std::cout << "\n=== " << results[0].precision << " Performance Results ===" << std::endl;

    const int col_width = 14;
    print_separator(7 * col_width + 8);

    std::cout << std::left << std::setw(col_width) << "Size"
              << std::left << std::setw(col_width) << "Naive (ms)"
              << std::left << std::setw(col_width) << "Blocked (ms)"
              << std::left << std::setw(col_width) << "Strassen (ms)"
              << std::left << std::setw(col_width) << "Auto (ms)"
              << std::left << std::setw(col_width) << "Auto Algo"
              << std::left << std::setw(col_width) << "Speedup" << std::endl;

    print_separator(7 * col_width + 8);

    for (const auto& r : results) {
        double blocked_speedup = 1.0;
        if (r.naive_time > 0) {
            blocked_speedup = r.naive_time / r.blocked_time;
        }

        std::cout << std::left << std::setw(col_width) << (std::to_string(r.size) + "x" + std::to_string(r.size))
                  << std::left << std::setw(col_width);
        if (r.naive_time > 0) {
            std::cout << std::fixed << std::setprecision(2) << r.naive_time;
        } else {
            std::cout << "N/A";
        }
        std::cout << std::left << std::setw(col_width) << std::fixed << std::setprecision(2) << r.blocked_time
                  << std::left << std::setw(col_width) << std::fixed << std::setprecision(2) << r.strassen_time
                  << std::left << std::setw(col_width) << std::fixed << std::setprecision(2) << r.auto_time
                  << std::left << std::setw(col_width) << r.auto_algo
                  << std::left << std::setw(col_width) << std::fixed << std::setprecision(2) << blocked_speedup << "x" << std::endl;
    }
    print_separator(7 * col_width + 8);
}

template <typename T>
void print_gflops_table(const std::vector<BenchmarkResult<T>>& results) {
    if (results.empty()) return;

    std::cout << "\n=== " << results[0].precision << " GFLOPS Performance ===" << std::endl;

    const int col_width = 14;
    print_separator(5 * col_width + 6);

    std::cout << std::left << std::setw(col_width) << "Size"
              << std::left << std::setw(col_width) << "Naive"
              << std::left << std::setw(col_width) << "Blocked"
              << std::left << std::setw(col_width) << "Strassen"
              << std::left << std::setw(col_width) << "Auto" << std::endl;

    print_separator(5 * col_width + 6);

    for (const auto& r : results) {
        std::cout << std::left << std::setw(col_width) << (std::to_string(r.size) + "x" + std::to_string(r.size))
                  << std::left << std::setw(col_width);
        if (r.naive_time > 0) {
            std::cout << std::fixed << std::setprecision(2) << calculate_gflops(r.size, r.naive_time);
        } else {
            std::cout << "N/A";
        }
        std::cout << std::left << std::setw(col_width) << std::fixed << std::setprecision(2) << calculate_gflops(r.size, r.blocked_time)
                  << std::left << std::setw(col_width) << std::fixed << std::setprecision(2) << calculate_gflops(r.size, r.strassen_time)
                  << std::left << std::setw(col_width) << std::fixed << std::setprecision(2) << calculate_gflops(r.size, r.auto_time) << std::endl;
    }
    print_separator(5 * col_width + 6);
}

int main() {
    std::cout << "========================================" << std::endl;
    std::cout << "  High Performance Matrix Multiplication" << std::endl;
    std::cout << "========================================" << std::endl;

#ifdef _OPENMP
    std::cout << "\nOpenMP enabled with " << omp_get_max_threads() << " threads" << std::endl;
#else
    std::cout << "\nOpenMP disabled" << std::endl;
#endif

    verify_correctness<float>();
    verify_correctness<double>();

    std::vector<std::size_t> sizes = {16, 32, 64, 128, 256, 512, 1024};
    std::size_t iterations = 3;

    std::cout << "\n=== Running Benchmarks ===" << std::endl;

    std::vector<BenchmarkResult<float>> float_results;
    std::vector<BenchmarkResult<double>> double_results;

    for (std::size_t N : sizes) {
        float_results.push_back(run_benchmark<float>(N, iterations));
    }

    for (std::size_t N : sizes) {
        double_results.push_back(run_benchmark<double>(N, iterations));
    }

    print_results_table(float_results);
    print_gflops_table(float_results);

    print_results_table(double_results);
    print_gflops_table(double_results);

    std::cout << "\n=== Benchmark Complete ===" << std::endl;

    return 0;
}
