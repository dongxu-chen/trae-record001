#!/bin/bash
# ==========================================
# 主机健康检查脚本
# 输出 JSON 格式的健康指标
# ==========================================

TIMEOUT=30
CRITICAL_LOAD=8.0
CRITICAL_MEM=90
CRITICAL_DISK=90
CRITICAL_CPU=85

# 初始化指标
METRICS='{}'

# 1. 检查系统负载
LOAD_1MIN=$(awk '{print $1}' /proc/loadavg 2>/dev/null || echo "0")
LOAD_5MIN=$(awk '{print $2}' /proc/loadavg 2>/dev/null || echo "0")
LOAD_15MIN=$(awk '{print $3}' /proc/loadavg 2>/dev/null || echo "0")

# 2. 检查内存使用率
MEM_TOTAL=$(free -m | awk '/Mem:/ {print $2}')
MEM_USED=$(free -m | awk '/Mem:/ {print $3}')
MEM_RATE=$((MEM_USED * 100 / MEM_TOTAL))

# 3. 检查磁盘使用率
DISK_USAGE=$(df -h / | awk '/\// {print $5}' | sed 's/%//')

# 4. 检查 CPU 使用率
CPU_IDLE=$(top -bn1 | grep 'Cpu(s)' | sed 's/.*, *\([0-9.]*\)%* id.*/\1/' | awk '{print 100 - $1}')

# 5. 检查关键服务
SERVICES_OK=true
for service in sshd rsyslog; do
    if systemctl is-active --quiet $service 2>/dev/null; then
        continue
    else
        SERVICES_OK=false
        break
    fi
done

# 6. 检查网络连通性
NETWORK_OK=true
ping -c 1 -W 2 8.8.8.8 >/dev/null 2>&1 || NETWORK_OK=false

# 7. 检查文件系统只读
FS_READONLY=false
touch /tmp/.health_check 2>/dev/null && rm -f /tmp/.health_check || FS_READONLY=true

# 8. 综合判断健康状态
STATUS="healthy"

# 负载检查
if (( $(echo "$LOAD_1MIN > $CRITICAL_LOAD" | bc -l) )); then
    STATUS="warning"
fi

# 内存检查
if [ "$MEM_RATE" -gt "$CRITICAL_MEM" ]; then
    STATUS="warning"
fi

# 磁盘检查
if [ "$DISK_USAGE" -gt "$CRITICAL_DISK" ]; then
    STATUS="critical"
fi

# CPU检查
if (( $(echo "$CPU_IDLE > $CRITICAL_CPU" | bc -l) )); then
    STATUS="warning"
fi

# 服务检查
if [ "$SERVICES_OK" = "false" ]; then
    STATUS="critical"
fi

# 网络检查
if [ "$NETWORK_OK" = "false" ]; then
    STATUS="warning"
fi

# 文件系统检查
if [ "$FS_READONLY" = "true" ]; then
    STATUS="critical"
fi

# 输出 JSON 结果
cat << EOF
{
  "status": "$STATUS",
  "load_1min": "$LOAD_1MIN",
  "load_5min": "$LOAD_5MIN",
  "load_15min": "$LOAD_15MIN",
  "memory_usage_pct": "$MEM_RATE",
  "disk_usage_pct": "$DISK_USAGE",
  "cpu_usage_pct": "$CPU_IDLE",
  "services_ok": "$SERVICES_OK",
  "network_ok": "$NETWORK_OK",
  "fs_readonly": "$FS_READONLY",
  "timestamp": "$(date +%Y-%m-%dT%H:%M:%S%z)"
}
EOF
