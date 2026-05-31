import React from 'react';
import { Card, Form, Input, Switch, Button, message, Divider, Table, Tag, Space } from 'antd';
import { EditOutlined, DeleteOutlined } from '@ant-design/icons';

const Settings: React.FC = () => {
  const [form] = Form.useForm();

  const handleSystemSave = (values: any) => {
    message.success('系统设置已保存');
    console.log('System settings:', values);
  };

  const users = [
    {
      key: '1',
      username: 'admin',
      role: '管理员',
      email: 'admin@example.com',
      status: 'active',
      createdAt: '2024-01-01',
    },
    {
      key: '2',
      username: 'operator',
      role: '操作员',
      email: 'operator@example.com',
      status: 'active',
      createdAt: '2024-01-15',
    },
    {
      key: '3',
      username: 'viewer',
      role: '只读用户',
      email: 'viewer@example.com',
      status: 'inactive',
      createdAt: '2024-02-01',
    },
  ];

  const userColumns = [
    {
      title: '用户名',
      dataIndex: 'username',
      key: 'username',
    },
    {
      title: '角色',
      dataIndex: 'role',
      key: 'role',
      render: (role: string) => {
        const colorMap: Record<string, string> = {
          管理员: 'red',
          操作员: 'blue',
          只读用户: 'default',
        };
        return <Tag color={colorMap[role] || 'default'}>{role}</Tag>;
      },
    },
    {
      title: '邮箱',
      dataIndex: 'email',
      key: 'email',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Tag color={status === 'active' ? 'success' : 'default'}>
          {status === 'active' ? '启用' : '禁用'}
        </Tag>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'createdAt',
      key: 'createdAt',
    },
    {
      title: '操作',
      key: 'action',
      render: () => (
        <Space>
          <Button type="link" icon={<EditOutlined />}>
            编辑
          </Button>
          <Button type="link" danger icon={<DeleteOutlined />}>
            删除
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">系统设置</h1>

      <Card title="系统配置" className="mb-6">
        <Form form={form} layout="vertical" onFinish={handleSystemSave} initialValues={{ maxConcurrentTasks: 5, enableEmailNotify: true }}>
          <div className="grid grid-cols-2 gap-6">
            <Form.Item name="systemName" label="系统名称">
              <Input placeholder="请输入系统名称" />
            </Form.Item>
            <Form.Item name="maxConcurrentTasks" label="最大并发任务数">
              <Input type="number" placeholder="请输入最大并发任务数" />
            </Form.Item>
            <Form.Item name="defaultBatchSize" label="默认批量大小">
              <Input type="number" placeholder="请输入默认批量大小" />
            </Form.Item>
            <Form.Item name="retryCount" label="失败重试次数">
              <Input type="number" placeholder="请输入失败重试次数" />
            </Form.Item>
          </div>
          <Form.Item name="enableEmailNotify" label="邮件通知" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit">
              保存设置
            </Button>
          </Form.Item>
        </Form>
      </Card>

      <Divider />

      <Card
        title="用户管理"
        extra={
          <Button type="primary">
            新增用户
          </Button>
        }
      >
        <Table columns={userColumns} dataSource={users} pagination={false} />
      </Card>

      <Divider />

      <Card title="脱敏规则配置" className="mt-6">
        <div className="grid grid-cols-3 gap-4">
          <Card size="small" title="手机号脱敏">
            <p className="text-gray-600 text-sm">保留前3位和后4位，中间用*代替</p>
            <p className="text-gray-500 text-xs mt-2">示例: 138****1234</p>
          </Card>
          <Card size="small" title="邮箱脱敏">
            <p className="text-gray-600 text-sm">保留首字符和域名，中间用*代替</p>
            <p className="text-gray-500 text-xs mt-2">示例: a***@example.com</p>
          </Card>
          <Card size="small" title="身份证脱敏">
            <p className="text-gray-600 text-sm">保留前6位和后4位，中间用*代替</p>
            <p className="text-gray-500 text-xs mt-2">示例: 110101********1234</p>
          </Card>
        </div>
      </Card>
    </div>
  );
};

export default Settings;
