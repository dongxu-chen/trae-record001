import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Button, Spin, message, Tag, Space, FloatButton } from 'antd';
import { ArrowLeftOutlined, DownloadOutlined, EditOutlined, FullscreenOutlined } from '@ant-design/icons';
import { templateAPI } from '../services/api';
import { Template } from '../types';
import ChartRenderer from '../components/ChartRenderer';

const PreviewPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [template, setTemplate] = useState<Template | null>(null);
  const [loading, setLoading] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);

  useEffect(() => {
    if (id) {
      fetchTemplate();
    }
  }, [id]);

  const fetchTemplate = async () => {
    if (!id) return;
    setLoading(true);
    try {
      const response = await templateAPI.getTemplateById(id);
      setTemplate(response.template);
    } catch (error) {
      console.error('获取模板详情失败:', error);
      message.error('获取模板详情失败');
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async () => {
    if (!id) return;
    try {
      await templateAPI.downloadTemplate(id);
      message.success('下载成功！');
    } catch (error) {
      message.error('下载失败，请重试');
    }
  };

  const handleEdit = () => {
    navigate(`/editor/${id}`);
  };

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen();
      setIsFullscreen(true);
    } else {
      document.exitFullscreen();
      setIsFullscreen(false);
    }
  };

  if (loading || !template) {
    return (
      <div className="flex items-center justify-center h-screen" style={{ background: '#0F172A' }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div className="min-h-screen" style={{ background: '#0F172A' }}>
      <div className="fixed top-0 left-0 right-0 z-50 px-6 py-4 flex items-center justify-between"
           style={{ background: 'rgba(15, 23, 42, 0.95)', backdropFilter: 'blur(10px)' }}>
        <div className="flex items-center gap-4">
          <Button
            type="text"
            icon={<ArrowLeftOutlined />}
            onClick={() => navigate(-1)}
            style={{ color: '#fff' }}
          >
            返回
          </Button>
          <div>
            <h1 className="text-xl font-bold text-white">{template.title}</h1>
            <div className="flex items-center gap-2 mt-1">
              <Tag color="blue">在线预览</Tag>
              <span className="text-slate-400 text-sm">
                {template.components?.length || 0} 个组件
              </span>
            </div>
          </div>
        </div>
        <Space>
          <Button icon={<FullscreenOutlined />} onClick={toggleFullscreen}>
            {isFullscreen ? '退出全屏' : '全屏预览'}
          </Button>
          <Button type="primary" icon={<DownloadOutlined />} onClick={handleDownload}>
            下载模板
          </Button>
          <Button icon={<EditOutlined />} onClick={handleEdit}>
            在线编辑
          </Button>
        </Space>
      </div>

      <div className="pt-20 pb-8 px-6">
        <div className="max-w-7xl mx-auto">
          <div className="rounded-2xl overflow-hidden" style={{ background: '#1E293B' }}>
            {template.components && template.components.length > 0 ? (
              <div
                className="p-6"
                style={{
                  display: 'grid',
                  gridTemplateColumns: `repeat(${template.layout?.gridCols || 12}, 1fr)`,
                  gridAutoRows: '120px',
                  gap: `${template.layout?.gutter || 16}px`,
                  background: template.layout?.backgroundColor || '#0F172A',
                  minHeight: 'calc(100vh - 200px)'
                }}
              >
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
                    {comp.type === 'chart' && (
                      <ChartRenderer component={comp} style={{ height: 'calc(100% - 30px)' }} />
                    )}
                    {comp.type === 'metric' && (
                      <div className="text-center py-4">
                        <p className="text-3xl font-bold text-white">{comp.config.value}</p>
                        <p className="text-sm" style={{ color: comp.config.color }}>{comp.config.trend}</p>
                      </div>
                    )}
                    {comp.type === 'text' && (
                      <div className="text-slate-300">{comp.config.content || '文本组件'}</div>
                    )}
                    {comp.type === 'table' && (
                      <div className="text-slate-400">表格组件</div>
                    )}
                    {comp.type === 'image' && (
                      <div className="text-slate-400">图片组件</div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-32">
                <p className="text-slate-400 text-lg mb-4">该模板暂无预览内容</p>
                <Button type="primary" onClick={handleDownload}>
                  下载后查看完整内容
                </Button>
              </div>
            )}
          </div>

          <div className="mt-6 p-6 rounded-2xl" style={{ background: '#1E293B' }}>
            <h2 className="text-xl font-bold text-white mb-4">模板信息</h2>
            <p className="text-slate-400 mb-4">{template.description}</p>
            <div className="flex flex-wrap gap-2">
              {template.tags?.map((tag, idx) => (
                <Tag key={idx}>{tag}</Tag>
              ))}
            </div>
          </div>
        </div>
      </div>

      <FloatButton.Group>
        <FloatButton
          icon={<DownloadOutlined />}
          onClick={handleDownload}
          tooltip="下载模板"
          type="primary"
        />
        <FloatButton
          icon={<EditOutlined />}
          onClick={handleEdit}
          tooltip="在线编辑"
        />
        <FloatButton
          icon={<FullscreenOutlined />}
          onClick={toggleFullscreen}
          tooltip="全屏预览"
        />
        <FloatButton.BackTop />
      </FloatButton.Group>
    </div>
  );
};

export default PreviewPage;
