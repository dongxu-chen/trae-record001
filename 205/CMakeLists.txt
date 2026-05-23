cmake_minimum_required(VERSION 3.18)
project(HighPerformanceMatrixMul VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

option(USE_OPENMP "Enable OpenMP parallelization" ON)
option(USE_CUDA "Enable CUDA GPU acceleration" OFF)
option(BUILD_PYTHON_BINDINGS "Build Python bindings with pybind11" OFF)
option(BUILD_TESTS "Build test programs" ON)

if(USE_CUDA)
    enable_language(CUDA)
    find_package(CUDA REQUIRED)
    set(CMAKE_CUDA_STANDARD 17)
    set(CMAKE_CUDA_STANDARD_REQUIRED ON)
endif()

if(USE_OPENMP)
    find_package(OpenMP REQUIRED)
endif()

add_library(matrix_mul INTERFACE)
target_include_directories(matrix_mul INTERFACE ${CMAKE_CURRENT_SOURCE_DIR}/include)

if(USE_OPENMP AND OpenMP_CXX_FOUND)
    target_link_libraries(matrix_mul INTERFACE OpenMP::OpenMP_CXX)
endif()

if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    target_compile_options(matrix_mul INTERFACE -O3 -march=native -ffast-math)
elseif(MSVC)
    target_compile_options(matrix_mul INTERFACE /O2 /arch:AVX2 /fp:fast)
endif()

if(USE_CUDA)
    add_library(matrix_mul_gpu STATIC src/GpuMultiply.cu)
    target_include_directories(matrix_mul_gpu PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
    set_target_properties(matrix_mul_gpu PROPERTIES CUDA_SEPARABLE_COMPILATION ON)
    target_compile_options(matrix_mul_gpu PRIVATE $<$<COMPILE_LANGUAGE:CUDA>:-O3;-arch=sm_61>)
    target_compile_definitions(matrix_mul INTERFACE USE_CUDA)
endif()

if(BUILD_TESTS)
    add_executable(benchmark tests/benchmark.cpp)
    target_link_libraries(benchmark PRIVATE matrix_mul)
    if(USE_CUDA)
        target_link_libraries(benchmark PRIVATE matrix_mul_gpu)
    endif()
endif()

if(BUILD_PYTHON_BINDINGS)
    add_subdirectory(third_party/pybind11)
    
    pybind11_add_module(matrix_mul_python python/matrix_mul_bindings.cpp)
    target_include_directories(matrix_mul_python PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/include)
    target_link_libraries(matrix_mul_python PRIVATE matrix_mul)
    
    if(USE_CUDA)
        target_link_libraries(matrix_mul_python PRIVATE matrix_mul_gpu)
    endif()
    
    set_target_properties(matrix_mul_python PROPERTIES OUTPUT_NAME matrix_mul)
endif()

enable_testing()
