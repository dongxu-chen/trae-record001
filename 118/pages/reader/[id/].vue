<template>
  <div class="reader-container">
    <header class="reader-header">
      <button class="back-btn" @click="handleBack">← 返回</button>
      <h2>{{ book?.title }}</h2>
      <div class="header-controls">
        <span class="connection-status" :class="{ connected: isConnected }">
          {{ isConnected ? '🔵 同步中' : '⚪ 离线' }}
        </span>
        <button @click="addBookmark" class="icon-btn" :title="hasBookmark ? '已加书签' : '添加书签'">
          {{ hasBookmark ? '🔖' : '📑' }}
        </button>
        <button @click="toggleTTSPanel" class="icon-btn" :title="'朗读'">
          {{ isSpeaking ? '🔊' : '🔈' }}
        </button>
        <button @click="toggleSummaryPanel" class="icon-btn" :title="'AI 摘要'">
          🤖
        </button>
        <button @click="toggleSettings" class="icon-btn">⚙️</button>
        <button @click="toggleAnnotations" class="icon-btn">📝</button>
      </div>
    </header>

    <div class="viewer-container">
      <div ref="viewerRef" class="viewer"></div>
    </div>

    <footer class="reader-footer">
      <button @click="prevPage" class="nav-btn" :disabled="!canPrev">◀ 上一页</button>
      <div class="progress-info">
        <span>章节 {{ currentChapter + 1 }} / {{ totalChapters }} · 进度 {{ progress }}%</span>
        <div class="progress-bar">
          <div class="progress-fill" :style="{ width: progress + '%' }"></div>
        </div>
      </div>
      <button @click="nextPage" class="nav-btn" :disabled="!canNext">下一页 ▶</button>
    </footer>

    <div v-if="showSettings" class="settings-panel" @click.self="showSettings = false">
      <div class="settings-content">
        <h3>阅读设置</h3>
        <div class="setting-item">
          <label>字体大小: {{ fontSize }}px</label>
          <input type="range" v-model.number="fontSize" min="12" max="32" @change="applySettings">
        </div>
        <div class="setting-item">
          <label>行高: {{ lineHeight }}</label>
          <input type="range" v-model.number="lineHeight" min="1.2" max="2" step="0.1" @change="applySettings">
        </div>
        <div class="setting-item">
          <label>主题</label>
          <div class="theme-options">
            <button 
              v-for="t in themes" 
              :key="t.name"
              @click="setTheme(t)"
              class="theme-btn"
              :style="{ background: t.bg, color: t.text }"
            >
              {{ t.name }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <div v-if="showTTSPanel" class="tts-panel" @click.self="showTTSPanel = false">
      <div class="tts-content">
        <h3>🔊 文本朗读</h3>
        
        <div class="tts-controls">
          <button @click="toggleSpeak" class="tts-main-btn">
            {{ isSpeaking ? (isPaused ? '▶️ 继续' : '⏸️ 暂停') : '▶️ 开始朗读' }}
          </button>
          <button @click="stopTTS" class="tts-stop-btn" :disabled="!isSpeaking">
            ⏹️ 停止
          </button>
        </div>

        <div class="setting-item">
          <label>语速: {{ ttsOptions.rate }}x</label>
          <input type="range" v-model.number="ttsOptions.rate" min="0.5" max="2" step="0.1">
        </div>

        <div class="setting-item">
          <label>音调: {{ ttsOptions.pitch }}</label>
          <input type="range" v-model.number="ttsOptions.pitch" min="0.5" max="2" step="0.1">
        </div>

        <div class="setting-item">
          <label>音量: {{ Math.round(ttsOptions.volume * 100) }}%</label>
          <input type="range" v-model.number="ttsOptions.volume" min="0" max="1" step="0.1">
        </div>

        <div class="setting-item">
          <label>选择语音</label>
          <select v-model="selectedVoiceIndex" class="voice-select">
            <option v-for="(voice, index) in voices" :key="index" :value="index">
              {{ voice.name }} ({{ voice.lang }})
            </option>
          </select>
        </div>
      </div>
    </div>

    <div v-if="showSummaryPanel" class="summary-panel" @click.self="showSummaryPanel = false">
      <div class="summary-content">
        <h3>🤖 AI 摘要</h3>
        
        <div v-if="isGeneratingSummary" class="loading-summary">
          <span>正在生成摘要...</span>
        </div>
        
        <div v-else class="summary-text">
          <div v-if="bookSummary" class="book-summary">
            <h4>📚 本书摘要</h4>
            <p>{{ bookSummary }}</p>
          </div>
          
          <div v-if="chapterSummaries.length > 0" class="chapter-summaries">
            <h4>📖 章节摘要</h4>
            <div v-for="summary in chapterSummaries" :key="summary.id" class="chapter-summary-item">
              <strong>{{ summary.chapterTitle }}:</strong>
              <p>{{ summary.summary }}</p>
            </div>
          </div>
        </div>

        <div class="summary-actions">
          <button @click="generateBookSummary" class="generate-btn" :disabled="isGeneratingSummary">
            生成书籍摘要
          </button>
          <button @click="generateChapterSummary" class="generate-btn" :disabled="isGeneratingSummary">
            生成当前章节摘要
          </button>
        </div>
      </div>
    </div>

    <div v-if="showAnnotationsPanel" class="annotations-panel" @click.self="showAnnotationsPanel = false">
      <div class="annotations-content">
        <h3>📝 我的笔记</h3>
        
        <div class="tabs">
          <button 
            class="tab-btn" 
            :class="{ active: activeTab === 'annotations' }"
            @click="activeTab = 'annotations'"
          >
            高亮笔记
          </button>
          <button 
            class="tab-btn" 
            :class="{ active: activeTab === 'bookmarks' }"
            @click="activeTab = 'bookmarks'"
          >
            书签
          </button>
        </div>

        <div v-if="activeTab === 'annotations'">
          <div v-if="annotations.length === 0" class="empty-annotations">
            还没有笔记，选中文本添加高亮
          </div>
          <div v-else class="annotations-list">
            <div v-for="ann in annotations" :key="ann.id" class="annotation-item" @click="goToAnnotation(ann)">
              <div class="annotation-text" :style="{ borderLeftColor: ann.color }">
                {{ ann.text }}
              </div>
              <p v-if="ann.note" class="annotation-note">{{ ann.note }}</p>
              <span class="annotation-location">第 {{ getChapterFromCFI(ann.cfi) + 1 }} 章</span>
              <button @click.stop="deleteAnnotation(ann.id)" class="delete-btn">删除</button>
            </div>
          </div>
        </div>

        <div v-if="activeTab === 'bookmarks'">
          <div v-if="bookmarks.length === 0" class="empty-annotations">
            还没有书签，点击顶部 📑 添加
          </div>
          <div v-else class="annotations-list">
            <div v-for="bm in bookmarks" :key="bm.id" class="annotation-item" @click="goToBookmark(bm)">
              <div class="annotation-text" style="borderLeftColor: #f39c12">
                {{ bm.chapter || '书签位置' }}
              </div>
              <p v-if="bm.note" class="annotation-note">{{ bm.note }}</p>
              <span class="annotation-time">{{ formatDate(bm.createdAt) }}</span>
              <button @click.stop="deleteBookmark(bm.id)" class="delete-btn">删除</button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="showHighlightPopup" class="highlight-popup" :style="popupPosition">
      <div class="highlight-colors">
        <button 
          v-for="color in highlightColors" 
          :key="color"
          @click="addHighlight(color)"
          class="color-btn"
          :style="{ background: color }"
        ></button>
      </div>
      <button @click="addNote" class="note-btn">添加批注</button>
    </div>

    <div v-if="showSyncPrompt" class="sync-prompt">
      <div class="sync-content">
        <p>检测到其他设备的阅读进度，是否同步？</p>
        <div class="sync-actions">
          <button @click="showSyncPrompt = false" class="cancel-btn">取消</button>
          <button @click="syncToRemote" class="confirm-btn">同步</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import ePub, { type Book, type Rendition } from 'epubjs'
import { CFIUtils, calculateProgressByCFI } from '~/utils/cfiUtils'

const route = useRoute()
const bookId = parseInt(route.params.id as string)
const viewerRef = ref<HTMLElement | null>(null)

const { data: book } = await useFetch(`/api/books/${bookId}`)
const { data: savedProgress } = await useFetch(`/api/progress/${bookId}`)
const { data: annotations, refresh: refreshAnnotations } = await useFetch(`/api/annotations/${bookId}`)
const { data: bookmarks, refresh: refreshBookmarks } = await useFetch(`/api/bookmarks/${bookId}`)
const { data: chapterSummaries } = await useFetch(`/api/summary/${bookId}/chapters`)

const bookInstance = ref<Book | null>(null)
const rendition = ref<Rendition | null>(null)
const currentLocation = ref('')
const currentChapter = ref(0)
const totalChapters = ref(1)
const progress = ref(0)
const canPrev = ref(false)
const canNext = ref(false)

const showSettings = ref(false)
const showTTSPanel = ref(false)
const showSummaryPanel = ref(false)
const showAnnotationsPanel = ref(false)
const activeTab = ref('annotations')
const fontSize = ref(16)
const lineHeight = ref(1.6)
const currentTheme = ref({ bg: '#ffffff', text: '#333333' })

const themes = [
  { name: '明亮', bg: '#ffffff', text: '#333333' },
  { name: '护眼', bg: '#f5f5dc', text: '#333333' },
  { name: '夜间', bg: '#1a1a1a', text: '#cccccc' }
]

const showHighlightPopup = ref(false)
const popupPosition = ref({ top: '0px', left: '0px' })
const selectedText = ref('')
const selectedCfi = ref('')
const selectedCfiRange = ref<any>(null)
const highlightColors = ['#ffff00', '#90ee90', '#87ceeb', '#ffb6c1', '#dda0dd']

const { isConnected, remoteProgress, syncProgress, connect, updateProgress } = useWebSocket(bookId)
const showSyncPrompt = ref(false)
const pendingSyncCfi = ref('')

const bookSummary = computed(() => book.value?.summary)
const isGeneratingSummary = ref(false)

const hasBookmark = computed(() => {
  return bookmarks.value?.some(bm => bm.cfi === currentLocation.value) || false
})

const readingSessionId = ref<number | null>(null)
const pageReadCount = ref(0)

const { 
  isSpeaking, 
  isPaused, 
  voices,
  options: ttsOptions,
  speak,
  pause,
  resume,
  stop: stopTTS
} = useTTS()

const selectedVoiceIndex = ref(0)

watch(selectedVoiceIndex, (index) => {
  if (voices.value[index]) {
    ttsOptions.value.lang = voices.value[index].lang
  }
})

watch(remoteProgress, (newProgress) => {
  if (newProgress) {
    pendingSyncCfi.value = newProgress.cfi
    showSyncPrompt.value = true
  }
})

watch(syncProgress, (sync) => {
  if (sync && sync.cfi && rendition.value) {
    rendition.value.display(sync.cfi)
  }
})

onMounted(async () => {
  if (book.value && viewerRef.value) {
    await initReader()
    nextTick(() => {
      connect()
    })
  }
})

const initReader = async () => {
  if (!viewerRef.value || !book.value) return

  const bookUrl = `/api/books/file/${book.value.filePath}`
  bookInstance.value = ePub(bookUrl) as Book

  rendition.value = bookInstance.value.renderTo(viewerRef.value, {
    width: '100%',
    height: '100%',
    spread: 'none'
  }) as Rendition

  await bookInstance.value.ready

  const spine: any = bookInstance.value.spine
  totalChapters.value = spine?.length || 1

  const startCfi = savedProgress.value?.location || null
  await rendition.value.display(startCfi)

  await startReadingSession()

  rendition.value.on('relocated', (location: any) => {
    currentLocation.value = location.start.cfi
    
    const chapterIndex = CFIUtils.getChapterIndex(location.start.cfi)
    currentChapter.value = Math.max(0, chapterIndex)
    
    progress.value = calculateProgressByCFI(location.start.cfi, totalChapters.value)
    
    canPrev.value = !location.atStart
    canNext.value = !location.atEnd

    updateProgressDebounced()
    pageReadCount.value++
  })

  rendition.value.on('selected', (cfiRange: any, contents: any) => {
    const selection = contents.window.getSelection()
    if (selection && selection.toString()) {
      selectedText.value = selection.toString()
      selectedCfi.value = cfiRange.cfi
      selectedCfiRange.value = cfiRange
      
      const range = selection.getRangeAt(0)
      const rect = range.getBoundingClientRect()
      popupPosition.value = {
        top: `${rect.bottom + window.scrollY + 10}px`,
        left: `${rect.left + window.scrollX}px`
      }
      showHighlightPopup.value = true
    }
  })

  await loadAnnotations()
}

const startReadingSession = async () => {
  try {
    const result = await $fetch('/api/reading/session/start', {
      method: 'POST',
      body: {
        bookId,
        startCfi: currentLocation.value
      }
    })
    readingSessionId.value = result.id
  } catch (e) {
    console.error('Failed to start reading session:', e)
  }
}

const endReadingSession = async () => {
  if (!readingSessionId.value) return
  
  try {
    await $fetch('/api/reading/session/end', {
      method: 'POST',
      body: {
        sessionId: readingSessionId.value,
        endCfi: currentLocation.value,
        pagesRead: pageReadCount.value
      }
    })
  } catch (e) {
    console.error('Failed to end reading session:', e)
  }
}

const handleBack = async () => {
  stopTTS()
  await endReadingSession()
  navigateTo('/')
}

onUnmounted(async () => {
  stopTTS()
  await endReadingSession()
})

const updateProgressDebounced = useDebounceFn(() => {
  if (currentLocation.value) {
    updateProgress(currentLocation.value, progress.value)
  }
}, 1000)

const prevPage = () => {
  rendition.value?.prev()
}

const nextPage = () => {
  rendition.value?.next()
}

const toggleSettings = () => {
  showSettings.value = !showSettings.value
  showTTSPanel.value = false
  showSummaryPanel.value = false
  showAnnotationsPanel.value = false
}

const toggleTTSPanel = () => {
  showTTSPanel.value = !showTTSPanel.value
  showSettings.value = false
  showSummaryPanel.value = false
  showAnnotationsPanel.value = false
}

const toggleSummaryPanel = () => {
  showSummaryPanel.value = !showSummaryPanel.value
  showSettings.value = false
  showTTSPanel.value = false
  showAnnotationsPanel.value = false
}

const toggleAnnotations = () => {
  showAnnotationsPanel.value = !showAnnotationsPanel.value
  showSettings.value = false
  showTTSPanel.value = false
  showSummaryPanel.value = false
}

const applySettings = () => {
  if (rendition.value) {
    rendition.value.themes.fontSize(`${fontSize.value}px`)
    rendition.value.themes.override('line-height', `${lineHeight.value}`)
  }
}

const setTheme = (theme: any) => {
  currentTheme.value = theme
  if (rendition.value) {
    rendition.value.themes.override('background-color', theme.bg)
    rendition.value.themes.override('color', theme.text)
  }
}

const toggleSpeak = () => {
  if (isSpeaking.value) {
    if (isPaused.value) {
      resume()
    } else {
      pause()
    }
  } else {
    speakSelectedText()
  }
}

const speakSelectedText = () => {
  if (selectedText.value) {
    speak(selectedText.value)
  } else {
    speak('请选择要朗读的文本')
  }
}

const loadAnnotations = async () => {
  if (!rendition.value || !annotations.value) return

  for (const ann of annotations.value) {
    try {
      if (ann.cfi && CFIUtils.validate(ann.cfi)) {
        rendition.value.annotations.highlight(ann.cfi, {}, { fill: ann.color })
      }
    } catch (e) {
      console.warn('Failed to load annotation:', e)
    }
  }
}

const addHighlight = async (color: string) => {
  if (!rendition.value || !selectedCfi.value) {
    showHighlightPopup.value = false
    return
  }

  try {
    const normalizedCfi = CFIUtils.normalize(selectedCfi.value)
    
    rendition.value.annotations.highlight(selectedCfi.value, {}, { fill: color })
    
    await $fetch('/api/annotations', {
      method: 'POST',
      body: {
        bookId,
        cfi: selectedCfi.value,
        normalizedCfi: normalizedCfi,
        text: selectedText.value,
        color
      }
    })
    
    refreshAnnotations()
  } catch (e) {
    console.error('Failed to save highlight:', e)
  }

  showHighlightPopup.value = false
}

const addNote = () => {
  const note = prompt('输入批注：')
  if (note) {
    addHighlightWithNote('#ffff00', note)
  }
  showHighlightPopup.value = false
}

const addHighlightWithNote = async (color: string, note: string) => {
  if (!rendition.value || !selectedCfi.value) return

  try {
    const normalizedCfi = CFIUtils.normalize(selectedCfi.value)
    
    rendition.value.annotations.highlight(selectedCfi.value, {}, { fill: color })
    
    await $fetch('/api/annotations', {
      method: 'POST',
      body: {
        bookId,
        cfi: selectedCfi.value,
        normalizedCfi: normalizedCfi,
        text: selectedText.value,
        note,
        color
      }
    })
    
    refreshAnnotations()
  } catch (e) {
    console.error('Failed to save note:', e)
  }
}

const deleteAnnotation = async (id: number) => {
  await $fetch(`/api/annotations/${id}`, {
    method: 'DELETE'
  })
  refreshAnnotations()
}

const addBookmark = async () => {
  if (!currentLocation.value) return

  try {
    await $fetch('/api/bookmarks', {
      method: 'POST',
      body: {
        bookId,
        cfi: currentLocation.value,
        chapter: `第 ${currentChapter.value + 1} 章`
      }
    })
    refreshBookmarks()
  } catch (e) {
    console.error('Failed to add bookmark:', e)
  }
}

const deleteBookmark = async (id: number) => {
  await $fetch(`/api/bookmarks/${id}`, {
    method: 'DELETE'
  })
  refreshBookmarks()
}

const goToAnnotation = (annotation: any) => {
  if (annotation.cfi && rendition.value) {
    try {
      rendition.value.display(annotation.cfi)
      showAnnotationsPanel.value = false
    } catch (e) {
      console.error('Failed to navigate to annotation:', e)
    }
  }
}

const goToBookmark = (bookmark: any) => {
  if (bookmark.cfi && rendition.value) {
    try {
      rendition.value.display(bookmark.cfi)
      showAnnotationsPanel.value = false
    } catch (e) {
      console.error('Failed to navigate to bookmark:', e)
    }
  }
}

const getChapterFromCFI = (cfi: string): number => {
  return CFIUtils.getChapterIndex(cfi)
}

const syncToRemote = () => {
  if (pendingSyncCfi.value && rendition.value) {
    rendition.value.display(pendingSyncCfi.value)
  }
  showSyncPrompt.value = false
}

const generateBookSummary = async () => {
  isGeneratingSummary.value = true
  try {
    await $fetch('/api/summary/generate', {
      method: 'POST',
      body: { bookId }
    })
    await refreshNuxtData()
  } catch (e) {
    console.error('Failed to generate summary:', e)
  }
  isGeneratingSummary.value = false
}

const generateChapterSummary = async () => {
  isGeneratingSummary.value = true
  try {
    await $fetch('/api/summary/generate', {
      method: 'POST',
      body: {
        bookId,
        chapterIndex: currentChapter.value,
        chapterTitle: `第 ${currentChapter.value + 1} 章`,
        content: selectedText.value || ''
      }
    })
    await refreshNuxtData()
  } catch (e) {
    console.error('Failed to generate chapter summary:', e)
  }
  isGeneratingSummary.value = false
}

const formatDate = (dateString: string): string => {
  const date = new Date(dateString)
  return `${date.getMonth() + 1}/${date.getDate()} ${date.getHours()}:${String(date.getMinutes()).padStart(2, '0')}`
}
</script>

<style scoped>
.reader-container {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f5f5f5;
}

.reader-header {
  display: flex;
  align-items: center;
  padding: 15px 20px;
  background: white;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  gap: 20px;
}

.back-btn {
  background: none;
  border: none;
  font-size: 16px;
  cursor: pointer;
  color: #666;
}

.reader-header h2 {
  flex: 1;
  font-size: 18px;
  color: #333;
}

.header-controls {
  display: flex;
  align-items: center;
  gap: 10px;
}

.connection-status {
  font-size: 12px;
  color: #999;
}

.connection-status.connected {
  color: #27ae60;
}

.icon-btn {
  background: none;
  border: none;
  font-size: 20px;
  cursor: pointer;
  padding: 5px 10px;
  border-radius: 4px;
  transition: background 0.2s;
}

.icon-btn:hover {
  background: #f0f0f0;
}

.viewer-container {
  flex: 1;
  overflow: hidden;
  position: relative;
}

.viewer {
  width: 100%;
  height: 100%;
}

.reader-footer {
  display: flex;
  align-items: center;
  padding: 15px 20px;
  background: white;
  box-shadow: 0 -2px 10px rgba(0, 0, 0, 0.1);
  gap: 20px;
}

.nav-btn {
  padding: 10px 20px;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
}

.nav-btn:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.progress-info {
  flex: 1;
  text-align: center;
}

.progress-info span {
  display: block;
  margin-bottom: 8px;
  font-size: 14px;
  color: #666;
}

.progress-bar {
  width: 100%;
  height: 6px;
  background: #e0e0e0;
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #667eea, #764ba2);
  transition: width 0.3s;
}

.settings-panel,
.tts-panel,
.summary-panel,
.annotations-panel {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: flex-end;
  z-index: 1000;
}

.settings-content,
.tts-content,
.summary-content,
.annotations-content {
  width: 380px;
  background: white;
  padding: 30px;
  overflow-y: auto;
}

.settings-content h3,
.tts-content h3,
.summary-content h3,
.annotations-content h3 {
  margin-bottom: 25px;
  color: #333;
}

.setting-item {
  margin-bottom: 25px;
}

.setting-item label {
  display: block;
  margin-bottom: 10px;
  color: #666;
}

.setting-item input[type="range"] {
  width: 100%;
}

.voice-select {
  width: 100%;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
}

.theme-options {
  display: flex;
  gap: 10px;
}

.theme-btn {
  flex: 1;
  padding: 15px;
  border: 2px solid #ddd;
  border-radius: 8px;
  cursor: pointer;
  font-size: 12px;
}

.tts-controls {
  display: flex;
  gap: 10px;
  margin-bottom: 25px;
}

.tts-main-btn,
.tts-stop-btn {
  flex: 1;
  padding: 12px;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
}

.tts-main-btn {
  background: #667eea;
  color: white;
}

.tts-stop-btn {
  background: #e74c3c;
  color: white;
}

.tts-stop-btn:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.loading-summary {
  text-align: center;
  padding: 40px;
  color: #666;
}

.summary-text h4 {
  margin-bottom: 12px;
  color: #333;
}

.book-summary p,
.chapter-summary-item p {
  line-height: 1.8;
  color: #555;
  margin-bottom: 20px;
}

.chapter-summaries {
  margin-top: 20px;
  border-top: 1px solid #eee;
  padding-top: 20px;
}

.chapter-summary-item {
  margin-bottom: 20px;
  padding-bottom: 20px;
  border-bottom: 1px solid #f0f0f0;
}

.chapter-summary-item:last-child {
  border-bottom: none;
  margin-bottom: 0;
  padding-bottom: 0;
}

.summary-actions {
  display: flex;
  gap: 10px;
  margin-top: 20px;
}

.generate-btn {
  flex: 1;
  padding: 12px;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
}

.generate-btn:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.tabs {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
}

.tab-btn {
  flex: 1;
  padding: 10px;
  border: none;
  background: #f0f0f0;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
}

.tab-btn.active {
  background: #667eea;
  color: white;
}

.empty-annotations {
  text-align: center;
  padding: 40px 20px;
  color: #999;
}

.annotations-list {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.annotation-item {
  padding: 15px;
  background: #f8f9fa;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s;
}

.annotation-item:hover {
  background: #f0f0f0;
}

.annotation-text {
  padding-left: 8px;
  border-left: 4px solid;
  font-size: 14px;
  color: #333;
  line-height: 1.5;
}

.annotation-note {
  margin-top: 8px;
  font-size: 13px;
  color: #666;
  font-style: italic;
}

.annotation-location,
.annotation-time {
  display: inline-block;
  margin-top: 8px;
  font-size: 11px;
  color: #999;
  background: #eee;
  padding: 2px 6px;
  border-radius: 4px;
}

.delete-btn {
  margin-top: 10px;
  padding: 5px 10px;
  background: #ff4444;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
}

.highlight-popup {
  position: fixed;
  z-index: 1001;
  background: white;
  padding: 10px;
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
  display: flex;
  gap: 10px;
  align-items: center;
}

.highlight-colors {
  display: flex;
  gap: 5px;
}

.color-btn {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  border: 2px solid #ddd;
  cursor: pointer;
}

.note-btn {
  padding: 5px 10px;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
}

.sync-prompt {
  position: fixed;
  top: 80px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 1002;
}

.sync-content {
  background: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
  min-width: 300px;
}

.sync-content p {
  margin-bottom: 15px;
  color: #333;
}

.sync-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}

.sync-actions .cancel-btn {
  padding: 8px 16px;
  background: #eee;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.sync-actions .confirm-btn {
  padding: 8px 16px;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}
</style>
