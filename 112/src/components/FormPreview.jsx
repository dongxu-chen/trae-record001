import React from 'react'
import {
  Form,
  Input,
  Select,
  Radio,
  Checkbox,
  DatePicker,
  TimePicker,
  Switch,
  Rate,
  Slider,
  Button,
  message
} from 'antd'
import { CloseOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'

const { TextArea } = Input

const FormPreview = ({ nodes, onClose }) => {
  const [form] = Form.useForm()
  const formFieldNodes = nodes.filter(n => n.type === 'formField')

  const getFormComponent = (fieldType, fieldData) => {
    switch (fieldType) {
      case 'input':
        return <Input placeholder={fieldData.placeholder} />
      case 'textarea':
        return <TextArea rows={fieldData.rows || 4} placeholder={fieldData.placeholder} />
      case 'select':
        return (
          <Select placeholder={fieldData.placeholder} style={{ width: '100%' }}>
            {fieldData.options?.map(opt => (
              <Select.Option key={opt.value} value={opt.value}>
                {opt.label}
              </Select.Option>
            ))}
          </Select>
        )
      case 'radio':
        return (
          <Radio.Group>
            {fieldData.options?.map(opt => (
              <Radio key={opt.value} value={opt.value}>
                {opt.label}
              </Radio>
            ))}
          </Radio.Group>
        )
      case 'checkbox':
        return (
          <Checkbox.Group>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {fieldData.options?.map(opt => (
                <Checkbox key={opt.value} value={opt.value}>
                  {opt.label}
                </Checkbox>
              ))}
            </div>
          </Checkbox.Group>
        )
      case 'date':
        return <DatePicker style={{ width: '100%' }} format={fieldData.format || 'YYYY-MM-DD'} />
      case 'time':
        return <TimePicker style={{ width: '100%' }} format={fieldData.format || 'HH:mm:ss'} />
      case 'switch':
        return <Switch />
      case 'rate':
        return <Rate count={fieldData.max || 5} />
      case 'slider':
        return <Slider min={fieldData.min || 0} max={fieldData.max || 100} />
      default:
        return <Input />
    }
  }

  const handleSubmit = (values) => {
    console.log('表单数据:', values)
    message.success('表单提交成功！')
  }

  return (
    <div className="preview-panel">
      <div className="preview-header">
        <span>表单预览</span>
        <Button type="text" icon={<CloseOutlined />} onClick={onClose} />
      </div>
      <div className="preview-content">
        {formFieldNodes.length === 0 ? (
          <div style={{ textAlign: 'center', color: '#999', padding: '40px' }}>
            暂无表单字段
          </div>
        ) : (
          <Form
            form={form}
            layout="vertical"
            onFinish={handleSubmit}
            initialValues={{
              [formFieldNodes.find(n => n.data.type === 'switch')?.data.fieldName]: false
            }}
          >
            {formFieldNodes.map(node => (
              <Form.Item
                key={node.id}
                label={
                  <span>
                    {node.data.label}
                    {node.data.required && <span style={{ color: '#ff4d4f', marginLeft: '4px' }}>*</span>}
                  </span>
                }
                name={node.data.fieldName || node.id}
                rules={[
                  node.data.required && { required: true, message: '此项为必填' },
                  node.data.minLength && { min: node.data.minLength, message: `至少${node.data.minLength}个字符` },
                  node.data.maxLength && { max: node.data.maxLength, message: `最多${node.data.maxLength}个字符` }
                ].filter(Boolean)}
              >
                {getFormComponent(node.data.type, node.data)}
              </Form.Item>
            ))}
            <Form.Item>
              <Button type="primary" htmlType="submit" style={{ width: '100%' }}>
                提交表单
              </Button>
            </Form.Item>
          </Form>
        )}
      </div>
    </div>
  )
}

export default FormPreview
