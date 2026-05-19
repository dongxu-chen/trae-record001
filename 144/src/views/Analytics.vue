<template>
  <div class="analytics-page">
    <el-card class="header-card" shadow="never">
      <div class="page-header">
        <div class="header-left">
          <h2>流水线分析看板</h2>
          <p>监控流水线执行趋势和性能指标</p>
        </div>
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          style="width: 350px"
        />
      </div>
    </el-card>

    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="6">
        <el-card class="stat-card primary">
          <div class="stat-icon">
            <el-icon size="28"><Timer /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ stats.totalRuns }}</div>
            <div class="stat-label">总执行次数</div>
            <div class="stat-trend up">
              <el-icon><Top /></el-icon>
              +12.5%
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card success">
          <div class="stat-icon">
            <el-icon size="28"><CircleCheck /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ stats.successRate }}%</div>
            <div class="stat-label">成功率</div>
            <div class="stat-trend up">
              <el-icon><Top /></el-icon>
              +5.2%
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card info">
          <div class="stat-icon">
            <el-icon size="28"><Clock /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ stats.avgDuration }}</div>
            <div class="stat-label">平均耗时</div>
            <div class="stat-trend down">
              <el-icon><Bottom /></el-icon>
              -8.3%
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card warning">
          <div class="stat-icon">
            <el-icon size="28"><DataLine /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ stats.activePipelines }}</div>
            <div class="stat-label">活跃流水线</div>
            <div class="stat-trend up">
              <el-icon><Top /></el-icon>
              +2
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="16">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>执行时长趋势</span>
              <el-radio-group v-model="trendView" size="small">
                <el-radio-button label="daily">每日</el-radio-button>
                <el-radio-button label="weekly">每周</el-radio-button>
              </el-radio-group>
            </div>
          </template>
          <div class="chart-container">
            <canvas ref="trendChartRef"></canvas>
          </div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header>
            <span>状态分布</span>
          </template>
          <div class="chart-container pie-chart">
            <canvas ref="statusChartRef"></canvas>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>
            <span>任务耗时分布</span>
          </template>
          <div class="chart-container">
            <canvas ref="taskTimeChartRef"></canvas>
          </div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>
            <span>流水线性能排名</span>
          </template>
          <div class="ranking-list">
            <div v-for="(item, index) in pipelineRanking" :key="item.name" class="ranking-item">
              <div class="rank-number" :class="`rank-${index + 1}`">{{ index + 1 }}</div>
              <div class="ranking-info">
                <div class="ranking-name">{{ item.name }}</div>
                <div class="ranking-meta">
                  {{ item.runs }} 次执行 · 平均 {{ item.avgTime }}
                </div>
              </div>
              <div class="ranking-bar">
                <div class="bar-fill" :style="{ width: `${(item.avgTimeSeconds / maxTime) * 100}%` }"></div>
              </div>
              <div class="ranking-time">{{ item.avgTime }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="24">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>最近执行记录</span>
              <el-button type="primary" link size="small">查看全部</el-button>
            </div>
          </template>
          <el-table :data="recentRuns" style="width: 100%">
            <el-table-column prop="name" label="流水线" width="200" />
            <el-table-column prop="status" label="状态" width="100">
              <template #default="scope">
                <el-tag :type="getStatusType(scope.row.status)" size="small">
                  {{ scope.row.status }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="startTime" label="开始时间" width="180">
              <template #default="scope">
                {{ formatTime(scope.row.startTime) }}
              </template>
            </el-table-column>
            <el-table-column prop="duration" label="耗时" width="100" />
            <el-table-column prop="trigger" label="触发方式" width="120">
              <template #default="scope">
                <el-tag size="small" type="info">{{ scope.row.trigger }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="100">
              <template #default="scope">
                <el-button size="small" type="primary" link>查看日志</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useTektonStore } from '@/stores/tekton'
import {
  Timer, CircleCheck, Clock, DataLine, Top, Bottom
} from '@element-plus/icons-vue'
import {
  Chart, LineController, LineElement, PointElement, LinearScale,
  CategoryScale, BarController, BarElement, PieController,
  ArcElement, Legend, Tooltip
} from 'chart.js'

Chart.register(
  LineController, LineElement, PointElement, LinearScale,
  CategoryScale, BarController, BarElement, PieController,
  ArcElement, Legend, Tooltip
)

const tektonStore = useTektonStore()

const dateRange = ref(null)
const trendView = ref('daily')
const trendChartRef = ref(null)
const statusChartRef = ref(null)
const taskTimeChartRef = ref(null)

const stats = ref({
  totalRuns: 156,
  successRate: 89.7,
  avgDuration: '12m30s',
  activePipelines: 8
})

const pipelineRanking = ref([
  { name: 'frontend-build', runs: 45, avgTime: '8m15s', avgTimeSeconds: 495 },
  { name: 'backend-build', runs: 38, avgTime: '15m30s', avgTimeSeconds: 930 },
  { name: 'docker-build-push', runs: 32, avgTime: '10m20s', avgTimeSeconds: 620 },
  { name: 'k8s-deploy', runs: 28, avgTime: '5m45s', avgTimeSeconds: 345 },
  { name: 'integration-tests', runs: 18, avgTime: '22m10s', avgTimeSeconds: 1330 }
])

const maxTime = computed(() => {
  return Math.max(...pipelineRanking.value.map(p => p.avgTimeSeconds))
})

const recentRuns = computed(() => {
  return tektonStore.pipelineRuns.map(r => ({
    ...r,
    trigger: ['Git Push', 'Manual', 'Scheduled'][Math.floor(Math.random() * 3)]
  })).slice(0, 10)
})

const getStatusType = (status) => {
  const types = {
    Succeeded: 'success',
    Failed: 'danger',
    Running: 'primary',
    Pending: 'warning'
  }
  return types[status] || 'info'
}

const formatTime = (timestamp) => {
  if (!timestamp) return '-'
  return new Date(timestamp).toLocaleString('zh-CN')
}

const initCharts = () => {
  const trendCtx = trendChartRef.value.getContext('2d')
  new Chart(trendCtx, {
    type: 'line',
    data: {
      labels: ['周一', '周二', '周三', '周四', '周五', '周六', '周日'],
      datasets: [
        {
          label: '平均执行时长 (分钟)',
          data: [12, 15, 10, 14, 18, 8, 11],
          borderColor: '#4f46e5',
          backgroundColor: 'rgba(79, 70, 229, 0.1)',
          fill: true,
          tension: 0.4
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'top' }
      },
      scales: {
        y: { beginAtZero: true }
      }
    }
  })

  const statusCtx = statusChartRef.value.getContext('2d')
  new Chart(statusCtx, {
    type: 'pie',
    data: {
      labels: ['成功', '失败', '运行中', '待处理'],
      datasets: [{
        data: [140, 12, 3, 1],
        backgroundColor: ['#67c23a', '#f56c6c', '#409eff', '#e6a23c']
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

  const taskCtx = taskTimeChartRef.value.getContext('2d')
  new Chart(taskCtx, {
    type: 'bar',
    data: {
      labels: ['git-clone', 'npm-install', 'build', 'test', 'docker-build', 'deploy'],
      datasets: [{
        label: '平均耗时 (秒)',
        data: [45, 120, 180, 90, 240, 60],
        backgroundColor: 'rgba(79, 70, 229, 0.8)'
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false }
      },
      scales: {
        y: { beginAtZero: true }
      }
    }
  })
}

onMounted(() => {
  setTimeout(initCharts, 100)
})
</script>

<style scoped>
.analytics-page {
  padding: 0;
}

.header-card {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-left h2 {
  margin: 0 0 8px 0;
  font-size: 24px;
}

.header-left p {
  margin: 0;
  opacity: 0.9;
  font-size: 14px;
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
  padding: 20px;
  transition: all 0.3s;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
}

.stat-card.primary .stat-icon {
  color: #4f46e5;
  background: rgba(79, 70, 229, 0.1);
}

.stat-card.success .stat-icon {
  color: #67c23a;
  background: rgba(103, 194, 58, 0.1);
}

.stat-card.info .stat-icon {
  color: #409eff;
  background: rgba(64, 158, 255, 0.1);
}

.stat-card.warning .stat-icon {
  color: #e6a23c;
  background: rgba(230, 162, 60, 0.1);
}

.stat-icon {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.stat-content .stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #1e293b;
  line-height: 1.2;
}

.stat-content .stat-label {
  font-size: 14px;
  color: #64748b;
  margin-top: 4px;
}

.stat-trend {
  font-size: 12px;
  margin-top: 6px;
  display: flex;
  align-items: center;
  gap: 2px;
}

.stat-trend.up {
  color: #67c23a;
}

.stat-trend.down {
  color: #f56c6c;
}

.chart-container {
  height: 300px;
  width: 100%;
}

.pie-chart {
  height: 280px;
}

.ranking-list {
  max-height: 300px;
  overflow-y: auto;
}

.ranking-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px solid #f1f5f9;
}

.ranking-item:last-child {
  border-bottom: none;
}

.rank-number {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 14px;
  flex-shrink: 0;
}

.rank-1 {
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
  color: white;
}

.rank-2 {
  background: linear-gradient(135deg, #6b7280 0%, #4b5563 100%);
  color: white;
}

.rank-3 {
  background: linear-gradient(135deg, #b45309 0%, #92400e 100%);
  color: white;
}

.rank-4, .rank-5 {
  background: #e2e8f0;
  color: #64748b;
}

.ranking-info {
  flex: 1;
  min-width: 0;
}

.ranking-name {
  font-weight: 500;
  color: #1e293b;
  margin-bottom: 2px;
}

.ranking-meta {
  font-size: 12px;
  color: #64748b;
}

.ranking-bar {
  width: 120px;
  height: 8px;
  background: #e2e8f0;
  border-radius: 4px;
  overflow: hidden;
  flex-shrink: 0;
}

.bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #4f46e5 0%, #7c3aed 100%);
  border-radius: 4px;
  transition: width 0.3s ease;
}

.ranking-time {
  font-family: 'Consolas', monospace;
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
  width: 70px;
  text-align: right;
  flex-shrink: 0;
}
</style>
