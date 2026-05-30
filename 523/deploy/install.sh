#!/bin/bash
set -e

DETECTOR_VERSION="1.0.0"
INSTALL_DIR="/usr/local/bin"
CONFIG_DIR="/etc/escape-detector"
RULES_DIR="${CONFIG_DIR}/rules"
SYSTEMD_DIR="/etc/systemd/system"
LOG_DIR="/var/log/escape-detector"

echo "========================================"
echo "Container Escape Detector Installation"
echo "========================================"
echo ""

if [ "$(id -u)" != "0" ]; then
    echo "ERROR: This script must be run as root"
    exit 1
fi

check_kernel_version() {
    local kernel_version=$(uname -r | cut -d. -f1,2)
    local major=$(echo $kernel_version | cut -d. -f1)
    local minor=$(echo $kernel_version | cut -d. -f2)
    
    if [ "$major" -lt 4 ] || ([ "$major" -eq 4 ] && [ "$minor" -lt 15 ]); then
        echo "ERROR: Linux kernel 4.15+ required for eBPF support (current: $(uname -r))"
        exit 1
    fi
    echo "[OK] Kernel version: $(uname -r)"
}

check_bpf_support() {
    if [ ! -f /sys/kernel/debug/tracing/trace_pipe ]; then
        echo "WARNING: Kernel tracing may not be available"
        mount -t debugfs none /sys/kernel/debug 2>/dev/null || true
    fi
    
    if [ -f /proc/config.gz ]; then
        if zcat /proc/config.gz | grep -q "CONFIG_BPF=y"; then
            echo "[OK] BPF support enabled"
        else
            echo "WARNING: BPF may not be enabled in kernel"
        fi
    fi
}

check_dependencies() {
    local deps=("docker" "curl")
    for dep in "${deps[@]}"; do
        if command -v $dep &> /dev/null; then
            echo "[OK] $dep found: $(command -v $dep)"
        else
            echo "WARNING: $dep not found"
        fi
    done
}

echo "[1/6] Checking system requirements..."
check_kernel_version
check_bpf_support
check_dependencies
echo ""

echo "[2/6] Creating directories..."
mkdir -p ${CONFIG_DIR}
mkdir -p ${RULES_DIR}
mkdir -p ${LOG_DIR}
chmod 755 ${CONFIG_DIR}
chmod 750 ${RULES_DIR}
chmod 750 ${LOG_DIR}
echo "[OK] Directories created"
echo ""

echo "[3/6] Installing binary..."
BINARY_PATH="../cmd/escape-detector/escape-detector"
if [ -f "$BINARY_PATH" ]; then
    cp ${BINARY_PATH} ${INSTALL_DIR}/escape-detector
    chmod 755 ${INSTALL_DIR}/escape-detector
    chown root:root ${INSTALL_DIR}/escape-detector
    echo "[OK] Binary installed to ${INSTALL_DIR}/escape-detector"
else
    echo "WARNING: Binary not found at ${BINARY_PATH}"
    echo "Please build first: make build"
fi
echo ""

echo "[4/6] Installing configuration files..."
cp ../configs/config.yaml ${CONFIG_DIR}/config.yaml
chmod 644 ${CONFIG_DIR}/config.yaml
chown root:root ${CONFIG_DIR}/config.yaml

if [ -d "../configs/rules" ]; then
    cp -r ../configs/rules/* ${RULES_DIR}/
    chmod 640 ${RULES_DIR}/*.yaml
    chown root:root ${RULES_DIR}/*.yaml
fi
echo "[OK] Configuration installed"
echo ""

echo "[5/6] Installing systemd service..."
cp escape-detector.service ${SYSTEMD_DIR}/
chmod 644 ${SYSTEMD_DIR}/escape-detector.service
systemctl daemon-reload
echo "[OK] systemd service installed"
echo ""

echo "[6/6] Enabling service..."
systemctl enable escape-detector.service 2>/dev/null || true
echo "[OK] Service enabled"
echo ""

echo "========================================"
echo "Installation Complete!"
echo "========================================"
echo ""
echo "To start the service:"
echo "  systemctl start escape-detector"
echo ""
echo "To check status:"
echo "  systemctl status escape-detector"
echo ""
echo "To view logs:"
echo "  journalctl -u escape-detector -f"
echo ""
echo "Configuration files:"
echo "  - Main config: ${CONFIG_DIR}/config.yaml"
echo "  - Rules: ${RULES_DIR}/"
echo ""
echo "Metrics endpoints:"
echo "  - http://localhost:9090/metrics"
echo "  - http://localhost:9090/alerts"
echo "  - http://localhost:9090/health"
echo "  - http://localhost:9090/risk"
echo ""
