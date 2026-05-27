import React, { useEffect, useState, useCallback } from 'react';
import { Row, Col, Button, Tag, Rate, Avatar, Carousel, Descriptions, List, Input, Modal, message, Radio, Badge, Space } from 'antd';
import {
  DownloadOutlined, HeartOutlined, EditOutlined, ShareAltOutlined,
  UserOutlined, SendOutlined, HeartFilled, MergeOutlined,
  WarningOutlined, CheckCircleOutlined, ReloadOutlined, EyeOutlined
} from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import { useSelector } from 'react-redux';
import { RootState } from '../store';
import { templateAPI, commentAPI, userAPI } from '../services/api';
import { Template, Comment, TemplateComponent, LayoutConfig } from '../types';
import { getCategoryInfo, getComplexityInfo, formatDate, formatNumber } from '../utils/helpers';
import ChartRenderer from '../components/ChartRenderer';
import useWebSocket from '../hooks/useWebSocket';

const { TextArea } = Input;
const { confirm } = Modal;

const TemplateDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { isAuthenticated } = useSelector((state: RootState) => state.auth);
  const [template, setTemplate] = useState<Template | null>(null);
  const [comments, setComments] = useState<Comment[]>([]);
  const [loading, setLoading] = useState(false);
  const [commentText, setCommentText] = useState('');
  const [rating, setRating] = useState(5);
  const [isFavorite, setIsFavorite] = useState(false);
  const [previewVisible, setPreviewVisible] = useState(false);
  const [applyModalVisible, setApplyModalVisible] = useState(false);
  const [applyMode, setApplyMode] = useState<'merge' | 'overwrite'>('merge');
  const [hasRated, setHasRated] = useState(false);
  const [userRating, setUserRating] = useState<number | null>(null);
  const [localConfig, setLocalConfig] = useState<{ components: TemplateComponent[]; layout: LayoutConfig } | null>(null);

  const handleStatsUpdate = useCallback((stats: any) => {
    if (template) {
      setTemplate(prev => {
        if (!prev) return prev;
        return {
          ...prev,
          viewCount: stats.viewCount ?? prev.viewCount,
          downloadCount: stats.downloadCount ?? prev.downloadCount,
          rating: stats.rating ?? prev.rating,
          ratingCount: stats.ratingCount ?? prev.ratingCount
        };
      });
    }
  }, [template]);

  const { isConnected } = useWebSocket({
    templateId: id,
    onTemplateStatsUpdate: handleStatsUpdate
  });

  useEffect(() => {
    if (id) {
      fetchTemplate();
      fetchComments();
      if (isAuthenticated) {
        checkUserRating();
      }
    }
  }, [id, isAuthenticated]);

  useEffect(() => {
    const saved = localStorage.getItem('dashboard_config');
    if (saved) {
      try {
        setLocalConfig(JSON.parse(saved));
      } catch (e) {
        console.error('解析本地配置失败:', e);
      }
    }
  }, []);

  const fetchTemplate = async () => {
    if (!id) return;
    setLoading(true);
    try {
      const response = await templateAPI.getTemplateById(id);
      setTemplate(response.template);
    } catch (error) {
      console.error('获取模板详情失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchComments = async () => {
    if (!id) return;
    try {
      const response = await commentAPI.getComments(id);
      setComments(response.comments);
    } catch (error) {
      console.error('获取评论失败:', error);
    }
  };

  const checkUserRating = async () => {
    if (!id) return;
    try {
      const response = await templateAPI.getUserRating(id);
      setHasRated(response.hasRated);
      setUserRating(response.userRating);
    } catch (error) {
      console.error('检查用户评分失败:', error);
    }
  };

  const showApplyConfirm = () => {
    if (!template) return;

    confirm({
      title: '应用模板确认',
      icon: <WarningOutlined style={{ color: '#FAAD14' }} />,
      content: (
        <div className="space-y-4">
          <p>请选择应用模式：</p>
          <Radio.Group
            value={applyMode}
            onChange={(e) => setApplyMode(e.target.value)}
            className="w-full"
          >
            <Space direction="vertical" className="w-full">
              <Radio value="merge" className="w-full">
                <div className="py-2">
                  <p className="font-medium text-white flex items-center gap-2">
                    <MergeOutlined /> 合并模式
                  </p>
                  <p className="text-sm text-slate-400 ml-6">
                    将模板组件与现有配置合并，保留您的自定义组件
                  </p>
                </div>
              </Radio>
              <Radio value="overwrite" className="w-full">
                <div className="py-2">
                  <p className="font-medium text-white flex items-center gap-2">
                    <ReloadOutlined /> 覆盖模式
                  </p>
                  <p className="text-sm text-slate-400 ml-6">
                    完全替换现有配置，原有配置将被备份
                  </p>
                </div>
              </Radio>
            </Space>
          </Radio.Group>
          
          {applyMode === 'overwrite' && localConfig && (
            <div className="p-4 rounded-lg" style={{ background: '#0F172A' }}>
              <p className="text-sm text-slate-400 mb-2">
                <CheckCircleOutlined style={{ color: '#10B981', marginRight: 8 }} />
                检测到本地配置，将在应用前自动备份
              </p>
              <p className="text-xs text-slate-500">
                备份包含 {localConfig.components.length} 个组件
              </p>
            </div>
          )}
        </div>
      ),
      okText: `确认${applyMode === 'merge' ? '合并' : '覆盖'}`,
      cancelText: '取消',
      onOk: handleApplyTemplate,
      okButtonProps: {
        danger: applyMode === 'overwrite'
      }
    });
  };

  const handleApplyTemplate = async () => {
    if (!id || !template) return;
    
    try {
      let backup = null;
      if (applyMode === 'overwrite' && localConfig) {
        backup = {
          ...localConfig,
          templateId: id,
          backedUpAt: new Date().toISOString()
        };
        
        const backups = JSON.parse(localStorage.getItem('template_backups') || '[]');
        backups.unshift(backup);
        localStorage.setItem('template_backups', JSON.stringify(backups.slice(0, 10)));
        
        message.info('本地配置已备份，可在设置中恢复');
      }

      const response = await templateAPI.applyTemplate(id, applyMode, backup);
      
      if (applyMode === 'merge' && localConfig) {
        const mergedComponents = [
          ...localConfig.components,
          ...response.template.components
        ];
        
        localStorage.setItem('dashboard_config', JSON.stringify({
          components: mergedComponents,
          layout: response.template.layout
        }));
        
        message.success(`模板合并成功！已添加 ${response.template.components.length} 个新组件`);
      } else {
        localStorage.setItem('dashboard_config', JSON.stringify({
          components: response.template.components,
          layout: response.template.layout
        }));
        
        message.success('模板覆盖应用成功！');
      }
      
      navigate('/editor/new');
    } catch (error: any) {
      message.error(error.response?.data?.message || '应用模板失败');
    }
  };

  const handleDownload = async () => {
    if (!id) return;
    try {
      await templateAPI.downloadTemplate(id);
      message.success('下载成功！模板已保存到您的空间');
    } catch (error) {
      console.error('下载失败:', error);
      message.error('下载失败，请重试');
    }
  };

  const handleFavorite = async () => {
    if (!id) return;
    try {
      if (isFavorite) {
        await userAPI.removeFavorite(id);
        setIsFavorite(false);
        message.success('已取消收藏');
      } else {
        await userAPI.addFavorite(id);
        setIsFavorite(true);
        message.success('收藏成功');
      }
    } catch (error) {
      console.error('收藏失败:', error);
    }
  };

  const handleSubmitComment = async () => {
    if (!id || !commentText.trim()) return;
    
    if (hasRated) {
      message.warning('您已对此模板评分，每个模板只能评分一次');
      return;
    }

    try {
      await commentAPI.createComment(id, commentText, rating);
      message.success('评论发表成功');
      setCommentText('');
      setRating(5);
      setHasRated(true);
      setUserRating(rating);
      fetchComments();
      fetchTemplate();
    } catch (error: any) {
      if (error.response?.status === 400) {
        message.error(error.response.data.message);
      } else {
        message.error('发表评论失败，请重试');
      }
    }
  };

  const handleEditTemplate = () => {
    navigate(`/editor/${id}`);
  };

  if (loading || !template) {
    return <div className="flex items-center justify-center h-96 text-white">加载中...</div>;
  }

  const categoryInfo = getCategoryInfo(template.category);
  const complexityInfo = getComplexityInfo(template.complexity);

  return (
    <div className="space-y-8">
      <Row gutter={[24, 24]}>
        <Col xs={24} lg={16}>
          <div className="rounded-2xl overflow-hidden cursor-pointer" style={{ background: '#1E293B' }} onClick={() => setPreviewVisible(true)}>
            <img
              src={template.thumbnail}
              alt={template.title}
              className="w-full h-96 object-cover"
            />
            <div className="p-4 border-t border-slate-700">
              <div className="flex gap-2 overflow-x-auto">
                {template.previewImages.map((img, idx) => (
                  <img
                    key={idx}
                    src={img}
                    alt={`预览 ${idx + 1}`}
                    className="w-20 h-14 object-cover rounded-lg flex-shrink-0 border-2 border-transparent hover:border-blue-500 transition-colors"
                  />
                ))}
              </div>
            </div>
          </div>
        </Col>

        <Col xs={24} lg={8}>
          <div className="sticky top-24 space-y-6">
            <div className="p-6 rounded-2xl" style={{ background: '#1E293B' }}>
              <div className="flex items-center gap-2 mb-4">
                <Badge dot color={isConnected ? '#10B981' : '#EF4444'} offset={[5, 5]}>
                  <Tag color={categoryInfo.color} style={{ borderRadius: '4px' }}>
                    {categoryInfo.label}
                  </Tag>
                </Badge>
                <Tag color={complexityInfo.color} style={{ borderRadius: '4px' }}>
                  {complexityInfo.label}
                </Tag>
                {template.price > 0 ? (
                  <Tag color="orange" style={{ borderRadius: '4px' }}>¥{template.price}</Tag>
                ) : (
                  <Tag color="green" style={{ borderRadius: '4px' }}>免费</Tag>
                )}
              </div>

              <h1 className="text-2xl font-bold text-white mb-3">{template.title}</h1>
              <p className="text-slate-400 mb-6">{template.description}</p>

              <div className="flex items-center gap-6 mb-6 text-sm">
                <div className="flex items-center gap-2">
                  <Rate disabled value={template.rating} count={5} />
                  <span className="text-white">{template.rating.toFixed(1)}</span>
                </div>
                <span className="text-slate-400">{template.ratingCount} 条评价</span>
                <span className="text-slate-400">{formatNumber(template.downloadCount)} 次下载</span>
              </div>

              <div className="space-y-3">
                <Button
                  type="primary"
                  size="large"
                  block
                  icon={<DownloadOutlined />}
                  onClick={handleDownload}
                >
                  下载模板
                </Button>
                <Button
                  size="large"
                  block
                  icon={<MergeOutlined />}
                  onClick={showApplyConfirm}
                  type="default"
                >
                  应用模板
                </Button>
                <Button
                  size="large"
                  block
                  icon={<EyeOutlined />}
                  onClick={() => navigate(`/preview/${id}`)}
                  type="default"
                >
                  在线预览
                </Button>
                <div className="flex gap-3">
                  <Button
                    size="large"
                    block
                    icon={isFavorite ? <HeartFilled style={{ color: '#EF4444' }} /> : <HeartOutlined />}
                    onClick={handleFavorite}
                  >
                    {isFavorite ? '已收藏' : '收藏'}
                  </Button>
                  <Button size="large" block icon={<EditOutlined />} onClick={handleEditTemplate}>
                    在线编辑
                  </Button>
                </div>
                <Button size="large" block icon={<ShareAltOutlined />}>
                  分享模板
                </Button>
              </div>
            </div>

            <div className="p-6 rounded-2xl" style={{ background: '#1E293B' }}>
              <div className="flex items-center gap-3 mb-4">
                <Avatar size={48} icon={<UserOutlined />} src={template.author.avatar} />
                <div>
                  <p className="text-white font-semibold">{template.author.username}</p>
                  <p className="text-slate-400 text-sm">
                    加入于 {formatDate(template.author.createdAt)}
                  </p>
                </div>
              </div>
              {template.author.bio && (
                <p className="text-slate-400 text-sm">{template.author.bio}</p>
              )}
            </div>
          </div>
        </Col>
      </Row>

      {template.components && template.components.length > 0 && (
        <div className="p-6 rounded-2xl" style={{ background: '#1E293B' }}>
          <h2 className="text-xl font-bold text-white mb-6">模板预览</h2>
          <div className="grid gap-4" style={{
            display: 'grid',
            gridTemplateColumns: `repeat(${template.layout.gridCols}, 1fr)`,
            gridAutoRows: '100px',
            gap: `${template.layout.gutter}px`,
            background: template.layout.backgroundColor,
            padding: `${template.layout.gutter}px`,
            borderRadius: '12px'
          }}>
            {template.components.map((comp) => (
              <div
                key={comp.id}
                className="rounded-xl p-4"
                style={{
                  gridColumn: `${comp.position.x + 1} / span ${comp.size.w}`,
                  gridRow: `${comp.position.y + 1} / span ${comp.size.h}`,
                  background: '#1E293B',
                  border: '1px solid #334155'
                }}
              >
                <h4 className="text-white font-medium mb-2">{comp.title}</h4>
                {comp.type === 'chart' && <ChartRenderer component={comp} style={{ height: 'calc(100% - 30px)' }} />}
                {comp.type === 'metric' && (
                  <div className="text-center py-4">
                    <p className="text-3xl font-bold text-white">{comp.config.value}</p>
                    <p className="text-sm" style={{ color: comp.config.color }}>{comp.config.trend}</p>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="p-6 rounded-2xl" style={{ background: '#1E293B' }}>
        <h2 className="text-xl font-bold text-white mb-6">模板信息</h2>
        <Descriptions column={2} labelStyle={{ color: '#94A3B8' }} contentStyle={{ color: '#E2E8F0' }}>
          <Descriptions.Item label="版本">{template.version}</Descriptions.Item>
          <Descriptions.Item label="更新时间">{formatDate(template.updatedAt)}</Descriptions.Item>
          <Descriptions.Item label="发布时间">{formatDate(template.createdAt)}</Descriptions.Item>
          <Descriptions.Item label="浏览量">{formatNumber(template.viewCount)}</Descriptions.Item>
          <Descriptions.Item label="标签" span={2}>
            {template.tags.map((tag, idx) => (
              <Tag key={idx} style={{ borderRadius: '4px' }}>{tag}</Tag>
            ))}
          </Descriptions.Item>
        </Descriptions>
      </div>

      <div className="p-6 rounded-2xl" style={{ background: '#1E293B' }}>
        <h2 className="text-xl font-bold text-white mb-6">发表评论</h2>
        {hasRated ? (
          <div className="p-4 rounded-lg" style={{ background: '#0F172A' }}>
            <div className="flex items-center gap-3">
              <CheckCircleOutlined style={{ color: '#10B981', fontSize: 24 }} />
              <div>
                <p className="text-white font-medium">您已对此模板评分</p>
                <div className="flex items-center gap-2 mt-1">
                  <Rate disabled value={userRating || 0} count={5} />
                  <span className="text-slate-400 text-sm">感谢您的评价！</span>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <span className="text-slate-400">评分：</span>
              <Rate value={rating} onChange={setRating} />
            </div>
            <TextArea
              value={commentText}
              onChange={(e) => setCommentText(e.target.value)}
              placeholder="分享您使用此模板的体验..."
              rows={4}
              style={{ background: '#0F172A', border: '1px solid #334155', color: '#fff' }}
            />
            <Button
              type="primary"
              icon={<SendOutlined />}
              onClick={handleSubmitComment}
              disabled={!commentText.trim()}
            >
              发表评论
            </Button>
          </div>
        )}

        <div className="mt-8">
          <h3 className="text-lg font-semibold text-white mb-4">
            全部评论 ({comments.length})
          </h3>
          <List
            dataSource={comments}
            renderItem={(comment) => (
              <List.Item key={comment._id} style={{ borderBottom: '1px solid #334155' }}>
                <List.Item.Meta
                  avatar={<Avatar icon={<UserOutlined />} src={comment.user.avatar} />}
                  title={
                    <div className="flex items-center gap-2">
                      <span className="text-white">{comment.user.username}</span>
                      <Rate disabled value={comment.rating} count={5} />
                      <span className="text-slate-400 text-sm">{formatDate(comment.createdAt)}</span>
                    </div>
                  }
                  description={<p className="text-slate-300">{comment.content}</p>}
                />
              </List.Item>
            )}
          />
        </div>
      </div>

      <Modal
        open={previewVisible}
        footer={null}
        onCancel={() => setPreviewVisible(false)}
        width="90vw"
        style={{ top: 20 }}
      >
        <Carousel autoplay>
          {[template.thumbnail, ...template.previewImages].map((img, idx) => (
            <div key={idx}>
              <img src={img} alt={`预览 ${idx + 1}`} style={{ width: '100%', maxHeight: '80vh', objectFit: 'contain' }} />
            </div>
          ))}
        </Carousel>
      </Modal>
    </div>
  );
};

export default TemplateDetailPage;
