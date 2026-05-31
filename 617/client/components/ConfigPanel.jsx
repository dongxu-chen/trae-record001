import React from 'react';

function ConfigPanel({
  config,
  onConfigChange,
  onGenerate,
  loading,
  error,
  onRegenerateColors,
  onUseExtractedColors,
  hasData,
  extractedColors,
  animationTypes,
  debugMode,
  onDebugModeChange
}) {
  return (
    <div className="config-panel">
      {error && (
        <div className="error-message">
          {error}
        </div>
      )}
      
      <div className="config-section">
        <h3>页面地址</h3>
        <div className="form-group">
          <label>输入网页URL</label>
          <div className="url-input-wrapper">
            <input
              type="text"
              placeholder="https://example.com"
              value={config.url}
              onChange={(e) => onConfigChange('url', e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && onGenerate()}
            />
            <button
              className="generate-btn"
              onClick={onGenerate}
              disabled={loading || !config.url}
            >
              生成
            </button>
          </div>
        </div>
      </div>
      
      <div className="config-section">
        <h3>设备类型</h3>
        <div className="form-group">
          <div className="device-selector">
            <button
              className={`device-btn ${config.device === 'desktop' ? 'active' : ''}`}
              onClick={() => onConfigChange('device', 'desktop')}
            >
              💻 桌面端
            </button>
            <button
              className={`device-btn ${config.device === 'mobile' ? 'active' : ''}`}
              onClick={() => onConfigChange('device', 'mobile')}
            >
              📱 移动端
            </button>
          </div>
        </div>
      </div>
      
      <div className="config-section">
        <h3>颜色设置</h3>
        
        <div className="form-group">
          <div className="toggle-group">
            <div className="toggle-item">
              <span>自动提取页面主色调</span>
              <div
                className={`toggle-switch ${config.autoColor ? 'active' : ''}`}
                onClick={() => onConfigChange('autoColor', !config.autoColor)}
              />
            </div>
          </div>
        </div>
        
        {extractedColors && (
          <div className="form-group extracted-colors">
            <label style={{ marginBottom: '8px' }}>🎨 页面提取颜色</label>
            <div style={{ display: 'flex', gap: '8px', marginBottom: '12px' }}>
              <div style={{ flex: 1 }}>
                <div style={{ 
                  height: '32px', 
                  borderRadius: '6px', 
                  background: extractedColors.backgroundColor,
                  border: '1px solid #ddd'
                }}></div>
                <div style={{ fontSize: '11px', textAlign: 'center', marginTop: '4px', color: '#888' }}>
                  {extractedColors.backgroundColor}
                </div>
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ 
                  height: '32px', 
                  borderRadius: '6px', 
                  background: extractedColors.highlightColor,
                  border: '1px solid #ddd'
                }}></div>
                <div style={{ fontSize: '11px', textAlign: 'center', marginTop: '4px', color: '#888' }}>
                  {extractedColors.highlightColor}
                </div>
              </div>
            </div>
            {!config.autoColor && (
              <button
                className="action-btn"
                style={{ width: '100%', fontSize: '12px', padding: '6px 12px' }}
                onClick={onUseExtractedColors}
              >
                使用提取的颜色
              </button>
            )}
          </div>
        )}
        
        {!config.autoColor && (
          <div className="form-group">
            <div className="color-picker-wrapper">
              <div className="color-item">
                <label>背景色</label>
                <div className="color-input-wrapper">
                  <input
                    type="color"
                    value={config.backgroundColor || '#f0f0f0'}
                    onChange={(e) => onConfigChange('backgroundColor', e.target.value)}
                  />
                  <input
                    type="text"
                    value={config.backgroundColor || '#f0f0f0'}
                    onChange={(e) => onConfigChange('backgroundColor', e.target.value)}
                  />
                </div>
              </div>
              <div className="color-item">
                <label>高亮色</label>
                <div className="color-input-wrapper">
                  <input
                    type="color"
                    value={config.highlightColor || '#e0e0e0'}
                    onChange={(e) => onConfigChange('highlightColor', e.target.value)}
                  />
                  <input
                    type="text"
                    value={config.highlightColor || '#e0e0e0'}
                    onChange={(e) => onConfigChange('highlightColor', e.target.value)}
                  />
                </div>
              </div>
            </div>
          </div>
        )}
        
        {hasData && !config.autoColor && (
          <button
            className="action-btn primary"
            style={{ width: '100%', marginTop: '12px' }}
            onClick={onRegenerateColors}
          >
            应用新颜色
          </button>
        )}
      </div>
      
      <div className="config-section">
        <h3>动画效果</h3>
        <div className="form-group">
          <div className="toggle-group">
            <div className="toggle-item">
              <span>启用骨架动画</span>
              <div
                className={`toggle-switch ${config.animation ? 'active' : ''}`}
                onClick={() => onConfigChange('animation', !config.animation)}
              />
            </div>
          </div>
        </div>
        
        {config.animation && (
          <div className="form-group">
            <label>动画类型</label>
            <select
              className="select-input"
              value={config.animationType}
              onChange={(e) => onConfigChange('animationType', e.target.value)}
            >
              {animationTypes.map(type => (
                <option key={type.value} value={type.value}>
                  {type.label}
                </option>
              ))}
            </select>
          </div>
        )}
        
        {config.animation && (
          <div className="form-group">
            <label>动画速度: {config.animationSpeed}s</label>
            <input
              type="range"
              min="0.5"
              max="3"
              step="0.1"
              value={config.animationSpeed}
              onChange={(e) => onConfigChange('animationSpeed', parseFloat(e.target.value))}
              className="range-input"
            />
          </div>
        )}
      </div>
      
      <div className="config-section">
        <h3>元素处理</h3>
        <div className="form-group">
          <div className="toggle-group">
            <div className="toggle-item">
              <span>移除图片内容</span>
              <div
                className={`toggle-switch ${config.removeImages ? 'active' : ''}`}
                onClick={() => onConfigChange('removeImages', !config.removeImages)}
              />
            </div>
            <div className="toggle-item">
              <span>移除文字内容</span>
              <div
                className={`toggle-switch ${config.removeText ? 'active' : ''}`}
                onClick={() => onConfigChange('removeText', !config.removeText)}
              />
            </div>
          </div>
        </div>
      </div>
      
      {hasData && (
        <div className="config-section">
          <h3>调试模式</h3>
          <div className="form-group">
            <div className="toggle-group">
              <div className="toggle-item">
                <span>启用元素编辑</span>
                <div
                  className={`toggle-switch ${debugMode ? 'active' : ''}`}
                  onClick={() => onDebugModeChange(!debugMode)}
                />
              </div>
            </div>
            {debugMode && (
              <div style={{ marginTop: '12px', padding: '12px', background: '#f5f5f5', borderRadius: '8px', fontSize: '12px' }}>
                <p>💡 点击预览中的元素可以选中并编辑：</p>
                <ul style={{ marginLeft: '16px', marginTop: '8px' }}>
                  <li>调整位置和尺寸</li>
                  <li>删除不需要的元素</li>
                  <li>实时预览效果</li>
                </ul>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default ConfigPanel;
