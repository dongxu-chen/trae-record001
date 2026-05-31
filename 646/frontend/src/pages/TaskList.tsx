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
  Card,
  message,
  Popconfirm,
  Progress,
} from 'antd';
import {
  PlusOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  EyeOutlined,
  DeleteOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useAppStore } from '@/store/appStore';
import { MigrationTask, taskApi } from '@/services/api';

const { Option } = Select;

const TaskList: React.FC = () => {
  const { tasks, dataSources, fetchTasks, fetchDataSources } = useAppStore();
  const [modalVisible, setModalVisible] = useState(false);
  const [form] = Form.useForm();
  const navigate = useNavigate();

  useEffect(() => {
    fetchTasks();
    fetchDataSources();
  }, [fetchTasks, fetchDataSources]);

  const handleAdd = () => {
    form.resetFields();
    setModalVisible(true);
  };

  const handleSubmit = async (values: any) => {
    try {
      const { name, sourceId, targetId, mode, tableName } = values;
      await taskApi.create({
        name,
        sourceId,
        targetId,
        mode,
        config: { tableName },
      });
      message.success('创建成功');
      setModalVisible(false);
      fetchTasks();
    } catch (error) {
      message.error('创建失败');
    }
  };

  const handleStart = async (id: string) => {
    try {
      await taskApi.start(id);
      message.success('任务已启动');
      fetchTasks();
    } catch (error) {
      message.error('启动失败');
    }
  };

  const handlePause = async (id: string) => {
    try {
      await taskApi.pause(id);
      message.success('任务已暂停');
      fetchTasks();
    } catch (error) {
      message.error('暂停失败');
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await taskApi.delete(id);
      message.success('删除成功');
      fetchTasks();
    } catch (error) {
      message.error('删除失败');
    }
  };

  const columns = [
    {
      title: '任务名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '源数据源',
      dataIndex: 'sourceId',
      key: 'sourceId',
      render: (id: string) => {
        const ds = dataSources.find((d) => d.id === id);
        return ds?.name || '-';
      },
    },
    {
      title: '目标数据源',
      dataIndex: 'targetId',
      key: 'targetId',
      render: (id: string) => {
        const ds = dataSources.find((d) => d.id === id);
        return ds?.name || '-';
      },
    },
    {
      title: '模式',
      dataIndex: 'mode',
      key: 'mode',
      render: (mode: string) => (
        <Tag color={mode === 'full' ? 'blue' : 'green'}>{mode === 'full' ? '全量' : '增量'}</Tag>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const statusMap: Record<string, { color: string; text: string }> = {
          running: { color: 'processing', text: '运行中' },
          completed: { color: 'success', text: '已完成' },
          pending: { color: 'default', text: '等待中' },
          failed: { color: 'error', text: '失败' },
          paused: { color: 'warning', text: '已暂停' },
        };
        const cfg = statusMap[status] || statusMap.pending;
        return <Tag color={cfg.color}>{cfg.text}</Tag>;
      },
    },
    {
      title: '进度',
      dataIndex: 'progress',
      key: 'progress',
      render: (_: any, record: MigrationTask) => {
        let percent = 0;
        if (record.status === 'completed') percent = 100;
        else if (record.status === 'running') percent = 50;

        return (
          <Progress
            percent={percent}
            size="small"
            status={record.status === 'failed' ? 'exception' : undefined}
          />
        );
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
      render: (_: any, record: MigrationTask) => (
        <Space>
          <Button
            type="link"
            icon={<EyeOutlined />}
            onClick={() => navigate(`/task/${record.id}/monitor`)}
          >
            监控
          </Button>
          {record.status === 'pending' && (
            <Button type="link" icon={<PlayCircleOutlined />} onClick={() => handleStart(record.id)}>
              启动
            </Button>
          )}
          {record.status === 'running' && (
            <Button type="link" icon={<PauseCircleOutlined />} onClick={() => handlePause(record.id)}>
              暂停
            </Button>
          )}
          <Popconfirm title="确认删除?" onConfirm={() => handleDelete(record.id)}>
            <Button type="link" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">迁移任务</h1>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
          新建任务
        </Button>
      </div>

      <Card>
        <Table columns={columns} dataSource={tasks} rowKey="id" />
      </Card>

      <Modal
        title="新建迁移任务"
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        onOk={() => form.submit()}
        width={600}
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item name="name" label="任务名称" rules={[{ required: true, message: '请输入任务名称' }]}>
            <Input placeholder="请输入任务名称" />
          </Form.Item>

          <Form.Item name="sourceId" label="源数据源" rules={[{ required: true, message: '请选择源数据源' }]}>
            <Select placeholder="请选择源数据源">
              {dataSources.map((ds) => (
                <Option key={ds.id} value={ds.id}>
                  {ds.name}
                </Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item name="targetId" label="目标数据源" rules={[{ required: true, message: '请选择目标数据源' }]}>
            <Select placeholder="请选择目标数据源">
              {dataSources.map((ds) => (
                <Option key={ds.id} value={ds.id}>
                  {ds.name}
                </Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item name="mode" label="迁移模式" rules={[{ required: true, message: '请选择迁移模式' }]}>
            <Select placeholder="请选择迁移模式">
              <Option value="full">全量迁移</Option>
              <Option value="incremental">增量迁移</Option>
            </Select>
          </Form.Item>

          <Form.Item name="tableName" label="表名" rules={[{ required: true, message: '请输入表名' }]}>
            <Input placeholder="请输入要迁移的表名" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default TaskList;
