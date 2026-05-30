import React, { useState, useCallback, useRef, useEffect, useMemo } from 'react';
import {
  ReactFlow,
  addEdge,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  useReactFlow,
  ReactFlowProvider,
  Panel,
  Handle,
  Position,
} from 'reactflow';
import 'reactflow/dist/style.css';
import dagre from 'dagre';
import { Button, Space, Input, Form, Select, InputNumber, message, Drawer, Card, Tag } from 'antd';
import { SaveOutlined, RocketOutlined, LayoutOutlined } from '@ant-design/icons';
import { useNavigate, useParams } from 'react-router-dom';
import { workflowApi } from '../api';
import { TaskTypes, TaskTypeLabels } from '../types';

const dagreGraph = new dagre.graphlib.Graph();
dagreGraph.setDefaultEdgeLabel(() => ({}));

const NODE_WIDTH = 180;
const NODE_HEIGHT = 80;

const getLayoutedElements = (nodes, edges, direction = 'TB') => {
  const isHorizontal = direction === 'LR';
  dagreGraph.setGraph({ rankdir: direction, nodesep: 80, ranksep: 100, marginx: 40, marginy: 40 });

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: NODE_WIDTH, height: NODE_HEIGHT });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagreGraph.layout();

  const layoutedNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    return {
      ...node,
      position: {
        x: nodeWithPosition.x - NODE_WIDTH / 2,
        y: nodeWithPosition.y - NODE_HEIGHT / 2,
      },
      sourcePosition: isHorizontal ? Position.Right : Position.Bottom,
      targetPosition: isHorizontal ? Position.Left : Position.Top,
    };
  });

  return { nodes: layoutedNodes, edges };
};

const CustomNode = ({ data, selected }) => {
  const nodeColors = {
    SHELL: '#13c2c2',
    PYTHON: '#fa8c16',
    HTTP: '#eb2f96',
    DATA_SYNC: '#722ed1',
    EMAIL: '#faad14'
  };

  const color = nodeColors[data.taskType] || '#1890ff';

  return (
    <div
      style={{
        padding: 12,
        border: `2px solid ${selected ? '#1890ff' : color}`,
        borderRadius: 8,
        background: selected ? '#e6f7ff' : 'white',
        minWidth: NODE_WIDTH - 24,
        boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
      }}
    >
      <Handle
        type="target"
        position={Position.Top}
        style={{ background: '#1890ff', width: 10, height: 10 }}
      />
      <div style={{ fontWeight: 'bold', fontSize: 14, marginBottom: 4 }}>
        {data.label}
      </div>
      <Tag color={color} style={{ fontSize: 11, margin: 0 }}>
        {TaskTypeLabels[data.taskType] || data.taskType}
      </Tag>
      <Handle
        type="source"
        position={Position.Bottom}
        style={{ background: '#1890ff', width: 10, height: 10 }}
      />
    </div>
  );
};

const nodeTypes = {
  custom: CustomNode,
};

const WorkflowEditorInner = () => {
  const navigate = useNavigate();
  const { id } = useParams();
  const isEdit = !!id;
  const reactFlowInstance = useReactFlow();

  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [workflowName, setWorkflowName] = useState('');
  const [workflowDesc, setWorkflowDesc] = useState('');
  const [taskDrawer, setTaskDrawer] = useState(false);
  const [selectedNode, setSelectedNode] = useState(null);
  const [layoutDir, setLayoutDir] = useState('TB');
  const [form] = Form.useForm();

  useEffect(() => {
    if (isEdit) {
      loadWorkflow();
    }
  }, [id]);

  const loadWorkflow = async () => {
    try {
      const data = await workflowApi.get(id);
      setWorkflowName(data.name);
      setWorkflowDesc(data.description || '');

      if (data.tasks && data.tasks.length > 0) {
        const flowNodes = data.tasks.map(task => ({
          id: task.taskKey,
          type: 'custom',
          position: { x: task.positionX || 0, y: task.positionY || 0 },
          data: { label: task.taskName, taskType: task.taskType, ...task },
        }));

        const flowEdges = [];
        data.tasks.forEach(task => {
          if (task.upstreamKeys && task.upstreamKeys.length > 0) {
            task.upstreamKeys.forEach(upKey => {
              flowEdges.push({
                id: `${upKey}-${task.taskKey}`,
                source: upKey,
                target: task.taskKey,
                type: 'smoothstep',
                animated: true,
              });
            });
          }
        });

        const layouted = getLayoutedElements(flowNodes, flowEdges, layoutDir);
        setNodes(layouted.nodes);
        setEdges(layouted.edges);
      }
    } catch (err) {
      message.error('加载工作流失败');
    }
  };

  const onAutoLayout = useCallback(() => {
    const layouted = getLayoutedElements(nodes, edges, layoutDir);
    setNodes(layouted.nodes);
    setEdges(layouted.edges);
    setTimeout(() => reactFlowInstance.fitView({ padding: 0.2 }), 50);
    message.success('自动布局已应用');
  }, [nodes, edges, layoutDir, setNodes, setEdges, reactFlowInstance]);

  const onConnect = useCallback(
    (params) => setEdges((eds) => addEdge({ ...params, animated: true, type: 'smoothstep' }, eds)),
    [setEdges]
  );

  const onDragOver = (event) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  };

  const onDrop = (event) => {
    event.preventDefault();

    const type = event.dataTransfer.getData('application/reactflow');
    if (!type) return;

    const position = reactFlowInstance.screenToFlowPosition({
      x: event.clientX,
      y: event.clientY,
    });

    const newNode = {
      id: `task_${Date.now()}`,
      type: 'custom',
      position,
      data: {
        label: `${TaskTypeLabels[type]}任务`,
        taskType: type,
        taskName: `${TaskTypeLabels[type]}任务_${Date.now()}`,
        taskPriority: 5,
        retryCount: 0,
        retryInterval: 30,
        retryStrategy: 'FIXED',
        timeoutSeconds: 3600,
        dataProducts: [],
      },
    };

    setNodes((nds) => nds.concat(newNode));
  };

  const onNodeDoubleClick = (_, node) => {
    setSelectedNode(node);
    form.setFieldsValue({
      taskKey: node.id,
      taskName: node.data.label,
      taskType: node.data.taskType,
      taskPriority: node.data.taskPriority || 5,
      retryCount: node.data.retryCount || 0,
      retryInterval: node.data.retryInterval || 30,
      retryStrategy: node.data.retryStrategy || 'FIXED',
      timeoutSeconds: node.data.timeoutSeconds || 3600,
      dataProducts: (node.data.dataProducts || []).join(', '),
    });
    setTaskDrawer(true);
  };

  const saveTaskConfig = () => {
    form.validateFields().then(values => {
      const dataProductsStr = values.dataProducts || '';
      const dataProducts = dataProductsStr
        .split(',')
        .map(s => s.trim())
        .filter(s => s.length > 0);

      setNodes(nds => nds.map(node => {
        if (node.id === selectedNode.id) {
          return {
            ...node,
            id: values.taskKey,
            data: {
              ...node.data,
              label: values.taskName,
              ...values,
              dataProducts,
            },
          };
        }
        return node;
      }));

      if (selectedNode.id !== values.taskKey) {
        setEdges(eds => eds.map(e => {
          if (e.source === selectedNode.id) return { ...e, source: values.taskKey };
          if (e.target === selectedNode.id) return { ...e, target: values.taskKey };
          return e;
        }));
      }

      setTaskDrawer(false);
      message.success('任务配置已保存');
    });
  };

  const saveWorkflow = async () => {
    if (!workflowName.trim()) {
      message.error('请输入工作流名称');
      return;
    }

    const tasks = nodes.map(node => {
      const upstreams = edges
        .filter(e => e.target === node.id)
        .map(e => e.source);

      return {
        taskKey: node.id,
        taskName: node.data.taskName || node.data.label,
        taskType: node.data.taskType,
        taskPriority: node.data.taskPriority || 5,
        retryCount: node.data.retryCount || 0,
        retryInterval: node.data.retryInterval || 30,
        retryStrategy: node.data.retryStrategy || 'FIXED',
        timeoutSeconds: node.data.timeoutSeconds || 3600,
        dataProducts: node.data.dataProducts || [],
        positionX: node.position.x,
        positionY: node.position.y,
        upstreamKeys: upstreams,
      };
    });

    const data = {
      name: workflowName,
      description: workflowDesc,
      dagJson: JSON.stringify({ nodes, edges }),
      tasks,
    };

    try {
      if (isEdit) {
        await workflowApi.update(id, data);
        message.success('工作流已更新');
      } else {
        await workflowApi.create(data);
        message.success('工作流已创建');
        navigate('/workflows');
      }
    } catch (err) {
      message.error('保存失败');
    }
  };

  const publishWorkflow = async () => {
    if (!isEdit) {
      message.error('请先保存工作流');
      return;
    }
    try {
      await workflowApi.publish(id);
      message.success('工作流已发布');
    } catch (err) {
      message.error('发布失败');
    }
  };

  const DraggableNode = ({ type, label, color }) => (
    <div
      draggable
      onDragStart={(event) => {
        event.dataTransfer.setData('application/reactflow', type);
        event.dataTransfer.effectAllowed = 'move';
      }}
      style={{
        padding: '8px 12px',
        border: `2px solid ${color}`,
        borderRadius: 6,
        background: 'white',
        cursor: 'grab',
        marginBottom: 8,
        fontSize: 13,
      }}
    >
      {label}
    </div>
  );

  return (
    <div style={{ height: 'calc(100vh - 200px)', display: 'flex' }}>
      <div style={{ width: 200, padding: 16, borderRight: '1px solid #f0f0f0' }}>
        <h4 style={{ marginBottom: 16 }}>拖拽添加任务</h4>
        {Object.entries(TaskTypes).map(([key, value]) => (
          <DraggableNode
            key={key}
            type={value}
            label={TaskTypeLabels[value]}
            color="#1890ff"
          />
        ))}

        <div style={{ marginTop: 24, borderTop: '1px solid #f0f0f0', paddingTop: 16 }}>
          <h4 style={{ marginBottom: 12 }}>自动布局</h4>
          <Select
            value={layoutDir}
            onChange={setLayoutDir}
            style={{ width: '100%', marginBottom: 8 }}
            options={[
              { value: 'TB', label: '从上到下' },
              { value: 'LR', label: '从左到右' },
            ]}
          />
          <Button
            icon={<LayoutOutlined />}
            onClick={onAutoLayout}
            style={{ width: '100%' }}
          >
            自动布局
          </Button>
        </div>
      </div>

      <div style={{ flex: 1 }}>
        <div style={{ marginBottom: 16, display: 'flex', alignItems: 'center', gap: 16 }}>
          <Input
            style={{ width: 250 }}
            placeholder="工作流名称"
            value={workflowName}
            onChange={e => setWorkflowName(e.target.value)}
            size="large"
          />
          <Input
            style={{ width: 300 }}
            placeholder="工作流描述"
            value={workflowDesc}
            onChange={e => setWorkflowDesc(e.target.value)}
            size="large"
          />
          <Space style={{ marginLeft: 'auto' }}>
            <Button icon={<LayoutOutlined />} onClick={onAutoLayout}>自动布局</Button>
            <Button icon={<SaveOutlined />} onClick={saveWorkflow}>保存</Button>
            {isEdit && (
              <Button type="primary" icon={<RocketOutlined />} onClick={publishWorkflow}>
                发布
              </Button>
            )}
            <Button onClick={() => navigate('/workflows')}>返回</Button>
          </Space>
        </div>

        <div style={{ height: '100%', background: '#fafafa', borderRadius: 8 }}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onDrop={onDrop}
            onDragOver={onDragOver}
            onNodeDoubleClick={onNodeDoubleClick}
            nodeTypes={nodeTypes}
            fitView
            snapToGrid
            snapGrid={[15, 15]}
          >
            <Background />
            <Controls />
            <MiniMap />
            <Panel position="top-right">
              <Card size="small" title="操作提示" style={{ width: 180 }}>
                <div style={{ fontSize: 12, color: '#666', lineHeight: 1.8 }}>
                  拖拽左侧任务到画布<br />
                  拖拽节点连接连线<br />
                  双击节点编辑配置<br />
                  点击「自动布局」优化排列<br />
                  Del键删除选中节点
                </div>
              </Card>
            </Panel>
          </ReactFlow>
        </div>
      </div>

      <Drawer
        title="任务配置"
        open={taskDrawer}
        onClose={() => setTaskDrawer(false)}
        width={420}
        footer={
          <Space style={{ float: 'right' }}>
            <Button onClick={() => setTaskDrawer(false)}>取消</Button>
            <Button type="primary" onClick={saveTaskConfig}>保存</Button>
          </Space>
        }
      >
        <Form form={form} layout="vertical">
          <Form.Item name="taskKey" label="任务ID" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="taskName" label="任务名称" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="taskType" label="任务类型">
            <Select>
              {Object.entries(TaskTypes).map(([key, value]) => (
                <Select.Option key={key} value={value}>
                  {TaskTypeLabels[value]}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item name="taskPriority" label="任务优先级 (1-10，越高越优先)">
            <InputNumber min={1} max={10} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="retryStrategy" label="重试策略">
            <Select>
              <Select.Option value="FIXED">固定间隔</Select.Option>
              <Select.Option value="EXPONENTIAL">指数退避</Select.Option>
              <Select.Option value="LINEAR">线性递增</Select.Option>
              <Select.Option value="NONE">不重试</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="retryCount" label="最大重试次数">
            <InputNumber min={0} max={10} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="retryInterval" label="基础重试间隔(秒)">
            <InputNumber min={1} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="timeoutSeconds" label="超时时间(秒)">
            <InputNumber min={30} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="dataProducts" label="产出数据产品（逗号分隔）">
            <Input.TextArea
              rows={3}
              placeholder="例如: user_report, order_summary"
            />
          </Form.Item>
        </Form>
      </Drawer>
    </div>
  );
};

const WorkflowEditor = () => (
  <ReactFlowProvider>
    <WorkflowEditorInner />
  </ReactFlowProvider>
);

export default WorkflowEditor;
