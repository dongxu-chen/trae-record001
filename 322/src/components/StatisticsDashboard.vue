<template>
  <div v-if="visible" class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-content dashboard-modal">
      <div class="modal-header">
        <h3>
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
            <line x1="3" y1="9" x2="21" y2="9"></line>
            <line x1="9" y1="21" x2="9" y2="9"></line>
            <path d="M9 15l3-3 3 3 4-4"></path>
          </svg>
          标注统计仪表板
        </h3>
        <button class="modal-close" @click="$emit('close')">×</button>
      </div>

      <div class="modal-body dashboard-body">
        <div v-if="loading" class="loading-section">
          <div class="spinner"></div>
          <p>加载统计数据...</p>
        </div>

        <div v-else class="dashboard-content">
          <div class="overview-section">
            <div class="overview-grid">
              <div class="overview-card">
                <div class="card-icon total">
                  <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                  </svg>
                </div>
                <div class="card-content">
                  <div class="card-value">{{ stats.overview?.total || 0 }}</div>
                  <div class="card-label">总标注数</div>
                </div>
              </div>

              <div class="overview-card">
                <div class="card-icon ai">
                  <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M12 2a5 5 0 0 0-5 5v1a5 5 0 0 0-2 4v5a5 5 0 0 0 5 5h8a5 5 0 0 0 5-5v-5a5 5 0 0 0-2-4V7a5 5 0 0 0-5-5z"></path>
                  </svg>
                </div>
                <div class="card-content">
                  <div class="card-value">{{ stats.overview?.aiGenerated || 0 }}</div>
                  <div class="card-label">AI生成</div>
                </div>
              </div>

              <div class="overview-card">
                <div class="card-icon manual">
                  <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"></path>
                  </svg>
                </div>
                <div class="card-content">
                  <div class="card-value">{{ stats.overview?.manual || 0 }}</div>
                  <div class="card-label">人工标注</div>
                </div>
              </div>

              <div class="overview-card">
                <div class="card-icon confidence">
                  <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                    <polyline points="22 4 12 14.01 9 11.01"></polyline>
                  </svg>
                </div>
                <div class="card-content">
                  <div class="card-value">{{ (stats.overview?.avgConfidence * 100).toFixed(0) }}%</div>
                  <div class="card-label">平均置信度</div>
                </div>
              </div>
            </div>
          </div>

          <div class="progress-section">
            <h4 class="section-title">标注进度</h4>
            <div class="progress-card">
              <div class="progress-header">
                <span class="progress-label">完成进度</span>
                <span class="progress-value">{{ stats.progressData?.percentage || 0 }}%</span>
              </div>
              <div class="progress-bar-large">
                <div class="progress-fill" :style="{ width: stats.progressData?.percentage + '%' }"></div>
              </div>
              <div class="progress-stats">
                <span>已完成: {{ stats.progressData?.completed || 0 }}</span>
                <span>目标: {{ stats.progressData?.total || 100 }}</span>
                <span>剩余: {{ stats.progressData?.remaining || 0 }}</span>
              </div>
            </div>
          </div>

          <div class="charts-section">
            <div class="chart-card">
              <h4 class="section-title">分类分布</h4>
              <div class="category-chart">
                <div 
                  v-for="cat in stats.categoryStats" 
                  :key="cat.id" 
                  class="category-bar-item"
                >
                  <div class="category-header">
                    <span class="category-color" :style="{ backgroundColor: cat.color }"></span>
                    <span class="category-name">{{ cat.name }}</span>
                    <span class="category-count">{{ cat.count }}</span>
                    <span class="category-percent">{{ cat.percentage }}%</span>
                  </div>
                  <div class="category-bar">
                    <div 
                      class="category-fill" 
                      :style="{ 
                        width: cat.percentage + '%', 
                        backgroundColor: cat.color 
                      }"
                    ></div>
                  </div>
                  <div class="category-substats">
                    <span v-if="cat.aiCount > 0">AI: {{ cat.aiCount }}</span>
                    <span v-if="cat.manualCount > 0">人工: {{ cat.manualCount }}</span>
                    <span v-if="cat.avgConfidence > 0">置信度: {{ (cat.avgConfidence * 100).toFixed(0) }}%</span>
                  </div>
                </div>
              </div>
            </div>

            <div class="chart-card">
              <h4 class="section-title">类型分布</h4>
              <div class="type-chart">
                <div 
                  v-for="t in stats.typeStats" 
                  :key="t.type"
                  class="type-bar-item"
                >
                  <div class="type-header">
                    <span class="type-color" :style="{ backgroundColor: t.color }"></span>
                    <span class="type-name">{{ t.name }}</span>
                    <span class="type-count">{{ t.count }}</span>
                  </div>
                  <div class="type-bar">
                    <div 
                      class="type-fill" 
                      :style="{ 
                        width: t.percentage + '%', 
                        backgroundColor: t.color 
                      }"
                    ></div>
                  </div>
                </div>
              </div>

              <h4 class="section-title" style="margin-top: 24px;">置信度分布</h4>
              <div class="confidence-chart">
                <div class="confidence-item high">
                  <span class="confidence-label">高 (≥80%)</span>
                  <span class="confidence-count">{{ stats.overview?.byConfidence?.high || 0 }}</span>
                </div>
                <div class="confidence-item medium">
                  <span class="confidence-label">中 (60-80%)</span>
                  <span class="confidence-count">{{ stats.overview?.byConfidence?.medium || 0 }}</span>
                </div>
                <div class="confidence-item low">
                  <span class="confidence-label">低 (<60%)</span>
                  <span class="confidence-count">{{ stats.overview?.byConfidence?.low || 0 }}</span>
                </div>
              </div>
            </div>
          </div>

          <div class="kappa-section">
            <h4 class="section-title">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"></circle>
                <path d="M12 16v-4"></path>
                <path d="M12 8h.01"></path>
              </svg>
              一致性 Kappa 系数
            </h4>
            
            <div v-if="kappaResult" class="kappa-card">
              <div class="kappa-header">
                <div class="kappa-value" :style="{ color: kappaResult.overall?.level?.color }">
                  {{ kappaResult.overall?.kappa?.toFixed(3) }}
                </div>
                <div class="kappa-level" :style="{ color: kappaResult.overall?.level?.color }">
                  {{ kappaResult.overall?.level?.label }}
                </div>
              </div>
              
              <div class="kappa-details">
                <div class="kappa-stat">
                  <span class="kappa-stat-label">一致率</span>
                  <span class="kappa-stat-value">{{ kappaResult.overall?.agreement }}%</span>
                </div>
                <div class="kappa-stat">
                  <span class="kappa-stat-label">观察一致性</span>
                  <span class="kappa-stat-value">{{ (kappaResult.overall?.observedAgreement * 100).toFixed(1) }}%</span>
                </div>
                <div class="kappa-stat">
                  <span class="kappa-stat-label">机遇一致性</span>
                  <span class="kappa-stat-value">{{ (kappaResult.overall?.chanceAgreement * 100).toFixed(1) }}%</span>
                </div>
              </div>

              <div class="kappa-categories">
                <div 
                  v-for="k in kappaResult.byCategory" 
                  :key="k.category"
                  class="kappa-category-item"
                >
                  <span class="kappa-category-name">
                    {{ getCategoryName(k.category) }}
                  </span>
                  <div class="kappa-category-bar">
                    <div 
                      class="kappa-category-fill"
                      :style="{ 
                        width: Math.max(0, (k.kappa + 1) * 50) + '%',
                        backgroundColor: k.level?.color 
                      }"
                    ></div>
                  </div>
                  <span class="kappa-category-value" :style="{ color: k.level?.color }">
                    {{ k.kappa.toFixed(2) }}
                  </span>
                </div>
              </div>

              <div v-if="kappaResult.suggestions?.length > 0" class="kappa-suggestions">
                <h5>改进建议</h5>
                <div 
                  v-for="(s, idx) in kappaResult.suggestions" 
                  :key="idx"
                  class="suggestion-item"
                  :class="s.priority"
                >
                  <span class="suggestion-icon">!</span>
                  <span class="suggestion-message">{{ s.message }}</span>
                </div>
              </div>
            </div>
            
            <div v-else class="no-kappa-data">
              <p>需要至少两位标注者的标注数据才能计算 Kappa 系数</p>
              <button class="btn btn-secondary" @click="generateMockKappa">
                生成示例数据
              </button>
            </div>
          </div>

          <div class="timeline-section">
            <h4 class="section-title">近7天标注趋势</h4>
            <div class="timeline-chart">
              <div 
                v-for="(day, idx) in timeSeriesData" 
                :key="idx"
                class="timeline-item"
              >
                <div class="timeline-bars">
                  <div 
                    class="timeline-bar total"
                    :style="{ height: Math.max(4, (day.total / maxTimeSeriesValue) * 100) + 'px' }"
                    :title="`总计: ${day.total}`"
                  ></div>
                  <div 
                    class="timeline-bar ai"
                    :style="{ height: Math.max(4, (day.ai / maxTimeSeriesValue) * 100) + 'px' }"
                    :title="`AI: ${day.ai}`"
                  ></div>
                </div>
                <div class="timeline-label">{{ day.date }}</div>
                <div class="timeline-value">{{ day.total }}</div>
              </div>
            </div>
            <div class="timeline-legend">
              <span><i class="legend-dot total"></i> 总计</span>
              <span><i class="legend-dot ai"></i> AI生成</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import statistics from '../utils/statistics'
import { ANNOTATION_CATEGORIES } from '../constants'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  annotations: {
    type: Array,
    default: () => []
  },
  images: {
    type: Array,
    default: () => []
  },
  totalTargets: {
    type: Number,
    default: 100
  }
})

defineEmits(['close'])

const loading = ref(false)
const kappaResult = ref(null)
const timeSeriesData = ref([])

const stats = computed(() => ({
  overview: statistics.overview.value,
  categoryStats: statistics.categoryStats.value,
  typeStats: statistics.typeStats.value,
  progressData: statistics.progressData.value
}))

const maxTimeSeriesValue = computed(() => {
  return Math.max(1, ...timeSeriesData.value.map(d => d.total))
})

const loadData = async () => {
  loading.value = true
  await new Promise(resolve => setTimeout(resolve, 300))
  
  statistics.setData(props.annotations, props.images, props.totalTargets)
  
  timeSeriesData.value = statistics.getTimeSeriesData(7)
  
  if (props.annotations.length > 0) {
    generateMockKappa()
  }
  
  loading.value = false
}

const generateMockKappa = () => {
  const mockAnnotator1 = props.annotations.filter((_, i) => i % 2 === 0)
  const mockAnnotator2 = props.annotations.filter((_, i) => i % 2 === 1)
  
  if (mockAnnotator1.length > 0 && mockAnnotator2.length > 0) {
    kappaResult.value = statistics.getConsistencyReport([mockAnnotator1, mockAnnotator2])
  }
}

const getCategoryName = (categoryId) => {
  const cat = ANNOTATION_CATEGORIES.find(c => c.id === categoryId)
  return cat ? cat.name : categoryId
}

watch(() => props.visible, (val) => {
  if (val) {
    loadData()
  }
})
</script>

<style scoped>
.dashboard-modal {
  min-width: 800px;
  max-width: 900px;
  max-height: 90vh;
}

.dashboard-body {
  overflow-y: auto;
  max-height: calc(90vh - 80px);
  padding: 20px;
}

.dashboard-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.loading-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px;
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

.overview-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.overview-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  background: linear-gradient(135deg, #f5f7fa 0%, #ecf5ff 100%);
  border-radius: 12px;
  border: 1px solid #ebeef5;
}

.card-icon {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
}

.card-icon.total { background: linear-gradient(135deg, #409eff 0%, #66b1ff 100%); }
.card-icon.ai { background: linear-gradient(135deg, #9c27b0 0%, #ba68c8 100%); }
.card-icon.manual { background: linear-gradient(135deg, #e6a23c 0%, #f0c78a 100%); }
.card-icon.confidence { background: linear-gradient(135deg, #67c23a 0%, #85ce61 100%); }

.card-value {
  font-size: 28px;
  font-weight: 700;
  color: #303133;
  line-height: 1.2;
}

.card-label {
  font-size: 13px;
  color: #909399;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 16px;
}

.progress-card {
  padding: 20px;
  background: #fff;
  border-radius: 12px;
  border: 1px solid #ebeef5;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 12px;
}

.progress-label {
  font-size: 14px;
  color: #606266;
  font-weight: 500;
}

.progress-value {
  font-size: 20px;
  font-weight: 700;
  color: #409eff;
}

.progress-bar-large {
  height: 20px;
  background: #f0f2f5;
  border-radius: 10px;
  overflow: hidden;
  margin-bottom: 12px;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #409eff 0%, #66b1ff 100%);
  border-radius: 10px;
  transition: width 0.5s ease;
}

.progress-stats {
  display: flex;
  gap: 24px;
  font-size: 13px;
  color: #909399;
}

.charts-section {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.chart-card {
  padding: 20px;
  background: #fff;
  border-radius: 12px;
  border: 1px solid #ebeef5;
}

.category-bar-item,
.type-bar-item {
  margin-bottom: 16px;
}

.category-header,
.type-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.category-color,
.type-color {
  width: 12px;
  height: 12px;
  border-radius: 3px;
}

.category-name,
.type-name {
  flex: 1;
  font-size: 13px;
  color: #606266;
}

.category-count,
.type-count {
  font-weight: 600;
  color: #303133;
}

.category-percent {
  font-size: 12px;
  color: #909399;
  min-width: 45px;
  text-align: right;
}

.category-bar,
.type-bar {
  height: 8px;
  background: #f0f2f5;
  border-radius: 4px;
  overflow: hidden;
}

.category-fill,
.type-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.5s ease;
}

.category-substats {
  display: flex;
  gap: 12px;
  font-size: 11px;
  color: #909399;
  margin-top: 4px;
}

.confidence-chart {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.confidence-item {
  display: flex;
  justify-content: space-between;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 13px;
}

.confidence-item.high { background: #f0f9eb; color: #67c23a; }
.confidence-item.medium { background: #fdf6ec; color: #e6a23c; }
.confidence-item.low { background: #fef0f0; color: #f56c6c; }

.confidence-count {
  font-weight: 600;
}

.kappa-card {
  padding: 24px;
  background: linear-gradient(135deg, #faf5ff 0%, #f3e8ff 100%);
  border-radius: 12px;
  border: 1px solid #e9d5ff;
}

.kappa-header {
  text-align: center;
  margin-bottom: 20px;
}

.kappa-value {
  font-size: 48px;
  font-weight: 700;
  line-height: 1.2;
}

.kappa-level {
  font-size: 18px;
  font-weight: 600;
}

.kappa-details {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 20px;
}

.kappa-stat {
  text-align: center;
  padding: 12px;
  background: rgba(255, 255, 255, 0.6);
  border-radius: 8px;
}

.kappa-stat-label {
  display: block;
  font-size: 12px;
  color: #909399;
  margin-bottom: 4px;
}

.kappa-stat-value {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.kappa-categories {
  margin-bottom: 20px;
}

.kappa-category-item {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 10px;
}

.kappa-category-name {
  min-width: 80px;
  font-size: 13px;
  color: #606266;
}

.kappa-category-bar {
  flex: 1;
  height: 8px;
  background: #fff;
  border-radius: 4px;
  overflow: hidden;
}

.kappa-category-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.5s ease;
}

.kappa-category-value {
  min-width: 50px;
  text-align: right;
  font-weight: 600;
  font-size: 13px;
}

.kappa-suggestions h5 {
  font-size: 13px;
  font-weight: 600;
  color: #606266;
  margin-bottom: 10px;
}

.suggestion-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 6px;
  margin-bottom: 6px;
  font-size: 13px;
}

.suggestion-item.high { background: #fef0f0; color: #f56c6c; }
.suggestion-item.medium { background: #fdf6ec; color: #e6a23c; }
.suggestion-item.low { background: #f5f7fa; color: #909399; }

.suggestion-icon {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: currentColor;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
  flex-shrink: 0;
}

.no-kappa-data {
  text-align: center;
  padding: 40px;
  color: #909399;
}

.no-kappa-data p {
  margin-bottom: 16px;
}

.timeline-chart {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 8px;
  height: 150px;
  padding: 20px 0;
  background: #fff;
  border-radius: 12px;
  border: 1px solid #ebeef5;
}

.timeline-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.timeline-bars {
  display: flex;
  align-items: flex-end;
  gap: 2px;
  height: 80px;
}

.timeline-bar {
  width: 12px;
  border-radius: 4px 4px 0 0;
  transition: height 0.5s ease;
}

.timeline-bar.total { background: linear-gradient(180deg, #409eff 0%, #66b1ff 100%); }
.timeline-bar.ai { background: linear-gradient(180deg, #9c27b0 0%, #ba68c8 100%); }

.timeline-label {
  font-size: 11px;
  color: #909399;
}

.timeline-value {
  font-size: 12px;
  font-weight: 600;
  color: #606266;
}

.timeline-legend {
  display: flex;
  justify-content: center;
  gap: 24px;
  margin-top: 12px;
  font-size: 12px;
  color: #909399;
}

.legend-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 4px;
}

.legend-dot.total { background: #409eff; }
.legend-dot.ai { background: #9c27b0; }

@media (max-width: 768px) {
  .dashboard-modal {
    min-width: auto;
    width: 95vw;
  }
  
  .overview-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .charts-section {
    grid-template-columns: 1fr;
  }
  
  .kappa-details {
    grid-template-columns: 1fr;
  }
}
</style>
