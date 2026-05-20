<template>
  <div class="video-preview">
    <div class="preview-container">
      <div class="video-wrapper">
        <video 
          ref="videoElement"
          class="preview-video"
          :src="currentVideoUrl"
          @timeupdate="handleTimeUpdate"
          @loadedmetadata="handleLoadedMetadata"
          @ended="handleEnded"
          @play="handlePlay"
          @pause="handlePause"
          crossorigin="anonymous"
        ></video>

        <canvas 
          ref="subtitleCanvas" 
          class="subtitle-canvas"
          v-if="hasSubtitleTrack"
        ></canvas>

        <div class="empty-preview" v-if="!currentVideoUrl">
          <span class="empty-icon">🎥</span>
          <p class="empty-text">将视频拖入时间轴开始编辑</p>
          <p class="empty-hint">支持 MP4、WebM、MOV 等格式</p>
        </div>
      </div>

      <div class="preview-controls">
        <div class="time-display">
          <span class="current-time">{{ formatTime(store.currentTime) }}</span>
          <span class="time-separator">/</span>
          <span class="total-time">{{ formatTime(store.totalDuration) }}</span>
        </div>

        <div class="control-buttons">
          <button class="control-btn" @click="skipBackward" title="后退5秒">
            ⏪
          </button>
          <button class="control-btn play-btn" @click="togglePlay" :disabled="!hasVideo">
            {{ store.isPlaying ? '⏸️' : '▶️' }}
          </button>
          <button class="control-btn" @click="skipForward" title="前进5秒">
            ⏩
          </button>
        </div>

        <div class="status-indicators">
          <div class="sync-indicator" :style="{ color: getSyncQualityColor() }" :title="'同步质量: ' + syncQuality.label">
            <span>📡</span>
            <span class="sync-quality">{{ syncQuality.quality }}%</span>
          </div>
          
          <div class="render-stats" v-if="hasSubtitleTrack" title="字幕缓存命中率">
            <span>🎨</span>
            <span class="cache-hit">{{ renderStats.hitRate }}</span>
          </div>
        </div>

        <div class="volume-control">
          <span class="volume-icon">{{ isMuted ? '🔇' : '🔊' }}</span>
          <input 
            type="range" 
            class="volume-slider"
            min="0" 
            max="1" 
            step="0.1" 
            v-model.number="volume"
            @input="handleVolumeChange"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useEditorStore } from '../stores/editor'
import { formatTime } from '../utils/format'
import { SubtitleRenderer } from '../utils/subtitleRenderer'
import { AudioVideoSynchronizer } from '../utils/ptsSync'

const store = useEditorStore()

const videoElement = ref(null)
const subtitleCanvas = ref(null)
const volume = ref(1)
const isMuted = ref(false)
let animationFrameId = null
let subtitleRenderer = null
let audioVideoSync = null
const renderStats = ref({ cached: 0, total: 0, hitRate: '0%' })

const currentVideoUrl = computed(() => {
  const clips = store.sortedVideoClips
  if (clips.length === 0) return null

  const currentTime = store.currentTime
  for (const clip of clips) {
    if (currentTime >= clip.startTime && currentTime < clip.endTime) {
      return clip.url
    }
  }
  return clips[0]?.url || null
})

const currentClip = computed(() => {
  const clips = store.sortedVideoClips
  if (clips.length === 0) return null

  const currentTime = store.currentTime
  for (const clip of clips) {
    if (currentTime >= clip.startTime && currentTime < clip.endTime) {
      return clip
    }
  }
  return null
})

const hasVideo = computed(() => store.videoTrack.length > 0)

const hasSubtitleTrack = computed(() => store.subtitleTrack.length > 0)

const currentSubtitle = computed(() => {
  const currentTime = store.currentTime
  return store.subtitleTrack.find(s => 
    currentTime >= s.startTime && currentTime < s.endTime
  )
})

const syncQuality = ref({ quality: 100, label: 'excellent' })

watch(() => store.isPlaying, (isPlaying) => {
  if (isPlaying) {
    startPlayback()
  } else {
    stopPlayback()
  }
})

watch(() => store.currentTime, (time) => {
  if (currentClip.value && videoElement.value) {
    const videoTime = time - currentClip.value.startTime + currentClip.value.trimStart
    if (Math.abs(videoElement.value.currentTime - videoTime) > 0.1) {
      videoElement.value.currentTime = Math.min(videoTime, currentClip.value.trimEnd)
    }
  }
})

watch(currentVideoUrl, (url) => {
  if (videoElement.value && url) {
    videoElement.value.load()
  }
})

watch(hasSubtitleTrack, async (hasTrack) => {
  if (hasTrack && subtitleCanvas.value) {
    await nextTick()
    initSubtitleRenderer()
  }
})

watch(currentSubtitle, (subtitle) => {
  renderSubtitle(subtitle)
})

watch(() => store.currentTime, (time) => {
  if (currentClip.value && videoElement.value) {
    const videoTime = time - currentClip.value.startTime + currentClip.value.trimStart
    if (Math.abs(videoElement.value.currentTime - videoTime) > 0.1) {
      videoElement.value.currentTime = Math.min(videoTime, currentClip.value.trimEnd)
    }
  }
  if (subtitleRenderer && store.subtitleTrack.length > 0) {
    subtitleRenderer.preloadSubtitles(store.subtitleTrack, time)
  }
})

onMounted(async () => {
  if (videoElement.value) {
    videoElement.value.volume = volume.value
  }
  await nextTick()
  if (hasSubtitleTrack.value && subtitleCanvas.value) {
    initSubtitleRenderer()
  }
  initAudioSync()
})

onBeforeUnmount(() => {
  stopPlayback()
  if (videoElement.value) {
    videoElement.value.pause()
  }
  if (subtitleRenderer) {
    subtitleRenderer.dispose()
    subtitleRenderer = null
  }
  if (audioVideoSync) {
    audioVideoSync.dispose()
    audioVideoSync = null
  }
})

function initSubtitleRenderer() {
  if (!subtitleCanvas.value) return
  
  const rect = subtitleCanvas.value.getBoundingClientRect()
  const width = rect.width
  const height = rect.height
  
  subtitleRenderer = new SubtitleRenderer({
    width,
    height,
    cacheSize: 200,
    poolSize: 30,
  })
  
  subtitleCanvas.value.width = width
  subtitleCanvas.value.height = height
  
  renderSubtitle(currentSubtitle.value)
}

function renderSubtitle(subtitle) {
  if (!subtitleRenderer || !subtitleCanvas.value) return
  
  const result = subtitleRenderer.renderToCanvas(
    subtitleCanvas.value,
    subtitle,
    store.currentTime
  )
  
  if (result) {
    const stats = subtitleRenderer.getStats()
    renderStats.value = {
      cached: stats.render.cachedRenders,
      total: stats.render.totalRenders,
      hitRate: stats.cache.hitRate,
    }
  }
}

function initAudioSync() {
  if (!videoElement.value) return
  
  const audioElement = document.createElement('audio')
  audioElement.style.display = 'none'
  document.body.appendChild(audioElement)
  
  audioVideoSync = new AudioVideoSynchronizer(
    videoElement.value,
    audioElement,
    {
      driftThreshold: 0.03,
      correctionCooldown: 0.5,
      syncMode: 'video_master',
      autoCorrect: true,
      correctionMethod: 'seek',
      onDriftDetected: (stats) => {
        console.warn('[Sync] 音视频漂移检测:', stats)
        updateSyncQuality()
      },
      onCorrectionApplied: (correction, method) => {
        console.log(`[Sync] 已应用${method}校正: ${(correction * 1000).toFixed(1)}ms`)
        updateSyncQuality()
      },
      onSyncLost: (stats) => {
        console.warn('[Sync] 同步丢失:', stats)
      },
      onSyncRestored: (stats) => {
        console.log('[Sync] 同步已恢复:', stats)
        updateSyncQuality()
      },
    }
  )
  
  updateSyncQuality()
  
  const audioClip = store.audioTrack[0]
  if (audioClip && audioClip.url) {
    audioElement.src = audioClip.url
  }
  
  watch(() => store.audioTrack, (track) => {
    const audioClip = track[0]
    if (audioClip && audioClip.url && audioElement) {
      audioElement.src = audioClip.url
    }
  }, { deep: true })
}

function updateSyncQuality() {
  if (audioVideoSync) {
    syncQuality.value = audioVideoSync.getSyncQuality()
  }
}

function getSyncQualityColor() {
  const quality = syncQuality.value.quality
  if (quality >= 90) return '#10b981'
  if (quality >= 75) return '#f59e0b'
  if (quality >= 50) return '#f97316'
  return '#ef4444'
}

function startPlayback() {
  if (videoElement.value && currentVideoUrl.value) {
    const videoTime = store.currentTime - currentClip.value.startTime + currentClip.value.trimStart
    videoElement.value.currentTime = videoTime
    videoElement.value.play().catch(e => console.log('播放失败:', e))
  }
  
  if (audioVideoSync) {
    const audioElement = audioVideoSync.aligner.audioElement
    if (audioElement && audioElement.src) {
      const currentClipData = currentClip.value
      if (currentClipData) {
        const audioTime = store.currentTime
        audioElement.currentTime = Math.max(0, audioTime)
        audioElement.play().catch(e => console.log('音频播放失败:', e))
      }
    }
  }

  function tick() {
    if (store.isPlaying && store.totalDuration > 0) {
      const nextTime = store.currentTime + 1/30
      if (nextTime >= store.totalDuration) {
        store.setCurrentTime(0)
        store.isPlaying = false
      } else {
        store.setCurrentTime(nextTime)
      }
      animationFrameId = requestAnimationFrame(tick)
    }
  }
  tick()
}

function stopPlayback() {
  if (animationFrameId) {
    cancelAnimationFrame(animationFrameId)
    animationFrameId = null
  }
  if (videoElement.value) {
    videoElement.value.pause()
  }
  if (audioVideoSync) {
    const audioElement = audioVideoSync.aligner.audioElement
    if (audioElement) {
      audioElement.pause()
    }
  }
}

function togglePlay() {
  if (!hasVideo.value) return
  store.togglePlay()
}

function handleTimeUpdate() {
}

function handleLoadedMetadata() {
  if (videoElement.value && currentClip.value) {
    const videoTime = store.currentTime - currentClip.value.startTime + currentClip.value.trimStart
    videoElement.value.currentTime = Math.min(videoTime, currentClip.value.trimEnd)
  }
}

function handleEnded() {
  if (currentClip.value) {
    const clips = store.sortedVideoClips
    const currentIndex = clips.findIndex(c => c.id === currentClip.value.id)
    if (currentIndex < clips.length - 1) {
      store.setCurrentTime(clips[currentIndex + 1].startTime)
    } else {
      store.setCurrentTime(0)
      store.isPlaying = false
    }
  }
}

function handlePlay() {
}

function handlePause() {
}

function handleVolumeChange() {
  if (videoElement.value) {
    videoElement.value.volume = volume.value
    videoElement.value.muted = volume.value === 0
    isMuted.value = volume.value === 0
  }
}

function skipBackward() {
  store.setCurrentTime(Math.max(0, store.currentTime - 5))
}

function skipForward() {
  store.setCurrentTime(Math.min(store.totalDuration, store.currentTime + 5))
}

defineExpose({
  videoElement,
})
</script>

<style scoped>
.video-preview {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  background: var(--bg-tertiary);
  overflow: hidden;
}

.preview-container {
  display: flex;
  flex-direction: column;
  width: 100%;
  max-width: 900px;
  gap: 16px;
}

.video-wrapper {
  position: relative;
  width: 100%;
  aspect-ratio: 16/9;
  background: #000;
  border-radius: var(--radius);
  overflow: hidden;
  box-shadow: var(--shadow);
}

.preview-video {
  width: 100%;
  height: 100%;
  object-fit: contain;
  background: #000;
}

.subtitle-canvas {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 5;
}

.empty-preview {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, var(--bg-tertiary), var(--bg-secondary));
}

.empty-icon {
  font-size: 64px;
  margin-bottom: 16px;
  opacity: 0.5;
}

.empty-text {
  font-size: 16px;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.empty-hint {
  font-size: 13px;
  color: var(--text-muted);
}

.preview-controls {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 20px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius);
}

.time-display {
  font-size: 13px;
  font-family: 'Courier New', monospace;
  color: var(--text-secondary);
  min-width: 140px;
}

.current-time {
  color: var(--accent-primary);
  font-weight: 600;
}

.time-separator {
  margin: 0 6px;
  color: var(--text-muted);
}

.control-buttons {
  display: flex;
  align-items: center;
  gap: 12px;
}

.control-btn {
  width: 40px;
  height: 40px;
  border: none;
  border-radius: 50%;
  background: var(--bg-clip);
  color: var(--text-primary);
  font-size: 16px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.control-btn:hover:not(:disabled) {
  background: var(--accent-primary);
  transform: scale(1.1);
}

.control-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.play-btn {
  width: 48px;
  height: 48px;
  background: var(--accent-primary);
  font-size: 18px;
}

.play-btn:hover:not(:disabled) {
  background: #ff5a75;
}

.status-indicators {
  display: flex;
  align-items: center;
  gap: 16px;
  min-width: 120px;
  justify-content: center;
}

.sync-indicator {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  font-weight: 600;
  transition: color 0.3s;
}

.sync-quality {
  font-family: 'Courier New', monospace;
}

.render-stats {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--text-secondary);
}

.cache-hit {
  font-family: 'Courier New', monospace;
  color: var(--accent-secondary);
  font-weight: 600;
}

.volume-control {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 140px;
  justify-content: flex-end;
}

.volume-icon {
  font-size: 16px;
}

.volume-slider {
  width: 80px;
  height: 4px;
  -webkit-appearance: none;
  appearance: none;
  background: var(--bg-track);
  border-radius: 2px;
  outline: none;
}

.volume-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 14px;
  height: 14px;
  background: var(--accent-primary);
  border-radius: 50%;
  cursor: pointer;
  transition: transform 0.2s;
}

.volume-slider::-webkit-slider-thumb:hover {
  transform: scale(1.2);
}

.volume-slider::-moz-range-thumb {
  width: 14px;
  height: 14px;
  background: var(--accent-primary);
  border-radius: 50%;
  cursor: pointer;
  border: none;
}
</style>
