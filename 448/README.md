# 数据库连接池优化工具

基于排队论和业务负载模拟的数据库连接池参数优化系统，支持 HikariCP、Druid、Tomcat JDBC 多种连接池。

## 功能特性

- **多种连接池支持**：HikariCP、Druid、Tomcat JDBC
- **排队论分析**：基于 Erlang C 模型计算等待概率、队列长度等指标
- **业务负载模拟**：泊松到达 + 高斯服务时间分布的离散事件模拟
- **智能优化算法**：自动推荐最佳连接池参数
- **可视化分析**：等待时间分布、利用率趋势图表
- **对比分析**：优化前后配置对比，量化改进效果

## 技术栈

### 后端
- Java 17 + Spring Boot 3.2
- Apache Commons Math3 (排队论计算)
- HikariCP, Druid 连接池库

### 前端
- React 18 + Material UI
- Recharts 图表库
- Axios HTTP 客户端

## 项目结构

```
├── src/
│   └── main/
│       ├── java/com/dbpool/optimizer/
│       │   ├── core/                    # 核心算法模块
│       │   │   ├── QueueingTheoryAnalyzer.java   # 排队论分析
│       │   │   ├── ConnectionPoolSimulator.java  # 连接池模拟器
│       │   │   └── PoolOptimizer.java            # 优化算法
│       │   ├── model/                   # 数据模型
│       │   ├── parser/                  # 配置解析器
│       │   │   ├── HikariCPConfigParser.java
│       │   │   ├── DruidConfigParser.java
│       │   │   └── TomcatJDBCConfigParser.java
│       │   └── controller/              # REST API
│       └── resources/
├── frontend/                            # React 前端应用
└── pom.xml
```

## 核心算法

### 排队论 (M/M/c 模型)

- **Erlang C 公式**：计算请求需要等待的概率
- **平均等待时间**：Wq = (ErlangC * 1000) / (c*μ - λ)
- **平均队列长度**：Lq = λ * Wq / 1000

### 优化目标函数

```
minimize: (等待时间权重 * 等待时间) + (资源成本权重 * 连接数)
subject to:
  - 利用率 ≤ 最大允许利用率
  - 等待时间 ≤ 目标等待时间
  - 连接数 ∈ [5, 100]
```

## 快速开始

### 环境要求

- JDK 17+
- Node.js 16+
- Maven 3.6+

### 启动后端

```bash
# 编译项目
mvn clean package

# 运行应用
mvn spring-boot:run
```

后端服务启动在 http://localhost:8080

### 启动前端

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm start
```

前端应用启动在 http://localhost:3000

## API 接口

### 模拟连接池性能
```http
POST /api/pool-optimizer/simulate
Content-Type: application/json

{
  "config": {
    "poolType": "HIKARICP",
    "maxPoolSize": 10,
    "minIdle": 5,
    "connectionTimeoutMs": 30000
  },
  "workload": {
    "arrivalRate": 50.0,
    "avgServiceTimeMs": 100.0,
    "peakConcurrentUsers": 100
  }
}
```

### 优化连接池配置
```http
POST /api/pool-optimizer/optimize
Content-Type: application/json

{
  "currentConfig": {...},
  "workload": {...},
  "targetWaitTimeMs": 50,
  "maxAllowedUtilization": 0.8
}
```

### 获取默认配置
```http
GET /api/pool-optimizer/default-config/HIKARICP
GET /api/pool-optimizer/default-workload
```

## 配置参数说明

### 连接池配置

| 参数 | 说明 | HikariCP | Druid | Tomcat JDBC |
|------|------|----------|-------|-------------|
| maxPoolSize | 最大连接数 | maximumPoolSize | maxActive | maxActive |
| minIdle | 最小空闲连接 | minimumIdle | minIdle | minIdle |
| connectionTimeoutMs | 连接超时 | connectionTimeout | maxWait | maxWait |
| idleTimeoutMs | 空闲超时 | idleTimeout | minEvictableIdleTimeMillis | minEvictableIdleTimeMillis |
| maxLifetimeMs | 连接最大生命周期 | maxLifetime | maxEvictableIdleTimeMillis | maxAge |
| leakDetectionThresholdMs | 泄漏检测阈值 | leakDetectionThreshold | removeAbandonedTimeout | suspectTimeout |

### 业务负载配置

| 参数 | 说明 | 建议值 |
|------|------|--------|
| arrivalRate | 请求到达率 (req/s) | 根据实际业务 |
| avgServiceTimeMs | 平均服务时间 (ms) | 50-500 |
| serviceTimeStdDevMs | 服务时间标准差 (ms) | 10-100 |
| peakConcurrentUsers | 峰值并发用户数 | 根据实际业务 |
| simulationDurationMs | 模拟时长 (ms) | 5000-30000 |
| varianceFactor | 方差因子 | 0.3-1.0 |

## 使用建议

1. **开始前**：收集真实业务的数据库访问性能数据
2. **模拟验证**：先用模拟功能验证当前配置的性能表现
3. **优化建议**：使用智能优化获取推荐配置
4. **对比分析**：查看优化前后的对比数据
5. **灰度发布**：在测试环境验证后逐步推广到生产

## License

MIT License
