import type { ComponentConfig } from '@/types/form'

export const componentConfigs: ComponentConfig[] = [
  {
    type: 'input',
    label: '单行输入',
    icon: 'type',
    category: 'basic',
    defaultProps: {
      placeholder: '请输入内容'
    }
  },
  {
    type: 'textarea',
    label: '多行输入',
    icon: 'align-left',
    category: 'basic',
    defaultProps: {
      placeholder: '请输入内容',
      rows: 4
    }
  },
  {
    type: 'number',
    label: '数字输入',
    icon: 'hash',
    category: 'basic',
    defaultProps: {
      placeholder: '请输入数字',
      min: undefined,
      max: undefined
    }
  },
  {
    type: 'select',
    label: '下拉选择',
    icon: 'chevron-down',
    category: 'basic',
    defaultProps: {
      placeholder: '请选择',
      options: [
        { label: '选项1', value: 'option1' },
        { label: '选项2', value: 'option2' }
      ]
    }
  },
  {
    type: 'radio',
    label: '单选框组',
    icon: 'circle-dot',
    category: 'basic',
    defaultProps: {
      options: [
        { label: '选项1', value: 'option1' },
        { label: '选项2', value: 'option2' }
      ]
    }
  },
  {
    type: 'checkbox',
    label: '多选框组',
    icon: 'check-square',
    category: 'basic',
    defaultProps: {
      options: [
        { label: '选项1', value: 'option1' },
        { label: '选项2', value: 'option2' }
      ]
    }
  },
  {
    type: 'switch',
    label: '开关',
    icon: 'toggle-left',
    category: 'basic',
    defaultProps: {
      defaultValue: false
    }
  },
  {
    type: 'date',
    label: '日期选择',
    icon: 'calendar',
    category: 'advanced',
    defaultProps: {
      placeholder: '请选择日期'
    }
  },
  {
    type: 'time',
    label: '时间选择',
    icon: 'clock',
    category: 'advanced',
    defaultProps: {
      placeholder: '请选择时间'
    }
  },
  {
    type: 'rate',
    label: '评分',
    icon: 'star',
    category: 'advanced',
    defaultProps: {
      max: 5,
      defaultValue: 0
    }
  },
  {
    type: 'slider',
    label: '滑块',
    icon: 'sliders',
    category: 'advanced',
    defaultProps: {
      min: 0,
      max: 100,
      defaultValue: 50
    }
  },
  {
    type: 'divider',
    label: '分割线',
    icon: 'minus',
    category: 'layout',
    defaultProps: {
      text: ''
    }
  },
  {
    type: 'text',
    label: '静态文本',
    icon: 'file-text',
    category: 'layout',
    defaultProps: {
      content: '静态文本内容'
    }
  }
]

export const categories = [
  { key: 'basic', label: '基础组件' },
  { key: 'advanced', label: '高级组件' },
  { key: 'layout', label: '布局组件' }
]
