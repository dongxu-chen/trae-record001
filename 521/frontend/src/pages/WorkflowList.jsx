import React, { useState, useEffect } from 'react';
import { Table, Button, Space, Tag, message, Popconfirm, Card, Row, Col, Statistic } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, PlayCircleOutlined, RocketOutlined, FileTextOutlined, CheckCircleOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { workflowApi } from '../api';

const WorkflowList = () => {
  const navigate = useNavigate();
  const [workflows, setWorkflows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState({ total: 0, published: 0, draft: 0 });

  useEffect(() => {
    fetchWorkflows();
  }, []);

  const fetchWorkflows = async () => {
    setLoading(true);
    try {
      const data = await workflowApi.list();
      setWorkflows(data);
      setStats({
        total: data.length,
        published: data.filter(w => w.status === 'PUBLISHED').length,
        draft: data.filter(w => w.status === 'DRAFT').length
      });
    } catch (err) {
      message.error('加载工作流列表失败');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id) => {
    try {
      await workflowApi.delete(id);
      message.success('删除成功');
      fetchWorkflows();
    } catch (err) {
      message.error('删除失败');
    }
  };

  const handlePublish = async (id) => {
    try {
      await workflowApi.publish(id);
      message.success('发布成功');
      fetchWorkflows();
    } catch (err) {
      message.error('发布失败');
    }
  };

  const handleTrigger = async (id) => {
    try {
      await workflowApi.trigger(id);
      message.success('已触发执行');
    } catch (err) {
      message.error('触发失败');
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
      title: '工作流名称',
      dataIndex: 'name',
      key: 'name',
      render: (text) => (
        <Space>
          <FileTextOutlined style={{ color: '#1890ff' }} />
          <span>{text}</span>
        </Space>
      ),
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status) => (
        <Tag color={status === 'PUBLISHED' ? 'green' : 'default'}>
          {status === 'PUBLISHED' ? '已发布' : '草稿'}
        </Tag>
      ),
    },
    {
      title: '任务数',
      key: 'taskCount',
      render: (_, record) => record.tasks?.length || 0,
    },
    {
      title: '版本',
      dataIndex: 'version',
      key: 'version',
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
      width: 280,
      render: (_, record) => (
        <Space size="small">
          <Button type="link" size="small" onClick={() => navigate(`/workflows/${record.id}/edit`)}>
            <EditOutlined /> 编辑
          </Button>
          {record.status === 'DRAFT' && (
            <Button type="link" size="small" onClick={() => handlePublish(record.id)}>
              <CheckCircleOutlined /> 发布
            </Button>
          )}
          {record.status === 'PUBLISHED' && (
            <Button type="link" size="small" onClick={() => handleTrigger(record.id)}>
              <PlayCircleOutlined /> 执行
            </Button>
          )}
          <Popconfirm title="确认删除?" onConfirm={() => handleDelete(record.id)} okText="确认" cancelText="取消">
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
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={8}>
          <Card>
            <Statistic title="工作流总数" value={stats.total} prefix={<FileTextOutlined style={{ color: '#1890ff' }} />} />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic title="已发布" value={stats.published} valueStyle={{ color: '#52c41a' }} prefix={<RocketOutlined />} />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic title="草稿" value={stats.draft} valueStyle={{ color: '#faad14' }} prefix={<FileTextOutlined />} />
          </Card>
        </Col>
      </Row>

      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'flex-end' }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate('/workflows/new')}>
          新建工作流
        </Button>
      </div>

      <Table columns={columns} dataSource={workflows} rowKey="id" loading={loading} pagination={{ pageSize: 10 }} />
    </div>
  );
};

export default WorkflowList;
