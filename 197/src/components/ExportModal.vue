<template>
  <div class="modal-overlay" @click.self="close">
    <div class="modal-content">
      <div class="modal-header">
        <h2>📤 导出视频</h2>
        <button class="close-btn" @click="close">×</button>
      </div>

      <div class="modal-body">
        <div v-if="!exportStarted" class="export-settings">
          <div class="settings-section">
            <h3 class="section-title">基本设置</h3>
            
            <div class="form-group">
              <label>输出文件名</label>
              <input 
                type="text" 
                class="form-input"
                v-model="outputName"
                placeholder="my_video"
              />
            </div>

            <div class="form-group">
              <label>输出格式</label>
              <select class="form-input" v-model="outputFormat">
                <option value="mp4">MP4 (推荐)</option>
                <option value="webm">WebM</option>
              </select>
            </div>

            <div class="form-row">
              <div class="form-group">
                <label>分辨率</label>
                <select class="form-input" v-model="resolution">
                  <option value="1920x1080">1920 × 1080 (1080p)</option>
                  <option value="1280x720">1280 × 720 (720p)</option>
                  <option value="854x480">854 × 480 (480p)</option>
                </select>
              </div>
              <div class="form-group">
                <label>帧率</label>
                <select class="form-input" v-model="framerate">
                  <option value="30">30 fps</option>
                  <option value="60">60 fps</option>
                  <option value="24">24 fps</option>
                </select>
              </div>
            </div>

            <div class="form-row">
              <div class="form-group">
                <label>视频质量</label>
                <select class="form-input" v-model="quality">
                  <option value="high">高质量</option>
                  <option value="medium">中等质量</option>
                  <option value="low">低质量</option>
                </select>
              </div>
              <div class="form-group">
                <label>编码速度</label>
                <select class="form-input" v-model="speed">
                  <option value="slow">慢速 (高质量)</option>
                  <option value="medium">中速</option>
                  <option value="fast">快速</option>
                </select>
              </div>
            </div>
          </div>

          <div class="settings-section">
            <h3 class="section-title">包含内容</h3>
            
            <label class="checkbox-item">
              <input type="checkbox" v-model="includeSubtitles" />
              <span>包含字幕</span>
            </label>
            
            <label class="checkbox-item">
              <input type="checkbox" v-model="includeAudio" />
              <span>包含音频</span>
            </label>
            
            <label class="checkbox-item">
              <input type="checkbox" v-model="includeTransitions" />
              <span>应用转场效果</span>
            </label>
          </div>

          <div class="summary-section">
            <h3 class="section-title">项目摘要</h3>
            <div class="summary-grid">
              <div class="summary-item">
                <span class="summary-label">视频片段</span>
                <span class="summary-value">{{ store.videoTrack.length }}</span>
              </div>
              <div class="summary-item">
                <span class="summary-label">音频片段</span>
                <span class="summary-value">{{ store.audioTrack.length }}</span>
              </div>
              <div class="summary-item">
                <span class="summary-label">字幕数量</span>
                <span class="summary-value">{{ store.subtitleTrack.length }}</span>
              </div>
              <div class="summary-item">
                <span class="summary-label">总时长</span>
                <span class="summary-value">{{ formatTimeShort(store.totalDuration) }}</span>
              </div>
            </div>
          </div>
        </div>

        <div v-else class="export-progress">
          <div class="progress-icon">
            {{ exportCompleted ? '✅' : '⚙️' }}
          </div>
          <h3 class="progress-title">
            {{ exportCompleted ? '导出完成！' : '正在导出视频...' }}
          </h3>
          <p class="progress-text">
            {{ exportCompleted ? '您的视频已经准备好下载了' : '正在处理视频，请耐心等待' }}
          </p>
          
          <div class="progress-bar large" v-if="!exportCompleted">
            <div 
              class="progress-bar-fill" 
              :style="{ width: (exportProgress * 100).toFixed(0) + '%' }"
            ></div>
          </div>
          
          <p class="progress-percent" v-if="!exportCompleted">
            {{ (exportProgress * 100).toFixed(0) }}%
          </p>

          <div class="export-actions" v-if="exportCompleted">
            <button class="btn btn-success" @click="downloadVideo">
              📥 下载视频
            </button>
            <button class="btn" @click="resetExport">
              🔄 重新导出
            </button>
          </div>

          <div class="export-log" v-if="exportLog.length > 0">
            <h4>处理日志</h4>
            <div class="log-content">
              <p v-for="(log, i) in exportLog" :key="i">{{ log }}</p>
            </div>
          </div>
        </div>
      </div>

      <div class="modal-footer" v-if="!exportStarted">
        <button class="btn" @click="close">取消</button>
        <button 
          class="btn btn-primary" 
          @click="startExport"
          :disabled="store.videoTrack.length === 0"
        >
          🚀 开始导出
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useEditorStore } from '../stores/editor'
import { ffmpegService } from '../utils/ffmpeg'
import { formatTimeShort } from '../utils/format'

const emit = defineEmits(['close'])

const store = useEditorStore()

const outputName = ref('my_edited_video')
const outputFormat = ref('mp4')
const resolution = ref('1920x1080')
const framerate = ref('30')
const quality = ref('high')
const speed = ref('medium')
const includeSubtitles = ref(true)
const includeAudio = ref(true)
const includeTransitions = ref(true)

const exportStarted = ref(false)
const exportCompleted = ref(false)
const exportProgress = ref(0)
const exportLog = ref([])
const exportedBlob = ref(null)

function close() {
  if (!exportStarted || exportCompleted) {
    emit('close')
  } else {
    if (confirm('导出正在进行中，确定要取消吗？')) {
      emit('close')
    }
  }
}

function addLog(message) {
  const time = new Date().toLocaleTimeString()
  exportLog.value.push(`[${time}] ${message}`)
}

async function startExport() {
  if (store.videoTrack.length === 0) {
    alert('请先添加视频片段到时间轴')
    return
  }

  exportStarted.value = true
  exportCompleted.value = false
  exportProgress.value = 0
  exportLog.value = []

  try {
    addLog('开始导出项目...')
    addLog(`视频片段: ${store.videoTrack.length} 个`)
    addLog(`总时长: ${formatTimeShort(store.totalDuration)}`)

    let videoBlob = null

    const clips = store.sortedVideoClips

    if (clips.length === 1) {
      addLog('正在处理单个视频片段...')
      
      const clip = clips[0]
      videoBlob = await ffmpegService.trimVideo(
        clip.file,
        clip.trimStart,
        clip.trimEnd,
        (p) => {
          exportProgress.value = 0.3 + (p.progress || 0) * 0.4
          addLog(`处理中: ${((p.progress || 0) * 100).toFixed(0)}%`)
        }
      )
    } else {
      addLog('正在拼接多个视频片段...')
      
      const videoFiles = clips.map(c => {
        if (c.trimStart > 0 || c.trimEnd < c.originalDuration) {
          return new File([c.file.slice(0)], c.file.name, { type: c.file.type })
        }
        return c.file
      })
      
      videoBlob = await ffmpegService.concatVideos(
        videoFiles,
        (p) => {
          exportProgress.value = 0.3 + (p.progress || 0) * 0.4
          addLog(`拼接中: ${((p.progress || 0) * 100).toFixed(0)}%`)
        }
      )
    }

    exportProgress.value = 0.7

    if (includeSubtitles.value && store.subtitleTrack.length > 0) {
      addLog('正在添加字幕...')
      
      const subtitles = [...store.subtitleTrack].sort((a, b) => a.startTime - b.startTime)
      
      const subtitleFile = new File([], 'video.mp4', { type: 'video/mp4' })
      Object.defineProperty(subtitleFile, 'name', { value: 'video.mp4' })
      
      videoBlob = await ffmpegService.addSubtitles(
        new File([videoBlob], 'temp_video.mp4', { type: 'video/mp4' }),
        subtitles,
        (p) => {
          exportProgress.value = 0.8 + (p.progress || 0) * 0.15
          addLog(`字幕处理中: ${((p.progress || 0) * 100).toFixed(0)}%`)
        }
      )
    }

    if (store.backgroundMusic && includeAudio.value) {
      addLog('正在添加背景音乐...')
      
      videoBlob = await ffmpegService.replaceAudio(
        new File([videoBlob], 'temp_video.mp4', { type: 'video/mp4' }),
        store.backgroundMusic.file,
        0,
        (p) => {
          exportProgress.value = 0.95 + (p.progress || 0) * 0.05
          addLog(`音频处理中: ${((p.progress || 0) * 100).toFixed(0)}%`)
        }
      )
    }

    exportProgress.value = 1
    exportedBlob.value = videoBlob
    exportCompleted.value = true
    
    addLog('✅ 导出完成！')
    addLog(`文件大小: ${(videoBlob.size / 1024 / 1024).toFixed(2)} MB`)

  } catch (error) {
    console.error('导出失败:', error)
    addLog(`❌ 导出失败: ${error.message}`)
    alert('导出失败: ' + error.message)
    exportStarted.value = false
  }
}

function downloadVideo() {
  if (!exportedBlob.value) return
  
  const url = URL.createObjectURL(exportedBlob.value)
  const a = document.createElement('a')
  a.href = url
  a.download = `${outputName.value}.${outputFormat.value}`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
  
  addLog('📥 视频已开始下载')
}

function resetExport() {
  exportStarted.value = false
  exportCompleted.value = false
  exportProgress.value = 0
  exportLog.value = []
  exportedBlob.value = null
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.8);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10000;
}

.modal-content {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 16px;
  width: 90%;
  max-width: 560px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
}

.modal-header {
  padding: 20px 24px;
  background: var(--bg-tertiary);
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.modal-header h2 {
  font-size: 18px;
  font-weight: 600;
}

.close-btn {
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: var(--text-muted);
  font-size: 24px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.close-btn:hover {
  background: var(--bg-clip);
  color: var(--text-primary);
}

.modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

.modal-footer {
  padding: 16px 24px;
  background: var(--bg-tertiary);
  border-top: 1px solid var(--border-color);
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.settings-section {
  margin-bottom: 24px;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 16px;
  color: var(--text-primary);
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border-color);
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 16px;
}

.form-group label {
  font-size: 12px;
  color: var(--text-secondary);
}

.form-input {
  padding: 10px 14px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  color: var(--text-primary);
  font-size: 14px;
  transition: border-color 0.2s;
}

.form-input:focus {
  border-color: var(--accent-primary);
  outline: none;
}

.form-row {
  display: flex;
  gap: 16px;
}

.form-row .form-group {
  flex: 1;
}

.checkbox-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 0;
  cursor: pointer;
  font-size: 14px;
}

.checkbox-item input[type="checkbox"] {
  width: 18px;
  height: 18px;
  accent-color: var(--accent-primary);
  cursor: pointer;
}

.summary-section {
  padding: 16px;
  background: var(--bg-tertiary);
  border-radius: 12px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.summary-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.summary-label {
  font-size: 12px;
  color: var(--text-muted);
}

.summary-value {
  font-size: 14px;
  font-weight: 600;
  color: var(--accent-secondary);
}

.export-progress {
  text-align: center;
  padding: 20px 0;
}

.progress-icon {
  font-size: 64px;
  margin-bottom: 20px;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.1); }
}

.progress-title {
  font-size: 20px;
  font-weight: 600;
  margin-bottom: 8px;
}

.progress-text {
  font-size: 14px;
  color: var(--text-muted);
  margin-bottom: 24px;
}

.progress-bar.large {
  height: 12px;
  margin-bottom: 12px;
}

.progress-percent {
  font-size: 18px;
  font-weight: 700;
  color: var(--accent-secondary);
}

.export-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
  margin-top: 24px;
}

.export-log {
  margin-top: 24px;
  text-align: left;
}

.export-log h4 {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 12px;
  color: var(--text-secondary);
}

.log-content {
  background: var(--bg-tertiary);
  border-radius: 8px;
  padding: 12px;
  max-height: 150px;
  overflow-y: auto;
  font-family: 'Courier New', monospace;
  font-size: 11px;
  color: var(--text-muted);
}

.log-content p {
  margin-bottom: 4px;
}

.export-actions .btn {
  padding: 12px 24px;
  font-size: 14px;
}
</style>
