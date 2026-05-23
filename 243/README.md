# CI/CD 流水线自动化工具

一个功能完整的CI/CD流水线自动化工具，支持多仓库监听、并行任务执行、阶段式流水线。

## 功能特性

### 核心功能
- ✅ **多仓库监听**: 支持 GitHub 和 GitLab Webhook
- ✅ **阶段式流水线**: 编译-测试-构建-部署 四阶段执行
- ✅ **并行任务执行**: 支持阶段内任务并行执行
- ✅ **条件执行**: 基于分支、前序阶段状态等条件判断
- ✅ **任务缓存**: 支持 Maven、npm 等依赖缓存
- ✅ **构建产物归档**: 自动归档和管理构建产物
- ✅ **Docker 集成**: 基于 Docker 的隔离执行环境
- ✅ **Jenkins API 集成**: 可触发 Jenkins 任务

### 技术栈
- **Node.js**: 后端运行时
- **Docker**: 容器化执行环境
- **Jenkins API**: 外部CI系统集成
- **Express**: Web服务器框架

## 快速开始

### 1. 环境要求
- Node.js 18+
- Docker (可选但推荐)
- Git

### 2. 安装依赖

```bash
npm install
```

### 3. 配置

复制环境变量示例文件：

```bash
cp .env.example .env
```

编辑 `.env` 文件配置：

```env
GITHUB_WEBHOOK_SECRET=your-github-webhook-secret
GITLAB_WEBHOOK_SECRET=your-gitlab-webhook-secret
JENKINS_URL=http://localhost:8080
JENKINS_USERNAME=admin
JENKINS_API_TOKEN=your-jenkins-api-token
```

编辑 `config.yaml` 配置仓库和流水线：

```yaml
repositories:
  - name: "username/my-app"
    url: "https://github.com/username/my-app.git"
    branch: "main"
    stages:
      - name: checkout
        script:
          - "git clone $CLONE_URL ."
          - "git checkout $GIT_COMMIT"
      
      - name: build
        image: node:18-alpine
        script:
          - "npm install"
          - "npm run build"
        cache:
          key: "node-modules"
          paths:
            - "node_modules"
```

### 4. 启动服务

#### 本地启动

```bash
npm start
```

#### Docker 启动

```bash
docker-compose up -d
```

#### 包含 Jenkins 的完整启动

```bash
docker-compose --profile jenkins up -d
```

## Webhook 配置

### GitHub Webhook
1. 进入仓库 Settings → Webhooks → Add webhook
2. Payload URL: `http://your-server:3000/webhook/github`
3. Content type: `application/json`
4. Secret: 与配置中的 `GITHUB_WEBHOOK_SECRET` 一致
5. 选择事件: Just the push event

### GitLab Webhook
1. 进入项目 Settings → Webhooks
2. URL: `http://your-server:3000/webhook/gitlab`
3. Secret Token: 与配置中的 `GITLAB_WEBHOOK_SECRET` 一致
4. 选择触发事件: Push events

## 流水线配置

### 基础配置

```yaml
stages:
  - name: 阶段名称
    image: docker-image:tag  # 可选，默认使用 node:18-alpine
    script:  # 执行命令列表
      - "command1"
      - "command2"
    parallel: false  # 是否并行执行任务
    required: true   # 该阶段失败是否终止流水线
```

### 并行任务

```yaml
- name: test
  parallel: true
  tasks:
    - name: unit-test
      script:
        - "npm run test:unit"
    - name: lint
      script:
        - "npm run lint"
    - name: e2e-test
      script:
        - "npm run test:e2e"
```

### 条件执行

#### 基于分支

```yaml
- name: deploy
  condition:
    branch: ["main", "master"]
  script:
    - "deploy-script.sh"
```

#### 基于前序阶段

```yaml
- name: notification
  condition:
    previousStage: test
  script:
    - "send-notification.sh"
```

#### 基于执行状态

```yaml
- name: rollback
  condition:
    status: failure  # 仅在之前有失败阶段时执行
  script:
    - "rollback.sh"
```

### 任务缓存

#### Maven 依赖缓存

```yaml
- name: build
  image: maven:3.8-openjdk-17
  script:
    - "mvn clean package"
  cache:
    key: "maven-deps"
    paths:
      - "~/.m2/repository"
```

#### Node.js 依赖缓存

```yaml
- name: install
  image: node:18-alpine
  script:
    - "npm install"
  cache:
    key: "node-modules-{{ checksum 'package-lock.json' }}"
    paths:
      - "node_modules"
```

### 构建产物归档

```yaml
- name: build
  script:
    - "npm run build"
  artifacts:
    paths:
      - "dist/"
      - "build/"
    name: "build-output"
    retentionDays: 30
```

### Jenkins 集成

```yaml
- name: deploy
  useJenkins: true
  jobName: "my-app-deploy"
  parameters:
    ENV: "production"
    VERSION: "$GIT_COMMIT"
```

### Docker 卷挂载

```yaml
- name: docker-build
  image: docker:latest
  script:
    - "docker build -t my-app ."
  volumes:
    - "/var/run/docker.sock:/var/run/docker.sock"
    - "/host/path:/container/path:ro"
```

## API 接口

### 健康检查

```
GET /health
```

### 获取活动流水线

```
GET /pipelines
```

### 获取流水线状态

```
GET /pipelines/:id
```

### 触发 GitHub Webhook

```
POST /webhook/github
```

### 触发 GitLab Webhook

```
POST /webhook/gitlab
```

## 环境变量

流水线执行时自动注入以下环境变量：

| 变量名 | 说明 |
|--------|------|
| `PIPELINE_ID` | 流水线唯一ID |
| `WORKSPACE` | 工作目录路径 |
| `CI` | 固定为 "true" |
| `GIT_BRANCH` | Git 分支名 |
| `GIT_COMMIT` | Git Commit Hash |
| `GIT_REPOSITORY` | 仓库名称 |
| `GIT_AUTHOR` | 提交作者 |

## 目录结构

```
.
├── src/
│   ├── index.js              # 主入口文件
│   ├── config/
│   │   └── index.js          # 配置管理
│   ├── webhook/
│   │   └── server.js         # Webhook服务器
│   ├── pipeline/
│   │   ├── engine.js         # 流水线引擎
│   │   ├── stage.js          # 阶段执行器
│   │   └── context.js        # 流水线上下文
│   ├── cache/
│   │   └── manager.js        # 缓存管理器
│   ├── archive/
│   │   └── manager.js        # 归档管理器
│   ├── executors/
│   │   └── docker.js         # Docker执行器
│   └── integrations/
│       └── jenkins.js        # Jenkins集成
├── workspace/                # 流水线工作目录
├── cache/                    # 缓存存储
├── archives/                 # 构建产物归档
├── logs/                     # 日志文件
├── config.yaml               # 主配置文件
├── docker-compose.yml        # Docker编排
├── Dockerfile                # 镜像构建文件
└── package.json
```

## 常见问题

### Docker 不可用怎么办？
系统会自动降级到本地执行模式，直接在主机上执行命令。

### 如何查看流水线日志？
日志文件位于 `logs/pipeline.log`，也可以通过 API 获取流水线状态。

### 缓存过期时间是多久？
默认 24 小时，可在 `config.yaml` 的 `cache.ttl` 配置（毫秒）。

## 许可证

MIT
