# Kubernetes资源推荐工具

一个基于Python和Prometheus的Kubernetes资源智能推荐工具，使用VPA（垂直Pod自动扩缩容）算法分析历史资源使用数据，为Pod提供CPU和内存资源请求/限制的优化建议，并支持HPA（水平Pod自动扩缩容）的副本数推荐。

## ✨ 功能特性

- **垂直资源推荐 (VPA)**：基于历史使用数据推荐CPU/内存的requests和limits
- **水平资源推荐 (HPA)**：基于利用率推荐Deployment的副本数
- **置信区间计算**：提供90%/95%/99%置信区间，量化推荐可靠性
- **成本预估**：计算优化前后的成本差异，量化节省金额
- **多维度统计分析**：百分位数、偏度、峰度、变异系数等统计指标
- **异常检测**：自动识别资源使用中的异常值和尖峰
- **趋势预测**：基于指数平滑法预测未来资源使用趋势
- **多云支持**：支持AWS、GCP、Azure、阿里云、自建机房等多种成本模型
- **多种输出格式**：支持表格、JSON、YAML三种输出格式
- **演示模式**：无Prometheus环境也可体验完整功能

## 📦 安装

### 环境要求

- Python >= 3.9
- pip >= 21.0

### 安装步骤

```bash
# 克隆项目
git clone <repository-url>
cd k8s-resource-recommender

# 安装依赖
pip install -r requirements.txt

# 或使用setup.py安装
pip install -e .
```

## 🚀 快速开始

### 1. 查看命令帮助

```bash
# 查看所有可用命令
k8s-resource-recommender --help

# 查看子命令帮助
k8s-resource-recommender vpa --help
k8s-resource-recommender hpa --help
k8s-resource-recommender analyze --help
```

### 2. 演示模式（无需Prometheus）

```bash
# 垂直资源推荐演示
k8s-resource-recommender vpa -n default -p demo-pod

# 水平资源推荐演示
k8s-resource-recommender hpa -n default -d demo-deployment

# 综合分析演示
k8s-resource-recommender analyze -n default -d demo-app --cloud-provider aws

# 列出示例资源
k8s-resource-recommender list
```

### 3. 连接真实Prometheus

```bash
# 设置环境变量
export PROMETHEUS_URL="http://prometheus:9090"
export PROMETHEUS_TOKEN="your-token"  # 可选

# 或使用命令行参数
k8s-resource-recommender --prometheus-url http://prometheus:9090 \
  vpa -n default -p my-pod -d 7
```

## 📖 命令详解

### 垂直资源推荐 (vpa)

为单个Pod推荐CPU和内存资源。

```bash
k8s-resource-recommender vpa \
  -n <namespace> \
  -p <pod-name> \
  -d 7 \
  --workload-type stateless \
  --risk-tolerance medium \
  --output table
```

**参数说明：**
- `-n, --namespace`: Kubernetes命名空间
- `-p, --pod`: Pod名称
- `-d, --days`: 分析历史数据的天数，默认7天
- `-s, --step`: 数据采样间隔，默认1分钟
- `--workload-type`: 工作负载类型 (stateless/stateful/critical)
- `--risk-tolerance`: 风险容忍度 (low/medium/high)
- `--output`: 输出格式 (table/json/yaml)

### 水平资源推荐 (hpa)

为Deployment推荐副本数。

```bash
k8s-resource-recommender hpa \
  -n <namespace> \
  -d <deployment-name> \
  -a 7 \
  --cpu-target 70 \
  --memory-target 75 \
  --min-replicas 1 \
  --max-replicas 10
```

**参数说明：**
- `--cpu-target`: CPU目标利用率百分比，默认70%
- `--memory-target`: 内存目标利用率百分比，默认75%
- `--min-replicas`: 最小副本数，默认1
- `--max-replicas`: 最大副本数，默认10

### 综合分析 (analyze)

同时提供垂直和水平资源推荐及详细成本分析。

```bash
k8s-resource-recommender analyze \
  -n <namespace> \
  -d <deployment-name> \
  -a 7 \
  --cloud-provider aws \
  --output json
```

**参数说明：**
- `--cloud-provider`: 云服务提供商 (aws/gcp/azure/alibaba/onprem)

### 资源列表 (list)

列出Kubernetes中的Pods和Deployments。

```bash
k8s-resource-recommender list -n default --resource-type all
```

## 🔧 配置文件

可以使用 `config.yaml` 配置默认参数：

```yaml
prometheus:
  url: "http://localhost:9090"
  token: null
  verify_ssl: true

vpa:
  cpu_percentile: 85.0
  memory_percentile: 95.0
  safety_margin_factor: 1.15

hpa:
  cpu_target_utilization: 70.0
  memory_target_utilization: 75.0

cost:
  cloud_provider: "aws"
  cpu_cost_per_core_per_hour: 0.023
  memory_cost_per_gb_per_hour: 0.003
```

## 📊 输出示例

### 垂直资源推荐输出

```
╭─────────────────────────────────────────────────────────────────────╮
│                      垂直资源推荐 (VPA)                              │
│ 命名空间: default | Pod: demo-pod | 分析周期: 7天                    │
╰─────────────────────────────────────────────────────────────────────╯

╭─────────────────────────────────────────────────────────────────────╮
│                         资源推荐详情                                  │
├──────────┬──────────┬──────────┬──────────┬──────────────┬──────────┤
│ 资源类型  │ 当前请求  │ 推荐请求  │ 推荐限制  │ 置信区间      │ 置信度   │
├──────────┼──────────┼──────────┼──────────┼──────────────┼──────────┤
│ CPU      │ 1.000 cores │ 477.3m  │ 715.9m   │ 376.2m ~ 578.5m │ 89%      │
│ 内存     │ 2.00 Gi   │ 1.40 Gi  │ 2.10 Gi  │ 1.31 Gi ~ 1.50 Gi │ 94%     │
╰──────────┴──────────┴──────────┴──────────┴──────────────┴──────────╯

╭─────────────────────────────────────────────────────────────────────╮
│                          成本分析                                   │
├──────────┬────────────┬────────────┬───────────────────────────────┤
│ 项目     │ 当前 (每月) │ 推荐 (每月) │ 节省 (每月)                   │
├──────────┼────────────┼────────────┼───────────────────────────────┤
│ CPU成本  │ $16.80     │ $8.03      │ $+8.77                        │
│ 内存成本 │ $14.60     │ $10.22     │ $+4.38                        │
│ 总计     │ $31.40     │ $18.25     │ $+13.15 (+41.9%)              │
╰──────────┴────────────┴────────────┴───────────────────────────────╯

╭─────────────────────────────────────────────────────────────────────╮
│ 🎉 预计每月节省 $13.15 (41.9%)                                     │
│ 年度预计节省: $157.80                                              │
╰─────────────────────────────────────────────────────────────────────╯
```

## 🧠 算法原理

### VPA算法核心思想

1. **数据采集**：从Prometheus获取Pod的CPU和内存历史使用数据
2. **数据清洗**：去除异常值、填充缺失数据、处理时间序列对齐
3. **统计分析**：
   - 计算P50/P80/P90/P95/P99等多个百分位数
   - 计算均值、中位数、标准差、变异系数
   - 计算90%/95%/99%置信区间
4. **推荐计算**：
   - CPU使用P85百分位数作为基准值
   - 内存使用P95百分位数作为基准值
   - 根据工作负载类型和风险容忍度应用安全边际
   - 限制设置为请求的1.5倍
5. **平滑处理**：考虑当前配置，避免剧烈变动

### HPA算法核心思想

1. **利用率计算**：基于目标利用率计算所需副本数
2. **多维度评估**：
   - 基于均值的激进推荐
   - 基于P90/P95/P99的保守推荐
   - 基于置信区间的范围推荐
3. **加权融合**：对不同百分位数的推荐结果进行加权
4. **稳定性控制**：基于历史副本数波动进行平滑处理
5. **边界约束**：确保推荐值在min/max副本数范围内

### 置信度计算

置信度基于以下四个维度加权计算：
- 数据点数量（25%）
- 数据持续时间（25%）
- 置信区间宽度（25%）
- 使用稳定性（25%）

## 📈 成本计算

### 多云价格参考（美元）

| 云服务商 | CPU (每核每小时) | 内存 (每GB每小时) |
|---------|-----------------|------------------|
| AWS     | $0.023          | $0.003           |
| GCP     | $0.020          | $0.0025          |
| Azure   | $0.021          | $0.0027          |
| 阿里云   | $0.018          | $0.002           |
| 自建机房 | $0.010          | $0.0015          |

### 成本公式

- CPU月度成本 = CPU核数 × 每核每小时价格 × 730小时
- 内存月度成本 = 内存GB数 × 每GB每小时价格 × 730小时

## 🔍 Prometheus指标要求

工具需要以下Prometheus指标：

```
# CPU使用率
container_cpu_usage_seconds_total

# 内存使用量
container_memory_working_set_bytes

# 资源请求
kube_pod_container_resource_requests

# 资源限制
kube_pod_container_resource_limits

# Pod信息
kube_pod_info

# Deployment信息
kube_deployment_created
kube_deployment_spec_replicas
```

## 🛠️ 开发

### 项目结构

```
k8s_resource_recommender/
├── __init__.py
├── prometheus_client.py    # Prometheus API客户端
├── data_collector.py       # 数据采集和预处理
├── statistics_analyzer.py  # 统计分析模块
├── vpa_recommender.py      # VPA垂直推荐算法
├── hpa_recommender.py      # HPA水平推荐算法
├── cost_estimator.py       # 成本计算模块
├── demo_data_generator.py  # 演示数据生成器
└── cli.py                  # 命令行接口
```

### 核心类关系

```
PrometheusClient
    ↓
DataCollector → PodResourceData / DeploymentResourceData
    ↓
StatisticsAnalyzer → ResourceStatistics
    ↓
VPARecommender / HPARecommender
    ↓
CostEstimator → CostAnalysis
    ↓
CLI (rich output / JSON / YAML)
```

## 📝 最佳实践

### 1. 数据周期建议

- **日常优化**：建议使用7天数据
- **月度评估**：建议使用30天数据
- **年度规划**：建议使用90天数据

### 2. 工作负载类型选择

| 工作负载类型 | 适用场景 | 安全边际 |
|-----------|---------|---------|
| stateless | Web服务、API网关、无状态应用 | 1.2x ~ 1.5x |
| stateful | 数据库、消息队列、缓存服务 | 1.3x ~ 1.8x |
| critical | 支付网关、核心业务服务 | 1.5x ~ 2.5x |

### 3. 风险容忍度

- **low**：保守策略，优先保证稳定性
- **medium**：平衡策略，兼顾稳定性和成本
- **high**：激进策略，优先优化成本

### 4. 资源比例建议

- **CPU限制/请求比**：建议 1.5 ~ 2.0
- **内存限制/请求比**：建议 1.2 ~ 1.5
- **HPA目标CPU利用率**：建议 60% ~ 80%
- **HPA目标内存利用率**：建议 65% ~ 85%

## ⚠️ 注意事项

1. **数据质量**：确保Prometheus有足够的历史数据，建议至少7天
2. **异常排除**：分析前排除发布、压测等特殊时段数据
3. **业务周期**：考虑业务的周期性（如周末、节假日流量差异）
4. **灰度实施**：建议先在测试环境验证，再逐步应用到生产
5. **监控调整**：应用推荐后持续观察，根据实际情况微调

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📄 许可证

MIT License

## 📮 联系方式

如有问题或建议，请通过Issue联系我们。
