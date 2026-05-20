<template>
  <div class="pipeline-editor">
    <el-row :gutter="20">
      <el-col :span="5">
        <el-card class="task-library-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <el-icon><Grid /></el-icon>
              <span>任务库</span>
            </div>
          </template>
          <div class="task-list">
            <div
              v-for="task in tektonStore.tasks"
              :key="task.id"
              class="task-item"
              draggable="true"
              @dragstart="handleDragStart($event, task)"
            >
              <div class="task-icon">{{ getTaskIcon(task.name) }}</div>
              <div class="task-info">
                <div class="task-name">{{ task.name }}</div>
                <div class="task-desc">{{ task.description }}</div>
              </div>
            </div>
          </div>
        </el-card>

        <el-card class="saved-pipelines-card" shadow="hover" style="margin-top: 20px">
          <template #header>
            <div class="card-header">
              <el-icon><Collection /></el-icon>
              <span>已保存流水线</span>
            </div>
          </template>
          <div class="pipeline-list">
            <div
              v-for="pipeline in tektonStore.pipelines"
              :key="pipeline.id"
              class="pipeline-item"
            >
              <div class="pipeline-info">
                <div class="pipeline-name">{{ pipeline.name }}</div>
                <div class="pipeline-desc">{{ pipeline.description || '无描述' }}</div>
              </div>
              <div class="pipeline-actions">
                <el-button size="small" type="primary" @click="loadPipeline(pipeline)">
                  加载
                </el-button>
                <el-button size="small" type="danger" @click="deletePipeline(pipeline.id)">
                  删除
                </el-button>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="14">
        <el-card class="canvas-card" shadow="hover">
          <template #header>
            <div class="card-header canvas-header">
              <div class="pipeline-title">
                <el-input
                  v-model="tektonStore.editorPipeline.name"
                  placeholder="流水线名称"
                  style="width: 300px; margin-right: 20px"
                />
                <el-tag type="info">{{ tektonStore.editorPipeline.tasks.length }} 个任务</el-tag>
              </div>
              <div class="header-actions">
                <el-button size="small" @click="showTemplates">
                  <el-icon><DocumentCopy /></el-icon>
                  模板
                </el-button>
                <el-button size="small" @click="tektonStore.resetEditorPipeline()">
                  <el-icon><Refresh /></el-icon>
                  重置
                </el-button>
                <el-button size="small" type="primary" @click="tektonStore.savePipeline()">
                  <el-icon><Save /></el-icon>
                  保存
                </el-button>
                <el-button size="small" type="success" @click="deployToK8s">
                  <el-icon><Upload /></el-icon>
                  部署到K8s
                </el-button>
                <el-button size="small" type="warning" @click="showYAML = true">
                  <el-icon><View /></el-icon>
                  查看YAML
                </el-button>
              </div>
            </div>
          </template>

          <div
            class="canvas-area"
            @drop="handleDrop"
            @dragover="handleDragOver"
            ref="canvasRef"
          >
            <div v-if="tektonStore.editorPipeline.tasks.length === 0" class="empty-canvas">
              <el-empty description="拖拽左侧任务到此处开始构建流水线" :image-size="150">
                <template #description>
                  <p>拖拽左侧任务到此处开始构建流水线</p>
                  <el-button type="primary" @click="showTemplates">使用模板快速开始</el-button>
                </template>
              </el-empty>
            </div>

            <div v-else class="tasks-flow">
              <div
                v-for="(task, index) in tektonStore.editorPipeline.tasks"
                :key="task.id"
                class="task-node"
                :class="{ selected: tektonStore.selectedTask?.id === task.id }"
                @click="selectTask(task)"
              >
                <div class="node-header">
                  <span class="node-name">{{ task.name }}</span>
                  <el-button
                    size="small"
                    type="danger"
                    text
                    @click.stop="removeTask(task.id)"
                  >
                    <el-icon><Close /></el-icon>
                  </el-button>
                </div>
                <div class="node-body">
                  <div class="node-taskref">{{ task.taskRef.name }}</div>
                  <div class="node-params">
                    <span v-for="param in task.params.slice(0, 2)" :key="param.name" class="param-tag">
                      {{ param.name }}: {{ param.value || '未设置' }}
                    </span>
                    <span v-if="task.params.length > 2" class="param-tag">+{{ task.params.length - 2 }}</span>
                  </div>
                </div>
                <div v-if="task.runAfter && task.runAfter.length > 0" class="node-runafter">
                  依赖: {{ task.runAfter.join(', ') }}
                </div>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="5">
        <el-card class="config-panel" shadow="hover" v-if="tektonStore.selectedTask">
          <template #header>
            <div class="card-header">
              <el-icon><Setting /></el-icon>
              <span>任务配置</span>
            </div>
          </template>

          <el-form label-position="top" size="small">
            <el-form-item label="任务名称">
              <el-input v-model="tektonStore.selectedTask.name" />
            </el-form-item>

            <el-form-item label="任务引用">
              <el-select v-model="tektonStore.selectedTask.taskRef.name" style="width: 100%">
                <el-option
                  v-for="task in tektonStore.tasks"
                  :key="task.id"
                  :label="task.name"
                  :value="task.name"
                />
              </el-select>
            </el-form-item>

            <el-form-item label="参数配置">
              <div v-for="param in tektonStore.selectedTask.params" :key="param.name" class="param-item">
                <el-input
                  :model-value="param.value"
                  @update:model-value="updateParam(param.name, $event)"
                  :placeholder="param.name"
                  size="small"
                />
              </div>
              <el-button type="primary" link size="small" @click="addParam">
                添加参数
              </el-button>
            </el-form-item>

            <el-form-item label="依赖任务 (runAfter)">
              <el-select
                v-model="tektonStore.selectedTask.runAfter"
                multiple
                style="width: 100%"
              >
                <el-option
                  v-for="t in tektonStore.editorPipeline.tasks.filter(t => t.id !== tektonStore.selectedTask.id)"
                  :key="t.id"
                  :label="t.name"
                  :value="t.name"
                />
              </el-select>
            </el-form-item>

            <el-form-item label="工作空间映射">
              <div v-for="ws in tektonStore.selectedTask.workspaces" :key="ws.name" class="ws-item">
                <span class="ws-label">{{ ws.name }} → </span>
                <el-input v-model="ws.workspace" size="small" style="width: calc(100% - 80px)" />
              </div>
            </el-form-item>
          </el-form>
        </el-card>

        <el-card class="pipeline-params-card" shadow="hover" style="margin-top: 20px">
          <template #header>
            <div class="card-header">
              <el-icon><Key /></el-icon>
              <span>流水线参数</span>
              <el-button size="small" type="primary" text @click="showAddParam = true">
                添加
              </el-button>
            </div>
          </template>
          <div class="params-list">
            <div
              v-for="param in tektonStore.editorPipeline.params"
              :key="param.name"
              class="param-row"
            >
              <div class="param-info">
                <span class="param-name">{{ param.name }}</span>
                <span class="param-type">({{ param.type }})</span>
              </div>
              <el-button size="small" type="danger" text @click="tektonStore.removeParam(param.name)">
                删除
              </el-button>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-dialog v-model="showYAML" title="Tekton YAML" width="800px">
      <el-tabs v-model="activeYAMLTab">
        <el-tab-pane label="Pipeline" name="pipeline">
          <pre class="yaml-content">{{ pipelineYAML }}</pre>
        </el-tab-pane>
        <el-tab-pane label="PipelineRun" name="pipelinerun">
          <pre class="yaml-content">{{ pipelineRunYAML }}</pre>
        </el-tab-pane>
      </el-tabs>
      <template #footer>
        <el-button @click="copyYAML">复制到剪贴板</el-button>
        <el-button type="primary" @click="downloadYAML">下载 YAML</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showTemplatesDialog" title="选择流水线模板" width="700px">
      <el-row :gutter="20">
        <el-col :span="12" v-for="template in templates" :key="template.id">
          <el-card class="template-card" shadow="hover" @click="applyTemplate(template)">
            <div class="template-icon">{{ template.icon }}</div>
            <div class="template-name">{{ template.name }}</div>
            <div class="template-desc">{{ template.description }}</div>
            <el-tag size="small" type="info">{{ template.tasks.length }} 个任务</el-tag>
          </el-card>
        </el-col>
      </el-row>
    </el-dialog>

    <el-dialog v-model="showAddParam" title="添加参数" width="400px">
      <el-form label-position="top">
        <el-form-item label="参数名称">
          <el-input v-model="newParam.name" />
        </el-form-item>
        <el-form-item label="参数类型">
          <el-select v-model="newParam.type" style="width: 100%">
            <el-option label="string" value="string" />
            <el-option label="array" value="array" />
            <el-option label="object" value="object" />
          </el-select>
        </el-form-item>
        <el-form-item label="默认值">
          <el-input v-model="newParam.default" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="newParam.description" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddParam = false">取消</el-button>
        <el-button type="primary" @click="confirmAddParam">确认添加</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useTektonStore } from '@/stores/tekton'
import { k8sClient } from '@/api/kubernetes'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Grid, Collection, DocumentCopy, Refresh, Save, Upload, View, Close, Setting, Key
} from '@element-plus/icons-vue'

const tektonStore = useTektonStore()
const canvasRef = ref(null)
const showYAML = ref(false)
const activeYAMLTab = ref('pipeline')
const showTemplatesDialog = ref(false)
const showAddParam = ref(false)
const newParam = ref({ name: '', type: 'string', default: '', description: '' })

const templates = [
  {
    id: 'nodejs-build',
    name: 'Node.js 构建部署',
    icon: '📦',
    description: 'Git拉取 → npm安装 → 构建 → 镜像构建 → 部署',
    tasks: ['git-clone', 'npm', 'docker-build', 'kubectl'],
    params: [
      { name: 'git-url', type: 'string', description: 'Git仓库地址' },
      { name: 'git-revision', type: 'string', default: 'main', description: 'Git分支' },
      { name: 'image-name', type: 'string', description: '镜像名称' }
    ]
  },
  {
    id: 'java-maven',
    name: 'Java Maven 构建',
    icon: '☕',
    description: 'Git拉取 → Maven构建 → 单元测试 → 镜像构建 → 部署',
    tasks: ['git-clone', 'maven', 'docker-build', 'kubectl'],
    params: [
      { name: 'git-url', type: 'string', description: 'Git仓库地址' },
      { name: 'mvn-goals', type: 'string', default: 'clean package', description: 'Maven目标' }
    ]
  },
  {
    id: 'simple-git',
    name: '简易Git构建',
    icon: '🚀',
    description: 'Git拉取 → 脚本执行',
    tasks: ['git-clone', 'npm'],
    params: [
      { name: 'git-url', type: 'string', description: 'Git仓库地址' }
    ]
  }
]

const pipelineYAML = computed(() => tektonStore.generatePipelineYAML())
const pipelineRunYAML = computed(() => {
  const params = {}
  tektonStore.editorPipeline.params.forEach(p => {
    params[p.name] = p.default || ''
  })
  return tektonStore.generatePipelineRunYAML(tektonStore.editorPipeline.name, params)
})

const getTaskIcon = (taskName) => {
  const icons = {
    'git-clone': '📥',
    'npm': '📦',
    'maven': '☕',
    'docker-build': '🐳',
    'kubectl': '☸️'
  }
  return icons[taskName] || '📋'
}

const handleDragStart = (event, task) => {
  event.dataTransfer.setData('application/json', JSON.stringify(task))
  event.dataTransfer.effectAllowed = 'copy'
}

const handleDragOver = (event) => {
  event.preventDefault()
  event.dataTransfer.dropEffect = 'copy'
}

const handleDrop = (event) => {
  event.preventDefault()
  try {
    const taskData = JSON.parse(event.dataTransfer.getData('application/json'))
    tektonStore.addTaskToPipeline(taskData)
    ElMessage.success('任务已添加')
  } catch (e) {
    console.error('Drop error:', e)
  }
}

const selectTask = (task) => {
  tektonStore.selectedTask = task
}

const removeTask = (taskId) => {
  ElMessageBox.confirm('确定要删除此任务吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    tektonStore.removeTaskFromPipeline(taskId)
    if (tektonStore.selectedTask?.id === taskId) {
      tektonStore.selectedTask = null
    }
    ElMessage.success('任务已删除')
  }).catch(() => {})
}

const updateParam = (paramName, value) => {
  const param = tektonStore.selectedTask.params.find(p => p.name === paramName)
  if (param) {
    param.value = value
  }
}

const addParam = () => {
  tektonStore.selectedTask.params.push({ name: 'new-param', value: '' })
}

const confirmAddParam = () => {
  if (newParam.value.name) {
    tektonStore.addParam(newParam.value)
    newParam.value = { name: '', type: 'string', default: '', description: '' }
    showAddParam.value = false
    ElMessage.success('参数已添加')
  } else {
    ElMessage.warning('请输入参数名称')
  }
}

const applyTemplate = (template) => {
  tektonStore.resetEditorPipeline()
  tektonStore.editorPipeline.name = template.id
  tektonStore.editorPipeline.description = template.description

  template.tasks.forEach(taskName => {
    const taskTemplate = tektonStore.tasks.find(t => t.name === taskName)
    if (taskTemplate) {
      tektonStore.addTaskToPipeline(taskTemplate)
    }
  })

  tektonStore.editorPipeline.params = [...template.params]

  if (tektonStore.editorPipeline.tasks.length > 1) {
    for (let i = 1; i < tektonStore.editorPipeline.tasks.length; i++) {
      tektonStore.editorPipeline.tasks[i].runAfter = [tektonStore.editorPipeline.tasks[i - 1].name]
    }
  }

  showTemplatesDialog.value = false
  ElMessage.success(`已应用模板: ${template.name}`)
}

const loadPipeline = (pipeline) => {
  tektonStore.loadPipeline(pipeline.id)
  ElMessage.success('流水线已加载')
}

const deletePipeline = async (pipelineId) => {
  try {
    await ElMessageBox.confirm('确定要删除此流水线吗？', '提示', {
      type: 'warning'
    })
    tektonStore.deletePipeline(pipelineId)
    ElMessage.success('流水线已删除')
  } catch {
  }
}

const showTemplates = () => {
  showTemplatesDialog.value = true
}

const deployToK8s = async () => {
  try {
    await ElMessageBox.confirm('将部署 Pipeline 到 Kubernetes 集群', '确认部署', {
      type: 'info'
    })

    const yaml = tektonStore.generatePipelineYAML()
    await k8sClient.createPipeline(tektonStore.namespace, yaml)
    ElMessage.success('Pipeline 已部署到 Kubernetes')
  } catch (error) {
    ElMessage.error('部署失败: ' + error.message)
  }
}

const copyYAML = async () => {
  const content = activeYAMLTab.value === 'pipeline' ? pipelineYAML.value : pipelineRunYAML.value
  try {
    await navigator.clipboard.writeText(content)
    ElMessage.success('已复制到剪贴板')
  } catch (e) {
    ElMessage.error('复制失败')
  }
}

const downloadYAML = () => {
  const content = activeYAMLTab.value === 'pipeline' ? pipelineYAML.value : pipelineRunYAML.value
  const blob = new Blob([content], { type: 'text/yaml' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${tektonStore.editorPipeline.name}-${activeYAMLTab.value}.yaml`
  a.click()
  URL.revokeObjectURL(url)
}
</script>

<style scoped>
.pipeline-editor {
  padding: 0;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}

.task-list, .pipeline-list, .params-list {
  max-height: 400px;
  overflow-y: auto;
}

.task-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  margin-bottom: 8px;
  cursor: grab;
  transition: all 0.2s;
}

.task-item:hover {
  border-color: #409eff;
  background-color: #ecf5ff;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.15);
}

.task-item:active {
  cursor: grabbing;
}

.task-icon {
  font-size: 24px;
}

.task-info .task-name {
  font-weight: 600;
  color: #303133;
  margin-bottom: 4px;
}

.task-info .task-desc {
  font-size: 12px;
  color: #909399;
}

.pipeline-item {
  padding: 12px;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  margin-bottom: 8px;
}

.pipeline-info .pipeline-name {
  font-weight: 600;
  margin-bottom: 4px;
}

.pipeline-info .pipeline-desc {
  font-size: 12px;
  color: #909399;
  margin-bottom: 8px;
}

.pipeline-actions {
  display: flex;
  gap: 8px;
}

.canvas-card {
  min-height: 700px;
}

.canvas-header {
  justify-content: space-between;
}

.pipeline-title {
  display: flex;
  align-items: center;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.canvas-area {
  min-height: 600px;
  border: 2px dashed #dcdfe6;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.canvas-area:hover {
  border-color: #409eff;
  background-color: #f5f7fa;
}

.empty-canvas {
  text-align: center;
}

.tasks-flow {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 40px;
  width: 100%;
}

.task-node {
  background: white;
  border: 2px solid #dcdfe6;
  border-radius: 12px;
  padding: 16px;
  min-width: 280px;
  transition: all 0.2s;
  position: relative;
}

.task-node.selected {
  border-color: #409eff;
  box-shadow: 0 0 0 3px rgba(64, 158, 255, 0.1);
}

.task-node:hover {
  border-color: #409eff;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.node-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.node-name {
  font-weight: 600;
  font-size: 14px;
}

.node-body .node-taskref {
  font-size: 12px;
  color: #606266;
  margin-bottom: 8px;
}

.node-params {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.param-tag {
  background-color: #f4f4f5;
  color: #909399;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 11px;
}

.node-runafter {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid #ebeef5;
  font-size: 12px;
  color: #909399;
}

.config-panel, .pipeline-params-card {
  min-height: 350px;
}

.param-item, .ws-item {
  margin-bottom: 8px;
}

.param-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid #ebeef5;
}

.param-info .param-name {
  font-weight: 500;
}

.param-info .param-type {
  color: #909399;
  font-size: 12px;
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

.template-card {
  cursor: pointer;
  transition: all 0.2s;
  text-align: center;
}

.template-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
}

.template-icon {
  font-size: 48px;
  margin-bottom: 12px;
}

.template-name {
  font-weight: 600;
  margin-bottom: 8px;
}

.template-desc {
  font-size: 12px;
  color: #909399;
  margin-bottom: 12px;
}

.ws-label {
  font-size: 12px;
  color: #606266;
}
</style>
