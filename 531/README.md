# SLA 监控平台

服务等级协议（SLA）监控平台，基于 Java + Prometheus + React 技术栈实现。

## 功能特性

- **SLA 指标监控**：实时监控各服务的可用性、延迟、错误率
- **滑动窗口计算**：基于滑动窗口实时计算 SLA 指标
- **SLA 达成率统计**：综合计算各项指标的 SLA 达成率
- **时序预测**：基于线性回归预测 SLA 未来趋势
- **多服务对比**：雷达图、柱状图多维度对比服务性能
- **SLA 违规预警**：实时告警机制，支持预测性告警
- **根因分析**：自动分析 SLA 违规的根本原因，提供优化建议

## 技术栈

### 后端
- Java 17
- Spring Boot 3.2
- Micrometer + Prometheus
- Apache Commons Math3 (时序预测)
- H2 Database (内存数据库)
- Lombok

### 前端
- React 18
- Material UI (MUI)
- Recharts (图表库)
- React Router
- Axios
- Vite

### DevOps
- Docker & Docker Compose
- Prometheus
- Grafana

## 快速开始

### 方式一：Docker Compose 启动

```bash
# 克隆项目后，在根目录执行
docker-compose up -d

# 访问前端: http://localhost:3000
# 访问后端API: http://localhost:8080
# Prometheus: http://localhost:9090
# Grafana: http://localhost:3001 (admin/admin)
```

### 方式二：本地开发启动

#### 启动后端
```bash
cd backend
mvn spring-boot:run
```

#### 启动前端
```bash
cd frontend
npm install
npm run dev
```

## API 接口

### 服务管理
- `GET /api/services` - 获取所有服务
- `GET /api/services/active` - 获取活跃服务
- `GET /api/services/{name}` - 获取指定服务
- `POST /api/services` - 创建服务
- `PUT /api/services/{name}` - 更新服务
- `DELETE /api/services/{name}` - 删除服务

### 指标查询
- `GET /api/metrics/{serviceName}/latest` - 获取最新指标
- `GET /api/metrics/{serviceName}/history` - 获取历史指标
- `GET /api/metrics/compare` - 多服务对比
- `GET /api/metrics/{serviceName}/prediction` - 获取预测数据
- `GET /api/metrics/{serviceName}/root-cause` - 根因分析

### 告警管理
- `GET /api/alerts` - 获取告警列表
- `GET /api/alerts/active` - 获取活跃告警
- `POST /api/alerts/{id}/acknowledge` - 确认告警
- `POST /api/alerts/{id}/resolve` - 解决告警

### 数据模拟
- `POST /api/metrics/{serviceName}/simulate` - 生成模拟请求
- `POST /api/metrics/simulate-all` - 生成所有服务历史数据

## 核心算法

### SLA 达成率计算
```
SLA达成率 = 可用性评分 * 0.5 + 延迟评分 * 0.3 + 错误率评分 * 0.2
```

### 滑动窗口
- 默认窗口大小：60分钟
- 更新间隔：10秒
- 自动清理过期数据

### 时序预测
- 基于线性回归模型
- 使用过去24小时数据预测未来2小时
- 自动检测趋势方向（改善/下降/稳定）

## 项目结构

```
.
├── backend/                 # Java 后端
│   ├── src/
│   │   ├── main/
│   │   │   ├── java/com/sla/monitor/
│   │   │   │   ├── engine/      # 核心引擎（滑动窗口、Prometheus）
│   │   │   │   ├── service/     # 业务服务（计算、预测、告警）
│   │   │   │   ├── controller/  # REST API
│   │   │   │   ├── model/       # 数据模型
│   │   │   │   ├── dto/         # 数据传输对象
│   │   │   │   ├── repository/  # 数据访问层
│   │   │   │   └── config/      # 配置类
│   │   │   └── resources/
│   ├── pom.xml
│   └── Dockerfile
├── frontend/               # React 前端
│   ├── src/
│   │   ├── components/     # React 组件
│   │   ├── services/       # API 服务
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── package.json
│   ├── vite.config.js
│   └── Dockerfile
├── prometheus/             # Prometheus 配置
├── docker-compose.yml
└── README.md
```

## 默认服务

系统启动时自动创建以下示例服务：

| 服务名称 | 可用性目标 | 延迟目标 | 错误率目标 |
|---------|-----------|---------|-----------|
| user-service | 99.9% | 300ms | 1.0% |
| order-service | 99.5% | 500ms | 2.0% |
| payment-service | 99.99% | 800ms | 0.5% |
| inventory-service | 99.0% | 400ms | 3.0% |

## Screenshots

### 仪表板
- 服务概览卡片
- 实时 SLA 达成率
- 告警统计

### 服务详情
- 指标趋势图表
- SLA 预测曲线
- 根因分析报告

### 服务对比
- 雷达图对比
- 柱状图对比
- 详细对比表

## License

MIT
