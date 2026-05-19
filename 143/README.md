# 跨平台电子书同步系统

使用 Flutter + Dart + Firebase 构建的跨平台电子书同步应用，支持 iOS、Android 和 Web 三端。系统采用改进的离线优先架构，支持 AI 书摘总结、阅读习惯分析、Delta 格式笔记、CRDT 同步策略和 OCR 图像预处理。

## 🤖 AI 智能功能

### 1. AI 书摘摘要生成

系统集成 AI 服务，自动为书摘内容生成精炼摘要：

```dart
final summary = await aiService.generateBookmarkSummary(
  bookTitle: '原则',
  excerpt: '痛苦+反思=进步...',
);
```

**功能特性：**
- ✨ 一句话精华提炼
- 💡 核心观点提取（3-5点）
- 🎯 个人感悟启发
- 🏷️ 智能标签推荐

### 2. 阅读习惯 AI 分析

基于阅读数据生成个性化阅读分析报告：

```dart
final analysis = await aiService.analyzeReadingHabits(stats);
```

**分析维度：**
- 📊 阅读模式识别（晨读/夜读/碎片化）
- ⚡ 专注度评估
- 📈 习惯养成建议（3条）
- 🎯 下月阅读目标推荐

### 3. 智能书摘搜索引擎

支持全文检索和相关度排序：

```dart
final results = await aiService.searchBookmarks(
  '成长',
  allBookmarks,
);
```

**搜索特性：**
- 🔍 关键词匹配高亮
- 📊 相关度百分比显示
- 🏷️ 标签快捷搜索
- ⭐ 热门搜索推荐

### 4. 精美书摘卡片分享

一键生成精美分享卡片：

```dart
final imageData = await CardGeneratorService.generateBookmarkCard(
  bookmark: bookmark,
  template: CardTemplate.elegant,
);
```

**卡片模板：**
- 🎨 极简风格（Minimalist）
- 🌟 优雅风格（Elegant）
- ✨ 创意风格（Creative）
- 💬 名言风格（Quote）

## ✨ 架构改进

### 1. Delta 格式笔记存储与跨平台渲染

笔记系统采用类 Quill 的 Delta 格式存储，支持富文本编辑和跨平台一致渲染：

```dart
// Delta 操作示例
[
  {"insert": "Hello "},
  {"insert": "World", "attributes": {"bold": true}},
  {"insert": "\n", "attributes": {"color": "red"}}
]
```

**特性：**
- 支持插入、删除、保留、格式化操作
- 可渲染为 HTML、Markdown 或原生 Widget
- 版本化操作历史，支持冲突合并
- 各平台独立渲染，保持一致性

### 2. 数据分层架构

采用 **本地优先** + **云端历史** 的双层架构：

```
┌─────────────────────────────────────────────────────────────┐
│                        UI Layer                               │
│                    (State Management)                         │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│                     LocalDataManager                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │SharedPrefs   │  │Cache (Mem)   │  │Pending Ops   │        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│                      SyncService (CRDT/LWW)                   │
│  ┌─────────────────────────────────────────────────────────┐│
│  │Conflict Resolution │Vector Clocks │Transaction Logic    ││
│  └─────────────────────────────────────────────────────────┘│
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│                         Firebase                              │
│  ┌──────────┐  ┌──────────┐  ┌─────────┐  ┌──────────────┐  │
│  │Auth      │  │Firestore │  │Storage  │  │Version Hist. │  │
│  └──────────┘  └──────────┘  └─────────┘  └──────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

**优势：**
- 极速本地响应（无需等待网络）
- 离线操作完整支持
- 云端作为单一可信源
- 变更历史可审计可追溯

### 3. OCR 图像预处理管道

书摘截图识别前的图像处理流水线：

```
原始图像 → 倾斜校正 → 内容裁剪 → 尺寸归一化 → 对比度增强
          ↓
    Otsu二值化 ← 自适应中值去噪 ← 反锐化掩模
          ↓
    预处理完成图像
```

**处理技术：**
- **Hough 变换** 检测并校正图像倾斜
- **Otsu 算法** 自适应二值化阈值
- **自适应中值滤波** 去除椒盐噪声
- **Unsharp Mask** 增强边缘锐度

### 4. CRDT / LWW 离线同步策略

**冲突解决策略：**

| 策略 | 说明 | 适用场景 |
|------|------|----------|
| **Last-Write-Wins** | 时间戳最新的操作胜出 | 大多数业务场景 |
| **Merge** | 向量时钟检测并发，智能合并内容 | 笔记、书摘编辑 |
| **Client Wins** | 客户端强制覆盖服务端 | 用户主动选择 |
| **Server Wins** | 服务端版本优先 | 管理员操作 |

**向量时钟机制：**
```dart
// 设备A和设备B的并发修改
Device A: {A: 2, B: 1}
Device B: {A: 1, B: 2}
→ 检测为并发，触发合并策略
```

## 📦 核心功能

### 📚 书籍管理
- 上传电子书（支持 epub、pdf、txt 格式）
- 书籍元数据管理（标题、作者、描述等）
- 阅读进度同步与展示
- 封面图片显示

### 📝 笔记标注
- Delta 格式富文本笔记
- 高亮文本与颜色标记
- 按书籍/页码组织
- 离线编辑自动同步

### 📖 阅读进度同步
- 跨设备实时同步阅读位置
- LWW 策略解决进度冲突
- 设备信息记录
- 百分比进度展示

### 🔖 书摘管理
- 创建书摘并添加标签
- 图片 OCR 预处理支持
- 搜索和筛选功能
- 导出与分享

## 🏗️ 项目结构

```
lib/
├── main.dart                          # 应用入口
├── models/                            # 数据模型
│   ├── book.dart
│   ├── note.dart
│   ├── reading_progress.dart
│   ├── bookmark.dart
│   └── reading_stats.dart             # 阅读统计数据模型
├── services/                          # 服务层
│   ├── firebase_service.dart          # Firebase 原始服务
│   ├── local_storage_service.dart     # 本地存储与数据管理器
│   ├── sync_service.dart              # 同步引擎（CRDT/LWW）
│   ├── ai_service.dart                # AI 智能服务（摘要/搜索/OCR）
│   └── card_generator_service.dart    # 书摘卡片生成器
├── providers/                         # 状态管理
│   ├── auth_provider.dart
│   ├── sync_provider.dart             # 同步状态管理
│   ├── book_provider.dart
│   ├── note_provider.dart
│   ├── progress_provider.dart
│   ├── bookmark_provider.dart
│   ├── ai_provider.dart               # AI 状态管理
│   └── stats_provider.dart            # 统计状态管理
├── utils/                             # 工具类
│   ├── delta_format.dart              # Delta 格式与渲染器
│   └── image_preprocessor.dart        # OCR 图像预处理
├── widgets/                           # 通用组件
│   └── reading_charts.dart            # 阅读统计图表组件
└── screens/                           # 界面层
    ├── login_screen.dart
    ├── home_screen.dart
    ├── reader_screen.dart
    ├── bookmarks_screen.dart
    ├── add_book_screen.dart
    ├── stats_screen.dart              # 阅读统计页面
    ├── bookmark_search_screen.dart    # 书摘搜索页面
    └── bookmark_card_preview_screen.dart # 书摘卡片预览
```

## 🚀 快速开始

### 前置要求

- Flutter SDK 3.0+
- Dart SDK 3.0+
- Firebase 项目配置

### 安装依赖

```bash
flutter pub get
```

### Firebase 配置

1. 在 Firebase 控制台创建项目
2. 启用 Email/Password 认证
3. 创建 Firestore 数据库
4. 配置安全规则：

```rules
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /{collection}/{document} {
      allow read, write: if request.auth != null 
        && request.auth.uid == resource.data.userId;
    }
  }
}
```

5. 更新 `lib/main.dart` 中的 Firebase 配置

### 运行应用

```bash
# Android
flutter run

# Web
flutter run -d chrome

# iOS
flutter run -d ios
```

## ⚙️ 同步机制详解

### 操作队列

```dart
// 离线操作入队
await syncService.queueOperation(SyncOperation(
  type: OperationType.update,
  entityType: 'note',
  entityId: note.id,
  data: note.toMap(),
  timestamp: DateTime.now(),
  vectorClock: vectorClock,
));

// 网络恢复后自动同步
// 支持断点续传和幂等操作
```

### 自动同步触发点

- ✅ 网络连接恢复时
- ✅ 每 5 分钟自动轮询
- ✅ 用户手动触发
- ✅ 应用进入前台时

### 冲突检测与解决

```dart
// 1. 获取服务端向量时钟
final serverVc = VectorClock.fromMap(serverData['vectorClock']);

// 2. 检测因果关系
if (clientVc.happensBefore(serverVc)) {
  // 客户端变更已包含在服务端，跳过
} else if (clientVc.isConcurrent(serverVc)) {
  // 并发修改，执行合并策略
  final merged = await resolveConflict(clientData, serverData);
} else {
  // 客户端更新，直接写入
}
```

## 🧪 测试建议

### 离线同步测试

1. 断网状态下创建笔记
2. 修改阅读进度
3. 添加新书摘
4. 恢复网络，验证数据正确同步

### 冲突解决测试

1. 设备 A 和 B 同时打开同一本书
2. 在两台设备上分别进行不同修改
3. 验证 LWW 策略正确应用
4. 验证最终状态一致

### OCR 预处理测试

1. 测试不同角度倾斜图像校正
2. 测试低光照图像增强效果
3. 验证噪声去除有效性
4. 对比预处理前后 OCR 识别率

## 📄 许可证

MIT License
