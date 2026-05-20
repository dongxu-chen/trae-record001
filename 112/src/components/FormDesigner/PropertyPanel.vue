<template>
  <aside class="property-panel">
    <h3>属性配置</h3>
    
    <div v-if="!selectedField" class="empty-panel">
      <p>请选择一个组件进行配置</p>
    </div>
    
    <div v-else class="property-content">
      <el-form label-width="80px" size="small">
        <el-form-item label="字段ID">
          <el-input v-model="localField.id" disabled />
        </el-form-item>
        
        <el-form-item label="组件类型">
          <el-input :value="getFieldTypeLabel(localField.type)" disabled />
        </el-form-item>
        
        <el-form-item label="标签名称">
          <el-input v-model="localField.props.label" placeholder="请输入标签名称" @input="handlePropChange" />
        </el-form-item>
        
        <el-form-item v-if="hasPlaceholder" label="占位文本">
          <el-input v-model="localField.props.placeholder" placeholder="请输入占位文本" @input="handlePropChange" />
        </el-form-item>
        
        <el-form-item v-if="hasRows" label="行数">
          <el-input-number v-model="localField.props.rows" :min="1" :max="20" @change="handlePropChange" />
        </el-form-item>
        
        <el-form-item v-if="hasRange" label="最小值">
          <el-input-number v-model="localField.props.min" @change="handlePropChange" />
        </el-form-item>
        
        <el-form-item v-if="hasRange" label="最大值">
          <el-input-number v-model="localField.props.max" @change="handlePropChange" />
        </el-form-item>
        
        <el-form-item v-if="hasLength" label="最小长度">
          <el-input-number v-model="localField.props.minLength" :min="0" @change="handlePropChange" />
        </el-form-item>
        
        <el-form-item v-if="hasLength" label="最大长度">
          <el-input-number v-model="localField.props.maxLength" :min="0" @change="handlePropChange" />
        </el-form-item>
        
        <el-form-item v-if="hasItemsRange" label="最小选择数">
          <el-input-number v-model="localField.props.minItems" :min="0" @change="handlePropChange" />
        </el-form-item>
        
        <el-form-item v-if="hasItemsRange" label="最大选择数">
          <el-input-number v-model="localField.props.maxItems" :min="0" @change="handlePropChange" />
        </el-form-item>
        
        <el-form-item v-if="hasPattern" label="正则校验">
          <el-input v-model="localField.props.pattern" placeholder="输入正则表达式" @input="handlePropChange" />
        </el-form-item>
        
        <el-form-item v-if="hasOptions" label="选项配置">
          <div class="options-editor">
            <div v-for="(option, index) in localField.props.options" :key="index" class="option-item">
              <el-input
                v-model="option.label"
                placeholder="选项标签"
                size="small"
                style="width: 45%"
                @input="handlePropChange"
              />
              <el-input
                v-model="option.value"
                placeholder="选项值"
                size="small"
                style="width: 45%"
                @input="handlePropChange"
              />
              <el-button
                type="danger"
                size="small"
                icon="Delete"
                circle
                @click="removeOption(index)"
              />
            </div>
            <el-button type="primary" size="small" @click="addOption" style="width: 100%; margin-top: 8px;">
              添加选项
            </el-button>
          </div>
        </el-form-item>
        
        <el-form-item v-if="hasGutter" label="栅格间距">
          <el-input-number v-model="localField.props.gutter" :min="0" :max="100" @change="handlePropChange" />
        </el-form-item>
        
        <el-form-item label="是否必填">
          <el-switch v-model="localField.props.required" @change="handlePropChange" />
        </el-form-item>

        <el-divider content-position="left">联动配置</el-divider>

        <el-form-item label="显隐表达式">
          <el-input
            v-model="localField.props.visibleExpression"
            type="textarea"
            :rows="2"
            placeholder="例如: formData.field1 === 'value'"
            @input="handlePropChange"
          />
          <div class="expression-hint">
            <small>使用 formData.字段名 引用其他字段值</small>
          </div>
        </el-form-item>

        <el-form-item v-if="['input', 'textarea', 'number'].includes(localField?.type)" label="自定义校验">
          <el-input
            v-model="localField.props.customValidator"
            type="textarea"
            :rows="2"
            placeholder="例如: value === formData.confirmPassword"
            @input="handlePropChange"
          />
          <div class="expression-hint">
            <small>使用 value 代表当前字段值，使用 formData.字段名 引用其他字段</small>
          </div>
        </el-form-item>

        <el-form-item v-if="['input', 'textarea', 'number'].includes(localField?.type)" label="校验提示">
          <el-input
            v-model="localField.props.validatorMessage"
            placeholder="校验失败时的提示信息"
            @input="handlePropChange"
          />
        </el-form-item>
      </el-form>
      
      <div class="panel-footer">
        <el-button type="primary" size="small" @click="applyChanges">应用更改</el-button>
        <el-button size="small" @click="resetChanges">重置</el-button>
      </div>
    </div>
  </aside>
</template>

<script setup>
import { ref, computed, watch, reactive } from 'vue'
import { ElMessage } from 'element-plus'

const props = defineProps({
  selectedField: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['update:field', 'field-change'])

const localField = ref(null)

watch(() => props.selectedField, (newVal) => {
  if (newVal) {
    localField.value = reactive(JSON.parse(JSON.stringify(newVal)))
  } else {
    localField.value = null
  }
}, { immediate: true, deep: true })

watch(() => localField.value, (newVal) => {
  if (newVal && props.selectedField) {
    emit('field-change', JSON.parse(JSON.stringify(newVal)))
  }
}, { deep: true })

const hasPlaceholder = computed(() => {
  return ['input', 'textarea', 'number', 'select', 'date', 'time'].includes(localField.value?.type)
})

const hasRows = computed(() => {
  return localField.value?.type === 'textarea'
})

const hasRange = computed(() => {
  return ['number', 'slider', 'rate'].includes(localField.value?.type)
})

const hasLength = computed(() => {
  return ['input', 'textarea'].includes(localField.value?.type)
})

const hasItemsRange = computed(() => {
  return localField.value?.type === 'checkbox'
})

const hasPattern = computed(() => {
  return ['input', 'textarea'].includes(localField.value?.type)
})

const hasOptions = computed(() => {
  return ['radio', 'checkbox', 'select'].includes(localField.value?.type)
})

const hasGutter = computed(() => {
  return localField.value?.type === 'grid'
})

function handlePropChange() {
  if (localField.value && props.selectedField) {
    emit('update:field', JSON.parse(JSON.stringify(localField.value)))
  }
}

function addOption() {
  if (localField.value?.props?.options) {
    const index = localField.value.props.options.length + 1
    localField.value.props.options.push({
      label: `选项${index}`,
      value: `option${index}`
    })
    handlePropChange()
  }
}

function removeOption(index) {
  if (localField.value?.props?.options && localField.value.props.options.length > 1) {
    localField.value.props.options.splice(index, 1)
    handlePropChange()
  } else {
    ElMessage.warning('至少保留一个选项')
  }
}

function applyChanges() {
  if (localField.value) {
    emit('update:field', JSON.parse(JSON.stringify(localField.value)))
    ElMessage.success('属性已更新')
  }
}

function resetChanges() {
  if (props.selectedField) {
    localField.value = reactive(JSON.parse(JSON.stringify(props.selectedField)))
    ElMessage.info('已重置')
  }
}

function getFieldTypeLabel(type) {
  const labelMap = {
    grid: '栅格布局',
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
    slider: '滑块'
  }
  return labelMap[type] || type
}
</script>

<style scoped>
.property-panel {
  width: 320px;
  background: #fff;
  border-left: 1px solid #e4e7ed;
  padding: 16px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

.property-panel h3 {
  font-size: 16px;
  color: #303133;
  margin-bottom: 16px;
  padding-bottom: 8px;
  border-bottom: 1px solid #ebeef5;
  flex-shrink: 0;
}

.empty-panel {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #909399;
  font-size: 14px;
}

.property-content {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.options-editor {
  width: 100%;
}

.option-item {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
  align-items: center;
}

.panel-footer {
  display: flex;
  gap: 8px;
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid #ebeef5;
  flex-shrink: 0;
}

.expression-hint {
  margin-top: 4px;
  color: #909399;
  line-height: 1.4;
}
</style>
