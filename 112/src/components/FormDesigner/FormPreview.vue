<template>
  <div class="form-preview">
    <el-form
      ref="formRef"
      :model="formData"
      :rules="formRules"
      label-width="100px"
      size="default"
    >
      <template v-for="field in flatFields" :key="field.id">
        <el-form-item
          v-if="field.type !== 'grid' && fieldVisibility[field.id] !== false"
          :label="field.props.label"
          :prop="field.id"
        >
          <component :is="getFormComponent(field.type)" v-bind="getComponentProps(field)" v-model="formData[field.id]" />
        </el-form-item>
      </template>
      
      <template v-for="(grid, gridIndex) in gridFields" :key="grid.id">
        <div class="grid-label">{{ grid.props.label }}</div>
        <el-row :gutter="grid.props.gutter || 20" class="grid-row">
          <el-col
                    v-for="(col, colIndex) in grid.children"
                    :key="colIndex"
                    :span="col.span || 6"
                  >
                    <el-form-item
                      v-for="subField in col.fields"
                      :key="subField.id"
                      v-if="fieldVisibility[subField.id] !== false"
                      :label="subField.props.label"
                      :prop="subField.id"
                    >
              <component :is="getFormComponent(subField.type)" v-bind="getComponentProps(subField)" v-model="formData[subField.id]" />
            </el-form-item>
          </el-col>
        </el-row>
      </template>
      
      <el-form-item>
        <el-button type="primary" @click="submitForm">提交</el-button>
        <el-button @click="resetForm">重置</el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup>
import { ref, computed, watch, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { expressionEngine } from './utils/expressionEngine.js'

const props = defineProps({
  schema: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['submit'])

const formRef = ref(null)
const formData = reactive({})
const formRules = reactive({})
const fieldVisibility = reactive({})
const expressionResults = ref([])

function updateFieldVisibility() {
  const fields = props.schema.fields || []
  
  function processField(field) {
    if (field.type === 'grid') {
      field.children?.forEach(col => {
        col.fields?.forEach(subField => processField(subField))
      })
    } else {
      const visible = !field.props?.visibleExpression || 
        expressionEngine.evaluateCondition(field.props.visibleExpression, { formData })
      fieldVisibility[field.id] = visible
    }
  }
  
  fields.forEach(field => processField(field))
}

watch(formData, () => {
  updateFieldVisibility()
}, { deep: true, immediate: true })

const flatFields = computed(() => {
  const fields = []
  props.schema.fields?.forEach(field => {
    if (field.type !== 'grid') {
      fields.push(field)
    }
  })
  return fields
})

const gridFields = computed(() => {
  return props.schema.fields?.filter(field => field.type === 'grid') || []
})

watch(() => props.schema, (newSchema) => {
  const fields = newSchema.fields || []
  const newFormData = {}
  const newRules = {}
  
  function processField(field) {
    if (field.type === 'grid') {
      field.children?.forEach(col => {
        col.fields?.forEach(subField => processField(subField))
      })
    } else {
      newFormData[field.id] = getDefaultValue(field)
      newRules[field.id] = generateFieldRules(field)
    }
  }
  
  fields.forEach(field => processField(field))
  
  Object.assign(formData, newFormData)
  Object.assign(formRules, newRules)
}, { immediate: true, deep: true })

function getDefaultValue(field) {
  const type = field.type
  switch (type) {
    case 'checkbox':
      return []
    case 'switch':
      return false
    case 'number':
    case 'rate':
    case 'slider':
      return undefined
    default:
      return ''
  }
}

function generateFieldRules(field) {
  const rules = []
  const props = field.props || {}
  
  if (props.required) {
    rules.push({
      required: true,
      message: `请${getPlaceholderText(field.type)}`,
      trigger: getTriggerType(field.type)
    })
  }
  
  if (props.minLength !== undefined) {
    rules.push({
      min: props.minLength,
      message: `最小长度为${props.minLength}`,
      trigger: 'blur'
    })
  }
  
  if (props.maxLength !== undefined) {
    rules.push({
      max: props.maxLength,
      message: `最大长度为${props.maxLength}`,
      trigger: 'blur'
    })
  }
  
  if (props.min !== undefined && ['number', 'slider', 'rate'].includes(field.type)) {
    rules.push({
      type: 'number',
      min: props.min,
      message: `最小值为${props.min}`,
      trigger: 'blur'
    })
  }
  
  if (props.max !== undefined && ['number', 'slider', 'rate'].includes(field.type)) {
    rules.push({
      type: 'number',
      max: props.max,
      message: `最大值为${props.max}`,
      trigger: 'blur'
    })
  }
  
  if (props.pattern && props.pattern.trim()) {
    rules.push({
      pattern: new RegExp(props.pattern.trim()),
      message: '格式不正确',
      trigger: 'blur'
    })
  }
  
  if (props.minItems !== undefined) {
    rules.push({
      type: 'array',
      min: props.minItems,
      message: `至少选择${props.minItems}项`,
      trigger: 'change'
    })
  }
  
  if (props.maxItems !== undefined) {
    rules.push({
      type: 'array',
      max: props.maxItems,
      message: `最多选择${props.maxItems}项`,
      trigger: 'change'
    })
  }
  
  if (props.customValidator && props.customValidator.trim()) {
    rules.push({
      validator: (rule, value, callback) => {
        try {
          const result = expressionEngine.evaluateCondition(props.customValidator, { 
            formData, 
            value, 
            fieldName: field.id 
          })
          if (result) {
            callback()
          } else {
            callback(new Error(props.validatorMessage || '自定义校验失败'))
          }
        } catch (error) {
          callback(new Error(`表达式错误: ${error.message}`))
        }
      },
      trigger: ['blur', 'change']
    })
  }
  
  return rules
}

function getPlaceholderText(type) {
  const placeholderMap = {
    input: '输入内容',
    textarea: '输入内容',
    number: '输入数字',
    radio: '选择选项',
    checkbox: '选择选项',
    select: '选择选项',
    date: '选择日期',
    time: '选择时间',
    switch: '开启开关',
    rate: '进行评分',
    slider: '拖动滑块'
  }
  return placeholderMap[type] || '填写内容'
}

function getTriggerType(type) {
  if (['radio', 'checkbox', 'select', 'switch', 'date', 'time', 'rate', 'slider'].includes(type)) {
    return 'change'
  }
  return 'blur'
}

function getFormComponent(type) {
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

function getComponentProps(field) {
  const props = {}
  const type = field.type
  const fieldProps = field.props || {}
  
  if (type === 'textarea') {
    props.type = 'textarea'
    props.rows = fieldProps.rows || 3
  }
  
  if (fieldProps.placeholder) {
    props.placeholder = fieldProps.placeholder
  }
  
  if (type === 'radio' && fieldProps.options) {
    props.options = fieldProps.options
  }
  
  if (type === 'checkbox' && fieldProps.options) {
    props.options = fieldProps.options
  }
  
  if (type === 'select') {
    props.clearable = true
  }
  
  if (type === 'date') {
    props.type = 'date'
    props.format = fieldProps.format || 'YYYY-MM-DD'
    props.valueFormat = fieldProps.format || 'YYYY-MM-DD'
  }
  
  if (type === 'time') {
    props.format = fieldProps.format || 'HH:mm:ss'
    props.valueFormat = fieldProps.format || 'HH:mm:ss'
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

async function submitForm() {
  if (!formRef.value) return
  
  try {
    await formRef.value.validate()
    ElMessage.success('表单提交成功')
    emit('submit', { ...formData })
    console.log('表单数据:', formData)
  } catch (error) {
    ElMessage.error('请检查表单填写是否正确')
    console.error('表单校验失败:', error)
  }
}

function resetForm() {
  if (formRef.value) {
    formRef.value.resetFields()
    ElMessage.info('表单已重置')
  }
}
</script>

<style scoped>
.form-preview {
  padding: 20px 0;
}

.grid-label {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #ebeef5;
}

.grid-row {
  margin-bottom: 20px;
}
</style>
