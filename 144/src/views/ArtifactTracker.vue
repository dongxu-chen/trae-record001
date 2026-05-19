<template>
  <div class="artifact-tracker">
    <el-row :gutter="20">
      <el-col :span="24">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>制品晋级追踪</span>
              <el-select v-model="stageFilter" placeholder="筛选环境" size="small" style="width: 140px" clearable>
                <el-option label="开发环境" value="dev" />
                <el-option label="测试环境" value="test" />
                <el-option label="预发布环境" value="uat" />
                <el-option label="生产环境" value="prod" />
              </el-select>
            </div>
          </template>

          <el-table :data="filteredArtifacts" style="width: 100%">
            <el-table-column prop="name" label="制品名称" width="160">
              <template #default="{ row }">
                <div class="artifact-name">
                  <el-icon><Box /></el-icon>
                  <span>{{ row.name }}</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="version" label="版本" width="120">
              <template #default="{ row }">
                <el-tag size="small" type="success">{{ row.version }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="type" label="类型" width="100">
              <template #default="{ row }">
                <el-tag size="small">{{ row.type }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="buildNumber" label="构建号" width="100" />
            <el-table-column prop="size" label="大小" width="100" />
            <el-table-column prop="currentStage" label="当前阶段" width="120">
              <template #default="{ row }">
                <el-tag :type="getStageType(row.currentStage)" size="small">
                  {{ getStageLabel(row.currentStage) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="晋级进度">
              <template #default="{ row }">
                <div class="promotion-steps">
                  <div
                    v-for="(stage, index) in row.stages"
                    :key="stage.name"
                    class="step"
                    :class="[stage.status, { active: index <= getCurrentStageIndex(row) }]"
                  >
                    <div class="step-icon">
                      <el-icon v-if="stage.status === 'success'"><CircleCheck /></el-icon>
                      <el-icon v-else-if="stage.status === 'running'"><Loading /></el-icon>
                      <el-icon v-else-if="stage.status === 'failed'"><CircleClose /></el-icon>
                      <el-icon v-else-if="stage.status === 'blocked'"><Lock /></el-icon>
                      <el-icon v-else><Timer /></el-icon>
                    </div>
                    <span class="step-name">{{ stage.name }}</span>
                  </div>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="180">
              <template #default="{ row }">
                <el-button size="small" @click="showArtifactDetail(row)">
                  <el-icon><View /></el-icon>
                  详情
                </el-button>
                <el-button
                  v-if="canPromote(row)"
                  size="small"
                  type="primary"
                  @click="promoteArtifact(row)"
                >
                  <el-icon><ArrowRight /></el-icon>
                  晋级
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <el-dialog v-model="detailDialogVisible" title="制品详情" width="900px">
      <div v-if="currentArtifact" class="artifact-detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="制品名称">{{ currentArtifact.name }}</el-descriptions-item>
          <el-descriptions-item label="版本号">{{ currentArtifact.version }}</el-descriptions-item>
          <el-descriptions-item label="制品类型">{{ currentArtifact.type }}</el-descriptions-item>
          <el-descriptions-item label="构建号">#{{ currentArtifact.buildNumber }}</el-descriptions-item>
          <el-descriptions-item label="文件大小">{{ currentArtifact.size }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ currentArtifact.createdAt }}</el-descriptions-item>
          <el-descriptions-item label="创建人">{{ currentArtifact.createdBy }}</el-descriptions-item>
          <el-descriptions-item label="当前阶段">
            <el-tag :type="getStageType(currentArtifact.currentStage)">
              {{ getStageLabel(currentArtifact.currentStage) }}
            </el-tag>
          </el-descriptions-item>
        </el-descriptions>

        <el-divider content-position="left">质量门禁</el-divider>
        <el-row :gutter="16">
          <el-col v-for="(check, key) in currentArtifact.checks" :key="key" :span="6">
            <el-card shadow="hover" class="check-card">
              <div class="check-icon" :class="{ passed: check.passed, failed: !check.passed }">
                <el-icon v-if="check.passed" size="32"><CircleCheck /></el-icon>
                <el-icon v-else size="32"><CircleClose /></el-icon>
              </div>
              <div class="check-name">{{ getCheckName(key) }}</div>
              <div class="check-value" v-if="check.coverage">覆盖率: {{ check.coverage }}</div>
              <div class="check-value" v-else-if="check.vulnerabilities !== undefined">漏洞: {{ check.vulnerabilities }}</div>
              <div class="check-value" v-else-if="check.score">评分: {{ check.score }}</div>
            </el-card>
          </el-col>
        </el-row>

        <el-divider content-position="left">晋级记录</el-divider>
        <el-timeline>
          <el-timeline-item
            v-for="(stage, index) in currentArtifact.stages"
            :key="stage.name"
            :type="getStageTimelineType(stage.status)"
            :hollow="stage.status === 'pending'"
          >
            <div class="timeline-content">
              <span class="timeline-stage">{{ getStageLabel(stage.name) }}</span>
              <el-tag v-if="stage.status === 'success'" type="success" size="small">已通过</el-tag>
              <el-tag v-else-if="stage.status === 'running'" type="warning" size="small">进行中</el-tag>
              <el-tag v-else-if="stage.status === 'failed'" type="danger" size="small">已失败</el-tag>
              <el-tag v-else-if="stage.status === 'blocked'" type="info" size="small">已阻塞</el-tag>
              <el-tag v-else size="small">待处理</el-tag>
              <div v-if="stage.time" class="timeline-time">{{ stage.time }}</div>
              <div v-if="stage.approver" class="timeline-approver">审批人: {{ stage.approver }}</div>
            </div>
          </el-timeline-item>
        </el-timeline>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { useArtifactStore } from '@/stores/artifact'

const artifactStore = useArtifactStore()
const stageFilter = ref('')
const detailDialogVisible = ref(false)
const currentArtifact = ref(null)

const filteredArtifacts = computed(() => {
  return artifactStore.getArtifactsByStage(stageFilter.value)
})

const getStageType = (stage) => {
  const typeMap = {
    dev: 'info',
    test: 'warning',
    uat: 'primary',
    prod: 'success'
  }
  return typeMap[stage] || 'info'
}

const getStageLabel = (stage) => {
  const labelMap = {
    dev: '开发环境',
    test: '测试环境',
    uat: '预发布',
    prod: '生产环境'
  }
  return labelMap[stage] || stage
}

const getCurrentStageIndex = (artifact) => {
  return artifact.stages.findIndex(s => s.name === artifact.currentStage)
}

const canPromote = (artifact) => {
  const currentIndex = getCurrentStageIndex(artifact)
  const currentStage = artifact.stages[currentIndex]
  return currentStage && currentStage.status === 'success' && currentIndex < artifact.stages.length - 1
}

const promoteArtifact = (artifact) => {
  const currentIndex = getCurrentStageIndex(artifact)
  const nextStage = artifact.stages[currentIndex + 1]
  if (nextStage) {
    artifactStore.promoteArtifact(artifact.id, nextStage.name, 'currentUser')
    ElMessage.success(`${artifact.name} 已成功晋级到 ${getStageLabel(nextStage.name)}`)
  }
}

const showArtifactDetail = (artifact) => {
  currentArtifact.value = artifact
  detailDialogVisible.value = true
}

const getCheckName = (key) => {
  const nameMap = {
    unitTests: '单元测试',
    integrationTests: '集成测试',
    securityScan: '安全扫描',
    codeQuality: '代码质量'
  }
  return nameMap[key] || key
}

const getStageTimelineType = (status) => {
  switch (status) {
    case 'success': return 'success'
    case 'running': return 'warning'
    case 'failed': return 'danger'
    default: return ''
  }
}
</script>

<style scoped>
.artifact-tracker {
  height: 100%;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.artifact-name {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
}

.promotion-steps {
  display: flex;
  align-items: center;
  gap: 4px;
}

.step {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  opacity: 0.5;
}

.step.active {
  opacity: 1;
}

.step.success .step-icon {
  color: #67c23a;
}

.step.running .step-icon {
  color: #e6a23c;
  animation: spin 1s linear infinite;
}

.step.failed .step-icon {
  color: #f56c6c;
}

.step.blocked .step-icon {
  color: #909399;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.step-icon {
  font-size: 16px;
}

.step-name {
  font-size: 11px;
  color: #606266;
}

.artifact-detail {
  padding: 10px 0;
}

.check-card {
  text-align: center;
}

.check-icon {
  margin-bottom: 8px;
}

.check-icon.passed {
  color: #67c23a;
}

.check-icon.failed {
  color: #f56c6c;
}

.check-name {
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 4px;
}

.check-value {
  font-size: 12px;
  color: #909399;
}

.timeline-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.timeline-stage {
  font-weight: 600;
  font-size: 14px;
}

.timeline-time,
.timeline-approver {
  font-size: 12px;
  color: #909399;
}
</style>
