#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${SCRIPT_DIR}/config/patch-manager.conf"
ANSIBLE_PLAYBOOKS_DIR="${SCRIPT_DIR}/ansible/playbooks"
REPORTS_DIR="${SCRIPT_DIR}/reports"
INVENTORY_FILE="${SCRIPT_DIR}/config/inventory.ini"
LOG_DIR="${SCRIPT_DIR}/logs"

VERSION="3.0.0"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

log() {
    local level="$1"
    local message="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${timestamp} [${level}] ${message}" | tee -a "${LOG_DIR}/patch-manager.log"
}

info() {
    log "INFO" "${GREEN}$1${NC}"
}

warn() {
    log "WARN" "${YELLOW}$1${NC}"
}

error() {
    log "ERROR" "${RED}$1${NC}"
}

debug() {
    log "DEBUG" "${BLUE}$1${NC}"
}

init_directories() {
    mkdir -p "${CONFIG_FILE%/*}"
    mkdir -p "${ANSIBLE_PLAYBOOKS_DIR}"
    mkdir -p "${REPORTS_DIR}"
    mkdir -p "${LOG_DIR}"
}

check_dependencies() {
    local missing_deps=()
    
    if ! command -v ansible &> /dev/null; then
        missing_deps+=("ansible")
    fi
    
    if ! command -v ansible-playbook &> /dev/null; then
        missing_deps+=("ansible-playbook")
    fi
    
    if [ ${#missing_deps[@]} -gt 0 ]; then
        error "Missing required dependencies: ${missing_deps[*]}"
        exit 1
    fi
    
    info "All dependencies checked successfully"
}

load_config() {
    if [ -f "$CONFIG_FILE" ]; then
        source "$CONFIG_FILE"
        info "Configuration loaded from $CONFIG_FILE"
    else
        warn "Configuration file not found. Using defaults."
    fi
}

show_help() {
    cat << EOF
Security Patch Manager - Version ${VERSION}

Usage: $(basename "$0") [COMMAND] [OPTIONS]

Core Commands:
  scan        Scan for CVE vulnerabilities on target hosts
  baseline    Run security baseline compliance scan
  simulate    Simulate patch installation (dry-run) with CVSS prioritization
  install     Install security patches on target hosts
  rollback    Rollback last installed patches
  report      Generate compliance report

Notification Commands:
  notify      Send report notification to DingTalk/WeChat Work

Options:
  -i, --inventory FILE    Specify inventory file (default: config/inventory.ini)
  -l, --limit HOSTS       Limit execution to specific hosts
  -t, --tags TAGS         Only run tasks tagged with specific tags
  -v, --verbose           Enable verbose output
  --force-rollback        Force rollback even if safety checks fail
  --no-reboot             Disable automatic reboot after patch installation
  --webhook URL           Webhook URL for notification
  --webhook-type TYPE     Webhook type: dingtalk/wechat (default: dingtalk)
  --report FILE           Path to report JSON file for notification
  -h, --help              Show this help message

Examples:
  $(basename "$0") baseline
  $(basename "$0") simulate --limit web_servers
  $(basename "$0") install --no-reboot
  $(basename "$0") notify --webhook "https://your-webhook-url" --webhook-type dingtalk --report reports/vulnerability_scan_20240101_120000.json

Patch Status Codes:
  FIXED     - No pending security updates
  UNFIXED   - Security updates pending installation
  NA        - Not applicable (unsupported OS)

CVSS Priority Levels:
  CRITICAL  - CVSS ≥ 9.0 (3 days SLA)
  HIGH      - CVSS ≥ 7.0 (7 days SLA)
  MEDIUM    - CVSS ≥ 4.0 (15 days SLA)
  LOW       - CVSS ≥ 0.0 (30 days SLA)

EOF
}

display_scan_summary() {
    local report_file="$1"
    if command -v jq &> /dev/null && [ -f "$report_file" ]; then
        echo ""
        echo "========================================"
        echo "         VULNERABILITY SCAN SUMMARY     "
        echo "========================================"
        echo ""
        jq -r '.summary' "$report_file" 2>/dev/null || true
        echo ""
        echo "Critical hosts:    $(jq -r '.statistics.critical_hosts // "N/A"' "$report_file" 2>/dev/null)"
        echo "Warning hosts:     $(jq -r '.statistics.warning_hosts // "N/A"' "$report_file" 2>/dev/null)"
        echo "OK hosts:          $(jq -r '.statistics.ok_hosts // "N/A"' "$report_file" 2>/dev/null)"
        echo "From cache:        $(jq -r '.statistics.from_cache // "N/A"' "$report_file" 2>/dev/null)"
        echo ""
        echo "========================================"
    fi
}

display_baseline_summary() {
    local report_file="$1"
    if command -v jq &> /dev/null && [ -f "$report_file" ]; then
        echo ""
        echo "========================================"
        echo "      SECURITY BASELINE SCAN SUMMARY    "
        echo "========================================"
        echo ""
        echo "Total hosts:       $(jq -r '.total_hosts // "N/A"' "$report_file" 2>/dev/null)"
        echo "Compliant:         $(jq -r '.compliant_count // "N/A"' "$report_file" 2>/dev/null)"
        echo "Warning:           $(jq -r '.warning_count // "N/A"' "$report_file" 2>/dev/null)"
        echo "Non-Compliant:     $(jq -r '.non_compliant_count // "N/A"' "$report_file" 2>/dev/null)"
        echo "Average Score:     $(jq -r '.average_score // "N/A"' "$report_file" 2>/dev/null)%"
        echo ""
        echo "Baseline Version:  $(jq -r '.baseline_version // "N/A"' "$report_file" 2>/dev/null)"
        echo "Scan Date:         $(jq -r '.scan_date // "N/A"' "$report_file" 2>/dev/null)"
        echo "========================================"
    fi
}

display_simulation_summary() {
    local report_file="$1"
    if command -v jq &> /dev/null && [ -f "$report_file" ]; then
        echo ""
        echo "========================================"
        echo "       PATCH SIMULATION SUMMARY         "
        echo "========================================"
        echo ""
        echo "📊 Host Statistics:"
        echo "  Total hosts:      $(jq -r '.summary.total_hosts // "N/A"' "$report_file" 2>/dev/null)"
        echo "  With updates:     $(jq -r '.summary.hosts_with_updates // "N/A"' "$report_file" 2>/dev/null)"
        echo "  Security updates: $(jq -r '.summary.hosts_with_security_updates // "N/A"' "$report_file" 2>/dev/null)"
        echo "  Needs reboot:     $(jq -r '.summary.hosts_needing_reboot // "N/A"' "$report_file" 2>/dev/null)"
        echo ""
        echo "⚠️  Patch Priorities:"
        echo "  CRITICAL (≥9.0):  $(jq -r '.summary.total_critical_patches // "N/A"' "$report_file" 2>/dev/null)"
        echo "  HIGH (≥7.0):      $(jq -r '.summary.total_high_patches // "N/A"' "$report_file" 2>/dev/null)"
        echo "  MEDIUM (≥4.0):    $(jq -r '.summary.total_medium_patches // "N/A"' "$report_file" 2>/dev/null)"
        echo "  LOW (≥0.0):       $(jq -r '.summary.total_low_patches // "N/A"' "$report_file" 2>/dev/null)"
        echo ""
        echo "⚠️  WARNING: $(jq -r '.summary.total_critical_patches // 0' "$report_file" 2>/dev/null) CRITICAL patches need attention!"
        echo "========================================"
    fi
}

display_install_summary() {
    local report_file="$1"
    if command -v jq &> /dev/null && [ -f "$report_file" ]; then
        echo ""
        echo "========================================"
        echo "        PATCH INSTALLATION SUMMARY      "
        echo "========================================"
        echo ""
        jq -r '.summary' "$report_file" 2>/dev/null || true
        echo ""
        echo "Total hosts:       $(jq -r '.total_hosts // "N/A"' "$report_file" 2>/dev/null)"
        echo "Success:           $(jq -r '.success_count // "N/A"' "$report_file" 2>/dev/null)"
        echo "Changed:           $(jq -r '.changed_count // "N/A"' "$report_file" 2>/dev/null)"
        echo "Reboot required:   $(jq -r '.reboot_required_count // "N/A"' "$report_file" 2>/dev/null)"
        echo "Already patched:   $(jq -r '.already_patched_count // "N/A"' "$report_file" 2>/dev/null)"
        echo ""
        
        local reboot_count=$(jq -r '.reboot_required_count // 0' "$report_file" 2>/dev/null)
        if [ "$reboot_count" -gt 0 ]; then
            warn "NOTE: ${reboot_count} hosts require reboot after kernel updates!"
        fi
        echo "========================================"
    fi
}

display_rollback_summary() {
    local report_file="$1"
    if command -v jq &> /dev/null && [ -f "$report_file" ]; then
        echo ""
        echo "========================================"
        echo "          PATCH ROLLBACK SUMMARY        "
        echo "========================================"
        echo ""
        jq -r '.summary' "$report_file" 2>/dev/null || true
        echo ""
        echo "Total hosts:       $(jq -r '.total_hosts // "N/A"' "$report_file" 2>/dev/null)"
        echo "Success:           $(jq -r '.success_count // "N/A"' "$report_file" 2>/dev/null)"
        echo "Warnings:          $(jq -r '.warning_count // "N/A"' "$report_file" 2>/dev/null)"
        echo "Rolled back:       $(jq -r '.rolled_back_count // "N/A"' "$report_file" 2>/dev/null)"
        echo "Kernel rollback:   $(jq -r '.kernel_rollback_count // "N/A"' "$report_file" 2>/dev/null)"
        echo "Unsafe rollbacks:  $(jq -r '.unsafe_rollback_count // "N/A"' "$report_file" 2>/dev/null)"
        echo ""
        
        local kernel_rollback_count=$(jq -r '.kernel_rollback_count // 0' "$report_file" 2>/dev/null)
        if [ "$kernel_rollback_count" -gt 0 ]; then
            warn "NOTE: ${kernel_rollback_count} hosts had kernel rollbacks! Consider rebooting."
        fi
        echo "========================================"
    fi
}

display_report_summary() {
    local json_report="$1"
    if command -v jq &> /dev/null && [ -f "$json_report" ]; then
        echo ""
        echo "========================================"
        echo "         COMPLIANCE REPORT SUMMARY      "
        echo "========================================"
        echo ""
        jq -r '.summary' "$json_report" 2>/dev/null || true
        echo ""
        echo "-------- PATCH STATUS --------"
        echo "FIXED:        $(jq -r '.patch_statistics.fixed_count // "N/A"' "$json_report" 2>/dev/null)"
        echo "UNFIXED:      $(jq -r '.patch_statistics.unfixed_count // "N/A"' "$json_report" 2>/dev/null)"
        echo "N/A:          $(jq -r '.patch_statistics.na_count // "N/A"' "$json_report" 2>/dev/null)"
        echo "Total Patches Applied: $(jq -r '.patch_statistics.total_patches_applied // "N/A"' "$json_report" 2>/dev/null)"
        echo ""
        echo "------ COMPLIANCE STATUS ------"
        echo "Compliant:    $(jq -r '.compliance_statistics.compliant_hosts // "N/A"' "$json_report" 2>/dev/null)"
        echo "Warning:      $(jq -r '.compliance_statistics.warning_hosts // "N/A"' "$json_report" 2>/dev/null)"
        echo "Non-Compliant:$(jq -r '.compliance_statistics.non_compliant_hosts // "N/A"' "$json_report" 2>/dev/null)"
        echo "Avg Score:    $(jq -r '.compliance_statistics.average_score // "N/A"' "$json_report" 2>/dev/null)%"
        echo ""
        echo "========================================"
    fi
}

scan_vulnerabilities() {
    info "Starting CVE vulnerability scan..."
    
    local extra_args=()
    
    if [ -n "${LIMIT:-}" ]; then
        extra_args+=("--limit" "$LIMIT")
    fi
    
    if [ -n "${TAGS:-}" ]; then
        extra_args+=("--tags" "$TAGS")
    fi
    
    if [ "${VERBOSE:-false}" = "true" ]; then
        extra_args+=("-v")
    fi
    
    local scan_report="${REPORTS_DIR}/vulnerability_scan_$(date '+%Y%m%d_%H%M%S').json"
    
    ansible-playbook \
        -i "$INVENTORY_FILE" \
        "${ANSIBLE_PLAYBOOKS_DIR}/scan-vulnerabilities.yml" \
        --extra-vars "report_file=${scan_report}" \
        "${extra_args[@]}"
    
    if [ $? -eq 0 ]; then
        info "Vulnerability scan completed successfully"
        info "Scan report saved to: ${scan_report}"
        display_scan_summary "$scan_report"
    else
        error "Vulnerability scan failed"
        exit 1
    fi
}

baseline_scan() {
    info "Starting security baseline compliance scan..."
    
    local extra_args=()
    
    if [ -n "${LIMIT:-}" ]; then
        extra_args+=("--limit" "$LIMIT")
    fi
    
    if [ -n "${TAGS:-}" ]; then
        extra_args+=("--tags" "$TAGS")
    fi
    
    if [ "${VERBOSE:-false}" = "true" ]; then
        extra_args+=("-v")
    fi
    
    local baseline_report="${REPORTS_DIR}/baseline_scan_$(date '+%Y%m%d_%H%M%S').json"
    
    ansible-playbook \
        -i "$INVENTORY_FILE" \
        "${ANSIBLE_PLAYBOOKS_DIR}/baseline-scan.yml" \
        --extra-vars "report_file=${baseline_report}" \
        "${extra_args[@]}"
    
    if [ $? -eq 0 ]; then
        info "Baseline scan completed successfully"
        info "Baseline report saved to: ${baseline_report}"
        display_baseline_summary "$baseline_report"
    else
        error "Baseline scan failed"
        exit 1
    fi
}

simulate_patches() {
    info "Starting patch simulation (dry-run) with CVSS prioritization..."
    info "This will NOT install any patches on your systems"
    
    local extra_args=()
    
    if [ -n "${LIMIT:-}" ]; then
        extra_args+=("--limit" "$LIMIT")
    fi
    
    if [ -n "${TAGS:-}" ]; then
        extra_args+=("--tags" "$TAGS")
    fi
    
    if [ "${VERBOSE:-false}" = "true" ]; then
        extra_args+=("-v")
    fi
    
    local simulation_report="${REPORTS_DIR}/patch_simulation_$(date '+%Y%m%d_%H%M%S').json"
    
    ansible-playbook \
        -i "$INVENTORY_FILE" \
        "${ANSIBLE_PLAYBOOKS_DIR}/patch-simulation.yml" \
        --extra-vars "report_file=${simulation_report}" \
        "${extra_args[@]}"
    
    if [ $? -eq 0 ]; then
        info "Patch simulation completed successfully"
        info "Simulation report saved to: ${simulation_report}"
        display_simulation_summary "$simulation_report"
    else
        error "Patch simulation failed"
        exit 1
    fi
}

install_patches() {
    info "Starting security patch installation..."
    
    local extra_args=()
    
    if [ -n "${LIMIT:-}" ]; then
        extra_args+=("--limit" "$LIMIT")
    fi
    
    if [ -n "${TAGS:-}" ]; then
        extra_args+=("--tags" "$TAGS")
    fi
    
    if [ "${VERBOSE:-false}" = "true" ]; then
        extra_args+=("-v")
    fi
    
    if [ "${NO_REBOOT:-false}" = "true" ]; then
        extra_args+=("--extra-vars" "reboot_after_update=false")
    fi
    
    local install_report="${REPORTS_DIR}/patch_install_$(date '+%Y%m%d_%H%M%S').json"
    
    ansible-playbook \
        -i "$INVENTORY_FILE" \
        "${ANSIBLE_PLAYBOOKS_DIR}/install-patches.yml" \
        --extra-vars "report_file=${install_report}" \
        "${extra_args[@]}"
    
    if [ $? -eq 0 ]; then
        info "Patch installation completed successfully"
        info "Installation report saved to: ${install_report}"
        display_install_summary "$install_report"
    else
        error "Patch installation failed"
        exit 1
    fi
}

rollback_patches() {
    warn "Starting patch rollback. This will revert the last applied patches!"
    
    local extra_args=()
    
    if [ "${FORCE_ROLLBACK:-false}" = "true" ]; then
        warn "Force rollback enabled: Safety checks will be bypassed!"
        extra_args+=("--extra-vars" "force_rollback=true")
    fi
    
    echo ""
    echo "PLEASE NOTE:"
    echo "- Rollback will revert packages to previous state"
    echo "- Dependency checks will be performed before rollback"
    echo "- Kernel rollbacks may require reboot"
    echo ""
    
    read -p "Are you sure you want to proceed? Type 'YES' to confirm: " confirm
    if [ "$confirm" != "YES" ]; then
        info "Rollback cancelled by user"
        exit 0
    fi
    
    if [ -n "${LIMIT:-}" ]; then
        extra_args+=("--limit" "$LIMIT")
    fi
    
    if [ "${VERBOSE:-false}" = "true" ]; then
        extra_args+=("-v")
    fi
    
    local rollback_report="${REPORTS_DIR}/patch_rollback_$(date '+%Y%m%d_%H%M%S').json"
    
    ansible-playbook \
        -i "$INVENTORY_FILE" \
        "${ANSIBLE_PLAYBOOKS_DIR}/rollback-patches.yml" \
        --extra-vars "report_file=${rollback_report}" \
        "${extra_args[@]}"
    
    if [ $? -eq 0 ]; then
        info "Patch rollback completed successfully"
        info "Rollback report saved to: ${rollback_report}"
        display_rollback_summary "$rollback_report"
    else
        error "Patch rollback failed"
        exit 1
    fi
}

generate_report() {
    info "Generating compliance report..."
    
    local report_date=$(date '+%Y-%m-%d')
    local report_file="${REPORTS_DIR}/compliance_report_${report_date}.html"
    local json_report="${REPORTS_DIR}/compliance_report_${report_date}.json"
    
    local extra_args=()
    
    if [ -n "${LIMIT:-}" ]; then
        extra_args+=("--limit" "$LIMIT")
    fi
    
    ansible-playbook \
        -i "$INVENTORY_FILE" \
        "${ANSIBLE_PLAYBOOKS_DIR}/generate-report.yml" \
        --extra-vars "html_report=${report_file} json_report=${json_report}" \
        "${extra_args[@]}"
    
    if [ $? -eq 0 ]; then
        info "Compliance report generated successfully"
        info "HTML Report: ${report_file}"
        info "JSON Report: ${json_report}"
        display_report_summary "$json_report"
    else
        error "Compliance report generation failed"
        exit 1
    fi
}

send_notification() {
    info "Sending notification..."
    
    if [ -z "${WEBHOOK_URL:-}" ]; then
        error "Webhook URL is required. Use --webhook option"
        exit 1
    fi
    
    if [ -z "${REPORT_FILE:-}" ]; then
        error "Report file is required. Use --report option"
        exit 1
    fi
    
    if [ ! -f "$REPORT_FILE" ]; then
        error "Report file not found: $REPORT_FILE"
        exit 1
    fi
    
    local webhook_type="${WEBHOOK_TYPE:-dingtalk}"
    
    info "Webhook Type: $webhook_type"
    info "Report File: $REPORT_FILE"
    
    ansible-playbook \
        "${ANSIBLE_PLAYBOOKS_DIR}/send-notification.yml" \
        --extra-vars "webhook_url=${WEBHOOK_URL}" \
        --extra-vars "webhook_type=${webhook_type}" \
        --extra-vars "report_file=${REPORT_FILE}"
    
    if [ $? -eq 0 ]; then
        info "Notification sent successfully!"
    else
        error "Notification failed"
        exit 1
    fi
}

main() {
    local command=""
    VERBOSE=false
    LIMIT=""
    TAGS=""
    FORCE_ROLLBACK=false
    NO_REBOOT=false
    WEBHOOK_URL=""
    WEBHOOK_TYPE="dingtalk"
    REPORT_FILE=""
    
    while [[ $# -gt 0 ]]; do
        case "$1" in
            scan|baseline|simulate|install|rollback|report|notify|help)
                command="$1"
                shift
                ;;
            -i|--inventory)
                INVENTORY_FILE="$2"
                shift 2
                ;;
            -l|--limit)
                LIMIT="$2"
                shift 2
                ;;
            -t|--tags)
                TAGS="$2"
                shift 2
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            --force-rollback)
                FORCE_ROLLBACK=true
                shift
                ;;
            --no-reboot)
                NO_REBOOT=true
                shift
                ;;
            --webhook)
                WEBHOOK_URL="$2"
                shift 2
                ;;
            --webhook-type)
                WEBHOOK_TYPE="$2"
                shift 2
                ;;
            --report)
                REPORT_FILE="$2"
                shift 2
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    init_directories
    check_dependencies
    load_config
    
    case "$command" in
        scan)
            scan_vulnerabilities
            ;;
        baseline)
            baseline_scan
            ;;
        simulate)
            simulate_patches
            ;;
        install)
            install_patches
            ;;
        rollback)
            rollback_patches
            ;;
        report)
            generate_report
            ;;
        notify)
            send_notification
            ;;
        help|*)
            show_help
            ;;
    esac
}

main "$@"
