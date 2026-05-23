<template>
  <div class="statistics-panel">
    <div class="stats-header">
      <h3>表单统计分析</h3>
      <button class="btn btn-default btn-small" @click="refreshStats">刷新</button>
    </div>

    <div class="stats-summary">
      <div class="summary-card">
        <div class="summary-value">{{ totalFields }}</div>
        <div class="summary-label">字段总数</div>
      </div>
      <div class="summary-card">
        <div class="summary-value">{{ avgFillRate }}</div>
        <div class="summary-label">平均填写率</div>
      </div>
      <div class="summary-card">
        <div class="summary-value">{{ totalChanges }}</div>
        <div class="summary-label">总修改次数</div>
      </div>
    </div>

    <div class="stats-section">
      <h4>字段详情</h4>
      <div class="stats-table">
        <div class="table-header">
          <span>字段名称</span>
          <span>填写率</span>
          <span>修改次数</span>
          <span>最后修改</span>
        </div>
        <div
          v-for="stat in fieldStats"
          :key="stat.fieldName"
          class="table-row"
        >
          <span class="field-name">{{ stat.fieldName }}</span>
          <span class="fill-rate" :class="getFillRateClass(stat.fillRate)">
            {{ stat.fillRate }}
          </span>
          <span class="change-count">{{ stat.changeCount }}</span>
          <span class="last-modified">{{ formatDate(stat.lastModified) }}</span>
        </div>
      </div>
    </div>

    <div v-if="suggestions.length > 0" class="stats-section">
      <h4>优化建议</h4>
      <div class="suggestions-list">
        <div
          v-for="(suggestion, index) in suggestions"
          :key="index"
          class="suggestion-item"
          :class="suggestion.type"
        >
          <span class="suggestion-icon">{{ suggestion.type === 'warning' ? '⚠️' : '💡' }}</span>
          <span class="suggestion-text">{{ suggestion.message }}</span>
        </div>
      </div>
    </div>

    <div class="stats-section">
      <h4>布局优化</h4>
      <div class="layout-options">
        <div class="layout-option">
          <label class="config-checkbox">
            <input type="checkbox" v-model="autoGroupByFillRate" />
            按填写率自动分组（低填写率字段放后面）
          </label>
        </div>
        <div class="layout-option">
          <label class="config-checkbox">
            <input type="checkbox" v-model="showOptionalCollapsed" />
            非必填字段默认折叠显示
          </label>
        </div>
        <button class="btn btn-primary btn-small" @click="applyOptimization">
          应用优化布局
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { StatisticsCollector } from '../utils/IndexedDB.js'

const props = defineProps({
  formId: {
    type: String,
    default: 'default_form'
  },
  formItems: {
    type: Array,
    default: () => []
  },
  totalSubmissions: {
    type: Number,
    default: 1
  }
})

const emit = defineEmits(['optimizeLayout'])

const fieldStats = ref([])
const suggestions = ref([])
const autoGroupByFillRate = ref(false)
const showOptionalCollapsed = ref(false)

const totalFields = computed(() => props.formItems.length)

const avgFillRate = computed(() => {
  if (fieldStats.value.length === 0) return '0%'
  const total = fieldStats.value.reduce((sum, s) => {
    return sum + parseFloat(s.fillRate || 0)
  }, 0)
  return (total / fieldStats.value.length).toFixed(1) + '%'
})

const totalChanges = computed(() => {
  return fieldStats.value.reduce((sum, s) => sum + (s.changeCount || 0), 0)
})

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

const getFillRateClass = (rate) => {
  const num = parseFloat(rate)
  if (num >= 80) return 'high'
  if (num >= 50) return 'medium'
  return 'low'
}

const loadStatistics = async () => {
  const stats = await StatisticsCollector.calculateFillRate(props.formId, props.totalSubmissions)
  
  const fieldMap = new Map(props.formItems.map(item => [item.field, item.label]))
  fieldStats.value = stats.map(s => ({
    ...s,
    fieldName: fieldMap.get(s.fieldName) || s.fieldName
  }))

  suggestions.value = StatisticsCollector.getOptimizationSuggestions(fieldStats.value)
}

const refreshStats = () => {
  loadStatistics()
}

const applyOptimization = () => {
  emit('optimizeLayout', {
    autoGroupByFillRate: autoGroupByFillRate.value,
    showOptionalCollapsed: showOptionalCollapsed.value,
    fieldStats: fieldStats.value
  })
}

watch(() => props.formItems, () => {
  loadStatistics()
}, { deep: true })

onMounted(() => {
  loadStatistics()
})
</script>

<style scoped>
.statistics-panel {
  padding: 16px;
}

.stats-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.stats-header h3 {
  margin: 0;
  font-size: 16px;
}

.stats-summary {
  display: flex;
  gap: 16px;
  margin-bottom: 24px;
}

.summary-card {
  flex: 1;
  padding: 16px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 8px;
  color: #fff;
  text-align: center;
}

.summary-card:nth-child(2) {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
}

.summary-card:nth-child(3) {
  background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
}

.summary-value {
  font-size: 28px;
  font-weight: 700;
  margin-bottom: 4px;
}

.summary-label {
  font-size: 12px;
  opacity: 0.9;
}

.stats-section {
  margin-bottom: 24px;
}

.stats-section h4 {
  margin: 0 0 12px 0;
  font-size: 14px;
  color: #303133;
}

.stats-table {
  border: 1px solid #e8e8e8;
  border-radius: 6px;
  overflow: hidden;
}

.table-header {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr 1.5fr;
  padding: 10px 12px;
  background: #f5f7fa;
  font-weight: 600;
  font-size: 13px;
  color: #606266;
}

.table-row {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr 1.5fr;
  padding: 10px 12px;
  border-top: 1px solid #e8e8e8;
  font-size: 13px;
  align-items: center;
}

.fill-rate.high {
  color: #67c23a;
  font-weight: 600;
}

.fill-rate.medium {
  color: #e6a23c;
}

.fill-rate.low {
  color: #f56c6c;
}

.last-modified {
  color: #909399;
  font-size: 12px;
}

.suggestions-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.suggestion-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 6px;
  font-size: 13px;
}

.suggestion-item.warning {
  background: #fdf6ec;
  color: #e6a23c;
}

.suggestion-item.info {
  background: #ecf5ff;
  color: #409eff;
}

.suggestion-icon {
  font-size: 16px;
}

.layout-options {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.layout-option {
  padding: 8px 0;
}
</style>
