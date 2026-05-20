import { useState, useEffect } from 'react'
import { Table, Card, Tag, Space, Button, Select, message, Descriptions, Progress, Alert } from 'antd'
import { ReloadOutlined, PlayCircleOutlined } from '@ant-design/icons'
import { pipelineApi } from '../services/api'
import dayjs from 'dayjs'

export default function ExecutionMonitor() {
  const [pipelines, setPipelines] = useState([])
  const [selectedPipeline, setSelectedPipeline] = useState(null)
  const [executions, setExecutions] = useState([])
  const [selectedExecution, setSelectedExecution] = useState(null)
  const [executionTasks, setExecutionTasks] = useState([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    loadPipelines()
  }, [])

  const loadPipelines = async () => {
    try {
      const data = await pipelineApi.list()
      setPipelines(data)
    } catch (error) {
      message.error('加载管道列表失败')
    }
  }

  const loadExecutions = async (pipelineId) => {
    if (!pipelineId) {
      setExecutions([])
      return
    }
    setLoading(true)
    try {
      const data = await pipelineApi.getExecutions(pipelineId)
      setExecutions(data)
    } catch (error) {
      message.error('加载执行记录失败')
    } finally {
      setLoading(false)
    }
  }

  const loadExecutionTasks = async (executionId) => {
    if (!executionId) {
      setExecutionTasks([])
      return
    }
    try {
      const data = await pipelineApi.getExecutionTasks(executionId)
      setExecutionTasks(data)
    } catch (error) {
      message.error('加载任务详情失败')
    }
  }

  const handlePipelineChange = (value) => {
    setSelectedPipeline(value)
    setSelectedExecution(null)
    setExecutionTasks([])
    loadExecutions(value)
  }

  const handleExecutionClick = (record) => {
    setSelectedExecution(record)
    loadExecutionTasks(record.id)
  }

  const handleResume = async (executionId) => {
    try {
      const checkpoint = await pipelineApi.getCheckpoint(executionId)
      if (!checkpoint.can_resume) {
        message.warning('该执行无法断点续跑')
        return
      }
      message.info('开始断点续跑...')
      const result = await pipelineApi.run(selectedPipeline, {
        resume_from_checkpoint: executionId
      })
      message.success(`续跑成功! 新执行ID: ${result.execution_id}`)
      loadExecutions(selectedPipeline)
    } catch (error) {
      message.error('断点续跑失败')
    }
  }

  const getStatusColor = (status) => {
    const colors = {
      'COMPLETED': 'green',
      'RUNNING': 'blue',
      'FAILED': 'red',
      'PENDING': 'default'
    }
    return colors[status] || 'default'
  }

  const executionColumns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 80,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status) => (
        <Tag color={getStatusColor(status)}>{status}</Tag>
      ),
    },
    {
      title: '开始时间',
      dataIndex: 'start_time',
      key: 'start_time',
      render: (date) => dayjs(date).format('YYYY-MM-DD HH:mm:ss'),
    },
    {
      title: '结束时间',
      dataIndex: 'end_time',
      key: 'end_time',
      render: (date) => date ? dayjs(date).format('YYYY-MM-DD HH:mm:ss') : '-',
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space>
          {record.status === 'FAILED' && (
            <Button
              type="link"
              size="small"
              icon={<PlayCircleOutlined />}
              onClick={() => handleResume(record.id)}
            >
              断点续跑
            </Button>
          )}
        </Space>
      ),
    },
  ]

  const taskColumns = [
    {
      title: '任务名称',
      dataIndex: 'task_name',
      key: 'task_name',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status) => (
        <Tag color={getStatusColor(status)}>{status}</Tag>
      ),
    },
    {
      title: '开始时间',
      dataIndex: 'start_time',
      key: 'start_time',
      render: (date) => date ? dayjs(date).format('HH:mm:ss') : '-',
    },
    {
      title: '结束时间',
      dataIndex: 'end_time',
      key: 'end_time',
      render: (date) => date ? dayjs(date).format('HH:mm:ss') : '-',
    },
  ]

  const successRate = executions.length > 0
    ? Math.round((executions.filter(e => e.status === 'COMPLETED').length / executions.length) * 100)
    : 0

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h3>执行监控</h3>
        <Button icon={<ReloadOutlined />} onClick={() => loadExecutions(selectedPipeline)}>
          刷新
        </Button>
      </div>

      <Card style={{ marginBottom: 16 }}>
        <Space style={{ marginBottom: 16 }}>
          <span>选择管道:</span>
          <Select
            style={{ width: 300 }}
            placeholder="请选择管道"
            value={selectedPipeline}
            onChange={handlePipelineChange}
            options={pipelines.map(p => ({ label: p.name, value: p.id }))}
          />
        </Space>

        {selectedPipeline && executions.length > 0 && (
          <div style={{ marginBottom: 16 }}>
            <Descriptions bordered size="small" column={3}>
              <Descriptions.Item label="总执行次数">{executions.length}</Descriptions.Item>
              <Descriptions.Item label="成功次数">
                {executions.filter(e => e.status === 'COMPLETED').length}
              </Descriptions.Item>
              <Descriptions.Item label="失败次数">
                {executions.filter(e => e.status === 'FAILED').length}
              </Descriptions.Item>
            </Descriptions>
            <div style={{ marginTop: 16 }}>
              <span style={{ marginRight: 8 }}>成功率:</span>
              <Progress percent={successRate} size="small" style={{ width: 200 }} />
            </div>
          </div>
        )}
      </Card>

      <div style={{ display: 'flex', gap: 16 }}>
        <Card title="执行记录" style={{ flex: 1 }}>
          <Table
            columns={executionColumns}
            dataSource={executions}
            rowKey="id"
            loading={loading}
            onRow={(record) => ({
              onClick: () => handleExecutionClick(record),
              style: { cursor: 'pointer' }
            })}
            pagination={{ pageSize: 10 }}
          />
        </Card>

        <Card title="任务详情" style={{ width: 500 }}>
          {selectedExecution ? (
            <div>
              {selectedExecution.error_message && (
                <Alert
                  message="执行错误"
                  description={selectedExecution.error_message}
                  type="error"
                  showIcon
                  style={{ marginBottom: 16 }}
                />
              )}
              <Table
                columns={taskColumns}
                dataSource={executionTasks}
                rowKey="id"
                pagination={false}
                size="small"
              />
            </div>
          ) : (
            <div style={{ textAlign: 'center', color: '#999', padding: 40 }}>
              点击左侧执行记录查看详情
            </div>
          )}
        </Card>
      </div>
    </div>
  )
}
