# Docker 镜像清理巡检工具

一个基于 Python + Docker SDK + schedule 的 Docker 镜像清理巡检脚本。

## 功能特性

- 扫描 Docker 环境中的所有镜像
- 统计镜像使用频率、大小、创建时间
- 标记超过指定天数（默认30天）未使用的镜像为待清理
- **Dockerfile 依赖分析**：自动扫描 Dockerfile 的 FROM 指令，识别被依赖的基础镜像
- **白名单正则支持**：支持通配符匹配，如 `nginx:*`、`registry.example.com/*`、`v*`
- **干跑模拟删除**：验证删除可行性，过滤无法删除的镜像，输出最终清理列表
- **磁盘空间预测**：基于历史增长趋势预测多少天后磁盘满
- **自动清理策略**：磁盘使用率超过阈值（默认80%）时触发清理
- **清理审计日志**：记录清理操作和释放空间量，支持输出到ELK
- 支持定时任务自动执行

## 安装依赖

```bash
pip install -r requirements.txt
```

## 快速开始

### 单次执行（干跑模式 + 模拟删除）

```bash
python docker_cleaner.py --dry-run
```

### 单次执行（实际清理）

修改 `config.yaml` 中 `dry_run: false`，然后执行：

```bash
python docker_cleaner.py
```

### 自定义清理阈值

```bash
python docker_cleaner.py --days 15 --dry-run
```

### 定时任务模式

```bash
python docker_cleaner.py --schedule
```

### 跳过模拟删除验证

```bash
python docker_cleaner.py --dry-run --no-simulate
```

### 强制执行清理

```bash
python docker_cleaner.py --force-clean
```

## 配置说明

`config.yaml` 配置文件：

```yaml
cleanup:
  days_unused: 30           # 未使用天数阈值
  dry_run: true             # 干跑模式
  schedule: "02:00"         # 定时执行时间
  remove_dangling: true     # 清理悬空镜像

auto_cleanup:
  enable: true              # 启用自动清理
  disk_usage_threshold: 80  # 磁盘使用率阈值(%)
  force_clean: false        # 触发时强制执行清理（忽略dry_run）

disk:
  history_file: "./data/disk_history.json"  # 磁盘历史数据文件

dependency:
  enable: true              # 启用Dockerfile依赖分析
  dockerfile_paths:         # Dockerfile扫描路径
    - "./"
    - "/path/to/projects"

whitelist:
  repositories:             # 白名单仓库（支持通配符）
    - "nginx"
    - "alpine"
    - "registry.example.com/*"
  tags:                     # 白名单标签（支持通配符）
    - "latest"
    - "stable"
    - "v*"
  images:                   # 白名单特定镜像（支持通配符）
    - "busybox:1.36"
    - "ubuntu:*"

audit:
  enable: true              # 启用审计日志
  log_file: "./logs/audit.log"
  elk:
    enable: false           # 启用ELK输出
    host: "localhost"
    port: 9200
    index: "docker-cleaner-audit"
```

## 白名单通配符规则

支持标准的 shell 通配符：

| 模式 | 说明 | 示例 | 匹配 |
|------|------|------|------|
| `*` | 匹配任意字符 | `nginx:*` | `nginx:latest`, `nginx:1.25` |
| `?` | 匹配单个字符 | `ubuntu:20.0?` | `ubuntu:20.04`, `ubuntu:20.01` |
| `[seq]` | 匹配序列中的字符 | `python:3.[89]` | `python:3.8`, `python:3.9` |
| `[!seq]` | 匹配不在序列中的字符 | `python:3.[!01]` | `python:3.2`, `python:3.8` |

## 磁盘空间预测

脚本会自动记录每次运行时的磁盘使用情况，并基于历史数据预测磁盘满的时间：

- 记录最近100次磁盘使用数据
- 计算日平均增长量
- 预测剩余可用天数
- 报告中显示磁盘使用情况和预测结果

## 自动清理策略

当磁盘使用率超过配置的阈值（默认80%）时：

1. 触发自动清理警告
2. 如果配置了 `force_clean: true`，将忽略 dry_run 设置强制执行清理
3. 记录触发原因到审计日志

## 审计日志

每次清理操作都会记录详细的审计日志，格式为 JSON：

```json
{
  "@timestamp": "2024-01-01T02:00:00Z",
  "event": "cleanup",
  "host": "node-01",
  "dry_run": false,
  "trigger_reason": "磁盘使用率 85.2% 超过阈值 80%",
  "total_images": 10,
  "deleted_count": 8,
  "failed_count": 2,
  "total_freed_bytes": 5242880000,
  "total_freed_human": "5.00 GB",
  "deleted_images": [
    {
      "id": "abc123def456",
      "tags": "old-image:v1.0",
      "size": 1048576000,
      "size_human": "1.00 GB"
    }
  ],
  "failed_images": [
    {
      "id": "def789ghi012",
      "tags": "used-image:latest",
      "error": "镜像正在被使用"
    }
  ]
}
```

### ELK 集成

配置 `audit.elk.enable: true` 后，审计日志会自动发送到 Elasticsearch：

- 使用 HTTP API 发送到 `http://{host}:{port}/{index}/_doc`
- 可以在 Kibana 中创建仪表板监控清理情况
- 支持按主机、时间、释放空间等维度统计

## 输出说明

脚本会生成以下内容：

1. **控制台输出**：详细的巡检报告
2. **报告文件**：保存在 `./reports/` 目录下
3. **日志文件**：保存在 `./logs/` 目录下
4. **审计日志**：保存在 `./logs/audit.log`（JSON格式）
5. **磁盘历史数据**：保存在 `./data/disk_history.json`

报告包含：
- **磁盘使用情况**：总容量、已使用、使用率、预测信息
- **统计概览**：镜像总数、总大小、待清理数量、可释放空间、白名单数、被依赖镜像数、悬空镜像数
- **模拟删除失败列表**（干跑模式）：无法删除的镜像及失败原因
- **最终待清理镜像列表**：经过验证可以安全删除的镜像
- **白名单镜像列表**
- **Dockerfile 依赖镜像列表**
- **所有镜像详情表**

## 命令行参数

| 参数 | 说明 |
|------|------|
| `-c, --config` | 指定配置文件路径 |
| `--dry-run` | 启用干跑模式，执行模拟删除验证 |
| `--no-simulate` | 干跑模式下跳过模拟删除验证 |
| `--force-clean` | 强制执行清理（忽略dry_run设置） |
| `--schedule` | 以定时任务模式运行 |
| `--days` | 覆盖未使用天数阈值 |

## 工作流程

```
1. 获取磁盘使用情况 → 记录历史数据 → 预测满盘时间
2. 检查自动清理触发条件 → 磁盘使用率是否超过阈值
3. 扫描Dockerfile → 分析FROM指令 → 识别被依赖镜像
4. 扫描Docker镜像 → 收集大小、创建时间、使用情况
5. 应用白名单规则（支持通配符）
6. 标记待清理镜像（超过阈值 + 非白名单 + 非被依赖 + 无容器使用）
7. 干跑模式：模拟删除验证 → 过滤无法删除的镜像 → 输出最终列表
8. 生成详细报告
9. 执行清理（非干跑模式）
10. 记录审计日志 → 发送到ELK（如果配置）
```
