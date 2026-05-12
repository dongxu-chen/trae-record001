#!/usr/bin/env python3
import subprocess
import os
import sys
import argparse
import json

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CHECK_SYS_SH = os.path.join(SCRIPT_DIR, "check_sys.sh")
INSTALL_PHP_PY = os.path.join(SCRIPT_DIR, "install_php.py")
CONFIG_NGINX_PY = os.path.join(SCRIPT_DIR, "config_nginx.py")
DOCKER_BUILD_PY = os.path.join(SCRIPT_DIR, "docker_build.py")
ROLLBACK_SH = os.path.join(SCRIPT_DIR, "rollback.sh")


def log_info(msg):
    print(f"\033[0;32m[INFO]\033[0m {msg}")


def log_warn(msg):
    print(f"\033[1;33m[WARN]\033[0m {msg}")


def log_error(msg):
    print(f"\033[0;31m[ERROR]\033[0m {msg}")


def log_step(step_num, msg):
    print(f"\n\033[1;36m[{step_num}] {msg}\033[0m")


def run_command(cmd, shell=True, capture_output=True, text=True, check=True):
    log_info(f"Running: {cmd}")
    try:
        result = subprocess.run(
            cmd,
            shell=shell,
            stdout=subprocess.PIPE if capture_output else None,
            stderr=subprocess.STDOUT if capture_output else None,
            text=text,
            check=check
        )
        if capture_output and result.stdout:
            print(result.stdout)
        return result
    except subprocess.CalledProcessError as e:
        log_error(f"Command failed with exit code {e.returncode}")
        if capture_output and e.stdout:
            print(e.stdout)
        raise


def check_python_version():
    if sys.version_info < (3, 6):
        log_error("Python 3.6+ is required")
        sys.exit(1)
    log_info(f"Python version: {sys.version.split()[0]}")


def parse_check_sys_output(output):
    info = {}
    for line in output.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            info[key.strip()] = value.strip()
    return info


def step_check_system():
    log_step(1, "System Check")

    if not os.path.exists(CHECK_SYS_SH):
        log_error(f"Script not found: {CHECK_SYS_SH}")
        sys.exit(1)

    os.chmod(CHECK_SYS_SH, 0o755)
    result = run_command(f"bash {CHECK_SYS_SH}")
    info = parse_check_sys_output(result.stdout)

    log_info("System info parsed:")
    for k, v in info.items():
        log_info(f"  {k} = {v}")

    return info


def step_install_dependencies(sys_info):
    log_step(2, "Installing Dependencies (Nginx, MySQL)")

    pm_update = sys_info.get("PM_UPDATE", "")
    pm_install = sys_info.get("PM_INSTALL", "")
    os_name = sys_info.get("OS_NAME", "")

    if not pm_install:
        log_warn("Package manager not detected, skipping dependency install")
        return

    if pm_update:
        run_command(pm_update, check=False)

    if os_name in ["ubuntu", "debian"]:
        packages = "nginx mariadb-server mariadb-client"
    else:
        packages = "nginx mariadb-server mariadb"

    try:
        run_command(f"{pm_install} {packages}")
    except subprocess.CalledProcessError:
        log_warn(f"Some packages may have failed to install, continuing...")

    log_info("Dependencies installed")


def step_install_php(sys_info, php_version, php_prefix, jobs):
    log_step(3, f"Installing PHP {php_version}")

    if not os.path.exists(INSTALL_PHP_PY):
        log_error(f"Script not found: {INSTALL_PHP_PY}")
        sys.exit(1)

    os_type = "debian" if sys_info.get("OS_NAME") in ["ubuntu", "debian"] else "rhel"
    pm_install = sys_info.get("PM_INSTALL", "")

    cmd = [
        sys.executable,
        INSTALL_PHP_PY,
        "--version", php_version,
        "--prefix", php_prefix,
        "--jobs", str(jobs),
        "--os-type", os_type,
    ]

    if pm_install:
        cmd.extend(["--pm-install", pm_install])

    run_command(" ".join(cmd), shell=True)
    log_info(f"PHP {php_version} installed to {php_prefix}")


def step_secure_mysql():
    log_step(4, "Securing MySQL (optional)")
    log_warn("MySQL security setup skipped (requires interactive input)")
    log_info("Manual steps:")
    log_info("  - Run: mysql_secure_installation")
    log_info("  - Set root password")
    log_info("  - Remove anonymous users")
    log_info("  - Disallow remote root login")


def step_start_services(sys_info, php_version):
    log_step(5, "Starting Services")

    os_name = sys_info.get("OS_NAME", "")

    if os_name in ["ubuntu", "debian"]:
        nginx_service = "nginx"
        mysql_service = "mariadb"
    else:
        nginx_service = "nginx"
        mysql_service = "mariadb"

    services = [nginx_service, mysql_service, f"php-fpm-{php_version}"]

    for service in services:
        try:
            run_command(f"systemctl enable {service}", check=False)
            run_command(f"systemctl restart {service}", check=False)
            log_info(f"Service {service} started")
        except Exception as e:
            log_warn(f"Failed to start {service}: {e}")


def step_configure_site(domain, root_dir, php_fpm):
    log_step(6, f"Configuring site: {domain}")

    if not os.path.exists(CONFIG_NGINX_PY):
        log_error(f"Script not found: {CONFIG_NGINX_PY}")
        sys.exit(1)

    cmd = [
        sys.executable,
        CONFIG_NGINX_PY,
        "create",
        "--domain", domain,
        "--root", root_dir,
        "--php-fpm", php_fpm,
        "--no-reload",
    ]

    run_command(" ".join(cmd), shell=True)
    log_info(f"Site {domain} configured")


def step_final_report(sys_info, php_version, php_prefix, domain, root_dir):
    log_step(7, "Deployment Summary")

    print("")
    log_info("LNMP deployment complete!")
    print("")
    log_info("System:")
    log_info(f"  OS: {sys_info.get('OS_NAME', 'unknown')} {sys_info.get('OS_VERSION', '')}")
    log_info(f"  Arch: {sys_info.get('ARCH', 'unknown')}")
    print("")
    log_info("Services:")
    log_info("  - Nginx: http://localhost")
    log_info("  - MySQL/MariaDB: port 3306")
    log_info(f"  - PHP {php_version}:")
    log_info(f"      Binary: {php_prefix}/bin/php")
    log_info(f"      FPM: {php_prefix}/sbin/php-fpm")
    log_info(f"      Service: php-fpm-{php_version}")
    print("")
    log_info("Site:")
    log_info(f"  Domain: {domain}")
    log_info(f"  Root: {root_dir}")
    print("")
    log_info("Commands:")
    log_info("  Check PHP version:")
    log_info(f"    {php_prefix}/bin/php -v")
    log_info("  Test PHP-FPM status:")
    log_info(f"    systemctl status php-fpm-{php_version}")
    log_info("  Test nginx status:")
    log_info("    nginx -t")
    log_info("    systemctl status nginx")
    print("")


def step_docker_generate(config):
    log_step(1, "Generating Docker files")

    if not os.path.exists(DOCKER_BUILD_PY):
        log_error(f"Script not found: {DOCKER_BUILD_PY}")
        sys.exit(1)

    output_dir = config.get("docker_output_dir", ".")

    cmd = [
        sys.executable,
        DOCKER_BUILD_PY,
        "generate",
        "--all",
        "--output-dir", output_dir,
        "--project", config.get("project", "lnmp"),
        "--php-version", config.get("php_version", "8.2"),
        "--mysql-version", config.get("mysql_version", "10.11"),
        "--php-prefix", config.get("php_prefix", "/usr/local/php"),
    ]

    if config.get("mysql_root_password"):
        cmd.extend(["--mysql-root-password", config["mysql_root_password"]])
    if config.get("mysql_database"):
        cmd.extend(["--mysql-database", config["mysql_database"]])
    if config.get("mysql_user"):
        cmd.extend(["--mysql-user", config["mysql_user"]])
    if config.get("mysql_password"):
        cmd.extend(["--mysql-password", config["mysql_password"]])
    if config.get("no_expose_ports"):
        cmd.append("--no-expose")

    run_command(" ".join(cmd), shell=True)
    log_info(f"Docker files generated in: {os.path.abspath(output_dir)}")


def step_docker_build(config):
    log_step(2, "Building Docker images")

    output_dir = config.get("docker_output_dir", ".")

    cmd = [
        sys.executable,
        DOCKER_BUILD_PY,
        "build",
        "--output-dir", output_dir,
    ]

    if config.get("docker_service"):
        cmd.extend(["--service", config["docker_service"]])

    run_command(" ".join(cmd), shell=True)
    log_info("Docker build complete")


def step_docker_up(config):
    log_step(3, "Starting Docker containers")

    output_dir = config.get("docker_output_dir", ".")

    cmd = [
        sys.executable,
        DOCKER_BUILD_PY,
        "up",
        "--output-dir", output_dir,
    ]

    if config.get("docker_build_first"):
        cmd.append("--build")
    if config.get("docker_force_recreate"):
        cmd.append("--force-recreate")

    run_command(" ".join(cmd), shell=True)
    log_info("Docker containers started")


def step_docker_status(config):
    log_step(4, "Checking Docker status")

    output_dir = config.get("docker_output_dir", ".")
    cmd = [sys.executable, DOCKER_BUILD_PY, "ps", "--output-dir", output_dir]
    run_command(" ".join(cmd), shell=True)


def step_docker_final_report(config):
    log_step(5, "Docker Deployment Summary")

    output_dir = os.path.abspath(config.get("docker_output_dir", "."))

    print("")
    log_info("LNMP Docker deployment complete!")
    print("")
    log_info("Services:")
    log_info("  - nginx: http://localhost (port 80)")
    log_info("  - php-fpm: internal port 9000")
    log_info("  - mysql: localhost:3306")
    print("")
    log_info("Directories:")
    log_info(f"  Web root: {output_dir}/www")
    log_info(f"  MySQL data: {output_dir}/mysql")
    log_info(f"  Nginx config: {output_dir}/nginx/conf.d")
    print("")
    log_info("Docker commands:")
    log_info(f"  cd {output_dir}")
    log_info("  docker compose ps          - List containers")
    log_info("  docker compose logs -f     - View logs")
    log_info("  docker compose down        - Stop containers")
    log_info("  docker compose down -v     - Stop and remove volumes")
    log_info("  docker exec -it lnmp-php bash")
    log_info("  docker exec -it lnmp-mysql mysql -uroot -proot")
    print("")
    log_info("Test PHP:")
    log_info("  curl http://localhost")
    print("")


def cmd_backup(args):
    log_info("Creating backup before deployment...")

    if not os.path.exists(ROLLBACK_SH):
        log_error(f"Script not found: {ROLLBACK_SH}")
        return

    os.chmod(ROLLBACK_SH, 0o755)

    if getattr(args, "docker", False):
        env = os.environ.copy()
        if args.docker_output_dir:
            env["DOCKER_COMPOSE_DIR"] = args.docker_output_dir
        run_command(f"bash {ROLLBACK_SH} docker-backup", env=env, shell=True)
    else:
        env = os.environ.copy()
        if args.php_prefix:
            env["PHP_PREFIX"] = args.php_prefix
        run_command(f"bash {ROLLBACK_SH} backup", env=env, shell=True)


def cmd_rollback(args):
    log_info("Starting rollback...")

    if not os.path.exists(ROLLBACK_SH):
        log_error(f"Script not found: {ROLLBACK_SH}")
        return

    os.chmod(ROLLBACK_SH, 0o755)

    if getattr(args, "docker", False):
        env = os.environ.copy()
        if args.docker_output_dir:
            env["DOCKER_COMPOSE_DIR"] = args.docker_output_dir
        run_command(f"bash {ROLLBACK_SH} docker-rollback", env=env, shell=True)
    else:
        backup_id = getattr(args, "backup_id", None)
        cmd = f"bash {ROLLBACK_SH} restore {backup_id}" if backup_id else f"bash {ROLLBACK_SH} restore"
        env = os.environ.copy()
        if args.php_prefix:
            env["PHP_PREFIX"] = args.php_prefix
        run_command(cmd, env=env, shell=True)


def cmd_docker(args):
    config = vars(args)
    output_dir = args.output_dir or "."

    print("")
    print("=" * 50)
    print("  LNMP Docker Deployment")
    print("=" * 50)
    print("")

    if args.action == "generate":
        step_docker_generate(config)
    elif args.action == "build":
        step_docker_build(config)
    elif args.action == "up":
        step_docker_up(config)
    elif args.action == "ps":
        step_docker_status(config)
    elif args.action == "deploy":
        step_docker_generate(config)
        step_docker_build(config)
        step_docker_up(config)
        step_docker_status(config)
        step_docker_final_report(config)
    else:
        log_error(f"Unknown docker action: {args.action}")


def load_config(config_file):
    if not os.path.exists(config_file):
        return {}
    with open(config_file, "r") as f:
        return json.load(f)


def save_config(config_file, config):
    with open(config_file, "w") as f:
        json.dump(config, f, indent=2)
    log_info(f"Config saved: {config_file}")


def interactive_mode():
    log_info("Interactive mode")

    config = {}

    print("\nDeployment mode:")
    print("  [1] Bare-metal (direct install)")
    print("  [2] Docker (containerized)")
    mode_choice = input("Choice [1]: ").strip() or "1"
    config["_mode"] = "docker" if mode_choice == "2" else "baremetal"

    if config["_mode"] == "docker":
        print("\nSelect PHP version:")
        print("  [1] 7.4")
        print("  [2] 8.0")
        print("  [3] 8.1")
        print("  [4] 8.2 (default)")
        print("  [5] 8.3")
        choice = input("Choice [4]: ").strip() or "4"
        versions = {"1": "7.4", "2": "8.0", "3": "8.1", "4": "8.2", "5": "8.3"}
        config["php_version"] = versions.get(choice, "8.2")

        config["project"] = input("Project name [lnmp]: ").strip() or "lnmp"
        config["docker_output_dir"] = input("Output directory [.]: ").strip() or "."
        config["mysql_root_password"] = input("MySQL root password [root]: ").strip() or "root"
        config["mysql_database"] = input("MySQL database [app]: ").strip() or "app"
        config["mysql_user"] = input("MySQL user [app]: ").strip() or "app"
        config["mysql_password"] = input("MySQL password [app]: ").strip() or "app"
    else:
        print("\nSelect PHP version:")
        print("  [1] 7.4")
        print("  [2] 8.0")
        print("  [3] 8.1")
        print("  [4] 8.2 (default)")
        print("  [5] 8.3")
        choice = input("Choice [4]: ").strip() or "4"
        versions = {"1": "7.4", "2": "8.0", "3": "8.1", "4": "8.2", "5": "8.3"}
        config["php_version"] = versions.get(choice, "8.2")

        config["php_prefix"] = input("PHP install prefix [/usr/local/php]: ").strip() or "/usr/local/php"

        import multiprocessing
        default_jobs = str(multiprocessing.cpu_count())
        config["jobs"] = int(input(f"Make jobs [{default_jobs}]: ").strip() or default_jobs)

        config["domain"] = input("Site domain [example.com]: ").strip() or "example.com"
        config["root_dir"] = input(f"Document root [/var/www/{config['domain']}]: ").strip() or f"/var/www/{config['domain']}"
        config["php_fpm"] = input("PHP-FPM address [127.0.0.1:9000]: ").strip() or "127.0.0.1:9000"

    return config


def cmd_baremetal_deploy(args):
    check_python_version()

    if args.interactive:
        config = interactive_mode()
    elif args.config:
        config = load_config(args.config)
    else:
        config = {
            "php_version": args.php_version,
            "php_prefix": args.php_prefix,
            "jobs": args.jobs,
            "domain": args.domain,
            "root_dir": args.root_dir or f"/var/www/{args.domain}",
            "php_fpm": args.php_fpm,
        }

    if args.save_config:
        save_config(args.save_config, config)
        return

    print("")
    print("=" * 50)
    print("  LNMP Bare-metal Deployment")
    print("=" * 50)
    print("")

    if args.backup:
        cmd_backup(args)

    sys_info = {}
    if not args.skip_check:
        sys_info = step_check_system()

    if not args.skip_deps:
        step_install_dependencies(sys_info)

    if not args.skip_php:
        step_install_php(
            sys_info,
            config["php_version"],
            config["php_prefix"],
            config["jobs"],
        )

    step_secure_mysql()

    if not args.skip_php:
        step_start_services(sys_info, config["php_version"])

    if not args.skip_site:
        step_configure_site(config["domain"], config["root_dir"], config["php_fpm"])

    step_final_report(
        sys_info,
        config["php_version"],
        config["php_prefix"],
        config["domain"],
        config["root_dir"],
    )


def main():
    parser = argparse.ArgumentParser(description="LNMP Automated Deployment Script")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    baremetal_parser = subparsers.add_parser("deploy", help="Bare-metal deployment (default)")
    baremetal_parser.add_argument("--config", "-c", help="Config file path")
    baremetal_parser.add_argument("--php-version", default="8.2", help="PHP version (7.4, 8.0, 8.1, 8.2, 8.3)")
    baremetal_parser.add_argument("--php-prefix", default="/usr/local/php", help="PHP install prefix")
    baremetal_parser.add_argument("--jobs", "-j", type=int, default=2, help="Make jobs")
    baremetal_parser.add_argument("--domain", default="example.com", help="Default site domain")
    baremetal_parser.add_argument("--root-dir", help="Site document root")
    baremetal_parser.add_argument("--php-fpm", default="127.0.0.1:9000", help="PHP-FPM address")
    baremetal_parser.add_argument("--interactive", "-i", action="store_true", help="Interactive mode")
    baremetal_parser.add_argument("--backup", action="store_true", help="Create backup before deployment")
    baremetal_parser.add_argument("--skip-check", action="store_true", help="Skip system check")
    baremetal_parser.add_argument("--skip-deps", action="store_true", help="Skip nginx/mysql install")
    baremetal_parser.add_argument("--skip-php", action="store_true", help="Skip PHP install")
    baremetal_parser.add_argument("--skip-site", action="store_true", help="Skip site config")
    baremetal_parser.add_argument("--save-config", help="Save config to file")

    docker_parser = subparsers.add_parser("docker", help="Docker deployment")
    docker_parser.add_argument("action", nargs="?", default="deploy",
                               choices=["generate", "build", "up", "ps", "deploy"],
                               help="Action: generate (files only), build (images), up (start), ps (status), deploy (all)")
    docker_parser.add_argument("--output-dir", "-o", default=".", help="Output directory")
    docker_parser.add_argument("--project", default="lnmp", help="Project name")
    docker_parser.add_argument("--php-version", default="8.2", help="PHP version")
    docker_parser.add_argument("--php-prefix", default="/usr/local/php", help="PHP install prefix in container")
    docker_parser.add_argument("--mysql-version", default="10.11", help="MariaDB version")
    docker_parser.add_argument("--mysql-root-password", default="root", help="MySQL root password")
    docker_parser.add_argument("--mysql-database", default="app", help="MySQL database")
    docker_parser.add_argument("--mysql-user", default="app", help="MySQL user")
    docker_parser.add_argument("--mysql-password", default="app", help="MySQL password")
    docker_parser.add_argument("--no-expose-ports", action="store_true", help="Do not expose ports to host")
    docker_parser.add_argument("--service", dest="docker_service", help="Specific service for build")
    docker_parser.add_argument("--build", dest="docker_build_first", action="store_true", help="Build before starting")
    docker_parser.add_argument("--force-recreate", dest="docker_force_recreate", action="store_true", help="Force recreate containers")

    backup_parser = subparsers.add_parser("backup", help="Create backup")
    backup_parser.add_argument("--docker", action="store_true", help="Docker mode backup")
    backup_parser.add_argument("--docker-output-dir", default=".", help="Docker compose directory")
    backup_parser.add_argument("--php-prefix", default="/usr/local/php", help="PHP prefix for bare-metal")

    rollback_parser = subparsers.add_parser("rollback", help="Rollback to previous backup")
    rollback_parser.add_argument("--docker", action="store_true", help="Docker mode rollback")
    rollback_parser.add_argument("--docker-output-dir", default=".", help="Docker compose directory")
    rollback_parser.add_argument("--php-prefix", default="/usr/local/php", help="PHP prefix for bare-metal")
    rollback_parser.add_argument("--backup-id", help="Backup ID to restore (bare-metal)")
    
    args = parser.parse_args()

    if args.command == "docker":
        cmd_docker(args)
    elif args.command == "backup":
        cmd_backup(args)
    elif args.command == "rollback":
        cmd_rollback(args)
    elif args.command == "deploy" or args.command is None:
        cmd_baremetal_deploy(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
