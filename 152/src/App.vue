<template>
  <div class="app-container">
    <header class="app-header">
      <h1>🎨 CanvasKit 矢量编辑器</h1>
      <div class="header-badges">
        <span class="badge">GPU 加速</span>
        <span class="badge">Skia 渲染</span>
        <span class="badge">WebAssembly</span>
      </div>
    </header>
    <CanvasKitEditor />
  </div>
</template>

<script setup>
import CanvasKitEditor from './components/CanvasKitEditor.vue'
</script>

<style scoped>
.app-container {
  width: 100vw;
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #1a1a2e;
}

.app-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 24px;
  background: #0f3460;
  border-bottom: 1px solid #16213e;
}

.app-header h1 {
  margin: 0;
  font-size: 20px;
  color: #fff;
  font-weight: 600;
}

.header-badges {
  display: flex;
  gap: 8px;
}

.badge {
  padding: 4px 12px;
  background: #e94560;
  color: #fff;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 500;
}
</style>
