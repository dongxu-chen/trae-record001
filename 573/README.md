# Docker 镜像安全扫描工具

一个功能完整的Docker镜像安全扫描工具，支持CVE漏洞扫描、敏感文件检测、配置风险检查，提供Web界面、REST API和CLI工具。

## ✨ 功能特性

- **🔍 漏洞扫描 (CVE)** - 基于Trivy扫描已知安全漏洞
- **🔑 敏感信息检测** - 检测密码、密钥、API令牌等敏感数据（正则+关键词+文件名三重检测）
- **⚙️ 配置风险检查** - 10+条安全规则，检查容器配置最佳实践
- **🔄 漏洞库自动更新** - 每日自动更新Trivy漏洞库，支持离线导入导出
- **🏆 基础镜像推荐** - 扫描后智能推荐更安全的基础镜像，含Dockerfile迁移建议
- **🔧 自动修复** - 可修复问题自动生成修复PR，支持GitHub/GitLab
- **📋 CIS合规基线** - 对照CIS Docker Benchmark 21项控制检测，评分分级
- **🚀 多镜像并发扫描** - 支持同时扫描多个Docker镜像
- **📊 报告输出** - JSON/HTML/JUnit XML格式报告，CI原生支持
- **🌐 Web界面** - React前端，直观易用
- **🔌 REST API** - 完整的API接口，便于集成
- **💻 CLI工具** - 命令行工具，支持CI/CD集成
- **🐳 Docker部署** - 一键部署，开箱即用

## 🏗️ 技术栈

**后端:**
- Python 3.11+
- FastAPI - REST API框架
- Trivy - CVE漏洞扫描引擎
- Docker SDK - 镜像操作

**前端:**
- React 18
- Vite - 构建工具
- Tailwind CSS - 样式框架
- Recharts - 数据可视化

## 📦 快速开始

### 环境要求

- Python 3.11+
- Node.js 18+
- Docker
- Trivy

### 方式一: Docker Compose 部署

```bash
# 克隆项目
git clone <repo-url>
cd docker-security-scanner

# 启动服务
docker-compose up -d

# 访问Web界面
# 前端: http://localhost:3000
# API文档: http://localhost:8000/docs
```

### 方式二: 本地开发

**1. 安装后端依赖**
```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

**2. 安装Trivy**
```bash
# macOS
brew install aquasecurity/trivy/trivy

# Linux
curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh

# Windows
scoop install trivy
```

**3. 启动后端服务**
```bash
python -m backend.api.main
# 或
uvicorn backend.api.main:app --reload
```

**4. 启动前端**
```bash
cd frontend
npm install
npm run dev
```

## 🎯 使用方式

### 1. Web界面

访问 `http://localhost:3000`

- **仪表盘** - 查看系统状态和最近任务
- **新建扫描** - 添加Docker镜像进行扫描
- **任务列表** - 查看所有扫描任务
- **任务详情** - 查看详细扫描结果（漏洞、敏感信息、规则检查）
- **报告** - 下载和管理扫描报告
- **规则** - 查看安全检查规则

### 2. CLI工具

```bash
# 查看帮助
python cli/scanner_cli.py --help

# 扫描单个镜像
python cli/scanner_cli.py scan --images nginx:latest --wait

# 扫描多个镜像
python cli/scanner_cli.py scan --images nginx:latest alpine:3.18 --wait

# 生成报告
python cli/scanner_cli.py scan --images myapp:latest --wait --output-html --output-json

# CI集成: 风险分数超过50则失败
python cli/scanner_cli.py scan --images myapp:latest --wait --fail-on-risk 50

# 查看任务状态
python cli/scanner_cli.py status <job_id>

# 查看任务结果
python cli/scanner_cli.py results <job_id>
python cli/scanner_cli.py results <job_id> --format json

# 列出任务
python cli/scanner_cli.py list --limit 10

# 列出报告
python cli/scanner_cli.py reports
```

### 3. REST API

API文档: `http://localhost:8000/docs`

**创建扫描任务:**
```bash
curl -X POST "http://localhost:8000/api/scan" \
  -H "Content-Type: application/json" \
  -d '{
    "images": ["nginx:latest", "alpine:3.18"],
    "scan_types": ["vulnerabilities", "secrets", "rules"],
    "generate_reports": true
  }'
```

**获取任务状态:**
```bash
curl "http://localhost:8000/api/scan/<job_id>"
```

**获取任务结果:**
```bash
curl "http://localhost:8000/api/scan/<job_id>/results"
```

**生成报告:**
```bash
curl -X POST "http://localhost:8000/api/scan/<job_id>/reports?report_type=html"
```

### 4. CI/CD 集成

**GitHub Actions:**
```yaml
- name: Run security scan
  run: |
    python cli/scanner_cli.py scan \
      --images myapp:${{ github.sha }} \
      --wait \
      --output-json \
      --fail-on-risk 50
```

**GitLab CI:**
```yaml
security_scan:
  script:
    - python cli/scanner_cli.py scan --images $DOCKER_IMAGE --wait --fail-on-risk 60
```

## 📁 项目结构

```
docker-security-scanner/
├── backend/                    # 后端代码
│   ├── api/                    # REST API
│   │   └── main.py            # FastAPI主入口
│   ├── core/                   # 核心模块
│   │   └── scan_manager.py    # 扫描管理器
│   ├── scanners/               # 扫描器
│   │   ├── trivy_scanner.py   # Trivy CVE扫描
│   │   ├── trivy_db_updater.py # Trivy漏洞库自动更新
│   │   ├── sensitive_scanner.py # 敏感信息扫描
│   │   ├── base_image_recommender.py # 基础镜像推荐
│   │   ├── auto_fix_engine.py # 自动修复与PR生成
│   │   └── cis_benchmark.py   # CIS Benchmark合规检测
│   ├── engine/                 # 规则引擎
│   │   └── rules_engine.py    # 配置规则检查
│   ├── reports/                # 报告生成
│   │   ├── report_generator.py # 报告生成器（JUnit/JSON/HTML）
│   │   └── templates/
│   └── config/                 # 配置文件
│       ├── config.py
│       ├── sensitive_patterns.yaml
│       └── rules.yaml
├── frontend/                   # React前端
│   ├── src/
│   │   ├── components/
│   │   └── pages/
│   └── package.json
├── cli/                        # 命令行工具
│   └── scanner_cli.py
├── reports/                    # 报告目录
├── .github/workflows/          # GitHub Actions
├── .gitlab-ci.yml             # GitLab CI配置
├── Dockerfile                  # 后端Dockerfile
├── docker-compose.yml          # Docker Compose配置
├── requirements.txt            # Python依赖
├── .env.example               # 环境变量示例
└── README.md
```

## 🔧 配置说明

### 核心配置 (.env)

```env
# 漏洞库自动更新
TRIVY_DB_AUTO_UPDATE=True              # 启用自动更新
TRIVY_DB_UPDATE_INTERVAL_HOURS=24      # 更新间隔（小时）
TRIVY_DB_DIR=/tmp/trivy-cache/db       # 数据库存储目录
TRIVY_OFFLINE_DB_PATH=                 # 预加载离线库路径

# 敏感信息检测
SENSITIVE_SCAN_KEYWORDS=True           # 启用关键词扫描
SENSITIVE_SCAN_FILES=True              # 启用可疑文件扫描
SENSITIVE_SCAN_MAX_FILE_SIZE_MB=50     # 扫描文件大小限制

# 报告生成
DEFAULT_REPORT_FORMAT=json             # 默认报告格式
JUNIT_REPORT_FAIL_ON_SEVERITY=MEDIUM   # JUnit报告失败阈值
```

### 扫描规则配置

编辑 `backend/config/rules.yaml` 自定义安全检查规则:

```yaml
rules:
  - id: R001
    name: Root User Check
    description: Container should not run as root user
    severity: high
    category: configuration
    check: |
      def check(config):
          user = config.get('Config', {}).get('User', '')
          return user == '' or user == 'root'
    remediation: Use USER instruction to switch to a non-root user
```

### 敏感信息模式配置

编辑 `backend/config/sensitive_patterns.yaml` 添加自定义检测模式:

```yaml
# 正则模式匹配
patterns:
  - name: Custom API Key
    pattern: 'my_api_key_[a-zA-Z0-9]{32}'
    severity: high
    description: Custom API key detected

# 内容关键词匹配
content_keywords:
  - name: Password Comment
    keywords: ['password', 'passwd', 'pwd']
    severity: medium
    description: Password-related keywords detected in comments

# 可疑文件检测
suspicious_files:
  - name: SSH Key Files
    patterns: ['id_rsa', 'id_dsa', '*.pem']
    severity: critical
    description: Private SSH key file detected
```

## 🔄 漏洞库自动更新

服务启动时会自动开始每日漏洞库更新，无需人工干预。

**离线使用流程:**

1. **在联网机器导出离线包:**
```bash
python cli/scanner_cli.py db update --force
python cli/scanner_cli.py db export --path /tmp/trivy-db-offline
```

2. **在离线机器导入:**
```bash
python cli/scanner_cli.py db import --path /path/to/trivy-db-offline.tar.gz
```

## 📝 JUnit 报告格式

工具生成标准JUnit XML格式报告，包含以下测试用例:

- **漏洞测试** - 每个CVE作为一个测试用例
- **敏感信息测试** - 每个敏感信息发现作为一个测试用例
- **规则检查测试** - 每个规则违反作为一个测试用例
- **风险评分测试** - 整体风险评估结果

示例输出:
```xml
<testsuites>
  <testsuite name="Security Scan" tests="25" failures="3" errors="0">
    <testcase name="CVE-2023-12345" classname="Vulnerability">
      <failure type="CRITICAL">
        OpenSSL vulnerability...
      </failure>
    </testcase>
    <testcase name="API Key in config.py" classname="Secret">
      <failure type="HIGH">
        API token detected...
      </failure>
    </testcase>
  </testsuite>
</testsuites>
```

## 📊 风险评分说明

| 分数 | 风险等级 | 说明 |
|------|----------|------|
| 0    | 安全     | 未发现安全问题 |
| 1-29 | 低       | 存在少量低风险问题 |
| 30-49| 中       | 建议修复 |
| 50-69| 高       | 应尽快修复 |
| 70+  | 严重     | 必须立即修复 |

风险评分权重:
- 漏洞 (CVE): 40%
- 敏感信息: 30%
- 配置规则: 30%

## 🔒 安全建议

1. **定期扫描** - 在CI/CD流水线中集成安全扫描
2. **及时修复** - 优先修复高风险漏洞
3. **最小权限** - 容器应使用非root用户运行
4. **密钥管理** - 使用Docker Secrets或密钥管理系统
5. **基础镜像** - 选择经过安全验证的基础镜像
6. **镜像精简** - 移除不必要的工具和文件

## 🤝 贡献指南

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📄 许可证

MIT License

## 📧 问题反馈

如有问题或建议，请提交Issue。
