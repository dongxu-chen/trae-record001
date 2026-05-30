# 服务依赖限流配置推荐工具

基于排队论的智能限流配置推荐系统，提供服务级和接口级的限流阈值推荐、过载保护模拟和限流水位可视化。

## ✨ 新增增强功能 (V2.0)

### 🔥 上下游协同限流
- **智能联动保护**: 下游服务达到水位阈值时，自动触发上游服务降额
- **依赖链分析**: 自动识别并通知所有依赖的上游服务
- **梯度降额**: 根据依赖权重计算不同上游的降额比例
- **自动恢复**: 压力缓解后自动解除限流限制

### 🌊 多峰流量模型
- **周期性峰值**: 早高峰、午高峰、晚高峰、夜间低峰
- **突发流量模拟**: 秒杀活动、营销推送、随机尖峰
- **真实波形**: 高斯分布 + 震荡波动 + 渐变缓升缓降
- **可配置参数**: 强度、持续时间、触发时机

### ⚡ WebSocket实时推送
- **毫秒级更新**: 100ms间隔水位数据推送
- **实时协同事件**: 协同限流触发/解除即时通知
- **多主题订阅**: 水位、协同事件、告警分开发送
- **自动重连**: 断线自动重连机制

## 功能特性

### 核心功能
- **服务拓扑分析** - 基于调用关系分析和依赖链分析
- **排队论计算引擎** - M/M/c模型计算最优限流阈值
- **时间序列预测** - ARIMA模型流量预测
- **过载保护模拟** - 对比有限流/无限流的系统表现
- **限流水位可视化** - 实时监控各服务限流水位
- **一键应用配置** - 推荐配置一键生效

### 技术栈
**后端**:
- Java 11 + Spring Boot 2.7
- Spring WebSocket + STOMP 协议
- Apache Commons Math3 (排队论计算)
- Springfox Swagger (API文档)

**前端**:
- React 18 + Ant Design 4
- Recharts (图表可视化)
- @stomp/stompjs + sockjs-client (WebSocket)
- React Router (路由)

## 项目结构

```
.
├── backend/                    # Java后端
│   ├── src/main/java/com/ratelimit/recommender
│   │   ├── controller/         # REST API控制器
│   │   │   ├── RealtimeDataController.java    # 新增: 实时数据API
│   │   │   └── ...
│   │   ├── service/            # 业务服务
│   │   │   ├── CoordinatedRateLimitService.java # 新增: 协同限流
│   │   │   ├── MultiPeakTrafficGenerator.java  # 新增: 多峰流量
│   │   │   ├── RealtimeDataPushService.java    # 新增: WebSocket推送
│   │   │   └── ...
│   │   ├── model/              # 数据模型
│   │   │   ├── CoordinatedRateLimit.java       # 新增: 协同限流模型
│   │   │   ├── MultiPeakTrafficPattern.java    # 新增: 多峰流量模型
│   │   │   ├── WaterLevelUpdate.java           # 新增: 水位更新模型
│   │   │   └── ...
│   │   ├── config/             # 配置类
│   │   │   ├── WebSocketConfig.java            # 新增: WebSocket配置
│   │   │   └── ...
│   │   └── RateLimitRecommenderApplication.java
│   └── pom.xml
│   └── src/main/resources
│       └── application.yml
└── frontend/                   # React前端
    ├── src/
    │   ├── hooks/              # 新增: React Hooks
    │   │   └── useWebSocket.js
    │   ├── pages/              # 页面组件
    │   │   ├── RealtimeWaterLevel.js          # 新增: 实时水位监控
    │   │   └── ...
    │   ├── services/           # API服务
    │   ├── App.js
    │   └── index.js
    │   └── index.css
    └── package.json
    └── public/
```

## 快速开始

### 后端启动

```bash
cd backend
mvn clean package
java -jar target/rate-limit-recommender-1.0.0.jar
```

或者使用Maven直接运行:

```bash
cd backend
mvn spring-boot:run
```

后端服务将在 http://localhost:8080/api 启动

### 前端启动

```bash
cd frontend
npm install
npm start
```

前端服务将在 http://localhost:3000 启动

## API接口

### 实时数据 (新增)
- `GET /api/realtime/status` - 获取当前状态
- `GET /api/realtime/water-levels` - 获取当前水位
- `GET /api/realtime/coordinations` - 获取活跃协同限流
- `POST /api/realtime/coordination/trigger/{serviceId}` - 触发协同限流
- `POST /api/realtime/coordination/release/{coordinationId}` - 解除协同限流
- `GET /api/realtime/coordination/{coordinationId}/impact` - 获取协同影响
- `GET /api/realtime/traffic-pattern/{serviceId}` - 获取流量模式
- `GET /api/realtime/traffic-series/{serviceId}` - 获取多峰流量时间序列
- `POST /api/realtime/traffic-burst/{serviceId}` - 触发突发流量

### WebSocket 端点
- `ws://localhost:8080/api/ws` - WebSocket连接端点
- `/topic/water-levels` - 水位更新主题
- `/topic/coordination-events` - 协同事件主题
- `/topic/alerts` - 告警主题

### 拓扑分析
- `GET /api/topology` - 获取服务拓扑
- `GET /api/topology/services` - 获取服务列表
- `GET /api/topology/services/{serviceId}` - 获取服务详情
- `GET /api/topology/bottlenecks` - 获取瓶颈服务

### 限流推荐
- `GET /api/ratelimit/recommend/{serviceId}` - 获取服务限流推荐
- `GET /api/ratelimit/recommend/all` - 获取所有服务推荐
- `POST /api/ratelimit/apply` - 应用推荐配置

### 配置管理
- `GET /api/ratelimit/config/{serviceId}` - 获取配置
- `GET /api/ratelimit/configs` - 获取所有配置
- `PUT /api/ratelimit/config/{serviceId}` - 更新配置
- `DELETE /api/ratelimit/config/{serviceId}` - 删除配置
- `POST /api/ratelimit/config/{serviceId}/toggle` - 开关配置
- `GET /api/ratelimit/config/{serviceId}/export` - 导出配置

### 流量预测
- `GET /api/prediction/traffic/{serviceId}` - 获取流量预测

### 过载模拟
- `POST /api/simulation/overload/{serviceId}` - 运行过载模拟(无限流)
- `POST /api/simulation/overload/{serviceId}/protected` - 运行过载模拟(有限流)
- `POST /api/simulation/overload/{serviceId}/compare` - 对比模拟

## 算法原理

### 排队论 M/M/c 模型

基于排队论计算系统参数:
- λ: 到达率 (请求/秒)
- μ: 服务率 (请求/秒)
- c: 服务实例数

计算指标:
- 系统利用率 ρ = λ/(c*μ)
- 平均排队时间 Wq
- 平均系统时间 W
- 平均队列长度 Lq

### 上下游协同算法

1. **水位检测**: 实时监控各服务水位
2. **触发判断**: 水位 ≥ 90% 触发协同
3. **依赖发现**: 向上递归查找所有上游服务
4. **权重计算**: 根据调用关系计算依赖权重
5. **梯度降额**: 权重越高，降额比例越大
6. **阈值调整**: 动态调整各上游限流阈值

### 多峰流量模型

```
QPS(t) = baseline * (1 + Σ(peak_i(t)) + Σ(burst_j(t))) * (1 + noise)
```

- **周期性峰值**: 高斯分布模拟早晚高峰
- **突发流量**: 梯形包络 + 正弦震荡
- **随机噪声**: 正态分布模拟真实波动

## 使用说明

1. **实时监控** - 进入"实时监控"页面查看100ms级水位更新
2. **触发突发** - 点击"触发突发流量"模拟真实业务峰值
3. **协同限流** - 观察下游高水位时上游自动降额的联动效果
4. **服务拓扑** - 查看服务调用关系和依赖链
5. **限流推荐** - 查看基于排队论的智能推荐配置
6. **过载模拟** - 对比有限流/无限流的系统表现

## 许可证

MIT License
