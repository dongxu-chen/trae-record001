#!/usr/bin/env python3
import os
import argparse
import subprocess

NGINX_CONF_DIRS = [
    "/etc/nginx/conf.d",
    "/etc/nginx/sites-available",
    "/usr/local/nginx/conf.d",
    "/usr/local/nginx/conf",
]

DEFAULT_PHP_FPM_SOCK = "127.0.0.1:9000"


def log_info(msg):
    print(f"\033[0;32m[INFO]\033[0m {msg}")


def log_warn(msg):
    print(f"\033[1;33m[WARN]\033[0m {msg}")


def log_error(msg):
    print(f"\033[0;31m[ERROR]\033[0m {msg}")


def run_cmd(cmd, shell=True, check=True):
    try:
        result = subprocess.run(
            cmd,
            shell=shell,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=check
        )
        return result
    except subprocess.CalledProcessError as e:
        log_error(f"Command failed: {cmd}")
        if e.stderr:
            print(e.stderr)
        raise


def detect_nginx_conf_dir():
    try:
        result = run_cmd("nginx -t 2>&1", check=False)
        output = result.stdout + result.stderr
        import re
        match = re.search(r"configuration file\s+(\S+)\s+test is successful", output)
        if match:
            conf_file = match.group(1)
            conf_dir = os.path.dirname(conf_file)
            conf_d = os.path.join(conf_dir, "conf.d")
            if os.path.exists(conf_d):
                return conf_d
            sites_avail = os.path.join(conf_dir, "sites-available")
            if os.path.exists(sites_avail):
                return sites_avail
            return conf_dir
    except:
        pass

    for d in NGINX_CONF_DIRS:
        if os.path.exists(d):
            return d
    return None


def generate_site_config(
    domain,
    root_dir,
    php_fpm=DEFAULT_PHP_FPM_SOCK,
    ssl=False,
    ssl_cert="",
    ssl_key="",
    index_files=None,
    server_name_alias=None,
):
    if index_files is None:
        index_files = ["index.php", "index.html", "index.htm"]

    index_str = " ".join(index_files)

    if php_fpm.startswith("/"):
        fastcgi_pass = f"unix:{php_fpm}"
    else:
        fastcgi_pass = php_fpm

    server_name = domain
    if server_name_alias:
        server_name = f"{domain} {server_name_alias}"

    http_block = f"""server {{
    listen 80;
    server_name {server_name};
    root {root_dir};
    index {index_str};

    location / {{
        try_files $uri $uri/ =404;
    }}

    location ~ \.php$ {{
        include fastcgi_params;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
        fastcgi_pass {fastcgi_pass};
    }}

    location ~* \.(js|css|png|jpg|jpeg|gif|ico|woff|woff2|svg|eot|ttf|otf)$ {{
        expires 30d;
        log_not_found off;
    }}

    access_log /var/log/nginx/{domain}.log;
    error_log /var/log/nginx/{domain}-error.log;
}}
"""

    if not ssl:
        return http_block

    https_block = f"""server {{
    listen 443 ssl http2;
    server_name {server_name};
    root {root_dir};
    index {index_str};

    ssl_certificate {ssl_cert};
    ssl_certificate_key {ssl_key};
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    location / {{
        try_files $uri $uri/ =404;
    }}

    location ~ \.php$ {{
        include fastcgi_params;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
        fastcgi_pass {fastcgi_pass};
    }}

    location ~* \.(js|css|png|jpg|jpeg|gif|ico|woff|woff2|svg|eot|ttf|otf)$ {{
        expires 30d;
        log_not_found off;
    }}

    access_log /var/log/nginx/{domain}.log;
    error_log /var/log/nginx/{domain}-error.log;
}}

server {{
    listen 80;
    server_name {server_name};
    return 301 https://$host$request_uri;
}}
"""

    return https_block


def check_port(port):
    try:
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            result = s.connect_ex(("127.0.0.1", port))
            return result == 0
    except:
        pass

    try:
        result = run_cmd(f"ss -tulpn 2>/dev/null | grep -q ':{port} '", check=False)
        if result.returncode == 0:
            return True
        result = run_cmd(f"netstat -tulpn 2>/dev/null | grep -q ':{port} '", check=False)
        return result.returncode == 0
    except:
        return False


def save_config(content, conf_dir, domain, sites_enabled=None):
    conf_file = os.path.join(conf_dir, f"{domain}.conf")

    os.makedirs(conf_dir, exist_ok=True)

    with open(conf_file, "w") as f:
        f.write(content)

    log_info(f"Config saved: {conf_file}")

    if sites_enabled and os.path.exists(sites_enabled):
        enabled_link = os.path.join(sites_enabled, f"{domain}.conf")
        if os.path.exists(enabled_link):
            os.remove(enabled_link)
        os.symlink(conf_file, enabled_link)
        log_info(f"Enabled: {enabled_link}")

    return conf_file


def test_nginx_config():
    log_info("Testing nginx configuration...")
    result = run_cmd("nginx -t", check=False)
    output = result.stdout + result.stderr
    print(output)
    return result.returncode == 0


def reload_nginx():
    log_info("Reloading nginx...")
    run_cmd("nginx -s reload")
    log_info("Nginx reloaded")


def create_document_root(root_dir):
    if os.path.exists(root_dir):
        log_warn(f"Document root exists: {root_dir}")
        return

    os.makedirs(root_dir, exist_ok=True)
    log_info(f"Created document root: {root_dir}")

    index_php = os.path.join(root_dir, "index.php")
    with open(index_php, "w") as f:
        f.write("<?php phpinfo();")
    log_info(f"Created test file: {index_php}")


def list_sites(conf_dir):
    if not conf_dir or not os.path.exists(conf_dir):
        log_warn(f"Config directory not found: {conf_dir}")
        return

    files = [f for f in os.listdir(conf_dir) if f.endswith(".conf")]
    if not files:
        log_info("No sites configured")
        return

    log_info(f"Configured sites:")
    for f in sorted(files):
        print(f"  - {f}")


def main():
    parser = argparse.ArgumentParser(description="Generate Nginx site configuration")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    create_parser = subparsers.add_parser("create", help="Create a new site")
    create_parser.add_argument("--domain", "-d", required=True, help="Domain name")
    create_parser.add_argument("--root", "-r", required=True, help="Document root")
    create_parser.add_argument("--php-fpm", default=DEFAULT_PHP_FPM_SOCK, help="PHP-FPM address or socket")
    create_parser.add_argument("--ssl", action="store_true", help="Enable SSL")
    create_parser.add_argument("--ssl-cert", help="SSL certificate path")
    create_parser.add_argument("--ssl-key", help="SSL key path")
    create_parser.add_argument("--alias", help="Server name alias")
    create_parser.add_argument("--conf-dir", help="Nginx config directory")
    create_parser.add_argument("--sites-enabled", help="Sites-enabled directory for symlink")
    create_parser.add_argument("--no-reload", action="store_true", help="Do not reload nginx")
    create_parser.add_argument("--no-test", action="store_true", help="Do not test nginx config")

    list_parser = subparsers.add_parser("list", help="List configured sites")
    list_parser.add_argument("--conf-dir", help="Nginx config directory")

    args = parser.parse_args()

    if args.command == "list":
        conf_dir = args.conf_dir or detect_nginx_conf_dir()
        list_sites(conf_dir)
        return

    if args.command != "create":
        parser.print_help()
        return

    if args.ssl and (not args.ssl_cert or not args.ssl_key):
        log_error("--ssl requires --ssl-cert and --ssl-key")
        return

    conf_dir = args.conf_dir or detect_nginx_conf_dir()
    if not conf_dir:
        log_error("Could not detect nginx config directory")
        return

    log_info(f"Using config directory: {conf_dir}")

    ports_to_check = [80]
    if args.ssl:
        ports_to_check.append(443)

    for port in ports_to_check:
        if check_port(port):
            log_warn(f"Port {port} is already in use")
        else:
            log_info(f"Port {port} is available")

    create_document_root(args.root)

    config_content = generate_site_config(
        domain=args.domain,
        root_dir=args.root,
        php_fpm=args.php_fpm,
        ssl=args.ssl,
        ssl_cert=args.ssl_cert or "",
        ssl_key=args.ssl_key or "",
        server_name_alias=args.alias,
    )

    save_config(config_content, conf_dir, args.domain, args.sites_enabled)

    if not args.no_test and not test_nginx_config():
        log_error("Nginx config test failed")
        return

    if not args.no_reload:
        reload_nginx()

    log_info(f"Site {args.domain} configured successfully")


if __name__ == "__main__":
    main()
