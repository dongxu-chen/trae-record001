# 代码审查辅助工具 (Code Review Assistant Tool)

一个功能强大的代码审查辅助工具，集成GitLab/GitHub PR，自动分析代码变更、检测代码规范问题、圈复杂度、重复代码，并输出审查报告和风险等级。

## 功能特性

### 1. Git平台集成
- 支持 GitHub Pull Request 分析
- 支持 GitLab Merge Request 分析
- 自动获取PR/MR详情和变更文件

### 2. 代码规范检测
- **Pylint** - Python代码规范检测
- **ESLint** - JavaScript/TypeScript代码规范检测
- 支持自定义配置文件

### 3. 代码复杂度分析
- 使用 **Lizard** 进行圈复杂度(CCN)分析
- 支持多语言（Python、JavaScript、Java、C/C++、C#等）
- 高风险函数识别
- 函数参数数量检查

### 4. 重复代码检测
- 单文件内部重复检测
- 跨文件重复检测
- 基于token指纹的相似度匹配

### 5. 自定义规则集
- Python专属规则（参数数量、嵌套深度、行长等）
- JavaScript专属规则（函数长度、console.log检测等）
- 安全规则（硬编码密码、API密钥等）
- 命名规范规则（类名、函数名等）

### 6. SonarQube集成
- 支持SonarQube API获取问题
- 支持运行SonarQube Scanner
- 质量门状态检查

### 7. 报告生成
- JSON格式详细报告
- 文本格式摘要报告
- 风险等级评估（critical/high/medium/low）
- 风险分数计算

## 项目结构

```
code-review-tool/
├── src/
│   ├── __init__.py
│   ├── code_review_tool.py      # 主入口类
│   ├── config_loader.py         # 配置加载器
│   ├── git_integration.py       # Git平台集成
│   ├── linting.py               # 代码规范检测
│   ├── complexity_analyzer.py   # 复杂度分析
│   ├── duplication_detector.py  # 重复代码检测
│   ├── custom_rules.py          # 自定义规则检查
│   ├── sonarqube_integration.py # SonarQube集成
│   └── report_generator.py      # 报告生成
├── config/
│   ├── config.yaml              # 主配置文件
│   └── rules/
│       └── custom_rules.yaml    # 自定义规则配置
├── examples/
│   └── usage_example.py         # 使用示例
├── reports/                     # 报告输出目录
├── .env.example                 # 环境变量示例
├── requirements.txt             # Python依赖
├── main.py                      # 命令行入口
└── README.md                    # 本文件
```

## 安装

1. 克隆或下载项目
2. 安装Python依赖：

```bash
pip install -r requirements.txt
```

3. 配置环境变量（可选）：

```bash
cp .env.example .env
# 编辑 .env 文件，填入你的token
```

## 使用方法

### 命令行使用

#### 1. 分析本地目录

```bash
python main.py --mode directory --path /path/to/your/code --format all
```

#### 2. 分析单个文件

```bash
python main.py --mode file --path /path/to/your/file.py
```

#### 3. 分析GitHub Pull Request

```bash
python main.py --mode pr --repo-owner owner --repo-name repo --pr-number 123
```

#### 4. 分析GitLab Merge Request

```bash
# 修改 config/config.yaml 中的 platform 为 gitlab
python main.py --mode pr --repo-owner owner --repo-name repo --pr-number 456
```

### 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--mode` | 分析模式: pr/directory/file | directory |
| `--path` | 目录或文件路径 | 当前目录 |
| `--repo-owner` | 仓库所有者 | 配置文件 |
| `--repo-name` | 仓库名称 | 配置文件 |
| `--pr-number` | PR/MR编号 | 配置文件 |
| `--config` | 配置文件路径 | config/config.yaml |
| `--rules` | 规则文件路径 | config/rules/custom_rules.yaml |
| `--format` | 输出格式: json/text/all | json |
| `--no-report` | 不生成报告文件 | False |

### Python API 使用

```python
from src.code_review_tool import CodeReviewTool

# 初始化工具
tool = CodeReviewTool()

# 分析本地目录
results = tool.analyze_directory("/path/to/code")

# 生成报告
reports = tool.generate_reports(results, "all")

# 打印摘要
tool.report_generator.print_summary(results)
```

更多示例请查看 [examples/usage_example.py](examples/usage_example.py)

## 配置说明

### 主配置文件 (config/config.yaml)

```yaml
code_review:
  platform: github          # github 或 gitlab
  repo_owner: "owner"
  repo_name: "repo"
  pr_number: 1

linting:
  eslint:
    enabled: true
    config_file: ".eslintrc.js"
  pylint:
    enabled: true
    config_file: ".pylintrc"

complexity:
  enabled: true
  max_ccn: 10              # 最大圈复杂度
  max_function_length: 50   # 最大函数行数

duplication:
  enabled: true
  min_lines: 5             # 最小重复行数
  min_tokens: 50           # 最小重复token数

sonarqube:
  enabled: false
  project_key: "project-key"

rules:
  severity_weights:         # 严重程度权重
    critical: 10
    high: 5
    medium: 2
    low: 1
  
  risk_thresholds:          # 风险等级阈值
    critical: 80
    high: 50
    medium: 20
    low: 0

output:
  format: json
  report_dir: "reports"
```

### 自定义规则 (config/rules/custom_rules.yaml)

支持配置以下类型的规则：

- **Python规则**: max_function_args, max_nesting_depth, max_line_length
- **JavaScript规则**: max_function_length, no_console_log
- **安全规则**: hardcoded_secrets (密码/密钥检测)
- **命名规则**: class_name_pattern, function_name_pattern

每个规则可以配置：
- `enabled`: 是否启用
- `severity`: 严重程度 (critical/high/medium/low)
- `message`: 提示信息
- 规则特定参数（如max_args, max_depth等）

## 风险等级说明

| 等级 | 分数范围 | 说明 |
|------|---------|------|
| Critical | >= 80 | 严重问题，建议立即修复 |
| High | 50-79 | 高风险，需要审查 |
| Medium | 20-49 | 中等风险，建议修复 |
| Low | 0-19 | 低风险，可选择性修复 |
| None | 0 | 无问题 |

## 支持的语言

- **Python** (.py) - 完整支持
- **JavaScript** (.js, .jsx) - 完整支持
- **TypeScript** (.ts, .tsx) - 部分支持
- **Java** (.java) - 复杂度分析
- **C/C++** (.c, .cpp, .h) - 复杂度分析
- **C#** (.cs) - 复杂度分析

## 环境变量

在 `.env` 文件中配置：

```
GITHUB_TOKEN=your_github_token_here
GITLAB_TOKEN=your_gitlab_token_here
GITLAB_URL=https://gitlab.com
SONARQUBE_URL=http://localhost:9000
SONARQUBE_TOKEN=your_sonarqube_token_here
```

## 扩展开发

### 添加新的分析模块

1. 在 `src/` 目录下创建新的分析器类
2. 实现 `analyze_file()` 和 `analyze_directory()` 方法
3. 在 `code_review_tool.py` 中集成新模块

### 添加自定义规则

1. 在 `custom_rules.py` 中添加新的检查方法
2. 在 `config/rules/custom_rules.yaml` 中添加配置
3. 在 `check_file()` 方法中调用新检查

## 注意事项

1. ESLint需要Node.js环境和项目中安装eslint包
2. SonarQube功能需要配置SonarQube服务器
3. Git API有速率限制，大量使用建议配置token
4. 分析大项目可能需要较长时间

## License

MIT License
