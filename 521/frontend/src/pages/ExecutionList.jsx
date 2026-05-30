import React, { useState, useEffect } from 'react';
import { Table, Button, Space, Tag, Select, message, Card, Row, Col, Statistic } from 'antd';
import { EyeOutlined, ReloadOutlined, StopOutlined, RocketOutlined, CheckCircleOutlined, CloseCircleOutlined, ClockCircleOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { executionApi, workflowApi } from '../api';
import { StatusColors, TriggerTypeLabels } from '../types';

const ExecutionList = () => {
  const navigate = useNavigate();
  const [executions, setExecutions] = useState([]);
  const [workflows, setWorkflows] = useState([]);
  const [selectedWorkflow, setSelectedWorkflow] = useState();
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState({ running: 0, success: 0, failed: 0, total: 0 });

  useEffect(() => {
    fetchWorkflows();
    fetchExecutions();
    const interval = setInterval(fetchExecutions, 5000);
    return () => clearInterval(interval);
  }, [selectedWorkflow]);

  const fetchWorkflows = async () => {
    try {
      const data = await workflowApi.list();
      setWorkflows(data);
    } catch (err) {
      message.error('加载工作流失败');
    }
  };

  const fetchExecutions = async () => {
    setLoading(true);
    try {
      const data = await executionApi.list(selectedWorkflow);
      setExecutions(data);
      setStats({
        total: data.length,
        running: data.filter(e => e.status === 'RUNNING').length,
        success: data.filter(e => e.status === 'SUCCESS').length,
        failed: data.filter(e => e.status === 'FAILED').length,
      });
    } catch (err) {
      message.error('加载执行列表失败');
    } finally {
      setLoading(false);
    }
  };

  const handleRetry = async (executionId) => {
    try {
      await executionApi.retry(executionId);
      message.success('已重新执行');
      fetchExecutions();
    } catch (err) {
      message.error('重试失败');
    }
  };

  const handleCancel = async (executionId) => {
    try {
      await executionApi.cancel(executionId);
      message.success('已取消执行');
      fetchExecutions();
    } catch (err) {
      message.error('取消失败');
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

  const columns = [
    {
      title: '执行ID',
      dataIndex: 'executionId',
      key: 'executionId',
      width: 140,
      render: (id) => <code style={{ color: '#1890ff' }}>{id}</code>,
    },
    {
      title: '工作流ID',
      dataIndex: 'workflowId',
      key: 'workflowId',
      width: 100,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: getStatusTag,
    },
    {
      title: '触发方式',
      dataIndex: 'triggerType',
      key: 'triggerType',
      width: 120,
      render: (type) => TriggerTypeLabels[type] || type,
    },
    {
      title: '任务数',
      key: 'taskCount',
      width: 100,
      render: (_, record) => record.taskExecutions?.length || 0,
    },
    {
      title: '开始时间',
      dataIndex: 'startedAt',
      key: 'startedAt',
      width: 180,
    },
    {
      title: '结束时间',
      dataIndex: 'finishedAt',
      key: 'finishedAt',
      width: 180,
    },
    {
      title: '操作',
      key: 'action',
      width: 200,
      render: (_, record) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            onClick={() => navigate(`/executions/${record.executionId}`)}
          >
            <EyeOutlined /> 详情
          </Button>
          {record.status === 'FAILED' && (
            <Button
              type="link"
              size="small"
              onClick={() => handleRetry(record.executionId)}
            >
              <ReloadOutlined /> 重试
            </Button>
          )}
          {(record.status === 'RUNNING' || record.status === 'PENDING') && (
            <Button
              type="link"
              size="small"
              danger
              onClick={() => handleCancel(record.executionId)}
            >
              <StopOutlined /> 取消
            </Button>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="总执行数"
              value={stats.total}
              prefix={<RocketOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="运行中"
              value={stats.running}
              valueStyle={{ color: '#faad14' }}
              prefix={<ClockCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="成功"
              value={stats.success}
              valueStyle={{ color: '#52c41a' }}
              prefix={<CheckCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="失败"
              value={stats.failed}
              valueStyle={{ color: '#ff4d4f' }}
              prefix={<CloseCircleOutlined />}
            />
          </Card>
        </Col>
      </Row>

      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Select
          style={{ width: 250 }}
          placeholder="选择工作流"
          allowClear
          onChange={setSelectedWorkflow}
        >
          {workflows.map(wf => (
            <Select.Option key={wf.id} value={wf.id}>{wf.name}</Select.Option>
          ))}
        </Select>
        <Button icon={<ReloadOutlined />} onClick={fetchExecutions}>刷新</Button>
      </div>

      <Table
        columns={columns}
        dataSource={executions}
        rowKey="id"
        loading={loading}
        pagination={{ pageSize: 10 }}
      />
    </div>
  );
};

export default ExecutionList;
