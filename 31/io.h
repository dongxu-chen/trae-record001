#ifndef IO_H
#define IO_H

#include <Eigen/Dense>
#include <fstream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
#include <cctype>

namespace matrix_lib {

namespace {

std::string trim(const std::string& s) {
    size_t start = 0;
    while (start < s.size() && std::isspace(static_cast<unsigned char>(s[start]))) {
        ++start;
    }
    size_t end = s.size();
    while (end > start && std::isspace(static_cast<unsigned char>(s[end - 1]))) {
        --end;
    }
    return s.substr(start, end - start);
}

std::vector<std::string> split_csv_line(const std::string& line, char delimiter = ',') {
    std::vector<std::string> tokens;
    std::string current;
    bool in_quotes = false;

    for (size_t i = 0; i < line.size(); ++i) {
        char c = line[i];
        if (c == '"') {
            if (in_quotes && i + 1 < line.size() && line[i + 1] == '"') {
                current += '"';
                ++i;
            } else {
                in_quotes = !in_quotes;
            }
        } else if (c == delimiter && !in_quotes) {
            tokens.push_back(trim(current));
            current.clear();
        } else {
            current += c;
        }
    }
    tokens.push_back(trim(current));
    return tokens;
}

} 

template <typename Scalar>
Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic> read_csv(
    const std::string& filename,
    bool has_header = false,
    char delimiter = ',') {

    std::ifstream file(filename);
    if (!file.is_open()) {
        throw std::runtime_error("Could not open file: " + filename);
    }

    std::vector<std::vector<Scalar>> data;
    std::string line;
    bool first_line = true;

    while (std::getline(file, line)) {
        if (line.empty()) {
            continue;
        }

        if (first_line && has_header) {
            first_line = false;
            continue;
        }
        first_line = false;

        std::vector<std::string> tokens = split_csv_line(line, delimiter);

        if (tokens.empty()) {
            continue;
        }

        std::vector<Scalar> row;
        for (const auto& t : tokens) {
            if (t.empty()) {
                row.push_back(static_cast<Scalar>(0));
            } else {
                std::istringstream converter(t);
                Scalar value;
                if (!(converter >> value)) {
                    throw std::runtime_error("Could not parse value: " + t);
                }
                row.push_back(value);
            }
        }

        if (!data.empty() && row.size() != data[0].size()) {
            throw std::runtime_error("Inconsistent number of columns in CSV file");
        }

        data.push_back(row);
    }

    if (data.empty()) {
        return Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic>();
    }

    Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic> result(
        data.size(), data[0].size());

    for (size_t i = 0; i < data.size(); ++i) {
        for (size_t j = 0; j < data[i].size(); ++j) {
            result(static_cast<Eigen::Index>(i), static_cast<Eigen::Index>(j)) = data[i][j];
        }
    }

    return result;
}

template <typename Scalar>
void write_csv(
    const std::string& filename,
    const Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic>& matrix,
    const std::vector<std::string>& headers = std::vector<std::string>(),
    char delimiter = ',',
    int precision = 10) {

    std::ofstream file(filename);
    if (!file.is_open()) {
        throw std::runtime_error("Could not open file for writing: " + filename);
    }

    file.precision(precision);

    if (!headers.empty()) {
        if (headers.size() != static_cast<size_t>(matrix.cols())) {
            throw std::invalid_argument("Number of headers must match number of columns");
        }
        for (size_t i = 0; i < headers.size(); ++i) {
            if (i > 0) {
                file << delimiter;
            }
            file << headers[i];
        }
        file << "\n";
    }

    for (Eigen::Index i = 0; i < matrix.rows(); ++i) {
        for (Eigen::Index j = 0; j < matrix.cols(); ++j) {
            if (j > 0) {
                file << delimiter;
            }
            file << matrix(i, j);
        }
        file << "\n";
    }
}

template <typename Scalar>
Eigen::Matrix<Scalar, Eigen::Dynamic, 1> read_csv_vector(
    const std::string& filename,
    bool has_header = false) {

    auto matrix = read_csv<Scalar>(filename, has_header);
    if (matrix.cols() == 1) {
        return matrix.col(0);
    } else if (matrix.rows() == 1) {
        return matrix.row(0);
    } else {
        throw std::invalid_argument("CSV file does not contain a single vector");
    }
}

template <typename Scalar>
void write_csv_vector(
    const std::string& filename,
    const Eigen::Matrix<Scalar, Eigen::Dynamic, 1>& vector,
    const std::string& header = "",
    char delimiter = ',',
    int precision = 10) {

    std::vector<std::string> headers;
    if (!header.empty()) {
        headers.push_back(header);
    }

    Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic> matrix = vector;
    write_csv<Scalar>(filename, matrix, headers, delimiter, precision);
}

} 

#endif
