import React from 'react'
import { Handle, Position } from 'reactflow'
import {
  EditOutlined,
  CheckCircleOutlined,
  CalendarOutlined,
  SettingOutlined
} from '@ant-design/icons'

const iconMap = {
  input: EditOutlined,
  textarea: EditOutlined,
  select: SettingOutlined,
  radio: CheckCircleOutlined,
  checkbox: CheckCircleOutlined,
  date: CalendarOutlined,
  time: CalendarOutlined,
  switch: SettingOutlined,
  rate: SettingOutlined,
  slider: SettingOutlined
}

const FormFieldNode = ({ data, selected }) => {
  const IconComponent = iconMap[data?.type] || EditOutlined

  return (
    <div className={`form-field-node ${selected ? 'selected' : ''}`}>
      <Handle
        type="target"
        position={Position.Top}
        className="handle"
      />
      <div className="node-header">
        <IconComponent />
        <span>{data?.label || '表单字段'}</span>
      </div>
      <div className="node-body">
        <div className="node-field-name">
          {data?.fieldName || '未设置字段名'}
        </div>
        <div className="node-field-type">
          类型: {data?.typeLabel || data?.type}
        </div>
        {data?.required && (
          <div style={{ color: '#ff4d4f', fontSize: '12px', marginTop: '4px' }}>
            * 必填
          </div>
        )}
      </div>
      <Handle
        type="source"
        position={Position.Bottom}
        className="handle"
      />
    </div>
  )
}

export default FormFieldNode
