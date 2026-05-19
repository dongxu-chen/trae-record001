# TensorFlow Lite 端侧推理实现说明

## 📋 概述

本项目将 MediaPipe 手势检测重构为使用 TensorFlow Lite 进行端侧推理，实现更低延迟和离线支持。

## 🎯 核心目标

1. **低延迟推理**: 目标 < 30ms/帧
2. **离线支持**: 模型本地缓存，无需网络连接
3. **移动端优化**: WebAssembly / WebGL 加速
4. **向后兼容**: 保留 MediaPipe 作为降级方案

## 📁 文件结构

```
├── index-tflite.html          # TFLite 版本主页面
├── app-tflite.js              # 主应用逻辑（TFLite版本）
├── tfjs-hand-detection.js     # TF.js 手势检测封装
├── tflite-engine.js           # TFLite 推理引擎（基础）
├── hand-detection.js          # 手部检测完整管道
├── style.css                  # 样式文件
└── TFLITE_IMPLEMENTATION.md   # 本文档
```

## 🔧 技术实现

### 1. 推理引擎架构

**双引擎设计**:
- **首选**: TensorFlow.js + MediaPipe Hands 模型（WebGL 加速）
- **降级**: MediaPipe WASM 版本（兼容性更好）

### 2. 性能优化技术

#### 关键点平滑滤波（一阶低通滤波）
```javascript
const ALPHA = 0.3;  // 滤波系数 [0,1]
smoothed_x = prev_x * (1-ALPHA) + current_x * ALPHA
```
- 消除手部抖动
- 提高绘制流畅度

#### 手势防抖锁定
```javascript
const GESTURE_LOCK_DURATION = 200;  // ms
```
- 200ms内手势状态不切换
- 防止误触和闪烁

#### 推理帧率控制
```javascript
targetFPS = 30;  // 限制推理帧率，降低CPU占用
```

### 3. 离线支持机制

使用 IndexedDB 存储模型文件：
```javascript
class OfflineModelManager {
    async saveModel(modelName, modelUrl);
    async loadModel(modelName);
    async hasModel(modelName);
}
```

**首次加载**:
1. 从 CDN 下载 TF.js Runtime
2. 下载手势检测模型（~10MB）
3. 缓存到本地 IndexedDB
4. 后续启动直接从本地加载

### 4. 坐标系统转换

```
MediaPipe 归一化坐标 [0,1]
       ↓ (反归一化)
   屏幕像素坐标
       ↓ (逆透视投影)
   3D世界坐标
       ↓ (逆旋转)
画布局部坐标系
       ↓ (逆缩放)
   绘制坐标
```

四元数旋转同步：
```javascript
const inverseQuaternion = canvasMesh.quaternion.clone().inverse();
pos.applyQuaternion(inverseQuaternion);
```

## 🎮 手势定义

| 手势 | 手指状态 | 功能 |
|------|---------|------|
| 绘制 | 仅食指伸直 | 画笔轨迹 |
| 擦除 | 全部手指弯曲 | 橡皮擦 |
| 旋转 | 双手食指 | 画布旋转 |
| 撤销 | 食/中/无名指三指左滑 | 撤销上一步 |

## 📊 性能指标

### 目标性能
- **推理时间**: < 30ms/帧
- **端到端延迟**: < 100ms
- **FPS**: 稳定 30+

### 性能监控
```javascript
class PerformanceMonitor {
    recordFrame();           // 记录帧时间
    recordInferenceTime();   // 记录推理时间
    getStats();              // 获取统计数据
    printReport();           // 打印性能报告
}
```

### 后端优先级
1. **WebGL**: GPU 加速，性能最好
2. **WebAssembly**: CPU 优化，中等性能
3. **CPU**: 纯 JavaScript，兼容性最好

## 🌐 浏览器兼容性

| 特性 | Chrome | Firefox | Safari | Edge |
|------|--------|---------|--------|------|
| WebGL 2.0 | ✅ | ✅ | ✅ | ✅ |
| WebAssembly | ✅ | ✅ | ✅ | ✅ |
| IndexedDB | ✅ | ✅ | ✅ | ✅ |
| MediaDevices | ✅ | ✅ | ✅ | ✅ |

**移动端测试**:
- iOS Safari: ✅ 支持
- Android Chrome: ✅ 支持
- WeChat 内置浏览器: ⚠️ 需测试

## 🚀 快速开始

### 运行 TFLite 版本
```bash
# 启动本地服务器
python -m http.server 8000

# 浏览器访问
open http://localhost:8000/index-tflite.html
```

### 验证端侧推理
1. 打开浏览器开发者工具 (F12)
2. 查看 Console 标签页
3. 确认显示:
   ```
   初始化 TensorFlow.js 手部检测...
   使用后端: webgl
   模型加载完成！
   检测耗时: XX.Xms
   ```
4. 断网后刷新页面，确认仍可正常工作

## 🔄 降级机制

当 TF.js 初始化失败时，自动降级到 MediaPipe:

```javascript
try {
    handDetector = new TFJSHandDetector();
    await handDetector.init();
} catch (error) {
    console.log('使用 MediaPipe 作为后备方案');
    await fallbackToMediaPipe();
}
```

## 📈 优化方向

### 短期优化
- [ ] 实现 TFLite WebAssembly 后端
- [ ] 优化输入图像预处理管线
- [ ] 添加 SIMD 指令支持
- [ ] 实现模型量化（INT8）

### 长期优化
- [ ] 集成 MediaPipe Hands TFLite 模型
- [ ] 实现 Web Worker 后台推理
- [ ] 添加神经风格迁移滤镜
- [ ] 实现多人协同白板（WebRTC）

## 🐛 已知问题

1. **Safari 浏览器**: WebGL 后端可能有兼容性问题
2. **移动端**: 性能可能低于桌面端
3. **模型加载**: 首次加载需要网络（约10MB）

## 📚 参考资源

- [TensorFlow.js 官方文档](https://www.tensorflow.org/js)
- [MediaPipe Hands 模型](https://google.github.io/mediapipe/solutions/hands)
- [TFLite Web 运行时](https://www.tensorflow.org/lite/web)
- [Three.js 3D 文档](https://threejs.org/docs/)

## 📄 许可证

本项目基于 MIT 许可证开源。
