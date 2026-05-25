<template>
  <div v-if="visible" class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-content export-modal">
      <div class="modal-header">
        <h3>导出标注数据</h3>
        <button class="modal-close" @click="$emit('close')">×</button>
      </div>

      <div class="modal-body">
        <div class="export-options">
          <h4 class="option-title">选择导出范围</h4>
          <div class="radio-group">
            <label class="radio-item">
              <input
                type="radio"
                v-model="exportScope"
                value="current"
                :disabled="!hasCurrentImage"
              />
              <span>当前图片</span>
            </label>
            <label class="radio-item">
              <input
                type="radio"
                v-model="exportScope"
                value="all"
                :disabled="!hasMultipleImages"
              />
              <span>所有图片 ({{ imagesCount }}张)</span>
            </label>
          </div>
        </div>

        <div class="export-options">
          <h4 class="option-title">选择导出格式</h4>
          <div class="format-grid">
            <div
              class="format-item"
              :class="{ active: exportFormat === 'coco' }"
              @click="exportFormat = 'coco'"
            >
              <div class="format-icon">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                  <polyline points="14 2 14 8 20 8"></polyline>
                  <line x1="16" y1="13" x2="8" y2="13"></line>
                  <line x1="16" y1="17" x2="8" y2="17"></line>
                </svg>
              </div>
              <div class="format-info">
                <div class="format-name">COCO</div>
                <div class="format-desc">Microsoft COCO 格式 JSON</div>
              </div>
              <div v-if="exportFormat === 'coco'" class="format-check">✓</div>
            </div>

            <div
              class="format-item"
              :class="{ active: exportFormat === 'voc' }"
              @click="exportFormat = 'voc'"
            >
              <div class="format-icon">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"></path>
                </svg>
              </div>
              <div class="format-info">
                <div class="format-name">PASCAL VOC</div>
                <div class="format-desc">XML 标注格式</div>
              </div>
              <div v-if="exportFormat === 'voc'" class="format-check">✓</div>
            </div>

            <div
              class="format-item"
              :class="{ active: exportFormat === 'json' }"
              @click="exportFormat = 'json'"
            >
              <div class="format-icon">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <polyline points="16 18 22 12 16 6"></polyline>
                  <polyline points="8 6 2 12 8 18"></polyline>
                </svg>
              </div>
              <div class="format-info">
                <div class="format-name">JSON</div>
                <div class="format-desc">通用 JSON 格式</div>
              </div>
              <div v-if="exportFormat === 'json'" class="format-check">✓</div>
            </div>
          </div>
        </div>

        <div class="export-options">
          <h4 class="option-title">导出预览</h4>
          <div class="preview-box">
            <div class="preview-info">
              <div class="preview-row">
                <span class="preview-label">图片数量:</span>
                <span class="preview-value">{{ exportData.length }}</span>
              </div>
              <div class="preview-row">
                <span class="preview-label">标注总数:</span>
                <span class="preview-value">{{ totalAnnotations }}</span>
              </div>
              <div class="preview-row">
                <span class="preview-label">导出格式:</span>
                <span class="preview-value">{{ formatNames[exportFormat] }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="modal-footer">
        <button class="btn btn-secondary" @click="$emit('close')">取消</button>
        <button
          class="btn btn-success"
          :disabled="exportData.length === 0 || exporting"
          @click="handleExport"
        >
          <span v-if="exporting">导出中...</span>
          <span v-else>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
              <polyline points="7 10 12 15 17 10"></polyline>
              <line x1="12" y1="15" x2="12" y2="3"></line>
            </svg>
            导出
          </span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import exportAnnotations from '../utils/export'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  currentImageData: {
    type: Object,
    default: null
  },
  allImagesData: {
    type: Array,
    default: () => []
  },
  projectInfo: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['close', 'exported'])

const exportScope = ref('current')
const exportFormat = ref('coco')
const exporting = ref(false)

const formatNames = {
  coco: 'COCO JSON',
  voc: 'PASCAL VOC XML',
  json: 'JSON'
}

const hasCurrentImage = computed(() => {
  return props.currentImageData && props.currentImageData.annotations.length > 0
})

const hasMultipleImages = computed(() => {
  return props.allImagesData.length > 1
})

const imagesCount = computed(() => props.allImagesData.length)

const exportData = computed(() => {
  if (exportScope.value === 'current' && props.currentImageData) {
    return [props.currentImageData]
  }
  return props.allImagesData.filter(d => d.annotations.length > 0)
})

const totalAnnotations = computed(() => {
  return exportData.value.reduce((sum, d) => sum + d.annotations.length, 0)
})

const handleExport = async () => {
  exporting.value = true
  try {
    await new Promise(resolve => setTimeout(resolve, 300))

    if (exportFormat.value === 'coco') {
      exportAnnotations.coco(exportData.value, props.projectInfo)
    } else if (exportFormat.value === 'voc') {
      if (exportScope.value === 'current' && props.currentImageData) {
        exportAnnotations.voc(props.currentImageData, {
          folder: props.projectInfo?.name || 'images'
        })
      } else {
        const results = exportAnnotations.vocAll(exportData.value, props.projectInfo)
        if (results.length > 1) {
          alert(`已导出 ${results.length} 个 VOC XML 文件`)
        }
      }
    } else if (exportFormat.value === 'json') {
      exportAnnotations.json(exportData.value, props.projectInfo)
    }

    emit('exported', { format: exportFormat.value, scope: exportScope.value })
    emit('close')
  } catch (error) {
    console.error('导出失败:', error)
    alert('导出失败: ' + error.message)
  } finally {
    exporting.value = false
  }
}

watch(() => props.visible, (val) => {
  if (val) {
    if (hasCurrentImage.value) {
      exportScope.value = 'current'
    } else if (hasMultipleImages.value) {
      exportScope.value = 'all'
    }
  }
})
</script>

<style scoped>
.export-modal {
  min-width: 500px;
}

.export-options {
  margin-bottom: 24px;
}

.option-title {
  font-size: 13px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 12px;
}

.radio-group {
  display: flex;
  gap: 16px;
}

.radio-item {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-size: 14px;
  color: #606266;
}

.radio-item input[type="radio"]:disabled + span {
  color: #c0c4cc;
  cursor: not-allowed;
}

.format-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.format-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  border: 2px solid #ebeef5;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  position: relative;
}

.format-item:hover {
  border-color: #409eff;
  background-color: #ecf5ff;
}

.format-item.active {
  border-color: #409eff;
  background-color: #ecf5ff;
}

.format-icon {
  color: #409eff;
  flex-shrink: 0;
}

.format-info {
  flex: 1;
  min-width: 0;
}

.format-name {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 2px;
}

.format-desc {
  font-size: 11px;
  color: #909399;
}

.format-check {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background-color: #409eff;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
}

.preview-box {
  background-color: #f5f7fa;
  border-radius: 6px;
  padding: 16px;
}

.preview-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.preview-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.preview-label {
  font-size: 13px;
  color: #909399;
}

.preview-value {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}
</style>
