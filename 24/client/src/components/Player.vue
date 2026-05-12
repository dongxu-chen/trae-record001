<template>
  <div class="player-wrapper">
    <div v-if="showLyrics && lyrics.length > 0" class="lyrics-panel">
      <div class="lyrics-header">
        <h3>歌词</h3>
        <button @click="showLyrics = false" class="close-btn">✕</button>
      </div>
      <div class="lyrics-content" ref="lyricsContainer">
        <div v-if="isLoadingLyrics" class="loading">加载歌词中...</div>
        <div v-else-if="lyrics.length === 0" class="no-lyrics">暂无歌词</div>
        <ul v-else class="lyrics-list">
          <li
            v-for="(lyric, index) in lyrics"
            :key="index"
            class="lyric-item"
            :class="{ 'is-active': index === currentLyricIndex }"
            :ref="el => { if (index === currentLyricIndex) activeLyricRef = el }"
            @click="jumpToLyric(lyric.time)"
          >
            {{ lyric.text }}
          </li>
        </ul>
      </div>
    </div>

    <div class="player">
      <audio ref="audioRef"></audio>

      <div class="player-content">
        <div class="song-info" @click="toggleLyrics">
          <div class="cover">
            <img v-if="currentSong?.cover" :src="currentSong.cover" :alt="currentSong.title" />
            <div v-else class="cover-placeholder">♪</div>
          </div>
          <div class="song-details">
            <h3>{{ currentSong?.title || '未播放' }}</h3>
            <p>{{ currentSong?.artist || '-' }}</p>
            <p v-if="currentLyric" class="current-lyric-text">{{ currentLyric.text }}</p>
          </div>
        </div>

        <div class="controls">
          <button @click="playPrev" :disabled="!hasPrevSong" class="control-btn">
            ⏮
          </button>
          <button @click="togglePlay" class="control-btn play-btn">
            {{ isPlaying ? '⏸' : '▶' }}
          </button>
          <button @click="playNext" :disabled="!hasNextSong" class="control-btn">
            ⏭
          </button>
          <button @click="toggleLoopMode" class="control-btn loop-btn" :class="{ 'is-active': loopMode !== 'none' }">
            {{ loopModeIcon }}
          </button>
        </div>

        <div class="progress-section">
          <div class="time">
            <span>{{ formatTime(currentTime) }}</span>
          </div>
          <div class="progress-bar-container">
            <input
              type="range"
              min="0"
              :max="duration || 100"
              :value="currentTime"
              @input="handleProgressChange"
              class="progress-bar"
            />
            <div class="progress-fill" :style="{ width: progressPercent + '%' }"></div>
          </div>
          <div class="time">
            <span>{{ formatTime(duration) }}</span>
          </div>
        </div>

        <div class="extra-controls">
          <button @click="toggleLyrics" class="control-btn lyrics-btn" :class="{ 'is-active': showLyrics }">
            📜
          </button>
          <div class="volume-section">
            <span>🔊</span>
            <input
              type="range"
              min="0"
              max="1"
              step="0.1"
              :value="volume"
              @input="handleVolumeChange"
              class="volume-bar"
            />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch, nextTick } from 'vue'
import { useAudioStore } from '../store/audio'

const audioStore = useAudioStore()
const audioRef = ref(null)
const lyricsContainer = ref(null)
const activeLyricRef = ref(null)
const showLyrics = ref(false)

const {
  currentSong,
  isPlaying,
  currentTime,
  duration,
  volume,
  loopMode,
  lyrics,
  currentLyricIndex,
  currentLyric,
  isLoadingLyrics,
  hasPrevSong,
  hasNextSong,
  togglePlay,
  playNext,
  playPrev,
  setTime,
  setVolume,
  setAudioElement,
  toggleLoopMode,
  formatTime
} = audioStore

const loopModeIcon = computed(() => {
  if (loopMode === 'one') return '🔂'
  if (loopMode === 'all') return '🔁'
  return '🔄'
})

const progressPercent = computed(() => {
  if (duration === 0) return 0
  return (currentTime / duration) * 100
})

function handleProgressChange(event) {
  const time = parseFloat(event.target.value)
  setTime(time)
}

function handleVolumeChange(event) {
  const vol = parseFloat(event.target.value)
  setVolume(vol)
}

function toggleLyrics() {
  showLyrics.value = !showLyrics.value
}

function jumpToLyric(time) {
  setTime(time)
}

watch(currentLyricIndex, async () => {
  if (showLyrics.value && activeLyricRef.value && lyricsContainer.value) {
    await nextTick()
    activeLyricRef.value.scrollIntoView({
      behavior: 'smooth',
      block: 'center'
    })
  }
})

onMounted(() => {
  if (audioRef.value) {
    setAudioElement(audioRef.value)
  }
})
</script>

<style scoped>
.player-wrapper {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 1000;
}

.lyrics-panel {
  position: absolute;
  bottom: 100%;
  left: 0;
  right: 0;
  max-height: 300px;
  background: linear-gradient(135deg, #2d2d44 0%, #1e1e2e 100%);
  border-top-left-radius: 16px;
  border-top-right-radius: 16px;
  box-shadow: 0 -4px 20px rgba(0, 0, 0, 0.3);
  display: flex;
  flex-direction: column;
}

.lyrics-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 2rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.lyrics-header h3 {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  color: white;
}

.close-btn {
  background: transparent;
  color: #aaa;
  font-size: 1.2rem;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  transition: all 0.2s ease;
}

.close-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  color: white;
}

.lyrics-content {
  flex: 1;
  overflow-y: auto;
  padding: 1rem 2rem;
}

.loading, .no-lyrics {
  text-align: center;
  color: #888;
  padding: 2rem;
}

.lyrics-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.lyric-item {
  padding: 0.75rem 0;
  color: #888;
  font-size: 0.95rem;
  cursor: pointer;
  transition: all 0.3s ease;
  text-align: center;
}

.lyric-item:hover {
  color: #ccc;
}

.lyric-item.is-active {
  color: #667eea;
  font-size: 1.1rem;
  font-weight: 600;
  transform: scale(1.02);
}

.player {
  background: linear-gradient(135deg, #1e1e2e 0%, #2d2d44 100%);
  color: white;
  padding: 1rem 2rem;
  box-shadow: 0 -2px 20px rgba(0, 0, 0, 0.3);
}

.player-content {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  gap: 2rem;
  flex-wrap: wrap;
}

.song-info {
  display: flex;
  align-items: center;
  gap: 1rem;
  min-width: 200px;
  cursor: pointer;
  padding: 0.5rem;
  border-radius: 8px;
  transition: background 0.2s ease;
}

.song-info:hover {
  background: rgba(255, 255, 255, 0.05);
}

.cover {
  width: 60px;
  height: 60px;
  border-radius: 8px;
  overflow: hidden;
  background: #444;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.cover-placeholder {
  font-size: 2rem;
  color: #888;
}

.song-details {
  min-width: 0;
}

.song-details h3 {
  font-size: 1rem;
  font-weight: 600;
  margin-bottom: 0.25rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 150px;
}

.song-details p {
  font-size: 0.85rem;
  color: #aaa;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 150px;
  margin: 0;
}

.current-lyric-text {
  color: #667eea !important;
  font-weight: 500;
}

.controls {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.control-btn {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: transparent;
  color: white;
  font-size: 1rem;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}

.control-btn:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.1);
}

.control-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.play-btn {
  width: 50px;
  height: 50px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  font-size: 1.2rem;
}

.play-btn:hover {
  transform: scale(1.05);
}

.loop-btn.is-active,
.lyrics-btn.is-active {
  color: #667eea;
  background: rgba(102, 126, 234, 0.2);
}

.progress-section {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex: 1;
  min-width: 250px;
}

.time {
  font-size: 0.85rem;
  color: #aaa;
  min-width: 45px;
  text-align: center;
}

.progress-bar-container {
  flex: 1;
  position: relative;
  height: 4px;
}

.progress-bar {
  width: 100%;
  height: 4px;
  -webkit-appearance: none;
  appearance: none;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 2px;
  cursor: pointer;
  position: relative;
  z-index: 2;
}

.progress-bar::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #667eea;
  cursor: pointer;
}

.progress-bar::-moz-range-thumb {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #667eea;
  cursor: pointer;
  border: none;
}

.progress-fill {
  position: absolute;
  top: 0;
  left: 0;
  height: 4px;
  background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
  border-radius: 2px;
  pointer-events: none;
}

.extra-controls {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.volume-section {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.volume-bar {
  width: 80px;
  height: 4px;
  -webkit-appearance: none;
  appearance: none;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 2px;
  cursor: pointer;
}

.volume-bar::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #667eea;
  cursor: pointer;
}

.volume-bar::-moz-range-thumb {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #667eea;
  cursor: pointer;
  border: none;
}

@media (max-width: 768px) {
  .player-content {
    gap: 1rem;
  }

  .song-details h3,
  .song-details p {
    max-width: 100px;
  }

  .progress-section {
    order: 5;
    width: 100%;
    min-width: auto;
  }

  .extra-controls {
    margin-left: auto;
  }
}
</style>
