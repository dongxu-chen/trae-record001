# Prometheus Alert Tester

一个用于测试Prometheus告警规则的Go工具，支持模拟指标、验证告警表达式、检查语法错误，并生成详细的测试报告。

## ✨ 功能特性

### 1. 范围向量和瞬时向量支持
- 正确处理PromQL范围向量(range vector)查询
- 支持瞬时向量(instant vector)评估
- 内置内存存储实现时序数据查询

### 2. for语句连续触发窗口
- 模拟Prometheus的`for`等待窗口行为
- 支持Pending状态到Firing状态的转换
- 可配置的告警持续时间阈值

### 3. Resolve Delay模拟
- 实现告警自动恢复(resolve)逻辑
- 可配置的恢复延迟时间
- 追踪告警触发和恢复时间点

### 4. 自定义模拟指标
- 支持自定义模拟时长(`-duration`)
- 支持自定义评估步长(`-step`)
- 支持从JSON文件加载自定义指标
- API支持添加带时间序列的指标值

### 5. 详细的测试报告
- 通过率统计(Pass Rate)
- 失败规则详情
- 告警状态分类(Firing/Pending/Resolved)
- 平均告警持续时间
- 详细的语法错误信息
- 控制台汇总输出 + JSON文件报告

## 📦 安装

```bash
# 克隆项目
git clone <repository-url>
cd prometheus-alert-tester

# 下载依赖
go mod tidy

# 编译
go build -o promalert
```

## 🚀 使用方法

### 基本用法
```bash
# 使用默认指标测试告警规则
./promalert -rules examples/rules.yaml

# 启用详细输出
./promalert -rules examples/rules.yaml -verbose

# 指定自定义指标文件
./promalert -rules examples/rules.yaml -metrics examples/metrics.json
```

### 高级配置
```bash
# 自定义模拟时长和步长
./promalert -rules examples/rules.yaml -duration 30m -step 30s

# 自定义resolve delay
./promalert -rules examples/rules.yaml -resolve-delay 10m

# 指定输出报告文件
./promalert -rules examples/rules.yaml -output my_report.json
```

### 完整参数列表
| 参数 | 说明 | 默认值 |
|------|------|--------|
| `-rules` | Prometheus告警规则文件路径 (必需) | - |
| `-metrics` | 指标模拟JSON文件路径 | 内置默认指标 |
| `-output` | 测试报告输出路径 | `alert_test_report.json` |
| `-verbose` | 启用详细输出 | `false` |
| `-duration` | 模拟时长 | `10m` |
| `-step` | 评估步长间隔 | `15s` |
| `-resolve-delay` | 告警恢复延迟 | `5m` |

## 📁 项目结构

```
prometheus-alert-tester/
├── main.go                    # 主程序入口
├── go.mod                     # Go模块配置
├── README.md                  # 本文档
├── internal/
│   ├── alert/
│   │   └── validator.go       # 告警验证核心逻辑
│   ├── metrics/
│   │   └── simulator.go       # 指标模拟器
│   └── report/
│       └── report.go          # 报告生成器
└── examples/
    ├── rules.yaml             # 示例告警规则
    └── metrics_example.json   # 示例指标配置
```

## 📊 示例输出

### 控制台报告
```
============================================================
Prometheus Alert Tester - Test Report
============================================================
Test Time: 2024-01-15T10:30:00+08:00
Rules File: examples/rules.yaml
Test Duration: 1.234s

--- Statistics ---
Total Rules: 4
Passed: 4 (100.00%)
Failed: 0

Alerts Firing: 1
Alerts Pending: 1
Alerts Resolved: 0
Average Firing Duration: 120.50 seconds

--- Active Alerts ---
  - InstanceDown: firing (value: 1.00)
  - HighMemoryUsage: pending (value: 0.87)
============================================================

Report saved to: alert_test_report.json
```

### JSON报告结构
```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "rules_file": "examples/rules.yaml",
  "test_duration_seconds": 1234000000,
  "time_range": {
    "start": "2024-01-15T10:20:00Z",
    "end": "2024-01-15T10:30:00Z",
    "step": "15s"
  },
  "statistics": {
    "total_rules": 4,
    "passed_rules": 4,
    "failed_rules": 0,
    "pass_rate": 100,
    "alerts_firing": 1,
    "alerts_pending": 1,
    "alerts_resolved": 0,
    "average_firing_time_seconds": 120.5
  },
  "alerts": [...]
}
```

## 🔧 核心API

### Metrics Simulator
```go
sim := metrics.NewSimulator()
sim.SetTimeRange(startTime, endTime)
sim.SetStep(15 * time.Second)
sim.AddMetricWithConstantValue("up", labels, 1)
sim.AddMetricWithTransitions("up", labels, transitions)
```

### Alert Validator
```go
validator := alert.NewValidator()
validator.SetResolveDelay(5 * time.Minute)
validator.SetEvalTimestamps(timestamps)
validator.LoadRules("rules.yaml")
syntaxErrors := validator.CheckSyntax()
evals, err := validator.EvaluateRules(timeSeries)
alerts := validator.GenerateAlertResults(evals)
```

## 📝 指标配置文件格式

```json
{
  "start_time": "2024-01-15T10:00:00Z",
  "end_time": "2024-01-15T10:10:00Z",
  "step": "15s",
  "metrics": [
    {
      "name": "up",
      "labels": {
        "job": "api_server",
        "instance": "localhost:8080"
      },
      "values": [
        {
          "timestamp": "2024-01-15T10:00:00Z",
          "value": 1
        },
        {
          "timestamp": "2024-01-15T10:05:00Z",
          "value": 0
        }
      ]
    }
  ]
}
```

## 🏗️ 技术栈

- Go 1.19+
- Prometheus Client Libraries
  - `github.com/prometheus/prometheus/model/labels`
  - `github.com/prometheus/prometheus/model/rulefmt`
  - `github.com/prometheus/prometheus/promql`
  - `github.com/prometheus/prometheus/storage`
- YAML: `gopkg.in/yaml.v3`

## 📄 License

MIT
