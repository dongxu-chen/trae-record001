# 在线考试防作弊系统

基于 WebRTC + Socket.io + React + Express 构建的全栈防作弊在线考试系统。

## ✨ 最新功能更新 (v2.0)

### 🔄 WebRTC 自动重连机制
- 自动检测连接断开，最多支持 5 次重连尝试
- 指数退避算法，重连间隔逐渐增加
- 支持 STUN/TURN 服务器配置（内置 Google STUN 和公共 TURN）
- 连接状态实时监控和显示

### 🛡️ 增强防作弊检测
- **Visibility API 切屏检测**: 监控页面可见性变化，检测最小化、切换标签等行为
- **全屏模式监控**: 检测考生是否退出全屏考试模式
- **窗口失焦检测**: 监控浏览器窗口是否失去焦点
- **虚拟机检测**: 通过 UserAgent、WebGL、CPU 核心数、屏幕分辨率等多维度检测虚拟机环境
- **防刷新/关闭**: 阻止考生意外刷新或关闭页面

### 🧑 FaceNet 人脸识别升级
- 升级使用 SSD Mobilenet 模型，更精准的人脸检测
- 可配置的相似度阈值（默认 0.6）
- 多人脸样本采集（最多 3 个样本），提高比对准确率
- 持续人脸验证，检测人脸离开或换人
- 实时相似度显示和验证状态

### 📊 监考端性能优化
- 懒加载视频流：只在点击"查看画面"后才建立 WebRTC 连接
- 连接状态实时显示：每个视频流都有独立的状态指示器
- 优化告警显示：分级显示危险/警告/信息告警，统计危险告警数量
- 卡片式布局：支持多列显示，自适应考生数量

---

## 📋 功能特性

### 1. 双摄像头监控
- 前置摄像头实时监控考生面部
- 屏幕共享实时监控考生操作
- 通过 WebRTC 实现低延迟视频传输
- 自动重连机制保证连接稳定性

### 2. 多重切屏检测
- Visibility API 页面可见性监控
- 浏览器窗口失焦检测
- 全屏模式退出检测
- 刷新/关闭页面阻止
- 检测到异常时立即触发告警并通知监考端

### 3. 虚拟机环境检测
- UserAgent 特征检测
- WebGL 渲染器特征分析
- CPU 核心数异常检测
- 屏幕分辨率特征分析
- 多维度综合判断，减少误报

### 4. 考生身份验证（FaceNet）
- 基于 face-api.js 的 FaceNet 人脸识别
- 考试开始时采集多个人脸样本
- 考试过程中持续进行人脸验证
- 可配置的相似度比对阈值
- 检测到人脸不匹配或人脸离开时触发告警

### 5. 监考端实时监控
- 实时查看所有在线考生列表
- 按需建立 WebRTC 连接，节省带宽
- 实时显示每个视频流的连接状态
- 实时接收所有作弊告警，按严重程度分级
- 支持多个考生同时监控
- 告警数量统计和历史记录

## 📁 项目结构

```
.
├── server/                 # 后端服务
│   ├── server.js          # Express + Socket.io 服务器
│   ├── package.json       # 后端依赖
│   └── .env               # 环境变量
├── client/                # 前端应用
│   ├── src/
│   │   ├── components/    # 可复用组件
│   │   │   ├── ExamineeCard.js    # 考生卡片（含懒加载）
│   │   │   └── VirtualScroll.js    # 虚拟滚动组件
│   │   ├── utils/         # 工具类
│   │   │   ├── webrtcManager.js    # WebRTC 管理器（考生端）
│   │   │   ├── proctorWebRTCManager.js  # WebRTC 管理器（监考端）
│   │   │   ├── antiCheatDetector.js    # 防作弊检测器
│   │   │   └── faceVerification.js     # 人脸识别验证器
│   │   ├── pages/         # 页面组件
│   │   │   ├── Home.js          # 首页/登录页
│   │   │   ├── ExamineePage.js  # 考生页面
│   │   │   └── ProctorPage.js   # 监考页面
│   │   ├── App.js         # 应用主组件
│   │   ├── App.css        # 样式文件
│   │   ├── index.js       # 入口文件
│   │   └── index.css      # 全局样式
│   ├── public/
│   │   ├── index.html     # HTML 模板
│   │   └── models/        # face-api.js 模型文件
│   └── package.json       # 前端依赖
└── README.md
```

## 🚀 安装和运行

### 前置要求
- Node.js >= 14.0.0
- npm 或 yarn
- 现代浏览器（Chrome/Firefox/Edge）

### 步骤1: 安装后端依赖

```bash
cd server
npm install
```

### 步骤2: 安装前端依赖

```bash
cd ../client
npm install
```

### 步骤3: 下载 face-api.js 模型

在 `client/public` 目录下创建 `models` 文件夹，并下载以下模型文件：

- **SSD Mobilenet 模型** (推荐，更准确):
  - ssd_mobilenetv1_model-weights_manifest.json
  - ssd_mobilenetv1_model-shard1
  - ssd_mobilenetv1_model-shard2

- **人脸关键点模型**:
  - face_landmark_68_model-weights_manifest.json
  - face_landmark_68_model-shard1

- **人脸识别模型 (FaceNet)**:
  - face_recognition_model-weights_manifest.json
  - face_recognition_model-shard1
  - face_recognition_model-shard2

可以从这里下载：https://github.com/justadudewhohacks/face-api.js/tree/master/weights

### 步骤4: 启动后端服务器

```bash
cd server
npm start
```

服务器将在 http://localhost:3001 启动

### 步骤5: 启动前端应用

```bash
cd client
npm start
```

前端应用将在 http://localhost:3000 启动

## 📖 使用说明

### 考生端使用流程
1. 访问首页，选择"我是考生"
2. 输入考试ID、用户ID、姓名
3. 进入考试页面，系统自动启动摄像头
4. 点击"开始屏幕共享"进行屏幕共享
5. 点击"采集人脸样本"3次，采集不同角度的人脸
6. 人脸采集完成后自动开始持续验证
7. 点击"进入全屏考试模式"开始正式考试
8. 考试过程中保持摄像头开启，系统自动监控

### 监考端使用流程
1. 访问首页，选择"我是监考"
2. 输入考试ID、用户ID、姓名
3. 进入监考页面，查看在线考生列表
4. 点击考生卡片上的"查看画面"按钮建立 WebRTC 连接
5. 查看考生的摄像头画面和屏幕共享画面
6. 实时接收作弊告警，按严重程度分级显示
7. 监控告警记录面板，查看详细的告警历史

## 🔧 技术栈

### 后端
- **Express**: Web 服务器框架
- **Socket.io**: 实时通信库
- **CORS**: 跨域资源共享

### 前端
- **React**: 用户界面框架
- **React Router**: 路由管理
- **Socket.io Client**: 实时通信客户端
- **face-api.js**: 人脸识别库（FaceNet 模型）
- **WebRTC**: 实时音视频通信
- **WebRTC Utils**: 自定义 WebRTC 连接管理

## 🔄 WebRTC 通信流程

1. 监考端点击"查看画面"，向服务器发送 Offer
2. 服务器将 Offer 转发给考生端
3. 考生端创建 Answer 并发送给服务器
4. 服务器将 Answer 转发给监考端
5. 双方交换 ICE 候选者
6. 建立 P2P 连接，传输视频流
7. 持续监控连接状态，断开时自动重连
8. 考生离开时自动关闭连接

## ⚙️ 可配置参数

### 人脸识别配置
- `similarityThreshold`: 人脸相似度阈值，默认 0.6，范围 0-1
- `verificationInterval`: 人脸验证间隔，默认 3000ms
- `minReferenceSamples`: 最少参考样本数，默认 3 个
- `maxReferenceSamples`: 最多参考样本数，默认 5 个

### WebRTC 配置
- `maxReconnectAttempts`: 最大重连次数，默认 5 次
- `reconnectDelay`: 初始重连延迟，默认 2000ms

### 防作弊配置
- `cooldownPeriod`: 告警冷却时间，默认 3000ms

## ⚠️ 注意事项

1. **HTTPS 要求**: 生产环境需要使用 HTTPS，因为摄像头和屏幕共享需要安全上下文
2. **网络环境**: WebRTC 在复杂网络环境下可能需要配置私有 TURN 服务器
3. **浏览器兼容性**: 建议使用 Chrome、Firefox、Edge 等现代浏览器
4. **模型文件**: 确保 face-api.js 的模型文件正确放置在 public/models 目录
5. **权限**: 首次使用需要授予摄像头和屏幕共享权限
6. **性能**: 同时监控大量考生时，建议使用高性能服务器或分布式部署

## 🔮 未来改进方向

- 添加音频监控和语音识别
- 实现考试题目展示和答题功能
- 添加作弊行为 AI 检测（多人检测、异常动作、手机检测等）
- 实现视频录像和回放功能
- 添加考试统计和分析报告
- 支持移动端响应式布局
- 集成第三方身份验证系统
- 添加白名单/黑名单功能
- 支持自定义告警规则配置
- 实现考试数据加密存储

## 🤝 贡献

欢迎提交 Issue 和 Pull Request 来改进这个项目！

## 📄 许可证

MIT License
