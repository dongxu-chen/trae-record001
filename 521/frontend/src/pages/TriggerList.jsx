import React, { useState, useEffect } from 'react';
import { Table, Button, Space, Tag, Switch, message, Popconfirm, Card } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, ClockCircleOutlined, ThunderboltOutlined, ApiOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { triggerApi } from '../api';
import { TriggerTypeLabels } from '../types';

const TriggerList = () => {
  const navigate = useNavigate();
  const [triggers, setTriggers] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchTriggers();
  }, []);

  const fetchTriggers = async () => {
    setLoading(true);
    try {
      const data = await triggerApi.list();
      setTriggers(data);
    } catch (err) {
      message.error('加载触发策略列表失败');
    } finally {
      setLoading(false);
    }
  };

  const handleToggle = async (id, enabled) => {
    try {
      await triggerApi.toggle(id, enabled);
      message.success(enabled ? '已启用' : '已禁用');
      fetchTriggers();
    } catch (err) {
      message.error('操作失败');
    }
  };

  const handleDelete = async (id) => {
    try {
      await triggerApi.delete(id);
      message.success('删除成功');
      fetchTriggers();
    } catch (err) {
      message.error('删除失败');
    }
  };

  const getTypeIcon = (type) => {
    switch (type) {
      case 'CRON': return <ClockCircleOutlined />;
      case 'EVENT': return <ThunderboltOutlined />;
      case 'WEBHOOK': return <ApiOutlined />;
      default: return null;
    }
  };

  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 80,
    },
    {
      title: '工作流ID',
      dataIndex: 'workflowId',
      key: 'workflowId',
      width: 100,
    },
    {
      title: '触发类型',
      dataIndex: 'triggerType',
      key: 'triggerType',
      width: 130,
      render: (type) => (
        <Space>
          {getTypeIcon(type)}
          {TriggerTypeLabels[type] || type}
        </Space>
      ),
    },
    {
      title: '配置',
      key: 'config',
      render: (_, record) => {
        if (record.triggerType === 'CRON') {
          return <Tag color="blue">{record.cronExpression}</Tag>;
        }
        if (record.triggerType === 'EVENT') {
          return <Tag color="purple">Topic: {record.eventTopic}</Tag>;
        }
        if (record.triggerType === 'WEBHOOK') {
          return <Tag color="green">/webhook/{record.webhookPath}</Tag>;
        }
        return '-';
      },
    },
    {
      title: '状态',
      dataIndex: 'enabled',
      key: 'enabled',
      width: 100,
      render: (enabled) => (
        <Tag color={enabled ? 'green' : 'default'}>
          {enabled ? '已启用' : '已禁用'}
        </Tag>
      ),
    },
    {
      title: '最后触发时间',
      dataIndex: 'lastTriggerTime',
      key: 'lastTriggerTime',
      width: 180,
    },
    {
      title: '创建时间',
      dataIndex: 'createdAt',
      key: 'createdAt',
      width: 180,
    },
    {
      title: '操作',
      key: 'action',
      width: 220,
      render: (_, record) => (
        <Space size="small">
          <Switch
            checked={record.enabled}
            onChange={(checked) => handleToggle(record.id, checked)}
            size="small"
          />
          <Button
            type="link"
            size="small"
            onClick={() => navigate(`/triggers/${record.id}/edit`)}
          >
            <EditOutlined /> 编辑
          </Button>
          <Popconfirm
            title="确认删除?"
            onConfirm={() => handleDelete(record.id)}
            okText="确认"
            cancelText="取消"
          >
            <Button type="link" size="small" danger>
              <DeleteOutlined /> 删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'flex-end' }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate('/triggers/new')}>
          新建触发策略
        </Button>
      </div>

      <Card>
        <Table
          columns={columns}
          dataSource={triggers}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 10 }}
        />
      </Card>
    </div>
  );
};

export default TriggerList;
