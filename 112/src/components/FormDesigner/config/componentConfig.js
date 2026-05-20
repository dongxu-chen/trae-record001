export const componentList = [
  {
    type: 'grid',
    label: '栅格布局',
    icon: 'Grid',
    defaultProps: {
      label: '栅格布局',
      gutter: 20
    }
  },
  {
    type: 'input',
    label: '输入框',
    icon: 'Edit',
    defaultProps: {
      label: '输入框',
      placeholder: '请输入',
      required: false,
      pattern: '',
      minLength: undefined,
      maxLength: undefined,
      visibleExpression: '',
      customValidator: '',
      validatorMessage: ''
    }
  },
  {
    type: 'textarea',
    label: '文本域',
    icon: 'Document',
    defaultProps: {
      label: '文本域',
      placeholder: '请输入',
      rows: 3,
      required: false,
      minLength: undefined,
      maxLength: undefined,
      visibleExpression: '',
      customValidator: '',
      validatorMessage: ''
    }
  },
  {
    type: 'number',
    label: '数字输入框',
    icon: 'Operation',
    defaultProps: {
      label: '数字输入框',
      placeholder: '请输入数字',
      min: undefined,
      max: undefined,
      required: false,
      visibleExpression: '',
      customValidator: '',
      validatorMessage: ''
    }
  },
  {
    type: 'radio',
    label: '单选框',
    icon: 'CircleCheck',
    defaultProps: {
      label: '单选框',
      options: [
        { label: '选项1', value: 'option1' },
        { label: '选项2', value: 'option2' }
      ],
      required: false,
      visibleExpression: ''
    }
  },
  {
    type: 'checkbox',
    label: '多选框',
    icon: 'Check',
    defaultProps: {
      label: '多选框',
      options: [
        { label: '选项1', value: 'option1' },
        { label: '选项2', value: 'option2' }
      ],
      required: false,
      minItems: undefined,
      maxItems: undefined,
      visibleExpression: ''
    }
  },
  {
    type: 'select',
    label: '下拉选择',
    icon: 'ArrowDown',
    defaultProps: {
      label: '下拉选择',
      placeholder: '请选择',
      options: [
        { label: '选项1', value: 'option1' },
        { label: '选项2', value: 'option2' }
      ],
      required: false,
      visibleExpression: ''
    }
  },
  {
    type: 'date',
    label: '日期选择器',
    icon: 'Calendar',
    defaultProps: {
      label: '日期选择器',
      placeholder: '请选择日期',
      required: false,
      format: 'YYYY-MM-DD',
      visibleExpression: ''
    }
  },
  {
    type: 'time',
    label: '时间选择器',
    icon: 'Clock',
    defaultProps: {
      label: '时间选择器',
      placeholder: '请选择时间',
      required: false,
      format: 'HH:mm:ss',
      visibleExpression: ''
    }
  },
  {
    type: 'switch',
    label: '开关',
    icon: 'Switch',
    defaultProps: {
      label: '开关',
      required: false,
      visibleExpression: ''
    }
  },
  {
    type: 'rate',
    label: '评分',
    icon: 'Star',
    defaultProps: {
      label: '评分',
      max: 5,
      required: false,
      min: 0,
      visibleExpression: ''
    }
  },
  {
    type: 'slider',
    label: '滑块',
    icon: 'Rank',
    defaultProps: {
      label: '滑块',
      min: 0,
      max: 100,
      required: false,
      visibleExpression: ''
    }
  }
]

export function generateFieldId() {
  return 'field_' + Math.random().toString(36).substr(2, 9)
}
