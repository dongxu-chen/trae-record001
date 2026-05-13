#ifndef ROUTER_HPP
#define ROUTER_HPP

#include "file_handler.hpp"
#include <boost/beast/http.hpp>
#include <string>
#include <functional>
#include <unordered_map>
#include <vector>

namespace beast = boost::beast;
namespace http = beast::http;

class router {
public:
    using handler_func = std::function<
        http::response<http::string_body>(
            const http::request<http::string_body>&)>;

    router() = default;

    void add_route(
        http::verb method,
        const std::string& path_pattern,
        handler_func handler);

    void set_static_handler(handler_func handler);

    http::response<http::string_body> route(
        const http::request<http::string_body>& req) const;

private:
    struct route_entry {
        http::verb method;
        std::string pattern;
        handler_func handler;
    };

    std::vector<route_entry> routes_;
    handler_func static_handler_;
};

#endif
