# SkyWalking 告警规则优化工具

一个基于 Python + React 的 SkyWalking 告警规则智能优化平台，通过统计分析和机器学习算法，帮助 SRE 团队识别低效告警规则、优化配置参数、提升告警质量。

## ✨ 功能特性

### 🎯 核心功能

- **告警聚类分析** - 使用 DBSCAN 时间序列聚类 + TF-IDF 文本相似度算法，自动识别告警模式和周期性特征
- **低效规则识别** - 多维度评分模型（频率、关键度、噪声），精准定位频繁触发但不关键的告警规则
- **智能优化建议** - 阈值敏感性分析 + 百分位数最优计算，推荐 threshold/period/count/silencePeriod 参数配置
- **效果评估引擎** - 滑动窗口模拟告警触发，多维度评估优化效果（告警减少率、噪声率、关键覆盖率）
- **完整分析报告** - 一键生成包含数据概览、聚类分析、优化建议、效果评估的完整报告

### 🛠 技术栈

#### 后端
- **Web 框架**: FastAPI 0.109 + Uvicorn 0.27
- **数据模型**: Pydantic 2.5 + pydantic-settings
- **数据分析**: NumPy 1.26 + Pandas 2.1 + SciPy 1.11
- **机器学习**: Scikit-learn 1.3 (DBSCAN, TF-IDF)
- **API 客户端**: HTTPX 异步客户端

#### 前端
- **UI 框架**: React 18 + TypeScript 5 + Vite 5
- **样式方案**: Tailwind CSS 3 + Ant Design 5
- **状态管理**: Zustand 4
- **数据可视化**: ECharts 5 + echarts-for-react
- **图标库**: Phosphor Icons
- **路由**: React Router DOM 6
- **工具库**: Day.js + Axios

## 📁 项目结构

```
.
├── backend/                          # 后端 Python 项目
│   ├── app/
│   │   ├── analysis/                 # 分析算法模块
│   │   │   ├── clustering.py         # 告警聚类算法（DBSCAN + TF-IDF）
│   │   │   ├── rule_analyzer.py      # 低效规则识别（多维度评分）
│   │   │   ├── optimizer.py          # 规则优化算法（敏感性分析）
│   │   │   └── evaluator.py          # 效果评估引擎（模拟验证）
│   │   ├── api/
│   │   │   └── routes.py             # REST API 接口
│   │   ├── clients/
│   │   │   └── skywalking.py         # SkyWalking API 客户端（含 Mock）
│   │   ├── models/
│   │   │   └── alert.py              # 数据模型定义
│   │   ├── config.py                 # 配置管理
│   │   └── main.py                   # FastAPI 应用入口
│   ├── requirements.txt              # Python 依赖
│   └── .env.example                  # 环境变量示例
│
├── frontend/                         # 前端 React 项目
│   ├── src/
│   │   ├── pages/                    # 页面组件
│   │   │   ├── Dashboard.tsx         # 仪表盘总览
│   │   │   ├── Clustering.tsx        # 告警聚类分析
│   │   │   ├── Rules.tsx             # 低效规则识别
│   │   │   ├── Optimizer.tsx         # 优化建议中心
│   │   │   ├── Evaluator.tsx         # 效果评估中心
│   │   │   ├── Report.tsx            # 分析报告
│   │   │   └── Settings.tsx          # 系统设置
│   │   ├── components/               # 通用组件
│   │   │   ├── layout/
│   │   │   │   └── AppLayout.tsx     # 主布局组件
│   │   │   ├── ui/
│   │   │   │   └── StatCard.tsx      # 统计卡片
│   │   │   └── charts/               # 图表组件
│   │   │       ├── LineChart.tsx     # 折线/面积图
│   │   │       ├── PieChart.tsx      # 饼图/环形图
│   │   │       ├── BarChart.tsx      # 柱状图
│   │   │       └── RadarChart.tsx    # 雷达图
│   │   ├── stores/
│   │   │   └── analysisStore.ts      # Zustand 状态管理
│   │   ├── services/
│   │   │   └── api.ts                # API 服务层
│   │   ├── types/
│   │   │   └── index.ts              # TypeScript 类型定义
│   │   ├── utils/
│   │   │   └── format.ts             # 工具函数
│   │   └── styles/
│   │       └── index.css             # 全局样式
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── tailwind.config.js
│
└── .trae/documents/                  # 项目文档
    ├── PRD_SkyWalking告警规则优化工具.md
    └── 技术架构_SkyWalking告警规则优化工具.md
```

## 🚀 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+
- npm 9+ 或 yarn 1.22+

### 后端启动

1. 进入后端目录并安装依赖：

```bash
cd backend
pip install -r requirements.txt
```

2. 配置环境变量：

```bash
cp .env.example .env
# 编辑 .env 文件，配置 SkyWalking 连接信息
```

3. 启动后端服务：

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

4. 验证服务：

```bash
curl http://localhost:8000/api/v1/health
```

### 前端启动

1. 进入前端目录并安装依赖：

```bash
cd frontend
npm install
```

2. 启动开发服务器：

```bash
npm run dev
```

3. 访问应用：

打开浏览器访问 http://localhost:3000

4. 构建生产版本：

```bash
npm run build
```

## 🔧 配置说明

### 后端配置 (.env)

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `SKYWALKING_BASE_URL` | `http://localhost:12800` | SkyWalking OAP 服务地址 |
| `SKYWALKING_TIMEOUT` | `30` | API 超时时间（秒） |
| `CLUSTERING_EPS_TIME` | `300` | 聚类时间窗口（秒） |
| `CLUSTERING_MIN_SAMPLES` | `5` | 聚类最小样本数 |
| `MIN_INEFFICIENCY_SCORE` | `0.3` | 低效规则最小评分阈值 |
| `MIN_OPTIMIZATION_CONFIDENCE` | `0.5` | 优化建议最小置信度 |

### 前端配置 (vite.config.ts)

```typescript
server: {
  port: 3000,
  proxy: {
    '/api': {
      target: 'http://localhost:8000',  // 后端服务地址
      changeOrigin: true,
    },
  },
}
```

## 📊 核心算法

### 1. 告警聚类算法

**时间序列聚类 (DBSCAN)**
- 基于告警触发时间进行密度聚类
- 自动识别时间上聚集的告警群组
- 参数：eps=300秒（5分钟），min_samples=5

**文本相似度匹配 (TF-IDF + 余弦相似度)**
- 对告警消息进行向量化处理
- 识别内容相似的告警模式
- 阈值：相似度 > 0.85 归为同类

**周期性检测**
- 使用自相关分析检测周期性模式
- 识别每日/每周重复的告警

### 2. 多维度评分模型

低效度综合评分公式：

```
inefficiency_score = (frequency * 0.4 + noise * 0.4) * (1 - criticality * 0.5)
```

- **频率评分 (frequency)**: 告警触发频率归一化值
- **关键度评分 (criticality)**: 基于优先级、服务重要性、业务影响评估
- **噪声评分 (noise)**: 基于告警波动性、持续时间、恢复速度评估

### 3. 规则优化算法

**阈值敏感性分析**
- 遍历阈值范围内的所有可能值
- 计算每个阈值下的告警触发次数
- 寻找最优平衡点（减少噪声 + 保留关键告警）

**百分位数最优阈值计算**
```
optimal_threshold = percentile(metric_values, 95)
```

**参数优化策略**
- `threshold`: 基于指标分布的百分位数调整
- `period`: 基于告警持续时间分布调整
- `count`: 基于告警频率分布调整
- `silencePeriod`: 基于告警间隔分布调整

### 4. 效果评估引擎

**滑动窗口模拟**
```
窗口大小 = period * 1分钟
步长 = 1分钟
在每个窗口内统计满足条件的指标点数量
如果数量 >= count，则触发告警
```

**评估指标**
- 告警数量变化率
- 噪声减少率
- 关键告警覆盖率
- 平均告警间隔
- 告警持续时间变化

## 📡 API 接口

### 健康检查
```
GET /api/v1/health
```

### 告警数据
```
GET /api/v1/alerts?lookbackHours=168
GET /api/v1/alerts/clusters?lookbackHours=168
```

### 规则管理
```
GET /api/v1/rules
GET /api/v1/rules/inefficient?lookbackHours=168&minInefficiencyScore=0.3
GET /api/v1/rules/optimize?lookbackHours=168&minConfidence=0.5
GET /api/v1/rules/evaluate?lookbackHours=168
POST /api/v1/rules/compare-configs
```

### 分析报告
```
GET /api/v1/analysis/report?lookbackHours=168
```

## 🎨 界面预览

### 页面功能

1. **仪表盘** - 告警总览、趋势分析、分布统计
2. **告警聚类** - 聚类结果展示、模式识别、周期性分析
3. **低效规则** - 多维度评分、规则排名、问题诊断
4. **优化建议** - 参数对比、预期效果、置信度评估
5. **效果评估** - 优化前后对比、多维度评估、模拟验证
6. **分析报告** - 完整分析报告、导出功能
7. **系统设置** - 连接配置、参数调整、规则管理

### 设计特点

- 深色主题设计，护眼舒适
- 玻璃态卡片效果，现代感强
- 响应式布局，支持多端访问
- 丰富的数据可视化图表

## 🧪 演示模式

项目内置 Mock 数据生成器，无需连接真实 SkyWalking 环境即可体验所有功能：

1. 启动后端服务（默认使用 Mock 模式）
2. 访问前端页面即可看到演示数据
3. 在「系统设置」中可以切换 Mock 模式

Mock 数据包含：
- 1000+ 条历史告警
- 20+ 条告警规则
- 多种告警模式和周期性特征
- 不同严重程度的低效规则

## 🛡 安全注意事项

1. **API 密钥安全**: 不要在代码中硬编码 SkyWalking API 密钥，使用环境变量管理
2. **CORS 配置**: 生产环境请严格限制允许的域名
3. **接口鉴权**: 建议在生产环境添加 API 认证机制（如 API Key、OAuth2）
4. **数据脱敏**: 告警消息可能包含敏感信息，展示时注意脱敏处理

## 🤝 贡献指南

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📝 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 📞 技术支持

如有问题或建议，请通过以下方式联系：

- 提交 Issue
- 发送邮件至 sre@example.com
- 查看项目文档：`.trae/documents/` 目录

---

**让告警更智能，让运维更高效！** 🚀
