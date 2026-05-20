<template>
  <div class="loading-overlay">
    <div class="loading-content">
      <div class="loading-spinner">
        <div class="spinner-ring"></div>
        <div class="spinner-ring"></div>
        <div class="spinner-ring"></div>
      </div>
      <h2 class="loading-title">正在加载 FFmpeg</h2>
      <p class="loading-text">首次加载需要下载 WebAssembly 模块，请耐心等待...</p>
      <div class="progress-bar">
        <div class="progress-bar-fill" :style="{ width: '100%' }"></div>
      </div>
      <p class="loading-hint">💡 提示：FFmpeg 运行在浏览器中，您的视频文件不会上传到服务器</p>
    </div>
  </div>
</template>

<script setup>
</script>

<style scoped>
.loading-overlay {
  position: fixed;
  inset: 0;
  background: var(--bg-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
}

.loading-content {
  text-align: center;
  max-width: 480px;
  padding: 40px;
}

.loading-spinner {
  position: relative;
  width: 80px;
  height: 80px;
  margin: 0 auto 30px;
}

.spinner-ring {
  position: absolute;
  inset: 0;
  border: 3px solid transparent;
  border-top-color: var(--accent-primary);
  border-radius: 50%;
  animation: spin 1.2s linear infinite;
}

.spinner-ring:nth-child(2) {
  inset: 8px;
  border-top-color: var(--accent-secondary);
  animation-delay: 0.15s;
}

.spinner-ring:nth-child(3) {
  inset: 16px;
  border-top-color: var(--accent-success);
  animation-delay: 0.3s;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-title {
  font-size: 22px;
  font-weight: 700;
  margin-bottom: 12px;
  color: var(--text-primary);
}

.loading-text {
  font-size: 14px;
  color: var(--text-secondary);
  margin-bottom: 24px;
  line-height: 1.6;
}

.loading-hint {
  margin-top: 20px;
  font-size: 13px;
  color: var(--accent-secondary);
  padding: 12px 16px;
  background: rgba(0, 217, 255, 0.1);
  border-radius: var(--radius);
}
</style>
