# Clipboard Sync - Tauri 跨平台剪贴板同步工具

基于 Rust + Tauri 开发的跨平台剪贴板同步工具，支持 Windows、Mac、Linux 三端，提供 GUI 和 CLI 两种运行模式。

## ✨ 特性

### 🔐 安全加密
- **端到端加密**：使用 ECC (secp256r1) 密钥协商 + AES-GCM 加密传输
- **设备白名单**：仅与已信任设备同步，防止未授权访问
- **本地加密存储**：配置文件和历史记录本地安全存储

### 📋 剪贴板同步
- **文本同步**：支持纯文本、富文本跨设备复制粘贴
- **图片同步**：支持图片格式剪贴板内容同步
- **文件传输**：支持大文件分片传输（默认 1MB 分片）
- **传输确认**：接收端确认机制，30秒超时自动取消

### 🔍 历史记录管理
- **搜索功能**：按关键词、内容类型筛选历史
- **时间过滤**：支持按日期范围查询历史记录
- **本地持久化**：历史记录自动保存到本地文件系统

### 🔌 设备发现与配对
- **IP 范围扫描**：支持跨网段设备发现
- **二维码配对**：生成配对二维码，快速添加设备
- **设备信息展示**：实时显示设备名称、IP、端口、平台信息

### 🚀 性能优势 (vs Electron)
- **内存占用**：< 50MB (Electron 版本通常 > 200MB)
- **启动速度**：Rust 编译二进制，秒级启动
- **CPU 占用**：异步 runtime，低资源消耗

## 📁 项目结构

```
clipboard-sync/
├── src/
│   ├── main.rs              # Tauri GUI 主入口
│   ├── lib.rs               # 核心库，Tauri commands 定义
│   ├── models.rs            # 数据结构定义
│   ├── crypto.rs            # 加密模块 (ECC + AES-GCM)
│   ├── device.rs            # 设备管理 (白名单)
│   ├── transfer.rs          # 传输管理 (分片 + 确认)
│   ├── history.rs           # 历史记录管理
│   ├── discovery.rs         # 设备发现 (IP 扫描 + mDNS)
│   ├── server.rs            # HTTP 服务端
│   ├── clipboard.rs         # 系统剪贴板操作
│   ├── config.rs            # 配置管理
│   └── cli/
│       └── main.rs          # CLI 命令行入口
├── dist/
│   └── index.html           # 前端 UI 界面
├── Cargo.toml               # Rust 依赖配置
├── tauri.conf.json          # Tauri 配置
└── README.md                # 项目说明
```

## 🛠️ 技术栈

| 组件 | 技术选型 |
|------|---------|
| **GUI 框架** | Tauri 1.5 |
| **后端语言** | Rust 1.70+ |
| **加密算法** | ECC (secp256r1) + AES-256-GCM |
| **HTTP 服务** | Warp |
| **异步 Runtime** | Tokio |
| **设备发现** | local-ip-address + 端口扫描 |
| **剪贴板** | arboard |
| **二维码** | qrcode |
| **前端** | 原生 HTML/CSS/JS |

## 🚀 快速开始

### 前置要求

1. **Rust 工具链**
```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

2. **Tauri CLI**
```bash
cargo install tauri-cli
```

3. **系统依赖**
   - Windows: Visual Studio Build Tools
   - macOS: Xcode Command Line Tools
   - Linux: `sudo apt install libwebkit2gtk-4.0-dev build-essential`

### 开发运行

```bash
# GUI 版本
cargo tauri dev

# CLI 版本
cargo run --bin clipboard-sync-cli -- serve
```

### 构建发布

```bash
# GUI 应用
cargo tauri build

# CLI 二进制
cargo build --release --bin clipboard-sync-cli
```

## 📟 CLI 使用说明

```bash
# 启动后台服务
clipboard-sync-cli serve

# 列出发现的设备
clipboard-sync-cli devices

# 列出信任设备
clipboard-sync-cli whitelist

# 扫描 IP 范围发现设备
clipboard-sync-cli scan --start 192.168.1.1 --end 192.168.1.255

# 查看历史记录
clipboard-sync-cli history

# 搜索历史记录
clipboard-sync-cli search --keyword "hello" --type text

# 生成配对二维码
clipboard-sync-cli qrcode

# 发送剪贴板内容到设备
clipboard-sync-cli send --device-id <device-id> --text "Hello World"
clipboard-sync-cli send --device-id <device-id> --file /path/to/file
```

## 🔒 安全架构

### 密钥协商流程
```
设备 A                          设备 B
   |                              |
   |    1. 交换 ECC 公钥          |
   | ---------------------------> |
   |                              |
   |    2. 各自计算共享密钥        |
   |      ECDH(私钥, 对端公钥)    |
   |                              |
   |    3. SHA256 派生 AES 密钥   |
   |                              |
   |    4. AES-GCM 加密传输       |
   | <--------------------------> |
```

### 白名单验证
- 所有传输请求需验证设备是否在白名单中
- 未信任设备需要用户手动确认后才能传输
- 支持一键添加/移除信任设备

## 📊 性能指标

| 指标 | 目标值 | 说明 |
|------|-------|------|
| 内存占用 | < 50MB | 远低于 Electron |
| 启动时间 | < 2s | Rust 编译优化 |
| 传输速度 | > 100MB/s | 本地网络环境 |
| 单文件支持 | > 4GB | 分片传输机制 |
| 并发连接 | > 10 设备 | 异步 IO 处理 |

## 🔧 配置说明

配置文件位置：
- Windows: `%APPDATA%\clipboard-sync\config.json`
- macOS: `~/Library/Application Support/clipboard-sync/config.json`
- Linux: `~/.config/clipboard-sync/config.json`

默认配置：
```json
{
  "device_id": "自动生成的UUID",
  "device_name": "hostname-platform",
  "server_port": 38765,
  "chunk_size": 1048576,
  "confirm_timeout": 30,
  "max_retry": 3,
  "enable_encryption": true,
  "auto_accept_trusted": true,
  "history_limit": 200
}
```

## 🤝 贡献指南

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📝 开发计划

- [ ] 完整的 mDNS 自动发现实现
- [ ] P2P 打洞穿透，支持外网同步
- [ ] WebSocket 实时传输优化
- [ ] 更多剪贴板格式支持 (RTF, HTML 等)
- [ ] 传输进度条和速度显示
- [ ] 断点续传功能
- [ ] 端到端身份验证增强
- [ ] 移动端支持 (iOS/Android)

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

---

**注意**：本项目仍在活跃开发中，部分功能可能尚未完全实现，欢迎提交 Issue 和 PR 参与贡献！
