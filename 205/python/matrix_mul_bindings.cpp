#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include <pybind11/stl.h>
#include <string>
#include <stdexcept>

#include "matrix/Matrix.h"
#include "matrix/Multiply.h"
#include "matrix/SparseMatrix.h"
#include "matrix/MatrixMulExt.h"
#include "matrix/GpuMultiply.h"

namespace py = pybind11;
using namespace matrix;
using namespace matrix::multiply;

template <typename T>
Matrix<T> numpy_to_matrix(py::array_t<T, py::array::c_style> array) {
    auto buf = array.request();
    if (buf.ndim != 2) {
        throw std::runtime_error("Number of dimensions must be 2");
    }

    std::size_t rows = static_cast<std::size_t>(buf.shape[0]);
    std::size_t cols = static_cast<std::size_t>(buf.shape[1]);

    Matrix<T> mat(rows, cols);
    T* ptr = static_cast<T*>(buf.ptr);
    std::copy(ptr, ptr + rows * cols, mat.vector().begin());
    return mat;
}

template <typename T>
py::array_t<T> matrix_to_numpy(const Matrix<T>& mat) {
    std::vector<std::size_t> shape = {mat.rows(), mat.cols()};
    std::vector<std::size_t> strides = {mat.cols() * sizeof(T), sizeof(T)};
    
    auto result = py::array_t<T>(shape, strides);
    auto buf = result.request();
    T* ptr = static_cast<T*>(buf.ptr);
    std::copy(mat.vector().begin(), mat.vector().end(), ptr);
    return result;
}

py::object multiply_numpy(py::object A_obj, py::object B_obj,
                          const std::string& dtype = "auto",
                          const std::string& algorithm = "auto",
                          const std::string& device = "auto",
                          double sparsity_threshold = 0.9) {
    
    bool is_float32 = false;
    bool is_float64 = false;

    if (py::isinstance<py::array_t<float>>(A_obj) && py::isinstance<py::array_t<float>>(B_obj)) {
        is_float32 = true;
    } else if (py::isinstance<py::array_t<double>>(A_obj) && py::isinstance<py::array_t<double>>(B_obj)) {
        is_float64 = true;
    } else {
        throw std::runtime_error("Input arrays must be both float32 or both float64");
    }

    ExecutionConfig<float> config_f;
    ExecutionConfig<double> config_d;
    
    if (algorithm == "naive") {
        config_f.algorithm = Algorithm::Naive;
        config_d.algorithm = Algorithm::Naive;
    } else if (algorithm == "blocked") {
        config_f.algorithm = Algorithm::Blocked;
        config_d.algorithm = Algorithm::Blocked;
    } else if (algorithm == "strassen") {
        config_f.algorithm = Algorithm::Strassen;
        config_d.algorithm = Algorithm::Strassen;
    } else {
        config_f.algorithm = Algorithm::Auto;
        config_d.algorithm = Algorithm::Auto;
    }

    if (device == "cpu") {
        config_f.device = Device::CPU;
        config_d.device = Device::CPU;
    } else if (device == "gpu") {
        config_f.device = Device::GPU;
        config_d.device = Device::GPU;
    } else {
        config_f.device = Device::Auto;
        config_d.device = Device::Auto;
    }

    config_f.sparsity_threshold = sparsity_threshold;
    config_d.sparsity_threshold = sparsity_threshold;

    if (is_float32) {
        auto A = numpy_to_matrix(A_obj.cast<py::array_t<float>>());
        auto B = numpy_to_matrix(B_obj.cast<py::array_t<float>>());
        auto C = multiply_auto(A, B, config_f);
        return py::cast(matrix_to_numpy(C));
    } else {
        auto A = numpy_to_matrix(A_obj.cast<py::array_t<double>>());
        auto B = numpy_to_matrix(B_obj.cast<py::array_t<double>>());
        auto C = multiply_auto(A, B, config_d);
        return py::cast(matrix_to_numpy(C));
    }
}

template <typename T>
py::dict get_matrix_info(const Matrix<T>& mat) {
    py::dict info;
    info["rows"] = mat.rows();
    info["cols"] = mat.cols();
    info["sparsity"] = SparseMatrixCSR<T>::calculate_sparsity(mat);
    info["nnz"] = static_cast<std::size_t>(mat.rows() * mat.cols() * 
                              (1.0 - SparseMatrixCSR<T>::calculate_sparsity(mat)));
    return info;
}

std::string get_gpu_info() {
    if (gpu::is_cuda_available()) {
        return gpu::get_cuda_version();
    }
    return "No GPU available";
}

bool has_gpu_support() {
    return gpu::is_cuda_available();
}

PYBIND11_MODULE(matrix_mul, m) {
    m.doc() = "High Performance Matrix Multiplication Library";

    m.def("multiply", &multiply_numpy,
          py::arg("A"), py::arg("B"),
          py::arg("dtype") = "auto",
          py::arg("algorithm") = "auto",
          py::arg("device") = "auto",
          py::arg("sparsity_threshold") = 0.9,
          "Matrix multiplication with automatic algorithm and device selection\n\n"
          "Args:\n"
          "    A: First matrix (numpy array, float32 or float64)\n"
          "    B: Second matrix (numpy array, float32 or float64)\n"
          "    algorithm: 'auto', 'naive', 'blocked', or 'strassen'\n"
          "    device: 'auto', 'cpu', or 'gpu'\n"
          "    sparsity_threshold: Sparsity level to switch to sparse algorithm (default: 0.9)\n"
          "\n"
          "Returns:\n"
          "    Result matrix as numpy array\n");

    m.def("has_gpu", &has_gpu_support, "Check if GPU (CUDA) is available");
    m.def("gpu_info", &get_gpu_info, "Get GPU information");

    m.def("estimate_sparsity", [](py::array_t<float> arr) -> double {
        auto mat = numpy_to_matrix(arr);
        return SparseMatrixCSR<float>::calculate_sparsity(mat);
    }, "Estimate matrix sparsity");

    m.def("get_matrix_info", [](py::array_t<float> arr) -> py::dict {
        auto mat = numpy_to_matrix(arr);
        return get_matrix_info(mat);
    }, "Get matrix information including sparsity");

    py::enum_<Algorithm>(m, "Algorithm")
        .value("Naive", Algorithm::Naive)
        .value("Blocked", Algorithm::Blocked)
        .value("Strassen", Algorithm::Strassen)
        .value("Auto", Algorithm::Auto);

    py::enum_<Device>(m, "Device")
        .value("CPU", Device::CPU)
        .value("GPU", Device::GPU)
        .value("Auto", Device::Auto);

    m.attr("__version__") = "1.0.0";
}
