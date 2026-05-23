export const componentTypes = [
  { type: 'input', label: '单行输入', icon: '📝' },
  { type: 'textarea', label: '多行输入', icon: '📄' },
  { type: 'radio', label: '单选框', icon: '🔘' },
  { type: 'checkbox', label: '复选框', icon: '☑️' },
  { type: 'date', label: '日期选择', icon: '📅' },
  { type: 'select', label: '下拉选择', icon: '📋' },
  { type: 'number', label: '数字输入', icon: '🔢' }
]

export const defaultOptions = [
  { label: '选项1', value: 'option1' },
  { label: '选项2', value: 'option2' },
  { label: '选项3', value: 'option3' }
]

export function createComponent(type) {
  const id = `field_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  const baseConfig = {
    id,
    type,
    label: componentTypes.find(c => c.type === type)?.label || '未命名',
    field: id,
    placeholder: '',
    defaultValue: '',
    required: false,
    validation: {
      pattern: '',
      minLength: null,
      maxLength: null,
      message: ''
    },
    linkage: {
      enabled: false,
      rules: []
    }
  }

  if (['radio', 'checkbox', 'select'].includes(type)) {
    baseConfig.options = JSON.parse(JSON.stringify(defaultOptions))
    baseConfig.dataSource = {
      type: 'static',
      url: '',
      method: 'GET',
      labelField: 'label',
      valueField: 'value'
    }
  }

  if (type === 'number') {
    baseConfig.min = null
    baseConfig.max = null
    baseConfig.step = 1
  }

  return baseConfig
}
