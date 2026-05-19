<template>
  <div class="tasks-page">
    <el-card class="header-card" shadow="never">
      <div class="page-header">
        <div class="header-left">
          <h2>任务库 (Tasks)</h2>
          <p>管理 Tekton Task，构建可复用的流水线组件</p>
        </div>
        <el-button type="primary" @click="showCreateDialog = true">
          <el-icon><Plus /></el-icon>
          新建 Task
        </el-button>
      </div>
    </el-card>

    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="8" v-for="task in tasks" :key="task.id">
        <el-card class="task-card" shadow="hover">
          <div class="task-header">
            <div class="task-icon" :style="{ background: task.color }">
              <el-icon size="24"><component :is="task.icon" /></el-icon>
            </div>
            <div class="task-title">
              <h3>{{ task.name }}</h3>
              <el-tag size="small" type="info">{{ task.category }}</el-tag>
            </div>
          </div>
          <p class="task-desc">{{ task.description }}</p>
          <div class="task-meta">
            <span class="meta-item">
              <el-icon size="14"><Document /></el-icon>
              {{ task.params.length }} 参数
            </span>
            <span class="meta-item">
              <el-icon size="14"><Box /></el-icon>
              {{ task.steps.length }} 步骤
            </span>
            <span class="meta-item">
              <el-icon size="14"><FolderOpened /></el-icon>
              {{ task.workspaces.length }} 工作区
            </span>
          </div>
          <div class="task-actions">
            <el-button size="small" @click="viewTask(task)">查看详情</el-button>
            <el-button size="small" type="primary" @click="useTask(task)">使用</el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-dialog v-model="detailDialogVisible" title="Task 详情" width="900px">
      <div v-if="selectedTask" class="task-detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="Task 名称">{{ selectedTask.name }}</el-descriptions-item>
          <el-descriptions-item label="分类">{{ selectedTask.category }}</el-descriptions-item>
          <el-descriptions-item label="描述" :span="2">{{ selectedTask.description }}</el-descriptions-item>
        </el-descriptions>

        <h4 style="margin: 20px 0 12px 0">参数定义</h4>
        <el-table :data="selectedTask.params" size="small" style="width: 100%">
          <el-table-column prop="name" label="参数名" width="150" />
          <el-table-column prop="type" label="类型" width="100" />
          <el-table-column prop="description" label="描述" />
          <el-table-column prop="default" label="默认值" width="150" />
        </el-table>

        <h4 style="margin: 20px 0 12px 0">工作区</h4>
        <el-table :data="selectedTask.workspaces" size="small" style="width: 100%">
          <el-table-column prop="name" label="名称" width="150" />
          <el-table-column prop="description" label="描述" />
        </el-table>

        <h4 style="margin: 20px 0 12px 0">执行步骤 (Steps)</h4>
        <div class="steps-list">
          <div v-for="(step, index) in selectedTask.steps" :key="index" class="step-item">
            <div class="step-number">{{ index + 1 }}</div>
            <div class="step-content">
              <div class="step-name">{{ step.name }}</div>
              <div class="step-image">镜像: {{ step.image }}</div>
              <pre class="step-script">{{ step.script }}</pre>
            </div>
          </div>
        </div>

        <h4 style="margin: 20px 0 12px 0">YAML 定义</h4>
        <pre class="yaml-content">{{ generateTaskYAML(selectedTask) }}</pre>
      </div>
      <template #footer>
        <el-button @click="copyYAML">复制 YAML</el-button>
        <el-button type="primary" @click="useTask(selectedTask)">使用此 Task</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showCreateDialog" title="新建 Task" width="700px">
      <el-form :model="newTask" label-width="100px">
        <el-form-item label="Task 名称">
          <el-input v-model="newTask.name" placeholder="例如: build-image" />
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="newTask.category" style="width: 100%">
            <el-option label="Git 操作" value="git" />
            <el-option label="Node.js" value="nodejs" />
            <el-option label="Java" value="java" />
            <el-option label="Python" value="python" />
            <el-option label="Go" value="go" />
            <el-option label="Docker" value="docker" />
            <el-option label="Kubernetes" value="k8s" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="newTask.description" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="参数">
          <div v-for="(param, index) in newTask.params" :key="index" class="param-row">
            <el-input v-model="param.name" placeholder="参数名" style="width: 120px" />
            <el-select v-model="param.type" style="width: 100px; margin: 0 8px">
              <el-option label="string" value="string" />
              <el-option label="array" value="array" />
            </el-select>
            <el-input v-model="param.description" placeholder="描述" style="flex: 1" />
            <el-button size="small" type="danger" text @click="newTask.params.splice(index, 1)">
              删除
            </el-button>
          </div>
          <el-button size="small" type="primary" text @click="newTask.params.push({ name: '', type: 'string', description: '', default: '' })">
            添加参数
          </el-button>
        </el-form-item>
        <el-form-item label="工作区">
          <div v-for="(ws, index) in newTask.workspaces" :key="index" class="param-row">
            <el-input v-model="ws.name" placeholder="名称" style="width: 150px" />
            <el-input v-model="ws.description" placeholder="描述" style="flex: 1" />
            <el-button size="small" type="danger" text @click="newTask.workspaces.splice(index, 1)">
              删除
            </el-button>
          </div>
          <el-button size="small" type="primary" text @click="newTask.workspaces.push({ name: '', description: '' })">
            添加工作区
          </el-button>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="createTask">创建 Task</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useTektonStore } from '@/stores/tekton'
import { ElMessage } from 'element-plus'
import {
  Plus, Document, Box, FolderOpened,
  Download, MagicStick, Monitor, Coin
} from '@element-plus/icons-vue'
import YAML from 'yaml'

const router = useRouter()
const tektonStore = useTektonStore()

const detailDialogVisible = ref(false)
const showCreateDialog = ref(false)
const selectedTask = ref(null)

const taskIcons = {
  git: Download,
  nodejs: MagicStick,
  java: Monitor,
  python: Coin,
  docker: Box,
  k8s: FolderOpened
}

const taskColors = {
  git: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
  nodejs: 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
  java: 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
  python: 'linear-gradient(135deg, #a8edea 0%, #fed6e3 100%)',
  docker: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
  k8s: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)'
}

const tasks = ref(tektonStore.tasks.map(t => ({
  ...t,
  category: t.category || 'nodejs',
  icon: taskIcons[t.category || 'nodejs'] || Document,
  color: taskColors[t.category || 'nodejs'] || taskColors.nodejs
})))

const newTask = ref({
  name: '',
  category: 'nodejs',
  description: '',
  params: [],
  workspaces: [],
  steps: []
})

const viewTask = (task) => {
  selectedTask.value = task
  detailDialogVisible.value = true
}

const useTask = (task) => {
  tektonStore.addTaskToPipeline(task)
  detailDialogVisible.value = false
  router.push('/pipeline')
  ElMessage.success(`已添加 Task: ${task.name}`)
}

const generateTaskYAML = (task) => {
  const taskCR = {
    apiVersion: 'tekton.dev/v1beta1',
    kind: 'Task',
    metadata: {
      name: task.name,
      labels: { 'app.kubernetes.io/managed-by': 'tekton-builder' }
    },
    spec: {
      params: task.params.map(p => ({
        name: p.name,
        type: p.type,
        description: p.description,
        default: p.default
      })),
      workspaces: task.workspaces.map(w => ({
        name: w.name,
        description: w.description
      })),
      steps: task.steps.map(s => ({
        name: s.name,
        image: s.image,
        script: s.script
      }))
    }
  }
  return YAML.stringify(taskCR, null, 2)
}

const copyYAML = async () => {
  try {
    const yaml = generateTaskYAML(selectedTask.value)
    await navigator.clipboard.writeText(yaml)
    ElMessage.success('已复制 YAML 到剪贴板')
  } catch (e) {
    ElMessage.error('复制失败')
  }
}

const createTask = () => {
  if (!newTask.value.name) {
    ElMessage.warning('请输入 Task 名称')
    return
  }
  showCreateDialog.value = false
  ElMessage.success('Task 创建成功')
}
</script>

<style scoped>
.tasks-page {
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

.task-card {
  transition: all 0.3s;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.task-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.12);
}

.task-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.task-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.task-title h3 {
  margin: 0 0 4px 0;
  font-size: 16px;
  font-weight: 600;
  color: #1e293b;
}

.task-desc {
  font-size: 14px;
  color: #64748b;
  margin: 0 0 16px 0;
  line-height: 1.5;
  flex: 1;
}

.task-meta {
  display: flex;
  gap: 16px;
  font-size: 13px;
  color: #64748b;
  margin-bottom: 16px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.task-actions {
  display: flex;
  gap: 8px;
}

.steps-list {
  max-height: 400px;
  overflow-y: auto;
}

.step-item {
  display: flex;
  gap: 12px;
  padding: 16px;
  background: #f8fafc;
  border-radius: 8px;
  margin-bottom: 8px;
}

.step-number {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #4f46e5;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  flex-shrink: 0;
}

.step-content {
  flex: 1;
}

.step-name {
  font-weight: 600;
  margin-bottom: 4px;
  color: #1e293b;
}

.step-image {
  font-size: 13px;
  color: #64748b;
  margin-bottom: 8px;
}

.step-script {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 12px;
  border-radius: 6px;
  margin: 0;
  font-family: 'Consolas', monospace;
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-all;
}

.yaml-content {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 16px;
  border-radius: 8px;
  max-height: 400px;
  overflow: auto;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 13px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-all;
  margin: 0;
}

.param-row {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
  gap: 8px;
}
</style>
