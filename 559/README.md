# 直播带货数据实时分析面板

一个基于 Python + WebSocket + React + ECharts 的直播带货数据实时分析系统。

## 功能特性

- **实时数据展示**：观看人数、商品点击、订单量、转化率、热度趋势
- **主播话术建议**：基于实时数据分析提供智能话术建议
- **商品推荐切换**：根据热度自动推荐商品，支持一键切换
- **竞品监控**：实时监控竞品直播间的价格、观看人数、销量

## 技术栈

### 后端
- Python 3.8+
- Kafka (可选，用于生产环境)
- Redis (可选，用于生产环境)
- WebSocket (实时数据推送)

### 前端
- React 18
- TypeScript
- Vite
- ECharts (数据可视化)
- Ant Design (UI组件库)

## 项目结构

```
.
├── backend/                 # 后端代码
│   ├── demo_server.py      # 演示服务器（无需Kafka/Redis）
│   ├── kafka_producer.py   # Kafka数据生产者
│   ├── realtime_processor.py # 实时数据处理器
│   ├── websocket_server.py # WebSocket服务器
│   ├── config.py           # 配置文件
│   └── requirements.txt    # Python依赖
├── frontend/               # 前端代码
│   ├── src/
│   │   ├── components/     # React组件
│   │   ├── hooks/          # 自定义Hooks
│   │   ├── types/          # TypeScript类型定义
│   │   ├── App.tsx         # 主应用组件
│   │   └── main.tsx        # 入口文件
│   ├── package.json
│   └── vite.config.ts
└── README.md
```

## 快速开始

### 方式一：演示模式（推荐，无需额外依赖）

#### 1. 启动后端演示服务器

```bash
cd backend
pip install -r requirements.txt
python demo_server.py
```

演示服务器会在 `ws://localhost:8765` 启动，内置模拟数据生成器，无需Kafka和Redis。

#### 2. 启动前端

```bash
cd frontend
npm install
npm run dev
```

前端会在 `http://localhost:3000` 启动。

### 方式二：完整模式（需要Kafka和Redis）

#### 1. 启动依赖服务

确保已安装并启动：
- Kafka (默认端口: 9092)
- Redis (默认端口: 6379)

#### 2. 启动Kafka数据生产者

```bash
cd backend
python kafka_producer.py
```

#### 3. 启动WebSocket服务器

```bash
cd backend
python websocket_server.py
```

#### 4. 启动前端

```bash
cd frontend
npm install
npm run dev
```

## 功能说明

### 实时数据指标

1. **观看人数**：实时显示直播间在线人数及趋势
2. **商品点击**：累计商品点击次数
3. **订单量**：累计成功订单数量
4. **转化率**：订单数/点击数的百分比

### 数据可视化

- 观看人数趋势图
- 直播间热度趋势图
- 商品点击与订单对比柱状图
- 评论情感分析饼图

### 智能分析

1. **主播话术建议**
   - 转化率低时建议强调优惠
   - 负面评论多时建议回应用户
   - 热度下降时建议发起互动

2. **商品推荐**
   - 根据点击和订单数据计算推荐指数
   - 前三名商品自动推荐
   - 支持一键切换讲解商品

3. **竞品监控**
   - 实时显示竞品价格
   - 竞品观看人数
   - 竞品销量数据

## 配置说明

修改 `backend/config.py` 可以配置：

- Kafka连接地址
- WebSocket端口
- Redis连接信息
- 商品列表
- 竞品列表

## 注意事项

1. 演示模式使用内置的模拟数据生成器，适合快速预览
2. 生产环境建议使用完整的Kafka + Flink架构
3. 前端WebSocket连接地址默认为 `ws://localhost:8765`，如需修改请编辑 `frontend/src/hooks/useWebSocket.ts`

## License

MIT
