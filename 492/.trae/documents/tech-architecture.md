## 1. 架构设计

```mermaid
flowchart TB
    subgraph "前端层"
        "A[React 组件层]" --> "B[Zustand 状态管理]"
        "B" --> "C[Canvas 渲染引擎]"
        "C" --> "D[CSS3 动画层]"
    end
    subgraph "组件层"
        "E[LED预览组件]" --> "C"
        "F[控制面板组件]" --> "B"
        "G[ColorPicker组件]" --> "F"
        "H[背景特效引擎]" --> "C"
    end
```

## 2. 技术说明

- **前端框架**：React@18 + TypeScript + Vite
- **样式方案**：Tailwind CSS@3
- **状态管理**：Zustand
- **渲染引擎**：Canvas 2D API（LED字幕渲染 + 背景特效）
- **动画方案**：CSS3 @keyframes（滚动动画）+ requestAnimationFrame（Canvas特效）
- **颜色选择**：自研ColorPicker组件（基于Canvas色相环+亮度/饱和度面板）
- **图标库**：lucide-react
- **初始化工具**：vite-init (react-ts模板)
- **后端**：无（纯前端应用）
- **数据库**：无（状态仅存在于内存，可选localStorage持久化）

## 3. 路由定义

| 路由 | 用途 |
|------|------|
| / | 主页面，包含LED预览区和控制面板 |

## 4. 核心组件架构

### 4.1 组件树

```
App
├── LEDPreview          // Canvas实时预览区
│   ├── LEDCanvas       // Canvas渲染层（字幕+特效）
│   └── FullscreenToggle // 全屏切换按钮
├── ControlPanel        // 右侧控制面板
│   ├── TextEditor      // 多行文字编辑
│   ├── FontSettings    // 字体选择
│   ├── ColorSettings   // 颜色配置（含ColorPicker）
│   ├── ScrollSettings  // 滚动方向/速度/模式
│   ├── EffectSettings  // 背景特效选择
│   └── PresetTemplates // 预设模板
└── ColorPicker         // 颜色选择器弹窗
```

### 4.2 状态模型（Zustand Store）

```typescript
interface LEDStore {
  lines: LineConfig[]
  font: FontConfig
  scroll: ScrollConfig
  background: BackgroundConfig
  activeLineIndex: number
  
  addLine: () => void
  removeLine: (index: number) => void
  updateLine: (index: number, text: string) => void
  setFont: (font: Partial<FontConfig>) => void
  setScroll: (scroll: Partial<ScrollConfig>) => void
  setBackground: (bg: Partial<BackgroundConfig>) => void
  applyPreset: (preset: PresetConfig) => void
}

interface LineConfig {
  id: string
  text: string
  color: string
}

interface FontConfig {
  family: string
  size: number
  weight: number
  glow: boolean
  glowIntensity: number
}

interface ScrollConfig {
  direction: 'left' | 'right' | 'up' | 'down'
  speed: number
  mode: 'continuous' | 'once'
}

interface BackgroundConfig {
  color: string
  effect: 'none' | 'particles' | 'matrix' | 'neon-glow' | 'starfield'
  effectIntensity: number
  effectColor: string
}
```

### 4.3 Canvas渲染流程

```mermaid
flowchart LR
    "A[requestAnimationFrame循环]" --> "B[清除Canvas]"
    "B" --> "C[绘制背景特效]"
    "C" --> "D[计算字幕位置(根据滚动偏移)]"
    "D" --> "E[绘制字幕文字+发光效果]"
    "E" --> "F[更新滚动偏移量]"
    "F" --> "A"
```

## 5. 数据模型

不适用（纯前端应用，无数据库）。

## 6. 性能优化策略

- Canvas渲染使用requestAnimationFrame，确保60fps
- 背景特效粒子数量根据屏幕尺寸自适应
- 字幕文字预渲染到离屏Canvas，减少每帧重绘开销
- 控制面板参数变更使用requestAnimationFrame去抖动，避免频繁重绘
- CSS3动画用于辅助UI过渡效果，Canvas专注核心渲染
