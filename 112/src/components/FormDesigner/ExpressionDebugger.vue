<template>
  <div class="expression-debugger">
    <div class="debugger-header">
      <span>表达式调试</span>
      <el-button size="small" @click="toggleCollapse">
        {{ collapsed ? '展开' : '收起' }}
      </el-button>
    </div>
    
    <div v-if="!collapsed" class="debugger-content">
      <div class="section">
        <h4>测试表达式</h4>
        <el-input
          v-model="testExpression"
          type="textarea"
          :rows="2"
          placeholder="输入表达式，例如: formData.field1 === 'test'"
        />
        <el-button type="primary" size="small" @click="evaluateExpression" style="margin-top: 8px">
          计算
        </el-button>
      </div>

      <div class="section result-section">
        <h4>计算结果</h4>
        <div class="result-box" :class="{ error: !evaluationResult.valid }">
          {{ evaluationResult.result }}
        </div>
        <div v-if="evaluationResult.dependencies.length > 0" class="dependencies">
          <span>依赖字段:</span>
          <el-tag v-for="dep in evaluationResult.dependencies" :key="dep" size="small" style="margin-left: 4px">
            {{ dep }}
          </el-tag>
        </div>
      </div>

      <div class="section">
        <h4>表单数据 (模拟)</h4>
        <div class="form-data-editor">
          <div v-for="field in allFields" :key="field.id" class="field-row">
            <span class="field-name">{{ field.props.label || field.id }}:</span>
            <component
              :is="getEditorComponent(field.type)"
              v-model="mockFormData[field.id]"
              v-bind="getEditorProps(field)"
              size="small"
              @change="onFieldChange"
            />
          </div>
        </div>
      </div>

      <div class="section">
        <h4>字段显隐状态</h4>
        <div class="visibility-list">
          <div v-for="field in allFields" :key="field.id" class="visibility-item">
            <span class="field-label">{{ field.props.label || field.id }}</span>
            <el-tag :type="getFieldVisibility(field) ? 'success' : 'info'" size="small">
              {{ getFieldVisibility(field) ? '显示' : '隐藏' }}
            </el-tag>
            <div v-if="field.props.visibleExpression" class="expression-preview">
              <small>{{ field.props.visibleExpression }}</small>
            </div>
          </div>
        </div>
      </div>

      <div class="section">
        <h4>表达式示例</h4>
        <ul class="examples">
          <li @click="useExample('formData.field1 === \'value\'')">
            等于: formData.field1 === 'value'
          </li>
          <li @click="useExample('formData.field1 !== \'value\'')">
            不等于: formData.field1 !== 'value'
          </li>
          <li @click="useExample('formData.field1 > 10 && formData.field2 < 100')">
            范围: formData.field1 > 10 && formData.field2 < 100
          </li>
          <li @click="useExample('formData.field1 && formData.field2')">
            逻辑与: formData.field1 && formData.field2
          </li>
          <li @click="useExample('formData.field1 || formData.field2')">
            逻辑或: formData.field1 || formData.field2
          </li>
          <li @click="useExample('formData.checkbox.includes(\'option1\')')">
            包含: formData.checkbox.includes('option1')
          </li>
          <li @click="useExample('value === formData.password')">
            校验示例 (自定义校验): value === formData.password
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, reactive, watch } from 'vue'
import { expressionEngine } from './utils/expressionEngine.js'

const props = defineProps({
  fieldList: {
    type: Array,
    default: () => []
  }
})

const collapsed = ref(false)
const testExpression = ref('')
const mockFormData = reactive({})

const allFields = computed(() => {
  const fields = []
  props.fieldList.forEach(field => {
    if (field.type === 'grid') {
      field.children?.forEach(col => {
        col.fields?.forEach(subField => fields.push(subField))
      })
    } else {
      fields.push(field)
    }
  })
  return fields
})

const evaluationResult = ref({
  result: '',
  valid: true,
  dependencies: []
})

watch(() => props.fieldList, (newFields) => {
  newFields.forEach(field => {
    if (field.type !== 'grid' && mockFormData[field.id] === undefined) {
      mockFormData[field.id] = getDefaultValue(field)
    }
    if (field.type === 'grid' && field.children) {
      field.children.forEach(col => {
        col.fields?.forEach(subField => {
          if (mockFormData[subField.id] === undefined) {
            mockFormData[subField.id] = getDefaultValue(subField)
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

function getEditorComponent(type) {
  const map = {
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
  return map[type] || 'el-input'
}

function getEditorProps(field) {
  const props = { size: 'small' }
  const type = field.type
  const fieldProps = field.props || {}
  
  if (type === 'textarea') {
    props.type = 'textarea'
    props.rows = 2
  }
  if (fieldProps.placeholder) {
    props.placeholder = fieldProps.placeholder
  }
  if ((type === 'radio' || type === 'checkbox') && fieldProps.options) {
    props.options = fieldProps.options
  }
  if (type === 'select') {
    props.options = fieldProps.options
  }
  if (type === 'date') {
    props.type = 'date'
    props.format = 'YYYY-MM-DD'
    props.valueFormat = 'YYYY-MM-DD'
  }
  if (type === 'time') {
    props.format = 'HH:mm:ss'
    props.valueFormat = 'HH:mm:ss'
  }
  if (type === 'rate') {
    props.max = fieldProps.max || 5
  }
  if (type === 'slider') {
    props.min = fieldProps.min || 0
    props.max = fieldProps.max || 100
  }
  
  return props
}

function evaluateExpression() {
  if (!testExpression.value.trim()) {
    evaluationResult.value = {
      result: '请输入表达式',
      valid: false,
      dependencies: []
    }
    return
  }
  
  try {
    const result = expressionEngine.evaluate(testExpression.value, { formData: mockFormData })
    const dependencies = expressionEngine.extractDependencies(testExpression.value)
    evaluationResult.value = {
      result: String(result),
      valid: true,
      dependencies
    }
  } catch (error) {
    evaluationResult.value = {
      result: `错误: ${error.message}`,
      valid: false,
      dependencies: expressionEngine.extractDependencies(testExpression.value)
    }
  }
}

function onFieldChange() {
  if (testExpression.value.trim()) {
    evaluateExpression()
  }
}

function getFieldVisibility(field) {
  if (!field.props?.visibleExpression) {
    return true
  }
  return expressionEngine.evaluateCondition(field.props.visibleExpression, { formData: mockFormData })
}

function useExample(expr) {
  testExpression.value = expr
  evaluateExpression()
}

function toggleCollapse() {
  collapsed.value = !collapsed.value
}
</script>

<style scoped>
.expression-debugger {
  background: #f5f7fa;
  border-top: 1px solid #e4e7ed;
}

.debugger-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  font-weight: 500;
  color: #303133;
}

.debugger-content {
  padding: 16px;
  max-height: 400px;
  overflow-y: auto;
}

.section {
  margin-bottom: 20px;
}

.section:last-child {
  margin-bottom: 0;
}

.section h4 {
  margin: 0 0 10px 0;
  font-size: 13px;
  color: #606266;
  font-weight: 500;
}

.result-box {
  padding: 10px;
  background: #f0f9eb;
  border: 1px solid #e1f3d8;
  border-radius: 4px;
  font-family: 'Consolas', monospace;
  font-size: 13px;
  color: #67c23a;
}

.result-box.error {
  background: #fef0f0;
  border-color: #fde2e2;
  color: #f56c6c;
}

.dependencies {
  margin-top: 8px;
  font-size: 12px;
  color: #909399;
}

.form-data-editor {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 12px;
}

.field-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.field-name {
  font-size: 12px;
  color: #606266;
  min-width: 80px;
  flex-shrink: 0;
}

.visibility-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.visibility-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px;
  background: #fff;
  border-radius: 4px;
}

.field-label {
  font-size: 13px;
  color: #303133;
  flex: 1;
}

.expression-preview {
  flex: 1;
  text-align: right;
}

.expression-preview small {
  color: #909399;
  font-family: 'Consolas', monospace;
}

.examples {
  list-style: none;
  padding: 0;
  margin: 0;
}

.examples li {
  padding: 6px 10px;
  background: #fff;
  border-radius: 4px;
  margin-bottom: 4px;
  cursor: pointer;
  font-family: 'Consolas', monospace;
  font-size: 12px;
  color: #409eff;
  transition: all 0.2s;
}

.examples li:hover {
  background: #ecf5ff;
  color: #66b1ff;
}
</style>
