# API安全漏洞扫描器

一个功能强大的API安全漏洞扫描器，支持扫描API常见漏洞（越权、SQL注入、XXE、IDOR），生成漏洞报告。

## 功能特性

- 🛡️ **漏洞检测**: SQL注入、XXE注入、IDOR（不安全直接对象引用）、越权访问
- 🔐 **认证支持**: Bearer Token、Basic Auth、自定义头部
- ⚡ **并发扫描**: 支持多线程并发检测
- ✅ **误报验证**: 自动验证减少误报
- 📊 **报告生成**: 支持HTML、Markdown、JSON格式报告
- 🎨 **Web界面**: 美观的React前端界面

## 项目结构

```
.
├── backend/                 # Python后端
│   ├── main.py            # FastAPI主应用
│   ├── requirements.txt # Python依赖
│   ├── scanner/           # 扫描器模块
│   │   ├── config.py   # 配置模型
│   │   ├── request_engine.py    # 请求引擎
│   │   ├── vulnerability_detector.py  # 漏洞检测器
│   │   ├── scan_manager.py    # 扫描管理器
│   │   └── report_generator.py  # 报告生成器
│   └── payloads/          # 漏洞载荷库
│       ├── sql_injection.txt   # SQL注入载荷
│       ├── xxe.txt        # XXE注入载荷
│       └── idor.txt       # IDOR载荷
└── frontend/              # React前端
    ├── package.json
    ├── public/
    └── src/
        ├── App.js
        ├── index.js
        ├── styles.css
        ├── services/
        │   └── api.js
        └── components/
            ├── ScanPage.js
            ├── ResultsPage.js
            └── PayloadsPage.js
```

## 快速开始

### 1. 启动后端服务

```bash
cd backend
pip install -r requirements.txt
python main.py
```

后端服务将在 http://localhost:8000 启动

### 2. 启动前端服务

```bash
cd frontend
npm install
npm start
```

前端服务将在 http://localhost:3000 启动

## API文档

启动后端后，访问 http://localhost:8000/docs 查看Swagger API文档

## 使用说明

1. 在扫描页面输入目标URL
2. 配置认证方式（如果需要）
3. 选择扫描类型
4. 点击开始扫描
5. 查看结果并导出报告

## 支持的漏洞类型

- **SQL注入**: 检测SQL注入漏洞
- **XXE注入**: 检测XML外部实体注入
- **IDOR**: 检测不安全直接对象引用
- **越权访问**: 检测权限提升和越权访问
