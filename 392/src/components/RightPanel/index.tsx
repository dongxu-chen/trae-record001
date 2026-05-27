import React from 'react';
import { useIconStore, getIconById } from '../../store/iconStore';
import { Heart, Clock, X, Trash2 } from 'lucide-react';

interface RightPanelProps {
  type: 'favorites' | 'recent';
  onClose: () => void;
}

const RightPanel: React.FC<RightPanelProps> = ({ type, onClose }) => {
  const { favorites, recent, setActiveIcon, currentColor } = useIconStore();

  const items = type === 'favorites'
    ? Object.values(favorites).sort((a, b) => b.addedAt - a.addedAt)
    : Object.values(recent).sort((a, b) => b.usedAt - a.usedAt);

  const title = type === 'favorites' ? '收藏夹' : '最近使用';
  const emptyText = type === 'favorites' ? '暂无收藏的图标' : '暂无使用记录';

  const formatTime = (timestamp: number) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    
    if (diff < 60000) return '刚刚';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`;
    return date.toLocaleDateString();
  };

  return (
    <div className="w-72 bg-[#12121a] border-l border-[#2a2a3a] flex flex-col">
      <div className="p-4 border-b border-[#2a2a3a] flex items-center justify-between">
        <div className="flex items-center gap-2">
          {type === 'favorites' ? (
            <Heart size={16} className="text-[#4F46E5]" />
          ) : (
            <Clock size={16} className="text-[#06B6D4]" />
          )}
          <h3 className="text-sm font-semibold text-gray-200">{title}</h3>
          <span className="text-xs text-gray-500">({items.length})</span>
        </div>
        <button
          onClick={onClose}
          className="p-1 rounded-md text-gray-500 hover:text-gray-300 hover:bg-[#1a1a2a] transition-all"
        >
          <X size={16} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {items.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            {type === 'favorites' ? (
              <Heart size={48} className="text-gray-700 mb-4" />
            ) : (
              <Clock size={48} className="text-gray-700 mb-4" />
            )}
            <p className="text-sm text-gray-500">{emptyText}</p>
          </div>
        ) : (
          <div className="space-y-2">
            {items.map((item) => {
              const icon = getIconById(item.iconId);
              if (!icon) return null;
              
              return (
                <div
                  key={item.iconId}
                  onClick={() => setActiveIcon(icon.id)}
                  className="flex items-center gap-3 p-3 rounded-xl bg-[#1a1a2a] hover:bg-[#2a2a3a] cursor-pointer transition-all group"
                >
                  <svg
                    width={24}
                    height={24}
                    viewBox="0 0 24 24"
                    fill={currentColor}
                  >
                    <path d={icon.svgPath} />
                  </svg>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-gray-200 font-medium truncate">
                      {icon.name}
                    </p>
                    <p className="text-xs text-gray-500">
                      {type === 'favorites'
                        ? formatTime(item.addedAt)
                        : formatTime(item.usedAt)}
                    </p>
                  </div>
                  <span className="text-xs px-2 py-0.5 rounded-full bg-[#0a0a12] text-gray-500">
                    {icon.library === 'fontawesome' ? 'FA' : icon.library === 'material' ? 'MD' : '自定义'}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

export default RightPanel;
