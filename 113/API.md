# 短链系统与埋点平台 API 文档 v3.0

## 前置要求
- Node.js >= 16
- Redis >= 6
- ClickHouse >= 22

## 安装依赖
```bash
npm install
```

## 启动服务
```bash
npm start
# 或开发模式
npm run dev
```

## 演示地址
- 热力图演示: `GET /demo`

## 核心功能

### v2.0 功能
1. **Snowflake 唯一短码生成**
   - 分布式唯一 ID，避免并发冲突
   - 64 进制转换为可读短码

2. **异步埋点 + 批量写入**
   - Redis List 消息队列
   - 每 3 秒批量消费 500 条记录

3. **ClickHouse 物化视图**
   - `stats_hourly`: 小时级预聚合
   - `stats_daily`: 天级预聚合

4. **TTL 自动过期**
   - 1 年未访问自动过期
   - 每小时自动清理

### v3.0 新增 - 热力图与 UVM 分析
1. **Canvas 设备指纹**
   - 基于 Canvas 渲染特征生成唯一指纹
   - 结合 UserAgent、语言、屏幕分辨率等多维度
   - 准确识别独立访客

2. **UV/MV 识别**
   - UV (Unique Visitor): 基于设备指纹去重
   - MV (Multiple Visits): 同指纹多次访问统计
   - 实时会话追踪

3. **实时点击热力图**
   - 前端 SDK 自动采集点击坐标
   - 记录点击元素、视口位置、滚动位置
   - 网格聚合统计热门点击区域

4. **热力图可视化**
   - Canvas 实时渲染热力图
   - SVG 矢量图导出支持
   - 可叠加页面截图（扩展）

## API 接口

### 一、短链接 API

#### 1. 长链接转短链接
**POST** `/api/shortlink/create`

请求体：
```json
{
  "longUrl": "https://www.example.com/very/long/url"
}
```

响应：
```json
{
  "shortCode": "123abcXYZ",
  "shortLink": "http://localhost:3000/123abcXYZ",
  "longUrl": "https://www.example.com/very/long/url",
  "ttl": "1 year from last access"
}
```

#### 2. 短链跳转
**GET** `/:shortCode`

- 302 重定向到原始长链接
- 异步记录访问埋点数据
- 自动更新最后访问时间（TTL 续期）

### 二、热力图与 UVM 分析 API

#### 1. 埋点数据上报
**POST** `/api/heatmap/track`

前端 SDK 自动调用，无需手动请求。

请求体：
```json
{
  "fingerprint": "abc123xyz",
  "sessionId": "sess_abc123",
  "pageInfo": {
    "url": "https://example.com/page",
    "path": "/page",
    "viewportWidth": 1920,
    "viewportHeight": 1080
  },
  "clicks": [
    {
      "x": 500,
      "y": 300,
      "absoluteX": 500,
      "absoluteY": 300,
      "scrollX": 0,
      "scrollY": 0,
      "target": "BUTTON",
      "id": "submit-btn",
      "className": "btn-primary",
      "timestamp": 1700000000000
    }
  ]
}
```

#### 2. 获取热力图数据
**GET** `/api/heatmap/data`

查询参数：
- `path` (可选): 页面路径，如 `/demo.html`
- `startDate` (可选): 开始时间
- `endDate` (可选): 结束时间
- `resolution` (可选): 精度 `high|medium|low`

响应：
```json
{
  "heatmap": [
    { "x": 500, "y": 300, "value": 45 },
    { "x": 520, "y": 320, "value": 23 }
  ],
  "uvm": {
    "uv": 156,
    "mv": 89,
    "totalClicks": 2345
  },
  "topTargets": [
    { "target": "BUTTON", "target_id": "btn1", "target_class": "", "click_count": 156 }
  ]
}
```

#### 3. UVM 统计详情
**GET** `/api/heatmap/uvm-stats`

查询参数：
- `path` (可选): 页面路径
- `startDate` (可选): 开始时间
- `endDate` (可选): 结束时间
- `granularity` (可选): 粒度 `hourly|daily|weekly`

响应：
```json
{
  "trend": [
    { "time": "2024-01-01 10:00:00", "uv": 45, "sessions": 67, "clicks": 234 }
  ],
  "topVisitors": [
    { "fingerprint": "abc123", "click_count": 156, "session_count": 5 }
  ],
  "deviceStats": [
    { "device": "Desktop", "uv": 120, "clicks": 1800 }
  ],
  "browserStats": [
    { "browser": "Chrome", "uv": 98, "clicks": 1500 }
  ]
}
```

#### 4. 生成热力图 SVG
**POST** `/api/heatmap/overlay`

请求体：
```json
{
  "path": "/demo.html",
  "width": 1920,
  "height": 1080,
  "startDate": "2024-01-01",
  "endDate": "2024-01-02"
}
```

响应：SVG 图片文件（可下载）

### 三、通用统计 API

**GET** `/api/stats`

查询参数：
- `shortCode` (可选): 短码
- `startDate` (可选): 开始时间
- `endDate` (可选): 结束时间

响应包含 PV、UV、地域分布、浏览器、操作系统、设备等统计。

## 数据字段说明

### 访问埋点
- `ip`: 访问 IP
- `user_agent`: 用户代理
- `referer`: 来源页面
- `country/region/city`: 地理位置
- `browser/os/device`: 设备信息
- `timestamp`: 访问时间

### 热力图点击
- `fingerprint`: 设备指纹
- `session_id`: 会话 ID
- `x/y`: 视口坐标
- `absolute_x/absolute_y`: 绝对坐标
- `scroll_x/scroll_y`: 滚动位置
- `target`: 点击元素标签
- `target_id/target_class`: 元素属性

### 访客会话
- `fingerprint`: 设备指纹（唯一标识）
- `session_id`: 会话 ID
- `first_seen/last_seen`: 首次/最后访问时间
- `visit_count`: 访问次数
- `page_views`: 页面浏览数
- `total_clicks`: 总点击数

## 前端 SDK 使用

```html
<!-- 自动加载并初始化 -->
<script src="/sdk/heatmap-sdk.js"></script>

<script>
  // 手动初始化（可选）
  const heatmap = new HeatmapSDK({
    trackUrl: '/api/heatmap/track',
    maxBatchSize: 50,
    flushInterval: 5000
  });
  
  // 获取当前指纹
  console.log(heatmap.getFingerprint());
  
  // 手动刷新队列
  heatmap.flush();
</script>
```

## 项目结构
```
├── app.js                 # 应用入口
├── config/
│   ├── redis.js           # Redis 配置
│   └── clickhouse.js      # ClickHouse 配置 + 物化视图
├── controllers/
│   ├── shortlinkController.js  # 短链控制器
│   ├── statsController.js      # 统计控制器
│   └── heatmapController.js    # 热力图控制器
├── middlewares/
│   └── analytics.js       # 分析中间件
├── routes/
│   ├── shortlink.js       # 短链路由
│   ├── stats.js           # 统计路由
│   └── heatmap.js         # 热力图路由
├── services/
│   ├── messageQueue.js    # Redis 消息队列
│   ├── batchConsumer.js   # 批量消费服务
│   └── ttlService.js      # TTL 管理服务
├── utils/
│   ├── Snowflake.js       # Snowflake ID 生成器
│   └── shortCode.js       # 短码工具
└── public/
    ├── sdk/
    │   └── heatmap-sdk.js # 前端 SDK
    └── demo.html          # 演示页面
```