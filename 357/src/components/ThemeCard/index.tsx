import React, { useState } from 'react';
import { Star, Edit2, Trash2, Check, X } from 'lucide-react';
import type { SavedTheme, RecommendedTheme } from '@/types/theme';
import './index.less';

interface ThemeCardProps {
  theme: SavedTheme | RecommendedTheme;
  onApply?: () => void;
  onFavorite?: () => void;
  onDelete?: (e?: React.MouseEvent) => void;
  onRename?: (name: string, description: string) => void;
  showActions?: boolean;
  isSaved?: boolean;
}

const ThemeCard: React.FC<ThemeCardProps> = ({
  theme,
  onApply,
  onFavorite,
  onDelete,
  onRename,
  showActions = true,
  isSaved = false,
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editName, setEditName] = useState(isSaved ? (theme as SavedTheme).name : theme.name);
  const [editDesc, setEditDesc] = useState(isSaved ? (theme as SavedTheme).description : theme.description);

  const previewColors = (theme as RecommendedTheme).previewColors || (theme as SavedTheme).previewColors || [];

  const handleSave = () => {
    if (onRename && editName.trim()) {
      onRename(editName.trim(), editDesc.trim());
    }
    setIsEditing(false);
  };

  const handleCancel = () => {
    setEditName((theme as SavedTheme).name || theme.name);
    setEditDesc((theme as SavedTheme).description || theme.description);
    setIsEditing(false);
  };

  const savedTheme = isSaved ? (theme as SavedTheme) : null;

  return (
    <div className={`theme-card ${isEditing ? 'editing' : ''}`}>
      {isEditing ? (
        <div className="theme-card-edit">
          <input
            className="edit-input"
            value={editName}
            onChange={(e) => setEditName(e.target.value)}
            placeholder="主题名称"
            autoFocus
          />
          <textarea
            className="edit-textarea"
            value={editDesc}
            onChange={(e) => setEditDesc(e.target.value)}
            placeholder="主题描述"
            rows={2}
          />
          <div className="edit-actions">
            <button className="edit-btn cancel" onClick={handleCancel}>
              <X size={14} />
              取消
            </button>
            <button className="edit-btn confirm" onClick={handleSave}>
              <Check size={14} />
              保存
            </button>
          </div>
        </div>
      ) : (
        <>
          <div className="theme-card-preview">
            {previewColors.slice(0, 5).map((color: string, index: number) => (
              <div
                key={index}
                className="preview-color"
                style={{ backgroundColor: color }}
                title={color}
              />
            ))}
          </div>
          <div className="theme-card-info">
            <h4 className="theme-name">{theme.name}</h4>
            <p className="theme-description">{theme.description}</p>
            {isSaved && (
              <div className="theme-meta">
                <span className="category-tag">
                  {(savedTheme as SavedTheme).isFavorite ? '★ 已收藏' : '团队库'}
                </span>
              </div>
            )}
          </div>
          {showActions && (
            <div className="theme-card-actions">
              {onFavorite && isSaved && (
                <button
                  className={`action-btn ${(savedTheme as SavedTheme).isFavorite ? 'favorited' : ''}`}
                  onClick={onFavorite}
                  title={(savedTheme as SavedTheme).isFavorite ? '取消收藏' : '收藏'}
                >
                  <Star size={16} fill={(savedTheme as SavedTheme).isFavorite ? 'currentColor' : 'none'} />
                </button>
              )}
              {onRename && isSaved && (
                <button
                  className="action-btn"
                  onClick={() => setIsEditing(true)}
                  title="重命名"
                >
                  <Edit2 size={16} />
                </button>
              )}
              {onDelete && isSaved && (
                <button
                  className="action-btn delete"
                  onClick={onDelete}
                  title="删除"
                >
                  <Trash2 size={16} />
                </button>
              )}
            </div>
          )}
          {onApply && (
            <button className="apply-btn" onClick={onApply}>
              应用
            </button>
          )}
        </>
      )}
    </div>
  );
};

export default React.memo(ThemeCard);
