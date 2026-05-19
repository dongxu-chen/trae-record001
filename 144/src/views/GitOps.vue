<template>
  <div class="gitops">
    <el-row :gutter="20">
      <el-col :span="8">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>GitOps 配置</span>
              <el-switch v-model="gitopsConfig.enabled" active-text="已启用" inactive-text="已禁用" />
            </div>
          </template>
          <el-form :model="gitopsConfig" label-width="100px">
            <el-form-item label="Git Provider">
              <el-select v-model="gitopsConfig.provider" size="small">
                <el-option label="GitHub" value="github" />
                <el-option label="GitLab" value="gitlab" />
                <el-option label="Gitee" value="gitee" />
              </el-select>
            </el-form-item>
            <el-form-item label="仓库地址">
              <el-input v-model="gitopsConfig.repoUrl" size="small" placeholder="https://github.com/org/repo" />
            </el-form-item>
            <el-form-item label="Webhook 密钥">
              <el-input v-model="gitopsConfig.webhookSecret" type="password" size="small" show-password />
            </el-form-item>
            <el-form-item label="自动构建">
              <el-switch v-model="gitopsConfig.autoBuildOnPR" active-text="开启" inactive-text="关闭" />
            </el-form-item>
            <el-form-item label="自动合并">
              <el-switch v-model="gitopsConfig.autoMergeOnSuccess" active-text="开启" inactive-text="关闭" />
            </el-form-item>
            <el-form-item label="质量门禁">
              <el-checkbox-group v-model="gitopsConfig.requiredChecks">
                <el-checkbox label="unitTests">单元测试</el-checkbox>
                <el-checkbox label="lint">代码检查</el-checkbox>
                <el-checkbox label="build">构建验证</el-checkbox>
                <el-checkbox label="security">安全扫描</el-checkbox>
              </el-checkbox-group>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" size="small" @click="saveConfig">保存配置</el-button>
              <el-button size="small" @click="testWebhook">测试 Webhook</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <el-col :span="16">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>Pull Requests</span>
              <el-tag type="success" size="small">{{ prList.length }} 个活跃 PR</el-tag>
            </div>
          </template>
          <div class="pr-list">
            <div v-for="pr in prList" :key="pr.id" class="pr-item">
              <div class="pr-header">
                <div class="pr-title">
                  <el-icon size="18" color="#409eff"><PullRequest /></el-icon>
                  <span>{{ pr.title }}</span>
                </div>
                <el-tag :type="getPRStatusType(pr.status)" size="small">
                  {{ getPRStatusLabel(pr.status) }}
                </el-tag>
              </div>
              <div class="pr-meta">
                <span class="pr-branch">
                  <el-icon size="12"><ArrowRight /></el-icon>
                  {{ pr.branch }} → {{ pr.targetBranch }}
                </span>
                <span class="pr-author">
                  <el-icon size="12"><User /></el-icon>
                  {{ pr.author }}
                </span>
                <span class="pr-time">
                  <el-icon size="12"><Clock /></el-icon>
                  {{ pr.createdAt }}
                </span>
              </div>
              <div class="pr-stats">
                <span class="stat-item">
                  <el-icon size="12"><Document /></el-icon>
                  {{ pr.filesChanged }} 个文件变更
                </span>
                <span class="stat-item">
                  <el-icon size="12"><Coordinate /></el-icon>
                  {{ pr.commits }} 次提交
                </span>
              </div>
              <div class="pr-checks">
                <div
                  v-for="(passed, check) in pr.checks"
                  :key="check"
                  class="check-item"
                  :class="{ passed, failed: passed === false, pending: passed === null }"
                >
                  <el-icon size="14">
                    <CircleCheck v-if="passed === true" />
                    <CircleClose v-else-if="passed === false" />
                    <Loading v-else />
                  </el-icon>
                  <span>{{ getCheckLabel(check) }}</span>
                </div>
              </div>
              <div class="pr-actions">
                <el-button
                  v-if="pr.status !== 'success'"
                  size="small"
                  type="primary"
                  @click="triggerBuild(pr)"
                >
                  <el-icon><VideoPlay /></el-icon>
                  触发构建
                </el-button>
                <el-button
                  v-if="pr.status === 'success'"
                  size="small"
                  type="success"
                  @click="mergePR(pr)"
                >
                  <el-icon><Check /></el-icon>
                  合并 PR
                </el-button>
                <el-button size="small" @click="viewPRDetails(pr)">
                  <el-icon><View /></el-icon>
                  查看详情
                </el-button>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="24">
        <el-card>
          <template #header>
            <span>Webhook 最近事件</span>
          </template>
          <el-timeline>
            <el-timeline-item
              v-for="(event, index) in webhookEvents"
              :key="index"
              :type="event.type"
              :timestamp="event.time"
            >
              <div class="event-content">
                <span class="event-title">{{ event.title }}</span>
                <span class="event-desc">{{ event.description }}</span>
              </div>
            </el-timeline-item>
          </el-timeline>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useArtifactStore } from '@/stores/artifact'

const artifactStore = useArtifactStore()
const prList = artifactStore.prList
const gitopsConfig = ref({ ...artifactStore.gitOpsConfig })

const webhookEvents = ref([
  {
    title: 'PR 自动构建完成',
    description: 'Pull Request #3 构建成功，所有检查通过',
    type: 'success',
    time: '2024-01-15 14:30:00'
  },
  {
    title: '新 PR 触发构建',
    description: '收到 Pull Request #3，自动触发流水线构建',
    type: 'warning',
    time: '2024-01-15 14:00:00'
  },
  {
    title: 'PR 构建失败',
    description: 'Pull Request #2 构建失败，lint 检查未通过',
    type: 'danger',
    time: '2024-01-15 11:45:00'
  },
  {
    title: 'PR 自动合并',
    description: 'Pull Request #1 已自动合并到 main 分支',
    type: 'success',
    time: '2024-01-15 10:20:00'
  },
  {
    title: 'Webhook 连接成功',
    description: 'GitHub Webhook 已成功连接，开始监听事件',
    type: 'primary',
    time: '2024-01-15 09:00:00'
  }
])

const getPRStatusType = (status) => {
  switch (status) {
    case 'success': return 'success'
    case 'running': return 'warning'
    case 'failed': return 'danger'
    default: return 'info'
  }
}

const getPRStatusLabel = (status) => {
  switch (status) {
    case 'success': return '检查通过'
    case 'running': return '构建中'
    case 'failed': return '检查失败'
    default: return '待处理'
  }
}

const getCheckLabel = (check) => {
  const labelMap = {
    unitTests: '单元测试',
    lint: '代码检查',
    build: '构建验证'
  }
  return labelMap[check] || check
}

const saveConfig = () => {
  Object.assign(artifactStore.gitOpsConfig, gitopsConfig.value)
  ElMessage.success('GitOps 配置已保存')
}

const testWebhook = () => {
  ElMessage.success('Webhook 连接测试成功')
}

const triggerBuild = (pr) => {
  artifactStore.triggerPRBuild(pr.id)
  ElMessage.success(`已为 PR #${pr.id} 触发构建`)
}

const mergePR = async (pr) => {
  try {
    await ElMessageBox.confirm(
      `确定要合并 PR #${pr.id} 吗？所有检查已通过。`,
      '合并确认',
      {
        confirmButtonText: '合并',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    ElMessage.success(`PR #${pr.id} 已成功合并到 ${pr.targetBranch}`)
  } catch {
  }
}

const viewPRDetails = (pr) => {
  ElMessage.info(`正在打开 PR #${pr.id} 详情页面`)
}
</script>

<style scoped>
.gitops {
  height: 100%;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.pr-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-height: 600px;
  overflow-y: auto;
}

.pr-item {
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 16px;
  background: white;
  transition: all 0.2s;
}

.pr-item:hover {
  border-color: #409eff;
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.1);
}

.pr-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.pr-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}

.pr-meta {
  display: flex;
  gap: 20px;
  font-size: 12px;
  color: #909399;
  margin-bottom: 12px;
}

.pr-branch,
.pr-author,
.pr-time {
  display: flex;
  align-items: center;
  gap: 4px;
}

.pr-stats {
  display: flex;
  gap: 20px;
  font-size: 12px;
  color: #606266;
  margin-bottom: 12px;
  padding: 8px 12px;
  background: #f5f7fa;
  border-radius: 4px;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.pr-checks {
  display: flex;
  gap: 16px;
  margin-bottom: 12px;
  padding: 12px;
  background: #fafafa;
  border-radius: 6px;
}

.check-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
}

.check-item.passed {
  color: #67c23a;
}

.check-item.failed {
  color: #f56c6c;
}

.check-item.pending {
  color: #e6a23c;
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.pr-actions {
  display: flex;
  gap: 8px;
}

.event-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.event-title {
  font-weight: 600;
  font-size: 14px;
  color: #303133;
}

.event-desc {
  font-size: 12px;
  color: #909399;
}
</style>
