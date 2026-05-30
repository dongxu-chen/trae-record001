# Prometheus 指标数据降采样工具

一个功能完整的 Prometheus 指标数据降采样工具，支持对高分辨率指标数据进行降采样处理，显著降低存储成本，同时保留关键数据特征。

## 功能特性

- **多种聚合函数**：支持 avg、max、min、sum、count、p50、p90、p95、p99
- **多级降采样**：支持按分钟（1m）、5分钟（5m）、15分钟（15m）、小时（1h）、6小时（6h）、天（1d）降采样
- **查询透明**：内置查询代理，根据时间范围自动选择最合适的降采样级别
- **Thanos 集成**：支持通过 Remote Write 协议写入 Thanos Receiver
- **灵活的规则配置**：支持按指标匹配模式定义降采样规则
- **标签管理**：支持保留/删除特定标签，降低存储占用
- **保留策略**：支持为不同降采样级别设置数据保留周期
- **缓存机制**：查询结果缓存，提升查询性能
- **重试机制**：自动重试失败的降采样任务

## 架构设计

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Prometheus     │────▶│  降采样引擎     │────▶│  Thanos Receiver│
│  (原始数据)     │     │  (Downsampler)  │     │  (降采样数据)   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                 ▲
                                 │
                        ┌────────▼────────┐
                        │  查询代理       │
                        │  (透明访问)     │
                        └────────┬────────┘
                                 │
                        ┌────────▼────────┐
                        │  终端用户       │
                        └─────────────────┘
```

## 快速开始

### 1. 编译项目

```bash
go mod download
go build -o downsampler ./cmd/downsampler
```

### 2. 配置文件

复制示例配置并根据实际环境修改：

```bash
cp configs/config.yaml configs/my-config.yaml
```

### 3. 运行模式

#### 守护进程模式（持续运行）

```bash
./downsampler --config configs/config.yaml
```

#### 单次运行模式（执行一次降采样）

```bash
./downsampler --config configs/config.yaml --once
```

#### 查看状态

```bash
./downsampler --config configs/config.yaml --status
```

## 配置说明

### 全局配置

```yaml
global:
  log_level: info           # 日志级别: debug, info, warn, error
  namespace: downsampled    # 降采样指标前缀
```

### Prometheus 配置

```yaml
prometheus:
  address: "http://localhost:9090"  # Prometheus 地址
  timeout: 30s                      # 查询超时
  query_concurrency: 5              # 并发查询数
```

### Thanos 配置

```yaml
thanos:
  enabled: true                     # 是否启用 Thanos 写入
  address: "localhost:10901"        # Thanos Receiver 地址
  timeout: 30s                      # 写入超时
  batch_size: 1000                  # 批处理大小
  use_tls: false                    # 是否使用 TLS
  external_labels:                  # 外部标签
    cluster: production
```

### 调度器配置

```yaml
scheduler:
  interval: 5m                      # 执行间隔
  lookback: 1h                      # 每次处理的时间范围
  max_retries: 3                    # 失败重试次数
  retry_interval: 10s               # 重试间隔
```

### 查询代理配置

```yaml
proxy:
  enabled: true                     # 是否启用查询代理
  listen_address: ":9091"           # 代理监听地址
  cache_ttl: 5m                     # 结果缓存 TTL
  auto_select_level: true           # 自动选择降采样级别
```

### 降采样规则

```yaml
metric_rules:
  - name: http_requests                              # 规则名称
    match: '{__name__=~"http_requests_.*"}'          # 指标匹配模式
    aggregations:                                     # 聚合函数列表
      - avg
      - sum
      - max
      - p99
    downsampling_levels:                              # 降采样级别
      - 1m
      - 5m
      - 15m
      - 1h
    retention_policies:                               # 保留策略
      - level: raw
        retention: 72h
      - level: 1m
        retention: 7d
      - level: 1h
        retention: 365d
    preserve_labels:                                  # 保留的标签
      - method
      - status
      - handler
    drop_labels:                                      # 删除的标签
      - instance_id
```

## 降采样级别自动选择逻辑

查询代理会根据以下规则自动选择最合适的降采样级别：

| 时间范围          | 推荐降采样级别 |
|-------------------|---------------|
| < 1小时           | raw（原始）   |
| 1小时 - 6小时     | 1m            |
| 6小时 - 24小时    | 15m           |
| > 24小时          | 1h            |

同时也会根据查询步长（step）进行匹配，选择最合适的粒度。

## 聚合函数说明

| 函数  | 说明                                    | 适用场景              |
|-------|-----------------------------------------|-----------------------|
| avg   | 平均值                                  | 使用率、延迟等常规指标 |
| max   | 最大值                                  | 峰值监控              |
| min   | 最小值                                  | 资源空闲分析          |
| sum   | 求和                                    | 计数型指标、流量      |
| count | 样本数量                                | 数据点统计            |
| p50   | 50分位数（中位数）                      | 延迟分布              |
| p90   | 90分位数                                | 长尾延迟监控          |
| p95   | 95分位数                                | 性能瓶颈分析          |
| p99   | 99分位数                                | 最差情况分析          |

## 查询代理 API

### 范围查询

```bash
curl -X POST http://localhost:9091/api/v1/query_range \
  -H "Content-Type: application/json" \
  -d '{
    "query": "http_requests_total{status=\"200\"}",
    "start": "2024-01-01T00:00:00Z",
    "end": "2024-01-02T00:00:00Z",
    "step": "15m"
  }'
```

### 即时查询

```bash
curl -X POST http://localhost:9091/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "http_requests_total",
    "time": "2024-01-01T12:00:00Z"
  }'
```

### 状态查询

```bash
curl http://localhost:9091/api/v1/status
```

## 降采样指标命名规则

降采样后的指标命名格式为：

```
<namespace>:<original_metric>:<aggregation>:<level>
```

示例：
- `downsampled:http_requests_total:avg:1m`
- `downsampled:http_requests_total:p99:1h`

同时会自动添加以下标签：
- `ds_level`: 降采样级别（1m, 5m, 1h 等）
- `ds_agg`: 聚合函数（avg, p99 等）

## 存储成本估算

假设原始数据采集频率为 15秒：

| 降采样级别 | 数据点/小时 | 压缩比 | 每年存储（1指标） |
|-----------|------------|--------|-------------------|
| raw (15s) | 240        | 1x     | ~1.75 MB          |
| 1m        | 60         | 4x     | ~0.44 MB          |
| 5m        | 12         | 20x    | ~0.09 MB          |
| 15m       | 4          | 60x    | ~0.03 MB          |
| 1h        | 1          | 240x   | ~0.007 MB         |

**实际收益**：对于1000个指标，保留1年：
- 原始数据：~1.7 GB
- 全级别降采样：~2.4 MB（节省 99.8%）

## 目录结构

```
.
├── cmd/
│   └── downsampler/
│       └── main.go           # 主程序入口
├── pkg/
│   ├── config/               # 配置模块
│   │   └── config.go
│   ├── prometheus/           # Prometheus 客户端
│   │   └── client.go
│   ├── downsampling/         # 降采样引擎
│   │   └── engine.go
│   ├── thanos/               # Thanos 集成
│   │   └── writer.go
│   └── proxy/                # 查询代理
│       └── proxy.go
├── configs/
│   └── config.yaml           # 示例配置
├── go.mod
└── README.md
```

## 最佳实践

1. **合理设置降采样级别**：根据业务需求选择必要的级别，避免过度降采样
2. **保留关键标签**：只保留查询必需的标签，大幅降低存储
3. **错开执行时间**：多实例部署时，调整 `lookback` 和 `interval` 避免冲突
4. **监控降采样效果**：关注 `reduction` 日志，评估压缩比
5. **渐进式部署**：先对非关键指标启用，验证效果后再推广

## 故障排查

### 问题：查询不到降采样数据

**检查点**：
1. 确认 Thanos Receiver 是否正常运行
2. 检查日志中是否有写入错误
3. 验证降采样指标命名是否正确
4. 查看 `ds_level` 和 `ds_agg` 标签是否正确

### 问题：降采样任务失败

**检查点**：
1. 确认 Prometheus 连接正常
2. 检查查询语句是否合法
3. 查看网络连接和超时设置
4. 增加 `log_level: debug` 查看详细日志

### 问题：查询代理没有选择降采样数据

**检查点**：
1. 确认 `auto_select_level: true`
2. 检查查询时间范围是否触发降级阈值
3. 查看代理日志中的 `Query rewritten` 信息

## 许可证

MIT License
