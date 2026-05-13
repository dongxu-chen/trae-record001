#!/bin/bash

RED_COLOR='\033[0;31m'
GREEN_COLOR='\033[0;32m'
YELLOW_COLOR='\033[1;33m'
PLAIN='\033[0m'

log_info() {
    echo -e "${GREEN_COLOR}[INFO]${PLAIN} $1"
}

log_warn() {
    echo -e "${YELLOW_COLOR}[WARN]${PLAIN} $1"
}

log_error() {
    echo -e "${RED_COLOR}[ERROR]${PLAIN} $1"
}

check_root() {
    if [ "$EUID" -ne 0 ]; then
        log_error "Please run as root"
        exit 1
    fi
    log_info "Root privilege checked"
}

check_os() {
    if [ -f /etc/os-release ]; then
        OS_NAME=$(grep -E '^ID=' /etc/os-release | cut -d= -f2 | tr -d '"')
        OS_VERSION=$(grep -E '^VERSION_ID=' /etc/os-release | cut -d= -f2 | tr -d '"')
        OS_PRETTY=$(grep -E '^PRETTY_NAME=' /etc/os-release | cut -d= -f2 | tr -d '"')

        if [ -z "$OS_VERSION" ] && [ -f /etc/debian_version ]; then
            OS_VERSION=$(cat /etc/debian_version)
        fi
    elif [ -f /etc/redhat-release ]; then
        OS_NAME="centos"
        OS_VERSION=$(cat /etc/redhat-release | grep -oE '[0-9]+\.[0-9]+' | head -1)
        OS_PRETTY=$(cat /etc/redhat-release)
    elif [ -f /etc/debian_version ]; then
        OS_NAME="debian"
        OS_VERSION=$(cat /etc/debian_version)
        OS_PRETTY="Debian $OS_VERSION"
    else
        log_error "Unsupported OS"
        exit 1
    fi

    case $OS_NAME in
        ubuntu|debian)
            PM="apt"
            PM_UPDATE="apt-get update"
            PM_INSTALL="apt-get install -y"
            ;;
        centos|rhel|rocky|almalinux)
            PM="yum"
            if command -v dnf >/dev/null 2>&1; then
                PM="dnf"
            fi
            PM_UPDATE="$PM makecache"
            PM_INSTALL="$PM install -y"
            ;;
        *)
            log_error "Unsupported package manager for $OS_NAME"
            exit 1
            ;;
    esac

    log_info "Detected OS: $OS_PRETTY"
    log_info "Package manager: $PM"

    export OS_NAME
    export OS_VERSION
    export PM
    export PM_UPDATE
    export PM_INSTALL
}

check_mem() {
    TOTAL_MEM=$(free -m | awk '/^Mem:/{print $2}')
    log_info "Total memory: ${TOTAL_MEM}MB"
    
    if [ "$TOTAL_MEM" -lt 1024 ]; then
        log_warn "Memory less than 1GB, compilation may be slow"
    fi
}

check_arch() {
    ARCH=$(uname -m)
    log_info "Architecture: $ARCH"
    export ARCH
}

check_port() {
    local port=$1
    local service=$2
    if netstat -tulpn 2>/dev/null | grep -q ":${port} " || ss -tulpn 2>/dev/null | grep -q ":${port} "; then
        log_warn "Port $port is already in use ($service)"
    else
        log_info "Port $port is available ($service)"
    fi
}

check_installed() {
    if command -v nginx >/dev/null 2>&1; then
        log_warn "Nginx is already installed"
    else
        log_info "Nginx not installed"
    fi

    if command -v mysql >/dev/null 2>&1 || command -v mariadb >/dev/null 2>&1; then
        log_warn "MySQL/MariaDB is already installed"
    else
        log_info "MySQL/MariaDB not installed"
    fi

    if command -v php >/dev/null 2>&1; then
        PHP_VER=$(php -v 2>/dev/null | head -1 | grep -oE 'PHP [0-9]+\.[0-9]+')
        log_warn "PHP is already installed: $PHP_VER"
    else
        log_info "PHP not installed"
    fi
}

run_all_checks() {
    log_info "=================================="
    log_info "  System Check Starting"
    log_info "=================================="
    
    check_root
    check_os
    check_arch
    check_mem
    check_installed
    check_port 80 "HTTP"
    check_port 443 "HTTPS"
    check_port 3306 "MySQL"
    check_port 9000 "PHP-FPM"
    
    log_info "=================================="
    log_info "  System Check Completed"
    log_info "=================================="

    echo "OS_NAME=$OS_NAME"
    echo "OS_VERSION=$OS_VERSION"
    echo "PM=$PM"
    echo "PM_UPDATE=$PM_UPDATE"
    echo "PM_INSTALL=$PM_INSTALL"
    echo "ARCH=$ARCH"
}

if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    run_all_checks
fi
