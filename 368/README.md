# SSL证书过期监控工具

一个基于 Go + React 的 SSL 证书过期监控工具，支持批量管理域名、检查证书有效期、发送告警通知。

## 功能特性

- 域名批量管理（支持CSV导入、批量添加）
- SSL证书自动检查（有效期、签发机构、加密算法强度）
- **可控并发扫描**：可配置最大并发数，避免服务器压力
- **随机延时保护**：可配置扫描间隔和随机抖动，防止被封禁
- **算法规则库**：内置安全标准，支持定期更新、自定义规则
- **DNS MX记录扫描**：自动发现邮件服务器域名
- **子域名发现**：从DNS记录、证书SANs中发现子域名并自动监控
- **证书链完整性检查**：自动检测证书链是否完整，缺失中间证书时告警
- **证书透明度(CT)日志查询**：检测证书是否在CT日志备案，发现未备案证书
- **历史证书对比**：新老证书变更差异展示，识别签发机构、算法等重要变更
- 多级告警通知（钉钉/邮件/企业微信）
- 定时自动扫描（基于cron）
- 可视化仪表盘和报告
- 证书历史记录追踪

## 技术栈

### 后端
- Go 1.21+
- Gin (Web框架)
- GORM + SQLite (数据库)
- robfig/cron (定时任务)
- viper (配置管理)
- zap (日志)

### 前端
- React 18
- Ant Design 5
- Vite
- Axios

## 项目结构

```
.
├── backend/                    # Go 后端
│   ├── main.go                # 入口文件
│   ├── config/
│   │   └── config.go          # 配置管理
│   ├── models/
│   │   └── models.go          # 数据模型
│   ├── handlers/
│   │   └── handlers.go        # HTTP处理器
│   ├── services/
│   │   ├── ssl.go             # SSL证书检查服务
│   │   ├── alert.go           # 告警服务
│   │   ├── rule_library.go    # 算法规则库服务
│   │   ├── dns.go             # DNS扫描服务
│   │   └── cert_analysis.go   # 证书分析服务（证书链、CT日志、证书对比）
│   ├── cron/
│   │   └── cron.go            # 定时任务
│   ├── storage/
│   │   └── storage.go         # 数据库初始化
│   └── config.yaml            # 配置文件
├── frontend/                   # React 前端
│   ├── src/
│   │   ├── components/        # 组件
│   │   │   ├── Dashboard.jsx
│   │   │   ├── DomainList.jsx
│   │   │   ├── CertList.jsx
│   │   │   ├── AlertLogs.jsx
│   │   │   ├── Report.jsx
│   │   │   ├── SubdomainDiscovery.jsx
│   │   │   ├── RuleLibrary.jsx
│   │   │   └── ScanSettings.jsx
│   │   ├── services/
│   │   │   └── api.js         # API服务
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── index.css
│   ├── package.json
│   └── vite.config.js
└── README.md
```

## 快速开始

### 1. 启动后端服务

```bash
cd backend

# 安装依赖
go mod tidy

# 创建数据目录
mkdir -p data

# 启动服务
go run main.go
```

后端服务默认监听 `http://localhost:8080`

### 2. 启动前端

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端服务默认监听 `http://localhost:3000`

## 配置说明

编辑 `backend/config.yaml` 文件配置服务：

```yaml
server:
  port: 8080                    # 服务端口
  mode: release                 # 运行模式 (release/debug)

database:
  dsn: ./data/ssl_monitor.db   # SQLite数据库路径

cron:
  scan_interval: "0 */6 * * *"  # 扫描间隔（每6小时）
  check_expired_days: 30        # 过期预警天数
  warning_days: 7               # 严重预警天数

alert:
  dingtalk:                     # 钉钉告警
    enabled: false
    webhook: "https://oapi.dingtalk.com/robot/send?access_token=YOUR_TOKEN"
    secret: "YOUR_SECRET"

  email:                        # 邮件告警
    enabled: false
    host: smtp.example.com
    port: 465
    username: your_email@example.com
    password: your_password
    from: your_email@example.com
    to: admin@example.com

  wecom:                        # 企业微信告警
    enabled: false
    webhook: "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY"
```

## API接口

### 域名管理
- `GET /api/domains` - 获取域名列表
- `POST /api/domains` - 添加域名
- `PUT /api/domains/:id` - 更新域名
- `DELETE /api/domains/:id` - 删除域名
- `POST /api/domains/import` - CSV导入域名
- `POST /api/domains/batch` - 批量添加域名
- `POST /api/domains/:id/check` - 手动检查证书

### 证书信息
- `GET /api/certs` - 获取证书列表
- `GET /api/certs/:domain_id/history` - 获取证书历史

### 告警
- `GET /api/alerts` - 获取告警记录
- `POST /api/alerts/test` - 发送测试告警

### 报告
- `GET /api/report` - 获取统计报告
- `GET /api/report/export` - 导出CSV报告

## CSV导入格式

```csv
域名,端口,备注,标签
example.com,443,示例网站,生产
test.com,443,测试网站,测试
```

## 证书状态说明

- **正常 (valid)** - 证书有效期大于30天
- **即将过期 (warning)** - 证书剩余7-30天
- **严重 (critical)** - 证书剩余0-7天
- **已过期 (expired)** - 证书已过期
- **检查失败 (error)** - 无法连接或获取证书

## 构建生产版本

### 后端
```bash
cd backend
go build -o ssl-monitor main.go
```

### 前端
```bash
cd frontend
npm run build
```

## 许可证

MIT License
