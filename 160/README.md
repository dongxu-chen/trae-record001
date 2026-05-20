# EEG Processing Toolbox v2.0

基于 **BrainFlow** 的脑电信号实时处理工具箱，支持多种采集设备，集成LSL数据传输协议，并提供REST API接口。

## 架构概览

```
┌─────────────────────────────────────────────────────────┐
│                     PyQt5 GUI 界面                      │
├─────────────────────────────────────────────────────────┤
│  设备控制  |  LSL输出   |  实时波形   |  频段功率 | API │
└─────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  brainflow_acq  │  │signal_processing│  │  lsl_integration│
│   (采集层)      │  │    (处理层)     │  │    (传输层)     │
└─────────────────┘  └─────────────────┘  └─────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────┐
│                    FastAPI REST API                     │
└─────────────────────────────────────────────────────────┘
```

## 核心模块

### 1. 数据采集层 - `brainflow_acquisition.py`
基于BrainFlow的设备抽象层，支持多种EEG采集设备：

| 设备类型 | 说明 | 通道数 | 采样率 |
|---------|------|--------|--------|
| OpenBCI Cyton | 8通道脑电帽 | 8 | 250 Hz |
| OpenBCI Ganglion | 4通道便携设备 | 4 | 200 Hz |
| NeuroSky MindWave | 单通道意念耳机 | 1 | 512 Hz |
| Muse | 消费级头环 | 4 | 256 Hz |
| Synthetic Board | 模拟测试设备 | 16 | 250 Hz |

**核心功能：**
- 统一的设备连接/断开接口
- 实时数据流回调机制
- 线程安全的数据缓冲区
- 设备参数自动配置

### 2. 信号处理层 - `signal_processing.py`
实时EEG信号处理流水线：

| 处理模块 | 功能 |
|---------|------|
| EEGFilter | 带通滤波 + 50Hz陷波 |
| BandPowerExtractor | 5频段功率计算 (δ/θ/α/β/γ) |
| RealtimePipeline | 完整处理管线 + 回调系统 |

**处理流程：**
```
原始数据 → 单位转换(µV) → 带通滤波(1-50Hz) → 陷波滤波
                                                  ↓
                                        频段功率提取 → 回调分发
```

### 3. LSL传输层 - `lsl_integration.py`
Lab Streaming Layer协议集成，支持输入和输出：

- **LSL输入**：接收外部LSL流，支持多设备同步
- **LSL输出**：
  - 原始/滤波后EEG数据流
  - 频段功率数据流（10Hz更新）
- 自动流发现和连接管理
- 线程安全的数据推送

### 4. REST API层 - `rest_api.py`
基于FastAPI的HTTP接口，支持远程控制和数据查询：

| 端点 | 方法 | 功能 |
|-----|------|------|
| `/devices` | GET | 获取支持设备列表 |
| `/connect` | POST | 连接指定设备 |
| `/start_stream` | POST | 启动数据采集 |
| `/stop_stream` | POST | 停止数据采集 |
| `/data/latest` | GET | 获取最新EEG数据 |
| `/bandpower` | GET | 获取当前频段功率 |
| `/lsl/start` | POST | 启动LSL输出流 |
| `/status` | GET | 获取系统状态 |

**自动文档：**
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 5. GUI界面 - `main_gui.py`
PyQt5图形界面，包含：

| 标签页 | 显示内容 |
|-------|---------|
| EEG信号 | 多通道实时波形 |
| 频段功率 | 5频段功率实时曲线 |
| 频谱 | FFT功率谱密度 |

**控制面板功能：**
- 设备选择与连接控制
- LSL输出流开关
- 显示参数配置（通道数、时间窗口）
- 专注度LCD数字显示
- REST API服务器启停

## 安装与运行

### 环境要求
- Python 3.8+
- Windows / Linux / macOS

### 安装依赖
```bash
pip install -r requirements.txt
```

### 运行GUI程序
```bash
python main_gui.py
```

### 仅运行API服务器
```bash
python rest_api.py
```

## 使用说明

### 快速开始
1. 启动程序：`python main_gui.py`
2. 选择设备类型（建议先用"Synthetic Board"测试）
3. 点击"连接设备"
4. 点击"开始采集"
5. 查看EEG波形和频段功率变化
6. 可选：启动LSL流或REST API

### API调用示例

**连接设备：**
```bash
curl -X POST "http://localhost:8000/connect" \
  -H "Content-Type: application/json" \
  -d '{"device_type": "synthetic"}'
```

**获取最新数据：**
```bash
curl "http://localhost:8000/data/latest?num_samples=100"
```

**获取频段功率：**
```bash
curl "http://localhost:8000/bandpower"
```

**启动LSL输出：**
```bash
curl -X POST "http://localhost:8000/lsl/start" \
  -H "Content-Type: application/json" \
  -d '{"stream_name": "MyEEG", "stream_type": "EEG"}'
```

## 项目文件结构

```
.
├── main_gui.py              # 主GUI程序
├── brainflow_acquisition.py # 数据采集层
├── signal_processing.py     # 信号处理管线
├── lsl_integration.py       # LSL协议集成
├── rest_api.py              # FastAPI服务
├── requirements.txt         # 依赖包列表
└── README.md               # 本文档
```

## 扩展开发

### 添加新设备支持
在 `DEVICE_CONFIG` 字典中添加新设备配置：

```python
DeviceType.NEW_DEVICE: {
    "board_id": BoardIds.NEW_BOARD.value,
    "eeg_channels": list(range(1, 33)),  # 32通道
    "sampling_rate": 500,
    "name": "新设备名称"
}
```

### 添加自定义处理算法
继承或修改 `RealtimePipeline` 类，添加回调函数：

```python
def custom_processor(data, band_powers):
    # 自定义处理逻辑
    pass

pipeline.add_callback(custom_processor)
```

### API接口扩展
在 `rest_api.py` 的 `create_app()` 函数中添加新路由：

```python
@app.get("/custom_endpoint")
async def custom_endpoint():
    return {"status": "ok", "data": "..."}
```

## 技术栈

| 模块 | 技术选型 |
|-----|---------|
| 硬件采集 | BrainFlow 5.x |
| 信号处理 | NumPy + SciPy |
| GUI框架 | PyQt5 + PyQtGraph |
| API服务 | FastAPI + Uvicorn |
| 数据传输 | pylsl (LSL 1.16) |

## 注意事项

1. **设备驱动**：使用真实硬件前请确保安装对应驱动
2. **采样率匹配**：LSL流输出前请确认采样率参数正确
3. **线程安全**：跨线程数据访问请使用锁机制
4. **内存管理**：长时间运行请关注缓冲区大小

## 许可证

本项目基于BrainFlow开源框架开发，遵循相应开源协议。
