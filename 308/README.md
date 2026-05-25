# Git Commit Quality Checker

一个功能强大的Git提交质量检查工具，帮助团队维护高质量的代码提交历史。

## ✨ 功能特性

### 1. Conventional Commits 格式检查
- 验证提交信息是否符合 [Conventional Commits](https://www.conventionalcommits.org/) 规范
- 支持自定义提交类型（feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert）
- 检查subject长度、大小写、结尾标点
- 验证body和footer格式
- 检测破坏性变更（!标记）

### 2. 变更范围分析
- 自动识别变更涉及的模块
- 检测跨模块提交
- 分析提交的内聚性
- 可配置模块识别正则模式

### 3. 代码变更量统计
- 统计新增/删除行数
- 统计变更文件数
- 智能识别重构操作（适当放宽限制）
- 支持排除自动生成的文件（lock文件、压缩文件等）

### 4. 质量评分系统
- 加权评分机制（可自定义权重）
- A-F等级评定
- 详细的改进建议
- 可配置通过阈值

### 5. 自定义规则
- 支持Python脚本规则
- 支持YAML声明式规则
- 灵活的规则加载机制

### 6. CI集成
- GitHub Actions
- GitLab CI
- Jenkins
- 通用CI脚本
- Git commit-msg hook

## 🚀 快速开始

### 安装

```bash
pip install -r requirements.txt
pip install -e .
```

### 基本使用

检查最新提交：
```bash
git-commit-check
# 或简写
gcc
```

检查指定提交：
```bash
git-commit-check check a1b2c3d
```

检查最近N个提交：
```bash
git-commit-check check -n 5
```

检查提交范围：
```bash
git-commit-check check --range develop..feature/x
```

### 其他命令

```bash
# 生成配置文件
git-commit-check init-config

# 验证/格式化提交信息
git-commit-check format-commit --type feat --scope auth --subject "add login"

# 生成CI配置
git-commit-check generate-ci --ci github

# 生成pre-commit钩子
git-commit-check pre-commit -o commit-msg-hook.py
```

### 输出格式

支持三种输出格式：

```bash
# 人类可读（默认）
git-commit-check --format human

# JSON格式（便于机器解析）
git-commit-check --format json

# Markdown格式（便于报告）
git-commit-check --format markdown
```

## ⚙️ 配置

### 生成默认配置

```bash
git-commit-check init-config
```

### 配置项说明

```yaml
conventional_commits:
  enabled: true
  weight: 35                    # 权重（总分100）
  types:                        # 允许的提交类型
    - feat
    - fix
    - docs
    - style
    - refactor
    - perf
    - test
    - build
    - ci
    - chore
    - revert
  require_scope: false          # 是否要求scope
  allow_empty_scope: true       # 是否允许空scope
  max_subject_length: 72        # subject最大长度
  require_body: false           # 是否要求body
  require_footer: false         # 是否要求footer

change_scope:
  enabled: true
  weight: 30
  module_patterns:              # 模块识别模式
    - "^src/([^/]+)/"
    - "^([^/]+)/"
    - "^packages/([^/]+)/"
  max_modules_per_commit: 2     # 单提交最大模块数
  cross_module_warning: true    # 跨模块警告

change_size:
  enabled: true
  weight: 35
  max_lines_changed: 400        # 最大变更行数
  max_files_changed: 20         # 最大变更文件数
  warn_lines_changed: 200       # 警告行数阈值
  warn_files_changed: 10        # 警告文件数阈值
  exclude_patterns:             # 排除文件模式
    - "package-lock.json"
    - "yarn.lock"
    - "*.min.js"
    - "dist/"
    - "build/"

scoring:
  pass_threshold: 70            # 通过阈值（百分比）
  warning_threshold: 50         # 警告阈值
  perfect_score: 100

custom_rules:
  enabled: false
  rules_dir: ".commit-rules"    # 自定义规则目录
```

## 🎯 自定义规则

### Python规则（.commit-rules/issue_reference.py）

```python
import re
from git_commit_checker.custom_rules import CustomRuleResult

name = "issue-reference"
weight = 10

def check(commit_info):
    message = commit_info.get("message", "")
    if not re.search(r"#\d+", message):
        return CustomRuleResult(
            rule_name=name,
            valid=False,
            score=0,
            max_score=weight,
            issues=["Commit message should reference an issue (#123)"],
            details={}
        )
    return CustomRuleResult(
        rule_name=name,
        valid=True,
        score=weight,
        max_score=weight,
        issues=[],
        details={"issue_found": True}
    )
```

### YAML规则（.commit-rules/max_files.yaml）

```yaml
name: max-files-per-commit
weight: 10
type: file_count
conditions:
  max: 15
error_message: "Commit should not modify more than 15 files"
```

支持的规则类型：
- `message`: 基于正则检查提交信息
- `file_count`: 限制文件数量
- `line_count`: 限制变更行数
- `file_pattern`: 禁止/允许特定文件

## 🔧 CI集成

### GitHub Actions

创建 `.github/workflows/commit-check.yml`：

```yaml
name: Commit Quality Check

on: [pull_request, push]

jobs:
  commit-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install git-commit-quality-checker

      - name: Check commit quality
        run: |
          if [ "${{ github.event_name }}" = "pull_request" ]; then
            git-commit-check check --range ${{ github.base_ref }}..${{ github.head_ref }} --strict
          else
            git-commit-check check -n 1 --strict
          fi
```

### GitLab CI

添加到 `.gitlab-ci.yml`：

```yaml
commit-quality-check:
  stage: test
  image: python:3.11-slim
  before_script:
    - pip install git-commit-quality-checker
  script:
    - |
      if [ "$CI_PIPELINE_SOURCE" = "merge_request_event" ]; then
        git-commit-check check --range $CI_MERGE_REQUEST_DIFF_BASE_SHA..$CI_COMMIT_SHA --strict
      else
        git-commit-check check -n 1 --strict
      fi
  rules:
    - if: '$CI_COMMIT_BRANCH'
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
```

### Git Hook

安装commit-msg钩子：

```bash
git-commit-check pre-commit -o .git/hooks/commit-msg
chmod +x .git/hooks/commit-msg
```

## 📊 评分说明

### 等级划分

| 分数范围 | 等级 | 说明 |
|---------|------|------|
| 90-100% | A (Excellent) | 优秀，提交质量很高 |
| 75-89% | B (Good) | 良好，基本符合规范 |
| 60-74% | C (Fair) | 一般，有改进空间 |
| 40-59% | D (Poor) | 较差，需要改进 |
| 0-39% | F (Fail) | 未通过，必须修改 |

### 权重分配（默认）

| 检查项 | 权重 | 说明 |
|-------|------|------|
| Conventional Commits格式 | 35% | 提交信息规范性 |
| 变更范围 | 30% | 模块内聚性 |
| 变更大小 | 35% | 提交粒度 |

## 🧪 测试

运行单元测试：

```bash
python -m pytest tests/ -v
```

或使用unittest：

```bash
python -m unittest discover tests -v
```

## 📖 Conventional Commits 规范

### 格式

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### 常用类型

- **feat**: 新功能
- **fix**: Bug修复
- **docs**: 文档更新
- **style**: 代码风格（不影响功能）
- **refactor**: 重构（既不新增功能也不修Bug）
- **perf**: 性能优化
- **test**: 测试相关
- **build**: 构建系统/依赖
- **ci**: CI配置
- **chore**: 其他杂项
- **revert**: 回滚提交

### 示例

```
feat(auth): add oauth2 login support

Add OAuth2 authentication with Google and GitHub providers.
Includes new login pages and callback handling.

Closes #123
BREAKING CHANGE: old session tokens are no longer valid
```

## 🤝 最佳实践

1. **原子提交**: 每个提交只做一件事
2. **描述清晰**: 提交信息要说明"为什么"而不只是"改了什么"
3. **粒度适中**: 避免过大的提交，便于审查和回滚
4. **关联Issue**: 相关Issue要在提交信息中引用
5. **使用规范**: 遵循Conventional Commits便于自动化

## 📝 License

MIT License
