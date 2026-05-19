<template>
  <div class="form-designer">
    <header class="designer-header">
      <h1>可视化表单设计器</h1>
      <div class="header-actions">
        <el-button type="primary" @click="previewForm">预览表单</el-button>
        <el-button type="success" @click="generateSchema">生成JSON</el-button>
        <el-button @click="clearCanvas">清空画布</el-button>
      </div>
    </header>
    
    <div class="designer-main">
      <div class="designer-content">
        <ComponentLibrary @drag-start="handleDragStart" />
        
        <CanvasArea
          :field-list="fieldList"
          :dragging-component="draggingComponent"
          @update:field-list="handleFieldListUpdate"
          @select-field="handleSelectField"
          @remove-field="handleRemoveField"
        />
        
        <PropertyPanel
          :selected-field="selectedField"
          @update:field="handleUpdateField"
          @field-change="handleFieldChange"
        />
      </div>
      
      <ExpressionDebugger :field-list="fieldList" />
    </div>
    
    <el-dialog v-model="previewVisible" title="表单预览" width="700px">
      <FormPreview :schema="formSchema" />
    </el-dialog>
    
    <el-dialog v-model="schemaVisible" title="JSON Schema" width="800px">
      <el-input
        v-model="schemaJson"
        type="textarea"
        :rows="25"
        readonly
        class="schema-textarea"
      />
      <template #footer>
        <el-button @click="copySchema">复制</el-button>
        <el-button @click="downloadSchema">下载</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, reactive } from 'vue'
import ComponentLibrary from './ComponentLibrary.vue'
import CanvasArea from './CanvasArea.vue'
import PropertyPanel from './PropertyPanel.vue'
import FormPreview from './FormPreview.vue'
import ExpressionDebugger from './ExpressionDebugger.vue'
import { ElMessage } from 'element-plus'

const fieldList = ref([])
const selectedField = ref(null)
const draggingComponent = ref(null)
const previewVisible = ref(false)
const schemaVisible = ref(false)
const schemaJson = ref('')

const formSchema = computed(() => {
  const properties = {}
  const required = []
  
  function processField(field) {
    if (field.type === 'grid') {
      field.children?.forEach(col => {
        col.fields?.forEach(subField => processField(subField))
      })
    } else {
      const fieldProps = field.props || {}
      const schema = {
        type: getSchemaType(field.type),
        title: fieldProps.label || field.id,
        ...generateValidationRules(field)
      }
      
      if (fieldProps.options) {
        schema.enum = fieldProps.options.map(opt => opt.value)
      }
      
      properties[field.id] = schema
      
      if (fieldProps.required) {
        required.push(field.id)
      }
    }
  }
  
  fieldList.value.forEach(field => processField(field))
  
  const result = {
    type: 'object',
    title: '表单配置',
    properties,
    fields: fieldList.value
  }
  
  if (required.length > 0) {
    result.required = required
  }
  
  return result
})

function getSchemaType(type) {
  const typeMap = {
    input: 'string',
    textarea: 'string',
    number: 'number',
    radio: 'string',
    checkbox: 'array',
    select: 'string',
    date: 'string',
    time: 'string',
    switch: 'boolean',
    rate: 'number',
    slider: 'number'
  }
  return typeMap[type] || 'string'
}

function generateValidationRules(field) {
  const rules = {}
  const props = field.props || {}
  
  if (props.min !== undefined) {
    rules.minimum = props.min
  }
  if (props.max !== undefined) {
    rules.maximum = props.max
  }
  if (props.minLength !== undefined) {
    rules.minLength = props.minLength
  }
  if (props.maxLength !== undefined) {
    rules.maxLength = props.maxLength
  }
  if (props.minItems !== undefined) {
    rules.minItems = props.minItems
  }
  if (props.maxItems !== undefined) {
    rules.maxItems = props.maxItems
  }
  if (props.pattern && props.pattern.trim()) {
    rules.pattern = props.pattern.trim()
  }
  if (props.format) {
    rules.format = props.format
  }
  
  return rules
}

function handleDragStart(component) {
  draggingComponent.value = component
}

function handleFieldListUpdate(list) {
  fieldList.value = list
}

function handleSelectField(field) {
  selectedField.value = field
}

function handleRemoveField(fieldId) {
  removeFieldById(fieldList.value, fieldId)
  if (selectedField.value?.id === fieldId) {
    selectedField.value = null
  }
}

function removeFieldById(list, fieldId) {
  const index = list.findIndex(f => f.id === fieldId)
  if (index > -1) {
    list.splice(index, 1)
    return true
  }
  for (const field of list) {
    if (field.children) {
      for (const col of field.children) {
        if (col.fields) {
          const subIndex = col.fields.findIndex(f => f.id === fieldId)
          if (subIndex > -1) {
            col.fields.splice(subIndex, 1)
            return true
          }
        }
      }
    }
  }
  return false
}

function handleUpdateField(updatedField) {
  updateFieldById(fieldList.value, updatedField)
  if (selectedField.value?.id === updatedField.id) {
    selectedField.value = reactive({ ...updatedField })
  }
}

function handleFieldChange(changedField) {
  updateFieldById(fieldList.value, changedField)
}

function updateFieldById(list, updatedField) {
  const index = list.findIndex(f => f.id === updatedField.id)
  if (index > -1) {
    list[index] = reactive(updatedField)
    return true
  }
  for (const field of list) {
    if (field.children) {
      for (const col of field.children) {
        if (col.fields) {
          const subIndex = col.fields.findIndex(f => f.id === updatedField.id)
          if (subIndex > -1) {
            col.fields[subIndex] = reactive(updatedField)
            return true
          }
        }
      }
    }
  }
  return false
}

function previewForm() {
  if (fieldList.value.length === 0) {
    ElMessage.warning('请先添加表单组件')
    return
  }
  previewVisible.value = true
}

function generateSchema() {
  schemaJson.value = JSON.stringify(formSchema.value, null, 2)
  schemaVisible.value = true
}

function copySchema() {
  navigator.clipboard.writeText(schemaJson.value)
  ElMessage.success('已复制到剪贴板')
}

function downloadSchema() {
  const blob = new Blob([schemaJson.value], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'form-schema.json'
  a.click()
  URL.revokeObjectURL(url)
  ElMessage.success('下载成功')
}

function clearCanvas() {
  fieldList.value = []
  selectedField.value = null
  ElMessage.success('画布已清空')
}
</script>

<style scoped>
.form-designer {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #f5f7fa;
}

.designer-header {
  height: 60px;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  flex-shrink: 0;
}

.designer-header h1 {
  font-size: 20px;
  color: #303133;
  font-weight: 500;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.designer-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.designer-content {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.schema-textarea {
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 13px;
}
</style>
