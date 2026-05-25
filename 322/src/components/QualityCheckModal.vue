<template>
  <div v-if="visible" class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-content quality-modal">
      <div class="modal-header">
        <h3>标注质量检查</h3>
        <button class="modal-close" @click="$emit('close')">×</button>
      </div>

      <div class="modal-body">
        <div v-if="!result" class="checking">
          <div class="spinner"></div>
          <p>正在检查标注质量...</p>
        </div>

        <div v-else class="quality-result">
          <div class="score-section">
            <div class="score-circle" :style="{ borderColor: scoreColor }">
              <span class="score-value" :style="{ color: scoreColor }">{{ result.score }}</span>
              <span class="score-label">分</span>
            </div>
            <div class="score-info">
              <div class="score-level" :style="{ color: scoreColor }">
                {{ levelText }}
              </div>
              <div class="score-desc">
                共 {{ result.stats?.total || 0 }} 个标注
              </div>
            </div>
          </div>

          <div class="details-section">
            <div v-for="(detail, key) in result.details" :key="key" class="detail-item">
              <div class="detail-header">
                <span class="detail-name">{{ detail.description }}</span>
                <span class="detail-score">{{ detail.score }}分</span>
              </div>
              <div class="quality-score">
                <div class="score-bar">
                  <div
                    class="score-fill"
                    :style="{
                      width: detail.score + '%',
                      backgroundColor: getScoreColor(detail.score)
                    }"
                  ></div>
                </div>
              </div>
              <div class="checks">
                <span
                  v-for="check in detail.checks"
                  :key="check.name"
                  class="check-tag"
                  :class="{ pass: check.pass, fail: !check.pass }"
                >
                  <span v-if="check.pass">✓</span>
                  <span v-else>✗</span>
                  {{ check.name }}
                </span>
              </div>
            </div>
          </div>

          <div v-if="result.issues?.length > 0" class="issues-section">
            <h4 class="section-title">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="12" y1="8" x2="12" y2="12"></line>
                <line x1="12" y1="16" x2="12.01" y2="16"></line>
              </svg>
              严重问题 ({{ result.issues.length }})
            </h4>
            <div class="issue-list">
              <div v-for="issue in result.issues" :key="issue.id" class="issue-item error">
                <span class="issue-icon">!</span>
                <span class="issue-message">{{ issue.message }}</span>
              </div>
            </div>
          </div>

          <div v-if="result.warnings?.length > 0" class="warnings-section">
            <h4 class="section-title">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
                <line x1="12" y1="9" x2="12" y2="13"></line>
                <line x1="12" y1="17" x2="12.01" y2="17"></line>
              </svg>
              警告 ({{ result.warnings.length }})
            </h4>
            <div class="issue-list">
              <div v-for="warning in result.warnings" :key="warning.id" class="issue-item warning">
                <span class="issue-icon">!</span>
                <span class="issue-message">{{ warning.message }}</span>
              </div>
            </div>
          </div>

          <div v-if="result.passed?.length > 0" class="passed-section">
            <h4 class="section-title">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                <polyline points="22 4 12 14.01 9 11.01"></polyline>
              </svg>
              通过检查 ({{ result.passed.length }})
            </h4>
            <div class="passed-list">
              <div v-for="pass in result.passed" :key="pass.id" class="passed-item">
                <span class="passed-icon">✓</span>
                <span class="passed-message">{{ pass.message }}</span>
              </div>
            </div>
          </div>

          <div v-if="result.reasonableness?.length > 0" class="reasonableness-section">
            <h4 class="section-title">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                <polyline points="14 2 14 8 20 8"></polyline>
                <line x1="16" y1="13" x2="8" y2="13"></line>
                <line x1="16" y1="17" x2="8" y2="17"></line>
                <polyline points="10 9 9 9 8 9"></polyline>
              </svg>
              合理性检查
            </h4>
            <div class="reasonableness-list">
              <div 
                v-for="check in result.reasonableness" 
                :key="check.id" 
                class="reasonableness-item"
                :class="check.type"
              >
                <span class="reasonableness-icon">
                  <span v-if="check.type === 'pass'">✓</span>
                  <span v-else>!</span>
                </span>
                <div class="reasonableness-content">
                  <span class="reasonableness-message">{{ check.message }}</span>
                  <div v-if="check.category" class="reasonableness-category">
                    <span class="category-tag">{{ getCategoryLabel(check.category) }}</span>
                  </div>
                  <div v-if="check.currentPosition || check.currentWidth || check.currentDistance" class="reasonableness-details">
                    <span v-if="check.currentPosition">当前: {{ check.currentPosition }}</span>
                    <span v-if="check.expectedPosition">, 期望: {{ check.expectedPosition }}</span>
                    <span v-if="check.currentWidth">当前: {{ check.currentWidth }}</span>
                    <span v-if="check.expectedRange">, 范围: {{ check.expectedRange }}</span>
                    <span v-if="check.currentDistance">当前距离: {{ check.currentDistance }}</span>
                    <span v-if="check.expectedDistance">, 期望: {{ check.expectedDistance }}</span>
                    <span v-if="check.currentRatio">当前比例: {{ check.currentRatio }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div v-if="result.stats" class="stats-section">
            <h4 class="section-title">统计信息</h4>
            <div class="stats-grid">
              <div class="stat-item">
                <span class="stat-label">矩形框</span>
                <span class="stat-value">{{ result.stats.byType?.rectangle || 0 }}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">箭头</span>
                <span class="stat-value">{{ result.stats.byType?.arrow || 0 }}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">文本</span>
                <span class="stat-value">{{ result.stats.byType?.text || 0 }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="modal-footer">
        <button class="btn btn-secondary" @click="$emit('close')">关闭</button>
        <button
          class="btn btn-primary"
          :disabled="result.score >= 80"
          @click="$emit('optimize')"
        >
          一键优化
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { checkAnnotationQuality, getQualityLevelColor, getQualityLevelText } from '../utils/qualityCheck'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  annotations: {
    type: Array,
    default: () => []
  },
  imageInfo: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['close', 'optimize'])

const result = ref(null)
const checking = ref(false)

const scoreColor = computed(() => {
  if (!result.value) return '#909399'
  return getQualityLevelColor(result.value.level)
})

const levelText = computed(() => {
  if (!result.value) return ''
  return getQualityLevelText(result.value.level)
})

const getScoreColor = (score) => {
  if (score >= 90) return '#67c23a'
  if (score >= 80) return '#409eff'
  if (score >= 60) return '#e6a23c'
  return '#f56c6c'
}

const getCategoryLabel = (category) => {
  const labels = {
    position: '位置',
    size: '尺寸',
    relation: '关系'
  }
  return labels[category] || category
}

watch(() => props.visible, async (val) => {
  if (val) {
    checking.value = true
    result.value = null
    await new Promise(resolve => setTimeout(resolve, 500))
    result.value = checkAnnotationQuality(props.annotations, props.imageInfo)
    checking.value = false
  }
})
</script>

<style scoped>
.quality-modal {
  min-width: 500px;
  max-width: 600px;
}

.checking {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  color: #909399;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #ebeef5;
  border-top-color: #409eff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 16px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.score-section {
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 24px;
  background: linear-gradient(135deg, #f5f7fa 0%, #ecf5ff 100%);
  border-radius: 8px;
  margin-bottom: 24px;
}

.score-circle {
  width: 100px;
  height: 100px;
  border-radius: 50%;
  border: 6px solid;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background-color: #fff;
}

.score-value {
  font-size: 36px;
  font-weight: 700;
  line-height: 1;
}

.score-label {
  font-size: 14px;
  color: #909399;
}

.score-info {
  flex: 1;
}

.score-level {
  font-size: 24px;
  font-weight: 600;
  margin-bottom: 8px;
}

.score-desc {
  font-size: 14px;
  color: #606266;
}

.details-section {
  margin-bottom: 24px;
}

.detail-item {
  margin-bottom: 16px;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.detail-name {
  font-size: 13px;
  font-weight: 500;
  color: #303133;
}

.detail-score {
  font-size: 13px;
  font-weight: 600;
  color: #606266;
}

.checks {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}

.check-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 11px;
}

.check-tag.pass {
  background-color: #f0f9eb;
  color: #67c23a;
}

.check-tag.fail {
  background-color: #fef0f0;
  color: #f56c6c;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 12px;
}

.issues-section .section-title {
  color: #f56c6c;
}

.warnings-section .section-title {
  color: #e6a23c;
}

.passed-section .section-title {
  color: #67c23a;
}

.issues-section,
.warnings-section,
.passed-section {
  margin-bottom: 20px;
}

.issue-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.issue-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 6px;
  font-size: 13px;
}

.issue-item.error {
  background-color: #fef0f0;
  color: #f56c6c;
}

.issue-item.warning {
  background-color: #fdf6ec;
  color: #e6a23c;
}

.issue-icon {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background-color: currentColor;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  flex-shrink: 0;
}

.passed-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.passed-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  background-color: #f0f9eb;
  border-radius: 6px;
  font-size: 13px;
  color: #67c23a;
}

.passed-icon {
  font-size: 14px;
  font-weight: 700;
}

.stats-section {
  padding-top: 16px;
  border-top: 1px solid #ebeef5;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 12px;
  background-color: #f5f7fa;
  border-radius: 6px;
}

.stat-label {
  font-size: 12px;
  color: #909399;
  margin-bottom: 4px;
}

.stat-value {
  font-size: 20px;
  font-weight: 600;
  color: #303133;
}

.reasonableness-section {
  margin-bottom: 20px;
}

.reasonableness-section .section-title {
  color: #9c27b0;
}

.reasonableness-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.reasonableness-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px;
  border-radius: 6px;
  font-size: 13px;
}

.reasonableness-item.pass {
  background-color: #f0f9eb;
  color: #67c23a;
}

.reasonableness-item.warning {
  background-color: #fdf6ec;
  color: #e6a23c;
}

.reasonableness-item.error {
  background-color: #fef0f0;
  color: #f56c6c;
}

.reasonableness-icon {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background-color: currentColor;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  flex-shrink: 0;
}

.reasonableness-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.reasonableness-message {
  font-weight: 500;
}

.reasonableness-category {
  display: flex;
  gap: 6px;
}

.category-tag {
  display: inline-block;
  padding: 2px 6px;
  background-color: rgba(255, 255, 255, 0.5);
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
}

.reasonableness-details {
  font-size: 11px;
  opacity: 0.8;
  font-family: 'Courier New', monospace;
}
</style>
