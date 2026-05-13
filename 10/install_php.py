#!/usr/bin/env python3
import subprocess
import os
import sys
import argparse
import shutil

PHP_VERSIONS = {
    "7.4": "https://www.php.net/distributions/php-7.4.33.tar.gz",
    "8.0": "https://www.php.net/distributions/php-8.0.30.tar.gz",
    "8.1": "https://www.php.net/distributions/php-8.1.29.tar.gz",
    "8.2": "https://www.php.net/distributions/php-8.2.20.tar.gz",
    "8.3": "https://www.php.net/distributions/php-8.3.8.tar.gz",
}

DEFAULT_PREFIX = "/usr/local/php"
DEFAULT_SRC_DIR = "/usr/local/src"

DEPS_DEBIAN = [
    "build-essential",
    "autoconf",
    "libtool",
    "re2c",
    "pkg-config",
    "bison",
    "flex",
    "libxml2-dev",
    "libssl-dev",
    "libbz2-dev",
    "libcurl4-openssl-dev",
    "libpng-dev",
    "libjpeg-dev",
    "libfreetype6-dev",
    "libzip-dev",
    "libonig-dev",
    "libreadline-dev",
    "zlib1g-dev",
    "libsqlite3-dev",
]

DEPS_RHEL = [
    "gcc",
    "gcc-c++",
    "make",
    "autoconf",
    "libtool",
    "re2c",
    "bison",
    "flex",
    "pkgconfig",
    "libxml2-devel",
    "openssl-devel",
    "bzip2-devel",
    "libcurl-devel",
    "libpng-devel",
    "libjpeg-devel",
    "freetype-devel",
    "libzip-devel",
    "oniguruma-devel",
    "readline-devel",
    "zlib-devel",
    "sqlite-devel",
]


def log_info(msg):
    print(f"\033[0;32m[INFO]\033[0m {msg}")


def log_warn(msg):
    print(f"\033[1;33m[WARN]\033[0m {msg}")


def log_error(msg):
    print(f"\033[0;31m[ERROR]\033[0m {msg}")


def run_cmd(cmd, shell=True, check=True, retry=0, retry_delay=5):
    log_info(f"Executing: {cmd}")
    last_exception = None

    for attempt in range(retry + 1):
        if attempt > 0:
            log_warn(f"Retry {attempt}/{retry} after {retry_delay}s...")
            import time
            time.sleep(retry_delay)

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
            last_exception = e
            if attempt < retry:
                log_warn(f"Attempt {attempt + 1} failed, will retry")
            else:
                log_error(f"Command failed after {retry + 1} attempts: {cmd}")
                if e.stdout:
                    print(e.stdout)
                raise

    if last_exception:
        raise last_exception


def detect_os():
    if os.path.exists("/etc/debian_version"):
        return "debian"
    elif any(os.path.exists(f) for f in ["/etc/redhat-release", "/etc/rocky-release", "/etc/almalinux-release"]):
        return "rhel"
    return "unknown"


def install_dependencies(os_type, pm_install):
    log_info("Installing dependencies...")
    if os_type == "debian":
        deps = DEPS_DEBIAN
    elif os_type == "rhel":
        deps = DEPS_RHEL
    else:
        log_error("Unsupported OS for dependency installation")
        sys.exit(1)

    deps_str = " ".join(deps)
    run_cmd(f"{pm_install} {deps_str}")


def download_php(version, src_dir):
    if version not in PHP_VERSIONS:
        log_error(f"Unsupported PHP version: {version}")
        sys.exit(1)

    url = PHP_VERSIONS[version]
    tarball = os.path.basename(url)
    tarball_path = os.path.join(src_dir, tarball)
    extract_dir = os.path.join(src_dir, tarball.replace(".tar.gz", ""))

    os.makedirs(src_dir, exist_ok=True)

    if os.path.exists(extract_dir):
        log_warn(f"Source directory exists: {extract_dir}, reusing")
        return extract_dir

    if not os.path.exists(tarball_path):
        log_info(f"Downloading PHP {version}...")
        run_cmd(f"wget -t 3 -T 30 -c -O {tarball_path} {url}", retry=2, retry_delay=10)

    log_info(f"Extracting {tarball}...")
    run_cmd(f"tar -xzf {tarball_path} -C {src_dir}")

    return extract_dir


def get_configure_options(prefix, fpm_user="www-data", fpm_group="www-data"):
    return [
        f"--prefix={prefix}",
        "--enable-fpm",
        f"--with-fpm-user={fpm_user}",
        f"--with-fpm-group={fpm_group}",
        "--enable-mysqlnd",
        "--with-mysqli=mysqlnd",
        "--with-pdo-mysql=mysqlnd",
        "--enable-mbstring",
        "--enable-bcmath",
        "--with-zlib",
        "--with-bz2",
        "--enable-exif",
        "--with-openssl",
        "--with-curl",
        "--enable-gd",
        "--with-jpeg",
        "--with-freetype",
        "--enable-soap",
        "--with-xmlrpc",
        "--with-xsl",
        "--enable-intl",
        "--enable-pcntl",
        "--enable-sockets",
        "--with-readline",
        "--enable-sysvmsg",
        "--enable-sysvsem",
        "--enable-sysvshm",
        "--with-pear",
        "--with-zip",
        "--enable-opcache",
    ]


def compile_php(src_dir, prefix, jobs, fpm_user="www-data", fpm_group="www-data"):
    old_cwd = os.getcwd()
    try:
        os.chdir(src_dir)
        
        configure_opts = get_configure_options(prefix, fpm_user, fpm_group)
        configure_cmd = "./configure " + " ".join(configure_opts)
        
        log_info("Running configure...")
        run_cmd(configure_cmd)
        
        log_info(f"Compiling with {jobs} jobs...")
        run_cmd(f"make -j{jobs}")
        
        log_info("Installing...")
        run_cmd("make install")
        
        return True
    finally:
        os.chdir(old_cwd)


def setup_php_files(prefix, version):
    etc_dir = os.path.join(prefix, "etc")
    php_ini_prod = os.path.join(prefix, "lib", "php.ini-production")
    php_ini = os.path.join(prefix, "lib", "php.ini")
    fpm_conf = os.path.join(etc_dir, "php-fpm.conf")
    www_conf = os.path.join(etc_dir, "php-fpm.d", "www.conf")

    if os.path.exists(php_ini_prod) and not os.path.exists(php_ini):
        shutil.copy(php_ini_prod, php_ini)
        log_info(f"Copied php.ini to {php_ini}")

    if not os.path.exists(fpm_conf):
        sample = f"{fpm_conf}.default"
        if os.path.exists(sample):
            shutil.copy(sample, fpm_conf)
            log_info(f"Copied php-fpm.conf")

    if not os.path.exists(www_conf):
        sample = f"{www_conf}.default"
        if os.path.exists(sample):
            shutil.copy(sample, www_conf)
            log_info(f"Copied www.conf")

    return php_ini, fpm_conf


def create_systemd_service(prefix, version, skip_systemd=False):
    php_fpm_bin = os.path.join(prefix, "sbin", "php-fpm")
    php_fpm_conf = os.path.join(prefix, "etc", "php-fpm.conf")
    pid_file = os.path.join(prefix, "var", "run", "php-fpm.pid")

    if skip_systemd:
        log_info("Skipping systemd service creation (container mode)")
        return None

    service_content = f"""[Unit]
Description=The PHP FastCGI Process Manager
After=syslog.target network.target

[Service]
Type=forking
PIDFile={pid_file}
ExecStart={php_fpm_bin} --fpm-config {php_fpm_conf}
ExecReload=/bin/kill -USR2 $MAINPID
PrivateTmp=true

[Install]
WantedBy=multi-user.target
"""

    service_path = f"/etc/systemd/system/php-fpm-{version}.service"
    with open(service_path, "w") as f:
        f.write(service_content)
    
    log_info(f"Created systemd service: {service_path}")
    run_cmd("systemctl daemon-reload", check=False)
    return service_path


def main():
    parser = argparse.ArgumentParser(description="Compile and install PHP")
    parser.add_argument("--version", "-v", default="8.2", choices=PHP_VERSIONS.keys(), help="PHP version")
    parser.add_argument("--prefix", "-p", default=DEFAULT_PREFIX, help="Installation prefix")
    parser.add_argument("--src-dir", default=DEFAULT_SRC_DIR, help="Source directory")
    parser.add_argument("--jobs", "-j", type=int, default=2, help="Make jobs")
    parser.add_argument("--os-type", help="OS type (debian/rhel)")
    parser.add_argument("--pm-install", help="Package manager install command")
    parser.add_argument("--skip-deps", action="store_true", help="Skip dependency installation")
    parser.add_argument("--docker", action="store_true", help="Docker container mode")
    parser.add_argument("--fpm-user", default="www-data", help="PHP-FPM user")
    parser.add_argument("--fpm-group", default="www-data", help="PHP-FPM group")
    parser.add_argument("--skip-systemd", action="store_true", help="Skip systemd service creation")
    
    args = parser.parse_args()

    os_type = args.os_type or detect_os()
    if os_type == "unknown":
        log_error("Could not detect OS type")
        sys.exit(1)

    skip_systemd = args.skip_systemd or args.docker

    if not args.skip_deps and args.pm_install:
        install_dependencies(os_type, args.pm_install)
    elif not args.skip_deps:
        log_warn("Skipping dependency installation (no pm-install provided)")

    src_dir = download_php(args.version, args.src_dir)
    prefix = args.prefix

    log_info(f"Installing PHP {args.version} to {prefix}")
    compile_php(src_dir, prefix, args.jobs, args.fpm_user, args.fpm_group)

    setup_php_files(prefix, args.version)
    create_systemd_service(prefix, args.version, skip_systemd)

    log_info(f"PHP {args.version} installation complete!")
    log_info(f"  Prefix: {prefix}")
    log_info(f"  Binary: {prefix}/bin/php")
    log_info(f"  FPM: {prefix}/sbin/php-fpm")
    if not skip_systemd:
        log_info(f"  Service: php-fpm-{args.version}")


if __name__ == "__main__":
    main()
