# Code Quality Checker

一个功能全面的代码质量自动检查工具，支持多种编程语言、增量检查、阈值配置和自动修复，可无缝集成到GitLab CI和GitHub Actions中。

## 功能特性

- **多语言支持**：JavaScript/TypeScript (ESLint)、Python (Pylint + Black)、Java (Checkstyle)
- **增量检查**：仅检查Git仓库中变更的文件，自动识别重命名文件并跳过旧路径
- **自定义规则**：通过YAML配置自定义正则检查规则，灵活扩展检查能力
- **质量门禁**：可配置各检查工具的通过分数，不达标时阻止合并
- **安全自动修复**：仅应用安全的自动修复（ESLint安全规则 + Black格式化）
- **HTML报告**：生成带图表和趋势对比的美观HTML报告
- **多种报告格式**：表格、JSON、纯文本、HTML输出
- **CI平台自动识别**：自动检测GitLab、GitHub、Travis、CircleCI、Jenkins、Bitbucket
- **灵活配置**：通过YAML文件自定义所有检查行为

## 项目结构

```
code_quality_checker/
├── __init__.py              # 版本信息
├── __main__.py              # 模块入口
├── cli.py                   # 命令行接口
├── config.py                # 配置加载和数据类
├── git_utils.py             # Git仓库操作和增量检查
├── checker.py               # 检查协调器
├── report.py                # 报告生成
├── threshold.py             # 阈值检查
└── linters/
    ├── __init__.py
    ├── base.py              # 检查器基类
    ├── eslint.py            # ESLint检查器
    ├── pylint.py            # Pylint检查器
    └── checkstyle.py        # Checkstyle检查器
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 安装必要的linter工具

```bash
# JavaScript/TypeScript
npm install -g eslint

# Python
pip install pylint

# Java (下载Checkstyle JAR)
wget https://github.com/checkstyle/checkstyle/releases/download/checkstyle-10.12.6/checkstyle-10.12.6-all.jar -O checkstyle.jar
```

### 3. 初始化配置

```bash
python -m code_quality_checker init-config
```

这会在当前目录创建 `.code-quality.yml` 配置文件。

### 4. 运行检查

```bash
# 增量检查（默认，只检查变更文件）
python -m code_quality_checker check

# 全量检查
python -m code_quality_checker check --no-incremental

# 指定基准分支
python -m code_quality_checker check --base-branch develop

# 自动修复
python -m code_quality_checker check --fix

# 检查指定文件
python -m code_quality_checker check src/file1.py src/file2.js

# JSON格式输出
python -m code_quality_checker check --format json
```

## 配置说明

`.code-quality.yml` 配置文件示例：

```yaml
thresholds:
  error: 0           # 错误数阈值，超过则CI失败
  warning: 10        # 警告数阈值
  pylint_score: 8.0  # Pylint最低分数要求

linters:
  eslint:
    enabled: true
    config_file: ".eslintrc.js"
    auto_fix: true
    extensions: [".js", ".jsx", ".ts", ".tsx", ".vue"]

  pylint:
    enabled: true
    config_file: ".pylintrc"
    auto_fix: false
    extensions: [".py"]
    args: ["--max-line-length=120"]

  checkstyle:
    enabled: true
    config_file: "checkstyle.xml"
    auto_fix: false
    extensions: [".java"]
    jar_path: "checkstyle.jar"

incremental:
  enabled: true
  base_branch: "main"

report:
  format: "table"
  output_dir: "quality-reports"
  show_summary: true

ci:
  fail_on_threshold: true
  generate_badge: true
```

## CLI命令参考

```bash
# 查看版本
code-quality-checker --version

# 查看帮助
code-quality-checker --help

# 子命令
code-quality-checker check [OPTIONS] [FILES]...   # 运行代码质量检查
code-quality-checker list [OPTIONS]                # 列出可用的linter
code-quality-checker init-config [OPTIONS]         # 生成默认配置文件
code-quality-checker show-changed [OPTIONS]        # 显示增量检查会检查的文件
```

### check 命令选项

| 选项 | 说明 |
|------|------|
| `--incremental/--no-incremental` | 启用/禁用增量检查 |
| `-b, --base-branch TEXT` | 增量检查的基准分支（默认：main） |
| `--fix/--no-fix` | 启用自动修复 |
| `-f, --format [table\|json\|text]` | 输出格式 |
| `--save-report/--no-save-report` | 保存JSON报告到文件 |
| `-c, --config PATH` | 指定配置文件路径 |
| `-r, --repo-path PATH` | 指定仓库路径 |

## CI/CD集成

### GitHub Actions

将 `.github/workflows/code-quality.yml` 复制到你的项目中即可。功能包括：

- PR（Pull Request）时自动进行增量检查
- 推送到主分支时进行全量检查
- 自动在PR中添加代码质量报告评论
- 上传检查报告作为artifact

### GitLab CI

将 `.gitlab-ci.yml` 复制到你的项目中即可。功能包括：

- MR（Merge Request）时自动进行增量检查
- 推送到主分支时进行全量检查
- 集成到GitLab Code Quality报告
- 检查失败时阻止MR合并

## 输出示例

### 表格格式（默认）

```
================================================================================
  Code Quality Report - 2026-05-21 15:30:00
================================================================================

Summary:
| Linter   |   Files |   Errors |   Warnings | Score   | Status   |
|----------|---------|----------|------------|---------|----------|
| eslint   |       5 |        0 |          2 | N/A     | PASS     |
| pylint   |       3 |        1 |          0 | 7.50    | FAIL     |

Total files checked: 8
Total errors: 1
Total warnings: 2

PYLINT Issues:
--------------------------------------------------------------------------------
File        |   Line |   Col | Severity   | Rule         | Message
------------|--------|-------|------------|--------------|---------------------------------
src/app.py  |     45 |     0 | error      | syntax-error | invalid syntax

================================================================================
  THRESHOLD VIOLATIONS:
================================================================================
  ✗ Error count (1) exceeds threshold (0)
  ✗ Pylint score (7.50) is below threshold (8.0)

✗ Quality checks failed!
```

### JSON格式

```json
{
  "timestamp": "2026-05-21 15:30:00",
  "total_errors": 1,
  "total_warnings": 2,
  "total_files_checked": 8,
  "threshold_passed": false,
  "threshold_violations": [
    "Error count (1) exceeds threshold (0)",
    "Pylint score (7.50) is below threshold (8.0)"
  ],
  "results": [...],
  "summary": {
    "by_linter": {
      "eslint": {"errors": 0, "warnings": 2, "score": null, "files_checked": 5},
      "pylint": {"errors": 1, "warnings": 0, "score": 7.5, "files_checked": 3}
    }
  }
}
```

## 作为Python库使用

```python
from code_quality_checker.config import load_config
from code_quality_checker.checker import CodeQualityChecker

# 加载配置
config = load_config(".code-quality.yml")

# 创建检查器
checker = CodeQualityChecker(config, repo_path=".")

# 运行检查
report, exit_code = checker.run(
    incremental=True,
    base_branch="main",
    auto_fix=False,
    format="json",
)

# 访问结果
print(f"Total errors: {report.total_errors}")
print(f"Total warnings: {report.total_warnings}")
print(f"Threshold passed: {report.threshold_passed}")

for result in report.results:
    print(f"{result.linter_name}: {result.error_count} errors")
```

## 扩展自定义Linter

1. 在 `code_quality_checker/linters/` 目录下创建新的检查器类，继承 `BaseLinter`
2. 实现 `is_available()` 和 `check_files()` 方法
3. 在 `checker.py` 的 `LINTER_CLASSES` 字典中注册新的linter

示例：

```python
from .base import BaseLinter, LinterResult, LinterIssue

class MyLinter(BaseLinter):
    name = "mylinter"
    extensions = [".xxx"]

    def is_available(self) -> bool:
        # 检查linter是否已安装
        returncode, _, _ = self._run_command(["mylinter", "--version"])
        return returncode == 0

    def check_files(self, files, auto_fix=False):
        result = LinterResult(linter_name=self.name, success=True)
        # 实现检查逻辑
        return result
```

## License

MIT
