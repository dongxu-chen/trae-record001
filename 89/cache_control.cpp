#include "cache_control.hpp"
#include <sstream>
#include <iomanip>
#include <functional>
#include <chrono>

namespace cache_control {

std::string compute_etag(
    const std::string& content,
    std::chrono::system_clock::time_point last_modified)
{
    auto time_t = std::chrono::system_clock::to_time_t(last_modified);
    std::stringstream ss;
    ss << "\""
       << std::hex << std::setw(8) << std::setfill('0')
       << static_cast<std::uint64_t>(time_t)
       << "-"
       << std::hex << std::setw(8) << std::setfill('0')
       << content.size()
       << "\"";
    return ss.str();
}

bool check_if_none_match(
    const http::request<http::string_body>& req,
    const std::string& etag)
{
    auto it = req.find(http::field::if_none_match);
    if (it == req.end()) {
        return false;
    }

    std::string client_etags = it->value().to_string();
    if (client_etags == "*") {
        return true;
    }

    std::size_t pos = 0;
    while (pos < client_etags.size()) {
        std::size_t comma = client_etags.find(',', pos);
        std::string token = (comma == std::string::npos) ?
            client_etags.substr(pos) : client_etags.substr(pos, comma - pos);
        
        while (!token.empty() && (token.front() == ' ' || token.front() == '\t')) {
            token.erase(token.begin());
        }
        while (!token.empty() && (token.back() == ' ' || token.back() == '\t')) {
            token.pop_back();
        }

        if (!token.empty()) {
            bool weak = false;
            if (token.size() >= 2 && token[0] == 'W' && token[1] == '/') {
                weak = true;
                token = token.substr(2);
            }
            if (token == etag) {
                return true;
            }
        }

        if (comma == std::string::npos) {
            break;
        }
        pos = comma + 1;
    }

    return false;
}

void apply_cache_headers(
    http::response<http::string_body>& res,
    const cache_policy& policy,
    const std::string& etag,
    std::chrono::system_clock::time_point last_modified)
{
    if (!policy.enable_cache) {
        res.set(http::field::cache_control, "no-store, no-cache, must-revalidate");
        res.set(http::field::pragma, "no-cache");
        res.set(http::field::expires, "0");
        return;
    }

    std::stringstream cc;
    if (policy.is_public) {
        cc << "public";
    } else {
        cc << "private";
    }
    cc << ", max-age=" << policy.max_age.count();
    if (policy.must_revalidate) {
        cc << ", must-revalidate";
    }
    if (policy.no_cache) {
        cc << ", no-cache";
    }
    if (policy.no_store) {
        cc << ", no-store";
    }
    res.set(http::field::cache_control, cc.str());

    if (!etag.empty()) {
        res.set(http::field::etag, etag);
    }

    auto time_t = std::chrono::system_clock::to_time_t(last_modified);
    std::tm tm_buf;
#if defined(_WIN32)
    gmtime_s(&tm_buf, &time_t);
#else
    gmtime_r(&time_t, &tm_buf);
#endif
    std::stringstream lm;
    lm << std::put_time(&tm_buf, "%a, %d %b %Y %H:%M:%S GMT");
    res.set(http::field::last_modified, lm.str());

    auto expires_tp = last_modified + policy.max_age;
    auto expires_time_t = std::chrono::system_clock::to_time_t(expires_tp);
#if defined(_WIN32)
    gmtime_s(&tm_buf, &expires_time_t);
#else
    gmtime_r(&expires_time_t, &tm_buf);
#endif
    std::stringstream exp;
    exp << std::put_time(&tm_buf, "%a, %d %b %Y %H:%M:%S GMT");
    res.set(http::field::expires, exp.str());
}

http::response<http::string_body> make_304(
    const http::request<http::string_body>& req,
    const std::string& etag)
{
    http::response<http::string_body> res{
        http::status::not_modified, req.version()};
    res.set(http::field::etag, etag);
    res.keep_alive(req.keep_alive());
    res.prepare_payload();
    return res;
}

}
