<template>
  <div class="app-container">
    <header class="app-header">
      <h1>🎵 音频可视化播放器</h1>
    </header>

    <main class="app-main">
      <div class="main-content">
        <div class="visualizer-section">
          <div class="drop-zone" 
               @dragover.prevent="onDragOver"
               @dragleave="onDragLeave"
               @drop="onDrop"
               :class="{ 'drag-over': isDragOver }">
            <canvas ref="spectrumCanvas" class="spectrum-canvas"></canvas>
            <canvas ref="waveformCanvas" class="waveform-canvas"></canvas>
            <div v-if="!playlist.length" class="drop-hint">
              <p>拖拽音频/歌词文件到此处或点击上传</p>
              <input type="file" ref="fileInput" accept="audio/*,.lrc,.srt,.json,.txt" multiple @change="onFileSelect" style="display: none;">
              <button class="upload-btn" @click="$refs.fileInput.click()">选择文件</button>
            </div>
          </div>

          <div class="lyrics-section" v-if="currentTrack">
            <div class="lyrics-header">
              <div class="lyrics-format-badge" v-if="lyricsFormat">格式: {{ lyricsFormat.toUpperCase() }}</div>
              <button class="translate-btn" @click="toggleTranslation" :class="{ active: showTranslation }">
                {{ showTranslation ? '隐藏翻译' : 'AI翻译' }}
              </button>
            </div>
            <div class="lyrics-container" ref="lyricsContainer">
              <div class="lyrics-line" 
                   v-for="(line, index) in lyrics" 
                   :key="index"
                   :class="{ active: currentLyricIndex === index }">
                <div class="original-text">{{ line.text }}</div>
                <div v-if="showTranslation && line.translation" class="translation-text">{{ line.translation }}</div>
              </div>
              <div v-if="!lyrics.length" class="no-lyrics">暂无歌词（可拖拽 .lrc/.srt/.json/.txt 文件上传）</div>
              <div v-if="isTranslating" class="translating-indicator">
                <span class="spinner"></span> 翻译中...
              </div>
            </div>
          </div>
        </div>

        <div class="control-section">
          <div class="track-info" v-if="currentTrack">
            <div class="track-name">{{ currentTrack.name }}</div>
            <div class="track-time">{{ formatTime(currentTime) }} / {{ formatTime(duration) }}</div>
          </div>

          <div class="progress-bar" @click="seekTo">
            <div class="progress-fill" :style="{ width: progressPercent + '%' }"></div>
          </div>

          <div class="controls">
            <button class="control-btn" @click="prevTrack" :disabled="!hasPrev">⏮</button>
            <button class="control-btn play-btn" @click="togglePlay">
              {{ isPlaying ? '⏸' : '▶' }}
            </button>
            <button class="control-btn" @click="nextTrack" :disabled="!hasNext">⏭</button>
          </div>

          <div class="extra-controls">
            <div class="volume-control">
              <span>🔊</span>
              <input type="range" min="0" max="1" step="0.01" v-model.number="volume" @input="setVolume">
              <span>{{ Math.round(volume * 100) }}%</span>
            </div>
            <div class="speed-control">
              <span>速度:</span>
              <select v-model="playbackRate" @change="setPlaybackRate">
                <option v-for="rate in speedOptions" :key="rate" :value="rate">{{ rate }}x</option>
              </select>
            </div>
            <div class="fps-control">
              <span>FPS: {{ currentFPS }}</span>
            </div>
          </div>
        </div>

        <div class="equalizer-section" v-if="showEqualizer">
          <div class="section-header">
            <h3>🎛 均衡器</h3>
            <div class="eq-presets">
              <button v-for="preset in eqPresets" :key="preset.name" 
                      @click="applyPreset(preset)"
                      :class="{ active: currentPreset === preset.name }">
                {{ preset.label }}
              </button>
            </div>
          </div>
          <div class="eq-bands">
            <div class="eq-band" v-for="(band, index) in eqBands" :key="index">
              <div class="eq-slider">
                <input type="range" 
                       :min="-12" 
                       :max="12" 
                       step="1" 
                       :value="band.gain"
                       @input="setBandGain(index, $event.target.value)">
              </div>
              <div class="eq-label">{{ band.label }}</div>
              <div class="eq-value">{{ band.gain > 0 ? '+' : '' }}{{ band.gain }}dB</div>
            </div>
          </div>
          <button class="reset-eq-btn" @click="resetEqualizer">重置均衡器</button>
        </div>

        <div class="cutter-section" v-if="showCutter">
          <div class="section-header">
            <h3>✂ 音频裁剪</h3>
            <button class="close-btn" @click="showCutter = false">✕</button>
          </div>
          <div class="cutter-waveform">
            <canvas ref="cutterCanvas" class="cutter-canvas" @mousedown="startCutterDrag" @mousemove="onCutterDrag" @mouseup="endCutterDrag"></canvas>
            <div class="cutter-selection" :style="cutterSelectionStyle"></div>
          </div>
          <div class="cutter-controls">
            <div class="time-inputs">
              <label>
                开始时间:
                <input type="number" v-model.number="cutterStartTime" min="0" :max="cutterEndTime" step="0.1">
                秒
              </label>
              <label>
                结束时间:
                <input type="number" v-model.number="cutterEndTime" :min="cutterStartTime" :max="duration" step="0.1">
                秒
              </label>
            </div>
            <div class="cutter-actions">
              <button class="preview-btn" @click="previewClip">预览片段</button>
              <button class="export-btn" @click="exportClip" :disabled="isExporting">
                {{ isExporting ? '导出中...' : '导出 WAV' }}
              </button>
            </div>
          </div>
        </div>

        <div class="toolbar">
          <button class="tool-btn" @click="showEqualizer = !showEqualizer" :class="{ active: showEqualizer }">
            🎛 均衡器
          </button>
          <button class="tool-btn" @click="toggleCutter" :class="{ active: showCutter }" :disabled="!currentTrack">
            ✂ 裁剪
          </button>
        </div>
      </div>

      <aside class="playlist-section">
        <div class="playlist-header">
          <h3>播放列表</h3>
          <button class="clear-btn" @click="clearPlaylist" v-if="playlist.length">清空</button>
        </div>
        <div class="playlist-items">
          <div class="playlist-item" 
               v-for="(track, index) in playlist" 
               :key="index"
               :class="{ active: currentIndex === index }"
               @click="playTrack(index)">
            <div class="item-index">{{ index + 1 }}</div>
            <div class="item-info">
              <div class="item-name">{{ track.name }}</div>
              <div class="item-duration">{{ formatTime(track.duration) }}</div>
            </div>
            <button class="remove-btn" @click.stop="removeTrack(index)">✕</button>
          </div>
          <div v-if="!playlist.length" class="empty-playlist">
            暂无歌曲，请添加音频文件
          </div>
        </div>
      </aside>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick, shallowRef } from 'vue'
import { LyricsParser } from './utils/lyricsParser.js'
import { LyricsTranslator } from './utils/lyricsTranslator.js'
import { AudioCutter } from './utils/audioCutter.js'

const isDragOver = ref(false)
const playlist = ref([])
const currentIndex = ref(-1)
const isPlaying = ref(false)
const currentTime = ref(0)
const duration = ref(0)
const volume = ref(0.8)
const playbackRate = ref(1)
const speedOptions = [0.5, 0.75, 1, 1.25, 1.5, 2]
const lyrics = ref([])
const currentLyricIndex = ref(-1)
const lyricsFormat = ref('')
const currentFPS = ref(60)

const showTranslation = ref(false)
const isTranslating = ref(false)
const lyricsTranslator = new LyricsTranslator()

const showEqualizer = ref(false)
const showCutter = ref(false)
const isExporting = ref(false)

const spectrumCanvas = ref(null)
const waveformCanvas = ref(null)
const cutterCanvas = ref(null)
const lyricsContainer = ref(null)
const fileInput = ref(null)

const audioContext = shallowRef(null)
const analyser = shallowRef(null)
const gainNode = shallowRef(null)
const audioElement = shallowRef(null)
const waveformWorker = shallowRef(null)
const eqFilters = shallowRef([])
const audioCutter = new AudioCutter()

const spectrumCtx = shallowRef(null)
const waveformCtx = shallowRef(null)
const cutterCtx = shallowRef(null)

let animationId = null
let lastFrameTime = 0
let frameCount = 0
let fpsUpdateTime = 0
const TARGET_FPS = 60
const FRAME_INTERVAL = 1000 / TARGET_FPS

const staticWaveformData = ref([])
const isWaveformReady = ref(false)

const eqBands = ref([
  { freq: 32, label: '32Hz', gain: 0 },
  { freq: 64, label: '64Hz', gain: 0 },
  { freq: 125, label: '125Hz', gain: 0 },
  { freq: 250, label: '250Hz', gain: 0 },
  { freq: 500, label: '500Hz', gain: 0 },
  { freq: 1000, label: '1kHz', gain: 0 },
  { freq: 2000, label: '2kHz', gain: 0 },
  { freq: 4000, label: '4kHz', gain: 0 },
  { freq: 8000, label: '8kHz', gain: 0 },
  { freq: 16000, label: '16kHz', gain: 0 }
])

const eqPresets = [
  { name: 'flat', label: '默认', gains: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0] },
  { name: 'bass', label: '低音增强', gains: [6, 5, 4, 2, 0, -1, -1, 0, 1, 2] },
  { name: 'treble', label: '高音增强', gains: [-2, -1, 0, 1, 2, 3, 4, 5, 6, 6] },
  { name: 'vocal', label: '人声增强', gains: [-2, -1, 0, 2, 4, 4, 3, 1, 0, -1] },
  { name: 'rock', label: '摇滚', gains: [4, 3, 2, 0, -1, 0, 2, 3, 4, 4] },
  { name: 'pop', label: '流行', gains: [-1, 1, 3, 4, 3, 1, 0, 1, 2, 1] }
]

const currentPreset = ref('flat')

const cutterStartTime = ref(0)
const cutterEndTime = ref(30)
const isDraggingCutter = ref(false)
const dragType = ref(null)

const currentTrack = computed(() => {
  return currentIndex.value >= 0 ? playlist.value[currentIndex.value] : null
})

const hasPrev = computed(() => currentIndex.value > 0)
const hasNext = computed(() => currentIndex.value < playlist.value.length - 1)

const progressPercent = computed(() => {
  return duration.value > 0 ? (currentTime.value / duration.value) * 100 : 0
})

const cutterSelectionStyle = computed(() => {
  if (!duration.value) return {}
  const left = (cutterStartTime.value / duration.value) * 100
  const width = ((cutterEndTime.value - cutterStartTime.value) / duration.value) * 100
  return {
    left: `${left}%`,
    width: `${width}%`
  }
})

function initAudioContext() {
  if (!audioContext.value) {
    audioContext.value = new (window.AudioContext || window.webkitAudioContext)()
    analyser.value = audioContext.value.createAnalyser()
    analyser.value.fftSize = 512
    analyser.value.smoothingTimeConstant = 0.8
    gainNode.value = audioContext.value.createGain()
    gainNode.value.gain.value = volume.value
    
    eqFilters.value = eqBands.value.map(band => {
      const filter = audioContext.value.createBiquadFilter()
      filter.type = band.freq < 100 ? 'lowshelf' : band.freq > 8000 ? 'highshelf' : 'peaking'
      filter.frequency.value = band.freq
      filter.Q.value = 1
      filter.gain.value = band.gain
      return filter
    })
  }
}

function initCanvas() {
  nextTick(() => {
    if (spectrumCanvas.value) {
      spectrumCtx.value = spectrumCanvas.value.getContext('2d', { alpha: false })
      resizeCanvas(spectrumCanvas.value)
    }
    if (waveformCanvas.value) {
      waveformCtx.value = waveformCanvas.value.getContext('2d', { alpha: false })
      resizeCanvas(waveformCanvas.value)
    }
    if (cutterCanvas.value) {
      cutterCtx.value = cutterCanvas.value.getContext('2d', { alpha: false })
    }
  })
}

function initWaveformWorker() {
  if (typeof Worker !== 'undefined') {
    try {
      waveformWorker.value = new Worker(new URL('./workers/waveform.worker.js', import.meta.url), {
        type: 'module'
      })
      waveformWorker.value.onmessage = handleWorkerMessage
    } catch (e) {
      console.warn('Web Worker not available, using main thread for waveform processing')
    }
  }
}

function handleWorkerMessage(e) {
  const { type, data, error } = e.data
  
  switch (type) {
    case 'waveform':
      staticWaveformData.value = data
      isWaveformReady.value = true
      drawStaticWaveform()
      drawCutterWaveform()
      break
    case 'decoded':
      break
    case 'error':
      console.error('Waveform worker error:', error)
      break
  }
}

function resizeCanvas(canvas) {
  const rect = canvas.parentElement.getBoundingClientRect()
  const dpr = window.devicePixelRatio || 1
  canvas.width = rect.width * dpr
  canvas.height = (rect.height / 2) * dpr
  const ctx = canvas.getContext('2d')
  ctx.scale(dpr, dpr)
  canvas.style.width = rect.width + 'px'
  canvas.style.height = (rect.height / 2) + 'px'
}

function onDragOver(e) {
  isDragOver.value = true
}

function onDragLeave(e) {
  isDragOver.value = false
}

async function onDrop(e) {
  isDragOver.value = false
  const files = Array.from(e.dataTransfer.files)
  
  const audioFiles = files.filter(f => f.type.startsWith('audio/'))
  const lyricFiles = files.filter(f => 
    ['.lrc', '.srt', '.json', '.txt'].some(ext => f.name.toLowerCase().endsWith(ext))
  )
  
  if (audioFiles.length) {
    await addAudioFiles(audioFiles)
  }
  
  if (lyricFiles.length) {
    await loadLyricsFromFile(lyricFiles[0])
  }
}

async function onFileSelect(e) {
  const files = Array.from(e.target.files)
  
  const audioFiles = files.filter(f => f.type.startsWith('audio/'))
  const lyricFiles = files.filter(f => 
    ['.lrc', '.srt', '.json', '.txt'].some(ext => f.name.toLowerCase().endsWith(ext))
  )
  
  if (audioFiles.length) {
    await addAudioFiles(audioFiles)
  }
  
  if (lyricFiles.length) {
    await loadLyricsFromFile(lyricFiles[0])
  }
  
  e.target.value = ''
}

async function addAudioFiles(files) {
  for (const file of files) {
    const duration = await getAudioDuration(file)
    const track = {
      name: file.name.replace(/\.[^/.]+$/, ''),
      file: file,
      duration: duration,
      url: URL.createObjectURL(file),
      waveformData: null
    }
    
    if (waveformWorker.value) {
      computeWaveformForTrack(track)
    }
    
    playlist.value.push(track)
  }
  
  if (currentIndex.value === -1 && playlist.value.length > 0) {
    currentIndex.value = 0
    loadTrack()
  }
}

async function computeWaveformForTrack(track) {
  try {
    const arrayBuffer = await track.file.arrayBuffer()
    waveformWorker.value.postMessage({
      type: 'decode',
      data: arrayBuffer
    }, [arrayBuffer])
  } catch (e) {
    console.warn('Failed to compute waveform:', e)
  }
}

function getAudioDuration(file) {
  return new Promise((resolve) => {
    const tempAudio = new Audio()
    tempAudio.onloadedmetadata = () => {
      resolve(tempAudio.duration)
      tempAudio.remove()
    }
    tempAudio.src = URL.createObjectURL(file)
  })
}

async function loadLyricsFromFile(file) {
  try {
    const content = await file.text()
    const format = LyricsParser.detectFormat(content)
    lyricsFormat.value = format
    lyrics.value = LyricsParser.parse(content)
    currentLyricIndex.value = 0
    showTranslation.value = false
  } catch (e) {
    console.error('Failed to load lyrics:', e)
  }
}

async function toggleTranslation() {
  if (!showTranslation.value && !lyrics.value[0]?.translation) {
    isTranslating.value = true
    lyrics.value = await lyricsTranslator.translateLyrics(lyrics.value)
    isTranslating.value = false
  }
  showTranslation.value = !showTranslation.value
}

function loadTrack() {
  if (!currentTrack.value) return
  
  initAudioContext()
  
  if (audioElement.value) {
    audioElement.value.pause()
    audioElement.value.remove()
  }
  
  audioElement.value = new Audio(currentTrack.value.url)
  audioElement.value.volume = volume.value
  audioElement.value.playbackRate = playbackRate.value
  
  const source = audioContext.value.createMediaElementSource(audioElement.value)
  
  let lastNode = source
  eqFilters.value.forEach(filter => {
    lastNode.connect(filter)
    lastNode = filter
  })
  lastNode.connect(analyser.value)
  analyser.value.connect(gainNode.value)
  gainNode.value.connect(audioContext.value.destination)
  
  audioElement.value.addEventListener('timeupdate', onTimeUpdate)
  audioElement.value.addEventListener('loadedmetadata', onLoadedMetadata)
  audioElement.value.addEventListener('ended', onTrackEnded)
  
  isWaveformReady.value = false
  staticWaveformData.value = []
  
  if (waveformWorker.value && currentTrack.value.file) {
    computeWaveformForTrack(currentTrack.value)
  }
  
  if (!lyrics.value.length) {
    parseLyrics(currentTrack.value.name)
  }
  
  cutterStartTime.value = 0
  cutterEndTime.value = Math.min(30, currentTrack.value.duration || 30)
}

function onTimeUpdate() {
  currentTime.value = audioElement.value.currentTime
  updateLyricIndex()
}

function onLoadedMetadata() {
  duration.value = audioElement.value.duration
  cutterEndTime.value = Math.min(30, duration.value)
  drawCutterWaveform()
}

function onTrackEnded() {
  if (hasNext.value) {
    nextTrack()
  } else {
    isPlaying.value = false
    cancelAnimationFrame(animationId)
  }
}

function togglePlay() {
  if (!currentTrack.value) return
  
  if (audioContext.value && audioContext.value.state === 'suspended') {
    audioContext.value.resume()
  }
  
  if (isPlaying.value) {
    audioElement.value.pause()
    cancelAnimationFrame(animationId)
  } else {
    audioElement.value.play()
    lastFrameTime = performance.now()
    startVisualization()
  }
  isPlaying.value = !isPlaying.value
}

function playTrack(index) {
  currentIndex.value = index
  lyrics.value = []
  lyricsFormat.value = ''
  showTranslation.value = false
  loadTrack()
  nextTick(() => {
    if (!isPlaying.value) {
      togglePlay()
    }
  })
}

function prevTrack() {
  if (hasPrev.value) {
    playTrack(currentIndex.value - 1)
  }
}

function nextTrack() {
  if (hasNext.value) {
    playTrack(currentIndex.value + 1)
  }
}

function seekTo(e) {
  if (!audioElement.value || !duration.value) return
  const rect = e.currentTarget.getBoundingClientRect()
  const percent = (e.clientX - rect.left) / rect.width
  audioElement.value.currentTime = percent * duration.value
}

function setVolume() {
  if (audioElement.value) {
    audioElement.value.volume = volume.value
  }
  if (gainNode.value) {
    gainNode.value.gain.value = volume.value
  }
}

function setPlaybackRate() {
  if (audioElement.value) {
    audioElement.value.playbackRate = playbackRate.value
  }
}

function setBandGain(index, value) {
  eqBands.value[index].gain = parseInt(value)
  if (eqFilters.value[index]) {
    eqFilters.value[index].gain.value = eqBands.value[index].gain
  }
  currentPreset.value = ''
}

function applyPreset(preset) {
  currentPreset.value = preset.name
  preset.gains.forEach((gain, index) => {
    eqBands.value[index].gain = gain
    if (eqFilters.value[index]) {
      eqFilters.value[index].gain.value = gain
    }
  })
}

function resetEqualizer() {
  applyPreset(eqPresets[0])
}

function toggleCutter() {
  showCutter.value = !showCutter.value
  if (showCutter.value) {
    nextTick(() => {
      const canvas = cutterCanvas.value
      if (canvas) {
        const rect = canvas.parentElement.getBoundingClientRect()
        canvas.width = rect.width
        canvas.height = 100
        cutterCtx.value = canvas.getContext('2d')
        drawCutterWaveform()
      }
    })
  }
}

function drawCutterWaveform() {
  if (!cutterCtx.value || staticWaveformData.value.length === 0) return
  
  const canvas = cutterCanvas.value
  const ctx = cutterCtx.value
  const width = canvas.width
  const height = canvas.height
  
  ctx.fillStyle = '#0f172a'
  ctx.fillRect(0, 0, width, height)
  
  const barWidth = width / staticWaveformData.value.length
  const centerY = height / 2
  
  for (let i = 0; i < staticWaveformData.value.length; i++) {
    const barHeight = staticWaveformData.value[i] * height * 0.4
    const x = i * barWidth
    
    ctx.fillStyle = '#475569'
    ctx.fillRect(x, centerY - barHeight, barWidth - 1, barHeight * 2)
  }
}

function startCutterDrag(e) {
  if (!duration.value) return
  const rect = cutterCanvas.value.getBoundingClientRect()
  const x = e.clientX - rect.left
  const clickTime = (x / rect.width) * duration.value
  
  const startX = (cutterStartTime.value / duration.value) * rect.width
  const endX = (cutterEndTime.value / duration.value) * rect.width
  
  if (Math.abs(x - startX) < 10) {
    isDraggingCutter.value = true
    dragType.value = 'start'
  } else if (Math.abs(x - endX) < 10) {
    isDraggingCutter.value = true
    dragType.value = 'end'
  } else if (x > startX && x < endX) {
    isDraggingCutter.value = true
    dragType.value = 'both'
  }
}

function onCutterDrag(e) {
  if (!isDraggingCutter.value || !duration.value) return
  const rect = cutterCanvas.value.getBoundingClientRect()
  const x = e.clientX - rect.left
  const newTime = Math.max(0, Math.min(duration.value, (x / rect.width) * duration.value))
  
  if (dragType.value === 'start') {
    cutterStartTime.value = Math.min(newTime, cutterEndTime.value - 1)
  } else if (dragType.value === 'end') {
    cutterEndTime.value = Math.max(newTime, cutterStartTime.value + 1)
  } else if (dragType.value === 'both') {
    const diff = cutterEndTime.value - cutterStartTime.value
    const newStart = Math.max(0, Math.min(duration.value - diff, newTime - diff / 2))
    cutterStartTime.value = newStart
    cutterEndTime.value = newStart + diff
  }
}

function endCutterDrag() {
  isDraggingCutter.value = false
  dragType.value = null
}

function previewClip() {
  if (audioElement.value) {
    audioElement.value.currentTime = cutterStartTime.value
    if (!isPlaying.value) {
      togglePlay()
    }
  }
}

async function exportClip() {
  if (!currentTrack.value) return
  
  isExporting.value = true
  const filename = `${currentTrack.value.name}_clip_${formatTime(cutterStartTime.value).replace(':', '-')}_${formatTime(cutterEndTime.value).replace(':', '-')}.wav`
  
  try {
    await audioCutter.exportClip(
      currentTrack.value.url,
      cutterStartTime.value,
      cutterEndTime.value,
      filename
    )
  } catch (e) {
    console.error('Export failed:', e)
  }
  
  isExporting.value = false
}

function removeTrack(index) {
  const wasPlaying = isPlaying.value && currentIndex.value === index
  URL.revokeObjectURL(playlist.value[index].url)
  playlist.value.splice(index, 1)
  
  if (index === currentIndex.value) {
    if (wasPlaying) {
      audioElement.value?.pause()
      cancelAnimationFrame(animationId)
      isPlaying.value = false
    }
    if (playlist.value.length > 0) {
      currentIndex.value = Math.min(index, playlist.value.length - 1)
      loadTrack()
      if (wasPlaying) {
        nextTick(() => togglePlay())
      }
    } else {
      currentIndex.value = -1
      currentTime.value = 0
      duration.value = 0
    }
  } else if (index < currentIndex.value) {
    currentIndex.value--
  }
}

function clearPlaylist() {
  if (audioElement.value) {
    audioElement.value.pause()
    cancelAnimationFrame(animationId)
  }
  playlist.value.forEach(track => URL.revokeObjectURL(track.url))
  playlist.value = []
  currentIndex.value = -1
  isPlaying.value = false
  currentTime.value = 0
  duration.value = 0
  lyrics.value = []
  lyricsFormat.value = ''
  currentLyricIndex.value = -1
  staticWaveformData.value = []
  showTranslation.value = false
}

function startVisualization() {
  if (!analyser.value || !spectrumCtx.value) return
  
  const bufferLength = analyser.value.frequencyBinCount
  const dataArray = new Uint8Array(bufferLength)
  const timeDataArray = new Uint8Array(bufferLength)
  
  function draw(timestamp) {
    animationId = requestAnimationFrame(draw)
    
    const deltaTime = timestamp - lastFrameTime
    if (deltaTime < FRAME_INTERVAL) {
      return
    }
    lastFrameTime = timestamp - (deltaTime % FRAME_INTERVAL)
    
    frameCount++
    if (timestamp - fpsUpdateTime >= 1000) {
      currentFPS.value = frameCount
      frameCount = 0
      fpsUpdateTime = timestamp
    }
    
    analyser.value.getByteFrequencyData(dataArray)
    drawSpectrum(dataArray, bufferLength)
    
    if (!isWaveformReady.value || staticWaveformData.value.length === 0) {
      analyser.value.getByteTimeDomainData(timeDataArray)
      drawRealtimeWaveform(timeDataArray, bufferLength)
    } else {
      drawStaticWaveformWithProgress()
    }
  }
  
  animationId = requestAnimationFrame(draw)
}

function drawSpectrum(dataArray, bufferLength) {
  const canvas = spectrumCanvas.value
  const ctx = spectrumCtx.value
  const width = canvas.width / (window.devicePixelRatio || 1)
  const height = canvas.height / (window.devicePixelRatio || 1)
  
  ctx.fillStyle = 'rgba(15, 23, 42, 0.95)'
  ctx.fillRect(0, 0, width, height)
  
  const barWidth = (width / bufferLength) * 2.5
  let x = 0
  
  for (let i = 0; i < bufferLength; i++) {
    const barHeight = (dataArray[i] / 255) * height
    
    const hue = (i / bufferLength) * 120 + 180
    const saturation = 80
    const lightness = 50 + (dataArray[i] / 255) * 15
    ctx.fillStyle = `hsl(${hue}, ${saturation}%, ${lightness}%)`
    
    ctx.beginPath()
    ctx.roundRect(x, height - barHeight, barWidth - 2, barHeight, 2)
    ctx.fill()
    
    x += barWidth
  }
}

function drawRealtimeWaveform(timeDataArray, bufferLength) {
  const canvas = waveformCanvas.value
  const ctx = waveformCtx.value
  const width = canvas.width / (window.devicePixelRatio || 1)
  const height = canvas.height / (window.devicePixelRatio || 1)
  
  ctx.fillStyle = 'rgba(15, 23, 42, 0.95)'
  ctx.fillRect(0, 0, width, height)
  
  ctx.lineWidth = 2
  ctx.strokeStyle = '#06b6d4'
  ctx.beginPath()
  
  const sliceWidth = width / bufferLength
  let x = 0
  
  for (let i = 0; i < bufferLength; i++) {
    const v = timeDataArray[i] / 128.0
    const y = (v * height) / 2
    
    if (i === 0) {
      ctx.moveTo(x, y)
    } else {
      ctx.lineTo(x, y)
    }
    
    x += sliceWidth
  }
  
  ctx.lineTo(width, height / 2)
  ctx.stroke()
}

function drawStaticWaveform() {
  if (!waveformCtx.value || staticWaveformData.value.length === 0) return
  
  const canvas = waveformCanvas.value
  const ctx = waveformCtx.value
  const width = canvas.width / (window.devicePixelRatio || 1)
  const height = canvas.height / (window.devicePixelRatio || 1)
  
  ctx.fillStyle = 'rgba(15, 23, 42, 0.95)'
  ctx.fillRect(0, 0, width, height)
  
  const barWidth = width / staticWaveformData.value.length
  const centerY = height / 2
  
  ctx.fillStyle = '#06b6d4'
  
  for (let i = 0; i < staticWaveformData.value.length; i++) {
    const barHeight = staticWaveformData.value[i] * height * 0.4
    const x = i * barWidth
    
    ctx.fillRect(x, centerY - barHeight, barWidth - 1, barHeight * 2)
  }
}

function drawStaticWaveformWithProgress() {
  if (!waveformCtx.value || staticWaveformData.value.length === 0 || !duration.value) return
  
  const canvas = waveformCanvas.value
  const ctx = waveformCtx.value
  const width = canvas.width / (window.devicePixelRatio || 1)
  const height = canvas.height / (window.devicePixelRatio || 1)
  
  ctx.fillStyle = 'rgba(15, 23, 42, 0.95)'
  ctx.fillRect(0, 0, width, height)
  
  const barWidth = width / staticWaveformData.value.length
  const centerY = height / 2
  const progressX = (currentTime.value / duration.value) * width
  
  for (let i = 0; i < staticWaveformData.value.length; i++) {
    const barHeight = staticWaveformData.value[i] * height * 0.4
    const x = i * barWidth
    
    ctx.fillStyle = x < progressX ? '#06b6d4' : '#475569'
    ctx.fillRect(x, centerY - barHeight, barWidth - 1, barHeight * 2)
  }
}

function parseLyrics(trackName) {
  lyrics.value = [
    { time: 0, text: '♪ 音乐播放中...' },
    { time: 5, text: '欢迎使用音频可视化播放器' },
    { time: 10, text: '支持多种音频格式播放' },
    { time: 15, text: '频谱动画实时显示' },
    { time: 20, text: '波形图可视化效果' },
    { time: 25, text: '拖拽上传音频文件' },
    { time: 30, text: '创建您的播放列表' },
    { time: 35, text: '调节音量和播放速度' },
    { time: 40, text: '享受音乐的美妙' },
    { time: 45, text: '♪ 旋律在心中回荡...' }
  ]
  lyricsFormat.value = 'default'
  currentLyricIndex.value = 0
}

function updateLyricIndex() {
  const time = currentTime.value
  let index = -1
  
  for (let i = lyrics.value.length - 1; i >= 0; i--) {
    if (time >= lyrics.value[i].time) {
      index = i
      break
    }
  }
  
  if (index !== currentLyricIndex.value && index !== -1) {
    currentLyricIndex.value = index
    scrollToLyric(index)
  }
}

function scrollToLyric(index) {
  nextTick(() => {
    const container = lyricsContainer.value
    const lines = container?.querySelectorAll('.lyrics-line')
    if (lines && lines[index]) {
      lines[index].scrollIntoView({ behavior: 'smooth', block: 'center' })
    }
  })
}

function formatTime(seconds) {
  if (!seconds || isNaN(seconds)) return '0:00'
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

function handleResize() {
  if (spectrumCanvas.value) resizeCanvas(spectrumCanvas.value)
  if (waveformCanvas.value) resizeCanvas(waveformCanvas.value)
}

onMounted(() => {
  initCanvas()
  initWaveformWorker()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  cancelAnimationFrame(animationId)
  
  if (audioElement.value) {
    audioElement.value.pause()
    audioElement.value.remove()
  }
  
  playlist.value.forEach(track => URL.revokeObjectURL(track.url))
  
  if (audioContext.value) {
    audioContext.value.close()
  }
  
  if (waveformWorker.value) {
    waveformWorker.value.postMessage({ type: 'cleanup' })
    waveformWorker.value.terminate()
  }
})

watch(volume, setVolume)
watch(playbackRate, setPlaybackRate)
</script>

<style scoped>
.app-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  padding: 20px;
  max-width: 1600px;
  margin: 0 auto;
}

.app-header {
  text-align: center;
  margin-bottom: 20px;
}

.app-header h1 {
  font-size: 2rem;
  background: linear-gradient(90deg, #06b6d4, #8b5cf6, #ec4899);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.app-main {
  display: flex;
  gap: 20px;
  flex: 1;
  min-height: 0;
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 20px;
  min-width: 0;
}

.visualizer-section {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 16px;
  padding: 20px;
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.drop-zone {
  position: relative;
  height: 400px;
  border: 2px dashed rgba(255, 255, 255, 0.2);
  border-radius: 12px;
  overflow: hidden;
  transition: all 0.3s ease;
}

.drop-zone.drag-over {
  border-color: #06b6d4;
  background: rgba(6, 182, 212, 0.1);
}

.spectrum-canvas,
.waveform-canvas {
  position: absolute;
  left: 0;
  width: 100%;
}

.spectrum-canvas {
  top: 0;
  height: 50%;
}

.waveform-canvas {
  bottom: 0;
  height: 50%;
}

.drop-hint {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
  color: rgba(255, 255, 255, 0.6);
  z-index: 10;
}

.drop-hint p {
  margin-bottom: 16px;
  font-size: 1.1rem;
}

.upload-btn {
  padding: 10px 24px;
  background: linear-gradient(90deg, #06b6d4, #8b5cf6);
  border: none;
  border-radius: 25px;
  color: white;
  font-size: 1rem;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
}

.upload-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 15px rgba(6, 182, 212, 0.4);
}

.lyrics-section {
  margin-top: 20px;
  height: 180px;
  overflow: hidden;
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.2);
  position: relative;
}

.lyrics-header {
  position: absolute;
  top: 8px;
  right: 8px;
  z-index: 10;
  display: flex;
  gap: 8px;
  align-items: center;
}

.lyrics-format-badge {
  padding: 4px 8px;
  background: rgba(139, 92, 246, 0.3);
  border-radius: 4px;
  font-size: 0.75rem;
  color: #a78bfa;
}

.translate-btn {
  padding: 4px 12px;
  background: rgba(6, 182, 212, 0.2);
  border: 1px solid rgba(6, 182, 212, 0.3);
  border-radius: 4px;
  font-size: 0.75rem;
  color: #06b6d4;
  cursor: pointer;
  transition: all 0.2s;
}

.translate-btn:hover,
.translate-btn.active {
  background: rgba(6, 182, 212, 0.4);
}

.lyrics-container {
  height: 100%;
  overflow-y: auto;
  padding: 30px 10px 10px;
  text-align: center;
}

.lyrics-line {
  padding: 8px;
  color: rgba(255, 255, 255, 0.5);
  transition: all 0.3s ease;
}

.original-text {
  font-size: 1rem;
}

.translation-text {
  font-size: 0.85rem;
  color: rgba(6, 182, 212, 0.7);
  margin-top: 4px;
}

.lyrics-line.active {
  color: #06b6d4;
}

.lyrics-line.active .original-text {
  font-size: 1.2rem;
  font-weight: bold;
  text-shadow: 0 0 10px rgba(6, 182, 212, 0.5);
}

.lyrics-line.active .translation-text {
  color: rgba(6, 182, 212, 0.9);
}

.no-lyrics {
  padding: 20px;
  color: rgba(255, 255, 255, 0.4);
}

.translating-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 20px;
  color: #8b5cf6;
  font-size: 0.9rem;
}

.spinner {
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 2px solid rgba(139, 92, 246, 0.3);
  border-top-color: #8b5cf6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.control-section {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 16px;
  padding: 24px;
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.track-info {
  text-align: center;
  margin-bottom: 16px;
}

.track-name {
  font-size: 1.3rem;
  font-weight: 600;
  margin-bottom: 8px;
  color: #fff;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.track-time {
  color: rgba(255, 255, 255, 0.6);
  font-size: 0.9rem;
}

.progress-bar {
  height: 6px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 3px;
  cursor: pointer;
  margin-bottom: 20px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #06b6d4, #8b5cf6);
  border-radius: 3px;
  transition: width 0.1s linear;
}

.controls {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 20px;
  margin-bottom: 20px;
}

.control-btn {
  width: 50px;
  height: 50px;
  border-radius: 50%;
  border: none;
  background: rgba(255, 255, 255, 0.1);
  color: white;
  font-size: 1.2rem;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.control-btn:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.2);
  transform: scale(1.1);
}

.control-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.control-btn.play-btn {
  width: 70px;
  height: 70px;
  font-size: 1.8rem;
  background: linear-gradient(135deg, #06b6d4, #8b5cf6);
  box-shadow: 0 4px 15px rgba(139, 92, 246, 0.4);
}

.control-btn.play-btn:hover {
  box-shadow: 0 6px 20px rgba(139, 92, 246, 0.6);
}

.extra-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 20px;
}

.volume-control,
.speed-control,
.fps-control {
  display: flex;
  align-items: center;
  gap: 10px;
  color: rgba(255, 255, 255, 0.8);
}

.fps-control {
  font-size: 0.9rem;
  padding: 4px 8px;
  background: rgba(6, 182, 212, 0.2);
  border-radius: 4px;
}

.volume-control input[type="range"] {
  width: 120px;
  height: 6px;
  -webkit-appearance: none;
  appearance: none;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 3px;
  cursor: pointer;
}

.volume-control input[type="range"]::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #06b6d4;
  cursor: pointer;
  transition: transform 0.2s;
}

.volume-control input[type="range"]::-webkit-slider-thumb:hover {
  transform: scale(1.2);
}

.speed-control select {
  padding: 6px 12px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 6px;
  color: white;
  cursor: pointer;
  outline: none;
}

.speed-control select option {
  background: #1a1a2e;
  color: white;
}

.toolbar {
  display: flex;
  gap: 10px;
}

.tool-btn {
  flex: 1;
  padding: 12px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  color: rgba(255, 255, 255, 0.8);
  cursor: pointer;
  transition: all 0.2s;
  font-size: 0.95rem;
}

.tool-btn:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(255, 255, 255, 0.2);
}

.tool-btn.active {
  background: rgba(6, 182, 212, 0.2);
  border-color: #06b6d4;
  color: #06b6d4;
}

.tool-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.equalizer-section,
.cutter-section {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 16px;
  padding: 20px;
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.section-header h3 {
  color: #fff;
  font-size: 1.1rem;
}

.eq-presets {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.eq-presets button {
  padding: 6px 12px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 4px;
  color: rgba(255, 255, 255, 0.8);
  font-size: 0.8rem;
  cursor: pointer;
  transition: all 0.2s;
}

.eq-presets button:hover,
.eq-presets button.active {
  background: rgba(6, 182, 212, 0.3);
  border-color: #06b6d4;
  color: #06b6d4;
}

.eq-bands {
  display: flex;
  justify-content: space-around;
  align-items: flex-end;
  gap: 10px;
  margin-bottom: 20px;
  padding: 20px 0;
  min-height: 200px;
}

.eq-band {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.eq-slider {
  height: 150px;
  display: flex;
  align-items: center;
}

.eq-slider input[type="range"] {
  width: 150px;
  height: 8px;
  -webkit-appearance: none;
  appearance: none;
  background: linear-gradient(to right, #ef4444, #22c55e, #ef4444);
  border-radius: 4px;
  cursor: pointer;
  transform: rotate(-90deg);
}

.eq-slider input[type="range"]::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #06b6d4;
  cursor: pointer;
  box-shadow: 0 0 10px rgba(6, 182, 212, 0.5);
}

.eq-label {
  font-size: 0.75rem;
  color: rgba(255, 255, 255, 0.6);
}

.eq-value {
  font-size: 0.8rem;
  color: #06b6d4;
  font-weight: bold;
}

.reset-eq-btn {
  width: 100%;
  padding: 10px;
  background: rgba(239, 68, 68, 0.2);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 6px;
  color: #ef4444;
  cursor: pointer;
  transition: all 0.2s;
}

.reset-eq-btn:hover {
  background: rgba(239, 68, 68, 0.3);
}

.cutter-waveform {
  position: relative;
  height: 100px;
  background: #0f172a;
  border-radius: 8px;
  margin-bottom: 20px;
  cursor: pointer;
}

.cutter-canvas {
  width: 100%;
  height: 100%;
  border-radius: 8px;
}

.cutter-selection {
  position: absolute;
  top: 0;
  height: 100%;
  background: rgba(6, 182, 212, 0.3);
  border-left: 2px solid #06b6d4;
  border-right: 2px solid #06b6d4;
  pointer-events: none;
}

.cutter-controls {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.time-inputs {
  display: flex;
  gap: 20px;
  flex-wrap: wrap;
}

.time-inputs label {
  display: flex;
  align-items: center;
  gap: 8px;
  color: rgba(255, 255, 255, 0.8);
  font-size: 0.9rem;
}

.time-inputs input[type="number"] {
  width: 80px;
  padding: 6px 10px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 4px;
  color: white;
  font-size: 0.9rem;
}

.cutter-actions {
  display: flex;
  gap: 12px;
}

.preview-btn,
.export-btn {
  flex: 1;
  padding: 12px;
  border-radius: 8px;
  font-size: 0.95rem;
  cursor: pointer;
  transition: all 0.2s;
}

.preview-btn {
  background: rgba(139, 92, 246, 0.2);
  border: 1px solid rgba(139, 92, 246, 0.3);
  color: #a78bfa;
}

.preview-btn:hover {
  background: rgba(139, 92, 246, 0.3);
}

.export-btn {
  background: linear-gradient(135deg, #06b6d4, #8b5cf6);
  border: none;
  color: white;
  font-weight: bold;
}

.export-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 15px rgba(139, 92, 246, 0.4);
}

.export-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.close-btn {
  width: 30px;
  height: 30px;
  background: rgba(255, 255, 255, 0.1);
  border: none;
  border-radius: 50%;
  color: rgba(255, 255, 255, 0.6);
  cursor: pointer;
  font-size: 1rem;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.close-btn:hover {
  background: rgba(239, 68, 68, 0.3);
  color: #ef4444;
}

.playlist-section {
  width: 320px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 16px;
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.playlist-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.playlist-header h3 {
  font-size: 1.2rem;
  color: #fff;
}

.clear-btn {
  padding: 6px 12px;
  background: rgba(239, 68, 68, 0.2);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 6px;
  color: #ef4444;
  font-size: 0.85rem;
  cursor: pointer;
  transition: all 0.2s;
}

.clear-btn:hover {
  background: rgba(239, 68, 68, 0.3);
}

.playlist-items {
  flex: 1;
  overflow-y: auto;
  padding: 10px;
}

.playlist-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  margin-bottom: 6px;
}

.playlist-item:hover {
  background: rgba(255, 255, 255, 0.08);
}

.playlist-item.active {
  background: rgba(6, 182, 212, 0.2);
  border-left: 3px solid #06b6d4;
}

.item-index {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.85rem;
  color: rgba(255, 255, 255, 0.5);
}

.playlist-item.active .item-index {
  color: #06b6d4;
  font-weight: bold;
}

.item-info {
  flex: 1;
  min-width: 0;
}

.item-name {
  font-size: 0.95rem;
  color: #fff;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-bottom: 4px;
}

.item-duration {
  font-size: 0.8rem;
  color: rgba(255, 255, 255, 0.5);
}

.remove-btn {
  width: 24px;
  height: 24px;
  border: none;
  background: transparent;
  color: rgba(255, 255, 255, 0.4);
  cursor: pointer;
  border-radius: 4px;
  transition: all 0.2s;
  opacity: 0;
}

.playlist-item:hover .remove-btn {
  opacity: 1;
}

.remove-btn:hover {
  background: rgba(239, 68, 68, 0.3);
  color: #ef4444;
}

.empty-playlist {
  text-align: center;
  padding: 40px 20px;
  color: rgba(255, 255, 255, 0.4);
  font-size: 0.95rem;
}

@media (max-width: 900px) {
  .app-main {
    flex-direction: column;
  }
  
  .playlist-section {
    width: 100%;
    max-height: 300px;
  }
  
  .drop-zone {
    height: 300px;
  }
  
  .eq-bands {
    overflow-x: auto;
    padding: 20px 10px;
  }
  
  .eq-band {
    min-width: 40px;
  }
}
</style>
