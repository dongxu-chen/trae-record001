<template>
  <div class="form-builder">
    <div class="page-header">
      <h2>{{ isEdit ? '编辑表单' : '新建表单' }}</h2>
      <div>
        <el-button @click="$router.back()">取消</el-button>
        <el-button type="primary" @click="saveForm()" :loading="saving">保存</el-button>
      </div>
    </div>
    
    <el-row :gutter="20">
      <el-col :span="4">
        <el-card class="field-palette">
          <template #header>字段库</template>
          <div v-for="field in fieldTypes" :key="field.type" class="field-item" draggable="true" @dragstart="onDragStart($event, field)">
            <el-icon><component :is="field.icon" /></el-icon>
            <span>{{ field.label }}</span>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="14">
        <el-card class="canvas">
          <template #header>
            <el-input v-model="formData.name" placeholder="表单名称" size="large" />
          </template>
          <div
            class="form-canvas"
            @dragover.prevent
            @drop="onDrop"
          >
            <div v-if="fields.length === 0" class="empty-state">
              <el-icon><Document /></el-icon>
              <p>从左侧拖拽字段到这里</p>
            </div>
            <draggable v-model="fields" item-key="name" class="field-list">
              <template #item="{ element, index }">
                <div class="canvas-field" @click="selectField(index)">
                  <div class="field-header">
                    <span class="field-label">{{ element.label }}</span>
                    <el-button link type="danger" size="small" @click.stop="removeField(index)">
                      <el-icon><Delete /></el-icon>
                    </el-button>
                  </div>
                  <div class="field-preview">
                    <component :is="getFieldComponent(element.type)" v-bind="element" />
                  </div>
                </div>
              </template>
            </draggable>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card class="field-config">
          <template #header>字段配置</template>
          <div v-if="selectedField !== null" class="config-panel">
            <el-form label-width="80px">
              <el-form-item label="字段标签">
                <el-input v-model="fields[selectedField].label" />
              </el-form-item>
              <el-form-item label="字段名称">
                <el-input v-model="fields[selectedField].name" />
              </el-form-item>
              <el-form-item label="是否必填">
                <el-switch v-model="fields[selectedField].is_required" />
              </el-form-item>
              <template v-if="hasOptions(fields[selectedField].type)">
                <el-form-item label="选项">
                  <div v-for="(option, idx) in fields[selectedField].options" :key="idx" class="option-item">
                    <el-input v-model="fields[selectedField].options[idx]" style="width: 80%" />
                    <el-button link type="danger" @click="removeOption(idx)">删除</el-button>
                  </div>
                  <el-button size="small" @click="addOption">+ 添加选项</el-button>
                </el-form-item>
              </template>
            </el-form>
          </div>
          <div v-else class="empty-config">
            <p>选择一个字段进行配置</p>
          </div>
        </el-card>
        
        <el-card class="flow-config" style="margin-top: 20px">
          <template #header>审批流程</template>
          <el-select v-model="formData.approval_flow_id" placeholder="选择审批流程" style="width: 100%">
            <el-option v-for="flow in approvalFlows" :key="flow.id" :label="flow.name" :value="flow.id" />
          </el-select>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import draggable from 'vuedraggable'
import { Document, Edit, Input, Calendar, Select, Switch, Delete, Plus } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const router = useRouter()
const route = useRoute()

const isEdit = computed(() => !!route.params.id)
const saving = ref(false)
const selectedField = ref(null)
const fields = ref([])
const approvalFlows = ref([])

const formData = ref({
  name: '',
  description: '',
  approval_flow_id: null
})

const fieldTypes = [
  { type: 'text', label: '单行文本', icon: Edit },
  { type: 'textarea', label: '多行文本', icon: Input },
  { type: 'number', label: '数字', icon: Input },
  { type: 'select', label: '下拉选择', icon: Select },
  { type: 'radio', label: '单选', icon: Select },
  { type: 'checkbox', label: '多选', icon: Select },
  { type: 'date', label: '日期', icon: Calendar },
  { type: 'switch', label: '开关', icon: Switch }
]

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

const hasOptions = (type) => {
  return ['select', 'radio', 'checkbox'].includes(type)
}

const onDragStart = (event, field) => {
  event.dataTransfer.setData('fieldType', JSON.stringify(field))
}

const onDrop = (event) => {
  const fieldData = JSON.parse(event.dataTransfer.getData('fieldType'))
  const newField = {
    type: fieldData.type,
    label: fieldData.label,
    name: `field_${Date.now()}`,
    is_required: false,
    options: hasOptions(fieldData.type) ? ['选项1', '选项2'] : null
  }
  fields.value.push(newField)
  selectedField.value = fields.value.length - 1
}

const removeField = (index) => {
  fields.value.splice(index, 1)
  if (selectedField.value === index) {
    selectedField.value = null
  }
}

const selectField = (index) => {
  selectedField.value = index
}

const addOption = () => {
  if (selectedField.value !== null) {
    fields.value[selectedField.value].options.push(`选项${fields.value[selectedField.value].options.length + 1}`)
  }
}

const removeOption = (index) => {
  if (selectedField.value !== null) {
    fields.value[selectedField.value].options.splice(index, 1)
  }
}

onMounted(async () => {
  await loadApprovalFlows()
  if (isEdit.value) {
    await loadForm()
  }
})

const loadApprovalFlows = async () => {
  try {
    const response = await axios.get('/approval-flows')
    approvalFlows.value = response.data.data || []
  } catch (error) {
    console.error('加载审批流程失败', error)
  }
}

const loadForm = async () => {
  try {
    const response = await axios.get(`/forms/${route.params.id}`)
    formData.value = {
      name: response.data.name,
      description: response.data.description,
      approval_flow_id: response.data.approval_flow_id
    }
    fields.value = response.data.fields || []
  } catch (error) {
    ElMessage.error('加载表单失败')
  }
}

const saveForm = async () => {
  if (!formData.value.name) {
    ElMessage.warning('请输入表单名称')
    return
  }
  if (fields.value.length === 0) {
    ElMessage.warning('请至少添加一个字段')
    return
  }

  saving.value = true
  try {
    const data = { ...formData.value, fields: fields.value }
    if (isEdit.value) {
      await axios.put(`/forms/${route.params.id}`, data)
    } else {
      await axios.post('/forms', data)
    }
    ElMessage.success('保存成功')
    router.push('/forms')
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

.field-palette .field-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  margin-bottom: 8px;
  cursor: move;
  transition: all 0.3s;
}

.field-palette .field-item:hover {
  border-color: #409EFF;
  background: #ecf5ff;
}

.form-canvas {
  min-height: 500px;
  padding: 20px;
  border: 2px dashed #dcdfe6;
  border-radius: 8px;
}

.empty-state {
  text-align: center;
  color: #909399;
  padding: 100px 0;
}

.empty-state .el-icon {
  font-size: 48px;
  margin-bottom: 10px;
}

.canvas-field {
  padding: 15px;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  margin-bottom: 10px;
  background: white;
  cursor: pointer;
  transition: all 0.3s;
}

.canvas-field:hover {
  border-color: #409EFF;
}

.canvas-field.selected {
  border-color: #409EFF;
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.2);
}

.field-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.field-label {
  font-weight: 500;
  color: #303133;
}

.field-preview {
  padding-left: 0;
}

.empty-config {
  text-align: center;
  color: #909399;
  padding: 50px 0;
}

.option-item {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
}
</style>
