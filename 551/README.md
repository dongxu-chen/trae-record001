# 实时语音转文字字幕系统

基于 Python + SpeechRecognition + WebSocket + React + Node.js 实现的实时语音转文字字幕系统。

## 功能特性

- ✅ **实时语音识别**：接收麦克风音频流，实时转写为文字
- ✅ **滚动字幕显示**：美观的滚动字幕界面
- ✅ **多语言支持**：支持10种语言识别（中文、英语、日语、韩语、法语、德语、西班牙语、俄语等）
- ✅ **标点预测**：智能添加中英文标点符号
- ✅ **热词优化**：自定义热词库，提高专业术语识别准确率
- ✅ **实时通信**：基于 WebSocket 的实时数据传输

## 技术栈

### 后端
- **Python**：语音识别核心
  - SpeechRecognition - 语音识别库
  - PyAudio - 音频输入
  - websockets - WebSocket服务
  - jieba - 中文分词
- **Node.js**：WebSocket代理服务器
  - ws - WebSocket库
  - express - Web服务器
  - cors - 跨域支持

### 前端
- **React 18**：前端框架
- **原生CSS**：样式设计

## 项目结构

```
551/
├── backend-python/          # Python语音识别后端
│   ├── requirements.txt     # Python依赖
│   ├── config.py            # 配置管理
│   ├── speech_recognizer.py # 主语音识别服务
│   ├── punctuation_predictor.py  # 标点预测
│   └── hotword_optimizer.py      # 热词优化
├── backend-node/            # Node.js WebSocket服务器
│   ├── package.json
│   └── server.js
├── frontend/                # React前端
│   ├── package.json
│   ├── public/
│   │   └── index.html
│   └── src/
│       ├── index.js
│       ├── index.css
│       └── App.js
├── install.bat              # Windows安装脚本
├── start.bat                # Windows启动脚本
└── README.md
```

## 安装说明

### 前置要求

- Python 3.8+
- Node.js 16+
- 麦克风设备

### Windows 一键安装

1. 双击运行 `install.bat`
2. 等待所有依赖安装完成

### 手动安装

#### 1. Python后端依赖
```bash
cd backend-python
pip install -r requirements.txt
```

#### 2. Node.js后端依赖
```bash
cd backend-node
npm install
```

#### 3. React前端依赖
```bash
cd frontend
npm install
```

## 启动说明

### Windows 一键启动

1. 双击运行 `start.bat`
2. 等待三个服务启动完成
3. 浏览器自动打开 http://localhost:3000

### 手动启动

#### 1. 启动Python语音识别服务
```bash
cd backend-python
python speech_recognizer.py
```

#### 2. 启动Node.js WebSocket服务器（新终端）
```bash
cd backend-node
npm start
```

#### 3. 启动React前端（新终端）
```bash
cd frontend
npm start
```

## 技术架构升级说明

### 1. BERT标点预测模型

**文件**: [punctuation_predictor.py](file:///d:/Project/trae/project/record001/551/backend-python/punctuation_predictor.py)

- **模型架构**: 使用预训练的BERT/ALBERT模型进行Token分类
- **中文模型**: `ckiplab/albert-tiny-chinese-ws` - 轻量级中文分词和标点预测
- **英文模型**: `oliverguhr/fullstop-punctuation-multilang-large` - 多语言标点恢复
- **推理优化**: 
  - 自动检测CUDA，优先使用GPU加速
  - 后台线程异步加载模型，不阻塞启动
  - 线程安全的模型推理锁
  - 自动降级到规则引擎（当模型不可用时）
- **支持标点**: 句号、逗号、问号、感叹号、冒号、分号、顿号

### 2. 加权前缀树（Weighted Trie）热词匹配

**文件**: [hotword_optimizer.py](file:///d:/Project/trae/project/record001/551/backend-python/hotword_optimizer.py)

**数据结构**:
```
WeightedTrieNode
├── children: Dict[char, WeightedTrieNode]
├── is_end_of_word: bool
├── weight: float          # 节点权重（向上传播）
├── word: str              # 完整热词
└── hotword_info: Dict     # 热词元数据
```

**核心算法**:
- **权重传播**: 插入热词时，权重从叶子节点向上传播到根节点
- **优先匹配**: 遍历时遇到高权重节点优先返回
- **重叠解决**: 重叠匹配时选择权重更高、相似度更高的热词
- **模糊匹配**: 基于Jaccard相似度 + 长度比的混合相似度算法
- **动态权重**: 每次匹配成功后热词权重自动增加（强化学习）

**性能优化**:
- O(n*m) 时间复杂度（n为文本长度，m为平均热词长度）
- 支持阈值过滤（默认0.6）
- 支持热词删除后的内存回收

### 3. 流式语音识别（<500ms延迟）

**文件**: [speech_recognizer.py](file:///d:/Project/trae/project/record001/551/backend-python/speech_recognizer.py)

**架构设计**:
```
麦克风音频流
    ↓ (512 samples/chunk)
音频捕获线程 → 实时能量检测 → 音频队列
    ↓ (0.3s缓冲)
识别线程 → Google API识别 → 热词优化 → BERT标点
    ↓ (partial/final)
WebSocket广播 → React前端实时显示
```

**延迟优化**:
- **小音频块**: 512 samples/chunk（约32ms）
- **短缓冲**: 0.3秒音频缓冲即开始识别
- **快速静音检测**: 基于实时能量计算
- **多线程流水线**: 捕获/识别/发送完全并行
- **Partial结果**: 识别中间结果立即发送，Final结果延迟确认

**延迟监控**:
- 捕获延迟（Capture Latency）: 音频捕获到进入队列
- 处理延迟（Processing Time）: 识别+优化+标点
- 总延迟（Total Latency）: 从音频捕获到WebSocket发送
- 前端显示滑动窗口平均延迟（最近20条）

## 使用说明

### 基本使用

1. 确保麦克风已连接并授权
2. 系统启动后，对着麦克风说话
3. 文字会实时显示在字幕区域

### 语言切换

1. 在右侧控制面板的"语言选择"下拉菜单中选择目标语言
2. 支持的语言：
   - 中文（普通话）- zh-CN
   - 中文（台湾）- zh-TW
   - 英语（美国）- en-US
   - 英语（英国）- en-GB
   - 日语 - ja-JP
   - 韩语 - ko-KR
   - 法语 - fr-FR
   - 德语 - de-DE
   - 西班牙语 - es-ES
   - 俄语 - ru-RU

### 热词管理

1. 在"热词优化"区域输入专业术语或常用词汇
2. 点击"添加"按钮或按回车键
3. 热词会提高语音识别的准确率
4. 点击热词旁的×按钮可删除热词

### 清空记录

点击字幕区域右上角的"清空记录"按钮可清除所有历史字幕。

## 配置说明

Python语音识别服务配置文件位于 `backend-python/config.json`（首次运行后生成），可配置：

- 默认语言
- 热词列表
- WebSocket端口
- 音频参数

## 注意事项

1. **麦克风权限**：首次使用时，请确保允许浏览器访问麦克风
2. **网络连接**：语音识别使用Google API，需要稳定的网络连接
3. **环境噪音**：在安静环境下使用可获得更好的识别效果
4. **说话语速**：适中的语速有助于提高识别准确率

## 端口说明

- Python WebSocket: `8765`
- Node.js Server: `3001`
- React Frontend: `3000`

## 故障排除

### Python语音识别启动失败
- 检查PyAudio是否正确安装
- 确认麦克风设备已连接
- 尝试升级SpeechRecognition库

### WebSocket连接失败
- 检查端口是否被占用
- 确认Python服务已正常启动
- 查看控制台错误信息

### 前端无法加载
- 确认Node.js服务已启动
- 检查浏览器控制台错误
- 尝试清除浏览器缓存

## 许可证

MIT License
