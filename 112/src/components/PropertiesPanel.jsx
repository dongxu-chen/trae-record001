import React from 'react'
import {
  Form,
  Input,
  Checkbox,
  InputNumber,
  Select,
  Button,
  Space,
  Divider,
  Collapse
} from 'antd'
import { DeleteOutlined, PlusOutlined } from '@ant-design/icons'
import { useFlowStore } from '../store/flowStore'
import { nodeTypeLabels } from '../config/nodeTypes'

const { TextArea } = Input
const { Panel } = Collapse

const PropertiesPanel = () => {
  const { selectedNode, updateNode, deleteNode, nodes } = useFlowStore()
  const [form] = Form.useForm()

  React.useEffect(() => {
    if (selectedNode) {
      form.setFieldsValue(selectedNode.data)
    } else {
      form.resetFields()
    }
  }, [selectedNode, form])

  const handleValueChange = (changedValues) => {
    if (selectedNode) {
      updateNode(selectedNode.id, changedValues)
    }
  }

  const getFieldNames = () => {
    return nodes
      .filter(n => n.type === 'formField' && n.data.fieldName)
      .map(n => ({ label: n.data.fieldName, value: n.data.fieldName }))
  }

  if (!selectedNode) {
    return (
      <div className="properties-panel">
        <div className="properties-header">
          <span>属性配置</span>
        </div>
        <div className="properties-content">
          <div className="empty-properties">
            点击节点查看属性
          </div>
        </div>
      </div>
    )
  }

  const renderCommonProps = () => (
    <>
      <Form.Item label="标签" name="label">
        <Input />
      </Form.Item>
      <Form.Item label="字段名称" name="fieldName">
        <Input placeholder="例如: username" />
      </Form.Item>
    </>
  )

  const renderFormFieldProps = () => {
    const type = selectedNode.data.type

    return (
      <>
        {['input', 'textarea', 'select', 'date', 'time'].includes(type) && (
          <Form.Item label="占位文本" name="placeholder">
            <Input />
          </Form.Item>
        )}

        <Form.Item label="是否必填" name="required" valuePropName="checked">
          <Checkbox />
        </Form.Item>

        {type === 'textarea' && (
          <Form.Item label="行数" name="rows">
            <InputNumber min={1} max={20} style={{ width: '100%' }} />
          </Form.Item>
        )}

        {['input', 'textarea'].includes(type) && (
          <>
            <Form.Item label="最小长度" name="minLength">
              <InputNumber min={0} style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item label="最大长度" name="maxLength">
              <InputNumber min={0} style={{ width: '100%' }} />
            </Form.Item>
          </>
        )}

        {['slider', 'rate'].includes(type) && (
          <>
            <Form.Item label="最小值" name="min">
              <InputNumber style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item label="最大值" name="max">
              <InputNumber style={{ width: '100%' }} />
            </Form.Item>
          </>
        )}

        {['select', 'radio', 'checkbox'].includes(type) && (
          <Form.Item label="选项配置">
            <Form.List name="options">
              {(fields, { add, remove }) => (
                <>
                  {fields.map(({ key, name, ...restField }) => (
                    <Space key={key} style={{ display: 'flex', marginBottom: 8 }} align="baseline">
                      <Form.Item
                        {...restField}
                        name={[name, 'label']}
                        rules={[{ required: true, message: '请输入选项标签' }]}
                        noStyle
                      >
                        <Input placeholder="标签" style={{ width: '45%' }} />
                      </Form.Item>
                      <Form.Item
                        {...restField}
                        name={[name, 'value']}
                        rules={[{ required: true, message: '请输入选项值' }]}
                        noStyle
                      >
                        <Input placeholder="值" style={{ width: '45%' }} />
                      </Form.Item>
                      <DeleteOutlined onClick={() => remove(name)} style={{ cursor: 'pointer', color: '#ff4d4f' }} />
                    </Space>
                  ))}
                  <Button type="dashed" onClick={() => add()} block icon={<PlusOutlined />}>
                    添加选项
                  </Button>
                </>
              )}
            </Form.List>
          </Form.Item>
        )}
      </>
    )
  }

  const renderBranchProps = () => (
    <>
      <Form.Item label="条件表达式" name="condition">
        <TextArea rows={3} placeholder="例如: formData.age > 18" />
      </Form.Item>
      <Form.Item label="引用字段" name="referenceField">
        <Select placeholder="选择用于判断的字段">
          {getFieldNames().map(field => (
            <Select.Option key={field.value} value={field.value}>
              {field.label}
            </Select.Option>
          ))}
        </Select>
      </Form.Item>
      <Form.Item label="真值标签" name="trueLabel">
        <Input />
      </Form.Item>
      <Form.Item label="假值标签" name="falseLabel">
        <Input />
      </Form.Item>
    </>
  )

  const renderLoopProps = () => (
    <>
      <Form.Item label="循环条件" name="loopCondition">
        <TextArea rows={3} placeholder="例如: formData.index < 10" />
      </Form.Item>
      <Form.Item label="引用字段" name="referenceField">
        <Select placeholder="选择用于循环判断的字段">
          {getFieldNames().map(field => (
            <Select.Option key={field.value} value={field.value}>
              {field.label}
            </Select.Option>
          ))}
        </Select>
      </Form.Item>
      <Form.Item label="最大循环次数" name="maxLoops">
        <InputNumber min={1} style={{ width: '100%' }} />
      </Form.Item>
    </>
  )

  const renderDataFlowConfig = () => (
    <div className="data-flow-config">
      <div className="data-flow-title">数据流配置</div>
      <Form.Item label="输入字段映射">
        <Select
          mode="multiple"
          placeholder="选择输入字段"
          style={{ width: '100%' }}
        >
          {getFieldNames().map(field => (
            <Select.Option key={field.value} value={field.value}>
              {field.label}
            </Select.Option>
          ))}
        </Select>
      </Form.Item>
      <Form.Item label="输出字段映射">
        <Select
          mode="multiple"
          placeholder="选择输出字段"
          style={{ width: '100%' }}
        >
          {getFieldNames().map(field => (
            <Select.Option key={field.value} value={field.value}>
              {field.label}
            </Select.Option>
          ))}
        </Select>
      </Form.Item>
    </div>
  )

  return (
    <div className="properties-panel">
      <div className="properties-header">
        <span>属性配置</span>
        <Button
          type="text"
          danger
          icon={<DeleteOutlined />}
          onClick={() => deleteNode(selectedNode.id)}
        >
          删除
        </Button>
      </div>
      <div className="properties-content">
        <div style={{ marginBottom: 16 }}>
          <strong>节点类型：</strong>
          {nodeTypeLabels[selectedNode.data.type] || selectedNode.type}
        </div>
        <Form
          form={form}
          layout="vertical"
          size="small"
          onValuesChange={handleValueChange}
        >
          <Collapse defaultActiveKey={['basic', 'dataflow']}>
            <Panel header="基础配置" key="basic">
              {renderCommonProps()}
              {selectedNode.type === 'formField' && renderFormFieldProps()}
              {selectedNode.type === 'branch' && renderBranchProps()}
              {selectedNode.type === 'loop' && renderLoopProps()}
            </Panel>

            {selectedNode.type === 'formField' && (
              <Panel header="数据流" key="dataflow">
                {renderDataFlowConfig()}
              </Panel>
            )}
          </Collapse>
        </Form>
      </div>
    </div>
  )
}

export default PropertiesPanel
