# Nginx 日志解析可视化工具

一个基于 Python + Flask + ECharts + GeoIP 的 Nginx 日志实时分析可视化工具。

## 功能特性

- 📊 **实时日志解析** - 增量读取 access.log 和 error.log，支持实时刷新
- 📈 **请求量统计** - 按小时统计请求量趋势，支持时间范围筛选
- 🎯 **响应码分布** - 可视化展示 HTTP 状态码分布情况
- 🐢 **慢接口分析** - 自动识别响应时间超过阈值的慢接口，支持路径聚合统计
- 🌍 **IP地理分布** - 基于 GeoIP 展示客户端 IP 地理分布地图，带智能缓存
- 🔍 **关键词搜索** - 支持按 IP、路径、User Agent 等关键词搜索
- 📱 **响应式设计** - 适配桌面和移动设备
- ⚡ **实时刷新** - 自动刷新数据，实时监控日志变化
- 👁️ **文件事件监听** - 基于 inotify/watchdog，文件变化才读取，高效低耗
- 🗂️ **URL路径聚合** - 自动忽略查询参数和动态路径段，聚合统计慢接口
- 💾 **GeoIP智能缓存** - 带TTL自动过期的GeoIP缓存，定期自动清理
- 🔔 **异常巡检告警** - 自动检测5xx错误突增、日志缺失、流量异常
- 📡 **Webhook推送** - 告警触发时自动推送到指定Webhook URL
- ⚙️ **告警规则配置** - 支持自定义告警阈值、检测窗口、严重程度
- ▶️ **日志回放** - 模拟指定时间段流量，重现故障场景
- ⏯️ **回放控制** - 支持播放/暂停/停止/变速，进度实时跟踪

## 技术栈

- **后端**: Python 3.8+ + Flask
- **前端**: HTML5 + CSS3 + JavaScript + ECharts 5.x
- **地理定位**: GeoIP2 (MaxMind)
- **User Agent 解析**: user-agents

## 项目结构

```
nginx-log-analyzer/
├── app.py                 # Flask 应用主程序 + API路由
├── config.py              # 配置文件
├── log_parser.py          # 日志解析引擎
├── alert_engine.py        # 异常巡检告警引擎
├── log_replay.py          # 日志回放引擎
├── requirements.txt       # Python 依赖包
├── start.bat              # Windows 启动脚本
├── start.sh               # Linux/Mac 启动脚本
├── templates/
│   └── index.html         # 前端页面（含告警管理、日志回放）
├── static/                # 静态资源目录
└── logs/
    ├── access.log         # Nginx 访问日志（示例）
    └── error.log          # Nginx 错误日志（示例）
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置日志路径

修改 `config.py` 中的日志路径配置：

```python
ACCESS_LOG_PATH = '/path/to/your/access.log'
ERROR_LOG_PATH = '/path/to/your/error.log'
```

或通过环境变量设置：

```bash
export ACCESS_LOG_PATH="/var/log/nginx/access.log"
export ERROR_LOG_PATH="/var/log/nginx/error.log"
```

### 3. 配置 GeoIP 数据库（可选）

下载 MaxMind GeoLite2-City 数据库：

1. 访问 https://dev.maxmind.com/geoip/geolite2-free-geolocation-data
2. 注册账号并下载 GeoLite2-City.mmdb
3. 将数据库文件放到项目根目录

或通过环境变量指定路径：

```bash
export GEOIP_DB_PATH="/path/to/GeoLite2-City.mmdb"
```

### 4. 启动应用

**Windows:**
```bash
start.bat
```

**Linux/Mac:**
```bash
chmod +x start.sh
./start.sh
```

或手动启动：
```bash
python app.py
```

### 5. 访问应用

打开浏览器访问 http://localhost:5000

## 功能说明

### 数据概览

- **总请求数**: 筛选范围内的总访问请求数
- **错误日志数**: 筛选范围内的错误日志条数
- **总流量**: 访问日志统计的总数据传输量
- **平均响应时间**: 请求的平均响应时间（秒）
- **错误率**: 4xx/5xx 状态码请求占比
- **独立IP数**: 不同客户端 IP 数量

### 图表说明

1. **请求量趋势图** - 按小时展示请求数、错误数和平均响应时间
2. **响应码分布图** - 饼图展示 2xx/3xx/4xx/5xx 状态码分布
3. **地理分布图** - 世界地图展示 IP 来源分布
4. **热门接口Top10** - 访问量最高的接口排名
5. **访问IP Top10** - 访问次数最多的 IP 排名
6. **错误级别分布** - error.log 中各错误级别的分布

### 筛选功能

- **时间范围**: 支持 1小时、6小时、24小时、7天、30天及自定义时间范围
- **关键词搜索**: 支持按 IP、请求路径、消息内容、User Agent 进行搜索

## Nginx 日志格式配置

工具支持标准的 Nginx combined 日志格式，建议在 nginx.conf 中配置：

```nginx
log_format combined '$remote_addr - $remote_user [$time_local] '
                    '"$request" $status $body_bytes_sent '
                    '"$http_referer" "$http_user_agent" '
                    '$request_time';

access_log /var/log/nginx/access.log combined;
```

其中 `$request_time` 用于统计响应时间，是可选字段。

## API 接口

| 接口 | 方法 | 说明 | 参数 |
|------|------|------|------|
| `/api/overview` | GET | 获取完整统计数据 | start_time, end_time, keyword |
| `/api/refresh` | GET | 刷新日志并返回统计 | - |
| `/api/access_logs` | GET | 分页获取访问日志 | page, per_page, start_time, end_time, keyword |
| `/api/error_logs` | GET | 分页获取错误日志 | page, per_page, start_time, end_time, keyword |
| `/api/hourly_stats` | GET | 获取小时统计数据 | start_time, end_time, keyword |
| `/api/status_distribution` | GET | 获取状态码分布 | start_time, end_time, keyword |
| `/api/slow_requests` | GET | 获取慢请求列表 | threshold, limit, start_time, end_time, keyword |
| `/api/geo_distribution` | GET | 获取地理分布数据 | start_time, end_time, keyword |
| `/api/top_paths` | GET | 获取热门接口 | limit, start_time, end_time, keyword |
| `/api/top_ips` | GET | 获取热门IP | limit, start_time, end_time, keyword |

## 配置说明

可通过环境变量或修改 `config.py` 进行配置：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `ACCESS_LOG_PATH` | `./logs/access.log` | 访问日志路径 |
| `ERROR_LOG_PATH` | `./logs/error.log` | 错误日志路径 |
| `GEOIP_DB_PATH` | `./GeoLite2-City.mmdb` | GeoIP 数据库路径 |
| `GEOIP_CACHE_TTL` | `3600` | GeoIP缓存过期时间（秒） |
| `GEOIP_CACHE_CLEANUP_INTERVAL` | `300` | GeoIP缓存清理间隔（秒） |
| `USE_FILE_WATCHER` | `true` | 是否启用文件事件监听 |
| `FILE_WATCHER_DEBOUNCE` | `0.5` | 文件监听防抖时间（秒） |
| `AGGREGATE_SLOW_REQUESTS` | `true` | 是否聚合慢接口路径 |
| `AGGREGATE_QUERY_PARAMS` | `true` | 是否忽略查询参数进行聚合 |
| `SLOW_REQUEST_THRESHOLD` | `1.0` | 慢请求阈值（秒） |
| `REFRESH_INTERVAL` | `5000` | 前端自动刷新间隔（毫秒） |
| `MAX_LOG_LINES` | `100000` | 最大缓存日志行数 |

### 新增功能说明

#### 1. GeoIP 智能缓存
- 内置带 TTL 的内存缓存，避免重复查询 GeoIP 数据库
- 自动检测 GeoIP 数据库文件更新，自动重新加载
- 后台线程定期清理过期缓存，控制内存使用
- 未命中缓存时自动查询并回填

#### 2. 文件事件监听
- 使用 `watchdog` 库监听日志文件变化
- 支持 Linux inotify、macOS kqueue、Windows ReadDirectoryChangesW
- 文件变化时才读取，比轮询更高效
- 内置防抖机制，避免频繁读取
- 自动降级：监听失败时自动回退到轮询模式

#### 3. URL 路径聚合
- 自动忽略 URL 查询参数（如 `?page=1&size=10`）
- 自动识别并替换动态路径参数（如 `/api/user/123` → `/api/user/{param}`）
- 预置数字、UUID、MongoDB ObjectID 等常见模式
- 支持自定义聚合规则（通过 `AGGREGATE_PATH_PATTERNS` 配置）
- 慢接口统计按聚合路径分组，展示调用次数、平均/最大/最小响应时间

## 注意事项

1. 确保日志文件有读取权限
2. 首次启动时会读取全部现有日志，大日志文件可能需要较长时间
3. GeoIP 功能需要下载对应的数据库文件，未提供时地理分布功能将显示为空
4. 生产环境建议使用 Gunicorn 或 uWSGI 部署

## 许可证

MIT License
