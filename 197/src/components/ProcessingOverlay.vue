<template>
  <div class="processing-overlay">
    <div class="processing-content">
      <div class="processing-icon">⚙️</div>
      <h2 class="processing-title">{{ store.processingText || '正在处理...' }}</h2>
      <p class="processing-text">请耐心等待，视频处理需要一些时间</p>
      <div class="progress-bar">
        <div 
          class="progress-bar-fill" 
          :style="{ width: (store.processingProgress * 100).toFixed(0) + '%' }"
        ></div>
      </div>
      <p class="processing-percent">{{ (store.processingProgress * 100).toFixed(0) }}%</p>
    </div>
  </div>
</template>

<script setup>
import { useEditorStore } from '../stores/editor'

const store = useEditorStore()
</script>

<style scoped>
.processing-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.8);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9998;
}

.processing-content {
  text-align: center;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 16px;
  padding: 48px 56px;
  box-shadow: var(--shadow);
  min-width: 360px;
}

.processing-icon {
  font-size: 56px;
  margin-bottom: 20px;
  animation: rotate 2s linear infinite;
}

@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.processing-title {
  font-size: 20px;
  font-weight: 600;
  margin-bottom: 12px;
  color: var(--text-primary);
}

.processing-text {
  font-size: 14px;
  color: var(--text-secondary);
  margin-bottom: 24px;
}

.processing-percent {
  margin-top: 12px;
  font-size: 14px;
  font-weight: 600;
  color: var(--accent-secondary);
}
</style>
