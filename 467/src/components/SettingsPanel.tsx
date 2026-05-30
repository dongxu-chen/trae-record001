import React from 'react';
import type { CompressionSettings, ImageFormat, OperationMode, SmartSuggestion } from '../types';

interface SettingsPanelProps {
  settings: CompressionSettings;
  onSettingsChange: (settings: CompressionSettings) => void;
  mode: OperationMode;
  onModeChange: (mode: OperationMode) => void;
  suggestion?: SmartSuggestion;
  onApplySuggestion: (suggestion: SmartSuggestion) => void;
}

const formatOptions: { value: ImageFormat; label: string; desc: string }[] = [
  { value: 'jpeg', label: 'JPEG', desc: '照片最佳' },
  { value: 'png', label: 'PNG', desc: '无损透明' },
  { value: 'webp', label: 'WebP', desc: '现代高效' }
];

const modeOptions: { value: OperationMode; label: string; icon: string }[] = [
  { value: 'compress', label: '压缩', icon: '🗜️' },
  { value: 'convert', label: '格式转换', icon: '🔄' }
];

export const SettingsPanel: React.FC<SettingsPanelProps> = ({
  settings,
  onSettingsChange,
  mode,
  onModeChange,
  suggestion,
  onApplySuggestion
}) => {
  const handleQualityChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onSettingsChange({ ...settings, quality: Number(e.target.value) });
  };

  const handleFormatChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    onSettingsChange({ ...settings, format: e.target.value as ImageFormat });
  };

  const handleMaxSizeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    if (value === '') {
      const { maxWidthOrHeight, ...rest } = settings;
      onSettingsChange(rest);
    } else {
      onSettingsChange({ ...settings, maxWidthOrHeight: Number(value) });
    }
  };

  return (
    <div className="settings-panel">
      <h3>操作设置</h3>

      <div className="setting-group">
        <label>
          操作模式
          <div className="mode-switcher">
            {modeOptions.map(opt => (
              <button
                key={opt.value}
                className={`mode-btn ${mode === opt.value ? 'active' : ''}`}
                onClick={() => onModeChange(opt.value)}
              >
                <span className="mode-icon">{opt.icon}</span>
                <span className="mode-label">{opt.label}</span>
              </button>
            ))}
          </div>
        </label>
      </div>

      <div className="setting-group">
        <label>
          {mode === 'convert' ? '目标格式' : '输出格式'}
          <select value={settings.format} onChange={handleFormatChange}>
            {formatOptions.map(opt => (
              <option key={opt.value} value={opt.value}>
                {opt.label} - {opt.desc}
              </option>
            ))}
          </select>
        </label>
      </div>

      {mode === 'compress' && (
        <>
          <div className="setting-group">
            <label>
              压缩质量: {settings.quality}%
              <input
                type="range"
                min="10"
                max="100"
                value={settings.quality}
                onChange={handleQualityChange}
                className="quality-slider"
              />
              <div className="quality-labels">
                <span>高压缩</span>
                <span>高质量</span>
              </div>
            </label>
          </div>
          <div className="setting-group">
            <label>
              最大尺寸 (可选，保持原始分辨率留空)
              <input
                type="number"
                placeholder="保持原始分辨率"
                value={settings.maxWidthOrHeight ?? ''}
                onChange={handleMaxSizeChange}
                min="100"
                max="10000"
                className="max-size-input"
              />
              <span className="hint">像素，最大边限制</span>
            </label>
          </div>
        </>
      )}

      {suggestion && mode === 'compress' && (
        <div className="smart-suggestion">
          <div className="suggestion-header">
            <span className="suggestion-icon">🧠</span>
            <span className="suggestion-title">智能建议</span>
          </div>
          <div className="suggestion-body">
            <p className="suggestion-reason">{suggestion.reason}</p>
            <div className="suggestion-params">
              <span className="suggestion-param">
                格式: <strong>{suggestion.format.toUpperCase()}</strong>
              </span>
              <span className="suggestion-param">
                质量: <strong>{suggestion.quality}%</strong>
              </span>
              <span className="suggestion-param">
                预估压缩率: <strong>{Math.round(suggestion.estimatedRatio * 100)}%</strong>
              </span>
            </div>
          </div>
          <button
            className="btn btn-suggestion"
            onClick={() => onApplySuggestion(suggestion)}
          >
            应用建议
          </button>
        </div>
      )}
    </div>
  );
};
