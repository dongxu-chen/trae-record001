#ifndef COMPRESSION_HPP
#define COMPRESSION_HPP

#include <string>
#include <vector>

namespace compression {

enum class method {
    none,
    gzip,
    brotli
};

struct result {
    bool success = false;
    std::string data;
    method used = method::none;
};

result compress_gzip(const std::string& input, int level = 6);
result compress_brotli(const std::string& input, int quality = 6);

std::vector<method> parse_accept_encoding(const std::string& header);
result compress_best(const std::string& input, const std::vector<method>& preferred);

std::size_t crc32(const std::string& data);

}

#endif
