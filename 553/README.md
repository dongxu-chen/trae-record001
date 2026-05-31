# Elasticsearch 分片均衡工具

一个用于 Elasticsearch 集群分片自动均衡管理的工具，支持冷热分离、磁盘水位感知和迁移限速功能。

## 功能特性

- 📊 **集群监控**：实时监控集群健康状态、节点信息、分片分布
- ⚖️ **自动均衡**：智能算法分析分片分布，自动生成迁移计划
- 🔥 ❄️ **冷热分离**：支持基于节点属性的冷热数据分层管理
- 💾 **动态磁盘水位**：根据磁盘容量动态计算阈值，大容量节点阈值更高
- 📈 **节点IO历史评估**：持续监控节点CPU、负载、IO等待，迁移时避让高负载节点
- 🔥 **分片热度分析**：持续统计索引查询和写入频率，热分片优先均衡
- 🧪 **迁移演练**：模拟迁移效果，评估迁移后的分片分布和磁盘使用率
- 🚀 **自动扩容**：磁盘达到洪水水位时自动触发Webhook增加节点
- 🚀 **自适应迁移限速**：根据集群负载动态调整迁移速度，低负载加速，高负载减速
- 🎯 **可视化界面**：React 前端仪表盘，直观展示集群状态和负载数据

## 技术架构

### 后端
- **语言**：Go 1.21+
- **框架**：Gin Web 框架
- **ES 客户端**：go-elasticsearch/v8
- **定时任务**：cron
- **配置管理**：Viper
- **日志**：Zap

### 前端
- **框架**：React 18 + TypeScript
- **构建工具**：Vite
- **样式**：Tailwind CSS
- **状态管理**：TanStack Query (React Query)
- **图表**：Recharts
- **UI 组件**：Headless UI + Heroicons

## 项目结构

```
.
├── backend/                 # Go 后端
│   ├── cmd/
│   │   └── main.go         # 主程序入口
│   ├── config/
│   │   └── config.yaml     # 配置文件
│   ├── pkg/
│   │   ├── api/            # HTTP API 层
│   │   ├── balancer/       # 均衡算法
│   │   ├── config/         # 配置管理
│   │   └── elasticsearch/  # ES 客户端
│   └── go.mod
│
└── frontend/               # React 前端
    ├── src/
    │   ├── api/            # API 接口
    │   ├── components/     # 组件
    │   ├── hooks/          # 自定义 Hooks
    │   ├── pages/          # 页面
    │   ├── types/          # 类型定义
    │   └── utils/          # 工具函数
    └── package.json
```

## 快速开始

### 后端启动

1. **进入后端目录**
```bash
cd backend
```

2. **修改配置文件**
编辑 `config/config.yaml`，配置 Elasticsearch 连接信息：
```yaml
elasticsearch:
  url: "http://localhost:9200"
  username: "your_username"
  password: "your_password"
```

3. **安装依赖**
```bash
go mod download
```

4. **运行后端**
```bash
go run cmd/main.go
```

后端服务将在 `http://localhost:8080` 启动

### 前端启动

1. **进入前端目录**
```bash
cd frontend
```

2. **安装依赖**
```bash
npm install
```

3. **启动开发服务器**
```bash
npm run dev
```

前端服务将在 `http://localhost:3000` 启动

## 功能说明

### 1. 集群总览仪表盘
- 集群健康状态（绿色/黄色/红色）
- 节点数量、总分片数统计
- 实时迁移任务数
- 节点分片分布图表
- 磁盘使用率监控

### 2. 节点管理
- 节点列表展示（热节点/冷节点/普通节点）
- 每个节点的分片数量和索引列表
- 节点磁盘使用率详情
- 分片详情查看

### 3. 分片分布
- 分片矩阵可视化
- 按索引/节点搜索筛选
- 手动迁移分片功能
- 分片状态列表

### 4. 迁移任务
- 待执行迁移计划预览
- 迁移任务执行确认
- 实时迁移进度追踪
- 迁移历史记录

### 5. 系统设置
- **迁移速度限制**：10MB/s - 500MB/s 可配置
- **磁盘水位阈值**：
  - 低水位：停止分配新分片
  - 高水位：开始迁移分片
  - 洪水水位：索引设为只读
- **冷热分离**：配置节点属性识别热/冷节点
- **自动均衡**：定时任务自动执行均衡

## API 接口

### 集群相关
- `GET /api/cluster/health` - 获取集群健康状态
- `GET /api/cluster/nodes` - 获取节点列表
- `GET /api/cluster/shards` - 获取分片列表
- `GET /api/cluster/distribution` - 获取分片分布

### 均衡器相关
- `GET /api/balancer/plan` - 生成迁移计划
- `POST /api/balancer/execute` - 执行迁移
- `POST /api/balancer/move` - 手动迁移分片
- `GET /api/balancer/tasks` - 获取迁移任务

### 设置相关
- `GET /api/config` - 获取配置
- `POST /api/settings/speed-limit` - 设置迁移速度
- `POST /api/settings/disk-watermark` - 设置磁盘水位

## 均衡算法说明

### 均衡策略
1. **磁盘水位优先**：优先处理超过高水位的节点
2. **动态水位计算**：大容量节点阈值更高，充分利用磁盘空间
3. **冷热分离**：同类型节点间才允许迁移
4. **负载感知**：优先选择低负载节点作为迁移目标，避让高负载节点
5. **分片数均衡**：目标是让每个节点的分片数接近平均值
6. **阈值控制**：只有超过阈值（平均值的 10%）才触发迁移

### 动态水位计算规则
```
水位增加值 = min((实际容量 / 基准容量 - 1) * 2, 最大额外百分比)
动态水位 = 基础水位 + 水位增加值
```
- 例如：基准容量500GB，基础高水位90%，最大额外10%
- 500GB磁盘：高水位 = 90%
- 1TB磁盘：高水位 = 92%
- 2TB磁盘：高水位 = 96%
- 3TB+磁盘：高水位 = 100%（封顶97%）

### 节点负载评估
综合评分（0-1）：
- CPU使用率：30%权重
- 负载均值（1分钟）：40%权重
- IO等待百分比：30%权重

判定为高负载的条件（满足任一即可）：
- 综合评分 >= 高负载阈值（默认0.8）
- IO等待 >= IO等待阈值（默认50%）
- CPU使用率 >= CPU负载阈值*100（默认80%）

### 自适应限速规则
根据待处理任务数与目标值的比率调整：
- 比率 < 0.5：提速 20%
- 比率 > 2.0：减速 50%
- 比率 > 1.5：减速 20%
- 其他情况：保持当前速度

### 迁移限制
- 每次最多执行 5 个迁移任务（可配置）
- 有迁移任务进行中时，不启动新的均衡周期
- 副本分片不参与主动迁移
- 高负载节点不被选为迁移目标（当负载感知启用时）
- 热分片优先于普通分片进行迁移（当热度分析启用时）
- 自动扩容有冷却时间限制，避免频繁扩容

### 配置文件示例

完整的 `config/config.yaml` 配置：
```yaml
elasticsearch:
  url: "http://localhost:9200"
  username: ""
  password: ""
  timeout: 30

server:
  port: 8080
  mode: "release"

balancer:
  enabled: true
  schedule: "0 */5 * * * * *"
  max_migrations_per_cycle: 5
  migration_timeout: 300
  
  disk_watermark:
    low: 85
    high: 90
    flood: 95
    dynamic_enabled: true
    base_capacity_gb: 500
    max_extra_percent: 10
  
  speed_limit:
    max_bytes_per_sec: "100mb"
    min_bytes_per_sec: "10mb"
    adaptive_enabled: true
    target_pending_tasks: 5
    adjust_interval_sec: 60
  
  hot_cold:
    enabled: false
    hot_node_attr: "box_type"
    hot_node_value: "hot"
    cold_node_attr: "box_type"
    cold_node_value: "cold"
  
  load_awareness:
    enabled: true
    history_size: 10
    high_load_threshold: 0.8
    io_wait_threshold: 50
    cpu_load_threshold: 0.8
    avoid_high_load_nodes: true
  
  shard_heat:
    enabled: true
    history_size: 10
    query_weight: 0.6
    index_weight: 0.4
    heat_threshold: 0.7
    priority_boost: 1.5
    collect_interval_sec: 60
  
  auto_scaling:
    enabled: false
    flood_threshold: 95
    cooldown_minutes: 30
    min_nodes: 3
    max_nodes: 10
    provider: "webhook"
    node_type: "data_hot"
    disk_size_gb: 1000
    webhook_url: "http://localhost:9090/api/scale"

logging:
  level: "info"
  format: "json"
```

## 注意事项

1. **权限要求**：确保 Elasticsearch 用户具有以下权限：
   - cluster:monitor/*
   - cluster:admin/reroute
   - indices:admin/settings/*

2. **性能影响**：分片迁移会占用网络和磁盘 IO，建议在业务低峰期执行

3. **数据安全**：
   - 迁移前确保有足够的磁盘空间
   - 建议先在测试环境验证
   - 重要索引建议先做快照备份

## License

MIT License
