#include "router.hpp"
#include <string>

void router::add_route(
    http::verb method,
    const std::string& path_pattern,
    handler_func handler)
{
    routes_.push_back({method, path_pattern, std::move(handler)});
}

void router::set_static_handler(handler_func handler)
{
    static_handler_ = std::move(handler);
}

http::response<http::string_body> router::route(
    const http::request<http::string_body>& req) const
{
    std::string target = req.target().to_string();
    std::string::size_type query_pos = target.find('?');
    if (query_pos != std::string::npos) {
        target = target.substr(0, query_pos);
    }

    for (const auto& entry : routes_) {
        if (entry.method != req.method()) {
            continue;
        }

        if (entry.pattern == target) {
            return entry.handler(req);
        }

        if (!entry.pattern.empty() && entry.pattern.back() == '*') {
            std::string prefix = entry.pattern.substr(0, entry.pattern.size() - 1);
            if (target.substr(0, prefix.size()) == prefix) {
                return entry.handler(req);
            }
        }
    }

    if (static_handler_) {
        return static_handler_(req);
    }

    http::response<http::string_body> res{
        http::status::not_found, req.version()};
    res.set(http::field::content_type, "text/plain");
    res.body() = "Not Found";
    res.prepare_payload();
    return res;
}
