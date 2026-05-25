<template>
  <div v-if="visible" class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-content ai-modal">
      <div class="modal-header">
        <h3>
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 2a5 5 0 0 0-5 5v1a5 5 0 0 0-2 4v5a5 5 0 0 0 5 5h8a5 5 0 0 0 5-5v-5a5 5 0 0 0-2-4V7a5 5 0 0 0-5-5z"></path>
          </svg>
          AI 预标注结果
        </h3>
        <button class="modal-close" @click="$emit('close')">×</button>
      </div>

      <div class="modal-body ai-body">
        <div v-if="isProcessing" class="processing-section">
          <div class="processing-animation">
            <div class="ai-spinner"></div>
          </div>
          <p class="processing-text">AI 正在分析图表...</p>
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: progress + '%' }"></div>
          </div>
          <p class="progress-text">{{ progress }}%</p>
        </div>

        <div v-else-if="results" class="results-section">
          <div class="results-summary">
            <div class="summary-item">
              <span class="summary-label">检测到标注</span>
              <span class="summary-value">{{ results.all?.length || 0 }}</span>
            </div>
            <div class="summary-item">
              <span class="summary-label">自动采纳</span>
              <span class="summary-value auto">{{ results.autoAccepted?.length || 0 }}</span>
            </div>
            <div class="summary-item">
              <span class="summary-label">待审核</span>
              <span class="summary-value review">{{ results.needReview?.length || 0 }}</span>
            </div>
          </div>

          <div v-if="results.autoAccepted?.length > 0" class="results-group">
            <h4 class="group-title">
              <span class="group-icon auto">✓</span>
              自动采纳 (置信度 ≥ {{ (autoAcceptThreshold * 100).toFixed(0) }}%)
            </h4>
            <div class="annotations-list">
              <div 
                v-for="ann in results.autoAccepted" 
                :key="ann.id"
                class="annotation-item auto"
              >
                <div class="annotation-header">
                  <span class="category-badge" :style="{ backgroundColor: ann.color }">
                    {{ getCategoryName(ann.category) }}
                  </span>
                  <span class="confidence-badge" :class="getConfidenceClass(ann.confidence)">
                    {{ (ann.confidence * 100).toFixed(0) }}%
                  </span>
                </div>
                <div class="annotation-label">{{ ann.label }}</div>
                <div class="annotation-coords">
                  {{ formatCoords(ann.imageCoords) }}
                </div>
              </div>
            </div>
          </div>

          <div v-if="results.needReview?.length > 0" class="results-group">
            <h4 class="group-title">
              <span class="group-icon review">!</span>
              待审核 (置信度 {{ (minConfidence * 100).toFixed(0) }}% - {{ (autoAcceptThreshold * 100).toFixed(0) }}%)
            </h4>
            <div class="annotations-list">
              <div 
                v-for="ann in results.needReview" 
                :key="ann.id"
                class="annotation-item review"
                :class="{ selected: selectedIds.includes(ann.id) }"
                @click="toggleSelection(ann.id)"
              >
                <div class="annotation-checkbox">
                  <input type="checkbox" :checked="selectedIds.includes(ann.id)" />
                </div>
                <div class="annotation-content">
                  <div class="annotation-header">
                    <span class="category-badge" :style="{ backgroundColor: ann.color }">
                      {{ getCategoryName(ann.category) }}
                    </span>
                    <span class="confidence-badge" :class="getConfidenceClass(ann.confidence)">
                      {{ (ann.confidence * 100).toFixed(0) }}%
                    </span>
                  </div>
                  <div class="annotation-label">{{ ann.label }}</div>
                  <div class="annotation-coords">
                    {{ formatCoords(ann.imageCoords) }}
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div v-if="!results.all?.length" class="no-results">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <circle cx="12" cy="12" r="10"></circle>
              <line x1="12" y1="8" x2="12" y2="12"></line>
              <line x1="12" y1="16" x2="12.01" y2="16"></line>
            </svg>
            <p>未检测到可标注的图表元素</p>
            <p class="hint">请尝试调整置信度阈值后重试</p>
          </div>
        </div>

        <div class="settings-section">
          <h4 class="group-title">检测设置</h4>
          <div class="settings-grid">
            <div class="setting-item">
              <label>最小置信度</label>
              <input 
                type="range" 
                v-model.number="minConfidence" 
                min="0.3" 
                max="0.8" 
                step="0.05"
                @change="updateThresholds"
              />
              <span class="setting-value">{{ (minConfidence * 100).toFixed(0) }}%</span>
            </div>
            <div class="setting-item">
              <label>自动采纳阈值</label>
              <input 
                type="range" 
                v-model.number="autoAcceptThreshold" 
                min="0.6" 
                max="0.95" 
                step="0.05"
                @change="updateThresholds"
              />
              <span class="setting-value">{{ (autoAcceptThreshold * 100).toFixed(0) }}%</span>
            </div>
          </div>
          <button 
            v-if="!isProcessing" 
            class="btn btn-secondary reanalyze-btn"
            @click="reAnalyze"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M23 4v6h-6"></path>
              <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path>
            </svg>
            重新分析
          </button>
        </div>
      </div>

      <div class="modal-footer">
        <button class="btn btn-secondary" @click="$emit('close')">取消</button>
        <button 
          class="btn btn-primary"
          :disabled="isProcessing || !hasAnnotationsToAdd"
          @click="applyAnnotations"
        >
          <span v-if="isProcessing">处理中...</span>
          <span v-else>应用标注 ({{ getSelectedCount() }})</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import aiPreAnnotator from '../utils/aiPreannotation'
import { ANNOTATION_CATEGORIES, CONFIDENCE_LEVELS } from '../constants'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  imageElement: {
    type: Object,
    default: null
  },
  imageInfo: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['close', 'apply'])

const isProcessing = ref(false)
const progress = ref(0)
const results = ref(null)
const selectedIds = ref([])
const minConfidence = ref(aiPreAnnotator.minConfidence.value)
const autoAcceptThreshold = ref(aiPreAnnotator.autoAcceptThreshold.value)

const hasAnnotationsToAdd = computed(() => {
  return getSelectedCount() > 0
})

watch(() => props.visible, (val) => {
  if (val && props.imageElement && props.imageInfo) {
    runPreAnnotation()
  }
})

watch(aiPreAnnotator.progress, (val) => {
  progress.value = val
})

const runPreAnnotation = async () => {
  isProcessing.value = true
  progress.value = 0
  results.value = null
  selectedIds.value = []

  try {
    const result = await aiPreAnnotator.preAnnotate(props.imageElement, props.imageInfo)
    results.value = result
    selectedIds.value = result.needReview?.map(a => a.id) || []
  } catch (error) {
    console.error('Pre-annotation error:', error)
  } finally {
    isProcessing.value = false
  }
}

const toggleSelection = (id) => {
  const idx = selectedIds.value.indexOf(id)
  if (idx !== -1) {
    selectedIds.value.splice(idx, 1)
  } else {
    selectedIds.value.push(id)
  }
}

const getSelectedCount = () => {
  const autoCount = results.value?.autoAccepted?.length || 0
  const selectedCount = selectedIds.value.length
  return autoCount + selectedCount
}

const applyAnnotations = () => {
  const autoAccepted = results.value?.autoAccepted || []
  const selected = (results.value?.needReview || []).filter(
    a => selectedIds.value.includes(a.id)
  )
  
  const allAnnotations = [...autoAccepted, ...selected].map(a => ({
    ...a,
    status: a.confidence >= autoAcceptThreshold.value ? 'approved' : 'manual_approved'
  }))
  
  emit('apply', allAnnotations)
  emit('close')
}

const getCategoryName = (categoryId) => {
  const cat = ANNOTATION_CATEGORIES.find(c => c.id === categoryId)
  return cat ? cat.name : categoryId
}

const getConfidenceClass = (confidence) => {
  if (confidence >= CONFIDENCE_LEVELS.HIGH.min) return 'high'
  if (confidence >= CONFIDENCE_LEVELS.MEDIUM.min) return 'medium'
  return 'low'
}

const formatCoords = (coords) => {
  if (!coords) return ''
  return `${coords.x?.toFixed(0) || coords.left?.toFixed(0) || 0}, ${coords.y?.toFixed(0) || coords.top?.toFixed(0) || 0} - ${(coords.width).toFixed(0)}×${(coords.height).toFixed(0)}`
}

const updateThresholds = () => {
  aiPreAnnotator.setMinConfidence(minConfidence.value)
  aiPreAnnotator.setAutoAcceptThreshold(autoAcceptThreshold.value)
}

const reAnalyze = () => {
  updateThresholds()
  runPreAnnotation()
}
</script>

<style scoped>
.ai-modal {
  min-width: 650px;
  max-width: 700px;
  max-height: 85vh;
}

.ai-body {
  overflow-y: auto;
  max-height: calc(85vh - 120px);
  padding: 20px;
  position: relative;
}

.processing-section {
  text-align: center;
  padding: 40px 20px;
}

.processing-animation {
  margin-bottom: 20px;
}

.ai-spinner {
  width: 60px;
  height: 60px;
  margin: 0 auto;
  border: 4px solid #e8e8e8;
  border-top-color: #9c27b0;
  border-right-color: #9c27b0;
  border-radius: 50%;
  animation: ai-spin 1s linear infinite;
}

@keyframes ai-spin {
  to { transform: rotate(360deg); }
}

.processing-text {
  font-size: 16px;
  color: #303133;
  margin-bottom: 16px;
}

.progress-bar {
  width: 200px;
  height: 8px;
  background: #f0f2f5;
  border-radius: 4px;
  margin: 0 auto 8px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #9c27b0 0%, #ba68c8 100%);
  border-radius: 4px;
  transition: width 0.3s ease;
}

.progress-text {
  font-size: 13px;
  color: #909399;
}

.results-summary {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.summary-item {
  text-align: center;
  padding: 16px;
  background: #f5f7fa;
  border-radius: 12px;
}

.summary-label {
  display: block;
  font-size: 13px;
  color: #909399;
  margin-bottom: 4px;
}

.summary-value {
  font-size: 28px;
  font-weight: 700;
  color: #303133;
}

.summary-value.auto { color: #67c23a; }
.summary-value.review { color: #e6a23c; }

.results-group {
  margin-bottom: 24px;
}

.group-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 12px;
}

.group-icon {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  color: #fff;
}

.group-icon.auto { background: #67c23a; }
.group-icon.review { background: #e6a23c; }

.annotations-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 300px;
  overflow-y: auto;
}

.annotation-item {
  display: flex;
  gap: 12px;
  padding: 12px;
  background: #fff;
  border: 2px solid #ebeef5;
  border-radius: 8px;
  transition: all 0.2s ease;
}

.annotation-item.review {
  cursor: pointer;
}

.annotation-item.review:hover {
  border-color: #9c27b0;
  background: #faf5ff;
}

.annotation-item.review.selected {
  border-color: #9c27b0;
  background: #f3e8ff;
}

.annotation-item.auto {
  opacity: 0.85;
}

.annotation-checkbox {
  display: flex;
  align-items: flex-start;
  padding-top: 4px;
}

.annotation-content {
  flex: 1;
}

.annotation-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.category-badge {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
  color: #fff;
}

.confidence-badge {
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
}

.confidence-badge.high { background: #f0f9eb; color: #67c23a; }
.confidence-badge.medium { background: #fdf6ec; color: #e6a23c; }
.confidence-badge.low { background: #fef0f0; color: #f56c6c; }

.annotation-label {
  font-size: 13px;
  color: #303133;
  font-weight: 500;
  margin-bottom: 2px;
}

.annotation-coords {
  font-size: 11px;
  color: #909399;
  font-family: 'Courier New', monospace;
}

.no-results {
  text-align: center;
  padding: 40px 20px;
  color: #909399;
}

.no-results svg {
  margin-bottom: 16px;
  opacity: 0.5;
}

.no-results p {
  margin: 0 0 8px;
  font-size: 14px;
}

.no-results .hint {
  font-size: 12px;
}

.settings-section {
  padding: 16px;
  background: #f5f7fa;
  border-radius: 8px;
}

.settings-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin-bottom: 12px;
}

.setting-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.setting-item label {
  font-size: 12px;
  color: #606266;
  font-weight: 500;
}

.setting-item input[type="range"] {
  width: 100%;
  height: 6px;
  -webkit-appearance: none;
  background: #dcdfe6;
  border-radius: 3px;
  outline: none;
}

.setting-item input[type="range"]::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 16px;
  height: 16px;
  background: #9c27b0;
  border-radius: 50%;
  cursor: pointer;
}

.setting-value {
  font-size: 12px;
  color: #9c27b0;
  font-weight: 600;
  text-align: right;
}

.reanalyze-btn {
  width: 100%;
  justify-content: center;
}
</style>
