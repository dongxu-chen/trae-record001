#include "router.hpp"
#include "file_handler.hpp"

#include <boost/asio.hpp>
#include <boost/asio/ssl.hpp>
#include <boost/beast/core.hpp>
#include <boost/beast/http.hpp>
#include <boost/beast/ssl.hpp>
#include <boost/beast/version.hpp>

#include <cstdlib>
#include <iostream>
#include <memory>
#include <string>
#include <thread>

namespace beast = boost::beast;
namespace http = beast::http;
namespace net = boost::asio;
namespace ssl = net::ssl;
using tcp = net::ip::tcp;

struct server_config {
    std::string address;
    unsigned short port;
    std::string doc_root;
    int threads;
    bool use_ssl = false;
    std::string cert_file;
    std::string key_file;
    std::string dh_file;
};

class plain_session : public std::enable_shared_from_this<plain_session> {
    tcp::socket socket_;
    beast::flat_buffer buffer_;
    http::request<http::string_body> req_;
    const router& router_;

public:
    plain_session(tcp::socket socket, const router& r)
        : socket_(std::move(socket)), router_(r) {}

    void run() {
        do_read();
    }

private:
    void do_read() {
        auto self(shared_from_this());
        http::async_read(socket_, buffer_, req_,
            [this, self](beast::error_code ec, std::size_t bytes_transferred) {
                boost::ignore_unused(bytes_transferred);
                if (ec == http::error::end_of_stream) {
                    return do_close();
                }
                if (ec) {
                    return;
                }
                handle_request();
            });
    }

    void handle_request() {
        auto response = router_.route(req_);
        bool should_close = response.need_eof() || !response.keep_alive();

        auto self(shared_from_this());
        auto sp = std::make_shared<http::response<http::string_body>>(std::move(response));

        http::async_write(socket_, *sp,
            [this, self, sp, should_close](beast::error_code ec, std::size_t bytes_transferred) {
                boost::ignore_unused(bytes_transferred);
                if (ec) {
                    return;
                }
                if (should_close) {
                    return do_close();
                }
                req_ = {};
                do_read();
            });
    }

    void do_close() {
        beast::error_code ec;
        socket_.shutdown(tcp::socket::shutdown_send, ec);
    }
};

class ssl_session : public std::enable_shared_from_this<ssl_session> {
    beast::ssl_stream<beast::tcp_stream> stream_;
    beast::flat_buffer buffer_;
    http::request<http::string_body> req_;
    const router& router_;

public:
    ssl_session(beast::tcp_stream&& stream, ssl::context& ctx, const router& r)
        : stream_(std::move(stream), ctx), router_(r) {}

    void run() {
        net::dispatch(stream_.get_executor(),
            beast::bind_front_handler(&ssl_session::on_run, shared_from_this()));
    }

private:
    void on_run() {
        beast::get_lowest_layer(stream_).expires_after(std::chrono::seconds(30));
        stream_.async_handshake(ssl::stream_base::server,
            beast::bind_front_handler(&ssl_session::on_handshake, shared_from_this()));
    }

    void on_handshake(beast::error_code ec) {
        if (ec) {
            return;
        }
        do_read();
    }

    void do_read() {
        beast::get_lowest_layer(stream_).expires_after(std::chrono::seconds(30));
        auto self(shared_from_this());
        http::async_read(stream_, buffer_, req_,
            [this, self](beast::error_code ec, std::size_t bytes_transferred) {
                boost::ignore_unused(bytes_transferred);
                if (ec == http::error::end_of_stream) {
                    return do_close();
                }
                if (ec) {
                    return;
                }
                handle_request();
            });
    }

    void handle_request() {
        auto response = router_.route(req_);
        bool should_close = response.need_eof() || !response.keep_alive();

        auto self(shared_from_this());
        auto sp = std::make_shared<http::response<http::string_body>>(std::move(response));

        http::async_write(stream_, *sp,
            [this, self, sp, should_close](beast::error_code ec, std::size_t bytes_transferred) {
                boost::ignore_unused(bytes_transferred);
                if (ec) {
                    return;
                }
                if (should_close) {
                    return do_close();
                }
                req_ = {};
                do_read();
            });
    }

    void do_close() {
        beast::get_lowest_layer(stream_).expires_after(std::chrono::seconds(30));
        stream_.async_shutdown(
            beast::bind_front_handler(&ssl_session::on_shutdown, shared_from_this()));
    }

    void on_shutdown(beast::error_code ec) {
        if (ec) {
            return;
        }
    }
};

class plain_server : public std::enable_shared_from_this<plain_server> {
    net::io_context& ioc_;
    tcp::acceptor acceptor_;
    const router& router_;

public:
    plain_server(net::io_context& ioc, tcp::endpoint endpoint, const router& r)
        : ioc_(ioc), acceptor_(net::make_strand(ioc)), router_(r) {
        beast::error_code ec;
        acceptor_.open(endpoint.protocol(), ec);
        if (ec) return;
        acceptor_.set_option(net::socket_base::reuse_address(true), ec);
        if (ec) return;
        acceptor_.bind(endpoint, ec);
        if (ec) return;
        acceptor_.listen(net::socket_base::max_listen_connections, ec);
    }

    void run() {
        do_accept();
    }

private:
    void do_accept() {
        acceptor_.async_accept(net::make_strand(ioc_),
            beast::bind_front_handler(&plain_server::on_accept, shared_from_this()));
    }

    void on_accept(beast::error_code ec, tcp::socket socket) {
        if (!ec) {
            std::cout << "HTTP Connection from: "
                      << socket.remote_endpoint().address().to_string() << ":"
                      << socket.remote_endpoint().port() << "\n";
            std::make_shared<plain_session>(std::move(socket), router_)->run();
        }
        do_accept();
    }
};

class ssl_server : public std::enable_shared_from_this<ssl_server> {
    net::io_context& ioc_;
    tcp::acceptor acceptor_;
    ssl::context& ctx_;
    const router& router_;

public:
    ssl_server(net::io_context& ioc, tcp::endpoint endpoint,
               ssl::context& ctx, const router& r)
        : ioc_(ioc), acceptor_(net::make_strand(ioc)), ctx_(ctx), router_(r) {
        beast::error_code ec;
        acceptor_.open(endpoint.protocol(), ec);
        if (ec) return;
        acceptor_.set_option(net::socket_base::reuse_address(true), ec);
        if (ec) return;
        acceptor_.bind(endpoint, ec);
        if (ec) return;
        acceptor_.listen(net::socket_base::max_listen_connections, ec);
    }

    void run() {
        do_accept();
    }

private:
    void do_accept() {
        acceptor_.async_accept(net::make_strand(ioc_),
            beast::bind_front_handler(&ssl_server::on_accept, shared_from_this()));
    }

    void on_accept(beast::error_code ec, tcp::socket socket) {
        if (!ec) {
            std::cout << "HTTPS Connection from: "
                      << socket.remote_endpoint().address().to_string() << ":"
                      << socket.remote_endpoint().port() << "\n";
            std::make_shared<ssl_session>(
                beast::tcp_stream(std::move(socket)), ctx_, router_)->run();
        }
        do_accept();
    }
};

void load_server_certificates(ssl::context& ctx,
    const std::string& cert_file, const std::string& key_file,
    const std::string& dh_file = "")
{
    ctx.set_options(
        ssl::context::default_workarounds |
        ssl::context::no_sslv2 |
        ssl::context::no_sslv3 |
        ssl::context::single_dh_use);

    ctx.use_certificate_chain_file(cert_file);
    ctx.use_private_key_file(key_file, ssl::context::pem);
    if (!dh_file.empty()) {
        ctx.use_tmp_dh_file(dh_file);
    }
}

void print_usage(const char* prog) {
    std::cerr << "Usage: " << prog << " [options] <address> <port> <doc_root>\n\n";
    std::cerr << "Options:\n";
    std::cerr << "  --ssl               Enable HTTPS\n";
    std::cerr << "  --cert <file>       Path to SSL certificate file\n";
    std::cerr << "  --key <file>        Path to SSL private key file\n";
    std::cerr << "  --dh <file>         Path to DH params file (optional)\n";
    std::cerr << "  --threads <n>       Number of worker threads\n\n";
    std::cerr << "HTTP Example: " << prog << " 0.0.0.0 8080 ./public\n";
    std::cerr << "HTTPS Example: " << prog << " --ssl --cert cert.pem --key key.pem 0.0.0.0 8443 ./public\n";
}

int main(int argc, char* argv[]) {
    server_config cfg;
    cfg.threads = std::max<int>(1, std::thread::hardware_concurrency());
    std::vector<std::string> positional;

    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg == "--ssl") {
            cfg.use_ssl = true;
        } else if (arg == "--cert" && i + 1 < argc) {
            cfg.cert_file = argv[++i];
        } else if (arg == "--key" && i + 1 < argc) {
            cfg.key_file = argv[++i];
        } else if (arg == "--dh" && i + 1 < argc) {
            cfg.dh_file = argv[++i];
        } else if (arg == "--threads" && i + 1 < argc) {
            cfg.threads = std::atoi(argv[++i]);
        } else if (arg == "--help" || arg == "-h") {
            print_usage(argv[0]);
            return EXIT_SUCCESS;
        } else if (!arg.empty() && arg[0] != '-') {
            positional.push_back(arg);
        }
    }

    if (positional.size() != 3) {
        print_usage(argv[0]);
        return EXIT_FAILURE;
    }

    cfg.address = positional[0];
    cfg.port = static_cast<unsigned short>(std::atoi(positional[1].c_str()));
    cfg.doc_root = positional[2];

    if (cfg.use_ssl && (cfg.cert_file.empty() || cfg.key_file.empty())) {
        std::cerr << "Error: HTTPS requires --cert and --key\n";
        return EXIT_FAILURE;
    }

    router r;
    file_handler fh(cfg.doc_root);

    r.set_static_handler([&fh](const http::request<http::string_body>& req) {
        return fh.handle_request(req);
    });

    r.add_route(http::verb::get, "/ping",
        [](const http::request<http::string_body>& req) {
            http::response<http::string_body> res{http::status::ok, req.version()};
            res.set(http::field::content_type, "application/json");
            res.keep_alive(req.keep_alive());
            res.body() = "{\"status\":\"ok\",\"message\":\"pong\"}";
            res.prepare_payload();
            return res;
        });

    r.add_route(http::verb::get, "/api/status",
        [](const http::request<http::string_body>& req) {
            http::response<http::string_body> res{http::status::ok, req.version()};
            res.set(http::field::content_type, "application/json");
            res.keep_alive(req.keep_alive());
            res.body() = "{\"status\":\"running\",\"server\":\"Boost.Beast Static Server\"}";
            res.prepare_payload();
            return res;
        });

    net::io_context ioc{cfg.threads};

    try {
        auto const address = net::ip::make_address(cfg.address);
        tcp::endpoint endpoint{address, cfg.port};

        if (cfg.use_ssl) {
            ssl::context ctx{ssl::context::tlsv12};
            load_server_certificates(ctx, cfg.cert_file, cfg.key_file, cfg.dh_file);
            std::make_shared<ssl_server>(ioc, endpoint, ctx, r)->run();
            std::cout << "HTTPS Server running on: " << cfg.address << ":" << cfg.port << "\n";
        } else {
            std::make_shared<plain_server>(ioc, endpoint, r)->run();
            std::cout << "HTTP Server running on: " << cfg.address << ":" << cfg.port << "\n";
        }

        std::cout << "Document root: " << cfg.doc_root << "\n";
        std::cout << "Using " << cfg.threads << " threads\n";
        if (cfg.use_ssl) {
            std::cout << "SSL/TLS enabled\n";
        }
    } catch (std::exception const& e) {
        std::cerr << "Error: " << e.what() << "\n";
        return EXIT_FAILURE;
    }

    std::vector<std::thread> v;
    v.reserve(cfg.threads - 1);
    for (auto i = cfg.threads - 1; i > 0; --i) {
        v.emplace_back([&ioc] { ioc.run(); });
    }
    ioc.run();

    return EXIT_SUCCESS;
}
