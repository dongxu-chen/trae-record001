import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  addEdge,
  Handle,
  Position,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { Card, Descriptions, Button, Space, Tag, message, List, Typography, Row, Col, Statistic } from 'antd';
import { ArrowLeftOutlined, ReloadOutlined, StopOutlined, FileTextOutlined, ClockCircleOutlined, CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { executionApi, workflowApi } from '../api';
import { StatusColors, TriggerTypeLabels } from '../types';

const { Text } = Typography;

const StatusNode = ({ data }) => {
  const statusColors = {
    PENDING: '#d9d9d9',
    RUNNING: '#faad14',
    SUCCESS: '#52c41a',
    FAILED: '#ff4d4f',
    CANCELLED: '#8c8c8c',
  };

  const color = statusColors[data.status] || '#d9d9d9';

  return (
    <div
      style={{
        padding: 10,
        border: `3px solid ${color}`,
        borderRadius: 8,
        background: data.status === 'RUNNING' ? '#fffbe6' : data.status === 'SUCCESS' ? '#f6ffed' : data.status === 'FAILED' ? '#fff2f0' : 'white',
        minWidth: 160,
        boxShadow: data.status === 'RUNNING' ? '0 0 10px rgba(250, 173, 20, 0.5)' : '0 2px 8px rgba(0,0,0,0.15)',
        animation: data.status === 'RUNNING' ? 'pulse 2s infinite' : 'none',
      }}
    >
      <Handle type="target" position={Position.Top} style={{ background: color, width: 12, height: 12 }} />
      <div style={{ fontWeight: 'bold', fontSize: 14, marginBottom: 4 }}>
        {data.label}
      </div>
      <Tag color={color} style={{ margin: 0 }}>
        {data.status}
      </Tag>
      {data.duration && (
        <div style={{ fontSize: 11, color: '#666', marginTop: 4 }}>
          耗时: {(data.duration / 1000).toFixed(2)}s
        </div>
      )}
      <Handle type="source" position={Position.Bottom} style={{ background: color, width: 12, height: 12 }} />
    </div>
  );
};

const nodeTypes = {
  status: StatusNode,
};

const ExecutionDetail = () => {
  const navigate = useNavigate();
  const { id } = useParams();
  const [execution, setExecution] = useState(null);
  const [workflow, setWorkflow] = useState(null);
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [selectedTask, setSelectedTask] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 3000);
    return () => clearInterval(interval);
  }, [id]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const execData = await executionApi.get(id);
      setExecution(execData);

      if (execData.workflowId) {
        const wfData = await workflowApi.get(execData.workflowId);
        setWorkflow(wfData);
        buildFlowGraph(wfData, execData);
      }
    } catch (err) {
      message.error('加载执行详情失败');
    } finally {
      setLoading(false);
    }
  };

  const buildFlowGraph = (wfData, execData) => {
    if (!wfData.tasks) return;

    const taskExecMap = {};
    if (execData.taskExecutions) {
      execData.taskExecutions.forEach(te => {
        taskExecMap[te.taskKey] = te;
      });
    }

    const flowNodes = wfData.tasks.map(task => {
      const taskExec = taskExecMap[task.taskKey];
      return {
        id: task.taskKey,
        type: 'status',
        position: { x: task.positionX || 0, y: task.positionY || 0 },
        data: {
          label: task.taskName,
          taskType: task.taskType,
          status: taskExec?.status || 'PENDING',
          duration: taskExec?.durationMs,
        },
      };
    });
    setNodes(flowNodes);

    const flowEdges = [];
    wfData.tasks.forEach(task => {
      if (task.upstreamKeys && task.upstreamKeys.length > 0) {
        task.upstreamKeys.forEach(upKey => {
          const upTask = wfData.tasks.find(t => t.taskKey === upKey);
          const upExec = upTask ? taskExecMap[upKey] : null;
          const targetExec = taskExecMap[task.taskKey];

          let color = '#d9d9d9';
          let animated = false;
          if (upExec?.status === 'SUCCESS' && targetExec?.status === 'RUNNING') {
            color = '#1890ff';
            animated = true;
          } else if (upExec?.status === 'SUCCESS' && targetExec?.status === 'SUCCESS') {
            color = '#52c41a';
          }

          flowEdges.push({
            id: `${upKey}-${task.taskKey}`,
            source: upKey,
            target: task.taskKey,
            type: 'smoothstep',
            animated,
            style: { stroke: color, strokeWidth: 2 },
          });
        });
      }
    });
    setEdges(flowEdges);
  };

  const handleCancel = async () => {
    try {
      await executionApi.cancel(id);
      message.success('已取消执行');
      fetchData();
    } catch (err) {
      message.error('取消失败');
    }
  };

  const handleRetry = async () => {
    try {
      const newExec = await executionApi.retry(id);
      message.success('已重新执行');
      navigate(`/executions/${newExec.executionId}`);
    } catch (err) {
      message.error('重试失败');
    }
  };

  const getStatusTag = (status) => {
    const color = StatusColors[status] || '#d9d9d9';
    const labels = {
      PENDING: '等待中',
      RUNNING: '运行中',
      SUCCESS: '成功',
      FAILED: '失败',
      CANCELLED: '已取消'
    };
    return <Tag color={color}>{labels[status] || status}</Tag>;
  };

  if (!execution) {
    return <div>加载中...</div>;
  }

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/executions')}>
            返回
          </Button>
          <h2 style={{ margin: 0 }}>执行详情: {execution.executionId}</h2>
        </Space>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={fetchData}>刷新</Button>
          {execution.status === 'FAILED' && (
            <Button onClick={handleRetry}>重试</Button>
          )}
          {(execution.status === 'RUNNING' || execution.status === 'PENDING') && (
            <Button danger onClick={handleCancel}>取消</Button>
          )}
        </Space>
      </div>

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="状态"
              valueRender={() => getStatusTag(execution.status)}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="触发方式"
              value={TriggerTypeLabels[execution.triggerType] || execution.triggerType}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="任务数"
              value={execution.taskExecutions?.length || 0}
              prefix={<FileTextOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="耗时"
              value={execution.startedAt && execution.finishedAt
                ? `${((new Date(execution.finishedAt) - new Date(execution.startedAt)) / 1000).toFixed(2)}s`
                : execution.startedAt
                ? `${((new Date() - new Date(execution.startedAt)) / 1000).toFixed(2)}s`
                : '-'
              }
              prefix={<ClockCircleOutlined />}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={16}>
        <Col span={14}>
          <Card title="DAG执行图" style={{ marginBottom: 16 }}>
            <div style={{ height: 400 }}>
              <ReactFlow
                nodes={nodes}
                edges={edges}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                nodeTypes={nodeTypes}
                fitView
                onNodeClick={(_, node) => {
                  const taskExec = execution.taskExecutions?.find(t => t.taskKey === node.id);
                  setSelectedTask(taskExec);
                }}
              >
                <Background />
                <Controls />
              </ReactFlow>
            </div>
          </Card>
        </Col>

        <Col span={10}>
          <Card title="任务详情" style={{ height: 480, overflow: 'auto' }}>
            <List
              dataSource={execution.taskExecutions || []}
              renderItem={item => (
                <List.Item
                  key={item.id}
                  onClick={() => setSelectedTask(item)}
                  style={{
                    cursor: 'pointer',
                    background: selectedTask?.id === item.id ? '#e6f7ff' : 'transparent',
                    padding: '12px',
                    borderRadius: 8,
                    marginBottom: 8,
                  }}
                >
                  <div style={{ width: '100%' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                      <Text strong>{item.taskKey}</Text>
                      {getStatusTag(item.status)}
                    </div>
                    <div style={{ fontSize: 12, color: '#666' }}>
                      第 {item.attempt} 次尝试 | 耗时: {item.durationMs ? `${(item.durationMs / 1000).toFixed(2)}s` : '-'}
                    </div>
                  </div>
                </List.Item>
              )}
            />
          </Card>
        </Col>
      </Row>

      {selectedTask && (
        <Card title="任务日志" style={{ marginTop: 16 }}>
          <Descriptions column={2} size="small" style={{ marginBottom: 16 }}>
            <Descriptions.Item label="任务ID">{selectedTask.taskKey}</Descriptions.Item>
            <Descriptions.Item label="状态">{getStatusTag(selectedTask.status)}</Descriptions.Item>
            <Descriptions.Item label="尝试次数">{selectedTask.attempt}</Descriptions.Item>
            <Descriptions.Item label="工作节点">{selectedTask.workerNode || '-'}</Descriptions.Item>
            <Descriptions.Item label="开始时间">{selectedTask.startedAt || '-'}</Descriptions.Item>
            <Descriptions.Item label="结束时间">{selectedTask.finishedAt || '-'}</Descriptions.Item>
          </Descriptions>
          {selectedTask.errorMessage && (
            <Card type="inner" title="错误信息" size="small" style={{ marginBottom: 16, background: '#fff2f0' }}>
              <Text type="danger">{selectedTask.errorMessage}</Text>
            </Card>
          )}
          <Card type="inner" title="执行日志" size="small">
            <pre style={{
              background: '#1e1e1e',
              color: '#d4d4d4',
              padding: 16,
              borderRadius: 4,
              maxHeight: 200,
              overflow: 'auto',
              fontSize: 12,
              margin: 0,
            }}>
              {selectedTask.logText || '暂无日志'}
            </pre>
          </Card>
        </Card>
      )}
    </div>
  );
};

export default ExecutionDetail;
