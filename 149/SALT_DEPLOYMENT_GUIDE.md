# SaltStack 秒级补丁管理系统 - 部署指南

## 🚀 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                   Salt Master (控制节点)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │   CLI 工具   │  │   Reactor    │  │  Redis 统计缓存   │   │
│  │              │  │  事件处理引擎  │  │                  │   │
│  └──────────────┘  └──────────────┘  └──────────────────┘   │
│                              ↓                               │
│                   ZeroMQ 消息总线 (4505/4506)                 │
└─────────────────────────────────────────────────────────────┘
                              ↓
    ┌───────────────────┬───────────────────┬───────────────┐
    │                   │                   │               │
┌───────────┐     ┌───────────┐     ┌───────────┐    ┌───────────┐
│  Minion 1 │     │  Minion 2 │     │  Minion 3 │... │ Minion N  │
│  (主机A)   │     │  (主机B)   │     │  (主机C)   │    │  (...)    │
└───────────┘     └───────────┘     └───────────┘    └───────────┘
```

## ✅ 核心功能特性

| 功能 | 说明 | 性能指标 |
|------|------|---------|
| ⚡ 秒级下发 | ZeroMQ 消息总线，并发无阻塞 | < 3秒 |
| 🚀 高并发 | 原生批量处理，支持万级节点 | 10,000+ minions |
| 🐦 金丝雀发布 | 1% → 5% → 15% → 30% → 60% → 100% | 可配置 |
| 🔄 自动回滚 | 异常率 >10% 自动触发回滚 | 实时检测 |
| 📊 实时监控 | 事件驱动，秒级状态更新 | 延迟 < 1秒 |
| 📢 企业通知 | 钉钉/企业微信 webhook | Markdown 格式 |

## 📦 目录结构

```
.
├── salt-patch-manager.sh          # CLI 主程序 (v2.0)
├── config/
│   └── salt-patch.conf            # 配置文件
├── salt/
│   ├── config/
│   │   ├── master.conf            # Master 配置
│   │   └── minion.conf            # Minion 配置
│   ├── states/                    # Salt States
│   │   ├── patch/
│   │   │   ├── scan.sls           # 补丁扫描
│   │   │   ├── install.sls        # 补丁安装
│   │   │   └── rollback.sls       # 补丁回滚
│   │   ├── canary/
│   │   │   └── deploy.sls         # 金丝雀编排
│   │   └── monitor/
│   │       ├── health.sls         # 健康检查
│   │       └── files/
│   │           └── health-check.sh
│   └── reactor/                   # 事件处理器
│       ├── patch_result.sls       # 补丁结果处理
│       └── health_check.sls       # 健康检查处理
├── reports/                       # 报表输出
└── logs/                          # 日志目录
```

---

## 🔧 快速部署步骤

### 步骤 1: 安装 Salt Master (控制节点)

```bash
# 安装 SaltStack
curl -L https://bootstrap.saltstack.com -o install_salt.sh
sudo sh install_salt.sh -M -P

# 安装 Redis (用于统计缓存)
yum install -y redis   # CentOS/RHEL
apt install -y redis   # Debian/Ubuntu

# 启动服务
systemctl enable --now redis
systemctl enable --now salt-master
```

### 步骤 2: 配置 Salt Master

```bash
# 备份原配置
cp /etc/salt/master /etc/salt/master.bak

# 使用项目配置
cp salt/config/master.conf /etc/salt/master.d/

# 重启 Master
systemctl restart salt-master
```

### 步骤 3: 部署 States 文件

```bash
# 复制 States 到 salt 根目录
cp -r salt/states/* /srv/salt/
cp -r salt/reactor/* /srv/reactor/

# 验证文件结构
ls -la /srv/salt/
```

### 步骤 4: 安装 Minion (被管节点)

```bash
# 所有被管节点执行
curl -L https://bootstrap.saltstack.com -o install_salt.sh
sudo sh install_salt.sh -P

# 配置 Master 地址
echo "master: your-salt-master-ip" >> /etc/salt/minion

# 启动 Minion
systemctl enable --now salt-minion
```

### 步骤 5: 接受 Minion 密钥

```bash
# 在 Master 上查看待接受的密钥
salt-key -L

# 接受所有密钥 (生产环境建议逐个确认)
salt-key -A -y

# 验证连通性
salt '*' test.ping
```

### 步骤 6: 部署 CLI 工具

```bash
# 赋予执行权限
chmod +x salt-patch-manager.sh

# 链接到系统路径
ln -s $(pwd)/salt-patch-manager.sh /usr/local/bin/salt-patch

# 验证安装
salt-patch help
```

---

## 🎯 使用示例

### 1. 扫描所有主机补丁状态

```bash
# 快速扫描（3秒内返回）
salt-patch scan

# 指定目标扫描
salt-patch scan --target "web-*"
```

### 2. 批量安装安全补丁

```bash
# 30% 并发批量，仅安全更新
salt-patch install --batch 30 --security-only

# 全量安装，自动重启
salt-patch install --batch 100 --auto-reboot
```

### 3. 金丝雀发布（推荐生产使用）

```bash
# 默认 1% 金丝雀比例 + 自动回滚
salt-patch canary

# 自定义 5% 金丝雀
salt-patch canary --canary-percent 5
```

### 4. 实时监控补丁状态

```bash
# 监控指定补丁ID
salt-patch monitor --patch-id 20240101_120000

# 刷新显示实时进度
```

### 5. 安全回滚

```bash
# 回滚指定补丁
salt-patch rollback --patch-id 20240101_120000
```

### 6. 发送钉钉/企业微信通知

```bash
# 钉钉通知
salt-patch notify \
  --webhook "https://oapi.dingtalk.com/robot/send?access_token=xxx" \
  --webhook-type dingtalk

# 企业微信通知
salt-patch notify \
  --webhook "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx" \
  --webhook-type wechat
```

---

## 🔄 金丝雀发布流程

```
阶段 0: 初始化
    ↓
阶段 1: 1% 节点 (金丝雀)
    ↓ 成功 → 健康检查
    ↓ 失败 → 停止 + 报警
阶段 2: 5% 节点
    ↓
阶段 3: 15% 节点
    ↓
阶段 4: 30% 节点
    ↓
阶段 5: 60% 节点
    ↓
阶段 6: 100% 节点
```

---

## 🚨 自动回滚触发条件

满足以下任意条件即触发自动回滚：

| 条件 | 阈值 | 说明 |
|------|------|------|
| 失败率 | >20% | 安装失败的主机比例 |
| 不健康率 | >10% | 健康检查失败的主机比例 |
| 响应超时 | >30秒 | 无响应的主机比例 |

---

## 📊 性能调优建议

### Master 配置优化

```yaml
# /etc/salt/master.d/performance.conf
worker_threads: 32
publisher_threads: 16
timeout: 5
gather_job_timeout: 10
max_event_size: 10485760
```

### 系统内核优化

```ini
# /etc/sysctl.conf
net.core.somaxconn = 65535
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
net.ipv4.tcp_max_syn_backlog = 8192
```

### 大型环境建议

| 节点规模 | 服务器配置 | 建议 |
|---------|-----------|------|
| < 100 | 4C8G | 单 Master |
| 100-1000 | 8C16G | 双 Master HA |
| 1000+ | 16C32G | Master 集群 + Redis 哨兵 |

---

## 🔍 故障排查

### 问题: Minion 不响应

```bash
# 检查 Master 日志
tail -f /var/log/salt/master

# 检查 Minion 状态
salt-run manage.status

# 重启失联 Minion
salt '*' saltutil.refresh_pillar
```

### 问题: Redis 连接失败

```bash
# 检查 Redis 状态
systemctl status redis
redis-cli ping

# 检查连接配置
grep redis /etc/salt/master
```

### 问题: 性能缓慢

```bash
# 检查队列长度
salt-run manage.up | wc -l

# 调整并发批量
salt-patch install --batch 10
```

---

## 📋 命令速查表

```bash
# 扫描
salt-patch scan                          # 全量扫描
salt-patch scan -t "db-*"                # 指定目标

# 安装
salt-patch install                       # 默认30%批量
salt-patch install -b 50                 # 50%批量
salt-patch install --auto-reboot         # 自动重启
salt-patch install --no-reboot           # 禁止自动重启

# 金丝雀
salt-patch canary                        # 1%默认比例
salt-patch canary --canary-percent 5     # 5%金丝雀

# 回滚
salt-patch rollback -p 20240101_120000

# 监控
salt-patch monitor -p 20240101_120000

# 通知
salt-patch notify --webhook URL --webhook-type dingtalk

# 状态
salt-patch status
```

---

## 📞 技术支持

如遇问题，请检查：

1. Salt Master/Minion 版本匹配 (3000+)
2. 防火墙端口开放 (4505, 4506)
3. 网络连通性和 DNS 解析
4. Redis 服务状态

---

**版本**: 2.0.0
**最后更新**: 2024-01
