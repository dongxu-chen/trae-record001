import React, { useEffect, useState } from 'react';
import {
  Table,
  Button,
  Tag,
  Space,
  Modal,
  Form,
  Input,
  Select,
  InputNumber,
  message,
  Popconfirm,
  Card,
} from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, PlayCircleOutlined } from '@ant-design/icons';
import { useAppStore } from '@/store/appStore';
import { DataSource, dataSourceApi } from '@/services/api';

const { Option } = Select;

const DataSourceList: React.FC = () => {
  const { dataSources, fetchDataSources } = useAppStore();
  const [modalVisible, setModalVisible] = useState(false);
  const [editingItem, setEditingItem] = useState<DataSource | null>(null);
  const [form] = Form.useForm();
  const [testing, setTesting] = useState(false);

  useEffect(() => {
    fetchDataSources();
  }, [fetchDataSources]);

  const handleAdd = () => {
    setEditingItem(null);
    form.resetFields();
    setModalVisible(true);
  };

  const handleEdit = (item: DataSource) => {
    setEditingItem(item);
    form.setFieldsValue({
      name: item.name,
      type: item.type,
      ...item.config,
    });
    setModalVisible(true);
  };

  const handleDelete = async (id: string) => {
    try {
      await dataSourceApi.delete(id);
      message.success('删除成功');
      fetchDataSources();
    } catch (error) {
      message.error('删除失败');
    }
  };

  const handleTest = async (id: string) => {
    setTesting(true);
    try {
      const response = await dataSourceApi.test(id);
      if (response.data.success) {
        message.success('连接成功');
      } else {
        message.error('连接失败: ' + response.data.message);
      }
      fetchDataSources();
    } catch (error) {
      message.error('测试失败');
    } finally {
      setTesting(false);
    }
  };

  const handleSubmit = async (values: any) => {
    try {
      const { name, type, ...config } = values;
      const data = { name, type, config };

      if (editingItem) {
        await dataSourceApi.update(editingItem.id, data);
        message.success('更新成功');
      } else {
        await dataSourceApi.create(data);
        message.success('创建成功');
      }
      setModalVisible(false);
      fetchDataSources();
    } catch (error) {
      message.error('操作失败');
    }
  };

  const columns = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      render: (type: string) => {
        const typeMap: Record<string, string> = {
          mysql: 'MySQL',
          postgresql: 'PostgreSQL',
          mongodb: 'MongoDB',
          s3: 'S3/OSS',
          kafka: 'Kafka',
          rabbitmq: 'RabbitMQ',
        };
        return <Tag color="blue">{typeMap[type] || type}</Tag>;
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const statusMap: Record<string, { color: string; text: string }> = {
          active: { color: 'success', text: '已连接' },
          inactive: { color: 'default', text: '未连接' },
          testing: { color: 'processing', text: '测试中' },
        };
        const cfg = statusMap[status] || statusMap.inactive;
        return <Tag color={cfg.color}>{cfg.text}</Tag>;
      },
    },
    {
      title: '创建时间',
      dataIndex: 'createdAt',
      key: 'createdAt',
      render: (date: string) => new Date(date).toLocaleString(),
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: DataSource) => (
        <Space>
          <Button
            type="link"
            icon={<PlayCircleOutlined />}
            onClick={() => handleTest(record.id)}
            loading={testing}
          >
            测试
          </Button>
          <Button type="link" icon={<EditOutlined />} onClick={() => handleEdit(record)}>
            编辑
          </Button>
          <Popconfirm title="确认删除?" onConfirm={() => handleDelete(record.id)}>
            <Button type="link" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const dataSourceTypes = [
    { value: 'mysql', label: 'MySQL' },
    { value: 'postgresql', label: 'PostgreSQL' },
    { value: 'mongodb', label: 'MongoDB' },
    { value: 'kafka', label: 'Kafka' },
    { value: 'rabbitmq', label: 'RabbitMQ' },
  ];

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">数据源管理</h1>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
          新增数据源
        </Button>
      </div>

      <Card>
        <Table columns={columns} dataSource={dataSources} rowKey="id" />
      </Card>

      <Modal
        title={editingItem ? '编辑数据源' : '新增数据源'}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        onOk={() => form.submit()}
        width={600}
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item name="name" label="名称" rules={[{ required: true, message: '请输入名称' }]}>
            <Input placeholder="请输入数据源名称" />
          </Form.Item>

          <Form.Item name="type" label="类型" rules={[{ required: true, message: '请选择类型' }]}>
            <Select placeholder="请选择数据源类型">
              {dataSourceTypes.map((item) => (
                <Option key={item.value} value={item.value}>
                  {item.label}
                </Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item noStyle shouldUpdate={(prev, curr) => prev.type !== curr.type}>
            {({ getFieldValue }) => {
              const type = getFieldValue('type');
              if (['mysql', 'postgresql'].includes(type)) {
                return (
                  <>
                    <Form.Item name="host" label="主机" rules={[{ required: true }]}>
                      <Input placeholder="localhost" />
                    </Form.Item>
                    <Form.Item name="port" label="端口" rules={[{ required: true }]}>
                      <InputNumber placeholder={type === 'mysql' ? '3306' : '5432'} style={{ width: '100%' }} />
                    </Form.Item>
                    <Form.Item name="database" label="数据库" rules={[{ required: true }]}>
                      <Input placeholder="请输入数据库名" />
                    </Form.Item>
                    <Form.Item name="username" label="用户名" rules={[{ required: true }]}>
                      <Input placeholder="请输入用户名" />
                    </Form.Item>
                    <Form.Item name="password" label="密码" rules={[{ required: true }]}>
                      <Input.Password placeholder="请输入密码" />
                    </Form.Item>
                  </>
                );
              }
              if (type === 'mongodb') {
                return (
                  <>
                    <Form.Item name="host" label="主机" rules={[{ required: true }]}>
                      <Input placeholder="localhost" />
                    </Form.Item>
                    <Form.Item name="port" label="端口" rules={[{ required: true }]}>
                      <InputNumber placeholder="27017" style={{ width: '100%' }} />
                    </Form.Item>
                    <Form.Item name="database" label="数据库" rules={[{ required: true }]}>
                      <Input placeholder="请输入数据库名" />
                    </Form.Item>
                  </>
                );
              }
              return null;
            }}
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default DataSourceList;
