import React, { useState, useEffect } from 'react';
import {
  Card, Table, Button, Modal, Form, Input, InputNumber, Select, Switch,
  Tag, Space, message, Popconfirm, Row, Col, Descriptions
} from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import { strategyApi } from '../services/api';

const { Option } = Select;

const strategyTypes = [
  { value: 'DIRECT_REJECT', label: '直接拒绝' },
  { value: 'WARM_UP', label: '预热模式' },
  { value: 'RATE_LIMITER', label: '排队等待' },
  { value: 'CIRCUIT_BREAKER', label: '熔断降级' },
  { value: 'ADAPTIVE', label: '自适应保护' },
];

const Strategy = () => {
  const [strategies, setStrategies] = useState([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingStrategy, setEditingStrategy] = useState(null);
  const [detailVisible, setDetailVisible] = useState(false);
  const [selectedStrategy, setSelectedStrategy] = useState(null);
  const [form] = Form.useForm();

  useEffect(() => {
    loadStrategies();
  }, []);

  const loadStrategies = async () => {
    setLoading(true);
    try {
      const res = await strategyApi.list();
      setStrategies(res.data?.data || []);
    } catch (e) {
      message.error('加载策略列表失败');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = () => {
    setEditingStrategy(null);
    form.resetFields();
    form.setFieldsValue({
      type: 'DIRECT_REJECT',
      threshold: 50,
      timeoutMs: 5000,
      circuitBreakerRatio: 0.5,
      circuitBreakerTimeoutMs: 10000,
      warmupPeriodSec: 10,
      maxQueueingTimeMs: 500,
      enabled: true,
    });
    setModalVisible(true);
  };

  const handleEdit = (record) => {
    setEditingStrategy(record);
    form.setFieldsValue(record);
    setModalVisible(true);
  };

  const handleDelete = async (id) => {
    try {
      await strategyApi.delete(id);
      message.success('删除成功');
      loadStrategies();
    } catch (e) {
      message.error('删除失败');
    }
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      if (editingStrategy) {
        await strategyApi.update(editingStrategy.id, values);
        message.success('更新成功');
      } else {
        await strategyApi.create(values);
        message.success('创建成功');
      }
      setModalVisible(false);
      loadStrategies();
    } catch (e) {
      if (e.errorFields) return;
      message.error('操作失败');
    }
  };

  const showDetail = (record) => {
    setSelectedStrategy(record);
    setDetailVisible(true);
  };

  const typeLabelMap = {};
  strategyTypes.forEach(t => { typeLabelMap[t.value] = t.label; });

  const columns = [
    { title: '策略名称', dataIndex: 'name', key: 'name', width: 160 },
    {
      title: '策略类型',
      dataIndex: 'type',
      key: 'type',
      width: 120,
      render: (type) => <Tag color="blue">{typeLabelMap[type] || type}</Tag>,
    },
    { title: '限流阈值(QPS)', dataIndex: 'threshold', key: 'threshold', width: 130 },
    { title: '超时(ms)', dataIndex: 'timeoutMs', key: 'timeoutMs', width: 100 },
    {
      title: '状态',
      dataIndex: 'enabled',
      key: 'enabled',
      width: 80,
      render: (enabled) => <Tag color={enabled ? 'green' : 'default'}>{enabled ? '启用' : '禁用'}</Tag>,
    },
    {
      title: '操作',
      key: 'action',
      width: 200,
      render: (_, record) => (
        <Space>
          <Button type="link" size="small" onClick={() => showDetail(record)}>详情</Button>
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)}>编辑</Button>
          <Popconfirm title="确定删除此策略？" onConfirm={() => handleDelete(record.id)}>
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Card
        title="限流降级策略"
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
            新建策略
          </Button>
        }
      >
        <Table
          columns={columns}
          dataSource={strategies}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 10 }}
          locale={{ emptyText: '暂无策略，请点击"新建策略"创建' }}
        />
      </Card>

      <Modal
        title={editingStrategy ? '编辑策略' : '新建策略'}
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={() => setModalVisible(false)}
        width={640}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="name" label="策略名称" rules={[{ required: true, message: '请输入策略名称' }]}>
                <Input placeholder="输入策略名称" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="type" label="策略类型" rules={[{ required: true }]}>
                <Select>
                  {strategyTypes.map(t => (
                    <Option key={t.value} value={t.value}>{t.label}</Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="threshold" label="限流阈值 (QPS)" rules={[{ required: true }]}>
                <InputNumber min={1} max={100000} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="timeoutMs" label="超时时间 (ms)">
                <InputNumber min={100} max={60000} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="circuitBreakerRatio" label="熔断比例阈值">
                <InputNumber min={0} max={1} step={0.1} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="circuitBreakerTimeoutMs" label="熔断恢复时间 (ms)">
                <InputNumber min={1000} max={300000} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="warmupPeriodSec" label="预热时长 (秒)">
                <InputNumber min={1} max={300} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="maxQueueingTimeMs" label="最大排队时间 (ms)">
                <InputNumber min={0} max={10000} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item name="description" label="策略描述">
            <Input.TextArea rows={2} placeholder="描述策略用途和场景" />
          </Form.Item>

          <Form.Item name="fallbackResponse" label="降级响应内容">
            <Input.TextArea rows={2} placeholder='{"code":429,"message":"Rate limited"}' />
          </Form.Item>

          <Form.Item name="enabled" label="启用策略" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="策略详情"
        open={detailVisible}
        onCancel={() => setDetailVisible(false)}
        footer={null}
        width={600}
      >
        {selectedStrategy && (
          <Descriptions bordered column={2} size="small">
            <Descriptions.Item label="策略名称">{selectedStrategy.name}</Descriptions.Item>
            <Descriptions.Item label="策略类型">
              <Tag color="blue">{typeLabelMap[selectedStrategy.type] || selectedStrategy.type}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="限流阈值">{selectedStrategy.threshold} QPS</Descriptions.Item>
            <Descriptions.Item label="超时时间">{selectedStrategy.timeoutMs} ms</Descriptions.Item>
            <Descriptions.Item label="熔断比例">{selectedStrategy.circuitBreakerRatio}</Descriptions.Item>
            <Descriptions.Item label="熔断恢复时间">{selectedStrategy.circuitBreakerTimeoutMs} ms</Descriptions.Item>
            <Descriptions.Item label="预热时长">{selectedStrategy.warmupPeriodSec} s</Descriptions.Item>
            <Descriptions.Item label="最大排队时间">{selectedStrategy.maxQueueingTimeMs} ms</Descriptions.Item>
            <Descriptions.Item label="状态" span={2}>
              <Tag color={selectedStrategy.enabled ? 'green' : 'default'}>
                {selectedStrategy.enabled ? '启用' : '禁用'}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="描述" span={2}>
              {selectedStrategy.description || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="降级响应" span={2}>
              <code style={{ fontSize: 12 }}>{selectedStrategy.fallbackResponse || '-'}</code>
            </Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
    </div>
  );
};

export default Strategy;
