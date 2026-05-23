#ifndef MATRIX_MATRIX_H
#define MATRIX_MATRIX_H

#include <vector>
#include <cstddef>
#include <cassert>
#include <random>
#include <iomanip>
#include <ostream>
#include <algorithm>

namespace matrix {

template <typename T>
class Matrix {
public:
    using value_type = T;
    using size_type = std::size_t;

    Matrix() : rows_(0), cols_(0) {}

    Matrix(size_type rows, size_type cols)
        : rows_(rows), cols_(cols), data_(rows * cols, T{}) {}

    Matrix(size_type rows, size_type cols, const T& value)
        : rows_(rows), cols_(cols), data_(rows * cols, value) {}

    Matrix(const Matrix&) = default;
    Matrix(Matrix&&) noexcept = default;
    Matrix& operator=(const Matrix&) = default;
    Matrix& operator=(Matrix&&) noexcept = default;

    static Matrix zero(size_type rows, size_type cols) {
        return Matrix(rows, cols, T{0});
    }

    static Matrix ones(size_type rows, size_type cols) {
        return Matrix(rows, cols, T{1});
    }

    static Matrix identity(size_type n) {
        Matrix mat(n, n, T{0});
        for (size_type i = 0; i < n; ++i) {
            mat(i, i) = T{1};
        }
        return mat;
    }

    static Matrix random(size_type rows, size_type cols, T min = T{-1}, T max = T{1}, unsigned int seed = 42) {
        Matrix mat(rows, cols);
        std::mt19937 gen(seed);
        std::uniform_real_distribution<T> dist(min, max);
        for (auto& val : mat.data_) {
            val = dist(gen);
        }
        return mat;
    }

    size_type rows() const noexcept { return rows_; }
    size_type cols() const noexcept { return cols_; }
    size_type size() const noexcept { return data_.size(); }

    T& operator()(size_type row, size_type col) {
        assert(row < rows_ && col < cols_);
        return data_[row * cols_ + col];
    }

    const T& operator()(size_type row, size_type col) const {
        assert(row < rows_ && col < cols_);
        return data_[row * cols_ + col];
    }

    T* data() noexcept { return data_.data(); }
    const T* data() const noexcept { return data_.data(); }

    std::vector<T>& vector() noexcept { return data_; }
    const std::vector<T>& vector() const noexcept { return data_; }

    bool operator==(const Matrix& other) const {
        if (rows_ != other.rows_ || cols_ != other.cols_) return false;
        return data_ == other.data_;
    }

    bool isApprox(const Matrix& other, T epsilon = T{1e-5}) const {
        if (rows_ != other.rows_ || cols_ != other.cols_) return false;
        for (size_type i = 0; i < data_.size(); ++i) {
            if (std::abs(data_[i] - other.data_[i]) > epsilon) {
                return false;
            }
        }
        return true;
    }

    Matrix transpose() const {
        Matrix result(cols_, rows_);
        for (size_type i = 0; i < rows_; ++i) {
            for (size_type j = 0; j < cols_; ++j) {
                result(j, i) = (*this)(i, j);
            }
        }
        return result;
    }

    Matrix& operator+=(const Matrix& other) {
        assert(rows_ == other.rows_ && cols_ == other.cols_);
        for (size_type i = 0; i < data_.size(); ++i) {
            data_[i] += other.data_[i];
        }
        return *this;
    }

    Matrix& operator-=(const Matrix& other) {
        assert(rows_ == other.rows_ && cols_ == other.cols_);
        for (size_type i = 0; i < data_.size(); ++i) {
            data_[i] -= other.data_[i];
        }
        return *this;
    }

    Matrix operator+(const Matrix& other) const {
        Matrix result = *this;
        result += other;
        return result;
    }

    Matrix operator-(const Matrix& other) const {
        Matrix result = *this;
        result -= other;
        return result;
    }

    Matrix submatrix(size_type row_start, size_type col_start, size_type row_end, size_type col_end) const {
        assert(row_end <= rows_ && col_end <= cols_);
        assert(row_start <= row_end && col_start <= col_end);
        size_type new_rows = row_end - row_start;
        size_type new_cols = col_end - col_start;
        Matrix result(new_rows, new_cols);
        for (size_type i = 0; i < new_rows; ++i) {
            for (size_type j = 0; j < new_cols; ++j) {
                result(i, j) = (*this)(row_start + i, col_start + j);
            }
        }
        return result;
    }

    void set_submatrix(size_type row_start, size_type col_start, const Matrix& sub) {
        assert(row_start + sub.rows_ <= rows_ && col_start + sub.cols_ <= cols_);
        for (size_type i = 0; i < sub.rows_; ++i) {
            for (size_type j = 0; j < sub.cols_; ++j) {
                (*this)(row_start + i, col_start + j) = sub(i, j);
            }
        }
    }

private:
    size_type rows_;
    size_type cols_;
    std::vector<T> data_;
};

template <typename T>
std::ostream& operator<<(std::ostream& os, const Matrix<T>& mat) {
    for (std::size_t i = 0; i < mat.rows(); ++i) {
        for (std::size_t j = 0; j < mat.cols(); ++j) {
            os << std::setw(10) << std::setprecision(4) << mat(i, j) << " ";
        }
        os << "\n";
    }
    return os;
}

} // namespace matrix

#endif // MATRIX_MATRIX_H
