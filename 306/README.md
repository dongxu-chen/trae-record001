# 在线考试防作弊系统

基于人脸识别、屏幕录制、切屏检测的智能在线考试防作弊系统。

## 技术栈

- **后端框架**: FastAPI + Uvicorn
- **人脸识别**: OpenCV + PyTorch (FaceNet)
- **屏幕录制**: mss + OpenCV
- **实时通信**: WebSocket + WebRTC (aiortc)
- **答案相似度分析**: Sentence-BERT + 余弦相似度
- **前端**: HTML5 + CSS3 + JavaScript

## 功能特性

### 🔐 身份验证
- 考前人脸注册与验证
- 考试中实时人脸检测
- 多人脸检测预警
- 人脸比对相似度计算

### 📹 考试监控
- 全程屏幕录制
- WebRTC实时视频流传输
- 视频帧人脸识别标注
- 录像文件自动保存

### 🖥️ 切屏检测
- 系统级窗口切换检测
- 浏览器标签页可见性检测
- 可疑窗口识别
- 频繁切换预警

### ⚠️ 异常预警
- 实时告警推送（WebSocket）
- 多级告警级别（信息/警告/危险）
- 告警确认机制
- 详细告警元数据

### 🎲 随机抽题
- 支持按科目、难度筛选
- 题目和选项随机打乱
- 防止题目泄露
- 灵活的抽题策略

### 📊 相似度分析
- 多算法融合（余弦相似度、Jaccard、编辑距离）
- Sentence-BERT语义分析
- 批量答案比对
- 抄袭自动检测预警

## 项目结构

```
306/
├── core/                          # 核心功能模块
│   ├── face_recognition/          # 人脸识别模块
│   │   ├── __init__.py
│   │   └── face_recognition.py
│   ├── screen_recorder/           # 屏幕录制模块
│   │   ├── __init__.py
│   │   └── screen_recorder.py
│   ├── tab_detection/             # 切屏检测模块
│   │   ├── __init__.py
│   │   └── tab_detection.py
│   ├── question_bank/             # 题库管理模块
│   │   ├── __init__.py
│   │   └── question_bank.py
│   ├── similarity/                # 相似度分析模块
│   │   ├── __init__.py
│   │   └── similarity.py
│   └── monitoring/                # 考试监控模块
│       ├── __init__.py
│       └── monitoring.py
├── server/                        # 服务端模块
│   ├── websocket/                 # WebSocket通信
│   │   ├── __init__.py
│   │   └── websocket_server.py
│   └── webrtc/                    # WebRTC视频流
│       ├── __init__.py
│       └── webrtc_server.py
├── templates/                     # HTML模板
│   ├── index.html                 # 首页
│   ├── student.html               # 考生端
│   └── teacher.html               # 教师端
├── static/                        # 静态资源
│   ├── css/
│   │   └── style.css
│   └── js/
│       ├── webrtc.js              # WebRTC逻辑
│       ├── student.js             # 考生端逻辑
│       └── teacher.js             # 教师端逻辑
├── data/                          # 数据目录
│   ├── recordings/                # 录屏文件
│   ├── uploads/                   # 上传文件
│   ├── reports/                   # 考试报告
│   └── sample_questions.json      # 示例题库
├── models/                        # 模型文件目录
├── config.py                      # 配置文件
├── main.py                        # 主服务入口
├── requirements.txt               # 依赖列表
└── README.md                      # 项目说明
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动服务

```bash
python main.py
```

或使用uvicorn：

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. 访问系统

- 首页: http://localhost:8000
- 考生端: http://localhost:8000/student
- 教师端: http://localhost:8000/teacher
- API文档: http://localhost:8000/docs

## API接口

### 认证接口
- `POST /api/auth/login` - 登录

### 人脸接口
- `POST /api/face/register` - 注册人脸
- `POST /api/face/verify` - 验证人脸

### 考试接口
- `POST /api/exam/start` - 开始考试
- `POST /api/exam/answer` - 提交答案
- `POST /api/exam/submit` - 提交试卷
- `GET /api/exam/questions` - 获取题目

### 监控接口
- `GET /api/monitor/stats` - 获取监控统计
- `GET /api/monitor/student/{student_id}` - 获取学生状态
- `GET /api/monitor/alerts` - 获取告警列表
- `POST /api/monitor/alert/acknowledge` - 确认告警

### WebRTC接口
- `POST /api/webrtc/offer` - 处理WebRTC offer
- `POST /api/webrtc/ice` - 添加ICE候选
- `DELETE /api/webrtc/peer/{student_id}` - 关闭连接

### WebSocket接口
- `WS /ws/{student_id}?role=student` - 考生WebSocket
- `WS /ws/{student_id}?role=teacher` - 教师WebSocket

## 配置说明

主要配置参数在 `config.py` 中：

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `FACE_RECOGNITION_THRESHOLD` | 人脸识别阈值 | 0.6 |
| `SCREEN_RECORD_FPS` | 录屏帧率 | 10 |
| `TAB_SWITCH_THRESHOLD` | 切屏告警阈值 | 3次/分钟 |
| `SIMILARITY_THRESHOLD` | 相似度告警阈值 | 0.85 |
| `QUESTION_COUNT_PER_EXAM` | 每考试题数 | 10 |

## 使用流程

### 考生端流程
1. 进入考生页面，输入考生ID
2. 注册/验证人脸
3. 开始考试，系统随机抽题
4. 考试过程中：
   - 摄像头实时监控
   - 屏幕自动录制
   - 切屏行为被检测
5. 答题并提交试卷
6. 系统自动进行相似度分析

### 教师端流程
1. 进入教师监控页面
2. 实时查看所有考生状态
3. 接收异常告警通知
4. 查看考生视频画面
5. 查看考试统计和相似度分析报告

## 告警类型

| 类型 | 级别 | 说明 |
|------|------|------|
| `face_not_detected` | WARNING | 未检测到人脸 |
| `face_mismatch` | DANGER | 人脸不匹配 |
| `multiple_faces` | WARNING | 检测到多人脸 |
| `tab_switch` | WARNING | 窗口切换 |
| `excessive_switching` | DANGER | 频繁切换窗口 |
| `tab_hidden` | WARNING | 页面被隐藏 |
| `answer_similarity` | DANGER | 答案相似度过高 |

## 注意事项

1. **浏览器权限**: 需要授予摄像头和屏幕共享权限
2. **HTTPS**: 生产环境必须使用HTTPS，否则摄像头功能受限
3. **模型文件**: FaceNet模型可自行下载放入 `models/` 目录
4. **跨平台**: 切屏检测支持Windows、Linux、macOS
5. **性能**: 建议使用GPU加速人脸识别和相似度分析

## 扩展建议

- 添加数据库持久化存储
- 集成JWT身份认证
- 支持更多题型（判断、填空、编程题）
- 添加AI作弊行为分析
- 支持考试回放功能
- 集成在线IDE支持编程题
- 添加考试时间限制和倒计时

## 许可证

MIT License
