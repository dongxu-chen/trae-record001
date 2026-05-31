# 人脸面部捕捉与重定向系统

基于 Python + MediaPipe + OpenCV + Blender + VRChat 的实时面部动捕系统。

## ✨ 功能特性

### 核心功能
- **头部姿态追踪**: 俯仰(Pitch)、偏航(Yaw)、翻滚(Roll)
- **眼部运动追踪**: 眼睛睁开度、眼球转动、眨眼检测
- **嘴型同步**: 嘴巴张开度、微笑/皱眉、嘴部宽窄
- **眉毛运动**: 眉毛上下运动追踪
- **Blender 实时连接**: 通过 OSC 协议实时驱动 3D 模型

### 🆕 高级功能
- **虹膜边缘检测**: 使用MediaPipe虹膜边缘关键点进行更精确的眼动追踪
- **音频唇形同步**: 融合音频特征（RMS、过零率、频谱质心）实现音画同步
- **参数压缩映射**: 分段线性、Sigmoid、Tanh三种压缩算法
- **VRChat驱动**: 通过OSC协议实时驱动VRChat虚拟形象
- **WebSocket广播**: 支持多客户端接收面部追踪数据
- **面部动作单元(AU)分析**: 基于FACS标准，30+个动作单元识别
- **表情混合引擎**: 多层叠加、6种混合模式、16种预设表情

## 📁 项目结构

```
.
├── main.py                         # 主程序入口
├── requirements.txt                # Python依赖
├── README.md                       # 使用说明文档
├── src/
│   ├── __init__.py
│   ├── face_capture.py            # MediaPipe人脸捕捉模块
│   ├── expression_extractor.py    # 表情参数提取(虹膜检测+参数压缩)
│   ├── audio_sync.py              # 音频唇形同步模块
│   ├── action_units.py            # 面部动作单元(AU)分析
│   ├── expression_blender.py      # 表情混合引擎
│   ├── vrchat_driver.py           # VRChat OSC驱动
│   └── osc_sender.py              # OSC数据发送模块
├── config/
│   ├── __init__.py
│   └── config.py                  # 配置文件
└── blender_scripts/
    └── osc_receiver.py            # Blender端接收脚本
```

## 📦 安装步骤

### 1. 安装 Python 依赖

```bash
pip install -r requirements.txt
```

**音频相关依赖说明:**
- `pyaudio`: 麦克风音频捕获
- `librosa`: 音频特征提取
- `websockets`: WebSocket服务器

**Windows 安装 PyAudio:**
```bash
pip install pipwin
pipwin install pyaudio
```

### 2. Blender 端配置

1. 打开 Blender
2. 在 Blender 中安装依赖:
   ```bash
   "Blender Python 路径" -m pip install pythonosc
   ```
3. 运行 `blender_scripts/osc_receiver.py`

### 3. VRChat 配置

1. 打开 VRChat
2. 启动时添加启动参数: `--osc=9000:9001`
3. 或者在游戏内设置中启用 OSC
4. 使用支持面部追踪的Avatar

## 🚀 使用方法

### 1. 启动捕捉程序

```bash
# 基础模式
python main.py

# 启用VRChat驱动
python main.py --vrchat

# 启用WebSocket广播
python main.py --websocket

# 启用所有高级功能
python main.py --vrchat --websocket

# 禁用AU分析和表情混合
python main.py --no-au --no-blending

# 启动时应用预设表情
python main.py --preset happy --preset-influence 0.7
```

### 2. 运行时快捷键

| 按键 | 功能 |
|-----|------|
| `q` | 退出程序 |
| `d` | 切换面部网格显示 |
| `a` | 切换音频同步 |
| `c` | 切换参数压缩映射 |
| `u` | 切换AU分析 |
| `b` | 切换表情混合 |
| `v` | 切换VRChat驱动 |
| `w` | 切换WebSocket |
| `r` | 重新连接OSC |
| `n` / `p` | 下一个/上一个表情预设 |
| `[` / `]` | 减少/增加预设影响力 |
| `0` | 重置表情混合 |

## 🔬 核心技术详解

### 1. VRChat OSC驱动

**实现位置**: [vrchat_driver.py](file:///d:/Trae/project/record001/645/src/vrchat_driver.py)

支持VRChat官方面部追踪协议，包含60+参数:
- **眼部参数**: EyeLeft/Right X/Y, EyeLid, EyeWiden, EyeSquint
- **眉毛参数**: BrowLeft/Right Up/Down
- **嘴部参数**: JawOpen, MouthSmile, MouthFrown, MouthFunnel, MouthPucker
- **头部姿态**: HeadPitch, HeadYaw, HeadRoll
- **高级参数**: CheekSquint, NoseSneer, Tongue控制等

### 2. 面部动作单元(AU)分析

**实现位置**: [action_units.py](file:///d:/Trae/project/record001/645/src/action_units.py)

基于FACS (Facial Action Coding System) 标准，支持30+动作单元:

| AU编号 | 名称 | 说明 |
|-------|------|------|
| AU1 | Inner Brow Raiser | 眉毛内侧上扬 |
| AU2 | Outer Brow Raiser | 眉毛外侧上扬 |
| AU4 | Brow Lowerer | 眉毛下压 |
| AU5 | Upper Lid Raiser | 上眼睑抬起 |
| AU6 | Cheek Raiser | 脸颊抬起 |
| AU7 | Lid Tightener | 眼睑收紧 |
| AU12 | Lip Corner Puller | 嘴角拉伸(微笑) |
| AU15 | Lip Corner Depressor | 嘴角下压(皱眉) |
| AU25 | Lips Part | 嘴唇分开 |
| AU26 | Jaw Drop | 下颚下降 |
| AU43 | Eyes Closed | 闭眼 |
| AU45 | Blink | 眨眼 |

**基线校准**: 启动时自动采集30帧中性表情作为基线

### 3. 表情混合引擎

**实现位置**: [expression_blender.py](file:///d:/Trae/project/record001/645/src/expression_blender.py)

**混合模式 (BlendMode)**:
| 模式 | 说明 | 公式 |
|-----|------|------|
| `ADDITIVE` | 加法混合 | `result += weight * influence` |
| `MULTIPLICATIVE` | 乘法混合 | `result *= (1 + weight * influence)` |
| `MAXIMUM` | 取最大值 | `result = max(result, weight)` |
| `MINIMUM` | 取最小值 | `result = min(result, weight)` |
| `AVERAGE` | 平均 | `result = (result + weight) / 2` |
| `WEIGHTED` | 加权混合 | `result = result*(1-inf) + weight*inf` |

**内置表情预设 (16种)**:
`happy`, `sad`, `angry`, `surprised`, `fear`, `disgust`, 
`contempt`, `neutral`, `excited`, `thinking`, `suspicious`, 
`playful`, `shy`, `kiss`, `laugh`, `scream`, `whisper`

**混合层结构**:
1. **facial_tracking** - 面部追踪数据 (加权混合)
2. **emotion_preset** - 表情预设叠加 (加法混合)
3. **correction** - 修正层 (加权混合)

### 4. WebSocket广播

**实现位置**: [vrchat_driver.py](file:///d:/Trae/project/record001/645/src/vrchat_driver.py#L364-L461)

广播数据格式 (JSON):
```json
{
  "type": "face_data",
  "timestamp": 1234567890.123,
  "data": {
    "head_pose": {"pitch": 0.0, "yaw": 0.0, "roll": 0.0},
    "expressions": {"mouth_open": 0.5, "smile": 0.8},
    "action_units": {"AU1": 0.3, "AU12": 0.7},
    "blend_info": {"master_gain": 1.0, "layers": [...]}
  }
}
```

## 📊 完整命令行参数

```bash
python main.py [OPTIONS]

基础配置:
  --config PATH        配置文件路径
  --video INT          视频源设备ID (默认: 0)
  --ip STR             OSC服务器IP (默认: 127.0.0.1)
  --port INT           OSC服务器端口 (默认: 9000)

功能开关:
  --no-preview         不显示预览窗口
  --no-audio           禁用音频同步
  --no-compression     禁用参数压缩映射
  --no-au              禁用AU分析
  --no-blending        禁用表情混合
  --vrchat             启用VRChat驱动
  --websocket          启用WebSocket服务器

高级参数:
  --audio-weight FLOAT 音频融合权重 0-1 (默认: 0.3)
  --preset STR         初始表情预设 (happy, sad, angry...)
  --preset-influence FLOAT 预设影响力 0-1 (默认: 0.5)
```

## 📡 VRChat 参数映射

### 眼部参数
| OSC地址 | 范围 | 说明 |
|---------|------|------|
| `/avatar/parameters/EyeLeftX` | -1~1 | 左眼水平位置 |
| `/avatar/parameters/EyeLeftY` | -1~1 | 左眼垂直位置 |
| `/avatar/parameters/EyeLeftLid` | 0~1 | 左眼睁开度 |
| `/avatar/parameters/EyeLeftWiden` | 0~1 | 左眼睁大 |
| `/avatar/parameters/EyeLeftSquint` | 0~1 | 左眼眯眼 |

### 眉毛参数
| OSC地址 | 范围 | 说明 |
|---------|------|------|
| `/avatar/parameters/BrowLeftUp` | 0~1 | 左眉上扬 |
| `/avatar/parameters/BrowLeftDown` | 0~1 | 左眉下压 |
| `/avatar/parameters/BrowRightUp` | 0~1 | 右眉上扬 |
| `/avatar/parameters/BrowRightDown` | 0~1 | 右眉下压 |

### 嘴部参数
| OSC地址 | 范围 | 说明 |
|---------|------|------|
| `/avatar/parameters/JawOpen` | 0~1 | 下颚张开 |
| `/avatar/parameters/MouthApeShape` | 0~1 | 嘴巴张开 |
| `/avatar/parameters/MouthSmileLeft` | 0~1 | 左嘴角微笑 |
| `/avatar/parameters/MouthSmileRight` | 0~1 | 右嘴角微笑 |
| `/avatar/parameters/MouthFrownLeft` | 0~1 | 左嘴角皱眉 |
| `/avatar/parameters/MouthFrownRight` | 0~1 | 右嘴角皱眉 |
| `/avatar/parameters/MouthFunnel` | 0~1 | 嘴巴呈漏斗状 |
| `/avatar/parameters/MouthPucker` | 0~1 | 噘嘴 |

## 🎮 VRChat 使用流程

1. **启动 VRChat** (确保添加 `--osc` 参数)
2. **加载支持面部追踪的 Avatar**
3. **启动捕捉程序**:
   ```bash
   python main.py --vrchat
   ```
4. **按 `v` 键** 启用/禁用 VRChat 驱动
5. **在 VRChat 中** 即可看到面部追踪效果

## 🔌 WebSocket 客户端示例

```javascript
// 浏览器端接收面部数据
const ws = new WebSocket('ws://127.0.0.1:8080');

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === 'face_data') {
        console.log('头部姿态:', data.data.head_pose);
        console.log('表情参数:', data.data.expressions);
        console.log('动作单元:', data.data.action_units);
    }
};
```

## 💻 系统要求

- Python 3.8+
- OpenCV 4.8+
- MediaPipe 0.10+
- Blender 3.0+ (可选)
- VRChat (可选)
- 摄像头设备
- 麦克风设备 (音频同步可选)

## 🔧 故障排除

1. **VRChat无反应**: 确认启动参数 `--osc=9000:9001`，Avatar支持面部追踪
2. **WebSocket连接失败**: 确认端口8080未被占用，防火墙允许连接
3. **AU分析不准确**: 确保启动时保持中性表情3秒完成基线校准
4. **表情混合异常**: 按 `0` 键重置混合状态，调整预设影响力

## 📝 新增功能总结

| 功能 | 文件 | 说明 |
|-----|------|------|
| VRChat驱动 | [vrchat_driver.py](file:///d:/Trae/project/record001/645/src/vrchat_driver.py) | 60+ VRChat参数映射 |
| AU分析 | [action_units.py](file:///d:/Trae/project/record001/645/src/action_units.py) | 30+ FACS动作单元 |
| 表情混合 | [expression_blender.py](file:///d:/Trae/project/record001/645/src/expression_blender.py) | 6种混合模式,16种预设 |
| WebSocket | [vrchat_driver.py](file:///d:/Trae/project/record001/645/src/vrchat_driver.py#L364-L461) | 实时数据广播 |

## 📄 许可证

MIT License
