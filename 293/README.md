# Docker 镜像构建层缓存分析工具

一个用于分析 Dockerfile 构建层缓存效率的 Python 工具，提供缓存命中概率分析、构建时间预测、自动优化和CI检查集成。

## ✨ 功能特性

### 核心分析功能
- **Dockerfile 解析**: 完整解析 Dockerfile，支持多阶段构建
- **智能文件修改频率权重**: 基于文件名模式和修改时间计算文件变更频率
- **缓存命中分析**: 计算每一层的缓存命中概率，识别高风险缓存破坏点
- **跨阶段依赖检测**: 自动识别 `COPY --from` 跨阶段复制依赖
- **构建时间预测**: 预测无缓存/全缓存构建时间，模拟优化后加速效果
- **层大小分析**: 估算各层大小，按类别统计
- **共享层分析**: 检测多个阶段中重复的层，计算增量节省空间

### 优化建议生成
- 合并连续的 RUN 命令
- 按文件修改频率优化 COPY 命令顺序
- 添加包管理器清理命令
- 合并 apt-get update 和 install
- 建议使用多阶段构建
- 合并多个 COPY --from 命令
- 使用 COPY 代替 ADD
- 建议创建共享基础镜像

### 高级功能
- **一键自动优化**: 自动应用优化建议，生成优化后的 Dockerfile
- **CI 检查集成**: 支持 GitHub Actions、GitLab CI 等自动化检查
- **多种输出格式**: 支持文本和 JSON 格式输出
- **彩色终端输出**: 直观的分析报告

## 🚀 安装

```bash
pip install -r requirements.txt
```

## 📖 使用方法

### 基本用法

```bash
python main.py path/to/Dockerfile
```

### 指定上下文路径

```bash
python main.py Dockerfile --context .
```

### 只显示部分报告

```bash
# 不显示大小分析
python main.py Dockerfile --no-size

# 不显示缓存分析
python main.py Dockerfile --no-cache

# 不显示构建时间预测
python main.py Dockerfile --no-time

# 不显示优化建议
python main.py Dockerfile --no-optimizations
```

### JSON 格式输出

```bash
python main.py Dockerfile --format json
```

### 一键自动优化

```bash
# 自动应用优化并保存为 Dockerfile.optimized
python main.py Dockerfile --auto-optimize

# 指定输出路径
python main.py Dockerfile --auto-optimize --output Dockerfile.optimized
```

### CI 检查模式

```bash
# 控制台 CI 报告
python main.py Dockerfile --ci console

# GitHub Actions 格式
python main.py Dockerfile --ci github

# GitLab CI 格式
python main.py Dockerfile --ci gitlab
```

### 生成 CI 配置文件

```bash
# 生成 GitHub Actions 工作流
python main.py Dockerfile --generate-ci github > .github/workflows/dockerfile-analysis.yml

# 生成 GitLab CI 配置
python main.py Dockerfile --generate-ci gitlab >> .gitlab-ci.yml
```

## 📊 示例

### 分析待优化的 Dockerfile

```bash
python main.py examples/bad.Dockerfile
```

输出将包含:
1. 各层缓存命中概率分析
2. 镜像大小统计
3. 构建时间预测和优化加速模拟
4. 详细的优化建议（含优化前后代码对比）

### 分析多阶段构建 Dockerfile

```bash
python main.py examples/shared_layers.Dockerfile
```

### 一键自动优化

```bash
python main.py examples/bad.Dockerfile --auto-optimize
```

### 运行 CI 检查

```bash
python main.py examples/bad.Dockerfile --ci console
```

## 📁 项目结构

```
.
├── main.py                  # 主入口 CLI
├── dockerfile_parser.py     # Dockerfile 解析模块
├── cache_analyzer.py        # 缓存分析模块
├── optimizer.py             # 优化建议生成器
├── size_analyzer.py         # 层大小分析模块
├── build_time_predictor.py  # 构建时间预测模块
├── auto_optimizer.py        # 自动优化生成器
├── ci_checker.py            # CI 检查集成模块
├── requirements.txt         # 依赖列表
├── test_enhanced.py         # 增强功能测试脚本
└── examples/                # 示例 Dockerfile
    ├── bad.Dockerfile       # 待优化的示例
    ├── good.Dockerfile      # 优化后的示例
    ├── multistage.Dockerfile # 多阶段构建示例
    └── shared_layers.Dockerfile # 共享层多阶段示例
```

## 核心模块说明

### dockerfile_parser.py
- `DockerfileParser`: 主解析类
- `LayerInfo`: 层信息数据类
- `StageInfo`: 构建阶段信息数据类

### cache_analyzer.py
- `CacheAnalyzer`: 缓存分析器
- `CacheAnalysisResult`: 缓存分析结果

### optimizer.py
- `Optimizer`: 优化建议生成器
- `OptimizationSuggestion`: 优化建议数据类
- `OptimizationSeverity`: 建议严重程度枚举

### size_analyzer.py
- `SizeAnalyzer`: 大小分析器
- `LayerSizeAnalysis`: 层大小分析结果

## 优化建议严重程度

| 级别 | 图标 | 说明 |
|------|------|------|
| CRITICAL | 🔴 | 必须修复，可能导致构建失败或严重缓存问题 |
| HIGH | 🟠 | 强烈建议修复，显著影响构建性能 |
| MEDIUM | 🟡 | 建议修复，中等程度影响 |
| LOW | 🟢 | 可选优化，轻微影响 |

## 缓存命中概率评估因素

1. **指令类型**: 不同指令有不同的基础缓存概率
2. **文件修改频率权重**: 基于文件名模式和修改时间的智能评估
3. **上下文文件**: 文件变更频率评估
4. **跨阶段依赖**: COPY --from 引用的前置阶段缓存概率
5. **动态内容**: 命令中的动态执行
6. **网络请求**: 外部依赖的稳定性
7. **通配符使用**: 增加文件变更风险
8. **高频文件顺序**: 低频文件前置获得更高缓存概率

## 新增增强功能详解

### 📊 文件修改频率权重

工具会根据文件名模式自动计算文件修改频率：

- **高频率 (0.8)**: `.js`, `.ts`, `.py`, `.java`, `src/` 等源代码文件
- **中频率 (0.5)**: `package.json`, `requirements.txt`, `Dockerfile` 等配置文件
- **低频率 (0.2)**: `.lock`, `.md`, 图片资源等稳定文件

高频文件应放在 Dockerfile 后面，以获得更好的缓存利用。

### 🔗 多阶段构建依赖检测

自动识别 `COPY --from` 跨阶段复制：

```dockerfile
COPY --from=builder /app/dist /usr/share/nginx/html
```

工具会：
- 识别依赖的前置阶段
- 计算前置阶段的缓存概率
- 将前置阶段的缓存状态考虑到当前层

### 💾 共享层与增量节省

分析多个阶段中的重复指令，计算实际增量节省：

- **总预估节省**: 所有优化建议的空间总和
- **增量实际节省**: 扣除共享层后的实际可节省空间

例如：如果一个 RUN 命令在 3 个阶段中重复出现，增量节省为 (3-1) × 层大小。

## 许可证

MIT License
