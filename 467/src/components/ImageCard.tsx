import React, { useState, useCallback } from 'react';
import type { ImageItem, ImageFormat } from '../types';
import { formatFileSize, calculateSavings } from '../utils/format';
import { downloadSingleImage } from '../utils/zipDownload';

interface ImageCardProps {
  image: ImageItem;
  format: ImageFormat;
  mode: 'compress' | 'convert';
  onRemove: (id: string) => void;
}

export const ImageCard: React.FC<ImageCardProps> = ({ image, format, mode, onRemove }) => {
  const [showComparison, setShowComparison] = useState(false);
  const [sliderPosition, setSliderPosition] = useState(50);

  const handleSliderMove = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    if (!showComparison) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const percentage = (x / rect.width) * 100;
    setSliderPosition(Math.max(0, Math.min(100, percentage)));
  }, [showComparison]);

  const handleDownload = () => {
    downloadSingleImage(image, format);
  };

  const handleRemove = () => {
    onRemove(image.id);
  };

  const getStatusBadge = () => {
    switch (image.status) {
      case 'pending':
        return <span className="status-badge pending">等待中</span>;
      case 'analyzing':
        return <span className="status-badge analyzing">分析中</span>;
      case 'compressing':
        return <span className="status-badge compressing">{mode === 'convert' ? '转换中' : '压缩中'} {image.progress}%</span>;
      case 'completed':
        return <span className="status-badge completed">{mode === 'convert' ? '已转换' : '已完成'}</span>;
      case 'error':
        return <span className="status-badge error">失败</span>;
    }
  };

  const formatLabel = (fmt: string) => {
    switch (fmt) {
      case 'jpeg': return 'JPG';
      case 'png': return 'PNG';
      case 'webp': return 'WebP';
      default: return fmt.toUpperCase();
    }
  };

  return (
    <div className="image-card">
      <div className="image-header">
        <div className="image-info">
          <span className="image-name" title={image.file.name}>
            {image.file.name}
          </span>
          <span className="image-dimensions">
            {image.width} × {image.height}
          </span>
        </div>
        <div className="image-actions">
          {getStatusBadge()}
          {image.status === 'completed' && (
            <>
              <button
                className="action-btn compare-btn"
                onClick={() => setShowComparison(!showComparison)}
                title="对比效果"
              >
                🔄
              </button>
              <button
                className="action-btn download-btn"
                onClick={handleDownload}
                title="下载"
              >
                ⬇️
              </button>
            </>
          )}
          <button
            className="action-btn remove-btn"
            onClick={handleRemove}
            title="移除"
          >
            ✕
          </button>
        </div>
      </div>

      <div
        className={`image-preview-container ${showComparison ? 'comparison-mode' : ''}`}
        onMouseMove={handleSliderMove}
      >
        {showComparison && image.compressedUrl ? (
          <>
            <img src={image.compressedUrl} alt="compressed" className="preview-img" />
            <div
              className="comparison-overlay"
              style={{ clipPath: `inset(0 ${100 - sliderPosition}% 0 0)` }}
            >
              <img src={image.originalUrl} alt="original" className="preview-img" />
            </div>
            <div
              className="comparison-slider"
              style={{ left: `${sliderPosition}%` }}
            >
              <div className="slider-handle">
                <span className="slider-label left">原图</span>
                <span className="slider-label right">压缩后</span>
              </div>
            </div>
          </>
        ) : (
          <img
            src={image.compressedUrl || image.originalUrl}
            alt={image.file.name}
            className="preview-img"
          />
        )}

        {image.status === 'analyzing' && (
          <div className="analyzing-overlay">
            <div className="analyzing-spinner" />
            <span className="analyzing-text">智能分析中...</span>
          </div>
        )}

        {image.status === 'compressing' && (
          <div className="progress-overlay">
            <div className="progress-bar">
              <div
                className="progress-fill"
                style={{ width: `${image.progress}%` }}
              />
            </div>
            <span className="progress-text">{image.progress}%</span>
          </div>
        )}

        {image.status === 'error' && (
          <div className="error-overlay">
            <span className="error-text">{image.error || (mode === 'convert' ? '转换失败' : '压缩失败')}</span>
          </div>
        )}

        <div className="image-badges">
          <span className="format-badge original">{formatLabel(image.originalFormat)}</span>
          {image.hasAlpha && <span className="alpha-badge">α</span>}
          <span className={`complexity-badge ${image.colorComplexity}`}>
            {image.colorComplexity === 'low' ? '简单' : image.colorComplexity === 'medium' ? '中等' : '复杂'}
          </span>
        </div>
      </div>

      <div className="image-stats">
        <div className="stat-item">
          <span className="stat-label">原始</span>
          <span className="stat-value">{formatFileSize(image.originalSize)}</span>
        </div>
        {image.estimatedSize !== undefined && image.status !== 'completed' && (
          <>
            <div className="stat-arrow estimate">→</div>
            <div className="stat-item">
              <span className="stat-label">预估</span>
              <span className="stat-value estimated">
                ~{formatFileSize(image.estimatedSize)}
              </span>
            </div>
            <div className="stat-item savings">
              <span className="savings-badge estimated">
                -{calculateSavings(image.originalSize, image.estimatedSize)}%
              </span>
            </div>
          </>
        )}
        {image.compressedSize !== undefined && (
          <>
            <div className="stat-arrow">→</div>
            <div className="stat-item">
              <span className="stat-label">{mode === 'convert' ? '转换后' : '压缩后'}</span>
              <span className="stat-value compressed">
                {formatFileSize(image.compressedSize)}
              </span>
            </div>
            <div className="stat-item savings">
              <span className="savings-badge">
                -{calculateSavings(image.originalSize, image.compressedSize)}%
              </span>
            </div>
          </>
        )}
      </div>

      {image.suggestion && image.status === 'pending' && mode === 'compress' && (
        <div className="card-suggestion">
          <span className="card-suggestion-icon">💡</span>
          <span className="card-suggestion-text">
            建议 {formatLabel(image.suggestion.format)} Q{image.suggestion.quality}
          </span>
        </div>
      )}
    </div>
  );
};
