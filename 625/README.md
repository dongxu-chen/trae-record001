# 文本摘要生成工具 (Text Summarizer)

基于 HuggingFace Transformers + PyTorch + FastAPI + React 构建的智能文本摘要生成工具。

## 功能特性

- ✅ **双模式摘要**：支持生成式（Abstractive）和抽取式（Extractive）两种摘要方式
- ✅ **多模型支持**：集成 BART (Facebook) 和 T5 (Google) 两大预训练模型
- ✅ **多语言支持**：自动检测并支持 20+ 种语言的文本处理
- ✅ **长度可控制**：灵活配置摘要长度，满足不同场景需求
- ✅ **关键词提取**：智能提取并展示文本中的关键信息
- ✅ **文件上传**：支持上传 TXT 文本文件进行批量处理
- ✅ **压缩率统计**：实时显示原文与摘要的压缩比例
- ✅ **现代 Web 界面**：基于 React + Tailwind CSS 的优雅交互界面

## 技术栈

### 后端
- **FastAPI**：高性能 Web 框架
- **PyTorch**：深度学习框架
- **HuggingFace Transformers**：BART、T5 模型
- **NLTK + NetworkX**：抽取式摘要算法（TextRank、MMR）
- **scikit-learn**：TF-IDF 向量化、余弦相似度计算

### 前端
- **React 18**：UI 框架
- **Vite**：构建工具
- **Tailwind CSS**：样式框架
- **Lucide React**：图标库
- **Axios**：HTTP 客户端

## 项目结构

```
.
├── backend/                 # 后端服务
│   ├── app/
│   │   ├── main.py         # FastAPI 主应用
│   │   ├── models/         # Pydantic 数据模型
│   │   ├── services/       # 核心服务
│   │   │   ├── abstractive_summarizer.py  # 生成式摘要（BART/T5）
│   │   │   └── extractive_summarizer.py   # 抽取式摘要（TextRank/MMR）
│   │   └── utils/          # 工具模块
│   │       ├── language_detector.py       # 语言检测
│   │       └── keyword_extractor.py       # 关键词提取
│   ├── requirements.txt    # Python 依赖
│   └── .env               # 环境配置
└── frontend/              # 前端应用
    ├── src/
    │   ├── App.jsx        # 主组件
    │   ├── components/    # UI 组件
    │   ├── services/      # API 服务
    │   └── styles/        # 样式文件
    └── package.json       # Node 依赖
```

## 快速开始

### 1. 启动后端服务

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

后端 API 文档：http://localhost:8000/docs

### 2. 启动前端服务

```bash
cd frontend
npm install
npm run dev
```

前端访问地址：http://localhost:3000

## API 接口

### 生成摘要

**POST** `/summarize`

请求体：
```json
{
  "text": "要摘要的文本内容...",
  "summary_type": "abstractive",
  "model": "bart",
  "max_length": 150,
  "min_length": 50,
  "extractive_sentences": 3,
  "preserve_keywords": true
}
```

响应：
```json
{
  "summary": "生成的摘要...",
  "original_length": 1234,
  "summary_length": 256,
  "summary_type": "abstractive",
  "model": "bart",
  "language": "zh",
  "key_phrases": ["关键词1", "关键词2", ...],
  "compression_ratio": 0.79
}
```

### 健康检查

**GET** `/health`

## 使用说明

### 生成式摘要 (Abstractive)
使用 BART 或 T5 模型，通过深度学习生成全新的摘要文本，更符合人类表达习惯。

### 抽取式摘要 (Extractive)
使用 TextRank 算法，从原文中提取最重要的句子组成摘要，保留原文措辞。

### 参数说明
- **摘要类型**：选择生成式或抽取式
- **模型选择**：BART 或 T5（仅生成式）
- **长度设置**：控制摘要的最大/最小长度或句子数量
- **保留关键信息**：优化算法以更好地保留关键词

## 注意事项

1. 首次启动会自动下载预训练模型（约 1.5GB），请耐心等待
2. 建议在有 GPU 的环境下运行，CPU 模式下处理速度较慢
3. 支持的文本最大长度为 1024 个 tokens
4. 中文摘要建议使用 BART 模型，效果更佳

## License

MIT
