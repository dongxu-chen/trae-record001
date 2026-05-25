# CI 流水线并行调度优化工具

一个基于 Go 语言实现的 CI 流水线并行调度优化工具，支持 DAG 依赖分析、关键路径计算、资源感知调度、任务优先级和失败自动重试。

## 架构概览

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  DAG 解析器     │────▶│ 关键路径计算    │────▶│  资源感知调度器  │
│  (pkg/dag)      │     │  (pkg/dag)      │     │ (pkg/scheduler) │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                          │
                                                          ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  流水线引擎     │◀────│  Kubernetes API │◀────│  资源监控模块   │
│  (pkg/engine)   │     │ (pkg/k8sclient) │     │  (pkg/monitor)  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
          │
          ▼
    ┌───────────┐
    │ CLI 入口  │
    │ (cmd/)    │
    └───────────┘
```

## 核心功能

### 1. DAG 任务依赖分析 (`pkg/dag`)
- **YAML 配置解析**：支持从 YAML 文件加载流水线配置
- **依赖关系验证**：自动检测循环依赖和无效依赖
- **拓扑排序**：Kahn 算法实现任务的拓扑排序
- **DAG 构建**：自动构建任务依赖图

### 2. 关键路径计算 (`pkg/dag/critical_path.go`)
- **最早/最晚时间计算**：计算每个任务的 ES、EF、LS、LF
- **松弛时间分析**：识别任务的可延迟时间
- **关键路径识别**：找出决定总工期的关键任务序列
- **最大并行度分析**：计算理论最大并行任务数

### 3. 资源感知调度器 (`pkg/scheduler`)
- **四种调度策略**：
  - `critical_path_first`：关键路径优先
  - `priority_first`：任务优先级优先
  - `resource_aware`：资源需求优先（小任务优先）
  - `balanced`：综合均衡策略（默认）
- **优先级队列**：基于堆的优先级任务队列
- **最佳适配算法**：根据资源使用选择最优执行器
- **负载均衡**：避免单个执行器过载

### 4. 资源监控模块 (`pkg/monitor`)
- **系统级监控**：CPU、内存、磁盘使用率实时采集
- **执行器资源管理**：跟踪每个执行器的资源分配
- **资源分配/释放**：原子操作保证资源计数准确
- **历史数据统计**：平均资源使用率计算

### 5. Kubernetes 客户端 (`pkg/k8sclient`)
- **Pod 生命周期管理**：创建、删除、查询 Pod
- **Pod 状态监听**：Watch 机制实时感知状态变化
- **日志获取**：获取任务执行日志
- **节点资源查询**：查询 Kubernetes 节点资源容量
- **自动清理**：定期清理已完成的 Pod

### 6. 流水线执行引擎 (`pkg/engine`)
- **两种执行模式**：
  - `local`：本地模拟执行（用于测试）
  - `kubernetes`：Kubernetes 集群执行
- **调度循环**：持续扫描就绪任务并调度
- **失败重试**：可配置的重试次数和间隔
- **任务编排**：协调 DAG、调度器、K8s 客户端
- **结果统计**：详细的任务执行报告

## 项目结构

```
ci-scheduler/
├── cmd/
│   └── main.go              # CLI 入口
├── pkg/
│   ├── dag/
│   │   ├── types.go         # 数据结构定义
│   │   ├── parser.go        # DAG 解析与构建
│   │   ├── critical_path.go # 关键路径计算
│   │   └── dag_test.go      # 单元测试
│   ├── scheduler/
│   │   └── scheduler.go     # 资源感知调度器
│   ├── monitor/
│   │   └── monitor.go       # 资源监控模块
│   ├── k8sclient/
│   │   └── client.go        # Kubernetes API 封装
│   └── engine/
│       └── engine.go        # 流水线执行引擎
├── examples/
│   ├── pipeline.yaml        # 完整示例流水线
│   └── simple-pipeline.yaml # 简单测试流水线
├── go.mod                   # Go 模块依赖
└── README.md
```

## 快速开始

### 前置要求
- Go 1.21+
- Kubernetes 集群（可选，用于 K8s 模式）

### 安装

```bash
# 克隆项目
git clone <repository>
cd ci-scheduler

# 下载依赖
go mod tidy

# 编译
go build -o ci-scheduler ./cmd/main.go
```

### 使用方法

#### 1. 分析流水线（仅分析不执行）

```bash
./ci-scheduler analyze -p examples/simple-pipeline.yaml
```

输出内容包括：
- 关键路径分析
- 任务调度时间表（ES、EF、LS、LF、Slack）
- 最大并行度

#### 2. 本地模拟执行

```bash
./ci-scheduler run \
  -p examples/simple-pipeline.yaml \
  -m local \
  -s balanced \
  --executors exec-1,exec-2,exec-3 \
  --executor-cpu 4.0,4.0,4.0 \
  --executor-mem 8192,8192,8192
```

#### 3. Kubernetes 执行

```bash
./ci-scheduler run \
  -p examples/pipeline.yaml \
  -m kubernetes \
  -n ci-namespace \
  --kubeconfig ~/.kube/config \
  -s critical_path_first
```

### CLI 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `-p, --pipeline` | 流水线 YAML 文件路径 | 必填 |
| `-m, --mode` | 执行模式：local/kubernetes | local |
| `-n, --namespace` | Kubernetes 命名空间 | default |
| `--kubeconfig` | kubeconfig 文件路径 | ~/.kube/config |
| `--executors` | 执行器名称列表 | exec-1,exec-2,exec-3 |
| `--executor-cpu` | 每个执行器的 CPU 核数 | 4.0,4.0,4.0 |
| `--executor-mem` | 每个执行器的内存 (MiB) | 8192,8192,8192 |
| `-s, --strategy` | 调度策略 | balanced |
| `--monitor-interval` | 资源监控间隔 | 5s |

## 流水线配置格式

```yaml
id: pipeline-001
name: My CI Pipeline
default_resources:
  cpu: 1.0
  memory: 1024
labels:
  team: backend
  environment: production

tasks:
  - id: clone-repo
    name: Clone Repository
    image: alpine/git:latest
    command: ["git", "clone", "..."]
    priority: 10          # 1-10，越高越优先
    max_retries: 3        # 最大重试次数
    retry_delay: 5        # 重试间隔（秒）
    estimated_time: 30s   # 预估执行时间
    resources:
      cpu: 0.5
      memory: 512
    labels:
      stage: prepare

  - id: build
    name: Build Application
    image: golang:1.21
    command: ["go", "build", "..."]
    depends_on:           # 依赖任务
      - clone-repo
    priority: 8
    estimated_time: 2m
    resources:
      cpu: 2.0
      memory: 2048
```

## 调度策略详解

### 1. 关键路径优先 (critical_path_first)
关键路径上的任务获得最高优先级加成 (+1000)，确保关键任务优先执行，缩短总工期。

### 2. 优先级优先 (priority_first)
纯优先级驱动，完全按照任务配置的 priority 字段排序。

### 3. 资源感知 (resource_aware)
小任务优先执行，资源需求越小优先级越高，提高执行器利用率。

### 4. 综合均衡 (balanced) - 默认
综合考虑以下因素计算优先级：
```
优先级 = 基础优先级 + 关键路径加成(500) + 松弛时间加成 - 资源消耗惩罚
```

## 运行测试

```bash
# 运行所有单元测试
go test ./... -v

# 运行 DAG 缓存测试
go test ./pkg/dag -run TestTopoCache -v

# 运行错误分类器测试
go test ./pkg/errors -v

# 运行任务预热测试
go test ./pkg/warmup -v

# 运行动态扩缩容测试
go test ./pkg/autoscaler -v

# 运行耗时预测测试
go test ./pkg/predictor -v

# 运行特定测试
go test ./pkg/dag -run TestCalculateCriticalPath -v
```

## 核心算法

### 关键路径算法
1. 拓扑排序获取任务执行顺序
2. 正向遍历计算最早开始(ES)和最早结束(EF)时间
3. 反向遍历计算最晚开始(LS)和最晚结束(LF)时间
4. 计算松弛时间 Slack = LS - ES
5. Slack = 0 的任务构成关键路径

### 最佳适配调度算法
1. 筛选所有能容纳任务资源需求的执行器
2. 计算每个候选执行器放置任务后的综合负载
3. 选择负载最低的执行器（均衡负载）

### ⭐ 历史加权负载评分算法
```
综合评分 = (70% × 当前负载 + 30% × 历史加权平均负载 + 5% × 任务数惩罚

其中：
- 当前负载 = (已分配CPU + 新任务CPU) / 总CPU + (已分配内存 + 新任务内存) / 总内存
- 历史加权平均 = Σ(数据点权重 × 使用率)，新数据权重更高（线性加权）
- 任务数惩罚 = 0.05 × 每任务
```

### ⭐ 拓扑缓存构建算法
1. 构建DAG时预计算：
   - 拓扑排序（Kahn算法）
   - 反向传播计算后代集合（descendantCache[taskID] → O(n)
   - 正向传播计算祖先集合（ancestorCache[taskID] → O(n)
2. 依赖查询 O(1) 复杂度：
   - `IsDescendant(A, B) → descendantCache[A][B]
   - `IsAncestor(A, B) → ancestorCache[A][B]
   - `CanRunParallel(A, B) → !IsDescendant(A,B) && !IsAncestor(A,B)

## ⭐ 新特性详解

### 1. DAG 拓扑缓存加速
**性能提升**：依赖检测从 O(n) → O(1)

**API 示例**：
```go
dag, _ := BuildDAG(pipeline)

// 检查任务依赖
isDesc, _ := dag.IsDescendant("task-1", "task-4")  // true, O(1)
isAnc, _ := dag.IsAncestor("task-4", "task-1")     // true, O(1)
dep, _ := dag.AreDependent("task-2", "task-3")       // false, O(1)
parallel, _ := dag.CanRunParallel("task-2", "task-3") // true, O(1)

// 获取拓扑排序
topoOrder, _ := dag.GetTopoOrder()                    // ["task-1", "task-2", "task-3", "task-4"]

// 获取所有后代
descendants, _ := dag.GetDescendants("task-1")        // ["task-2", "task-3", "task-4"]
```

**缓存失效**：
```go
dag.InvalidateCache()  // 手动失效
topoOrder, _ := dag.GetTopoOrder()  // 自动重建
```

### 2. 历史使用率加权调度
**负载均衡提升**：避免任务集中到同一执行器

**评分公式**：
```
执行器评分 = 0.7 × (CPU利用率 + 内存利用率) + 0.3 × (历史CPU加权平均 + 历史内存加权平均) + 0.05 × 任务数
```

**加权平均计算**（线性加权，新数据权重更高）：
```
权重(i) = (i+1) / (n×(n+1)/2)  // n=历史数据点数
加权平均 = Σ(权重(i) × 数据点(i))
```

### 3. 错误类型分类与智能重试
**错误类型矩阵**：

| 错误类型 | 严重程度 | 可重试 | 说明 |
|---------|---------|--------|------|
| compile_error | high | ❌ 否 | 编译错误，需修复代码 |
| test_failed | high | ❌ 否 | 测试失败，需修复代码 |
| config_error | high | ❌ 否 | 配置错误，需修复配置 |
| network_error | low | ✅ 是 | 网络波动，可重试 |
| timeout | low | ✅ 是 | 操作超时，可重试 |
| resource_exhausted | medium | ✅ 是 | 资源不足，等待重试 |
| dependency_error | low | ✅ 是 | 依赖下载失败，可重试 |
| infrastructure_error | medium | ✅ 是 | 基础设施故障，可重试 |

**重试策略**：
- 不可重试错误：立即告警 → 标记失败 → 跳过下游任务
- 可重试错误：指数退避（重试次数 × 基础延迟）→ 最多 max_retries 次

**告警回调示例**：
```go
engine.SetAlertCallback(func(classification *errors.ErrorClassification, taskID string) {
    // 发送钉钉/邮件/企业微信告警
    sendAlert(classification.GetAlertMessage())
})
```

**错误分类 API**：
```go
classifier := errors.NewErrorClassifier()

result := classifier.Classify(errorMessage)
fmt.Printf("类型: %s, 可重试: %v, 严重程度: %s\n",
    result.Type, result.Retryable, result.Severity)

if classifier.IsCompileError(errorMessage) {
    // 发送编译错误告警
}
```

## 注意事项

1. **Kubernetes 模式**：需要确保集群有足够的资源，且 Service Account 具有 Pod 创建/删除权限
2. **资源配额**：任务的资源请求不能超过任何单个执行器的容量
3. **重试机制**：关键任务建议设置较低的重试次数，避免阻塞后续任务
4. **超时控制**：Kubernetes 模式下默认超时 1 小时，可根据需要调整
5. **错误分类**：正则匹配基于常见错误模式，可根据需要扩展 patterns

## 运行测试

```bash
# 运行所有测试
go test ./... -v

# 运行 DAG 缓存测试
go test ./pkg/dag -run TestTopoCache -v

# 运行错误分类器测试
go test ./pkg/errors -v
```

## 许可证

MIT License
