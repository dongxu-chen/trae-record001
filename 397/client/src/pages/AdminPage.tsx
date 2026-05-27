import React, { useEffect, useState } from 'react';
import {
  Table, Button, Space, Tag, Modal, Input, message, Card, Row, Col, Statistic
} from 'antd';
import {
  CheckOutlined, CloseOutlined, SearchOutlined,
  ClockCircleOutlined, CheckCircleOutlined, StopOutlined,
  UserOutlined, FileOutlined, CommentOutlined
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useSelector } from 'react-redux';
import { RootState } from '../store';
import { adminAPI } from '../services/api';
import { Template } from '../types';
import { formatDate, formatNumber } from '../utils/helpers';

const { TextArea } = Input;

const AdminPage: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useSelector((state: RootState) => state.auth);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [loading, setLoading] = useState(false);
  const [pagination, setPagination] = useState({ current: 1, pageSize: 10, total: 0 });
  const [rejectModalVisible, setRejectModalVisible] = useState(false);
  const [rejectReason, setRejectReason] = useState('');
  const [selectedTemplate, setSelectedTemplate] = useState<Template | null>(null);
  const [statistics, setStatistics] = useState<any>(null);

  useEffect(() => {
    if (user?.role !== 'admin') {
      navigate('/');
      message.warning('无权限访问');
      return;
    }
    fetchPendingTemplates();
    fetchStatistics();
  }, [user, navigate]);

  const fetchPendingTemplates = async (page = 1, pageSize = 10) => {
    setLoading(true);
    try {
      const response = await adminAPI.getPendingTemplates(page, pageSize);
      setTemplates(response.templates);
      setPagination({
        current: page,
        pageSize,
        total: response.pagination.total
      });
    } catch (error) {
      console.error('获取待审核模板失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchStatistics = async () => {
    try {
      const response = await adminAPI.getStatistics();
      setStatistics(response);
    } catch (error) {
      console.error('获取统计数据失败:', error);
    }
  };

  const handleApprove = async (template: Template) => {
    Modal.confirm({
      title: '确认通过审核',
      content: `确定要通过模板「${template.title}」的审核吗？`,
      okText: '通过',
      cancelText: '取消',
      onOk: async () => {
        try {
          await adminAPI.approveTemplate(template._id);
          message.success('审核通过');
          fetchPendingTemplates(pagination.current, pagination.pageSize);
          fetchStatistics();
        } catch (error) {
          message.error('操作失败');
        }
      }
    });
  };

  const showRejectModal = (template: Template) => {
    setSelectedTemplate(template);
    setRejectReason('');
    setRejectModalVisible(true);
  };

  const handleReject = async () => {
    if (!selectedTemplate || !rejectReason.trim()) {
      message.warning('请填写拒绝原因');
      return;
    }

    try {
      await adminAPI.rejectTemplate(selectedTemplate._id, rejectReason);
      message.success('已拒绝');
      setRejectModalVisible(false);
      fetchPendingTemplates(pagination.current, pagination.pageSize);
      fetchStatistics();
    } catch (error) {
      message.error('操作失败');
    }
  };

  const handleViewTemplate = (id: string) => {
    navigate(`/preview/${id}`);
  };

  const columns = [
    {
      title: '模板',
      dataIndex: 'title',
      key: 'title',
      render: (text: string, record: Template) => (
        <div className="flex items-center gap-3">
          <img
            src={record.thumbnail}
            alt={text}
            className="w-16 h-12 object-cover rounded"
          />
          <div>
            <p className="text-white font-medium cursor-pointer hover:text-blue-400"
               onClick={() => handleViewTemplate(record._id)}>
              {text}
            </p>
            <p className="text-slate-400 text-sm">{record.author?.username}</p>
          </div>
        </div>
      )
    },
    {
      title: '分类',
      dataIndex: 'category',
      key: 'category',
      width: 100,
      render: (category: string) => {
        const colors: Record<string, string> = {
          operation: 'blue',
          sales: 'cyan',
          finance: 'green',
          ops: 'purple'
        };
        const labels: Record<string, string> = {
          operation: '运营',
          sales: '销售',
          finance: '财务',
          ops: '运维'
        };
        return <Tag color={colors[category]}>{labels[category]}</Tag>;
      }
    },
    {
      title: '提交时间',
      dataIndex: 'createdAt',
      key: 'createdAt',
      width: 180,
      render: (date: string) => formatDate(date)
    },
    {
      title: '操作',
      key: 'action',
      width: 180,
      render: (_: any, record: Template) => (
        <Space>
          <Button
            type="primary"
            size="small"
            icon={<CheckOutlined />}
            onClick={() => handleApprove(record)}
          >
            通过
          </Button>
          <Button
            danger
            size="small"
            icon={<CloseOutlined />}
            onClick={() => showRejectModal(record)}
          >
            拒绝
          </Button>
          <Button
            size="small"
            icon={<SearchOutlined />}
            onClick={() => handleViewTemplate(record._id)}
          >
            预览
          </Button>
        </Space>
      )
    }
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">模板审核管理</h1>
      </div>

      {statistics && (
        <Row gutter={[16, 16]}>
          <Col xs={12} sm={6}>
            <Card>
              <Statistic
                title="待审核"
                value={statistics.overview.pendingTemplates}
                prefix={<ClockCircleOutlined style={{ color: '#F59E0B' }} />}
                valueStyle={{ color: '#F59E0B' }}
              />
            </Card>
          </Col>
          <Col xs={12} sm={6}>
            <Card>
              <Statistic
                title="已通过"
                value={statistics.overview.approvedTemplates}
                prefix={<CheckCircleOutlined style={{ color: '#10B981' }} />}
                valueStyle={{ color: '#10B981' }}
              />
            </Card>
          </Col>
          <Col xs={12} sm={6}>
            <Card>
              <Statistic
                title="已拒绝"
                value={statistics.overview.rejectedTemplates}
                prefix={<StopOutlined style={{ color: '#EF4444' }} />}
                valueStyle={{ color: '#EF4444' }}
              />
            </Card>
          </Col>
          <Col xs={12} sm={6}>
            <Card>
              <Statistic
                title="总模板数"
                value={statistics.overview.totalTemplates}
                prefix={<FileOutlined />}
              />
            </Card>
          </Col>
          <Col xs={12} sm={6}>
            <Card>
              <Statistic
                title="用户数"
                value={statistics.overview.totalUsers}
                prefix={<UserOutlined />}
              />
            </Card>
          </Col>
          <Col xs={12} sm={6}>
            <Card>
              <Statistic
                title="评论数"
                value={statistics.overview.totalComments}
                prefix={<CommentOutlined />}
              />
            </Card>
          </Col>
        </Row>
      )}

      <Card title="待审核模板" style={{ background: '#1E293B' }}>
        <Table
          columns={columns}
          dataSource={templates}
          rowKey="_id"
          loading={loading}
          pagination={{
            ...pagination,
            onChange: (page, pageSize) => fetchPendingTemplates(page, pageSize),
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条`
          }}
        />
      </Card>

      <Modal
        title="拒绝模板"
        open={rejectModalVisible}
        onOk={handleReject}
        onCancel={() => setRejectModalVisible(false)}
        okText="确认拒绝"
        okButtonProps={{ danger: true }}
        cancelText="取消"
      >
        <p className="mb-4 text-slate-400">
          请填写拒绝「{selectedTemplate?.title}」的原因：
        </p>
        <TextArea
          value={rejectReason}
          onChange={(e) => setRejectReason(e.target.value)}
          placeholder="请输入拒绝原因..."
          rows={4}
          maxLength={500}
          showCount
        />
      </Modal>
    </div>
  );
};

export default AdminPage;
