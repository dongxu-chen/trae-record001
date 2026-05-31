# DepGuard - 微服务依赖版本管理工具

## 项目概述

DepGuard 是一个面向 DevOps 团队和 Java 微服务开发者的依赖版本管理工具，提供以下核心功能：

- **依赖扫描**: 自动解析 Maven/Gradle 项目的依赖树
- **全依赖树版本冲突检测**: 使用 Maven Resolver 完整遍历传递依赖，检测所有层级的版本冲突
- **安全漏洞扫描**: 集成 NVD CVE 数据库检测依赖中的安全漏洞
- **过时依赖检测**: 自动识别过期的依赖库
- **智能升级建议**: 基于语义化版本规则提供升级建议
- **ASM 二进制兼容性检查**: 使用 Java ASM 字节码分析，检测 API 变更和 Breaking Changes
- **依赖健康评分**: 综合漏洞、新旧、流行度的多维度评分系统
- **自动升级**: 高兼容性依赖自动升级，一键创建 PR
- **依赖使用分析**: ASM 字节码分析检测未使用的依赖，建议移除
- **兼容性评估**: 综合版本规则和二进制分析，评估升级风险
- **PR 预测试构建验证**: 在创建 PR 前先验证构建是否成功
- **批量升级 PR**: 一键创建批量依赖升级的 Pull Request

## 技术栈

### 后端
- Java 17
- Spring Boot 3.2
- Maven Resolver (依赖解析)
- GitHub API (org.kohsuke:github-api)
- JPA + H2 Database (嵌入式)
- Caffeine 缓存

### 前端
- React 18 + TypeScript
- Vite
- TailwindCSS 3
- Zustand (状态管理)
- Lucide React (图标)
- Recharts (图表)

## 快速开始

### 启动前端

```bash
cd frontend
npm install
npm run dev
```

访问 http://localhost:5173 (或后续可用端口)

### 启动后端

**前置条件**: Java 17+, Maven 3.6+

```bash
cd backend
mvn spring-boot:run
```

或者使用 Maven Wrapper:
```bash
cd backend
./mvnw.cmd spring-boot:run
```

后端 API 运行在 http://localhost:8080

### 访问 H2 控制台

http://localhost:8080/h2-console
- JDBC URL: `jdbc:h2:file:./depguard`
- 用户名: `sa`
- 密码: (留空)

## 项目结构

```
depguard/
├── backend/                          # Spring Boot 后端
│   ├── src/main/java/com/depguard/
│   │   ├── config/                   # 配置类 (Async, Cache, CORS, GitHub)
│   │   ├── controller/               # REST API 控制器
│   │   ├── dto/                      # 数据传输对象
│   │   ├── entity/                   # JPA 实体
│   │   ├── enums/                    # 枚举类型
│   │   ├── repository/               # JPA Repository
│   │   ├── service/                  # 业务逻辑服务
│   │   └── DepGuardApplication.java  # 主类
│   └── src/main/resources/
│       ├── application.yml           # 应用配置
│       └── data.sql                  # 初始化数据
└── frontend/                         # React 前端
    ├── src/
    │   ├── components/               # 组件
    │   │   ├── layout/               # 布局组件
    │   │   └── ui/                   # UI 组件
    │   ├── pages/                    # 页面
    │   ├── stores/                   # Zustand 状态管理
    │   ├── types/                    # TypeScript 类型定义
    │   └── utils/                    # 工具函数
    └── package.json
```

## 核心引擎功能

### 1. 全依赖树版本冲突检测 (Maven Resolver)

使用 Eclipse Aether (Maven Resolver) 构建完整的依赖树，包括所有传递依赖，然后进行跨服务的版本冲突检测。

**核心类**: [MavenDependencyTreeResolver.java](file:///d:/Project/trae/project/record001/591/backend/src/main/java/com/depguard/engine/MavenDependencyTreeResolver.java)

**功能特性**:
- 完整递归解析所有传递依赖
- 构建依赖树并记录深度层级
- 跨服务比对每个 `groupId:artifactId` 的版本
- 按冲突数量分级严重程度 (HIGH/MEDIUM/LOW)
- 提供推荐的统一版本

**API 端点**:
- `GET /api/conflicts/full-tree` - 获取全依赖树的版本冲突
- `GET /api/services/{repoId}/dependencies/full-tree` - 获取单个服务的完整依赖树

---

### 2. ASM 二进制兼容性检查

使用 ObjectWeb ASM 字节码分析框架，对比升级前后的 JAR 文件，检测 API 级别的不兼容变更。

**核心类**: [BinaryCompatibilityChecker.java](file:///d:/Project/trae/project/record001/591/backend/src/main/java/com/depguard/engine/BinaryCompatibilityChecker.java)

**检测项**:
- ✅ 移除的类 (Removed Classes)
- ✅ 移除的方法 (Removed Methods)
- ✅ 移除的字段 (Removed Fields)
- ✅ 方法签名变更 (Method Signature Changes)
- ✅ 访问权限变更 (Access Modifier Changes)
- ✅ 字段类型变更 (Field Type Changes)

**兼容性评分算法**:
```
问题比率 = 问题数 / 总类数
- 0%     → 95分
- <1%    → 90分
- 1-5%   → 80分
- 5-10%  → 70分
- 10-20% → 60分
- 20-30% → 50分
- 30-50% → 40分
- >50%   → 30分
```

---

### 3. PR 预测试构建验证

在创建批量升级 PR 之前，先进行构建验证，确保升级不会破坏现有功能。

**核心类**: [BuildVerificationService.java](file:///d:/Project/trae/project/record001/591/backend/src/main/java/com/depguard/service/BuildVerificationService.java)

**验证流程**:
1. 模拟依赖版本更新
2. 编译兼容性检查
3. 依赖冲突检测
4. 单元测试模拟运行
5. (可选) 实际 Maven 构建

**验证状态**:
- `PENDING` - 等待中
- `RUNNING` - 执行中
- `SUCCESS` - 验证通过
- `FAILED` - 验证失败
- `SKIPPED` - 跳过验证

**API 端点**:
- `POST /api/upgrades/verify/{repoId}` - 同步验证构建
- `POST /api/upgrades/verify/async/{repoId}` - 异步验证
- `GET /api/upgrades/verify/status/{buildId}` - 获取验证状态
- `POST /api/upgrades/batch-pr/verify` - 验证并创建 PR

---

## API 端点

### 仪表盘

### 仓库管理
- `GET /api/repositories` - 获取仓库列表
- `POST /api/repositories` - 添加新仓库
- `DELETE /api/repositories/{id}` - 删除仓库
- `POST /api/repositories/{id}/scan` - 触发仓库扫描
- `GET /api/repositories/{id}/scans` - 获取扫描历史

### 依赖分析
- `GET /api/services/{repoId}/dependencies` - 获取服务依赖树
- `GET /api/conflicts` - 获取全局版本冲突
- `GET /api/services/{repoId}/conflicts` - 获取服务版本冲突

### 漏洞报告
- `GET /api/vulnerabilities` - 获取漏洞列表
- `GET /api/vulnerabilities/{cveId}` - 获取 CVE 详情
- `GET /api/vulnerabilities/stats` - 获取漏洞统计

### 升级建议
- `GET /api/upgrades` - 获取升级建议列表
- `POST /api/upgrades/batch-pr` - 创建批量升级 PR
- `GET /api/upgrades/compatibility/{groupId}/{artifactId}` - 获取兼容性矩阵

## 配置 GitHub Token

为了使用 GitHub 集成功能，需要配置 GitHub Personal Access Token:

1. 在 GitHub 上创建 Token: Settings -> Developer settings -> Personal access tokens
2. 设置环境变量: `GITHUB_TOKEN=your_token`
3. 或者修改 `backend/src/main/resources/application.yml` 中的 `depguard.github.token`

## 核心特性说明

### 1. 依赖解析引擎
- Maven: 使用 `maven-model` 精确解析 pom.xml
- Gradle: 使用正则解析 build.gradle
- 支持直接依赖和传递依赖识别

### 2. 版本冲突检测
- 跨仓库按 `groupId:artifactId` 分组
- 检测不同版本的使用
- 按严重程度分级 (HIGH/MEDIUM/LOW)

### 3. 安全漏洞扫描
- 集成 NVD CVE 数据库
- CVSS 评分系统
- 影响范围分析

### 4. 兼容性评估算法
- PATCH 升级: ~95 分 (安全)
- MINOR 升级: 60-90 分 (根据版本间距)
- MAJOR 升级: 20-70 分 (根据大版本差)
- 结合 Breaking Changes 识别调整评分

### 5. 健康评分
- 基准分: 100 分
- 版本冲突: 每个扣 5 分
- 安全漏洞: 每个扣 10 分
- 过时依赖: 每个扣 2 分
- 最低分: 0 分

## 前端页面

1. **仪表盘** (`/`) - 全局概览、风险统计、健康评分
2. **漏洞报告** (`/vulnerabilities`) - CVE 列表、详情、筛选
3. **升级建议** (`/upgrades`) - 升级推荐、兼容性、批量 PR
4. **健康管理** (`/health`) - 健康评分、使用分析、自动升级
5. **仓库管理** (`/repositories`) - 仓库接入、扫描调度
6. **服务详情** (`/services/:id`) - 依赖树、版本冲突
7. **CVE 详情** (`/vulnerabilities/:cveId`) - 漏洞详细信息

## 设计特点

- **暗色主题**: 深青色 (#0A2540) + 亮绿色 (#00D4AA)
- **JetBrains Mono**: 代码和版本号使用等宽字体
- **微交互动画**: 卡片发光、脉冲告警、平滑过渡
- **响应式设计**: 支持桌面、平板、移动端
- **Mock 数据**: 后端不可用时自动降级使用模拟数据
