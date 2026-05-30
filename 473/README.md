# Redis 内存碎片整理工具

一个功能完整的 Redis 内存碎片管理工具，支持单机和集群模式，自动检测并整理内存碎片，不影响服务正常运行。

## 功能特性

- ✅ **碎片率分析** - 实时监控 Redis 内存碎片率
- ✅ **自动整理** - 碎片率过高时自动执行 MEMORY PURGE
- ✅ **集群支持** - 完整支持 Redis Cluster 模式
- ✅ **前后对比** - 详细的整理前后内存对比报告
- ✅ **定时执行** - 基于 Celery 的定期自动检查和整理
- ✅ **统计分析** - 碎片率历史趋势、整理效果统计
- ✅ **日报生成** - 每日自动生成碎片状态报告
- ✅ **命令行工具** - 简洁易用的 CLI 界面
- ✅ **版本检测降级** - 根据 Redis 版本自动选择最优整理方法
- ✅ **多整理策略** - MEMORY PURGE / 重启从节点 / 主从切换
- ✅ **并行执行** - 支持多节点并行整理，提高效率
- ✅ **性能监控** - P50/P99 延迟、QPS、命中率实时监控
- ✅ **碎片原因分析** - 识别导致高碎片的业务模式
- ✅ **预测性整理** - 基于历史数据预测碎片率趋势，提前处理
- ✅ **成本收益分析** - 评估整理的资源消耗与收益

## 技术栈

- **Python 3.8+**
- **redis-py** - Redis 客户端
- **redis-py-cluster** - Redis Cluster 支持
- **Celery** - 分布式任务队列
- **NumPy/Pandas** - 统计分析
- **python-dotenv** - 环境变量管理

## 安装

1. 克隆项目
2. 安装依赖：

```bash
pip install -r requirements.txt
```

3. 复制环境变量配置：

```bash
cp .env.example .env
```

4. 根据实际情况修改 `.env` 文件

## 配置说明

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `REDIS_MODE` | Redis 模式：`standalone` 或 `cluster` | `standalone` |
| `REDIS_HOST` | Redis 主机（单机模式） | `localhost` |
| `REDIS_PORT` | Redis 端口（单机模式） | `6379` |
| `REDIS_PASSWORD` | Redis 密码 | 无 |
| `REDIS_DB` | Redis 数据库编号 | `0` |
| `REDIS_CLUSTER_NODES` | 集群节点列表，逗号分隔 | 无 |
| `FRAGMENTATION_THRESHOLD` | 碎片率阈值，超过触发整理 | `1.5` |
| `MIN_MEMORY_MB` | 最小内存（MB），低于此值跳过整理 | `1024` |
| `CELERY_BROKER_URL` | Celery Broker URL | `redis://localhost:6379/1` |
| `CELERY_RESULT_BACKEND` | Celery 结果后端 | `redis://localhost:6379/1` |
| `SCHEDULE_INTERVAL_MINUTES` | 定时检查间隔（分钟） | `60` |
| `STORAGE_REDIS_URL` | 统计数据存储 Redis | `redis://localhost:6379/2` |
| `PURGE_TIMEOUT` | PURGE 操作超时（秒） | `300` |

## 快速开始

### 命令行使用

```bash
# 检查内存碎片状态
python main.py check

# 整理高碎片节点
python main.py defrag-high

# 整理指定节点
python main.py defrag-node --node-id standalone

# 整理所有节点
python main.py defrag-all

# 查看统计信息
python main.py stats --hours 24
```

### 定时任务模式

```bash
# 启动 Celery Worker
python main.py worker --concurrency 2

# 启动 Celery Beat（定时调度）
python main.py beat
```

## 模块说明

### 1. redis_connection.py - Redis 连接管理

- `RedisConnectionManager` - 统一的连接管理器
- 自动切换单机/集群模式
- 支持获取所有 master 节点

### 2. memory_analyzer.py - 内存分析

- `MemoryInfo` - 内存信息数据类
- `MemoryAnalyzer` - 碎片分析器
  - `get_all_memory_info()` - 获取所有节点内存信息
  - `is_fragmentation_high()` - 判断碎片率是否过高
  - `get_cluster_fragmentation_summary()` - 集群汇总

### 3. memory_defrag.py - 内存整理

- `DefragResult` - 整理结果数据类
- `MemoryDefragmenter` - 碎片整理器
  - `defrag_node()` - 整理单个节点
  - `defrag_high_fragmentation_nodes()` - 整理高碎片节点
  - `compare_before_after()` - 生成对比报告

### 4. statistics_analyzer.py - 统计分析

- `FragmentationTrend` - 碎片趋势数据类
- `StatisticsAnalyzer` - 统计分析器
  - `store_memory_snapshot()` - 存储内存快照
  - `get_memory_history()` - 获取历史数据
  - `calculate_fragmentation_statistics()` - 计算统计指标
  - `generate_daily_report()` - 生成日报

### 5. tasks.py - Celery 任务

- `check_fragmentation()` - 检查碎片
- `defrag_node()` - 整理节点
- `defrag_high_fragmentation_nodes()` - 整理高碎片节点
- `periodic_defrag_check()` - 周期性检查并整理
- `daily_fragmentation_report()` - 每日报告

## 编程接口示例

```python
from redis_connection import RedisConnectionManager
from memory_analyzer import MemoryAnalyzer
from memory_defrag import MemoryDefragmenter
from statistics_analyzer import StatisticsAnalyzer

# 1. 检查碎片
connection_manager = RedisConnectionManager()
analyzer = MemoryAnalyzer(connection_manager)
summary = analyzer.get_cluster_fragmentation_summary()
print(f"Average fragmentation: {summary['avg_fragmentation_ratio']:.2f}")

# 2. 整理高碎片节点
defragmenter = MemoryDefragmenter(connection_manager)
results = defragmenter.defrag_high_fragmentation_nodes()
for result in results:
    if result.success:
        print(f"Saved {result.memory_saved_mb:.2f} MB on {result.host}")

# 3. 存储统计
stats_analyzer = StatisticsAnalyzer()
for mem_info in analyzer.get_all_memory_info():
    stats_analyzer.store_memory_snapshot(mem_info)

# 4. 获取历史趋势
trend = stats_analyzer.get_memory_history('node_id', hours=24)
print(f"Data points: {len(trend.fragmentation_ratios)}")
```

## 内存碎片率说明

### 什么是内存碎片率

碎片率 = `used_memory_rss` / `used_memory`

- **< 1.0**: 正常范围，部分内存被操作系统 swap
- **1.0 - 1.5**: 健康范围
- **1.5 - 2.0**: 需要关注
- **> 2.0**: 严重碎片化，建议整理

### MEMORY PURGE 说明

`MEMORY PURGE` 命令会：
1. 尝试清理 jemalloc 分配器中的脏页
2. 将未使用的内存归还给操作系统
3. 在后台执行，不阻塞正常请求
4. 执行时间取决于碎片程度（通常几秒到几分钟）

**注意**：该命令仅在 Redis 4.0+ 版本且使用 jemalloc 分配器时有效。

## 架构设计

```
┌─────────────────────────────────────────────────────────┐
│                     CLI / API Layer                     │
│  (main.py, example_usage.py)                            │
└────────────────────┬────────────────────────────────────┘
                     │
    ┌────────────────▼────────────────┐
    │        Celery Tasks             │
    │  (tasks.py)                     │
    └────────┬──────────────┬─────────┘
             │              │
┌────────────▼────┐   ┌────▼─────────────┐
│  MemoryAnalyzer │   │ MemoryDefrag     │
│  (碎片分析)     │   │ (碎片整理)       │
└────────┬────────┘   └────┬─────────────┘
         │                 │
    ┌────▼─────────────────▼────┐
    │  RedisConnectionManager   │
    │  (连接管理: 单机/集群)    │
    └────┬─────────────────────┘
         │
    ┌────▼─────────────────────┐
    │  StatisticsAnalyzer      │
    │  (历史存储/统计分析)      │
    └──────────────────────────┘
```

## 生产部署建议

1. **监控告警**：建议配合 Prometheus + Grafana 监控碎片率和 P99 延迟趋势
2. **执行窗口**：建议在业务低峰期执行碎片整理
3. **阈值调整**：根据业务场景调整 `FRAGMENTATION_THRESHOLD`，建议 1.3-1.8
4. **并发控制**：
   - 中小集群：并行模式，workers = CPU 核心数
   - 大集群或高负载：串行模式，避免资源争抢
5. **版本检查**：首次使用先运行 `check-versions` 确认整理策略
6. **性能基线**：建立整理前的性能基线，便于对比整理影响
7. **结果验证**：整理后验证碎片率下降和延迟变化
8. **降级策略**：低版本 Redis 建议配合编排系统实现自动重启

## 常见问题

### Q: 如何检查 Redis 版本支持的整理方法？

A: 运行版本检查命令：
```bash
python main.py check-versions
```

### Q: P99 延迟上升多少算正常？

A: MEMORY PURGE 通常会导致 P99 延迟上升 0.5-2ms，如果超过 5ms 建议：
- 降低并发数
- 在业务低峰期执行
- 考虑分批整理

### Q: 低版本 Redis 如何自动重启？

A: `SLAVE_RESTART` 策略需要配合外部编排系统：
- **K8s**: 配置 livenessProbe 或使用 Operator
- **systemd**: 配置 `systemctl restart redis` 钩子
- 建议先在从节点验证，再考虑主节点

### Q: 为什么碎片率会很高？

A: 频繁的增删操作会导致内存碎片化，特别是大量过期键删除时。可以运行 `python main.py analyze-causes` 识别具体原因。

### Q: 如何识别碎片的根本原因？

A: 使用碎片原因分析功能：
```bash
python main.py analyze-causes
```
可以识别：频繁删除、大量过期键、大键问题、高写入吞吐量等。

### Q: 什么是预测性整理？

A: 预测性整理基于历史数据预测碎片率趋势，在碎片率达到阈值前提前执行整理。这样可以：
- 避免碎片率过高
- 在业务低峰期提前处理
- 减少高负载时的性能影响

使用方法：
```bash
python main.py predictive-defrag --hours 24 --dry-run
```

### Q: 成本收益分析如何帮助决策？

A: 成本收益分析帮助评估：
- 预计能节省多少内存
- 整理需要多长时间
- 对 CPU 和延迟的影响
- 是否值得执行整理

建议整理前运行：
```bash
python main.py analyze-cost
```

### Q: MEMORY PURGE 会影响服务吗？

A: 不会。PURGE 操作在后台线程执行，不会阻塞正常请求。但在碎片严重时可能会占用一些 CPU。

### Q: 多久执行一次整理？

A: 取决于写入频率。一般建议每天检查一次，碎片率超过 1.5 时自动执行。也可以启用预测性整理模式，提前处理。

### Q: 集群模式下如何工作？

A: 工具会遍历所有 master 节点，对每个节点独立检查和整理。支持并行模式同时处理多个节点。

## License

MIT
