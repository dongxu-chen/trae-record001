import React from 'react';
import { Card, Tag, Rate, Button } from 'antd';
import { EyeOutlined, DownloadOutlined, HeartOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { Template } from '../types';
import { getCategoryInfo, getComplexityInfo, formatNumber } from '../utils/helpers';

interface TemplateCardProps {
  template: Template;
  onFavorite?: (id: string) => void;
  isFavorite?: boolean;
}

const TemplateCard: React.FC<TemplateCardProps> = ({ template, onFavorite, isFavorite }) => {
  const navigate = useNavigate();
  const categoryInfo = getCategoryInfo(template.category);
  const complexityInfo = getComplexityInfo(template.complexity);

  return (
    <Card
      hoverable
      className="template-card overflow-hidden group"
      style={{
        background: '#1E293B',
        borderRadius: '12px',
        border: '1px solid #334155'
      }}
      bodyStyle={{ padding: 0 }}
      onClick={() => navigate(`/templates/${template._id}`)}
    >
      <div className="relative overflow-hidden">
        <img
          src={template.thumbnail}
          alt={template.title}
          className="w-full h-48 object-cover transition-transform duration-300 group-hover:scale-105"
        />
        <div className="absolute top-3 left-3 flex gap-2">
          <Tag color={categoryInfo.color} style={{ borderRadius: '4px' }}>
            {categoryInfo.label}
          </Tag>
          {template.price > 0 ? (
            <Tag color="orange" style={{ borderRadius: '4px' }}>
              ¥{template.price}
            </Tag>
          ) : (
            <Tag color="green" style={{ borderRadius: '4px' }}>
              免费
            </Tag>
          )}
        </div>
        <Button
          type="text"
          icon={<HeartOutlined style={{ color: isFavorite ? '#EF4444' : undefined }} />}
          className="absolute top-3 right-3 bg-slate-800/80 backdrop-blur"
          onClick={(e) => {
            e.stopPropagation();
            onFavorite?.(template._id);
          }}
        />
      </div>
      <div className="p-4">
        <h3 className="text-white font-semibold text-lg mb-2 truncate">
          {template.title}
        </h3>
        <p className="text-slate-400 text-sm mb-3 line-clamp-2 h-10">
          {template.description}
        </p>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4 text-slate-400 text-sm">
            <span className="flex items-center gap-1">
              <EyeOutlined /> {formatNumber(template.viewCount)}
            </span>
            <span className="flex items-center gap-1">
              <DownloadOutlined /> {formatNumber(template.downloadCount)}
            </span>
          </div>
          <Rate disabled value={template.rating} count={5} />
        </div>
        <div className="flex items-center gap-2 mt-3">
          <Tag color={complexityInfo.color} style={{ borderRadius: '4px', marginRight: 0 }}>
            {complexityInfo.label}
          </Tag>
          {template.tags.slice(0, 2).map((tag, index) => (
            <Tag key={index} style={{ borderRadius: '4px', marginRight: 0 }}>
              {tag}
            </Tag>
          ))}
        </div>
      </div>
    </Card>
  );
};

export default TemplateCard;
