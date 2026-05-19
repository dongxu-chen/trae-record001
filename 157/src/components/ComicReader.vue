<template>
  <div ref="containerRef" class="comic-reader">
    <div ref="canvasContainer" class="canvas-container"></div>
    
    <DanmakuRenderer 
      ref="danmakuRef"
      :enabled="danmakuEnabled" 
      :currentPage="currentPage"
    />
    
    <FeaturePanel 
      :totalPages="totalPages"
      :currentPage="currentPage"
      :imageUrls="demoImages"
      @toggleDanmaku="handleToggleDanmaku"
      @toggleCrop="handleToggleCrop"
      @cropThresholdChange="handleCropThresholdChange"
    />
    
    <ControlPanel 
      :currentPage="currentPage"
      :totalPages="totalPages"
      :viewMode="viewMode"
      :zoom="zoom"
      :bookmarks="bookmarks"
      @prev="prevPage"
      @next="nextPage"
      @goTo="goToPage"
      @toggleMode="toggleViewMode"
      @zoomIn="zoomIn"
      @zoomOut="zoomOut"
      @resetZoom="resetZoom"
      @toggleBookmark="toggleBookmark"
      @syncBookmarks="syncBookmarks"
    />
    
    <div v-if="isLoading" class="loading-overlay">
      <div class="loading-spinner"></div>
      <p>加载中...</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import * as PIXI from 'pixi.js'
import ControlPanel from './ControlPanel.vue'
import DanmakuRenderer from './DanmakuRenderer.vue'
import FeaturePanel from './FeaturePanel.vue'
import { usePreload } from '../composables/usePreload'
import { bookmarkService } from '../services/bookmarkService'
import { readingStatsService } from '../services/readingStats'
import { imageCropper } from '../utils/imageCrop'

const containerRef = ref(null)
const canvasContainer = ref(null)
const danmakuRef = ref(null)
const isLoading = ref(true)

let app = null
let stage = null
let renderer = null
let scrollContainer = null
let pageSprites = []
let currentPageIndex = 0
let position = { x: 0, y: 0 }
let isDragging = false
let dragStart = { x: 0, y: 0 }
let isScrolling = false
let scrollTimeout = null

const currentPage = ref(1)
const totalPages = ref(0)
const viewMode = ref('double')
const zoom = ref(1)
const bookmarks = ref([])
const danmakuEnabled = ref(true)
const autoCropEnabled = ref(false)

const demoImages = [
  'https://picsum.photos/800/1200?random=1',
  'https://picsum.photos/800/1200?random=2',
  'https://picsum.photos/800/1200?random=3',
  'https://picsum.photos/800/1200?random=4',
  'https://picsum.photos/800/1200?random=5',
  'https://picsum.photos/800/1200?random=6',
  'https://picsum.photos/800/1200?random=7',
  'https://picsum.photos/800/1200?random=8',
  'https://picsum.photos/800/1200?random=9',
  'https://picsum.photos/800/1200?random=10',
  'https://picsum.photos/800/1200?random=11',
  'https://picsum.photos/800/1200?random=12',
]

const { preloadPages, getTexture, hasTexture, setTexture, getCacheStats, clearCache } = usePreload()

onMounted(async () => {
  await bookmarkService.init()
  bookmarks.value = bookmarkService.getAllBookmarks()
  
  await initPixi()
  totalPages.value = demoImages.length
  await loadInitialPages()
  setupInteractions()
  isLoading.value = false
})

onUnmounted(() => {
  cleanup()
})

function cleanup() {
  window.removeEventListener('resize', handleResize)
  
  if (app) {
    app.destroy(true)
    app = null
  }
  
  clearCache()
  stage = null
  renderer = null
  scrollContainer = null
  pageSprites = []
}

async function initPixi() {
  app = new PIXI.Application({
    width: canvasContainer.value.clientWidth,
    height: canvasContainer.value.clientHeight,
    backgroundColor: 0x1a1a1a,
    resolution: window.devicePixelRatio,
    autoDensity: true,
    antialias: true,
  })
  
  canvasContainer.value.appendChild(app.view)
  stage = app.stage
  renderer = app.renderer
  
  window.addEventListener('resize', handleResize)
}

async function loadInitialPages() {
  const { loadPage } = usePreload()
  
  for (let i = 0; i < Math.min(5, demoImages.length); i++) {
    try {
      const texture = await loadPage(i, demoImages[i])
      if (texture) {
        setTexture(i, texture)
      } else {
        const fallbackTexture = await PIXI.Texture.fromURL(demoImages[i])
        setTexture(i, fallbackTexture)
      }
    } catch (error) {
      console.error(`加载初始页面 ${i + 1} 失败:`, error)
      try {
        const fallbackTexture = await PIXI.Texture.fromURL(demoImages[i])
        setTexture(i, fallbackTexture)
      } catch (e) {
        console.error(`Fall-back也失败了:`, e)
      }
    }
  }
  
  preloadPages(0, demoImages)
  renderPages()
}

function renderPages() {
  stage.removeChildren()
  pageSprites = []
  
  if (viewMode.value === 'double') {
    renderDoublePage()
  } else {
    renderScrollMode()
  }
}

function renderDoublePage() {
  const container = new PIXI.Container()
  const screenWidth = renderer.width
  const screenHeight = renderer.height
  
  const leftPageIndex = currentPageIndex % 2 === 0 ? currentPageIndex : currentPageIndex - 1
  const rightPageIndex = leftPageIndex + 1
  
  const pageWidth = screenWidth / 2
  
  if (leftPageIndex >= 0 && leftPageIndex < demoImages.length) {
    const leftTexture = getTexture(leftPageIndex)
    if (leftTexture) {
      const leftSprite = new PIXI.Sprite(leftTexture)
      fitSpriteToScreen(leftSprite, pageWidth, screenHeight)
      leftSprite.x = 0
      container.addChild(leftSprite)
      pageSprites.push({ sprite: leftSprite, index: leftPageIndex })
    }
  }
  
  if (rightPageIndex < demoImages.length) {
    const rightTexture = getTexture(rightPageIndex)
    if (rightTexture) {
      const rightSprite = new PIXI.Sprite(rightTexture)
      fitSpriteToScreen(rightSprite, pageWidth, screenHeight)
      rightSprite.x = pageWidth
      container.addChild(rightSprite)
      pageSprites.push({ sprite: rightSprite, index: rightPageIndex })
    }
  }
  
  container.scale.set(zoom.value)
  container.x = position.x
  container.y = position.y
  
  stage.addChild(container)
}

function renderScrollMode() {
  scrollContainer = new PIXI.Container()
  const screenWidth = renderer.width
  let yOffset = 0
  
  for (let i = 0; i < demoImages.length; i++) {
    const texture = getTexture(i)
    if (texture) {
      const sprite = new PIXI.Sprite(texture)
      const ratio = screenWidth / sprite.width
      sprite.width = screenWidth
      sprite.height = sprite.height * ratio
      sprite.y = yOffset
      yOffset += sprite.height + 20
      scrollContainer.addChild(sprite)
      pageSprites.push({ sprite, index: i, y: sprite.y, height: sprite.height })
    }
  }
  
  scrollContainer.scale.set(zoom.value)
  scrollContainer.x = position.x
  scrollContainer.y = position.y
  
  stage.addChild(scrollContainer)
}

function fitSpriteToScreen(sprite, maxWidth, maxHeight) {
  const ratio = Math.min(maxWidth / sprite.width, maxHeight / sprite.height)
  sprite.width = sprite.width * ratio
  sprite.height = sprite.height * ratio
  
  sprite.x = (maxWidth - sprite.width) / 2
  sprite.y = (maxHeight - sprite.height) / 2
}

function setupInteractions() {
  app.view.addEventListener('mousedown', startDrag)
  app.view.addEventListener('mousemove', drag)
  app.view.addEventListener('mouseup', endDrag)
  app.view.addEventListener('mouseleave', endDrag)
  app.view.addEventListener('wheel', handleWheel)
  app.view.addEventListener('click', handleClick)
}

function startDrag(e) {
  isDragging = true
  dragStart = {
    x: e.clientX - position.x,
    y: e.clientY - position.y
  }
}

function drag(e) {
  if (!isDragging) return
  
  position.x = e.clientX - dragStart.x
  position.y = e.clientY - dragStart.y
  
  if (viewMode.value === 'scroll' && scrollContainer) {
    scrollContainer.x = position.x
    scrollContainer.y = position.y
    
    if (scrollTimeout) {
      clearTimeout(scrollTimeout)
    }
    isScrolling = true
    
    scrollTimeout = setTimeout(() => {
      updateCurrentPageFromScroll()
      isScrolling = false
    }, 150)
  } else if (viewMode.value === 'double') {
    renderPages()
  }
}

function endDrag() {
  isDragging = false
}

function updateCurrentPageFromScroll() {
  if (viewMode.value !== 'scroll' || pageSprites.length === 0) return
  
  const screenHeight = renderer.height
  const scrollY = -position.y / zoom.value
  const viewportCenter = scrollY + screenHeight / 2
  
  let closestPage = 0
  let minDistance = Infinity
  
  for (const page of pageSprites) {
    const pageCenter = page.y + page.height / 2
    const distance = Math.abs(viewportCenter - pageCenter)
    
    if (distance < minDistance) {
      minDistance = distance
      closestPage = page.index
    }
  }
  
  if (closestPage !== currentPageIndex) {
    currentPageIndex = closestPage
    currentPage.value = currentPageIndex + 1
    preloadPages(currentPageIndex, demoImages)
    console.log(`卷轴模式: 当前页更新为 ${currentPage.value}`)
  }
}

function handleWheel(e) {
  e.preventDefault()
  
  if (viewMode.value === 'scroll') {
    const scrollSpeed = 50
    position.y -= e.deltaY > 0 ? -scrollSpeed : scrollSpeed
    position.y = Math.min(0, position.y)
    
    if (scrollContainer) {
      scrollContainer.y = position.y
    }
    
    if (scrollTimeout) {
      clearTimeout(scrollTimeout)
    }
    isScrolling = true
    
    scrollTimeout = setTimeout(() => {
      updateCurrentPageFromScroll()
      isScrolling = false
    }, 200)
  } else {
    const delta = e.deltaY > 0 ? 0.9 : 1.1
    const newZoom = Math.max(0.5, Math.min(3, zoom.value * delta))
    zoom.value = newZoom
    renderPages()
  }
}

function handleClick(e) {
  if (isDragging || isScrolling) return
  
  const rect = app.view.getBoundingClientRect()
  const x = e.clientX - rect.left
  
  if (viewMode.value === 'double') {
    if (x < rect.width / 3) {
      prevPage()
    } else if (x > rect.width * 2 / 3) {
      nextPage()
    }
  }
}

function prevPage() {
  if (viewMode.value === 'double') {
    if (currentPageIndex >= 2) {
      currentPageIndex -= 2
      currentPage.value = currentPageIndex + 1
      preloadPages(currentPageIndex, demoImages)
      recordReadingProgress()
      position = { x: 0, y: 0 }
      renderPages()
    }
  } else {
    if (currentPageIndex > 0) {
      currentPageIndex--
      currentPage.value = currentPageIndex + 1
      preloadPages(currentPageIndex, demoImages)
      recordReadingProgress()
      scrollToCurrentPage()
    }
  }
}

function nextPage() {
  if (viewMode.value === 'double') {
    if (currentPageIndex + 2 < demoImages.length) {
      currentPageIndex += 2
      currentPage.value = currentPageIndex + 1
      preloadPages(currentPageIndex, demoImages)
      recordReadingProgress()
      position = { x: 0, y: 0 }
      renderPages()
    }
  } else {
    if (currentPageIndex < demoImages.length - 1) {
      currentPageIndex++
      currentPage.value = currentPageIndex + 1
      preloadPages(currentPageIndex, demoImages)
      recordReadingProgress()
      scrollToCurrentPage()
    }
  }
}

function scrollToCurrentPage() {
  if (viewMode.value !== 'scroll' || pageSprites.length === 0) return
  
  const targetPage = pageSprites.find(p => p.index === currentPageIndex)
  if (targetPage) {
    position.y = -targetPage.y * zoom.value
    if (scrollContainer) {
      scrollContainer.y = position.y
    }
  }
}

function goToPage(page) {
  currentPageIndex = page - 1
  currentPage.value = page
  preloadPages(currentPageIndex, demoImages)
  recordReadingProgress()
  position = { x: 0, y: 0 }
  
  if (viewMode.value === 'scroll') {
    nextTick(() => {
      scrollToCurrentPage()
    })
  } else {
    renderPages()
  }
}

function toggleViewMode() {
  viewMode.value = viewMode.value === 'double' ? 'scroll' : 'double'
  position = { x: 0, y: 0 }
  renderPages()
  
  if (viewMode.value === 'scroll') {
    nextTick(() => {
      scrollToCurrentPage()
    })
  }
}

function zoomIn() {
  zoom.value = Math.min(3, zoom.value + 0.25)
  renderPages()
}

function zoomOut() {
  zoom.value = Math.max(0.5, zoom.value - 0.25)
  renderPages()
}

function resetZoom() {
  zoom.value = 1
  position = { x: 0, y: 0 }
  renderPages()
}

async function toggleBookmark() {
  await bookmarkService.toggleBookmark(currentPage.value)
  bookmarks.value = bookmarkService.getAllBookmarks()
}

async function syncBookmarks() {
  await bookmarkService.forceSync()
  bookmarks.value = bookmarkService.getAllBookmarks()
}

function handleToggleDanmaku(enabled) {
  danmakuEnabled.value = enabled
}

function handleToggleCrop(enabled) {
  autoCropEnabled.value = enabled
  console.log('自动裁剪:', enabled)
}

function handleCropThresholdChange(threshold) {
  imageCropper.setThreshold(threshold)
}

function recordReadingProgress() {
  readingStatsService.recordPageRead(currentPage.value)
}

function handleResize() {
  if (!app) return
  
  app.renderer.resize(
    canvasContainer.value.clientWidth,
    canvasContainer.value.clientHeight
  )
  renderPages()
}

watch(viewMode, () => {
  renderPages()
})
</script>

<style scoped>
.comic-reader {
  width: 100%;
  height: 100%;
  position: relative;
  background: #1a1a1a;
  overflow: hidden;
}

.canvas-container {
  width: 100%;
  height: 100%;
}

.loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.loading-spinner {
  width: 50px;
  height: 50px;
  border: 4px solid #333;
  border-top-color: #007aff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 20px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-overlay p {
  color: #fff;
  font-size: 16px;
}
</style>
