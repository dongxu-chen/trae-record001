# eBPF无侵入MySQL死锁检测系统使用说明

## 概述

本系统使用eBPF（Extended Berkeley Packet Filter）技术，在内核层面监控锁等待事件，实现对MySQL死锁的**零侵入**、**实时**检测。

### 核心特性

- ✅ **零侵入**：无需修改MySQL源码，无需重启MySQL
- ✅ **实时检测**：微秒级响应，发现死锁立即告警
- ✅ **低开销**：内核态运行，性能损耗极低
- ✅ **多锁类型**：支持FUTEX、MUTEX、RWSEM
- ✅ **Prometheus集成**：内置指标输出，支持Grafana可视化
- ✅ **钉钉告警**：检测到死锁立即推送通知

## 系统要求

### 操作系统
- Linux Kernel 4.15+ (推荐5.4+)
- 开启CONFIG_BPF、CONFIG_BPF_SYSCALL等内核配置

### 依赖安装

#### Ubuntu/Debian
```bash
sudo apt-get update
sudo apt-get install -y bcc-tools libbcc-examples linux-headers-$(uname -r)
sudo pip3 install bcc psutil prometheus_client
```

#### CentOS/RHEL
```bash
sudo yum install -y bcc-tools bcc-devel kernel-headers-$(uname -r)
sudo pip3 install bcc psutil prometheus_client
```

## 快速开始

### 1. 启动eBPF检测器

```bash
# 需要root权限
sudo python3 main.py ebpf
```

### 2. 指定MySQL进程监控

```bash
# 自动发现MySQL进程
sudo python3 main.py ebpf

# 或手动指定MySQL PID
sudo python3 main.py ebpf --pid 1234 5678
```

### 3. 监控所有进程（不只是MySQL）

```bash
sudo python3 main.py ebpf --no-mysql-filter
```

## 核心组件说明

### 1. eBPF探针 (`ebpf_probes.c`)

内核态C程序，挂载多个kprobe/tracepoint：

- **sys_enter_futex** / **sys_exit_futex**: 捕获futex锁等待
- **mutex_lock** / **mutex_lock_ret**: 捕获互斥锁等待
- **down_read** / **down_write**: 捕获读写信号量等待

### 2. 用户态检测器 (`ebpf_deadlock_detector.py`)

Python程序，负责：

- 通过BPF ring buffer接收内核事件
- 维护锁等待图（Wait-for Graph）
- 使用DFS检测环路（死锁）
- 输出Prometheus指标
- 触发钉钉告警

### 3. 死锁检测算法

```
事件触发:
    当线程A开始等待锁X时
        构建等待边: A → X
        获取锁X的持有者: B, C, ...
        为每个持有者构建持有边: X → B
        从A开始DFS遍历等待图
        如果发现环路 → 死锁!
```

## Prometheus指标

指标默认暴露在 `http://localhost:9091/metrics`

| 指标名称 | 类型 | 说明 |
|---------|------|------|
| `mysql_lock_events_total` | Counter | 锁等待事件总数 |
| `mysql_lock_wait_duration_seconds` | Histogram | 锁等待时长分布 |
| `mysql_waiting_threads` | Gauge | 当前等待锁的线程数 |
| `mysql_held_locks` | Gauge | 当前持有的锁数量 |
| `mysql_deadlocks_detected_total` | Counter | 检测到的死锁总数 |

## Grafana仪表盘

### 导入仪表盘

1. 打开Grafana → Create → Import
2. 上传 `grafana_dashboard.json` 或粘贴内容
3. 选择Prometheus数据源
4. 点击Import

### 仪表盘包含的面板

1. **死锁总数**：统计面板
2. **锁事件速率**：5分钟滑动窗口速率
3. **等待线程数**：实时Gauge
4. **持有锁数量**：实时Gauge
5. **死锁检测速率**：1小时趋势
6. **锁等待和持有趋势**：双Y轴对比
7. **各类型锁事件分布**：柱状图对比
8. **锁等待时长百分位数**：P50/P90/P99
9. **各类型锁等待时长P99**：分类对比

## 告警配置

### 钉钉告警

在 `.env` 中配置：

```bash
DINGTALK_ENABLED=true
DINGTALK_WEBHOOK=https://oapi.dingtalk.com/robot/send?access_token=your_token
DINGTALK_SECRET=your_secret
```

检测到死锁时，告警内容包含：
- 死锁发生时间
- 涉及的线程ID列表
- 完整的等待链详情
- 建议的处理方案

### Prometheus告警规则示例

```yaml
groups:
- name: mysql_deadlock_alerts
  rules:
  - alert: HighDeadlockRate
    expr: rate(mysql_deadlocks_detected_total[5m]) > 0.1
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "MySQL死锁频率过高"
      description: "过去5分钟平均每分钟死锁次数超过0.1次"

  - alert: HighLockWaitTime
    expr: histogram_quantile(0.99, rate(mysql_lock_wait_duration_seconds_bucket[5m])) > 0.1
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: "锁等待时间过长"
      description: "P99锁等待时间超过100ms"
```

## 性能影响

### 基准测试

| 场景 | CPU开销 | 内存开销 |
|------|---------|---------|
| 空闲系统 | < 1% | ~ 50MB |
| 高并发MySQL | 1-3% | ~ 80MB |

### 性能优化建议

1. **只监控MySQL进程**：避免无关进程的事件处理开销
2. **调整BPF缓冲区大小**：根据实际负载调整
3. **过滤高频短事件**：在BPF层过滤极短的锁等待

## 故障排查

### 常见问题

#### 1. "bpf module not found"
```
原因: bcc Python绑定未正确安装
解决: sudo pip3 install bcc --upgrade
```

#### 2. "Permission denied"
```
原因: 需要root权限运行eBPF程序
解决: 使用sudo运行
```

#### 3. "kprobe attach failed"
```
原因: 内核符号不匹配
解决: 
  - 检查内核版本: uname -r
  - 确认内核符号存在: cat /proc/kallsyms | grep mutex_lock
  - 尝试使用tracepoint替代kprobe
```

#### 4. 没有检测到任何事件
```
排查步骤:
  1. 确认有MySQL进程在运行: ps aux | grep mysqld
  2. 确认MySQL有锁竞争: show processlist
  3. 检查是否指定了正确的PID过滤
  4. 查看dmesg是否有BPF相关错误
```

### 调试模式

添加调试输出，查看原始事件：

```python
# 在ebpf_deadlock_detector.py的handle_lock_event中添加
print(f"Event: pid={event.pid}, tid={event.tid}, lock={hex(event.lock_addr)}, type={event.lock_type}")
```

## 架构设计

### 数据流向

```
MySQL进程 → 内核锁原语 → eBPF探针 → BPF ring buffer → Python用户态
                                                                 ↓
                                                         等待图构建 & DFS检测
                                                                 ↓
                                                         ┌───────────────┐
                                                         │ 发现死锁?     │
                                                         └───┬───────┬───┘
                                                             ↓ Yes   ↓ No
                                                    ┌──────────┐   ┌────────┐
                                                    │ 钉钉告警 │   │ 统计更新│
                                                    └──────────┘   └────────┘
                                                             ↓
                                                        Prometheus指标
                                                             ↓
                                                        Grafana可视化
```

### 关键数据结构

```c
// 内核态 - 锁等待事件
struct lock_event {
    u64 timestamp;         // 纳秒级时间戳
    u32 pid;               // 进程ID
    u32 tid;               // 线程ID
    u64 lock_addr;         // 锁地址
    u32 lock_type;         // 1=FUTEX, 2=MUTEX, 3=RWSEM
    u32 event_type;        // 1=WAIT_START, 2=WAIT_END
    u64 wait_duration;     // 等待时长(ns)
    char comm[16];         // 进程名
};
```

```python
# 用户态 - 等待图
class WaitGraph:
    waiting_for: Dict[int, Set[int]]  # tid -> 锁地址集合
    holders: Dict[int, Set[int]]      # 锁地址 -> tid集合
    holds: Dict[int, Set[int]]        # tid -> 持有的锁集合
    
    def detect_cycle(self, start_tid) -> Optional[List[int]]:
        # DFS环路检测...
```

## 扩展开发

### 添加新的锁类型监控

1. 在 `ebpf_probes.c` 中添加新的kprobe
2. 在 `LOCK_TYPE_*` 枚举中添加新类型
3. 在用户态处理函数中添加对应的事件处理

### 自定义告警逻辑

继承 `EBPFDeadlockDetector` 并重写 `_handle_deadlock` 方法：

```python
class CustomDetector(EBPFDeadlockDetector):
    def _handle_deadlock(self, cycle, trigger_event):
        super()._handle_deadlock(cycle, trigger_event)
        # 添加自定义逻辑: 写入日志、调用其他API等
```

## 许可证

本项目遵循原项目许可证。

## 贡献

欢迎提交Issue和PR！
