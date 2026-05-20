import { useState, useCallback, useRef, useEffect } from 'react'
import ReactFlow, {
  useNodesState,
  useEdgesState,
  addEdge,
  Controls,
  Background,
  BackgroundVariant,
  Handle,
  Position,
} from 'reactflow'
import 'reactflow/dist/style.css'
import {
  Card,
  Button,
  Space,
  Input,
  Select,
  Form,
  Drawer,
  message,
  Divider,
  Tag
} from 'antd'
import {
  SaveOutlined,
  PlayCircleOutlined,
  DeleteOutlined,
  ImportOutlined,
  FilterOutlined,
  ExportOutlined,
  AuditOutlined
} from '@ant-design/icons'
import { useParams, useNavigate } from 'react-router-dom'
import { pipelineApi } from '../services/api'

const taskTypes = [
  { type: 'extract_csv', label: 'CSV提取', category: 'extract', icon: <ImportOutlined /> },
  { type: 'extract_database', label: '数据库提取', category: 'extract', icon: <ImportOutlined /> },
  { type: 'transform_filter', label: '数据过滤', category: 'transform', icon: <FilterOutlined /> },
  { type: 'transform_rename', label: '字段重命名', category: 'transform', icon: <FilterOutlined /> },
  { type: 'transform_select', label: '字段选择', category: 'transform', icon: <FilterOutlined /> },
  { type: 'transform_join', label: '数据合并', category: 'transform', icon: <FilterOutlined /> },
  { type: 'load_csv', label: 'CSV导出', category: 'load', icon: <ExportOutlined /> },
  { type: 'load_database', label: '数据库导出', category: 'load', icon: <ExportOutlined /> },
  { type: 'check_null_values', label: '空值检查', category: 'data-quality', icon: <AuditOutlined /> },
  { type: 'check_duplicates', label: '重复检查', category: 'data-quality', icon: <AuditOutlined /> },
]

function CustomNode({ data }) {
  const taskInfo = taskTypes.find(t => t.type === data.taskType)
  const categoryClass = taskInfo?.category || 'transform'

  return (
    <div className={`dndnode ${categoryClass}`}>
      <Handle type="target" position={Position.Top} />
      <div className="node-header">
        {taskInfo?.icon}
        <span>{data.label}</span>
      </div>
      <div className="node-label">{taskInfo?.label}</div>
      <Handle type="source" position={Position.Bottom} />
    </div>
  )
}

const nodeTypes = { custom: CustomNode }

let id = 0
const getId = () => `node_${++id}`

export default function PipelineDesigner() {
  const { id: pipelineId } = useParams()
  const navigate = useNavigate()
  const reactFlowWrapper = useRef(null)
  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])
  const [reactFlowInstance, setReactFlowInstance] = useState(null)
  const [pipelineName, setPipelineName] = useState('新管道')
  const [selectedNode, setSelectedNode] = useState(null)
  const [drawerVisible, setDrawerVisible] = useState(false)
  const [form] = Form.useForm()
  const [currentPipeline, setCurrentPipeline] = useState(null)

  useEffect(() => {
    if (pipelineId) {
      loadPipeline(pipelineId)
    }
  }, [pipelineId])

  const loadPipeline = async (id) => {
    try {
      const pipeline = await pipelineApi.get(id)
      setCurrentPipeline(pipeline)
      setPipelineName(pipeline.name)
      const config = pipeline.flow_config
      if (config.tasks) {
        setNodes(config.tasks)
      }
      if (config.edges) {
        setEdges(config.edges)
      }
    } catch (error) {
      message.error('加载管道失败')
    }
  }

  const onConnect = useCallback(
    (params) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  )

  const onDragOver = useCallback((event) => {
    event.preventDefault()
    event.dataTransfer.dropEffect = 'move'
  }, [])

  const onDrop = useCallback(
    (event) => {
      event.preventDefault()

      const type = event.dataTransfer.getData('application/reactflow')
      if (!type) return

      const position = reactFlowInstance.screenToFlowPosition({
        x: event.clientX,
        y: event.clientY,
      })

      const taskInfo = taskTypes.find(t => t.type === type)
      const newNode = {
        id: getId(),
        type: 'custom',
        position,
        data: {
          label: taskInfo?.label || type,
          taskType: type,
          params: {}
        },
      }

      setNodes((nds) => nds.concat(newNode))
    },
    [reactFlowInstance, setNodes]
  )

  const onNodeClick = (event, node) => {
    setSelectedNode(node)
    form.setFieldsValue({
      label: node.data.label,
      taskType: node.data.taskType,
      ...node.data.params
    })
    setDrawerVisible(true)
  }

  const deleteSelectedNode = () => {
    if (selectedNode) {
      setNodes((nds) => nds.filter((node) => node.id !== selectedNode.id))
      setEdges((eds) => eds.filter(
        (edge) => edge.source !== selectedNode.id && edge.target !== selectedNode.id
      ))
      setDrawerVisible(false)
      setSelectedNode(null)
    }
  }

  const updateNodeParams = () => {
    if (!selectedNode) return
    const values = form.getFieldsValue()
    const { label, ...params } = values

    setNodes((nds) =>
      nds.map((node) => {
        if (node.id === selectedNode.id) {
          return {
            ...node,
            data: {
              ...node.data,
              label: label || node.data.label,
              params
            }
          }
        }
        return node
      })
    )
    setDrawerVisible(false)
    message.success('节点配置已更新')
  }

  const savePipeline = async () => {
    const flowConfig = {
      name: pipelineName,
      tasks: nodes,
      edges: edges
    }

    try {
      if (currentPipeline) {
        await pipelineApi.update(currentPipeline.id, {
          name: pipelineName,
          flow_config: flowConfig
        })
      } else {
        await pipelineApi.create({
          name: pipelineName,
          flow_config: flowConfig
        })
      }
      message.success('管道保存成功')
      navigate('/pipelines')
    } catch (error) {
      message.error('保存失败')
    }
  }

  const runPipeline = async () => {
    if (!currentPipeline) {
      message.warning('请先保存管道')
      return
    }
    try {
      message.info('开始执行管道...')
      const result = await pipelineApi.run(currentPipeline.id)
      message.success(`执行成功! 执行ID: ${result.execution_id}`)
    } catch (error) {
      message.error('执行失败')
    }
  }

  const onDragStart = (event, nodeType) => {
    event.dataTransfer.setData('application/reactflow', nodeType)
    event.dataTransfer.effectAllowed = 'move'
  }

  const getTaskCategory = (category) => {
    const labels = {
      extract: { label: '数据提取', color: 'green' },
      transform: { label: '数据转换', color: 'blue' },
      load: { label: '数据加载', color: 'orange' },
      'data-quality': { label: '数据质量', color: 'pink' }
    }
    return labels[category] || labels.transform
  }

  const renderSidebarNodes = () => {
    const categories = ['extract', 'transform', 'load', 'data-quality']
    return categories.map(category => {
      const categoryInfo = getTaskCategory(category)
      const categoryTasks = taskTypes.filter(t => t.category === category)
      return (
        <div key={category} style={{ marginBottom: 20 }}>
          <Tag color={categoryInfo.color} style={{ marginBottom: 8 }}>
            {categoryInfo.label}
          </Tag>
          {categoryTasks.map(task => (
            <div
              key={task.type}
              className="sidebar-node"
              style={{
                border: `1px solid var(--ant-${categoryInfo.color}-color)`,
                background: `var(--ant-${categoryInfo.color}-1)`
              }}
              onDragStart={(e) => onDragStart(e, task.type)}
              draggable
            >
              {task.icon}
              <span>{task.label}</span>
            </div>
          ))}
        </div>
      )
    })
  }

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ padding: '0 0 16px 0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Space>
          <Input
            value={pipelineName}
            onChange={(e) => setPipelineName(e.target.value)}
            style={{ width: 300 }}
            placeholder="管道名称"
          />
        </Space>
        <Space>
          <Button icon={<SaveOutlined />} onClick={savePipeline}>
            保存
          </Button>
          <Button type="primary" icon={<PlayCircleOutlined />} onClick={runPipeline}>
            运行
          </Button>
        </Space>
      </div>

      <div style={{ display: 'flex', flex: 1, minHeight: 0 }}>
        <Card
          style={{ width: 240, marginRight: 16 }}
          bodyStyle={{ padding: 12 }}
          title="任务节点"
          size="small"
        >
          {renderSidebarNodes()}
        </Card>

        <div style={{ flex: 1, height: '100%' }} ref={reactFlowWrapper}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onInit={setReactFlowInstance}
            onDrop={onDrop}
            onDragOver={onDragOver}
            onNodeClick={onNodeClick}
            nodeTypes={nodeTypes}
            fitView
          >
            <Controls />
            <Background variant={BackgroundVariant.Dots} gap={12} size={1} />
          </ReactFlow>
        </div>
      </div>

      <Drawer
        title="节点配置"
        placement="right"
        onClose={() => setDrawerVisible(false)}
        open={drawerVisible}
        width={400}
      >
        {selectedNode && (
          <Form form={form} layout="vertical">
            <Form.Item name="label" label="节点名称">
              <Input />
            </Form.Item>
            <Divider />
            <Form.Item label="任务类型">
              <Input value={selectedNode.data.taskType} disabled />
            </Form.Item>

            {selectedNode.data.taskType === 'extract_csv' && (
              <Form.Item name="file_path" label="文件路径">
                <Input placeholder="/path/to/file.csv" />
              </Form.Item>
            )}

            {selectedNode.data.taskType === 'transform_filter' && (
              <>
                <Form.Item name="column" label="字段名称">
                  <Input placeholder="column_name" />
                </Form.Item>
                <Form.Item name="operator" label="操作符">
                  <Select>
                    <Select.Option value="equals">等于</Select.Option>
                    <Select.Option value="greater_than">大于</Select.Option>
                    <Select.Option value="less_than">小于</Select.Option>
                    <Select.Option value="contains">包含</Select.Option>
                  </Select>
                </Form.Item>
                <Form.Item name="value" label="值">
                  <Input placeholder="过滤值" />
                </Form.Item>
              </>
            )}

            {selectedNode.data.taskType === 'transform_rename' && (
              <Form.Item name="rename_mapping" label="重命名映射 (JSON)">
                <Input.TextArea rows={4} placeholder='{"old_name": "new_name"}' />
              </Form.Item>
            )}

            {selectedNode.data.taskType === 'transform_select' && (
              <Form.Item name="columns" label="选择字段 (逗号分隔)">
                <Input placeholder="col1, col2, col3" />
              </Form.Item>
            )}

            {selectedNode.data.taskType === 'load_csv' && (
              <Form.Item name="output_path" label="输出路径">
                <Input placeholder="/path/to/output.csv" />
              </Form.Item>
            )}

            <Divider />
            <Space>
              <Button type="primary" onClick={updateNodeParams}>
                保存配置
              </Button>
              <Button danger icon={<DeleteOutlined />} onClick={deleteSelectedNode}>
                删除节点
              </Button>
            </Space>
          </Form>
        )}
      </Drawer>
    </div>
  )
}
