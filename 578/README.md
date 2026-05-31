# Flink Job Resource Recommender

Flink作业资源推荐工具 - 基于Flink REST API的智能资源配置推荐系统。

## 功能特性

### 核心功能
- **作业拓扑分析** - 分析Flink作业的DAG结构、算子耗时、并行度配置
- **数据倾斜检测** - 通过统计分析检测各subtask的数据分布，识别数据倾斜
- **资源优化推荐** - 基于性能数据自动推荐最优的内存、CPU、并行度配置
- **历史数据学习** - 基于历史运行数据进行趋势分析和预测
- **成本估算** - TCO计算、成本对比、缩放模拟

### 技术架构

#### 后端技术栈
- **Java 11 + Spring Boot 2.7.x
- **Flink REST API** - 与Flink集群交互
- **Apache Commons Math3** - 统计算法库
- **Spring Data JPA + H2** - 数据持久化
- **OkHttp3** - HTTP客户端

#### 前端技术栈
- **React 18** + **React Router 6
- **Material UI (MUI)** - UI组件库
- **Recharts** - 数据可视化
- **Axios** - HTTP客户端

## 项目结构
```
├── backend/
│   ├── src/main/java/com/flink/recommender/
│   │   ├── FlinkResourceRecommenderApplication.java
│   │   ├── config/          # 配置类
│   │   ├── controller/      # REST API控制器
│   │   ├── service/         # 业务逻辑
│   │   ├── model/           # 数据模型
│   │   ├── repository/      # 数据访问层
│   │   ├── flink/           # Flink REST API客户端
│   │   ├── analysis/        # 作业分析模块
│   │   ├── recommendation/  # 资源推荐算法
│   │   ├── history/         # 历史数据分析
│   │   └── cost/            # 成本估算
│   └── pom.xml
│   └── src/main/resources/
│       └── application.yml
└── frontend/
│   ├── package.json
│   └── src/
│       ├── App.js
│       ├── components/
│       ├── pages/
│       └── services/
└── README.md
```

## 快速开始

### 后端启动

```bash
cd backend

# 编译项目
mvn clean package

# 运行应用
mvn spring-boot:run
```

后端服务将在 `http://localhost:8080` 启动

### 前端启动

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm start
```

前端应用将在 `http://localhost:3000` 启动

## API接口

### 作业分析API
- `GET /api/jobs` - 获取所有作业列表
- `GET /api/jobs/{jobId}/analyze` - 分析指定作业
- `GET /api/jobs/{jobId}/history` - 获取作业历史
- `GET /api/jobs/{jobId}/trends` - 获取作业趋势分析
- `GET /api/jobs/{jobId}/predict` - 预测资源需求

### 资源推荐API
- `GET /api/recommendations/{jobId}` - 获取资源推荐
- `POST /api/recommendations/{jobId}/apply` - 应用推荐配置
- `GET /api/recommendations/{jobId}/cost-comparison` - 成本对比
- `GET /api/recommendations/{jobId}/tco` - 总拥有成本计算

### 成本估算API
- `POST /api/cost/calculate` - 计算配置成本
- `POST /api/cost/compare` - 对比配置成本
- `POST /api/cost/tco` - 计算TCO
- `POST /api/cost/simulate-scaling` - 模拟缩放成本

## 核心算法

### 数据倾斜检测
- **倾斜因子计算：max_records / avg_records
- **变异系数：std_dev / mean
- **阈值判断**：
  - 倾斜因子 >= 2.0 → HIGH
  - 倾斜因子 >= 1.5 → MEDIUM
  - 否则 → LOW

### 资源优化算法
- **CPU利用率优化**：
  - CPU > 85% → 增加并行度 50%
  - CPU < 30% → 减少并行度 30%
- **数据倾斜处理**：根据倾斜因子调整并行度
- **瓶颈检测**：耗时占比超过30%标记为瓶颈
- **目标利用率**：CPU 70%，内存 75%

### 成本估算模型
```
每小时成本 = (CPU核心数 × $0.05/小时) + (内存GB × $0.02/GB/小时)
```

## 配置说明

### Flink集群配置
```yaml
flink:
  rest:
    base-url: http://localhost:8081
    timeout: 30000
```

### 推荐参数配置
```yaml
recommendation:
  min-parallelism: 1
  max-parallelism: 128
  cost-per-cpu-per-hour: 0.05
  cost-per-gb-memory-per-hour: 0.02
```

## 主要功能页面

1. **Dashboard** - 作业概览和性能指标
2. **Job Analysis** - 详细的作业拓扑分析、瓶颈分析
3. **Recommendation** - 智能资源推荐
4. **Cost Estimator** - 成本估算器和成本计算器

## License

MIT License
