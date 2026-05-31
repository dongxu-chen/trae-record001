# 视频动作识别系统

基于深度学习的实时视频动作识别系统，支持视频流实时分析、动作时序定位和多类别同时识别。

## 技术栈

### 后端
- **Python 3.10+**
- **FastAPI** - Web框架和WebSocket服务
- **PyTorch 2.1+** - 深度学习框架
- **TimeSformer / VideoMAE** - 视频动作识别模型
- **OpenCV / FFmpeg** - 视频处理
- **pytorchvideo** - 视频模型库

### 前端
- **React 18** - UI框架
- **TypeScript** - 类型安全
- **Vite** - 构建工具
- **TailwindCSS 3** - 样式框架
- **Zustand** - 状态管理
- **Lucide React** - 图标库

## 功能特性

1. **实时视频流识别** - 支持摄像头实时采集和视频文件上传
2. **动作时序定位** - 精确标注动作的起始/结束时间点
3. **多类别同时识别** - 支持同一时间段内多个动作并行检测
4. **模型切换** - 支持TimeSformer和VideoMAE两种模型
5. **可视化面板** - 实时展示识别结果、动作时间轴、置信度热力图
6. **结果导出** - 支持JSON/CSV格式导出识别结果

## 支持的动作类别

| 类别 | 说明 |
|------|------|
| 跑步 | 快速移动 |
| 跳跃 | 双脚离地 |
| 挥手 | 手臂摆动 |
| 走路 | 正常行走 |
| 站立 | 静止站立 |
| 坐下 | 坐姿 |
| 蹲下 | 蹲姿 |
| 其他 | 未定义动作 |

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+
- FFmpeg (已安装并添加到PATH)
- CUDA 11.8+ (可选，用于GPU加速)

### 安装后端依赖

```bash
cd backend
pip install -r requirements.txt
```

### 安装前端依赖

```bash
cd frontend
npm install
```

### 启动后端服务

```bash
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 启动前端开发服务器

```bash
cd frontend
npm run dev
```

### 访问应用

打开浏览器访问: http://localhost:5173

## 项目结构

```
action-recognition-system/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI入口
│   │   ├── config.py          # 配置管理
│   │   └── schemas.py         # 数据模型
│   ├── services/
│   │   ├── video_capture.py   # 视频采集服务
│   │   ├── frame_processor.py # 帧处理服务
│   │   ├── inference.py       # 推理服务
│   │   ├── temporal_locator.py # 时序定位服务
│   │   └── websocket_manager.py # WebSocket管理
│   ├── models/
│   │   ├── base.py            # 模型基类
│   │   ├── timesformer.py     # TimeSformer实现
│   │   ├── videomae.py        # VideoMAE实现
│   │   └── model_loader.py    # 模型加载器
│   ├── utils/
│   │   ├── ffmpeg_utils.py    # FFmpeg工具
│   │   └── video_utils.py     # 视频处理工具
│   └── requirements.txt
└── frontend/
    ├── src/
    │   ├── components/
    │   │   ├── VideoPlayer.tsx
    │   │   ├── ResultPanel.tsx
    │   │   ├── Timeline.tsx
    │   │   └── ControlBar.tsx
    │   ├── hooks/
    │   │   └── useWebSocket.ts
    │   ├── store/
    │   │   └── appStore.ts
    │   ├── types/
    │   │   └── index.ts
    │   ├── pages/
    │   │   └── Home.tsx
    │   ├── App.tsx
    │   └── main.tsx
    └── package.json
```

## WebSocket协议

### 客户端消息

```json
{
  "type": "start",
  "source": "camera",
  "modelType": "timesformer",
  "fps": 16,
  "confidenceThreshold": 0.5
}
```

### 服务端消息

```json
{
  "type": "result",
  "timestamp": 1.234,
  "frameIndex": 30,
  "predictions": [
    {
      "action": "跑步",
      "confidence": 0.92
    }
  ],
  "fps": 15.5,
  "latency": 45.2
}
```

## 模型说明

### TimeSformer
- 论文: [Is Space-Time Attention All You Need for Video Understanding?](https://arxiv.org/abs/2102.05095)
- 特点: 时空分离注意力机制，适合实时视频理解
- 输入: 16帧 × 224×224
- 预训练: Kinetics-400

### VideoMAE
- 论文: [VideoMAE: Masked Autoencoders are Data-Efficient Learners for Self-Supervised Video Pre-Training](https://arxiv.org/abs/2203.12602)
- 特点: 掩码自编码器，小样本场景表现优异
- 输入: 16帧 × 224×224
- 预训练: Kinetics-400

## 核心算法

### 动作时序定位

1. 对每个动作类别构建置信度时间序列
2. 使用高斯滤波平滑置信度曲线
3. 双阈值法检测动作起始点和结束点
4. 合并间隔小于阈值的相邻同类别区间
5. 过滤持续时间过短或平均置信度过低的区间

### 实时推理优化

- FP16半精度推理
- 批量处理提高GPU利用率
- 动态跳帧保证实时性

## License

MIT
