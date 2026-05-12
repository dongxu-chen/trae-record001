#!/bin/bash

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

LOCK_FILE="/tmp/deploy-web-server.lock"
TERRAFORM_MAX_RETRIES=5
TERRAFORM_RETRY_INTERVAL=30
DEFAULT_ENV="dev"
VALID_ENVS=("dev" "staging" "prod")

print_step() {
    echo -e "${GREEN}[+] $1${NC}"
}

print_warn() {
    echo -e "${YELLOW}[!] $1${NC}"
}

print_error() {
    echo -e "${RED}[x] $1${NC}"
}

print_info() {
    echo -e "${CYAN}[i] $1${NC}"
}

check_dependency() {
    if ! command -v "$1" &> /dev/null; then
        print_error "$1 未安装，请先安装 $1"
        exit 1
    fi
}

validate_env() {
    local env="$1"
    for valid in "${VALID_ENVS[@]}"; do
        if [ "$env" = "$valid" ]; then
            return 0
        fi
    done
    print_error "无效的环境: $env"
    print_info "有效环境: ${VALID_ENVS[*]}"
    exit 1
}

acquire_lock() {
    local lock_fd
    exec {lock_fd}>"$LOCK_FILE"
    if ! flock -n "$lock_fd"; then
        print_error "另一个部署进程正在运行，退出..."
        exit 1
    fi
    echo "$$" > "$LOCK_FILE"
    export LOCK_FD="$lock_fd"
    trap 'release_lock' EXIT INT TERM HUP
}

release_lock() {
    if [[ -n "${LOCK_FD:-}" ]]; then
        flock -u "$LOCK_FD"
        exec {LOCK_FD}>&-
        rm -f "$LOCK_FILE"
    fi
}

run_terraform_with_retry() {
    local cmd="$1"
    local args=("${@:2}")
    local attempt=1

    while (( attempt <= TERRAFORM_MAX_RETRIES )); do
        print_step "执行 Terraform $cmd (尝试 $attempt/$TERRAFORM_MAX_RETRIES)..."
        
        if terraform "$cmd" "${args[@]}" 2>&1; then
            return 0
        else
            local exit_code=$?
            if (( attempt == TERRAFORM_MAX_RETRIES )); then
                print_error "Terraform $cmd 执行失败，已达到最大重试次数"
                exit $exit_code
            fi
            print_warn "Terraform $cmd 执行失败，$TERRAFORM_RETRY_INTERVAL 秒后重试..."
            sleep "$TERRAFORM_RETRY_INTERVAL"
            ((attempt++))
        fi
    done
}

switch_workspace() {
    local env="$1"
    print_step "切换到工作区: $env"
    terraform workspace new "$env" 2>/dev/null || true
    terraform workspace select "$env"
}

wait_for_ssh() {
    local hosts_file="$1"
    local max_wait=300
    local wait_interval=10
    local elapsed=0

    while (( elapsed < max_wait )); do
        local all_ready=true
        while read -r line; do
            if [[ "$line" == *ansible_host=* ]]; then
                local host=$(echo "$line" | grep -oP 'ansible_host=\K[^\s]+')
                if ! nc -z "$host" 22 2>/dev/null; then
                    all_ready=false
                    break
                fi
            fi
        done < "$hosts_file"

        if "$all_ready"; then
            print_step "所有实例 SSH 服务已就绪"
            return 0
        fi

        print_warn "等待 SSH 服务就绪... (${elapsed}/${max_wait}s)"
        sleep "$wait_interval"
        ((elapsed += wait_interval))
    done

    print_error "SSH 服务等待超时"
    exit 1
}

display_help() {
    echo "用法: $0 [选项] [环境]"
    echo ""
    echo "环境:"
    echo "  dev        开发环境 (默认)"
    echo "  staging    测试环境"
    echo "  prod       生产环境"
    echo ""
    echo "选项:"
    echo "  --destroy  销毁环境"
    echo "  --plan     仅执行 plan"
    echo "  -h, --help 显示帮助"
    echo ""
    echo "示例:"
    echo "  $0 dev           部署到开发环境"
    echo "  $0 staging --plan  查看 staging 环境变更计划"
    echo "  $0 prod --destroy 销毁生产环境"
    exit 0
}

ACTION="apply"
ENVIRONMENT="$DEFAULT_ENV"

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            display_help
            ;;
        --destroy)
            ACTION="destroy"
            shift
            ;;
        --plan)
            ACTION="plan"
            shift
            ;;
        *)
            if [[ -z "$ENVIRONMENT" ]]; then
                ENVIRONMENT="$1"
            else
                ENVIRONMENT="$1"
            fi
            shift
            ;;
    esac
done

validate_env "$ENVIRONMENT"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================"
print_info "环境: $ENVIRONMENT"
print_info "操作: $ACTION"
echo "========================================"

check_dependency terraform
check_dependency ansible
check_dependency nc
check_dependency flock

print_step "获取本地锁..."
acquire_lock

print_step "初始化 Terraform..."
run_terraform_with_retry init

print_step "切换工作区..."
switch_workspace "$ENVIRONMENT"

print_step "验证 Terraform 配置..."
run_terraform_with_retry validate

if [ "$ACTION" = "plan" ]; then
    print_step "执行 Terraform plan..."
    run_terraform_with_retry plan
    exit 0
fi

print_step "执行 Terraform plan (预览变更)..."
run_terraform_with_retry plan

if [ "$ACTION" = "destroy" ]; then
    print_warn "⚠️  即将销毁 $ENVIRONMENT 环境所有资源！"
    read -p "输入 'DESTROY-$ENVIRONMENT' 确认: " -r
    echo
    if [[ $REPLY != "DESTROY-$ENVIRONMENT" ]]; then
        print_warn "已取消销毁"
        exit 0
    fi
    print_step "执行 Terraform destroy..."
    run_terraform_with_retry destroy -auto-approve
    print_step "环境 $ENVIRONMENT 已销毁"
    exit 0
fi

print_warn "准备在 $ENVIRONMENT 环境创建基础设施。"
read -p "是否继续? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_warn "已取消部署"
    exit 0
fi

print_step "执行 Terraform apply..."
run_terraform_with_retry apply -auto-approve

ALB_DNS=$(terraform output -raw alb_dns_name)
ASG_NAME=$(terraform output -raw asg_name)
print_step "EC2 Auto Scaling 组创建完成: $ASG_NAME"
print_step "ALB 地址: http://$ALB_DNS"

sleep 30

print_step "等待实例就绪..."
sleep 20

print_step "安装 Ansible AWS 集合..."
cd "$SCRIPT_DIR/ansible"
ansible-galaxy collection install -r requirements.yml

print_step "执行 Ansible playbook..."
ANSIBLE_HOST_KEY_CHECKING=False ansible-playbook -i aws_ec2.yml playbook.yml \
    -e "env=$ENVIRONMENT" \
    --limit "env_$ENVIRONMENT"

cd "$SCRIPT_DIR"

print_step "部署完成!"
echo -e "${GREEN}========================================${NC}"
echo -e "环境: $ENVIRONMENT"
echo -e "ALB 地址: http://$ALB_DNS"
echo -e "Auto Scaling 组: $ASG_NAME"
echo -e "健康检查: http://$ALB_DNS/health"
echo -e "${GREEN}========================================${NC}"

print_step "查看当前工作区:"
terraform workspace show
