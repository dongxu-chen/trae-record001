<template>
  <div class="template-library">
    <div class="library-header">
      <h2 class="library-title">
        <span class="title-icon">📚</span>
        模板库
      </h2>
      <div class="header-actions">
        <div class="search-box">
          <span class="search-icon">🔍</span>
          <input 
            type="text" 
            class="search-input"
            v-model="searchQuery"
            placeholder="搜索模板..."
          />
        </div>
      </div>
    </div>

    <div class="library-filters">
      <div class="filter-group">
        <span class="filter-label">类型:</span>
        <div class="filter-buttons">
          <button 
            class="filter-btn"
            :class="{ active: activeType === null }"
            @click="activeType = null"
          >
            全部
          </button>
          <button 
            v-for="type in templateTypes" 
            :key="type.id"
            class="filter-btn"
            :class="{ active: activeType === type.id }"
            @click="activeType = type.id"
          >
            {{ type.icon }} {{ type.name }}
          </button>
        </div>
      </div>

      <div class="filter-group">
        <span class="filter-label">分类:</span>
        <div class="filter-buttons">
          <button 
            class="filter-btn"
            :class="{ active: activeCategory === null }"
            @click="activeCategory = null"
          >
            全部
          </button>
          <button 
            v-for="cat in categories" 
            :key="cat.id"
            class="filter-btn"
            :class="{ active: activeCategory === cat.id }"
            @click="activeCategory = cat.id"
          >
            {{ cat.name }}
          </button>
        </div>
      </div>

      <div class="filter-group">
        <button 
          class="filter-btn favorite-btn"
          :class="{ active: showFavoritesOnly }"
          @click="showFavoritesOnly = !showFavoritesOnly"
        >
          ⭐ 收藏
        </button>
        <button 
          class="filter-btn recent-btn"
          :class="{ active: showRecentOnly }"
          @click="showRecentOnly = !showRecentOnly"
        >
          🕐 最近
        </button>
      </div>
    </div>

    <div class="library-content">
      <div class="templates-grid">
        <div 
          v-for="template in filteredTemplates" 
          :key="template.id"
          class="template-card"
          :class="{ selected: selectedTemplate?.id === template.id }"
          @click="selectTemplate(template)"
        >
          <div class="template-thumbnail" :style="getThumbnailStyle(template)">
            <span class="thumbnail-icon">{{ template.thumbnail }}</span>
            <button 
              class="favorite-toggle"
              @click.stop="toggleFavorite(template.id)"
              :title="isFavorite(template.id) ? '取消收藏' : '添加收藏'"
            >
              {{ isFavorite(template.id) ? '❤️' : '🤍' }}
            </button>
          </div>
          <div class="template-info">
            <div class="template-name">{{ template.name }}</div>
            <div class="template-meta">
              <span class="template-type">{{ getTypeName(template.type) }}</span>
              <span class="template-duration" v-if="template.duration > 0">
                {{ template.duration }}s
              </span>
            </div>
            <div class="template-description">{{ template.description }}</div>
          </div>
          <div class="template-actions" v-if="selectedTemplate?.id === template.id">
            <button 
              class="btn btn-primary btn-sm"
              @click.stop="applyTemplate(template, 'start')"
              :disabled="!store.selectedClip && template.type !== 'filter'"
            >
              ➕ 添加到开头
            </button>
            <button 
              class="btn btn-primary btn-sm"
              @click.stop="applyTemplate(template, 'end')"
              :disabled="!store.selectedClip && template.type !== 'filter'"
            >
              ➕ 添加到结尾
            </button>
          </div>
        </div>

        <div v-if="filteredTemplates.length === 0" class="empty-templates">
          <span class="empty-icon">📭</span>
          <p>没有找到匹配的模板</p>
          <p class="hint">尝试调整筛选条件</p>
        </div>
      </div>
    </div>

    <div class="library-stats">
      <span>共 {{ filteredTemplates.length }} 个模板</span>
      <span v-if="showFavoritesOnly"> | 已收藏 {{ favorites.size }} 个</span>
      <span v-if="showRecentOnly"> | 最近使用 {{ recentlyUsed.length }} 个</span>
    </div>

    <div v-if="selectedTemplate" class="template-preview">
      <div class="preview-header">
        <h3>模板预览</h3>
        <button class="close-btn" @click="selectedTemplate = null">✕</button>
      </div>
      <div class="preview-content">
        <div class="preview-thumbnail" :style="getThumbnailStyle(selectedTemplate)">
          <span class="preview-icon">{{ selectedTemplate.thumbnail }}</span>
        </div>
        <div class="preview-details">
          <h4>{{ selectedTemplate.name }}</h4>
          <p class="preview-desc">{{ selectedTemplate.description }}</p>
          <div class="preview-meta">
            <div class="meta-item">
              <span class="meta-label">类型:</span>
              <span class="meta-value">{{ getTypeName(selectedTemplate.type) }}</span>
            </div>
            <div class="meta-item" v-if="selectedTemplate.duration > 0">
              <span class="meta-label">时长:</span>
              <span class="meta-value">{{ selectedTemplate.duration }} 秒</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">分类:</span>
              <span class="meta-value">{{ getCategoryName(selectedTemplate.category) }}</span>
            </div>
          </div>
          <div class="preview-effects">
            <h5>包含效果:</h5>
            <ul>
              <li v-for="(effect, idx) in selectedTemplate.effects" :key="idx">
                {{ getEffectName(effect.type) }}
              </li>
            </ul>
          </div>
          <div class="preview-actions">
            <button 
              class="btn btn-primary"
              @click="applyTemplate(selectedTemplate, 'start')"
              :disabled="!store.selectedClip && selectedTemplate.type !== 'filter'"
            >
              ➕ 应用到开头
            </button>
            <button 
              class="btn btn-primary"
              @click="applyTemplate(selectedTemplate, 'end')"
              :disabled="!store.selectedClip && selectedTemplate.type !== 'filter'"
            >
              ➕ 应用到结尾
            </button>
            <button 
              class="btn"
              @click="toggleFavorite(selectedTemplate.id)"
            >
              {{ isFavorite(selectedTemplate.id) ? '❤️ 已收藏' : '🤍 收藏' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useEditorStore } from '../stores/editor'
import TemplateLibrary from '../utils/templateLibrary'
import { TemplateType, TemplateCategory } from '../utils/templateLibrary'
import { ffmpegService } from '../utils/ffmpeg'

const store = useEditorStore()

const library = new TemplateLibrary()
const selectedTemplate = ref(null)
const searchQuery = ref('')
const activeType = ref(null)
const activeCategory = ref(null)
const showFavoritesOnly = ref(false)
const showRecentOnly = ref(false)
const favorites = ref(new Set())
const recentlyUsed = ref([])

const templateTypes = [
  { id: TemplateType.INTRO, name: '片头', icon: '🎬' },
  { id: TemplateType.OUTRO, name: '片尾', icon: '🔚' },
  { id: TemplateType.TRANSITION, name: '转场', icon: '✨' },
  { id: TemplateType.LOWER_THIRD, name: '字幕条', icon: '📝' },
  { id: TemplateType.FILTER, name: '滤镜', icon: '🎨' },
]

const categories = computed(() => {
  return library.getCategories()
})

const filteredTemplates = computed(() => {
  let templates = library.getTemplates({
    type: activeType.value,
    category: activeCategory.value,
    search: searchQuery.value,
    favoritesOnly: showFavoritesOnly.value,
    recentOnly: showRecentOnly.value,
  })
  return templates
})

function selectTemplate(template) {
  selectedTemplate.value = template
}

function toggleFavorite(templateId) {
  const isFav = library.toggleFavorite(templateId)
  favorites.value = new Set(library.getFavorites().map(t => t.id))
  return isFav
}

function isFavorite(templateId) {
  return library.isFavorite(templateId)
}

function getTypeName(type) {
  const names = {
    [TemplateType.INTRO]: '片头',
    [TemplateType.OUTRO]: '片尾',
    [TemplateType.TRANSITION]: '转场',
    [TemplateType.LOWER_THIRD]: '字幕条',
    [TemplateType.FILTER]: '滤镜',
  }
  return names[type] || type
}

function getCategoryName(category) {
  const names = {
    [TemplateCategory.BUSINESS]: '商务',
    [TemplateCategory.SOCIAL_MEDIA]: '社交媒体',
    [TemplateCategory.EDUCATION]: '教育',
    [TemplateCategory.ENTERTAINMENT]: '娱乐',
    [TemplateCategory.TECHNOLOGY]: '科技',
    [TemplateCategory.PERSONAL]: '个人',
  }
  return names[category] || category
}

function getEffectName(effectType) {
  const names = {
    'fade_in': '淡入',
    'fade_out': '淡出',
    'text_animation': '文字动画',
    'particle_effect': '粒子效果',
    'slide_in': '滑入',
    'line_animation': '线条动画',
    'zoom_in': '放大',
    'sticker_effect': '贴纸',
    'bounce_out': '弹跳',
    'subscribe_button': '订阅按钮',
    'qr_code_placeholder': '二维码占位',
    'social_icons': '社交图标',
    'contact_info': '联系信息',
    'emoji_rain': '表情雨',
    'lower_third': '底部字幕',
    'logo_placeholder': 'Logo占位',
    'glitch_effect': '故障效果',
    'rgb_split': 'RGB分离',
    'static_noise': '噪点',
    'color_grading': '调色',
    'vignette': '暗角',
    'film_grain': '胶片颗粒',
    'flicker': '闪烁',
  }
  return names[effectType] || effectType
}

function getThumbnailStyle(template) {
  const bg = template.colorScheme.background
  if (bg.startsWith('linear-gradient')) {
    return { background: bg }
  }
  return { backgroundColor: bg }
}

async function applyTemplate(template, position = 'start') {
  try {
    store.setProcessing(true, `正在应用模板: ${template.name}...`)
    
    if (template.type === TemplateType.INTRO) {
      const result = await library.applyIntro(template.id, store.selectedClip)
      store.applyTemplate(template.id, 'start')
      
      const introBlob = await generateIntroVideo(template)
      const introFile = new File([introBlob], `intro_${template.id}.mp4`, { type: 'video/mp4' })
      const mediaItem = await store.addMediaFile(introFile)
      
      const insertTime = position === 'start' ? 0 : (store.totalDuration || 0)
      store.addToVideoTrack(mediaItem, insertTime)
      
      alert(`片头模板"${template.name}"已应用！`)
    } else if (template.type === TemplateType.OUTRO) {
      const result = await library.applyOutro(template.id, store.selectedClip)
      store.applyTemplate(template.id, 'end')
      
      const outroBlob = await generateOutroVideo(template)
      const outroFile = new File([outroBlob], `outro_${template.id}.mp4`, { type: 'video/mp4' })
      const mediaItem = await store.addMediaFile(outroFile)
      
      const insertTime = position === 'end' ? (store.totalDuration || 0) : 0
      store.addToVideoTrack(mediaItem, insertTime)
      
      alert(`片尾模板"${template.name}"已应用！`)
    } else if (template.type === TemplateType.FILTER) {
      const filterResult = await library.applyFilter(template.id, store.sortedVideoClips)
      store.applyTemplate(template.id, position)
      alert(`滤镜模板"${template.name}"已应用！`)
    } else {
      store.applyTemplate(template.id, position)
      alert(`模板"${template.name}"已应用到${position === 'start' ? '开头' : '结尾'}！`)
    }
    
    recentlyUsed.value = library.getRecentlyUsed(10).map(t => t.id)
    store.setProcessing(false)
    
  } catch (error) {
    console.error('模板应用失败:', error)
    alert('模板应用失败: ' + error.message)
    store.setProcessing(false)
  }
}

async function generateIntroVideo(template) {
  const duration = template.duration || 3
  const color = template.colorScheme.primary.replace('#', '')
  const bgColor = template.colorScheme.background.startsWith('linear-gradient') 
    ? '000000' 
    : template.colorScheme.background.replace('#', '')
  
  const outputName = 'intro_' + Date.now() + '.mp4'
  
  await ffmpegService.exec(
    '-f', 'lavfi',
    '-i', `color=c=0x${bgColor}:s=1920x1080:d=${duration}`,
    '-vf', `drawtext=text='${template.name}':fontsize=72:fontcolor=0x${color}:` +
           `x=(w-text_w)/2:y=(h-text_h)/2:enable='between(t,0,${duration})'`,
    '-c:v', 'libx264',
    '-t', duration.toString(),
    '-y',
    outputName
  )
  
  const data = await ffmpegService.readFile(outputName)
  const blob = new Blob([data], { type: 'video/mp4' })
  await ffmpegService.deleteFile(outputName)
  
  return blob
}

async function generateOutroVideo(template) {
  const duration = template.duration || 3
  const color = template.colorScheme.primary.replace('#', '')
  const bgColor = template.colorScheme.background.startsWith('linear-gradient') 
    ? '000000' 
    : template.colorScheme.background.replace('#', '')
  
  const outputName = 'outro_' + Date.now() + '.mp4'
  
  await ffmpegService.exec(
    '-f', 'lavfi',
    '-i', `color=c=0x${bgColor}:s=1920x1080:d=${duration}`,
    '-vf', `drawtext=text='感谢观看':fontsize=64:fontcolor=0x${color}:` +
           `x=(w-text_w)/2:y=(h-text_h)/2-40:enable='between(t,0,${duration})',` +
           `drawtext=text='订阅关注':fontsize=36:fontcolor=0x${color}:` +
           `x=(w-text_w)/2:y=(h-text_h)/2+40:enable='between(t,0,${duration})'`,
    '-c:v', 'libx264',
    '-t', duration.toString(),
    '-y',
    outputName
  )
  
  const data = await ffmpegService.readFile(outputName)
  const blob = new Blob([data], { type: 'video/mp4' })
  await ffmpegService.deleteFile(outputName)
  
  return blob
}

onMounted(() => {
  favorites.value = new Set(library.getFavorites().map(t => t.id))
  recentlyUsed.value = library.getRecentlyUsed(10).map(t => t.id)
})
</script>

<style scoped>
.template-library {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--bg-primary);
}

.library-header {
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-secondary);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.library-title {
  font-size: 18px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--text-primary);
  margin: 0;
}

.title-icon {
  font-size: 24px;
}

.header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.search-box {
  position: relative;
  display: flex;
  align-items: center;
}

.search-icon {
  position: absolute;
  left: 12px;
  font-size: 14px;
  color: var(--text-muted);
}

.search-input {
  padding: 8px 12px 8px 36px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--text-primary);
  font-size: 13px;
  width: 200px;
}

.search-input:focus {
  outline: none;
  border-color: var(--accent-primary);
}

.library-filters {
  padding: 12px 20px;
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-tertiary);
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 12px;
}

.filter-label {
  font-size: 12px;
  color: var(--text-secondary);
  font-weight: 500;
  min-width: 40px;
}

.filter-buttons {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.filter-btn {
  padding: 6px 12px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  color: var(--text-secondary);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.filter-btn:hover {
  border-color: var(--accent-secondary);
  color: var(--text-primary);
}

.filter-btn.active {
  background: var(--accent-primary);
  border-color: var(--accent-primary);
  color: white;
}

.favorite-btn.active {
  background: #fbbf24;
  border-color: #fbbf24;
  color: white;
}

.recent-btn.active {
  background: #8b5cf6;
  border-color: #8b5cf6;
  color: white;
}

.library-content {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.templates-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 16px;
}

.template-card {
  background: var(--bg-secondary);
  border: 2px solid var(--border-color);
  border-radius: 12px;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  flex-direction: column;
}

.template-card:hover {
  border-color: var(--accent-secondary);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

.template-card.selected {
  border-color: var(--accent-primary);
  box-shadow: 0 0 0 3px rgba(233, 69, 96, 0.2);
}

.template-thumbnail {
  aspect-ratio: 16/9;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  background: var(--bg-tertiary);
}

.thumbnail-icon {
  font-size: 48px;
}

.favorite-toggle {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.5);
  font-size: 16px;
  cursor: pointer;
  transition: all 0.2s;
}

.favorite-toggle:hover {
  transform: scale(1.1);
  background: rgba(0, 0, 0, 0.7);
}

.template-info {
  padding: 12px;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.template-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.template-meta {
  display: flex;
  gap: 8px;
  font-size: 11px;
  color: var(--text-muted);
}

.template-type {
  background: rgba(233, 69, 96, 0.1);
  color: var(--accent-primary);
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: 500;
}

.template-duration {
  font-family: 'Courier New', monospace;
}

.template-description {
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.template-actions {
  padding: 12px;
  border-top: 1px solid var(--border-color);
  display: flex;
  gap: 8px;
}

.btn-sm {
  padding: 6px 10px;
  font-size: 11px;
  flex: 1;
}

.empty-templates {
  grid-column: 1 / -1;
  text-align: center;
  padding: 60px 20px;
  color: var(--text-muted);
}

.empty-icon {
  font-size: 48px;
  display: block;
  margin-bottom: 12px;
}

.empty-templates p {
  margin: 4px 0;
  font-size: 13px;
}

.empty-templates .hint {
  font-size: 12px;
  color: var(--text-muted);
}

.library-stats {
  padding: 12px 20px;
  border-top: 1px solid var(--border-color);
  background: var(--bg-secondary);
  font-size: 12px;
  color: var(--text-secondary);
}

.template-preview {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 600px;
  max-width: 90vw;
  max-height: 80vh;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
  z-index: 1000;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.preview-header {
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.preview-header h3 {
  margin: 0;
  font-size: 16px;
  color: var(--text-primary);
}

.close-btn {
  width: 28px;
  height: 28px;
  border: none;
  background: transparent;
  color: var(--text-muted);
  font-size: 18px;
  cursor: pointer;
  border-radius: 4px;
  transition: all 0.2s;
}

.close-btn:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.preview-content {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.preview-thumbnail {
  aspect-ratio: 16/9;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  margin-bottom: 20px;
}

.preview-icon {
  font-size: 72px;
}

.preview-details h4 {
  margin: 0 0 8px 0;
  font-size: 18px;
  color: var(--text-primary);
}

.preview-desc {
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 16px;
  line-height: 1.5;
}

.preview-meta {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 16px;
  padding: 12px;
  background: var(--bg-tertiary);
  border-radius: 8px;
}

.meta-item {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
}

.meta-label {
  color: var(--text-muted);
}

.meta-value {
  color: var(--text-primary);
  font-weight: 500;
}

.preview-effects h5 {
  margin: 0 0 8px 0;
  font-size: 13px;
  color: var(--text-secondary);
}

.preview-effects ul {
  margin: 0;
  padding-left: 20px;
  font-size: 12px;
  color: var(--text-primary);
}

.preview-effects li {
  margin: 4px 0;
}

.preview-actions {
  display: flex;
  gap: 8px;
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid var(--border-color);
}

.preview-actions .btn {
  flex: 1;
}
</style>
