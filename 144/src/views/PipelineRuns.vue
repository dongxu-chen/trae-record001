<template>
  <div class="pipeline-runs-page">
    <el-card class="header-card" shadow="never">
      <div class="page-header">
        <div class="header-left">
          <h2>流水线运行记录</h2>
          <p>查看和管理所有 Tekton PipelineRun</p>
        </div>
        <div class="header-actions">
          <el-button type="primary" @click="showRunDialog = true">
            <el-icon><Plus /></el-icon>
            新建运行
          </el-button>
          <el-button @click="loadRuns">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
        </div>
      </div>
    </el-card>

    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="6">
        <el-card class="stat-card success">
          <div class="stat-icon">
            <el-icon size="28"><CircleCheck /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ stats.succeeded }}</div>
            <div class="stat-label">成功</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card failed">
          <div class="stat-icon">
            <el-icon size="28"><CircleClose /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ stats.failed }}</div>
            <div class="stat-label">失败</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card running">
          <div class="stat-icon">
            <el-icon size="28"><Loading /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ stats.running }}</div>
            <div class="stat-label">运行中</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card pending">
          <div class="stat-icon">
            <el-icon size="28"><Clock /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ stats.pending }}</div>
            <div class="stat-label">等待中</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-card style="margin-top: 20px">
      <el-table :data="pipelineRuns" style="width: 100%">
        <el-table-column prop="name" label="运行名称" min-width="200">
          <template #default="scope">
            <span class="run-name">{{ scope.row.name }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="pipeline" label="流水线" width="150">
          <template #default="scope">
            <el-tag size="small" type="info">{{ scope.row.pipeline }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="120">
          <template #default="scope">
            <el-tag :type="getStatusType(scope.row.status)" size="small">
              {{ scope.row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="namespace" label="命名空间" width="120" />
        <el-table-column prop="startTime" label="开始时间" width="180">
          <template #default="scope">
            {{ formatTime(scope.row.startTime) }}
          </template>
        </el-table-column>
        <el-table-column prop="duration" label="耗时" width="100" />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="scope">
            <el-button size="small" type="primary" link @click="viewLogs(scope.row)">
              日志
            </el-button>
            <el-button size="small" type="success" link @click="rerun(scope.row)">
              重运行
            </el-button>
            <el-button size="small" type="danger" link @click="deleteRun(scope.row)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="logsDialogVisible" title="运行日志" width="90%" top="5vh">
      <div class="logs-container">
        <pre class="logs-content">{{ currentLogs }}</pre>
      </div>
      <template #footer>
        <el-button @click="downloadLogs">下载日志</el-button>
        <el-button type="primary" @click="logsDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showRunDialog" title="新建 PipelineRun" width="600px">
      <el-form :model="newRun" label-width="120px">
        <el-form-item label="选择流水线">
          <el-select v-model="newRun.pipeline" style="width: 100%" placeholder="选择流水线">
            <el-option
              v-for="p in tektonStore.pipelines"
              :key="p.id"
              :label="p.name"
              :value="p.name"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="命名空间">
          <el-input v-model="newRun.namespace" placeholder="default" />
        </el-form-item>
        <el-form-item label="参数">
          <div v-for="(param, index) in newRun.params" :key="index" class="param-row">
            <el-input v-model="param.name" placeholder="参数名" style="width: 150px; margin-right: 8px" />
            <el-input v-model="param.value" placeholder="参数值" style="flex: 1" />
            <el-button size="small" type="danger" text @click="newRun.params.splice(index, 1)" style="margin-left: 8px">
              <el-icon><Close /></el-icon>
            </el-button>
          </div>
          <el-button size="small" type="primary" text @click="newRun.params.push({ name: '', value: '' })">
            添加参数
          </el-button>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showRunDialog = false">取消</el-button>
        <el-button type="primary" @click="createRun">创建运行</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useTektonStore } from '@/stores/tekton'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Plus, Refresh, CircleCheck, CircleClose, Loading, Clock, Close
} from '@element-plus/icons-vue'

const tektonStore = useTektonStore()

const pipelineRuns = ref([])
const logsDialogVisible = ref(false)
const showRunDialog = ref(false)
const currentLogs = ref('')
const newRun = ref({
  pipeline: '',
  namespace: 'default',
  params: []
})

const stats = computed(() => {
  const runs = tektonStore.pipelineRuns
  return {
    succeeded: runs.filter(r => r.status === 'Succeeded').length,
    failed: runs.filter(r => r.status === 'Failed').length,
    running: runs.filter(r => r.status === 'Running').length,
    pending: runs.filter(r => r.status === 'Pending').length,
    total: runs.length
  }
})

onMounted(() => {
  loadRuns()
})

const loadRuns = () => {
  pipelineRuns.value = tektonStore.pipelineRuns.map(r => ({
    ...r,
    duration: calculateDuration(r.startTime, r.completionTime)
  }))
  ElMessage.success('已刷新运行记录')
}

const calculateDuration = (start, end) => {
  if (!end) return '进行中'
  const startDate = new Date(start)
  const endDate = new Date(end)
  const diff = Math.floor((endDate - startDate) / 1000)
  const minutes = Math.floor(diff / 60)
  const seconds = diff % 60
  return `${minutes}m ${seconds}s`
}

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

const viewLogs = (run) => {
  currentLogs.value = `
========================================
PipelineRun: ${run.name}
Pipeline: ${run.pipeline}
Namespace: ${run.namespace}
Status: ${run.status}
========================================

[git-clone] Cloning repository https://github.com/example/repo.git
[git-clone] Checking out revision main
[git-clone] Clone completed successfully

[npm] Installing dependencies...
[npm] npm WARN deprecated legacy-package@1.0.0
[npm] added 1234 packages in 45s

[npm] Running tests...
[npm] PASS test/unit.test.js
[npm] PASS test/integration.test.js
[npm] Test Suites: 2 passed, 2 total
[npm] Tests: 15 passed, 15 total

[docker-build] Building image...
[docker-build] Step 1/5 : FROM node:18-alpine
[docker-build] Step 2/5 : WORKDIR /app
[docker-build] Step 3/5 : COPY package*.json ./
[docker-build] Step 4/5 : RUN npm ci --only=production
[docker-build] Step 5/5 : COPY . .
[docker-build] Successfully built image myapp:latest

[kubectl] Applying deployment...
[kubectl] deployment.apps/myapp configured
[kubectl] service/myapp configured

========================================
PipelineRun completed successfully!
Duration: 2 minutes 30 seconds
========================================
  `.trim()
  logsDialogVisible.value = true
}

const downloadLogs = () => {
  const blob = new Blob([currentLogs.value], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'pipeline-logs.txt'
  a.click()
  URL.revokeObjectURL(url)
}

const rerun = async (run) => {
  try {
    await ElMessageBox.confirm(`确定要重新运行 ${run.name} 吗？`, '确认重运行', {
      type: 'info'
    })
    ElMessage.success('已触发重新运行')
  } catch {
  }
}

const deleteRun = async (run) => {
  try {
    await ElMessageBox.confirm(`确定要删除 ${run.name} 吗？`, '确认删除', {
      type: 'warning'
    })
    ElMessage.success('删除成功')
  } catch {
  }
}

const createRun = () => {
  if (!newRun.value.pipeline) {
    ElMessage.warning('请选择流水线')
    return
  }
  showRunDialog.value = false
  ElMessage.success('PipelineRun 已创建')
}
</script>

<style scoped>
.pipeline-runs-page {
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

.header-actions {
  display: flex;
  gap: 12px;
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

.stat-card.success .stat-icon {
  color: #67c23a;
  background: rgba(103, 194, 58, 0.1);
}

.stat-card.failed .stat-icon {
  color: #f56c6c;
  background: rgba(245, 108, 108, 0.1);
}

.stat-card.running .stat-icon {
  color: #409eff;
  background: rgba(64, 158, 255, 0.1);
}

.stat-card.pending .stat-icon {
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

.run-name {
  font-family: 'Consolas', monospace;
  font-size: 13px;
  color: #1e293b;
}

.logs-container {
  background: #1e1e1e;
  border-radius: 8px;
  padding: 16px;
  max-height: 60vh;
  overflow: auto;
}

.logs-content {
  margin: 0;
  color: #d4d4d4;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-all;
}

.param-row {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
}
</style>
