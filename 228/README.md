# Docker 镜像构建加速工具

一个基于 Go 和 Docker SDK 的 Docker 镜像构建加速工具，提供以下核心功能：

## ✨ 功能特性

### 1. 层缓存优化 (Layer Cache Optimization)
- 根据 Dockerfile 命令类型智能预测缓存命中率
- 分析源文件变更对缓存的影响
- 检测高风险缓存失效命令（如 apt-get update、npm install 等）
- 提供详细的缓存优化报告和建议

### 2. 并行构建 (Parallel Build)
- 自动分析多阶段构建的依赖关系
- 独立阶段并行执行，充分利用系统资源
- 智能调度，确保依赖阶段按顺序执行
- 实时进度跟踪和构建摘要报告

### 3. 构建历史分析 (Build History Analysis)
- 记录每次构建的详细信息（耗时、大小、各层数据）
- 分析最慢和最大的镜像层
- 统计各命令类型的平均耗时和大小
- 生成历史趋势分析报告
- 提供针对性的优化建议

### 4. 分片并行上传 (Parallel Upload)
- 自动检测已存在的镜像层，避免重复上传
- 多层并行上传，提高上传速度
- 支持私有仓库认证
- 自动重试失败的上传任务
- 实时上传进度和吞吐量统计

## 📦 安装

### 环境要求
- Go 1.21+
- Docker Engine 20.10+

### 编译安装
```bash
# 克隆或下载项目
cd docker-build-accelerator

# 下载依赖
go mod tidy

# 编译
go build -o dba ./cmd
```

## 🚀 使用方法

### 1. 构建镜像
```bash
# 基本构建
./dba build -f Dockerfile -t myapp:latest

# 指定构建上下文
./dba build -f Dockerfile -c ./src -t myapp:latest

# 并行构建（默认4并发）
./dba build -f Dockerfile -t myapp:latest -j 8

# 构建完成后自动推送到私有仓库
./dba build -f Dockerfile -t myapp:latest --push --registry registry.example.com
```

### 2. 分析 Dockerfile
```bash
# 分析Dockerfile并给出优化建议
./dba analyze -f Dockerfile

# 查看详细的缓存预测报告
./dba analyze -f Dockerfile -c ./src
```

### 3. 查看构建历史
```bash
# 查看构建历史分析报告
./dba history

# 指定历史记录目录
./dba history --history-dir ./my-build-history
```

### 4. 推送镜像到私有仓库
```bash
# 并行上传镜像
./dba push -t myapp:latest --registry registry.example.com

# 带认证的私有仓库
./dba push -t myapp:latest --registry registry.example.com --registry-user admin --registry-pass secret

# 指定并发数
./dba push -t myapp:latest --registry registry.example.com -j 8
```

## 📁 项目结构

```
docker-build-accelerator/
├── cmd/
│   └── main.go              # CLI 入口程序
├── pkg/
│   ├── parser/              # Dockerfile 解析器
│   │   └── parser.go
│   ├── cache/               # 缓存优化模块
│   │   └── optimizer.go
│   ├── parallel/            # 并行构建调度器
│   │   └── scheduler.go
│   ├── analysis/            # 构建历史分析
│   │   └── analyzer.go
│   └── upload/              # 并行上传模块
│       └── uploader.go
├── go.mod
├── go.sum
└── README.md
```

## 📊 输出示例

### 缓存优化报告
```
=== Cache Optimization Report for builder ===
Total Commands: 12
Expected Cache Hits: 9 (75.0%)
Estimated Time Saved: ~45.0 seconds

Recommendations:
  - Consider reordering high-risk cache commands to the end of the Dockerfile
  - Line 15: Package manager commands frequently update packages, breaking cache
```

### 并行构建摘要
```
=== Parallel Build Summary ===
Total Stages: 3
  ✓ builder: completed (12.34s)
  ✓ tester: completed (8.56s)
  ✓ final: completed (5.12s)

Total Build Time: 17.89s (wall clock)
Sequential Estimate: 26.02s
Speedup: 1.45x
```

### 构建历史分析
```
=== Build Analysis Report ===
Total Builds Analyzed: 10
Average Build Time: 24.5s
Average Image Size: 342.5 MB
Cache Hit Rate: 68.5%

=== Slowest Layers (Top 5) ===
1. [RUN] 45.2s - 128.5 MB - apt-get update && apt-get install...
2. [COPY] 12.3s - 85.2 MB - COPY . .

=== Optimization Tips ===
1. RUN commands average 22.1s. Consider combining multiple RUN commands.
```

## 🔧 配置选项

### build 命令
| 参数 | 说明 | 默认值 |
|------|------|--------|
| `-f, --file` | Dockerfile 路径 | Dockerfile |
| `-c, --context` | 构建上下文目录 | . |
| `-t, --tag` | 镜像标签 | 无 |
| `-j, --concurrency` | 并发数 | 4 |
| `--registry` | 私有仓库 URL | 无 |
| `--registry-user` | 仓库用户名 | 无 |
| `--registry-pass` | 仓库密码 | 无 |
| `--history-dir` | 历史记录目录 | ./.build-history |
| `--no-cache` | 禁用缓存 | false |
| `--push` | 构建后自动推送 | false |

## 🎯 最佳实践

### 提高缓存命中率
1. 将不常变化的命令放在 Dockerfile 前面
2. 将 `COPY package.json` 放在 `COPY . .` 之前
3. 合并多个 RUN 命令以减少层数
4. 使用 `.dockerignore` 排除不必要的文件

### 优化并行构建
1. 使用多阶段构建，命名各个阶段
2. 减少阶段间的依赖关系
3. 独立的测试和构建阶段可以并行执行

### 加速上传
1. 使用并发上传（-j 参数）
2. 基础镜像尽量使用官方镜像（通常已存在于仓库）
3. 合理控制镜像层大小

## 📝 示例 Dockerfile

```dockerfile
# 多阶段构建示例
FROM golang:1.21 AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -o myapp .

FROM node:20 AS frontend
WORKDIR /app
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ .
RUN npm run build

FROM alpine:latest AS final
WORKDIR /app
COPY --from=builder /app/myapp .
COPY --from=frontend /app/dist ./static
EXPOSE 8080
CMD ["./myapp"]
```

## 📄 许可证

MIT License
