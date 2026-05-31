import React, { useState, useEffect } from 'react';
import {
  Card,
  Form,
  Input,
  InputNumber,
  Select,
  Button,
  Table,
  Tag,
  Modal,
  message,
  Switch,
  Space,
  Drawer,
  Popconfirm,
  Tooltip,
  Typography,
  Descriptions,
  Row,
  Col,
  Divider,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  EyeOutlined,
  CopyOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { accessControlAPI } from '../services/api';
import type { AccessControlRule } from '../types';

const { Title, Text, Paragraph } = Typography;
const { Option } = Select;
const { TextArea } = Input;

const AccessControlPage: React.FC = () => {
  const [rules, setRules] = useState<AccessControlRule[]>([]);
  const [loading, setLoading] = useState(false);
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [editMode, setEditMode] = useState(false);
  const [editingRule, setEditingRule] = useState<AccessControlRule | null>(null);
  const [detailVisible, setDetailVisible] = useState(false);
  const [selectedRule, setSelectedRule] = useState<AccessControlRule | null>(null);
  const [form] = Form.useForm();

  const fetchRules = async () => {
    setLoading(true);
    try {
      const res = await accessControlAPI.listRules();
      setRules(res.data.rules || []);
    } catch (err) {
      message.error('Failed to fetch access control rules');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRules();
  }, []);

  const handleCreate = async () => {
    try {
      const values = await form.validateFields();

      const listItems = values.listType === 'ip'
        ? { ipList: values.ipList?.split('\n').filter((s: string) => s.trim()) }
        : values.listType === 'user'
        ? { userIdList: values.userIdList?.split('\n').filter((s: string) => s.trim()) }
        : {
            headerName: values.headerName,
            headerValues: values.headerValues?.split('\n').filter((s: string) => s.trim()),
          };

      const ruleData = {
        ...values,
        ...listItems,
      };

      if (editMode && editingRule) {
        await accessControlAPI.updateRule(editingRule.id, ruleData);
        message.success('Rule updated successfully');
      } else {
        await accessControlAPI.createRule(ruleData);
        message.success('Rule created successfully');
      }

      setCreateModalVisible(false);
      setEditMode(false);
      setEditingRule(null);
      form.resetFields();
      fetchRules();
    } catch (err) {
      console.error('Failed to save rule:', err);
    }
  };

  const handleToggleStatus = async (rule: AccessControlRule) => {
    try {
      await accessControlAPI.updateRule(rule.id, {
        status: rule.status === 'active' ? 'inactive' : 'active',
      });
      message.success(`Rule ${rule.status === 'active' ? 'disabled' : 'enabled'}`);
      fetchRules();
    } catch (err) {
      message.error('Failed to update rule status');
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await accessControlAPI.deleteRule(id);
      message.success('Rule deleted');
      fetchRules();
    } catch (err) {
      message.error('Failed to delete rule');
    }
  };

  const handleEdit = (rule: AccessControlRule) => {
    setEditMode(true);
    setEditingRule(rule);

    const listValue = rule.ruleType === 'ip'
      ? rule.ipList?.join('\n')
      : rule.ruleType === 'user'
      ? rule.userIdList?.join('\n')
      : rule.headerValues?.join('\n');

    form.setFieldsValue({
      ...rule,
      listItems: listValue,
    });

    setCreateModalVisible(true);
  };

  const handleCopy = async (rule: AccessControlRule) => {
    const newRule = {
      ...rule,
      id: undefined,
      name: `${rule.name}-copy`,
      status: 'inactive',
    };
    try {
      await accessControlAPI.createRule(newRule);
      message.success('Rule copied');
      fetchRules();
    } catch (err) {
      message.error('Failed to copy rule');
    }
  };

  const getRuleTypeTag = (ruleType: string) => {
    const typeMap: Record<string, { color: string; icon: string }> = {
      'ip': { color: 'blue', icon: '🌐' },
      'user': { color: 'purple', icon: '👤' },
      'header': { color: 'cyan', icon: '📋' },
    };
    const info = typeMap[ruleType] || { color: 'default', icon: '' };
    return (
      <Tag color={info.color}>
        {info.icon} {ruleType.toUpperCase()}
      </Tag>
    );
  };

  const getControlTypeTag = (controlType: string, listType: string) => {
    if (listType === 'whitelist') {
      return <Tag color="green">Allow (Whitelist)</Tag>;
    }
    return <Tag color="red">Deny (Blacklist)</Tag>;
  };

  const columns: ColumnsType<AccessControlRule> = [
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
      width: 200,
    },
    {
      title: 'Service',
      dataIndex: 'serviceName',
      key: 'serviceName',
      width: 150,
    },
    {
      title: 'Type',
      dataIndex: 'ruleType',
      key: 'ruleType',
      width: 120,
      render: (type) => getRuleTypeTag(type),
    },
    {
      title: 'Control',
      key: 'control',
      width: 160,
      render: (_, record) => getControlTypeTag(record.controlType, record.listType),
    },
    {
      title: 'Entries',
      key: 'entries',
      width: 200,
      render: (_, record) => {
        const count = record.ruleType === 'ip'
          ? record.ipList?.length || 0
          : record.ruleType === 'user'
          ? record.userIdList?.length || 0
          : record.headerValues?.length || 0;

        const sample = record.ruleType === 'ip'
          ? record.ipList?.slice(0, 2)
          : record.ruleType === 'user'
          ? record.userIdList?.slice(0, 2)
          : record.headerValues?.slice(0, 2);

        return (
          <Space direction="vertical" size={0}>
            <Text strong>{count} entries</Text>
            {sample && sample.length > 0 && (
              <Text type="secondary" style={{ fontSize: 11 }}>
                {sample.join(', ')}{count > 2 ? '...' : ''}
              </Text>
            )}
          </Space>
        );
      },
    },
    {
      title: 'Priority',
      dataIndex: 'priority',
      key: 'priority',
      width: 100,
      render: (p) => <Tag color={p > 50 ? 'orange' : 'default'}>#{p}</Tag>,
    },
    {
      title: 'Status',
      key: 'status',
      width: 100,
      render: (_, record) => (
        <Switch
          checked={record.status === 'active'}
          onChange={() => handleToggleStatus(record)}
          size="small"
          checkedChildren={<CheckCircleOutlined />}
          unCheckedChildren={<CloseCircleOutlined />}
        />
      ),
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 180,
      render: (_, record) => (
        <Space size="small">
          <Tooltip title="View Details">
            <Button
              type="text"
              size="small"
              icon={<EyeOutlined />}
              onClick={() => {
                setSelectedRule(record);
                setDetailVisible(true);
              }}
            />
          </Tooltip>
          <Tooltip title="Edit">
            <Button
              type="text"
              size="small"
              icon={<EditOutlined />}
              onClick={() => handleEdit(record)}
            />
          </Tooltip>
          <Tooltip title="Duplicate">
            <Button
              type="text"
              size="small"
              icon={<CopyOutlined />}
              onClick={() => handleCopy(record)}
            />
          </Tooltip>
          <Popconfirm
            title="Delete this rule?"
            onConfirm={() => handleDelete(record.id)}
            okText="Delete"
            cancelText="Cancel"
            okButtonProps={{ danger: true }}
          >
            <Button
              type="text"
              danger
              size="small"
              icon={<DeleteOutlined />}
            />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Card
        title="Access Control Manager"
        extra={
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => {
              setEditMode(false);
              setEditingRule(null);
              form.resetFields();
              form.setFieldsValue({
                namespace: 'default',
                ruleType: 'ip',
                controlType: 'allow',
                listType: 'whitelist',
                priority: 10,
                status: 'active',
              });
              setCreateModalVisible(true);
            }}
          >
            New Rule
          </Button>
        }
      >
        <Table
          columns={columns}
          dataSource={rules}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 10 }}
        />
      </Card>

      <Modal
        title={editMode ? 'Edit Access Control Rule' : 'Create Access Control Rule'}
        open={createModalVisible}
        onCancel={() => {
          setCreateModalVisible(false);
          setEditMode(false);
          setEditingRule(null);
        }}
        width={600}
        footer={
          <Space>
            <Button onClick={() => setCreateModalVisible(false)}>Cancel</Button>
            <Button type="primary" onClick={handleCreate}>
              {editMode ? 'Update' : 'Create'}
            </Button>
          </Space>
        }
      >
        <Form form={form} layout="vertical">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="name"
                label="Rule Name"
                rules={[{ required: true }]}
              >
                <Input placeholder="e.g., block-bad-ips" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="namespace"
                label="Namespace"
                initialValue="default"
                rules={[{ required: true }]}
              >
                <Input />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="serviceName"
                label="Target Service"
                rules={[{ required: true }]}
              >
                <Input placeholder="e.g., payment-service" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="priority"
                label="Priority"
                initialValue={10}
                tooltip="Higher number = higher priority"
              >
                <InputNumber min={1} max={100} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                name="ruleType"
                label="Rule Type"
                initialValue="ip"
                rules={[{ required: true }]}
              >
                <Select>
                  <Option value="ip">IP Address</Option>
                  <Option value="user">User ID</Option>
                  <Option value="header">Custom Header</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="controlType"
                label="Control Type"
                initialValue="allow"
                rules={[{ required: true }]}
              >
                <Select>
                  <Option value="allow">Allow</Option>
                  <Option value="deny">Deny</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="listType"
                label="List Type"
                initialValue="whitelist"
                rules={[{ required: true }]}
              >
                <Select>
                  <Option value="whitelist">Whitelist</Option>
                  <Option value="blacklist">Blacklist</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            noStyle
            shouldUpdate={(prev, curr) => prev.ruleType !== curr.ruleType}
          >
            {({ getFieldValue }) => {
              const ruleType = getFieldValue('ruleType');

              if (ruleType === 'header') {
                return (
                  <Form.Item
                    name="headerName"
                    label="Header Name"
                    rules={[{ required: true }]}
                  >
                    <Input placeholder="e.g., X-API-Key" />
                  </Form.Item>
                );
              }
              return null;
            }}
          </Form.Item>

          <Form.Item
            noStyle
            shouldUpdate={(prev, curr) => prev.ruleType !== curr.ruleType}
          >
            {({ getFieldValue }) => {
              const ruleType = getFieldValue('ruleType');
              const label = ruleType === 'ip'
                ? 'IP Addresses (one per line, supports CIDR)'
                : ruleType === 'user'
                ? 'User IDs (one per line)'
                : 'Header Values (one per line)';

              return (
                <Form.Item
                  name="listItems"
                  label={label}
                  rules={[{ required: true }]}
                >
                  <TextArea
                    rows={6}
                    placeholder={ruleType === 'ip'
                      ? "192.168.1.0/24\n10.0.0.1\n172.16.0.0/16"
                      : ruleType === 'user'
                      ? "user-123\nuser-456\nuser-789"
                      : "value1\nvalue2\nvalue3"
                    }
                  />
                </Form.Item>
              );
            }}
          </Form.Item>

          <Form.Item
            name="description"
            label="Description"
          >
            <TextArea rows={2} placeholder="Optional description for this rule" />
          </Form.Item>
        </Form>
      </Modal>

      <Drawer
        title="Rule Details"
        width={600}
        open={detailVisible}
        onClose={() => setDetailVisible(false)}
      >
        {selectedRule && (
          <Space direction="vertical" size="large" style={{ width: '100%' }}>
            <Card>
              <Descriptions column={2} size="small">
                <Descriptions.Item label="Name">{selectedRule.name}</Descriptions.Item>
                <Descriptions.Item label="Service">{selectedRule.serviceName}</Descriptions.Item>
                <Descriptions.Item label="Type">{getRuleTypeTag(selectedRule.ruleType)}</Descriptions.Item>
                <Descriptions.Item label="Control">{getControlTypeTag(selectedRule.controlType, selectedRule.listType)}</Descriptions.Item>
                <Descriptions.Item label="Priority">#{selectedRule.priority}</Descriptions.Item>
                <Descriptions.Item label="Status">
                  <Tag color={selectedRule.status === 'active' ? 'green' : 'default'}>
                    {selectedRule.status}
                  </Tag>
                </Descriptions.Item>
                <Descriptions.Item label="Created">{selectedRule.createdAt}</Descriptions.Item>
                <Descriptions.Item label="Updated">{selectedRule.updatedAt}</Descriptions.Item>
              </Descriptions>
            </Card>

            {selectedRule.description && (
              <Card title="Description">
                <Paragraph>{selectedRule.description}</Paragraph>
              </Card>
            )}

            <Card title={
              <Space>
                {getRuleTypeTag(selectedRule.ruleType)}
                <span>List Entries</span>
                <Tag color="blue">{
                  selectedRule.ruleType === 'ip'
                    ? selectedRule.ipList?.length || 0
                    : selectedRule.ruleType === 'user'
                    ? selectedRule.userIdList?.length || 0
                    : selectedRule.headerValues?.length || 0
                } entries</Tag>
              </Space>
            }>
              {selectedRule.ruleType === 'header' && (
                <div style={{ marginBottom: 16 }}>
                  <Text type="secondary">Header Name: </Text>
                  <Text code>{selectedRule.headerName}</Text>
                </div>
              )}
              <div style={{
                maxHeight: 400,
                overflowY: 'auto',
                background: '#fafafa',
                padding: 12,
                borderRadius: 4,
                fontFamily: 'monospace',
                fontSize: 13,
              }}>
                {selectedRule.ruleType === 'ip' && selectedRule.ipList?.map((ip, idx) => (
                  <div key={idx} style={{ padding: '2px 0' }}>{ip}</div>
                ))}
                {selectedRule.ruleType === 'user' && selectedRule.userIdList?.map((uid, idx) => (
                  <div key={idx} style={{ padding: '2px 0' }}>{uid}</div>
                ))}
                {selectedRule.ruleType === 'header' && selectedRule.headerValues?.map((val, idx) => (
                  <div key={idx} style={{ padding: '2px 0' }}>{val}</div>
                ))}
              </div>
            </Card>
          </Space>
        )}
      </Drawer>
    </Space>
  );
};

export default AccessControlPage;
