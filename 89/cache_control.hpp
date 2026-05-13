#ifndef CACHE_CONTROL_HPP
#define CACHE_CONTROL_HPP

#include <boost/beast/http.hpp>
#include <string>
#include <chrono>

namespace beast = boost::beast;
namespace http = beast::http;

namespace cache_control {

struct cache_policy {
    bool enable_cache = true;
    std::chrono::seconds max_age = std::chrono::seconds(3600);
    bool is_public = true;
    bool must_revalidate = false;
    bool no_cache = false;
    bool no_store = false;
};

struct compression_result {
    bool compressed = false;
    std::string encoding;
    std::string data;
};

std::string compute_etag(
    const std::string& content,
    std::chrono::system_clock::time_point last_modified);

bool check_if_none_match(
    const http::request<http::string_body>& req,
    const std::string& etag);

void apply_cache_headers(
    http::response<http::string_body>& res,
    const cache_policy& policy,
    const std::string& etag,
    std::chrono::system_clock::time_point last_modified);

http::response<http::string_body> make_304(
    const http::request<http::string_body>& req,
    const std::string& etag);

}

#endif
