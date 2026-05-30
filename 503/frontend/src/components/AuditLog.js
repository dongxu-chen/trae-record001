import React, { useState, useEffect } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Table,
  Tag,
  Button,
  Space,
  message,
  Select,
  Progress,
  Modal,
  Input,
  Form,
  Collapse,
  Typography,
} from 'antd';
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  CloseCircleOutlined,
  PlusOutlined,
  FileTextOutlined,
} from '@ant-design/icons';
import { auditAPI } from '../api/api';

const { TextArea } = Input;
const { Option } = Select;
const { Panel } = Collapse;
const { Text, Paragraph } = Typography;

function getStatusColor(status) {
  const colors = {
    completed: '#52c41a',
    pending: '#faad14',
    planned: '#1890ff',
    recommended: '#722ed1',
    failed: '#cf1322',
    executed: '#52c41a',
    generated: '#13c2c2',
  };
  return colors[status] || '#999';
}

function getStatusLabel(status) {
  const labels = {
    completed: '已完成',
    pending: '待处理',
    planned: '已规划',
    recommended: '建议',
    failed: '失败',
    executed: '已执行',
    generated: '已生成',
  };
  return labels[status] || status;
}

function getTypeLabel(type) {
  const labels = {
    hash_shard: 'Hash分片',
    hash_optimize: 'Hash优化',
    list_shard: 'List分片',
    list_optimize: 'List优化',
    set_shard: 'Set分片',
    set_optimize: 'Set优化',
    zset_shard: 'ZSet分片',
    zset_optimize: 'ZSet优化',
    string_shard: 'String分片',
    string_optimize: 'String优化',
    hot_key: '热点Key优化',
    command_replace: '命令替换',
    prediction_trend: '趋势预测',
    prediction_risk: '风险预测',
    manual: '手动操作',
  };
  return labels[type] || type;
}

function AuditLog() {
  const [loading, setLoading] = useState(false);
  const [logs, setLogs] = useState([]);
  const [statistics, setStatistics] = useState(null);
  const [pending, setPending] = useState([]);
  const [statusFilter, setStatusFilter] = useState(null);
  const [typeFilter, setTypeFilter] = useState(null);
  const [modalVisible, setModalVisible] = useState(false);
  const [form] = Form.useForm();

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [logsRes, statsRes, pendingRes] = await Promise.all([
        auditAPI.getLogs(statusFilter, typeFilter),
        auditAPI.getStatistics(),
        auditAPI.getPending(),
      ]);

      if (logsRes.data.success) {
        setLogs(logsRes.data.data || []);
      }
      if (statsRes.data.success) {
        setStatistics(statsRes.data.data);
      }
      if (pendingRes.data.success) {
        setPending(pendingRes.data.data || []);
      }
    } catch (error) {
      message.error('加载审计日志失败');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [statusFilter, typeFilter]);

  const handleCreateLog = async (values) => {
    try {
      await auditAPI.createLog({
        action_type: values.action_type,
        target_key: values.target_key,
        description: values.description,
        status: values.status,
        metadata: { notes: values.notes },
      });
      message.success('创建日志成功');
      setModalVisible(false);
      form.resetFields();
      loadData();
    } catch (error) {
      message.error('创建日志失败');
      console.error(error);
    }
  };

  const markAsCompleted = async (id) => {
    try {
      await auditAPI.executeLog(id, '标记完成');
      message.success('标记完成');
      loadData();
    } catch (error) {
      message.error('操作失败');
      console.error(error);
    }
  };

  const markAsFailed = async (id) => {
    try {
      await auditAPI.failLog(id, '标记失败');
      message.success('标记失败');
      loadData();
    } catch (error) {
      message.error('操作失败');
      console.error(error);
    }
  };

  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 70,
    },
    {
      title: '时间',
      dataIndex: 'datetime',
      key: 'datetime',
      width: 170,
    },
    {
      title: '类型',
      dataIndex: 'action_type',
      key: 'action_type',
      width: 120,
      render: (val) => <Tag color="purple">{getTypeLabel(val)}</Tag>,
      filters: [
        { text: 'Hash优化', value: 'hash_optimize' },
        { text: 'List优化', value: 'list_optimize' },
        { text: '热点Key', value: 'hot_key' },
        { text: '手动操作', value: 'manual' },
      ],
      onFilter: (value, record) => record.action_type === value,
    },
    {
      title: '目标Key',
      dataIndex: 'target_key',
      key: 'target_key',
      render: (text) => (text ? <Tag color="magenta">{text}</Tag> : '-'),
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (val) => (
        <Tag color={getStatusColor(val)} style={{ fontWeight: 'bold' }}>
          {getStatusLabel(val)}
        </Tag>
      ),
      filters: [
        { text: '待处理', value: 'pending' },
        { text: '已完成', value: 'completed' },
        { text: '失败', value: 'failed' },
        { text: '建议', value: 'recommended' },
      ],
      onFilter: (value, record) => record.status === value,
    },
    {
      title: '操作',
      key: 'action',
      width: 150,
      render: (_, record) => (
        <Space>
          {record.status !== 'completed' && record.status !== 'failed' && (
            <>
              <Button
                type="link"
                size="small"
                icon={<CheckCircleOutlined />}
                onClick={() => markAsCompleted(record.id)}
              >
                完成
              </Button>
              <Button
                type="link"
                size="small"
                danger
                icon={<CloseCircleOutlined />}
                onClick={() => markAsFailed(record.id)}
              >
                失败
              </Button>
            </>
          )}
        </Space>
      ),
    },
  ];

  const expandedRowRender = (record) => (
    <Card size="small" style={{ margin: '8px 0' }}>
      <Space direction="vertical" style={{ width: '100%' }}>
        {record.result && (
          <div>
            <Text strong>执行结果:</Text>
            <Paragraph style={{ marginTop: 4 }}>{record.result}</Paragraph>
          </div>
        )}
        {record.completed_at && (
          <div>
            <Text strong>完成时间:</Text> {record.completed_at}
          </div>
        )}
        {record.metadata && Object.keys(record.metadata).length > 0 && (
          <div>
            <Text strong>元数据:</Text>
            <pre
              style={{
                background: '#f5f5f5',
                padding: 12,
                borderRadius: 4,
                marginTop: 8,
                fontSize: 12,
                whiteSpace: 'pre-wrap',
              }}
            >
              {JSON.stringify(record.metadata, null, 2)}
            </pre>
          </div>
        )}
      </Space>
    </Card>
  );

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
        <Space>
          <Select
            placeholder="过滤状态"
            allowClear
            style={{ width: 120 }}
            value={statusFilter}
            onChange={setStatusFilter}
          >
            <Option value="pending">待处理</Option>
            <Option value="completed">已完成</Option>
            <Option value="failed">失败</Option>
            <Option value="recommended">建议</Option>
          </Select>
          <Select
            placeholder="过滤类型"
            allowClear
            style={{ width: 150 }}
            value={typeFilter}
            onChange={setTypeFilter}
          >
            <Option value="hash_optimize">Hash优化</Option>
            <Option value="list_optimize">List优化</Option>
            <Option value="hot_key">热点Key</Option>
            <Option value="manual">手动操作</Option>
          </Select>
          <Button onClick={loadData} loading={loading}>
            刷新
          </Button>
        </Space>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalVisible(true)}>
          新建记录
        </Button>
      </div>

      {statistics && (
        <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
          <Col xs={24} sm={12} md={4}>
            <Card className="stat-card">
              <Statistic
                title="总记录数"
                value={statistics.total_entries}
                valueStyle={{ color: '#667eea' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={4}>
            <Card className="stat-card">
              <Statistic
                title="待处理"
                value={statistics.pending_actions}
                valueStyle={{ color: '#faad14' }}
                prefix={<ClockCircleOutlined />}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={4}>
            <Card className="stat-card">
              <Statistic
                title="已完成"
                value={statistics.completed_actions}
                valueStyle={{ color: '#52c41a' }}
                prefix={<CheckCircleOutlined />}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={4}>
            <Card className="stat-card">
              <Statistic
                title="失败"
                value={statistics.failed_actions}
                valueStyle={{ color: '#cf1322' }}
                prefix={<CloseCircleOutlined />}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={8}>
            <Card className="stat-card">
              <div style={{ display: 'flex', alignItems: 'center' }}>
                <div style={{ flex: 1 }}>
                  <Statistic
                    title="完成率"
                    value={statistics.completion_rate || 0}
                    suffix="%"
                    valueStyle={{ color: '#722ed1' }}
                  />
                </div>
                <Progress
                  type="circle"
                  percent={Math.round(statistics.completion_rate || 0)}
                  size={60}
                />
              </div>
            </Card>
          </Col>
        </Row>
      )}

      {pending.length > 0 && (
        <Card
          title="待处理优化项"
          style={{ marginBottom: 16 }}
          extra={<Tag color="orange">{pending.length} 项</Tag>}
        >
          <Collapse defaultActiveKey={[]}>
            {pending.slice(0, 5).map((item) => (
              <Panel
                header={
                  <Space>
                    <Tag color={getStatusColor(item.status)}>
                      {getStatusLabel(item.status)}
                    </Tag>
                    <Text strong>{item.target_key}</Text>
                    <Text type="secondary">{item.description}</Text>
                  </Space>
                }
                key={item.id}
              >
                <Space>
                  <Button
                    type="primary"
                    size="small"
                    icon={<CheckCircleOutlined />}
                    onClick={() => markAsCompleted(item.id)}
                  >
                    标记完成
                  </Button>
                  <Button
                    size="small"
                    danger
                    icon={<CloseCircleOutlined />}
                    onClick={() => markAsFailed(item.id)}
                  >
                    标记失败
                  </Button>
                </Space>
              </Panel>
            ))}
          </Collapse>
        </Card>
      )}

      <Card title="审计日志" className="table-container">
        <Table
          columns={columns}
          dataSource={logs}
          rowKey="id"
          loading={loading}
          expandable={{
            expandedRowRender,
            expandRowByClick: true,
          }}
          pagination={{
            pageSize: 20,
            showTotal: (total) => `共 ${total} 条记录`,
          }}
        />
      </Card>

      <Modal
        title="新建审计记录"
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        footer={null}
      >
        <Form form={form} layout="vertical" onFinish={handleCreateLog}>
          <Form.Item
            name="action_type"
            label="操作类型"
            rules={[{ required: true }]}
          >
            <Select placeholder="请选择操作类型">
              <Option value="manual">手动操作</Option>
              <Option value="hash_optimize">Hash优化</Option>
              <Option value="list_optimize">List优化</Option>
              <Option value="hot_key">热点Key处理</Option>
              <Option value="command_replace">命令替换</Option>
              <Option value="config_change">配置变更</Option>
            </Select>
          </Form.Item>
          <Form.Item name="target_key" label="目标Key">
            <Input placeholder="请输入目标Key" />
          </Form.Item>
          <Form.Item
            name="description"
            label="描述"
            rules={[{ required: true }]}
          >
            <Input placeholder="请输入操作描述" />
          </Form.Item>
          <Form.Item name="status" label="状态">
            <Select defaultValue="pending">
              <Option value="pending">待处理</Option>
              <Option value="planned">已规划</Option>
              <Option value="completed">已完成</Option>
            </Select>
          </Form.Item>
          <Form.Item name="notes" label="备注">
            <TextArea rows={3} placeholder="请输入备注信息" />
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                创建
              </Button>
              <Button onClick={() => setModalVisible(false)}>取消</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}

export default AuditLog;
