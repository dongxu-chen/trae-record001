# Prometheus Alert Tester - 项目结构说明

## 📁 完整目录结构

```
prometheus-alert-tester/
├── main.go                                    # 主程序入口
├── go.mod                                       # Go 模块配置
├── go.sum                                       # 依赖版本锁定
├── README.md                                    # 项目使用文档
├── PROJECT_STRUCTURE.md                          # 本文档
├── test_build.go                                # 构建测试文件
├── examples/                                     # 示例配置目录
│   ├── rules.yaml                              # Prometheus 告警规则示例
│   └── metrics_example.json                     # 指标模拟配置示例
│
└── internal/                                    # 内部包目录
    ├── alert/                                  # 告警规则验证模块
    │   └── validator.go                        # 告警验证核心逻辑
    │
    ├── metrics/                                # 指标模拟模块
    │   └── simulator.go                      # 时序指标模拟器
    │
    ├── report/                                 # 报告生成模块
    │   └── report.go                         # 测试报告生成器
    │
    └── enhancements/                          # 增强功能模块 (新添加)
        ├── silence.go                         # 告警静默管理
        ├── slo.go                            # SLO 烧毁率计算
        ├── thanos.go                         # Thanos 多集群支持
        └── templates.go                      # YAML 模板导出

```

---

## 📦 模块功能详解

### 1. main.go - 主程序

**功能说明：**
- 命令行参数解析
- 整合所有模块功能
- 流程控制和协调

**新增命令行参数：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `-export-templates | bool | false | 导出 Prometheus 规则模板 |
| `-templates-dir` | string | "templates" | 模板输出目录 |
| `-enable-slo` | bool | false | 启用 SLO 烧毁率计算 |
| `-slo-target` | float | 99.9 | SLO 可用性目标百分比 |
| `-enable-clusters` | bool | false | 启用多集群测试 |
| `-cluster-env` | string | "production" | 集群环境 (production/staging) |
| `-silences` | string | "" | 静默配置文件路径 |

---

### 2. internal/enhancements/silence.go - 告警静默管理

**核心功能：**
- 支持按时间段静默配置
- 按标签匹配静默规则
- 支持正则表达式匹配
- 支持创建/管理 API

**类型定义：**
```go
type Silence struct {
    ID        string
    Matchers  []Matcher
    StartsAt  time.Time
    EndsAt    time.Time
    CreatedBy string
    Comment   string
}

type Matcher struct {
    Name    string
    Value   string
    IsRegex bool
    IsNot   bool
}
```

**主要方法：**
- `NewSilenceManager()` - 创建静默管理器
- `AddSilence(s Silence)` - 添加静默规则
- `IsSilenced(labels, evalTime)` - 检查是否被静默
- `CreateSimpleSilence()` - 快速创建简单静默规则

---

### 3. internal/enhancements/slo.go - SLO 烧毁率计算

**核心功能：**
- 基于错误预算的烧毁率计算
- 多窗口烧毁率告警
- SLO 目标和实际达成率对比
- 预测预算耗尽时间

**类型定义：**
```go
type SLO struct {
    Name                string
    Description         string
    TargetPercent       float64
    Window              time.Duration
    TotalRequestsMetric string
    ErrorRequestsMetric string
}

type SLOResult struct {
    SLOName               string
    TargetPercent         float64
    ActualPercent       float64
    ErrorBudgetRemaining float64
    BurnRate             float64
    BurnRateStatus       string
    TimeUntilBudgetExhausted string
}
```

**烧毁率状态说明：**
- `healthy` - 烧毁率正常 (< 0.5x)
- `warning` - 烧毁率偏高 (0.5x - 1.0x)
- `critical` - 烧毁率过高 (1.0x - 2.0x)
- `exhausted` - 预算已耗尽 (> 2.0x)

**主要方法：**
- `NewSLOManager()` - 创建 SLO 管理器
- `EvaluateSLO(name, total, errors)` - 计算单个 SLO
- `GenerateMultiBurnRateAlerts()` - 生成多窗口烧毁率告警

---

### 4. internal/enhancements/thanos.go - Thanos 多集群支持

**核心功能：**
- 多集群配置管理
- 跨集群指标聚合
- 集群健康状态评估
- 集群差异比较

**类型定义：**
```go
type Cluster struct {
    Name       string
    Endpoint   string
    Labels     map[string]string
    Enabled    bool
    MetricPath string
}

type MultiClusterMetric struct {
    MetricName string
    Clusters   map[string]float64
    Total      float64
    Average    float64
    Max        float64
    Min        float64
}
```

**主要方法：**
- `NewThanosManager()` - 创建 Thanos 管理器
- `AddCluster(c Cluster)` - 添加集群配置
- `AggregateMetrics(metrics)` - 聚合跨集群指标
- `EvaluateClusterHealth(metrics)` - 评估集群健康状态
- `CreateProductionClusters()` - 创建生产环境集群配置
- `CreateStagingClusters()` - 创建测试环境集群配置

---

### 5. internal/enhancements/templates.go - YAML 模板导出

**核心功能：**
- 导出 Kubernetes 告警模板
- 导出主机监控告警模板
- SLO 烧毁率告警模板
- 聚合规则模板
- Alertmanager 配置模板
- 自动生成 README 文档

**导出的模板文件：**

| 1. **kubernetes-alerts.yaml**
   - Pod CrashLoop 检测
   - Pod 就绪状态检查
   - Deployment 副本不匹配告警
   - Job 失败告警
   - CPU 过度提交告警

2. **node-alerts.yaml**
   - CPU 高使用率告警 (>90%)
   - 内存高使用率告警 (>90%)
   - 磁盘高使用率告警 (>90%)
   - 主机不可达告警

3. **slo-alerts.yaml**
   - 多窗口烧毁率告警 (1h/6h/3d)
   - Page 级别告警 (14.4x)
   - Ticket 级别告警 (6x)

4. **aggregation-recording.yaml**
   - HTTP 请求率聚合
   - 错误率聚合
   - 成功率计算
   - CPU 利用率聚合
   - 集群可用率比率

5. **alertmanager-config.yaml**
   - Slack 通知配置
   - PagerDuty 集成配置
   - Email 通知配置

**主要方法：**
- `NewTemplateExporter(outputDir)` - 创建模板导出器
- `GenerateFullTemplateCollection(exporter)` - 生成完整模板集合
- `GenerateREADME(outputDir)` - 生成 README 文档

---

## 🎯 核心功能矩阵

| 功能模块 | 文件位置 | 状态 |
|---------|---------|------|
| 告警规则语法检查 | alert/validator.go | ✅ 完成 |
| 时序指标模拟 | metrics/simulator.go | ✅ 完成 |
| PromQL 表达式验证 | alert/validator.go | ✅ 完成 |
| 告警状态追踪 | alert/validator.go | ✅ 完成 |
| 告警静默管理 | enhancements/silence.go | ✅ 新增 |
| SLO 烧毁率计算 | enhancements/slo.go | ✅ 新增 |
| Thanos 多集群支持 | enhancements/thanos.go | ✅ 新增 |
| YAML 模板导出 | enhancements/templates.go | ✅ 新增 |
| 测试报告生成 | report/report.go | ✅ 完成 |

---

## 🔧 使用示例

### 示例 1: 导出告警规则模板

```bash
go run . -export-templates -templates-dir ./my-templates
```

**输出：**
```
Exporting Prometheus rule templates to: ./my-templates
Templates exported successfully!
Generated files in ./my-templates:
  - kubernetes-alerts.yaml
  - node-alerts.yaml
  - slo-alerts.yaml
  - aggregation-recording.yaml
  - alertmanager-config.yaml
  - README.md
```

### 示例 2: 启用 SLO 烧毁率计算

```bash
go run . -rules examples/rules.yaml -enable-slo -slo-target 99.5
```

### 示例 3: 多集群测试

```bash
go run . -rules examples/rules.yaml -enable-clusters -cluster-env staging
```

### 示例 4: 完整功能测试

```bash
go run . \
  -rules examples/rules.yaml \
  -metrics examples/metrics_example.json \
  -enable-slo \
  -slo-target 99.9 \
  -enable-clusters \
  -cluster-env production \
  -verbose
```

---

## 📊 报告输出字段说明

**新增报告字段：**

```json
{
  "statistics": {
    "total_rules": 10,
    "passed_rules": 9,
    "failed_rules": 1,
    "pass_rate": 90.0,
    "alerts_firing": 2,
    "alerts_pending": 1,
    "alerts_resolved": 0,
    "alerts_silenced": 1,
    "average_firing_time_seconds": 300,
    "slo_violations": 1
  },
  "silenced_alerts": ["HighMemoryUsage"],
  "slo_results": [
    {
      "slo_name": "API Availability",
      "target_percent": 99.9,
      "actual_percent": 99.8,
      "burn_rate": 2.0,
      "burn_rate_status": "critical"
    }
  ],
  "cluster_report": {
    "clusters": [...],
    "enabled_count": 4,
    "total_count": 4,
    "health_status": {
      "us-east-1": "healthy",
      "eu-central-1": "degraded"
    }
  }
}
```

---

## 🚀 下一步扩展方向

1. **Web UI 界面
2. **CI/CD 集成
3. **历史数据对比
4. **告警规则推荐
5. **自动化静默建议
6. **更多 SLO 指标类型支持
7. **Grafana 仪表板模板
8. **实时告警模拟

---

*文档版本: 2.0.0
最后更新: 2024-01-15*
