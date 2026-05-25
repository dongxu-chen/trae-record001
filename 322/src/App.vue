<template>
  <div class="app-container">
    <Toolbar
      @upload="handleUpload"
      @export="showExportModal = true"
      @check-quality="showQualityModal = true"
      @tool-change="handleToolChange"
      @category-change="handleCategoryChange"
      @ai-preannotate="showAIPreannotateModal = true"
      @show-statistics="showStatisticsModal = true"
      @show-shortcuts="showShortcutModal = true"
    />

    <div class="main-content">
      <CanvasArea
        ref="canvasAreaRef"
        :project-id="currentProjectId"
        :image-id="currentImageId"
        @image-loaded="handleImageLoaded"
        @annotation-add="handleAnnotationAdd"
        @annotation-update="handleAnnotationUpdate"
        @annotation-delete="handleAnnotationDelete"
      />

      <Sidebar
        :annotations="annotations"
        :selected-annotation="selectedAnnotation"
        @update:selected-annotation="selectedAnnotation = $event"
        @category-change="handleCategoryChange"
        @annotation-delete="handleAnnotationDelete"
        @annotation-update="handleAnnotationUpdate"
      />
    </div>

    <QualityCheckModal
      :visible="showQualityModal"
      :annotations="annotations"
      :image-info="currentImageInfo"
      @close="showQualityModal = false"
      @optimize="handleOptimize"
    />

    <ExportModal
      :visible="showExportModal"
      :current-image-data="currentImageData"
      :all-images-data="allImagesData"
      :project-info="currentProject"
      @close="showExportModal = false"
      @exported="handleExported"
    />

    <AIPreannotationModal
      :visible="showAIPreannotateModal"
      :image-element="currentImageElement"
      :image-info="canvasManager.imageInfo"
      @close="showAIPreannotateModal = false"
      @apply="handleAIApplyAnnotations"
    />

    <StatisticsDashboard
      :visible="showStatisticsModal"
      :annotations="annotations"
      :images="allImages"
      :total-targets="100"
      @close="showStatisticsModal = false"
    />

    <ShortcutSettings
      :visible="showShortcutModal"
      @close="showShortcutModal = false"
    />

    <div v-if="showWelcome" class="welcome-overlay">
      <div class="welcome-content">
        <div class="welcome-logo">
          <svg width="80" height="80" viewBox="0 0 24 24" fill="none" stroke="#409eff" stroke-width="1.5">
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
            <line x1="3" y1="9" x2="21" y2="9"></line>
            <line x1="9" y1="21" x2="9" y2="9"></line>
            <path d="M21 15l-5-5L5 21"></path>
          </svg>
        </div>
        <h1>图表标注工具</h1>
        <p class="welcome-desc">支持多种标注类型、多人协作、格式导出</p>

        <div class="feature-grid">
          <div class="feature-item">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#409eff" stroke-width="2">
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
            </svg>
            <span>矩形框标注</span>
          </div>
          <div class="feature-item">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#67c23a" stroke-width="2">
              <line x1="5" y1="12" x2="19" y2="12"></line>
              <polyline points="12 5 19 12 12 19"></polyline>
            </svg>
            <span>箭头标注</span>
          </div>
          <div class="feature-item">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#e6a23c" stroke-width="2">
              <polyline points="4 7 4 4 20 4 20 7"></polyline>
              <line x1="9" y1="20" x2="15" y2="20"></line>
              <line x1="12" y1="4" x2="12" y2="20"></line>
            </svg>
            <span>文本注释</span>
          </div>
          <div class="feature-item">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#f56c6c" stroke-width="2">
              <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
              <circle cx="9" cy="7" r="4"></circle>
              <path d="M23 21v-2a4 4 0 0 0-3-3.87"></path>
              <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
            </svg>
            <span>多人协作</span>
          </div>
          <div class="feature-item">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#909399" stroke-width="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
              <polyline points="14 2 14 8 20 8"></polyline>
            </svg>
            <span>COCO/VOC导出</span>
          </div>
          <div class="feature-item">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#9c27b0" stroke-width="2">
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
              <polyline points="22 4 12 14.01 9 11.01"></polyline>
            </svg>
            <span>质量检查</span>
          </div>
        </div>

        <div class="welcome-actions">
          <label class="btn btn-primary btn-lg">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
              <polyline points="17 8 12 3 7 8"></polyline>
              <line x1="12" y1="3" x2="12" y2="15"></line>
            </svg>
            开始标注
            <input
              type="file"
              accept="image/*"
              @change="handleWelcomeUpload"
              style="display: none"
            />
          </label>
          <button class="btn btn-secondary btn-lg" @click="showWelcome = false">
            稍后再说
          </button>
        </div>

        <div class="welcome-tips">
          <h4>快捷键</h4>
          <div class="tips-grid">
            <span><kbd>V</kbd> 选择</span>
            <span><kbd>R</kbd> 矩形</span>
            <span><kbd>A</kbd> 箭头</span>
            <span><kbd>T</kbd> 文本</span>
            <span><kbd>H</kbd> 平移</span>
            <span><kbd>Ctrl+Z</kbd> 撤销</span>
            <span><kbd>Ctrl+Y</kbd> 重做</span>
            <span><kbd>Delete</kbd> 删除</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import Toolbar from './components/Toolbar.vue'
import CanvasArea from './components/CanvasArea.vue'
import Sidebar from './components/Sidebar.vue'
import QualityCheckModal from './components/QualityCheckModal.vue'
import ExportModal from './components/ExportModal.vue'
import AIPreannotationModal from './components/AIPreannotationModal.vue'
import StatisticsDashboard from './components/StatisticsDashboard.vue'
import ShortcutSettings from './components/ShortcutSettings.vue'
import canvasManager from './utils/canvasManager'
import db from './utils/db'

const canvasAreaRef = ref(null)
const showWelcome = ref(true)
const showQualityModal = ref(false)
const showExportModal = ref(false)
const showAIPreannotateModal = ref(false)
const showStatisticsModal = ref(false)
const showShortcutModal = ref(false)

const currentProjectId = ref(null)
const currentImageId = ref(null)
const currentImage = ref(null)
const currentImageElement = ref(null)
const currentProject = ref(null)
const allImages = ref([])
const selectedAnnotation = ref(null)

const annotations = computed(() => canvasManager.annotations.value)

const currentImageInfo = computed(() => {
  if (!currentImage.value) return null
  return {
    width: currentImage.value.width,
    height: currentImage.value.height
  }
})

const currentImageData = computed(() => {
  if (!currentImage.value) return null
  return {
    image: {
      id: currentImage.value.id,
      name: currentImage.value.name,
      width: currentImage.value.width,
      height: currentImage.value.height
    },
    annotations: annotations.value
  }
})

const allImagesData = ref([])

const initProject = async () => {
  await db.init()

  let projects = await db.getProjects()
  if (projects.length === 0) {
    const project = await db.createProject({
      name: '图表标注项目',
      description: '默认图表标注项目'
    })
    projects = [project]
  }

  currentProject.value = projects[0]
  currentProjectId.value = projects[0].id

  const images = await db.getImages(currentProjectId.value)
  allImagesData.value = []
  for (const img of images) {
    const anns = await db.getAnnotations(img.id)
    allImagesData.value.push({
      image: {
        id: img.id,
        name: img.name,
        width: img.width,
        height: img.height
      },
      annotations: anns
    })
  }

  if (images.length > 0) {
    currentImageId.value = images[0].id
    showWelcome.value = false
  }
}

const handleUpload = () => {
  canvasAreaRef.value?.triggerFileInput()
}

const handleWelcomeUpload = (e) => {
  const file = e.target.files[0]
  if (file) {
    showWelcome.value = false
    const input = canvasAreaRef.value?.$refs.fileInputRef
    if (input) {
      const dt = new DataTransfer()
      dt.items.add(file)
      input.files = dt.files
      input.dispatchEvent(new Event('change'))
    }
  }
}

const handleImageLoaded = (imageData) => {
  currentImage.value = imageData
  currentImageId.value = imageData.id
  showWelcome.value = false
  
  if (canvasManager.backgroundImage) {
    const img = canvasManager.backgroundImage.getElement()
    if (img instanceof HTMLImageElement) {
      currentImageElement.value = img
    }
  }

  const idx = allImagesData.value.findIndex(d => d.image.id === imageData.id)
  const data = {
    image: {
      id: imageData.id,
      name: imageData.name,
      width: imageData.width,
      height: imageData.height
    },
    annotations: annotations.value
  }
  if (idx >= 0) {
    allImagesData.value[idx] = data
  } else {
    allImagesData.value.push(data)
  }
  
  loadAllImages()
}

const handleAIApplyAnnotations = async (annotations) => {
  for (const ann of annotations) {
    try {
      await canvasManager.addAnnotationFromData(ann)
      
      const fullAnnotation = {
        ...ann,
        projectId: currentProjectId.value,
        imageId: currentImageId.value
      }
      
      canvasManager.annotations.value.push(fullAnnotation)
      
      if (currentProjectId.value && currentImageId.value) {
        await db.addAnnotation(fullAnnotation)
      }
    } catch (e) {
      console.error('Failed to add AI annotation:', e)
    }
  }
  
  canvasManager.canvas?.renderAll()
  updateAllImagesData()
}

const loadAllImages = async () => {
  if (currentProjectId.value) {
    allImages.value = await db.getImages(currentProjectId.value)
  }
}

const handleAnnotationAdd = (annotation) => {
  updateAllImagesData()
}

const handleAnnotationUpdate = (annotation) => {
  updateAllImagesData()
  const idx = annotations.value.findIndex(a => a.id === annotation.id)
  if (idx >= 0) {
    selectedAnnotation.value = annotations.value[idx]
  }
}

const handleAnnotationDelete = (annotationId) => {
  if (selectedAnnotation.value?.id === annotationId) {
    selectedAnnotation.value = null
  }
  updateAllImagesData()
}

const updateAllImagesData = () => {
  if (!currentImage.value) return
  const idx = allImagesData.value.findIndex(d => d.image.id === currentImage.value.id)
  if (idx >= 0) {
    allImagesData.value[idx].annotations = [...annotations.value]
  }
}

const handleToolChange = (tool) => {
  console.log('Tool changed:', tool)
}

const handleCategoryChange = (category) => {
  console.log('Category changed:', category)
}

const handleOptimize = () => {
  alert('一键优化功能将在后续版本中实现')
}

const handleExported = (result) => {
  console.log('Exported:', result)
}

watch(annotations, () => {
  updateAllImagesData()
}, { deep: true })

onMounted(() => {
  initProject()

  canvasManager.on('annotation:select', (annotation) => {
    selectedAnnotation.value = annotation
  })
})
</script>

<style scoped>
.app-container {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
}

.main-content {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.welcome-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(245, 247, 250, 0.98);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  overflow-y: auto;
}

.welcome-content {
  text-align: center;
  max-width: 700px;
  padding: 40px;
}

.welcome-logo {
  margin-bottom: 24px;
}

.welcome-content h1 {
  font-size: 36px;
  font-weight: 700;
  color: #303133;
  margin-bottom: 12px;
}

.welcome-desc {
  font-size: 16px;
  color: #909399;
  margin-bottom: 40px;
}

.feature-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 40px;
}

.feature-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 20px 16px;
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  font-size: 13px;
  color: #606266;
  transition: all 0.2s;
}

.feature-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
}

.welcome-actions {
  display: flex;
  justify-content: center;
  gap: 16px;
  margin-bottom: 40px;
}

.btn-lg {
  padding: 12px 32px;
  font-size: 16px;
}

.welcome-tips {
  background-color: #fff;
  border-radius: 8px;
  padding: 20px 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.welcome-tips h4 {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 16px;
}

.tips-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  font-size: 13px;
  color: #606266;
}

.tips-grid span {
  display: flex;
  align-items: center;
  gap: 6px;
}

kbd {
  display: inline-block;
  padding: 2px 8px;
  background-color: #f5f7fa;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  font-family: monospace;
  font-size: 12px;
  color: #606266;
}
</style>
