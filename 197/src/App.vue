<template>
  <div class="app-container">
    <LoadingOverlay v-if="store.isLoadingFFmpeg" />
    <ProcessingOverlay v-if="store.processing" />

    <header class="app-header">
      <div class="header-left">
        <h1 class="app-title">
          <span class="logo-icon">🎬</span>
          Web视频剪辑工具
        </h1>
        <span class="ffmpeg-status" :class="{ loaded: store.isFFmpegLoaded }">
          <span class="status-dot"></span>
          {{ store.isFFmpegLoaded ? 'FFmpeg 已就绪' : 'FFmpeg 加载中...' }}
        </span>
      </div>
      <div class="header-right">
        <button class="btn" @click="showTemplateLibrary = true">
          <span>📚</span> 模板库
        </button>
        <button class="btn" @click="clearProject">
          <span>🗑️</span> 清空项目
        </button>
        <button class="btn btn-primary" @click="showExportModal = true" :disabled="store.videoTrack.length === 0">
          <span>📤</span> 导出视频
        </button>
      </div>
    </header>

    <main class="app-main">
      <aside class="sidebar-left">
        <MediaLibrary @add-to-track="handleAddToTrack" />
      </aside>

      <section class="main-content">
        <VideoPreview ref="previewRef" />
        <Timeline />
      </section>

      <aside class="sidebar-right">
        <ToolPanel />
      </aside>
    </main>

    <ExportModal v-if="showExportModal" @close="showExportModal = false" />
    
    <div v-if="showTemplateLibrary" class="modal-overlay" @click.self="showTemplateLibrary = false">
      <div class="modal-content template-modal">
        <TemplateLibrary />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useEditorStore } from './stores/editor'
import LoadingOverlay from './components/LoadingOverlay.vue'
import ProcessingOverlay from './components/ProcessingOverlay.vue'
import MediaLibrary from './components/MediaLibrary.vue'
import VideoPreview from './components/VideoPreview.vue'
import Timeline from './components/Timeline.vue'
import ToolPanel from './components/ToolPanel.vue'
import ExportModal from './components/ExportModal.vue'
import TemplateLibrary from './components/TemplateLibrary.vue'

const store = useEditorStore()
const showExportModal = ref(false)
const showTemplateLibrary = ref(false)
const previewRef = ref(null)

onMounted(async () => {
  try {
    await store.loadFFmpeg()
  } catch (error) {
    alert('FFmpeg加载失败，请刷新页面重试。\n\n错误信息: ' + error.message)
  }
})

onBeforeUnmount(() => {
  store.isPlaying = false
})

function handleAddToTrack(mediaItem) {
  if (mediaItem.type === 'video') {
    store.addToVideoTrack(mediaItem)
  } else if (mediaItem.type === 'audio') {
    store.addToAudioTrack(mediaItem)
  }
}

function clearProject() {
  if (confirm('确定要清空所有轨道吗？此操作不可撤销。')) {
    store.clearAll()
  }
}
</script>

<style scoped>
.app-container {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--bg-primary);
}

.app-header {
  height: 60px;
  padding: 0 20px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 20px;
}

.app-title {
  font-size: 18px;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 10px;
  background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.logo-icon {
  font-size: 24px;
  -webkit-text-fill-color: initial;
}

.ffmpeg-status {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--text-muted);
}

.ffmpeg-status.loaded {
  color: var(--accent-success);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--text-muted);
}

.ffmpeg-status.loaded .status-dot {
  background: var(--accent-success);
  box-shadow: 0 0 8px var(--accent-success);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.app-main {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.sidebar-left {
  width: 280px;
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  background: var(--bg-secondary);
  flex-shrink: 0;
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.sidebar-right {
  width: 300px;
  border-left: 1px solid var(--border-color);
  background: var(--bg-secondary);
  flex-shrink: 0;
  overflow-y: auto;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.modal-content {
  background: var(--bg-secondary);
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
  animation: slideUp 0.3s ease;
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.template-modal {
  width: 90vw;
  max-width: 1200px;
  height: 80vh;
}
</style>
