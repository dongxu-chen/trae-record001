<template>
  <div class="templates-page">
    <el-card class="header-card" shadow="never">
      <div class="page-header">
        <div class="header-left">
          <h2>流水线模板市场</h2>
          <p>快速开始使用预制的 Tekton 流水线模板</p>
        </div>
        <el-input
          v-model="searchQuery"
          placeholder="搜索模板..."
          style="width: 300px"
          prefix-icon="Search"
        />
      </div>
    </el-card>

    <el-card style="margin-top: 20px">
      <div class="filter-bar">
        <div class="filter-tags">
          <el-tag
            v-for="cat in categories"
            :key="cat.id"
            :type="selectedCategory === cat.id ? 'primary' : 'info'"
            @click="selectedCategory = cat.id"
            style="cursor: pointer"
          >
            {{ cat.name }} ({{ cat.count }})
          </el-tag>
        </div>
      </div>

      <el-row :gutter="24" class="templates-grid">
        <el-col
          v-for="template in filteredTemplates"
          :key="template.id"
          :xs="24"
          :sm="12"
          :md="8"
          :lg="6"
        >
          <el-card class="template-card" shadow="hover" :body-style="{ padding: '20px' }">
            <div class="template-icon" :style="{ background: template.color }">
              <el-icon size="32"><component :is="template.icon" /></el-icon>
            </div>
            <h3 class="template-name">{{ template.name }}</h3>
            <p class="template-desc">{{ template.description }}</p>
            <div class="template-tags">
              <el-tag size="small" type="info" v-for="tag in template.tags" :key="tag">
                {{ tag }}
              </el-tag>
            </div>
            <div class="template-meta">
              <span class="meta-item">
                <el-icon size="14"><Timer /></el-icon>
                {{ template.avgDuration }}
              </span>
              <span class="meta-item">
                <el-icon size="14"><Box /></el-icon>
                {{ template.taskCount }} 任务
              </span>
            </div>
            <el-button type="primary" style="width: 100%; margin-top: 16px" @click="useTemplate(template)">
              使用模板
            </el-button>
          </el-card>
        </el-col>
      </el-row>
    </el-card>

    <el-dialog v-model="previewVisible" title="模板详情" width="900px">
      <div v-if="selectedTemplate" class="template-preview">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="模板名称">{{ selectedTemplate.name }}</el-descriptions-item>
          <el-descriptions-item label="分类">{{ selectedTemplate.category }}</el-descriptions-item>
          <el-descriptions-item label="任务数">{{ selectedTemplate.taskCount }}</el-descriptions-item>
          <el-descriptions-item label="平均耗时">{{ selectedTemplate.avgDuration }}</el-descriptions-item>
          <el-descriptions-item label="标签" :span="2">
            <el-tag size="small" v-for="tag in selectedTemplate.tags" :key="tag" style="margin-right: 8px">
              {{ tag }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="描述" :span="2">{{ selectedTemplate.description }}</el-descriptions-item>
        </el-descriptions>

        <h4 style="margin-top: 24px">任务流程</h4>
        <el-steps direction="vertical" finish-status="success">
          <el-step
            v-for="(task, index) in selectedTemplate.tasks"
            :key="index"
            :title="task"
            :description="`步骤 ${index + 1}`"
          />
        </el-steps>

        <h4 style="margin-top: 24px">YAML 预览</h4>
        <pre class="yaml-preview">{{ previewYAML }}</pre>
      </div>
      <template #footer>
        <el-button @click="previewVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmUseTemplate">使用此模板</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useTektonStore } from '@/stores/tekton'
import {
  Search, Document, Code, Box, Timer, Loading,
  Service, Promotion, Platform, Coin
} from '@element-plus/icons-vue'

const router = useRouter()
const tektonStore = useTektonStore()

const searchQuery = ref('')
const selectedCategory = ref('all')
const previewVisible = ref(false)
const selectedTemplate = ref(null)
const previewYAML = ref('')

const categories = ref([
  { id: 'all', name: '全部', count: 8 },
  { id: 'nodejs', name: 'Node.js', count: 2 },
  { id: 'java', name: 'Java', count: 2 },
  { id: 'python', name: 'Python', count: 2 },
  { id: 'go', name: 'Go', count: 1 },
  { id: 'deploy', name: '部署', count: 1 }
])

const templates = ref([
  {
    id: 'nodejs-build',
    name: 'Node.js 完整构建',
    description: 'Node.js 项目完整 CI/CD 流水线，包含测试、构建、镜像推送',
    category: 'nodejs',
    tags: ['npm', 'test', 'build', 'docker'],
    icon: Document,
    color: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    avgDuration: '8-15 分钟',
    taskCount: 5,
    tasks: ['Git Clone', 'Install Dependencies', 'Run Tests', 'Build', 'Docker Build & Push']
  },
  {
    id: 'nodejs-serverless',
    name: 'Node.js Serverless',
    description: 'Serverless 框架部署，自动部署到阿里云/腾讯云函数',
    category: 'nodejs',
    tags: ['serverless', 'faas', 'deploy'],
    icon: Service,
    color: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
    avgDuration: '5-10 分钟',
    taskCount: 4,
    tasks: ['Git Clone', 'Install', 'Test', 'Serverless Deploy']
  },
  {
    id: 'java-maven',
    name: 'Java Maven 构建',
    description: 'Spring Boot 项目标准 CI/CD 流水线',
    category: 'java',
    tags: ['maven', 'spring-boot', 'docker'],
    icon: Code,
    color: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
    avgDuration: '10-20 分钟',
    taskCount: 6,
    tasks: ['Git Clone', 'Maven Test', 'Maven Build', 'SonarQube Scan', 'Docker Build', 'Deploy']
  },
  {
    id: 'java-gradle',
    name: 'Java Gradle 构建',
    description: 'Gradle 构建的 Java 项目流水线',
    category: 'java',
    tags: ['gradle', 'java', 'docker'],
    icon: Promotion,
    color: 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
    avgDuration: '10-18 分钟',
    taskCount: 5,
    tasks: ['Git Clone', 'Gradle Test', 'Gradle Build', 'Docker Build', 'Push']
  },
  {
    id: 'python-poetry',
    name: 'Python Poetry 构建',
    description: '使用 Poetry 管理依赖的 Python 项目流水线',
    category: 'python',
    tags: ['python', 'poetry', 'pytest'],
    icon: Platform,
    color: 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
    avgDuration: '5-12 分钟',
    taskCount: 5,
    tasks: ['Git Clone', 'Poetry Install', 'Pytest', 'Lint', 'Build Package']
  },
  {
    id: 'python-ml',
    name: 'Python ML 流水线',
    description: '机器学习项目完整训练和部署流水线',
    category: 'python',
    tags: ['ml', 'training', 'model'],
    icon: Coin,
    color: 'linear-gradient(135deg, #a8edea 0%, #fed6e3 100%)',
    avgDuration: '30-60 分钟',
    taskCount: 7,
    tasks: ['Git Clone', 'Data Prep', 'Train Model', 'Evaluate', 'Save Model', 'Build Image', 'Deploy']
  },
  {
    id: 'go-build',
    name: 'Go 构建部署',
    description: 'Golang 项目标准 CI/CD 流水线',
    category: 'go',
    tags: ['golang', 'build', 'docker'],
    icon: Loading,
    color: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    avgDuration: '3-8 分钟',
    taskCount: 5,
    tasks: ['Git Clone', 'Go Test', 'Go Build', 'Docker Build', 'Push']
  },
  {
    id: 'k8s-deploy',
    name: 'K8s 应用部署',
    description: 'Kubernetes 应用部署和更新流水线',
    category: 'deploy',
    tags: ['k8s', 'helm', 'deploy'],
    icon: Box,
    color: 'linear-gradient(135deg, #f5af19 0%, #f12711 100%)',
    avgDuration: '5-10 分钟',
    taskCount: 4,
    tasks: ['Git Clone', 'Helm Lint', 'Helm Template', 'Kubectl Apply']
  }
])

const filteredTemplates = computed(() => {
  let result = templates.value
  if (selectedCategory.value !== 'all') {
    result = result.filter(t => t.category === selectedCategory.value)
  }
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(t =>
      t.name.toLowerCase().includes(query) ||
      t.description.toLowerCase().includes(query) ||
      t.tags.some(tag => tag.toLowerCase().includes(query))
    )
  }
  return result
})

const useTemplate = (template) => {
  selectedTemplate.value = template
  previewYAML.value = tektonStore.generatePipelineYAML()
  previewVisible.value = true
}

const confirmUseTemplate = () => {
  tektonStore.resetEditorPipeline()
  tektonStore.editorPipeline.name = selectedTemplate.value.id
  tektonStore.editorPipeline.description = selectedTemplate.value.description

  selectedTemplate.value.tasks.forEach((taskName, index) => {
    const taskTemplate = tektonStore.tasks[index % tektonStore.tasks.length]
    tektonStore.addTaskToPipeline(taskTemplate)
  })

  previewVisible.value = false
  router.push('/pipeline')
}
</script>

<style scoped>
.templates-page {
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

.filter-bar {
  margin-bottom: 24px;
}

.filter-tags {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.templates-grid {
  margin-top: 20px;
}

.template-card {
  height: 100%;
  transition: all 0.3s;
}

.template-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.12);
}

.template-icon {
  width: 64px;
  height: 64px;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  margin-bottom: 16px;
}

.template-name {
  font-size: 18px;
  font-weight: 600;
  margin: 0 0 8px 0;
  color: #1e293b;
}

.template-desc {
  font-size: 14px;
  color: #64748b;
  margin: 0 0 12px 0;
  line-height: 1.5;
  min-height: 42px;
}

.template-tags {
  margin-bottom: 16px;
  min-height: 28px;
}

.template-meta {
  display: flex;
  gap: 16px;
  font-size: 13px;
  color: #64748b;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.yaml-preview {
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
</style>
