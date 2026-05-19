<template>
  <div class="form-view">
    <div class="page-header">
      <h2>{{ form.name }}</h2>
      <el-button type="primary" @click="submitForm" :loading="submitting">提交</el-button>
    </div>
    
    <el-card>
      <p style="color: #909399; margin-bottom: 20px">{{ form.description }}</p>
      <el-form ref="formRef" :model="formData" label-width="120px">
        <el-form-item
          v-for="field in form.fields"
          :key="field.id"
          :label="field.label"
          :required="field.is_required"
        >
          <component
            :is="getFieldComponent(field.type)"
            v-model="formData[field.name]"
            :options="field.options"
            style="width: 100%"
          />
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const route = useRoute()
const formRef = ref(null)
const submitting = ref(false)
const form = ref({ name: '', description: '', fields: [] })
const formData = ref({})

const getFieldComponent = (type) => {
  const components = {
    text: 'el-input',
    textarea: 'el-input',
    number: 'el-input-number',
    select: 'el-select',
    radio: 'el-radio-group',
    checkbox: 'el-checkbox-group',
    date: 'el-date-picker',
    switch: 'el-switch'
  }
  return components[type] || 'el-input'
}

onMounted(() => {
  loadForm()
})

const loadForm = async () => {
  try {
    const response = await axios.get(`/forms/${route.params.id}`)
    form.value = response.data
    response.data.fields.forEach(field => {
      formData.value[field.name] = ''
    })
  } catch (error) {
    ElMessage.error('加载表单失败')
  }
}

const submitForm = async () => {
  submitting.value = true
  try {
    await axios.post(`/forms/${route.params.id}/submit`, { data: formData.value })
    ElMessage.success('提交成功')
  } catch (error) {
    ElMessage.error('提交失败')
  } finally {
    submitting.value = false
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
</style>
