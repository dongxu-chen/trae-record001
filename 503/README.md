# Redis 慢查询分析工具

一个功能完整的Redis慢查询分析工具，用于分析Redis慢查询日志、识别热点Key和大Key，并提供优化建议。

## 功能特性

- 🔍 **慢查询日志分析**: 获取并解析Redis慢查询日志
- 📊 **命令模式分析**: 统计各类命令的执行次数、耗时分布
- 🔥 **热点Key识别**: 分析高频访问的Key
- 📦 **大Key扫描**: 发现占用内存较大的Key
- 💡 **优化建议**: 提供数据类型优化、分片建议
- 📈 **实时监控**: 实时监控Redis性能指标和新增慢查询

## 技术栈

### 后端
- Python 3.8+
- Flask - Web框架
- redis-py - Redis客户端
- flask-cors - 跨域支持

### 前端
- React 18+
- Ant Design - UI组件库
- Recharts - 图表库
- Axios - HTTP客户端

## 项目结构

```
redis-slowlog-analyzer/
├── backend/                 # 后端Flask应用
│   ├── app/
│   │   ├── __init__.py      # Flask应用初始化
│   │   ├── redis_client.py  # Redis客户端
│   │   ├── slowlog_analyzer.py  # 慢查询分析核心
│   │   ├── optimizer.py     # 优化建议生成
│   │   ├── monitor.py       # 实时监控模块
│   │   └── routes.py        # API路由
│   ├── run.py               # 应用入口
│   ├── requirements.txt     # Python依赖
│   └── .env.example         # 环境变量示例
└── frontend/                # 前端React应用
    ├── public/
    ├── src/
    │   ├── components/      # React组件
    │   │   ├── Overview.js       # 总览
    │   │   ├── SlowLogRanking.js # 慢查询排行
    │   │   ├── CommandAnalysis.js # 命令分析
    │   │   ├── HotKeys.js        # 热点Key
    │   │   ├── LargeKeys.js      # 大Key分析
    │   │   ├── Optimizations.js  # 优化建议
    │   │   └── RealTimeMonitor.js # 实时监控
    │   ├── api/
    │   │   └── api.js        # API调用封装
    │   ├── App.js           # 主应用组件
    │   ├── index.js         # 入口文件
    │   └── index.css        # 样式文件
    └── package.json         # Node依赖
```

## 快速开始

### 前置条件
- Redis Server 4.0+
- Python 3.8+
- Node.js 14+

### 1. 启动后端服务

```bash
cd backend

# 创建虚拟环境
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
copy .env.example .env
# 编辑.env文件，配置Redis连接信息

# 启动服务
python run.py
```

后端服务将在 http://localhost:5000 启动

### 2. 启动前端服务

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm start
```

前端服务将在 http://localhost:3000 启动

## API接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/health | 健康检查 |
| GET | /api/slowlogs | 获取慢查询日志 |
| GET | /api/slowlogs/config | 获取慢查询配置 |
| GET | /api/analysis/commands | 命令模式分析 |
| GET | /api/analysis/hotkeys | 热点Key分析 |
| GET | /api/analysis/largekeys | 大Key扫描 |
| GET | /api/analysis/ranking | 慢查询排行 |
| GET | /api/optimizations | 优化建议 |
| GET | /api/monitor/metrics | 实时指标 |
| GET | /api/full | 完整分析报告 |

## Redis慢查询配置

建议在Redis中配置以下参数：

```redis
# 设置慢查询阈值（微秒），10ms = 10000微秒
CONFIG SET slowlog-log-slower-than 10000

# 设置慢查询日志最大长度
CONFIG SET slowlog-max-len 1000
```

## 使用说明

1. **总览页面**: 查看Redis整体运行状态和关键指标
2. **慢查询排行**: 按耗时或频次排序查看慢查询
3. **命令分析**: 分析各类命令的执行统计
4. **热点Key**: 识别高频访问的Key
5. **大Key分析**: 扫描并分析大内存占用的Key
6. **优化建议**: 获取针对性的优化方案
7. **实时监控**: 实时监控Redis性能和新增慢查询

## 优化建议类型

### 命令优化
- KEYS命令 -> SCAN命令
- HGETALL -> HSCAN或HMGET
- SMEMBERS -> SSCAN
- 大LRANGE -> 分批获取

### 数据类型优化
- 大Hash -> Ziplist配置或分片
- 大List -> Stream或分片
- 大Set -> Hash或BitMap

### 分片建议
- 热点Key分片策略
- 大Key替代存储方案
- 读写分离建议

## 注意事项

1. 大Key扫描会遍历整个数据库，建议在低峰期执行
2. 慢查询日志长度有限，建议定期分析
3. 实时监控会持续轮询API，注意资源消耗
4. 生产环境使用时建议配置认证和访问控制
