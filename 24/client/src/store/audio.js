import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import axios from 'axios'
import { parseLRC, findCurrentLyricIndex } from '../utils/lyric_parser'

const LOOP_MODE_KEY = 'audio_loop_mode'
const USER_ID_KEY = 'music_user_id'

function generateUserId() {
  return 'user_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9)
}

function getOrCreateUserId() {
  let userId = localStorage.getItem(USER_ID_KEY)
  if (!userId) {
    userId = generateUserId()
    localStorage.setItem(USER_ID_KEY, userId)
  }
  return userId
}

export const useAudioStore = defineStore('audio', () => {
  const playlist = ref([])
  const currentSong = ref(null)
  const isPlaying = ref(false)
  const currentTime = ref(0)
  const duration = ref(0)
  const volume = ref(0.8)
  const isLoading = ref(false)
  const audioElement = ref(null)
  const loopMode = ref(localStorage.getItem(LOOP_MODE_KEY) || 'none')
  const userId = ref(getOrCreateUserId())

  const lyrics = ref([])
  const currentLyricIndex = ref(-1)
  const isLoadingLyrics = ref(false)

  const recommendedSongs = ref([])
  const popularSongs = ref([])
  const similarSongs = ref([])
  const isLoadingRecommendations = ref(false)

  const currentIndex = computed(() => {
    if (!currentSong.value) return -1
    return playlist.value.findIndex(song => song._id === currentSong.value._id)
  })

  const hasNextSong = computed(() => {
    return currentIndex.value < playlist.value.length - 1
  })

  const hasPrevSong = computed(() => {
    return currentIndex.value > 0
  })

  const currentLyric = computed(() => {
    if (currentLyricIndex.value >= 0 && currentLyricIndex.value < lyrics.value.length) {
      return lyrics.value[currentLyricIndex.value]
    }
    return null
  })

  watch(currentTime, (newTime) => {
    if (lyrics.value.length > 0) {
      currentLyricIndex.value = findCurrentLyricIndex(lyrics.value, newTime)
    }
  })

  watch(currentSong, async (newSong) => {
    if (newSong) {
      await fetchLyrics(newSong._id)
      await recordPlay(newSong._id)
      await fetchSimilarSongs(newSong._id)
    } else {
      lyrics.value = []
      currentLyricIndex.value = -1
    }
  })

  async function fetchSongs() {
    isLoading.value = true
    try {
      const response = await axios.get('/api/songs')
      if (response.data.success) {
        playlist.value = response.data.data
      }
    } catch (error) {
      console.error('Failed to fetch songs:', error)
    } finally {
      isLoading.value = false
    }
  }

  async function addSong(songData) {
    try {
      const response = await axios.post('/api/songs', songData)
      if (response.data.success) {
        playlist.value.unshift(response.data.data)
      }
    } catch (error) {
      console.error('Failed to add song:', error)
    }
  }

  async function fetchLyrics(songId) {
    isLoadingLyrics.value = true
    lyrics.value = []
    currentLyricIndex.value = -1

    try {
      const response = await axios.get(`/api/songs/${songId}/lyrics`)
      if (response.data.success && response.data.data.lyrics) {
        lyrics.value = parseLRC(response.data.data.lyrics)
      }
    } catch (error) {
      console.error('Failed to fetch lyrics:', error)
    } finally {
      isLoadingLyrics.value = false
    }
  }

  async function updateLyrics(songId, lrcContent) {
    try {
      const response = await axios.put(`/api/songs/${songId}/lyrics`, {
        lyrics: lrcContent
      })
      if (response.data.success) {
        if (currentSong.value && currentSong.value._id === songId) {
          lyrics.value = parseLRC(lrcContent)
          currentLyricIndex.value = -1
        }
        const songInPlaylist = playlist.value.find(s => s._id === songId)
        if (songInPlaylist) {
          songInPlaylist.lyrics = lrcContent
        }
        return true
      }
    } catch (error) {
      console.error('Failed to update lyrics:', error)
    }
    return false
  }

  async function fetchRecommendedSongs(topN = 10) {
    isLoadingRecommendations.value = true
    try {
      const response = await axios.get(`/api/recommend/user/${userId.value}?topN=${topN}`)
      if (response.data.success) {
        recommendedSongs.value = response.data.data
      }
    } catch (error) {
      console.error('Failed to fetch recommendations:', error)
    } finally {
      isLoadingRecommendations.value = false
    }
  }

  async function fetchPopularSongs(topN = 10) {
    try {
      const response = await axios.get(`/api/recommend/popular?topN=${topN}`)
      if (response.data.success) {
        popularSongs.value = response.data.data
      }
    } catch (error) {
      console.error('Failed to fetch popular songs:', error)
    }
  }

  async function fetchSimilarSongs(songId, topN = 5) {
    try {
      const response = await axios.get(`/api/recommend/similar/${songId}?topN=${topN}`)
      if (response.data.success) {
        similarSongs.value = response.data.data
      }
    } catch (error) {
      console.error('Failed to fetch similar songs:', error)
    }
  }

  async function recordPlay(songId) {
    try {
      await axios.post('/api/recommend/play', {
        userId: userId.value,
        songId
      })
      await fetchRecommendedSongs()
      await fetchPopularSongs()
    } catch (error) {
      console.error('Failed to record play:', error)
    }
  }

  function setAudioElement(element) {
    audioElement.value = element
    if (element) {
      element.volume = volume.value
      element.addEventListener('timeupdate', updateCurrentTime)
      element.addEventListener('loadedmetadata', updateDuration)
      element.addEventListener('ended', handleSongEnd)
      element.addEventListener('play', () => isPlaying.value = true)
      element.addEventListener('pause', () => isPlaying.value = false)
    }
  }

  function updateCurrentTime() {
    if (audioElement.value) {
      currentTime.value = audioElement.value.currentTime
    }
  }

  function updateDuration() {
    if (audioElement.value) {
      duration.value = audioElement.value.duration
    }
  }

  function handleSongEnd() {
    if (loopMode.value === 'one') {
      if (audioElement.value) {
        audioElement.value.currentTime = 0
        audioElement.value.play()
      }
      return
    }

    if (hasNextSong.value) {
      playNext()
    } else if (loopMode.value === 'all') {
      if (playlist.value.length > 0) {
        playSong(playlist.value[0])
      }
    } else {
      isPlaying.value = false
    }
  }

  function playSong(song) {
    if (!audioElement.value) return

    audioElement.value.pause()
    audioElement.value.src = ''
    audioElement.value.load()

    currentTime.value = 0
    duration.value = 0

    currentSong.value = song
    audioElement.value.src = song.url
    audioElement.value.load()
    audioElement.value.play()
  }

  function toggleLoopMode() {
    const modes = ['none', 'all', 'one']
    const currentIdx = modes.indexOf(loopMode.value)
    const nextIndex = (currentIdx + 1) % modes.length
    loopMode.value = modes[nextIndex]
    localStorage.setItem(LOOP_MODE_KEY, loopMode.value)
  }

  function togglePlay() {
    if (!audioElement.value || !currentSong.value) return

    if (isPlaying.value) {
      audioElement.value.pause()
    } else {
      audioElement.value.play()
    }
  }

  function playNext() {
    if (!hasNextSong.value) return
    const nextSong = playlist.value[currentIndex.value + 1]
    playSong(nextSong)
  }

  function playPrev() {
    if (!hasPrevSong.value) return
    const prevSong = playlist.value[currentIndex.value - 1]
    playSong(prevSong)
  }

  function setTime(time) {
    if (audioElement.value) {
      audioElement.value.currentTime = time
      currentTime.value = time
    }
  }

  function setVolume(newVolume) {
    volume.value = newVolume
    if (audioElement.value) {
      audioElement.value.volume = newVolume
    }
  }

  function formatTime(seconds) {
    if (!seconds || isNaN(seconds)) return '0:00'
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  return {
    playlist,
    currentSong,
    isPlaying,
    currentTime,
    duration,
    volume,
    isLoading,
    loopMode,
    userId,
    lyrics,
    currentLyricIndex,
    currentLyric,
    isLoadingLyrics,
    recommendedSongs,
    popularSongs,
    similarSongs,
    isLoadingRecommendations,
    currentIndex,
    hasNextSong,
    hasPrevSong,
    fetchSongs,
    addSong,
    fetchLyrics,
    updateLyrics,
    fetchRecommendedSongs,
    fetchPopularSongs,
    fetchSimilarSongs,
    recordPlay,
    setAudioElement,
    playSong,
    togglePlay,
    playNext,
    playPrev,
    setTime,
    setVolume,
    toggleLoopMode,
    formatTime
  }
})
