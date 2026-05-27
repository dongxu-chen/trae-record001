import React, { useEffect, useState } from 'react';
import { Tabs, Card, Row, Col, Statistic, Empty, Button, Tag, Space } from 'antd';
import { UserOutlined, UploadOutlined, HeartOutlined, DownloadOutlined, ClockCircleOutlined, CheckCircleOutlined, StopOutlined, EyeOutlined } from '@ant-design/icons';
import { useSelector } from 'react-redux';
import { RootState } from '../store';
import { userAPI } from '../services/api';
import { Template, Statistics } from '../types';
import TemplateCard from '../components/TemplateCard';
import ChartRenderer from '../components/ChartRenderer';
import { useNavigate } from 'react-router-dom';
import { formatDate } from '../utils/helpers';

const ProfilePage: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useSelector((state: RootState) => state.auth);
  const [activeTab, setActiveTab] = useState('templates');
  const [templates, setTemplates] = useState<Template[]>([]);
  const [favorites, setFavorites] = useState<Template[]>([]);
  const [downloads, setDownloads] = useState<Template[]>([]);
  const [statistics, setStatistics] = useState<Statistics | null>(null);
  const [downloadTrend, setDownloadTrend] = useState<Array<{ _id: string; count: number }>>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (activeTab === 'templates') {
      fetchMyTemplates();
    } else if (activeTab === 'favorites') {
      fetchFavorites();
    } else if (activeTab === 'downloads') {
      fetchDownloads();
    }
  }, [activeTab]);

  useEffect(() => {
    fetchStatistics();
  }, []);

  const fetchMyTemplates = async () => {
    setLoading(true);
    try {
      const response = await userAPI.getMyTemplates();
      setTemplates(response.templates);
    } catch (error) {
      console.error('获取我的模板失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchFavorites = async () => {
    setLoading(true);
    try {
      const response = await userAPI.getFavorites();
      setFavorites(response.templates);
    } catch (error) {
      console.error('获取收藏失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchDownloads = async () => {
    setLoading(true);
    try {
      const response = await userAPI.getDownloadHistory();
      setDownloads(response.templates);
    } catch (error) {
      console.error('获取下载历史失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchStatistics = async () => {
    try {
      const response = await userAPI.getStatistics();
      setStatistics(response.statistics);
      setDownloadTrend(response.downloadTrend);
    } catch (error) {
      console.error('获取统计数据失败:', error);
    }
  };

  const tabItems = [
    { key: 'templates', label: '我的模板', icon: <UploadOutlined /> },
    { key: 'favorites', label: '我的收藏', icon: <HeartOutlined /> },
    { key: 'downloads', label: '下载历史', icon: <DownloadOutlined /> }
  ];

  const getStatusTag = (status?: string) => {
    switch (status) {
      case 'pending':
        return <Tag icon={<ClockCircleOutlined />} color="orange">审核中</Tag>;
      case 'approved':
        return <Tag icon={<CheckCircleOutlined />} color="green">已通过</Tag>;
      case 'rejected':
        return <Tag icon={<StopOutlined />} color="red">已拒绝</Tag>;
      default:
        return <Tag color="gray">未知</Tag>;
    }
  };

  const renderMyTemplates = (list: Template[]) => {
    if (list.length === 0) {
      return <Empty description="暂无数据" style={{ marginTop: 60 }} />;
    }
    return (
      <Row gutter={[24, 24]}>
        {list.map((template) => (
          <Col xs={24} sm={12} lg={8} xl={6} key={template._id}>
            <Card
              hoverable
              className="h-full cursor-pointer"
              style={{ background: '#1E293B', border: 'none', borderRadius: '16px', overflow: 'hidden' }}
              onClick={() => navigate(`/templates/${template._id}`)}
              bodyStyle={{ padding: 0 }}
            >
              <div className="relative">
                <img src={template.thumbnail} alt={template.title} className="w-full h-40 object-cover" />
                <div className="absolute top-3 left-3">
                  {getStatusTag(template.status)}
                </div>
              </div>
              <div className="p-4">
                <h3 className="text-white font-semibold mb-2 truncate">{template.title}</h3>
                {template.status === 'rejected' && template.rejectReason && (
                  <p className="text-red-400 text-sm mb-2 line-clamp-2">拒绝原因: {template.rejectReason}</p>
                )}
                <p className="text-slate-500 text-xs">提交时间: {formatDate(template.createdAt)}</p>
                <div className="flex items-center justify-end mt-3">
                  <Button size="small" icon={<EyeOutlined />} onClick={(e) => { e.stopPropagation(); navigate(`/preview/${template._id}`); }}>
                    预览
                  </Button>
                </div>
              </div>
            </Card>
          </Col>
        ))}
      </Row>
    );
  };

  const renderTemplateList = (list: Template[]) => {
    if (list.length === 0) {
      return <Empty description="暂无数据" style={{ marginTop: 60 }} />;
    }
    return (
      <Row gutter={[24, 24]}>
        {list.map((template) => (
          <Col xs={24} sm={12} lg={8} xl={6} key={template._id}>
            <TemplateCard template={template} />
          </Col>
        ))}
      </Row>
    );
  };

  const trendComponent = {
    id: 'trend',
    type: 'chart' as const,
    chartType: 'line' as const,
    title: '下载趋势',
    position: { x: 0, y: 0 },
    size: { w: 12, h: 4 },
    config: {},
    dataSource: { type: 'static' as const }
  };

  return (
    <div className="space-y-6">
      <Card className="overflow-hidden" style={{ background: 'linear-gradient(135deg, #1E3A8A 0%, #4C1D95 100%)', borderRadius: '16px', border: 'none' }}>
        <div className="flex items-center gap-6 text-white">
          <div className="w-20 h-20 rounded-full bg-white/20 flex items-center justify-center text-4xl">
            <UserOutlined />
          </div>
          <div className="flex-1">
            <h1 className="text-2xl font-bold mb-1">{user?.username}</h1>
            <p className="text-blue-200">{user?.email}</p>
            <p className="text-sm text-blue-300 mt-2">
              加入于 {user?.createdAt ? new Date(user.createdAt).toLocaleDateString('zh-CN') : ''}
            </p>
          </div>
          {user?.role === 'creator' && (
            <span className="px-4 py-2 bg-orange-500/20 text-orange-300 rounded-full text-sm">
              创作者
            </span>
          )}
          {user?.role === 'admin' && (
            <span className="px-4 py-2 bg-red-500/20 text-red-300 rounded-full text-sm">
              管理员
            </span>
          )}
        </div>
      </Card>

      {statistics && (
        <Row gutter={[24, 24]}>
          <Col xs={24} sm={12} lg={6}>
            <Card className="text-center" style={{ background: '#1E293B', borderRadius: '12px' }}>
              <Statistic title="模板数量" value={statistics.templateCount} valueStyle={{ color: '#3B82F6' }} />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card className="text-center" style={{ background: '#1E293B', borderRadius: '12px' }}>
              <Statistic title="总下载量" value={statistics.totalDownloads} valueStyle={{ color: '#10B981' }} />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card className="text-center" style={{ background: '#1E293B', borderRadius: '12px' }}>
              <Statistic title="总浏览量" value={statistics.totalViews} valueStyle={{ color: '#F59E0B' }} />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card className="text-center" style={{ background: '#1E293B', borderRadius: '12px' }}>
              <Statistic title="平均评分" value={statistics.avgRating} precision={1} valueStyle={{ color: '#8B5CF6' }} />
            </Card>
          </Col>
        </Row>
      )}

      {downloadTrend.length > 0 && (
        <Card title="下载趋势" style={{ background: '#1E293B', borderRadius: '12px' }}>
          <div style={{ height: '300px' }}>
            <ChartRenderer component={trendComponent} />
          </div>
        </Card>
      )}

      <Card style={{ background: '#1E293B', borderRadius: '12px' }} bodyStyle={{ padding: 0 }}>
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={tabItems}
          tabBarStyle={{ padding: '0 24px', marginBottom: 0 }}
        />
        <div className="p-6">
          {activeTab === 'templates' && (
            <div>
              <div className="flex justify-between items-center mb-4">
                <Space wrap>
                  {getStatusTag('pending')}
                  <span className="text-slate-400 text-sm">待审核: {templates.filter(t => t.status === 'pending').length}</span>
                  {getStatusTag('approved')}
                  <span className="text-slate-400 text-sm">已通过: {templates.filter(t => t.status === 'approved').length}</span>
                  {getStatusTag('rejected')}
                  <span className="text-slate-400 text-sm">已拒绝: {templates.filter(t => t.status === 'rejected').length}</span>
                </Space>
                <Button type="primary" icon={<UploadOutlined />} onClick={() => navigate('/upload')}>
                  上传新模板
                </Button>
              </div>
              {renderMyTemplates(templates)}
            </div>
          )}
          {activeTab === 'favorites' && renderTemplateList(favorites)}
          {activeTab === 'downloads' && renderTemplateList(downloads)}
        </div>
      </Card>
    </div>
  );
};

export default ProfilePage;
