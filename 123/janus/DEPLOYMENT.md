# Janus Gateway SFU 架构部署说明

## 系统架构

本系统采用基于 Janus Gateway 的 SFU (Selective Forwarding Unit) 架构，支持万人级同时在线考试监考。

### 核心组件

1. **Janus Gateway** - WebRTC 媒体服务器，提供 SFU 功能
2. **Coturn** - STUN/TURN 服务器，用于 NAT 穿透
3. **Nginx** - 提供管理界面和静态资源服务
4. **Node.js 服务端** - 业务逻辑和 API 服务
5. **React 客户端** - 考生端和监考端 Web 应用

## 部署步骤

### 1. 启动 Janus Gateway 服务

```bash
cd janus
docker-compose up -d
```

这将启动以下服务：
- Janus Gateway (端口: 8088 HTTP API, 8188 WebSocket)
- Coturn TURN 服务器 (端口: 3478)
- Nginx 管理界面 (端口: 8080)

### 2. 验证 Janus 服务状态

```bash
# 检查容器状态
docker-compose ps

# 查看 Janus 日志
docker-compose logs -f janus-gateway

# 测试 API 连接
curl http://localhost:8088/janus/info
```

### 3. 启动服务端

```bash
cd server
npm install
npm start
```

服务端将在 `http://localhost:3001` 启动。

### 4. 启动客户端

```bash
cd client
npm install
npm start
```

客户端将在 `http://localhost:3000` 启动。

## API 接口说明

### Janus 相关 API

#### 获取录制列表
```
GET /api/janus/recordings
```

#### 播放录制
```
GET /api/janus/recordings/:id/play
```

#### 下载录制
```
GET /api/janus/recordings/:id/download
```

#### 删除录制
```
DELETE /api/janus/recordings/:id
```

#### 获取 Janus 状态
```
GET /api/janus/status
```

#### 创建房间
```
POST /api/janus/room/create
Body: { roomId, description, secret, publishers }
```

#### 获取房间参与者列表
```
GET /api/janus/room/:roomId/list
```

## 配置说明

### Janus 配置文件

- `config/janus.jcfg` - Janus 核心配置
- `config/janus.plugin.videoroom.jcfg` - VideoRoom 插件配置

### 关键配置项

#### 支持万人并发

```
publishers = 10000
bitrate = 512000
```

#### 录制配置

```
record = true
rec_dir = "/usr/local/share/janus/recordings"
```

#### NAT 穿透配置

```
stun_server = "stun.l.google.com"
stun_port = 19302
full_trickle = true
```

## 性能优化建议

### 1. 资源限制调整

在 `docker-compose.yml` 中调整资源限制：

```yaml
janus-gateway:
  deploy:
    resources:
      limits:
        cpus: '4'
        memory: 8G
      reservations:
        cpus: '2'
        memory: 4G
```

### 2. 网络优化

- 使用 UDP 传输媒体流
- 启用 Jitter Buffer 优化
- 调整 RTP 端口范围

### 3. 负载均衡

对于大规模部署，建议：
- 使用多个 Janus Gateway 实例
- 使用负载均衡器分发流量
- 录制文件存储使用分布式文件系统

## 故障排查

### Janus 连接失败

1. 检查防火墙是否开放相关端口
2. 验证 Docker 容器是否正常运行
3. 查看 Janus 日志排查错误

### WebRTC 连接失败

1. 检查 STUN/TURN 服务器配置
2. 验证 ICE 候选收集
3. 检查网络连接质量

### 录制文件无法播放

1. 检查录制目录权限
2. 验证 janus-pp-rec 工具是否可用
3. 尝试手动转换 MJR 文件

## 监控和日志

### 查看 Janus 日志

```bash
docker-compose logs -f janus-gateway
```

### 查看 Coturn 日志

```bash
docker-compose logs -f coturn
```

### 录制文件位置

- Docker 容器内: `/usr/local/share/janus/recordings`
- 宿主机挂载: `./janus/recordings`

## 安全建议

1. 修改默认的 API secret 和房间 secret
2. 配置 HTTPS 加密
3. 限制 API 访问来源
4. 定期更新 Janus 和依赖组件

## 扩展功能

1. 集成 AI 行为分析
2. 添加人脸识别验证
3. 实现云端录制存储
4. 开发移动端监考应用
