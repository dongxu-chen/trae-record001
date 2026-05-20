<template>
  <div class="timeline">
    <div class="timeline-header">
      <div class="timeline-scale" ref="scaleRef">
        <div 
          class="playhead" 
          :style="{ left: playheadPosition + 'px' }"
          ref="playheadRef"
        >
          <div class="playhead-line"></div>
          <div class="playhead-dot"></div>
        </div>
        <div class="scale-marks">
          <div 
            v-for="mark in scaleMarks" 
            :key="mark.time"
            class="scale-mark"
            :style="{ left: mark.position + 'px' }"
          >
            <span class="mark-label">{{ mark.label }}</span>
            <span class="mark-line"></span>
          </div>
        </div>
      </div>
    </div>

    <div 
      class="timeline-tracks" 
      ref="tracksRef"
      @scroll="handleScroll"
      @click="handleTimelineClick"
      @drop="handleDrop"
      @dragover.prevent
    >
      <div class="tracks-container" :style="{ width: timelineWidth + 'px' }">
        <div class="track video-track">
          <div class="track-label">
            <span class="track-icon">🎬</span>
            <span class="track-name">视频轨</span>
          </div>
          <div class="track-content">
            <div 
              v-for="clip in store.sortedVideoClips" 
              :key="clip.id"
              class="clip"
              :class="{ selected: store.selectedClipId === clip.id, dragging: draggingClipId === clip.id }"
              :style="{ 
                left: clip.startTime * pixelsPerSecond + 'px',
                width: clip.duration * pixelsPerSecond + 'px',
              }"
              draggable="true"
              @dragstart="handleClipDragStart($event, clip)"
              @dragend="handleClipDragEnd"
              @click.stop="selectClip(clip)"
              @mousedown.stop="startResize($event, clip)"
            >
              <div class="clip-thumbnail" v-if="clip.thumbnail">
                <img :src="clip.thumbnail" :alt="clip.name" />
              </div>
              <div class="clip-thumbnail placeholder" v-else>
                <span>🎬</span>
              </div>
              <div class="clip-info">
                <p class="clip-name">{{ clip.name }}</p>
                <p class="clip-time">{{ formatTimeShort(clip.duration) }}</p>
              </div>
              <div class="clip-handle left" @mousedown.stop="startTrim($event, clip, 'left')"></div>
              <div class="clip-handle right" @mousedown.stop="startTrim($event, clip, 'right')"></div>
              
              <div class="transition-indicator" v-if="clip.transition" @click.stop="showTransitionPanel(clip)">
                <span>✨</span>
              </div>
            </div>
          </div>
        </div>

        <div class="track audio-track">
          <div class="track-label">
            <span class="track-icon">🎵</span>
            <span class="track-name">音频轨</span>
          </div>
          <div class="track-content">
            <div 
              v-for="clip in store.audioTrack" 
              :key="clip.id"
              class="clip audio-clip"
              :style="{ 
                left: clip.startTime * pixelsPerSecond + 'px',
                width: clip.duration * pixelsPerSecond + 'px',
              }"
            >
              <div class="audio-waveform">
                <div v-for="i in 20" :key="i" class="wave-bar" :style="{ height: (20 + Math.random() * 60) + '%' }"></div>
              </div>
              <div class="clip-info">
                <p class="clip-name">{{ clip.name }}</p>
              </div>
              <button class="clip-delete" @click.stop="removeAudioClip(clip.id)" title="删除">×</button>
            </div>
          </div>
        </div>

        <div class="track subtitle-track">
          <div class="track-label">
            <span class="track-icon">📝</span>
            <span class="track-name">字幕轨</span>
            <button class="add-subtitle-btn" @click.stop="addSubtitleAtCurrent" title="添加字幕">+</button>
          </div>
          <div class="track-content">
            <div 
              v-for="sub in store.subtitleTrack" 
              :key="sub.id"
              class="subtitle-clip"
              :class="{ selected: selectedSubtitleId === sub.id }"
              :style="{ 
                left: sub.startTime * pixelsPerSecond + 'px',
                width: (sub.endTime - sub.startTime) * pixelsPerSecond + 'px',
              }"
              @click.stop="selectSubtitle(sub)"
            >
              <div class="subtitle-preview">{{ sub.text }}</div>
              <button class="clip-delete" @click.stop="removeSubtitle(sub.id)" title="删除">×</button>
            </div>
          </div>
        </div>

        <div 
          class="playhead" 
          :style="{ left: playheadPosition + 'px' }"
        >
          <div class="playhead-line"></div>
        </div>
      </div>
    </div>

    <div class="timeline-footer">
      <div class="zoom-control">
        <button class="zoom-btn" @click="zoomOut">−</button>
        <span class="zoom-level">{{ Math.round(pixelsPerSecond) }}px/s</span>
        <button class="zoom-btn" @click="zoomIn">+</button>
      </div>
      <div class="track-info">
        <span>总时长: {{ formatTimeShort(store.totalDuration) }}</span>
        <span>·</span>
        <span>{{ store.videoTrack.length }} 个片段</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useEditorStore } from '../stores/editor'
import { formatTimeShort } from '../utils/format'

const emit = defineEmits(['edit-clip'])

const store = useEditorStore()

const tracksRef = ref(null)
const scaleRef = ref(null)
const playheadRef = ref(null)
const pixelsPerSecond = ref(50)
const draggingClipId = ref(null)
const resizingClip = ref(null)
const selectedSubtitleId = ref(null)

const minPixelsPerSecond = 10
const maxPixelsPerSecond = 200

const timelineWidth = computed(() => {
  return Math.max(store.totalDuration * pixelsPerSecond.value + 200, 2000)
})

const playheadPosition = computed(() => {
  return store.currentTime * pixelsPerSecond.value
})

const scaleMarks = computed(() => {
  const marks = []
  const interval = pixelsPerSecond.value < 30 ? 5 : (pixelsPerSecond.value < 80 ? 2 : 1)
  const maxTime = Math.ceil(Math.max(store.totalDuration, 60))
  
  for (let t = 0; t <= maxTime; t += interval) {
    marks.push({
      time: t,
      position: t * pixelsPerSecond.value,
      label: formatTimeShort(t),
    })
  }
  return marks
})

watch(() => store.totalDuration, () => {
  if (tracksRef.value) {
    tracksRef.value.scrollLeft = 0
  }
})

function handleScroll(e) {
  if (scaleRef.value) {
    scaleRef.value.scrollLeft = e.target.scrollLeft
  }
}

function handleTimelineClick(e) {
  if (e.target.closest('.clip') || e.target.closest('.subtitle-clip')) return
  
  const rect = tracksRef.value.getBoundingClientRect()
  const x = e.clientX - rect.left + tracksRef.value.scrollLeft
  const time = x / pixelsPerSecond.value
  store.setCurrentTime(Math.max(0, Math.min(time, store.totalDuration)))
  store.selectClip(null)
  selectedSubtitleId.value = null
}

function handleDrop(e) {
  const mediaData = e.dataTransfer?.getData('mediaItem')
  if (!mediaData) return

  const mediaItem = JSON.parse(mediaData)
  const rect = tracksRef.value.getBoundingClientRect()
  const x = e.clientX - rect.left + tracksRef.value.scrollLeft
  const time = Math.max(0, x / pixelsPerSecond.value)

  if (mediaItem.type === 'video') {
    store.addToVideoTrack(mediaItem, time)
  } else if (mediaItem.type === 'audio') {
    store.addToAudioTrack(mediaItem, time)
  }
}

function selectClip(clip) {
  store.selectClip(clip.id)
  selectedSubtitleId.value = null
  emit('edit-clip', clip)
}

function handleClipDragStart(e, clip) {
  draggingClipId.value = clip.id
  e.dataTransfer.setData('clipId', clip.id)
  e.dataTransfer.effectAllowed = 'move'
}

function handleClipDragEnd() {
  draggingClipId.value = null
  resizingClip.value = null
}

function startResize(e, clip) {
  if (e.target.classList.contains('clip-handle')) return
  
  const startX = e.clientX
  const startTime = clip.startTime
  
  function handleMouseMove(moveEvent) {
    const deltaX = moveEvent.clientX - startX
    const deltaTime = deltaX / pixelsPerSecond.value
    const newStartTime = Math.max(0, startTime + deltaTime)
    store.moveClip(clip.id, newStartTime)
  }
  
  function handleMouseUp() {
    document.removeEventListener('mousemove', handleMouseMove)
    document.removeEventListener('mouseup', handleMouseUp)
  }
  
  document.addEventListener('mousemove', handleMouseMove)
  document.addEventListener('mouseup', handleMouseUp)
}

function startTrim(e, clip, side) {
  e.preventDefault()
  e.stopPropagation()
  
  const startX = e.clientX
  const originalTrimStart = clip.trimStart
  const originalTrimEnd = clip.trimEnd
  
  function handleMouseMove(moveEvent) {
    const deltaX = moveEvent.clientX - startX
    const deltaTime = deltaX / pixelsPerSecond.value
    
    if (side === 'left') {
      const newTrimStart = Math.max(0, Math.min(originalTrimStart + deltaTime, originalTrimEnd - 0.1))
      store.trimClip(clip.id, newTrimStart, originalTrimEnd)
    } else {
      const newTrimEnd = Math.max(originalTrimStart + 0.1, Math.min(originalTrimEnd + deltaTime, clip.originalDuration))
      store.trimClip(clip.id, originalTrimStart, newTrimEnd)
    }
  }
  
  function handleMouseUp() {
    document.removeEventListener('mousemove', handleMouseMove)
    document.removeEventListener('mouseup', handleMouseUp)
    resizingClip.value = null
  }
  
  resizingClip.value = { clipId: clip.id, side }
  document.addEventListener('mousemove', handleMouseMove)
  document.addEventListener('mouseup', handleMouseUp)
}

function selectSubtitle(sub) {
  selectedSubtitleId.value = sub.id
  store.selectClip(null)
  emit('edit-clip', { type: 'subtitle', ...sub })
}

function removeSubtitle(id) {
  if (confirm('确定要删除这个字幕吗？')) {
    store.removeSubtitle(id)
    if (selectedSubtitleId.value === id) {
      selectedSubtitleId.value = null
    }
  }
}

function removeAudioClip(id) {
  if (confirm('确定要删除这个音频片段吗？')) {
    store.removeAudioClip(id)
  }
}

function addSubtitleAtCurrent() {
  const startTime = store.currentTime
  const endTime = Math.min(startTime + 3, store.totalDuration || startTime + 3)
  store.addSubtitle('请输入字幕内容', startTime, endTime)
}

function showTransitionPanel(clip) {
  store.selectClip(clip.id)
  emit('edit-clip', clip)
}

function zoomIn() {
  pixelsPerSecond.value = Math.min(maxPixelsPerSecond, pixelsPerSecond.value + 10)
}

function zoomOut() {
  pixelsPerSecond.value = Math.max(minPixelsPerSecond, pixelsPerSecond.value - 10)
}

defineExpose({
  pixelsPerSecond,
})
</script>

<style scoped>
.timeline {
  height: 320px;
  display: flex;
  flex-direction: column;
  background: var(--bg-secondary);
  border-top: 1px solid var(--border-color);
}

.timeline-header {
  height: 32px;
  background: var(--bg-tertiary);
  border-bottom: 1px solid var(--border-color);
  overflow: hidden;
  flex-shrink: 0;
}

.timeline-scale {
  position: relative;
  height: 100%;
  overflow-x: auto;
  overflow-y: hidden;
  scrollbar-width: none;
}

.timeline-scale::-webkit-scrollbar {
  display: none;
}

.scale-marks {
  position: relative;
  height: 100%;
  min-width: 100%;
}

.scale-mark {
  position: absolute;
  top: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.mark-label {
  font-size: 10px;
  color: var(--text-muted);
  font-family: 'Courier New', monospace;
}

.mark-line {
  width: 1px;
  height: 8px;
  background: var(--border-color);
  margin-top: 2px;
}

.playhead {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 0;
  z-index: 10;
  pointer-events: none;
}

.playhead-line {
  position: absolute;
  top: 0;
  bottom: 0;
  left: -1px;
  width: 2px;
  background: var(--accent-primary);
  box-shadow: 0 0 8px rgba(233, 69, 96, 0.5);
}

.playhead-dot {
  position: absolute;
  top: -4px;
  left: -6px;
  width: 12px;
  height: 12px;
  background: var(--accent-primary);
  border-radius: 50%;
  border: 2px solid white;
}

.timeline-tracks {
  flex: 1;
  overflow-x: auto;
  overflow-y: auto;
  position: relative;
}

.tracks-container {
  position: relative;
  min-width: 100%;
}

.track {
  display: flex;
  border-bottom: 1px solid var(--border-color);
  min-height: 60px;
}

.track-label {
  width: 100px;
  min-width: 100px;
  padding: 8px 12px;
  background: var(--bg-tertiary);
  border-right: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 500;
  position: sticky;
  left: 0;
  z-index: 5;
}

.track-icon {
  font-size: 14px;
}

.add-subtitle-btn {
  margin-left: auto;
  width: 20px;
  height: 20px;
  border: none;
  border-radius: 4px;
  background: var(--accent-primary);
  color: white;
  font-size: 14px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.add-subtitle-btn:hover {
  background: #ff5a75;
}

.track-content {
  flex: 1;
  position: relative;
  height: 60px;
}

.video-track .track-content {
  height: 80px;
}

.audio-track .track-content {
  height: 50px;
}

.subtitle-track .track-content {
  height: 50px;
}

.clip {
  position: absolute;
  top: 4px;
  bottom: 4px;
  background: var(--bg-clip);
  border: 2px solid var(--border-color);
  border-radius: 6px;
  overflow: hidden;
  cursor: grab;
  transition: border-color 0.2s, box-shadow 0.2s;
  display: flex;
  gap: 6px;
  padding: 4px;
}

.clip:hover {
  border-color: var(--accent-secondary);
}

.clip.selected {
  border-color: var(--accent-primary);
  box-shadow: 0 0 0 2px rgba(233, 69, 96, 0.3);
}

.clip.dragging {
  opacity: 0.7;
  cursor: grabbing;
}

.clip-thumbnail {
  width: 60px;
  height: 100%;
  border-radius: 4px;
  overflow: hidden;
  background: var(--bg-tertiary);
  flex-shrink: 0;
}

.clip-thumbnail img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.clip-thumbnail.placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
}

.clip-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.clip-name {
  font-size: 11px;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.clip-time {
  font-size: 10px;
  color: var(--text-muted);
  margin-top: 2px;
}

.clip-handle {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 12px;
  cursor: ew-resize;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.2s;
}

.clip-handle::before {
  content: '';
  width: 4px;
  height: 20px;
  background: var(--accent-secondary);
  border-radius: 2px;
}

.clip-handle.left {
  left: 0;
  border-radius: 6px 0 0 6px;
}

.clip-handle.right {
  right: 0;
  border-radius: 0 6px 6px 0;
}

.clip:hover .clip-handle {
  opacity: 1;
}

.clip-handle:hover {
  background: rgba(0, 217, 255, 0.2);
}

.clip-delete {
  position: absolute;
  top: 2px;
  right: 2px;
  width: 18px;
  height: 18px;
  border: none;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.5);
  color: white;
  font-size: 14px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.2s, background 0.2s;
}

.clip:hover .clip-delete {
  opacity: 1;
}

.clip-delete:hover {
  background: var(--accent-primary);
}

.audio-clip {
  background: linear-gradient(135deg, #2d5a87, #1e3a5f);
  border-color: #3a7ab8;
}

.audio-waveform {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 0 4px;
}

.wave-bar {
  flex: 1;
  background: rgba(255, 255, 255, 0.6);
  border-radius: 1px;
  min-height: 4px;
}

.subtitle-clip {
  position: absolute;
  top: 4px;
  bottom: 4px;
  background: linear-gradient(135deg, #4a3f6b, #3a2f5b);
  border: 2px solid #6b5ba8;
  border-radius: 6px;
  padding: 4px 8px;
  cursor: pointer;
  transition: border-color 0.2s;
}

.subtitle-clip:hover {
  border-color: var(--accent-secondary);
}

.subtitle-clip.selected {
  border-color: var(--accent-primary);
  box-shadow: 0 0 0 2px rgba(233, 69, 96, 0.3);
}

.subtitle-preview {
  font-size: 11px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  color: var(--text-primary);
}

.transition-indicator {
  position: absolute;
  right: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 24px;
  height: 24px;
  background: var(--accent-warning);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  cursor: pointer;
  z-index: 2;
}

.timeline-footer {
  height: 36px;
  padding: 0 16px;
  background: var(--bg-tertiary);
  border-top: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
}

.zoom-control {
  display: flex;
  align-items: center;
  gap: 12px;
}

.zoom-btn {
  width: 24px;
  height: 24px;
  border: none;
  border-radius: 4px;
  background: var(--bg-clip);
  color: var(--text-primary);
  font-size: 16px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.zoom-btn:hover {
  background: var(--accent-primary);
}

.zoom-level {
  font-size: 11px;
  color: var(--text-muted);
  font-family: 'Courier New', monospace;
  min-width: 60px;
  text-align: center;
}

.track-info {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--text-muted);
}
</style>
