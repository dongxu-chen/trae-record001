<template>
  <main class="canvas-area">
    <div
      ref="canvasContainerRef"
      class="canvas-container"
      @dragover.prevent="handleDragOver"
      @drop="handleDrop"
    >
      <div v-if="fieldList.length === 0" class="empty-canvas">
        <el-icon class="empty-icon"><Plus /></el-icon>
        <p>将左侧组件拖拽到此处</p>
      </div>
      
      <draggable
        v-else
        v-model="localFieldList"
        item-key="id"
        class="field-list"
        ghost-class="ghost-item"
        drag-class="drag-item"
        chosen-class="chosen-item"
        animation="200"
        group="fields"
        @change="handleDragChange"
      >
        <template #item="{ element, index }">
          <div
            v-if="isFieldVisible(element)"
            :data-index="index"
            class="field-item"
            :class="{ 
              'selected': selectedFieldId === element.id, 
              'grid-item': element.type === 'grid',
              'hidden-by-expression': !isFieldVisible(element)
            }"
            @click="handleSelectField(element)"
          >
            <div class="field-header">
              <span class="field-label">{{ element.props.label }}</span>
              <div class="field-actions">
                <el-button
                  v-if="element.type === 'grid'"
                  type="primary"
                  size="small"
                  icon="Plus"
                  circle
                  @click.stop="addGridColumn(element)"
                />
                <el-button
                  type="danger"
                  size="small"
                  icon="Delete"
                  circle
                  @click.stop="handleRemoveField(element.id)"
                />
              </div>
            </div>
            
            <div v-if="element.type === 'grid'" class="grid-container">
              <div class="grid-row">
                <draggable
                  v-for="(column, colIndex) in element.children"
                  :key="colIndex"
                  v-model="element.children[colIndex].fields"
                  item-key="id"
                  class="grid-column"
                  :class="`col-${column.span || 6}`"
                  :group="{ name: 'gridFields', pull: true, put: true }"
                  animation="200"
                  ghost-class="ghost-item"
                  @change="(evt) => handleGridDragChange(evt, element, colIndex)"
                >
                  <template #item="{ element: subField }">
                    <div
                      v-if="isFieldVisible(subField)"
                      class="sub-field-item"
                      :class="{ 'selected': selectedFieldId === subField.id }"
                      @click.stop="handleSelectField(subField)"
                    >
                      <div class="sub-field-header">
                        <span class="sub-field-label">{{ subField.props.label }}</span>
                        <el-button
                          type="danger"
                          size="small"
                          icon="Delete"
                          circle
                          @click.stop="handleRemoveSubField(element, colIndex, subField.id)"
                        />
                      </div>
                      <div class="field-preview">
                        <component :is="getPreviewComponent(subField.type)" v-bind="getPreviewProps(subField)" />
                      </div>
                    </div>
                  </template>
                  <template #header>
                    <div class="column-header">
                      <span>列 {{ colIndex + 1 }} ({{ column.span || 6 }}/12)</span>
                      <el-input-number
                        v-model="column.span"
                        :min="1"
                        :max="12"
                        size="small"
                        @change="updateGridColumn(element)"
                      />
                    </div>
                  </template>
                </draggable>
              </div>
            </div>
            
            <div v-else class="field-preview">
              <component :is="getPreviewComponent(element.type)" v-bind="getPreviewProps(element)" />
            </div>
            
            <div v-if="element.type !== 'grid'" class="field-type">
              {{ getFieldTypeLabel(element.type) }}
            </div>
          </div>
        </template>
      </draggable>
    </div>
  </main>
</template>

<script setup>
import { ref, computed, watch, nextTick, reactive } from 'vue'
import draggable from 'vuedraggable'
import { ElMessage } from 'element-plus'
import { generateFieldId } from './config/componentConfig.js'
import { expressionEngine } from './utils/expressionEngine.js'

const props = defineProps({
  fieldList: {
    type: Array,
    default: () => []
  },
  draggingComponent: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['update:fieldList', 'select-field', 'remove-field'])

const canvasContainerRef = ref(null)
const localFieldList = ref([])
const selectedFieldId = ref(null)
const dragOverIndex = ref(-1)
const previewFormData = reactive({})

watch(localFieldList, (fields) => {
  fields.forEach(field => {
    if (field.type !== 'grid' && previewFormData[field.id] === undefined) {
      previewFormData[field.id] = getDefaultValue(field)
    }
    if (field.type === 'grid' && field.children) {
      field.children.forEach(col => {
        col.fields?.forEach(subField => {
          if (previewFormData[subField.id] === undefined) {
            previewFormData[subField.id] = getDefaultValue(subField)
          }
        })
      })
    }
  })
}, { deep: true, immediate: true })

function getDefaultValue(field) {
  switch (field.type) {
    case 'checkbox': return []
    case 'switch': return false
    case 'number': return undefined
    case 'rate': return 0
    case 'slider': return 50
    default: return ''
  }
}

function isFieldVisible(field) {
  if (!field.props?.visibleExpression) {
    return true
  }
  return expressionEngine.evaluateCondition(field.props.visibleExpression, { formData: previewFormData })
}

watch(() => props.fieldList, (newVal) => {
  localFieldList.value = JSON.parse(JSON.stringify(newVal))
}, { immediate: true, deep: true })

watch(localFieldList, (newVal) => {
  emit('update:fieldList', JSON.parse(JSON.stringify(newVal)))
}, { deep: true })

function handleDragOver(event) {
  event.dataTransfer.dropEffect = 'copy'
  
  const rect = canvasContainerRef.value?.getBoundingClientRect()
  if (!rect) return
  
  const y = event.clientY - rect.top
  const fieldItems = document.querySelectorAll('.field-item')
  
  let insertIndex = fieldItems.length
  fieldItems.forEach((item, index) => {
    const itemRect = item.getBoundingClientRect()
    const itemMiddle = itemRect.top - rect.top + itemRect.height / 2
    if (y < itemMiddle) {
      insertIndex = index
      return false
    }
  })
  
  dragOverIndex.value = insertIndex
}

function handleDrop(event) {
  event.preventDefault()
  event.stopPropagation()
  
  const componentData = event.dataTransfer.getData('text/plain')
  if (!componentData) return
  
  try {
    const component = JSON.parse(componentData)
    
    const newField = {
      id: generateFieldId(),
      type: component.type,
      props: { ...component.defaultProps }
    }
    
    if (component.type === 'grid') {
      newField.children = [
        { span: 6, fields: [] },
        { span: 6, fields: [] }
      ]
    }
    
    const insertIndex = dragOverIndex.value >= 0 && dragOverIndex.value <= localFieldList.value.length
      ? dragOverIndex.value
      : localFieldList.value.length
    
    localFieldList.value.splice(insertIndex, 0, newField)
    
    ElMessage.success(`已添加${component.label}组件，位置：第${insertIndex + 1}个`)
  } catch (e) {
    console.error('解析拖拽数据失败', e)
    ElMessage.error('添加组件失败')
  }
  
  dragOverIndex.value = -1
}

function handleSelectField(field) {
  selectedFieldId.value = field.id
  emit('select-field', field)
}

function handleRemoveField(fieldId) {
  const index = localFieldList.value.findIndex(f => f.id === fieldId)
  if (index > -1) {
    localFieldList.value.splice(index, 1)
    if (selectedFieldId.value === fieldId) {
      selectedFieldId.value = null
    }
    emit('remove-field', fieldId)
    ElMessage.success('已删除组件')
  }
}

function handleRemoveSubField(gridField, colIndex, fieldId) {
  const colFields = gridField.children[colIndex].fields
  const index = colFields.findIndex(f => f.id === fieldId)
  if (index > -1) {
    colFields.splice(index, 1)
    if (selectedFieldId.value === fieldId) {
      selectedFieldId.value = null
    }
    ElMessage.success('已删除子组件')
  }
}

function handleDragChange(evt) {
  nextTick(() => {
    if (evt.added) {
      ElMessage.info(`组件已移动到第${evt.added.newIndex + 1}位`)
    }
  })
}

function handleGridDragChange(evt, gridField, colIndex) {
  nextTick(() => {
    if (evt.added) {
      ElMessage.info(`子组件已移动到列${colIndex + 1}第${evt.added.newIndex + 1}位`)
    }
  })
}

function addGridColumn(gridField) {
  if (gridField.children.length < 4) {
    gridField.children.push({ span: 3, fields: [] })
    ElMessage.success('已添加栅格列')
  } else {
    ElMessage.warning('最多支持4列')
  }
}

function updateGridColumn(gridField) {
  const totalSpan = gridField.children.reduce((sum, col) => sum + (col.span || 0), 0)
  if (totalSpan > 12) {
    ElMessage.warning('总列宽不能超过12')
  }
}

function getPreviewComponent(type) {
  const componentMap = {
    input: 'el-input',
    textarea: 'el-input',
    number: 'el-input-number',
    radio: 'el-radio-group',
    checkbox: 'el-checkbox-group',
    select: 'el-select',
    date: 'el-date-picker',
    time: 'el-time-picker',
    switch: 'el-switch',
    rate: 'el-rate',
    slider: 'el-slider'
  }
  return componentMap[type] || 'el-input'
}

function getPreviewProps(field) {
  const props = { disabled: true, size: 'small' }
  const type = field.type
  const fieldProps = field.props
  
  if (type === 'textarea') {
    props.type = 'textarea'
    props.rows = fieldProps.rows
  }
  if (fieldProps.placeholder) {
    props.placeholder = fieldProps.placeholder
  }
  if (type === 'radio' || type === 'checkbox' || type === 'select') {
    props.options = fieldProps.options
  }
  if (type === 'number') {
    props.min = fieldProps.min
    props.max = fieldProps.max
  }
  if (type === 'rate') {
    props.max = fieldProps.max
  }
  if (type === 'slider') {
    props.min = fieldProps.min
    props.max = fieldProps.max
  }
  if (type === 'date') {
    props.type = 'date'
    props.format = 'YYYY-MM-DD'
  }
  if (type === 'time') {
    props.format = 'HH:mm:ss'
  }
  return props
}

function getFieldTypeLabel(type) {
  const labelMap = {
    input: '输入框',
    textarea: '文本域',
    number: '数字输入框',
    radio: '单选框',
    checkbox: '多选框',
    select: '下拉选择',
    date: '日期选择器',
    time: '时间选择器',
    switch: '开关',
    rate: '评分',
    slider: '滑块',
    grid: '栅格布局'
  }
  return labelMap[type] || type
}
</script>

<style scoped>
.canvas-area {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
}

.canvas-container {
  min-height: 100%;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  padding: 20px;
}

.empty-canvas {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 400px;
  color: #909399;
  border: 2px dashed #dcdfe6;
  border-radius: 8px;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.empty-canvas p {
  font-size: 16px;
}

.field-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.field-item {
  border: 2px solid #e4e7ed;
  border-radius: 8px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.2s;
  position: relative;
}

.field-item:hover {
  border-color: #409eff;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.2);
}

.field-item.selected {
  border-color: #409eff;
  background: #ecf5ff;
}

.field-item.grid-item {
  background: #f0f9ff;
  border-color: #67c23a;
}

.field-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.field-label {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
}

.field-actions {
  display: flex;
  gap: 8px;
}

.field-preview {
  margin-bottom: 8px;
}

.field-type {
  font-size: 12px;
  color: #909399;
}

.grid-container {
  margin-top: 12px;
  padding: 12px;
  background: #fff;
  border-radius: 4px;
  border: 1px dashed #dcdfe6;
}

.grid-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.grid-column {
  min-height: 80px;
  background: #f5f7fa;
  border-radius: 4px;
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.col-1 { width: calc(8.333% - 12px); }
.col-2 { width: calc(16.666% - 12px); }
.col-3 { width: calc(25% - 12px); }
.col-4 { width: calc(33.333% - 12px); }
.col-5 { width: calc(41.666% - 12px); }
.col-6 { width: calc(50% - 12px); }
.col-7 { width: calc(58.333% - 12px); }
.col-8 { width: calc(66.666% - 12px); }
.col-9 { width: calc(75% - 12px); }
.col-10 { width: calc(83.333% - 12px); }
.col-11 { width: calc(91.666% - 12px); }
.col-12 { width: 100%; }

.column-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  color: #909399;
  padding-bottom: 8px;
  border-bottom: 1px solid #e4e7ed;
}

.sub-field-item {
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  padding: 8px;
  background: #fff;
}

.sub-field-item.selected {
  border-color: #409eff;
  background: #ecf5ff;
}

.sub-field-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.sub-field-label {
  font-size: 12px;
  font-weight: 500;
  color: #606266;
}

.ghost-item {
  opacity: 0.5;
  background: #c8e8ff;
}

.drag-item {
  opacity: 0.8;
}

.chosen-item {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
}
</style>
