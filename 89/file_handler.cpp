#include "file_handler.hpp"
#include "mime_types.hpp"
#include <boost/filesystem.hpp>
#include <boost/optional.hpp>
#include <fstream>
#include <sstream>
#include <cctype>
#include <algorithm>
#include <list>
#include <shared_mutex>

namespace fs = boost::filesystem;

static const std::size_t MAX_CACHE_SIZE_BYTES = 64 * 1024 * 1024;
static const std::size_t MAX_FILE_SIZE_TO_CACHE = 2 * 1024 * 1024;
static const std::size_t MAX_CACHE_ENTRIES = 1024;

struct file_handler::cache_entry {
    std::string path;
    cached_file file;
    std::size_t size;
};

file_handler::file_handler(std::string doc_root)
    : doc_root_(std::move(doc_root))
{
    cache_policy_.enable_cache = true;
    cache_policy_.max_age = std::chrono::hours(24);
    cache_policy_.is_public = true;
    cache_policy_.must_revalidate = false;
}

std::string file_handler::url_decode(const std::string& in)
{
    std::string out;
    out.reserve(in.size());

    for (std::size_t i = 0; i < in.size(); ++i) {
        if (in[i] == '%' && i + 2 < in.size()) {
            std::string hex = in.substr(i + 1, 2);
            int value = 0;
            std::istringstream iss(hex);
            if (iss >> std::hex >> value) {
                out.push_back(static_cast<char>(value));
                i += 2;
            } else {
                out.push_back(in[i]);
            }
        } else if (in[i] == '+') {
            out.push_back(' ');
        } else {
            out.push_back(in[i]);
        }
    }

    return out;
}

std::string file_handler::normalize_path(const std::string& path)
{
    std::string result;
    result.reserve(path.size() + 1);

    bool prev_slash = false;
    for (char c : path) {
        if (c == '/' || c == '\\') {
            if (!prev_slash) {
                result.push_back('/');
                prev_slash = true;
            }
        } else {
            result.push_back(c);
            prev_slash = false;
        }
    }

    return result;
}

bool file_handler::path_traversal(const std::string& path)
{
    std::string normalized = normalize_path(path);
    
    std::size_t pos = 0;
    while ((pos = normalized.find("..", pos)) != std::string::npos) {
        bool has_preceding_slash = (pos == 0) || (normalized[pos - 1] == '/');
        bool has_following_slash = (pos + 2 == normalized.size()) ||
                                   (normalized[pos + 2] == '/');
        
        if (has_preceding_slash && has_following_slash) {
            return true;
        }
        ++pos;
    }

    return false;
}

bool file_handler::should_compress(const std::string& mime_type)
{
    if (mime_type.find("text/") == 0) return true;
    if (mime_type == "application/javascript") return true;
    if (mime_type == "application/json") return true;
    if (mime_type == "application/ld+json") return true;
    if (mime_type == "application/xml") return true;
    if (mime_type == "image/svg+xml") return true;
    if (mime_type == "font/ttf") return true;
    if (mime_type == "font/otf") return true;
    return false;
}

boost::optional<file_handler::cached_file> file_handler::read_file(const std::string& full_path)
{
    {
        std::shared_lock<std::shared_mutex> rlock(cache_mutex_);
        auto it = cache_map_.find(full_path);
        if (it != cache_map_.end()) {
            cached_file cf = it->second->file;
            rlock.unlock();
            std::unique_lock<std::shared_mutex> wlock(cache_mutex_);
            auto it2 = cache_map_.find(full_path);
            if (it2 != cache_map_.end()) {
                lru_list_.splice(lru_list_.begin(), lru_list_, it2->second);
            }
            return cf;
        }
    }

    fs::path p(full_path);
    if (!fs::exists(p) || !fs::is_regular_file(p)) {
        return boost::none;
    }

    std::uintmax_t file_size = fs::file_size(p);
    bool should_cache = file_size <= MAX_FILE_SIZE_TO_CACHE;

    std::ifstream file(full_path, std::ios::binary);
    if (!file) {
        return boost::none;
    }

    std::ostringstream oss;
    oss << file.rdbuf();

    std::string ext = p.extension().string();
    if (!ext.empty() && ext[0] == '.') {
        ext = ext.substr(1);
    }

    auto last_modified = std::chrono::system_clock::from_time_t(
        fs::last_write_time(p));
    std::string content = oss.str();
    std::string mime = mime_types::extension_to_type(ext);
    std::string etag = cache_control::compute_etag(content, last_modified);

    cached_file cf;
    cf.content = std::move(content);
    cf.mime_type = std::move(mime);
    cf.last_modified = last_modified;
    cf.etag = std::move(etag);

    if (should_cache && cf.content.size() <= MAX_FILE_SIZE_TO_CACHE) {
        std::unique_lock<std::shared_mutex> wlock(cache_mutex_);
        auto it = cache_map_.find(full_path);
        if (it != cache_map_.end()) {
            total_cache_size_ -= it->second->size;
            lru_list_.erase(it->second);
            cache_map_.erase(it);
        }

        while (total_cache_size_ + cf.content.size() > MAX_CACHE_SIZE_BYTES ||
               cache_map_.size() >= MAX_CACHE_ENTRIES) {
            if (lru_list_.empty()) {
                break;
            }
            auto last = lru_list_.end();
            --last;
            total_cache_size_ -= last->size;
            cache_map_.erase(last->path);
            lru_list_.erase(last);
        }

        cache_entry entry;
        entry.path = full_path;
        entry.file = cf;
        entry.size = cf.content.size();
        lru_list_.push_front(std::move(entry));
        cache_map_[full_path] = lru_list_.begin();
        total_cache_size_ += cf.content.size();
    }

    return cf;
}

http::response<http::string_body> file_handler::make_404()
{
    http::response<http::string_body> res{
        http::status::not_found, 11};
    res.set(http::field::content_type, "text/html");
    res.body() = "<html><head><title>404 Not Found</title></head>"
                 "<body><h1>404 Not Found</h1></body></html>";
    res.prepare_payload();
    return res;
}

http::response<http::string_body> file_handler::make_400()
{
    http::response<http::string_body> res{
        http::status::bad_request, 11};
    res.set(http::field::content_type, "text/html");
    res.body() = "<html><head><title>400 Bad Request</title></head>"
                 "<body><h1>400 Bad Request</h1></body></html>";
    res.prepare_payload();
    return res;
}

http::response<http::string_body> file_handler::make_404_with_version(
    unsigned version, bool keep_alive)
{
    http::response<http::string_body> res{
        http::status::not_found, version};
    res.set(http::field::content_type, "text/html");
    res.keep_alive(keep_alive);
    res.body() = "<html><head><title>404 Not Found</title></head>"
                 "<body><h1>404 Not Found</h1></body></html>";
    res.prepare_payload();
    return res;
}

http::response<http::string_body> file_handler::make_400_with_version(
    unsigned version, bool keep_alive)
{
    http::response<http::string_body> res{
        http::status::bad_request, version};
    res.set(http::field::content_type, "text/html");
    res.keep_alive(keep_alive);
    res.body() = "<html><head><title>400 Bad Request</title></head>"
                 "<body><h1>400 Bad Request</h1></body></html>";
    res.prepare_payload();
    return res;
}

http::response<http::string_body> file_handler::handle_request(
    const http::request<http::string_body>& req)
{
    bool req_keep_alive = req.keep_alive();
    unsigned req_version = req.version();

    if (req.method() != http::verb::get &&
        req.method() != http::verb::head) {
        http::response<http::string_body> res{
            http::status::method_not_allowed, req_version};
        res.set(http::field::content_type, "text/plain");
        res.keep_alive(req_keep_alive);
        res.body() = "Method not allowed";
        res.prepare_payload();
        return res;
    }

    std::string path = url_decode(req.target().to_string());

    std::string::size_type query_pos = path.find('?');
    if (query_pos != std::string::npos) {
        path = path.substr(0, query_pos);
    }

    if (path_traversal(path)) {
        return make_400_with_version(req_version, req_keep_alive);
    }

    if (path.empty() || path.back() != '/') {
        path += '/';
    }
    if (path.empty() || path[0] != '/') {
        path = "/" + path;
    }

    fs::path full_path = doc_root_;
    full_path /= path.substr(1);

    if (fs::is_directory(full_path)) {
        full_path /= "index.html";
    }

    auto file_opt = read_file(full_path.string());
    if (!file_opt) {
        return make_404_with_version(req_version, req_keep_alive);
    }

    const cached_file& cf = *file_opt;

    if (cache_control::check_if_none_match(req, cf.etag)) {
        return cache_control::make_304(req, cf.etag);
    }

    http::response<http::string_body> res{
        http::status::ok, req_version};
    res.set(http::field::content_type, cf.mime_type);
    res.set(http::field::server, "Boost.Beast Static Server");
    res.keep_alive(req_keep_alive);

    cache_control::apply_cache_headers(
        res, cache_policy_, cf.etag, cf.last_modified);

    if (req.method() != http::verb::head) {
        auto accept_enc = req[http::field::accept_encoding];
        if (should_compress(cf.mime_type) && !accept_enc.empty()) {
            auto methods = compression::parse_accept_encoding(
                accept_enc.to_string());
            auto comp = compression::compress_best(cf.content, methods);
            
            if (comp.used == compression::method::gzip) {
                res.set(http::field::content_encoding, "gzip");
                res.body() = std::move(comp.data);
            } else if (comp.used == compression::method::brotli) {
                res.set(http::field::content_encoding, "br");
                res.body() = std::move(comp.data);
            } else {
                res.body() = cf.content;
            }
        } else {
            res.body() = cf.content;
        }
    }

    res.prepare_payload();
    return res;
}
