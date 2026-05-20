<template>
  <div class="triggers-page">
    <el-row :gutter="20">
      <el-col :span="24">
        <el-card class="header-card" shadow="never">
          <div class="page-header">
            <div class="header-left">
              <h2>GitOps 触发器</h2>
              <p>配置 Git 事件触发 Tekton 流水线</p>
            </div>
            <el-button type="primary" @click="showCreateDialog">
              <el-icon><Plus /></el-icon>
              创建触发器
            </el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <el-icon><Bell /></el-icon>
              <span>EventListeners</span>
            </div>
          </template>
          <div class="resource-list">
            <div
              v-for="el in eventListeners"
              :key="el.name"
              class="resource-item"
            >
              <div class="resource-icon">
                <el-icon size="24"><Connection /></el-icon>
              </div>
              <div class="resource-info">
                <div class="resource-name">{{ el.name }}</div>
                <div class="resource-status">
                  <el-tag size="small" type="success">Active</el-tag>
                </div>
              </div>
              <div class="resource-actions">
                <el-button size="small" text @click="viewResource('eventlistener', el.name)">
                  查看
                </el-button>
                <el-button size="small" text type="danger" @click="deleteResource('eventlistener', el.name)">
                  删除
                </el-button>
              </div>
            </div>
            <el-empty v-if="eventListeners.length === 0" description="暂无 EventListener" :image-size="80" />
          </div>
        </el-card>
      </el-col>

      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <el-icon><Link /></el-icon>
              <span>TriggerBindings</span>
            </div>
          </template>
          <div class="resource-list">
            <div
              v-for="binding in triggerBindings"
              :key="binding.name"
              class="resource-item"
            >
              <div class="resource-icon">
                <el-icon size="24"><Promotion /></el-icon>
              </div>
              <div class="resource-info">
                <div class="resource-name">{{ binding.name }}</div>
                <div class="resource-desc">{{ binding.params.length }} 个参数映射</div>
              </div>
              <div class="resource-actions">
                <el-button size="small" text @click="viewResource('triggerbinding', binding.name)">
                  查看
                </el-button>
                <el-button size="small" text type="danger" @click="deleteResource('triggerbinding', binding.name)">
                  删除
                </el-button>
              </div>
            </div>
            <el-empty v-if="triggerBindings.length === 0" description="暂无 TriggerBinding" :image-size="80" />
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <el-icon><Document /></el-icon>
              <span>TriggerTemplates</span>
            </div>
          </template>
          <div class="resource-list">
            <div
              v-for="template in triggerTemplates"
              :key="template.name"
              class="resource-item"
            >
              <div class="resource-icon">
                <el-icon size="24"><Files /></el-icon>
              </div>
              <div class="resource-info">
                <div class="resource-name">{{ template.name }}</div>
                <div class="resource-desc">{{ template.pipelineRef }} 流水线</div>
              </div>
              <div class="resource-actions">
                <el-button size="small" text @click="viewResource('triggertemplate', template.name)">
                  查看
                </el-button>
                <el-button size="small" text type="danger" @click="deleteResource('triggertemplate', template.name)">
                  删除
                </el-button>
              </div>
            </div>
            <el-empty v-if="triggerTemplates.length === 0" description="暂无 TriggerTemplate" :image-size="80" />
          </div>
        </el-card>
      </el-col>

      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <el-icon><Timer /></el-icon>
              <span>最近触发记录</span>
            </div>
          </template>
          <div class="trigger-history">
            <div
              v-for="record in triggerHistory"
              :key="record.id"
              class="history-item"
            >
              <div class="history-icon">
                <el-icon :size="20" :color="getStatusColor(record.status)">
                  <component :is="getStatusIcon(record.status)" />
                </el-icon>
              </div>
              <div class="history-content">
                <div class="history-title">{{ record.eventType }}</div>
                <div class="history-meta">
                  <span>{{ record.repo }}</span>
                  <span>{{ record.branch }}</span>
                  <span>{{ formatTime(record.timestamp) }}</span>
                </div>
              </div>
              <el-tag :type="getStatusType(record.status)" size="small">
                {{ record.status }}
              </el-tag>
            </div>
            <el-empty v-if="triggerHistory.length === 0" description="暂无触发记录" :image-size="80" />
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-dialog v-model="createDialogVisible" title="创建 GitOps 触发器" width="900px">
      <el-form :model="newTrigger" label-width="120px">
        <el-form-item label="触发器名称">
          <el-input v-model="newTrigger.name" placeholder="例如: github-trigger" />
        </el-form-item>

        <el-form-item label="Git 提供商">
          <el-select v-model="newTrigger.provider" style="width: 100%">
            <el-option label="GitHub" value="github" />
            <el-option label="GitLab" value="gitlab" />
            <el-option label="Gitee" value="gitee" />
          </el-select>
        </el-form-item>

        <el-form-item label="事件类型">
          <el-checkbox-group v-model="newTrigger.eventTypes">
            <el-checkbox label="push">Push 事件</el-checkbox>
            <el-checkbox label="pull_request">Pull Request 事件</el-checkbox>
            <el-checkbox label="create">Tag 创建事件</el-checkbox>
          </el-checkbox-group>
        </el-form-item>

        <el-form-item label="目标流水线">
          <el-select v-model="newTrigger.pipelineName" style="width: 100%" placeholder="选择要触发的流水线">
            <el-option
              v-for="p in pipelines"
              :key="p.id"
              :label="p.name"
              :value="p.name"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="参数映射">
          <div class="param-mapping-table">
            <el-table :data="newTrigger.paramMappings" style="width: 100%" size="small">
              <el-table-column label="参数名称" prop="name">
                <template #default="scope">
                  <el-input v-model="scope.row.name" size="small" placeholder="tt.params.*" />
                </template>
              </el-table-column>
              <el-table-column label="表达式" prop="expression">
                <template #default="scope">
                  <el-input v-model="scope.row.expression" size="small" placeholder="$(body.head_commit.id)" />
                </template>
              </el-table-column>
              <el-table-column label="操作" width="80">
                <template #default="scope">
                  <el-button
                    size="small"
                    type="danger"
                    text
                    @click="removeParamMapping(scope.$index)"
                  >
                    删除
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
            <el-button size="small" type="primary" text @click="addParamMapping" style="margin-top: 8px">
              添加参数映射
            </el-button>
          </div>
        </el-form-item>

        <el-form-item label="Webhook Secret">
          <el-input v-model="newTrigger.webhookSecret" type="password" placeholder="用于验证 Git 事件签名" />
        </el-form-item>

        <el-form-item label="命名空间">
          <el-input v-model="newTrigger.namespace" placeholder="default" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="createTrigger">创建触发器</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="yamlPreviewVisible" title="YAML 预览" width="800px">
      <pre class="yaml-content">{{ generatedYAML }}</pre>
      <template #footer>
        <el-button @click="copyYAML">复制到剪贴板</el-button>
        <el-button type="primary" @click="downloadYAML">下载 YAML</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useTektonStore } from '@/stores/tekton'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Plus, Bell, Connection, Link, Promotion, Document, Files, Timer,
  CircleCheck, CircleClose, Loading, Clock
} from '@element-plus/icons-vue'
import YAML from 'yaml'

const tektonStore = useTektonStore()

const eventListeners = ref([
  { name: 'github-listener', namespace: 'default' }
])

const triggerBindings = ref([
  { name: 'github-binding', params: [{ name: 'git-revision' }, { name: 'git-url' }] }
])

const triggerTemplates = ref([
  { name: 'pipeline-template', pipelineRef: 'sample-pipeline' }
])

const triggerHistory = ref([
  { id: 1, eventType: 'push', repo: 'myorg/myapp', branch: 'main', status: 'success', timestamp: Date.now() - 3600000 },
  { id: 2, eventType: 'pull_request', repo: 'myorg/myapp', branch: 'feature/login', status: 'running', timestamp: Date.now() - 1800000 },
  { id: 3, eventType: 'push', repo: 'myorg/myapp', branch: 'develop', status: 'failed', timestamp: Date.now() - 86400000 }
])

const pipelines = ref(tektonStore.pipelines)
const createDialogVisible = ref(false)
const yamlPreviewVisible = ref(false)
const generatedYAML = ref('')

const newTrigger = ref({
  name: '',
  provider: 'github',
  eventTypes: ['push'],
  pipelineName: '',
  paramMappings: [
    { name: 'git-revision', expression: '$(body.head_commit.id)' },
    { name: 'git-url', expression: '$(body.repository.clone_url)' },
    { name: 'image-tag', expression: '$(body.head_commit.id)' }
  ],
  webhookSecret: '',
  namespace: 'default'
})

onMounted(() => {
  loadResources()
})

const loadResources = async () => {
  try {
    const [els, bindings, templates] = await Promise.all([
      tektonStore.k8sClient?.listEventListeners?.() || [],
      tektonStore.k8sClient?.listTriggerBindings?.() || [],
      tektonStore.k8sClient?.listTriggerTemplates?.() || []
    ])
    eventListeners.value = els.length ? els : eventListeners.value
    triggerBindings.value = bindings.length ? bindings : triggerBindings.value
    triggerTemplates.value = templates.length ? templates : triggerTemplates.value
  } catch (e) {
    console.log('Using mock data for triggers')
  }
}

const showCreateDialog = () => {
  createDialogVisible.value = true
}

const addParamMapping = () => {
  newTrigger.value.paramMappings.push({ name: '', expression: '' })
}

const removeParamMapping = (index) => {
  newTrigger.value.paramMappings.splice(index, 1)
}

const createTrigger = async () => {
  try {
    if (!newTrigger.value.name) {
      ElMessage.warning('请输入触发器名称')
      return
    }
    if (!newTrigger.value.pipelineName) {
      ElMessage.warning('请选择目标流水线')
      return
    }

    const yaml = tektonStore.generateTriggerYAML({
      name: newTrigger.value.name,
      eventListener: {
        serviceAccountName: 'tekton-triggers-sa',
        triggers: newTrigger.value.eventTypes.map(type => ({
          name: `${newTrigger.value.provider}-${type}`,
          interceptors: [{ ref: { name: newTrigger.value.provider } }],
          bindings: [{ ref: { name: `${newTrigger.value.name}-binding` } }],
          template: { ref: { name: `${newTrigger.value.name}-template` } }
        }))
      },
      triggerBinding: {
        params: newTrigger.value.paramMappings.map(p => ({ name: p.name, value: p.expression }))
      },
      triggerTemplate: {
        params: newTrigger.value.paramMappings.map(p => ({ name: p.name })),
        pipelineRef: { name: newTrigger.value.pipelineName }
      }
    })

    generatedYAML.value = yaml
    createDialogVisible.value = false
    yamlPreviewVisible.value = true

    ElMessage.success('触发器配置已生成')
  } catch (error) {
    ElMessage.error('创建失败: ' + error.message)
  }
}

const viewResource = (type, name) => {
  ElMessage.info(`查看 ${type}: ${name}`)
}

const deleteResource = (type, name) => {
  ElMessageBox.confirm(`确定要删除 ${type} ${name} 吗？`, '确认删除', {
    type: 'warning'
  }).then(() => {
    ElMessage.success('删除成功')
  }).catch(() => {})
}

const copyYAML = async () => {
  try {
    await navigator.clipboard.writeText(generatedYAML.value)
    ElMessage.success('已复制到剪贴板')
  } catch (e) {
    ElMessage.error('复制失败')
  }
}

const downloadYAML = () => {
  const blob = new Blob([generatedYAML.value], { type: 'text/yaml' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${newTrigger.value.name}-triggers.yaml`
  a.click()
  URL.revokeObjectURL(url)
}

const getStatusColor = (status) => {
  const colors = {
    success: '#67c23a',
    failed: '#f56c6c',
    running: '#409eff',
    pending: '#e6a23c'
  }
  return colors[status] || '#909399'
}

const getStatusType = (status) => {
  const types = {
    success: 'success',
    failed: 'danger',
    running: 'primary',
    pending: 'warning'
  }
  return types[status] || 'info'
}

const getStatusIcon = (status) => {
  const icons = {
    success: CircleCheck,
    failed: CircleClose,
    running: Loading,
    pending: Clock
  }
  return icons[status] || Clock
}

const formatTime = (timestamp) => {
  const date = new Date(timestamp)
  return date.toLocaleString('zh-CN')
}
</script>

<style scoped>
.triggers-page {
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
  align-items: center;
  gap: 8px;
  font-weight: 600;
}

.resource-list, .trigger-history {
  max-height: 400px;
  overflow-y: auto;
}

.resource-item, .history-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  margin-bottom: 8px;
  transition: all 0.2s;
}

.resource-item:hover, .history-item:hover {
  border-color: #409eff;
  background-color: #f5f7fa;
}

.resource-icon {
  color: #409eff;
}

.resource-info {
  flex: 1;
}

.resource-name {
  font-weight: 600;
  margin-bottom: 4px;
}

.resource-desc, .history-meta {
  font-size: 12px;
  color: #909399;
}

.history-meta {
  display: flex;
  gap: 12px;
}

.history-icon {
  flex-shrink: 0;
}

.history-content {
  flex: 1;
}

.history-title {
  font-weight: 500;
  text-transform: uppercase;
  margin-bottom: 4px;
}

.resource-actions {
  display: flex;
  gap: 8px;
}

.param-mapping-table {
  width: 100%;
}

.yaml-content {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 16px;
  border-radius: 8px;
  max-height: 500px;
  overflow: auto;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 13px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
