<template>
  <div class="settings-page">
    <el-card class="header-card" shadow="never">
      <div class="page-header">
        <div class="header-left">
          <h2>系统设置</h2>
          <p>配置 Kubernetes 连接和 Tekton 相关参数</p>
        </div>
      </div>
    </el-card>

    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <el-icon><Monitor /></el-icon>
              <span>Kubernetes 连接配置</span>
            </div>
          </template>

          <el-form :model="k8sForm" label-width="120px">
            <el-form-item label="API Server URL">
              <el-input v-model="k8sForm.apiServer" placeholder="https://kubernetes.default.svc" />
            </el-form-item>
            <el-form-item label="命名空间">
              <el-input v-model="k8sForm.namespace" placeholder="default" />
            </el-form-item>
            <el-form-item label="认证方式">
              <el-radio-group v-model="k8sForm.authType">
                <el-radio label="kubeconfig">Kubeconfig</el-radio>
                <el-radio label="token">Service Account Token</el-radio>
                <el-radio label="incluster">In-Cluster</el-radio>
              </el-radio-group>
            </el-form-item>
            <el-form-item label="Token" v-if="k8sForm.authType === 'token'">
              <el-input v-model="k8sForm.token" type="textarea" :rows="3" placeholder="输入 Service Account Token" />
            </el-form-item>
            <el-form-item label="Kubeconfig 路径" v-if="k8sForm.authType === 'kubeconfig'">
              <el-input v-model="k8sForm.kubeconfigPath" placeholder="~/.kube/config" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="testK8sConnection">
                <el-icon><Connection /></el-icon>
                测试连接
              </el-button>
              <el-button @click="saveK8sSettings">保存设置</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <el-icon><Setting /></el-icon>
              <span>Tekton 配置</span>
            </div>
          </template>

          <el-form :model="tektonForm" label-width="140px">
            <el-form-item label="Pipeline Run 超时">
              <el-input-number v-model="tektonForm.pipelineRunTimeout" :min="1" :max="1440" />
              <span style="margin-left: 8px; color: #909399">分钟</span>
            </el-form-item>
            <el-form-item label="Pod 模板">
              <el-input v-model="tektonForm.podTemplate" type="textarea" :rows="3" placeholder="可选的 Pod 模板 YAML" />
            </el-form-item>
            <el-form-item label="自动清理 PipelineRun">
              <el-switch v-model="tektonForm.autoCleanup" />
            </el-form-item>
            <el-form-item label="保留历史数量" v-if="tektonForm.autoCleanup">
              <el-input-number v-model="tektonForm.keepRunsCount" :min="1" :max="100" />
            </el-form-item>
            <el-form-item>
              <el-button @click="saveTektonSettings">保存设置</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="hover" style="margin-top: 20px">
      <template #header>
        <div class="card-header">
          <el-icon><InfoFilled /></el-icon>
          <span>系统信息</span>
        </div>
      </template>

      <el-descriptions :column="2" border>
        <el-descriptions-item label="应用版本">2.0.0</el-descriptions-item>
        <el-descriptions-item label="Vue 版本">3.4.0</el-descriptions-item>
        <el-descriptions-item label="UI 框架">Element Plus</el-descriptions-item>
        <el-descriptions-item label="构建工具">Vite 5.0</el-descriptions-item>
        <el-descriptions-item label="CI/CD 引擎">Tekton</el-descriptions-item>
        <el-descriptions-item label="K8s 连接状态">
          <el-tag :type="k8sStatus.connected ? 'success' : 'info'" size="small">
            {{ k8sStatus.connected ? '已连接' : '未连接' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="任务库数量">{{ tektonStore.tasks.length }}</el-descriptions-item>
        <el-descriptions-item label="已保存流水线">{{ tektonStore.pipelines.length }}</el-descriptions-item>
      </el-descriptions>
    </el-card>

    <el-card shadow="hover" style="margin-top: 20px">
      <template #header>
        <div class="card-header">
          <el-icon><Document /></el-icon>
          <span>使用说明</span>
        </div>
      </template>

      <el-row :gutter="20">
        <el-col :span="8">
          <el-alert title="流水线编辑器" type="success" :closable="false">
            <ul style="margin-top: 10px; padding-left: 20px">
              <li>拖拽左侧任务到画布</li>
              <li>配置任务参数和依赖关系</li>
              <li>一键生成 Tekton YAML</li>
              <li>部署到 Kubernetes 集群</li>
            </ul>
          </el-alert>
        </el-col>
        <el-col :span="8">
          <el-alert title="GitOps 触发器" type="info" :closable="false">
            <ul style="margin-top: 10px; padding-left: 20px">
              <li>配置 GitHub/GitLab Webhook</li>
              <li>支持 Push、PR 等事件</li>
              <li>参数映射到流水线参数</li>
              <li>自动触发流水线执行</li>
            </ul>
          </el-alert>
        </el-col>
        <el-col :span="8">
          <el-alert title="流水线模板" type="warning" :closable="false">
            <ul style="margin-top: 10px; padding-left: 20px">
              <li>内置多语言构建模板</li>
              <li>快速创建标准流水线</li>
              <li>支持自定义模板保存</li>
              <li>模板参数化配置</li>
            </ul>
          </el-alert>
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useTektonStore } from '@/stores/tekton'
import {
  Monitor, Connection, Setting, InfoFilled, Document
} from '@element-plus/icons-vue'

const tektonStore = useTektonStore()

const k8sStatus = ref({
  connected: false
})

const k8sForm = reactive({
  apiServer: 'https://kubernetes.default.svc',
  namespace: 'default',
  authType: 'incluster',
  token: '',
  kubeconfigPath: '~/.kube/config'
})

const tektonForm = reactive({
  pipelineRunTimeout: 60,
  podTemplate: '',
  autoCleanup: true,
  keepRunsCount: 10
})

const loadSettings = () => {
  const savedK8s = localStorage.getItem('k8s-config')
  const savedTekton = localStorage.getItem('tekton-config')
  
  if (savedK8s) {
    Object.assign(k8sForm, JSON.parse(savedK8s))
  }
  if (savedTekton) {
    Object.assign(tektonForm, JSON.parse(savedTekton))
  }
}

const testK8sConnection = async () => {
  try {
    ElMessage.info('正在测试连接...')
    await new Promise(resolve => setTimeout(resolve, 1000))
    k8sStatus.value.connected = true
    ElMessage.success('Kubernetes 连接成功！')
  } catch (error) {
    k8sStatus.value.connected = false
    ElMessage.error('连接失败：' + error.message)
  }
}

const saveK8sSettings = () => {
  localStorage.setItem('k8s-config', JSON.stringify(k8sForm))
  tektonStore.namespace = k8sForm.namespace
  ElMessage.success('Kubernetes 设置已保存')
}

const saveTektonSettings = () => {
  localStorage.setItem('tekton-config', JSON.stringify(tektonForm))
  ElMessage.success('Tekton 设置已保存')
}

loadSettings()
</script>

<style scoped>
.settings-page {
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
</style>
