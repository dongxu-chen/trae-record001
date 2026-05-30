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
  Form,
  Slider,
  Switch,
  Card,
  Row,
  Col,
  message,
  Divider,
  InputNumber,
  List,
} from 'antd';
import {
  SearchOutlined,
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  SettingOutlined,
  ApiOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import type { RoutingRule, RoutingStrategy, GrayStrategyType, HeaderParseRule, HeaderParseStrategy } from '../types';
import routingApi from '../api/routingApi';

const { Title } = Typography;
const { Option } = Select;
const { TextArea } = Input;

const strategyMap: Record<RoutingStrategy, { text: string; color: string }> = {
  PATH: { text: '路径路由', color: 'blue' },
  HEADER: { text: '请求头路由', color: 'cyan' },
  QUERY: { text: '参数路由', color: 'purple' },
  WEIGHTED: { text: '权重路由', color: 'geekblue' },
};

const grayStrategyMap: Record<GrayStrategyType, { text: string; color: string }> = {
  USER_ID: { text: '按用户ID', color: 'green' },
  IP: { text: '按IP段', color: 'orange' },
  WEIGHT: { text: '按权重', color: 'magenta' },
  CUSTOM: { text: '自定义', color: 'default' },
};

interface FormData {
  apiName: string;
  strategy: RoutingStrategy;
  matchExpression?: string;
  v1Weight: number;
  v2Weight: number;
  headerParseRules?: HeaderParseRule[];
  enableGray: boolean;
  grayType?: GrayStrategyType;
  grayWeight?: number;
  includeList?: string;
  excludeList?: string;
  customRule?: string;
  enabled: boolean;
}

const headerParseStrategyMap: Record<HeaderParseStrategy, { text: string; desc: string }> = {
  DIRECT: { text: '直接取值', desc: '直接使用Header值作为版本号' },
  REGEX: { text: '正则匹配', desc: '使用正则表达式提取版本号' },
  PREFIX: { text: '前缀提取', desc: '提取指定前缀后的内容' },
  DELIMITER: { text: '分隔符分割', desc: '按分隔符分割后取指定部分' },
  SEMVER: { text: '语义化版本', desc: '从语义化版本中提取主版本' },
};

export default function Routing() {
  const [data, setData] = useState<RoutingRule[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [statusFilter, setStatusFilter] = useState<boolean | 'all'>('all');
  const [modalVisible, setModalVisible] = useState(false);
  const [editingRecord, setEditingRecord] = useState<RoutingRule | null>(null);
  const [deleteModalVisible, setDeleteModalVisible] = useState(false);
  const [deletingRecord, setDeletingRecord] = useState<RoutingRule | null>(null);
  const [headerRulesModalVisible, setHeaderRulesModalVisible] = useState(false);
  const [headerRules, setHeaderRules] = useState<HeaderParseRule[]>([]);
  const [form] = Form.useForm<FormData>();

  const fetchData = async () => {
    setLoading(true);
    try {
      const result = await routingApi.getList();
      setData(result.list);
    } catch (error) {
      message.error('获取路由规则失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const filteredData = data.filter((item) => {
    const matchesSearch = item.apiName.toLowerCase().includes(searchText.toLowerCase());
    const matchesStatus = statusFilter === 'all' || item.enabled === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const handleAdd = () => {
    setEditingRecord(null);
    form.resetFields();
    form.setFieldsValue({
      strategy: 'WEIGHTED',
      v1Weight: 50,
      v2Weight: 50,
      enableGray: false,
      enabled: true,
    });
    setModalVisible(true);
  };

  const handleEdit = (record: RoutingRule) => {
    setEditingRecord(record);
    const v1Weight = record.versionWeights.v1 || 0;
    const v2Weight = record.versionWeights.v2 || 0;
    setHeaderRules(record.headerParseRules || []);
    form.setFieldsValue({
      apiName: record.apiName,
      strategy: record.strategy,
      matchExpression: record.matchExpression,
      v1Weight,
      v2Weight,
      headerParseRules: record.headerParseRules || [],
      enableGray: !!record.grayStrategy,
      grayType: record.grayStrategy?.type,
      grayWeight: record.grayStrategy?.weight,
      includeList: record.grayStrategy?.includeList?.join('\n'),
      excludeList: record.grayStrategy?.excludeList?.join('\n'),
      customRule: record.grayStrategy?.customRule,
      enabled: record.enabled ?? true,
    });
    setModalVisible(true);
  };

  const handleAddHeaderRule = () => {
    const newRule: HeaderParseRule = {
      headerName: '',
      parseStrategy: 'DIRECT',
      pattern: '',
      defaultValue: 'v1',
      priority: headerRules.length + 1,
    };
    setHeaderRules([...headerRules, newRule]);
  };

  const handleUpdateHeaderRule = (index: number, field: keyof HeaderParseRule, value: string | number) => {
    const updated = [...headerRules];
    updated[index] = { ...updated[index], [field]: value };
    setHeaderRules(updated);
  };

  const handleRemoveHeaderRule = (index: number) => {
    const updated = headerRules.filter((_, i) => i !== index);
    setHeaderRules(updated);
  };

  const handleOpenHeaderRules = () => {
    setHeaderRules(form.getFieldValue('headerParseRules') || []);
    setHeaderRulesModalVisible(true);
  };

  const handleSaveHeaderRules = () => {
    form.setFieldsValue({ headerParseRules: headerRules });
    setHeaderRulesModalVisible(false);
    message.success('Header解析规则已保存');
  };

  const handleDelete = (record: RoutingRule) => {
    setDeletingRecord(record);
    setDeleteModalVisible(true);
  };

  const confirmDelete = async () => {
    if (!deletingRecord) return;
    try {
      await routingApi.delete(deletingRecord.id);
      message.success('删除成功');
      fetchData();
    } catch (error) {
      message.error('删除失败');
    } finally {
      setDeleteModalVisible(false);
      setDeletingRecord(null);
    }
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      const grayStrategy = values.enableGray
        ? {
            type: values.grayType!,
            weight: values.grayWeight,
            includeList: values.includeList?.split('\n').filter(Boolean),
            excludeList: values.excludeList?.split('\n').filter(Boolean),
            customRule: values.customRule,
          }
        : undefined;

      const ruleData: Partial<RoutingRule> = {
        apiName: values.apiName,
        strategy: values.strategy,
        matchExpression: values.matchExpression,
        headerParseRules: values.headerParseRules,
        versionWeights: {
          v1: values.v1Weight,
          v2: values.v2Weight,
        },
        grayStrategy,
        enabled: values.enabled,
      };

      if (editingRecord) {
        await routingApi.update(editingRecord.id, ruleData);
        message.success('更新成功');
      } else {
        await routingApi.create(ruleData);
        message.success('创建成功');
      }
      fetchData();
      setModalVisible(false);
    } catch (error) {
      if ((error as { errorFields?: unknown[] }).errorFields) {
        return;
      }
      message.error(editingRecord ? '更新失败' : '创建失败');
    }
  };

  const toggleStatus = async (record: RoutingRule) => {
    try {
      await routingApi.update(record.id, { enabled: !record.enabled });
      message.success(record.enabled ? '已停用' : '已启用');
      fetchData();
    } catch (error) {
      message.error('操作失败');
    }
  };

  const columns: ColumnsType<RoutingRule> = [
    {
      title: 'API名称',
      dataIndex: 'apiName',
      key: 'apiName',
      width: 150,
    },
    {
      title: '策略',
      dataIndex: 'strategy',
      key: 'strategy',
      width: 120,
      render: (strategy: RoutingStrategy) => (
        <Tag color={strategyMap[strategy].color}>{strategyMap[strategy].text}</Tag>
      ),
    },
    {
      title: 'v1权重',
      dataIndex: ['versionWeights', 'v1'],
      key: 'v1Weight',
      width: 100,
      render: (weight: number) => (
        <span style={{ color: weight > 0 ? '#1677ff' : '#999' }}>{weight}%</span>
      ),
    },
    {
      title: 'v2权重',
      dataIndex: ['versionWeights', 'v2'],
      key: 'v2Weight',
      width: 100,
      render: (weight: number) => (
        <span style={{ color: weight > 0 ? '#52c41a' : '#999' }}>{weight}%</span>
      ),
    },
    {
      title: 'Header解析规则',
      dataIndex: 'headerParseRules',
      key: 'headerParseRules',
      width: 150,
      render: (rules: HeaderParseRule[]) => {
        if (!rules || rules.length === 0) {
          return <Tag color="default">默认规则</Tag>;
        }
        return (
          <Space>
            <Tag color="cyan">{rules.length} 条规则</Tag>
          </Space>
        );
      },
    },
    {
      title: '灰度策略',
      dataIndex: 'grayStrategy',
      key: 'grayStrategy',
      width: 120,
      render: (grayStrategy) => {
        if (!grayStrategy) {
          return <Tag color="default">未启用</Tag>;
        }
        const strategy = grayStrategyMap[grayStrategy.type];
        return <Tag color={strategy.color}>{strategy.text}</Tag>;
      },
    },
    {
      title: '状态',
      dataIndex: 'enabled',
      key: 'enabled',
      width: 100,
      render: (enabled: boolean) => (
        <Tag color={enabled ? 'success' : 'default'}>{enabled ? '已启用' : '已停用'}</Tag>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 200,
      fixed: 'right',
      render: (_, record) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            icon={record.enabled ? <PauseCircleOutlined /> : <PlayCircleOutlined />}
            onClick={() => toggleStatus(record)}
          >
            {record.enabled ? '停用' : '启用'}
          </Button>
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            编辑
          </Button>
          <Button
            type="link"
            size="small"
            danger
            icon={<DeleteOutlined />}
            onClick={() => handleDelete(record)}
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
              路由配置
            </Title>
          </Col>
          <Col>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
              新增路由规则
            </Button>
          </Col>
        </Row>

        <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
          <Col xs={24} sm={12} md={8}>
            <Input
              placeholder="搜索API名称"
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
              <Option value={true}>已启用</Option>
              <Option value={false}>已停用</Option>
            </Select>
          </Col>
        </Row>

        <Table
          columns={columns}
          dataSource={filteredData}
          rowKey="id"
          loading={loading}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => `共 ${total} 条记录`,
          }}
          scroll={{ x: 900 }}
        />

        <Modal
          title={
            <Space>
              <SettingOutlined />
              <span>{editingRecord ? '编辑路由规则' : '新增路由规则'}</span>
            </Space>
          }
          open={modalVisible}
          onOk={handleSubmit}
          onCancel={() => setModalVisible(false)}
          okText="保存"
          cancelText="取消"
          width={700}
          maskClosable={false}
        >
          <Form form={form} layout="vertical">
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item
                  name="apiName"
                  label="API名称"
                  rules={[{ required: true, message: '请输入API名称' }]}
                >
                  <Input placeholder="例如：用户服务" />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item
                  name="strategy"
                  label="路由策略"
                  rules={[{ required: true, message: '请选择路由策略' }]}
                >
                  <Select>
                    <Option value="PATH">路径路由</Option>
                    <Option value="HEADER">请求头路由</Option>
                    <Option value="QUERY">参数路由</Option>
                    <Option value="WEIGHTED">权重路由</Option>
                  </Select>
                </Form.Item>
              </Col>
            </Row>

            <Form.Item
              noStyle
              shouldUpdate={(prev, curr) => prev.strategy !== curr.strategy}
            >
              {({ getFieldValue }) => {
                const strategy = getFieldValue('strategy');
                if (strategy === 'WEIGHTED') return null;
                return (
                  <Form.Item
                    name="matchExpression"
                    label="匹配规则"
                    rules={[{ required: true, message: '请输入匹配规则' }]}
                  >
                    <Input
                      placeholder={
                        strategy === 'PATH'
                          ? '例如：/api/v2/orders/**'
                          : strategy === 'HEADER'
                          ? '例如：X-API-Version=v2'
                          : '例如：apiVersion=v2'
                      }
                    />
                  </Form.Item>
                );
              }}
            </Form.Item>

            <Divider orientation="left">Header解析规则</Divider>

            <Form.Item label="自定义Header解析规则">
              <Button
                icon={<ApiOutlined />}
                onClick={handleOpenHeaderRules}
              >
                配置Header解析规则 ({form.getFieldValue('headerParseRules')?.length || 0} 条)
              </Button>
              <div style={{ marginTop: 8, color: '#666', fontSize: 12 }}>
                配置从请求头中解析版本号的规则，支持多种解析策略
              </div>
            </Form.Item>

            <Divider orientation="left">版本权重分配</Divider>

            <Form.Item label="流量分配" required>
              <Space.Compact style={{ width: '100%', display: 'flex', gap: 16 }}>
                <Space style={{ minWidth: 100 }}>
                  <span style={{ color: '#1677ff' }}>v1:</span>
                  <Form.Item
                    name="v1Weight"
                    noStyle
                    rules={[{ required: true, message: '请输入v1权重' }]}
                  >
                    <InputNumber
                      min={0}
                      max={100}
                      formatter={(value) => `${value}%`}
                      parser={(value) => Number(value?.replace('%', ''))}
                      style={{ width: 100 }}
                    />
                  </Form.Item>
                </Space>
                <Form.Item
                  name="v1Weight"
                  noStyle
                  rules={[{ required: true, message: '请调节权重' }]}
                >
                  <Slider
                    min={0}
                    max={100}
                    style={{ flex: 1 }}
                    onChange={(value) => {
                      form.setFieldsValue({
                        v1Weight: value,
                        v2Weight: 100 - value,
                      });
                    }}
                  />
                </Form.Item>
                <Space style={{ minWidth: 100 }}>
                  <span style={{ color: '#52c41a' }}>v2:</span>
                  <Form.Item
                    name="v2Weight"
                    noStyle
                    rules={[{ required: true, message: '请输入v2权重' }]}
                  >
                    <InputNumber
                      min={0}
                      max={100}
                      formatter={(value) => `${value}%`}
                      parser={(value) => Number(value?.replace('%', ''))}
                      style={{ width: 100 }}
                    />
                  </Form.Item>
                </Space>
              </Space.Compact>
            </Form.Item>

            <Divider orientation="left">灰度发布配置</Divider>

            <Form.Item
              name="enableGray"
              label="启用灰度发布"
              valuePropName="checked"
            >
              <Switch />
            </Form.Item>

            <Form.Item
              noStyle
              shouldUpdate={(prev, curr) => prev.enableGray !== curr.enableGray}
            >
              {({ getFieldValue }) => {
                const enableGray = getFieldValue('enableGray');
                if (!enableGray) return null;
                return (
                  <>
                    <Row gutter={16}>
                      <Col span={12}>
                        <Form.Item
                          name="grayType"
                          label="灰度策略类型"
                          rules={[{ required: true, message: '请选择灰度策略类型' }]}
                        >
                          <Select>
                            <Option value="USER_ID">按用户ID</Option>
                            <Option value="IP">按IP段</Option>
                            <Option value="WEIGHT">按权重</Option>
                            <Option value="CUSTOM">自定义</Option>
                          </Select>
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item
                          noStyle
                          shouldUpdate={(prev, curr) => prev.grayType !== curr.grayType}
                        >
                          {({ getFieldValue: getValue }) => {
                            const grayType = getValue('grayType');
                            if (grayType !== 'WEIGHT') return null;
                            return (
                              <Form.Item
                                name="grayWeight"
                                label="灰度流量比例"
                                rules={[{ required: true, message: '请输入灰度比例' }]}
                              >
                                <Slider
                                  min={0}
                                  max={100}
                                  tooltip={{ formatter: (value) => `${value}%` }}
                                />
                              </Form.Item>
                            );
                          }}
                        </Form.Item>
                      </Col>
                    </Row>

                    <Form.Item
                      noStyle
                      shouldUpdate={(prev, curr) => prev.grayType !== curr.grayType}
                    >
                      {({ getFieldValue: getValue }) => {
                        const grayType = getValue('grayType');
                        if (!grayType || grayType === 'WEIGHT') return null;
                        if (grayType === 'CUSTOM') {
                          return (
                            <Form.Item
                              name="customRule"
                              label="自定义规则"
                              rules={[{ required: true, message: '请输入自定义规则' }]}
                            >
                              <TextArea
                                rows={3}
                                placeholder="请输入自定义灰度规则表达式..."
                              />
                            </Form.Item>
                          );
                        }
                        return (
                          <Row gutter={16}>
                            <Col span={12}>
                              <Form.Item name="includeList" label="包含列表">
                                <TextArea
                                  rows={3}
                                  placeholder={
                                    grayType === 'USER_ID'
                                      ? '每行一个用户ID，例如：\n1001\n1002\n1003'
                                      : '每行一个IP段，例如：\n192.168.1.0/24\n10.0.0.0/8'
                                  }
                                />
                              </Form.Item>
                            </Col>
                            <Col span={12}>
                              <Form.Item name="excludeList" label="排除列表">
                                <TextArea
                                  rows={3}
                                  placeholder={
                                    grayType === 'USER_ID'
                                      ? '每行一个用户ID，例如：\n9999\n8888'
                                      : '每行一个IP段，例如：\n172.16.0.0/12'
                                  }
                                />
                              </Form.Item>
                            </Col>
                          </Row>
                        );
                      }}
                    </Form.Item>
                  </>
                );
              }}
            </Form.Item>

            <Form.Item
              name="enabled"
              label="启用规则"
              valuePropName="checked"
            >
              <Switch defaultChecked />
            </Form.Item>
          </Form>
        </Modal>

        <Modal
          title="Header解析规则配置"
          open={headerRulesModalVisible}
          onOk={handleSaveHeaderRules}
          onCancel={() => setHeaderRulesModalVisible(false)}
          okText="保存规则"
          cancelText="取消"
          width={900}
          maskClosable={false}
        >
          <div style={{ marginBottom: 16 }}>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleAddHeaderRule}>
              添加解析规则
            </Button>
            <div style={{ marginTop: 8, color: '#666', fontSize: 12 }}>
              规则按优先级顺序执行，第一个匹配成功的规则返回结果
            </div>
          </div>

          <List
            dataSource={headerRules}
            locale={{ emptyText: '暂无解析规则，请点击上方按钮添加' }}
            renderItem={(rule, index) => (
              <List.Item
                key={index}
                style={{
                  padding: 16,
                  background: '#fafafa',
                  marginBottom: 12,
                  borderRadius: 8,
                }}
                extra={
                  <Button
                    type="text"
                    danger
                    icon={<DeleteOutlined />}
                    onClick={() => handleRemoveHeaderRule(index)}
                  >
                    删除
                  </Button>
                }
              >
                <Row gutter={[16, 16]} style={{ width: '100%' }}>
                  <Col span={4}>
                    <div style={{ fontWeight: 500, marginBottom: 4 }}>优先级</div>
                    <InputNumber
                      min={1}
                      max={100}
                      value={rule.priority}
                      onChange={(value) =>
                        handleUpdateHeaderRule(index, 'priority', value as number)
                      }
                      style={{ width: '100%' }}
                    />
                  </Col>
                  <Col span={6}>
                    <div style={{ fontWeight: 500, marginBottom: 4 }}>Header名称</div>
                    <Input
                      placeholder="例如: X-API-Version"
                      value={rule.headerName}
                      onChange={(e) =>
                        handleUpdateHeaderRule(index, 'headerName', e.target.value)
                      }
                    />
                  </Col>
                  <Col span={5}>
                    <div style={{ fontWeight: 500, marginBottom: 4 }}>解析策略</div>
                    <Select
                      value={rule.parseStrategy}
                      onChange={(value) =>
                        handleUpdateHeaderRule(index, 'parseStrategy', value)
                      }
                      style={{ width: '100%' }}
                    >
                      {Object.entries(headerParseStrategyMap).map(([key, config]) => (
                        <Option key={key} value={key} title={config.desc}>
                          {config.text}
                        </Option>
                      ))}
                    </Select>
                  </Col>
                  <Col span={6}>
                    <div style={{ fontWeight: 500, marginBottom: 4 }}>
                      {rule.parseStrategy === 'DIRECT'
                        ? '默认值'
                        : rule.parseStrategy === 'REGEX'
                        ? '正则表达式'
                        : rule.parseStrategy === 'PREFIX'
                        ? '前缀'
                        : rule.parseStrategy === 'DELIMITER'
                        ? '分隔符'
                        : '默认值'}
                    </div>
                    <Input
                      placeholder={
                        rule.parseStrategy === 'DIRECT'
                          ? 'v1'
                          : rule.parseStrategy === 'REGEX'
                          ? 'version=([^;]+)'
                          : rule.parseStrategy === 'PREFIX'
                          ? 'v'
                          : rule.parseStrategy === 'DELIMITER'
                          ? '.'
                          : 'v1'
                      }
                      value={
                        rule.parseStrategy === 'DIRECT' || rule.parseStrategy === 'SEMVER'
                          ? rule.defaultValue
                          : rule.pattern
                      }
                      onChange={(e) =>
                        handleUpdateHeaderRule(
                          index,
                          rule.parseStrategy === 'DIRECT' || rule.parseStrategy === 'SEMVER'
                            ? 'defaultValue'
                            : 'pattern',
                          e.target.value
                        )
                      }
                    />
                  </Col>
                  <Col span={3}>
                    <div style={{ fontWeight: 500, marginBottom: 4 }}>默认值</div>
                    <Input
                      placeholder="v1"
                      value={rule.defaultValue}
                      onChange={(e) =>
                        handleUpdateHeaderRule(index, 'defaultValue', e.target.value)
                      }
                    />
                  </Col>
                </Row>
                <div style={{ marginTop: 8, color: '#888', fontSize: 12 }}>
                  {headerParseStrategyMap[rule.parseStrategy].desc}
                </div>
              </List.Item>
            )}
          />
        </Modal>

        <Modal
          title="确认删除"
          open={deleteModalVisible}
          onOk={confirmDelete}
          onCancel={() => setDeleteModalVisible(false)}
          okText="确认删除"
          cancelText="取消"
          okButtonProps={{ danger: true }}
        >
          <p>
            确定要删除路由规则 <strong>{deletingRecord?.apiName}</strong> 吗？此操作不可恢复。
          </p>
        </Modal>
      </Card>
    </div>
  );
}
