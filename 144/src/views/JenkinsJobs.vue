<template>
  <div class="jenkins-jobs">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>Jenkins 任务列表</span>
          <el-button type="primary" size="small" @click="refreshJobs">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
        </div>
      </template>

      <el-table :data="jenkinsStore.jobs" style="width: 100%">
        <el-table-column prop="name" label="任务名称" />
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.color)" size="small">
              {{ getStatusText(row.color) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="最后构建" width="120">
          <template #default="{ row }">
            <span v-if="row.lastBuild">#{{ row.lastBuild.number }}</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="构建结果" width="120">
          <template #default="{ row }">
            <el-tag v-if="row.lastBuild" :type="getResultType(row.lastBuild.result)" size="small">
              {{ row.lastBuild.result }}
            </el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="280">
          <template #default="{ row }">
            <el-button size="small" @click="showBuildDialog(row)">
              <el-icon><VideoPlay /></el-icon>
              构建
            </el-button>
            <el-button size="small" @click="viewDetails(row)">
              <el-icon><View /></el-icon>
              详情
            </el-button>
            <el-button size="small" @click="viewConsole(row)">
              <el-icon><Document /></el-icon>
              日志
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog
      v-model="buildDialogVisible"
      title="参数化构建"
      width="600px"
    >
      <el-form :model="buildParams" label-width="120px">
        <el-form-item label="任务名称">
          <el-input v-model="selectedJob.name" disabled />
        </el-form-item>
        <div v-if="jobParams.length === 0">
          <el-alert
            title="此任务无构建参数"
            type="info"
            :closable="false"
          />
        </div>
        <div v-else>
          <el-form-item
            v-for="param in jobParams"
            :key="param.name"
            :label="param.name"
          >
            <el-input
              v-if="param.type === 'StringParameterDefinition'"
              v-model="buildParams[param.name]"
              :placeholder="param.defaultValue || ''"
            />
            <el-select
              v-else-if="param.type === 'ChoiceParameterDefinition'"
              v-model="buildParams[param.name]"
              style="width: 100%"
            >
              <el-option
                v-for="choice in param.choices"
                :key="choice"
                :label="choice"
                :value="choice"
              />
            </el-select>
            <el-input
              v-else-if="param.type === 'TextParameterDefinition'"
              v-model="buildParams[param.name]"
              type="textarea"
              :rows="3"
            />
            <el-checkbox
              v-else-if="param.type === 'BooleanParameterDefinition'"
              v-model="buildParams[param.name]"
            >
              {{ param.name }}
            </el-checkbox>
            <el-input v-else v-model="buildParams[param.name]" />
          </el-form-item>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="buildDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmBuild">开始构建</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="consoleVisible"
      title="控制台输出"
      width="800px"
    >
      <el-input
        v-model="consoleOutput"
        type="textarea"
        :rows="20"
        readonly
        style="font-family: monospace; font-size: 12px"
      />
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { useJenkinsStore } from '@/stores/jenkins'

const jenkinsStore = useJenkinsStore()

const buildDialogVisible = ref(false)
const consoleVisible = ref(false)
const selectedJob = ref({})
const buildParams = reactive({})
const jobParams = ref([])
const consoleOutput = ref('')

const getStatusType = (color) => {
  if (color.includes('anime')) return 'warning'
  if (color === 'blue') return 'success'
  if (color === 'red') return 'danger'
  return 'info'
}

const getStatusText = (color) => {
  if (color.includes('anime')) return '构建中'
  if (color === 'blue') return '成功'
  if (color === 'red') return '失败'
  return '未知'
}

const getResultType = (result) => {
  if (result === 'SUCCESS') return 'success'
  if (result === 'FAILURE') return 'danger'
  return 'info'
}

const refreshJobs = async () => {
  ElMessage.success('任务列表已刷新')
}

const showBuildDialog = async (job) => {
  selectedJob.value = job
  Object.keys(buildParams).forEach(key => delete buildParams[key])
  
  jobParams.value = [
    { name: 'ENV', type: 'ChoiceParameterDefinition', defaultValue: 'dev', choices: ['dev', 'test', 'prod'] },
    { name: 'BRANCH', type: 'StringParameterDefinition', defaultValue: 'main' },
    { name: 'DEBUG', type: 'BooleanParameterDefinition', defaultValue: true },
    { name: 'NOTES', type: 'TextParameterDefinition', defaultValue: '' }
  ]
  
  jobParams.value.forEach(param => {
    buildParams[param.name] = param.defaultValue
  })
  
  buildDialogVisible.value = true
}

const confirmBuild = async () => {
  const success = await jenkinsStore.buildJob(selectedJob.value.name, buildParams)
  if (success) {
    ElMessage.success('构建已触发')
    buildDialogVisible.value = false
  } else {
    ElMessage.error('构建触发失败')
  }
}

const viewDetails = (job) => {
  ElMessage.info(`查看 ${job.name} 详情`)
}

const viewConsole = async (job) => {
  consoleOutput.value = `Started by user admin\nRunning in Durability level: MAX_SURVIVABILITY\n[Pipeline] Start of Pipeline\n[Pipeline] node\nRunning on Jenkins in /var/jenkins_home/workspace/frontend-app\n[Pipeline] {\n[Pipeline] stage\n[Pipeline] { (Checkout)\n[Pipeline] checkout\nCloning the remote Git repository\nCloning repository https://github.com/example/frontend-app.git\n\n[Pipeline] }\n[Pipeline] // stage\n[Pipeline] stage\n[Pipeline] { (Build)\n[Pipeline] sh\n+ npm install\n\nadded 1234 packages in 45s\n\n+ npm run build\n\n> frontend-app@1.0.0 build\n> vite build\n\nvite v5.0.0 building for production...\n✓ 345 modules transformed.\ndist/index.html                  0.48 kB\ndist/assets/index-xxxx.js    156.23 kB\n✓ built in 2.3s\n\n[Pipeline] }\n[Pipeline] // stage\n[Pipeline] stage\n[Pipeline] { (Deploy)\n[Pipeline] sh\n+ docker build -t frontend-app:latest .\n\nSuccessfully built 123456789abc\n\n[Pipeline] }\n[Pipeline] // stage\n[Pipeline] }\n[Pipeline] // node\n[Pipeline] End of Pipeline\nFinished: SUCCESS`
  
  consoleVisible.value = true
}
</script>

<style scoped>
.jenkins-jobs {
  height: 100%;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
