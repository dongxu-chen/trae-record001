# 中文语音识别系统

基于 Wav2Vec2 的中文普通话语音识别系统，支持实时语音识别、VAD静音检测、自定义热词增强和WebSocket流式接口。

## 功能特性

- **Wav2Vec2预训练模型**: 使用中文预训练模型进行语音识别
- **VAD静音检测**: 基于WebRTC VAD的语音活动检测，自动切分语音片段
- **自定义热词增强**: 支持动态添加热词，提高特定词汇的识别率
- **实时语音识别**: 支持麦克风输入的实时语音识别
- **置信度输出**: 输出每个识别结果的置信度分数
- **WebSocket流式接口**: 提供实时流式API，支持部分和最终结果返回

## 环境要求

- Python 3.8+
- PyTorch 1.13+
- 推荐使用CUDA加速（可选）

## 安装依赖

```bash
pip install -r requirements.txt
```

**注意**: 
- 在Windows上安装PyAudio可能需要先安装Visual C++ Build Tools
- 或使用 `pip install pipwin` 然后 `pipwin install pyaudio`

## 快速开始

### 1. 麦克风实时识别

```bash
python main.py --mode mic --device cpu --hotwords "语音识别,人工智能"
```

### 2. WebSocket服务端模式

启动服务端:
```bash
python main.py --mode server --port 8765 --device cuda
```

运行客户端:
```bash
python client_example.py --server ws://localhost:8765 --hotwords "你好,再见"
```

### 3. 音频文件识别

```bash
python main.py --mode file --file audio.wav --device cpu
```

## 配置说明

### 环境变量

复制 `.env.example` 为 `.env` 并修改配置:

```env
DEVICE=cuda           # 运行设备: cpu 或 cuda
PORT=8765             # WebSocket端口
HOTWORDS=语音,识别    # 默认热词，用逗号分隔
```

### 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--mode` | 运行模式: server/mic/file | server |
| `--device` | 运行设备: cpu/cuda | cpu |
| `--port` | WebSocket端口 | 8765 |
| `--hotwords` | 自定义热词，逗号分隔 | 空 |
| `--model` | Wav2Vec2模型名称 | jonatasgrosman/wav2vec2-large-xlsr-53-chinese-zh-cn |
| `--file` | 音频文件路径（file模式） | 空 |

## WebSocket API

### 连接

```
ws://localhost:8765
```

### 发送消息

#### 1. 音频数据（二进制）
直接发送PCM16格式的音频数据，采样率16000Hz，单声道。

#### 2. 控制消息（JSON格式）

**设置热词:**
```json
{
  "type": "hotwords",
  "hotwords": ["热词1", "热词2", "热词3"]
}
```

**获取服务器信息:**
```json
{
  "type": "info"
}
```

### 接收消息

**部分结果（实时返回）:**
```json
{
  "type": "partial",
  "text": "识别中的文本",
  "confidence": 0.85,
  "duration": 2.5,
  "timestamp": 1234567890.123
}
```

**最终结果（语音结束后）:**
```json
{
  "type": "final",
  "text": "完整的识别文本",
  "confidence": 0.92,
  "duration": 3.2,
  "timestamp": 1234567895.456
}
```

**服务器信息:**
```json
{
  "type": "info",
  "model": "jonatasgrosman/wav2vec2-large-xlsr-53-chinese-zh-cn",
  "sample_rate": 16000,
  "hotwords": ["热词1", "热词2"],
  "connections": 1
}
```

## 项目结构

```
.
├── config.py           # 配置类定义
├── vad.py              # VAD静音检测模块
├── asr.py              # Wav2Vec2语音识别模型
├── audio_capture.py    # 麦克风音频采集
├── websocket_server.py # WebSocket服务端
├── main.py             # 主程序入口
├── client_example.py   # 客户端示例
├── requirements.txt    # 依赖列表
├── .env.example        # 环境变量示例
└── README.md           # 说明文档
```

## 模块说明

### VAD模块 (`vad.py`)
- 使用WebRTC VAD进行语音活动检测
- 支持3种检测模式（0-3，越大越严格）
- 自动进行语音分段，添加前后缓冲

### ASR模块 (`asr.py`)
- 加载Wav2Vec2预训练模型
- 支持热词logit增强
- 计算识别置信度
- 支持批量和流式处理

### WebSocket服务 (`websocket_server.py`)
- 异步处理多客户端连接
- 每个客户端独立VAD状态
- 支持热词动态更新
- 实时返回部分和最终结果

## 性能优化建议

1. **使用GPU**: 设置 `--device cuda` 可显著提升速度
2. **调整VAD参数**: 根据环境噪音调整VAD模式和阈值
3. **热词使用**: 合理使用热词可提高特定场景识别率
4. **内存优化**: 大模型建议使用batch推理或量化

## 常见问题

### 1. 模型下载慢
可以设置HuggingFace镜像:
```bash
export HF_ENDPOINT=https://hf-mirror.com
```

### 2. 麦克风没有声音
- 检查系统音频设置
- 使用 `--list-devices` 查看可用设备
- 确认麦克风权限已开启

### 3. 识别准确率低
- 确保音频采样率为16000Hz
- 尝试添加相关热词
- 检查录音质量，减少背景噪音

## 许可证

MIT License
