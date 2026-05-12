#!/usr/bin/env python3
import os
import argparse
import subprocess
import json

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

DEFAULT_BASE_IMAGE = "ubuntu:22.04"
DEFAULT_PHP_VERSION = "8.2"
DEFAULT_MYSQL_VERSION = "10.11"
DEFAULT_NGINX_VERSION = "1.27"

PHP_VERSIONS = ["7.4", "8.0", "8.1", "8.2", "8.3"]


def log_info(msg):
    print(f"\033[0;32m[INFO]\033[0m {msg}")


def log_warn(msg):
    print(f"\033[1;33m[WARN]\033[0m {msg}")


def log_error(msg):
    print(f"\033[0;31m[ERROR]\033[0m {msg}")


def run_cmd(cmd, shell=True, check=True):
    log_info(f"Running: {cmd}")
    try:
        result = subprocess.run(
            cmd,
            shell=shell,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=check
        )
        if result.stdout:
            print(result.stdout)
        return result
    except subprocess.CalledProcessError as e:
        log_error(f"Command failed: {cmd}")
        if e.stdout:
            print(e.stdout)
        raise


def generate_dockerfile_php(base_image, php_version, prefix="/usr/local/php"):
    return f"""FROM {base_image} AS builder

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN apt-get update && apt-get install -y \\
    build-essential \\
    autoconf \\
    libtool \\
    re2c \\
    pkg-config \\
    bison \\
    flex \\
    wget \\
    ca-certificates \\
    libxml2-dev \\
    libssl-dev \\
    libbz2-dev \\
    libcurl4-openssl-dev \\
    libpng-dev \\
    libjpeg-dev \\
    libfreetype6-dev \\
    libzip-dev \\
    libonig-dev \\
    libreadline-dev \\
    zlib1g-dev \\
    libsqlite3-dev

WORKDIR /tmp/build

COPY install_php.py /tmp/build/

RUN python3 install_php.py \\
    --version {php_version} \\
    --prefix {prefix} \\
    --src-dir /tmp/src \\
    --docker \\
    --skip-deps \\
    --jobs $(nproc)

FROM {base_image} AS runtime

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC
ENV PATH={prefix}/bin:{prefix}/sbin:$PATH

RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN apt-get update && apt-get install -y --no-install-recommends \\
    ca-certificates \\
    libxml2 \\
    libssl3 \\
    libbz2-1.0 \\
    libcurl4 \\
    libpng16-16 \\
    libjpeg8 \\
    libfreetype6 \\
    libzip4 \\
    libonig5 \\
    libreadline8 \\
    zlib1g \\
    libsqlite3-0 \\
    tini \\
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder {prefix} {prefix}

RUN groupadd -r www-data && useradd -r -g www-data -s /usr/sbin/nologin www-data

RUN mkdir -p /var/www/html \\
    && chown -R www-data:www-data /var/www/html

WORKDIR /var/www/html

EXPOSE 9000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \\
    CMD php-fpm -t || exit 1

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["php-fpm", "-F"]
"""


def generate_dockerfile_nginx(base_image="nginx:alpine"):
    return f"""FROM {base_image}

RUN apk add --no-cache tini

COPY nginx.conf /etc/nginx/nginx.conf
COPY conf.d/ /etc/nginx/conf.d/

RUN mkdir -p /var/www/html /var/log/nginx

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \\
    CMD wget --spider http://127.0.0.1:80 || exit 1

ENTRYPOINT ["/sbin/tini", "--"]
CMD ["nginx", "-g", "daemon off;"]
"""


def generate_nginx_conf():
    return """user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
}

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;

    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent"';

    access_log /var/log/nginx/access.log main;

    sendfile on;
    tcp_nopush on;
    keepalive_timeout 65;
    gzip on;

    include /etc/nginx/conf.d/*.conf;
}
"""


def generate_default_site_conf(php_service="php", php_port=9000):
    return f"""server {{
    listen 80;
    server_name _;
    root /var/www/html;
    index index.php index.html;

    location / {{
        try_files $uri $uri/ =404;
    }}

    location ~ \.php$ {{
        fastcgi_pass {php_service}:{php_port};
        fastcgi_index index.php;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
        include fastcgi_params;
    }}

    location ~* \.(js|css|png|jpg|jpeg|gif|ico|woff|woff2|svg|eot|ttf|otf)$ {{
        expires 30d;
        log_not_found off;
    }}
}}
"""


def generate_docker_compose(
    project_name="lnmp",
    php_version="8.2",
    mysql_version="10.11",
    php_image=None,
    nginx_image=None,
    mysql_root_password="root",
    mysql_database="app",
    mysql_user="app",
    mysql_password="app",
    web_root="./www",
    nginx_conf_dir="./nginx",
    mysql_data_dir="./mysql",
    expose_ports=True,
    network_name="lnmp-network",
):
    php_image = php_image or f"lnmp-php:{php_version}"
    nginx_image = nginx_image or "lnmp-nginx:latest"

    return f"""version: '3.8'

networks:
  {network_name}:
    driver: bridge

volumes:
  mysql_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: {os.path.abspath(mysql_data_dir) if os.path.isabs(mysql_data_dir) else mysql_data_dir}

services:
  php:
    image: {php_image}
    container_name: {project_name}-php
    restart: unless-stopped
    volumes:
      - {web_root}:/var/www/html:rw,cached
    networks:
      - {network_name}
    environment:
      - TZ=UTC
    healthcheck:
      test: ["CMD", "php-fpm", "-t"]
      interval: 30s
      timeout: 3s
      retries: 3
      start_period: 10s

  nginx:
    image: {nginx_image}
    container_name: {project_name}-nginx
    restart: unless-stopped
    depends_on:
      php:
        condition: service_healthy
    volumes:
      - {web_root}:/var/www/html:ro,cached
      - {nginx_conf_dir}/conf.d:/etc/nginx/conf.d:ro
    networks:
      - {network_name}
    {f'ports:' if expose_ports else ''}
      {f'- \"80:80\"' if expose_ports else ''}
      {f'- \"443:443\"' if expose_ports else ''}
    environment:
      - TZ=UTC
    healthcheck:
      test: ["CMD", "wget", "--spider", "http://127.0.0.1:80"]
      interval: 30s
      timeout: 3s
      retries: 3
      start_period: 10s

  mysql:
    image: mariadb:{mysql_version}
    container_name: {project_name}-mysql
    restart: unless-stopped
    volumes:
      - mysql_data:/var/lib/mysql
    networks:
      - {network_name}
    {f'ports:' if expose_ports else ''}
      {f'- \"127.0.0.1:3306:3306\"' if expose_ports else ''}
    environment:
      - TZ=UTC
      - MYSQL_ROOT_PASSWORD={mysql_root_password}
      - MYSQL_DATABASE={mysql_database}
      - MYSQL_USER={mysql_user}
      - MYSQL_PASSWORD={mysql_password}
    command:
      - --character-set-server=utf8mb4
      - --collation-server=utf8mb4_unicode_ci
      - --max-connections=200
    healthcheck:
      test: ["CMD", "healthcheck.sh", "--connect", "--innodb_initialized"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s
"""


def generate_docker_ignore():
    return """**/.git
**/.gitignore
**/__pycache__
**/*.pyc
**/*.pyo
**/.DS_Store
**/node_modules
**/vendor
**/*.log
**/tmp
**/mysql
**/www
"""


def generate_entrypoint_sh():
    return """#!/bin/bash
set -e

cd /var/www/html

if [ ! -f index.php ]; then
    echo "<?php phpinfo();" > index.php
    chown www-data:www-data index.php
fi

exec php-fpm -F
"""


def generate_readme_docker(project_name="lnmp"):
    return f"""# LNMP Docker Deployment

## Quick Start

```bash
# 1. Generate files
python3 docker_build.py generate --all

# 2. Build images
docker compose build

# 3. Start containers
docker compose up -d

# 4. Check status
docker compose ps

# 5. Test PHP
curl http://localhost
```

## Services

- **nginx**: Web server (port 80/443)
- **php**: PHP-FPM {DEFAULT_PHP_VERSION} (port 9000, internal)
- **mysql**: MariaDB {DEFAULT_MYSQL_VERSION} (port 3306, localhost only)

## Directory Structure

```
./
├── docker-compose.yml
├── php/
│   ├── Dockerfile
│   └── install_php.py
├── nginx/
│   ├── Dockerfile
│   ├── nginx.conf
│   └── conf.d/
│       └── default.conf
├── www/                    # Web root (mounted)
├── mysql/                  # MySQL data (mounted)
└── .dockerignore
```

## Default MySQL Credentials

- Root: root / root
- App: app / app
- Database: app

## Commands

```bash
# View logs
docker compose logs -f nginx php mysql

# Restart
docker compose restart

# Stop
docker compose down

# Stop and remove volumes
docker compose down -v

# Enter php container
docker exec -it {project_name}-php bash

# Enter mysql
docker exec -it {project_name}-mysql mysql -uroot -proot
```
"""


def create_directory_structure(output_dir):
    dirs = [
        output_dir,
        os.path.join(output_dir, "php"),
        os.path.join(output_dir, "nginx"),
        os.path.join(output_dir, "nginx", "conf.d"),
        os.path.join(output_dir, "www"),
        os.path.join(output_dir, "mysql"),
    ]
    for d in dirs:
        os.makedirs(d, exist_ok=True)
        log_info(f"Created directory: {d}")


def write_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    log_info(f"Generated: {path}")


def cmd_generate(args):
    output_dir = args.output_dir or "."

    create_directory_structure(output_dir)

    php_dockerfile = os.path.join(output_dir, "php", "Dockerfile")
    nginx_dockerfile = os.path.join(output_dir, "nginx", "Dockerfile")
    nginx_conf = os.path.join(output_dir, "nginx", "nginx.conf")
    default_conf = os.path.join(output_dir, "nginx", "conf.d", "default.conf")
    compose_file = os.path.join(output_dir, "docker-compose.yml")
    dockerignore = os.path.join(output_dir, ".dockerignore")
    readme = os.path.join(output_dir, "README_DOCKER.md")
    install_php_copy = os.path.join(output_dir, "php", "install_php.py")

    if args.all or args.php_dockerfile:
        write_file(php_dockerfile, generate_dockerfile_php(args.base_image, args.php_version, args.php_prefix))

    if args.all or args.nginx_dockerfile:
        write_file(nginx_dockerfile, generate_dockerfile_nginx(args.nginx_image))

    if args.all or args.nginx_conf:
        write_file(nginx_conf, generate_nginx_conf())
        write_file(default_conf, generate_default_site_conf())

    if args.all or args.compose:
        write_file(
            compose_file,
            generate_docker_compose(
                project_name=args.project,
                php_version=args.php_version,
                mysql_version=args.mysql_version,
                php_image=args.php_image,
                nginx_image=args.nginx_image_tag,
                mysql_root_password=args.mysql_root_password,
                mysql_database=args.mysql_database,
                mysql_user=args.mysql_user,
                mysql_password=args.mysql_password,
                web_root=args.web_root,
                nginx_conf_dir=args.nginx_conf_dir,
                mysql_data_dir=args.mysql_data_dir,
                expose_ports=not args.no_expose,
            ),
        )

    if args.all or args.dockerignore:
        write_file(dockerignore, generate_docker_ignore())

    if args.all or args.readme:
        write_file(readme, generate_readme_docker(args.project))

    if args.all:
        import shutil
        src_install_php = os.path.join(SCRIPT_DIR, "install_php.py")
        if os.path.exists(src_install_php) and not os.path.exists(install_php_copy):
            shutil.copy(src_install_php, install_php_copy)
            log_info(f"Copied: {install_php_copy}")

    log_info("Generation complete!")


def cmd_build(args):
    output_dir = args.output_dir or "."
    os.chdir(output_dir)

    if args.service:
        run_cmd(f"docker compose build {args.service}")
    else:
        run_cmd("docker compose build")

    log_info("Build complete!")


def cmd_up(args):
    output_dir = args.output_dir or "."
    os.chdir(output_dir)

    cmd = "docker compose up -d"
    if args.service:
        cmd += f" {args.service}"
    if args.build:
        cmd += " --build"
    if args.force_recreate:
        cmd += " --force-recreate"

    run_cmd(cmd)
    log_info("Containers started!")


def cmd_down(args):
    output_dir = args.output_dir or "."
    os.chdir(output_dir)

    cmd = "docker compose down"
    if args.volumes:
        cmd += " -v"
    if args.remove_orphans:
        cmd += " --remove-orphans"

    run_cmd(cmd)
    log_info("Containers stopped!")


def cmd_ps(args):
    output_dir = args.output_dir or "."
    os.chdir(output_dir)
    run_cmd("docker compose ps")


def cmd_logs(args):
    output_dir = args.output_dir or "."
    os.chdir(output_dir)

    cmd = "docker compose logs"
    if args.follow:
        cmd += " -f"
    if args.tail:
        cmd += f" --tail={args.tail}"
    if args.service:
        cmd += f" {args.service}"

    run_cmd(cmd)


def main():
    parser = argparse.ArgumentParser(description="LNMP Docker Deployment Generator")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    gen_parser = subparsers.add_parser("generate", help="Generate Docker files")
    gen_parser.add_argument("--output-dir", "-o", default=".", help="Output directory")
    gen_parser.add_argument("--project", default="lnmp", help="Project name")
    gen_parser.add_argument("--php-version", default=DEFAULT_PHP_VERSION, choices=PHP_VERSIONS, help="PHP version")
    gen_parser.add_argument("--php-prefix", default="/usr/local/php", help="PHP install prefix")
    gen_parser.add_argument("--base-image", default=DEFAULT_BASE_IMAGE, help="Base image for PHP")
    gen_parser.add_argument("--mysql-version", default=DEFAULT_MYSQL_VERSION, help="MariaDB version")
    gen_parser.add_argument("--nginx-image", default="nginx:alpine", help="Nginx base image")
    gen_parser.add_argument("--nginx-image-tag", default="lnmp-nginx:latest", help="Nginx image tag")
    gen_parser.add_argument("--php-image", help="PHP image tag override")
    gen_parser.add_argument("--mysql-root-password", default="root", help="MySQL root password")
    gen_parser.add_argument("--mysql-database", default="app", help="MySQL database")
    gen_parser.add_argument("--mysql-user", default="app", help="MySQL user")
    gen_parser.add_argument("--mysql-password", default="app", help="MySQL password")
    gen_parser.add_argument("--web-root", default="./www", help="Web root path")
    gen_parser.add_argument("--nginx-conf-dir", default="./nginx", help="Nginx config dir")
    gen_parser.add_argument("--mysql-data-dir", default="./mysql", help="MySQL data dir")
    gen_parser.add_argument("--no-expose", action="store_true", help="Do not expose ports to host")
    gen_parser.add_argument("--all", action="store_true", help="Generate all files")
    gen_parser.add_argument("--php-dockerfile", action="store_true", help="Generate PHP Dockerfile")
    gen_parser.add_argument("--nginx-dockerfile", action="store_true", help="Generate Nginx Dockerfile")
    gen_parser.add_argument("--nginx-conf", action="store_true", help="Generate Nginx config")
    gen_parser.add_argument("--compose", action="store_true", help="Generate docker-compose.yml")
    gen_parser.add_argument("--dockerignore", action="store_true", help="Generate .dockerignore")
    gen_parser.add_argument("--readme", action="store_true", help="Generate README")

    build_parser = subparsers.add_parser("build", help="Build images")
    build_parser.add_argument("--output-dir", "-o", default=".", help="Compose file directory")
    build_parser.add_argument("--service", help="Specific service to build")

    up_parser = subparsers.add_parser("up", help="Start containers")
    up_parser.add_argument("--output-dir", "-o", default=".", help="Compose file directory")
    up_parser.add_argument("--service", help="Specific service to start")
    up_parser.add_argument("--build", action="store_true", help="Build before starting")
    up_parser.add_argument("--force-recreate", action="store_true", help="Force recreate containers")

    down_parser = subparsers.add_parser("down", help="Stop and remove containers")
    down_parser.add_argument("--output-dir", "-o", default=".", help="Compose file directory")
    down_parser.add_argument("--volumes", "-v", action="store_true", help="Remove volumes")
    down_parser.add_argument("--remove-orphans", action="store_true", help="Remove orphaned containers")

    ps_parser = subparsers.add_parser("ps", help="List containers")
    ps_parser.add_argument("--output-dir", "-o", default=".", help="Compose file directory")

    logs_parser = subparsers.add_parser("logs", help="View logs")
    logs_parser.add_argument("--output-dir", "-o", default=".", help="Compose file directory")
    logs_parser.add_argument("--service", help="Specific service logs")
    logs_parser.add_argument("--follow", "-f", action="store_true", help="Follow logs")
    logs_parser.add_argument("--tail", type=int, default=100, help="Number of lines")

    args = parser.parse_args()

    if args.command == "generate":
        cmd_generate(args)
    elif args.command == "build":
        cmd_build(args)
    elif args.command == "up":
        cmd_up(args)
    elif args.command == "down":
        cmd_down(args)
    elif args.command == "ps":
        cmd_ps(args)
    elif args.command == "logs":
        cmd_logs(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
