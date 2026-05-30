import { useState, useEffect } from 'react';
import {
  Table,
  Button,
  Input,
  Select,
  Tag,
  Space,
  Typography,
  Modal,
  message,
  Card,
  Row,
  Col,
  Form,
  InputNumber,
  Switch,
  Badge,
  Descriptions,
  Empty,
} from 'antd';
import {
  SearchOutlined,
  PlayCircleOutlined,
  StopOutlined,
  DeleteOutlined,
  EyeOutlined,
  PlusOutlined,
  BugOutlined,
  SyncOutlined,
  EditOutlined,
  PoweroffOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import type { ColumnsType } from 'antd/es/table';
import mockApi from '../api/mockApi';
import type { MockVersionConfig, MockType } from '../types';

const { Title } = Typography;
const { Option } = Select;
const { TextArea } = Input;

type VersionStatus = 'active' | 'deprecated' | 'offline' | 'draft';

interface ApiVersion {
  id: string;
  version: string;
  name: string;
  status: VersionStatus;
  apiCount: number;
  traffic: number;
  createTime: string;
  updateTime: string;
  description: string;
}

const mockData: ApiVersion[] = [
  {
    id: '1',
    version: 'v1.0.0',
    name: '用户服务 v1',
    status: 'active',
    apiCount: 12,
    traffic: 35,
    createTime: '2026-01-15 10:30:00',
    updateTime: '2026-05-20 14:20:00',
    description: '初始版本，提供基础用户管理功能',
  },
  {
    id: '2',
    version: 'v1.5.0',
    name: '用户服务 v1.5',
    status: 'deprecated',
    apiCount: 15,
    traffic: 5,
    createTime: '2026-02-20 09:15:00',
    updateTime: '2026-05-10 11:30:00',
    description: '增加批量操作功能，已废弃',
  },
  {
    id: '3',
    version: 'v2.0.0',
    name: '用户服务 v2',
    status: 'active',
    apiCount: 18,
    traffic: 30,
    createTime: '2026-03-01 16:45:00',
    updateTime: '2026-05-25 09:10:00',
    description: '重构版本，性能优化，支持新的认证机制',
  },
  {
    id: '4',
    version: 'v2.1.0',
    name: '订单服务 v2.1',
    status: 'active',
    apiCount: 10,
    traffic: 20,
    createTime: '2026-04-10 08:30:00',
    updateTime: '2026-05-26 16:40:00',
    description: '订单管理服务，新增支付集成',
  },
  {
    id: '5',
    version: 'v3.0.0-beta',
    name: '用户服务 v3 测试版',
    status: 'draft',
    apiCount: 22,
    traffic: 0,
    createTime: '2026-05-01 14:00:00',
    updateTime: '2026-05-27 10:00:00',
    description: '全新架构版本，支持微服务拆分，测试中',
  },
  {
    id: '6',
    version: 'v0.9.0',
    name: '旧版用户服务',
    status: 'offline',
    apiCount: 8,
    traffic: 0,
    createTime: '2025-12-01 10:00:00',
    updateTime: '2026-04-01 18:00:00',
    description: '早期版本，已下线',
  },
  {
    id: '7',
    version: 'v2.2.0',
    name: '商品服务 v2.2',
    status: 'active',
    apiCount: 8,
    traffic: 10,
    createTime: '2026-04-20 11:30:00',
    updateTime: '2026-05-24 15:20:00',
    description: '商品管理服务，支持库存管理',
  },
];

const statusMap: Record<VersionStatus, { text: string; color: string }> = {
  active: { text: '活跃', color: 'green' },
  deprecated: { text: '已废弃', color: 'orange' },
  offline: { text: '已下线', color: 'red' },
  draft: { text: '草稿', color: 'default' },
};

const mockTypeMap: Record<MockType, { text: string; color: string }> = {
  SUCCESS: { text: '成功', color: 'green' },
  DELAY: { text: '延迟', color: 'blue' },
  ERROR: { text: '错误', color: 'red' },
  CUSTOM: { text: '自定义', color: 'purple' },
};

export default function VersionList() {
  const navigate = useNavigate();
  const [searchText, setSearchText] = useState('');
  const [statusFilter, setStatusFilter] = useState<VersionStatus | 'all'>('all');
  const [data, setData] = useState<ApiVersion[]>(mockData);
  const [modalState, setModalState] = useState<{
    visible: boolean;
    action: 'publish' | 'deprecate' | 'offline' | null;
    record: ApiVersion | null;
  }>({ visible: false, action: null, record: null });
  const [mockModalVisible, setMockModalVisible] = useState(false);
  const [currentVersion, setCurrentVersion] = useState<ApiVersion | null>(null);
  const [mockConfigs, setMockConfigs] = useState<MockVersionConfig[]>([]);
  const [mockForm] = Form.useForm();
  const [mockFormVisible, setMockFormVisible] = useState(false);
  const [editingMockConfig, setEditingMockConfig] = useState<MockVersionConfig | null>(null);
  const [mockLoading, setMockLoading] = useState(false);

  const filteredData = data.filter((item) => {
    const matchesSearch =
      item.version.toLowerCase().includes(searchText.toLowerCase()) ||
      item.name.toLowerCase().includes(searchText.toLowerCase());
    const matchesStatus = statusFilter === 'all' || item.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const loadMockConfigs = async (versionId: string) => {
    setMockLoading(true);
    try {
      const configs = await mockApi.getByVersionId(versionId);
      setMockConfigs(configs);
    } catch (error) {
      message.error('加载Mock配置失败');
    } finally {
      setMockLoading(false);
    }
  };

  const openMockModal = (record: ApiVersion) => {
    setCurrentVersion(record);
    setMockModalVisible(true);
    loadMockConfigs(record.id);
  };

  const openMockForm = (config?: MockVersionConfig) => {
    setEditingMockConfig(config || null);
    if (config) {
      mockForm.setFieldsValue(config);
    } else {
      mockForm.resetFields();
      mockForm.setFieldsValue({
        method: 'GET',
        mockType: 'SUCCESS',
        delayMs: 0,
        errorCode: 200,
        enabled: true,
      });
    }
    setMockFormVisible(true);
  };

  const handleSaveMockConfig = async () => {
    try {
      const values = await mockForm.validateFields();
      if (editingMockConfig) {
        await mockApi.update(editingMockConfig.id!, {
          ...values,
          versionId: currentVersion!.id,
        });
        message.success('Mock配置更新成功');
      } else {
        await mockApi.create({
          ...values,
          versionId: currentVersion!.id,
        });
        message.success('Mock配置创建成功');
      }
      setMockFormVisible(false);
      loadMockConfigs(currentVersion!.id);
    } catch (error) {
      message.error('保存Mock配置失败');
    }
  };

  const handleDeleteMockConfig = async (config: MockVersionConfig) => {
    Modal.confirm({
      title: '确认删除',
      content: `确定要删除Mock配置 ${config.path} 吗？`,
      okText: '确认',
      cancelText: '取消',
      onOk: async () => {
        try {
          await mockApi.delete(config.id!);
          message.success('Mock配置删除成功');
          loadMockConfigs(currentVersion!.id);
        } catch (error) {
          message.error('删除Mock配置失败');
        }
      },
    });
  };

  const handleToggleMockConfig = async (config: MockVersionConfig, enabled: boolean) => {
    try {
      await mockApi.toggle(config.id!, enabled);
      message.success(`Mock配置已${enabled ? '启用' : '禁用'}`);
      loadMockConfigs(currentVersion!.id);
    } catch (error) {
      message.error('操作失败');
    }
  };

  const handleSyncMockConfig = async (config: MockVersionConfig) => {
    try {
      await mockApi.sync(config.id!);
      message.success('Mock配置已同步到网关');
    } catch (error) {
      message.error('同步失败');
    }
  };

  const handleAction = (action: 'publish' | 'deprecate' | 'offline', record: ApiVersion) => {
    setModalState({ visible: true, action, record });
  };

  const confirmAction = () => {
    if (!modalState.record || !modalState.action) return;

    const { id, version } = modalState.record;
    let newStatus: VersionStatus | null = null;
    let successMsg = '';

    switch (modalState.action) {
      case 'publish':
        newStatus = 'active';
        successMsg = `版本 ${version} 发布成功`;
        break;
      case 'deprecate':
        newStatus = 'deprecated';
        successMsg = `版本 ${version} 已标记为废弃`;
        break;
      case 'offline':
        newStatus = 'offline';
        successMsg = `版本 ${version} 已下线`;
        break;
    }

    if (newStatus) {
      setData((prev) =>
        prev.map((item) => (item.id === id ? { ...item, status: newStatus! } : item))
      );
      message.success(successMsg);
    }

    setModalState({ visible: false, action: null, record: null });
  };

  const getActionButton = (record: ApiVersion) => {
    const buttons: JSX.Element[] = [];

    if (record.status === 'draft') {
      buttons.push(
        <Button
          key="publish"
          type="link"
          icon={<PlayCircleOutlined />}
          onClick={() => handleAction('publish', record)}
        >
          发布
        </Button>
      );
    }

    if (record.status === 'active') {
      buttons.push(
        <Button
          key="deprecate"
          type="link"
          icon={<StopOutlined />}
          onClick={() => handleAction('deprecate', record)}
        >
          废弃
        </Button>
      );
    }

    if (record.status === 'deprecated') {
      buttons.push(
        <Button
          key="offline"
          type="link"
          danger
          icon={<DeleteOutlined />}
          onClick={() => handleAction('offline', record)}
        >
          下线
        </Button>
      );
    }

    buttons.push(
      <Button
        key="mock"
        type="link"
        icon={<BugOutlined />}
        onClick={() => openMockModal(record)}
      >
        Mock配置
      </Button>
    );

    buttons.push(
      <Button
        key="detail"
        type="link"
        icon={<EyeOutlined />}
        onClick={() => navigate(`/versions/${record.id}`)}
      >
        查看详情
      </Button>
    );

    return <Space>{buttons}</Space>;
  };

  const columns: ColumnsType<ApiVersion> = [
    {
      title: '版本号',
      dataIndex: 'version',
      key: 'version',
      width: 120,
      render: (text) => <code className="bg-gray-100 px-2 py-1 rounded">{text}</code>,
    },
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      width: 200,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: VersionStatus) => (
        <Tag color={statusMap[status].color}>{statusMap[status].text}</Tag>
      ),
    },
    {
      title: '接口数量',
      dataIndex: 'apiCount',
      key: 'apiCount',
      width: 100,
      render: (count) => <span>{count} 个</span>,
    },
    {
      title: '流量占比',
      dataIndex: 'traffic',
      key: 'traffic',
      width: 120,
      render: (traffic) => <span>{traffic}%</span>,
    },
    {
      title: 'Mock配置',
      key: 'mock',
      width: 100,
      render: (_, record) => {
        const hasMock = mockConfigs.some(c => c.versionId === record.id && c.enabled);
        return hasMock ? (
          <Badge status="success" text="已启用" />
        ) : (
          <Badge status="default" text="未配置" />
        );
      },
    },
    {
      title: '更新时间',
      dataIndex: 'updateTime',
      key: 'updateTime',
      width: 180,
    },
    {
      title: '操作',
      key: 'action',
      width: 300,
      render: (_, record) => getActionButton(record),
    },
  ];

  const mockColumns: ColumnsType<MockVersionConfig> = [
    {
      title: '路径',
      dataIndex: 'path',
      key: 'path',
      width: 200,
      render: (text) => <code className="text-xs">{text}</code>,
    },
    {
      title: '方法',
      dataIndex: 'method',
      key: 'method',
      width: 80,
      render: (method) => <Tag color="blue">{method}</Tag>,
    },
    {
      title: 'Mock类型',
      dataIndex: 'mockType',
      key: 'mockType',
      width: 100,
      render: (type: MockType) => (
        <Tag color={mockTypeMap[type].color}>{mockTypeMap[type].text}</Tag>
      ),
    },
    {
      title: '延迟(ms)',
      dataIndex: 'delayMs',
      key: 'delayMs',
      width: 100,
      render: (val) => val || 0,
    },
    {
      title: '状态码',
      dataIndex: 'errorCode',
      key: 'errorCode',
      width: 100,
    },
    {
      title: '状态',
      dataIndex: 'enabled',
      key: 'enabled',
      width: 80,
      render: (enabled, record) => (
        <Switch
          checked={enabled}
          onChange={(checked) => handleToggleMockConfig(record, checked)}
          size="small"
        />
      ),
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
            icon={<EditOutlined />}
            onClick={() => openMockForm(record)}
          >
            编辑
          </Button>
          <Button
            type="link"
            size="small"
            icon={<SyncOutlined />}
            onClick={() => handleSyncMockConfig(record)}
          >
            同步
          </Button>
          <Button
            type="link"
            size="small"
            danger
            icon={<DeleteOutlined />}
            onClick={() => handleDeleteMockConfig(record)}
          >
            删除
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div className="p-6 bg-gray-50 min-h-screen">
      <Card>
        <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
          <Col>
            <Title level={3} style={{ margin: 0 }}>
              版本列表
            </Title>
          </Col>
          <Col>
            <Button type="primary" icon={<PlusOutlined />}>
              新建版本
            </Button>
          </Col>
        </Row>

        <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
          <Col xs={24} sm={12} md={8}>
            <Input
              placeholder="搜索版本号或名称"
              prefix={<SearchOutlined />}
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              allowClear
            />
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Select
              style={{ width: '100%' }}
              placeholder="按状态筛选"
              value={statusFilter}
              onChange={(value) => setStatusFilter(value)}
              allowClear
            >
              <Option value="all">全部状态</Option>
              <Option value="active">活跃</Option>
              <Option value="deprecated">已废弃</Option>
              <Option value="offline">已下线</Option>
              <Option value="draft">草稿</Option>
            </Select>
          </Col>
        </Row>

        <Table
          columns={columns}
          dataSource={filteredData}
          rowKey="id"
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => `共 ${total} 条记录`,
          }}
        />

        <Modal
          title={
            modalState.action === 'publish'
              ? '确认发布'
              : modalState.action === 'deprecate'
              ? '确认废弃'
              : '确认下线'
          }
          open={modalState.visible}
          onOk={confirmAction}
          onCancel={() => setModalState({ visible: false, action: null, record: null })}
          okText="确认"
          cancelText="取消"
          okButtonProps={{ danger: modalState.action === 'offline' }}
        >
          <p>
            {modalState.action === 'publish' &&
              `确定要发布版本 ${modalState.record?.version} 吗？`}
            {modalState.action === 'deprecate' &&
              `确定要将版本 ${modalState.record?.version} 标记为废弃吗？废弃后将不再接收新流量。`}
            {modalState.action === 'offline' &&
              `确定要下线版本 ${modalState.record?.version} 吗？此操作将停止该版本的所有服务，且不可恢复。`}
          </p>
        </Modal>

        <Modal
          title={`Mock版本配置 - ${currentVersion?.name} (${currentVersion?.version})`}
          open={mockModalVisible}
          onCancel={() => setMockModalVisible(false)}
          width={900}
          footer={[
            <Button key="close" onClick={() => setMockModalVisible(false)}>
              关闭
            </Button>,
            <Button key="add" type="primary" icon={<PlusOutlined />} onClick={() => openMockForm()}>
              新建Mock配置
            </Button>,
          ]}
        >
          {currentVersion && (
            <Descriptions size="small" column={2} style={{ marginBottom: 16 }}>
              <Descriptions.Item label="版本号">{currentVersion.version}</Descriptions.Item>
              <Descriptions.Item label="状态">
                <Tag color={statusMap[currentVersion.status].color}>
                  {statusMap[currentVersion.status].text}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="接口数量">{currentVersion.apiCount} 个</Descriptions.Item>
              <Descriptions.Item label="描述">{currentVersion.description}</Descriptions.Item>
            </Descriptions>
          )}
          
          <Table
            columns={mockColumns}
            dataSource={mockConfigs}
            rowKey="id"
            loading={mockLoading}
            locale={{ emptyText: <Empty description="暂无Mock配置，点击右上角新建" /> }}
            pagination={{
              pageSize: 5,
              showSizeChanger: true,
              showQuickJumper: true,
            }}
          />
        </Modal>

        <Modal
          title={editingMockConfig ? '编辑Mock配置' : '新建Mock配置'}
          open={mockFormVisible}
          onOk={handleSaveMockConfig}
          onCancel={() => setMockFormVisible(false)}
          okText="保存"
          cancelText="取消"
          width={600}
        >
          <Form
            form={mockForm}
            layout="vertical"
            initialValues={{
              method: 'GET',
              mockType: 'SUCCESS',
              delayMs: 0,
              errorCode: 200,
              enabled: true,
            }}
          >
            <Row gutter={16}>
              <Col span={16}>
                <Form.Item
                  name="path"
                  label="API路径"
                  rules={[{ required: true, message: '请输入API路径' }]}
                >
                  <Input placeholder="例如：/api/v1/users/{id}" />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item
                  name="method"
                  label="HTTP方法"
                  rules={[{ required: true, message: '请选择HTTP方法' }]}
                >
                  <Select>
                    <Option value="GET">GET</Option>
                    <Option value="POST">POST</Option>
                    <Option value="PUT">PUT</Option>
                    <Option value="DELETE">DELETE</Option>
                    <Option value="PATCH">PATCH</Option>
                  </Select>
                </Form.Item>
              </Col>
            </Row>

            <Row gutter={16}>
              <Col span={12}>
                <Form.Item
                  name="mockType"
                  label="Mock类型"
                  rules={[{ required: true, message: '请选择Mock类型' }]}
                >
                  <Select>
                    <Option value="SUCCESS">成功 - 返回自定义数据</Option>
                    <Option value="DELAY">延迟 - 延迟后返回响应</Option>
                    <Option value="ERROR">错误 - 返回指定错误码</Option>
                    <Option value="CUSTOM">自定义 - 完全自定义响应</Option>
                  </Select>
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item
                  name="delayMs"
                  label="响应延迟(ms)"
                  tooltip="设置Mock响应的延迟时间，用于模拟网络延迟"
                >
                  <InputNumber
                    min={0}
                    max={30000}
                    step={100}
                    style={{ width: '100%' }}
                    placeholder="0"
                  />
                </Form.Item>
              </Col>
            </Row>

            <Row gutter={16}>
              <Col span={12}>
                <Form.Item
                  name="errorCode"
                  label="HTTP状态码"
                  rules={[{ required: true, message: '请输入HTTP状态码' }]}
                >
                  <InputNumber
                    min={100}
                    max={599}
                    style={{ width: '100%' }}
                    placeholder="200"
                  />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item
                  name="enabled"
                  label="启用状态"
                  valuePropName="checked"
                >
                  <Switch checkedChildren="启用" unCheckedChildren="禁用" />
                </Form.Item>
              </Col>
            </Row>

            <Form.Item
              name="errorMessage"
              label="错误信息"
              tooltip="当Mock类型为ERROR时返回的错误信息"
            >
              <Input placeholder="例如：服务器内部错误" />
            </Form.Item>

            <Form.Item
              name="customResponse"
              label="自定义响应内容"
              tooltip="当Mock类型为SUCCESS或CUSTOM时返回的响应体，支持JSON格式"
            >
              <TextArea
                rows={6}
                placeholder='例如：{"id": 1, "name": "Mock User", "email": "mock@example.com"}'
                spellCheck={false}
              />
            </Form.Item>
          </Form>
        </Modal>
      </Card>
    </div>
  );
}
