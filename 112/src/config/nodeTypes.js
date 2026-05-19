import {
  EditOutlined,
  SelectOutlined,
  CalendarOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  CheckSquareOutlined,
  SlidersOutlined,
  StarOutlined,
  SwitcherOutlined,
  ForkOutlined,
  RetweetOutlined,
  PlayCircleOutlined,
  StopOutlined
} from '@ant-design/icons'

export const nodeTypesConfig = {
  formFields: [
    {
      type: 'input',
      label: '输入框',
      icon: EditOutlined,
      defaultData: {
        label: '输入框',
        fieldName: '',
        placeholder: '请输入',
        required: false,
        maxLength: undefined,
        minLength: undefined
      }
    },
    {
      type: 'textarea',
      label: '文本域',
      icon: EditOutlined,
      defaultData: {
        label: '文本域',
        fieldName: '',
        placeholder: '请输入',
        required: false,
        rows: 4
      }
    },
    {
      type: 'select',
      label: '下拉选择',
      icon: SelectOutlined,
      defaultData: {
        label: '下拉选择',
        fieldName: '',
        placeholder: '请选择',
        required: false,
        options: [
          { label: '选项1', value: 'option1' },
          { label: '选项2', value: 'option2' }
        ]
      }
    },
    {
      type: 'radio',
      label: '单选框',
      icon: CheckCircleOutlined,
      defaultData: {
        label: '单选框',
        fieldName: '',
        required: false,
        options: [
          { label: '选项1', value: 'option1' },
          { label: '选项2', value: 'option2' }
        ]
      }
    },
    {
      type: 'checkbox',
      label: '多选框',
      icon: CheckSquareOutlined,
      defaultData: {
        label: '多选框',
        fieldName: '',
        required: false,
        options: [
          { label: '选项1', value: 'option1' },
          { label: '选项2', value: 'option2' }
        ]
      }
    },
    {
      type: 'date',
      label: '日期选择',
      icon: CalendarOutlined,
      defaultData: {
        label: '日期选择',
        fieldName: '',
        placeholder: '请选择日期',
        required: false,
        format: 'YYYY-MM-DD'
      }
    },
    {
      type: 'time',
      label: '时间选择',
      icon: ClockCircleOutlined,
      defaultData: {
        label: '时间选择',
        fieldName: '',
        placeholder: '请选择时间',
        required: false,
        format: 'HH:mm:ss'
      }
    },
    {
      type: 'switch',
      label: '开关',
      icon: SwitcherOutlined,
      defaultData: {
        label: '开关',
        fieldName: '',
        defaultValue: false
      }
    },
    {
      type: 'rate',
      label: '评分',
      icon: StarOutlined,
      defaultData: {
        label: '评分',
        fieldName: '',
        max: 5,
        required: false
      }
    },
    {
      type: 'slider',
      label: '滑块',
      icon: SlidersOutlined,
      defaultData: {
        label: '滑块',
        fieldName: '',
        min: 0,
        max: 100,
        required: false
      }
    }
  ],
  controlFlow: [
    {
      type: 'start',
      label: '开始节点',
      icon: PlayCircleOutlined
    },
    {
      type: 'end',
      label: '结束节点',
      icon: StopOutlined
    },
    {
      type: 'branch',
      label: '条件分支',
      icon: ForkOutlined,
      defaultData: {
        label: '条件判断',
        condition: '',
        trueLabel: '是',
        falseLabel: '否'
      }
    },
    {
      type: 'loop',
      label: '循环节点',
      icon: RetweetOutlined,
      defaultData: {
        label: '循环',
        loopCondition: '',
        maxLoops: 10
      }
    }
  ]
}

export const nodeTypeLabels = {
  input: '输入框',
  textarea: '文本域',
  select: '下拉选择',
  radio: '单选框',
  checkbox: '多选框',
  date: '日期选择',
  time: '时间选择',
  switch: '开关',
  rate: '评分',
  slider: '滑块',
  start: '开始节点',
  end: '结束节点',
  branch: '条件分支',
  loop: '循环节点'
}
