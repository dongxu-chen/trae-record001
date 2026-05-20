<template>
  <div class="flow-form">
    <div class="page-header">
      <h2>{{ isEdit ? '编辑审批流程' : '新建审批流程' }}</h2>
      <div>
        <el-button @click="$router.back()">取消</el-button>
        <el-button type="primary" @click="saveFlow()" :loading="saving">保存</el-button>
      </div>
    </div>
    
    <el-card>
      <el-form label-width="100px">
        <el-form-item label="流程名称">
          <el-input v-model="formData.name" placeholder="请输入流程名称" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="formData.description" type="textarea" :rows="3" placeholder="请输入描述" />
        </el-form-item>
      </el-form>
      
      <div style="margin-top: 20px">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px">
          <h3>审批步骤</h3>
          <el-button size="small" type="primary" @click="addStep">
            <el-icon><Plus /></el-icon>
            添加步骤
          </el-button>
        </div>
        
        <div v-for="(step, index) in formData.steps" :key="index" class="step-item">
          <div class="step-header">
            <span class="step-number">第 {{ index + 1 }} 步</span>
            <el-button link type="danger" size="small" @click="removeStep(index)" v-if="formData.steps.length > 1">删除</el-button>
          </div>
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item label="步骤名称">
                <el-input v-model="step.name" placeholder="请输入步骤名称" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="审批人">
                <el-select v-model="step.approver_id" placeholder="选择审批人" style="width: 100%">
                  <el-option v-for="user in users" :key="user.id" :label="user.name" :value="user.id" />
                </el-select>
              </el-form-item>
            </el-col>
          </el-row>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { Plus } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const router = useRouter()
const route = useRoute()
const isEdit = computed(() => !!route.params.id)
const saving = ref(false)
const users = ref([])

const formData = ref({
  name: '',
  description: '',
  steps: [{ name: '', approver_id: null }]
})

onMounted(async () => {
  await loadUsers()
  if (isEdit.value) {
    await loadFlow()
  }
})

const loadUsers = async () => {
  try {
    const response = await axios.get('/tenant-users')
    users.value = response.data.data || []
  } catch (error) {
    console.error('加载用户失败', error)
  }
}

const loadFlow = async () => {
  try {
    const response = await axios.get(`/approval-flows/${route.params.id}`)
    formData.value = {
      name: response.data.name,
      description: response.data.description,
      steps: response.data.steps?.map(s => ({ name: s.name, approver_id: s.approver_id })) || []
    }
  } catch (error) {
    ElMessage.error('加载流程失败')
  }
}

const addStep = () => {
  formData.value.steps.push({ name: '', approver_id: null })
}

const removeStep = (index) => {
  formData.value.steps.splice(index, 1)
}

const saveFlow = async () => {
  if (!formData.value.name.trim()) {
    ElMessage.warning('请输入流程名称')
    return
  }
  if (formData.value.steps.some(s => !s.name.trim())) {
    ElMessage.warning('请填写所有步骤名称')
    return
  }
  if (formData.value.steps.some(s => !s.approver_id)) {
    ElMessage.warning('请选择所有步骤的审批人')
    return
  }

  saving.value = true
  try {
    if (isEdit.value) {
      await axios.put(`/approval-flows/${route.params.id}`, formData.value)
    } else {
      await axios.post('/approval-flows', formData.value)
    }
    ElMessage.success('保存成功')
    router.push('/approval-flows')
  } catch (error) {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0;
}

.step-item {
  padding: 15px;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  margin-bottom: 10px;
}

.step-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.step-number {
  font-weight: 500;
  color: #409EFF;
}
</style>
