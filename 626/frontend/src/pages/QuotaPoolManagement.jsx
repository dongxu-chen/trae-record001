import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Modal,
  Form,
  Input,
  InputNumber,
  Select,
  message,
  Popconfirm,
  Tag,
  Row,
  Col,
  Statistic,
  Progress,
  Descriptions,
} from 'antd';
import {
  PlusOutlined,
  TeamOutlined,
  DeleteOutlined,
  UserAddOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { poolApi, tenantApi } from '../services/api';

const { Option } = Select;

const QuotaPoolManagement = () => {
  const [pools, setPools] = useState([]);
  const [tenants, setTenants] = useState([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [memberModalVisible, setMemberModalVisible] = useState(false);
  const [statsModalVisible, setStatsModalVisible] = useState(false);
  const [selectedPool, setSelectedPool] = useState(null);
  const [poolStats, setPoolStats] = useState(null);
  const [members, setMembers] = useState([]);
  const [form] = Form.useForm();
  const [memberForm] = Form.useForm();

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [poolsResult, tenantsResult] = await Promise.all([
        poolApi.list(),
        tenantApi.list(),
      ]);
      setPools(poolsResult.data || []);
      setTenants(tenantsResult.data || []);
    } catch (error) {
      message.error('加载数据失败');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = () => {
    form.resetFields();
    setModalVisible(true);
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      await poolApi.create(values);
      message.success('创建共享池成功');
      setModalVisible(false);
      loadData();
    } catch (error) {
      if (!error.errorFields) {
        message.error('创建失败');
      }
    }
  };

  const handleDelete = async (poolId) => {
    try {
      await poolApi.delete(poolId);
      message.success('删除成功');
      loadData();
    } catch (error) {
      message.error('删除失败');
    }
  };

  const handleAddMember = (pool) => {
    setSelectedPool(pool);
    memberForm.resetFields();
    setMemberModalVisible(true);
  };

  const handleAddMemberSubmit = async () => {
    try {
      const values = await memberForm.validateFields();
      await poolApi.addMember(selectedPool.poolId, values);
      message.success('添加成员成功');
      setMemberModalVisible(false);
      loadMembers(selectedPool.poolId);
    } catch (error) {
      if (!error.errorFields) {
        message.error('添加失败');
      }
    }
  };

  const handleRemoveMember = async (poolId, tenantId) => {
    try {
      await poolApi.removeMember(poolId, tenantId);
      message.success('移除成员成功');
      loadMembers(poolId);
    } catch (error) {
      message.error('移除失败');
    }
  };

  const loadMembers = async (poolId) => {
    try {
      const result = await poolApi.getMembers(poolId);
      setMembers(result.data || []);
    } catch (error) {
      message.error('加载成员失败');
    }
  };

  const handleViewStats = async (pool) => {
    setSelectedPool(pool);
    try {
      const result = await poolApi.getStats(pool.poolId);
      setPoolStats(result.data);
      loadMembers(pool.poolId);
      setStatsModalVisible(true);
    } catch (error) {
      message.error('加载统计失败');
    }
  };

  const getStrategyLabel = (strategy) => {
    const labels = {
      EQUAL: '均分',
      WEIGHTED: '加权',
      DEMAND_BASED: '按需',
      FAIR_QUEUE: '公平队列',
    };
    return labels[strategy] || strategy;
  };

  const columns = [
    {
      title: '池名称',
      dataIndex: 'poolName',
      key: 'poolName',
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: '分钟容量',
      dataIndex: 'minuteCapacity',
      key: 'minuteCapacity',
    },
    {
      title: '小时容量',
      dataIndex: 'hourCapacity',
      key: 'hourCapacity',
    },
    {
      title: '日容量',
      dataIndex: 'dayCapacity',
      key: 'dayCapacity',
    },
    {
      title: '分配策略',
      dataIndex: 'allocationStrategy',
      key: 'allocationStrategy',
      render: (s) => <Tag color="blue">{getStrategyLabel(s)}</Tag>,
    },
    {
      title: '成员数',
      dataIndex: 'memberTenants',
      key: 'memberCount',
      render: (m) => m?.size || m?.length || 0,
    },
    {
      title: '状态',
      dataIndex: 'enabled',
      key: 'enabled',
      render: (e) => <Tag color={e ? 'green' : 'default'}>{e ? '启用' : '禁用'}</Tag>,
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space size="small">
          <Button type="link" icon={<TeamOutlined />} onClick={() => handleViewStats(record)}>
            详情
          </Button>
          <Button type="link" icon={<UserAddOutlined />} onClick={() => handleAddMember(record)}>
            加成员
          </Button>
          <Popconfirm
            title="确定删除该共享池？"
            onConfirm={() => handleDelete(record.poolId)}
          >
            <Button type="link" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Card>
        <Space style={{ marginBottom: 16 }}>
          <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
            创建共享池
          </Button>
          <Button icon={<ReloadOutlined />} onClick={loadData}>
            刷新
          </Button>
        </Space>

        <Table
          columns={columns}
          dataSource={pools}
          rowKey="poolId"
          loading={loading}
        />
      </Card>

      <Modal title="创建配额共享池" open={modalVisible} onOk={handleSubmit} onCancel={() => setModalVisible(false)} width={600}>
        <Form form={form} layout="vertical">
          <Form.Item name="poolName" label="池名称" rules={[{ required: true }]}>
            <Input placeholder="请输入池名称" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={3} placeholder="请输入描述" />
          </Form.Item>
          <Form.Item label="容量配置">
            <Space wrap>
              <Form.Item name="minuteCapacity" noStyle rules={[{ required: true }]}>
                <InputNumber min={1} placeholder="分钟" addonBefore="分钟" />
              </Form.Item>
              <Form.Item name="hourCapacity" noStyle rules={[{ required: true }]}>
                <InputNumber min={1} placeholder="小时" addonBefore="小时" />
              </Form.Item>
              <Form.Item name="dayCapacity" noStyle rules={[{ required: true }]}>
                <InputNumber min={1} placeholder="日" addonBefore="日" />
              </Form.Item>
            </Space>
          </Form.Item>
          <Form.Item label="单成员上限">
            <Space wrap>
              <Form.Item name="maxPerMemberMinute" noStyle>
                <InputNumber min={0} placeholder="分钟上限" addonBefore="分钟" />
              </Form.Item>
              <Form.Item name="maxPerMemberHour" noStyle>
                <InputNumber min={0} placeholder="小时上限" addonBefore="小时" />
              </Form.Item>
              <Form.Item name="maxPerMemberDay" noStyle>
                <InputNumber min={0} placeholder="日上限" addonBefore="日" />
              </Form.Item>
            </Space>
          </Form.Item>
          <Form.Item name="allocationStrategy" label="分配策略" rules={[{ required: true }]}>
            <Select>
              <Option value="EQUAL">均分</Option>
              <Option value="WEIGHTED">加权分配</Option>
              <Option value="DEMAND_BASED">按需分配</Option>
              <Option value="FAIR_QUEUE">公平队列</Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>

      <Modal title="添加成员" open={memberModalVisible} onOk={handleAddMemberSubmit} onCancel={() => setMemberModalVisible(false)}>
        <Form form={memberForm} layout="vertical">
          <Form.Item name="tenantId" label="选择租户" rules={[{ required: true }]}>
            <Select placeholder="请选择租户">
              {tenants.map(t => (
                <Option key={t.tenantId} value={t.tenantId}>
                  {t.tenantName} ({t.tenantId})
                </Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item name="weight" label="权重">
            <InputNumber min={0.1} max={10} step={0.1} style={{ width: '100%' }} placeholder="用于加权分配" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="共享池详情"
        open={statsModalVisible}
        onCancel={() => setStatsModalVisible(false)}
        footer={null}
        width={900}
      >
        {selectedPool && poolStats && (
          <Space direction="vertical" size="large" style={{ width: '100%' }}>
            <Descriptions title="基本信息" bordered size="small" column={3}>
              <Descriptions.Item label="池名称">{selectedPool.poolName}</Descriptions.Item>
              <Descriptions.Item label="分配策略">{getStrategyLabel(selectedPool.allocationStrategy)}</Descriptions.Item>
              <Descriptions.Item label="成员数">{members.length}</Descriptions.Item>
            </Descriptions>

            <Card title="池配额使用" size="small">
              <Row gutter={[16, 16]}>
                <Col span={8}>
                  <Statistic title="分钟使用" value={`${poolStats.usage?.minuteUsed || 0}/${selectedPool.minuteCapacity}`} />
                  <Progress percent={Math.round((poolStats.usage?.minuteUsageRate || 0) * 100)} />
                </Col>
                <Col span={8}>
                  <Statistic title="小时使用" value={`${poolStats.usage?.hourUsed || 0}/${selectedPool.hourCapacity}`} />
                  <Progress percent={Math.round((poolStats.usage?.hourUsageRate || 0) * 100)} />
                </Col>
                <Col span={8}>
                  <Statistic title="日使用" value={`${poolStats.usage?.dayUsed || 0}/${selectedPool.dayCapacity}`} />
                  <Progress percent={Math.round((poolStats.usage?.dayUsageRate || 0) * 100)} />
                </Col>
              </Row>
            </Card>

            <Card
              title="成员列表"
              size="small"
              extra={
                <Button size="small" type="primary" icon={<UserAddOutlined />} onClick={() => setMemberModalVisible(true)}>
                  添加
                </Button>
              }
            >
              <Table
                dataSource={members}
                rowKey="tenantId"
                size="small"
                pagination={false}
                columns={[
                  { title: '租户ID', dataIndex: 'tenantId' },
                  { title: '权重', dataIndex: 'weight' },
                  { title: '分钟已用', dataIndex: 'minuteUsed' },
                  { title: '小时已用', dataIndex: 'hourUsed' },
                  { title: '日已用', dataIndex: 'dayUsed' },
                  {
                    title: '操作',
                    render: (_, record) => (
                      <Popconfirm title="确定移除？" onConfirm={() => handleRemoveMember(selectedPool.poolId, record.tenantId)}>
                        <Button type="link" danger size="small">移除</Button>
                      </Popconfirm>
                    ),
                  },
                ]}
              />
            </Card>
          </Space>
        )}
      </Modal>
    </Space>
  );
};

export default QuotaPoolManagement;
