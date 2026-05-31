# ZooKeeper 节点数据量巡检工具

一个功能完整的ZooKeeper节点监控巡检工具，支持节点数据量统计、趋势预测和智能预警。

## 功能特性

### 核心功能
- 📊 **节点统计**: 监控Znode数量、数据大小、子节点深度
- 🚨 **智能预警**: 自动检测过大节点、过多子节点、过深路径
- 📈 **趋势预测**: 基于时序数据的线性回归预测，7天数据趋势分析
- 📁 **路径统计**: 按路径前缀聚合统计，支持多种排序方式
- 💡 **优化建议**: 基于最佳实践的智能优化建议

### 技术栈
- **后端**: Go + Gin + ZooKeeper API + 时序预测
- **前端**: React 18 + TypeScript + Ant Design + Recharts
- **部署**: Docker + Docker Compose

## 项目结构

```
.
├── backend/                 # Go 后端
│   ├── main.go             # 入口文件
│   ├── config/             # 配置模块
│   ├── internal/
│   │   ├── api/            # REST API 接口
│   │   ├── collector/      # ZooKeeper 数据采集器
│   │   ├── predictor/      # 时序预测模块
│   │   ├── storage/        # 内存存储
│   │   └── types/          # 公共类型定义
│   ├── .env                # 环境配置
│   ├── Dockerfile          # Docker 镜像构建
│   └── go.mod              # Go 依赖
├── frontend/               # React 前端
│   ├── src/
│   │   ├── pages/          # 页面组件
│   │   ├── services/       # API 服务
│   │   └── App.tsx         # 主应用
│   ├── package.json        # 前端依赖
│   └── vite.config.ts      # Vite 配置
└── docker-compose.yml      # 一键部署配置
```

## 快速开始

### 方式一：Docker Compose 部署（推荐）

```bash
# 启动所有服务
docker-compose up -d

# 访问前端: http://localhost:3000
# 访问API: http://localhost:8080
```

### 方式二：本地开发

#### 启动后端

```bash
cd backend

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，配置 ZooKeeper 服务器地址

# 安装依赖
go mod download

# 运行
go run main.go
```

#### 启动前端

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

## 配置说明

### 后端环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| ZK_SERVERS | ZooKeeper 服务器地址，逗号分隔 | localhost:2181 |
| PORT | API 服务端口 | 8080 |
| COLLECTION_INTERVAL | 数据采集间隔（秒） | 60 |
| PREDICTION_INTERVAL | 预测计算间隔（秒） | 300 |
| MAX_DEPTH | 最大遍历深度 | 10 |
| DATA_SIZE_THRESHOLD | 数据大小预警阈值（字节） | 1048576 (1MB) |
| NODE_COUNT_THRESHOLD | 节点数量预警阈值 | 1000 |

### 预警阈值配置

- **数据过大**: 单节点数据 > 1MB
- **子节点过多**: 单子节点数 > 500
- **路径过深**: 节点深度 > 15层

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/overview | 获取系统总览数据 |
| GET | /api/snapshot | 获取最新快照 |
| GET | /api/alerts | 获取预警列表 |
| GET | /api/paths/top | 获取Top路径统计 |
| GET | /api/timeseries/:metric | 获取时序数据 |
| GET | /api/predictions | 获取预测数据 |
| GET | /api/recommendations | 获取优化建议 |
| POST | /api/collect | 触发立即采集 |
| GET | /api/node/*path | 获取节点详情 |

## 前端页面

1. **总览**: 关键指标卡片 + 24小时趋势图
2. **路径统计**: 路径维度聚合分析 + 柱状图
3. **趋势预测**: 时序预测 + 7天预测值
4. **预警中心**: 分级预警列表 + 统计
5. **优化建议**: 智能建议 + 最佳实践

## 预警类型

| 类型 | 级别 | 说明 |
|------|------|------|
| large_data | warning | 节点数据过大 |
| many_children | warning | 子节点数量过多 |
| deep_path | info | 路径层级过深 |

## 算法说明

### 时序预测
使用线性回归算法对历史数据进行趋势预测：
- 输入：24小时历史数据点
- 输出：未来24小时预测值 + 7天预测值
- 指标：增长率、趋势方向

### 统计分析
- 按路径前缀聚合统计节点数量和数据量
- 计算平均节点大小、最大深度、临时节点占比

## 监控指标

- 总节点数 (total_nodes)
- 总数据量 (total_size)
- 最大路径深度 (max_depth)
- 预警数量 (alert_count)

## License

MIT
