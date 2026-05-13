#ifndef FILE_HANDLER_HPP
#define FILE_HANDLER_HPP

#include <boost/beast/core.hpp>
#include <boost/beast/http.hpp>
#include <string>
#include <memory>
#include <unordered_map>
#include <chrono>
#include <shared_mutex>
#include <list>

#include "cache_control.hpp"
#include "compression.hpp"

namespace beast = boost::beast;
namespace http = beast::http;

class file_handler {
public:
    explicit file_handler(std::string doc_root);

    http::response<http::string_body> handle_request(
        const http::request<http::string_body>& req);

private:
    struct cached_file {
        std::string content;
        std::chrono::system_clock::time_point last_modified;
        std::string mime_type;
        std::string etag;
    };

    struct cache_entry;

    std::string doc_root_;
    std::list<cache_entry> lru_list_;
    std::unordered_map<std::string, std::list<cache_entry>::iterator> cache_map_;
    std::size_t total_cache_size_ = 0;
    mutable std::shared_mutex cache_mutex_;
    cache_control::cache_policy cache_policy_;

    std::string url_decode(const std::string& in);
    std::string normalize_path(const std::string& path);
    bool path_traversal(const std::string& path);
    boost::optional<cached_file> read_file(const std::string& full_path);

    http::response<http::string_body> make_404();
    http::response<http::string_body> make_400();
    http::response<http::string_body> make_404_with_version(
        unsigned version, bool keep_alive);
    http::response<http::string_body> make_400_with_version(
        unsigned version, bool keep_alive);

    bool should_compress(const std::string& mime_type);
};

#endif
