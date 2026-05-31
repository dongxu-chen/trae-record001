# SVG动画编辑器 - 技术架构文档

## 1. 架构设计

```mermaid
graph TB
    subgraph "前端应用层"
        A["App 主应用
           - 布局管理
           - 全局状态
           - 主题系统
           - 快捷键"
    end
    
    subgraph "编辑器核心层
        B1["SVG画布模块
            - Snap.svg 渲染
            - 元素拖拽变换
            - 选择/多选
            - 变换控制"]
        B2["时间轴模块
            - 轨道管理
            - 关键帧系统
            - 播放控制
            - GSAP 动画引擎"]
        B3["属性编辑模块
            - 元素属性面板
            - 动画参数配置
            - 缓动曲线编辑"]
    end
    
    subgraph "工具层"
        C1["动画系统
            - 关键帧动画
            - 路径动画
            - 变形动画
            - MorphSVG 变形"]
        C2["导出系统
            - SVG 导出
            - JS 代码生成
            - 项目序列化"]
    end
    
    subgraph "状态管理层"
        D["Zustand 状态管理
           - 项目数据
           - 元素数据
           - 动画数据
           - 播放状态"
    end
    
    A --> B1
    A --> B2
    A --> B3
    B2 --> C1
    B2 --> C2
    B1 --> D
    B2 --> D
    B3 --> D
```

## 2. 技术描述

### 2.1 技术栈

| 层级 | 技术选型 | 版本 | 用途 |
|------|---------|------|------|
| 前端框架 | React | 18.x | UI 组件化开发 |
| 构建工具 | Vite | 5.x | 快速开发构建 |
| 样式方案 | Tailwind CSS | 3.x | 原子化CSS |
| SVG操作 | Snap.svg | 0.5.1 | SVG元素操作 |
| 动画引擎 | GSAP | 3.x | 高性能动画 |
| 状态管理 | Zustand | 4.x | 全局状态 |
| 图标库 | Lucide React | 0.3.x | 图标组件 |
| 语言 | TypeScript | 5.x | 类型安全 |

### 2.2 核心依赖

- **Snap.svg: 用于SVG元素的创建、选择、变换操作
- **GSAP (Greensock Animation Platform**:
  - `gsap`: 核心动画库
  - `MorphSVGPlugin`: 路径变形动画
  - `MotionPathPlugin`: 路径运动动画
  - `EasePack`: 缓动曲线
- **Zustand**: 轻量级状态管理，存储项目、元素、动画状态
- **Lucide React**: 统一的图标系统

## 3. 目录结构

```
src/
├── components/
│   ├── editor/
│   │   ├── Canvas.tsx          # SVG画布组件
│   │   ├── ElementToolbar.tsx  # 元素工具栏
│   │   └── TransformControls.tsx
│   ├── timeline/
│   │   ├── Timeline.tsx        # 时间轴主组件
│   │   ├── Track.tsx           # 轨道组件
│   │   ├── Keyframe.tsx        # 关键帧组件
│   │   └── PlayControls.tsx
│   ├── panels/
│   │   ├── ElementPanel.tsx   # 元素/图层面板
│   │   ├── PropertyPanel.tsx   # 属性面板
│   │   └── EasingEditor.tsx # 缓动曲线编辑器
│   └── common/
│       ├── Button.tsx
│       └── Input.tsx
│       └── Modal.tsx
├── store/
│   ├── useProjectStore.ts      # 项目状态
│   ├── useEditorStore.ts     # 编辑器状态
│   └── useAnimationStore.ts # 动画状态
├── hooks/
│   ├── useSnapSVG.ts           # Snap.svg hook
│   ├── useGSAP.ts
│   └── useKeyframes.ts
├── utils/
│   ├── svgExporter.ts        # SVG导出
│   ├── jsExporter.ts         # JS导出
│   └── easingPresets.ts
├── types/
│   └── index.ts
│   └── animation.ts
│   └── elements.ts
└── App.tsx
└── main.tsx
```

## 4. 数据模型

### 4.1 核心类型定义

```typescript
// SVG元素类型
interface SVGElementData {
  id: string;
  type: 'rect' | 'circle' | 'ellipse' | 'path' | 'line' | 'polygon' | 'text' | 'group';
  name: string;
  visible: boolean;
  locked: boolean;
  attributes: Record<string, any>;
  transform: {
    x: number;
    y: number;
    rotation: number;
    scaleX: number;
    scaleY: number;
  };
  animations: string[];
}

// 动画轨道
interface AnimationTrack {
  id: string;
  elementId: string;
  property: 'x' | 'y' | 'rotation' | 'scale' | 'opacity' | 'path' | 'morph';
  keyframes: Keyframe[];
  type: 'keyframes' | 'motionPath' | 'morph';
  easing: string;
}

// 关键帧
interface Keyframe {
  id: string;
  time: number;
  value: any;
  easing?: string;
}

// 路径动画
interface MotionPathConfig {
  path: string;
  align?: string;
  alignToSelf?: boolean;
  start?: number;
  end?: number;
}

// 项目数据
interface Project {
  id: string;
  name: string;
  width: number;
  height: number;
  duration: number;
  fps: number;
  elements: SVGElementData[];
  tracks: AnimationTrack[];
  createdAt: number;
}
```

## 5. 核心功能实现方案

### 5.1 SVG画布系统

- 使用Snap.svg操作SVG DOM
- 实现元素选择系统：点击选择、框选多选
- 变换控制：拖拽移动、缩放、旋转控制点
- 网格对齐：智能对齐辅助线

### 5.2 时间轴系统

- 多轨道显示：每个属性一个轨道
- 关键帧编辑：添加、删除、拖拽
- 播放控制：播放、暂停、逐帧、循环
- 时间缩放：缩放时间轴视图

### 5.3 动画系统

- **关键帧动画**: GSAP Timeline 构建
- **路径动画**: MotionPathPlugin
- **变形动画**: MorphSVGPlugin
- **缓动系统**: 预设 + 自定义贝塞尔

### 5.4 导出系统

- **SVG导出**: 内联SMIL动画
- **JS导出**: GSAP代码生成
- 独立运行：无需编辑器外可运行

## 6. 导出格式定义

### 6.1 快捷键

| 快捷键 | 功能 |
|--------|------|
| Space | 播放/暂停 |
| Ctrl+Z | 撤销 |
| Ctrl+S | 保存 |
| Delete | 删除选中 |
| Ctrl+A | 全选 |
| Arrow Keys | 微移元素 |
