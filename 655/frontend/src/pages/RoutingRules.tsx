import React, { useEffect, useState } from 'react';
import {
  Card, Tabs, Table, Tag, Button, Space, Modal, Form, Input, InputNumber,
  Select, message, Popconfirm, Divider, Row, Col, Slider, Tooltip,
} from 'antd';
import {
  PlusOutlined, DeleteOutlined, ReloadOutlined, ThunderboltOutlined,
  CopyOutlined, ExperimentOutlined,
} from '@ant-design/icons';
import { routingAPI } from '../services/api';
import type { RoutingRule } from '../types';

const { TabPane } = Tabs;
const { Option } = Select;

const typeTagMap: Record<string, { color: string; label: string }> = {
  weight: { color: 'blue', label: '权重路由' },
  header: { color: 'green', label: 'Header路由' },
  mirror: { color: 'purple', label: '流量镜像' },
  fault: { color: 'red', label: '故障注入' },
};

const RoutingRules: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [rules, setRules] = useState<RoutingRule[]>([]);
  const [namespace, setNamespace] = useState('default');
  const [modalVisible, setModalVisible] = useState(false);
  const [modalType, setModalType] = useState<string>('weight');
  const [form] = Form.useForm();

  useEffect(() => {
    fetchRules();
  }, [namespace]);

  const fetchRules = async () => {
    setLoading(true);
    try {
      const res = await routingAPI.getRoutingRules(namespace);
      setRules(res.data?.rules || []);
    } catch {
      message.error('获取路由规则失败');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await routingAPI.deleteRoutingRule(namespace, id);
      message.success('规则已删除');
      fetchRules();
    } catch {
      message.error('删除失败');
    }
  };

  const openCreateModal = (type: string) => {
    setModalType(type);
    setModalVisible(true);
    form.resetFields();

    if (type === 'weight') {
      form.setFieldsValue({
        subsets: [
          { subsetName: 'v1', weight: 80, version: 'v1' },
          { subsetName: 'v2', weight: 20, version: 'v2' },
        ],
      });
    }
    if (type === 'fault') {
      form.setFieldsValue({ percentage: 50 });
    }
    if (type === 'mirror') {
      form.setFieldsValue({ percentage: 100 });
    }
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      let apiCall;

      switch (modalType) {
        case 'weight':
          apiCall = routingAPI.createWeightRouting(values);
          break;
        case 'header':
          apiCall = routingAPI.createHeaderRouting(values);
          break;
        case 'mirror':
          apiCall = routingAPI.createTrafficMirror(values);
          break;
        case 'fault':
          apiCall = routingAPI.createFaultInjection(values);
          break;
        default:
          return;
      }

      await apiCall;
      message.success('路由规则创建成功，已热更新至Istio');
      setModalVisible(false);
      fetchRules();
    } catch (err: any) {
      if (err.errorFields) return;
      message.error(err.response?.data?.error || '创建失败');
    }
  };

  const columns = [
    { title: '规则名称', dataIndex: 'name', key: 'name', width: 180 },
    {
      title: '类型', dataIndex: 'type', key: 'type', width: 120,
      render: (type: string) => {
        const tag = typeTagMap[type] || { color: 'default', label: type };
        return <Tag color={tag.color}>{tag.label}</Tag>;
      },
    },
    { title: '服务', dataIndex: 'serviceName', key: 'serviceName', width: 160 },
    { title: '命名空间', dataIndex: 'namespace', key: 'namespace', width: 120 },
    {
      title: '状态', dataIndex: 'status', key: 'status', width: 100,
      render: (status: string) => (
        <Tag color={status === 'active' ? 'success' : 'default'}>
          {status === 'active' ? '活跃' : '禁用'}
        </Tag>
      ),
    },
    {
      title: '更新时间', dataIndex: 'updatedAt', key: 'updatedAt', width: 180,
      render: (v: string) => (v ? new Date(v).toLocaleString('zh-CN') : '-'),
    },
    {
      title: '操作', key: 'action', width: 120,
      render: (_: any, record: RoutingRule) => (
        <Popconfirm title="确定删除此规则？" onConfirm={() => handleDelete(record.id)}>
          <Button type="link" danger icon={<DeleteOutlined />} size="small">删除</Button>
        </Popconfirm>
      ),
    },
  ];

  const renderWeightForm = () => (
    <>
      <Form.Item name="name" label="规则名称" rules={[{ required: true, message: '请输入规则名称' }]}>
        <Input placeholder="例: product-canary" />
      </Form.Item>
      <Form.Item name="namespace" label="命名空间" initialValue="default" rules={[{ required: true }]}>
        <Select><Option value="default">default</Option><Option value="production">production</Option><Option value="staging">staging</Option></Select>
      </Form.Item>
      <Form.Item name="serviceName" label="服务名称" rules={[{ required: true, message: '请输入服务名称' }]}>
        <Input placeholder="例: product-service" />
      </Form.Item>
      <Form.List name="subsets">
        {(fields, { add, remove }) => (
          <>
            {fields.map(({ key, name, ...restField }) => (
              <Row key={key} gutter={8} align="middle">
                <Col span={7}>
                  <Form.Item {...restField} name={[name, 'subsetName']} label={name === 0 ? '子集名称' : ''} rules={[{ required: true }]}>
                    <Input placeholder="v1" />
                  </Form.Item>
                </Col>
                <Col span={7}>
                  <Form.Item {...restField} name={[name, 'weight']} label={name === 0 ? '权重(%)' : ''} rules={[{ required: true }]}>
                    <InputNumber min={0} max={100} style={{ width: '100%' }} />
                  </Form.Item>
                </Col>
                <Col span={7}>
                  <Form.Item {...restField} name={[name, 'version']} label={name === 0 ? '版本' : ''}>
                    <Input placeholder="v1" />
                  </Form.Item>
                </Col>
                <Col span={3}>
                  {fields.length > 1 && (
                    <Button type="link" danger onClick={() => remove(name)} icon={<DeleteOutlined />} />
                  )}
                </Col>
              </Row>
            ))}
            <Form.Item>
              <Button type="dashed" onClick={() => add()} block icon={<PlusOutlined />}>
                添加子集
              </Button>
            </Form.Item>
          </>
        )}
      </Form.List>
    </>
  );

  const renderHeaderForm = () => (
    <>
      <Form.Item name="name" label="规则名称" rules={[{ required: true, message: '请输入规则名称' }]}>
        <Input placeholder="例: canary-by-header" />
      </Form.Item>
      <Form.Item name="namespace" label="命名空间" initialValue="default" rules={[{ required: true }]}>
        <Select><Option value="default">default</Option><Option value="production">production</Option><Option value="staging">staging</Option></Select>
      </Form.Item>
      <Form.Item name="serviceName" label="服务名称" rules={[{ required: true, message: '请输入服务名称' }]}>
        <Input placeholder="例: product-service" />
      </Form.Item>
      <Form.Item name="targetSubset" label="目标子集" rules={[{ required: true, message: '请输入目标子集' }]}>
        <Input placeholder="例: v2" />
      </Form.Item>
      <Divider>Header匹配规则</Divider>
      <Form.List name="matchRules">
        {(fields, { add, remove }) => (
          <>
            {fields.map(({ key, name, ...restField }) => (
              <Row key={key} gutter={8}>
                <Col span={8}>
                  <Form.Item {...restField} name={[name, 'headerName']} label={name === 0 ? 'Header名' : ''} rules={[{ required: true }]}>
                    <Input placeholder="x-canary" />
                  </Form.Item>
                </Col>
                <Col span={6}>
                  <Form.Item {...restField} name={[name, 'matchType']} label={name === 0 ? '匹配方式' : ''} initialValue="exact" rules={[{ required: true }]}>
                    <Select><Option value="exact">精确匹配</Option><Option value="prefix">前缀匹配</Option><Option value="regex">正则匹配</Option></Select>
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item {...restField} name={[name, 'value']} label={name === 0 ? '值' : ''} rules={[{ required: true }]}>
                    <Input placeholder="true" />
                  </Form.Item>
                </Col>
                <Col span={2}>
                  {fields.length > 1 && (
                    <Button type="link" danger onClick={() => remove(name)} icon={<DeleteOutlined />} style={{ marginTop: name === 0 ? 30 : 0 }} />
                  )}
                </Col>
              </Row>
            ))}
            <Form.Item>
              <Button type="dashed" onClick={() => add()} block icon={<PlusOutlined />}>添加匹配规则</Button>
            </Form.Item>
          </>
        )}
      </Form.List>
    </>
  );

  const renderMirrorForm = () => (
    <>
      <Form.Item name="name" label="规则名称" rules={[{ required: true }]}>
        <Input placeholder="例: mirror-to-v2" />
      </Form.Item>
      <Form.Item name="namespace" label="命名空间" initialValue="default" rules={[{ required: true }]}>
        <Select><Option value="default">default</Option><Option value="production">production</Option></Select>
      </Form.Item>
      <Form.Item name="sourceService" label="源服务" rules={[{ required: true }]}>
        <Input placeholder="例: product-service" />
      </Form.Item>
      <Form.Item name="mirrorService" label="镜像目标服务" rules={[{ required: true }]}>
        <Input placeholder="例: product-service-v2" />
      </Form.Item>
      <Form.Item name="mirrorSubset" label="镜像子集">
        <Input placeholder="可选，例: v2" />
      </Form.Item>
      <Form.Item name="mirrorPort" label="镜像端口">
        <InputNumber min={1} max={65535} style={{ width: '100%' }} placeholder="可选" />
      </Form.Item>
      <Form.Item name="percentage" label="镜像百分比" rules={[{ required: true }]}>
        <Slider marks={{ 0: '0%', 25: '25%', 50: '50%', 75: '75%', 100: '100%' }} />
      </Form.Item>
    </>
  );

  const renderFaultForm = () => (
    <>
      <Form.Item name="name" label="规则名称" rules={[{ required: true }]}>
        <Input placeholder="例: delay-fault-test" />
      </Form.Item>
      <Form.Item name="namespace" label="命名空间" initialValue="default" rules={[{ required: true }]}>
        <Select><Option value="default">default</Option><Option value="production">production</Option></Select>
      </Form.Item>
      <Form.Item name="serviceName" label="目标服务" rules={[{ required: true }]}>
        <Input placeholder="例: product-service" />
      </Form.Item>
      <Form.Item name="faultType" label="故障类型" rules={[{ required: true }]}>
        <Select><Option value="delay">延迟注入</Option><Option value="abort">中断注入</Option></Select>
      </Form.Item>
      <Form.Item name="percentage" label="注入百分比" rules={[{ required: true }]}>
        <Slider marks={{ 0: '0%', 25: '25%', 50: '50%', 75: '75%', 100: '100%' }} />
      </Form.Item>
      <Form.Item noStyle shouldUpdate={(prev, cur) => prev.faultType !== cur.faultType}>
        {({ getFieldValue }) =>
          getFieldValue('faultType') === 'delay' ? (
            <Form.Item name={['delay', 'fixedDelay']} label="延迟时长" rules={[{ required: true }]}>
              <Input placeholder="例: 5s, 500ms" />
            </Form.Item>
          ) : getFieldValue('faultType') === 'abort' ? (
            <Form.Item name={['abort', 'httpStatus']} label="HTTP状态码" rules={[{ required: true }]}>
              <Select>
                <Option value={400}>400 Bad Request</Option>
                <Option value={403}>403 Forbidden</Option>
                <Option value={404}>404 Not Found</Option>
                <Option value={500}>500 Internal Server Error</Option>
                <Option value={503}>503 Service Unavailable</Option>
              </Select>
            </Form.Item>
          ) : null
        }
      </Form.Item>
    </>
  );

  const formMap: Record<string, () => React.ReactNode> = {
    weight: renderWeightForm,
    header: renderHeaderForm,
    mirror: renderMirrorForm,
    fault: renderFaultForm,
  };

  const titleMap: Record<string, string> = {
    weight: '创建权重路由',
    header: '创建Header路由',
    mirror: '创建流量镜像',
    fault: '创建故障注入',
  };

  return (
    <div>
      <Card
        title="路由规则管理"
        extra={
          <Space>
            <Select value={namespace} onChange={setNamespace} style={{ width: 140 }}>
              <Option value="default">default</Option>
              <Option value="production">production</Option>
              <Option value="staging">staging</Option>
            </Select>
            <Button icon={<ReloadOutlined />} onClick={fetchRules}>刷新</Button>
          </Space>
        }
      >
        <Tabs defaultActiveKey="all">
          <TabPane tab="全部规则" key="all">
            <Space style={{ marginBottom: 16 }} wrap>
              <Button type="primary" icon={<ThunderboltOutlined />} onClick={() => openCreateModal('weight')}>权重路由</Button>
              <Button style={{ background: '#52c41a', borderColor: '#52c41a', color: '#fff' }} icon={<CopyOutlined />} onClick={() => openCreateModal('header')}>Header路由</Button>
              <Button style={{ background: '#722ed1', borderColor: '#722ed1', color: '#fff' }} icon={<CopyOutlined />} onClick={() => openCreateModal('mirror')}>流量镜像</Button>
              <Button danger icon={<ExperimentOutlined />} onClick={() => openCreateModal('fault')}>故障注入</Button>
            </Space>
            <Table
              columns={columns}
              dataSource={rules}
              rowKey="id"
              loading={loading}
              pagination={{ pageSize: 10 }}
            />
          </TabPane>
          <TabPane tab="权重路由" key="weight">
            <Table columns={columns} dataSource={rules.filter((r) => r.type === 'weight')} rowKey="id" loading={loading} pagination={{ pageSize: 10 }} />
          </TabPane>
          <TabPane tab="Header路由" key="header">
            <Table columns={columns} dataSource={rules.filter((r) => r.type === 'header')} rowKey="id" loading={loading} pagination={{ pageSize: 10 }} />
          </TabPane>
          <TabPane tab="流量镜像" key="mirror">
            <Table columns={columns} dataSource={rules.filter((r) => r.type === 'mirror')} rowKey="id" loading={loading} pagination={{ pageSize: 10 }} />
          </TabPane>
          <TabPane tab="故障注入" key="fault">
            <Table columns={columns} dataSource={rules.filter((r) => r.type === 'fault')} rowKey="id" loading={loading} pagination={{ pageSize: 10 }} />
          </TabPane>
        </Tabs>
      </Card>

      <Modal
        title={titleMap[modalType]}
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={() => setModalVisible(false)}
        width={640}
        okText="创建并热更新"
        cancelText="取消"
      >
        <Form form={form} layout="vertical">
          {formMap[modalType]?.()}
        </Form>
      </Modal>
    </div>
  );
};

export default RoutingRules;
