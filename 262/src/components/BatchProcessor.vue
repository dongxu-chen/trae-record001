<template>
  <div class="batch-processor">
    <div class="panel-section">
      <h3>📦 批量处理</h3>
      
      <div class="upload-area">
        <input
          ref="batchInput"
          type="file"
          accept="image/*"
          multiple
          @change="handleBatchUpload"
          style="display: none"
        />
        <button class="btn btn-primary full-width" @click="triggerUpload">
          📁 批量上传图片
        </button>
        <p class="upload-hint">支持批量选择多张图片</p>
      </div>

      <div v-if="batchImages.length > 0" class="batch-list">
        <div class="batch-header">
          <span>图片列表 ({{ batchImages.length }})</span>
          <button class="btn small" @click="clearAll">清空</button>
        </div>
        
        <div class="thumbnail-grid">
          <div
            v-for="(img, index) in batchImages"
            :key="img.id"
            class="thumbnail-item"
            :class="{ active: currentBatchIndex === index }"
            @click="selectImage(index)"
          >
            <img :src="img.dataUrl" :alt="img.name" />
            <span class="thumbnail-name">{{ img.name }}</span>
            <button
              class="delete-btn"
              @click.stop="removeImage(img.id)"
            >
              ×
            </button>
            <span v-if="img.processed" class="processed-badge">✓</span>
          </div>
        </div>
      </div>

      <div v-if="batchImages.length > 0" class="operation-panel">
        <h4>操作设置</h4>
        
        <div class="operation-item">
          <label>
            <input type="checkbox" v-model="batchOps.rotate.enabled" />
            旋转
          </label>
          <select v-model="batchOps.rotate.angle" :disabled="!batchOps.rotate.enabled">
            <option value="90">顺时针 90°</option>
            <option value="-90">逆时针 90°</option>
            <option value="180">旋转 180°</option>
          </select>
        </div>

        <div class="operation-item">
          <label>
            <input type="checkbox" v-model="batchOps.filter.enabled" />
            滤镜调整
          </label>
        </div>
        
        <div v-if="batchOps.filter.enabled" class="filter-settings">
          <div class="slider-group small">
            <label>亮度: {{ batchOps.filter.brightness }}</label>
            <input
              type="range"
              v-model.number="batchOps.filter.brightness"
              min="-0.5"
              max="0.5"
              step="0.1"
            />
          </div>
          <div class="slider-group small">
            <label>对比度: {{ batchOps.filter.contrast }}</label>
            <input
              type="range"
              v-model.number="batchOps.filter.contrast"
              min="-0.5"
              max="0.5"
              step="0.1"
            />
          </div>
          <div class="slider-group small">
            <label>饱和度: {{ batchOps.filter.saturation }}</label>
            <input
              type="range"
              v-model.number="batchOps.filter.saturation"
              min="-0.5"
              max="0.5"
              step="0.1"
            />
          </div>
        </div>

        <div class="operation-item">
          <label>
            <input type="checkbox" v-model="batchOps.resize.enabled" />
            调整尺寸
          </label>
        </div>
        
        <div v-if="batchOps.resize.enabled" class="resize-settings">
          <div class="input-row">
            <input
              type="number"
              v-model.number="batchOps.resize.width"
              placeholder="宽度"
            />
            <span>×</span>
            <input
              type="number"
              v-model.number="batchOps.resize.height"
              placeholder="高度"
            />
          </div>
        </div>

        <button
          class="btn btn-success full-width"
          :disabled="isProcessing || !hasEnabledOps"
          @click="processBatch"
        >
          {{ isProcessing ? `处理中 ${processedCount}/${batchImages.length}` : '⚡ 批量处理' }}
        </button>

        <button
          v-if="hasProcessedImages"
          class="btn full-width"
          @click="exportAll"
        >
          💾 导出全部
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, reactive } from 'vue'

const emit = defineEmits(['imageSelected'])

const batchInput = ref(null)
const batchImages = ref([])
const currentBatchIndex = ref(-1)
const isProcessing = ref(false)
const processedCount = ref(0)

const batchOps = reactive({
  rotate: { enabled: false, angle: 90 },
  filter: { enabled: false, brightness: 0, contrast: 0, saturation: 0 },
  resize: { enabled: false, width: 800, height: 600 }
})

const hasEnabledOps = computed(() => {
  return batchOps.rotate.enabled || 
         batchOps.filter.enabled || 
         batchOps.resize.enabled
})

const hasProcessedImages = computed(() => {
  return batchImages.value.some(img => img.processed)
})

function triggerUpload() {
  batchInput.value.click()
}

async function handleBatchUpload(e) {
  const files = e.target.files
  if (!files || files.length === 0) return

  const { batchProcessor } = await import('../utils/BatchProcessor.js')
  const images = await batchProcessor.addImages(files)
  
  batchImages.value = images
  if (images.length > 0 && currentBatchIndex.value === -1) {
    currentBatchIndex.value = 0
    emit('imageSelected', images[0])
  }
  
  e.target.value = ''
}

function selectImage(index) {
  currentBatchIndex.value = index
  emit('imageSelected', batchImages.value[index])
}

function removeImage(id) {
  batchImages.value = batchImages.value.filter(img => img.id !== id)
  if (currentBatchIndex.value >= batchImages.value.length) {
    currentBatchIndex.value = Math.max(0, batchImages.value.length - 1)
  }
}

function clearAll() {
  batchImages.value = []
  currentBatchIndex.value = -1
  processedCount.value = 0
}

async function processBatch() {
  if (isProcessing.value || batchImages.value.length === 0) return

  isProcessing.value = true
  processedCount.value = 0

  const { batchProcessor } = await import('../utils/BatchProcessor.js')
  
  const operations = []
  
  if (batchOps.rotate.enabled) {
    operations.push({
      type: 'rotate',
      params: { angle: parseInt(batchOps.rotate.angle) }
    })
  }
  
  if (batchOps.filter.enabled) {
    operations.push({
      type: 'filter',
      params: {
        brightness: batchOps.filter.brightness,
        contrast: batchOps.filter.contrast,
        saturation: batchOps.filter.saturation
      }
    })
  }
  
  if (batchOps.resize.enabled) {
    operations.push({
      type: 'resize',
      params: {
        width: batchOps.resize.width,
        height: batchOps.resize.height
      }
    })
  }

  batchProcessor.setOperations(operations)
  batchProcessor.images = batchImages.value

  await batchProcessor.processAll((current, total) => {
    processedCount.value = current
  })

  batchImages.value = batchProcessor.getImages()
  isProcessing.value = false
}

async function exportAll() {
  const { batchProcessor } = await import('../utils/BatchProcessor.js')
  const files = await batchProcessor.exportAll('png')
  batchProcessor.downloadAll(files)
}
</script>

<style scoped>
.batch-processor {
  margin-bottom: 24px;
}

.upload-area {
  margin-bottom: 16px;
}

.upload-hint {
  font-size: 11px;
  color: #666;
  text-align: center;
  margin-top: 8px;
}

.batch-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  font-size: 13px;
  color: #a0a0c0;
}

.thumbnail-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  max-height: 150px;
  overflow-y: auto;
  margin-bottom: 16px;
}

.thumbnail-item {
  position: relative;
  aspect-ratio: 1;
  border-radius: 6px;
  overflow: hidden;
  cursor: pointer;
  border: 2px solid transparent;
  transition: all 0.2s;
}

.thumbnail-item:hover {
  border-color: #533483;
}

.thumbnail-item.active {
  border-color: #e94560;
}

.thumbnail-item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.thumbnail-name {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 4px;
  background: rgba(0, 0, 0, 0.7);
  font-size: 9px;
  color: #fff;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.delete-btn {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #e94560;
  color: #fff;
  border: none;
  cursor: pointer;
  font-size: 14px;
  line-height: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.delete-btn:hover {
  background: #ff6b8a;
}

.processed-badge {
  position: absolute;
  top: 4px;
  left: 4px;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #4ade80;
  color: #000;
  font-size: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.operation-panel {
  border-top: 1px solid #0f3460;
  padding-top: 16px;
}

.operation-panel h4 {
  font-size: 13px;
  color: #a0a0c0;
  margin-bottom: 12px;
}

.operation-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.operation-item label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #fff;
  cursor: pointer;
}

.operation-item select {
  padding: 4px 8px;
  background: #0f3460;
  border: 1px solid #1a1a2e;
  border-radius: 4px;
  color: #fff;
  font-size: 12px;
}

.filter-settings,
.resize-settings {
  padding: 12px;
  background: rgba(15, 52, 96, 0.3);
  border-radius: 6px;
  margin-bottom: 12px;
}

.slider-group.small label {
  font-size: 11px;
  margin-bottom: 4px;
}

.slider-group.small input[type="range"] {
  height: 4px;
}

.input-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.input-row input {
  flex: 1;
  padding: 6px 10px;
  background: #0f3460;
  border: 1px solid #1a1a2e;
  border-radius: 4px;
  color: #fff;
  font-size: 12px;
}

.input-row span {
  color: #666;
}

.btn.full-width {
  width: 100%;
  margin-bottom: 8px;
}
</style>
