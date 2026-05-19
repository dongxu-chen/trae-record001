<template>
  <div class="trend-analysis">
    <el-row :gutter="20">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon success">
            <el-icon size="28"><TrendCharts /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ stats.avgDuration }} min</div>
            <div class="stat-label">平均构建时长</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon warning">
            <el-icon size="28"><CircleCheck /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ stats.successRate }}%</div>
            <div class="stat-label">构建成功率</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon primary">
            <el-icon size="28"><Timer /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ stats.totalRuns }}</div>
            <div class="stat-label">总构建次数</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon info">
            <el-icon size="28"><ShoppingTrolley /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">3</div>
            <div class="stat-label">活跃流水线</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="16">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>流水线执行时长趋势</span>
              <el-select v-model="selectedPipeline" size="small" placeholder="选择流水线" style="width: 180px">
                <el-option label="全部流水线" value="" />
                <el-option label="frontend-app" value="frontend-app" />
                <el-option label="backend-service" value="backend-service" />
              </el-select>
            </div>
          </template>
          <div class="chart-container">
            <canvas ref="durationChart"></canvas>
          </div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card>
          <template #header>
            <span>构建成功率分布</span>
          </template>
          <div class="chart-container pie-chart">
            <canvas ref="statusChart"></canvas>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>各阶段耗时分布</span>
          </template>
          <div class="chart-container">
            <canvas ref="stageChart"></canvas>
          </div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>最近构建记录</span>
          </template>
          <div class="recent-builds">
            <div v-for="(build, index) in recentBuilds" :key="index" class="build-item">
              <div class="build-status" :class="build.status">
                <el-icon>
                  <CircleCheck v-if="build.status === 'success'" />
                  <Loading v-else-if="build.status === 'running'" />
                  <CircleClose v-else />
                </el-icon>
              </div>
              <div class="build-info">
                <div class="build-name">{{ build.pipeline }}</div>
                <div class="build-time">{{ build.date }}</div>
              </div>
              <div class="build-duration">
                {{ build.duration }} min
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useArtifactStore } from '@/stores/artifact'
import Chart from 'chart.js/auto'

const artifactStore = useArtifactStore()
const selectedPipeline = ref('')
const durationChart = ref(null)
const statusChart = ref(null)
const stageChart = ref(null)

let durationChartInstance = null
let statusChartInstance = null
let stageChartInstance = null

const stats = computed(() => {
  return artifactStore.getPipelineStats(selectedPipeline.value)
})

const recentBuilds = computed(() => {
  const metrics = selectedPipeline.value
    ? artifactStore.pipelineMetrics.filter(m => m.pipeline === selectedPipeline.value)
    : artifactStore.pipelineMetrics
  return metrics.slice(-5).reverse()
})

const initCharts = () => {
  initDurationChart()
  initStatusChart()
  initStageChart()
}

const initDurationChart = () => {
  if (durationChartInstance) {
    durationChartInstance.destroy()
  }

  const metrics = selectedPipeline.value
    ? artifactStore.pipelineMetrics.filter(m => m.pipeline === selectedPipeline.value)
    : artifactStore.pipelineMetrics

  const labels = [...new Set(metrics.map(m => m.date))]
  const datasets = []

  const pipelines = [...new Set(metrics.map(m => m.pipeline))]
  const colors = ['#409eff', '#67c23a', '#e6a23c', '#f56c6c']

  pipelines.forEach((pipeline, index) => {
    const data = labels.map(date => {
      const item = metrics.find(m => m.date === date && m.pipeline === pipeline)
      return item ? item.duration : null
    })
    datasets.push({
      label: pipeline,
      data,
      borderColor: colors[index % colors.length],
      backgroundColor: colors[index % colors.length] + '20',
      tension: 0.4,
      fill: true
    })
  })

  durationChartInstance = new Chart(durationChart.value, {
    type: 'line',
    data: { labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'bottom' }
      },
      scales: {
        y: {
          beginAtZero: true,
          title: { display: true, text: '时长 (分钟)' }
        }
      }
    }
  })
}

const initStatusChart = () => {
  if (statusChartInstance) {
    statusChartInstance.destroy()
  }

  const metrics = selectedPipeline.value
    ? artifactStore.pipelineMetrics.filter(m => m.pipeline === selectedPipeline.value)
    : artifactStore.pipelineMetrics

  const successCount = metrics.filter(m => m.status === 'success').length
  const failedCount = metrics.filter(m => m.status === 'failed').length
  const runningCount = metrics.filter(m => m.status === 'running').length

  statusChartInstance = new Chart(statusChart.value, {
    type: 'doughnut',
    data: {
      labels: ['成功', '失败', '进行中'],
      datasets: [{
        data: [successCount, failedCount, runningCount],
        backgroundColor: ['#67c23a', '#f56c6c', '#e6a23c'],
        borderWidth: 0
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'bottom' }
      }
    }
  })
}

const initStageChart = () => {
  if (stageChartInstance) {
    stageChartInstance.destroy()
  }

  const stageData = {
    '代码检出': 3,
    '构建': 8,
    '单元测试': 5,
    '集成测试': 10,
    '代码扫描': 4,
    '部署': 6
  }

  stageChartInstance = new Chart(stageChart.value, {
    type: 'bar',
    data: {
      labels: Object.keys(stageData),
      datasets: [{
        label: '平均耗时 (分钟)',
        data: Object.values(stageData),
        backgroundColor: [
          '#409eff',
          '#67c23a',
          '#e6a23c',
          '#f56c6c',
          '#909399',
          '#67c23a'
        ],
        borderRadius: 4
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false }
      },
      scales: {
        y: {
          beginAtZero: true,
          title: { display: true, text: '时长 (分钟)' }
        }
      }
    }
  })
}

watch(selectedPipeline, () => {
  initDurationChart()
  initStatusChart()
})

onMounted(() => {
  setTimeout(initCharts, 100)
})
</script>

<style scoped>
.trend-analysis {
  height: 100%;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 16px;
}

.stat-icon {
  width: 60px;
  height: 60px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.stat-icon.success {
  background: #f0f9eb;
  color: #67c23a;
}

.stat-icon.warning {
  background: #fdf6ec;
  color: #e6a23c;
}

.stat-icon.primary {
  background: #ecf5ff;
  color: #409eff;
}

.stat-icon.info {
  background: #f4f4f5;
  color: #909399;
}

.stat-content {
  flex: 1;
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: #303133;
  line-height: 1.2;
}

.stat-label {
  font-size: 13px;
  color: #909399;
  margin-top: 4px;
}

.chart-container {
  height: 300px;
  padding: 10px;
}

.pie-chart {
  height: 280px;
}

.recent-builds {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.build-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: #f5f7fa;
  border-radius: 8px;
}

.build-status {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.build-status.success {
  background: #f0f9eb;
  color: #67c23a;
}

.build-status.running {
  background: #fdf6ec;
  color: #e6a23c;
  animation: spin 1s linear infinite;
}

.build-status.failed {
  background: #fef0f0;
  color: #f56c6c;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.build-info {
  flex: 1;
}

.build-name {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
}

.build-time {
  font-size: 12px;
  color: #909399;
  margin-top: 2px;
}

.build-duration {
  font-size: 14px;
  font-weight: 600;
  color: #409eff;
}
</style>
