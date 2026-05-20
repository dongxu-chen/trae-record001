# 3D产品展示看板

基于 React + Three.js 的交互式3D产品展示应用。

## 功能特性

- ✅ 加载外部glTF格式3D模型
- ✅ 轨道控制器（旋转/缩放/平移）
- ✅ 材质属性调节（金属度、粗糙度、颜色）
- ✅ 材质预设（抛光金属、拉丝金属、哑光塑料等）
- ✅ 背景颜色切换
- ✅ 相机视角重置
- ✅ 响应式控制面板

## 技术栈

- React 18
- Vite
- Three.js
- @react-three/fiber
- @react-three/drei

## 快速开始

### 安装依赖

```bash
npm install
```

### 启动开发服务器

```bash
npm run dev
```

### 构建生产版本

```bash
npm run build
```

## 使用说明

### 相机控制
- **左键拖动**：旋转模型
- **右键拖动**：平移视角
- **滚轮**：缩放视图
- **重置视角按钮**：恢复初始相机位置

### 材质调节
1. **材质预设**：快速应用预设材质效果
2. **颜色选择器**：自定义模型颜色
3. **金属度滑块**：调节材质金属质感
4. **粗糙度滑块**：调节材质表面光滑度
5. **环境光强度**：调节环境光照效果

### 背景设置
- 从预设颜色中选择背景
- 使用自定义颜色选择器

## 项目结构

```
src/
├── components/
│   ├── Model.jsx        # 3D模型加载组件
│   ├── Environment.jsx  # 环境效果组件
│   └── ControlPanel.jsx # 控制面板组件
├── App.jsx              # 主应用组件
├── main.jsx             # 应用入口
└── index.css            # 全局样式
```

## 自定义模型

如需加载自定义glTF模型，请修改 `src/components/Model.jsx` 中的 `modelUrl`：

```javascript
setModelUrl('/path/to/your/model.gltf')
```

## 许可证

MIT
