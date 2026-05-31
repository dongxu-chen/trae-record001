# Git Branch Policy Checker

一个全面的Git分支策略检查工具，帮助团队维护代码质量和分支管理规范。

## 功能特性

### ✅ 分支命名规范检查
- 支持正则表达式定义分支命名规则
- 预定义常用分支类型：feature, bugfix, hotfix, release
- 自定义错误级别（error/warning/info）

### 🔀 合并方向检查
- 定义允许的分支合并路径
- 阻止危险的合并操作（如 main → feature）
- 支持glob模式匹配

### 📏 PR大小检查
- 检查变更文件数量
- 检查新增/删除代码行数
- 支持警告和错误两个阈值
- 可视化统计图表

### 📊 提交频率分析
- 统计每日/每周提交数量
- 按作者分析提交分布
- 检测异常高频提交
- 历史趋势图表

### 🔧 自动修复
- 分支名自动重命名建议
- 提交压缩（squash）
- 预览模式，安全无风险

### 🤖 CI/CD集成
- GitHub Actions 开箱即用
- JSON格式输出便于集成
- 非零退出码标记失败

### 🎨 Web界面
- React + Flask 前后端分离
- 实时可视化检查结果
- 交互式图表展示
- 深色主题设计

## 技术栈

**后端:**
- Python 3.10+
- GitPython - Git操作
- Flask - API服务
- PyYAML - 配置解析
- 正则引擎 - 命名规则匹配
- 自定义规则引擎

**前端:**
- React 18
- Axios - HTTP客户端
- Recharts - 图表库
- 纯CSS样式

## 快速开始

### 1. 安装依赖

```bash
# 安装Python依赖
pip install -r requirements.txt

# 安装前端依赖
cd frontend
npm install
```

### 2. 配置规则

编辑 `config/rules.yaml` 自定义检查规则：

```yaml
branch_naming:
  patterns:
    - name: feature
      pattern: ^feature/[A-Z]+-\d+-.+$
      description: feature/TICKET-123-description
```

### 3. 命令行使用

```bash
# 基本使用
python cli.py

# 指定分支
python cli.py --source feature/ABC-123 --target develop

# JSON输出
python cli.py --json > results.json

# 列出所有分支
python cli.py --list-branches
```

### 4. 启动Web界面

```bash
# 启动后端API (端口5000)
python -m backend.api

# 启动前端开发服务器 (端口3000)
cd frontend
npm start
```

访问 http://localhost:3000 查看Web界面。

## CI集成

### GitHub Actions

创建 `.github/workflows/branch-policy.yml`:

```yaml
name: Branch Policy Check
on: [pull_request]

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
      - run: pip install -r requirements.txt
      - run: python cli.py
```

## 项目结构

```
.
├── backend/
│   ├── __init__.py
│   ├── api.py              # Flask API服务
│   ├── git_utils.py        # Git操作工具类
│   ├── config.py           # 配置管理
│   ├── rule_engine.py      # 规则引擎核心
│   ├── auto_fix.py         # 自动修复功能
│   ├── ci_integration.py   # CI集成模块
│   └── checkers/
│       ├── branch_naming.py      # 分支命名检查
│       ├── merge_direction.py    # 合并方向检查
│       ├── pr_size.py            # PR大小检查
│       └── commit_frequency.py   # 提交频率检查
├── frontend/
│   ├── src/
│   │   ├── App.js
│   │   └── components/
│   └── package.json
├── config/
│   └── rules.yaml          # 规则配置文件
├── tests/
│   └── test_checkers.py
├── .github/
│   └── workflows/
│       └── branch-policy-check.yml
├── cli.py                  # 命令行入口
├── requirements.txt
└── README.md
```

## API接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| GET | `/api/branches` | 获取分支列表 |
| GET | `/api/check/all` | 运行所有检查 |
| GET | `/api/check/branch-naming` | 分支命名检查 |
| GET | `/api/check/merge-direction` | 合并方向检查 |
| GET | `/api/check/pr-size` | PR大小检查 |
| GET | `/api/check/commit-frequency` | 提交频率检查 |
| POST | `/api/fix/branch-name` | 分支名修复 |
| POST | `/api/fix/squash-commits` | 提交压缩 |
| GET | `/api/config` | 获取配置 |

## 运行测试

```bash
python -m pytest tests/ -v
```

## 许可证

MIT License
