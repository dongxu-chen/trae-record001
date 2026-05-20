import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { ffmpegService } from '../utils/ffmpeg'
import { BackgroundRemovalMethod, BackgroundType } from '../utils/backgroundRemover'
import { SpeechRecognitionProvider } from '../utils/speechToSubtitle'
import { TemplateType, TemplateCategory } from '../utils/templateLibrary'

export const useEditorStore = defineStore('editor', () => {
  const isFFmpegLoaded = ref(false)
  const isLoadingFFmpeg = ref(false)
  const loadProgress = ref(0)

  const mediaLibrary = ref([])
  const videoTrack = ref([])
  const audioTrack = ref([])
  const subtitleTrack = ref([])

  const selectedClipId = ref(null)
  const currentTime = ref(0)
  const isPlaying = ref(false)
  const totalDuration = ref(0)

  const processing = ref(false)
  const processingProgress = ref(0)
  const processingText = ref('')

  const backgroundMusic = ref(null)

  const transitions = ref([
    { id: 'fade', name: '淡入淡出', icon: 'fade' },
    { id: 'dissolve', name: '溶解', icon: 'dissolve' },
    { id: 'wipe_left', name: '左擦除', icon: 'wipe' },
    { id: 'wipe_right', name: '右擦除', icon: 'wipe' },
    { id: 'slide_left', name: '左滑动', icon: 'slide' },
    { id: 'slide_right', name: '右滑动', icon: 'slide' },
    { id: 'circle_in', name: '圆形展开', icon: 'circle' },
    { id: 'pixelize', name: '像素化', icon: 'pixel' },
  ])

  const backgroundRemoval = ref({
    enabled: false,
    method: BackgroundRemovalMethod.CHROMA_KEY,
    chromaKey: {
      color: '#00ff00',
      threshold: 0.4,
      smoothing: 0.1,
      spillSuppression: 0.2,
    },
    colorThreshold: {
      lower: [0, 0, 0],
      upper: [50, 50, 50],
      invert: false,
    },
    background: {
      type: BackgroundType.COLOR,
      color: '#ffffff',
      imageUrl: null,
      blurAmount: 10,
    },
    isProcessing: false,
  })

  const speechRecognition = ref({
    enabled: false,
    isRecording: false,
    isProcessing: false,
    provider: SpeechRecognitionProvider.WEB_SPEECH_API,
    apiKey: '',
    apiEndpoint: '',
    language: 'zh-CN',
    progress: 0,
    currentTranscript: '',
    interimTranscript: '',
  })

  const templateLibrary = ref({
    activeCategory: null,
    activeType: null,
    searchQuery: '',
    showFavoritesOnly: false,
    appliedTemplates: [],
  })

  const selectedClip = computed(() => {
    if (!selectedClipId.value) return null
    return videoTrack.value.find(c => c.id === selectedClipId.value)
  })

  const sortedVideoClips = computed(() => {
    return [...videoTrack.value].sort((a, b) => a.startTime - b.startTime)
  })

  async function loadFFmpeg() {
    if (isFFmpegLoaded.value || isLoadingFFmpeg.value) return

    isLoadingFFmpeg.value = true
    loadProgress.value = 0

    try {
      await ffmpegService.load()
      isFFmpegLoaded.value = true
    } catch (error) {
      console.error('加载FFmpeg失败:', error)
      throw error
    } finally {
      isLoadingFFmpeg.value = false
    }
  }

  function generateId() {
    return Date.now().toString(36) + Math.random().toString(36).substr(2)
  }

  async function addMediaFile(file) {
    const isVideo = file.type.startsWith('video/')
    const isAudio = file.type.startsWith('audio/')

    if (!isVideo && !isAudio) {
      throw new Error('不支持的文件类型')
    }

    const url = URL.createObjectURL(file)
    let info = { duration: 0, width: 0, height: 0 }

    if (isVideo) {
      try {
        info = await ffmpegService.getVideoInfo(file)
      } catch (e) {
        info = await getVideoInfoFromElement(url)
      }
    }

    const mediaItem = {
      id: generateId(),
      file,
      url,
      name: file.name,
      type: isVideo ? 'video' : 'audio',
      size: file.size,
      duration: info.duration,
      width: info.width,
      height: info.height,
      thumbnail: null,
    }

    if (isVideo) {
      try {
        mediaItem.thumbnail = await ffmpegService.generateThumbnail(file, info.duration / 2)
      } catch (e) {
        mediaItem.thumbnail = null
      }
    }

    mediaLibrary.value.push(mediaItem)
    return mediaItem
  }

  function getVideoInfoFromElement(url) {
    return new Promise((resolve) => {
      const video = document.createElement('video')
      video.src = url
      video.muted = true
      video.preload = 'metadata'

      video.onloadedmetadata = () => {
        resolve({
          duration: video.duration,
          width: video.videoWidth,
          height: video.videoHeight,
        })
        video.remove()
      }

      video.onerror = () => {
        resolve({ duration: 0, width: 0, height: 0 })
        video.remove()
      }
    })
  }

  function addToVideoTrack(mediaItem, startTime = null) {
    if (mediaItem.type !== 'video') return

    const lastClip = sortedVideoClips.value[sortedVideoClips.value.length - 1]
    const clipStartTime = startTime !== null ? startTime : (lastClip ? lastClip.endTime : 0)

    const clip = {
      id: generateId(),
      mediaId: mediaItem.id,
      file: mediaItem.file,
      url: mediaItem.url,
      name: mediaItem.name,
      thumbnail: mediaItem.thumbnail,
      startTime: clipStartTime,
      duration: mediaItem.duration,
      endTime: clipStartTime + mediaItem.duration,
      trimStart: 0,
      trimEnd: mediaItem.duration,
      originalDuration: mediaItem.duration,
      transition: null,
      transitionDuration: 1,
      type: 'video',
    }

    videoTrack.value.push(clip)
    updateTotalDuration()
    return clip
  }

  function addToAudioTrack(mediaItem, startTime = 0) {
    if (mediaItem.type !== 'audio') return

    const clip = {
      id: generateId(),
      mediaId: mediaItem.id,
      file: mediaItem.file,
      url: mediaItem.url,
      name: mediaItem.name,
      startTime,
      duration: mediaItem.duration,
      endTime: startTime + mediaItem.duration,
      trimStart: 0,
      trimEnd: mediaItem.duration,
      volume: 1,
      type: 'audio',
    }

    audioTrack.value.push(clip)
    updateTotalDuration()
    return clip
  }

  function addSubtitle(text, startTime, endTime) {
    const subtitle = {
      id: generateId(),
      text,
      startTime,
      endTime,
      style: {
        fontSize: 48,
        color: '#ffffff',
        backgroundColor: 'rgba(0,0,0,0.5)',
        position: 'bottom',
      },
    }

    subtitleTrack.value.push(subtitle)
    return subtitle
  }

  function updateSubtitle(id, updates) {
    const index = subtitleTrack.value.findIndex(s => s.id === id)
    if (index !== -1) {
      subtitleTrack.value[index] = { ...subtitleTrack.value[index], ...updates }
    }
  }

  function removeSubtitle(id) {
    subtitleTrack.value = subtitleTrack.value.filter(s => s.id !== id)
  }

  function selectClip(id) {
    selectedClipId.value = id
  }

  function updateClip(id, updates) {
    const index = videoTrack.value.findIndex(c => c.id === id)
    if (index !== -1) {
      videoTrack.value[index] = { ...videoTrack.value[index], ...updates }
      if (updates.duration !== undefined || updates.startTime !== undefined) {
        videoTrack.value[index].endTime = videoTrack.value[index].startTime + videoTrack.value[index].duration
      }
      updateTotalDuration()
    }
  }

  function removeClip(id) {
    videoTrack.value = videoTrack.value.filter(c => c.id !== id)
    if (selectedClipId.value === id) {
      selectedClipId.value = null
    }
    updateTotalDuration()
  }

  function removeAudioClip(id) {
    audioTrack.value = audioTrack.value.filter(c => c.id !== id)
    updateTotalDuration()
  }

  function moveClip(id, newStartTime) {
    const clip = videoTrack.value.find(c => c.id === id)
    if (clip) {
      clip.startTime = Math.max(0, newStartTime)
      clip.endTime = clip.startTime + clip.duration
      updateTotalDuration()
    }
  }

  function trimClip(id, trimStart, trimEnd) {
    const clip = videoTrack.value.find(c => c.id === id)
    if (clip) {
      const maxTrimEnd = clip.originalDuration
      clip.trimStart = Math.max(0, Math.min(trimStart, maxTrimEnd - 0.1))
      clip.trimEnd = Math.max(clip.trimStart + 0.1, Math.min(trimEnd, maxTrimEnd))
      clip.duration = clip.trimEnd - clip.trimStart
      clip.endTime = clip.startTime + clip.duration
      updateTotalDuration()
    }
  }

  function updateTotalDuration() {
    const maxVideoEnd = videoTrack.value.reduce((max, c) => Math.max(max, c.endTime), 0)
    const maxAudioEnd = audioTrack.value.reduce((max, c) => Math.max(max, c.endTime), 0)
    const maxSubtitleEnd = subtitleTrack.value.reduce((max, s) => Math.max(max, s.endTime), 0)
    totalDuration.value = Math.max(maxVideoEnd, maxAudioEnd, maxSubtitleEnd)
  }

  function setCurrentTime(time) {
    currentTime.value = Math.max(0, Math.min(time, totalDuration.value))
  }

  function togglePlay() {
    isPlaying.value = !isPlaying.value
  }

  function setBackgroundMusic(mediaItem) {
    backgroundMusic.value = mediaItem
  }

  function removeBackgroundMusic() {
    backgroundMusic.value = null
  }

  function removeFromMediaLibrary(id) {
    mediaLibrary.value = mediaLibrary.value.filter(m => m.id !== id)
  }

  function clearAll() {
    videoTrack.value = []
    audioTrack.value = []
    subtitleTrack.value = []
    selectedClipId.value = null
    currentTime.value = 0
    totalDuration.value = 0
    backgroundMusic.value = null
  }

  function setProcessing(active, text = '', progress = 0) {
    processing.value = active
    processingText.value = text
    processingProgress.value = progress
  }

  function setBackgroundRemoval(params) {
    backgroundRemoval.value = { ...backgroundRemoval.value, ...params }
  }

  function setChromaKeyParams(params) {
    backgroundRemoval.value.chromaKey = { ...backgroundRemoval.value.chromaKey, ...params }
  }

  function setBackgroundType(type, params = {}) {
    backgroundRemoval.value.background = { ...backgroundRemoval.value.background, type, ...params }
  }

  function toggleBackgroundRemoval() {
    backgroundRemoval.value.enabled = !backgroundRemoval.value.enabled
  }

  function setSpeechRecognition(params) {
    speechRecognition.value = { ...speechRecognition.value, ...params }
  }

  function toggleSpeechRecording() {
    speechRecognition.value.isRecording = !speechRecognition.value.isRecording
  }

  function setSpeechProvider(provider) {
    speechRecognition.value.provider = provider
  }

  function setTemplateLibrary(params) {
    templateLibrary.value = { ...templateLibrary.value, ...params }
  }

  function applyTemplate(templateId, position = 'start') {
    const applied = {
      id: Date.now().toString(36),
      templateId,
      position,
      clipId: selectedClipId.value,
      appliedAt: Date.now(),
    }
    templateLibrary.value.appliedTemplates.push(applied)
    return applied
  }

  function removeAppliedTemplate(appliedId) {
    templateLibrary.value.appliedTemplates = templateLibrary.value.appliedTemplates.filter(
      t => t.id !== appliedId
    )
  }

  function clearAll() {
    videoTrack.value = []
    audioTrack.value = []
    subtitleTrack.value = []
    selectedClipId.value = null
    currentTime.value = 0
    totalDuration.value = 0
    backgroundMusic.value = null
    backgroundRemoval.value.enabled = false
    templateLibrary.value.appliedTemplates = []
  }

  return {
    isFFmpegLoaded,
    isLoadingFFmpeg,
    loadProgress,
    mediaLibrary,
    videoTrack,
    audioTrack,
    subtitleTrack,
    selectedClipId,
    selectedClip,
    sortedVideoClips,
    currentTime,
    isPlaying,
    totalDuration,
    processing,
    processingProgress,
    processingText,
    backgroundMusic,
    transitions,
    backgroundRemoval,
    speechRecognition,
    templateLibrary,
    loadFFmpeg,
    addMediaFile,
    addToVideoTrack,
    addToAudioTrack,
    addSubtitle,
    updateSubtitle,
    removeSubtitle,
    selectClip,
    updateClip,
    removeClip,
    removeAudioClip,
    moveClip,
    trimClip,
    setCurrentTime,
    togglePlay,
    setBackgroundMusic,
    removeBackgroundMusic,
    removeFromMediaLibrary,
    clearAll,
    setProcessing,
    setBackgroundRemoval,
    setChromaKeyParams,
    setBackgroundType,
    toggleBackgroundRemoval,
    setSpeechRecognition,
    toggleSpeechRecording,
    setSpeechProvider,
    setTemplateLibrary,
    applyTemplate,
    removeAppliedTemplate,
  }
})
