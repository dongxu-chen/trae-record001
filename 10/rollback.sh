#!/bin/bash

RED_COLOR='\033[0;31m'
GREEN_COLOR='\033[0;32m'
YELLOW_COLOR='\033[1;33m'
BLUE_COLOR='\033[1;34m'
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

log_step() {
    echo -e "\n${BLUE_COLOR}[$1]${PLAIN} $2"
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/lnmp}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"

PHP_PREFIX="${PHP_PREFIX:-/usr/local/php}"
NGINX_CONF_DIR="${NGINX_CONF_DIR:-/etc/nginx}"
MYSQL_DATA_DIR="${MYSQL_DATA_DIR:-/var/lib/mysql}"
WEB_ROOT="${WEB_ROOT:-/var/www}"

DOCKER_MODE=0
DOCKER_COMPOSE_DIR="${DOCKER_COMPOSE_DIR:-.}"

show_usage() {
    cat << EOF
LNMP Deployment Rollback Script

Usage:
  $0 backup              Create a backup before changes
  $0 list                List available backups
  $0 restore <backup>    Restore from a backup
  $0 docker-backup       Backup docker volumes and images
  $0 docker-restore      Restore docker deployment
  $0 docker-rollback     Rollback docker to previous version
  $0 help                Show this help

Environment Variables:
  BACKUP_DIR          Backup directory (default: /var/backups/lnmp)
  PHP_PREFIX          PHP install prefix (default: /usr/local/php)
  NGINX_CONF_DIR      Nginx config directory (default: /etc/nginx)
  MYSQL_DATA_DIR      MySQL data directory (default: /var/lib/mysql)
  WEB_ROOT            Web root (default: /var/www)
  DOCKER_COMPOSE_DIR  Docker compose directory (default: .)

Examples:
  $0 backup
  $0 list
  $0 restore 20240512_120000
  $0 docker-backup
  $0 docker-rollback
EOF
}

check_root() {
    if [ "$EUID" -ne 0 ] && [ "$DOCKER_MODE" -eq 0 ]; then
        log_error "Please run as root for bare-metal operations"
        return 1
    fi
    return 0
}

check_tools() {
    local tools=("tar" "gzip")
    for tool in "${tools[@]}"; do
        if ! command -v "$tool" >/dev/null 2>&1; then
            log_error "Required tool not found: $tool"
            exit 1
        fi
    done
}

init_backup_dir() {
    mkdir -p "$BACKUP_DIR"
    if [ ! -w "$BACKUP_DIR" ]; then
        log_error "Cannot write to backup directory: $BACKUP_DIR"
        exit 1
    fi
    log_info "Using backup directory: $BACKUP_DIR"
}

create_backup_name() {
    local prefix="$1"
    local name="${prefix}_${TIMESTAMP}"
    echo "$name"
}

backup_php() {
    log_step "1" "Backing up PHP"
    
    if [ ! -d "$PHP_PREFIX" ]; then
        log_warn "PHP prefix not found: $PHP_PREFIX, skipping"
        return 0
    fi

    local backup_name="$(create_backup_name php)"
    local backup_path="$BACKUP_DIR/${backup_name}.tar.gz"

    log_info "Backing up PHP from $PHP_PREFIX"
    tar -czf "$backup_path" -C "$(dirname "$PHP_PREFIX")" "$(basename "$PHP_PREFIX")" 2>/dev/null
    
    if [ $? -eq 0 ]; then
        log_info "PHP backup created: $backup_path"
        echo "$backup_name" > "$BACKUP_DIR/.last_php_backup"
    else
        log_error "PHP backup failed"
        return 1
    fi
}

backup_nginx() {
    log_step "2" "Backing up Nginx"
    
    if [ ! -d "$NGINX_CONF_DIR" ]; then
        log_warn "Nginx config not found: $NGINX_CONF_DIR, skipping"
        return 0
    fi

    local backup_name="$(create_backup_name nginx)"
    local backup_path="$BACKUP_DIR/${backup_name}.tar.gz"

    log_info "Backing up nginx config from $NGINX_CONF_DIR"
    tar -czf "$backup_path" -C "$(dirname "$NGINX_CONF_DIR")" "$(basename "$NGINX_CONF_DIR")" 2>/dev/null
    
    if [ $? -eq 0 ]; then
        log_info "Nginx backup created: $backup_path"
        echo "$backup_name" > "$BACKUP_DIR/.last_nginx_backup"
    else
        log_error "Nginx backup failed"
        return 1
    fi
}

backup_web() {
    log_step "3" "Backing up Web Root"
    
    if [ ! -d "$WEB_ROOT" ]; then
        log_warn "Web root not found: $WEB_ROOT, skipping"
        return 0
    fi

    local backup_name="$(create_backup_name web)"
    local backup_path="$BACKUP_DIR/${backup_name}.tar.gz"

    log_info "Backing up web root from $WEB_ROOT"
    tar -czf "$backup_path" -C "$(dirname "$WEB_ROOT")" "$(basename "$WEB_ROOT")" 2>/dev/null
    
    if [ $? -eq 0 ]; then
        log_info "Web backup created: $backup_path"
        echo "$backup_name" > "$BACKUP_DIR/.last_web_backup"
    else
        log_error "Web backup failed"
        return 1
    fi
}

backup_mysql() {
    log_step "4" "Backing up MySQL"
    
    if ! command -v mysqldump >/dev/null 2>&1; then
        log_warn "mysqldump not found, skipping MySQL backup"
        return 0
    fi

    local backup_name="$(create_backup_name mysql)"
    local backup_path="$BACKUP_DIR/${backup_name}.sql.gz"

    log_info "Backing up all databases"
    
    if [ -n "$MYSQL_ROOT_PASSWORD" ]; then
        mysqldump -uroot -p"$MYSQL_ROOT_PASSWORD" --all-databases --single-transaction 2>/dev/null | gzip > "$backup_path"
    else
        mysqldump -uroot --all-databases --single-transaction 2>/dev/null | gzip > "$backup_path"
    fi
    
    if [ $? -eq 0 ] && [ -s "$backup_path" ]; then
        log_info "MySQL backup created: $backup_path"
        echo "$backup_name" > "$BACKUP_DIR/.last_mysql_backup"
    else
        log_warn "MySQL backup failed or empty (may need password)"
        rm -f "$backup_path"
    fi
}

cmd_backup() {
    log_info "=== LNMP Backup Started ==="
    log_info "Timestamp: $TIMESTAMP"
    
    check_root || exit 1
    check_tools
    init_backup_dir

    backup_php
    backup_nginx
    backup_web
    backup_mysql

    local manifest="$BACKUP_DIR/manifest_${TIMESTAMP}.json"
    cat > "$manifest" << EOF
{
    "timestamp": "$TIMESTAMP",
    "date": "$(date)",
    "php_prefix": "$PHP_PREFIX",
    "nginx_conf": "$NGINX_CONF_DIR",
    "web_root": "$WEB_ROOT",
    "mysql_data": "$MYSQL_DATA_DIR"
}
EOF

    log_info ""
    log_info "=== Backup Complete ==="
    log_info "Backup ID: $TIMESTAMP"
    log_info "Location: $BACKUP_DIR"
}

cmd_list() {
    log_info "Available backups in: $BACKUP_DIR"
    
    if [ ! -d "$BACKUP_DIR" ]; then
        log_warn "Backup directory does not exist"
        return 0
    fi

    local manifests=("$BACKUP_DIR"/manifest_*.json)
    if [ ! -e "${manifests[0]}" ]; then
        log_warn "No backups found"
        return 0
    fi

    echo ""
    printf "%-20s | %-30s | %s\n" "BACKUP ID" "DATE" "NOTE"
    printf "%s\n" "---------------------|--------------------------------|---------"
    
    for manifest in "${manifests[@]}"; do
        [ -e "$manifest" ] || continue
        local backup_id=$(basename "$manifest" | sed 's/manifest_//;s/.json//')
        local backup_date=$(grep '"date"' "$manifest" 2>/dev/null | cut -d'"' -f4)
        local note=""
        
        if [ -f "$BACKUP_DIR/php_${backup_id}.tar.gz" ]; then
            note="PHP"
        fi
        if [ -f "$BACKUP_DIR/nginx_${backup_id}.tar.gz" ]; then
            note="${note:+$note,}Nginx"
        fi
        if [ -f "$BACKUP_DIR/web_${backup_id}.tar.gz" ]; then
            note="${note:+$note,}Web"
        fi
        if [ -f "$BACKUP_DIR/mysql_${backup_id}.sql.gz" ]; then
            note="${note:+$note,}MySQL"
        fi
        
        printf "%-20s | %-30s | %s\n" "$backup_id" "$backup_date" "$note"
    done
    echo ""
}

restore_component() {
    local component="$1"
    local backup_id="$2"
    local target_dir="$3"
    local pattern="$4"

    local backup_file=$(find "$BACKUP_DIR" -maxdepth 1 -name "${pattern}_${backup_id}.tar.gz" -type f 2>/dev/null | head -1)
    
    if [ -z "$backup_file" ]; then
        log_warn "No $component backup found for ID: $backup_id"
        return 0
    fi

    log_info "Restoring $component from: $backup_file"
    
    if [ -d "$target_dir" ]; then
        local old_dir="${target_dir}.pre_restore_${TIMESTAMP}"
        log_warn "Moving existing $target_dir to $old_dir"
        mv "$target_dir" "$old_dir"
    fi

    mkdir -p "$(dirname "$target_dir")"
    
    if tar -xzf "$backup_file" -C "$(dirname "$target_dir")"; then
        log_info "$component restored successfully"
    else
        log_error "$component restore failed"
        return 1
    fi
}

restore_mysql() {
    local backup_id="$1"
    local backup_file="$BACKUP_DIR/mysql_${backup_id}.sql.gz"

    if [ ! -f "$backup_file" ]; then
        log_warn "No MySQL backup found for ID: $backup_id"
        return 0
    fi

    log_info "Restoring MySQL from: $backup_file"
    
    if command -v mysql >/dev/null 2>&1; then
        if [ -n "$MYSQL_ROOT_PASSWORD" ]; then
            gunzip -c "$backup_file" | mysql -uroot -p"$MYSQL_ROOT_PASSWORD"
        else
            gunzip -c "$backup_file" | mysql -uroot
        fi
        
        if [ $? -eq 0 ]; then
            log_info "MySQL restored successfully"
        else
            log_error "MySQL restore failed"
            return 1
        fi
    else
        log_warn "mysql command not found, manual restore required:"
        log_warn "  gunzip -c $backup_file | mysql -uroot"
    fi
}

cmd_restore() {
    local backup_id="$1"
    
    if [ -z "$backup_id" ]; then
        log_error "Please specify a backup ID"
        log_info "Use '$0 list' to see available backups"
        exit 1
    fi

    check_root || exit 1

    log_info "=== Restore Started ==="
    log_info "Backup ID: $backup_id"

    local manifest="$BACKUP_DIR/manifest_${backup_id}.json"
    if [ -f "$manifest" ]; then
        log_info "Manifest:"
        cat "$manifest"
    fi

    log_step "1" "Stopping services"
    if command -v systemctl >/dev/null 2>&1; then
        systemctl stop nginx php-fpm-* mariadb mysql 2>/dev/null || true
    fi

    log_step "2" "Restoring PHP"
    restore_component "PHP" "$backup_id" "$PHP_PREFIX" "php"

    log_step "3" "Restoring Nginx"
    restore_component "Nginx" "$backup_id" "$NGINX_CONF_DIR" "nginx"

    log_step "4" "Restoring Web Root"
    restore_component "Web" "$backup_id" "$WEB_ROOT" "web"

    log_step "5" "Restoring MySQL"
    restore_mysql "$backup_id"

    log_step "6" "Restarting services"
    if command -v systemctl >/dev/null 2>&1; then
        systemctl start nginx 2>/dev/null || true
        systemctl start mariadb 2>/dev/null || systemctl start mysql 2>/dev/null || true
        
        local php_service=$(systemctl list-unit-files 2>/dev/null | grep -o 'php-fpm-.*\.service' | head -1)
        if [ -n "$php_service" ]; then
            systemctl start "${php_service%.service}" 2>/dev/null || true
        fi
    fi

    log_info ""
    log_info "=== Restore Complete ==="
    log_info "Please verify the restoration is working correctly"
}

docker_save_images() {
    log_step "1" "Saving Docker images"
    
    local images_dir="$BACKUP_DIR/docker_images_${TIMESTAMP}"
    mkdir -p "$images_dir"

    if [ -f "$DOCKER_COMPOSE_DIR/docker-compose.yml" ]; then
        cd "$DOCKER_COMPOSE_DIR"
        
        local images=$(docker compose config --images 2>/dev/null || docker images --format '{{.Repository}}:{{.Tag}}' | grep -E 'lnmp|nginx|php|mariadb|mysql')
        
        for img in $images; do
            local safe_name=$(echo "$img" | tr '/:' '_')
            local tarball="$images_dir/${safe_name}.tar"
            
            log_info "Saving $img..."
            docker save -o "$tarball" "$img" 2>/dev/null
            if [ $? -eq 0 ]; then
                log_info "Saved: $tarball"
            fi
        done
    else
        log_warn "docker-compose.yml not found in $DOCKER_COMPOSE_DIR"
    fi
}

docker_save_volumes() {
    log_step "2" "Saving Docker volumes"
    
    local volumes_dir="$BACKUP_DIR/docker_volumes_${TIMESTAMP}"
    mkdir -p "$volumes_dir"

    if [ -d "$DOCKER_COMPOSE_DIR/mysql" ]; then
        log_info "Backing up MySQL volume..."
        tar -czf "$volumes_dir/mysql.tar.gz" -C "$DOCKER_COMPOSE_DIR" mysql 2>/dev/null && log_info "MySQL volume saved"
    fi

    if [ -d "$DOCKER_COMPOSE_DIR/www" ]; then
        log_info "Backing up www volume..."
        tar -czf "$volumes_dir/www.tar.gz" -C "$DOCKER_COMPOSE_DIR" www 2>/dev/null && log_info "WWW volume saved"
    fi
}

docker_save_manifests() {
    log_step "3" "Saving compose manifests"
    
    local compose_dir="$BACKUP_DIR/docker_compose_${TIMESTAMP}"
    mkdir -p "$compose_dir"

    if [ -f "$DOCKER_COMPOSE_DIR/docker-compose.yml" ]; then
        cp "$DOCKER_COMPOSE_DIR/docker-compose.yml" "$compose_dir/"
        log_info "Saved: docker-compose.yml"
    fi

    if [ -d "$DOCKER_COMPOSE_DIR/nginx" ]; then
        cp -r "$DOCKER_COMPOSE_DIR/nginx" "$compose_dir/"
        log_info "Saved: nginx configs"
    fi

    docker compose ps 2>/dev/null > "$compose_dir/state.txt"
    docker compose config 2>/dev/null > "$compose_dir/config.txt"
    docker images > "$compose_dir/images.txt"
}

cmd_docker_backup() {
    DOCKER_MODE=1
    
    if ! command -v docker >/dev/null 2>&1; then
        log_error "Docker not found"
        exit 1
    fi

    log_info "=== Docker Backup Started ==="
    log_info "Timestamp: $TIMESTAMP"
    log_info "Compose dir: $DOCKER_COMPOSE_DIR"
    
    init_backup_dir

    docker_save_images
    docker_save_volumes
    docker_save_manifests

    echo "$TIMESTAMP" > "$BACKUP_DIR/.last_docker_backup"

    log_info ""
    log_info "=== Docker Backup Complete ==="
    log_info "Backup ID: $TIMESTAMP"
}

cmd_docker_restore() {
    local backup_id="$1"
    
    DOCKER_MODE=1
    
    if [ -z "$backup_id" ]; then
        if [ -f "$BACKUP_DIR/.last_docker_backup" ]; then
            backup_id=$(cat "$BACKUP_DIR/.last_docker_backup")
            log_info "Using last backup: $backup_id"
        else
            log_error "Please specify a backup ID or set one with docker-backup first"
            exit 1
        fi
    fi

    if ! command -v docker >/dev/null 2>&1; then
        log_error "Docker not found"
        exit 1
    fi

    log_info "=== Docker Restore Started ==="
    log_info "Backup ID: $backup_id"

    log_step "1" "Stopping current stack"
    cd "$DOCKER_COMPOSE_DIR" && docker compose down 2>/dev/null || true

    log_step "2" "Restoring compose files"
    local compose_src="$BACKUP_DIR/docker_compose_${backup_id}"
    if [ -d "$compose_src" ]; then
        cp -r "$compose_src"/* "$DOCKER_COMPOSE_DIR/"
        log_info "Compose files restored"
    else
        log_warn "No compose files found in backup"
    fi

    log_step "3" "Restoring volumes"
    local volumes_src="$BACKUP_DIR/docker_volumes_${backup_id}"
    
    if [ -f "$volumes_src/mysql.tar.gz" ]; then
        log_info "Restoring MySQL volume..."
        rm -rf "$DOCKER_COMPOSE_DIR/mysql"
        tar -xzf "$volumes_src/mysql.tar.gz" -C "$DOCKER_COMPOSE_DIR"
    fi
    
    if [ -f "$volumes_src/www.tar.gz" ]; then
        log_info "Restoring www volume..."
        tar -xzf "$volumes_src/www.tar.gz" -C "$DOCKER_COMPOSE_DIR"
    fi

    log_step "4" "Restoring images (if needed)"
    local images_src="$BACKUP_DIR/docker_images_${backup_id}"
    if [ -d "$images_src" ]; then
        for tarball in "$images_src"/*.tar; do
            [ -f "$tarball" ] || continue
            log_info "Loading $(basename "$tarball")..."
            docker load -i "$tarball" 2>/dev/null
        done
    fi

    log_step "5" "Starting stack"
    cd "$DOCKER_COMPOSE_DIR" && docker compose up -d 2>/dev/null || true

    log_info ""
    log_info "=== Docker Restore Complete ==="
    log_info "Check status: docker compose ps"
}

cmd_docker_rollback() {
    DOCKER_MODE=1
    
    if [ ! -f "$BACKUP_DIR/.last_docker_backup" ]; then
        log_error "No previous docker backup found"
        log_info "Run '$0 docker-backup' first to create a restore point"
        exit 1
    fi

    local last_backup=$(cat "$BACKUP_DIR/.last_docker_backup")
    log_warn "This will rollback Docker deployment to: $last_backup"
    echo ""
    
    read -p "Are you sure? (y/N): " confirm
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        log_info "Cancelled"
        exit 0
    fi

    cmd_docker_restore "$last_backup"
}

case "${1:-help}" in
    backup)
        cmd_backup
        ;;
    list)
        cmd_list
        ;;
    restore)
        cmd_restore "$2"
        ;;
    docker-backup)
        cmd_docker_backup
        ;;
    docker-restore)
        cmd_docker_restore "$2"
        ;;
    docker-rollback)
        cmd_docker_rollback
        ;;
    help|--help|-h)
        show_usage
        ;;
    *)
        log_error "Unknown command: $1"
        show_usage
        exit 1
        ;;
esac
