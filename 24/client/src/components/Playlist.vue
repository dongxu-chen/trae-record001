<template>
  <div class="playlist">
    <div v-if="recommendedSongs.length > 0" class="recommend-section">
      <h3 class="section-title">🎵 为你推荐</h3>
      <div class="recommend-grid">
        <div
          v-for="song in recommendedSongs"
          :key="song._id"
          class="recommend-card"
          :class="{ 'is-active': currentSong?._id === song._id }"
          @click="playSong(song)"
        >
          <div class="recommend-cover">
            <img v-if="song.cover" :src="song.cover" :alt="song.title" />
            <div v-else class="cover-placeholder">♪</div>
            <div class="play-overlay">▶</div>
          </div>
          <div class="recommend-info">
            <h4>{{ song.title }}</h4>
            <p>{{ song.artist }}</p>
          </div>
        </div>
      </div>
    </div>

    <div v-if="similarSongs.length > 0 && currentSong" class="recommend-section">
      <h3 class="section-title">✨ 相似歌曲</h3>
      <div class="recommend-grid">
        <div
          v-for="song in similarSongs"
          :key="song._id"
          class="recommend-card"
          :class="{ 'is-active': currentSong?._id === song._id }"
          @click="playSong(song)"
        >
          <div class="recommend-cover">
            <img v-if="song.cover" :src="song.cover" :alt="song.title" />
            <div v-else class="cover-placeholder">♪</div>
            <div class="play-overlay">▶</div>
          </div>
          <div class="recommend-info">
            <h4>{{ song.title }}</h4>
            <p>{{ song.artist }}</p>
          </div>
        </div>
      </div>
    </div>

    <div class="playlist-header">
      <h2>全部歌曲</h2>
      <button @click="showAddForm = !showAddForm" class="add-btn">
        {{ showAddForm ? '取消' : '+ 添加歌曲' }}
      </button>
    </div>

    <div v-if="showAddForm" class="add-form">
      <input
        v-model="newSong.title"
        type="text"
        placeholder="歌曲名称 *"
      />
      <input
        v-model="newSong.artist"
        type="text"
        placeholder="艺术家 *"
      />
      <input
        v-model="newSong.album"
        type="text"
        placeholder="专辑 (可选)"
      />
      <input
        v-model="newSong.url"
        type="text"
        placeholder="音乐 URL *"
      />
      <input
        v-model="newSong.cover"
        type="text"
        placeholder="封面 URL (可选)"
      />
      <textarea
        v-model="newSong.lyrics"
        placeholder="LRC 歌词 (可选)"
        rows="3"
      ></textarea>
      <button @click="handleAddSong" class="submit-btn">添加</button>
    </div>

    <div v-if="isLoading" class="loading">加载中...</div>

    <div v-else-if="playlist.length === 0" class="empty">
      暂无歌曲，请添加音乐
    </div>

    <ul v-else class="song-list">
      <li
        v-for="(song, index) in playlist"
        :key="song._id"
        class="song-item"
        :class="{ 'is-active': currentSong?._id === song._id }"
        @click="playSong(song)"
      >
        <div class="song-number">
          <span v-if="currentSong?._id === song._id && isPlaying">♪</span>
          <span v-else>{{ index + 1 }}</span>
        </div>
        <div class="song-info">
          <div class="cover">
            <img v-if="song.cover" :src="song.cover" :alt="song.title" />
            <div v-else class="cover-placeholder">♪</div>
          </div>
          <div class="song-details">
            <h3>{{ song.title }}</h3>
            <p>{{ song.artist }}{{ song.album ? ' · ' + song.album : '' }}</p>
            <p v-if="song.playCount" class="play-count">播放 {{ song.playCount }} 次</p>
          </div>
        </div>
        <div class="song-duration">
          {{ formatTime(song.duration) }}
        </div>
      </li>
    </ul>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive } from 'vue'
import { useAudioStore } from '../store/audio'

const audioStore = useAudioStore()

const {
  playlist,
  currentSong,
  isPlaying,
  isLoading,
  recommendedSongs,
  similarSongs,
  fetchSongs,
  fetchRecommendedSongs,
  fetchPopularSongs,
  addSong,
  playSong,
  formatTime
} = audioStore

const showAddForm = ref(false)
const newSong = reactive({
  title: '',
  artist: '',
  album: '',
  url: '',
  cover: '',
  lyrics: ''
})

function handleAddSong() {
  if (!newSong.title || !newSong.artist || !newSong.url) {
    alert('请填写歌曲名称、艺术家和音乐 URL')
    return
  }

  addSong({
    title: newSong.title,
    artist: newSong.artist,
    album: newSong.album || undefined,
    url: newSong.url,
    cover: newSong.cover || undefined,
    lyrics: newSong.lyrics || undefined
  })

  newSong.title = ''
  newSong.artist = ''
  newSong.album = ''
  newSong.url = ''
  newSong.cover = ''
  newSong.lyrics = ''
  showAddForm.value = false
}

onMounted(async () => {
  await fetchSongs()
  await fetchRecommendedSongs(6)
  await fetchPopularSongs(6)
})
</script>

<style scoped>
.playlist {
  max-width: 1000px;
  margin: 0 auto;
}

.recommend-section {
  margin-bottom: 2rem;
}

.section-title {
  font-size: 1.2rem;
  font-weight: 600;
  color: #333;
  margin-bottom: 1rem;
}

.recommend-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 1rem;
}

.recommend-card {
  background: white;
  border-radius: 12px;
  padding: 0.75rem;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.recommend-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.12);
}

.recommend-card.is-active {
  box-shadow: 0 0 0 2px #667eea;
}

.recommend-cover {
  position: relative;
  width: 100%;
  padding-bottom: 100%;
  border-radius: 8px;
  overflow: hidden;
  background: #f0f0f0;
  margin-bottom: 0.75rem;
}

.recommend-cover img,
.recommend-cover .cover-placeholder {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 2rem;
  color: #aaa;
}

.play-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.2s ease;
  color: white;
  font-size: 2rem;
}

.recommend-card:hover .play-overlay {
  opacity: 1;
}

.recommend-info h4 {
  font-size: 0.9rem;
  font-weight: 600;
  margin-bottom: 0.25rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  color: #333;
}

.recommend-info p {
  font-size: 0.8rem;
  color: #888;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin: 0;
}

.playlist-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.playlist-header h2 {
  font-size: 1.5rem;
  font-weight: 600;
  color: #333;
}

.add-btn {
  padding: 0.6rem 1.2rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-radius: 6px;
  font-weight: 500;
  transition: all 0.2s ease;
}

.add-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.add-form {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 0.75rem;
  padding: 1.5rem;
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.08);
  margin-bottom: 1.5rem;
}

.add-form input,
.add-form textarea {
  padding: 0.8rem 1rem;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 0.95rem;
  transition: all 0.2s ease;
  font-family: inherit;
}

.add-form textarea {
  grid-column: 1 / -1;
  resize: vertical;
  min-height: 80px;
}

.add-form input:focus,
.add-form textarea:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.submit-btn {
  padding: 0.8rem 1.5rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-radius: 6px;
  font-weight: 500;
  transition: all 0.2s ease;
}

.submit-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.loading, .empty {
  text-align: center;
  padding: 3rem;
  color: #888;
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.08);
}

.song-list {
  list-style: none;
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.08);
  overflow: hidden;
}

.song-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem 1.5rem;
  cursor: pointer;
  transition: background 0.2s ease;
}

.song-item:hover {
  background: #f8f8f8;
}

.song-item.is-active {
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
}

.song-item + .song-item {
  border-top: 1px solid #eee;
}

.song-number {
  width: 30px;
  text-align: center;
  font-size: 0.9rem;
  color: #888;
  font-weight: 500;
}

.song-item.is-active .song-number {
  color: #667eea;
}

.song-info {
  display: flex;
  align-items: center;
  gap: 1rem;
  flex: 1;
  min-width: 0;
}

.cover {
  width: 50px;
  height: 50px;
  border-radius: 6px;
  overflow: hidden;
  background: #f0f0f0;
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
  font-size: 1.5rem;
  color: #aaa;
}

.song-details {
  min-width: 0;
}

.song-details h3 {
  font-size: 1rem;
  font-weight: 500;
  margin-bottom: 0.25rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.song-item.is-active .song-details h3 {
  color: #667eea;
  font-weight: 600;
}

.song-details p {
  font-size: 0.85rem;
  color: #888;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin: 0;
}

.play-count {
  font-size: 0.75rem !important;
  color: #aaa !important;
}

.song-duration {
  font-size: 0.85rem;
  color: #888;
  flex-shrink: 0;
}
</style>
