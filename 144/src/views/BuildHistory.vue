<template>
  <div class="build-history">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>构建历史</span>
          <el-select v-model="filterStatus" placeholder="筛选状态" size="small" style="width: 140px">
            <el-option label="全部" value="" />
            <el-option label="成功" value="success" />
            <el-option label="失败" value="failed" />
            <el-option label="进行中" value="running" />
          </el-select>
        </div>
      </template>

      <el-timeline>
        <el-timeline-item
          v-for="build in filteredBuilds"
          :key="build.id"
          :timestamp="build.startTime"
          placement="top"
          :type="getTimelineType(build.status)"
        >
          <el-card shadow="hover" class="build-card">
            <div class="build-header">
              <div class="build-title">
                <el-icon :color="getStatusColor(build.status)">
                  <component :is="getStatusIcon(build.status)" />
                </el-icon>
                <span class="build-name">{{ build.name }}</span>
                <el-tag :type="getTagType(build.status)" size="small">
                  {{ getStatusText(build.status) }}
                </el-tag>
              </div>
              <div class="build-time">
                <el-icon><Timer /></el-icon>
                <span>{{ build.duration }}</span>
              </div>
            </div>
            
            <div class="build-stages">
              <div
                v-for="(stage, index) in build.stages"
                :key="index"
                class="stage-item"
              >
                <div class="stage-status" :class="stage.status">
                  <el-icon size="12">
                    <component :is="getStageIcon(stage.status)" />
                  </el-icon>
                </div>
                <span class="stage-name">{{ stage.name }}</span>
              </div>
            </div>

            <div class="build-actions">
              <el-button size="small" text @click="viewLogs(build)">
                <el-icon><Document /></el-icon>
                查看日志
              </el-button>
              <el-button size="small" text type="danger" @click="rebuild(build)">
                <el-icon><RefreshRight /></el-icon>
                重新构建
              </el-button>
            </div>
          </el-card>
        </el-timeline-item>
      </el-timeline>
    </el-card>

    <el-dialog
      v-model="logsVisible"
      :title="`${selectedBuild?.name || ''} - 构建日志`"
      width="800px"
    >
      <el-input
        v-model="buildLogs"
        type="textarea"
        :rows="25"
        readonly
        style="font-family: monospace; font-size: 12px"
      />
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { usePipelineStore } from '@/stores/pipeline'

const pipelineStore = usePipelineStore()
const filterStatus = ref('')
const logsVisible = ref(false)
const selectedBuild = ref(null)
const buildLogs = ref('')

const filteredBuilds = computed(() => {
  if (!filterStatus.value) {
    return pipelineStore.buildHistory
  }
  return pipelineStore.buildHistory.filter(b => b.status === filterStatus.value)
})

const getTimelineType = (status) => {
  switch (status) {
    case 'success': return 'success'
    case 'failed': return 'danger'
    case 'running': return 'warning'
    default: return 'info'
  }
}

const getTagType = (status) => {
  switch (status) {
    case 'success': return 'success'
    case 'failed': return 'danger'
    case 'running': return 'warning'
    default: return 'info'
  }
}

const getStatusColor = (status) => {
  switch (status) {
    case 'success': return '#67c23a'
    case 'failed': return '#f56c6c'
    case 'running': return '#e6a23c'
    default: return '#909399'
  }
}

const getStatusIcon = (status) => {
  switch (status) {
    case 'success': return 'CircleCheck'
    case 'failed': return 'CircleClose'
    case 'running': return 'Loading'
    default: return 'Timer'
  }
}

const getStatusText = (status) => {
  switch (status) {
    case 'success': return '成功'
    case 'failed': return '失败'
    case 'running': return '进行中'
    default: return '待定'
  }
}

const getStageIcon = (status) => {
  switch (status) {
    case 'success': return 'CircleCheck'
    case 'failed': return 'CircleClose'
    case 'running': return 'Loading'
    default: return 'Timer'
  }
}

const viewLogs = (build) => {
  selectedBuild.value = build
  buildLogs.value = `=== ${build.name} - 构建日志\n\nStarted at: ${build.startTime}\n\n[Pipeline] Start of Pipeline\n[Pipeline] node\nRunning on Jenkins\n[Pipeline] {\n[Pipeline] stage\n[Pipeline] { (代码检出)\nCloning repository...\nChecking out branch main\n\n[Pipeline] }\n[Pipeline] // stage\n[Pipeline] stage\n[Pipeline] { (构建)\n+ npm install\n+ npm run build\n\nBuild completed successfully\n\n[Pipeline] }\n[Pipeline] // stage\n[Pipeline] stage\n[Pipeline] { (测试)\nRunning unit tests...\n123 tests passed\n\n[Pipeline] }\n[Pipeline] // stage\n[Pipeline] stage\n[Pipeline] { (部署)\nDeploying to production...\nDeployment completed\n\n[Pipeline] }\n[Pipeline] // stage\n[Pipeline] }\n[Pipeline] // node\n[Pipeline] End of Pipeline\n\nDuration: ${build.duration}\nResult: ${build.status.toUpperCase()}`
  
  logsVisible.value = true
}

const rebuild = (build) => {
  pipelineStore.triggerBuild()
  ElMessage.success('重新构建已触发')
}
</script>

<style scoped>
.build-history {
  height: 100%;
  overflow: auto;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.build-card {
  margin-bottom: 10px;
}

.build-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.build-title {
  display: flex;
  align-items: center;
  gap: 10px;
}

.build-name {
  font-size: 16px;
  font-weight: 600;
}

.build-time {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #909399;
  font-size: 13px;
}

.build-stages {
  display: flex;
  gap: 16px;
  padding: 12px 0;
  border-top: 1px solid #ebeef5;
  border-bottom: 1px solid #ebeef5;
  margin-bottom: 12px;
}

.stage-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
}

.stage-status {
  display: flex;
  align-items: center;
}

.stage-status.success {
  color: #67c23a;
}

.stage-status.failed {
  color: #f56c6c;
}

.stage-status.running {
  color: #e6a23c;
}

.stage-status.pending {
  color: #909399;
}

.stage-name {
  color: #606266;
}

.build-actions {
  display: flex;
  gap: 8px;
}
</style>
