import React, { useEffect, useState } from 'react';
import { Row, Col, Card, Spin, Tag } from 'antd';
import { ThunderboltOutlined, StarOutlined, EyeOutlined, DownloadOutlined } from '@ant-design/icons';
import { useSelector } from 'react-redux';
import { RootState } from '../store';
import { recommendAPI } from '../services/api';
import { Template } from '../types';
import { formatNumber } from '../utils/helpers';
import { useNavigate } from 'react-router-dom';

interface RecommendListProps {
  limit?: number;
  title?: string;
}

const RecommendList: React.FC<RecommendListProps> = ({ limit = 8, title = 'AI 智能推荐' }) => {
  const navigate = useNavigate();
  const { isAuthenticated } = useSelector((state: RootState) => state.auth);
  const [recommendations, setRecommendations] = useState<(Template & { reason: string })[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isAuthenticated) {
      fetchRecommendations();
    }
  }, [isAuthenticated, limit]);

  const fetchRecommendations = async () => {
    setLoading(true);
    try {
      const response = await recommendAPI.getRecommendations(limit);
      setRecommendations(response.recommendations);
    } catch (error) {
      console.error('获取推荐失败:', error);
    } finally {
      setLoading(false);
    }
  };

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="mb-12">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-white flex items-center gap-3">
          <ThunderboltOutlined style={{ color: '#FBBF24' }} />
          {title}
        </h2>
      </div>
      
      <Spin spinning={loading}>
        <Row gutter={[16, 16]}>
          {recommendations.map((template) => (
            <Col xs={24} sm={12} md={8} lg={6} key={template._id}>
              <Card
                hoverable
                className="h-full cursor-pointer"
                style={{ 
                  background: '#1E293B', 
                  border: 'none',
                  borderRadius: '16px',
                  overflow: 'hidden'
                }}
                onClick={() => navigate(`/templates/${template._id}`)}
                bodyStyle={{ padding: 0 }}
              >
                <div className="relative">
                  <img
                    src={template.thumbnail}
                    alt={template.title}
                    className="w-full h-40 object-cover"
                  />
                  <Tag
                    color="gold"
                    className="absolute top-3 left-3"
                    style={{ borderRadius: '4px' }}
                  >
                    AI 推荐
                  </Tag>
                </div>
                <div className="p-4">
                  <h3 className="text-white font-semibold mb-2 truncate">{template.title}</h3>
                  <p className="text-slate-400 text-sm mb-3 line-clamp-2" style={{ height: '40px' }}>
                    {template.reason}
                  </p>
                  <div className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-3 text-slate-400">
                      <span className="flex items-center gap-1">
                        <EyeOutlined /> {formatNumber(template.viewCount)}
                      </span>
                      <span className="flex items-center gap-1">
                        <DownloadOutlined /> {formatNumber(template.downloadCount)}
                      </span>
                    </div>
                    <div className="flex items-center gap-1 text-yellow-400">
                      <StarOutlined />
                      <span>{template.rating?.toFixed(1) || '0'}</span>
                    </div>
                  </div>
                </div>
              </Card>
            </Col>
          ))}
        </Row>
      </Spin>
    </div>
  );
};

export default RecommendList;
