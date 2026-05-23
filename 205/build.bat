@echo off
echo Building High Performance Matrix Multiplication Library...

if not exist build mkdir build
cd build

where g++ >nul 2>nul
if %errorlevel% equ 0 (
    echo Using MinGW g++...
    g++ -std=c++17 -O3 -march=native -ffast-math -fopenmp -I../include ../tests/benchmark.cpp -o benchmark.exe
    if %errorlevel% equ 0 (
        echo Build successful!
        echo Running benchmark...
        benchmark.exe
    ) else (
        echo Build failed with g++
    )
) else (
    where cl >nul 2>nul
    if %errorlevel% equ 0 (
        echo Using MSVC cl...
        cl /std:c++17 /O2 /arch:AVX2 /fp:fast /openmp /I../include ../tests/benchmark.cpp /Febenchmark.exe
        if %errorlevel% equ 0 (
            echo Build successful!
            echo Running benchmark...
            benchmark.exe
        ) else (
            echo Build failed with MSVC
        )
    ) else (
        echo No C++ compiler found. Please install MinGW or Visual Studio.
    )
)

cd ..
pause
